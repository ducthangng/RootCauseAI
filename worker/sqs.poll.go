package main

import (
	"context"
	"encoding/csv"
	"encoding/json"
	"fmt"
	"io"
	"log"

	"github.com/aws/aws-sdk-go-v2/aws"
	config "github.com/aws/aws-sdk-go-v2/config"
	"github.com/aws/aws-sdk-go-v2/service/s3"
	"github.com/aws/aws-sdk-go-v2/service/sqs"
	"github.com/aws/aws-sdk-go-v2/service/sqs/types"
)

func pollOnce(ctx context.Context, sqsClient *sqs.Client, queueURL string) error {
	resp, err := sqsClient.ReceiveMessage(ctx, &sqs.ReceiveMessageInput{
		QueueUrl:            aws.String(queueURL),
		MaxNumberOfMessages: 5,
		WaitTimeSeconds:     20, // long polling
	})
	if err != nil {
		return fmt.Errorf("receive message: %w", err)
	}

	for _, msg := range resp.Messages {
		if err := handleMessage(ctx, sqsClient, queueURL, msg); err != nil {
			log.Printf("job failed, message stays in queue for retry: %v", err)
			continue // KHÔNG xoá — SQS tự hiện lại sau visibility timeout, tối đa 3 lần rồi vào DLQ
		}
	}
	return nil
}

func handleMessage(ctx context.Context, sqsClient *sqs.Client, queueURL string, msg types.Message) error {
	var job ProcessJobMessage
	if err := json.Unmarshal([]byte(*msg.Body), &job); err != nil {
		// message không parse được -> xoá luôn, retry cũng không cứu được
		deleteMessage(ctx, sqsClient, queueURL, msg)
		return fmt.Errorf("bad message body, dropped: %w", err)
	}

	rows, err := downloadAndParseCSV(ctx, job.Bucket, job.ResultKey) // bước 3 + 4
	if err != nil {
		return fmt.Errorf("job %s: %w", job.JobID, err)
	}

	if err := insertComplaints(ctx, rows); err != nil { // bước 5
		return fmt.Errorf("job %s: insert: %w", job.JobID, err)
	}

	log.Printf("job %s done: %d rows inserted", job.JobID, len(rows))
	return deleteMessage(ctx, sqsClient, queueURL, msg)
}

func deleteMessage(ctx context.Context, sqsClient *sqs.Client, queueURL string, msg types.Message) error {
	_, err := sqsClient.DeleteMessage(ctx, &sqs.DeleteMessageInput{
		QueueUrl:      aws.String(queueURL),
		ReceiptHandle: msg.ReceiptHandle,
	})
	return err
}

// ── 3. Đọc CSV từ S3 ───────────────────────────────────────────────
func downloadAndParseCSV(ctx context.Context, bucket, key string) ([]Complaint, error) {
	cfg, err := config.LoadDefaultConfig(ctx, config.WithRegion("ap-southeast-1"))
	if err != nil {
		return nil, err
	}
	s3Client := s3.NewFromConfig(cfg)

	obj, err := s3Client.GetObject(ctx, &s3.GetObjectInput{Bucket: aws.String(bucket), Key: aws.String(key)})
	if err != nil {
		return nil, fmt.Errorf("s3 get: %w", err)
	}
	defer obj.Body.Close()

	reader := csv.NewReader(obj.Body)
	reader.FieldsPerRecord = -1 // một vài dòng CDESCR có thể chứa ký tự lạ, đừng chặn cứng số field

	header, err := reader.Read()
	if err != nil {
		return nil, fmt.Errorf("read header: %w", err)
	}
	colIdx := make(map[string]int, len(header))
	for i, h := range header {
		colIdx[h] = i
	}

	var complaints []Complaint
	rowNum := 1
	for {
		record, err := reader.Read()
		if err == io.EOF {
			break
		}
		if err != nil {
			return nil, fmt.Errorf("row %d: %w", rowNum, err)
		}
		rowNum++

		c, err := parseRow(record, colIdx)
		if err != nil {
			log.Printf("row %d: skip, parse error: %v", rowNum, err) // 1 dòng lỗi không chặn cả file
			continue
		}
		complaints = append(complaints, *c)
	}
	return complaints, nil
}
