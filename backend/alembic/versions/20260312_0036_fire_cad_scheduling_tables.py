# pylint: skip-file
# pyright: reportCallIssue=false, reportAttributeAccessIssue=false

"""Add Fire/NERIS, CAD, and Scheduling domain tables.

Adds typed tables for:
  - Fire: fire_neris_incidents, fire_neris_personnel, fire_neris_apparatus,
    fire_preplans_v2, fire_hydrants_v2, fire_inspections, neris_export_jobs
  - CAD: cad_calls, cad_units, cad_unit_assignments, cad_timeline_events,
    cad_unit_status_events
  - Scheduling: scheduling_shift_templates, scheduling_shift_instances,
    scheduling_swap_requests, scheduling_availability, scheduling_time_off,
    scheduling_credentials, scheduling_fatigue_assessments,
    scheduling_coverage_rules

Revision ID: 20260312_0036
Revises: 20260311_0035
Create Date: 2026-03-12
"""

from typing import Any, Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB, UUID

revision: str = "20260312_0036"
down_revision: Union[str, None] = "20260311_0035"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

_TENANT_IDX = True  # all tables get tenant_id index


def upgrade() -> None:
    bind = op.get_bind()
    _original_create_table = op.create_table

    def _safe_create_table(table_name: str, *columns: Any, **kwargs: Any) -> Any:
        if sa.inspect(bind).has_table(table_name):
            return None
        return _original_create_table(table_name, *columns, **kwargs)

    op.create_table = _safe_create_table  # type: ignore[assignment]

    # ── Fire / NERIS Tables ───────────────────────────────────────────────

    op.create_table(
        "fire_neris_incidents",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("tenant_id", UUID(as_uuid=True), nullable=False, index=True),
        sa.Column("incident_number", sa.String(30), nullable=False),
        sa.Column("incident_date", sa.DateTime(timezone=True), nullable=False),
        sa.Column("incident_type", sa.String(30), nullable=False),
        sa.Column("neris_incident_type_code", sa.String(10)),
        sa.Column("alarm_date", sa.DateTime(timezone=True)),
        sa.Column("arrival_date", sa.DateTime(timezone=True)),
        sa.Column("controlled_date", sa.DateTime(timezone=True)),
        sa.Column("last_unit_cleared_date", sa.DateTime(timezone=True)),
        sa.Column("shift", sa.String(10)),
        sa.Column("district", sa.String(20)),
        sa.Column("station", sa.String(20)),
        sa.Column("exposure_number", sa.Integer(), server_default="0"),
        sa.Column("street_address", sa.String(255)),
        sa.Column("city", sa.String(100)),
        sa.Column("state", sa.String(2)),
        sa.Column("zip_code", sa.String(10)),
        sa.Column("latitude", sa.Float()),
        sa.Column("longitude", sa.Float()),
        sa.Column("property_use_code", sa.String(10)),
        sa.Column("mixed_use", sa.String(10)),
        sa.Column("census_tract", sa.String(20)),
        sa.Column("area_of_origin_code", sa.String(10)),
        sa.Column("heat_source_code", sa.String(10)),
        sa.Column("item_first_ignited_code", sa.String(10)),
        sa.Column("cause_of_ignition_code", sa.String(10)),
        sa.Column("factor_contributing_code", sa.String(10)),
        sa.Column("human_factor_code", sa.String(10)),
        sa.Column("property_loss_dollars", sa.Integer(), server_default="0"),
        sa.Column("contents_loss_dollars", sa.Integer(), server_default="0"),
        sa.Column("property_value_dollars", sa.Integer()),
        sa.Column("contents_value_dollars", sa.Integer()),
        sa.Column("narrative", sa.Text()),
        sa.Column("validation_issues", JSONB()),
        sa.Column("export_state", sa.String(20), server_default="DRAFT"),
        sa.Column("locked", sa.Boolean(), server_default=sa.text("false")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    op.create_table(
        "fire_neris_personnel",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("incident_id", UUID(as_uuid=True), sa.ForeignKey("fire_neris_incidents.id"), nullable=False),
        sa.Column("member_id", sa.String(50), nullable=False),
        sa.Column("role", sa.String(50), nullable=False),
        sa.Column("activity_code", sa.String(10)),
        sa.Column("injury", sa.Boolean(), server_default=sa.text("false")),
        sa.Column("injury_type_code", sa.String(10)),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    op.create_table(
        "fire_neris_apparatus",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("incident_id", UUID(as_uuid=True), sa.ForeignKey("fire_neris_incidents.id"), nullable=False),
        sa.Column("unit_id", sa.String(30), nullable=False),
        sa.Column("apparatus_type_code", sa.String(10)),
        sa.Column("dispatch_time", sa.DateTime(timezone=True)),
        sa.Column("enroute_time", sa.DateTime(timezone=True)),
        sa.Column("arrival_time", sa.DateTime(timezone=True)),
        sa.Column("clear_time", sa.DateTime(timezone=True)),
        sa.Column("actions_taken", JSONB()),
        sa.Column("personnel_count", sa.Integer(), server_default="0"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    op.create_table(
        "fire_preplans_v2",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("tenant_id", UUID(as_uuid=True), nullable=False, index=True),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("address", sa.String(300), nullable=False),
        sa.Column("latitude", sa.Float()),
        sa.Column("longitude", sa.Float()),
        sa.Column("occupancy_type", sa.String(50)),
        sa.Column("construction_type", sa.String(50)),
        sa.Column("stories", sa.Integer()),
        sa.Column("sprinkler_system", sa.Boolean(), server_default=sa.text("false")),
        sa.Column("standpipe", sa.Boolean(), server_default=sa.text("false")),
        sa.Column("fire_alarm_system", sa.Boolean(), server_default=sa.text("false")),
        sa.Column("hazards", JSONB()),
        sa.Column("contacts", JSONB()),
        sa.Column("notes", sa.Text()),
        sa.Column("floor_plans_s3_keys", JSONB()),
        sa.Column("last_reviewed_at", sa.DateTime(timezone=True)),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    op.create_table(
        "fire_hydrants_v2",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("tenant_id", UUID(as_uuid=True), nullable=False, index=True),
        sa.Column("hydrant_number", sa.String(50), nullable=False),
        sa.Column("latitude", sa.Float(), nullable=False),
        sa.Column("longitude", sa.Float(), nullable=False),
        sa.Column("flow_rate_gpm", sa.Integer()),
        sa.Column("static_pressure_psi", sa.Integer()),
        sa.Column("hydrant_type", sa.String(30)),
        sa.Column("color_code", sa.String(20)),
        sa.Column("in_service", sa.Boolean(), server_default=sa.text("true")),
        sa.Column("last_tested_at", sa.DateTime(timezone=True)),
        sa.Column("notes", sa.Text()),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    op.create_table(
        "fire_inspections",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("tenant_id", UUID(as_uuid=True), nullable=False, index=True),
        sa.Column("preplan_id", UUID(as_uuid=True), sa.ForeignKey("fire_preplans_v2.id")),
        sa.Column("inspector_id", UUID(as_uuid=True)),
        sa.Column("status", sa.String(30), server_default="SCHEDULED"),
        sa.Column("scheduled_date", sa.DateTime(timezone=True)),
        sa.Column("completed_date", sa.DateTime(timezone=True)),
        sa.Column("findings", JSONB()),
        sa.Column("deficiencies", JSONB()),
        sa.Column("corrective_due_date", sa.DateTime(timezone=True)),
        sa.Column("photos_s3_keys", JSONB()),
        sa.Column("notes", sa.Text()),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    op.create_table(
        "neris_export_jobs",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("tenant_id", UUID(as_uuid=True), nullable=False, index=True),
        sa.Column("incident_ids", JSONB()),
        sa.Column("record_count", sa.Integer(), server_default="0"),
        sa.Column("state", sa.String(20), server_default="DRAFT"),
        sa.Column("validation_results", JSONB()),
        sa.Column("export_file_s3_key", sa.String(500)),
        sa.Column("submitted_at", sa.DateTime(timezone=True)),
        sa.Column("response_received_at", sa.DateTime(timezone=True)),
        sa.Column("response_blob", JSONB()),
        sa.Column("error_message", sa.Text()),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    # ── CAD Tables ────────────────────────────────────────────────────────

    op.create_table(
        "cad_calls",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("tenant_id", UUID(as_uuid=True), nullable=False, index=True),
        sa.Column("call_number", sa.String(30), nullable=False),
        sa.Column("state", sa.String(20), server_default="NEW"),
        sa.Column("priority", sa.String(20)),
        sa.Column("caller_name", sa.String(200)),
        sa.Column("caller_phone", sa.String(20)),
        sa.Column("callback_number", sa.String(20)),
        sa.Column("address", sa.String(300)),
        sa.Column("city", sa.String(100)),
        sa.Column("cross_street", sa.String(200)),
        sa.Column("latitude", sa.Float()),
        sa.Column("longitude", sa.Float()),
        sa.Column("nature_of_call", sa.String(200)),
        sa.Column("chief_complaint", sa.String(200)),
        sa.Column("acuity_score", sa.Integer()),
        sa.Column("recommended_level", sa.String(10)),
        sa.Column("triage_notes", sa.Text()),
        sa.Column("intake_answers", JSONB()),
        sa.Column("call_received_at", sa.DateTime(timezone=True)),
        sa.Column("dispatch_time", sa.DateTime(timezone=True)),
        sa.Column("first_enroute_time", sa.DateTime(timezone=True)),
        sa.Column("first_on_scene_time", sa.DateTime(timezone=True)),
        sa.Column("transport_time", sa.DateTime(timezone=True)),
        sa.Column("hospital_arrival_time", sa.DateTime(timezone=True)),
        sa.Column("cleared_time", sa.DateTime(timezone=True)),
        sa.Column("incident_id", UUID(as_uuid=True)),
        sa.Column("epcr_id", UUID(as_uuid=True)),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    op.create_table(
        "cad_units",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("tenant_id", UUID(as_uuid=True), nullable=False, index=True),
        sa.Column("unit_name", sa.String(30), nullable=False),
        sa.Column("unit_type", sa.String(30), nullable=False),
        sa.Column("service_level", sa.String(10)),
        sa.Column("state", sa.String(30), server_default="AVAILABLE"),
        sa.Column("station", sa.String(30)),
        sa.Column("latitude", sa.Float()),
        sa.Column("longitude", sa.Float()),
        sa.Column("last_gps_update", sa.DateTime(timezone=True)),
        sa.Column("readiness_score", sa.Integer(), server_default="100"),
        sa.Column("crew_ids", JSONB()),
        sa.Column("capabilities", JSONB()),
        sa.Column("active", sa.Boolean(), server_default=sa.text("true")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    op.create_table(
        "cad_unit_assignments",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("call_id", UUID(as_uuid=True), sa.ForeignKey("cad_calls.id"), nullable=False),
        sa.Column("unit_id", UUID(as_uuid=True), nullable=False),
        sa.Column("unit_name", sa.String(30), nullable=False),
        sa.Column("assigned_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("enroute_at", sa.DateTime(timezone=True)),
        sa.Column("on_scene_at", sa.DateTime(timezone=True)),
        sa.Column("cleared_at", sa.DateTime(timezone=True)),
        sa.Column("primary", sa.Boolean(), server_default=sa.text("false")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    op.create_table(
        "cad_timeline_events",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("call_id", UUID(as_uuid=True), sa.ForeignKey("cad_calls.id"), nullable=False),
        sa.Column("event_type", sa.String(50), nullable=False),
        sa.Column("description", sa.Text()),
        sa.Column("actor_id", UUID(as_uuid=True)),
        sa.Column("unit_id", UUID(as_uuid=True)),
        sa.Column("metadata_blob", JSONB()),
        sa.Column("occurred_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    op.create_table(
        "cad_unit_status_events",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("tenant_id", UUID(as_uuid=True), nullable=False, index=True),
        sa.Column("unit_id", UUID(as_uuid=True), nullable=False),
        sa.Column("old_state", sa.String(30)),
        sa.Column("new_state", sa.String(30), nullable=False),
        sa.Column("reason", sa.String(200)),
        sa.Column("actor_id", UUID(as_uuid=True)),
        sa.Column("occurred_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    # ── Scheduling Tables ─────────────────────────────────────────────────

    op.create_table(
        "scheduling_shift_templates",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("tenant_id", UUID(as_uuid=True), nullable=False, index=True),
        sa.Column("name", sa.String(100), nullable=False),
        sa.Column("pattern_type", sa.String(30), nullable=False),
        sa.Column("shift_hours", sa.Integer(), nullable=False),
        sa.Column("off_hours", sa.Integer(), nullable=False),
        sa.Column("rotation_days", sa.Integer()),
        sa.Column("start_time", sa.String(5), server_default="07:00"),
        sa.Column("min_crew", sa.Integer(), server_default="2"),
        sa.Column("required_roles", JSONB()),
        sa.Column("active", sa.Boolean(), server_default=sa.text("true")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    op.create_table(
        "scheduling_shift_instances",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("tenant_id", UUID(as_uuid=True), nullable=False, index=True),
        sa.Column("template_id", UUID(as_uuid=True), sa.ForeignKey("scheduling_shift_templates.id")),
        sa.Column("user_id", UUID(as_uuid=True), nullable=False, index=True),
        sa.Column("unit_id", UUID(as_uuid=True)),
        sa.Column("station", sa.String(30)),
        sa.Column("role", sa.String(50)),
        sa.Column("start_dt", sa.DateTime(timezone=True), nullable=False),
        sa.Column("end_dt", sa.DateTime(timezone=True), nullable=False),
        sa.Column("actual_start_dt", sa.DateTime(timezone=True)),
        sa.Column("actual_end_dt", sa.DateTime(timezone=True)),
        sa.Column("overtime", sa.Boolean(), server_default=sa.text("false")),
        sa.Column("notes", sa.Text()),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    op.create_table(
        "scheduling_swap_requests",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("tenant_id", UUID(as_uuid=True), nullable=False, index=True),
        sa.Column("requester_id", UUID(as_uuid=True), nullable=False),
        sa.Column("requester_shift_id", UUID(as_uuid=True), sa.ForeignKey("scheduling_shift_instances.id"), nullable=False),
        sa.Column("acceptor_id", UUID(as_uuid=True)),
        sa.Column("acceptor_shift_id", UUID(as_uuid=True), sa.ForeignKey("scheduling_shift_instances.id")),
        sa.Column("state", sa.String(20), server_default="REQUESTED"),
        sa.Column("reason", sa.Text()),
        sa.Column("approver_id", UUID(as_uuid=True)),
        sa.Column("approved_at", sa.DateTime(timezone=True)),
        sa.Column("denied_reason", sa.Text()),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    op.create_table(
        "scheduling_availability",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("tenant_id", UUID(as_uuid=True), nullable=False, index=True),
        sa.Column("user_id", UUID(as_uuid=True), nullable=False, index=True),
        sa.Column("available", sa.Boolean(), server_default=sa.text("true")),
        sa.Column("start_dt", sa.DateTime(timezone=True), nullable=False),
        sa.Column("end_dt", sa.DateTime(timezone=True), nullable=False),
        sa.Column("reason", sa.String(200)),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    op.create_table(
        "scheduling_time_off",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("tenant_id", UUID(as_uuid=True), nullable=False, index=True),
        sa.Column("user_id", UUID(as_uuid=True), nullable=False, index=True),
        sa.Column("start_date", sa.DateTime(timezone=True), nullable=False),
        sa.Column("end_date", sa.DateTime(timezone=True), nullable=False),
        sa.Column("category", sa.String(30), server_default="PTO"),
        sa.Column("status", sa.String(20), server_default="PENDING"),
        sa.Column("approver_id", UUID(as_uuid=True)),
        sa.Column("notes", sa.Text()),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    op.create_table(
        "scheduling_credentials",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("tenant_id", UUID(as_uuid=True), nullable=False, index=True),
        sa.Column("user_id", UUID(as_uuid=True), nullable=False, index=True),
        sa.Column("credential_type", sa.String(50), nullable=False),
        sa.Column("credential_number", sa.String(100)),
        sa.Column("issuing_authority", sa.String(200)),
        sa.Column("issued_date", sa.DateTime(timezone=True)),
        sa.Column("expiry_date", sa.DateTime(timezone=True)),
        sa.Column("state", sa.String(30), server_default="ACTIVE"),
        sa.Column("document_s3_key", sa.String(500)),
        sa.Column("verified", sa.Boolean(), server_default=sa.text("false")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    op.create_table(
        "scheduling_fatigue_assessments",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("tenant_id", UUID(as_uuid=True), nullable=False, index=True),
        sa.Column("user_id", UUID(as_uuid=True), nullable=False, index=True),
        sa.Column("kss_score", sa.Integer()),
        sa.Column("hours_on_duty", sa.Float()),
        sa.Column("hours_since_last_sleep", sa.Float()),
        sa.Column("calls_this_shift", sa.Integer(), server_default="0"),
        sa.Column("fatigue_risk_level", sa.String(20), server_default="LOW"),
        sa.Column("assessment_notes", sa.Text()),
        sa.Column("fit_for_duty", sa.Boolean(), server_default=sa.text("true")),
        sa.Column("assessed_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    op.create_table(
        "scheduling_coverage_rules",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("tenant_id", UUID(as_uuid=True), nullable=False, index=True),
        sa.Column("name", sa.String(100), nullable=False),
        sa.Column("station", sa.String(30)),
        sa.Column("unit_type", sa.String(30)),
        sa.Column("min_personnel", sa.Integer(), server_default="2"),
        sa.Column("required_roles", JSONB()),
        sa.Column("effective_from", sa.DateTime(timezone=True)),
        sa.Column("effective_to", sa.DateTime(timezone=True)),
        sa.Column("active", sa.Boolean(), server_default=sa.text("true")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    op.create_table = _original_create_table  # type: ignore[assignment]


def downgrade() -> None:
    # Scheduling
    op.drop_table("scheduling_coverage_rules")
    op.drop_table("scheduling_fatigue_assessments")
    op.drop_table("scheduling_credentials")
    op.drop_table("scheduling_time_off")
    op.drop_table("scheduling_availability")
    op.drop_table("scheduling_swap_requests")
    op.drop_table("scheduling_shift_instances")
    op.drop_table("scheduling_shift_templates")
    # CAD
    op.drop_table("cad_unit_status_events")
    op.drop_table("cad_timeline_events")
    op.drop_table("cad_unit_assignments")
    op.drop_table("cad_units")
    op.drop_table("cad_calls")
    # Fire
    op.drop_table("neris_export_jobs")
    op.drop_table("fire_inspections")
    op.drop_table("fire_hydrants_v2")
    op.drop_table("fire_preplans_v2")
    op.drop_table("fire_neris_apparatus")
    op.drop_table("fire_neris_personnel")
    op.drop_table("fire_neris_incidents")
