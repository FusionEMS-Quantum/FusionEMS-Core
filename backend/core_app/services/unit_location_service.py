from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy.orm import Session

from core_app.repositories.unit_location_repository import UnitLocationRepository
from core_app.schemas.unit_locations import LatestUnitLocation, LatestUnitLocationsResponse
from core_app.services.audit_service import AuditService


class UnitLocationService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.repo = UnitLocationRepository(db)
        self.audit = AuditService(db)

    def get_latest_unit_locations(
        self,
        *,
        tenant_id: uuid.UUID,
        actor_user_id: uuid.UUID | None,
        correlation_id: str | None,
        limit: int = 500,
    ) -> LatestUnitLocationsResponse:
        rows = self.repo.list_latest_by_unit(tenant_id=tenant_id, limit=limit)

        items: list[LatestUnitLocation] = []
        for row in rows:
            unit_id_raw = row.get("unit_id")
            record_id_raw = row.get("record_id")
            lat_raw = row.get("lat")
            lng_raw = row.get("lng")
            recorded_at_raw = row.get("recorded_at")

            try:
                unit_id = uuid.UUID(str(unit_id_raw))
                record_id = uuid.UUID(str(record_id_raw))
                lat = float(lat_raw)
                lng = float(lng_raw)
                recorded_at = (
                    recorded_at_raw
                    if isinstance(recorded_at_raw, datetime)
                    else datetime.fromisoformat(str(recorded_at_raw))
                )
            except Exception:
                continue

            items.append(
                LatestUnitLocation(
                    unit_id=unit_id,
                    lat=lat,
                    lng=lng,
                    recorded_at=recorded_at,
                    record_id=record_id,
                )
            )

        # Audited read (redacted; no coordinates in the audit payload).
        self.audit.log_mutation(
            tenant_id=tenant_id,
            action="read",
            entity_name="unit_locations",
            entity_id=uuid.UUID(int=0),
            actor_user_id=actor_user_id,
            field_changes={
                "access_type": "latest_per_unit",
                "returned": len(items),
                "redacted": True,
            },
            correlation_id=correlation_id,
        )
        self.db.commit()

        return LatestUnitLocationsResponse(items=items)
