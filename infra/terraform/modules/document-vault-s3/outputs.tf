output "documents_bucket_name" {
  description = "Name of the vault documents S3 bucket (use as S3_BUCKET_DOCS env var)"
  value       = aws_s3_bucket.documents.id
}

output "documents_bucket_arn" {
  description = "ARN of the vault documents S3 bucket"
  value       = aws_s3_bucket.documents.arn
}

output "exports_bucket_name" {
  description = "Name of the vault exports S3 bucket (use as S3_BUCKET_EXPORTS env var)"
  value       = aws_s3_bucket.exports.id
}

output "exports_bucket_arn" {
  description = "ARN of the vault exports S3 bucket"
  value       = aws_s3_bucket.exports.arn
}

output "kms_key_arn" {
  description = "ARN of the vault KMS CMK"
  value       = aws_kms_key.vault.arn
}

output "kms_key_id" {
  description = "ID of the vault KMS CMK"
  value       = aws_kms_key.vault.key_id
}

output "iam_policy_arn" {
  description = "ARN of the IAM policy granting ECS task access to vault buckets and Textract"
  value       = aws_iam_policy.vault_s3.arn
}
