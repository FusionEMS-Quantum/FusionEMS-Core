from __future__ import annotations

import base64
import binascii
import json
import logging
import uuid
from datetime import UTC, datetime
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy import text
from sqlalchemy.orm import Session

from core_app.api import voice_payment_helper
from core_app.api.dependencies import db_session_dependency
from core_app.core.config import get_settings
from core_app.services.telephony_ai_worker import decide_next_action
from core_app.telnyx.client import (
    TelnyxApiError,
    call_answer,
    call_gather_using_audio,
    call_hangup,
    call_playback_start,
    call_transfer,
)
from core_app.telnyx.signature import verify_telnyx_webhook

logger = logging.getLogger(__name__)

router = APIRouter(tags=["Telnyx Voice"])

# ── IVR state names ───────────────────────────────────────────────────────────
STATE_MENU = "MENU"
STATE_COLLECT_STMT = "COLLECT_STATEMENT_ID"
STATE_COLLECT_PHONE = "COLLECT_SMS_PHONE"
STATE_TRANSFER = "TRANSFER"
STATE_DONE = "DONE"

STOP_RETRY_ATTEMPTS = 1
MAX_STMT_RETRIES = 1


def _audio(prompt: str) -> str:
    settings = get_settings()
    base = str(settings.ivr_audio_base_url).rstrip("/")
    return f"{base}/{prompt}"


def _utcnow() -> str:
    return datetime.now(UTC).isoformat()


# ── DB helpers ────────────────────────────────────────────────────────────────


def _resolve_tenant_by_did(db: Session, to_number: str) -> dict[str, Any] | None:
    settings = get_settings()
    central_phone = (settings.central_billing_phone_e164 or "").strip()
    if central_phone and to_number == central_phone:
        return {"tenant_id": None, "forward_to": settings.founder_billing_escalation_phone_e164 or None}

    row = db.execute(
        text("SELECT phone_e164 FROM central_billing_lines WHERE phone_e164 = :phone AND is_active = true LIMIT 1"),
        {"phone": to_number},
    ).fetchone()
    if row:
        return {"tenant_id": None, "forward_to": settings.founder_billing_escalation_phone_e164 or None}

    row = db.execute(
        text(
            "SELECT tenant_id, forward_to_phone_e164 "
            "FROM tenant_phone_numbers "
            "WHERE phone_e164 = :phone AND purpose = 'billing_voice' "
            "LIMIT 1"
        ),
        {"phone": to_number},
    ).fetchone()
    if row:
        return {
            "tenant_id": str(row.tenant_id),
            "forward_to": row.forward_to_phone_e164,
        }
    return None


def _get_or_create_call(
    db: Session,
    call_control_id: str,
    tenant_id: str | None,
    from_phone: str,
    to_phone: str,
) -> dict[str, Any]:
    row = db.execute(
        text(
            "SELECT call_control_id, tenant_id, from_phone, to_phone, state, attempts, statement_id, sms_phone "
            "FROM telnyx_calls WHERE call_control_id = :cid"
        ),
        {"cid": call_control_id},
    ).fetchone()
    if row:
        row_as_dict = row._asdict() if hasattr(row, "_asdict") else None
        if isinstance(row_as_dict, dict):
            return row_as_dict
        return {
            "call_control_id": getattr(row, "call_control_id", call_control_id),
            "tenant_id": getattr(row, "tenant_id", tenant_id),
            "from_phone": getattr(row, "from_phone", from_phone),
            "to_phone": getattr(row, "to_phone", to_phone),
            "state": getattr(row, "state", STATE_MENU),
            "attempts": getattr(row, "attempts", 0),
            "statement_id": getattr(row, "statement_id", None),
            "sms_phone": getattr(row, "sms_phone", None),
        }
    db.execute(
        text(
            "INSERT INTO telnyx_calls "
            "(call_control_id, tenant_id, from_phone, to_phone, state, attempts, created_at, updated_at) "
            "VALUES (:cid, :tid, :from_, :to_, :state, 0, :now, :now)"
        ),
        {
            "cid": call_control_id,
            "tid": tenant_id,
            "from_": from_phone,
            "to_": to_phone,
            "state": STATE_MENU,
            "now": _utcnow(),
        },
    )
    db.commit()
    return {
        "call_control_id": call_control_id,
        "tenant_id": tenant_id,
        "state": STATE_MENU,
        "attempts": 0,
    }


