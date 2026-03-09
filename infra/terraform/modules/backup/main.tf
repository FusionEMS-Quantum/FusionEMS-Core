###############################################################################
# FusionEMS – AWS Backup Module
# Centralized backup vault, policies, and cross-region DR copy
###############################################################################

data "aws_caller_identity" "current" {}
data "aws_region" "current" {}

locals {
  name_prefix = "${var.project}-${var.environment}"
  is_prod     = var.environment == "prod"
  enable_dr   = var.dr_vault_arn != ""
}

# ─── KMS Key ────────────────────────────────────────────────────────────────

resource "aws_kms_key" "backup" {
  description             = "KMS key for ${local.name_prefix} backup vault encryption"
  deletion_window_in_days = 30
  enable_key_rotation     = true

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Sid       = "AllowAccountRoot"
        Effect    = "Allow"
        Principal = { AWS = "arn:aws:iam::${data.aws_caller_identity.current.account_id}:root" }
        Action    = "kms:*"
        Resource  = "*"
      },
      {
        Sid       = "AllowBackupService"
        Effect    = "Allow"
        Principal = { Service = "backup.amazonaws.com" }
        Action = [
          "kms:Decrypt",
          "kms:Encrypt",
          "kms:GenerateDataKey",
          "kms:GenerateDataKeyWithoutPlaintext",
          "kms:ReEncryptFrom",
          "kms:ReEncryptTo",
          "kms:DescribeKey",
          "kms:CreateGrant",
        ]
        Resource = "*"
      },
    ]
  })

  tags = merge(var.tags, { Name = "${local.name_prefix}-backup-key" })
}

resource "aws_kms_alias" "backup" {
  name          = "alias/${local.name_prefix}-backup"
  target_key_id = aws_kms_key.backup.key_id
}

# ─── Backup Vault ───────────────────────────────────────────────────────────

resource "aws_backup_vault" "main" {
  name        = "${local.name_prefix}-vault"
  kms_key_arn = aws_kms_key.backup.arn
  tags        = merge(var.tags, { Name = "${local.name_prefix}-vault" })
}

resource "aws_backup_vault_lock_configuration" "main" {
  count = local.is_prod ? 1 : 0

  backup_vault_name   = aws_backup_vault.main.name
  changeable_for_days = 3
  max_retention_days  = 2555
  min_retention_days  = 7
}

resource "aws_backup_vault_notifications" "main" {
  backup_vault_name   = aws_backup_vault.main.name
  sns_topic_arn       = var.alert_topic_arn
  backup_vault_events = ["BACKUP_JOB_FAILED", "RESTORE_JOB_FAILED", "COPY_JOB_FAILED"]
}

resource "aws_backup_vault_policy" "main" {
  backup_vault_name = aws_backup_vault.main.name

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Sid       = "DenyDeleteRecoveryPointsExceptRootAndBackupRole"
        Effect    = "Deny"
        Principal = "*"
        Action = [
          "backup:DeleteRecoveryPoint",
          "backup:UpdateRecoveryPointLifecycle",
        ]
        Resource = "*"
        Condition = {
          ArnNotLike = {
            "aws:PrincipalArn" = [
              "arn:aws:iam::${data.aws_caller_identity.current.account_id}:root",
              aws_iam_role.backup.arn,
            ]
          }
        }
      },
    ]
  })
}

# ─── IAM Role ───────────────────────────────────────────────────────────────

resource "aws_iam_role" "backup" {
  name = "${local.name_prefix}-backup-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect    = "Allow"
        Principal = { Service = "backup.amazonaws.com" }
        Action    = "sts:AssumeRole"
      },
    ]
  })

  tags = merge(var.tags, { Name = "${local.name_prefix}-backup-role" })
}

resource "aws_iam_role_policy_attachment" "backup" {
  role       = aws_iam_role.backup.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWSBackupServiceRolePolicyForBackup"
}

resource "aws_iam_role_policy_attachment" "restore" {
  role       = aws_iam_role.backup.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWSBackupServiceRolePolicyForRestores"
}

# ─── Backup Plan ────────────────────────────────────────────────────────────

resource "aws_backup_plan" "main" {
  name = "${local.name_prefix}-daily"

  # Rule 1: Daily backup – 35 day retention
  rule {
    rule_name         = "daily-backup"
    target_vault_name = aws_backup_vault.main.name
    schedule          = "cron(0 3 * * ? *)"
    start_window      = 60
    completion_window = 180

    lifecycle {
      delete_after = 35
    }
  }

  # Rule 2: Weekly backup – 1 year retention + optional DR copy
  rule {
    rule_name         = "weekly-backup"
    target_vault_name = aws_backup_vault.main.name
    schedule          = "cron(0 4 ? * SUN *)"
    start_window      = 120
    completion_window = 360

    lifecycle {
      delete_after = 365
    }

    dynamic "copy_action" {
      for_each = local.is_prod && local.enable_dr ? [1] : []
      content {
        destination_vault_arn = var.dr_vault_arn
        lifecycle {
          delete_after = 90
        }
      }
    }
  }

  # Rule 3: Monthly backup (prod only) – 7 year retention
  dynamic "rule" {
    for_each = local.is_prod ? [1] : []
    content {
      rule_name         = "monthly-backup"
      target_vault_name = aws_backup_vault.main.name
      schedule          = "cron(0 5 1 * ? *)"
      start_window      = 120
      completion_window = 360

      lifecycle {
        cold_storage_after = 90
        delete_after       = 2555
      }
    }
  }

  advanced_backup_setting {
    backup_options = {
      WindowsVSS = "enabled"
    }
    resource_type = "EC2"
  }

  tags = merge(var.tags, { Name = "${local.name_prefix}-backup-plan" })
}

# ─── Backup Selection ───────────────────────────────────────────────────────

resource "aws_backup_selection" "tag_based" {
  name         = "${local.name_prefix}-selection"
  plan_id      = aws_backup_plan.main.id
  iam_role_arn = aws_iam_role.backup.arn

  selection_tag {
    type  = "STRINGEQUALS"
    key   = "Project"
    value = var.project
  }

  dynamic "selection_tag" {
    for_each = var.environment != "" ? [1] : []
    content {
      type  = "STRINGEQUALS"
      key   = "Environment"
      value = var.environment
    }
  }

  resources = var.backup_resource_arns
}
