data "aws_caller_identity" "current" {}

resource "aws_cloudtrail" "global" {
  name                          = "${var.environment}-cloudtrail"
  s3_bucket_name                = var.s3_bucket_name
  include_global_service_events = true
  is_multi_region_trail         = var.multi_region
  enable_log_file_validation    = true
  kms_key_id                    = var.kms_key_arn

  event_selector {
    read_write_type           = "All"
    include_management_events = true

    data_resource {
      type   = "AWS::S3::Object"
      values = ["arn:aws:s3:::"]
    }
  }

  tags = {
    Environment = var.environment
    Compliance  = "SOC2,HIPAA,ISO27001"
  }
}
