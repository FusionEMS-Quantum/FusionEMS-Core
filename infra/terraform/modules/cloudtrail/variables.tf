variable "environment" {
  type = string
}

variable "project" {
  type = string
}

variable "alert_topic_arn" {
  type        = string
  description = "SNS topic ARN for alarm notifications"
}

variable "audit_bucket_arn" {
  type        = string
  default     = ""
  description = "S3 audit bucket ARN for data event logging"
}

variable "tags" {
  type    = map(string)
  default = {}
}

variable "create_kms_alias" {
  type        = bool
  default     = true
  description = "When false, do not create the module-managed KMS alias (useful to avoid alias collisions / reuse an existing alias)."
}

variable "kms_alias_name" {
  type        = string
  default     = ""
  description = "Optional explicit KMS alias name to create. If empty the module uses 'alias/project-env-cloudtrail'."
}
