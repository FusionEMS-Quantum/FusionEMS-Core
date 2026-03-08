variable "name_prefix" {
  description = "Name prefix for route table resources"
  type        = string
}

variable "vpc_id" {
  description = "VPC ID"
  type        = string
}

variable "internet_gateway_id" {
  description = "Internet gateway ID for public routes"
  type        = string
}

variable "availability_zones" {
  description = "Availability zones used for subnet-to-route associations"
  type        = list(string)
}

variable "public_subnet_ids" {
  description = "Public subnet IDs ordered by AZ"
  type        = list(string)
}

variable "private_app_subnet_ids" {
  description = "Private app subnet IDs ordered by AZ"
  type        = list(string)
}

variable "private_data_subnet_ids" {
  description = "Private data subnet IDs ordered by AZ"
  type        = list(string)
}

variable "nat_gateway_ids" {
  description = "NAT gateway IDs (per-AZ or single)"
  type        = list(string)

  validation {
    condition     = length(var.nat_gateway_ids) >= 1
    error_message = "At least one NAT gateway ID is required for private route egress."
  }
}

variable "data_subnet_internet_egress_enabled" {
  description = "Enable NAT egress routes for private data subnets"
  type        = bool
  default     = true
}

variable "tags" {
  description = "Resource tags"
  type        = map(string)
  default     = {}
}