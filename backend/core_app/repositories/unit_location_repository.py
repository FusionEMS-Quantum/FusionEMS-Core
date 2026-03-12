from __future__ import annotations

import uuid
from typing import Any

from sqlalchemy import text
from sqlalchemy.orm import Session


class UnitLocationRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def list_latest_by_unit(
        self,
        *,
        tenant_id: uuid.UUID,
        limit: int = 500,
    ) -> list[dict[str, Any]]:
                # Note: use created_at for ordering (server-authoritative, parse-safe).
                # We intentionally avoid casting lat/lng in SQL to prevent query failure
                # if legacy rows contain non-numeric values.
        sql = text(
            """
            SELECT *
            FROM (
                SELECT DISTINCT ON (data->>'unit_id')
                    id AS record_id,
                    data->>'unit_id' AS unit_id,
                                        data#>>'{points,0,lat}' AS lat,
                                        data#>>'{points,0,lng}' AS lng,
                    created_at AS recorded_at
                FROM unit_locations
                WHERE tenant_id = :tenant_id
                  AND deleted_at IS NULL
                ORDER BY data->>'unit_id', created_at DESC
            ) t
            WHERE t.unit_id IS NOT NULL
              AND t.lat IS NOT NULL
              AND t.lng IS NOT NULL
            LIMIT :limit
            """
        )
        rows = (
            self.db.execute(sql, {"tenant_id": str(tenant_id), "limit": limit})
            .mappings()
            .all()
        )
        return [dict(r) for r in rows]
