output "vpc_id" {
  description = "VPC ID"
  value       = module.vpc.vpc_id
}

output "vpc_cidr_block" {
  description = "VPC CIDR"
  value       = module.vpc.vpc_cidr_block
}

output "public_subnet_ids" {
  description = "Public subnet IDs"
  value       = module.subnets.public_subnet_ids
}

output "private_subnet_ids" {
  description = "Compatibility output: private app subnet IDs"
  value       = module.subnets.private_app_subnet_ids
}

output "private_app_subnet_ids" {
  description = "Private app subnet IDs"
  value       = module.subnets.private_app_subnet_ids
}

output "data_subnet_ids" {
  description = "Private data subnet IDs"
  value       = module.subnets.private_data_subnet_ids
}

output "nat_gateway_ids" {
  description = "NAT gateway IDs"
  value       = module.nat.nat_gateway_ids
}

output "public_route_table_id" {
  description = "Public route table ID"
  value       = module.route_tables.public_route_table_id
}

output "private_app_route_table_ids" {
  description = "Private app route table IDs"
  value       = module.route_tables.private_app_route_table_ids
}

output "private_data_route_table_ids" {
  description = "Private data route table IDs"
  value       = module.route_tables.private_data_route_table_ids
}

output "alb_security_group_id" {
  description = "ALB security group ID"
  value       = module.security_groups.alb_security_group_id
}

output "ecs_security_group_id" {
  description = "ECS security group ID"
  value       = module.security_groups.ecs_security_group_id
}

output "rds_security_group_id" {
  description = "RDS security group ID"
  value       = module.security_groups.rds_security_group_id
}

output "redis_security_group_id" {
  description = "Redis security group ID"
  value       = module.security_groups.redis_security_group_id
}

output "interface_endpoint_security_group_id" {
  description = "VPC endpoint security group ID"
  value       = module.vpc_endpoints.interface_endpoint_security_group_id
}

output "interface_endpoint_ids" {
  description = "Interface VPC endpoint IDs by service"
  value       = module.vpc_endpoints.interface_endpoint_ids
}

output "s3_gateway_endpoint_id" {
  description = "S3 gateway endpoint ID"
  value       = module.vpc_endpoints.s3_gateway_endpoint_id
}

output "dynamodb_gateway_endpoint_id" {
  description = "DynamoDB gateway endpoint ID"
  value       = module.vpc_endpoints.dynamodb_gateway_endpoint_id
}

output "alb_arn" {
  description = "Networking-managed ALB ARN (null when disabled)"
  value       = module.alb.alb_arn
}

output "alb_dns_name" {
  description = "Networking-managed ALB DNS name (null when disabled)"
  value       = module.alb.alb_dns_name
}

output "alb_listener_arn" {
  description = "Networking-managed ALB HTTPS listener ARN (null when disabled)"
  value       = module.alb.alb_https_listener_arn
}

output "alb_zone_id" {
  description = "Networking-managed ALB zone ID (null when disabled)"
  value       = module.alb.alb_zone_id
}