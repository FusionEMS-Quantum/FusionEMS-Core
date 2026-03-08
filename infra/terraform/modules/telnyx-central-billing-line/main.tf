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
  secret_json = try(jsondecode(data.aws_secretsmanager_secret_version.telnyx.secret_string), {})
  telnyx_api_key = try(local.secret_json.TELNYX_API_KEY, "")
}

data "external" "purchase" {
  program = ["python3", "${path.module}/scripts/purchase_tollfree.py"]

  query = {
    telnyx_api_key          = local.telnyx_api_key
    desired_tollfree_prefix = var.desired_tollfree_prefix
    existing_phone_e164     = var.existing_phone_e164
    project                 = var.project
    environment             = var.environment
  }
}

resource "aws_ssm_parameter" "central_billing_phone" {
  name  = "/fusionems/${var.environment}/billing/central_phone_e164"
  type  = "String"
  value = data.external.purchase.result.phone_e164
  tags  = var.tags
}

resource "aws_ssm_parameter" "central_billing_number_id" {
  name  = "/fusionems/${var.environment}/billing/telnyx_number_id"
  type  = "String"
  value = data.external.purchase.result.number_id
  tags  = var.tags
}

resource "aws_ssm_parameter" "central_billing_purchased_at" {
  name  = "/fusionems/${var.environment}/billing/central_phone_purchased_at"
  type  = "String"
  value = data.external.purchase.result.purchased_at
  tags  = var.tags
}
