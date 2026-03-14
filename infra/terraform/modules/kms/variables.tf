variable "environment" {
  description = "The deployment environment"
  type        = string
}

variable "alias_name" {
  description = "The alias for the KMS key"
  type        = string
}

variable "description" {
  description = "Description of the KMS key"
  type        = string
  default     = "FusionEMS Customer Managed Key for strict compliance"
}
