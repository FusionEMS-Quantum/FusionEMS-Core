"""Auth Rep Service — authorization representative lifecycle.

Handles registration, OTP verification, revocation, consent logging,
and document management for authorized patient representatives.
"""
from __future__ import annotations

import logging
import uuid
from datetime import UTC, datetime
from typing import Any

from sqlalchemy.orm import Session

from core_app.services.domination_service import DominationService
from core_app.services.event_publisher import EventPublisher

logger = logging.getLogger(__name__)


class AuthRepService:
    """Manages authorization representative lifecycle operations."""

    def __init__(self, db: Session, publisher: EventPublisher) -> None:
        self.db = db
        self.publisher = publisher
        self._svc = DominationService(db, publisher)

    async def revoke_authorization(
        self,
        *,
        tenant_id: uuid.UUID,
        rep_id: uuid.UUID,
        actor_user_id: uuid.UUID,
        reason: str,
        correlation_id: str | None = None,
    ) -> dict[str, Any]:
        """Revoke an authorized representative's access."""
        rep = self._svc.repo("authorized_reps").get(
            tenant_id=tenant_id, record_id=rep_id
        )
        if rep is None:
            return {"error": "rep_not_found"}

        await self._svc.update(
            table="authorized_reps",
            tenant_id=tenant_id,
            actor_user_id=actor_user_id,
            record_id=rep_id,
            expected_version=rep["version"],
            patch={
                "status": "revoked",
                "revoked_at": datetime.now(UTC).isoformat(),
                "revoked_reason": reason,
            },
            correlation_id=correlation_id,
        )

        await self._log_consent_event(
            tenant_id=tenant_id,
            rep_id=rep_id,
            actor_user_id=actor_user_id,
            event_type="REVOCATION",
            detail={"reason": reason},
            correlation_id=correlation_id,
        )

        await self.publisher.publish(
            "auth_rep.revoked",
            tenant_id=tenant_id,
            entity_id=rep_id,
            payload={"rep_id": str(rep_id), "reason": reason},
            entity_type="auth_rep",
            correlation_id=correlation_id,
        )

        logger.info(
            "auth_rep_revoked",
            extra={
                "tenant_id": str(tenant_id),
                "rep_id": str(rep_id),
                "correlation_id": correlation_id,
            },
        )
        return {"rep_id": str(rep_id), "status": "revoked"}

    async def log_consent(
        self,
        *,
        tenant_id: uuid.UUID,
        rep_id: uuid.UUID,
        actor_user_id: uuid.UUID,
        consent_type: str,
        granted: bool,
        detail: dict[str, Any] | None = None,
        correlation_id: str | None = None,
    ) -> dict[str, Any]:
        """Log a consent decision for an authorization representative."""
        event_type = f"CONSENT_{'GRANTED' if granted else 'DENIED'}"
        return await self._log_consent_event(
            tenant_id=tenant_id,
            rep_id=rep_id,
            actor_user_id=actor_user_id,
            event_type=event_type,
            detail={
                "consent_type": consent_type,
                "granted": granted,
                **(detail or {}),
            },
            correlation_id=correlation_id,
        )

    async def _log_consent_event(
        self,
        *,
        tenant_id: uuid.UUID,
        rep_id: uuid.UUID,
        actor_user_id: uuid.UUID,
        event_type: str,
        detail: dict[str, Any],
        correlation_id: str | None = None,
    ) -> dict[str, Any]:
        """Internal: persist a consent audit event."""
        event_data = {
            "rep_id": str(rep_id),
            "event_type": event_type,
            "actor_user_id": str(actor_user_id),
            "detail": detail,
            "recorded_at": datetime.now(UTC).isoformat(),
        }
        return await self._svc.create(
            table="auth_rep_consent_events",
            tenant_id=tenant_id,
            actor_user_id=actor_user_id,
            data=event_data,
            correlation_id=correlation_id,
        )

    async def list_consent_events(
        self,
        *,
        tenant_id: uuid.UUID,
        rep_id: uuid.UUID,
    ) -> list[dict[str, Any]]:
        """List all consent events for a specific authorized rep."""
        events = self._svc.repo("auth_rep_consent_events").list(
            tenant_id=tenant_id, limit=500
        )
        return [
            e for e in events
            if e.get("data", {}).get("rep_id") == str(rep_id)
        ]

    async def get_rep_status(
        self,
        *,
        tenant_id: uuid.UUID,
        rep_id: uuid.UUID,
    ) -> dict[str, Any]:
        """Get current status of an authorized representative."""
        rep = self._svc.repo("authorized_reps").get(
            tenant_id=tenant_id, record_id=rep_id
        )
        if rep is None:
            return {"error": "rep_not_found"}
        data = rep.get("data", {})
        return {
            "rep_id": str(rep_id),
            "status": data.get("status", "unknown"),
            "full_name": data.get("full_name"),
            "relationship": data.get("relationship"),
            "verified_at": data.get("verified_at"),
            "signed_at": data.get("signed_at"),
            "revoked_at": data.get("revoked_at"),
        }
