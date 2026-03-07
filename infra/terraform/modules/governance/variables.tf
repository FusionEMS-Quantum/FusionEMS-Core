variable "project" {
  description = "Project name used in resource naming"
  type        = string
}

variable "environment" {
  description = "Deployment environment (dev, staging, prod)"
  type        = string
}

variable "tags" {
  description = "Common resource tags"
  type        = map(string)
  default     = {}
}

variable "enable_object_lock" {
  description = "Enable S3 Object Lock (WORM) on audit export bucket. Requires bucket to be created with object lock enabled."
  type        = bool
  default     = false
}

variable "audit_retention_days" {
  description = "Number of days to retain audit exports under Object Lock governance mode"
  type        = number
  default     = 2555 # ~7 years for HIPAA
}

variable "phi_export_expiry_days" {
  description = "Number of days after which staged PHI exports are automatically deleted"
  type        = number
  default     = 30
}

variable "log_retention_days" {
  description = "CloudWatch log retention in days"
  type        = number
  default     = 365
}
