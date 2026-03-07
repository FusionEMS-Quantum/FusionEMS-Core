###############################################################################
# Governance & Tenant Isolation Terraform Module
# Enforces security boundaries for multi-tenant trust architecture
###############################################################################

terraform {
  required_version = ">= 1.6"

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = ">= 5.0"
    }
  }
}

locals {
  name_prefix = "${var.project}-${var.environment}"

  common_tags = merge(
    {
      Project     = var.project
      Environment = var.environment
      ManagedBy   = "terraform"
      Module      = "governance"
    },
    var.tags,
  )
}

# =============================================================================
# KMS – Governance Audit Log Encryption
# Separate key for audit data to enforce independent key rotation
# =============================================================================

resource "aws_kms_key" "governance_audit" {
  description             = "${local.name_prefix}-governance-audit"
  enable_key_rotation     = true
  deletion_window_in_days = 30

  tags = merge(local.common_tags, {
    Name    = "${local.name_prefix}-governance-audit-key"
    Purpose = "audit-log-encryption"
  })
}

resource "aws_kms_alias" "governance_audit" {
  name          = "alias/${local.name_prefix}-governance-audit"
  target_key_id = aws_kms_key.governance_audit.key_id
}

# =============================================================================
# S3 – Audit Export Bucket (immutable / WORM)
# =============================================================================

resource "aws_s3_bucket" "audit_exports" {
  bucket = "${local.name_prefix}-audit-exports"

  tags = merge(local.common_tags, {
    Name    = "${local.name_prefix}-audit-exports"
    Purpose = "immutable-audit-trail"
  })
}

resource "aws_s3_bucket_versioning" "audit_exports" {
  bucket = aws_s3_bucket.audit_exports.id
  versioning_configuration {
    status = "Enabled"
  }
}

resource "aws_s3_bucket_server_side_encryption_configuration" "audit_exports" {
  bucket = aws_s3_bucket.audit_exports.id

  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm     = "aws:kms"
      kms_master_key_id = aws_kms_key.governance_audit.arn
    }
    bucket_key_enabled = true
  }
}

resource "aws_s3_bucket_public_access_block" "audit_exports" {
  bucket = aws_s3_bucket.audit_exports.id

  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

resource "aws_s3_bucket_object_lock_configuration" "audit_exports" {
  count  = var.enable_object_lock ? 1 : 0
  bucket = aws_s3_bucket.audit_exports.id

  rule {
    default_retention {
      mode = "GOVERNANCE"
      days = var.audit_retention_days
    }
  }
}

resource "aws_s3_bucket_lifecycle_configuration" "audit_exports" {
  bucket = aws_s3_bucket.audit_exports.id

  rule {
    id     = "archive-old-audits"
    status = "Enabled"

    transition {
      days          = 90
      storage_class = "GLACIER"
    }
  }
}

# =============================================================================
# S3 – PHI Export Staging Bucket
# =============================================================================

resource "aws_s3_bucket" "phi_exports" {
  bucket = "${local.name_prefix}-phi-exports"

  tags = merge(local.common_tags, {
    Name    = "${local.name_prefix}-phi-exports"
    Purpose = "phi-export-staging"
    PHI     = "true"
  })
}

resource "aws_s3_bucket_versioning" "phi_exports" {
  bucket = aws_s3_bucket.phi_exports.id
  versioning_configuration {
    status = "Enabled"
  }
}

resource "aws_s3_bucket_server_side_encryption_configuration" "phi_exports" {
  bucket = aws_s3_bucket.phi_exports.id

  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm     = "aws:kms"
      kms_master_key_id = aws_kms_key.governance_audit.arn
    }
    bucket_key_enabled = true
  }
}

resource "aws_s3_bucket_public_access_block" "phi_exports" {
  bucket = aws_s3_bucket.phi_exports.id

  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

resource "aws_s3_bucket_lifecycle_configuration" "phi_exports" {
  bucket = aws_s3_bucket.phi_exports.id

  rule {
    id     = "expire-staged-exports"
    status = "Enabled"

    expiration {
      days = var.phi_export_expiry_days
    }
  }
}

# =============================================================================
# IAM – Governance Service Role (least privilege)
# =============================================================================

data "aws_iam_policy_document" "governance_task_assume" {
  statement {
    effect  = "Allow"
    actions = ["sts:AssumeRole"]
    principals {
      type        = "Service"
      identifiers = ["ecs-tasks.amazonaws.com"]
    }
  }
}

resource "aws_iam_role" "governance_task" {
  name               = "${local.name_prefix}-governance-task"
  assume_role_policy = data.aws_iam_policy_document.governance_task_assume.json
  tags               = merge(local.common_tags, { Name = "${local.name_prefix}-governance-task" })
}

data "aws_iam_policy_document" "governance_task_permissions" {
  # Audit export bucket access
  statement {
    sid    = "AuditExportBucket"
    effect = "Allow"
    actions = [
      "s3:PutObject",
      "s3:GetObject",
      "s3:ListBucket",
    ]
    resources = [
      aws_s3_bucket.audit_exports.arn,
      "${aws_s3_bucket.audit_exports.arn}/*",
    ]
  }

  # PHI export bucket access
  statement {
    sid    = "PHIExportBucket"
    effect = "Allow"
    actions = [
      "s3:PutObject",
      "s3:GetObject",
      "s3:ListBucket",
    ]
    resources = [
      aws_s3_bucket.phi_exports.arn,
      "${aws_s3_bucket.phi_exports.arn}/*",
    ]
  }

  # KMS decrypt for audit data
  statement {
    sid    = "GovernanceKMS"
    effect = "Allow"
    actions = [
      "kms:Decrypt",
      "kms:GenerateDataKey",
    ]
    resources = [aws_kms_key.governance_audit.arn]
  }

  # Secrets Manager read access for governance configs
  statement {
    sid    = "GovernanceSecrets"
    effect = "Allow"
    actions = [
      "secretsmanager:GetSecretValue",
    ]
    resources = [
      "arn:aws:secretsmanager:*:*:secret:${var.project}/${var.environment}/governance-*",
    ]
  }
}

resource "aws_iam_role_policy" "governance_task" {
  name   = "${local.name_prefix}-governance-task-policy"
  role   = aws_iam_role.governance_task.id
  policy = data.aws_iam_policy_document.governance_task_permissions.json
}

# =============================================================================
# CloudWatch – Governance Audit Log Group
# =============================================================================

resource "aws_cloudwatch_log_group" "governance_audit" {
  name              = "/ecs/${local.name_prefix}/governance-audit"
  retention_in_days = var.log_retention_days
  kms_key_id        = aws_kms_key.governance_audit.arn

  tags = merge(local.common_tags, {
    Name = "${local.name_prefix}-governance-audit-logs"
  })
}
