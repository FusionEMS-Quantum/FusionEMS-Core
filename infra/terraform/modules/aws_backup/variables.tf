###############################################################################
# FusionEMS – AWS Backup Module – Variables
###############################################################################

variable "environment" {
  description = "Deployment environment (dev, staging, prod, dr)"
  type        = string
}

variable "project" {
  description = "Project name for resource naming and tag-based selection"
  type        = string
}

variable "alert_topic_arn" {
  description = "SNS topic ARN for backup failure notifications"
  type        = string
}

variable "dr_vault_arn" {
  description = "DR region backup vault ARN for cross-region copy (prod only)"
  type        = string
  default     = ""
}

variable "backup_resource_arns" {
  description = "Explicit resource ARNs to back up (empty = tag-based selection only)"
  type        = list(string)
  default     = []
}

variable "tags" {
  description = "Common resource tags"
  type        = map(string)
  default     = {}
}
