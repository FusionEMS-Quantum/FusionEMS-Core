variable "enabled" {
  description = "Enable ALB creation"
  type        = bool
  default     = false
}

variable "name_prefix" {
  description = "Name prefix for ALB resources"
  type        = string
}

variable "internal" {
  description = "Create internal ALB when true"
  type        = bool
  default     = false
}

variable "alb_security_group_id" {
  description = "ALB security group ID"
  type        = string
}

variable "public_subnet_ids" {
  description = "Subnet IDs used by ALB"
  type        = list(string)
}

variable "acm_certificate_arn" {
  description = "ACM certificate ARN"
  type        = string
  default     = ""
}

variable "enable_http_listener" {
  description = "Enable an HTTP listener on port 80"
  type        = bool
  default     = true
}

variable "enable_deletion_protection" {
  description = "Enable ALB deletion protection"
  type        = bool
  default     = false
}

variable "tags" {
  description = "Resource tags"
  type        = map(string)
  default     = {}
}