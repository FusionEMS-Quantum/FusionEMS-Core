output "alb_arn" {
  description = "ALB ARN"
  value       = try(aws_lb.this[0].arn, null)
}

output "alb_dns_name" {
  description = "ALB DNS name"
  value       = try(aws_lb.this[0].dns_name, null)
}

output "alb_zone_id" {
  description = "ALB hosted zone ID"
  value       = try(aws_lb.this[0].zone_id, null)
}

output "alb_https_listener_arn" {
  description = "ALB HTTPS listener ARN"
  value       = try(aws_lb_listener.https[0].arn, null)
}

output "alb_http_listener_arn" {
  description = "ALB HTTP listener ARN"
  value       = try(aws_lb_listener.http[0].arn, null)
}