def _ensure_voice_session(
    db: Session,
    *,
    call_control_id: str,
    from_phone: str,
    to_phone: str,
) -> None:
    db.execute(
        text(
            """
            INSERT INTO billing_voice_sessions (
                session_id, call_control_id, caller_phone_number, central_line_phone,
                state, verification_state, started_at, created_at, updated_at
            ) VALUES (
                :sid, :cid, :from_phone, :to_phone,
                'CALL_RECEIVED', 'LOOKUP_PENDING', :now, :now, :now
            )
            ON CONFLICT (session_id) DO NOTHING
            """
        ),
        {
            "sid": call_control_id,
            "cid": call_control_id,
            "from_phone": from_phone,
            "to_phone": to_phone,
            "now": _utcnow(),
        },
    )
    db.commit()


def _update_voice_session(db: Session, call_control_id: str, **fields: Any) -> None:
    if not fields:
        return
    set_parts = ", ".join(f"{k} = :{k}" for k in fields)
    db.execute(
        text(
            f"UPDATE billing_voice_sessions SET {set_parts}, updated_at = :updated_at WHERE session_id = :sid"
        ),
        {
            **fields,
            "updated_at": _utcnow(),
            "sid": call_control_id,
        },
    )
    db.commit()


def _log_voice_event(
    db: Session,
    *,
    call_control_id: str,
    tenant_id: str | None,
    event_type: str,
    event_data: dict[str, Any],
    risk_level: str | None = None,
) -> None:
    db.execute(
        text(
            """
            INSERT INTO voice_automation_audit_events (
                session_id, tenant_id, event_type, event_data, risk_level, created_at
            ) VALUES (
                (SELECT id FROM billing_voice_sessions WHERE session_id = :sid),
                :tenant_id::uuid, :event_type, :event_data::jsonb, :risk_level, :now
            )
            """
        ),
        {
            "sid": call_control_id,
            "tenant_id": tenant_id,
            "event_type": event_type,
            "event_data": json.dumps(event_data),
            "risk_level": risk_level,
            "now": _utcnow(),
        },
    )
    db.commit()


def _resolve_account_context(db: Session, lookup_key: str) -> dict[str, Any] | None:
    sid = (lookup_key or "").strip()
    if not sid:
        return None

    # 1) billing_cases.id text match
    row = db.execute(
        text(
            "SELECT tenant_id, id::text AS account_id, id::text AS statement_id "
            "FROM billing_cases WHERE id::text = :sid LIMIT 1"
        ),
        {"sid": sid},
    ).fetchone()
    if row:
        return {
            "tenant_id": str(row.tenant_id),
            "account_id": str(row.account_id),
            "statement_id": str(row.statement_id),
        }

    # 2) lob_letters.statement_id match
    row2 = db.execute(
        text(
            "SELECT tenant_id, claim_id::text AS account_id, statement_id::text AS statement_id "
            "FROM lob_letters WHERE statement_id::text = :sid LIMIT 1"
        ),
        {"sid": sid},
    ).fetchone()
    if row2:
        return {
            "tenant_id": str(row2.tenant_id),
            "account_id": str(row2.account_id),
            "statement_id": str(row2.statement_id),
        }

    return None


