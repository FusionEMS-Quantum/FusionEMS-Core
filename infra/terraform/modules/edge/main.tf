################################################################################
# Edge Module – CloudFront + WAF + Route 53
################################################################################

terraform {
  required_version = ">= 1.6"

  required_providers {
    aws = {
      source                = "hashicorp/aws"
      version               = "~> 5.0"
      configuration_aliases = [aws.us_east_1]
    }
  }
}

locals {
  name_prefix = "${var.project}-${var.environment}"

  common_tags = merge(var.tags, {
    Project     = var.project
    Environment = var.environment
    ManagedBy   = "terraform"
  })

  # AWS-managed origin request policy: AllViewerExceptHostHeader
  all_viewer_except_host_header_policy_id = "b689b0a8-53d0-40ab-baf2-68738e2966ac"
}

data "aws_caller_identity" "current" {}

# ========================= WAF (CLOUDFRONT scope – us-east-1) =================

resource "aws_wafv2_web_acl" "cloudfront" {
  provider = aws.us_east_1

  name        = "${local.name_prefix}-edge-waf"
  scope       = "CLOUDFRONT"
  description = "WAF Web ACL for CloudFront distribution"

  default_action {
    allow {}
  }

  rule {
    name     = "AWSManagedCommon"
    priority = 1

    override_action {
      none {}
    }

    statement {
      managed_rule_group_statement {
        vendor_name = "AWS"
        name        = "AWSManagedRulesCommonRuleSet"
      }
    }

    visibility_config {
      cloudwatch_metrics_enabled = true
      metric_name                = "common"
      sampled_requests_enabled   = true
    }
  }

  rule {
    name     = "AWSManagedKnownBadInputs"
    priority = 2

    override_action {
      none {}
    }

    statement {
      managed_rule_group_statement {
        vendor_name = "AWS"
        name        = "AWSManagedRulesKnownBadInputsRuleSet"
      }
    }

    visibility_config {
      cloudwatch_metrics_enabled = true
      metric_name                = "known-bad-inputs"
      sampled_requests_enabled   = true
    }
  }

  rule {
    name     = "RateLimit"
    priority = 3

    action {
      block {}
    }

    statement {
      rate_based_statement {
        limit              = 2000
        aggregate_key_type = "IP"
      }
    }

    visibility_config {
      cloudwatch_metrics_enabled = true
      metric_name                = "rate-limit"
      sampled_requests_enabled   = true
    }
  }

  rule {
    name     = "AWSManagedSQLi"
    priority = 4

    override_action {
      none {}
    }

    statement {
      managed_rule_group_statement {
        vendor_name = "AWS"
        name        = "AWSManagedRulesSQLiRuleSet"
      }
    }

    visibility_config {
      cloudwatch_metrics_enabled = true
      metric_name                = "sqli"
      sampled_requests_enabled   = true
    }
  }

  visibility_config {
    cloudwatch_metrics_enabled = true
    metric_name                = "${local.name_prefix}-waf"
    sampled_requests_enabled   = true
  }

  tags = local.common_tags
}

# ========================= WAF Logging ========================================

resource "aws_cloudwatch_log_group" "waf" {
  provider = aws.us_east_1

  name              = "aws-waf-logs-${local.name_prefix}-edge"
  retention_in_days = 365

  tags = local.common_tags
}

resource "aws_wafv2_web_acl_logging_configuration" "cloudfront" {
  provider = aws.us_east_1

  log_destination_configs = [aws_cloudwatch_log_group.waf.arn]
  resource_arn            = aws_wafv2_web_acl.cloudfront.arn
}

# ========================= Security Headers ===================================

resource "aws_cloudfront_response_headers_policy" "security" {
  name = "${local.name_prefix}-security-headers"

  security_headers_config {
    strict_transport_security {
      override                   = true
      include_subdomains         = true
      preload                    = true
      access_control_max_age_sec = 63072000
    }

    content_type_options {
      override = true
    }

    frame_options {
      frame_option = "DENY"
      override     = true
    }

    referrer_policy {
      referrer_policy = "strict-origin-when-cross-origin"
      override        = true
    }
  }
}

# ========================= Cache Policies =====================================

