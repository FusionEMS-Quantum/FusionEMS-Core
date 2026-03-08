variable "name_prefix" {
  description = "Name prefix for security groups"
  type        = string
}

variable "vpc_id" {
  description = "VPC ID"
  type        = string
}

variable "vpc_cidr" {
  description = "VPC CIDR"
  type        = string
}

variable "ecs_ingress_ports" {
  description = "Ingress ports allowed from ALB to ECS tasks"
  type        = list(number)
  default     = [3000, 8000]
}

variable "enable_http_ingress" {
  description = "Enable HTTP ingress on ALB security group"
  type        = bool
  default     = true
}

variable "tags" {
  description = "Resource tags"
  type        = map(string)
  default     = {}
}