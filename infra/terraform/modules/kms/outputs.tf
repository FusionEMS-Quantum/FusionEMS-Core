output "key_arn" {
  value       = aws_kms_key.main.arn
  description = "The ARN of the KMS key"
}

output "key_id" {
  value       = aws_kms_key.main.key_id
  description = "The ID of the KMS key"
}
