from __future__ import annotations

import uuid

from core_app.services.event_publisher import EventPublisher


async def emit_authorization_verified(
    *,
    publisher: EventPublisher,
    tenant_id: uuid.UUID,
    rep_id: uuid.UUID,
    patient_id: uuid.UUID,
    method: str,
    correlation_id: str | None = None,
) -> None:
    await publisher.publish(
        "authorization_rep.verified",
        tenant_id=tenant_id,
        entity_id=rep_id,
        payload={
            "rep_id": str(rep_id),
            "patient_id": str(patient_id),
            "method": method,
        },
        entity_type="authorized_rep",
        correlation_id=correlation_id,
    )


async def emit_letter_viewed(
    *,
    publisher: EventPublisher,
    tenant_id: uuid.UUID,
    letter_id: uuid.UUID,
    view_token: str,
    correlation_id: str | None = None,
) -> None:
    await publisher.publish(
        "letter.viewed",
        tenant_id=tenant_id,
        entity_id=letter_id,
        payload={
            "letter_id": str(letter_id),
            "view_token": view_token,
        },
        entity_type="letter",
        correlation_id=correlation_id,
    )


async def emit_payment_confirmed(
    *,
    publisher: EventPublisher,
    tenant_id: uuid.UUID,
    payment_id: uuid.UUID,
    amount_cents: int,
    stripe_payment_intent: str | None,
    correlation_id: str | None = None,
) -> None:
    await publisher.publish(
        "payment.confirmed",
        tenant_id=tenant_id,
        entity_id=payment_id,
        payload={
            "payment_id": str(payment_id),
            "amount_cents": amount_cents,
            "stripe_payment_intent": stripe_payment_intent,
        },
        entity_type="payment",
        correlation_id=correlation_id,
    )


async def emit_incident_created(
    *,
    publisher: EventPublisher,
    tenant_id: uuid.UUID,
    incident_id: uuid.UUID,
    payload: dict[str, object],
    correlation_id: str | None = None,
) -> None:
    await publisher.publish(
        "fire.incident.created",
        tenant_id=tenant_id,
        entity_id=incident_id,
        payload={
            "incident_id": str(incident_id),
            **payload,
        },
        entity_type="fire_incident",
        correlation_id=correlation_id,
    )


async def emit_incident_locked(
    *,
    publisher: EventPublisher,
    tenant_id: uuid.UUID,
    incident_id: uuid.UUID,
    correlation_id: str | None = None,
) -> None:
    await publisher.publish(
        "fire.incident.locked",
        tenant_id=tenant_id,
        entity_id=incident_id,
        payload={"incident_id": str(incident_id), "locked": True},
        entity_type="fire_incident",
        correlation_id=correlation_id,
    )


async def emit_incident_dispatched(
    *,
    publisher: EventPublisher,
    tenant_id: uuid.UUID,
    incident_id: uuid.UUID,
    mission_id: uuid.UUID,
    service_level: str,
    priority: str,
    correlation_id: str | None = None,
) -> None:
    await publisher.publish(
        "fire.incident.dispatched",
        tenant_id=tenant_id,
        entity_id=incident_id,
        payload={
            "incident_id": str(incident_id),
            "mission_id": str(mission_id),
            "service_level": service_level,
            "priority": priority,
        },
        entity_type="fire_incident",
        correlation_id=correlation_id,
    )


async def emit_apparatus_status_changed(
    *,
    publisher: EventPublisher,
    tenant_id: uuid.UUID,
    apparatus_id: uuid.UUID,
    incident_id: uuid.UUID,
    status: str,
    unit_id: str | None = None,
    correlation_id: str | None = None,
) -> None:
    await publisher.publish(
        "fire.apparatus.status",
        tenant_id=tenant_id,
        entity_id=apparatus_id,
        payload={
            "apparatus_id": str(apparatus_id),
            "incident_id": str(incident_id),
            "status": status,
            "unit_id": unit_id,
        },
        entity_type="fire_apparatus",
        correlation_id=correlation_id,
    )


async def emit_dispatch_mission_created(
    *,
    publisher: EventPublisher,
    tenant_id: uuid.UUID,
    mission_id: uuid.UUID,
    payload: dict[str, object],
    correlation_id: str | None = None,
) -> None:
    await publisher.publish(
        "dispatch.mission.created",
        tenant_id=tenant_id,
        entity_id=mission_id,
        payload={
            "mission_id": str(mission_id),
            **payload,
        },
        entity_type="active_mission",
        correlation_id=correlation_id,
    )


async def emit_mission_state_transitioned(
    *,
    publisher: EventPublisher,
    tenant_id: uuid.UUID,
    mission_id: uuid.UUID,
    from_state: str,
    to_state: str,
    actor_user_id: uuid.UUID | None,
    override: bool,
    correlation_id: str | None = None,
) -> None:
    await publisher.publish(
        "dispatch.mission.transitioned",
        tenant_id=tenant_id,
        entity_id=mission_id,
        payload={
            "mission_id": str(mission_id),
            "from_state": from_state,
            "to_state": to_state,
            "actor_user_id": str(actor_user_id) if actor_user_id else None,
            "override": override,
        },
        entity_type="active_mission",
        correlation_id=correlation_id,
    )
