variable "name_prefix" {
  description = "Name prefix for DNS resources"
  type        = string
}

variable "create_public_zone" {
  description = "Create a public hosted zone"
  type        = bool
  default     = false
}

variable "public_zone_name" {
  description = "Public zone name"
  type        = string
  default     = ""
}

variable "create_private_zone" {
  description = "Create a private hosted zone"
  type        = bool
  default     = false
}

variable "private_zone_name" {
  description = "Private zone name"
  type        = string
  default     = ""
}

variable "vpc_id" {
  description = "VPC ID for private zone association"
  type        = string
  default     = ""
}

variable "tags" {
  description = "Resource tags"
  type        = map(string)
  default     = {}
}