variable "environment" {
  description = "Deployment environment"
  type        = string

  validation {
    condition     = contains(["dev", "staging", "prod", "dr"], var.environment)
    error_message = "environment must be one of: dev, staging, prod, dr."
  }
}

variable "project" {
  description = "Project name"
  type        = string
  default     = "fusionems"
}

variable "application" {
  description = "Application tag value"
  type        = string
  default     = "FusionEMS-Core"
}

variable "owner" {
  description = "Owner tag value"
  type        = string
  default     = "fusion-platform"
}

variable "cost_center" {
  description = "CostCenter tag value"
  type        = string
  default     = "fusionems"
}

variable "data_classification" {
  description = "DataClassification tag value"
  type        = string
  default     = "confidential"
}

variable "region" {
  description = "AWS region"
  type        = string
}

variable "vpc_cidr" {
  description = "CIDR for VPC"
  type        = string

  validation {
    condition     = can(cidrhost(var.vpc_cidr, 0))
    error_message = "vpc_cidr must be a valid CIDR block."
  }
}

variable "availability_zones" {
  description = "AZs for subnet placement"
  type        = list(string)

  validation {
    condition     = length(var.availability_zones) >= 2
    error_message = "At least 2 availability zones are required."
  }
}

variable "public_subnet_cidrs" {
  description = "Public subnet CIDRs"
  type        = list(string)
}

variable "private_subnet_cidrs" {
  description = "Deprecated: private app subnet CIDRs"
  type        = list(string)
  default     = []
}

variable "private_app_subnet_cidrs" {
  description = "Private app subnet CIDRs"
  type        = list(string)
}

variable "private_data_subnet_cidrs" {
  description = "Private data subnet CIDRs"
  type        = list(string)
}

variable "nat_gateway_mode" {
  description = "NAT topology mode (per_az or single). Leave empty for env-based default."
  type        = string
  default     = ""

  validation {
    condition     = var.nat_gateway_mode == "" || contains(["per_az", "single"], var.nat_gateway_mode)
    error_message = "nat_gateway_mode must be empty, per_az, or single."
  }
}

variable "map_public_ip_on_launch_public_subnets" {
  description = "Map public IP on launch for public subnets"
  type        = bool
  default     = false
}

variable "data_subnet_internet_egress_enabled" {
  description = "Enable controlled NAT egress for data subnets"
  type        = bool
  default     = true
}

variable "ecs_ingress_ports" {
  description = "Ports allowed from ALB to ECS tasks"
  type        = list(number)
  default     = [3000, 8000]
}

variable "enable_http_ingress" {
  description = "Enable ALB security group HTTP ingress"
  type        = bool
  default     = true
}

variable "enable_s3_gateway_endpoint" {
  description = "Enable S3 gateway endpoint"
  type        = bool
  default     = true
}

variable "enable_dynamodb_gateway_endpoint" {
  description = "Enable DynamoDB gateway endpoint"
  type        = bool
  default     = true
}

variable "create_interface_endpoints" {
  description = "Enable interface endpoint creation"
  type        = bool
  default     = true
}

variable "interface_endpoint_services" {
  description = "Interface endpoint service suffixes"
  type        = list(string)
  default = [
    "ecr.api",
    "ecr.dkr",
    "logs",
    "sts",
    "secretsmanager",
    "ssm",
    "kms"
  ]
}

variable "create_network_alb" {
  description = "Create ALB in networking module (disabled by default to avoid duplicate ALBs)"
  type        = bool
  default     = false
}

variable "enable_http_listener" {
  description = "Enable HTTP listener when ALB is created in this module"
  type        = bool
  default     = true
}

variable "acm_certificate_arn" {
  description = "ACM certificate ARN for networking-managed ALB (if enabled)"
  type        = string
  default     = ""
}

variable "enable_flow_logs" {
  description = "Enable VPC flow logs"
  type        = bool
  default     = true
}

variable "flow_logs_retention_days" {
  description = "CloudWatch retention for VPC flow logs"
  type        = number
  default     = 365
}

variable "tags" {
  description = "Additional tags"
  type        = map(string)
  default     = {}
}