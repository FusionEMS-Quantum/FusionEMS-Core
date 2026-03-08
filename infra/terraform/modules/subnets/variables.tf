variable "name_prefix" {
  description = "Name prefix for subnet resources"
  type        = string
}

variable "vpc_id" {
  description = "VPC ID for subnet creation"
  type        = string
}

variable "availability_zones" {
  description = "Availability zones for subnet placement"
  type        = list(string)

  validation {
    condition     = length(var.availability_zones) >= 2
    error_message = "At least 2 availability zones are required for resilience."
  }
}

variable "public_subnet_cidrs" {
  description = "Public subnet CIDRs, one per AZ"
  type        = list(string)
}

variable "private_app_subnet_cidrs" {
  description = "Private application subnet CIDRs, one per AZ"
  type        = list(string)
}

variable "private_data_subnet_cidrs" {
  description = "Private data subnet CIDRs, one per AZ"
  type        = list(string)
}

variable "map_public_ip_on_launch" {
  description = "Whether to map public IP on launch in public subnets"
  type        = bool
  default     = false
}

variable "tags" {
  description = "Resource tags"
  type        = map(string)
  default     = {}
}