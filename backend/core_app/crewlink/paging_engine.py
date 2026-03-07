"""
CrewLink Paging Engine — FusionEMS-Core
Real EMS mobile paging system with full state machine, escalation,
backup crew logic, push delivery audit, and mission context.

PAGING STATE MACHINE:
  ALERT_CREATED → TARGETS_RESOLVED → PUSH_SENT → PUSH_DELIVERED →
  ACKNOWLEDGED → ACCEPTED / DECLINED / NO_RESPONSE →
  ESCALATED → BACKUP_ALERT_SENT → CLOSED

HARD RULES:
- CrewLink NEVER handles billing messages
- Every push alert is auditable
- Escalation timers are deterministic
- Backup crew logic follows explicit rules only
- Human dispatch override is always possible
"""
from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta
from enum import StrEnum
from typing import Any

from sqlalchemy.orm import Session

from core_app.services.domination_service import DominationService
from core_app.services.event_publisher import EventPublisher


class PagingState(StrEnum):
    ALERT_CREATED = "ALERT_CREATED"
    TARGETS_RESOLVED = "TARGETS_RESOLVED"
    PUSH_SENT = "PUSH_SENT"
    PUSH_DELIVERED = "PUSH_DELIVERED"
    ACKNOWLEDGED = "ACKNOWLEDGED"
    ACCEPTED = "ACCEPTED"
    DECLINED = "DECLINED"
    NO_RESPONSE = "NO_RESPONSE"
    ESCALATED = "ESCALATED"
    BACKUP_ALERT_SENT = "BACKUP_ALERT_SENT"
    CLOSED = "CLOSED"


class CrewResponse(StrEnum):
    ACKNOWLEDGE = "ACKNOWLEDGE"
    ACCEPT = "ACCEPT"
    DECLINE = "DECLINE"


# Default escalation window in seconds
DEFAULT_ACK_TIMEOUT_SECONDS = 120   # 2 min to acknowledge
DEFAULT_ACCEPT_TIMEOUT_SECONDS = 300  # 5 min to accept
DEFAULT_BACKUP_TIMEOUT_SECONDS = 180  # 3 min before backup page


