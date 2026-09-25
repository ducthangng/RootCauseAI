# RootCause AI

Internal dashboard for Quality Engineers — auto-generates a Root-Cause Analysis (RCA) report from new incident text, using the NHTSA vehicle complaints dataset as the retrieval corpus. RAG pipeline built on LangGraph, positioned as portfolio evidence for trustworthy AI / model validation work.

## Architecture

```mermaid
graph TB
    subgraph Client["Client"]
        FE["React/TypeScript Frontend (Vercel)"]
    end

    subgraph AWS["AWS ap-southeast-1"]
        subgraph S3B["S3: root-cause-ai"]
            RAW["raw/"]
            PROC["processed/"]
        end

        LAMBDA_CLEAN["Lambda (container image)<br/>clean & process raw file"]
        SFN["Step Functions"]
        SM["SageMaker Processing Job<br/>(embedding)"]
        SQS["SQS: rootcause-load-queue"]
        DLQ["SQS DLQ"]

        subgraph VPC["VPC — private subnets"]
            subgraph SG_LAMBDA["SG: lambda-worker-sg"]
                LAMBDA_WORKER["Lambda: rootcause-insert-worker (Go)<br/>VPC-attached, provided.al2023/arm64"]
            end

            S3EP["S3 Gateway VPC Endpoint"]

            subgraph SG_EC2["SG: default (EC2)"]
                EC2["EC2: RAG API host<br/>nginx + Let's Encrypt TLS<br/>Docker: rootcause-api (FastAPI + LangGraph)"]
            end

            subgraph SG_RDS["SG: rds-sg"]
                RDS[("RDS PostgreSQL<br/>rootcause-db + pgvector")]
            end
        end

        ECR["ECR: rootcause-api repo"]
    end

    subgraph CICD["GitHub Actions CI/CD"]
        GH1["build-and-deploy-api.yml<br/>build -> ECR -> SSH deploy EC2"]
        GH2["build-and-deploy-worker.yml<br/>build bootstrap.zip -> update-function-code"]
    end

    FE -- "1. presigned PUT URL" --> RAW
    RAW -- "2. S3 event trigger" --> LAMBDA_CLEAN
    LAMBDA_CLEAN --> SFN
    SFN --> SM
    SM -- "embedded CSV" --> PROC
    PROC -- "3. S3 event -> message" --> SQS
    SQS -- "4. event source mapping" --> LAMBDA_WORKER
    SQS -. "maxReceiveCount exceeded" .-> DLQ
    LAMBDA_WORKER -- "5. GetObject" --> S3EP
    S3EP -.-> PROC
    LAMBDA_WORKER -- "6. INSERT, sslmode=require" --> RDS
    EC2 -- "pgx, sslmode=require" --> RDS
    FE -- "7. HTTPS query<br/>https://eip.nip.io" --> EC2

    GH1 -- "docker push" --> ECR
    GH1 -- "ssh + docker pull/run" --> EC2
    GH2 -- "update-function-code" --> LAMBDA_WORKER
```

## RAG Pipeline

`retrieve_node` → `analysis_node` → `evaluation_node` → (fail & under max_revision → back to `analysis_node`; pass or max_revision hit → `action_node`)

## Tech Stack

- **Orchestration**: LangGraph (StateGraph)
- **Embedding**: nomic-ai/nomic-embed-text-v1.5 (768-dim, HNSW m=24/ef_construction=200)
- **LLM**: gpt-4o-mini
- **Vector store**: Postgres + pgvector (RDS)
- **API**: FastAPI, deployed on EC2 behind nginx (TLS via Let's Encrypt)
- **Async worker**: Go, AWS Lambda (`provided.al2023`, arm64), SQS-triggered
- **Frontend**: React/TypeScript on Vercel
- **IaC**: manual for now, Terraform planned

## AWS

- **Region**: `ap-southeast-1`
- **S3**: `root-cause-ai` (`raw/` → cleaned by Lambda, `processed/` → embedded CSV output)
- **SQS**: `rootcause-load-queue` (event source mapping, `ReportBatchItemFailures` enabled)
- **RDS**: `rootcause-db` — PostgreSQL + pgvector, private subnet, `sslmode=require`
- **Lambda**: `rootcause-insert-worker` — Go, `provided.al2023`/arm64, VPC-attached
- **EC2**: RAG API host — Elastic IP + `<eip>.nip.io` domain for Let's Encrypt TLS
- **ECR**: `rootcause-api` repo
- **VPC**: S3 Gateway Endpoint attached to Lambda's route table (no NAT Gateway — keeps free tier)
- **Security Groups**: `lambda-worker-sg`, RDS SG, EC2 `default` SG — cross-referenced by SG id, not CIDR
- **IAM (Lambda execution role)**: `AWSLambdaVPCAccessExecutionRole`, `AWSLambdaSQSQueueExecutionRole`, inline `s3:GetObject` on `root-cause-ai/*`

All resources above are still hand-configured via Console, not Terraform — see [Known gaps](#known-gaps).

## Status

Demo/portfolio deployment, torn down between sessions. Not production-hardened (see [Known gaps](#known-gaps)).

## Known gaps

- [ ] Infra not yet in Terraform — see architecture diagram for full resource list
- [ ] Input/output guardrails (prompt injection via free-text `cdescr` field)
- [ ] SQS DLQ not yet configured
- [ ] No LangSmith/Arize Phoenix tracing yet

## Local development

```bash
cp .env.example .env   # fill in AWS + DB credentials
go test -run TestHandler -v ./...
```
