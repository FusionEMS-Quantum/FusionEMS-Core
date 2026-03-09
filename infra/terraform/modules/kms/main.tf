data "aws_caller_identity" "current" {}

resource "aws_kms_key" "main" {
  description             = var.description
  deletion_window_in_days = 30
  enable_key_rotation     = true
  multi_region            = true
  
  policy = jsonencode({
    Version = "2012-10-17"
    Id      = "key-consolepolicy-3"
    Statement = [
      {
        Sid    = "Enable IAM User Permissions"
        Effect = "Allow"
        Principal = {
          AWS = "arn:aws:iam::${data.aws_caller_identity.current.account_id}:root"
        }
        Action   = "kms:*"
        Resource = "*"
      },
      {
        Sid    = "Allow CloudTrail to encrypt logs"
        Effect = "Allow"
        Principal = {
          Service = "cloudtrail.amazonaws.com"
        }
        Action   = "kms:GenerateDataKey*"
        Resource = "*"
        Condition = {
          StringLike = {
            "kms:EncryptionContext:aws:cloudtrail:arn" = "arn:aws:cloudtrail:*:${data.aws_caller_identity.current.account_id}:trail/*"
          }
        }
      }
    ]
  })

  tags = {
    Environment = var.environment
    Compliance  = "HIPAA,SOC2"
  }
}

resource "aws_kms_alias" "main" {
  name          = "alias/${var.alias_name}"
  target_key_id = aws_kms_key.main.key_id
}
