# Web Application Firewall
resource "aws_wafv2_web_acl" "main" {
  name        = "${var.environment}-global-waf"
  description = "Managed WAF rules for web app"
  scope       = "REGIONAL"

  default_action {
    allow {}
  }
  
  rule {
    name     = "AWSManagedRulesCommonRuleSet"
    priority = 1

    override_action {
      none {}
    }

    statement {
      managed_rule_group_statement {
        name        = "AWSManagedRulesCommonRuleSet"
        vendor_name = "AWS"
      }
    }
    visibility_config {
      cloudwatch_metrics_enabled = true
      metric_name                = "AWSManagedRulesCommonRuleSetMetric"
      sampled_requests_enabled   = true
    }
  }

  rule {
    name     = "AWSManagedRulesSQLiRuleSet"
    priority = 2
    override_action {
      none {}
    }
    statement {
      managed_rule_group_statement {
        name        = "AWSManagedRulesSQLiRuleSet"
        vendor_name = "AWS"
      }
    }
    visibility_config {
      cloudwatch_metrics_enabled = true
      metric_name                = "AWSManagedRulesSQLiRuleSetMetric"
      sampled_requests_enabled   = true
    }
  }

  visibility_config {
    cloudwatch_metrics_enabled = true
    metric_name                = "${var.environment}-waf-metric"
    sampled_requests_enabled   = true
  }
}

# Network Firewall implementation 
# Note: Further detailed implementation depends on route tables provided to firewall subnets
resource "aws_networkfirewall_firewall" "main" {
  name                = "${var.environment}-firewall"
  firewall_policy_arn = aws_networkfirewall_firewall_policy.main.arn
  vpc_id              = var.vpc_id
  dynamic "subnet_mapping" {
    for_each = var.subnet_ids
    content {
      subnet_id = subnet_mapping.value
    }
  }
}

resource "aws_networkfirewall_firewall_policy" "main" {
  name = "${var.environment}-firewall-policy"
  firewall_policy {
    stateless_default_actions          = ["aws:forward_to_sfe"]
    stateless_fragment_default_actions = ["aws:forward_to_sfe"]
  }
}
