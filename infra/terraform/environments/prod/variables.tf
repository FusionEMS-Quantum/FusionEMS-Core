###############################################################################
# FusionEMS – Input variables (shared across all environments)
###############################################################################

# ─── General ─────────────────────────────────────────────────────────────────

variable "aws_region" {
  description = "AWS region for deployment"
  type        = string
  default     = "us-east-1"
}

variable "environment" {
  description = "Deployment environment name (dev, staging, prod, dr)"
  type        = string
}

variable "project" {
  description = "Project name used for resource naming and tagging"
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

# ─── Networking ──────────────────────────────────────────────────────────────

variable "vpc_cidr" {
  description = "CIDR block for the VPC"
  type        = string
}

variable "availability_zones" {
  description = "List of availability zones to deploy into"
  type        = list(string)
}

variable "public_subnet_cidrs" {
  description = "CIDR blocks for public subnets"
  type        = list(string)
}

variable "private_app_subnet_cidrs" {
  description = "CIDR blocks for private application subnets"
  type        = list(string)
}

variable "private_data_subnet_cidrs" {
  description = "CIDR blocks for private data subnets"
  type        = list(string)
}

variable "nat_gateway_mode" {
  description = "NAT topology mode: per_az or single"
  type        = string
  default     = "per_az"
}

# ─── DNS / TLS ───────────────────────────────────────────────────────────────

variable "root_domain_name" {
  description = "Root domain name for the application"
  type        = string
}

variable "api_domain_name" {
  description = "API domain name"
  type        = string
}

variable "hosted_zone_id" {
  description = "Route53 hosted zone ID for DNS records"
  type        = string
}

variable "acm_certificate_arn_us_east_1" {
  description = "ACM certificate ARN in us-east-1 (required for CloudFront)"
  type        = string
  default     = ""
}

# ─── Monitoring ──────────────────────────────────────────────────────────────

variable "alert_email" {
  description = "Email address for CloudWatch alarm notifications"
  type        = string
}

# ─── Container Images ───────────────────────────────────────────────────────

variable "backend_image_tag" {
  description = "Docker image tag for the backend service"
  type        = string
  default     = "latest"
}

variable "frontend_image_tag" {
  description = "Docker image tag for the frontend service"
  type        = string
  default     = "latest"
}

# ─── CI / CD ─────────────────────────────────────────────────────────────────

variable "github_org" {
  description = "GitHub organization for OIDC federation"
  type        = string
  default     = ""
}

variable "github_repo" {
  description = "GitHub repository name for OIDC federation"
  type        = string
  default     = ""
}

variable "github_actions_role_name" {
  description = "Role name GitHub Actions should assume for Terraform deployments"
  type        = string
  default     = ""
}

variable "github_allowed_subjects" {
  description = "Allowed GitHub OIDC subject patterns for the deployment role trust policy"
  type        = list(string)
  default     = []
}

# ─── Database ────────────────────────────────────────────────────────────────

variable "db_instance_class" {
  description = "RDS instance class"
  type        = string
}

# ─── Cache ───────────────────────────────────────────────────────────────────

variable "redis_node_type" {
  description = "ElastiCache Redis node type"
  type        = string
}

# ─── SES / Microsoft Graph ──────────────────────────────────────────────────

variable "graph_tenant_id" {
  description = "Microsoft Graph tenant ID for email integration"
  type        = string
  sensitive   = true
  default     = ""
}

variable "graph_client_id" {
  description = "Microsoft Graph client ID for email integration"
  type        = string
  sensitive   = true
  default     = ""
}

variable "graph_client_secret" {
  description = "Microsoft Graph client secret for email integration"
  type        = string
  sensitive   = true
  default     = ""
}

variable "graph_founder_email" {
  description = "Founder email address for Microsoft Graph integration"
  type        = string
  sensitive   = true
  default     = ""
}

# ─── Centralized Billing Line (Telnyx) ─────────────────────────────────────

variable "central_billing_desired_tollfree_prefix" {
  description = "Preferred toll-free prefix for centralized billing number purchase"
  type        = string
  default     = "800"
}

variable "central_billing_existing_phone_e164" {
  description = "Optional pre-provisioned centralized billing number in E.164; when set, purchase is skipped"
  type        = string
  default     = ""
}

variable "founder_billing_escalation_phone_e164" {
  description = "Founder escalation phone destination for high-risk billing calls"
  type        = string
  default     = ""
}

# ─── Brand Identity ────────────────────────────────────────────────────────────

variable "brand_display_name" {
  description = "Platform brand display name for all outbound communications"
  type        = string
  default     = "FusionEMS Quantum"
}

variable "brand_domain" {
  description = "Primary web domain for brand-linked emails and portal references"
  type        = string
  default     = "fusionemsquantum.com"
}
