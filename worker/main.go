package main

import (
	"context"
	"log"

	"github.com/aws/aws-lambda-go/events"
	"github.com/aws/aws-lambda-go/lambda"
)

var env *Env // kiểu return của loadEnv() cũ
// khai báo thêm ở đây các client mà pollOnce cũ có dùng (S3, DB pool...)

func init() {
	// chạy đúng 1 lần lúc cold start — KHÁC với main() cũ chạy lại mỗi vòng loop
	var err error
	env, err = loadEnv()
	if err != nil {
		log.Fatalf("config error: %v", err)
	}
	log.Printf("using queue: %s", env.SQSQueueURL)
	log.Printf("db config: host=%s port=%s user=%s dbname=%s", env.DBHost, env.DBPort, env.DBUser, env.DBName)

	cfg, err := awsConfig(context.Background(), env)
	if err != nil {
		log.Fatalf("load aws config: %v", err)
	}
	_ = cfg // khởi tạo S3/DB client cần dùng ở đây, gán biến package-level
}

func handler(ctx context.Context, sqsEvent events.SQSEvent) (events.SQSEventResponse, error) {
	var failures []events.SQSBatchItemFailure

	for _, record := range sqsEvent.Records {
		if err := handleMessage(ctx, record); err != nil {
			log.Printf("process error, messageId=%s: %v", record.MessageId, err)
			failures = append(failures, events.SQSBatchItemFailure{ItemIdentifier: record.MessageId})
			continue
		}
	}

	return events.SQSEventResponse{BatchItemFailures: failures}, nil
}

func main() {
	lambda.Start(handler)
}
