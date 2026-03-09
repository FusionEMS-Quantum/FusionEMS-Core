###############################################################################
# AWS Config Module — FusionEMS
# Records resource configuration, delivers to encrypted S3, enforces managed rules.
###############################################################################

data "aws_caller_identity" "current" {}
data "aws_region" "current" {}

locals {
  bucket_name = "${var.project}-${var.environment}-config-recordings"
  name_prefix = "${var.project}-${var.environment}"
}

# --------------------------------------------------------------------------- #
# S3 Bucket — Config Recordings
# --------------------------------------------------------------------------- #

resource "aws_s3_bucket" "config_recordings" {
  bucket        = local.bucket_name
  force_destroy = false

  tags = merge(var.tags, {
    Name = local.bucket_name
  })
}

resource "aws_s3_bucket_versioning" "config_recordings" {
  bucket = aws_s3_bucket.config_recordings.id

  versioning_configuration {
    status = "Enabled"
  }
}

resource "aws_s3_bucket_server_side_encryption_configuration" "config_recordings" {
  bucket = aws_s3_bucket.config_recordings.id

  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm = "AES256"
    }
    bucket_key_enabled = true
  }
}

resource "aws_s3_bucket_public_access_block" "config_recordings" {
  bucket = aws_s3_bucket.config_recordings.id

  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

resource "aws_s3_bucket_lifecycle_configuration" "config_recordings" {
  bucket = aws_s3_bucket.config_recordings.id

  rule {
    id     = "archive-and-expire"
    status = "Enabled"

    filter {}

    transition {
      days          = 365
      storage_class = "GLACIER"
    }

    expiration {
      days = 2555
    }

    abort_incomplete_multipart_upload {
      days_after_initiation = 7
    }
  }
}

resource "aws_s3_bucket_policy" "config_recordings_tls_only" {
  bucket = aws_s3_bucket.config_recordings.id

  depends_on = [aws_s3_bucket_public_access_block.config_recordings]

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Sid       = "DenyInsecureTransport"
        Effect    = "Deny"
        Principal = "*"
        Action    = "s3:*"
        Resource = [
          aws_s3_bucket.config_recordings.arn,
          "${aws_s3_bucket.config_recordings.arn}/*"
        ]
        Condition = {
          Bool = {
            "aws:SecureTransport" = "false"
          }
        }
      }
    ]
  })
}

# --------------------------------------------------------------------------- #
# IAM Role — AWS Config Service
# --------------------------------------------------------------------------- #

resource "aws_iam_role" "config" {
  name = "${local.name_prefix}-config-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Principal = {
          Service = "config.amazonaws.com"
        }
        Action = "sts:AssumeRole"
      }
    ]
  })

  tags = merge(var.tags, {
    Name = "${local.name_prefix}-config-role"
  })
}

resource "aws_iam_role_policy_attachment" "config_managed" {
  role       = aws_iam_role.config.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWS_ConfigRole"
}

resource "aws_iam_role_policy" "config_s3_delivery" {
  name = "${local.name_prefix}-config-s3-delivery"
  role = aws_iam_role.config.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Sid      = "AllowGetBucketAcl"
        Effect   = "Allow"
        Action   = "s3:GetBucketAcl"
        Resource = aws_s3_bucket.config_recordings.arn
      },
      {
        Sid      = "AllowPutObject"
        Effect   = "Allow"
        Action   = "s3:PutObject"
        Resource = "${aws_s3_bucket.config_recordings.arn}/AWSLogs/${data.aws_caller_identity.current.account_id}/Config/*"
        Condition = {
          StringEquals = {
            "s3:x-amz-acl" = "bucket-owner-full-control"
          }
        }
      }
    ]
  })
}

# --------------------------------------------------------------------------- #
# AWS Config Recorder & Delivery Channel
# --------------------------------------------------------------------------- #

resource "aws_config_configuration_recorder" "main" {
  name     = var.configuration_recorder_name
  role_arn = aws_iam_role.config.arn

  recording_group {
    all_supported                 = true
    include_global_resource_types = true
  }
}

resource "aws_config_delivery_channel" "main" {
  name           = var.delivery_channel_name
  s3_bucket_name = aws_s3_bucket.config_recordings.id

  snapshot_delivery_properties {
    delivery_frequency = "Six_Hours"
  }

  depends_on = [aws_config_configuration_recorder.main]
}

