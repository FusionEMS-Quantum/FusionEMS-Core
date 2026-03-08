"""Tests for FireService — NERIS validation and incident lifecycle."""
import uuid
from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock

import pytest

from core_app.services.fire_service import FireService


def _make_db() -> MagicMock:
    db = MagicMock()
    db.add = MagicMock()
    db.flush = AsyncMock()
    db.refresh = AsyncMock()
    db.commit = AsyncMock()
    db.execute = AsyncMock()
    return db


@pytest.fixture()
def service() -> FireService:
    return FireService(db=_make_db())


@pytest.fixture()
def tenant_id() -> uuid.UUID:
    return uuid.uuid4()


@pytest.fixture()
def user_id() -> uuid.UUID:
    return uuid.uuid4()


# ── Create Incident ─────────────────────────────────────────────────────────


@pytest.mark.asyncio()
async def test_create_incident_returns_dict(
    service: FireService, tenant_id: uuid.UUID, user_id: uuid.UUID
) -> None:
    result = await service.create_incident(
        tenant_id=tenant_id,
        actor_user_id=user_id,
        data={
            "incident_number": "FI-2026-001",
            "incident_type": "FIRE",
            "neris_incident_type_code": "111",
            "street_address": "100 Main St",
            "city": "Smallville",
            "state": "KS",
        },
    )
    assert result is not None
    assert "id" in result


# ── NERIS Validation ────────────────────────────────────────────────────────


def test_validate_neris_missing_fields(service: FireService, tenant_id: uuid.UUID) -> None:
    """Validate detects missing required NERIS Section A fields."""
    from core_app.models.fire import FireIncident

    incident = FireIncident(
        id=uuid.uuid4(),
        tenant_id=tenant_id,
        incident_number="FI-001",
        incident_type="FIRE",
        incident_date=datetime.now(UTC),
        export_state="DRAFT",
    )
    issues = service._validate_neris_fields(incident)
    assert len(issues) > 0
    field_paths = [i["field"] for i in issues]
    assert "neris_incident_type_code" in field_paths


def test_validate_neris_complete_incident(service: FireService, tenant_id: uuid.UUID) -> None:
    from core_app.models.fire import FireIncident

    incident = FireIncident(
        id=uuid.uuid4(),
        tenant_id=tenant_id,
        incident_number="FI-001",
        incident_type="FIRE",
        neris_incident_type_code="111",
        incident_date=datetime.now(UTC),
        alarm_date=datetime.now(UTC),
        arrival_date=datetime.now(UTC),
        street_address="100 Main St",
        city="Smallville",
        state="KS",
        zip_code="66002",
        property_use_code="419",
        area_of_origin_code="11",
        heat_source_code="10",
        item_first_ignited_code="21",
        narrative="Test narrative",
        export_state="DRAFT",
    )
    issues = service._validate_neris_fields(incident)
    errors_only = [i for i in issues if i["severity"] == "error"]
    assert len(errors_only) == 0


# ── Lock ─────────────────────────────────────────────────────────────────────


@pytest.mark.asyncio()
async def test_lock_incident(
    service: FireService, tenant_id: uuid.UUID
) -> None:
    from core_app.models.fire import FireIncident

    incident = FireIncident(
        id=uuid.uuid4(),
        tenant_id=tenant_id,
        incident_number="FI-001",
        incident_type="FIRE",
        incident_date=datetime.now(UTC),
        locked=False,
    )
    service.get_incident = AsyncMock(return_value=incident)  # type: ignore[method-assign]

    await service.lock_incident(tenant_id=tenant_id, incident_id=incident.id)
    assert incident.locked is True
