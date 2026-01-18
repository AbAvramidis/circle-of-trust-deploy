# Terraform Infrastructure for Circle of Trust

Complete infrastructure as code for AWS deployment.

## Architecture Components

- **VPC**: Custom VPC with public/private subnets across 2 AZs
- **ECS**: Fargate clusters for API (on-demand) and Workers (Spot)
- **ECR**: Container registries for API and Worker images
- **API Gateway**: HTTP API with VPC Link integration
- **Service Discovery**: AWS Cloud Map for internal service resolution
- **SQS**: Job queue with DLQ for failed messages
- **DynamoDB**: Conversations and Jobs tables with auto-scaling
- **S3**: Static website hosting for React frontend
- **IAM**: Least-privilege roles for ECS tasks and GitHub Actions
- **CloudWatch**: Logs and monitoring
- **Auto-scaling**: CPU-based for API, SQS queue-depth for Workers

---

## Prerequisites

1. **AWS CLI** configured with credentials
2. **Terraform** >= 1.6
3. **S3 Bucket** for Terraform state (create manually first)
4. **DynamoDB Table** for state locking (create manually first)

### Create Backend Resources

```bash
# S3 bucket for Terraform state
aws s3api create-bucket \
  --bucket circle-of-trust-terraform-state \
  --region us-east-1

aws s3api put-bucket-versioning \
  --bucket circle-of-trust-terraform-state \
  --versioning-configuration Status=Enabled

aws s3api put-bucket-encryption \
  --bucket circle-of-trust-terraform-state \
  --server-side-encryption-configuration '{
    "Rules": [{
      "ApplyServerSideEncryptionByDefault": {
        "SSEAlgorithm": "AES256"
      }
    }]
  }'

# DynamoDB table for state locking
aws dynamodb create-table \
  --table-name terraform-state-lock \
  --attribute-definitions AttributeName=LockID,AttributeType=S \
  --key-schema AttributeName=LockID,KeyType=HASH \
  --billing-mode PAY_PER_REQUEST \
  --region us-east-1
```

### Create GitHub OIDC Provider (one-time setup)

```bash
aws iam create-open-id-connect-provider \
  --url https://token.actions.githubusercontent.com \
  --client-id-list sts.amazonaws.com \
  --thumbprint-list 6938fd4d98bab03faadb97b34396831e3780aea1
```

---

## Deployment

### 1. Initialize Terraform

```bash
cd infra
terraform init
```

### 2. Create terraform.tfvars

```hcl
aws_region       = "us-east-1"
environment      = "production"
project_name     = "circle-of-trust"
s3_frontend_bucket = "circle-of-trust-frontend"

# PingID SSO configuration
pingid_metadata_url = "https://sso.pingone.com/your-org-id/saml/metadata"

# Domain configuration
domain_name = "circleoftrust.yourdomain.com"

# Enable NAT Gateway (adds $32/month, required if no VPC endpoints)
enable_nat_gateway = false

# ECS Configuration
api_task_cpu    = 512
api_task_memory = 1024
api_min_capacity = 2
api_max_capacity = 10

worker_task_cpu    = 2048
worker_task_memory = 4096
worker_min_capacity = 0
worker_max_capacity = 20

# Image tags (managed by CI/CD)
api_image_tag    = "latest"
worker_image_tag = "latest"
```

### 3. Plan and Apply

```bash
# Review changes
terraform plan

# Apply infrastructure
terraform apply

# Save outputs
terraform output > ../terraform-outputs.txt
```

### 4. Configure GitHub Secrets

Add these outputs as GitHub Secrets:

```bash
# Get values from Terraform outputs
terraform output -json > outputs.json

# Add to GitHub:
# AWS_ROLE_TO_ASSUME = github_actions_role_arn
# VITE_API_URL = api_gateway_url
# VITE_WS_URL = websocket_gateway_url
```

---

## CI/CD Integration

### How Image Updates Work

**Problem**: Terraform manages ECS task definitions, but CI/CD pushes new images with SHA tags. How to update ECS without Terraform state drift?

**Solution**: Terraform manages base infrastructure, GitHub Actions triggers **force new deployment**

### Task Definition Management Strategy

