"""
FusionEMS-Core — Development Database Seed Script
Seeds a local/dev database with deterministic test data for founder development.

Usage:
    python backend/scripts/seed_dev_db.py

Creates:
    - System tenant with known UUID
    - Demo agency (tenant)
    - Founder user
    - Sample patients, incidents, billing cases
    - Compliance pack assignments
    - CrewLink crew members and device registrations
"""
from __future__ import annotations

import os
import sys
import uuid
from datetime import UTC, datetime, timedelta

# Ensure backend is on path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

os.environ.setdefault("DATABASE_URL", "postgresql+psycopg2://postgres:postgres@localhost:5432/fusionems")
os.environ.setdefault("SECRET_KEY", "dev-seed-key-not-for-production")
os.environ.setdefault("ENVIRONMENT", "development")
os.environ.setdefault("REDIS_URL", "redis://localhost:6379")

from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session, sessionmaker

DATABASE_URL = os.environ["DATABASE_URL"]

# ── Deterministic UUIDs (stable across runs) ─────────────────────────────────
SYSTEM_TENANT_ID = uuid.UUID("00000000-0000-0000-0000-000000000001")
DEMO_TENANT_ID = uuid.UUID("10000000-0000-0000-0000-000000000001")
FOUNDER_USER_ID = uuid.UUID("20000000-0000-0000-0000-000000000001")
MEDIC_USER_ID = uuid.UUID("20000000-0000-0000-0000-000000000002")
DISPATCH_USER_ID = uuid.UUID("20000000-0000-0000-0000-000000000003")
PATIENT_1_ID = uuid.UUID("30000000-0000-0000-0000-000000000001")
PATIENT_2_ID = uuid.UUID("30000000-0000-0000-0000-000000000002")
INCIDENT_1_ID = uuid.UUID("40000000-0000-0000-0000-000000000001")
CREW_MEMBER_1_ID = uuid.UUID("50000000-0000-0000-0000-000000000001")
CREW_MEMBER_2_ID = uuid.UUID("50000000-0000-0000-0000-000000000002")

NOW = datetime.now(UTC)


def _utcnow() -> str:
    return NOW.isoformat()


def _seed_domination_record(
    db: Session,
    *,
    table: str,
    record_id: uuid.UUID,
    tenant_id: uuid.UUID,
    data: dict,
) -> None:
    """Insert a record into a domination-pattern JSONB table if it doesn't exist."""
    check = db.execute(
        text(f"SELECT id FROM {table} WHERE id = :id"),  # noqa: S608
        {"id": str(record_id)},
    ).fetchone()
    if check:
        print(f"  ↳ {table} {record_id} already exists, skipping")
        return

    db.execute(
        text(
            f"INSERT INTO {table} (id, tenant_id, version, data, created_at, updated_at) "  # noqa: S608
            "VALUES (:id, :tid, 1, :data::jsonb, :now, :now)"
        ),
        {
            "id": str(record_id),
            "tid": str(tenant_id),
            "data": __import__("json").dumps(data),
            "now": _utcnow(),
        },
    )
    print(f"  ✓ {table} {record_id}")


