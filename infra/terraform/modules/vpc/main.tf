locals {
  tags = merge(var.tags, {
    Name = "${var.name_prefix}-vpc"
  })
}

#checkov:skip=CKV2_AWS_11: VPC flow logs are enabled in the parent networking module where destination and IAM role are provisioned.
resource "aws_vpc" "this" {
  cidr_block           = var.vpc_cidr
  enable_dns_support   = var.enable_dns_support
  enable_dns_hostnames = var.enable_dns_hostnames

  tags = local.tags
}

resource "aws_internet_gateway" "this" {
  vpc_id = aws_vpc.this.id

  tags = merge(var.tags, {
    Name = "${var.name_prefix}-igw"
  })
}

resource "aws_default_security_group" "this" {
  vpc_id = aws_vpc.this.id

  ingress = []
  egress  = []

  tags = merge(var.tags, {
    Name = "${var.name_prefix}-default-sg"
  })
}