"""GPS / unit location retention sweep worker.

Purpose:
  - Soft-delete stale unit GPS telemetry from `unit_locations` after a short window.
  - Enforce tenant isolation (RLS) by setting `app.tenant_id` per-tenant.
  - Write sweep outcomes to `audit_logs` (no raw coordinates).

Run via the main worker loop:
  asyncio.create_task(_gps_retention_loop(stop_event))
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
import uuid
from datetime import UTC, datetime, timedelta
from typing import Any

from sqlalchemy import text

logger = logging.getLogger(__name__)


RETENTION_DAYS = int(os.getenv("GPS_RETENTION_DAYS", "30"))
SWEEP_INTERVAL_SECONDS = int(os.getenv("GPS_RETENTION_SWEEP_INTERVAL_SECONDS", str(6 * 3600)))


def _cutoff() -> datetime:
    return datetime.now(UTC) - timedelta(days=RETENTION_DAYS)


def _list_tenants(db: Any) -> list[uuid.UUID]:
    rows = db.execute(text("SELECT id FROM tenants")).mappings().all()
    out: list[uuid.UUID] = []
    for r in rows:
        try:
            out.append(uuid.UUID(str(r["id"])))
        except Exception:
            continue
    return out


def _set_tenant_context(db: Any, tenant_id: uuid.UUID) -> None:
    # Required for tenant-scoped tables protected by RLS.
    db.execute(
        text("SELECT set_config('app.tenant_id', :tid, true)"),
        {"tid": str(tenant_id)},
    )


def _sweep_unit_locations_for_tenant(db: Any, tenant_id: uuid.UUID, cutoff: datetime) -> int:
    _set_tenant_context(db, tenant_id)
    result = db.execute(
        text(
            """
            UPDATE unit_locations
            SET deleted_at = NOW(), updated_at = NOW()
            WHERE deleted_at IS NULL
              AND created_at < :cutoff
            """
        ),
        {"cutoff": cutoff},
    )
    return int(result.rowcount or 0)


def _audit_sweep(db: Any, *, tenant_id: uuid.UUID, deleted: int, cutoff: datetime) -> None:
    # Avoid raw telemetry in audit_logs; record only aggregate action.
    db.execute(
        text(
            """
            INSERT INTO audit_logs (
                tenant_id,
                actor_user_id,
                action,
                entity_name,
                entity_id,
                field_changes,
                correlation_id,
                created_at
            ) VALUES (
                :tenant_id,
                NULL,
                'retention',
                'unit_locations',
                :entity_id,
                CAST(:field_changes AS jsonb),
                NULL,
                NOW()
            )
            """
        ),
        {
            "tenant_id": str(tenant_id),
            "entity_id": str(uuid.UUID(int=0)),
            "field_changes": json.dumps(
                {
                    "retention_days": RETENTION_DAYS,
                    "cutoff": cutoff.isoformat(),
                    "deleted": deleted,
                    "redacted": True,
                }
            ),
        },
    )


async def run_retention_sweep(db_session_factory: Any) -> dict[str, int]:
    stats: dict[str, int] = {"unit_locations": 0, "tenants": 0}
    cutoff = _cutoff()
    try:
        with db_session_factory() as db:
            tenants = _list_tenants(db)
            stats["tenants"] = len(tenants)
            total_deleted = 0
            for tenant_id in tenants:
                deleted = _sweep_unit_locations_for_tenant(db, tenant_id, cutoff)
                if deleted:
                    _audit_sweep(db, tenant_id=tenant_id, deleted=deleted, cutoff=cutoff)
                total_deleted += deleted
            db.commit()
            stats["unit_locations"] = total_deleted
            if total_deleted:
                logger.info(
                    "GPS retention sweep: soft-deleted %d unit_locations rows (cutoff=%s)",
                    total_deleted,
                    cutoff.isoformat(),
                )
            else:
                logger.debug("GPS retention sweep: no unit_locations past cutoff=%s", cutoff.isoformat())
    except Exception as exc:
        logger.error("GPS retention sweep error: %s", exc)
    return stats


async def _gps_retention_loop(stop: asyncio.Event) -> None:
    await asyncio.sleep(120)
    while not stop.is_set():
        try:
            from core_app.db.session import get_db_session_ctx

            await run_retention_sweep(get_db_session_ctx)
        except Exception as exc:
            logger.error("GPS retention loop error: %s", exc)
        await asyncio.sleep(SWEEP_INTERVAL_SECONDS)
