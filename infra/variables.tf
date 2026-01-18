variable "aws_region" {
  description = "AWS region"
  type        = string
  default     = "us-east-1"
}

variable "environment" {
  description = "Environment name"
  type        = string
  default     = "production"
}

variable "project_name" {
  description = "Project name"
  type        = string
  default     = "circle-of-trust"
}

variable "s3_frontend_bucket" {
  description = "S3 bucket for frontend hosting"
  type        = string
  default     = "circle-of-trust-frontend"
}

variable "api_image_tag" {
  description = "Docker image tag for API service"
  type        = string
  default     = "latest"
}

variable "worker_image_tag" {
  description = "Docker image tag for Worker service"
  type        = string
  default     = "latest"
}

variable "api_task_cpu" {
  description = "CPU units for API task (1024 = 1 vCPU)"
  type        = number
  default     = 512
}

variable "api_task_memory" {
  description = "Memory for API task in MB"
  type        = number
  default     = 1024
}

variable "worker_task_cpu" {
  description = "CPU units for Worker task"
  type        = number
  default     = 2048
}

variable "worker_task_memory" {
  description = "Memory for Worker task in MB"
  type        = number
  default     = 4096
}

variable "api_min_capacity" {
  description = "Minimum number of API tasks"
  type        = number
  default     = 2
}

variable "api_max_capacity" {
  description = "Maximum number of API tasks"
  type        = number
  default     = 10
}

variable "worker_min_capacity" {
  description = "Minimum number of Worker tasks"
  type        = number
  default     = 0
}

variable "worker_max_capacity" {
  description = "Maximum number of Worker tasks"
  type        = number
  default     = 20
}

variable "pingid_metadata_url" {
  description = "PingID SAML metadata URL"
  type        = string
  sensitive   = true
}

variable "domain_name" {
  description = "Custom domain name for the application"
  type        = string
  default     = "circleoftrust.example.com"
}

variable "vpc_id" {
  description = "Existing VPC ID to deploy resources into"
  type        = string
}
