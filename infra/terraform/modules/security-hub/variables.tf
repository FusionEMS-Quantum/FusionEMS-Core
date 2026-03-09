variable "environment" {
  type        = string
  description = "Deployment environment (dev, staging, prod)"
}

variable "project" {
  type        = string
  description = "Project name used in resource naming"
}

variable "alert_topic_arn" {
  type        = string
  description = "ARN of the SNS topic for Security Hub critical/high findings"
}

variable "manage_sns_policy" {
  type        = bool
  default     = false
  description = "Whether this module manages the SNS topic policy (set false if managed elsewhere)"
}

variable "enable_cis_standard" {
  type        = bool
  default     = true
  description = "Enable CIS AWS Foundations Benchmark v1.4.0"
}

variable "enable_nist_standard" {
  type        = bool
  default     = true
  description = "Enable NIST 800-53 rev5 standard"
}

variable "tags" {
  type        = map(string)
  default     = {}
  description = "Common tags applied to all resources"
}
