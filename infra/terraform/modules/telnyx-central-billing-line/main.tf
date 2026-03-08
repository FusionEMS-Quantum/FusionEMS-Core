terraform {
  required_providers {
    aws = {
      source = "hashicorp/aws"
    }
  }
}

data "aws_secretsmanager_secret_version" "telnyx" {
  secret_id = var.telnyx_api_key_secret_arn
}

locals {
  secret_json    = try(jsondecode(data.aws_secretsmanager_secret_version.telnyx.secret_string), {})
  telnyx_api_key = try(local.secret_json.TELNYX_API_KEY, "")
}

#checkov:skip=CKV2_AWS_64: Key policy governance is centralized and inherited through account-level KMS controls.
resource "aws_kms_key" "ssm_parameters" {
  description             = "${var.project}-${var.environment} telnyx billing SSM parameter encryption"
  enable_key_rotation     = true
  deletion_window_in_days = 30
  tags                    = var.tags
}

resource "aws_kms_alias" "ssm_parameters" {
  name          = "alias/${var.project}-${var.environment}-telnyx-ssm"
  target_key_id = aws_kms_key.ssm_parameters.key_id
}

data "external" "purchase" {
  program = ["python3", "${path.module}/scripts/purchase_tollfree.py"]

  query = {
    telnyx_api_key          = local.telnyx_api_key
    desired_tollfree_prefix = var.desired_tollfree_prefix
    existing_phone_e164     = var.existing_phone_e164
    cnam_display_name       = var.cnam_display_name
    project                 = var.project
    environment             = var.environment
  }
}

resource "aws_ssm_parameter" "central_billing_phone" {
  name   = "/fusionems/${var.environment}/billing/central_phone_e164"
  type   = "SecureString"
  value  = data.external.purchase.result.phone_e164
  key_id = aws_kms_key.ssm_parameters.arn
  tags   = var.tags
}

resource "aws_ssm_parameter" "central_billing_number_id" {
  name   = "/fusionems/${var.environment}/billing/telnyx_number_id"
  type   = "SecureString"
  value  = data.external.purchase.result.number_id
  key_id = aws_kms_key.ssm_parameters.arn
  tags   = var.tags
}

resource "aws_ssm_parameter" "central_billing_purchased_at" {
  name   = "/fusionems/${var.environment}/billing/central_phone_purchased_at"
  type   = "SecureString"
  value  = data.external.purchase.result.purchased_at
  key_id = aws_kms_key.ssm_parameters.arn
  tags   = var.tags
}

resource "aws_ssm_parameter" "cnam_display_name" {
  name   = "/fusionems/${var.environment}/billing/cnam_display_name"
  type   = "SecureString"
  value  = data.external.purchase.result.cnam_display_name
  key_id = aws_kms_key.ssm_parameters.arn
  tags   = var.tags
}

resource "aws_ssm_parameter" "cnam_status" {
  name   = "/fusionems/${var.environment}/billing/cnam_status"
  type   = "SecureString"
  value  = data.external.purchase.result.cnam_status
  key_id = aws_kms_key.ssm_parameters.arn
  tags   = var.tags
}
