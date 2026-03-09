output "hub_arn" {
  description = "ARN of the Security Hub account"
  value       = aws_securityhub_account.main.arn
}

output "finding_rule_arn" {
  description = "ARN of the EventBridge rule for critical/high findings"
  value       = aws_cloudwatch_event_rule.securityhub_findings.arn
}