1. **Terraform creates initial task definition** with `latest` tag
2. **Terraform ignores image tag changes** via `lifecycle.ignore_changes`
3. **GitHub Actions pushes new image** to ECR with SHA tag (e.g., `abc123`)
4. **GitHub Actions updates ECS service** using AWS CLI: `aws ecs update-service --force-new-deployment`
5. **ECS automatically uses newest image** from ECR with same tag pattern

### Updated GitHub Actions Workflow

See `.github/workflows/deploy-backend-api.yml`:

```yaml
- name: Force ECS deployment with new image
  run: |
    aws ecs update-service \
      --cluster ${{ env.ECS_CLUSTER }} \
      --service ${{ env.ECS_SERVICE }} \
      --force-new-deployment \
      --no-cli-pager
```

**Benefits:**
- ✅ No Terraform state drift
- ✅ Terraform maintains infrastructure
- ✅ CI/CD handles rapid image deployments
- ✅ Automatic rollback on deployment failure (circuit breaker)
- ✅ No manual intervention needed

---

## Alternative: EventBridge-Based Deployment (Optional)

For fully automated deployments, add EventBridge rule to trigger ECS update on new ECR images:

```hcl
# infra/eventbridge.tf
resource "aws_cloudwatch_event_rule" "ecr_push" {
  name        = "${var.project_name}-ecr-push"
  description = "Trigger on ECR image push"
  
  event_pattern = jsonencode({
    source      = ["aws.ecr"]
    detail-type = ["ECR Image Action"]
    detail = {
      action-type = ["PUSH"]
      result      = ["SUCCESS"]
      repository-name = [
        aws_ecr_repository.api.name,
        aws_ecr_repository.worker.name
      ]
    }
  })
}

resource "aws_cloudwatch_event_target" "lambda_updater" {
  rule      = aws_cloudwatch_event_rule.ecr_push.name
  target_id = "UpdateECS"
  arn       = aws_lambda_function.ecs_updater.arn
}

# Lambda function to update ECS service
resource "aws_lambda_function" "ecs_updater" {
  filename      = "lambda_ecs_updater.zip"
  function_name = "${var.project_name}-ecs-updater"
  role          = aws_iam_role.lambda_ecs_updater.arn
  handler       = "index.handler"
  runtime       = "python3.11"
  
  environment {
    variables = {
      API_CLUSTER     = aws_ecs_cluster.api.name
      API_SERVICE     = aws_ecs_service.api.name
      WORKER_CLUSTER  = aws_ecs_cluster.workers.name
      WORKER_SERVICE  = aws_ecs_service.worker.name
    }
  }
}
```

**Lambda Handler** (`lambda_ecs_updater/index.py`):
```python
import boto3
import os

ecs = boto3.client('ecs')

def handler(event, context):
    repo_name = event['detail']['repository-name']
    
    # Determine which service to update
    if 'api' in repo_name:
        cluster = os.environ['API_CLUSTER']
        service = os.environ['API_SERVICE']
    elif 'worker' in repo_name:
        cluster = os.environ['WORKER_CLUSTER']
        service = os.environ['WORKER_SERVICE']
    else:
        return {'statusCode': 200, 'body': 'Unknown repository'}
    
    # Trigger rolling update
    response = ecs.update_service(
        cluster=cluster,
        service=service,
        forceNewDeployment=True
    )
    
    return {'statusCode': 200, 'body': f'Triggered deployment for {service}'}
```

**Trade-offs:**
- ✅ Fully automated (no GitHub Actions step needed)
- ❌ More complex (Lambda + EventBridge + IAM)
- ❌ Less control over deployment timing
- ❌ Harder to add gates/approvals

**Recommendation:** Stick with GitHub Actions approach for simplicity and control.

---

## Cost Optimization

### NAT Gateway vs VPC Endpoints

**With NAT Gateway** (default: disabled):
- Cost: **$32/month** per NAT Gateway ($0.045/hour)
- Internet access from private subnets
- Required for pulling public Docker images

**With VPC Endpoints** (default: enabled):
- Cost: **$7-10/month** ($0.01/hour per endpoint × 3 endpoints)
- Private connectivity to AWS services (S3, ECR, CloudWatch)
- Cannot access internet
- ECS images must be in ECR (not Docker Hub)

**Change via:**
```hcl
variable "enable_nat_gateway" {
  default = false  # Use VPC endpoints (cheaper)
}
```

