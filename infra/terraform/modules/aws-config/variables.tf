variable "environment" {
  type        = string
  description = "Deployment environment (dev, staging, prod)"
}

variable "project" {
  type        = string
  description = "Project name used in resource naming"
}

variable "record_global_resources" {
  type        = bool
  default     = true
  description = "Whether to record global resources (set true in primary region only)"
}

variable "tags" {
  type        = map(string)
  default     = {}
  description = "Common tags applied to all resources"
}
