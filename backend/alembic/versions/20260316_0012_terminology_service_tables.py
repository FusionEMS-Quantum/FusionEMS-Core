"""Add centralized terminology service tables.

Revision ID: 20260316_0012
Revises: 20260316_0011
Create Date: 2026-03-16 00:12:00.000000

"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB, UUID

revision = "20260316_0012"
down_revision = "20260316_0011"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # NOTE: These tables are tenant-scoped and designed for high-volume lookup.
    # Avoid destructive operations; prefer additive evolution.

    # Ensure required extensions exist for gen_random_uuid() and trigram search.
    op.execute("CREATE EXTENSION IF NOT EXISTS pgcrypto")
    op.execute("CREATE EXTENSION IF NOT EXISTS pg_trgm")

    op.create_table(
        "terminology_code_systems",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("tenant_id", UUID(as_uuid=True), sa.ForeignKey("tenants.id"), nullable=False),
        sa.Column("system_uri", sa.String(255), nullable=False),
        sa.Column("system_version", sa.String(64), nullable=False, server_default=""),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("publisher", sa.String(255), nullable=True),
        sa.Column("status", sa.String(32), nullable=False, server_default="active"),
        sa.Column("is_external", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("metadata_blob", JSONB(), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("version", sa.Integer(), nullable=False, server_default=sa.text("1")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.UniqueConstraint(
            "tenant_id",
            "system_uri",
            "system_version",
            name="uq_term_code_systems_tenant_uri_version",
        ),
    )
    op.create_index("ix_term_code_systems_tenant_id", "terminology_code_systems", ["tenant_id"])
    op.create_index("ix_term_code_systems_system_uri", "terminology_code_systems", ["system_uri"])

    op.execute('ALTER TABLE "terminology_code_systems" ENABLE ROW LEVEL SECURITY;')
    op.execute(
        'DO $$ BEGIN '
        'IF NOT EXISTS (SELECT 1 FROM pg_policies WHERE schemaname = current_schema() AND tablename = '"'"'terminology_code_systems'"'"' AND policyname = '"'"'terminology_code_systems_tenant_isolation'"'"') THEN '
        'CREATE POLICY "terminology_code_systems_tenant_isolation" ON "terminology_code_systems" '
        'USING (tenant_id = current_setting('"'"'app.tenant_id'"'"', true)::uuid); '
        'END IF; END $$;'
    )

    op.create_table(
        "terminology_dataset_versions",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("tenant_id", UUID(as_uuid=True), sa.ForeignKey("tenants.id"), nullable=False),
        sa.Column("code_system_id", UUID(as_uuid=True), sa.ForeignKey("terminology_code_systems.id"), nullable=False),
        sa.Column("dataset_source", sa.String(64), nullable=False),
        sa.Column("source_uri", sa.String(1024), nullable=True),
        sa.Column("source_version", sa.String(128), nullable=False),
        sa.Column("checksum_sha256", sa.String(64), nullable=True),
        sa.Column("imported_by_user_id", UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("imported_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("status", sa.String(32), nullable=False, server_default="imported"),
        sa.Column("metadata_blob", JSONB(), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("version", sa.Integer(), nullable=False, server_default=sa.text("1")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.UniqueConstraint(
            "tenant_id",
            "code_system_id",
            "dataset_source",
            "source_version",
            name="uq_term_dataset_versions_tenant_system_source_ver",
        ),
    )
    op.create_index("ix_term_dataset_versions_tenant_id", "terminology_dataset_versions", ["tenant_id"])
    op.create_index("ix_term_dataset_versions_code_system_id", "terminology_dataset_versions", ["code_system_id"])
    op.create_index("ix_term_dataset_versions_dataset_source", "terminology_dataset_versions", ["dataset_source"])

    op.execute('ALTER TABLE "terminology_dataset_versions" ENABLE ROW LEVEL SECURITY;')
    op.execute(
        'DO $$ BEGIN '
        'IF NOT EXISTS (SELECT 1 FROM pg_policies WHERE schemaname = current_schema() AND tablename = '"'"'terminology_dataset_versions'"'"' AND policyname = '"'"'terminology_dataset_versions_tenant_isolation'"'"') THEN '
        'CREATE POLICY "terminology_dataset_versions_tenant_isolation" ON "terminology_dataset_versions" '
        'USING (tenant_id = current_setting('"'"'app.tenant_id'"'"', true)::uuid); '
        'END IF; END $$;'
    )

    op.create_table(
        "terminology_concepts",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("tenant_id", UUID(as_uuid=True), sa.ForeignKey("tenants.id"), nullable=False),
        sa.Column("code_system_id", UUID(as_uuid=True), sa.ForeignKey("terminology_code_systems.id"), nullable=False),
        sa.Column("code", sa.String(64), nullable=False),
        sa.Column("display", sa.String(512), nullable=False),
        sa.Column("definition", sa.Text(), nullable=True),
        sa.Column("active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("effective_start_date", sa.Date(), nullable=True),
        sa.Column("effective_end_date", sa.Date(), nullable=True),
        sa.Column("properties", JSONB(), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("version", sa.Integer(), nullable=False, server_default=sa.text("1")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.UniqueConstraint(
            "tenant_id",
            "code_system_id",
            "code",
            name="uq_term_concepts_tenant_system_code",
        ),
    )
    op.create_index("ix_term_concepts_tenant_id", "terminology_concepts", ["tenant_id"])
    op.create_index("ix_term_concepts_code_system_id", "terminology_concepts", ["code_system_id"])
    op.create_index("ix_term_concepts_code", "terminology_concepts", ["code"])
    op.create_index("ix_term_concepts_display", "terminology_concepts", ["display"])

    op.execute('ALTER TABLE "terminology_concepts" ENABLE ROW LEVEL SECURITY;')
    op.execute(
        'DO $$ BEGIN '
        'IF NOT EXISTS (SELECT 1 FROM pg_policies WHERE schemaname = current_schema() AND tablename = '"'"'terminology_concepts'"'"' AND policyname = '"'"'terminology_concepts_tenant_isolation'"'"') THEN '
        'CREATE POLICY "terminology_concepts_tenant_isolation" ON "terminology_concepts" '
        'USING (tenant_id = current_setting('"'"'app.tenant_id'"'"', true)::uuid); '
        'END IF; END $$;'
    )

    # Accelerate fuzzy search / autocomplete via trigram GIN indexes.
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_term_concepts_code_trgm "
        "ON terminology_concepts USING gin (code gin_trgm_ops)"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_term_concepts_display_trgm "
        "ON terminology_concepts USING gin (display gin_trgm_ops)"
    )

    op.create_table(
        "terminology_synonyms",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("tenant_id", UUID(as_uuid=True), sa.ForeignKey("tenants.id"), nullable=False),
        sa.Column("concept_id", UUID(as_uuid=True), sa.ForeignKey("terminology_concepts.id"), nullable=False),
        sa.Column("synonym", sa.String(512), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.UniqueConstraint(
            "tenant_id",
            "concept_id",
            "synonym",
            name="uq_term_synonyms_tenant_concept_syn",
        ),
    )
    op.create_index("ix_term_synonyms_tenant_id", "terminology_synonyms", ["tenant_id"])
    op.create_index("ix_term_synonyms_concept_id", "terminology_synonyms", ["concept_id"])
    op.create_index("ix_term_synonyms_synonym", "terminology_synonyms", ["synonym"])
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_term_synonyms_synonym_trgm "
        "ON terminology_synonyms USING gin (synonym gin_trgm_ops)"
    )

    op.execute('ALTER TABLE "terminology_synonyms" ENABLE ROW LEVEL SECURITY;')
    op.execute(
        'DO $$ BEGIN '
        'IF NOT EXISTS (SELECT 1 FROM pg_policies WHERE schemaname = current_schema() AND tablename = '"'"'terminology_synonyms'"'"' AND policyname = '"'"'terminology_synonyms_tenant_isolation'"'"') THEN '
        'CREATE POLICY "terminology_synonyms_tenant_isolation" ON "terminology_synonyms" '
        'USING (tenant_id = current_setting('"'"'app.tenant_id'"'"', true)::uuid); '
        'END IF; END $$;'
    )

    op.create_table(
        "terminology_mappings",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("tenant_id", UUID(as_uuid=True), sa.ForeignKey("tenants.id"), nullable=False),
        sa.Column("from_concept_id", UUID(as_uuid=True), sa.ForeignKey("terminology_concepts.id"), nullable=False),
        sa.Column("to_concept_id", UUID(as_uuid=True), sa.ForeignKey("terminology_concepts.id"), nullable=False),
        sa.Column("map_type", sa.String(32), nullable=False, server_default="equivalent"),
        sa.Column("source", sa.String(64), nullable=False, server_default="manual"),
        sa.Column("confidence", sa.Float(), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("metadata_blob", JSONB(), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("version", sa.Integer(), nullable=False, server_default=sa.text("1")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.UniqueConstraint(
            "tenant_id",
            "from_concept_id",
            "to_concept_id",
            "map_type",
            "source",
            name="uq_term_mappings_tenant_from_to_type_source",
        ),
    )
    op.create_index("ix_term_mappings_tenant_id", "terminology_mappings", ["tenant_id"])
    op.create_index("ix_term_mappings_from_concept_id", "terminology_mappings", ["from_concept_id"])
    op.create_index("ix_term_mappings_to_concept_id", "terminology_mappings", ["to_concept_id"])

    op.execute('ALTER TABLE "terminology_mappings" ENABLE ROW LEVEL SECURITY;')
    op.execute(
        'DO $$ BEGIN '
        'IF NOT EXISTS (SELECT 1 FROM pg_policies WHERE schemaname = current_schema() AND tablename = '"'"'terminology_mappings'"'"' AND policyname = '"'"'terminology_mappings_tenant_isolation'"'"') THEN '
        'CREATE POLICY "terminology_mappings_tenant_isolation" ON "terminology_mappings" '
        'USING (tenant_id = current_setting('"'"'app.tenant_id'"'"', true)::uuid); '
        'END IF; END $$;'
    )

    op.create_table(
        "terminology_refresh_schedules",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("tenant_id", UUID(as_uuid=True), sa.ForeignKey("tenants.id"), nullable=False),
        sa.Column("code_system_id", UUID(as_uuid=True), sa.ForeignKey("terminology_code_systems.id"), nullable=False),
        sa.Column("schedule_key", sa.String(128), nullable=False),
        sa.Column("dataset_source", sa.String(64), nullable=False),
        sa.Column("refresh_interval_hours", sa.Integer(), nullable=False, server_default=sa.text("24")),
        sa.Column("is_enabled", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("last_run_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("next_run_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_run_status", sa.String(32), nullable=True),
        sa.Column("last_run_error", sa.Text(), nullable=True),
        sa.Column("metadata_blob", JSONB(), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.UniqueConstraint(
            "tenant_id",
            "code_system_id",
            "schedule_key",
            name="uq_term_refresh_tenant_system_key",
        ),
    )
    op.create_index("ix_term_refresh_tenant_id", "terminology_refresh_schedules", ["tenant_id"])
    op.create_index("ix_term_refresh_code_system_id", "terminology_refresh_schedules", ["code_system_id"])
    op.create_index("ix_term_refresh_next_run_at", "terminology_refresh_schedules", ["next_run_at"])

    op.execute('ALTER TABLE "terminology_refresh_schedules" ENABLE ROW LEVEL SECURITY;')
    op.execute(
        'DO $$ BEGIN '
        'IF NOT EXISTS (SELECT 1 FROM pg_policies WHERE schemaname = current_schema() AND tablename = '"'"'terminology_refresh_schedules'"'"' AND policyname = '"'"'terminology_refresh_schedules_tenant_isolation'"'"') THEN '
        'CREATE POLICY "terminology_refresh_schedules_tenant_isolation" ON "terminology_refresh_schedules" '
        'USING (tenant_id = current_setting('"'"'app.tenant_id'"'"', true)::uuid); '
        'END IF; END $$;'
    )


def downgrade() -> None:
    # Policies are dropped implicitly with tables.
    op.drop_index("ix_term_refresh_next_run_at", table_name="terminology_refresh_schedules")
    op.drop_index("ix_term_refresh_code_system_id", table_name="terminology_refresh_schedules")
    op.drop_index("ix_term_refresh_tenant_id", table_name="terminology_refresh_schedules")
    op.drop_table("terminology_refresh_schedules")

    op.drop_index("ix_term_mappings_to_concept_id", table_name="terminology_mappings")
    op.drop_index("ix_term_mappings_from_concept_id", table_name="terminology_mappings")
    op.drop_index("ix_term_mappings_tenant_id", table_name="terminology_mappings")
    op.drop_table("terminology_mappings")

    op.execute("DROP INDEX IF EXISTS ix_term_synonyms_synonym_trgm")
    op.drop_index("ix_term_synonyms_synonym", table_name="terminology_synonyms")
    op.drop_index("ix_term_synonyms_concept_id", table_name="terminology_synonyms")
    op.drop_index("ix_term_synonyms_tenant_id", table_name="terminology_synonyms")
    op.drop_table("terminology_synonyms")

    op.execute("DROP INDEX IF EXISTS ix_term_concepts_display_trgm")
    op.execute("DROP INDEX IF EXISTS ix_term_concepts_code_trgm")
    op.drop_index("ix_term_concepts_display", table_name="terminology_concepts")
    op.drop_index("ix_term_concepts_code", table_name="terminology_concepts")
    op.drop_index("ix_term_concepts_code_system_id", table_name="terminology_concepts")
    op.drop_index("ix_term_concepts_tenant_id", table_name="terminology_concepts")
    op.drop_table("terminology_concepts")

    op.drop_index("ix_term_dataset_versions_dataset_source", table_name="terminology_dataset_versions")
    op.drop_index("ix_term_dataset_versions_code_system_id", table_name="terminology_dataset_versions")
    op.drop_index("ix_term_dataset_versions_tenant_id", table_name="terminology_dataset_versions")
    op.drop_table("terminology_dataset_versions")

    op.drop_index("ix_term_code_systems_system_uri", table_name="terminology_code_systems")
    op.drop_index("ix_term_code_systems_tenant_id", table_name="terminology_code_systems")
    op.drop_table("terminology_code_systems")
