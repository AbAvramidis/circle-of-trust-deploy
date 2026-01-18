# GitHub Actions CI/CD Workflows

## Overview

This directory contains GitHub Actions workflows for automated deployment of the Circle of Trust application to AWS.

## Workflows

### 1. `deploy-frontend.yml`
Builds and deploys React frontend to S3 static website hosting.

**Triggers:**
- Push to `main` branch (when `frontend/**` changes)
- Manual workflow dispatch

**Steps:**
1. Checkout code
2. Setup Node.js 20 with npm caching
3. Install dependencies (`npm ci`)
4. Build production bundle (`npm run build`)
5. Deploy to S3 with optimized cache headers
6. (Optional) Invalidate CloudFront cache

**Required Secrets:**
- `AWS_ROLE_TO_ASSUME` - IAM role ARN for OIDC authentication
- `VITE_API_URL` - API Gateway endpoint URL
- `VITE_WS_URL` - WebSocket API Gateway URL

---

### 2. `deploy-backend-api.yml`
Builds and deploys API container to ECS Fargate (on-demand).

**Triggers:**
- Push to `main` branch (when `backend/**` or `Dockerfile.api` changes)
- Manual workflow dispatch

**Steps:**
1. Checkout code
2. Configure AWS credentials (OIDC)
3. Login to Amazon ECR
4. Build Docker image with SHA tag
5. Run security scan (Trivy)
6. Push image to ECR
7. Update ECS task definition
8. Deploy to ECS service
9. Wait for service stability

**Required Secrets:**
- `AWS_ROLE_TO_ASSUME` - IAM role ARN for OIDC authentication

**Environment Variables:**
- `ECR_REPOSITORY`: circle-of-trust-api
- `ECS_CLUSTER`: circle-of-trust-api
- `ECS_SERVICE`: api-service

---

### 3. `deploy-backend-worker.yml`
Builds and deploys Worker container to ECS Fargate Spot.

**Triggers:**
- Push to `main` branch (when `backend/**` or `Dockerfile.worker` changes)
- Manual workflow dispatch

**Steps:**
1. Checkout code
2. Configure AWS credentials (OIDC)
3. Login to Amazon ECR
4. Build Docker image with SHA tag
5. Run security scan (Trivy)
6. Push image to ECR
7. Update ECS task definition
8. Deploy to ECS service
9. Wait for service stability
10. Check SQS queue depth

**Required Secrets:**
- `AWS_ROLE_TO_ASSUME` - IAM role ARN for OIDC authentication

**Environment Variables:**
- `ECR_REPOSITORY`: circle-of-trust-worker
- `ECS_CLUSTER`: circle-of-trust-workers
- `ECS_SERVICE`: worker-service

---

## Setup Instructions

### 1. Configure AWS OIDC Provider (Recommended)

Create an OIDC provider in AWS IAM to allow GitHub Actions to assume an IAM role without long-lived credentials.

```bash
# Create OIDC provider (one-time setup)
aws iam create-open-id-connect-provider \
  --url https://token.actions.githubusercontent.com \
  --client-id-list sts.amazonaws.com \
  --thumbprint-list 6938fd4d98bab03faadb97b34396831e3780aea1
```

### 2. Create IAM Role for GitHub Actions

**Trust Policy:**
```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Principal": {
        "Federated": "arn:aws:iam::123456789012:oidc-provider/token.actions.githubusercontent.com"
      },
      "Action": "sts:AssumeRoleWithWebIdentity",
      "Condition": {
        "StringEquals": {
          "token.actions.githubusercontent.com:aud": "sts.amazonaws.com"
        },
        "StringLike": {
          "token.actions.githubusercontent.com:sub": "repo:AbAvramidis/circle-of-trust-deploy:*"
        }
      }
    }
  ]
}
```

**Permissions Policy:**
```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "s3:PutObject",
        "s3:GetObject",
        "s3:DeleteObject",
        "s3:ListBucket"
      ],
      "Resource": [
        "arn:aws:s3:::circle-of-trust-frontend",
        "arn:aws:s3:::circle-of-trust-frontend/*"
      ]
    },
    {
      "Effect": "Allow",
      "Action": [
        "ecr:GetAuthorizationToken",
        "ecr:BatchCheckLayerAvailability",
        "ecr:GetDownloadUrlForLayer",
        "ecr:BatchGetImage",
        "ecr:PutImage",
        "ecr:InitiateLayerUpload",
        "ecr:UploadLayerPart",
        "ecr:CompleteLayerUpload"
      ],
      "Resource": "*"
    },
    {
      "Effect": "Allow",
      "Action": [
        "ecs:DescribeServices",
        "ecs:DescribeTaskDefinition",
        "ecs:RegisterTaskDefinition",
        "ecs:UpdateService"
      ],
      "Resource": "*"
    },
    {
      "Effect": "Allow",
      "Action": [
        "iam:PassRole"
      ],
      "Resource": [
        "arn:aws:iam::123456789012:role/ecsTaskExecutionRole",
        "arn:aws:iam::123456789012:role/ecsTaskRole"
      ]
    },
    {
      "Effect": "Allow",
      "Action": [
        "sqs:GetQueueUrl",
        "sqs:GetQueueAttributes"
      ],
      "Resource": "arn:aws:sqs:us-east-1:123456789012:council-jobs-queue"
    }
  ]
}
```

