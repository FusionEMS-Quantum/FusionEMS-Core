"""Add founder specialty/records/integration command domain tables.

Revision ID: 20260308_0037
Revises: 20260312_0036
Create Date: 2026-03-08
"""

from typing import Any, Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB, UUID

revision: str = "20260308_0037"
down_revision: Union[str, None] = "20260312_0036"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    _original_create_table = op.create_table

    def _safe_create_table(table_name: str, *columns: Any, **kwargs: Any) -> Any:
        if sa.inspect(bind).has_table(table_name):
            return None
        return _original_create_table(table_name, *columns, **kwargs)

    op.create_table = _safe_create_table  # type: ignore[assignment]

    # Specialty Ops domain
    op.create_table(
        "premise_preplans",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("tenant_id", UUID(as_uuid=True), nullable=False),
        sa.Column("premise_name", sa.String(length=255), nullable=False),
        sa.Column("premise_address", sa.String(length=512), nullable=False),
        sa.Column("state", sa.String(length=64), nullable=False, server_default="PREPLAN_MISSING"),
        sa.Column("source_system", sa.String(length=128), nullable=False, server_default="manual"),
        sa.Column("source_timestamp", sa.DateTime(timezone=True), nullable=False),
        sa.Column("occupancy_type", sa.String(length=64), nullable=True),
        sa.Column("building_notes", sa.Text(), nullable=True),
        sa.Column("knox_fdc_notes", sa.Text(), nullable=True),
        sa.Column("command_support_notes", sa.Text(), nullable=True),
        sa.Column("accountability_references", JSONB(), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_premise_preplans_tenant_id", "premise_preplans", ["tenant_id"])
    op.create_index("ix_premise_preplans_state", "premise_preplans", ["state"])

    op.create_table(
        "hydrant_references",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("tenant_id", UUID(as_uuid=True), nullable=False),
        sa.Column("premise_preplan_id", UUID(as_uuid=True), sa.ForeignKey("premise_preplans.id"), nullable=False),
        sa.Column("hydrant_identifier", sa.String(length=128), nullable=False),
        sa.Column("latitude", sa.Float(), nullable=True),
        sa.Column("longitude", sa.Float(), nullable=True),
        sa.Column("static_pressure_psi", sa.Integer(), nullable=True),
        sa.Column("flow_rate_gpm", sa.Integer(), nullable=True),
        sa.Column("in_service", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("last_tested_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_hydrant_references_tenant_id", "hydrant_references", ["tenant_id"])
    op.create_index("ix_hydrant_references_preplan", "hydrant_references", ["premise_preplan_id"])

    op.create_table(
        "water_supply_notes",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("tenant_id", UUID(as_uuid=True), nullable=False),
        sa.Column("premise_preplan_id", UUID(as_uuid=True), sa.ForeignKey("premise_preplans.id"), nullable=False),
        sa.Column("note", sa.Text(), nullable=False),
        sa.Column("source", sa.String(length=128), nullable=False),
        sa.Column("recorded_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_water_supply_notes_tenant_id", "water_supply_notes", ["tenant_id"])
    op.create_index("ix_water_supply_notes_preplan", "water_supply_notes", ["premise_preplan_id"])

    op.create_table(
        "hazard_flags",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("tenant_id", UUID(as_uuid=True), nullable=False),
        sa.Column("premise_preplan_id", UUID(as_uuid=True), sa.ForeignKey("premise_preplans.id"), nullable=False),
        sa.Column("hazard_type", sa.String(length=128), nullable=False),
        sa.Column("severity", sa.String(length=32), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("source", sa.String(length=128), nullable=False),
        sa.Column("source_timestamp", sa.DateTime(timezone=True), nullable=False),
        sa.Column("details", JSONB(), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_hazard_flags_tenant_id", "hazard_flags", ["tenant_id"])
    op.create_index("ix_hazard_flags_preplan", "hazard_flags", ["premise_preplan_id"])
    op.create_index("ix_hazard_flags_active", "hazard_flags", ["is_active"])

    op.create_table(
        "fire_ops_audit_events",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("tenant_id", UUID(as_uuid=True), nullable=False),
        sa.Column("entity_type", sa.String(length=64), nullable=False),
        sa.Column("entity_id", UUID(as_uuid=True), nullable=False),
        sa.Column("event_type", sa.String(length=128), nullable=False),
        sa.Column("actor_user_id", UUID(as_uuid=True), nullable=True),
        sa.Column("correlation_id", sa.String(length=64), nullable=True),
        sa.Column("event_payload", JSONB(), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_fire_ops_audit_events_tenant_id", "fire_ops_audit_events", ["tenant_id"])

    op.create_table(
        "air_assets",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("tenant_id", UUID(as_uuid=True), nullable=False),
        sa.Column("asset_name", sa.String(length=255), nullable=False),
        sa.Column("callsign", sa.String(length=64), nullable=False),
        sa.Column("tail_number", sa.String(length=64), nullable=False),
        sa.Column("state", sa.String(length=64), nullable=False, server_default="AIR_ASSET_READY"),
        sa.Column("readiness_notes", sa.Text(), nullable=True),
        sa.Column("duty_minutes_remaining", sa.Integer(), nullable=True),
        sa.Column("capability_profile", JSONB(), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_air_assets_tenant_id", "air_assets", ["tenant_id"])
    op.create_index("ix_air_assets_callsign", "air_assets", ["callsign"])

    op.create_table(
        "flight_missions",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("tenant_id", UUID(as_uuid=True), nullable=False),
        sa.Column("mission_number", sa.String(length=128), nullable=False),
        sa.Column("air_asset_id", UUID(as_uuid=True), sa.ForeignKey("air_assets.id"), nullable=True),
        sa.Column("state", sa.String(length=64), nullable=False, server_default="LZ_PENDING"),
        sa.Column("origin", sa.String(length=255), nullable=True),
        sa.Column("destination", sa.String(length=255), nullable=True),
        sa.Column("receiving_facility_notes", sa.Text(), nullable=True),
        sa.Column("scheduled_departure_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("actual_departure_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("actual_arrival_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_flight_missions_tenant_id", "flight_missions", ["tenant_id"])
    op.create_index("ix_flight_missions_mission_number", "flight_missions", ["mission_number"])
    op.create_index("ix_flight_missions_state", "flight_missions", ["state"])

    op.create_table(
        "flight_leg_events",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("tenant_id", UUID(as_uuid=True), nullable=False),
        sa.Column("flight_mission_id", UUID(as_uuid=True), sa.ForeignKey("flight_missions.id"), nullable=False),
        sa.Column("leg_index", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("event_type", sa.String(length=128), nullable=False),
        sa.Column("event_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("payload", JSONB(), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_flight_leg_events_tenant_id", "flight_leg_events", ["tenant_id"])
    op.create_index("ix_flight_leg_events_mission", "flight_leg_events", ["flight_mission_id"])

    op.create_table(
        "landing_zone_records",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("tenant_id", UUID(as_uuid=True), nullable=False),
        sa.Column("flight_mission_id", UUID(as_uuid=True), sa.ForeignKey("flight_missions.id"), nullable=False),
        sa.Column("lz_name", sa.String(length=255), nullable=False),
        sa.Column("latitude", sa.Float(), nullable=True),
        sa.Column("longitude", sa.Float(), nullable=True),
        sa.Column("state", sa.String(length=64), nullable=False, server_default="LZ_PENDING"),
        sa.Column("approach_notes", sa.Text(), nullable=True),
        sa.Column("hazards", JSONB(), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("verified_by_user_id", UUID(as_uuid=True), nullable=True),
        sa.Column("verified_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_landing_zone_records_tenant_id", "landing_zone_records", ["tenant_id"])
    op.create_index("ix_landing_zone_records_mission", "landing_zone_records", ["flight_mission_id"])
    op.create_index("ix_landing_zone_records_state", "landing_zone_records", ["state"])

    op.create_table(
        "duty_time_flags",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("tenant_id", UUID(as_uuid=True), nullable=False),
        sa.Column("air_asset_id", UUID(as_uuid=True), sa.ForeignKey("air_assets.id"), nullable=True),
        sa.Column("crew_user_id", UUID(as_uuid=True), nullable=True),
        sa.Column("severity", sa.String(length=32), nullable=False),
        sa.Column("message", sa.Text(), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_duty_time_flags_tenant_id", "duty_time_flags", ["tenant_id"])
    op.create_index("ix_duty_time_flags_air_asset", "duty_time_flags", ["air_asset_id"])
    op.create_index("ix_duty_time_flags_active", "duty_time_flags", ["is_active"])

    op.create_table(
        "flight_ops_audit_events",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("tenant_id", UUID(as_uuid=True), nullable=False),
        sa.Column("entity_type", sa.String(length=64), nullable=False),
        sa.Column("entity_id", UUID(as_uuid=True), nullable=False),
        sa.Column("event_type", sa.String(length=128), nullable=False),
        sa.Column("actor_user_id", UUID(as_uuid=True), nullable=True),
        sa.Column("correlation_id", sa.String(length=64), nullable=True),
        sa.Column("event_payload", JSONB(), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_flight_ops_audit_events_tenant_id", "flight_ops_audit_events", ["tenant_id"])

    op.create_table(
        "specialty_mission_requirements",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("tenant_id", UUID(as_uuid=True), nullable=False),
        sa.Column("mission_ref", sa.String(length=128), nullable=False),
        sa.Column("requirement_type", sa.String(length=128), nullable=False),
        sa.Column("severity", sa.String(length=32), nullable=False),
        sa.Column("state", sa.String(length=64), nullable=False, server_default="SPECIALTY_FLAGGED"),
        sa.Column("details", JSONB(), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_specialty_mission_requirements_tenant_id", "specialty_mission_requirements", ["tenant_id"])
    op.create_index("ix_specialty_mission_requirements_mission_ref", "specialty_mission_requirements", ["mission_ref"])

    op.create_table(
        "specialty_equipment_checks",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("tenant_id", UUID(as_uuid=True), nullable=False),
        sa.Column("mission_requirement_id", UUID(as_uuid=True), sa.ForeignKey("specialty_mission_requirements.id"), nullable=False),
        sa.Column("equipment_code", sa.String(length=128), nullable=False),
        sa.Column("required_quantity", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("available_quantity", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("state", sa.String(length=64), nullable=False, server_default="EQUIPMENT_PENDING"),
        sa.Column("last_checked_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_specialty_equipment_checks_tenant_id", "specialty_equipment_checks", ["tenant_id"])
    op.create_index("ix_specialty_equipment_checks_requirement", "specialty_equipment_checks", ["mission_requirement_id"])

    op.create_table(
        "mission_fit_scores",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("tenant_id", UUID(as_uuid=True), nullable=False),
        sa.Column("mission_ref", sa.String(length=128), nullable=False),
        sa.Column("unit_ref", sa.String(length=128), nullable=False),
        sa.Column("score", sa.Integer(), nullable=False),
        sa.Column("crew_fit_score", sa.Integer(), nullable=False),
        sa.Column("equipment_fit_score", sa.Integer(), nullable=False),
        sa.Column("state", sa.String(length=64), nullable=False, server_default="READY"),
        sa.Column("calculated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("blocked_reason", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_mission_fit_scores_tenant_id", "mission_fit_scores", ["tenant_id"])
    op.create_index("ix_mission_fit_scores_mission_ref", "mission_fit_scores", ["mission_ref"])
    op.create_index("ix_mission_fit_scores_state", "mission_fit_scores", ["state"])

    op.create_table(
        "specialty_transport_audit_events",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("tenant_id", UUID(as_uuid=True), nullable=False),
        sa.Column("entity_type", sa.String(length=64), nullable=False),
        sa.Column("entity_id", UUID(as_uuid=True), nullable=False),
        sa.Column("event_type", sa.String(length=128), nullable=False),
        sa.Column("actor_user_id", UUID(as_uuid=True), nullable=True),
        sa.Column("correlation_id", sa.String(length=64), nullable=True),
        sa.Column("event_payload", JSONB(), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_specialty_transport_audit_events_tenant_id", "specialty_transport_audit_events", ["tenant_id"])

    op.create_table(
        "mission_packets",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("tenant_id", UUID(as_uuid=True), nullable=False),
        sa.Column("mission_ref", sa.String(length=128), nullable=False),
        sa.Column("state", sa.String(length=64), nullable=False, server_default="NOT_PREPARED"),
        sa.Column("source_record_hash", sa.String(length=128), nullable=False),
        sa.Column("generated_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("delivered_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("failure_reason", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_mission_packets_tenant_id", "mission_packets", ["tenant_id"])
    op.create_index("ix_mission_packets_mission_ref", "mission_packets", ["mission_ref"])
    op.create_index("ix_mission_packets_state", "mission_packets", ["state"])

    op.create_table(
        "mission_packet_sections",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("tenant_id", UUID(as_uuid=True), nullable=False),
        sa.Column("mission_packet_id", UUID(as_uuid=True), sa.ForeignKey("mission_packets.id"), nullable=False),
        sa.Column("section_type", sa.String(length=128), nullable=False),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("sort_order", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("payload", JSONB(), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_mission_packet_sections_tenant_id", "mission_packet_sections", ["tenant_id"])
    op.create_index("ix_mission_packet_sections_packet", "mission_packet_sections", ["mission_packet_id"])

    op.create_table(
        "mission_packet_deliveries",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("tenant_id", UUID(as_uuid=True), nullable=False),
        sa.Column("mission_packet_id", UUID(as_uuid=True), sa.ForeignKey("mission_packets.id"), nullable=False),
        sa.Column("destination_type", sa.String(length=64), nullable=False),
        sa.Column("destination_ref", sa.String(length=255), nullable=False),
        sa.Column("state", sa.String(length=64), nullable=False, server_default="DRAFTED"),
        sa.Column("delivered_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_mission_packet_deliveries_tenant_id", "mission_packet_deliveries", ["tenant_id"])
    op.create_index("ix_mission_packet_deliveries_packet", "mission_packet_deliveries", ["mission_packet_id"])

    op.create_table(
        "mission_packet_audit_events",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("tenant_id", UUID(as_uuid=True), nullable=False),
        sa.Column("entity_type", sa.String(length=64), nullable=False),
        sa.Column("entity_id", UUID(as_uuid=True), nullable=False),
        sa.Column("event_type", sa.String(length=128), nullable=False),
        sa.Column("actor_user_id", UUID(as_uuid=True), nullable=True),
        sa.Column("correlation_id", sa.String(length=64), nullable=True),
        sa.Column("event_payload", JSONB(), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_mission_packet_audit_events_tenant_id", "mission_packet_audit_events", ["tenant_id"])

    # Records/media domain
    op.create_table(
        "clinical_records",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("tenant_id", UUID(as_uuid=True), nullable=False),
        sa.Column("incident_number", sa.String(length=128), nullable=False),
        sa.Column("patient_external_ref", sa.String(length=128), nullable=True),
        sa.Column("lifecycle_state", sa.String(length=64), nullable=False, server_default="DRAFT"),
        sa.Column("source_system", sa.String(length=128), nullable=False),
        sa.Column("source_timestamp", sa.DateTime(timezone=True), nullable=False),
        sa.Column("sealed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("locked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_clinical_records_tenant_id", "clinical_records", ["tenant_id"])
    op.create_index("ix_clinical_records_incident_number", "clinical_records", ["incident_number"])
    op.create_index("ix_clinical_records_lifecycle_state", "clinical_records", ["lifecycle_state"])

    op.create_table(
        "record_sections",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("tenant_id", UUID(as_uuid=True), nullable=False),
        sa.Column("clinical_record_id", UUID(as_uuid=True), sa.ForeignKey("clinical_records.id"), nullable=False),
        sa.Column("section_type", sa.String(length=128), nullable=False),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("payload", JSONB(), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("hash_sha256", sa.String(length=128), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_record_sections_tenant_id", "record_sections", ["tenant_id"])
    op.create_index("ix_record_sections_record", "record_sections", ["clinical_record_id"])

    op.create_table(
        "document_artifacts",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("tenant_id", UUID(as_uuid=True), nullable=False),
        sa.Column("clinical_record_id", UUID(as_uuid=True), sa.ForeignKey("clinical_records.id"), nullable=False),
        sa.Column("artifact_type", sa.String(length=128), nullable=False),
        sa.Column("file_name", sa.String(length=255), nullable=False),
        sa.Column("mime_type", sa.String(length=128), nullable=False),
        sa.Column("storage_uri", sa.String(length=1024), nullable=False),
        sa.Column("byte_size", sa.Integer(), nullable=False),
        sa.Column("checksum_sha256", sa.String(length=128), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_document_artifacts_tenant_id", "document_artifacts", ["tenant_id"])
    op.create_index("ix_document_artifacts_record", "document_artifacts", ["clinical_record_id"])

    op.create_table(
        "signature_captures",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("tenant_id", UUID(as_uuid=True), nullable=False),
        sa.Column("clinical_record_id", UUID(as_uuid=True), sa.ForeignKey("clinical_records.id"), nullable=False),
        sa.Column("signer_role", sa.String(length=64), nullable=False),
        sa.Column("signature_state", sa.String(length=64), nullable=False, server_default="MISSING"),
        sa.Column("captured_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("verification_method", sa.String(length=128), nullable=True),
        sa.Column("failure_reason", sa.Text(), nullable=True),
        sa.Column("evidence_payload", JSONB(), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_signature_captures_tenant_id", "signature_captures", ["tenant_id"])
    op.create_index("ix_signature_captures_record", "signature_captures", ["clinical_record_id"])
    op.create_index("ix_signature_captures_state", "signature_captures", ["signature_state"])

    op.create_table(
        "ocr_processing_results",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("tenant_id", UUID(as_uuid=True), nullable=False),
        sa.Column("document_artifact_id", UUID(as_uuid=True), sa.ForeignKey("document_artifacts.id"), nullable=False),
        sa.Column("engine", sa.String(length=128), nullable=False),
        sa.Column("confidence_band", sa.String(length=16), nullable=False, server_default="MEDIUM"),
        sa.Column("confidence_score", sa.Integer(), nullable=False),
        sa.Column("extracted_payload", JSONB(), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("extraction_warnings", JSONB(), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_ocr_processing_results_tenant_id", "ocr_processing_results", ["tenant_id"])
    op.create_index("ix_ocr_processing_results_artifact", "ocr_processing_results", ["document_artifact_id"])
    op.create_index("ix_ocr_processing_results_band", "ocr_processing_results", ["confidence_band"])

    op.create_table(
        "chain_of_custody_events",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("tenant_id", UUID(as_uuid=True), nullable=False),
        sa.Column("clinical_record_id", UUID(as_uuid=True), sa.ForeignKey("clinical_records.id"), nullable=False),
        sa.Column("state", sa.String(length=32), nullable=False, server_default="CLEAN"),
        sa.Column("event_type", sa.String(length=128), nullable=False),
        sa.Column("actor_user_id", UUID(as_uuid=True), nullable=True),
        sa.Column("evidence", JSONB(), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_chain_of_custody_events_tenant_id", "chain_of_custody_events", ["tenant_id"])
    op.create_index("ix_chain_of_custody_events_record", "chain_of_custody_events", ["clinical_record_id"])
    op.create_index("ix_chain_of_custody_events_state", "chain_of_custody_events", ["state"])

    op.create_table(
        "compliance_packets",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("tenant_id", UUID(as_uuid=True), nullable=False),
        sa.Column("clinical_record_id", UUID(as_uuid=True), sa.ForeignKey("clinical_records.id"), nullable=False),
        sa.Column("packet_type", sa.String(length=128), nullable=False),
        sa.Column("packet_version", sa.String(length=64), nullable=False),
        sa.Column("rendered_artifact_id", UUID(as_uuid=True), sa.ForeignKey("document_artifacts.id"), nullable=True),
        sa.Column("generated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_compliance_packets_tenant_id", "compliance_packets", ["tenant_id"])
    op.create_index("ix_compliance_packets_record", "compliance_packets", ["clinical_record_id"])

    op.create_table(
        "legal_holds",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("tenant_id", UUID(as_uuid=True), nullable=False),
        sa.Column("clinical_record_id", UUID(as_uuid=True), sa.ForeignKey("clinical_records.id"), nullable=False),
        sa.Column("reason", sa.Text(), nullable=False),
        sa.Column("hold_owner", sa.String(length=128), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("activated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("released_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_legal_holds_tenant_id", "legal_holds", ["tenant_id"])
    op.create_index("ix_legal_holds_record", "legal_holds", ["clinical_record_id"])

    op.create_table(
        "release_authorizations",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("tenant_id", UUID(as_uuid=True), nullable=False),
        sa.Column("clinical_record_id", UUID(as_uuid=True), sa.ForeignKey("clinical_records.id"), nullable=False),
        sa.Column("requestor", sa.String(length=255), nullable=False),
        sa.Column("purpose", sa.String(length=255), nullable=False),
        sa.Column("approved_by_user_id", UUID(as_uuid=True), nullable=True),
        sa.Column("approved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("decision_notes", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_release_authorizations_tenant_id", "release_authorizations", ["tenant_id"])
    op.create_index("ix_release_authorizations_record", "release_authorizations", ["clinical_record_id"])

    op.create_table(
        "record_exports",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("tenant_id", UUID(as_uuid=True), nullable=False),
        sa.Column("clinical_record_id", UUID(as_uuid=True), sa.ForeignKey("clinical_records.id"), nullable=False),
        sa.Column("destination_system", sa.String(length=128), nullable=False),
        sa.Column("state", sa.String(length=32), nullable=False, server_default="QUEUED"),
        sa.Column("queued_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("delivered_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("failure_reason", sa.Text(), nullable=True),
        sa.Column("delivery_payload", JSONB(), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_record_exports_tenant_id", "record_exports", ["tenant_id"])
    op.create_index("ix_record_exports_record", "record_exports", ["clinical_record_id"])
    op.create_index("ix_record_exports_state", "record_exports", ["state"])

    op.create_table(
        "qa_exceptions",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("tenant_id", UUID(as_uuid=True), nullable=False),
        sa.Column("clinical_record_id", UUID(as_uuid=True), sa.ForeignKey("clinical_records.id"), nullable=False),
        sa.Column("rule_code", sa.String(length=128), nullable=False),
        sa.Column("severity", sa.String(length=32), nullable=False),
        sa.Column("state", sa.String(length=32), nullable=False, server_default="OPEN"),
        sa.Column("details", JSONB(), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("remediated_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_qa_exceptions_tenant_id", "qa_exceptions", ["tenant_id"])
    op.create_index("ix_qa_exceptions_record", "qa_exceptions", ["clinical_record_id"])
    op.create_index("ix_qa_exceptions_state", "qa_exceptions", ["state"])

    op.create_table(
        "records_audit_events",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("tenant_id", UUID(as_uuid=True), nullable=False),
        sa.Column("entity_type", sa.String(length=64), nullable=False),
        sa.Column("entity_id", UUID(as_uuid=True), nullable=False),
        sa.Column("event_type", sa.String(length=128), nullable=False),
        sa.Column("actor_user_id", UUID(as_uuid=True), nullable=True),
        sa.Column("correlation_id", sa.String(length=64), nullable=True),
        sa.Column("event_payload", JSONB(), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_records_audit_events_tenant_id", "records_audit_events", ["tenant_id"])

    # Integration domain
    op.create_table(
        "connector_catalog",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("connector_key", sa.String(length=128), nullable=False),
        sa.Column("display_name", sa.String(length=255), nullable=False),
        sa.Column("category", sa.String(length=128), nullable=False),
        sa.Column("capabilities", JSONB(), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("auth_modes", JSONB(), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("enabled_by_default", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint("connector_key", name="uq_connector_catalog_connector_key"),
    )
    op.create_index("ix_connector_catalog_connector_key", "connector_catalog", ["connector_key"])

    op.create_table(
        "connector_profiles",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("tenant_id", UUID(as_uuid=True), nullable=False),
        sa.Column("connector_catalog_id", UUID(as_uuid=True), sa.ForeignKey("connector_catalog.id"), nullable=False),
        sa.Column("profile_name", sa.String(length=255), nullable=False),
        sa.Column("install_state", sa.String(length=32), nullable=False, server_default="CONFIG_PENDING"),
        sa.Column("endpoint_base_url", sa.String(length=1024), nullable=True),
        sa.Column("config_payload", JSONB(), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("validation_report", JSONB(), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("last_validated_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_connector_profiles_tenant_id", "connector_profiles", ["tenant_id"])
    op.create_index("ix_connector_profiles_catalog", "connector_profiles", ["connector_catalog_id"])

    op.create_table(
        "tenant_connector_installs",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("tenant_id", UUID(as_uuid=True), nullable=False),
        sa.Column("connector_profile_id", UUID(as_uuid=True), sa.ForeignKey("connector_profiles.id"), nullable=False),
        sa.Column("install_state", sa.String(length=32), nullable=False, server_default="CONFIG_PENDING"),
        sa.Column("activated_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("disabled_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("disabled_reason", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_tenant_connector_installs_tenant_id", "tenant_connector_installs", ["tenant_id"])
    op.create_index("ix_tenant_connector_installs_profile", "tenant_connector_installs", ["connector_profile_id"])
    op.create_index("ix_tenant_connector_installs_state", "tenant_connector_installs", ["install_state"])

    op.create_table(
        "connector_secret_materializations",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("tenant_id", UUID(as_uuid=True), nullable=False),
        sa.Column("tenant_connector_install_id", UUID(as_uuid=True), sa.ForeignKey("tenant_connector_installs.id"), nullable=False),
        sa.Column("secret_ref", sa.String(length=255), nullable=False),
        sa.Column("materialized_by", sa.String(length=128), nullable=False, server_default="oidc-runtime"),
        sa.Column("materialized_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_connector_secret_materializations_tenant_id", "connector_secret_materializations", ["tenant_id"])
    op.create_index("ix_connector_secret_materializations_install", "connector_secret_materializations", ["tenant_connector_install_id"])

    op.create_table(
        "connector_sync_jobs",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("tenant_id", UUID(as_uuid=True), nullable=False),
        sa.Column("tenant_connector_install_id", UUID(as_uuid=True), sa.ForeignKey("tenant_connector_installs.id"), nullable=False),
        sa.Column("direction", sa.String(length=64), nullable=False),
        sa.Column("state", sa.String(length=32), nullable=False, server_default="QUEUED"),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("records_attempted", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("records_succeeded", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("records_failed", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("error_summary", JSONB(), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_connector_sync_jobs_tenant_id", "connector_sync_jobs", ["tenant_id"])
    op.create_index("ix_connector_sync_jobs_install", "connector_sync_jobs", ["tenant_connector_install_id"])
    op.create_index("ix_connector_sync_jobs_state", "connector_sync_jobs", ["state"])
    op.create_index("ix_connector_sync_jobs_created_at", "connector_sync_jobs", ["created_at"])

    op.create_table(
        "sync_dead_letters",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("tenant_id", UUID(as_uuid=True), nullable=False),
        sa.Column("connector_sync_job_id", UUID(as_uuid=True), sa.ForeignKey("connector_sync_jobs.id"), nullable=False),
        sa.Column("external_record_ref", sa.String(length=255), nullable=False),
        sa.Column("reason", sa.Text(), nullable=False),
        sa.Column("payload", JSONB(), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_sync_dead_letters_tenant_id", "sync_dead_letters", ["tenant_id"])
    op.create_index("ix_sync_dead_letters_job", "sync_dead_letters", ["connector_sync_job_id"])
    op.create_index("ix_sync_dead_letters_created_at", "sync_dead_letters", ["created_at"])

    op.create_table(
        "connector_webhook_endpoints",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("tenant_id", UUID(as_uuid=True), nullable=False),
        sa.Column("tenant_connector_install_id", UUID(as_uuid=True), sa.ForeignKey("tenant_connector_installs.id"), nullable=False),
        sa.Column("endpoint_url", sa.String(length=1024), nullable=False),
        sa.Column("signing_mode", sa.String(length=64), nullable=False, server_default="hmac-sha256"),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_connector_webhook_endpoints_tenant_id", "connector_webhook_endpoints", ["tenant_id"])
    op.create_index("ix_connector_webhook_endpoints_install", "connector_webhook_endpoints", ["tenant_connector_install_id"])

    op.create_table(
        "connector_webhook_deliveries",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("tenant_id", UUID(as_uuid=True), nullable=False),
        sa.Column("connector_webhook_endpoint_id", UUID(as_uuid=True), sa.ForeignKey("connector_webhook_endpoints.id"), nullable=False),
        sa.Column("state", sa.String(length=32), nullable=False, server_default="PENDING"),
        sa.Column("event_type", sa.String(length=128), nullable=False),
        sa.Column("payload", JSONB(), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("attempt_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("next_attempt_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("delivered_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("failure_reason", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_connector_webhook_deliveries_tenant_id", "connector_webhook_deliveries", ["tenant_id"])
    op.create_index("ix_connector_webhook_deliveries_endpoint", "connector_webhook_deliveries", ["connector_webhook_endpoint_id"])
    op.create_index("ix_connector_webhook_deliveries_state", "connector_webhook_deliveries", ["state"])

    op.create_table(
        "api_client_credentials",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("tenant_id", UUID(as_uuid=True), nullable=False),
        sa.Column("client_name", sa.String(length=255), nullable=False),
        sa.Column("client_id", sa.String(length=128), nullable=False),
        sa.Column("credential_state", sa.String(length=32), nullable=False, server_default="ACTIVE"),
        sa.Column("key_hash", sa.String(length=128), nullable=False),
        sa.Column("created_by_user_id", UUID(as_uuid=True), nullable=True),
        sa.Column("rotated_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_api_client_credentials_tenant_id", "api_client_credentials", ["tenant_id"])
    op.create_index("ix_api_client_credentials_client_id", "api_client_credentials", ["client_id"])
    op.create_index("ix_api_client_credentials_state", "api_client_credentials", ["credential_state"])

    op.create_table(
        "api_client_quotas",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("tenant_id", UUID(as_uuid=True), nullable=False),
        sa.Column("api_client_credential_id", UUID(as_uuid=True), sa.ForeignKey("api_client_credentials.id"), nullable=False),
        sa.Column("requests_per_minute", sa.Integer(), nullable=False, server_default="600"),
        sa.Column("requests_per_day", sa.Integer(), nullable=False, server_default="250000"),
        sa.Column("burst_limit", sa.Integer(), nullable=False, server_default="1200"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_api_client_quotas_tenant_id", "api_client_quotas", ["tenant_id"])
    op.create_index("ix_api_client_quotas_credential", "api_client_quotas", ["api_client_credential_id"])

    op.create_table(
        "api_client_usage_windows",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("tenant_id", UUID(as_uuid=True), nullable=False),
        sa.Column("api_client_credential_id", UUID(as_uuid=True), sa.ForeignKey("api_client_credentials.id"), nullable=False),
        sa.Column("window_start", sa.DateTime(timezone=True), nullable=False),
        sa.Column("window_end", sa.DateTime(timezone=True), nullable=False),
        sa.Column("request_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("denied_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_api_client_usage_windows_tenant_id", "api_client_usage_windows", ["tenant_id"])
    op.create_index("ix_api_client_usage_windows_credential", "api_client_usage_windows", ["api_client_credential_id"])
    op.create_index("ix_api_client_usage_windows_start", "api_client_usage_windows", ["window_start"])

    op.create_table(
        "integration_audit_events",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("tenant_id", UUID(as_uuid=True), nullable=False),
        sa.Column("entity_type", sa.String(length=64), nullable=False),
        sa.Column("entity_id", UUID(as_uuid=True), nullable=False),
        sa.Column("event_type", sa.String(length=128), nullable=False),
        sa.Column("actor_user_id", UUID(as_uuid=True), nullable=True),
        sa.Column("correlation_id", sa.String(length=64), nullable=True),
        sa.Column("event_payload", JSONB(), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_integration_audit_events_tenant_id", "integration_audit_events", ["tenant_id"])

    op.create_table = _original_create_table  # type: ignore[assignment]


def downgrade() -> None:
    op.drop_table("integration_audit_events")
    op.drop_table("api_client_usage_windows")
    op.drop_table("api_client_quotas")
    op.drop_table("api_client_credentials")
    op.drop_table("connector_webhook_deliveries")
    op.drop_table("connector_webhook_endpoints")
    op.drop_table("sync_dead_letters")
    op.drop_table("connector_sync_jobs")
    op.drop_table("connector_secret_materializations")
    op.drop_table("tenant_connector_installs")
    op.drop_table("connector_profiles")
    op.drop_table("connector_catalog")

    op.drop_table("records_audit_events")
    op.drop_table("qa_exceptions")
    op.drop_table("record_exports")
    op.drop_table("release_authorizations")
    op.drop_table("legal_holds")
    op.drop_table("compliance_packets")
    op.drop_table("chain_of_custody_events")
    op.drop_table("ocr_processing_results")
    op.drop_table("signature_captures")
    op.drop_table("document_artifacts")
    op.drop_table("record_sections")
    op.drop_table("clinical_records")

    op.drop_table("mission_packet_audit_events")
    op.drop_table("mission_packet_deliveries")
    op.drop_table("mission_packet_sections")
    op.drop_table("mission_packets")
    op.drop_table("specialty_transport_audit_events")
    op.drop_table("mission_fit_scores")
    op.drop_table("specialty_equipment_checks")
    op.drop_table("specialty_mission_requirements")
    op.drop_table("flight_ops_audit_events")
    op.drop_table("duty_time_flags")
    op.drop_table("landing_zone_records")
    op.drop_table("flight_leg_events")
    op.drop_table("flight_missions")
    op.drop_table("air_assets")
    op.drop_table("fire_ops_audit_events")
    op.drop_table("hazard_flags")
    op.drop_table("water_supply_notes")
    op.drop_table("hydrant_references")
    op.drop_table("premise_preplans")