resource "aws_config_configuration_recorder_status" "main" {
  name       = aws_config_configuration_recorder.main.name
  is_enabled = true

  depends_on = [aws_config_delivery_channel.main]
}

# --------------------------------------------------------------------------- #
# Managed Config Rules
# --------------------------------------------------------------------------- #

resource "aws_config_config_rule" "encrypted_volumes" {
  name = "${local.name_prefix}-encrypted-volumes"

  source {
    owner             = "AWS"
    source_identifier = "ENCRYPTED_VOLUMES"
  }

  tags = merge(var.tags, {
    Name = "${local.name_prefix}-encrypted-volumes"
  })

  depends_on = [aws_config_configuration_recorder_status.main]
}

resource "aws_config_config_rule" "rds_storage_encrypted" {
  name = "${local.name_prefix}-rds-storage-encrypted"

  source {
    owner             = "AWS"
    source_identifier = "RDS_STORAGE_ENCRYPTED"
  }

  tags = merge(var.tags, {
    Name = "${local.name_prefix}-rds-storage-encrypted"
  })

  depends_on = [aws_config_configuration_recorder_status.main]
}

resource "aws_config_config_rule" "s3_encryption" {
  name = "${local.name_prefix}-s3-bucket-server-side-encryption-enabled"

  source {
    owner             = "AWS"
    source_identifier = "S3_BUCKET_SERVER_SIDE_ENCRYPTION_ENABLED"
  }

  tags = merge(var.tags, {
    Name = "${local.name_prefix}-s3-bucket-server-side-encryption-enabled"
  })

  depends_on = [aws_config_configuration_recorder_status.main]
}

resource "aws_config_config_rule" "s3_public_read" {
  name = "${local.name_prefix}-s3-bucket-public-read-prohibited"

  source {
    owner             = "AWS"
    source_identifier = "S3_BUCKET_PUBLIC_READ_PROHIBITED"
  }

  tags = merge(var.tags, {
    Name = "${local.name_prefix}-s3-bucket-public-read-prohibited"
  })

  depends_on = [aws_config_configuration_recorder_status.main]
}

resource "aws_config_config_rule" "s3_public_write" {
  name = "${local.name_prefix}-s3-bucket-public-write-prohibited"

  source {
    owner             = "AWS"
    source_identifier = "S3_BUCKET_PUBLIC_WRITE_PROHIBITED"
  }

  tags = merge(var.tags, {
    Name = "${local.name_prefix}-s3-bucket-public-write-prohibited"
  })

  depends_on = [aws_config_configuration_recorder_status.main]
}

resource "aws_config_config_rule" "rds_public_access" {
  name = "${local.name_prefix}-rds-instance-public-access-check"

  source {
    owner             = "AWS"
    source_identifier = "RDS_INSTANCE_PUBLIC_ACCESS_CHECK"
  }

  tags = merge(var.tags, {
    Name = "${local.name_prefix}-rds-instance-public-access-check"
  })

  depends_on = [aws_config_configuration_recorder_status.main]
}

resource "aws_config_config_rule" "restricted_ssh" {
  name = "${local.name_prefix}-restricted-ssh"

  source {
    owner             = "AWS"
    source_identifier = "INCOMING_SSH_DISABLED"
  }

  tags = merge(var.tags, {
    Name = "${local.name_prefix}-restricted-ssh"
  })

  depends_on = [aws_config_configuration_recorder_status.main]
}

resource "aws_config_config_rule" "iam_root_access_key" {
  name = "${local.name_prefix}-iam-root-access-key-check"

  source {
    owner             = "AWS"
    source_identifier = "IAM_ROOT_ACCESS_KEY_CHECK"
  }

  tags = merge(var.tags, {
    Name = "${local.name_prefix}-iam-root-access-key-check"
  })

  depends_on = [aws_config_configuration_recorder_status.main]
}

resource "aws_config_config_rule" "mfa_iam_console" {
  name = "${local.name_prefix}-mfa-enabled-for-iam-console-access"

  source {
    owner             = "AWS"
    source_identifier = "MFA_ENABLED_FOR_IAM_CONSOLE_ACCESS"
  }

  tags = merge(var.tags, {
    Name = "${local.name_prefix}-mfa-enabled-for-iam-console-access"
  })

  depends_on = [aws_config_configuration_recorder_status.main]
}