### 3. Add GitHub Secrets

Go to: **Repository Settings → Secrets and variables → Actions**

Add the following secrets:

| Secret Name | Description | Example Value |
|-------------|-------------|---------------|
| `AWS_ROLE_TO_ASSUME` | IAM role ARN for OIDC | `arn:aws:iam::123456789012:role/GitHubActionsRole` |
| `VITE_API_URL` | API Gateway URL | `https://abc123.execute-api.us-east-1.amazonaws.com` |
| `VITE_WS_URL` | WebSocket API URL | `wss://def456.execute-api.us-east-1.amazonaws.com` |

### 4. Create ECR Repositories

```bash
# Create ECR repositories
aws ecr create-repository --repository-name circle-of-trust-api
aws ecr create-repository --repository-name circle-of-trust-worker

# Enable image scanning
aws ecr put-image-scanning-configuration \
  --repository-name circle-of-trust-api \
  --image-scanning-configuration scanOnPush=true

aws ecr put-image-scanning-configuration \
  --repository-name circle-of-trust-worker \
  --image-scanning-configuration scanOnPush=true
```

### 5. Test Workflows

```bash
# Trigger frontend deployment
git add frontend/
git commit -m "Update frontend"
git push origin main

# Trigger backend deployments
git add backend/ Dockerfile.api
git commit -m "Update API"
git push origin main

# Or trigger manually via GitHub UI:
# Actions → Select workflow → Run workflow
```

---

## Deployment Flow

```
Developer pushes code
         ↓
GitHub Actions triggered
         ↓
    ┌────┴────────────────┐
    ↓                      ↓                      ↓
Frontend Build        API Build             Worker Build
    ↓                      ↓                      ↓
Deploy to S3         Push to ECR           Push to ECR
                          ↓                      ↓
                    Update ECS API        Update ECS Worker
                          ↓                      ↓
                    Rolling deployment    Rolling deployment
                          ↓                      ↓
                    Service healthy       Service healthy
```

---

## Rollback Strategy

### Manual Rollback (via AWS Console)
1. Go to ECS → Clusters → Select service
2. Update service → Select previous task definition
3. Force new deployment

### Automated Rollback (via GitHub Actions)
```bash
# List recent deployments
aws ecs describe-services \
  --cluster circle-of-trust-api \
  --services api-service

# Rollback to previous task definition
aws ecs update-service \
  --cluster circle-of-trust-api \
  --service api-service \
  --task-definition api-service:42 \
  --force-new-deployment
```

---

## Monitoring Deployments

### Check Deployment Status
```bash
# Frontend (S3)
aws s3 ls s3://circle-of-trust-frontend/ --recursive --human-readable

# API Service
aws ecs describe-services \
  --cluster circle-of-trust-api \
  --services api-service \
  --query 'services[0].deployments'

# Worker Service
aws ecs describe-services \
  --cluster circle-of-trust-workers \
  --services worker-service \
  --query 'services[0].deployments'
```

### View Logs
```bash
# API logs
aws logs tail /ecs/circle-of-trust-api --follow

# Worker logs
aws logs tail /ecs/circle-of-trust-workers --follow
```

---

## Troubleshooting

### Issue: ECS deployment stuck
**Solution:** Check task definition, IAM roles, and security groups
```bash
aws ecs describe-services \
  --cluster circle-of-trust-api \
  --services api-service \
  --query 'services[0].events[0:10]'
```

### Issue: Image push fails
**Solution:** Verify ECR repository exists and credentials are valid
```bash
aws ecr describe-repositories --repository-names circle-of-trust-api
aws ecr get-login-password | docker login --username AWS --password-stdin <account>.dkr.ecr.us-east-1.amazonaws.com
```

### Issue: S3 sync fails
**Solution:** Check bucket policy and IAM permissions
```bash
aws s3api get-bucket-policy --bucket circle-of-trust-frontend
```

---

## Cost Optimization

- **GitHub Actions**: ~2000 free minutes/month (Linux runners)
- **ECR Storage**: $0.10/GB/month
- **Data Transfer**: Free within same region
- **Estimated Cost**: ~$2-5/month for CI/CD pipeline

---

## Security Best Practices

1. ✅ Use OIDC instead of long-lived credentials
2. ✅ Enable ECR image scanning
3. ✅ Run Trivy security scans in pipeline
4. ✅ Use least-privilege IAM roles
5. ✅ Rotate secrets regularly
6. ✅ Enable CloudTrail for audit logs
7. ✅ Use private ECR repositories
8. ✅ Pin GitHub Actions versions (@v4)

---

## Future Enhancements

- [ ] Add automated tests before deployment
- [ ] Implement blue-green deployments
- [ ] Add Slack/Email notifications
- [ ] Cache Docker layers for faster builds
- [ ] Add canary deployments
- [ ] Implement automatic rollback on errors
- [ ] Add deployment approvals for production
