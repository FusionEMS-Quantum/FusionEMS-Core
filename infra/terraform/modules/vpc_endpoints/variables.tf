variable "name_prefix" {
  description = "Name prefix for endpoint resources"
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

variable "region" {
  description = "AWS region"
  type        = string
}

variable "route_table_ids" {
  description = "Route table IDs for gateway endpoint associations"
  type        = list(string)
}

variable "private_app_subnet_ids" {
  description = "Private app subnet IDs for interface endpoint ENIs"
  type        = list(string)
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
  description = "Create interface endpoints"
  type        = bool
  default     = true
}

variable "interface_endpoint_services" {
  description = "AWS interface endpoint service suffixes"
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

variable "tags" {
  description = "Resource tags"
  type        = map(string)
  default     = {}
}