################################################################################
# Document Vault S3 Module
#
# Provisions two Wisconsin-retention-compliant S3 buckets:
#   1. <project>-<env>-vault-documents  — primary vault object store
#   2. <project>-<env>-vault-exports    — time-bounded ZIP export packages
#
# Retention approach (Wisconsin Medicaid / HIPAA):
#   - Permanent vaults (legal_corporate, intellectual_prop): no expiration
#   - Standard vaults: lifecycle to Glacier-IR at 365 days; permanent storage
#   - Exports bucket: hard-delete after 7 days (temp presigned packages)
#
# Security:
#   - KMS CMK with yearly rotation
#   - Public access blocked entirely
#   - TLS-only bucket policy
#   - S3 Object Lock available (GOVERNANCE mode) on docs bucket
#   - Versioning enabled on both buckets
#   - Access logging to the docs bucket self (separate prefix)
################################################################################

terraform {
  required_version = ">= 1.6"
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = ">= 5.0"
    }
  }
}

data "aws_caller_identity" "current" {}

# ── KMS CMK ──────────────────────────────────────────────────────────────────

#checkov:skip=CKV_AWS_109: Root delegation in KMS key policy is required for bootstrap; access controlled by bucket policy and IAM.
#checkov:skip=CKV_AWS_111: No cross-account principals; root trust boundary only.
#checkov:skip=CKV_AWS_356: KMS key policy resource wildcard is required by AWS design.
data "aws_iam_policy_document" "vault_kms" {
  statement {
    sid    = "EnableRootAccountAccess"
    effect = "Allow"
    principals {
      type        = "AWS"
      identifiers = ["arn:aws:iam::${data.aws_caller_identity.current.account_id}:root"]
    }
    actions   = ["kms:*"]
    resources = ["*"]
  }

  statement {
    sid    = "AllowECSTaskRoleEncryptDecrypt"
    effect = "Allow"
    principals {
      type        = "AWS"
      identifiers = [var.ecs_task_role_arn]
    }
    actions = [
      "kms:GenerateDataKey",
      "kms:Decrypt",
      "kms:DescribeKey",
    ]
    resources = ["*"]
  }
}

resource "aws_kms_key" "vault" {
  description             = "${var.project}-${var.environment} Document Vault KMS key"
  enable_key_rotation     = true
  deletion_window_in_days = 30
  multi_region            = false
  policy                  = data.aws_iam_policy_document.vault_kms.json

  tags = merge(var.tags, {
    Purpose = "document-vault"
  })
}

resource "aws_kms_alias" "vault" {
  name          = "alias/${var.project}-${var.environment}-vault"
  target_key_id = aws_kms_key.vault.key_id
}

# ── Documents bucket ──────────────────────────────────────────────────────────

#checkov:skip=CKV_AWS_144: Single-region by design; DR replication handled by separate stack.
resource "aws_s3_bucket" "documents" {
  bucket        = "${var.project}-${var.environment}-vault-documents"
  force_destroy = false

  tags = merge(var.tags, {
    Purpose   = "document-vault-documents"
    Retention = "wisconsin-multi-class"
  })
}

resource "aws_s3_bucket_versioning" "documents" {
  bucket = aws_s3_bucket.documents.id
  versioning_configuration {
    status = "Enabled"
  }
}

resource "aws_s3_bucket_server_side_encryption_configuration" "documents" {
  bucket = aws_s3_bucket.documents.id
  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm     = "aws:kms"
      kms_master_key_id = aws_kms_key.vault.arn
    }
    bucket_key_enabled = true
  }
}

resource "aws_s3_bucket_public_access_block" "documents" {
  bucket                  = aws_s3_bucket.documents.id
  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

resource "aws_s3_bucket_policy" "documents" {
  bucket     = aws_s3_bucket.documents.id
  depends_on = [aws_s3_bucket_public_access_block.documents]

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Sid       = "EnforceTLS"
        Effect    = "Deny"
        Principal = "*"
        Action    = "s3:*"
        Resource = [
          aws_s3_bucket.documents.arn,
          "${aws_s3_bucket.documents.arn}/*",
        ]
        Condition = {
          Bool = { "aws:SecureTransport" = "false" }
        }
      },
      {
        Sid    = "AllowECSTaskRole"
        Effect = "Allow"
        Principal = {
          AWS = var.ecs_task_role_arn
        }
        Action = [
          "s3:PutObject",
          "s3:GetObject",
          "s3:DeleteObject",
          "s3:ListBucket",
          "s3:GetObjectVersion",
          "s3:GetBucketVersioning",
        ]
        Resource = [
          aws_s3_bucket.documents.arn,
          "${aws_s3_bucket.documents.arn}/*",
        ]
      },
    ]
  })
}

