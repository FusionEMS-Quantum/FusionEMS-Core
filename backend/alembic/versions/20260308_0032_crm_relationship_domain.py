"""CRM / Relationship domain — patient identity, responsible parties, facilities,
relationship history, contact preferences.

Revision ID: 20260308_0032
Revises: 20260307_0031
Create Date: 2026-03-08

Creates:
  - patient_aliases (identity alias tracking)
  - patient_identifiers (external ID correlation)
  - patient_duplicate_candidates (duplicate detection queue)
  - patient_merge_requests (merge workflow)
  - patient_merge_audit_events (immutable merge audit trail)
  - patient_relationship_flags (identity relationship flags)
  - responsible_parties (guarantor/subscriber entities)
  - patient_responsible_party_links (patient ↔ party linkage)
  - insurance_subscriber_profiles (policy/carrier detail)
  - responsibility_audit_events (responsibility change audit)
  - facilities (hospital/SNF/LTC network)
  - facility_contacts (named facility contacts)
  - facility_relationship_notes (operational/billing notes)
  - facility_service_profiles (service line capabilities)
  - facility_friction_flags (friction issue tracking)
  - facility_audit_events (facility change audit)
  - relationship_timeline_events (longitudinal timelines)
  - internal_account_notes (permission-controlled notes)
  - patient_warning_flags (patient-level warnings)
  - facility_warning_flags (facility-level warnings)
  - relationship_summary_snapshots (AI/system summaries)
  - contact_preferences (communication eligibility)
  - communication_opt_out_events (opt-in/out log)
  - language_preferences (interpreter support)
  - contact_policy_audit_events (policy change audit)

All tables include tenant_id for RLS isolation.
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import UUID, JSONB

revision: str = "20260308_0032"
down_revision: Union[str, None] = "20260307_0031"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    _original_create_table = op.create_table

    def _safe_create_table(table_name: str, *columns: object, **kwargs: object) -> object:
        if sa.inspect(bind).has_table(table_name):
            return None
        return _original_create_table(table_name, *columns, **kwargs)

    op.create_table = _safe_create_table  # type: ignore[assignment]

    # ── PATIENT ALIASES ───────────────────────────────────────────────
    op.create_table(
        "patient_aliases",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("tenant_id", UUID(as_uuid=True), sa.ForeignKey("tenants.id"), nullable=False, index=True),
        sa.Column("patient_id", UUID(as_uuid=True), sa.ForeignKey("patients.id"), nullable=False, index=True),
        sa.Column("alias_type", sa.String(32), nullable=False),
        sa.Column("first_name", sa.String(128), nullable=False),
        sa.Column("middle_name", sa.String(128), nullable=True),
        sa.Column("last_name", sa.String(128), nullable=False),
        sa.Column("effective_date", sa.Date(), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now(), nullable=False),
    )

    # ── PATIENT IDENTIFIERS ───────────────────────────────────────────
    op.create_table(
        "patient_identifiers",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("tenant_id", UUID(as_uuid=True), sa.ForeignKey("tenants.id"), nullable=False, index=True),
        sa.Column("patient_id", UUID(as_uuid=True), sa.ForeignKey("patients.id"), nullable=False, index=True),
        sa.Column("source", sa.String(32), nullable=False),
        sa.Column("identifier_value", sa.String(256), nullable=False),
        sa.Column("issuing_authority", sa.String(256), nullable=True),
        sa.Column("provenance", sa.String(256), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now(), nullable=False),
    )
    op.execute(
        sa.text(
            "CREATE INDEX IF NOT EXISTS ix_patient_identifiers_source_value "
            "ON patient_identifiers (source, identifier_value)"
        )
    )

    # ── PATIENT DUPLICATE CANDIDATES ──────────────────────────────────
    op.create_table(
        "patient_duplicate_candidates",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("tenant_id", UUID(as_uuid=True), sa.ForeignKey("tenants.id"), nullable=False, index=True),
        sa.Column("patient_a_id", UUID(as_uuid=True), sa.ForeignKey("patients.id"), nullable=False),
        sa.Column("patient_b_id", UUID(as_uuid=True), sa.ForeignKey("patients.id"), nullable=False),
        sa.Column("confidence_score", sa.Float(), nullable=False, server_default=sa.text("0.0")),
        sa.Column("detection_method", sa.String(64), nullable=True),
        sa.Column("resolution", sa.String(32), nullable=False, server_default=sa.text("'UNRESOLVED'")),
        sa.Column("resolved_by_user_id", UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now(), nullable=False),
    )

    # ── PATIENT MERGE REQUESTS ────────────────────────────────────────
    op.create_table(
        "patient_merge_requests",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("tenant_id", UUID(as_uuid=True), sa.ForeignKey("tenants.id"), nullable=False, index=True),
        sa.Column("source_patient_id", UUID(as_uuid=True), sa.ForeignKey("patients.id"), nullable=False),
        sa.Column("target_patient_id", UUID(as_uuid=True), sa.ForeignKey("patients.id"), nullable=False),
        sa.Column("status", sa.String(32), nullable=False, server_default=sa.text("'PENDING_REVIEW'")),
        sa.Column("merge_reason", sa.Text(), nullable=True),
        sa.Column("field_resolution_map", JSONB(), nullable=True),
        sa.Column("requested_by_user_id", UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("reviewed_by_user_id", UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("review_notes", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now(), nullable=False),
    )

    # ── PATIENT MERGE AUDIT EVENTS ────────────────────────────────────
    op.create_table(
        "patient_merge_audit_events",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("tenant_id", UUID(as_uuid=True), sa.ForeignKey("tenants.id"), nullable=False, index=True),
        sa.Column("merge_request_id", UUID(as_uuid=True), sa.ForeignKey("patient_merge_requests.id"), nullable=False, index=True),
        sa.Column("action", sa.String(64), nullable=False),
        sa.Column("actor_user_id", UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("detail", JSONB(), nullable=True),
        sa.Column("correlation_id", sa.String(64), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )

    # ── PATIENT RELATIONSHIP FLAGS ────────────────────────────────────
    op.create_table(
        "patient_relationship_flags",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("tenant_id", UUID(as_uuid=True), sa.ForeignKey("tenants.id"), nullable=False, index=True),
        sa.Column("patient_id", UUID(as_uuid=True), sa.ForeignKey("patients.id"), nullable=False, index=True),
        sa.Column("flag_type", sa.String(64), nullable=False),
        sa.Column("severity", sa.String(32), nullable=False, server_default=sa.text("'INFO'")),
        sa.Column("title", sa.String(256), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("created_by_user_id", UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("resolved_by_user_id", UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("resolution_notes", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now(), nullable=False),
    )

    # ── RESPONSIBLE PARTIES ───────────────────────────────────────────
    op.create_table(
        "responsible_parties",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("tenant_id", UUID(as_uuid=True), sa.ForeignKey("tenants.id"), nullable=False, index=True),
        sa.Column("first_name", sa.String(128), nullable=False),
        sa.Column("middle_name", sa.String(128), nullable=True),
        sa.Column("last_name", sa.String(128), nullable=False),
        sa.Column("date_of_birth", sa.Date(), nullable=True),
        sa.Column("address_line_1", sa.String(256), nullable=True),
        sa.Column("address_line_2", sa.String(256), nullable=True),
        sa.Column("city", sa.String(128), nullable=True),
        sa.Column("state", sa.String(2), nullable=True),
        sa.Column("zip_code", sa.String(10), nullable=True),
        sa.Column("phone", sa.String(20), nullable=True),
        sa.Column("email", sa.String(256), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("version", sa.Integer(), nullable=False, server_default=sa.text("1")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now(), nullable=False),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
    )

    # ── PATIENT ↔ RESPONSIBLE PARTY LINKS ─────────────────────────────
    op.create_table(
        "patient_responsible_party_links",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("tenant_id", UUID(as_uuid=True), sa.ForeignKey("tenants.id"), nullable=False, index=True),
        sa.Column("patient_id", UUID(as_uuid=True), sa.ForeignKey("patients.id"), nullable=False, index=True),
        sa.Column("responsible_party_id", UUID(as_uuid=True), sa.ForeignKey("responsible_parties.id"), nullable=False, index=True),
        sa.Column("relationship_to_patient", sa.String(32), nullable=False),
        sa.Column("responsibility_state", sa.String(32), nullable=False, server_default=sa.text("'UNKNOWN'")),
        sa.Column("is_primary", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("effective_date", sa.Date(), nullable=True),
        sa.Column("end_date", sa.Date(), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now(), nullable=False),
    )

    # ── INSURANCE SUBSCRIBER PROFILES ─────────────────────────────────
    op.create_table(
        "insurance_subscriber_profiles",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("tenant_id", UUID(as_uuid=True), sa.ForeignKey("tenants.id"), nullable=False, index=True),
        sa.Column("responsible_party_id", UUID(as_uuid=True), sa.ForeignKey("responsible_parties.id"), nullable=False, index=True),
        sa.Column("insurance_carrier", sa.String(256), nullable=False),
        sa.Column("policy_number", sa.String(128), nullable=True),
        sa.Column("group_number", sa.String(128), nullable=True),
        sa.Column("member_id", sa.String(128), nullable=True),
        sa.Column("subscriber_name", sa.String(256), nullable=True),
        sa.Column("subscriber_dob", sa.Date(), nullable=True),
        sa.Column("relationship_to_subscriber", sa.String(64), nullable=True),
        sa.Column("effective_date", sa.Date(), nullable=True),
        sa.Column("termination_date", sa.Date(), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("version", sa.Integer(), nullable=False, server_default=sa.text("1")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now(), nullable=False),
    )

    # ── RESPONSIBILITY AUDIT EVENTS ───────────────────────────────────
    op.create_table(
        "responsibility_audit_events",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("tenant_id", UUID(as_uuid=True), sa.ForeignKey("tenants.id"), nullable=False, index=True),
        sa.Column("patient_id", UUID(as_uuid=True), sa.ForeignKey("patients.id"), nullable=False),
        sa.Column("responsible_party_id", UUID(as_uuid=True), sa.ForeignKey("responsible_parties.id"), nullable=False),
        sa.Column("action", sa.String(64), nullable=False),
        sa.Column("previous_state", sa.String(32), nullable=True),
        sa.Column("new_state", sa.String(32), nullable=True),
        sa.Column("actor_user_id", UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("detail", JSONB(), nullable=True),
        sa.Column("correlation_id", sa.String(64), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )

    # ── FACILITIES ────────────────────────────────────────────────────
    op.create_table(
        "facilities",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("tenant_id", UUID(as_uuid=True), sa.ForeignKey("tenants.id"), nullable=False, index=True),
        sa.Column("name", sa.String(256), nullable=False),
        sa.Column("facility_type", sa.String(32), nullable=False),
        sa.Column("npi", sa.String(20), nullable=True),
        sa.Column("address_line_1", sa.String(256), nullable=True),
        sa.Column("address_line_2", sa.String(256), nullable=True),
        sa.Column("city", sa.String(128), nullable=True),
        sa.Column("state", sa.String(2), nullable=True),
        sa.Column("zip_code", sa.String(10), nullable=True),
        sa.Column("phone", sa.String(20), nullable=True),
        sa.Column("fax", sa.String(20), nullable=True),
        sa.Column("email", sa.String(256), nullable=True),
        sa.Column("relationship_state", sa.String(32), nullable=False, server_default=sa.text("'NEW'")),
        sa.Column("destination_preference_notes", sa.Text(), nullable=True),
        sa.Column("service_notes", sa.Text(), nullable=True),
        sa.Column("version", sa.Integer(), nullable=False, server_default=sa.text("1")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now(), nullable=False),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
    )

    # ── FACILITY CONTACTS ─────────────────────────────────────────────
    op.create_table(
        "facility_contacts",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("tenant_id", UUID(as_uuid=True), sa.ForeignKey("tenants.id"), nullable=False, index=True),
        sa.Column("facility_id", UUID(as_uuid=True), sa.ForeignKey("facilities.id"), nullable=False, index=True),
        sa.Column("name", sa.String(256), nullable=False),
        sa.Column("role", sa.String(64), nullable=False),
        sa.Column("phone", sa.String(20), nullable=True),
        sa.Column("email", sa.String(256), nullable=True),
        sa.Column("preferred_contact_method", sa.String(32), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now(), nullable=False),
    )

    # ── FACILITY RELATIONSHIP NOTES ───────────────────────────────────
    op.create_table(
        "facility_relationship_notes",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("tenant_id", UUID(as_uuid=True), sa.ForeignKey("tenants.id"), nullable=False, index=True),
        sa.Column("facility_id", UUID(as_uuid=True), sa.ForeignKey("facilities.id"), nullable=False, index=True),
        sa.Column("note_type", sa.String(32), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("created_by_user_id", UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("is_internal", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )

    # ── FACILITY SERVICE PROFILES ─────────────────────────────────────
    op.create_table(
        "facility_service_profiles",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("tenant_id", UUID(as_uuid=True), sa.ForeignKey("tenants.id"), nullable=False, index=True),
        sa.Column("facility_id", UUID(as_uuid=True), sa.ForeignKey("facilities.id"), nullable=False, index=True),
        sa.Column("service_line", sa.String(128), nullable=False),
        sa.Column("accepts_ems_transport", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("average_turnaround_minutes", sa.Integer(), nullable=True),
        sa.Column("capability_notes", sa.Text(), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now(), nullable=False),
    )

    # ── FACILITY FRICTION FLAGS ───────────────────────────────────────
    op.create_table(
        "facility_friction_flags",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("tenant_id", UUID(as_uuid=True), sa.ForeignKey("tenants.id"), nullable=False, index=True),
        sa.Column("facility_id", UUID(as_uuid=True), sa.ForeignKey("facilities.id"), nullable=False, index=True),
        sa.Column("category", sa.String(64), nullable=False),
        sa.Column("title", sa.String(256), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("created_by_user_id", UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("resolved_by_user_id", UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("resolution_notes", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now(), nullable=False),
    )

    # ── FACILITY AUDIT EVENTS ─────────────────────────────────────────
    op.create_table(
        "facility_audit_events",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("tenant_id", UUID(as_uuid=True), sa.ForeignKey("tenants.id"), nullable=False, index=True),
        sa.Column("facility_id", UUID(as_uuid=True), sa.ForeignKey("facilities.id"), nullable=False, index=True),
        sa.Column("action", sa.String(64), nullable=False),
        sa.Column("actor_user_id", UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("detail", JSONB(), nullable=True),
        sa.Column("correlation_id", sa.String(64), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )

    # ── RELATIONSHIP TIMELINE EVENTS ──────────────────────────────────
    op.create_table(
        "relationship_timeline_events",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("tenant_id", UUID(as_uuid=True), sa.ForeignKey("tenants.id"), nullable=False, index=True),
        sa.Column("patient_id", UUID(as_uuid=True), sa.ForeignKey("patients.id"), nullable=True, index=True),
        sa.Column("facility_id", UUID(as_uuid=True), sa.ForeignKey("facilities.id"), nullable=True, index=True),
        sa.Column("event_type", sa.String(64), nullable=False),
        sa.Column("title", sa.String(256), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("source", sa.String(128), nullable=True),
        sa.Column("source_entity_id", UUID(as_uuid=True), nullable=True),
        sa.Column("actor_user_id", UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("metadata", JSONB(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )

    # ── INTERNAL ACCOUNT NOTES ────────────────────────────────────────
    op.create_table(
        "internal_account_notes",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("tenant_id", UUID(as_uuid=True), sa.ForeignKey("tenants.id"), nullable=False, index=True),
        sa.Column("patient_id", UUID(as_uuid=True), sa.ForeignKey("patients.id"), nullable=True),
        sa.Column("facility_id", UUID(as_uuid=True), sa.ForeignKey("facilities.id"), nullable=True),
        sa.Column("note_type", sa.String(64), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("created_by_user_id", UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("is_sensitive", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("visibility", sa.String(32), nullable=False, server_default=sa.text("'INTERNAL'")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now(), nullable=False),
    )

    # ── PATIENT WARNING FLAGS ─────────────────────────────────────────
    op.create_table(
        "patient_warning_flags",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("tenant_id", UUID(as_uuid=True), sa.ForeignKey("tenants.id"), nullable=False, index=True),
        sa.Column("patient_id", UUID(as_uuid=True), sa.ForeignKey("patients.id"), nullable=False, index=True),
        sa.Column("severity", sa.String(32), nullable=False),
        sa.Column("flag_type", sa.String(64), nullable=False),
        sa.Column("title", sa.String(256), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("created_by_user_id", UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("resolved_by_user_id", UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("resolution_notes", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now(), nullable=False),
    )

    # ── FACILITY WARNING FLAGS ────────────────────────────────────────
    op.create_table(
        "facility_warning_flags",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("tenant_id", UUID(as_uuid=True), sa.ForeignKey("tenants.id"), nullable=False, index=True),
        sa.Column("facility_id", UUID(as_uuid=True), sa.ForeignKey("facilities.id"), nullable=False, index=True),
        sa.Column("severity", sa.String(32), nullable=False),
        sa.Column("flag_type", sa.String(64), nullable=False),
        sa.Column("title", sa.String(256), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("created_by_user_id", UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("resolved_by_user_id", UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("resolution_notes", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now(), nullable=False),
    )

    # ── RELATIONSHIP SUMMARY SNAPSHOTS ────────────────────────────────
    op.create_table(
        "relationship_summary_snapshots",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("tenant_id", UUID(as_uuid=True), sa.ForeignKey("tenants.id"), nullable=False, index=True),
        sa.Column("patient_id", UUID(as_uuid=True), sa.ForeignKey("patients.id"), nullable=True),
        sa.Column("facility_id", UUID(as_uuid=True), sa.ForeignKey("facilities.id"), nullable=True),
        sa.Column("summary_type", sa.String(64), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("generated_by", sa.String(128), nullable=True),
        sa.Column("metadata", JSONB(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )

    # ── CONTACT PREFERENCES ───────────────────────────────────────────
    op.create_table(
        "contact_preferences",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("tenant_id", UUID(as_uuid=True), sa.ForeignKey("tenants.id"), nullable=False, index=True),
        sa.Column("patient_id", UUID(as_uuid=True), sa.ForeignKey("patients.id"), nullable=True, index=True),
        sa.Column("facility_id", UUID(as_uuid=True), sa.ForeignKey("facilities.id"), nullable=True, index=True),
        sa.Column("sms_allowed", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("call_allowed", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("email_allowed", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("mail_required", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("contact_restricted", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("preferred_channel", sa.String(32), nullable=True),
        sa.Column("preferred_time_start", sa.Time(), nullable=True),
        sa.Column("preferred_time_end", sa.Time(), nullable=True),
        sa.Column("facility_callback_preference", sa.Text(), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("version", sa.Integer(), nullable=False, server_default=sa.text("1")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now(), nullable=False),
    )

    # ── COMMUNICATION OPT-OUT EVENTS ──────────────────────────────────
    op.create_table(
        "communication_opt_out_events",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("tenant_id", UUID(as_uuid=True), sa.ForeignKey("tenants.id"), nullable=False, index=True),
        sa.Column("patient_id", UUID(as_uuid=True), sa.ForeignKey("patients.id"), nullable=True),
        sa.Column("facility_id", UUID(as_uuid=True), sa.ForeignKey("facilities.id"), nullable=True),
        sa.Column("channel", sa.String(32), nullable=False),
        sa.Column("action", sa.String(16), nullable=False),
        sa.Column("reason", sa.String(64), nullable=True),
        sa.Column("actor_user_id", UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )

    # ── LANGUAGE PREFERENCES ──────────────────────────────────────────
    op.create_table(
        "language_preferences",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("tenant_id", UUID(as_uuid=True), sa.ForeignKey("tenants.id"), nullable=False, index=True),
        sa.Column("patient_id", UUID(as_uuid=True), sa.ForeignKey("patients.id"), nullable=False, index=True),
        sa.Column("primary_language", sa.String(64), nullable=False, server_default=sa.text("'en'")),
        sa.Column("secondary_language", sa.String(64), nullable=True),
        sa.Column("interpreter_required", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("interpreter_language", sa.String(64), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now(), nullable=False),
    )

    # ── CONTACT POLICY AUDIT EVENTS ───────────────────────────────────
    op.create_table(
        "contact_policy_audit_events",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("tenant_id", UUID(as_uuid=True), sa.ForeignKey("tenants.id"), nullable=False, index=True),
        sa.Column("patient_id", UUID(as_uuid=True), sa.ForeignKey("patients.id"), nullable=True),
        sa.Column("facility_id", UUID(as_uuid=True), sa.ForeignKey("facilities.id"), nullable=True),
        sa.Column("action", sa.String(64), nullable=False),
        sa.Column("previous_state", JSONB(), nullable=True),
        sa.Column("new_state", JSONB(), nullable=True),
        sa.Column("actor_user_id", UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("correlation_id", sa.String(64), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )

    op.create_table = _original_create_table  # type: ignore[assignment]


def downgrade() -> None:
    op.drop_table("contact_policy_audit_events")
    op.drop_table("language_preferences")
    op.drop_table("communication_opt_out_events")
    op.drop_table("contact_preferences")
    op.drop_table("relationship_summary_snapshots")
    op.drop_table("facility_warning_flags")
    op.drop_table("patient_warning_flags")
    op.drop_table("internal_account_notes")
    op.drop_table("relationship_timeline_events")
    op.drop_table("facility_audit_events")
    op.drop_table("facility_friction_flags")
    op.drop_table("facility_service_profiles")
    op.drop_table("facility_relationship_notes")
    op.drop_table("facility_contacts")
    op.drop_table("facilities")
    op.drop_table("responsibility_audit_events")
    op.drop_table("insurance_subscriber_profiles")
    op.drop_table("patient_responsible_party_links")
    op.drop_table("responsible_parties")
    op.drop_table("patient_relationship_flags")
    op.drop_table("patient_merge_audit_events")
    op.drop_table("patient_merge_requests")
    op.drop_table("patient_duplicate_candidates")
    op.drop_index("ix_patient_identifiers_source_value", table_name="patient_identifiers")
    op.drop_table("patient_identifiers")
    op.drop_table("patient_aliases")