resource "aws_cloudfront_cache_policy" "no_cache" {
  name        = "${local.name_prefix}-no-cache"
  min_ttl     = 0
  default_ttl = 0
  max_ttl     = 1

  parameters_in_cache_key_and_forwarded_to_origin {
    enable_accept_encoding_gzip = false

    headers_config {
      header_behavior = "none"
    }

    query_strings_config {
      query_string_behavior = "all"
    }

    cookies_config {
      cookie_behavior = "all"
    }
  }
}

resource "aws_cloudfront_cache_policy" "static" {
  name        = "${local.name_prefix}-static"
  min_ttl     = 0
  default_ttl = 86400
  max_ttl     = 31536000

  parameters_in_cache_key_and_forwarded_to_origin {
    enable_accept_encoding_gzip = true

    headers_config {
      header_behavior = "none"
    }

    query_strings_config {
      query_string_behavior = "none"
    }

    cookies_config {
      cookie_behavior = "none"
    }
  }
}

# ========================= CloudFront Access Logs =============================

resource "aws_s3_bucket" "cloudfront_logs" {
  bucket = "${local.name_prefix}-cloudfront-logs"

  tags = merge(local.common_tags, {
    Name    = "${local.name_prefix}-cloudfront-logs"
    Purpose = "cloudfront-access-logs"
  })
}

resource "aws_s3_bucket_public_access_block" "cloudfront_logs" {
  bucket = aws_s3_bucket.cloudfront_logs.id

  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

resource "aws_s3_bucket_policy" "cloudfront_logs" {
  count  = var.create_cloudfront_log_policy ? 1 : 0
  bucket = aws_s3_bucket.cloudfront_logs.id

  depends_on = [aws_s3_bucket_public_access_block.cloudfront_logs]

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Sid       = "DenyInsecureTransport"
        Effect    = "Deny"
        Principal = "*"
        Action    = "s3:*"
        Resource = [
          aws_s3_bucket.cloudfront_logs.arn,
          "${aws_s3_bucket.cloudfront_logs.arn}/*"
        ]
        Condition = {
          Bool = {
            "aws:SecureTransport" = "false"
          }
        }
      },
      {
        Sid    = "AllowLogsDeliveryGetBucketAcl"
        Effect = "Allow"
        Principal = {
          Service = "delivery.logs.amazonaws.com"
        }
        Action   = "s3:GetBucketAcl"
        Resource = aws_s3_bucket.cloudfront_logs.arn
      },
      {
        Sid    = "AllowLogsDeliveryPutObject"
        Effect = "Allow"
        Principal = {
          Service = "delivery.logs.amazonaws.com"
        }
        Action   = "s3:PutObject"
        Resource = "${aws_s3_bucket.cloudfront_logs.arn}/*"
        Condition = {
          StringEquals = {
            "aws:SourceAccount" = data.aws_caller_identity.current.account_id
            "s3:x-amz-acl"      = "bucket-owner-full-control"
          }
        }
      }
    ]
  })
}

resource "aws_s3_bucket_server_side_encryption_configuration" "cloudfront_logs" {
  bucket = aws_s3_bucket.cloudfront_logs.id

  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm = "AES256"
    }
  }
}

resource "aws_s3_bucket_ownership_controls" "cloudfront_logs" {
  # checkov:skip=CKV2_AWS_65: "ACL required for legacy CloudFront log delivery"
  bucket = aws_s3_bucket.cloudfront_logs.id

  rule {
    # Prefer bucket owner control, but keep compatibility with AWS log-delivery ACL semantics.
    object_ownership = "BucketOwnerPreferred"
  }
}

# ========================= CloudFront Distribution ============================

