package main

import (
	"context"
	"log"
	"os/signal"
	"syscall"
	"time"

	"github.com/aws/aws-sdk-go-v2/service/sqs"
	"github.com/joho/godotenv"
)

func main() {
	ctx, stop := signal.NotifyContext(context.Background(), syscall.SIGINT, syscall.SIGTERM)
	defer stop()

	if err := godotenv.Load(); err != nil {
		log.Println("no .env file found, reading from real environment variables")
	}

	env, err := loadEnv()
	if err != nil {
		log.Fatalf("config error: %v", err) // dừng ngay, không chạy mù với config rỗng
	}
	log.Printf("using queue: %s", env.SQSQueueURL) // in ra để tự mắt thấy giá trị thật đang dùng

	cfg, err := awsConfig(ctx, env)
	if err != nil {
		log.Fatalf("load aws config: %v", err)
	}
	sqsClient := sqs.NewFromConfig(cfg)

	log.Println("worker started")
	for {
		select {
		case <-ctx.Done():
			log.Println("shutdown signal received, exiting cleanly")
			return
		default:
			if err := pollOnce(ctx, sqsClient, env.SQSQueueURL); err != nil {
				log.Printf("poll error: %v", err)
				time.Sleep(5 * time.Second)
			}
		}
	}
}
