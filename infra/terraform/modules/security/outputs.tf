output "guardduty_detector_id" {
  value = aws_guardduty_detector.primary.id
}

output "securityhub_arn" {
  value = aws_securityhub_account.primary.id
}
