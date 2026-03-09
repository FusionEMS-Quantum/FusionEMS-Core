output "trail_arn" {
  value = aws_cloudtrail.main.arn
}

output "trail_name" {
  value = aws_cloudtrail.main.id
}

output "log_bucket_arn" {
  value = aws_s3_bucket.cloudtrail_logs.arn
}

output "log_bucket_name" {
  value = aws_s3_bucket.cloudtrail_logs.id
}

output "log_group_arn" {
  value = aws_cloudwatch_log_group.cloudtrail.arn
}

output "kms_key_arn" {
  value = aws_kms_key.cloudtrail.arn
}
