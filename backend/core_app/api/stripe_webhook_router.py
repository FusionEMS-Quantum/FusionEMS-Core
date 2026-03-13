from __future__ import annotations

# ruff: noqa: TRY200
import logging
import uuid
from datetime import UTC, datetime

import stripe
from fastapi import APIRouter, Depends, Header, HTTPException, Request
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session

from core_app.api.dependencies import db_session_dependency
from core_app.core.config import get_settings
from core_app.payments.stripe_service import StripeConfig, verify_webhook_signature
from core_app.services.domination_service import DominationService
from core_app.services.event_publisher import get_event_publisher
from core_app.services.legal_requests_service import LegalRequestsService
from core_app.services.sqs_publisher import enqueue

logger = logging.getLogger(__name__)

router = APIRouter(tags=["Webhooks - Stripe"])


STRIPE_HANDLED_EVENTS = frozenset(
    {
        "checkout.session.completed",
        "payment_intent.succeeded",
        "payment_intent.payment_failed",
        "charge.refunded",
        "charge.dispute.created",
    }
)


@router.post("/api/v1/webhooks/stripe", include_in_schema=True)
async def stripe_webhook(
    request: Request,
    db: Session = Depends(db_session_dependency),
    stripe_signature: str = Header(default="", alias="Stripe-Signature"),
):
    """
    Stripe Connect webhook receiver.

    1. Read raw body (mandatory before any json parse for sig verification).
    2. Verify Stripe-Signature with signing secret.
    3. Route to correct tenant via connected account id.
    4. Idempotency check by Stripe event id.
    5. Persist raw event.
    6. Enqueue to SQS.
    7. Return 200 immediately.
    """
    raw_body = await request.body()
    correlation_id = getattr(request.state, "correlation_id", str(uuid.uuid4()))

    settings = get_settings()
    webhook_secret = settings.stripe_webhook_secret

    if not webhook_secret or str(webhook_secret).startswith("REPLACE"):
        logger.error(
            "stripe_webhook_secret_not_configured correlation_id=%s", correlation_id
        )
        raise HTTPException(status_code=500, detail="webhook_secret_not_configured")

    if not stripe_signature:
        raise HTTPException(status_code=400, detail="missing_stripe_signature")

    cfg = StripeConfig(
        secret_key=settings.stripe_secret_key,
        webhook_secret=webhook_secret,
    )

    try:
        event = verify_webhook_signature(
            cfg=cfg,
            payload=raw_body,
            sig_header=stripe_signature,
        )
    except stripe.error.SignatureVerificationError as exc:  # noqa: B904, TRY200
        logger.warning(
            "stripe_sig_invalid correlation_id=%s sig=%.20s error=%s",
            correlation_id,
            stripe_signature,
            exc,
        )
        return JSONResponse(status_code=400, content={"detail": "invalid_stripe_signature"})

    event_id: str = event.get("id", str(uuid.uuid4()))
    event_type: str = event.get("type", "unknown")
    connected_account_id: str | None = event.get("account")

    logger.info(
        "stripe_webhook_received event_id=%s event_type=%s account=%s correlation_id=%s",
        event_id,
        event_type,
        connected_account_id,
        correlation_id,
    )

    # ── Idempotency ───────────────────────────────────────────────────────────
    publisher = get_event_publisher()
    svc = DominationService(db, publisher)

    existing = svc.repo("stripe_webhook_receipts").list_raw_by_field(
        "event_id", event_id, limit=2
    )
    if existing:
        logger.info("stripe_webhook_duplicate event_id=%s", event_id)
        return {"status": "duplicate", "event_id": event_id}

    # ── Persist ───────────────────────────────────────────────────────────────
    system_tenant_id = uuid.UUID(settings.system_tenant_id)
    await svc.create(
        table="stripe_webhook_receipts",
        tenant_id=system_tenant_id,
        actor_user_id=None,
        data={
            "event_id": event_id,
            "event_type": event_type,
            "connected_account_id": connected_account_id,
            "payload": event,
            "received_at": datetime.now(UTC).isoformat(),
            "correlation_id": correlation_id,
        },
        correlation_id=correlation_id,
    )

    # Apply legal request payment transitions immediately for deterministic fulfillment holds.
    try:
        LegalRequestsService(db).apply_stripe_webhook_event(
            event=event,
            correlation_id=correlation_id,
        )
        db.commit()
    except Exception as exc:  # noqa: BLE001
        logger.error(
            "legal_stripe_webhook_apply_failed event_id=%s correlation_id=%s error=%s",
            event_id,
            correlation_id,
            str(exc),
        )

    # ── Enqueue to Stripe events queue (billing/statements worker) ───────────
    queue_url = settings.stripe_events_queue_url
    if not queue_url:
        logger.error(
            "stripe_events_queue_url_not_configured — cannot enqueue event_id=%s",
            event_id,
        )
        raise HTTPException(
            status_code=500, detail="stripe_events_queue_not_configured"
        )

    _message = {
        "source": "stripe_webhook",
        "event_id": event_id,
        "event_type": event_type,
        "connected_account_id": connected_account_id,
        "payload": event,
        "correlation_id": correlation_id,
        "received_at": datetime.now(UTC).isoformat(),
    }

    enqueue(queue_url, _message, deduplication_id=event_id)

    # ── Route checkout.session.completed to onboarding queue ─────────────────
    # This triggers the zero-error deployment state machine (onboarding_worker.py)
    # which provisions the new agency tenant idempotently.
    if event_type == "checkout.session.completed":
        onboarding_queue_url = settings.onboarding_events_queue_url
        if onboarding_queue_url:
            enqueue(
                onboarding_queue_url,
                _message,
                deduplication_id=f"onboard_{event_id}",
            )
            logger.info(
                "stripe_webhook_onboarding_enqueued event_id=%s correlation_id=%s",
                event_id, correlation_id,
            )
        else:
            logger.warning(
                "onboarding_events_queue_url_not_configured — "
                "checkout.session.completed event_id=%s will not trigger provisioning. "
                "Set ONBOARDING_EVENTS_QUEUE_URL to enable automatic tenant provisioning.",
                event_id,
            )

    return {"status": "ok", "event_id": event_id, "event_type": event_type}
