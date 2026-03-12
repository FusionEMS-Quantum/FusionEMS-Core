variable "environment" {
  description = "Deployment environment (dev / staging / prod)"
  type        = string
}

variable "project" {
  description = "Project name used in resource naming"
  type        = string
}

variable "aws_region" {
  description = "AWS region for the KMS key and lifecycle configs"
  type        = string
  default     = "us-east-1"
}

variable "ecs_task_role_arn" {
  description = "ARN of the ECS task IAM role that needs access to the vault buckets"
  type        = string
}

variable "tags" {
  description = "Common tags applied to all resources"
  type        = map(string)
  default     = {}
}
