output "public_route_table_id" {
  description = "Public route table ID"
  value       = aws_route_table.public.id
}

output "private_app_route_table_ids" {
  description = "Private app route table IDs ordered by AZ"
  value       = [for az in var.availability_zones : aws_route_table.private_app[az].id]
}

output "private_data_route_table_ids" {
  description = "Private data route table IDs ordered by AZ"
  value       = [for az in var.availability_zones : aws_route_table.private_data[az].id]
}