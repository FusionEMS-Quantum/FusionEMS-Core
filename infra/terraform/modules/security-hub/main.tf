###############################################################################
# Security Hub Module — FusionEMS
# Enables Security Hub with compliance standards and EventBridge alerting.
###############################################################################

data "aws_region" "current" {}
data "aws_caller_identity" "current" {}

locals {
  name_prefix = "${var.project}-${var.environment}"
}

# --------------------------------------------------------------------------- #
# Security Hub Account
# --------------------------------------------------------------------------- #

resource "aws_securityhub_account" "main" {
  auto_enable_controls = true
}

# --------------------------------------------------------------------------- #
# Standards Subscriptions
# --------------------------------------------------------------------------- #

resource "aws_securityhub_standards_subscription" "aws_foundational" {
  standards_arn = "arn:aws:securityhub:${data.aws_region.current.name}::standards/aws-foundational-security-best-practices/v/1.0.0"

  timeouts {
    create = "20m"
  }

  depends_on = [aws_securityhub_account.main]
}

resource "aws_securityhub_standards_subscription" "cis" {
  count = var.enable_cis_standard ? 1 : 0

  standards_arn = "arn:aws:securityhub:::ruleset/cis-aws-foundations-benchmark/v/1.2.0"

  timeouts {
    create = "20m"
  }

  depends_on = [aws_securityhub_account.main]
}

resource "aws_securityhub_standards_subscription" "nist" {
  count = var.enable_nist_standard ? 1 : 0

  standards_arn = "arn:aws:securityhub:${data.aws_region.current.name}::standards/nist-800-53/v/5.0.0"

  timeouts {
    create = "20m"
  }

  depends_on = [aws_securityhub_account.main]
}

# --------------------------------------------------------------------------- #
# EventBridge — Critical/High Findings
# --------------------------------------------------------------------------- #

resource "aws_cloudwatch_event_rule" "securityhub_findings" {
  name        = "${local.name_prefix}-securityhub-critical-high"
  description = "Routes Security Hub CRITICAL and HIGH findings to SNS"

  event_pattern = jsonencode({
    source      = ["aws.securityhub"]
    detail-type = ["Security Hub Findings - Imported"]
    detail = {
      findings = {
        Severity = {
          Label = ["CRITICAL", "HIGH"]
        }
      }
    }
  })

  tags = merge(var.tags, {
    Name = "${local.name_prefix}-securityhub-critical-high"
  })
}

resource "aws_cloudwatch_event_target" "securityhub_to_sns" {
  rule      = aws_cloudwatch_event_rule.securityhub_findings.name
  target_id = "${local.name_prefix}-securityhub-sns"
  arn       = var.alert_topic_arn
}

# --------------------------------------------------------------------------- #
# SNS Topic Policy (optional — only if this module owns the policy)
# --------------------------------------------------------------------------- #

resource "aws_sns_topic_policy" "securityhub_publish" {
  count = var.manage_sns_policy ? 1 : 0

  arn = var.alert_topic_arn

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Sid    = "AllowEventBridgePublish"
        Effect = "Allow"
        Principal = {
          Service = "events.amazonaws.com"
        }
        Action   = "sns:Publish"
        Resource = var.alert_topic_arn
        Condition = {
          ArnEquals = {
            "aws:SourceArn" = aws_cloudwatch_event_rule.securityhub_findings.arn
          }
        }
      }
    ]
  })
}
