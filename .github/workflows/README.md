# GitHub Actions CI/CD Workflows

## 📋 Table of Contents

1. [Overview](#overview)
2. [Workflow Files](#workflow-files)
   - [Terraform Apply](#1-terraform-applyyml)
   - [Deploy Frontend](#2-deploy-frontendyml)
   - [Deploy Backend API](#3-deploy-backend-apiyml)
   - [Deploy Backend Worker](#4-deploy-backend-workeryml)
   - [Update ECS Services](#5-update-ecsyml)
3. [Architecture Flow](#architecture-flow)
4. [Setup Instructions](#setup-instructions)
5. [Deployment Scenarios](#deployment-scenarios)
6. [Troubleshooting](#troubleshooting)
7. [Security Best Practices](#security-best-practices)

---

## Overview

This directory contains **5 GitHub Actions workflows** for automated deployment of the Circle of Trust application to AWS. The workflows use **OIDC authentication** (no long-lived credentials) and follow CI/CD best practices.

### Architecture Components

| Component | Technology | Deployment | Cost |
|-----------|-----------|------------|------|
| **Frontend** | React (Vite) | S3 Static Website | ~$0.50/month |
| **API** | Python FastAPI | ECS Fargate (On-Demand) | ~$30/month |
| **Worker** | Python Agent | ECS Fargate Spot | ~$10/month (70% cheaper) |
| **Queue** | SQS | Managed Service | ~$0.40/month |
| **Database** | DynamoDB | On-Demand | ~$2/month |
| **LLM** | Bedrock (planned) | Pay-per-use | Variable |

---

## Workflow Files

### 1. `terraform-apply.yml`

**Purpose:** Deploy and manage AWS infrastructure using Terraform (Infrastructure as Code)

**Triggers:**
- Push to `main` when `infra/**` files change
- Manual dispatch via GitHub Actions UI

**What it deploys:**
```
Infrastructure Components:
├── VPC & Networking (subnets, security groups, NAT gateway)
├── ECS Clusters (API cluster, Worker cluster)
├── ECR Repositories (API images, Worker images)
├── S3 Bucket (frontend static hosting)
├── DynamoDB Tables (jobs, conversations)
├── SQS Queue (job queue with DLQ)
├── IAM Roles (ECS execution, task roles)
├── CloudWatch Log Groups (API logs, Worker logs)
└── Auto-scaling Policies (CPU-based for API, SQS-based for Workers)
```

---

### 2. `deploy-frontend.yml`

**Purpose:** Build React frontend and deploy to S3 static website hosting

**Triggers:**
- Push to `main` when `frontend/**` files change
- Manual dispatch via GitHub Actions UI

**Step-by-step process:**
1. **Checkout code** - Clone repository
2. **Setup Node.js** - Install Node.js 20 with npm cache
3. **Install dependencies** - Run `npm ci` (clean install from lock file)
4. **Build frontend** - Run Vite build (`npm run build`)
   - Output: `frontend/dist/` folder
   - Contains: Minified JS/CSS, hashed asset names, index.html
   - Environment: Inject `VITE_API_URL` and `VITE_WS_URL` at build time
5. **Configure AWS** - Authenticate via OIDC
6. **Deploy to S3** - Upload files with optimized caching
   - **Assets (JS/CSS/images):** Cache for 1 year (immutable, hashed names)
   - **index.html:** No caching (ensures users get latest version)
   - **Delete old files:** Remove files not in new build
   - **Skip source maps:** Don't upload `.map` files to production
7. **Summary** - Display S3 URL

---

### 3. `deploy-backend-api.yml`

**Purpose:** Build API Docker image and push to ECR (automatically triggers ECS deployment)

**Triggers:**
- Push to `main` when `backend/**` or `Dockerfile.api` changes
- Manual dispatch via GitHub Actions UI
- **Note:** Does NOT trigger on test file changes (`!backend/tests/**`)

**Step-by-step process:**
1. **Checkout code** - Clone repository
2. **Configure AWS** - Authenticate via OIDC
3. **Login to ECR** - Get Docker credentials for ECR
4. **Set image tag** - Use git commit SHA as tag (enables rollback)
   - Example: `123456789012.dkr.ecr.us-east-1.amazonaws.com/circle-of-trust-api:abc123def`
5. **Build Docker image** - Build from `Dockerfile.api`
   - Base image: Python 3.11
   - Install dependencies from `pyproject.toml`
   - Copy backend code
   - Expose port 8000
   - Command: Run FastAPI with Uvicorn
6. **Security scan** - Run Trivy vulnerability scanner
   - Scans for critical/high vulnerabilities
   - Reports to GitHub Security tab
   - **Note:** Doesn't block deployment (informational only)
7. **Push to ECR** - Upload image with two tags:
   - `{git-sha}` - Specific version (for rollback)
   - `latest` - Always points to most recent
8. **Deployment summary** - Show image details in GitHub UI
9. **Trigger ECS update** - Automatically call `update-ecs.yml` workflow
   - Passes input: `service: api`
   - ECS will pull new image and deploy
10. **Verify deployment** - Display final status

**Docker Image Contents:**
```dockerfile
FROM python:3.11-slim
WORKDIR /app
COPY pyproject.toml .
RUN pip install .
COPY backend/ ./backend/
EXPOSE 8000
CMD ["uvicorn", "backend.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

---

### 4. `deploy-backend-worker.yml`

**Purpose:** Build Worker Docker image and push to ECR (automatically triggers ECS deployment)

**Triggers:**
- Push to `main` when `backend/**` or `Dockerfile.worker` changes
- Manual dispatch via GitHub Actions UI
- **Note:** Does NOT trigger on test file changes (`!backend/tests/**`)

**Step-by-step process:**
1. **Checkout code** - Clone repository
2. **Configure AWS** - Authenticate via OIDC
3. **Login to ECR** - Get Docker credentials for ECR
4. **Set image tag** - Use git commit SHA as tag
5. **Build Docker image** - Build from `Dockerfile.worker`
   - Base image: Python 3.11
   - Install dependencies from `pyproject.toml`
   - Copy backend code
   - Command: Run worker script (polls SQS)
6. **Security scan** - Run Trivy vulnerability scanner
7. **Push to ECR** - Upload image with SHA and `latest` tags
8. **Deployment summary** - Show image details
9. **Trigger ECS update** - Automatically call `update-ecs.yml` workflow
   - Passes input: `service: worker`
   - ECS will pull new image and deploy
10. **Verify deployment** - Display final status

**Why Fargate Spot?**
- **70% cheaper** than regular Fargate
- Workers can be interrupted (that's OK!)
- Jobs remain in SQS until processed
- ECS auto-restarts interrupted tasks
- Perfect for background processing

---

### 5. `update-ecs.yml`

**Purpose:** Force new deployment of ECS services to pull latest Docker images from ECR

**This is the KEY workflow** that actually deploys new code to running ECS services!

**Triggers:**
- **Automatically called** by `deploy-backend-api.yml` and `deploy-backend-worker.yml`
- **Manual dispatch** for rollback or redeployment

**Manual Trigger Options:**
- `api` - Update only API service
- `worker` - Update only Worker service
- `all` - Update both services in parallel

**How it works:**

#### Job 1: Update API Service
1. **Authenticate with AWS** - OIDC credentials
2. **Force new deployment** - Run `aws ecs update-service --force-new-deployment`
   - ECS pulls latest image with `:latest` tag from ECR
   - Starts new tasks with new image
   - Performs **rolling update** (blue-green deployment):
     - Start new tasks
     - Wait for health checks to pass
     - Drain connections from old tasks
     - Stop old tasks
   - **Circuit breaker enabled:** Auto-rollback if health checks fail
3. **Wait for stability** - Run `aws ecs wait services-stable`
   - Waits up to 10 minutes
   - Checks: All tasks healthy, old tasks stopped, desired count reached
   - Fails if service doesn't stabilize

#### Job 2: Update Worker Service
1. **Authenticate with AWS** - OIDC credentials
2. **Force new deployment** - Run `aws ecs update-service --force-new-deployment`
   - ECS pulls latest image from ECR
   - Starts new tasks on **Fargate Spot** (70% cheaper)
   - Performs rolling update
   - **No health checks** (workers don't expose HTTP endpoint)
3. **Wait for stability** - Wait for tasks to start and old tasks to stop

**Why separate from Terraform?**
- **Terraform manages infrastructure** (clusters, task definitions, initial setup)
- **CI/CD manages deployments** (updating running services with new images)
- Allows frequent deployments without running `terraform apply`
- Faster (2-3 min vs 5-10 min for Terraform)

**Deployment Strategy:**

**Deployment Strategy:**
```yaml
# ECS Rolling Update Configuration
deployment_configuration:
  maximum_percent: 200          # Can run 2x desired count during deployment
  minimum_healthy_percent: 100  # Always keep 100% capacity (zero downtime)

# Example: Desired count = 2 tasks
# During deployment:
# 1. Start 2 new tasks (total: 4 running) ← 200% max
# 2. Wait for health checks
# 3. Stop 2 old tasks (total: 2 running) ← 100% min
# Result: Zero downtime!
```
---

## Architecture Flow

### Complete Deployment Pipeline

```
┌─────────────────────────────────────────────────────────────────────┐
│                        CODE CHANGES                                 │
└─────────────────────────────────────────────────────────────────────┘
                               │
                    ┌──────────┼──────────┐
                    ↓          ↓          ↓
              ┌──────────┐ ┌──────────┐ ┌──────────┐
              │ Infra/** │ │Frontend│ │Backend  │
              │  Changes │ │ Changes│ │ Changes │
              └──────────┘ └──────────┘ └──────────┘
                    │          │          │
                    ↓          ↓          ↓
         ┌───────────────┐ ┌────────┐ ┌─────────┬─────────┐
         │  Terraform    │ │ Build  │ │ Build   │ Build   │
         │  Apply        │ │ Vite   │ │API Image│Worker  │
         │               │ │        │ │         │Image    │
         └───────────────┘ └────────┘ └─────────┴─────────┘
                    │          │          │         │
                    │          │          ↓         ↓
         ┌──────────▼──────────┼────► Push to ECR  │
         │  Creates/Updates:   │          │         │
         │  - VPC, Subnets     │          │         │
         │  - ECS Clusters     │          │         │
         │  - ECR Repos        │          │         │
         │  - S3 Bucket        ◄──────────┼─────────┤
         │  - DynamoDB         │          │         │
         │  - SQS, IAM, etc.   │          │         │
         └─────────────────────┘          │         │
                                           │         │
                                           ↓         ↓
                              ┌────────────────────────────┐
                              │   Trigger update-ecs.yml   │
                              │   (Automatic)              │
                              └────────────┬───────────────┘
                                           │
                              ┌────────────▼───────────┐
                              │ Force ECS Deployment   │
                              │ - Pull latest image    │
                              │ - Rolling update       │
                              │ - Health checks        │
                              │ - Auto rollback        │
                              └────────────┬───────────┘
                                           │
                              ┌────────────▼───────────┐
                              │  Service Running       │
                              │  ✅ Zero Downtime       │
                              └────────────────────────┘
```

### File Change → Triggered Workflow Matrix

| File Changed | Triggered Workflow(s) | What Gets Deployed |
|-------------|----------------------|-------------------|
| `infra/**` | `terraform-apply.yml` | Infrastructure changes |
| `frontend/**` | `deploy-frontend.yml` | React app to S3 |
| `backend/**` + `Dockerfile.api` | `deploy-backend-api.yml` → `update-ecs.yml` | API service |
| `backend/**` + `Dockerfile.worker` | `deploy-backend-worker.yml` → `update-ecs.yml` | Worker service |
| `backend/**` (no Dockerfile change) | Both API and Worker workflows | Both services |

---

### Current Estimated Costs

| Service | Usage | Monthly Cost |
|---------|-------|--------------|
| **ECS Fargate (API)** | 2 tasks × 0.25 vCPU × 0.5GB | ~$30 |
| **ECS Fargate Spot (Worker)** | 2 tasks × 0.25 vCPU × 0.5GB | ~$10 (70% discount) |
| **S3 (Frontend)** | 1GB storage, 10k requests | ~$0.50 |
| **DynamoDB** | On-demand, 10k reads, 5k writes | ~$2 |
| **SQS** | 100k requests | ~$0.40 |
| **ECR** | 2GB images | ~$0.20 |
| **CloudWatch Logs** | 5GB ingestion, 7 days retention | ~$5 |
| **GitHub Actions** | 2000 free minutes/month | $0 |
| **Data Transfer** | Within region | $0 |
| **TOTAL** | | **~$50/month** |
