variable "name_prefix" {
  description = "Name prefix for NAT resources"
  type        = string
}

variable "public_subnet_ids" {
  description = "Public subnet IDs for NAT placement"
  type        = list(string)

  validation {
    condition     = length(var.public_subnet_ids) >= 1
    error_message = "At least one public subnet ID is required for NAT deployment."
  }
}

variable "nat_gateway_mode" {
  description = "NAT strategy: per_az or single"
  type        = string
  default     = "per_az"

  validation {
    condition     = contains(["per_az", "single"], var.nat_gateway_mode)
    error_message = "nat_gateway_mode must be one of: per_az, single."
  }
}

variable "tags" {
  description = "Resource tags"
  type        = map(string)
  default     = {}
}