class CrewLinkPagingEngine:
    """
    Real paging engine for EMS crew notification and response tracking.
    Fully separated from Telnyx and billing communications.
    """

    def __init__(
        self,
        db: Session,
        publisher: EventPublisher,
        tenant_id: uuid.UUID,
        actor_user_id: uuid.UUID | None,
    ) -> None:
        self.svc = DominationService(db, publisher)
        self.tenant_id = tenant_id
        self.actor_user_id = actor_user_id

    # ── Alert Creation ────────────────────────────────────────────────────────

    async def create_paging_alert(
        self,
        *,
        mission_id: str,
        mission_title: str,
        mission_address: str,
        service_level: str,
        priority: str,
        target_crew_ids: list[str],
        unit_id: str | None = None,
        chief_complaint: str | None = None,
        special_instructions: str | None = None,
        ack_timeout_seconds: int = DEFAULT_ACK_TIMEOUT_SECONDS,
        accept_timeout_seconds: int = DEFAULT_ACCEPT_TIMEOUT_SECONDS,
        escalation_rules: list[dict] | None = None,
        correlation_id: str | None = None,
    ) -> dict[str, Any]:
        """
        Create a new paging alert for a mission.
        Resolves targets, creates recipient records, initiates push.
        NEVER sends billing content — operations only.
        """
        now = datetime.now(UTC)
        alert_data: dict[str, Any] = {
            "mission_id": mission_id,
            "mission_title": mission_title,
            "mission_address": mission_address,
            "service_level": service_level,
            "priority": priority,
            "chief_complaint": chief_complaint or "",
            "special_instructions": special_instructions or "",
            "unit_id": unit_id,
            "target_crew_ids": target_crew_ids,
            "state": PagingState.ALERT_CREATED.value,
            "ack_timeout_seconds": ack_timeout_seconds,
            "accept_timeout_seconds": accept_timeout_seconds,
            "ack_deadline": (now + timedelta(seconds=ack_timeout_seconds)).isoformat(),
            "accept_deadline": (now + timedelta(seconds=accept_timeout_seconds)).isoformat(),
            "created_at": now.isoformat(),
            "accepted_by": None,
            "accepted_at": None,
            "escalated_at": None,
        }

        alert = await self.svc.create(
            table="crew_paging_alerts",
            tenant_id=self.tenant_id,
            actor_user_id=self.actor_user_id,
            data=alert_data,
            correlation_id=correlation_id,
        )
        alert_id = str(alert["id"])

        # Resolve targets and create recipient records
        recipients = await self._resolve_targets(
            alert_id=alert_id,
            crew_ids=target_crew_ids,
            correlation_id=correlation_id,
        )

        # Update state to TARGETS_RESOLVED
        self.svc.repo("crew_paging_alerts").update(
            tenant_id=self.tenant_id,
            record_id=uuid.UUID(alert_id),
            expected_version=(alert.get("version") or 1),
            patch={"state": PagingState.TARGETS_RESOLVED.value},
        )

        # Audit entry
        await self._audit(
            alert_id=alert_id,
            event_type="ALERT_CREATED",
            data={
                "target_count": len(target_crew_ids),
                "mission_id": mission_id,
                "state": PagingState.ALERT_CREATED.value,
            },
            correlation_id=correlation_id,
        )

        # Create escalation rules if provided or use defaults
        if escalation_rules:
            for rule in escalation_rules:
                await self.svc.create(
                    table="crew_paging_escalation_rules",
                    tenant_id=self.tenant_id,
                    actor_user_id=self.actor_user_id,
                    data={**rule, "alert_id": alert_id},
                    correlation_id=correlation_id,
                )
        else:
            # Default escalation: backup page at accept_timeout
            await self.svc.create(
                table="crew_paging_escalation_rules",
                tenant_id=self.tenant_id,
                actor_user_id=self.actor_user_id,
                data={
                    "alert_id": alert_id,
                    "trigger": "NO_ACCEPT",
                    "timeout_seconds": accept_timeout_seconds,
                    "action": "BACKUP_PAGE",
                    "active": True,
                },
                correlation_id=correlation_id,
            )

        return {
            "alert_id": alert_id,
            "state": PagingState.TARGETS_RESOLVED.value,
            "recipient_count": len(recipients),
            "ack_deadline": alert_data["ack_deadline"],
            "accept_deadline": alert_data["accept_deadline"],
        }

    async def _resolve_targets(
        self,
        alert_id: str,
        crew_ids: list[str],
        correlation_id: str | None,
    ) -> list[dict]:
        """Create recipient records for each target crew member."""
        recipients = []
        now = datetime.now(UTC).isoformat()
        for cid in crew_ids:
            # Look up push device
            devices = self.svc.repo("crew_push_devices").list(
                tenant_id=self.tenant_id, limit=10
            )
            device_token = None
            platform = "unknown"
            for d in devices:
                if (d.get("data") or {}).get("crew_member_id") == cid:
                    device_token = (d.get("data") or {}).get("push_token")
                    platform = (d.get("data") or {}).get("platform", "unknown")
                    break

            rec = await self.svc.create(
                table="crew_paging_recipients",
                tenant_id=self.tenant_id,
                actor_user_id=self.actor_user_id,
                data={
                    "alert_id": alert_id,
                    "crew_member_id": cid,
                    "push_token": device_token,
                    "platform": platform,
                    "state": "PENDING",
                    "sent_at": None,
                    "delivered_at": None,
                    "read_at": None,
                    "response": None,
                    "response_at": None,
                    "created_at": now,
                },
                correlation_id=correlation_id,
            )
            recipients.append(rec)
        return recipients

    # ── Push Send ─────────────────────────────────────────────────────────────

    async def record_push_sent(
        self,
        *,
        alert_id: str,
        recipient_id: str,
        push_message_id: str,
        platform: str,
        correlation_id: str | None = None,
    ) -> dict[str, Any]:
        """
        Record that a push notification was sent to a recipient device.
        Called by the push delivery service after FCM/APNs dispatch.
        """
        now = datetime.now(UTC).isoformat()
        rec = self.svc.repo("crew_paging_recipients").update(
            tenant_id=self.tenant_id,
            record_id=uuid.UUID(recipient_id),
            expected_version=1,
            patch={
                "state": "SENT",
                "sent_at": now,
                "push_message_id": push_message_id,
                "platform": platform,
            },
        )
        await self._audit(
            alert_id=alert_id,
            event_type="PUSH_SENT",
            data={
                "recipient_id": recipient_id,
                "push_message_id": push_message_id,
                "platform": platform,
                "sent_at": now,
            },
            correlation_id=correlation_id,
        )
        return rec or {"recipient_id": recipient_id, "state": "SENT"}

    async def record_push_delivered(
        self,
        *,
        alert_id: str,
        recipient_id: str,
        push_message_id: str,
        correlation_id: str | None = None,
    ) -> dict[str, Any]:
        """Record FCM/APNs delivery receipt."""
        now = datetime.now(UTC).isoformat()
        rec = self.svc.repo("crew_paging_recipients").update(
            tenant_id=self.tenant_id,
            record_id=uuid.UUID(recipient_id),
            expected_version=2,
            patch={"state": "DELIVERED", "delivered_at": now},
        )
        await self._audit(
            alert_id=alert_id,
            event_type="PUSH_DELIVERED",
            data={"recipient_id": recipient_id, "push_message_id": push_message_id, "delivered_at": now},
            correlation_id=correlation_id,
        )
        return rec or {"recipient_id": recipient_id, "state": "DELIVERED"}

    # ── Crew Response ─────────────────────────────────────────────────────────

    async def record_crew_response(
        self,
        *,
        alert_id: str,
        crew_member_id: str,
        response: CrewResponse,
        decline_reason: str | None = None,
        location: dict | None = None,
        correlation_id: str | None = None,
    ) -> dict[str, Any]:
        """
        Record crew member response to a page.
        ACKNOWLEDGE → crew saw the page
        ACCEPT → crew is responding to the call
        DECLINE → crew cannot respond (backup logic may trigger)
        """
        now = datetime.now(UTC).isoformat()

        # Find recipient record
        recipients = self.svc.repo("crew_paging_recipients").list(
            tenant_id=self.tenant_id, limit=100
        )
        recipient = None
        for r in recipients:
            rdata = r.get("data") or {}
            if rdata.get("alert_id") == alert_id and rdata.get("crew_member_id") == crew_member_id:
                recipient = r
                break

        if not recipient:
            return {"error": "recipient_not_found"}

        # Build response record
        response_data: dict[str, Any] = {
            "alert_id": alert_id,
            "crew_member_id": crew_member_id,
            "response": response.value,
            "decline_reason": decline_reason,
            "location": location,
            "response_at": now,
        }
        await self.svc.create(
            table="crew_paging_responses",
            tenant_id=self.tenant_id,
            actor_user_id=self.actor_user_id,
            data=response_data,
            correlation_id=correlation_id,
        )

        # Update recipient state
        new_state = {
            CrewResponse.ACKNOWLEDGE: "ACKNOWLEDGED",
            CrewResponse.ACCEPT: "ACCEPTED",
            CrewResponse.DECLINE: "DECLINED",
        }[response]

        self.svc.repo("crew_paging_recipients").update(
            tenant_id=self.tenant_id,
            record_id=uuid.UUID(str(recipient["id"])),
            expected_version=(recipient.get("version") or 1),
            patch={
                "state": new_state,
                "response": response.value,
                "response_at": now,
                "decline_reason": decline_reason,
            },
        )

        # Update alert state
        alert = self.svc.repo("crew_paging_alerts").get(
            tenant_id=self.tenant_id,
            record_id=uuid.UUID(alert_id),
        )
        if alert:
            if response == CrewResponse.ACCEPT:
                self.svc.repo("crew_paging_alerts").update(
                    tenant_id=self.tenant_id,
                    record_id=uuid.UUID(alert_id),
                    expected_version=(alert.get("version") or 1),
                    patch={
                        "state": PagingState.ACCEPTED.value,
                        "accepted_by": crew_member_id,
                        "accepted_at": now,
                    },
                )
            elif response == CrewResponse.ACKNOWLEDGE:
                current_state = (alert.get("data") or {}).get("state")
                if current_state not in (PagingState.ACCEPTED.value, PagingState.DECLINED.value):
                    self.svc.repo("crew_paging_alerts").update(
                        tenant_id=self.tenant_id,
                        record_id=uuid.UUID(alert_id),
                        expected_version=(alert.get("version") or 1),
                        patch={"state": PagingState.ACKNOWLEDGED.value},
                    )

        await self._audit(
            alert_id=alert_id,
            event_type=f"CREW_{response.value}",
            data={
                "crew_member_id": crew_member_id,
                "response": response.value,
                "decline_reason": decline_reason,
                "response_at": now,
            },
            correlation_id=correlation_id,
        )

        # Check if we need backup logic for DECLINE
        result = {
            "alert_id": alert_id,
            "crew_member_id": crew_member_id,
            "response": response.value,
            "new_state": new_state,
            "ts": now,
        }
        if response == CrewResponse.DECLINE:
            backup_check = await self._check_backup_needed(alert_id, correlation_id)
            result["backup_triggered"] = backup_check.get("triggered", False)

        return result

    # ── Escalation ────────────────────────────────────────────────────────────

    async def escalate_alert(
        self,
        *,
        alert_id: str,
        escalation_reason: str,
        triggered_by: str = "SYSTEM_TIMER",
        backup_crew_ids: list[str] | None = None,
        correlation_id: str | None = None,
    ) -> dict[str, Any]:
        """
        Escalate a paging alert.
        Called by timer workers or manual dispatcher override.
        Creates escalation event and optionally pages backup crew.
        """
        now = datetime.now(UTC).isoformat()

        alert = self.svc.repo("crew_paging_alerts").get(
            tenant_id=self.tenant_id,
            record_id=uuid.UUID(alert_id),
        )
        if not alert:
            return {"error": "alert_not_found"}

        current_state = (alert.get("data") or {}).get("state")
        if current_state == PagingState.ACCEPTED.value:
            return {"status": "no_escalation_needed", "reason": "already_accepted"}

        # Record escalation event
        escalation_event = await self.svc.create(
            table="crew_paging_escalation_events",
            tenant_id=self.tenant_id,
            actor_user_id=self.actor_user_id,
            data={
                "alert_id": alert_id,
                "escalation_reason": escalation_reason,
                "triggered_by": triggered_by,
                "previous_state": current_state,
                "escalated_at": now,
            },
            correlation_id=correlation_id,
        )

        # Update alert state
        self.svc.repo("crew_paging_alerts").update(
            tenant_id=self.tenant_id,
            record_id=uuid.UUID(alert_id),
            expected_version=(alert.get("version") or 1),
            patch={"state": PagingState.ESCALATED.value, "escalated_at": now},
        )

        await self._audit(
            alert_id=alert_id,
            event_type="ALERT_ESCALATED",
            data={
                "reason": escalation_reason,
                "triggered_by": triggered_by,
                "escalated_at": now,
            },
            correlation_id=correlation_id,
        )

        result: dict[str, Any] = {
            "alert_id": alert_id,
            "state": PagingState.ESCALATED.value,
            "escalation_event_id": str(escalation_event["id"]),
            "ts": now,
        }

        # Page backup crew if provided
        if backup_crew_ids:
            backup = await self._send_backup_page(
                original_alert_id=alert_id,
                backup_crew_ids=backup_crew_ids,
                correlation_id=correlation_id,
            )
            result["backup_alert_id"] = backup.get("alert_id")
            result["backup_sent"] = True
        else:
            result["backup_sent"] = False

        return result

    async def _check_backup_needed(
        self, alert_id: str, correlation_id: str | None
    ) -> dict[str, Any]:
        """Check if all recipients declined and backup is needed."""
        recipients = self.svc.repo("crew_paging_recipients").list(
            tenant_id=self.tenant_id, limit=100
        )
        alert_recipients = [
            r for r in recipients
            if (r.get("data") or {}).get("alert_id") == alert_id
        ]
        all_declined = all(
            (r.get("data") or {}).get("state") == "DECLINED"
            for r in alert_recipients
        ) if alert_recipients else False

        if all_declined:
            await self._audit(
                alert_id=alert_id,
                event_type="ALL_CREW_DECLINED_BACKUP_REQUIRED",
                data={"backup_needed": True},
                correlation_id=correlation_id,
            )
            return {"triggered": True, "reason": "all_crew_declined"}
        return {"triggered": False}

    async def _send_backup_page(
        self,
        original_alert_id: str,
        backup_crew_ids: list[str],
        correlation_id: str | None,
    ) -> dict[str, Any]:
        """Send backup paging alert."""
        now = datetime.now(UTC).isoformat()
        original = self.svc.repo("crew_paging_alerts").get(
            tenant_id=self.tenant_id,
            record_id=uuid.UUID(original_alert_id),
        )
        original_data = (original.get("data") or {}) if original else {}

        backup_alert = await self.svc.create(
            table="crew_paging_alerts",
            tenant_id=self.tenant_id,
            actor_user_id=self.actor_user_id,
            data={
                "mission_id": original_data.get("mission_id"),
                "mission_title": original_data.get("mission_title"),
                "mission_address": original_data.get("mission_address"),
                "service_level": original_data.get("service_level"),
                "priority": original_data.get("priority"),
                "chief_complaint": original_data.get("chief_complaint"),
                "special_instructions": "BACKUP PAGE — Original crew unavailable.",
                "unit_id": original_data.get("unit_id"),
                "target_crew_ids": backup_crew_ids,
                "state": PagingState.ALERT_CREATED.value,
                "parent_alert_id": original_alert_id,
                "is_backup": True,
                "created_at": now,
            },
            correlation_id=correlation_id,
        )

        # Update original alert
        if original:
            self.svc.repo("crew_paging_alerts").update(
                tenant_id=self.tenant_id,
                record_id=uuid.UUID(original_alert_id),
                expected_version=(original.get("version") or 1),
                patch={"state": PagingState.BACKUP_ALERT_SENT.value},
            )

        await self._audit(
            alert_id=original_alert_id,
            event_type="BACKUP_ALERT_SENT",
            data={
                "backup_alert_id": str(backup_alert["id"]),
                "backup_crew_ids": backup_crew_ids,
            },
            correlation_id=correlation_id,
        )

        return {"alert_id": str(backup_alert["id"])}

    # ── Escalation Timer Check ────────────────────────────────────────────────

    def check_escalation_timers(self) -> list[dict[str, Any]]:
        """
        Check all active alerts against their escalation timers.
        Returns list of alerts that need escalation action.
        Called by background worker on interval.
        """
        now = datetime.now(UTC)
        alerts = self.svc.repo("crew_paging_alerts").list(
            tenant_id=self.tenant_id, limit=200
        )

        needs_action = []
        terminal_states = {PagingState.ACCEPTED.value, PagingState.CLOSED.value, PagingState.BACKUP_ALERT_SENT.value}

        for alert in alerts:
            data = alert.get("data") or {}
            state = data.get("state")
            if state in terminal_states:
                continue

            # Check accept deadline
            accept_deadline_str = data.get("accept_deadline")
            if accept_deadline_str and state not in (PagingState.ESCALATED.value,):
                try:
                    deadline = datetime.fromisoformat(accept_deadline_str.replace("Z", "+00:00"))
                    if now > deadline:
                        needs_action.append({
                            "alert_id": str(alert["id"]),
                            "action": "ESCALATE",
                            "reason": "ACCEPT_TIMEOUT",
                            "overdue_seconds": int((now - deadline).total_seconds()),
                            "mission_id": data.get("mission_id"),
                        })
                except Exception:
                    pass

        return needs_action

    # ── Status Update ─────────────────────────────────────────────────────────

    async def update_crew_status(
        self,
        *,
        crew_member_id: str,
        status: str,
        unit_id: str | None = None,
        location: dict | None = None,
        correlation_id: str | None = None,
    ) -> dict[str, Any]:
        """Record a crew status update (EN_ROUTE, ON_SCENE, etc.)."""
        now = datetime.now(UTC).isoformat()
        event = await self.svc.create(
            table="crew_status_events",
            tenant_id=self.tenant_id,
            actor_user_id=self.actor_user_id,
            data={
                "crew_member_id": crew_member_id,
                "status": status,
                "unit_id": unit_id,
                "location": location,
                "ts": now,
            },
            correlation_id=correlation_id,
        )
        return {"crew_member_id": crew_member_id, "status": status, "event_id": str(event["id"]), "ts": now}

    # ── Audit ─────────────────────────────────────────────────────────────────

    async def _audit(
        self,
        alert_id: str,
        event_type: str,
        data: dict[str, Any],
        correlation_id: str | None,
    ) -> None:
        await self.svc.create(
            table="crew_paging_audit_events",
            tenant_id=self.tenant_id,
            actor_user_id=self.actor_user_id,
            data={
                "alert_id": alert_id,
                "event_type": event_type,
                "data": data,
                "actor_user_id": str(self.actor_user_id) if self.actor_user_id else "SYSTEM",
                "ts": datetime.now(UTC).isoformat(),
                "correlation_id": correlation_id,
            },
            correlation_id=correlation_id,
        )
