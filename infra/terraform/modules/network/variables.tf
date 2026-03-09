variable "environment" {
  description = "Environment identifier"
  type        = string
}

variable "vpc_id" {
  description = "VPC ID where the firewall routes are applied"
  type        = string
}

variable "subnet_ids" {
  description = "List of public subnet IDs for firewall endpoints"
  type        = list(string)
}
