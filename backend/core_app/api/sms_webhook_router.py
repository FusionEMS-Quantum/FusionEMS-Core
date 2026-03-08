from __future__ import annotations

import json
import logging
import re
import uuid
from datetime import UTC, datetime
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy import text
from sqlalchemy.orm import Session

from core_app.api.dependencies import db_session_dependency
from core_app.core.config import get_settings

# from core_app.services.ai_narrative_service import AiNarrativeService # TODO: distinct service
from core_app.services.ai_assistant_service import AIAssistantService  # Use existing service
from core_app.telnyx.client import TelnyxApiError, send_sms
from core_app.telnyx.signature import verify_telnyx_webhook

logger = logging.getLogger(__name__)

router = APIRouter(tags=["Telnyx SMS"])

STOP_KEYWORDS = {"STOP", "UNSUBSCRIBE", "CANCEL", "END", "QUIT"}
HELP_KEYWORDS = {"HELP", "INFO"}
LOOKUP_RE = re.compile(r"\b(?:statement|stmt|account|acct)?[\s:#-]*([A-Za-z0-9-]{6,24})\b", re.IGNORECASE)


def _utcnow() -> str:
    return datetime.now(UTC).isoformat()


def _insert_event(
    db: Session, event_id: str, event_type: str, tenant_id: str | None, raw: dict
) -> bool:
    result = db.execute(
        text(
            "INSERT INTO telnyx_events (event_id, event_type, tenant_id, received_at, raw_json) "
            "VALUES (:eid, :etype, :tid, :now, :raw::jsonb) "
            "ON CONFLICT (event_id) DO NOTHING"
        ),
        {
            "eid": event_id,
            "etype": event_type,
            "tid": tenant_id,
            "now": _utcnow(),
            "raw": json.dumps(raw, default=str),
        },
    )
    db.commit()
    return (result.rowcount or 0) > 0


def _resolve_tenant_by_did(db: Session, to_number: str) -> str | None:
    row = db.execute(
        text(
            "SELECT tenant_id FROM tenant_phone_numbers "
            "WHERE phone_e164 = :phone AND purpose = 'billing_sms' LIMIT 1"
        ),
        {"phone": to_number},
    ).fetchone()
    # Handle SQLAlchemy row access safely
    return str(row.tenant_id) if row else None


def _extract_lookup_key(message_text: str) -> str | None:
    match = LOOKUP_RE.search(message_text or "")
    if not match:
        return None
    return str(match.group(1) or "").strip() or None


def _resolve_account_context(db: Session, lookup_key: str | None) -> dict[str, str] | None:
    key = (lookup_key or "").strip()
    if not key:
        return None

    row = db.execute(
        text(
            "SELECT tenant_id::text AS tenant_id, id::text AS account_id, id::text AS statement_id "
            "FROM billing_cases WHERE id::text = :sid LIMIT 1"
        ),
        {"sid": key},
    ).mappings().first()
    if row:
        return {
            "tenant_id": str(row.get("tenant_id") or ""),
            "account_id": str(row.get("account_id") or key),
            "statement_id": str(row.get("statement_id") or key),
        }

    row2 = db.execute(
        text(
            "SELECT tenant_id::text AS tenant_id, claim_id::text AS account_id, statement_id::text AS statement_id "
            "FROM lob_letters WHERE statement_id::text = :sid LIMIT 1"
        ),
        {"sid": key},
    ).mappings().first()
    if row2:
        return {
            "tenant_id": str(row2.get("tenant_id") or ""),
            "account_id": str(row2.get("account_id") or key),
            "statement_id": str(row2.get("statement_id") or key),
        }

    return None


