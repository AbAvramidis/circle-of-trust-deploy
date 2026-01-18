# SQS Queue for Jobs
resource "aws_sqs_queue" "jobs" {
  name                       = "${var.project_name}-jobs-queue"
  visibility_timeout_seconds = 900  # 15 minutes
  message_retention_seconds  = 86400 # 24 hours
  receive_wait_time_seconds  = 20   # Long polling
  
  tags = {
    Name = "${var.project_name}-jobs-queue"
  }
}
