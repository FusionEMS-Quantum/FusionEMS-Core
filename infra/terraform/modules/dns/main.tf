#checkov:skip=CKV2_AWS_38: DNSSEC is managed by enterprise DNS governance pipeline and registrar integration outside this module.
#checkov:skip=CKV2_AWS_39: Route53 query logging is configured by centralized DNS observability stack.
resource "aws_route53_zone" "public" {
  count = var.create_public_zone ? 1 : 0

  name = var.public_zone_name

  tags = merge(var.tags, {
    Name = "${var.name_prefix}-public-zone"
  })
}

resource "aws_route53_zone" "private" {
  count = var.create_private_zone ? 1 : 0

  name = var.private_zone_name

  vpc {
    vpc_id = var.vpc_id
  }

  tags = merge(var.tags, {
    Name = "${var.name_prefix}-private-zone"
  })
}