def _resolve_tenant_context(
    db: Session,
    *,
    to_number: str,
    body_text: str,
    settings: Any,
) -> dict[str, Any]:
    central_phone = str(settings.central_billing_phone_e164 or "").strip()
    is_central = bool(central_phone and to_number == central_phone)
    if not is_central:
        row = db.execute(
            text(
                "SELECT phone_e164 FROM central_billing_lines "
                "WHERE phone_e164 = :phone AND is_active = true LIMIT 1"
            ),
            {"phone": to_number},
        ).fetchone()
        is_central = row is not None

    if not is_central:
        return {
            "tenant_id": _resolve_tenant_by_did(db, to_number),
            "statement_id": None,
            "account_id": None,
            "lookup_key": None,
            "is_central": False,
        }

    lookup_key = _extract_lookup_key(body_text)
    context = _resolve_account_context(db, lookup_key)
    resolved_tenant_id = str((context or {}).get("tenant_id") or "").strip() or None
    return {
        "tenant_id": resolved_tenant_id,
        "statement_id": (context or {}).get("statement_id"),
        "account_id": (context or {}).get("account_id"),
        "lookup_key": lookup_key,
        "is_central": True,
    }


def _get_tenant_info(db: Session, tenant_id: str) -> dict[str, Any]:
    row = db.execute(
        text("SELECT name, billing_contact_phone FROM tenants WHERE id = :tid LIMIT 1"),
        {"tid": tenant_id},
    ).fetchone()
    if row:
        return {
            "name": row.name or "EMS Agency",
            "billing_phone": row.billing_contact_phone or "",
        }
    return {"name": "EMS Agency", "billing_phone": ""}


def _upsert_opt_out(db: Session, tenant_id: str | None, phone_e164: str, source: str) -> None:
    if not tenant_id:
        return
    db.execute(
        text(
            "INSERT INTO telnyx_opt_outs (tenant_id, phone_e164, opted_out_at, source) "
            "VALUES (:tid, :phone, :now, :src) "
            "ON CONFLICT (tenant_id, phone_e164) DO UPDATE SET opted_out_at = :now, source = :src"
        ),
        {"tid": tenant_id, "phone": phone_e164, "now": _utcnow(), "src": source},
    )
    db.commit()



def _is_opted_out(db: Session, tenant_id: str, phone_e164: str) -> bool:
    if not tenant_id:
        return False
    row = db.execute(
        text(
            "SELECT 1 FROM telnyx_opt_outs WHERE tenant_id = :tid AND phone_e164 = :phone LIMIT 1"
        ),
        {"tid": tenant_id, "phone": phone_e164},
    ).fetchone()
    return row is not None


def _log_sms(
    db: Session,
    message_id: str,
    tenant_id: str | None,
    direction: str,
    from_phone: str,
    to_phone: str,
    body: str,
    status: str,
) -> None:
    db.execute(
        text(
            "INSERT INTO telnyx_sms_messages "
            "(message_id, tenant_id, direction, from_phone, to_phone, body, status, created_at) "
            "VALUES (:mid, :tid, :dir, :from_, :to_, :body, :status, :now) "
            "ON CONFLICT (message_id) DO NOTHING"
        ),
        {
            "mid": message_id,
            "tid": tenant_id,
            "dir": direction,
            "from_": from_phone,
            "to_": to_phone,
            "body": body,
            "status": status,
            "now": _utcnow(),
        },
    )
    db.commit()


