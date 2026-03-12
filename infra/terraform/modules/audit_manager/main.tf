# Ensure an S3 bucket is configured for audit evidence
resource "aws_s3_bucket" "audit_evidence" {
  bucket        = var.report_destination_s3_bucket
  force_destroy = false
}

resource "aws_s3_bucket_versioning" "audit_evidence" {
  bucket = aws_s3_bucket.audit_evidence.id
  versioning_configuration {
    status = "Enabled"
  }
}

resource "aws_s3_bucket_public_access_block" "audit_evidence" {
  bucket                  = aws_s3_bucket.audit_evidence.id
  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

# AWS Audit Manager Framework Assessments
# Data sources include CloudTrail, AWS Config, and Security Hub

# Framework: SOC 2 Type II
resource "aws_auditmanager_assessment" "soc2" {
  name          = "${var.environment}-soc2-assessment"
  description   = "Automated evidence collection for SOC 2 Type II readiness"
  framework_id  = "arn:aws:auditmanager::aws:framework/SOC-2-Type-II" 
  
  assessment_reports_destination {
    destination_type = "S3"
    destination      = "s3://${aws_s3_bucket.audit_evidence.id}"
  }

  roles {
    role_arn  = aws_iam_role.audit_manager_role.arn
    role_type = "PROCESS_OWNER"
  }
}

# Framework: HIPAA Security Rule
resource "aws_auditmanager_assessment" "hipaa" {
  name          = "${var.environment}-hipaa-assessment"
  description   = "Automated evidence collection for HIPAA compliance"
  framework_id  = "arn:aws:auditmanager::aws:framework/HIPAA-Security-Rule-2003"
  
  assessment_reports_destination {
    destination_type = "S3"
    destination      = "s3://${aws_s3_bucket.audit_evidence.id}"
  }

  roles {
    role_arn  = aws_iam_role.audit_manager_role.arn
    role_type = "PROCESS_OWNER"
  }
}

resource "aws_iam_role" "audit_manager_role" {
  name = "${var.environment}-audit-manager-role"
  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = "sts:AssumeRole"
        Effect = "Allow"
        Principal = {
          Service = "auditmanager.amazonaws.com"
        }
      }
    ]
  })
}

resource "aws_iam_role_policy_attachment" "audit_manager_policy" {
  role       = aws_iam_role.audit_manager_role.name
  policy_arn = "arn:aws:iam::aws:policy/AWSAuditManagerAdministratorAccess"
}
