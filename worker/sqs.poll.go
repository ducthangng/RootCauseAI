package main

import (
	"context"
	"encoding/csv"
	"encoding/json"
	"fmt"
	"io"
	"log"

	"github.com/aws/aws-lambda-go/events"
	"github.com/aws/aws-sdk-go-v2/aws"
	config "github.com/aws/aws-sdk-go-v2/config"
	"github.com/aws/aws-sdk-go-v2/service/s3"
)

func handleMessage(ctx context.Context, msg events.SQSMessage) error {
	var job ProcessJobMessage
	if err := json.Unmarshal([]byte(msg.Body), &job); err != nil {
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
	return nil
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
