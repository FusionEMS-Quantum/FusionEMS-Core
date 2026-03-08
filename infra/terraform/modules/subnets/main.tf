locals {
  az_index = { for idx, az in var.availability_zones : az => idx }
}

check "subnet_az_alignment" {
  assert {
    condition = (
      length(var.public_subnet_cidrs) == length(var.availability_zones)
      && length(var.private_app_subnet_cidrs) == length(var.availability_zones)
      && length(var.private_data_subnet_cidrs) == length(var.availability_zones)
    )
    error_message = "Subnet CIDR list lengths must each match availability_zones length."
  }
}

resource "aws_subnet" "public" {
  for_each = local.az_index

  vpc_id                  = var.vpc_id
  cidr_block              = var.public_subnet_cidrs[each.value]
  availability_zone       = each.key
  map_public_ip_on_launch = var.map_public_ip_on_launch

  tags = merge(var.tags, {
    Name = "${var.name_prefix}-public-${each.key}"
    Tier = "public"
  })
}

resource "aws_subnet" "private_app" {
  for_each = local.az_index

  vpc_id            = var.vpc_id
  cidr_block        = var.private_app_subnet_cidrs[each.value]
  availability_zone = each.key

  tags = merge(var.tags, {
    Name = "${var.name_prefix}-private-app-${each.key}"
    Tier = "private-app"
  })
}

resource "aws_subnet" "private_data" {
  for_each = local.az_index

  vpc_id            = var.vpc_id
  cidr_block        = var.private_data_subnet_cidrs[each.value]
  availability_zone = each.key

  tags = merge(var.tags, {
    Name = "${var.name_prefix}-private-data-${each.key}"
    Tier = "private-data"
  })
}