def _get_billing_policy(db: Session, tenant_id: str | None) -> dict[str, Any]:
    if not tenant_id:
        return {}
    row = db.execute(
        text(
            "SELECT policy_json, allow_ai_payment_link_resend, allow_ai_statement_resend, "
            "allow_ai_payment_plan_intake, allow_ai_balance_inquiry "
            "FROM billing_phone_policies WHERE tenant_id = :tid::uuid LIMIT 1"
        ),
        {"tid": tenant_id},
    ).fetchone()
    if not row:
        return {}
    base = dict(row.policy_json or {})
    base.update(
        {
            "allow_ai_payment_link_resend": bool(row.allow_ai_payment_link_resend),
            "allow_ai_statement_resend": bool(row.allow_ai_statement_resend),
            "allow_ai_payment_plan_intake": bool(row.allow_ai_payment_plan_intake),
            "allow_ai_balance_inquiry": bool(row.allow_ai_balance_inquiry),
        }
    )
    return base


def _create_escalation(
    db: Session,
    *,
    call_control_id: str,
    tenant_id: str | None,
    caller_phone: str,
    statement_id: str | None,
    account_id: str | None,
    reason: str,
    ai_summary: str,
) -> None:
    db.execute(
        text(
            """
            INSERT INTO billing_call_escalations (
                session_id, tenant_id, caller_phone_number, statement_id, account_id,
                ai_summary, escalation_reason, recommended_next_action,
                status, created_at, updated_at
            ) VALUES (
                (SELECT id FROM billing_voice_sessions WHERE session_id = :sid),
                :tenant_id::uuid, :caller_phone, :statement_id, :account_id,
                :ai_summary, :reason, :next_action,
                'awaiting_human', :now, :now
            )
            """
        ),
        {
            "sid": call_control_id,
            "tenant_id": tenant_id,
            "caller_phone": caller_phone,
            "statement_id": statement_id,
            "account_id": account_id,
            "ai_summary": ai_summary,
            "reason": reason,
            "next_action": "Founder takeover with full account context",
            "now": _utcnow(),
        },
    )
    db.commit()


def _update_call(db: Session, call_control_id: str, **fields: Any) -> None:
    set_parts = ", ".join(f"{k} = :{k}" for k in fields)
    fields["cid"] = call_control_id
    fields["updated_at"] = _utcnow()
    db.execute(
        text(
            f"UPDATE telnyx_calls SET {set_parts}, updated_at = :updated_at WHERE call_control_id = :cid"
        ),
        fields,
    )
    db.commit()


def _get_call(db: Session, call_control_id: str) -> dict[str, Any] | None:
    row = db.execute(
        text(
            "SELECT call_control_id, tenant_id, from_phone, to_phone, state, attempts, statement_id, sms_phone "
            "FROM telnyx_calls WHERE call_control_id = :cid"
        ),
        {"cid": call_control_id},
    ).fetchone()
    if row is None:
        return None
    row_as_dict = row._asdict() if hasattr(row, "_asdict") else None
    if isinstance(row_as_dict, dict):
        return row_as_dict

    return {
        "state": getattr(row, "state", STATE_MENU),
        "attempts": getattr(row, "attempts", 0),
        "statement_id": getattr(row, "statement_id", None),
        "tenant_id": getattr(row, "tenant_id", None),
        "from_phone": getattr(row, "from_phone", None),
        "to_phone": getattr(row, "to_phone", None),
        "call_control_id": getattr(row, "call_control_id", call_control_id),
    }


