output "s3_frontend_bucket" {
  description = "S3 bucket for frontend"
  value       = aws_s3_bucket.frontend.bucket
}

output "s3_website_endpoint" {
  description = "S3 website endpoint"
  value       = aws_s3_bucket_website_configuration.frontend.website_endpoint
}

output "api_gateway_url" {
  description = "API Gateway URL"
  value       = aws_apigatewayv2_api.main.api_endpoint
}

output "api_gateway_id" {
  description = "API Gateway ID"
  value       = aws_apigatewayv2_api.main.id
}

output "ecr_api_repository_url" {
  description = "ECR repository URL for API"
  value       = aws_ecr_repository.api.repository_url
}

output "ecr_worker_repository_url" {
  description = "ECR repository URL for Worker"
  value       = aws_ecr_repository.worker.repository_url
}

output "sqs_queue_url" {
  description = "SQS queue URL"
  value       = aws_sqs_queue.jobs.url
}

output "dynamodb_tables" {
  description = "DynamoDB table names"
  value = {
    conversations = aws_dynamodb_table.conversations.name
    jobs          = aws_dynamodb_table.jobs.name
  }
}

output "ecs_api_cluster" {
  description = "ECS API cluster name"
  value       = aws_ecs_cluster.api.name
}

output "ecs_worker_cluster" {
  description = "ECS Worker cluster name"
  value       = aws_ecs_cluster.workers.name
}

output "ecs_api_service" {
  description = "ECS API service name"
  value       = aws_ecs_service.api.name
}

output "ecs_worker_service" {
  description = "ECS Worker service name"
  value       = aws_ecs_service.worker.name
}

output "vpc_id" {
  description = "VPC ID"
  value       = data.aws_vpc.main.id
}

output "private_subnet_ids" {
  description = "Private subnet IDs"
  value       = data.aws_subnets.private.ids
}

output "public_subnet_ids" {
  description = "Public subnet IDs"
  value       = data.aws_subnets.public.ids
}

output "github_actions_role_arn" {
  description = "IAM role ARN for GitHub Actions OIDC"
  value       = aws_iam_role.github_actions.arn
}
