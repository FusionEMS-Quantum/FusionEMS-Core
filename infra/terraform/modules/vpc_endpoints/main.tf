resource "aws_security_group" "interface_endpoints" {
  count = var.create_interface_endpoints ? 1 : 0

  name_prefix = "${var.name_prefix}-vpce-"
  description = "Security group for interface VPC endpoints"
  vpc_id      = var.vpc_id

  ingress {
    description = "HTTPS from VPC"
    from_port   = 443
    to_port     = 443
    protocol    = "tcp"
    cidr_blocks = [var.vpc_cidr]
  }

  egress {
    description = "Allow HTTPS egress"
    from_port   = 443
    to_port     = 443
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = merge(var.tags, {
    Name = "${var.name_prefix}-vpce-sg"
  })

  lifecycle {
    # Avoid replacing the security group when only the description text drifts
    # between console edits or minor formatting changes.
    create_before_destroy = true
    ignore_changes        = [description]
  }
}

resource "aws_vpc_endpoint" "s3" {
  count = var.enable_s3_gateway_endpoint ? 1 : 0

  vpc_id            = var.vpc_id
  service_name      = "com.amazonaws.${var.region}.s3"
  vpc_endpoint_type = "Gateway"
  route_table_ids   = var.route_table_ids

  tags = merge(var.tags, {
    Name = "${var.name_prefix}-vpce-s3"
  })
}

resource "aws_vpc_endpoint" "dynamodb" {
  count = var.enable_dynamodb_gateway_endpoint ? 1 : 0

  vpc_id            = var.vpc_id
  service_name      = "com.amazonaws.${var.region}.dynamodb"
  vpc_endpoint_type = "Gateway"
  route_table_ids   = var.route_table_ids

  tags = merge(var.tags, {
    Name = "${var.name_prefix}-vpce-dynamodb"
  })
}

resource "aws_vpc_endpoint" "interface" {
  for_each = var.create_interface_endpoints ? toset(var.interface_endpoint_services) : toset([])

  vpc_id              = var.vpc_id
  service_name        = "com.amazonaws.${var.region}.${each.value}"
  vpc_endpoint_type   = "Interface"
  private_dns_enabled = true
  subnet_ids          = var.private_app_subnet_ids
  security_group_ids  = [aws_security_group.interface_endpoints[0].id]

  tags = merge(var.tags, {
    Name = "${var.name_prefix}-vpce-${replace(each.value, ".", "-")}"
  })
}