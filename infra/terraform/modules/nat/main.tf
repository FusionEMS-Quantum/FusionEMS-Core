locals {
  nat_subnet_ids = var.nat_gateway_mode == "per_az" ? var.public_subnet_ids : [var.public_subnet_ids[0]]
}

resource "aws_eip" "nat" {
  count  = length(local.nat_subnet_ids)
  domain = "vpc"

  tags = merge(var.tags, {
    Name = "${var.name_prefix}-nat-eip-${count.index + 1}"
  })
}

resource "aws_nat_gateway" "this" {
  count = length(local.nat_subnet_ids)

  allocation_id = aws_eip.nat[count.index].id
  subnet_id     = local.nat_subnet_ids[count.index]

  tags = merge(var.tags, {
    Name = "${var.name_prefix}-nat-${count.index + 1}"
  })
}