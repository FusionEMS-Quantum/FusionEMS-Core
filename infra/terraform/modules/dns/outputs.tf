output "public_zone_id" {
  description = "Public hosted zone ID"
  value       = try(aws_route53_zone.public[0].zone_id, null)
}

output "private_zone_id" {
  description = "Private hosted zone ID"
  value       = try(aws_route53_zone.private[0].zone_id, null)
}