###############################################################################
# GuardDuty Module — FusionEMS
# Threat detection with automated alerting for high-severity findings
###############################################################################

data "aws_caller_identity" "current" {}
data "aws_region" "current" {}
data "aws_partition" "current" {}

locals {
  name_prefix = "${var.project}-${var.environment}"
  account_id  = data.aws_caller_identity.current.account_id
  region      = data.aws_region.current.id
  partition   = data.aws_partition.current.partition

  resource_tags = merge(var.tags, {
    Module = "guardduty"
  })
}

###############################################################################
# GuardDuty Detector
###############################################################################

resource "aws_guardduty_detector" "main" {
  enable                       = true
  finding_publishing_frequency = "FIFTEEN_MINUTES"

  datasources {
    s3_logs {
      enable = true
    }

    kubernetes {
      audit_logs {
        enable = false
      }
    }

    malware_protection {
      scan_ec2_instance_with_findings {
        ebs_volumes {
          enable = false
        }
      }
    }
  }

  tags = merge(local.resource_tags, {
    Name = "${local.name_prefix}-guardduty"
  })
}

###############################################################################
# KMS Key for GuardDuty SNS Encryption
###############################################################################

resource "aws_kms_key" "guardduty_sns" {
  description             = "KMS key for ${local.name_prefix} GuardDuty SNS encryption"
  deletion_window_in_days = 30
  enable_key_rotation     = true

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Sid    = "EnableRootAccountFullAccess"
        Effect = "Allow"
        Principal = {
          AWS = "arn:${local.partition}:iam::${local.account_id}:root"
        }
        Action   = "kms:*"
        Resource = "*"
      },
      {
        Sid    = "AllowEventBridgeEncrypt"
        Effect = "Allow"
        Principal = {
          Service = "events.amazonaws.com"
        }
        Action = [
          "kms:GenerateDataKey*",
          "kms:Decrypt",
        ]
        Resource = "*"
      },
      {
        Sid    = "AllowSNSUsage"
        Effect = "Allow"
        Principal = {
          Service = "sns.amazonaws.com"
        }
        Action = [
          "kms:GenerateDataKey*",
          "kms:Decrypt",
        ]
        Resource = "*"
      },
    ]
  })

  tags = merge(local.resource_tags, {
    Name = "${local.name_prefix}-guardduty-sns-kms"
  })
}

resource "aws_kms_alias" "guardduty_sns" {
  name          = "alias/${local.name_prefix}-guardduty-sns"
  target_key_id = aws_kms_key.guardduty_sns.key_id
}

###############################################################################
# SNS Topic for GuardDuty Findings
###############################################################################

resource "aws_sns_topic" "guardduty_findings" {
  name              = "${local.name_prefix}-guardduty-findings"
  kms_master_key_id = aws_kms_key.guardduty_sns.id

  tags = merge(local.resource_tags, {
    Name = "${local.name_prefix}-guardduty-findings"
  })
}

resource "aws_sns_topic_policy" "guardduty_findings" {
  arn = aws_sns_topic.guardduty_findings.arn

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Sid    = "AllowEventBridgePublish"
        Effect = "Allow"
        Principal = {
          Service = "events.amazonaws.com"
        }
        Action   = "SNS:Publish"
        Resource = aws_sns_topic.guardduty_findings.arn
      },
      {
        Sid    = "AllowAccountManagement"
        Effect = "Allow"
        Principal = {
          AWS = "arn:${local.partition}:iam::${local.account_id}:root"
        }
        Action = [
          "SNS:GetTopicAttributes",
          "SNS:SetTopicAttributes",
          "SNS:AddPermission",
          "SNS:RemovePermission",
          "SNS:DeleteTopic",
          "SNS:Subscribe",
          "SNS:ListSubscriptionsByTopic",
          "SNS:Publish",
        ]
        Resource = aws_sns_topic.guardduty_findings.arn
      },
    ]
  })
}

###############################################################################
# EventBridge Rule for GuardDuty Findings
###############################################################################

resource "aws_cloudwatch_event_rule" "guardduty_findings" {
  name        = "${local.name_prefix}-guardduty-findings"
  description = "Capture GuardDuty finding events for ${local.name_prefix}"

  event_pattern = jsonencode({
    source      = ["aws.guardduty"]
    detail-type = ["GuardDuty Finding"]
  })

  tags = merge(local.resource_tags, {
    Name = "${local.name_prefix}-guardduty-findings-rule"
  })
}

resource "aws_cloudwatch_event_target" "guardduty_sns" {
  rule      = aws_cloudwatch_event_rule.guardduty_findings.name
  target_id = "${local.name_prefix}-guardduty-to-sns"
  arn       = aws_sns_topic.guardduty_findings.arn
}

###############################################################################
# CloudWatch Log Group for GuardDuty Metrics
###############################################################################

resource "aws_cloudwatch_log_group" "guardduty" {
  name              = "/guardduty/${local.name_prefix}"
  retention_in_days = 365

  tags = merge(local.resource_tags, {
    Name = "${local.name_prefix}-guardduty-logs"
  })
}

resource "aws_cloudwatch_log_resource_policy" "guardduty_events" {
  policy_name = "${local.name_prefix}-guardduty-events-to-logs"

  policy_document = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Sid    = "AllowEventBridgeToPutGuardDutyLogs"
        Effect = "Allow"
        Principal = {
          Service = "events.amazonaws.com"
        }
        Action = [
          "logs:CreateLogStream",
          "logs:PutLogEvents",
        ]
        Resource = "${aws_cloudwatch_log_group.guardduty.arn}:*"
      },
    ]
  })
}

resource "aws_cloudwatch_event_target" "guardduty_logs" {
  rule      = aws_cloudwatch_event_rule.guardduty_findings.name
  target_id = "${local.name_prefix}-guardduty-to-logs"
  arn       = aws_cloudwatch_log_group.guardduty.arn

  depends_on = [aws_cloudwatch_log_resource_policy.guardduty_events]
}

###############################################################################
# CloudWatch Metric Filter & Alarm — High/Critical Severity Findings
###############################################################################

resource "aws_cloudwatch_log_metric_filter" "high_severity_findings" {
  name           = "${local.name_prefix}-guardduty-high-severity"
  log_group_name = aws_cloudwatch_log_group.guardduty.name
  pattern        = "{ $.detail.severity >= 7 }"

  metric_transformation {
    name          = "${local.name_prefix}-GuardDutyHighSeverityFindings"
    namespace     = "${var.project}/GuardDutyMetrics"
    value         = "1"
    default_value = "0"
  }
}

resource "aws_cloudwatch_metric_alarm" "high_severity_findings" {
  alarm_name          = "${local.name_prefix}-guardduty-high-severity"
  alarm_description   = "GuardDuty HIGH/CRITICAL severity finding detected for ${local.name_prefix}"
  comparison_operator = "GreaterThanOrEqualToThreshold"
  evaluation_periods  = 1
  metric_name         = "${local.name_prefix}-GuardDutyHighSeverityFindings"
  namespace           = "${var.project}/GuardDutyMetrics"
  period              = 300
  statistic           = "Sum"
  threshold           = 1
  treat_missing_data  = "notBreaching"
  alarm_actions       = [var.alert_topic_arn]
  ok_actions          = [var.alert_topic_arn]

  tags = merge(local.resource_tags, {
    Name = "${local.name_prefix}-guardduty-high-severity-alarm"
  })
}
