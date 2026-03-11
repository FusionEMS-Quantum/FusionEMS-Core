# ─── COMPLIANCE & SECURITY SUBSYSTEM (Domination Level) ───────────
# Deploys end-to-end continuous compliance architecture

# 1. KMS CMK Module (Underpins encrypting ALL data correctly)
module "prod_kms" {
  source      = "../../modules/kms"
  environment = var.environment
  alias_name  = "fusionems-${var.environment}-primary-cmk"
  description = "FIPS-compliant primary CMK for Production DBs and Volumes"
}

# 2. Audit Evidence S3 Bucket & Audit Manager configuration
module "prod_audit_manager" {
  source                       = "../../modules/audit_manager"
  environment                  = var.environment
  report_destination_s3_bucket = "fusionems-${var.environment}-audit-evidence-${data.aws_caller_identity.current.account_id}"
}

# 3. CloudTrail Implementation ensuring immutability 
module "prod_cloudtrail" {
  source         = "../../modules/audit"
  environment    = var.environment
  s3_bucket_name = "fusionems-${var.environment}-cloudtrail-logs-${data.aws_caller_identity.current.account_id}"
  kms_key_arn    = module.prod_kms.key_arn
  multi_region   = true
}

# 4. Security Subsystem (GuardDuty, Inspector, Config, Macie)
module "prod_security_subsystem" {
  source           = "../../modules/security"
  environment      = var.environment
  enable_macie     = true
  enable_inspector = true
}

# 5. Backup and Restore / Vault Lock immutability
module "prod_backups" {
  source          = "../../modules/aws_backup"
  environment     = var.environment
  project         = var.project
  alert_topic_arn = module.observability.alert_topic_arn
}

# 6. Global Web Application Firewall (Block SQLi, OWASP configs)
module "prod_waf" {
  source      = "../../modules/network"
  environment = var.environment
  vpc_id      = module.networking.vpc_id                        # Assumes a networking module output
  subnet_ids  = module.networking.public_subnet_ids             # Assumes networking module public subnets
}
