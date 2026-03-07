output "audit_export_bucket_arn" {
  description = "ARN of the immutable audit export S3 bucket"
  value       = aws_s3_bucket.audit_exports.arn
}

output "audit_export_bucket_name" {
  description = "Name of the audit export S3 bucket"
  value       = aws_s3_bucket.audit_exports.id
}

output "phi_export_bucket_arn" {
  description = "ARN of the PHI export staging S3 bucket"
  value       = aws_s3_bucket.phi_exports.arn
}

output "phi_export_bucket_name" {
  description = "Name of the PHI export staging S3 bucket"
  value       = aws_s3_bucket.phi_exports.id
}

output "governance_task_role_arn" {
  description = "ARN of the governance ECS task IAM role"
  value       = aws_iam_role.governance_task.arn
}

output "governance_kms_key_arn" {
  description = "ARN of the governance audit KMS key"
  value       = aws_kms_key.governance_audit.arn
}

output "governance_log_group_name" {
  description = "CloudWatch log group for governance audit events"
  value       = aws_cloudwatch_log_group.governance_audit.name
}
