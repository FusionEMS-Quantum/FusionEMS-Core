###############################################################################
# FusionEMS – AWS Backup Module – Outputs
###############################################################################

output "vault_arn" {
  description = "Backup vault ARN"
  value       = aws_backup_vault.main.arn
}

output "vault_name" {
  description = "Backup vault name"
  value       = aws_backup_vault.main.name
}

output "plan_arn" {
  description = "Backup plan ARN"
  value       = aws_backup_plan.main.arn
}

output "backup_role_arn" {
  description = "IAM role ARN used by AWS Backup"
  value       = aws_iam_role.backup.arn
}

output "kms_key_arn" {
  description = "KMS key ARN for backup vault encryption"
  value       = aws_kms_key.backup.arn
}
