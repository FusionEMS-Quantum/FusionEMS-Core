from __future__ import annotations

import base64
import binascii
import json
import logging
import uuid
from collections.abc import Mapping
from datetime import UTC, datetime
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy import text
from sqlalchemy.orm import Session

from core_app.api import voice_payment_helper
from core_app.api.dependencies import db_session_dependency
from core_app.core.config import get_settings
from core_app.services.billing_voicemail_service import ingest_voicemail_event
from core_app.services.telephony_ai_worker import decide_next_action
from core_app.services.telephony_control_service import (
    TelephonyControlConfig,
    transfer_call_with_fallback,
)
from core_app.telnyx.client import (
    TelnyxApiError,
    call_answer,
    call_gather_using_audio,
    call_gather_using_speak,
    call_hangup,
    call_playback_start,
    call_speak,
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

DEFAULT_PROMPT_TEXTS: dict[str, str] = {
    "menu_text": "Welcome to FusionEMS Billing. Press 1 to enter your statement ID, or press 0 to speak with billing.",
    "statement_text": "Please enter your statement ID followed by pound.",
    "phone_text": "Please enter your ten digit mobile phone number to receive your secure payment link.",
    "invalid_text": "Sorry, that entry was not valid.",
    "sent_sms_text": "Your secure payment link has been sent. Press 1 to speak with billing, or any other key to end this call.",
    "goodbye_text": "Thank you for calling FusionEMS Billing.",
    "transfer_text": "Please hold while we transfer your call.",
}


def _audio(prompt: str) -> str:
    settings = get_settings()
    base = str(settings.ivr_audio_base_url).rstrip("/")
    return f"{base}/{prompt}"


def _utcnow() -> str:
    return datetime.now(UTC).isoformat()


def _row_value(row: Any, key: str, index: int | None = None) -> Any:
    if row is None:
        return None
    attr_value = getattr(row, key, None)
    if attr_value is not None:
        return attr_value
    if isinstance(row, dict):
        return row.get(key)
    if index is None:
        return None
    try:
        return row[index]
    except (TypeError, KeyError, IndexError):
        return None


def _first_mapping_or_none(result: Any) -> Mapping[str, Any] | None:
    mappings_fn = getattr(result, "mappings", None)
    if not callable(mappings_fn):
        return None
    mapping_result = mappings_fn()
    first_fn = getattr(mapping_result, "first", None)
    if not callable(first_fn):
        return None
    row = first_fn()
    if isinstance(row, Mapping):
        return row
    return None


def _voice_runtime_config(db: Session) -> dict[str, Any]:
    settings = get_settings()
    system_tid = (settings.system_tenant_id or "").strip()
    cfg: dict[str, Any] = {
        "voice_mode": "human_audio",
        "tts_voice": "female",
        "tts_language": "en-US",
        "tts_primary_engine": "xtts",
        "tts_fallback_engine": "piper",
        "stt_engine": "faster_whisper",
        "stt_model_size": "small",
        "telephony_engine": "telnyx",
        "emergency_forwarding_enabled": False,
        "emergency_forward_reasons": ["legal_threat", "fraud_risk", "founder_review_required"],
        "prompts": dict(DEFAULT_PROMPT_TEXTS),
        "audio_urls": {
            "menu": "",
            "statement": "",
            "phone": "",
            "invalid": "",
            "sent_sms": "",
            "goodbye": "",
            "transfer": "",
        },
    }
    if not system_tid:
        return cfg

    row = db.execute(
        text(
            "SELECT policy_json FROM billing_phone_policies WHERE tenant_id = :tid::uuid LIMIT 1"
        ),
        {"tid": system_tid},
    ).fetchone()
    policy_json_raw = _row_value(row, "policy_json", 0)
    policy_json = dict(policy_json_raw or {})
    voice_cfg = dict(policy_json.get("voice_config") or {})

    cfg.update({
        "voice_mode": str(voice_cfg.get("voice_mode") or cfg["voice_mode"]),
        "tts_voice": str(voice_cfg.get("tts_voice") or cfg["tts_voice"]),
        "tts_language": str(voice_cfg.get("tts_language") or cfg["tts_language"]),
        "tts_primary_engine": str(voice_cfg.get("tts_primary_engine") or cfg["tts_primary_engine"]),
        "tts_fallback_engine": str(voice_cfg.get("tts_fallback_engine") or cfg["tts_fallback_engine"]),
        "stt_engine": str(voice_cfg.get("stt_engine") or cfg["stt_engine"]),
        "stt_model_size": str(voice_cfg.get("stt_model_size") or cfg["stt_model_size"]),
        "telephony_engine": str(voice_cfg.get("telephony_engine") or cfg["telephony_engine"]),
        "emergency_forwarding_enabled": bool(
            voice_cfg.get("emergency_forwarding_enabled", cfg["emergency_forwarding_enabled"])
        ),
        "emergency_forward_reasons": [
            str(v).strip().lower()
            for v in (
                voice_cfg.get("emergency_forward_reasons") or cfg["emergency_forward_reasons"]
            )
            if str(v).strip()
        ],
    })
    cfg["prompts"] = {**cfg["prompts"], **dict(voice_cfg.get("prompts") or {})}
    cfg["audio_urls"] = {**cfg["audio_urls"], **dict(voice_cfg.get("audio_urls") or {})}
    return cfg


def _gather_prompt(
    *,
    db: Session,
    api_key: str,
    call_control_id: str,
    prompt_key: str,
    fallback_audio_file: str,
    minimum_digits: int,
    maximum_digits: int,
    timeout_millis: int,
    client_state: str,
    terminating_digit: str = "",
) -> None:
    cfg = _voice_runtime_config(db)
    mode = str(cfg.get("voice_mode") or "human_audio").lower()
    audio_urls = dict(cfg.get("audio_urls") or {})
    prompts = dict(cfg.get("prompts") or {})

    custom_audio = str(audio_urls.get(prompt_key) or "").strip()
    tts_payload = str(prompts.get(f"{prompt_key}_text") or DEFAULT_PROMPT_TEXTS.get(f"{prompt_key}_text") or "").strip()

    if mode == "human_audio":
        audio_url = custom_audio or _audio(fallback_audio_file)
        call_gather_using_audio(
            api_key=api_key,
            call_control_id=call_control_id,
            audio_url=audio_url,
            minimum_digits=minimum_digits,
            maximum_digits=maximum_digits,
            terminating_digit=terminating_digit,
            timeout_millis=timeout_millis,
            client_state=client_state,
        )
        return

    call_gather_using_speak(
        api_key=api_key,
        call_control_id=call_control_id,
        payload=tts_payload or "Please enter your response.",
        voice=str(cfg.get("tts_voice") or "female"),
        language=str(cfg.get("tts_language") or "en-US"),
        minimum_digits=minimum_digits,
        maximum_digits=maximum_digits,
        terminating_digit=terminating_digit,
        timeout_millis=timeout_millis,
        client_state=client_state,
    )


def _play_prompt(
    *,
    db: Session,
    api_key: str,
    call_control_id: str,
    prompt_key: str,
    fallback_audio_file: str,
) -> None:
    cfg = _voice_runtime_config(db)
    mode = str(cfg.get("voice_mode") or "human_audio").lower()
    audio_urls = dict(cfg.get("audio_urls") or {})
    prompts = dict(cfg.get("prompts") or {})
    custom_audio = str(audio_urls.get(prompt_key) or "").strip()
    tts_payload = str(prompts.get(f"{prompt_key}_text") or DEFAULT_PROMPT_TEXTS.get(f"{prompt_key}_text") or "").strip()

    if mode == "human_audio":
        call_playback_start(
            api_key=api_key,
            call_control_id=call_control_id,
            audio_url=custom_audio or _audio(fallback_audio_file),
        )
        return

    call_speak(
        api_key=api_key,
        call_control_id=call_control_id,
        payload=tts_payload or "Please hold.",
        voice=str(cfg.get("tts_voice") or "female"),
        language=str(cfg.get("tts_language") or "en-US"),
    )


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
    result = db.execute(
        text(
            "SELECT call_control_id, tenant_id, from_phone, to_phone, state, attempts, statement_id, sms_phone "
            "FROM telnyx_calls WHERE call_control_id = :cid"
        ),
        {"cid": call_control_id},
    )
    row = _first_mapping_or_none(result)
    if row:
        return {
            "call_control_id": row.get("call_control_id", call_control_id),
            "tenant_id": row.get("tenant_id", tenant_id),
            "from_phone": row.get("from_phone", from_phone),
            "to_phone": row.get("to_phone", to_phone),
            "state": row.get("state", STATE_MENU),
            "attempts": row.get("attempts", 0),
            "statement_id": row.get("statement_id"),
            "sms_phone": row.get("sms_phone"),
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
    base = dict(_row_value(row, "policy_json", 0) or {})
    base.update(
        {
            "allow_ai_payment_link_resend": bool(_row_value(row, "allow_ai_payment_link_resend", 1)),
            "allow_ai_statement_resend": bool(_row_value(row, "allow_ai_statement_resend", 2)),
            "allow_ai_payment_plan_intake": bool(_row_value(row, "allow_ai_payment_plan_intake", 3)),
            "allow_ai_balance_inquiry": bool(_row_value(row, "allow_ai_balance_inquiry", 4)),
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
    result = db.execute(
        text(
            "SELECT call_control_id, tenant_id, from_phone, to_phone, state, attempts, statement_id, sms_phone "
            "FROM telnyx_calls WHERE call_control_id = :cid"
        ),
        {"cid": call_control_id},
    )
    mapping_row = _first_mapping_or_none(result)
    if mapping_row is not None:
        return {
            "state": mapping_row.get("state", STATE_MENU),
            "attempts": mapping_row.get("attempts", 0),
            "statement_id": mapping_row.get("statement_id"),
            "tenant_id": mapping_row.get("tenant_id"),
            "from_phone": mapping_row.get("from_phone"),
            "to_phone": mapping_row.get("to_phone"),
            "call_control_id": mapping_row.get("call_control_id", call_control_id),
        }

    fetchone_fn = getattr(result, "fetchone", None)
    row = fetchone_fn() if callable(fetchone_fn) else None
    if row is None:
        return None
    return {
        "state": _row_value(row, "state") or STATE_MENU,
        "attempts": int(_row_value(row, "attempts") or 0),
        "statement_id": _row_value(row, "statement_id"),
        "tenant_id": _row_value(row, "tenant_id"),
        "from_phone": _row_value(row, "from_phone"),
        "to_phone": _row_value(row, "to_phone"),
        "call_control_id": _row_value(row, "call_control_id") or call_control_id,
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


def _play_menu(db: Session, api_key: str, call_control_id: str, cid_log: str) -> None:
    logger.info("ivr_menu call_control_id=%s", cid_log)
    _gather_prompt(
        db=db,
        api_key=api_key,
        call_control_id=call_control_id,
        prompt_key="menu",
        fallback_audio_file="menu.wav",
        minimum_digits=1,
        maximum_digits=1,
        timeout_millis=8000,
        client_state=STATE_MENU,
    )


def _play_collect_statement(db: Session, api_key: str, call_control_id: str) -> None:
    _gather_prompt(
        db=db,
        api_key=api_key,
        call_control_id=call_control_id,
        prompt_key="statement",
        fallback_audio_file="enter_statement_id.wav",
        minimum_digits=6,
        maximum_digits=12,
        terminating_digit="#",
        timeout_millis=15000,
        client_state=STATE_COLLECT_STMT,
    )


def _play_collect_phone(db: Session, api_key: str, call_control_id: str) -> None:
    _gather_prompt(
        db=db,
        api_key=api_key,
        call_control_id=call_control_id,
        prompt_key="phone",
        fallback_audio_file="enter_phone.wav",
        minimum_digits=10,
        maximum_digits=10,
        timeout_millis=12000,
        client_state=STATE_COLLECT_PHONE,
    )


def _do_transfer(
    db: Session,
    api_key: str,
    call_control_id: str,
    forward_to: str | None,
    from_phone: str,
) -> None:
    if forward_to:
        logger.info(
            "ivr_transfer call_control_id=%s to=%s", call_control_id, forward_to
        )
        cfg = _voice_runtime_config(db)
        selected_engine = str(cfg.get("telephony_engine") or get_settings().billing_telephony_engine or "telnyx").strip().lower()
        settings = get_settings()
        control_cfg = TelephonyControlConfig(
            mode=selected_engine,
            asterisk_ari_base_url=str(settings.billing_telephony_control_url or "").strip(),
            asterisk_ari_username="",
            asterisk_ari_password=str(settings.billing_telephony_control_token or "").strip(),
            freeswitch_control_url=str(settings.billing_telephony_control_url or "").strip(),
        )

        engine_used = transfer_call_with_fallback(
            call_control_id=call_control_id,
            to_number=forward_to,
            from_number=from_phone,
            cfg=control_cfg,
            telnyx_transfer=lambda: call_transfer(
                api_key=api_key,
                call_control_id=call_control_id,
                to=forward_to,
                from_=from_phone,
                client_state=STATE_TRANSFER,
            ),
        )
        logger.info("ivr_transfer_engine_used call_control_id=%s engine=%s", call_control_id, engine_used)
    else:
        _play_prompt(
            db=db,
            api_key=api_key,
            call_control_id=call_control_id,
            prompt_key="transfer",
            fallback_audio_file="transferring.wav",
        )
        call_hangup(api_key=api_key, call_control_id=call_control_id)


def _normalize_e164_us(digits: str) -> str:
    d = "".join(c for c in digits if c.isdigit())
    if len(d) == 10:
        return f"+1{d}"
    if len(d) == 11 and d.startswith("1"):
        return f"+{d}"
    return f"+{d}"


def _forward_target(
    *,
    db: Session,
    tenant_forward: str | None,
    reason: str,
    settings: Any,
) -> str | None:
    cfg = _voice_runtime_config(db)
    if not bool(cfg.get("emergency_forwarding_enabled", False)):
        return tenant_forward

    reason_key = (reason or "").strip().lower()
    allowed = {
        str(v).strip().lower()
        for v in (cfg.get("emergency_forward_reasons") or [])
        if str(v).strip()
    }
    if reason_key and reason_key in allowed:
        founder_phone = str(settings.founder_billing_escalation_phone_e164 or "").strip()
        if founder_phone:
            return founder_phone
    return tenant_forward


# ── Webhook entrypoint ────────────────────────────────────────────────────────


@router.post("/api/v1/webhooks/telnyx/voice")
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
        _play_menu(db, api_key, call_control_id, call_control_id)
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

    if event_type in ("call.recording.saved", "call.recording.available", "call.voicemail.saved"):
        session_cfg = _voice_runtime_config(db)
        try:
            result = ingest_voicemail_event(
                db=db,
                event_payload=ep,
                from_phone=from_number,
                to_phone=to_number,
                call_control_id=call_control_id,
                system_tenant_id=settings.system_tenant_id,
                stt_engine=str(session_cfg.get("stt_engine") or settings.oss_stt_engine or "faster_whisper"),
                stt_model_size=str(session_cfg.get("stt_model_size") or settings.oss_stt_model_size or "small"),
            )
        except (ValueError, RuntimeError, OSError) as exc:
            logger.exception("voicemail_ingestion_failed call_control_id=%s error=%s", call_control_id, exc)
            result = {"status": "voicemail_ingestion_failed"}
        _log_voice_event(
            db,
            call_control_id=call_control_id,
            tenant_id=tenant_id,
            event_type="voicemail_ingested",
            event_data=result,
            risk_level=str(result.get("risk_level") or "low"),
        )
        _update_voice_session(
            db,
            call_control_id,
            state="VOICEMAIL_REQUESTED",
            handoff_required=True,
            handoff_reason="voicemail_fallback",
            ai_summary="Structured voicemail captured for callback workflow.",
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
        reason = "founder_review_required" if status == "no_input" else "invalid_input"
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
        _do_transfer(
            db,
            api_key,
            call_control_id,
            _forward_target(db=db, tenant_forward=forward_to, reason=reason, settings=settings),
            from_number,
        )
        return

    current_state = call_record.get("state", STATE_MENU)

    if current_state == STATE_MENU:
        if digits == "9":
            _play_menu(db, api_key, call_control_id, call_control_id)
        elif digits == "1":
            _update_call(db, call_control_id, state=STATE_COLLECT_STMT)
            _play_collect_statement(db, api_key, call_control_id)
        else:
            _update_call(db, call_control_id, state=STATE_TRANSFER)
            _do_transfer(
                db,
                api_key,
                call_control_id,
                _forward_target(
                    db=db,
                    tenant_forward=forward_to,
                    reason="founder_review_required",
                    settings=settings,
                ),
                from_number,
            )
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
            _do_transfer(
                db,
                api_key,
                call_control_id,
                _forward_target(
                    db=db,
                    tenant_forward=forward_to,
                    reason="founder_review_required",
                    settings=settings,
                ),
                from_number,
            )
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
                _play_prompt(
                    db=db,
                    api_key=api_key,
                    call_control_id=call_control_id,
                    prompt_key="invalid",
                    fallback_audio_file="invalid.wav",
                )
                _play_collect_statement(db, api_key, call_control_id)
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
                _do_transfer(
                    db,
                    api_key,
                    call_control_id,
                    _forward_target(
                        db=db,
                        tenant_forward=forward_to,
                        reason="founder_review_required",
                        settings=settings,
                    ),
                    from_number,
                )
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
            _play_collect_phone(db, api_key, call_control_id)
        return

    if current_state == STATE_COLLECT_PHONE:
        if len(digits) != 10:
            _play_prompt(
                db=db,
                api_key=api_key,
                call_control_id=call_control_id,
                prompt_key="invalid",
                fallback_audio_file="invalid.wav",
            )
            _play_collect_phone(db, api_key, call_control_id)
            return

        phone_e164 = _normalize_e164_us(digits)
        effective_tenant = call_record.get("tenant_id") or tenant_id

        if _check_opt_out(db, str(effective_tenant or ""), phone_e164):
            logger.info("ivr_opted_out phone=%s tenant_id=%s", phone_e164, tenant_id)
            _update_call(db, call_control_id, state=STATE_TRANSFER)
            _do_transfer(
                db,
                api_key,
                call_control_id,
                _forward_target(
                    db=db,
                    tenant_forward=forward_to,
                    reason="founder_review_required",
                    settings=settings,
                ),
                from_number,
            )
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
            _do_transfer(
                db,
                api_key,
                call_control_id,
                _forward_target(
                    db=db,
                    tenant_forward=forward_to,
                    reason="founder_review_required",
                    settings=settings,
                ),
                from_number,
            )
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

        _gather_prompt(
            db=db,
            api_key=api_key,
            call_control_id=call_control_id,
            prompt_key="sent_sms",
            fallback_audio_file="sent_sms.wav",
            minimum_digits=1,
            maximum_digits=1,
            timeout_millis=8000,
            client_state="POST_SMS",
        )
        return

    if call_state == "POST_SMS":
        if digits == "1":
            _do_transfer(
                db,
                api_key,
                call_control_id,
                _forward_target(
                    db=db,
                    tenant_forward=forward_to,
                    reason="founder_review_required",
                    settings=settings,
                ),
                from_number,
            )
        else:
            _play_prompt(
                db=db,
                api_key=api_key,
                call_control_id=call_control_id,
                prompt_key="goodbye",
                fallback_audio_file="goodbye.wav",
            )
            call_hangup(api_key=api_key, call_control_id=call_control_id)
        return