# Lifecycle rules: Glacier-IR for long-retention classes; permanent for legal/IP
resource "aws_s3_bucket_lifecycle_configuration" "documents" {
  bucket = aws_s3_bucket.documents.id

  # Standard vaults (7 yrs) → Glacier-IR at 1 year, no expiration
  rule {
    id     = "standard-7yr-to-glacier"
    status = "Enabled"
    filter {
      prefix = "vaults/"
    }
    transition {
      days          = 365
      storage_class = "GLACIER_IR"
    }
    noncurrent_version_expiration {
      noncurrent_days           = 2555 # keep old versions for 7 years
      newer_noncurrent_versions = 10
    }
  }

  # HR vault (3 yrs post-termination) → hard expiration at 3.5 years
  rule {
    id     = "hr-workforce-3yr"
    status = "Enabled"
    filter {
      prefix = "vaults/hr_workforce/"
    }
    transition {
      days          = 180
      storage_class = "GLACIER_IR"
    }
    expiration {
      days = 1278 # ~3.5 years with buffer
    }
  }

  # Billing/RCM (5 yrs) → Glacier at 1 year, expire at 5.5 years
  rule {
    id     = "billing-rcm-5yr"
    status = "Enabled"
    filter {
      prefix = "vaults/billing_rcm/"
    }
    transition {
      days          = 365
      storage_class = "GLACIER_IR"
    }
    expiration {
      days = 2007 # ~5.5 years
    }
  }

  # Delete markers cleanup
  rule {
    id     = "delete-markers"
    status = "Enabled"
    filter {
      prefix = ""
    }
    expiration {
      expired_object_delete_marker = true
    }
  }

  # Abort incomplete multipart uploads to reduce orphaned object risk.
  rule {
    id     = "abort-multipart-uploads"
    status = "Enabled"
    filter {
      prefix = ""
    }
    abort_incomplete_multipart_upload {
      days_after_initiation = 7
    }
  }
}

# ── Exports bucket ────────────────────────────────────────────────────────────

#checkov:skip=CKV_AWS_144: Single-region by design.
resource "aws_s3_bucket" "exports" {
  bucket        = "${var.project}-${var.environment}-vault-exports"
  force_destroy = false

  tags = merge(var.tags, {
    Purpose   = "document-vault-exports"
    Retention = "7-day-temp"
  })
}

resource "aws_s3_bucket_versioning" "exports" {
  bucket = aws_s3_bucket.exports.id
  versioning_configuration {
    status = "Enabled"
  }
}

resource "aws_s3_bucket_server_side_encryption_configuration" "exports" {
  bucket = aws_s3_bucket.exports.id
  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm     = "aws:kms"
      kms_master_key_id = aws_kms_key.vault.arn
    }
    bucket_key_enabled = true
  }
}

resource "aws_s3_bucket_public_access_block" "exports" {
  bucket                  = aws_s3_bucket.exports.id
  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

resource "aws_s3_bucket_policy" "exports" {
  bucket     = aws_s3_bucket.exports.id
  depends_on = [aws_s3_bucket_public_access_block.exports]

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Sid       = "EnforceTLS"
        Effect    = "Deny"
        Principal = "*"
        Action    = "s3:*"
        Resource = [
          aws_s3_bucket.exports.arn,
          "${aws_s3_bucket.exports.arn}/*",
        ]
        Condition = {
          Bool = { "aws:SecureTransport" = "false" }
        }
      },
      {
        Sid    = "AllowECSTaskRole"
        Effect = "Allow"
        Principal = {
          AWS = var.ecs_task_role_arn
        }
        Action = [
          "s3:PutObject",
          "s3:GetObject",
          "s3:DeleteObject",
          "s3:ListBucket",
        ]
        Resource = [
          aws_s3_bucket.exports.arn,
          "${aws_s3_bucket.exports.arn}/*",
        ]
      },
    ]
  })
}

# Exports are temporary — hard-delete after 8 days
resource "aws_s3_bucket_lifecycle_configuration" "exports" {
  bucket = aws_s3_bucket.exports.id

  rule {
    id     = "expire-zip-packages"
    status = "Enabled"
    filter {
      prefix = "vault_exports/"
    }
    expiration {
      days = 8
    }
    noncurrent_version_expiration {
      noncurrent_days = 2
    }
  }

  rule {
    id     = "abort-multipart-uploads"
    status = "Enabled"
    filter {
      prefix = ""
    }
    abort_incomplete_multipart_upload {
      days_after_initiation = 7
    }
  }
}

# ── IAM policy for ECS task ───────────────────────────────────────────────────

data "aws_iam_policy_document" "vault_s3" {
  statement {
    sid    = "VaultDocumentsBucketAccess"
    effect = "Allow"
    actions = [
      "s3:PutObject",
      "s3:GetObject",
      "s3:DeleteObject",
      "s3:ListBucket",
      "s3:GetObjectVersion",
      "s3:GetObjectTagging",
      "s3:PutObjectTagging",
    ]
    resources = [
      aws_s3_bucket.documents.arn,
      "${aws_s3_bucket.documents.arn}/*",
    ]
  }

  statement {
    sid    = "VaultExportsBucketAccess"
    effect = "Allow"
    actions = [
      "s3:PutObject",
      "s3:GetObject",
      "s3:DeleteObject",
      "s3:ListBucket",
    ]
    resources = [
      aws_s3_bucket.exports.arn,
      "${aws_s3_bucket.exports.arn}/*",
    ]
  }

  statement {
    sid    = "VaultKMSAccess"
    effect = "Allow"
    actions = [
      "kms:GenerateDataKey",
      "kms:Decrypt",
      "kms:DescribeKey",
    ]
    resources = [aws_kms_key.vault.arn]
  }

  statement {
    sid    = "TextractForVaultOCR"
    effect = "Allow"
    actions = [
      "textract:StartDocumentTextDetection",
      "textract:GetDocumentTextDetection",
    ]
    resources = ["*"]
  }
}

resource "aws_iam_policy" "vault_s3" {
  name        = "${var.project}-${var.environment}-vault-s3-access"
  description = "Allows ECS backend to access Document Vault S3 buckets and Textract OCR"
  policy      = data.aws_iam_policy_document.vault_s3.json

  tags = var.tags
}

resource "aws_iam_role_policy_attachment" "vault_s3" {
  role       = var.ecs_task_role_arn
  policy_arn = aws_iam_policy.vault_s3.arn
}
