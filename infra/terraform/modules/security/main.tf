# GuardDuty
resource "aws_guardduty_detector" "primary" {
  enable = true
  finding_publishing_frequency = "FIFTEEN_MINUTES"
  tags = {
    Environment = var.environment
    Compliance = "SOC2,HIPAA,ISO27001"
  }
}

# Security Hub
resource "aws_securityhub_account" "primary" {}

resource "aws_securityhub_standards_subscription" "cis" {
  depends_on    = [aws_securityhub_account.primary]
  standards_arn = "arn:aws:securityhub:::ruleset/cis-aws-foundations-benchmark/v/1.4.0"
}

resource "aws_securityhub_standards_subscription" "pci" {
  depends_on    = [aws_securityhub_account.primary]
  standards_arn = "arn:aws:securityhub:us-east-1::standards/pci-dss/v/3.2.1"
}

# Config
resource "aws_config_configuration_recorder" "main" {
  name     = "${var.environment}-config-recorder"
  role_arn = aws_iam_role.config_role.arn
  recording_group {
    all_supported = true
    include_global_resource_types = true
  }
}

resource "aws_config_delivery_channel" "main" {
  name           = "${var.environment}-config-delivery"
  s3_bucket_name = aws_s3_bucket.config_bucket.bucket
  depends_on     = [aws_config_configuration_recorder.main]
}

resource "aws_config_configuration_recorder_status" "main" {
  name       = aws_config_configuration_recorder.main.name
  is_enabled = true
  depends_on = [aws_config_delivery_channel.main]
}

resource "aws_s3_bucket" "config_bucket" {
  bucket = "${var.environment}-fusionems-config-logs"
  force_destroy = false
}
resource "aws_s3_bucket_public_access_block" "config_bucket_pab" {
  bucket                  = aws_s3_bucket.config_bucket.id
  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

resource "aws_iam_role" "config_role" {
  name = "${var.environment}-config-role"
  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = "sts:AssumeRole"
        Effect = "Allow"
        Principal = {
          Service = "config.amazonaws.com"
        }
      }
    ]
  })
}

resource "aws_iam_role_policy_attachment" "config_policy" {
  role       = aws_iam_role.config_role.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWS_ConfigRole"
}

# Macie
resource "aws_macie2_account" "main" {
  count  = var.enable_macie ? 1 : 0
  status = "ENABLED"
}

# Inspector
# Note: AWS Inspector v2 is enabled at the account level on supported resource types.
