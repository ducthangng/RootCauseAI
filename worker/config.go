package main

import (
	"context"
	"fmt"
	"os"
	"sync"

	"github.com/aws/aws-sdk-go-v2/aws"
	config "github.com/aws/aws-sdk-go-v2/config"
	"github.com/aws/aws-sdk-go-v2/credentials"
	"github.com/jackc/pgx/v5/pgxpool"
)

var (
	pgPool *pgxpool.Pool
	pgOnce sync.Once
	pgErr  error
)

// gom tất cả biến môi trường vào 1 chỗ — tránh os.Getenv rải rác khắp file, dễ thấy thiếu biến nào ngay lúc start
type Env struct {
	AWSAccessKeyID     string
	AWSSecretAccessKey string
	AWSRegion          string
	SQSQueueURL        string
	S3Bucket           string
	DBHost             string
	DBPort             string
	DBUser             string
	DBPassword         string
	DBName             string
}

func loadEnv() (*Env, error) {
	e := &Env{
		AWSAccessKeyID:     os.Getenv("AWS_ACCESS_KEY_ID"),
		AWSSecretAccessKey: os.Getenv("AWS_SECRET_ACCESS_KEY"),
		AWSRegion:          os.Getenv("AWS_REGION"),
		SQSQueueURL:        os.Getenv("SQS_QUEUE_URL"),
		S3Bucket:           os.Getenv("S3_BUCKET"),
		DBHost:             os.Getenv("DB_HOST"),
		DBPort:             os.Getenv("DB_PORT"),
		DBUser:             os.Getenv("DB_USER"),
		DBPassword:         os.Getenv("DB_PASSWORD"),
		DBName:             os.Getenv("DB_NAME"),
	}

	// fail nhanh lúc start, không để tới lúc gọi API mới lòi ra thiếu biến — đúng thứ đang gây khó debug cho bạn
	required := map[string]string{
		"AWS_ACCESS_KEY_ID":     e.AWSAccessKeyID,
		"AWS_SECRET_ACCESS_KEY": e.AWSSecretAccessKey,
		"AWS_REGION":            e.AWSRegion,
		"SQS_QUEUE_URL":         e.SQSQueueURL,
		"S3_BUCKET":             e.S3Bucket,
		"DB_HOST":               e.DBHost,
		"DB_USER":               e.DBUser,
		"DB_PASSWORD":           e.DBPassword,
		"DB_NAME":               e.DBName,
	}
	for name, val := range required {
		if val == "" {
			return nil, fmt.Errorf("missing required env var: %s", name)
		}
	}
	return e, nil
}

// dùng cho cả SQS lẫn S3 client — 1 nguồn config duy nhất, khỏi lệch region như lỗi vừa gặp
func awsConfig(ctx context.Context, e *Env) (aws.Config, error) {
	return config.LoadDefaultConfig(ctx,
		config.WithRegion(e.AWSRegion),
		config.WithCredentialsProvider(
			credentials.NewStaticCredentialsProvider(e.AWSAccessKeyID, e.AWSSecretAccessKey, ""),
		),
	)
}

func buildDatabaseURL() string {
	sslMode := "disable"
	if os.Getenv("DB_HOST") != "localhost" {
		sslMode = "require" // Supabase bắt buộc SSL, localhost dev thì không cần
	}
	return fmt.Sprintf(
		"postgres://%s:%s@%s:%s/%s?sslmode=%s",
		os.Getenv("DB_USER"),
		os.Getenv("DB_PASSWORD"),
		os.Getenv("DB_HOST"),
		os.Getenv("DB_PORT"),
		os.Getenv("DB_NAME"),
		sslMode,
	)
}

func getPool(ctx context.Context) (*pgxpool.Pool, error) {
	pgOnce.Do(func() {
		cfg, err := pgxpool.ParseConfig(buildDatabaseURL())
		if err != nil {
			pgErr = fmt.Errorf("parse database url: %w", err)
			return
		}
		cfg.MaxConns = 5 // Supabase pooler giới hạn connection, đừng để Go tự mở tràn lan
		pgPool, pgErr = pgxpool.NewWithConfig(ctx, cfg)
	})
	return pgPool, pgErr
}
