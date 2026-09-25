package main

import (
	"context"
	"errors"
	"fmt"
	"log"
	"net/url"
	"os"
	"sync"

	"github.com/aws/aws-sdk-go-v2/aws"
	config "github.com/aws/aws-sdk-go-v2/config"
	"github.com/aws/aws-sdk-go-v2/credentials"
	"github.com/jackc/pgx/v5/pgxpool"
	"github.com/spf13/viper"
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
	viper.SetConfigFile(".env")
	viper.SetConfigType("env")

	if err := viper.ReadInConfig(); err != nil {
		var notFound viper.ConfigFileNotFoundError
		if !errors.As(err, &notFound) {
			return nil, fmt.Errorf("read .env: %w", err)
		}
		wd, _ := os.Getwd()
		log.Printf("no .env found in %s, reading from real environment variables", wd)
	}

	viper.AutomaticEnv()

	e := &Env{
		AWSAccessKeyID:     viper.GetString("AWS_ACCESS_KEY_ID"),
		AWSSecretAccessKey: viper.GetString("AWS_SECRET_ACCESS_KEY"),
		AWSRegion:          viper.GetString("AWS_REGION"),
		SQSQueueURL:        viper.GetString("SQS_QUEUE_URL"),
		S3Bucket:           viper.GetString("S3_BUCKET"),
		DBHost:             viper.GetString("DB_HOST"),
		DBPort:             viper.GetString("DB_PORT"),
		DBUser:             viper.GetString("DB_USER"),
		DBPassword:         viper.GetString("DB_PASSWORD"),
		DBName:             viper.GetString("DB_NAME"),
	}

	if err := validateEnv(e); err != nil {
		return nil, err
	}
	return e, nil
}

func validateEnv(e *Env) error {
	required := map[string]string{
		"SQS_QUEUE_URL": e.SQSQueueURL,
		"DB_HOST":       e.DBHost,
		"DB_PORT":       e.DBPort,
		"DB_USER":       e.DBUser,
		"DB_NAME":       e.DBName,
	}
	var missing []string
	for k, v := range required {
		if v == "" {
			missing = append(missing, k)
		}
	}
	if len(missing) > 0 {
		return fmt.Errorf("missing required env vars: %v", missing)
	}
	return nil
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

	connString := fmt.Sprintf(
		"postgres://%s:%s@%s:%s/%s?sslmode=disable",
		url.QueryEscape(env.DBUser),
		url.QueryEscape(env.DBPassword),
		env.DBHost,
		env.DBPort,
		env.DBName,
	)

	pgOnce.Do(func() {
		pgPool, pgErr = pgxpool.New(ctx, connString)
		if pgErr != nil {
			pgErr = fmt.Errorf("parse database url: %w", pgErr)
			return
		}
	})

	return pgPool, pgErr
}
