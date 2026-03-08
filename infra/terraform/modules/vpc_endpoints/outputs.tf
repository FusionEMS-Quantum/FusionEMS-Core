output "interface_endpoint_security_group_id" {
  description = "Security group ID for interface endpoints"
  value       = try(aws_security_group.interface_endpoints[0].id, null)
}

output "interface_endpoint_ids" {
  description = "Map of interface endpoint IDs by service"
  value       = { for svc, ep in aws_vpc_endpoint.interface : svc => ep.id }
}

output "s3_gateway_endpoint_id" {
  description = "S3 gateway endpoint ID"
  value       = try(aws_vpc_endpoint.s3[0].id, null)
}

output "dynamodb_gateway_endpoint_id" {
  description = "DynamoDB gateway endpoint ID"
  value       = try(aws_vpc_endpoint.dynamodb[0].id, null)
}