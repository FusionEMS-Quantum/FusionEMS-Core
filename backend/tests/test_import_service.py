"""Tests for ImportService — batch validation, field mapping, execution."""
from unittest.mock import AsyncMock, MagicMock

import pytest

from core_app.services.import_service import ImportService


def _make_db() -> MagicMock:
    db = MagicMock()
    db.add = MagicMock()
    db.flush = AsyncMock()
    db.refresh = AsyncMock()
    db.commit = AsyncMock()
    return db


@pytest.fixture()
def service() -> ImportService:
    return ImportService(db=_make_db())


# ── Batch Validation ────────────────────────────────────────────────────────


@pytest.mark.asyncio()
async def test_validate_batch_good_data(service: ImportService) -> None:
    records = [
        {"first_name": "John", "last_name": "Doe", "dob": "1990-01-01"},
        {"first_name": "Jane", "last_name": "Smith", "dob": "1985-06-15"},
    ]
    result = await service.validate_batch(
        records=records, required_fields=["first_name", "last_name"]
    )
    assert result["valid"] == 2
    assert result["invalid"] == 0


@pytest.mark.asyncio()
async def test_validate_batch_missing_fields(service: ImportService) -> None:
    records = [
        {"first_name": "John"},
        {"first_name": "Jane", "last_name": "Smith"},
    ]
    result = await service.validate_batch(
        records=records, required_fields=["first_name", "last_name"]
    )
    assert result["valid"] == 1
    assert result["invalid"] == 1


# ── Completeness Score ───────────────────────────────────────────────────────


@pytest.mark.asyncio()
async def test_score_completeness_all_fields(service: ImportService) -> None:
    records = [
        {"a": 1, "b": 2, "c": 3},
        {"a": 1, "b": 2, "c": 3},
    ]
    result = await service.score_batch_completeness(records=records, schema_fields=["a", "b", "c"])
    assert result["completeness_pct"] == 100.0


@pytest.mark.asyncio()
async def test_score_completeness_partial(service: ImportService) -> None:
    records = [
        {"a": 1, "b": None, "c": 3},
        {"a": None, "b": 2},
    ]
    result = await service.score_batch_completeness(records=records, schema_fields=["a", "b", "c"])
    assert 0.0 < result["completeness_pct"] < 100.0


# ── Field Mapping ────────────────────────────────────────────────────────────


@pytest.mark.asyncio()
async def test_apply_field_mapping(service: ImportService) -> None:
    records = [{"FirstName": "John", "LastName": "Doe"}]
    mapping = {"FirstName": "first_name", "LastName": "last_name"}
    mapped = await service.apply_field_mapping(records=records, mapping=mapping)
    assert mapped[0]["first_name"] == "John"
    assert mapped[0]["last_name"] == "Doe"
