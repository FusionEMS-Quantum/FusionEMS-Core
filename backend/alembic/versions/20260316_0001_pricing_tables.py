"""Add pricing, products, modules, subscription plans, and contract tables

Revision ID: 20260316_0001
Revises: 20260315_bank_connections
Create Date: 2026-03-16 00:01:00.000000

"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID

revision = "20260316_0001"
down_revision = "20260315_bank_connections"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # products
    op.create_table(
        "products",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("name", sa.String(255), nullable=False, unique=True),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("stripe_product_id", sa.String(128), nullable=True, unique=True),
        sa.Column("active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
    )

    # modules
    op.create_table(
        "modules",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("name", sa.String(128), nullable=False, unique=True),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("product_id", UUID(as_uuid=True), sa.ForeignKey("products.id"), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
    )
    op.create_index("ix_modules_product_id", "modules", ["product_id"])

    # prices
    op.create_table(
        "prices",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("product_id", UUID(as_uuid=True), sa.ForeignKey("products.id"), nullable=False),
        sa.Column("module_id", UUID(as_uuid=True), sa.ForeignKey("modules.id"), nullable=True),
        sa.Column("amount_cents", sa.Integer(), nullable=False),
        sa.Column("currency", sa.String(3), nullable=False, server_default=sa.text("'usd'")),
        sa.Column("interval", sa.String(16), nullable=False, server_default=sa.text("'month'")),
        sa.Column("per_unit_amount_cents", sa.Integer(), nullable=True),
        sa.Column("usage_type", sa.String(16), nullable=False, server_default=sa.text("'licensed'")),
        sa.Column("stripe_price_id", sa.String(128), nullable=True, unique=True),
        sa.Column("active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("version", sa.Integer(), nullable=False, server_default=sa.text("1")),
        sa.Column("effective_from", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
    )
    op.create_index("ix_prices_product_id", "prices", ["product_id"])

    # subscription_plans
    op.create_table(
        "subscription_plans",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("tenant_id", UUID(as_uuid=True), sa.ForeignKey("tenants.id"), nullable=False, unique=True),
        sa.Column("status", sa.String(32), nullable=False, server_default=sa.text("'active'")),
        sa.Column("stripe_subscription_id", sa.String(128), nullable=True, unique=True),
        sa.Column("current_period_start", sa.DateTime(timezone=True), nullable=True),
        sa.Column("current_period_end", sa.DateTime(timezone=True), nullable=True),
        sa.Column("cancel_at_period_end", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
    )
    op.create_index("ix_subscription_plans_tenant_id", "subscription_plans", ["tenant_id"])

    # subscription_items
    op.create_table(
        "subscription_items",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("plan_id", UUID(as_uuid=True), sa.ForeignKey("subscription_plans.id"), nullable=False),
        sa.Column("price_id", UUID(as_uuid=True), sa.ForeignKey("prices.id"), nullable=False),
        sa.Column("quantity", sa.Integer(), nullable=False, server_default=sa.text("1")),
        sa.Column("stripe_subscription_item_id", sa.String(128), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
    )
    op.create_index("ix_subscription_items_plan_id", "subscription_items", ["plan_id"])

    # contract_overrides
    op.create_table(
        "contract_overrides",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("tenant_id", UUID(as_uuid=True), sa.ForeignKey("tenants.id"), nullable=False),
        sa.Column("price_id", UUID(as_uuid=True), sa.ForeignKey("prices.id"), nullable=False),
        sa.Column("override_amount_cents", sa.Integer(), nullable=False),
        sa.Column("reason", sa.String(255), nullable=True),
        sa.Column("valid_until", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
    )
    op.create_index("ix_contract_overrides_tenant_id", "contract_overrides", ["tenant_id"])

    # price_change_audits
    op.create_table(
        "price_change_audits",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("price_id", UUID(as_uuid=True), sa.ForeignKey("prices.id"), nullable=False),
        sa.Column("changed_by_user_id", UUID(as_uuid=True), nullable=False),
        sa.Column("old_value_cents", sa.Integer(), nullable=False),
        sa.Column("new_value_cents", sa.Integer(), nullable=False),
        sa.Column("reason", sa.String(255), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
    )
    op.create_index("ix_price_change_audits_price_id", "price_change_audits", ["price_id"])


def downgrade() -> None:
    op.drop_table("price_change_audits")
    op.drop_table("contract_overrides")
    op.drop_table("subscription_items")
    op.drop_table("subscription_plans")
    op.drop_table("prices")
    op.drop_table("modules")
    op.drop_table("products")
