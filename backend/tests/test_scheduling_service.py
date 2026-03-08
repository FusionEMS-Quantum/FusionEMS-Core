"""Tests for SchedulingService — shifts, swaps, fatigue, coverage."""
import uuid
from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, MagicMock

import pytest

from core_app.services.scheduling_service import SchedulingService


def _make_db() -> MagicMock:
    db = MagicMock()
    db.add = MagicMock()
    db.flush = AsyncMock()
    db.refresh = AsyncMock()
    db.commit = AsyncMock()
    db.execute = AsyncMock()
    return db


@pytest.fixture()
def service() -> SchedulingService:
    return SchedulingService(db=_make_db())


@pytest.fixture()
def tenant_id() -> uuid.UUID:
    return uuid.uuid4()


@pytest.fixture()
def user_id() -> uuid.UUID:
    return uuid.uuid4()


# ── Template Creation ────────────────────────────────────────────────────────


@pytest.mark.asyncio()
async def test_create_template(
    service: SchedulingService, tenant_id: uuid.UUID
) -> None:
    result = await service.create_template(
        tenant_id=tenant_id,
        data={
            "name": "24/48 Rotation",
            "pattern_type": "ROTATION",
            "shift_hours": 24,
            "off_hours": 48,
        },
    )
    assert result is not None
    assert result["name"] == "24/48 Rotation"


# ── Shift Instance ───────────────────────────────────────────────────────────


@pytest.mark.asyncio()
async def test_create_shift_instance(
    service: SchedulingService, tenant_id: uuid.UUID, user_id: uuid.UUID
) -> None:
    now = datetime.now(UTC)
    result = await service.create_instance(
        tenant_id=tenant_id,
        data={
            "user_id": str(user_id),
            "start_dt": now.isoformat(),
            "end_dt": (now + timedelta(hours=24)).isoformat(),
            "role": "Paramedic",
        },
    )
    assert result is not None
    assert "id" in result


# ── Swap Request ─────────────────────────────────────────────────────────────


@pytest.mark.asyncio()
async def test_request_swap(
    service: SchedulingService, tenant_id: uuid.UUID, user_id: uuid.UUID
) -> None:
    shift_a = uuid.uuid4()
    shift_b = uuid.uuid4()
    result = await service.request_swap(
        tenant_id=tenant_id,
        requester_id=user_id,
        data={
            "requester_shift_id": str(shift_a),
            "acceptor_shift_id": str(shift_b),
            "reason": "Family event",
        },
    )
    assert result is not None
    assert result["state"] == "REQUESTED"


# ── Fatigue Assessment ───────────────────────────────────────────────────────


@pytest.mark.asyncio()
async def test_fatigue_high_risk_over_16h(
    service: SchedulingService, tenant_id: uuid.UUID, user_id: uuid.UUID
) -> None:
    result = await service.record_fatigue_assessment(
        tenant_id=tenant_id,
        user_id=user_id,
        data={
            "hours_on_duty": 18.0,
            "hours_since_last_sleep": 20.0,
            "calls_this_shift": 5,
            "kss_score": 7,
        },
    )
    assert result is not None
    assert result["fatigue_risk_level"] == "HIGH"
    assert result["fit_for_duty"] is False


@pytest.mark.asyncio()
async def test_fatigue_low_risk(
    service: SchedulingService, tenant_id: uuid.UUID, user_id: uuid.UUID
) -> None:
    result = await service.record_fatigue_assessment(
        tenant_id=tenant_id,
        user_id=user_id,
        data={
            "hours_on_duty": 6.0,
            "hours_since_last_sleep": 8.0,
            "calls_this_shift": 2,
            "kss_score": 3,
        },
    )
    assert result is not None
    assert result["fatigue_risk_level"] == "LOW"
    assert result["fit_for_duty"] is True


# ── Coverage Rule ────────────────────────────────────────────────────────────


@pytest.mark.asyncio()
async def test_create_coverage_rule(
    service: SchedulingService, tenant_id: uuid.UUID
) -> None:
    result = await service.create_coverage_rule(
        tenant_id=tenant_id,
        data={
            "name": "Min staffing Station 1",
            "station": "Station 1",
            "min_personnel": 4,
            "required_roles": ["Paramedic", "EMT"],
        },
    )
    assert result is not None
    assert result["name"] == "Min staffing Station 1"
