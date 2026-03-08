locals {
  az_index = { for idx, az in var.availability_zones : az => idx }
}

resource "aws_route_table" "public" {
  vpc_id = var.vpc_id

  tags = merge(var.tags, {
    Name = "${var.name_prefix}-public-rt"
  })
}

resource "aws_route" "public_internet" {
  route_table_id         = aws_route_table.public.id
  destination_cidr_block = "0.0.0.0/0"
  gateway_id             = var.internet_gateway_id
}

resource "aws_route_table_association" "public" {
  for_each = local.az_index

  subnet_id      = var.public_subnet_ids[each.value]
  route_table_id = aws_route_table.public.id
}

resource "aws_route_table" "private_app" {
  for_each = local.az_index
  vpc_id   = var.vpc_id

  tags = merge(var.tags, {
    Name = "${var.name_prefix}-private-app-rt-${each.key}"
  })
}

resource "aws_route" "private_app_nat" {
  for_each = local.az_index

  route_table_id         = aws_route_table.private_app[each.key].id
  destination_cidr_block = "0.0.0.0/0"
  nat_gateway_id         = var.nat_gateway_ids[min(each.value, length(var.nat_gateway_ids) - 1)]
}

resource "aws_route_table_association" "private_app" {
  for_each = local.az_index

  subnet_id      = var.private_app_subnet_ids[each.value]
  route_table_id = aws_route_table.private_app[each.key].id
}

resource "aws_route_table" "private_data" {
  for_each = local.az_index
  vpc_id   = var.vpc_id

  tags = merge(var.tags, {
    Name = "${var.name_prefix}-private-data-rt-${each.key}"
  })
}

resource "aws_route" "private_data_nat" {
  for_each = var.data_subnet_internet_egress_enabled ? local.az_index : {}

  route_table_id         = aws_route_table.private_data[each.key].id
  destination_cidr_block = "0.0.0.0/0"
  nat_gateway_id         = var.nat_gateway_ids[min(each.value, length(var.nat_gateway_ids) - 1)]
}

resource "aws_route_table_association" "private_data" {
  for_each = local.az_index

  subnet_id      = var.private_data_subnet_ids[each.value]
  route_table_id = aws_route_table.private_data[each.key].id
}