#checkov:skip=CKV2_AWS_5: Security group is attached by composing ALB and ECS modules in this stack.
resource "aws_security_group" "alb" {
  name_prefix = "${var.name_prefix}-alb-"
  description = "ALB ingress boundary"
  vpc_id      = var.vpc_id

  tags = merge(var.tags, {
    Name = "${var.name_prefix}-alb-sg"
  })

  lifecycle {
    # Prevent unnecessary replacements when only descriptions drift between
    # live resources and Terraform-managed configuration (common during
    # environment updates or manual console edits). We still create before
    # destroy to preserve stability on changes.
    create_before_destroy = true
    ignore_changes = [description]
  }
}

resource "aws_security_group_rule" "alb_ingress_https" {
  security_group_id = aws_security_group.alb.id
  type              = "ingress"
  description       = "HTTPS ingress"
  from_port         = 443
  to_port           = 443
  protocol          = "tcp"
  cidr_blocks       = ["0.0.0.0/0"]

  lifecycle {
    # Description-only diffs should not cause rule recreation.
    ignore_changes = [description]
  }
}

#checkov:skip=CKV_AWS_260: Port 80 ingress exists solely for immediate HTTP->HTTPS redirect and controlled CloudFront-to-origin compatibility.
resource "aws_security_group_rule" "alb_ingress_http" {
  count = var.enable_http_ingress ? 1 : 0

  security_group_id = aws_security_group.alb.id
  type              = "ingress"
  description       = "HTTP ingress"
  from_port         = 80
  to_port           = 80
  protocol          = "tcp"
  cidr_blocks       = ["0.0.0.0/0"]

  lifecycle {
    ignore_changes = [description]
  }
}

#checkov:skip=CKV2_AWS_5: Security group is attached to ECS services by environment root modules.
resource "aws_security_group" "ecs" {
  name_prefix = "${var.name_prefix}-ecs-"
  description = "ECS task security group"
  vpc_id      = var.vpc_id

  tags = merge(var.tags, {
    Name = "${var.name_prefix}-ecs-sg"
  })

  lifecycle {
    create_before_destroy = true
    ignore_changes = [description]
  }
}

resource "aws_security_group_rule" "alb_to_ecs" {
  for_each = toset([for p in var.ecs_ingress_ports : tostring(p)])

  security_group_id        = aws_security_group.ecs.id
  type                     = "ingress"
  description              = "ALB to ECS on port ${each.value}"
  from_port                = tonumber(each.value)
  to_port                  = tonumber(each.value)
  protocol                 = "tcp"
  source_security_group_id = aws_security_group.alb.id

  lifecycle {
    ignore_changes = [description]
  }
}

resource "aws_security_group_rule" "ecs_egress_vpc" {
  security_group_id = aws_security_group.ecs.id
  type              = "egress"
  description       = "ECS egress to VPC"
  from_port         = 0
  to_port           = 65535
  protocol          = "tcp"
  cidr_blocks       = [var.vpc_cidr]

  lifecycle {
    ignore_changes = [description]
  }
}

resource "aws_security_group_rule" "ecs_egress_https" {
  security_group_id = aws_security_group.ecs.id
  type              = "egress"
  description       = "ECS egress HTTPS to internet"
  from_port         = 443
  to_port           = 443
  protocol          = "tcp"
  cidr_blocks       = ["0.0.0.0/0"]

  lifecycle {
    ignore_changes = [description]
  }
}

resource "aws_security_group_rule" "alb_to_ecs_egress" {
  security_group_id        = aws_security_group.alb.id
  type                     = "egress"
  description              = "ALB egress to ECS"
  from_port                = 0
  to_port                  = 65535
  protocol                 = "tcp"
  source_security_group_id = aws_security_group.ecs.id

  lifecycle {
    ignore_changes = [description]
  }
}

#checkov:skip=CKV2_AWS_5: Security group is attached to RDS instance in the rds module.
resource "aws_security_group" "rds" {
  name_prefix = "${var.name_prefix}-rds-"
  description = "RDS security group"
  vpc_id      = var.vpc_id

  tags = merge(var.tags, {
    Name = "${var.name_prefix}-rds-sg"
  })

  lifecycle {
    create_before_destroy = true
    ignore_changes = [description]
  }
}

resource "aws_security_group_rule" "ecs_to_rds" {
  security_group_id        = aws_security_group.rds.id
  type                     = "ingress"
  description              = "PostgreSQL from ECS"
  from_port                = 5432
  to_port                  = 5432
  protocol                 = "tcp"
  source_security_group_id = aws_security_group.ecs.id

  lifecycle {
    ignore_changes = [description]
  }
}

#checkov:skip=CKV2_AWS_5: Security group is attached to ElastiCache replication group in the redis module.
resource "aws_security_group" "redis" {
  name_prefix = "${var.name_prefix}-redis-"
  description = "Redis security group"
  vpc_id      = var.vpc_id

  tags = merge(var.tags, {
    Name = "${var.name_prefix}-redis-sg"
  })

  lifecycle {
    create_before_destroy = true
    ignore_changes = [description]
  }
}

resource "aws_security_group_rule" "ecs_to_redis" {
  security_group_id        = aws_security_group.redis.id
  type                     = "ingress"
  description              = "Redis from ECS"
  from_port                = 6379
  to_port                  = 6379
  protocol                 = "tcp"
  source_security_group_id = aws_security_group.ecs.id

  lifecycle {
    ignore_changes = [description]
  }
}