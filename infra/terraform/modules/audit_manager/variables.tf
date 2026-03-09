variable "environment" {
  description = "The deployment environment"
  type        = string
}

variable "report_destination_s3_bucket" {
  description = "The S3 bucket for AWS Audit Manager evidence reports"
  type        = string
}
