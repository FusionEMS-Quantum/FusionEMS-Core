output "public_subnet_ids" {
  description = "Public subnet IDs ordered by AZ input"
  value       = [for az in var.availability_zones : aws_subnet.public[az].id]
}

output "private_app_subnet_ids" {
  description = "Private application subnet IDs ordered by AZ input"
  value       = [for az in var.availability_zones : aws_subnet.private_app[az].id]
}

output "private_data_subnet_ids" {
  description = "Private data subnet IDs ordered by AZ input"
  value       = [for az in var.availability_zones : aws_subnet.private_data[az].id]
}