def _ensure_sms_thread(
    db: Session,
    *,
    tenant_id: str | None,
    central_phone: str,
    participant_phone: str,
    statement_id: str | None,
    account_id: str | None,
) -> str | None:
    try:
        row = db.execute(
            text(
                """
                SELECT id
                FROM billing_sms_threads
                WHERE central_phone = :central_phone
                  AND participant_phone = :participant_phone
                  AND COALESCE(state, 'SMS_CREATED') != 'SMS_CLOSED'
                ORDER BY updated_at DESC
                LIMIT 1
                """
            ),
            {
                "central_phone": central_phone,
                "participant_phone": participant_phone,
            },
        ).mappings().first()
        if row and row.get("id"):
            thread_id = str(row.get("id"))
            db.execute(
                text(
                    """
                    UPDATE billing_sms_threads
                    SET
                        tenant_id = COALESCE(:tenant_id::uuid, tenant_id),
                        statement_id = COALESCE(:statement_id, statement_id),
                        account_id = COALESCE(:account_id, account_id),
                        updated_at = :now
                    WHERE id = :id::uuid
                    """
                ),
                {
                    "tenant_id": tenant_id,
                    "statement_id": statement_id,
                    "account_id": account_id,
                    "now": _utcnow(),
                    "id": thread_id,
                },
            )
            db.commit()
            return thread_id

        created = db.execute(
            text(
                """
                INSERT INTO billing_sms_threads (
                    tenant_id, central_phone, participant_phone,
                    statement_id, account_id, state,
                    created_at, updated_at
                ) VALUES (
                    :tenant_id::uuid, :central_phone, :participant_phone,
                    :statement_id, :account_id, 'SMS_CREATED',
                    :now, :now
                )
                RETURNING id
                """
            ),
            {
                "tenant_id": tenant_id,
                "central_phone": central_phone,
                "participant_phone": participant_phone,
                "statement_id": statement_id,
                "account_id": account_id,
                "now": _utcnow(),
            },
        ).mappings().first()
        db.commit()
        return str((created or {}).get("id") or "") or None
    except Exception:
        logger.exception("billing_sms_thread_write_failed")
        db.rollback()
        return None


def _log_structured_sms_message(
    db: Session,
    *,
    thread_id: str | None,
    message_id: str,
    direction: str,
    from_phone: str,
    to_phone: str,
    body: str,
    status: str,
) -> None:
    if not thread_id:
        return
    try:
        db.execute(
            text(
                """
                INSERT INTO billing_sms_messages (
                    thread_id, message_id, direction,
                    from_phone, to_phone, body,
                    state, created_at
                ) VALUES (
                    :thread_id::uuid, :message_id, :direction,
                    :from_phone, :to_phone, :body,
                    :state, :now
                )
                """
            ),
            {
                "thread_id": thread_id,
                "message_id": message_id,
                "direction": direction,
                "from_phone": from_phone,
                "to_phone": to_phone,
                "body": body,
                "state": status,
                "now": _utcnow(),
            },
        )
        db.execute(
            text(
                "UPDATE billing_sms_threads SET state = :state, updated_at = :now WHERE id = :id::uuid"
            ),
            {
                "state": "SMS_REPLY_RECEIVED" if direction == "IN" else "SMS_SENT",
                "now": _utcnow(),
                "id": thread_id,
            },
        )
        db.commit()
    except Exception:
        logger.exception("billing_sms_message_write_failed")
        db.rollback()


def _send_reply(
    *,
    api_key: str,
    from_number: str,
    to_number: str,
    text_body: str,
    messaging_profile_id: str | None,
    tenant_id: str | None,
    db: Session,
) -> None:
    try:
        thread_id = _ensure_sms_thread(
            db,
            tenant_id=tenant_id,
            central_phone=from_number,
            participant_phone=to_number,
            statement_id=None,
            account_id=None,
        )
        resp = send_sms(
            api_key=api_key,
            from_number=from_number,
            to_number=to_number,
            text=text_body,
            messaging_profile_id=messaging_profile_id,
        )
        mid = (resp.get("data") or {}).get("id") or str(uuid.uuid4())
        _log_sms(db, mid, tenant_id, "OUT", from_number, to_number, text_body, "sent")
        _log_structured_sms_message(
            db,
            thread_id=thread_id,
            message_id=mid,
            direction="OUT",
            from_phone=from_number,
            to_phone=to_number,
            body=text_body,
            status="SMS_SENT",
        )
    except TelnyxApiError as exc:
        logger.error(
            "telnyx_sms_reply_failed from=%s to=%s error=%s",
            from_number,
            to_number,
            exc,
        )


