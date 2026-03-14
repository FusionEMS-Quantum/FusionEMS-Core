import uuid
from datetime import UTC, datetime
from typing import Any

from sqlalchemy.orm import Session

from core_app.models.audit_log import AuditLog


class AuditService:
    def __init__(self, db: Session) -> None:
        self.db = db

    def _redact_field_changes(self, *, entity_name: str, field_changes: dict[str, Any]) -> dict[str, Any]:
        if entity_name != "unit_locations":
            return field_changes

        def _scrub(obj: Any) -> Any:
            if isinstance(obj, dict):
                redacted: dict[str, Any] = {}
                for key, value in obj.items():
                    if key in {"lat", "lng", "latitude", "longitude", "location", "coordinates", "coords"}:
                        redacted[key] = "[REDACTED]"
                        continue
                    if key == "points":
                        redacted["points"] = "[REDACTED]"
                        redacted["points_count"] = len(value) if isinstance(value, list) else None
                        continue
                    redacted[key] = _scrub(value)
                return redacted
            if isinstance(obj, list):
                return [_scrub(v) for v in obj]
            return obj

        scrubbed = _scrub(field_changes)
        return scrubbed if isinstance(scrubbed, dict) else field_changes

    def log_mutation(
        self,
        *,
        tenant_id: uuid.UUID,
        action: str,
        entity_name: str,
        entity_id: uuid.UUID,
        actor_user_id: uuid.UUID | None,
        field_changes: dict,
        correlation_id: str | None,
    ) -> AuditLog:
        sanitized = self._redact_field_changes(entity_name=entity_name, field_changes=field_changes)
        entry = AuditLog(
            tenant_id=tenant_id,
            actor_user_id=actor_user_id,
            action=action,
            entity_name=entity_name,
            entity_id=entity_id,
            field_changes=sanitized,
            correlation_id=correlation_id,
            created_at=datetime.now(UTC),
        )
        self.db.add(entry)
        self.db.flush()
        return entry