def _insert_event(
    db: Session,
    event_id: str,
    event_type: str,
    tenant_id: str | None,
    raw: dict[str, Any],
) -> bool:
    result = db.execute(
        text(
            "INSERT INTO telnyx_events (event_id, event_type, tenant_id, received_at, raw_json, processed_at) "
            "VALUES (:eid, :etype, :tid, :now, :raw::jsonb, NULL) "
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
    rowcount = getattr(result, "rowcount", 0)
    return int(rowcount or 0) > 0


def _mark_event_processed(db: Session, event_id: str) -> None:
    db.execute(
        text("UPDATE telnyx_events SET processed_at = :now WHERE event_id = :eid"),
        {"now": _utcnow(), "eid": event_id},
    )
    db.commit()


def _validate_statement(db: Session, tenant_id: str, statement_id_digits: str) -> bool:
    row = db.execute(
        text(
            "SELECT id FROM billing_cases WHERE id::text = :sid AND tenant_id = :tid LIMIT 1"
        ),
        {"sid": statement_id_digits, "tid": tenant_id},
    ).fetchone()
    if row:
        return True
    row2 = db.execute(
        text(
            "SELECT statement_id FROM lob_letters WHERE statement_id::text = :sid AND tenant_id = :tid LIMIT 1"
        ),
        {"sid": statement_id_digits, "tid": tenant_id},
    ).fetchone()
    return row2 is not None


def _check_opt_out(db: Session, tenant_id: str, phone_e164: str) -> bool:
    if not tenant_id:
        return False
    row = db.execute(
        text(
            "SELECT 1 FROM telnyx_opt_outs WHERE tenant_id = :tid AND phone_e164 = :phone LIMIT 1"
        ),
        {"tid": tenant_id, "phone": phone_e164},
    ).fetchone()
    return row is not None


def _get_tenant_forward(db: Session, tenant_id: str) -> str | None:
    if not tenant_id:
        return None
    row = db.execute(
        text(
            "SELECT forward_to_phone_e164 FROM tenant_phone_numbers "
            "WHERE tenant_id = :tid AND purpose = 'billing_voice' LIMIT 1"
        ),
        {"tid": tenant_id},
    ).fetchone()
    return row.forward_to_phone_e164 if row else None


# ── IVR state actions ─────────────────────────────────────────────────────────


def _play_menu(api_key: str, call_control_id: str, cid_log: str) -> None:
    logger.info("ivr_menu call_control_id=%s", cid_log)
    call_gather_using_audio(
        api_key=api_key,
        call_control_id=call_control_id,
        audio_url=_audio("menu.wav"),
        minimum_digits=1,
        maximum_digits=1,
        timeout_millis=8000,
        client_state=STATE_MENU,
    )


def _play_collect_statement(api_key: str, call_control_id: str) -> None:
    call_gather_using_audio(
        api_key=api_key,
        call_control_id=call_control_id,
        audio_url=_audio("enter_statement_id.wav"),
        minimum_digits=6,
        maximum_digits=12,
        terminating_digit="#",
        timeout_millis=15000,
        client_state=STATE_COLLECT_STMT,
    )


def _play_collect_phone(api_key: str, call_control_id: str) -> None:
    call_gather_using_audio(
        api_key=api_key,
        call_control_id=call_control_id,
        audio_url=_audio("enter_phone.wav"),
        minimum_digits=10,
        maximum_digits=10,
        timeout_millis=12000,
        client_state=STATE_COLLECT_PHONE,
    )


def _do_transfer(
    api_key: str,
    call_control_id: str,
    forward_to: str | None,
    from_phone: str,
) -> None:
    if forward_to:
        logger.info(
            "ivr_transfer call_control_id=%s to=%s", call_control_id, forward_to
        )
        call_transfer(
            api_key=api_key,
            call_control_id=call_control_id,
            to=forward_to,
            from_=from_phone,
            client_state=STATE_TRANSFER,
        )
    else:
        call_playback_start(
            api_key=api_key,
            call_control_id=call_control_id,
            audio_url=_audio("transferring.wav"),
        )
        call_hangup(api_key=api_key, call_control_id=call_control_id)


def _normalize_e164_us(digits: str) -> str:
    d = "".join(c for c in digits if c.isdigit())
    if len(d) == 10:
        return f"+1{d}"
    if len(d) == 11 and d.startswith("1"):
        return f"+{d}"
    return f"+{d}"


# ── Webhook entrypoint ────────────────────────────────────────────────────────


@router.post("/webhooks/telnyx/voice")
async def telnyx_voice_webhook(
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
        logger.warning("telnyx_voice_webhook_invalid_signature")
        raise HTTPException(status_code=400, detail="invalid_telnyx_signature")

    try:
        payload = json.loads(raw_body)
    except json.JSONDecodeError as exc:
        raise HTTPException(status_code=400, detail="invalid_json") from exc

    data = payload.get("data", {})
    event_id: str = data.get("id") or str(uuid.uuid4())
    event_type: str = data.get("event_type", "")
    ep = data.get("payload", {})

    call_control_id: str = ep.get("call_control_id", "")
    to_number: str = ep.get("to", "") or ep.get("call_leg_id", "")
    from_number: str = ep.get("from", "")

    logger.info(
        "telnyx_voice event_type=%s call_control_id=%s event_id=%s",
        event_type,
        call_control_id,
        event_id,
    )

    tenant_info = _resolve_tenant_by_did(db, to_number)
    tenant_id: str | None = tenant_info["tenant_id"] if tenant_info else None

    inserted = _insert_event(db, event_id, event_type, tenant_id, payload)
    if not inserted:
        logger.info("telnyx_voice_duplicate event_id=%s", event_id)
        return {"status": "duplicate"}

    api_key = settings.telnyx_api_key
    if not api_key:
        logger.error("telnyx_voice TELNYX_API_KEY not configured")
        raise HTTPException(status_code=500, detail="telnyx_not_configured")

    try:
        await _dispatch_voice_event(
            event_type=event_type,
            ep=ep,
            call_control_id=call_control_id,
            from_number=from_number,
            to_number=to_number,
            tenant_id=tenant_id,
            tenant_info=tenant_info,
            api_key=api_key,
            db=db,
            settings=settings,
        )
    except TelnyxApiError as exc:
        logger.error(
            "telnyx_voice_api_error event_type=%s call_control_id=%s error=%s",
            event_type,
            call_control_id,
            exc,
        )
    finally:
        _mark_event_processed(db, event_id)

    return {"status": "ok"}


async def _dispatch_voice_event(
    *,
    event_type: str,
    ep: dict[str, Any],
    call_control_id: str,
    from_number: str,
    to_number: str,
    tenant_id: str | None,
    tenant_info: dict[str, Any] | None,
    api_key: str,
    db: Session,
    settings: Any,
) -> None:

    if event_type == "call.initiated":
        call_answer(api_key=api_key, call_control_id=call_control_id)
        return

    if event_type == "call.answered":
        _get_or_create_call(db, call_control_id, tenant_id, from_number, to_number)
        _ensure_voice_session(
            db,
            call_control_id=call_control_id,
            from_phone=from_number,
            to_phone=to_number,
        )
        _log_voice_event(
            db,
            call_control_id=call_control_id,
            tenant_id=tenant_id,
            event_type="call_answered",
            event_data={"from": from_number, "to": to_number},
        )
        _play_menu(api_key, call_control_id, call_control_id)
        return

    if event_type in ("call.gather.ended", "call.dtmf.received"):
        await _handle_gather(
            ep=ep,
            call_control_id=call_control_id,
            from_number=from_number,
            to_number=to_number,
            tenant_id=tenant_id,
            tenant_info=tenant_info,
            api_key=api_key,
            db=db,
            settings=settings,
        )
        return

    if event_type == "call.hangup":
        logger.info("ivr_hangup call_control_id=%s", call_control_id)
        _update_call(db, call_control_id, state=STATE_DONE)
        return

    logger.debug("telnyx_voice_unhandled_event event_type=%s", event_type)


async def _handle_gather(
    *,
    ep: dict[str, Any],
    call_control_id: str,
    from_number: str,
    to_number: str,
    tenant_id: str | None,
    tenant_info: dict[str, Any] | None,
    api_key: str,
    db: Session,
    settings: Any,
) -> None:
    digits: str = ep.get("digits", "").strip().rstrip("#")
    status: str = ep.get("status", "")

    raw_client_state: str = ep.get("client_state", "")
    try:
        call_state_bytes = base64.b64decode(raw_client_state + "==")
        call_state = call_state_bytes.decode("utf-8")
    except (ValueError, UnicodeDecodeError, binascii.Error):
        call_state = raw_client_state

    call_record = _get_call(db, call_control_id)
    if call_record is None:
        logger.warning("ivr_no_call_record call_control_id=%s", call_control_id)
        return

    forward_to = (tenant_info or {}).get("forward_to") or _get_tenant_forward(
        db, tenant_id or ""
    )

    if status == "no_input" or not digits:
        _update_voice_session(
            db,
            call_control_id,
            state="HUMAN_HANDOFF_REQUIRED",
            handoff_required=True,
            handoff_reason="no_input",
        )
        _create_escalation(
            db,
            call_control_id=call_control_id,
            tenant_id=tenant_id,
            caller_phone=from_number,
            statement_id=call_record.get("statement_id"),
            account_id=None,
            reason="no_input",
            ai_summary="Caller provided no usable input; requires human follow-up.",
        )
        _update_call(db, call_control_id, state=STATE_TRANSFER)
        _do_transfer(api_key, call_control_id, forward_to, from_number)
        return

    current_state = call_record.get("state", STATE_MENU)

    if current_state == STATE_MENU:
        if digits == "9":
            _play_menu(api_key, call_control_id, call_control_id)
        elif digits == "1":
            _update_call(db, call_control_id, state=STATE_COLLECT_STMT)
            _play_collect_statement(api_key, call_control_id)
        else:
            _update_call(db, call_control_id, state=STATE_TRANSFER)
            _do_transfer(api_key, call_control_id, forward_to, from_number)
        return

    if current_state == STATE_COLLECT_STMT:
        attempts: int = call_record.get("attempts", 0)
        tenant_for_validation = str(call_record.get("tenant_id") or tenant_id or "")
        if not digits or len(digits) < 6:
            _update_voice_session(
                db,
                call_control_id,
                state="HUMAN_HANDOFF_REQUIRED",
                handoff_required=True,
                handoff_reason="invalid_lookup_key",
            )
            _update_call(db, call_control_id, state=STATE_TRANSFER)
            _do_transfer(api_key, call_control_id, forward_to, from_number)
            return
        context = _resolve_account_context(db, digits)
        statement_valid = bool(
            tenant_for_validation
            and _validate_statement(db, tenant_for_validation, digits)
        )

        if context is None and statement_valid:
            context = {
                "tenant_id": tenant_for_validation,
                "statement_id": digits,
                "account_id": digits,
            }

        if not context:
            if attempts < MAX_STMT_RETRIES:
                _update_call(db, call_control_id, attempts=attempts + 1)
                call_playback_start(
                    api_key=api_key,
                    call_control_id=call_control_id,
                    audio_url=_audio("invalid.wav"),
                )
                _play_collect_statement(api_key, call_control_id)
            else:
                _update_voice_session(
                    db,
                    call_control_id,
                    state="HUMAN_HANDOFF_REQUIRED",
                    handoff_required=True,
                    handoff_reason="lookup_not_found",
                )
                _create_escalation(
                    db,
                    call_control_id=call_control_id,
                    tenant_id=tenant_id,
                    caller_phone=from_number,
                    statement_id=digits,
                    account_id=None,
                    reason="lookup_not_found",
                    ai_summary="Statement/account lookup failed after retry.",
                )
                _update_call(db, call_control_id, state=STATE_TRANSFER)
                _do_transfer(api_key, call_control_id, forward_to, from_number)
        else:
            resolved_tenant_id = context["tenant_id"]
            _update_call(
                db,
                call_control_id,
                state=STATE_COLLECT_PHONE,
                statement_id=context.get("statement_id") or digits,
                tenant_id=resolved_tenant_id,
                attempts=0,
            )
            _update_voice_session(
                db,
                call_control_id,
                state="LOOKUP_RESOLVED",
                verification_state="LOOKUP_RESOLVED",
                tenant_id=resolved_tenant_id,
                statement_id=context.get("statement_id") or digits,
                account_id=context.get("account_id"),
            )
            _log_voice_event(
                db,
                call_control_id=call_control_id,
                tenant_id=resolved_tenant_id,
                event_type="lookup_resolved",
                event_data={
                    "statement_id": context.get("statement_id") or digits,
                    "account_id": context.get("account_id"),
                },
            )
            _play_collect_phone(api_key, call_control_id)
        return

    if current_state == STATE_COLLECT_PHONE:
        if len(digits) != 10:
            call_playback_start(
                api_key=api_key,
                call_control_id=call_control_id,
                audio_url=_audio("invalid.wav"),
            )
            _play_collect_phone(api_key, call_control_id)
            return

        phone_e164 = _normalize_e164_us(digits)
        effective_tenant = call_record.get("tenant_id") or tenant_id

        if _check_opt_out(db, str(effective_tenant or ""), phone_e164):
            logger.info("ivr_opted_out phone=%s tenant_id=%s", phone_e164, tenant_id)
            _update_call(db, call_control_id, state=STATE_TRANSFER)
            _do_transfer(api_key, call_control_id, forward_to, from_number)
            return

        statement_id: str = call_record.get("statement_id", "")

        policy = _get_billing_policy(db, effective_tenant)
        decision = decide_next_action(
            utterance="text me the payment link",
            verification_ok=True,
            policy=policy,
        )

        if decision.action == "escalate_to_founder":
            _update_voice_session(
                db,
                call_control_id,
                state="HUMAN_HANDOFF_REQUIRED",
                handoff_required=True,
                handoff_reason=decision.reason,
                ai_intent=decision.intent,
                ai_summary="AI policy engine blocked autonomous action; escalation required.",
            )
            _create_escalation(
                db,
                call_control_id=call_control_id,
                tenant_id=effective_tenant,
                caller_phone=from_number,
                statement_id=statement_id,
                account_id=None,
                reason=decision.reason,
                ai_summary="Policy-aware AI required human takeover before sending payment workflow.",
            )
            _update_call(db, call_control_id, state=STATE_TRANSFER)
            _do_transfer(api_key, call_control_id, forward_to, from_number)
            return

        await voice_payment_helper.send_payment_link_for_call(
            db=db,
            api_key=api_key,
            settings=settings,
            tenant_id=effective_tenant or "",
            statement_id=statement_id,
            phone_e164=phone_e164,
            from_number=to_number,
        )

        _update_voice_session(
            db,
            call_control_id,
            state="ACTION_COMPLETED",
            verification_state="VERIFIED",
            ai_intent=decision.intent,
            ai_summary="Payment link sent successfully by centralized AI billing workflow.",
        )
        _log_voice_event(
            db,
            call_control_id=call_control_id,
            tenant_id=effective_tenant,
            event_type="send_sms_link",
            event_data={"statement_id": statement_id, "to_phone": phone_e164},
            risk_level="low",
        )

        _update_call(db, call_control_id, state=STATE_DONE, sms_phone=phone_e164)

        call_gather_using_audio(
            api_key=api_key,
            call_control_id=call_control_id,
            audio_url=_audio("sent_sms.wav"),
            minimum_digits=1,
            maximum_digits=1,
            timeout_millis=8000,
            client_state="POST_SMS",
        )
        return

    if call_state == "POST_SMS":
        if digits == "1":
            _do_transfer(api_key, call_control_id, forward_to, from_number)
        else:
            call_playback_start(
                api_key=api_key,
                call_control_id=call_control_id,
                audio_url=_audio("goodbye.wav"),
            )
            call_hangup(api_key=api_key, call_control_id=call_control_id)
        return