@router.post("/webhooks/telnyx/sms")
async def telnyx_sms_webhook(
    request: Request,
    db: Session = Depends(db_session_dependency),
) -> dict[str, Any]:
    raw_body = await request.body()
    settings = get_settings()

    if not verify_telnyx_webhook(
        raw_body=raw_body,
        signature_ed25519=request.headers.get("telnyx-signature-ed25519"),
        timestamp=request.headers.get("telnyx-timestamp"),
        public_key_base64=settings.telnyx_public_key,
        tolerance_seconds=settings.telnyx_webhook_tolerance_seconds,
    ):
        logger.warning("telnyx_sms_webhook_invalid_signature")
        raise HTTPException(status_code=400, detail="invalid_telnyx_signature")

    try:
        payload = json.loads(raw_body)
    except Exception:
        raise HTTPException(status_code=400, detail="invalid_json")

    data = payload.get("data", {})
    event_id: str = data.get("id") or str(uuid.uuid4())
    event_type: str = data.get("event_type", "")
    ep = data.get("payload", {})

    to_number: str = (
        ep.get("to", [{}])[0].get("phone_number", "")
        if isinstance(ep.get("to"), list)
        else ep.get("to", "")
    )
    from_number: str = (
        ep.get("from", {}).get("phone_number", "")
        if isinstance(ep.get("from"), dict)
        else ep.get("from", "")
    )
    body_text: str = (ep.get("text") or "").strip()
    message_id: str = ep.get("id") or event_id

    tenant_id: str | None = None
    if event_type == "message.received":
        context = _resolve_tenant_context(
            db,
            to_number=to_number,
            body_text=body_text,
            settings=settings,
        )
        tenant_id = context.get("tenant_id")
        thread_id = _ensure_sms_thread(
            db,
            tenant_id=tenant_id,
            central_phone=to_number,
            participant_phone=from_number,
            statement_id=context.get("statement_id"),
            account_id=context.get("account_id"),
        )

        inserted = _insert_event(db, event_id, event_type, tenant_id, data)
        if not inserted:
            logger.info("telnyx_sms_webhook_duplicate_event event_id=%s", event_id)
            return {"status": "duplicate_ignored"}
        _log_sms(
            db,
            message_id,
            tenant_id,
            "IN",
            from_number,
            to_number,
            body_text,
            "received",
        )
        _log_structured_sms_message(
            db,
            thread_id=thread_id,
            message_id=message_id,
            direction="IN",
            from_phone=from_number,
            to_phone=to_number,
            body=body_text,
            status="SMS_REPLY_RECEIVED",
        )

        # Opt out logic
        if body_text.upper() in STOP_KEYWORDS:
            _upsert_opt_out(db, tenant_id, from_number, "SMS_INBOUND")
            # Auto-ACK opt-out
            _send_reply(
                api_key=settings.telnyx_api_key,
                from_number=to_number,
                to_number=from_number,
                text_body="You have been unsubscribed from alerts. Reply START to resubscribe.",
                messaging_profile_id=None,
                tenant_id=tenant_id,
                db=db,
            )
            return {"status": "opt_out_processed"}

        if context.get("is_central") and not tenant_id:
            _send_reply(
                api_key=settings.telnyx_api_key,
                from_number=to_number,
                to_number=from_number,
                text_body=(
                    "FusionEMS Billing here. Please reply with your statement or account number "
                    "so I can route your request securely."
                ),
                messaging_profile_id=settings.telnyx_messaging_profile_id or None,
                tenant_id=None,
                db=db,
            )
            return {"status": "lookup_required", "matched": False}

        if not tenant_id:
            return {"status": "unmatched", "matched": False}

        # AI Reply Logic
        try:
            ai_service = AIAssistantService()
            reply = await ai_service.generate_sms_reply(
                tenant_id=tenant_id,
                patient_phone=from_number,
                message_body=body_text
            )

            if reply:
                _send_reply(
                    api_key=settings.telnyx_api_key,
                    from_number=to_number,
                    to_number=from_number,
                    text_body=reply,
                    messaging_profile_id=settings.telnyx_messaging_profile_id or None,
                    tenant_id=tenant_id,
                    db=db,
                )
        except Exception:
            logger.exception(
                "telnyx_sms_ai_reply_failed tenant_id=%s from=%s", tenant_id, from_number
            )
    elif event_type.startswith("message."):
        # delivery/failed/finalized events should still be auditable
        _insert_event(db, event_id, event_type, None, data)

    return {"status": "ok"}
