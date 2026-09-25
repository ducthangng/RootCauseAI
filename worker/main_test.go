// worker_test.go
package main

import (
	"context"
	"testing"

	"github.com/aws/aws-lambda-go/events"
)

// {"jobId": "manual-test-1", "bucket": "root-cause-ai", "resultKey": "processed/d331bfae-feb9-4dae-bffe-f790a4dd1b8b/processed.csv"}
func TestHandler(t *testing.T) {
	event := events.SQSEvent{
		Records: []events.SQSMessage{
			{MessageId: "manual-test-3", Body: `{"jobId": "manual-test-1", "bucket": "root-cause-ai", "resultKey": "processed/3d04f982-242e-45c7-a6d8-7c948c58c6b5/processed.csv"}`},
		},
	}

	resp, err := handler(context.Background(), event)
	if err != nil {
		t.Fatalf("handler error: %v", err)
	}
	if len(resp.BatchItemFailures) != 0 {
		t.Fatalf("unexpected failures: %+v", resp.BatchItemFailures)
	}
}
