###############################################################################
# FusionEMS Networking Module (Orchestrator)
# Modular composition for sovereign-grade, multi-AZ networking
###############################################################################

locals {
  name_prefix = "${var.project}-${var.environment}"

  effective_nat_gateway_mode = var.nat_gateway_mode != "" ? var.nat_gateway_mode : (
    var.environment == "prod" ? "per_az" : "single"
  )

  common_tags = merge(var.tags, {
    Application        = var.application
    Environment        = var.environment
    Owner              = var.owner
    ManagedBy          = "Terraform"
    CostCenter         = var.cost_center
    DataClassification = var.data_classification
  })
}

check "subnet_az_alignment" {
  assert {
    condition = (
      length(var.public_subnet_cidrs) == length(var.availability_zones)
      && length(var.private_app_subnet_cidrs) == length(var.availability_zones)
      && length(var.private_data_subnet_cidrs) == length(var.availability_zones)
    )
    error_message = "Subnet CIDR list lengths must each match availability_zones length."
  }
}

module "vpc" {
  source = "../vpc"

  name_prefix = local.name_prefix
  vpc_cidr    = var.vpc_cidr
  tags        = local.common_tags
}

module "subnets" {
  source = "../subnets"

  name_prefix               = local.name_prefix
  vpc_id                    = module.vpc.vpc_id
  availability_zones        = var.availability_zones
  public_subnet_cidrs       = var.public_subnet_cidrs
  private_app_subnet_cidrs  = var.private_app_subnet_cidrs
  private_data_subnet_cidrs = var.private_data_subnet_cidrs
  map_public_ip_on_launch   = var.map_public_ip_on_launch_public_subnets
  tags                      = local.common_tags
}

module "nat" {
  source = "../nat"

  name_prefix       = local.name_prefix
  public_subnet_ids = module.subnets.public_subnet_ids
  nat_gateway_mode  = local.effective_nat_gateway_mode
  tags              = local.common_tags
}

module "route_tables" {
  source = "../route_tables"

  name_prefix                         = local.name_prefix
  vpc_id                              = module.vpc.vpc_id
  internet_gateway_id                 = module.vpc.internet_gateway_id
  availability_zones                  = var.availability_zones
  public_subnet_ids                   = module.subnets.public_subnet_ids
  private_app_subnet_ids              = module.subnets.private_app_subnet_ids
  private_data_subnet_ids             = module.subnets.private_data_subnet_ids
  nat_gateway_ids                     = module.nat.nat_gateway_ids
  data_subnet_internet_egress_enabled = var.data_subnet_internet_egress_enabled
  tags                                = local.common_tags
}

module "security_groups" {
  source = "../security_groups"

  name_prefix         = local.name_prefix
  vpc_id              = module.vpc.vpc_id
  vpc_cidr            = var.vpc_cidr
  ecs_ingress_ports   = var.ecs_ingress_ports
  enable_http_ingress = var.enable_http_ingress
  tags                = local.common_tags
}

module "vpc_endpoints" {
  source = "../vpc_endpoints"

  name_prefix                      = local.name_prefix
  vpc_id                           = module.vpc.vpc_id
  vpc_cidr                         = var.vpc_cidr
  region                           = var.region
  route_table_ids                  = concat(module.route_tables.private_app_route_table_ids, module.route_tables.private_data_route_table_ids)
  private_app_subnet_ids           = module.subnets.private_app_subnet_ids
  enable_s3_gateway_endpoint       = var.enable_s3_gateway_endpoint
  enable_dynamodb_gateway_endpoint = var.enable_dynamodb_gateway_endpoint
  create_interface_endpoints       = var.create_interface_endpoints
  interface_endpoint_services      = var.interface_endpoint_services
  tags                             = local.common_tags
}

module "alb" {
  source = "../alb"

  enabled                    = var.create_network_alb
  name_prefix                = local.name_prefix
  internal                   = false
  alb_security_group_id      = module.security_groups.alb_security_group_id
  public_subnet_ids          = module.subnets.public_subnet_ids
  acm_certificate_arn        = var.acm_certificate_arn
  enable_http_listener       = var.enable_http_listener
  enable_deletion_protection = var.environment == "prod"
  tags                       = local.common_tags
}

resource "aws_cloudwatch_log_group" "flow_logs" {
  count = var.enable_flow_logs ? 1 : 0

  name              = "/aws/vpc/${local.name_prefix}-flow-logs"
  retention_in_days = var.flow_logs_retention_days

  tags = merge(local.common_tags, {
    Name = "${local.name_prefix}-flow-logs"
  })
}

resource "aws_iam_role" "flow_logs" {
  count = var.enable_flow_logs ? 1 : 0

  name_prefix = "${local.name_prefix}-flow-logs-"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Action = "sts:AssumeRole"
      Effect = "Allow"
      Principal = {
        Service = "vpc-flow-logs.amazonaws.com"
      }
    }]
  })

  tags = merge(local.common_tags, {
    Name = "${local.name_prefix}-flow-logs-role"
  })
}

resource "aws_iam_role_policy" "flow_logs" {
  count = var.enable_flow_logs ? 1 : 0

  name_prefix = "${local.name_prefix}-flow-logs-"
  role        = aws_iam_role.flow_logs[0].id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Action = [
        "logs:CreateLogGroup",
        "logs:CreateLogStream",
        "logs:PutLogEvents",
        "logs:DescribeLogGroups",
        "logs:DescribeLogStreams"
      ]
      Effect   = "Allow"
      Resource = "${aws_cloudwatch_log_group.flow_logs[0].arn}:*"
    }]
  })
}

resource "aws_flow_log" "main" {
  count = var.enable_flow_logs ? 1 : 0

  vpc_id               = module.vpc.vpc_id
  traffic_type         = "ALL"
  log_destination_type = "cloud-watch-logs"
  log_destination      = aws_cloudwatch_log_group.flow_logs[0].arn
  iam_role_arn         = aws_iam_role.flow_logs[0].arn

  tags = merge(local.common_tags, {
    Name = "${local.name_prefix}-flow-log"
  })
}