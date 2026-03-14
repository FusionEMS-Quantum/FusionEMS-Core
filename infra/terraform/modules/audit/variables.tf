variable "environment" {
  description = "The deployment environment"
  type        = string
}

variable "multi_region" {
  description = "Whether CloudTrail is enabled for all regions"
  type        = bool
  default     = true
}

variable "s3_bucket_name" {
  description = "The S3 bucket for storing CloudTrail logs"
  type        = string
}

variable "kms_key_arn" {
  description = "KMS key ARN to encrypt CloudTrail logs"
  type        = string
}
