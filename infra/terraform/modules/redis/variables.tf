variable "environment" {
  description = "Deployment environment (dev, staging, prod, dr)"
  type        = string

  validation {
    condition     = contains(["dev", "staging", "prod", "dr"], var.environment)
    error_message = "Environment must be one of: dev, staging, prod, dr."
  }
}

variable "project" {
  description = "Project name used for resource naming and tagging"
  type        = string
  default     = "fusionems"
}

variable "vpc_id" {
  description = "VPC ID where Redis will be deployed"
  type        = string
}

variable "private_subnet_ids" {
  description = "List of private subnet IDs for the ElastiCache subnet group"
  type        = list(string)
}

variable "redis_security_group_id" {
  description = "Security group ID to attach to the Redis replication group"
  type        = string
}

variable "node_type" {
  description = "ElastiCache node type"
  type        = string
  default     = "cache.t4g.medium"
}

variable "tags" {
  description = "Additional tags to apply to all resources"
  type        = map(string)
  default     = {}
}

variable "create_kms_alias" {
  type        = bool
  default     = true
  description = "Create module-managed KMS alias for Redis. Set to false if alias is managed externally to avoid collisions."
}

variable "kms_alias_name" {
  type        = string
  default     = ""
  description = "Optional explicit KMS alias name to create for Redis. If empty module uses 'alias/project-env-redis'."
}
