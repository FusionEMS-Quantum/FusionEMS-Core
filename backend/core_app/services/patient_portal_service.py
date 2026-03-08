"""Patient Portal Service — portal access, statements, messages, payments.

Provides patient-facing read operations for billing statements, messages,
payment history, and authorization representative management.
"""
from __future__ import annotations

import logging
import uuid
from typing import Any

from sqlalchemy.orm import Session

from core_app.services.domination_service import DominationService
from core_app.services.event_publisher import EventPublisher

logger = logging.getLogger(__name__)


class PatientPortalService:
    """Patient-facing service layer for portal access."""

    def __init__(self, db: Session, publisher: EventPublisher) -> None:
        self.db = db
        self.publisher = publisher
        self._svc = DominationService(db, publisher)

    async def get_patient_statements(
        self, *, tenant_id: uuid.UUID, patient_account_id: uuid.UUID
    ) -> list[dict[str, Any]]:
        """Retrieve billing statements for a patient."""
        items = self._svc.repo("billing_statements").list(
            tenant_id=tenant_id, limit=200
        )
        return [
            s for s in items
            if s.get("data", {}).get("patient_account_id") == str(patient_account_id)
        ]

    async def get_payment_history(
        self, *, tenant_id: uuid.UUID, patient_account_id: uuid.UUID
    ) -> list[dict[str, Any]]:
        """Retrieve payment history for a patient."""
        items = self._svc.repo("payment_events").list(
            tenant_id=tenant_id, limit=500
        )
        return [
            p for p in items
            if p.get("data", {}).get("patient_account_id") == str(patient_account_id)
        ]

    async def get_patient_messages(
        self, *, tenant_id: uuid.UUID, patient_account_id: uuid.UUID
    ) -> list[dict[str, Any]]:
        """Retrieve communication messages for a patient."""
        items = self._svc.repo("communication_messages").list(
            tenant_id=tenant_id, limit=100
        )
        return [
            m for m in items
            if m.get("data", {}).get("patient_account_id") == str(patient_account_id)
        ]

    async def get_authorized_reps(
        self, *, tenant_id: uuid.UUID, patient_account_id: uuid.UUID
    ) -> list[dict[str, Any]]:
        """Retrieve authorized representatives for a patient."""
        items = self._svc.repo("authorized_reps").list(
            tenant_id=tenant_id, limit=100
        )
        return [
            r for r in items
            if r.get("data", {}).get("patient_account_id") == str(patient_account_id)
        ]

    async def submit_payment(
        self,
        *,
        tenant_id: uuid.UUID,
        patient_account_id: uuid.UUID,
        actor_user_id: uuid.UUID | None,
        data: dict[str, Any],
        correlation_id: str | None = None,
    ) -> dict[str, Any]:
        """Record a patient-initiated payment."""
        payment_data = {
            "patient_account_id": str(patient_account_id),
            "amount": data["amount"],
            "payment_method": data.get("payment_method", "card"),
            "reference": data.get("reference"),
            "source": "patient_portal",
        }
        result = await self._svc.create(
            table="payment_events",
            tenant_id=tenant_id,
            actor_user_id=actor_user_id,
            data=payment_data,
            correlation_id=correlation_id,
        )
        await self.publisher.publish(
            "patient_portal.payment_submitted",
            tenant_id=tenant_id,
            entity_id=uuid.UUID(result["id"]),
            payload=payment_data,
            entity_type="payment",
            correlation_id=correlation_id,
        )
        return result

    async def send_message(
        self,
        *,
        tenant_id: uuid.UUID,
        patient_account_id: uuid.UUID,
        actor_user_id: uuid.UUID | None,
        data: dict[str, Any],
        correlation_id: str | None = None,
    ) -> dict[str, Any]:
        """Send a message from the patient portal."""
        msg_data = {
            "patient_account_id": str(patient_account_id),
            "subject": data.get("subject", ""),
            "body": data["body"],
            "direction": "inbound",
            "source": "patient_portal",
        }
        return await self._svc.create(
            table="communication_messages",
            tenant_id=tenant_id,
            actor_user_id=actor_user_id,
            data=msg_data,
            correlation_id=correlation_id,
        )