def seed(db: Session) -> None:
    print("\n╔══════════════════════════════════════════════════════════════╗")
    print("║          FusionEMS-Core — Dev Database Seed                 ║")
    print("╚══════════════════════════════════════════════════════════════╝\n")

    # ── Tenants ───────────────────────────────────────────────────────
    print("[1/6] Seeding tenants...")
    _seed_domination_record(
        db,
        table="tenants",
        record_id=SYSTEM_TENANT_ID,
        tenant_id=SYSTEM_TENANT_ID,
        data={
            "name": "FusionEMS System",
            "slug": "system",
            "tier": "founder",
            "status": "active",
            "created_at": _utcnow(),
        },
    )
    _seed_domination_record(
        db,
        table="tenants",
        record_id=DEMO_TENANT_ID,
        tenant_id=DEMO_TENANT_ID,
        data={
            "name": "Metro EMS Demo Agency",
            "slug": "metro-ems-demo",
            "tier": "professional",
            "status": "active",
            "npi": "1234567890",
            "state_license": "EMS-DEMO-001",
            "service_levels": ["ALS", "BLS", "CCT"],
            "created_at": _utcnow(),
        },
    )

    # ── Users ─────────────────────────────────────────────────────────
    print("[2/6] Seeding users...")
    _seed_domination_record(
        db,
        table="users",
        record_id=FOUNDER_USER_ID,
        tenant_id=DEMO_TENANT_ID,
        data={
            "email": "founder@fusionems.dev",
            "name": "Alex Founder",
            "role": "founder",
            "status": "active",
            "permissions": ["admin", "billing", "dispatch", "clinical", "compliance"],
            "created_at": _utcnow(),
        },
    )
    _seed_domination_record(
        db,
        table="users",
        record_id=MEDIC_USER_ID,
        tenant_id=DEMO_TENANT_ID,
        data={
            "email": "medic@fusionems.dev",
            "name": "Jordan Medic",
            "role": "paramedic",
            "status": "active",
            "certifications": ["NRP", "ACLS", "PALS"],
            "created_at": _utcnow(),
        },
    )
    _seed_domination_record(
        db,
        table="users",
        record_id=DISPATCH_USER_ID,
        tenant_id=DEMO_TENANT_ID,
        data={
            "email": "dispatch@fusionems.dev",
            "name": "Pat Dispatch",
            "role": "dispatcher",
            "status": "active",
            "created_at": _utcnow(),
        },
    )

    # ── Patients ──────────────────────────────────────────────────────
    print("[3/6] Seeding patients...")
    _seed_domination_record(
        db,
        table="patients",
        record_id=PATIENT_1_ID,
        tenant_id=DEMO_TENANT_ID,
        data={
            "first_name": "Jane",
            "last_name": "TestPatient",
            "dob": "1985-03-15",
            "gender": "female",
            "ssn_last4": "1234",
            "address": "123 Main St, Springfield, IL 62701",
            "phone": "+15555551234",
            "insurance_carrier": "Blue Cross Blue Shield",
            "insurance_policy": "BCBS-98765",
            "identity_state": "VERIFIED",
            "created_at": _utcnow(),
        },
    )
    _seed_domination_record(
        db,
        table="patients",
        record_id=PATIENT_2_ID,
        tenant_id=DEMO_TENANT_ID,
        data={
            "first_name": "John",
            "last_name": "TestPatient",
            "dob": "1972-08-22",
            "gender": "male",
            "ssn_last4": "5678",
            "address": "456 Oak Ave, Springfield, IL 62702",
            "phone": "+15555555678",
            "insurance_carrier": "Aetna",
            "insurance_policy": "AET-54321",
            "identity_state": "VERIFIED",
            "created_at": _utcnow(),
        },
    )

    # ── Incidents ─────────────────────────────────────────────────────
    print("[4/6] Seeding incidents...")
    dispatch_time = (NOW - timedelta(hours=2)).isoformat()
    _seed_domination_record(
        db,
        table="incidents",
        record_id=INCIDENT_1_ID,
        tenant_id=DEMO_TENANT_ID,
        data={
            "incident_number": "INC-2026-00001",
            "status": "IN_PROGRESS",
            "dispatch_time": dispatch_time,
            "service_level": "ALS",
            "chief_complaint": "Chest pain, 68yo male",
            "location_address": "789 Elm St, Springfield, IL 62703",
            "location_lat": 39.7817,
            "location_lng": -89.6502,
            "patient_id": str(PATIENT_2_ID),
            "assigned_unit": "MEDIC-1",
            "assigned_crew": [str(MEDIC_USER_ID)],
            "disposition": None,
            "created_at": _utcnow(),
        },
    )

    # ── Billing Cases ─────────────────────────────────────────────────
    print("[5/6] Seeding billing cases...")
    _seed_domination_record(
        db,
        table="billing_cases",
        record_id=uuid.UUID("60000000-0000-0000-0000-000000000001"),
        tenant_id=DEMO_TENANT_ID,
        data={
            "incident_id": str(INCIDENT_1_ID),
            "patient_id": str(PATIENT_2_ID),
            "status": "READY_FOR_SUBMISSION",
            "claim_state": "DRAFT",
            "total_billed_cents": 185000,
            "service_level": "ALS",
            "hcpcs_code": "A0427",
            "hcpcs_description": "ALS, Emergency, Non-Emergency",
            "mileage_loaded": 12.4,
            "pickup_zip": "62703",
            "dropoff_zip": "62701",
            "insurance_carrier": "Aetna",
            "insurance_policy": "AET-54321",
            "patient_balance_status": "INSURANCE_PENDING",
            "created_at": _utcnow(),
        },
    )

    # ── CrewLink Members ──────────────────────────────────────────────
    print("[6/6] Seeding CrewLink crew...")
    _seed_domination_record(
        db,
        table="crew_members",
        record_id=CREW_MEMBER_1_ID,
        tenant_id=DEMO_TENANT_ID,
        data={
            "user_id": str(MEDIC_USER_ID),
            "name": "Jordan Medic",
            "role": "paramedic",
            "certifications": ["NRP", "ACLS"],
            "shift_status": "on_duty",
            "unit_assignment": "MEDIC-1",
            "created_at": _utcnow(),
        },
    )
    _seed_domination_record(
        db,
        table="crew_members",
        record_id=CREW_MEMBER_2_ID,
        tenant_id=DEMO_TENANT_ID,
        data={
            "user_id": str(DISPATCH_USER_ID),
            "name": "Pat Dispatch",
            "role": "dispatcher",
            "certifications": ["EMD"],
            "shift_status": "on_duty",
            "unit_assignment": "DISPATCH-1",
            "created_at": _utcnow(),
        },
    )

    db.commit()
    print("\n▸ Seed complete. All records created or verified.\n")


def main() -> None:
    engine = create_engine(DATABASE_URL)
    SessionLocal = sessionmaker(bind=engine)
    db = SessionLocal()
    try:
        seed(db)
    except Exception as exc:
        db.rollback()
        print(f"\n✗ Seed failed: {exc}")
        sys.exit(1)
    finally:
        db.close()


if __name__ == "__main__":
    main()
