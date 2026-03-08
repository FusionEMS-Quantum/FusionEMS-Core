"""Tests for CADService — call lifecycle, unit management, GPS."""
import uuid
from unittest.mock import AsyncMock, MagicMock

import pytest

from core_app.services.cad_service import CADService


def _make_db() -> MagicMock:
    db = MagicMock()
    db.add = MagicMock()
    db.flush = AsyncMock()
    db.refresh = AsyncMock()
    db.commit = AsyncMock()
    db.execute = AsyncMock()
    return db


@pytest.fixture()
def service() -> CADService:
    return CADService(db=_make_db())


@pytest.fixture()
def tenant_id() -> uuid.UUID:
    return uuid.uuid4()


@pytest.fixture()
def user_id() -> uuid.UUID:
    return uuid.uuid4()


# ── Call Creation ────────────────────────────────────────────────────────────


@pytest.mark.asyncio()
async def test_create_call(
    service: CADService, tenant_id: uuid.UUID, user_id: uuid.UUID
) -> None:
    result = await service.create_call(
        tenant_id=tenant_id,
        actor_user_id=user_id,
        data={
            "caller_name": "John Doe",
            "caller_phone": "555-1234",
            "location_address": "100 Main St",
            "chief_complaint": "Chest pain",
            "priority": "DELTA",
        },
    )
    assert result is not None
    assert "id" in result
    assert result["state"] == "NEW"


# ── Call Transition ──────────────────────────────────────────────────────────


@pytest.mark.asyncio()
async def test_transition_call(
    service: CADService, tenant_id: uuid.UUID, user_id: uuid.UUID
) -> None:
    from core_app.models.cad import CADCall

    call = CADCall(
        id=uuid.uuid4(),
        tenant_id=tenant_id,
        call_number="C-001",
        state="NEW",
    )
    service.get_call = AsyncMock(return_value=call)  # type: ignore[method-assign]

    result = await service.transition_call(
        tenant_id=tenant_id,
        call_id=call.id,
        new_state="TRIAGED",
        actor_user_id=user_id,
    )
    assert result["new_state"] == "TRIAGED"


# ── Unit Registration ────────────────────────────────────────────────────────


@pytest.mark.asyncio()
async def test_register_unit(
    service: CADService, tenant_id: uuid.UUID
) -> None:
    result = await service.register_unit(
        tenant_id=tenant_id,
        data={"unit_name": "M-51", "unit_type": "ALS", "station": "Station 5"},
    )
    assert result is not None
    assert result["unit_name"] == "M-51"


# ── GPS Update ───────────────────────────────────────────────────────────────


@pytest.mark.asyncio()
async def test_update_unit_gps(
    service: CADService, tenant_id: uuid.UUID
) -> None:
    unit_id = uuid.uuid4()
    result = await service.update_unit_gps(
        tenant_id=tenant_id, unit_id=unit_id, lat=38.9, lng=-94.6
    )
    assert result is None
