"""ops_domination: dispatch, crewlink_paging, staffing, telemetry, transportlink, ops_ai

Revision ID: 20260307_0026
Revises: 20260301_0025
Create Date: 2026-03-07
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "20260307_0026"
down_revision = "20260301_0025"
branch_labels = None
depends_on = None

# All new tables for operations domination build
_TABLES = [
    # CAD / Dispatch
    "dispatch_requests",
    "dispatch_assignments",
    "dispatch_timeline_events",
    "dispatch_recommendations",
    "dispatch_overrides",
    "active_missions",
    "mission_audit_events",
    # CrewLink Paging
    "crew_paging_alerts",
    "crew_paging_recipients",
    "crew_paging_responses",
    "crew_paging_escalation_rules",
    "crew_paging_escalation_events",
    "crew_mission_assignments",
    "crew_push_devices",
    "crew_status_events",
    "crew_paging_audit_events",
    # Fleet / Telemetry
    "vehicle_telemetry_events",
    "vehicle_health_snapshots",
    "vehicle_fault_codes",
    "vehicle_maintenance_alerts",
    "vehicle_inspection_records",
    "fleet_audit_events",
    # Staffing / Response Readiness
    "crew_availability",
    "crew_qualifications",
    "crew_assignment_conflicts",
    "crew_fatigue_flags",
    "crew_readiness_scores",
    "staffing_audit_events",
    # TransportLink / Interfacility
    "facility_request_audit_events",
    "facility_request_decisions",
    "facility_portal_contacts",
    # Ops AI
    "ops_ai_issues",
    "ops_ai_recommendations",
]

# Tables that may already exist from earlier migrations
_SKIP_IF_EXISTS = {
    "crew_paging_alerts",   # Was in crewlink model
    "crew_push_devices",
}


def _table_exists(conn, table_name: str) -> bool:
    result = conn.execute(
        sa.text(
            "SELECT EXISTS (SELECT FROM information_schema.tables "
            "WHERE table_schema = 'public' AND table_name = :t)"
        ),
        {"t": table_name},
    )
    return result.scalar()


def upgrade() -> None:
    conn = op.get_bind()

    for table in _TABLES:
        if _table_exists(conn, table):
            continue

        op.create_table(
            table,
            sa.Column(
                "id",
                postgresql.UUID(as_uuid=True),
                primary_key=True,
                server_default=sa.text("gen_random_uuid()"),
            ),
            sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column("version", sa.Integer(), nullable=False, server_default="1"),
            sa.Column("data", postgresql.JSONB(), nullable=False, server_default="{}"),
            sa.Column(
                "created_at",
                sa.DateTime(timezone=True),
                nullable=False,
                server_default=sa.text("now()"),
            ),
            sa.Column(
                "updated_at",
                sa.DateTime(timezone=True),
                nullable=False,
                server_default=sa.text("now()"),
            ),
        )
        op.create_index(f"ix_{table}_tenant_id", table, ["tenant_id"])
        op.create_index(f"ix_{table}_created_at", table, ["created_at"])

    # Specialized JSONB indexes for high-frequency query paths
    _gin_indexes = [
        ("active_missions", "state"),
        ("active_missions", "service_level"),
        ("active_missions", "priority"),
        ("dispatch_requests", "state"),
        ("dispatch_assignments", "mission_id"),
        ("dispatch_timeline_events", "mission_id"),
        ("mission_audit_events", "mission_id"),
        ("crew_paging_alerts", "state"),
        ("crew_paging_alerts", "mission_id"),
        ("crew_paging_recipients", "alert_id"),
        ("crew_paging_recipients", "crew_member_id"),
        ("crew_paging_responses", "alert_id"),
        ("crew_paging_escalation_events", "alert_id"),
        ("crew_paging_audit_events", "alert_id"),
        ("crew_push_devices", "crew_member_id"),
        ("crew_status_events", "crew_member_id"),
        ("vehicle_telemetry_events", "unit_id"),
        ("vehicle_health_snapshots", "unit_id"),
        ("vehicle_fault_codes", "unit_id"),
        ("fleet_audit_events", "unit_id"),
        ("crew_availability", "crew_member_id"),
        ("crew_qualifications", "crew_member_id"),
        ("crew_assignment_conflicts", "crew_member_id"),
        ("crew_fatigue_flags", "crew_member_id"),
        ("crew_readiness_scores", "crew_member_id"),
        ("facility_request_decisions", "request_id"),
        ("facility_request_audit_events", "request_id"),
    ]

    for table, field in _gin_indexes:
        if not _table_exists(conn, table):
            continue
        idx_name = f"ix_{table}_{field}_gin"
        op.execute(
            f"CREATE INDEX IF NOT EXISTS {idx_name} "
            f"ON {table} USING gin((data->'{field}'));"
        )


def downgrade() -> None:
    conn = op.get_bind()
    for table in reversed(_TABLES):
        if _table_exists(conn, table):
            op.drop_table(table)