#checkov:skip=CKV_AWS_310: Single ALB origin is intentional; origin failover is provided at ECS service and multi-AZ layers.
#checkov:skip=CKV_AWS_374: Platform is national scope and must serve all geographies; geo-blocking is enforced at application policy layer.
#checkov:skip=CKV2_AWS_47: Associated CloudFront WAF ACL includes AWSManagedRulesKnownBadInputsRuleSet for Log4j coverage.
resource "aws_cloudfront_distribution" "this" {
  enabled             = true
  is_ipv6_enabled     = true
  http_version        = "http2and3"
  web_acl_id          = aws_wafv2_web_acl.cloudfront.arn
  default_root_object = "index.html"
  aliases             = [var.root_domain_name, "www.${var.root_domain_name}", var.api_domain_name]
  price_class         = "PriceClass_100"

  logging_config {
    bucket          = aws_s3_bucket.cloudfront_logs.bucket_domain_name
    include_cookies = false
    prefix          = "distribution/"
  }

  origin {
    domain_name = var.alb_dns_name
    origin_id   = "AlbOrigin"

    custom_origin_config {
      # CloudFront validates origin TLS certificates against the origin domain name.
      # ALBs use an AWS hostname as their DNS name which is not covered by our ACM cert,
      # so HTTPS origin connections fail with 502. Use HTTP for origin traffic instead.
      origin_protocol_policy = "http-only"
      http_port              = 80
      https_port             = 443
      origin_ssl_protocols   = ["TLSv1.2"]
    }
  }

  default_cache_behavior {
    target_origin_id           = "AlbOrigin"
    viewer_protocol_policy     = "redirect-to-https"
    allowed_methods            = ["GET", "HEAD", "OPTIONS", "PUT", "POST", "PATCH", "DELETE"]
    cached_methods             = ["GET", "HEAD"]
    compress                   = true
    cache_policy_id            = aws_cloudfront_cache_policy.static.id
    response_headers_policy_id = aws_cloudfront_response_headers_policy.security.id

    function_association {
      event_type   = "viewer-request"
      function_arn = aws_cloudfront_function.apex_redirect.arn
    }
  }

  ordered_cache_behavior {
    path_pattern             = "/api/*"
    target_origin_id         = "AlbOrigin"
    viewer_protocol_policy   = "https-only"
    allowed_methods          = ["GET", "HEAD", "OPTIONS", "PUT", "POST", "PATCH", "DELETE"]
    cached_methods           = ["GET", "HEAD"]
    cache_policy_id          = aws_cloudfront_cache_policy.no_cache.id
    origin_request_policy_id = local.all_viewer_except_host_header_policy_id
  }

  ordered_cache_behavior {
    path_pattern             = "/ws/*"
    target_origin_id         = "AlbOrigin"
    viewer_protocol_policy   = "https-only"
    allowed_methods          = ["GET", "HEAD", "OPTIONS", "PUT", "POST", "PATCH", "DELETE"]
    cached_methods           = ["GET", "HEAD"]
    cache_policy_id          = aws_cloudfront_cache_policy.no_cache.id
    origin_request_policy_id = local.all_viewer_except_host_header_policy_id
  }

  viewer_certificate {
    acm_certificate_arn      = var.acm_certificate_arn_us_east_1
    ssl_support_method       = "sni-only"
    minimum_protocol_version = "TLSv1.2_2021"
  }

  restrictions {
    geo_restriction {
      restriction_type = "none"
    }
  }

  depends_on = [aws_s3_bucket_ownership_controls.cloudfront_logs]

  tags = local.common_tags
}

# ========================= CloudFront Function: Apex -> WWW Redirect ==========

resource "aws_cloudfront_function" "apex_redirect" {
  name    = "${local.name_prefix}-apex-redirect"
  runtime = "cloudfront-js-2.0"
  publish = true

  code = <<-EOF
    function handler(event) {
      var request = event.request;
      var host = request.headers.host.value;
      if (host === '${var.root_domain_name}') {
        return {
          statusCode: 301,
          statusDescription: 'Moved Permanently',
          headers: {
            location: { value: 'https://www.${var.root_domain_name}' + request.uri }
          }
        };
      }
      return request;
    }
  EOF
}

# ========================= Route 53 Records ===================================

resource "aws_route53_record" "root" {
  zone_id = var.hosted_zone_id
  name    = var.root_domain_name
  type    = "A"

  alias {
    name                   = aws_cloudfront_distribution.this.domain_name
    zone_id                = aws_cloudfront_distribution.this.hosted_zone_id
    evaluate_target_health = false
  }
}

resource "aws_route53_record" "api" {
  zone_id = var.hosted_zone_id
  name    = var.api_domain_name
  type    = "A"

  alias {
    name                   = aws_cloudfront_distribution.this.domain_name
    zone_id                = aws_cloudfront_distribution.this.hosted_zone_id
    evaluate_target_health = false
  }
}

resource "aws_route53_record" "www" {
  zone_id = var.hosted_zone_id
  name    = "www.${var.root_domain_name}"
  type    = "A"

  alias {
    name                   = aws_cloudfront_distribution.this.domain_name
    zone_id                = aws_cloudfront_distribution.this.hosted_zone_id
    evaluate_target_health = false
  }
}
