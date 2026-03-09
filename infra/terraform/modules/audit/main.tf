data "aws_caller_identity" "current" {}
data "aws_region" "current" {}

# =============================================================================
# CloudWatch Log Group — CloudTrail writes here for near-real-time visibility
# =============================================================================

resource "aws_cloudwatch_log_group" "cloudtrail" {
  name              = "/aws/cloudtrail/${var.environment}-global"
  retention_in_days = 365
  kms_key_id        = var.kms_key_arn

  tags = {
    Environment = var.environment
    Compliance  = "SOC2,HIPAA,ISO27001"
  }
}

# =============================================================================
# IAM Role — allows CloudTrail to publish to the CloudWatch Log Group
# =============================================================================

resource "aws_iam_role" "cloudtrail_cloudwatch" {
  name = "${var.environment}-cloudtrail-cw-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Sid    = "AllowCloudTrailAssumeRole"
        Effect = "Allow"
        Principal = {
          Service = "cloudtrail.amazonaws.com"
        }
        Action = "sts:AssumeRole"
      }
    ]
  })

  tags = {
    Environment = var.environment
    Compliance  = "SOC2,HIPAA,ISO27001"
  }
}

resource "aws_iam_role_policy" "cloudtrail_cloudwatch" {
  name = "${var.environment}-cloudtrail-cw-policy"
  role = aws_iam_role.cloudtrail_cloudwatch.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Sid    = "AllowCreateLogStream"
        Effect = "Allow"
        Action = "logs:CreateLogStream"
        Resource = "${aws_cloudwatch_log_group.cloudtrail.arn}:log-stream:*"
      },
      {
        Sid    = "AllowPutLogEvents"
        Effect = "Allow"
        Action = "logs:PutLogEvents"
        Resource = "${aws_cloudwatch_log_group.cloudtrail.arn}:log-stream:*"
      }
    ]
  })
}

# =============================================================================
# SNS Topic — CloudTrail publishes notifications for each log delivery
# =============================================================================

resource "aws_sns_topic" "cloudtrail_alerts" {
  name              = "${var.environment}-cloudtrail-alerts"
  kms_master_key_id = var.kms_key_arn

  tags = {
    Environment = var.environment
    Compliance  = "SOC2,HIPAA,ISO27001"
  }
}

resource "aws_sns_topic_policy" "cloudtrail_alerts" {
  arn = aws_sns_topic.cloudtrail_alerts.arn

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Sid    = "AllowCloudTrailPublish"
        Effect = "Allow"
        Principal = {
          Service = "cloudtrail.amazonaws.com"
        }
        Action   = "SNS:Publish"
        Resource = aws_sns_topic.cloudtrail_alerts.arn
        Condition = {
          StringEquals = {
            "AWS:SourceAccount" = data.aws_caller_identity.current.account_id
          }
        }
      }
    ]
  })
}

# =============================================================================
# CloudTrail
# =============================================================================

resource "aws_cloudtrail" "global" {
  name                          = "${var.environment}-cloudtrail"
  s3_bucket_name                = var.s3_bucket_name
  include_global_service_events = true
  is_multi_region_trail         = var.multi_region
  enable_log_file_validation    = true
  kms_key_id                    = var.kms_key_arn
  sns_topic_name                = aws_sns_topic.cloudtrail_alerts.arn
  cloud_watch_logs_group_arn    = "${aws_cloudwatch_log_group.cloudtrail.arn}:*"
  cloud_watch_logs_role_arn     = aws_iam_role.cloudtrail_cloudwatch.arn

  event_selector {
    read_write_type           = "All"
    include_management_events = true

    data_resource {
      type   = "AWS::S3::Object"
      values = ["arn:aws:s3:::"]
    }
  }

  tags = {
    Environment = var.environment
    Compliance  = "SOC2,HIPAA,ISO27001"
  }
}
