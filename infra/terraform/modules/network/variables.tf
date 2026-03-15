variable "environment" {
  description = "Environment identifier"
  type        = string
}

variable "vpc_id" {
  description = "VPC ID where the firewall routes are applied"
  type        = string
}

variable "subnet_ids" {
  description = "List of public subnet IDs for firewall endpoints"
  type        = list(string)
}

variable "kms_key_arn" {
  description = "KMS CMK ARN used for Network Firewall and log encryption"
  type        = string
}

variable "log_retention_days" {
  description = "Retention period for security log groups"
  type        = number
  default     = 365
}