resource "aws_config_config_rule" "cloudtrail_enabled" {
  name = "${local.name_prefix}-cloud-trail-enabled"

  source {
    owner             = "AWS"
    source_identifier = "CLOUD_TRAIL_ENABLED"
  }

  tags = merge(var.tags, {
    Name = "${local.name_prefix}-cloud-trail-enabled"
  })

  depends_on = [aws_config_configuration_recorder_status.main]
}

resource "aws_config_config_rule" "multi_region_cloudtrail" {
  name = "${local.name_prefix}-cloudtrail-enabled"

  source {
    owner             = "AWS"
    source_identifier = "MULTI_REGION_CLOUD_TRAIL_ENABLED"
  }

  tags = merge(var.tags, {
    Name = "${local.name_prefix}-cloudtrail-enabled"
  })

  depends_on = [aws_config_configuration_recorder_status.main]
}

resource "aws_config_config_rule" "iam_password_policy" {
  name = "${local.name_prefix}-iam-password-policy"

  source {
    owner             = "AWS"
    source_identifier = "IAM_PASSWORD_POLICY"
  }

  tags = merge(var.tags, {
    Name = "${local.name_prefix}-iam-password-policy"
  })

  depends_on = [aws_config_configuration_recorder_status.main]
}

resource "aws_config_config_rule" "vpc_flow_logs" {
  name = "${local.name_prefix}-vpc-flow-logs-enabled"

  source {
    owner             = "AWS"
    source_identifier = "VPC_FLOW_LOGS_ENABLED"
  }

  tags = merge(var.tags, {
    Name = "${local.name_prefix}-vpc-flow-logs-enabled"
  })

  depends_on = [aws_config_configuration_recorder_status.main]
}

resource "aws_config_config_rule" "guardduty_enabled" {
  name = "${local.name_prefix}-guardduty-enabled-centralized"

  source {
    owner             = "AWS"
    source_identifier = "GUARDDUTY_ENABLED_CENTRALIZED"
  }

  tags = merge(var.tags, {
    Name = "${local.name_prefix}-guardduty-enabled-centralized"
  })

  depends_on = [aws_config_configuration_recorder_status.main]
}

resource "aws_config_config_rule" "rds_multi_az" {
  count = var.environment == "prod" ? 1 : 0

  name = "${local.name_prefix}-rds-multi-az-support"

  source {
    owner             = "AWS"
    source_identifier = "RDS_MULTI_AZ_SUPPORT"
  }

  tags = merge(var.tags, {
    Name = "${local.name_prefix}-rds-multi-az-support"
  })

  depends_on = [aws_config_configuration_recorder_status.main]
}

resource "aws_config_config_rule" "ecs_task_log_config" {
  name = "${local.name_prefix}-ecs-task-definition-log-configuration"

  source {
    owner             = "AWS"
    source_identifier = "ECS_TASK_DEFINITION_LOG_CONFIGURATION"
  }

  tags = merge(var.tags, {
    Name = "${local.name_prefix}-ecs-task-definition-log-configuration"
  })

  depends_on = [aws_config_configuration_recorder_status.main]
}

resource "aws_config_config_rule" "secrets_rotation" {
  name = "${local.name_prefix}-secretsmanager-scheduled-rotation-success-check"

  source {
    owner             = "AWS"
    source_identifier = "SECRETSMANAGER_SCHEDULED_ROTATION_SUCCESS_CHECK"
  }

  tags = merge(var.tags, {
    Name = "${local.name_prefix}-secretsmanager-scheduled-rotation-success-check"
  })

  depends_on = [aws_config_configuration_recorder_status.main]
}

resource "aws_config_config_rule" "kms_cmk_deletion" {
  name = "${local.name_prefix}-kms-cmk-not-scheduled-for-deletion"

  source {
    owner             = "AWS"
    source_identifier = "KMS_CMK_NOT_SCHEDULED_FOR_DELETION"
  }

  tags = merge(var.tags, {
    Name = "${local.name_prefix}-kms-cmk-not-scheduled-for-deletion"
  })

  depends_on = [aws_config_configuration_recorder_status.main]
}

resource "aws_config_config_rule" "acm_certificate_expiration" {
  name = "${local.name_prefix}-acm-certificate-expiration-check"

  source {
    owner             = "AWS"
    source_identifier = "ACM_CERTIFICATE_EXPIRATION_CHECK"
  }

  input_parameters = jsonencode({
    daysToExpiration = "30"
  })

  tags = merge(var.tags, {
    Name = "${local.name_prefix}-acm-certificate-expiration-check"
  })

  depends_on = [aws_config_configuration_recorder_status.main]
}
