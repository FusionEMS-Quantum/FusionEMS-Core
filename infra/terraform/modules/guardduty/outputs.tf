output "detector_id" {
  value = aws_guardduty_detector.main.id
}

output "findings_topic_arn" {
  value = aws_sns_topic.guardduty_findings.arn
}