---

## Monitoring

### Key Metrics

```bash
# ECS Service Status
aws ecs describe-services \
  --cluster circle-of-trust-api \
  --services api-service \
  --query 'services[0].[serviceName,status,runningCount,desiredCount]'

# SQS Queue Depth
aws sqs get-queue-attributes \
  --queue-url $(terraform output -raw sqs_queue_url) \
  --attribute-names ApproximateNumberOfMessagesVisible

# DynamoDB Metrics
aws cloudwatch get-metric-statistics \
  --namespace AWS/DynamoDB \
  --metric-name ConsumedReadCapacityUnits \
  --dimensions Name=TableName,Value=circle-of-trust-jobs \
  --start-time $(date -u -d '1 hour ago' +%Y-%m-%dT%H:%M:%S) \
  --end-time $(date -u +%Y-%m-%dT%H:%M:%S) \
  --period 300 \
  --statistics Sum
```

---

## Disaster Recovery

### Backup Strategy

- **DynamoDB**: Point-in-time recovery enabled (35 days)
- **S3**: Versioning enabled (30-day lifecycle)
- **ECR**: Keep last 10 images per repository

### Restore Procedure

```bash
# Restore DynamoDB from backup
aws dynamodb restore-table-to-point-in-time \
  --source-table-name circle-of-trust-jobs \
  --target-table-name circle-of-trust-jobs-restored \
  --restore-date-time "2026-01-15T10:00:00Z"

# Rollback S3 object
aws s3api list-object-versions \
  --bucket circle-of-trust-frontend \
  --prefix index.html

aws s3api get-object \
  --bucket circle-of-trust-frontend \
  --key index.html \
  --version-id <VERSION_ID> \
  index.html

# Rollback ECS to previous task definition
aws ecs update-service \
  --cluster circle-of-trust-api \
  --service api-service \
  --task-definition circle-of-trust-api:42
```

---

## Troubleshooting

### Issue: Terraform state lock

```bash
# Release lock manually (use with caution)
aws dynamodb delete-item \
  --table-name terraform-state-lock \
  --key '{"LockID":{"S":"circle-of-trust-terraform-state/prod/terraform.tfstate"}}'
```

### Issue: ECS tasks not starting

```bash
# Check task failures
aws ecs describe-tasks \
  --cluster circle-of-trust-api \
  --tasks $(aws ecs list-tasks --cluster circle-of-trust-api --query 'taskArns[0]' --output text) \
  --query 'tasks[0].stopReason'

# Check logs
aws logs tail /ecs/circle-of-trust-api --follow
```

### Issue: API Gateway 5xx errors

```bash
# Check VPC Link status
aws apigatewayv2 get-vpc-link --vpc-link-id <VPC_LINK_ID>

# Check Service Discovery
aws servicediscovery discover-instances \
  --namespace-name circle-of-trust.local \
  --service-name api-service
```

---

## Cleanup

```bash
# Destroy all infrastructure
terraform destroy

# Delete backend resources (manual)
aws s3 rm s3://circle-of-trust-terraform-state --recursive
aws s3api delete-bucket --bucket circle-of-trust-terraform-state
aws dynamodb delete-table --table-name terraform-state-lock
```

---

## Security Best Practices

1. ✅ All resources in private subnets (except S3)
2. ✅ Security groups with least privilege
3. ✅ IAM roles with resource-specific permissions
4. ✅ Secrets stored in AWS Secrets Manager
5. ✅ Encryption at rest (DynamoDB, S3, ECR)
6. ✅ Encryption in transit (TLS 1.3 on API Gateway)
7. ✅ VPC endpoints instead of NAT Gateway
8. ✅ Container image scanning on ECR push
9. ✅ Point-in-time recovery for DynamoDB
10. ✅ CloudTrail enabled for audit logs

---

## Future Enhancements

- [ ] Add Amazon Cognito for PingID integration
- [ ] Implement blue-green deployments
- [ ] Add AWS WAF rules for API Gateway
- [ ] Set up CloudWatch Dashboards
- [ ] Add SNS notifications for alarms
- [ ] Implement multi-region failover
- [ ] Add AWS Backup for automated backups
- [ ] Integrate with AWS Systems Manager Parameter Store
