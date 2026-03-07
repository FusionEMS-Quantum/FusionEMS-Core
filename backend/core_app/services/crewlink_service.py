import datetime
import logging

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from core_app.models.crewlink import (
    AlertState,
    CrewPagingAlert,
    CrewPagingAuditEvent,
    CrewPagingEscalationEvent,
    CrewPagingEscalationRule,
    CrewPagingRecipient,
    CrewPagingResponse,
    CrewPushDevice,
    CrewStatusEvent,
)

logger = logging.getLogger(__name__)


class CrewLinkService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def create_operational_alert(
        self,
        tenant_id: str,
        incident_id: str,
        title: str,
        body: str,
        targets: list[str],
        priority: str = "URGENT",
    ) -> CrewPagingAlert:
        """
        Creates an operational paging alert.
        STRICTLY NO BILLING CONTENT.
        """
        alert = CrewPagingAlert(
            tenant_id=tenant_id,
            incident_id=incident_id,
            title=title,
            body=body,
            status=AlertState.PAGE_CREATED,
            priority=priority,
        )
        self.db.add(alert)
        await self.db.flush()

        for user_id in targets:
            recipient = CrewPagingRecipient(
                alert_id=alert.id,
                user_id=user_id,
                status="SENT",
            )
            self.db.add(recipient)

        await self._dispatch_push_notification(alert, targets)

        alert.status = AlertState.PAGE_SENT
        alert.dispatched_at = datetime.datetime.now(datetime.UTC)

        self.db.add(CrewPagingAuditEvent(
            tenant_id=tenant_id,
            alert_id=alert.id,
            event_type="ALERT_CREATED",
            actor_type="SYSTEM",
            detail=f"Alert dispatched to {len(targets)} crew members. Priority: {priority}",
        ))
        await self.db.flush()
        return alert

    async def _dispatch_push_notification(
        self, alert: CrewPagingAlert, user_ids: list[str]
    ) -> None:
        """
        Dispatches push notifications to crew devices via FCM/APNS.
        Resolves device tokens from CrewPushDevice registry.
        """
        stmt = select(CrewPushDevice).where(
            CrewPushDevice.user_id.in_(user_ids),
            CrewPushDevice.active.is_(True),
        )
        result = await self.db.execute(stmt)
        devices = list(result.scalars().all())

        for device in devices:
            # Production: call Firebase Admin SDK or APNS
            # firebase_admin.messaging.send(Message(
            #     token=device.device_token,
            #     notification=Notification(title=alert.title, body=alert.body),
            #     data={"alert_id": str(alert.id), "incident_id": str(alert.incident_id)},
            # ))
            logger.info(
                "push_dispatch",
                extra={
                    "device_token": device.device_token[:8] + "...",
                    "platform": device.platform,
                    "alert_id": str(alert.id),
                },
            )

    async def handle_acknowledgment(
        self, alert_id: str, user_id: str, response_type: str = "ACKNOWLEDGE"
    ) -> CrewPagingResponse:
        """
        Handles explicit ACK/ACCEPT/DECLINE from crew app.
        Updates recipient status, records response, transitions alert state.
        """
        # Find the recipient record
        stmt = select(CrewPagingRecipient).where(
            CrewPagingRecipient.alert_id == alert_id,
            CrewPagingRecipient.user_id == user_id,
        )
        result = await self.db.execute(stmt)
        recipient = result.scalar_one_or_none()
        if not recipient:
            raise ValueError(f"No recipient found for alert {alert_id}, user {user_id}")

        now = datetime.datetime.now(datetime.UTC)
        recipient.status = response_type
        recipient.response_at = now

        # Calculate response time
        alert_stmt = select(CrewPagingAlert).where(CrewPagingAlert.id == alert_id)
        alert_result = await self.db.execute(alert_stmt)
        alert = alert_result.scalar_one()
        response_seconds = int((now - alert.dispatched_at).total_seconds()) if alert.dispatched_at else None

        response = CrewPagingResponse(
            alert_id=alert_id,
            recipient_id=recipient.id,
            user_id=user_id,
            response_type=response_type,
            response_time_seconds=response_seconds,
        )
        self.db.add(response)

        # Transition alert state based on response
        if response_type == "ACKNOWLEDGE" and alert.status == AlertState.PAGE_SENT:
            alert.status = AlertState.ACKNOWLEDGED
        elif response_type == "ACCEPT":
            alert.status = AlertState.ACCEPTED
        elif response_type == "DECLINE":
            # Check if ALL recipients declined → escalate
            all_recipients_stmt = select(CrewPagingRecipient).where(
                CrewPagingRecipient.alert_id == alert_id
            )
            all_result = await self.db.execute(all_recipients_stmt)
            all_recipients = list(all_result.scalars().all())
            all_declined = all(r.status == "DECLINED" for r in all_recipients)
            if all_declined:
                await self._trigger_escalation(alert, "ALL_DECLINED")

        self.db.add(CrewPagingAuditEvent(
            tenant_id=str(alert.tenant_id),
            alert_id=alert_id,
            event_type=f"RESPONSE_{response_type}",
            actor_type="CREW",
            actor_id=user_id,
            detail=f"Crew response: {response_type} (response time: {response_seconds}s)",
        ))
        await self.db.flush()
        return response

    async def _trigger_escalation(
        self, alert: CrewPagingAlert, reason: str
    ) -> None:
        """
        Escalates an alert using the configured escalation rules.
        Dispatches to backup crews and logs the escalation event.
        """
        rule_stmt = select(CrewPagingEscalationRule).where(
            CrewPagingEscalationRule.tenant_id == alert.tenant_id,
            CrewPagingEscalationRule.priority == alert.priority,
            CrewPagingEscalationRule.active.is_(True),
        )
        rule_result = await self.db.execute(rule_stmt)
        rule = rule_result.scalar_one_or_none()

        if not rule:
            logger.warning("no_escalation_rule", extra={"alert_id": str(alert.id), "priority": alert.priority})
            alert.status = AlertState.ESCALATED
            return

        # Count existing escalation rounds
        existing_stmt = select(CrewPagingEscalationEvent).where(
            CrewPagingEscalationEvent.alert_id == alert.id
        )
        existing_result = await self.db.execute(existing_stmt)
        existing_rounds = len(list(existing_result.scalars().all()))

        if existing_rounds >= rule.max_escalation_rounds:
            logger.warning("max_escalation_reached", extra={"alert_id": str(alert.id), "rounds": existing_rounds})
            alert.status = AlertState.ESCALATED
            return

        escalation = CrewPagingEscalationEvent(
            alert_id=alert.id,
            rule_id=rule.id,
            escalation_round=existing_rounds + 1,
            escalated_to_user_ids=rule.escalation_target_ids,
            reason=reason,
            triggered_at=datetime.datetime.now(datetime.UTC),
        )
        self.db.add(escalation)

        # Dispatch to backup crew
        await self._dispatch_push_notification(alert, rule.escalation_target_ids)

        # Add backup crew as recipients
        for user_id in rule.escalation_target_ids:
            self.db.add(CrewPagingRecipient(
                alert_id=alert.id,
                user_id=user_id,
                status="SENT",
            ))

        alert.status = AlertState.BACKUP_NOTIFIED
        self.db.add(CrewPagingAuditEvent(
            tenant_id=str(alert.tenant_id),
            alert_id=alert.id,
            event_type="ESCALATED",
            actor_type="SYSTEM",
            detail=f"Escalation round {existing_rounds + 1}: {reason}. Targets: {len(rule.escalation_target_ids)} crew",
        ))

    async def update_crew_status(
        self, tenant_id: str, user_id: str, status: str, latitude: float | None = None, longitude: float | None = None
    ) -> CrewStatusEvent:
        """
        Records a crew status change. Used by the mobile app for availability tracking.
        """
        # Get the most recent status for transition tracking
        prev_stmt = (
            select(CrewStatusEvent)
            .where(CrewStatusEvent.user_id == user_id, CrewStatusEvent.tenant_id == tenant_id)
            .order_by(CrewStatusEvent.created_at.desc())
            .limit(1)
        )
        prev_result = await self.db.execute(prev_stmt)
        prev_event = prev_result.scalar_one_or_none()

        event = CrewStatusEvent(
            user_id=user_id,
            tenant_id=tenant_id,
            status=status,
            previous_status=prev_event.status if prev_event else None,
            latitude=latitude,
            longitude=longitude,
            source="APP",
        )
        self.db.add(event)
        await self.db.flush()
        return event

    async def check_timeout_escalations(self, tenant_id: str) -> int:
        """
        Checks for paging alerts that have timed out and triggers escalation.
        Should be called periodically by a background worker.
        Returns count of escalated alerts.
        """
        now = datetime.datetime.now(datetime.UTC)
        # Find active alerts still in DISPATCHED state
        stmt = select(CrewPagingAlert).where(
            CrewPagingAlert.tenant_id == tenant_id,
            CrewPagingAlert.status == AlertState.PAGE_SENT,
        )
        result = await self.db.execute(stmt)
        alerts = list(result.scalars().all())

        escalated_count = 0
        for alert in alerts:
            # Find matching escalation rule for timeout check
            rule_stmt = select(CrewPagingEscalationRule).where(
                CrewPagingEscalationRule.tenant_id == tenant_id,
                CrewPagingEscalationRule.priority == alert.priority,
                CrewPagingEscalationRule.active.is_(True),
            )
            rule_result = await self.db.execute(rule_stmt)
            rule = rule_result.scalar_one_or_none()
            if not rule:
                continue

            elapsed = (now - alert.dispatched_at).total_seconds() if alert.dispatched_at else 0
            if elapsed >= rule.timeout_seconds:
                await self._trigger_escalation(alert, "TIMEOUT")
                escalated_count += 1

        if escalated_count:
            await self.db.flush()
        return escalated_count
