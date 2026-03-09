variable "environment" {
  description = "The environment for the deployment (e.g. prod, staging)"
  type        = string
}

variable "enable_macie" {
  description = "Whether to enable Amazon Macie to discover PII"
  type        = bool
  default     = true
}

variable "enable_inspector" {
  description = "Whether to enable Amazon Inspector for vulnerability management"
  type        = bool
  default     = true
}
