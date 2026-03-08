"""Import/Overlay Service — background import processing with validation.

Handles CSV/XML import batches: validation, field mapping,
background execution, error collection, and status tracking.
"""
from __future__ import annotations

import logging
import uuid
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)


class ImportBatch:
    """In-memory representation of an import batch for processing."""

    def __init__(
        self,
        *,
        batch_id: uuid.UUID,
        tenant_id: uuid.UUID,
        source_format: str,
        vendor: str | None,
        field_mapping: dict[str, str] | None,
        records: list[dict[str, Any]],
    ) -> None:
        self.batch_id = batch_id
        self.tenant_id = tenant_id
        self.source_format = source_format
        self.vendor = vendor
        self.field_mapping = field_mapping or {}
        self.records = records
        self.errors: list[dict[str, Any]] = []
        self.imported_count = 0
        self.skipped_count = 0


class ImportService:
    """Manages overlay/import batch lifecycle: validate → map → execute → report."""

    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def validate_batch(
        self,
        *,
        records: list[dict[str, Any]],
        required_fields: list[str],
    ) -> dict[str, Any]:
        """Validate records against required fields before import."""
        errors: list[dict[str, Any]] = []
        valid_count = 0
        for idx, rec in enumerate(records):
            missing = [f for f in required_fields if not rec.get(f)]
            if missing:
                errors.append({
                    "row": idx + 1,
                    "missing_fields": missing,
                    "severity": "error",
                })
            else:
                valid_count += 1
        return {
            "total": len(records),
            "valid": valid_count,
            "invalid": len(errors),
            "errors": errors,
        }

    async def apply_field_mapping(
        self,
        *,
        records: list[dict[str, Any]],
        mapping: dict[str, str],
    ) -> list[dict[str, Any]]:
        """Apply field mapping (source_field → target_field) to records."""
        mapped: list[dict[str, Any]] = []
        for rec in records:
            new_rec: dict[str, Any] = {}
            for src_key, target_key in mapping.items():
                if src_key in rec:
                    new_rec[target_key] = rec[src_key]
            # Carry over unmapped fields
            for k, v in rec.items():
                if k not in mapping:
                    new_rec[k] = v
            mapped.append(new_rec)
        return mapped

    async def execute_batch(
        self,
        *,
        batch: ImportBatch,
        target_table: str,
        domination_svc: Any,
        actor_user_id: uuid.UUID,
        correlation_id: str | None = None,
    ) -> dict[str, Any]:
        """Execute an import batch, creating records and collecting errors."""
        for idx, rec in enumerate(batch.records):
            try:
                mapped_rec = {}
                for src, tgt in batch.field_mapping.items():
                    if src in rec:
                        mapped_rec[tgt] = rec[src]
                for k, v in rec.items():
                    if k not in batch.field_mapping:
                        mapped_rec[k] = v

                await domination_svc.create(
                    table=target_table,
                    tenant_id=batch.tenant_id,
                    actor_user_id=actor_user_id,
                    data=mapped_rec,
                    correlation_id=correlation_id,
                )
                batch.imported_count += 1
            except Exception as exc:
                batch.errors.append({
                    "row": idx + 1,
                    "error": str(exc),
                    "record_preview": {k: v for k, v in list(rec.items())[:5]},
                })
                batch.skipped_count += 1
                logger.warning(
                    "import_row_failed",
                    extra={
                        "batch_id": str(batch.batch_id),
                        "row": idx + 1,
                        "error": str(exc),
                    },
                )

        logger.info(
            "import_batch_completed",
            extra={
                "batch_id": str(batch.batch_id),
                "tenant_id": str(batch.tenant_id),
                "imported": batch.imported_count,
                "skipped": batch.skipped_count,
                "correlation_id": correlation_id,
            },
        )
        return {
            "batch_id": str(batch.batch_id),
            "status": "completed",
            "imported": batch.imported_count,
            "skipped": batch.skipped_count,
            "errors": batch.errors,
        }

    async def score_batch_completeness(
        self, *, records: list[dict[str, Any]], schema_fields: list[str]
    ) -> dict[str, Any]:
        """Score how complete a batch is against expected schema fields."""
        if not records:
            return {"completeness_pct": 0.0, "field_coverage": {}}
        field_coverage: dict[str, float] = {}
        total = len(records)
        for f in schema_fields:
            filled = sum(1 for r in records if r.get(f))
            field_coverage[f] = round(filled / total * 100, 1)
        avg = sum(field_coverage.values()) / len(field_coverage) if field_coverage else 0.0
        return {
            "completeness_pct": round(avg, 1),
            "field_coverage": field_coverage,
        }
