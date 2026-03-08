from __future__ import annotations

import json
import logging
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from core_app.api.dependencies import db_session_dependency, get_current_user
from core_app.core.config import get_settings
from core_app.schemas.auth import CurrentUser
from core_app.services.open_source_tts_service import (
    OpenSourceTTSError,
    audio_file_path,
    render_prompts_to_audio_urls,
)

router = APIRouter(prefix="/api/v1/founder/billing-voice", tags=["Founder Billing Voice"])
logger = logging.getLogger(__name__)


def _isoformat_or_none(value: Any) -> str | None:
    if value is None:
        return None
    iso = getattr(value, "isoformat", None)
    if callable(iso):
        return str(iso())
    return str(value)


def _require_founder(current: CurrentUser) -> None:
    if str(current.role).lower() != "founder":
        raise HTTPException(status_code=403, detail="founder_only")


def _default_voice_config() -> dict[str, Any]:
    return {
        "voice_mode": "human_audio",  # human_audio | tts
        "tts_voice": "female",
        "tts_language": "en-US",
        "tts_primary_engine": "xtts",
        "tts_fallback_engine": "piper",
        "stt_engine": "faster_whisper",
        "stt_model_size": "small",
        "telephony_engine": "telnyx",  # telnyx | asterisk | freeswitch
        "emergency_forwarding_enabled": False,
        "emergency_forward_reasons": [
            "legal_threat",
            "fraud_risk",
            "founder_review_required",
        ],
        "prompts": {
            "menu_text": "Welcome to FusionEMS Billing. Press 1 to enter your statement ID, or press 0 to speak with billing.",
            "statement_text": "Please enter your statement ID followed by pound.",
            "phone_text": "Please enter your ten digit mobile phone number to receive your secure payment link.",
            "invalid_text": "Sorry, that entry was not valid.",
            "sent_sms_text": "Your secure payment link has been sent. Press 1 to speak with billing, or any other key to end this call.",
            "goodbye_text": "Thank you for calling FusionEMS Billing.",
            "transfer_text": "Please hold while we transfer your call.",
        },
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


def _load_voice_config(db: Session) -> dict[str, Any]:
    settings = get_settings()
    if not settings.system_tenant_id:
        return _default_voice_config()

    row = db.execute(
        text(
            "SELECT policy_json FROM billing_phone_policies "
            "WHERE tenant_id = :tid::uuid LIMIT 1"
        ),
        {"tid": settings.system_tenant_id},
    ).mappings().first()

    default_cfg = _default_voice_config()
    policy_json = (row or {}).get("policy_json") or {}
    voice_cfg = dict(policy_json.get("voice_config") or {})

    merged = {
        **default_cfg,
        **voice_cfg,
        "prompts": {
            **default_cfg["prompts"],
            **dict(voice_cfg.get("prompts") or {}),
        },
        "audio_urls": {
            **default_cfg["audio_urls"],
            **dict(voice_cfg.get("audio_urls") or {}),
        },
    }
    return merged


def _save_voice_config(db: Session, config_payload: dict[str, Any]) -> dict[str, Any]:
    settings = get_settings()
    if not settings.system_tenant_id:
        raise HTTPException(status_code=500, detail="SYSTEM_TENANT_ID is not configured")

    try:
        UUID(str(settings.system_tenant_id))
    except ValueError as exc:
        raise HTTPException(status_code=500, detail="SYSTEM_TENANT_ID is not a valid UUID") from exc

    default_cfg = _default_voice_config()
    mode = str(config_payload.get("voice_mode") or default_cfg["voice_mode"]).strip().lower()
    if mode not in ("human_audio", "tts"):
        raise HTTPException(status_code=422, detail="voice_mode must be one of: human_audio, tts")

    tts_primary_engine = str(
        config_payload.get("tts_primary_engine") or default_cfg["tts_primary_engine"]
    ).strip().lower()
    tts_fallback_engine = str(
        config_payload.get("tts_fallback_engine") or default_cfg["tts_fallback_engine"]
    ).strip().lower()
    stt_engine = str(config_payload.get("stt_engine") or default_cfg["stt_engine"]).strip().lower()
    telephony_engine = str(
        config_payload.get("telephony_engine") or default_cfg["telephony_engine"]
    ).strip().lower()

    if tts_primary_engine not in ("xtts", "piper"):
        raise HTTPException(status_code=422, detail="tts_primary_engine must be one of: xtts, piper")
    if tts_fallback_engine not in ("xtts", "piper"):
        raise HTTPException(status_code=422, detail="tts_fallback_engine must be one of: xtts, piper")
    if stt_engine not in ("faster_whisper",):
        raise HTTPException(status_code=422, detail="stt_engine must be: faster_whisper")
    if telephony_engine not in ("telnyx", "asterisk", "freeswitch"):
        raise HTTPException(
            status_code=422,
            detail="telephony_engine must be one of: telnyx, asterisk, freeswitch",
        )

    prompts = {
        **default_cfg["prompts"],
        **dict(config_payload.get("prompts") or {}),
    }
    audio_urls = {
        **default_cfg["audio_urls"],
        **dict(config_payload.get("audio_urls") or {}),
    }

    voice_cfg = {
        "voice_mode": mode,
        "tts_voice": str(config_payload.get("tts_voice") or default_cfg["tts_voice"]),
        "tts_language": str(config_payload.get("tts_language") or default_cfg["tts_language"]),
        "tts_primary_engine": tts_primary_engine,
        "tts_fallback_engine": tts_fallback_engine,
        "stt_engine": stt_engine,
        "stt_model_size": str(
            config_payload.get("stt_model_size") or default_cfg["stt_model_size"]
        ),
        "telephony_engine": telephony_engine,
        "emergency_forwarding_enabled": bool(
            config_payload.get("emergency_forwarding_enabled", default_cfg["emergency_forwarding_enabled"])
        ),
        "emergency_forward_reasons": [
            str(v).strip() for v in (config_payload.get("emergency_forward_reasons") or default_cfg["emergency_forward_reasons"]) if str(v).strip()
        ],
        "prompts": prompts,
        "audio_urls": audio_urls,
    }

    row = db.execute(
        text(
            "SELECT policy_json FROM billing_phone_policies WHERE tenant_id = :tid::uuid LIMIT 1"
        ),
        {"tid": settings.system_tenant_id},
    ).mappings().first()

    policy_json = dict((row or {}).get("policy_json") or {})
    policy_json["voice_config"] = voice_cfg

    now = datetime.now(UTC).isoformat()
    db.execute(
        text(
            """
            INSERT INTO billing_phone_policies (
                tenant_id, billing_mode,
                allow_ai_balance_inquiry, allow_ai_payment_link_resend,
                allow_ai_statement_resend, allow_ai_address_confirmation,
                allow_ai_payment_plan_intake, collections_enabled,
                debt_setoff_enabled, require_human_for_disputes,
                require_human_for_legal_threat, escalation_priority,
                policy_json, created_at, updated_at
            ) VALUES (
                :tenant_id::uuid, 'FUSION_RCM',
                true, true,
                true, false,
                false, false,
                false, true,
                true, 'normal',
                :policy_json::jsonb, :now, :now
            )
            ON CONFLICT (tenant_id)
            DO UPDATE SET
                policy_json = EXCLUDED.policy_json,
                updated_at = EXCLUDED.updated_at
            """
        ),
        {
            "tenant_id": settings.system_tenant_id,
            "policy_json": json.dumps(policy_json),
            "now": now,
        },
    )
    db.commit()
    return voice_cfg


@router.get("/config")
async def get_voice_config(
    current: CurrentUser = Depends(get_current_user),
    db: Session = Depends(db_session_dependency),
):
    _require_founder(current)
    return {"config": _load_voice_config(db)}


@router.put("/config")
async def update_voice_config(
    payload: dict[str, Any],
    current: CurrentUser = Depends(get_current_user),
    db: Session = Depends(db_session_dependency),
):
    _require_founder(current)
    cfg = _save_voice_config(db, payload)
    return {"status": "ok", "config": cfg}


@router.post("/config/render-prompts")
async def render_voice_prompts_to_audio(
    payload: dict[str, Any],
    current: CurrentUser = Depends(get_current_user),
    db: Session = Depends(db_session_dependency),
):
    _require_founder(current)
    cfg = _load_voice_config(db)
    preferred_engine = str(
        payload.get("preferred_engine") or cfg.get("tts_primary_engine") or "xtts"
    ).strip().lower()

    try:
        rendered_urls = render_prompts_to_audio_urls(
            dict(cfg.get("prompts") or {}),
            preferred_engine=preferred_engine,
        )
    except OpenSourceTTSError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    cfg["audio_urls"] = {
        **dict(cfg.get("audio_urls") or {}),
        **rendered_urls,
    }
    saved = _save_voice_config(db, cfg)
    return {
        "status": "ok",
        "rendered_count": len(rendered_urls),
        "engine": preferred_engine,
        "config": saved,
    }


@router.get("/audio/{audio_id}.wav")
async def serve_generated_prompt_audio(audio_id: str):
    try:
        wav_path = audio_file_path(audio_id)
    except OpenSourceTTSError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    if not Path(wav_path).exists():
        raise HTTPException(status_code=404, detail="audio_not_found")

    return FileResponse(path=wav_path, media_type="audio/wav", filename=f"{audio_id}.wav")


@router.get("/summary")
async def billing_voice_summary(
    current: CurrentUser = Depends(get_current_user),
    db: Session = Depends(db_session_dependency),
):
    _require_founder(current)
    active_calls = db.execute(
        text("SELECT COUNT(*) FROM billing_voice_sessions WHERE ended_at IS NULL")
    ).scalar() or 0
    pending_handoffs = db.execute(
        text("SELECT COUNT(*) FROM billing_call_escalations WHERE status = 'awaiting_human'")
    ).scalar() or 0
    unresolved_sessions = db.execute(
        text(
            "SELECT COUNT(*) FROM billing_voice_sessions "
            "WHERE state IN ('HUMAN_HANDOFF_REQUIRED', 'CALL_FAILED')"
        )
    ).scalar() or 0

    top_actions_rows = db.execute(
        text(
            "SELECT event_type, COUNT(*) AS c "
            "FROM voice_automation_audit_events "
            "WHERE created_at >= now() - interval '7 days' "
            "GROUP BY event_type ORDER BY c DESC LIMIT 3"
        )
    ).mappings().all()

    return {
        "active_billing_calls": int(active_calls),
        "awaiting_human_followup": int(pending_handoffs),
        "unresolved_voice_sessions": int(unresolved_sessions),
        "top_billing_phone_actions": [
            {"action": r["event_type"], "count": int(r["c"])} for r in top_actions_rows
        ],
    }


@router.get("/escalations")
async def list_escalations(
    status: str = "awaiting_human",
    limit: int = 50,
    current: CurrentUser = Depends(get_current_user),
    db: Session = Depends(db_session_dependency),
):
    _require_founder(current)
    rows = db.execute(
        text(
            """
            SELECT
                e.id,
                e.session_id,
                e.tenant_id,
                e.caller_phone_number,
                e.statement_id,
                e.account_id,
                e.ai_summary,
                e.escalation_reason,
                e.recommended_next_action,
                e.status,
                e.created_at,
                s.verification_state,
                s.ai_intent,
                s.ai_summary AS session_ai_summary
            FROM billing_call_escalations e
            LEFT JOIN billing_voice_sessions s ON s.id = e.session_id
            WHERE e.status = :status
            ORDER BY e.created_at DESC
            LIMIT :limit
            """
        ),
        {"status": status, "limit": max(1, min(limit, 200))},
    ).mappings().all()

    return {
        "items": [
            {
                "id": str(r["id"]),
                "session_id": str(r["session_id"]) if r.get("session_id") else None,
                "tenant_id": str(r["tenant_id"]) if r.get("tenant_id") else None,
                "caller_phone_number": r.get("caller_phone_number"),
                "statement_id": r.get("statement_id"),
                "account_id": r.get("account_id"),
                "verification_state": r.get("verification_state"),
                "ai_intent": r.get("ai_intent"),
                "ai_summary": r.get("ai_summary") or r.get("session_ai_summary"),
                "escalation_reason": r.get("escalation_reason"),
                "recommended_next_action": r.get("recommended_next_action"),
                "status": r.get("status"),
                "created_at": _isoformat_or_none(r.get("created_at")),
            }
            for r in rows
        ]
    }


@router.get("/voicemails")
async def list_voicemails(
    state: str | None = None,
    limit: int = 50,
    current: CurrentUser = Depends(get_current_user),
    db: Session = Depends(db_session_dependency),
):
    _require_founder(current)
    sql = (
        """
        SELECT
            v.id,
            v.caller_phone_number,
            v.received_at,
            v.tenant_id,
            v.statement_id,
            v.account_id,
            v.state,
            v.urgency,
            v.risk_level,
            t.transcript_text,
            i.intent_code,
            r.risk_score,
            r.risk_level AS risk_score_level
        FROM billing_voicemails v
        LEFT JOIN LATERAL (
            SELECT transcript_text
            FROM billing_voicemail_transcripts
            WHERE voicemail_id = v.id
            ORDER BY created_at DESC
            LIMIT 1
        ) t ON true
        LEFT JOIN LATERAL (
            SELECT intent_code
            FROM billing_voicemail_intents
            WHERE voicemail_id = v.id
            ORDER BY created_at DESC
            LIMIT 1
        ) i ON true
        LEFT JOIN LATERAL (
            SELECT risk_score, risk_level
            FROM billing_voicemail_risk_scores
            WHERE voicemail_id = v.id
            ORDER BY created_at DESC
            LIMIT 1
        ) r ON true
        """
    )
    params: dict[str, Any] = {"limit": max(1, min(limit, 200))}
    if state:
        sql += " WHERE v.state = :state "
        params["state"] = state
    sql += " ORDER BY v.received_at DESC NULLS LAST, v.created_at DESC LIMIT :limit"

    try:
        rows = db.execute(text(sql), params).mappings().all()
    except SQLAlchemyError as exc:
        logger.exception("billing_voice_voicemails_query_failed state=%s limit=%s", state, limit)
        raise HTTPException(status_code=503, detail="voicemail_query_unavailable") from exc
    return {
        "items": [
            {
                "id": str(r.get("id")),
                "caller_phone_number": r.get("caller_phone_number"),
                "received_at": _isoformat_or_none(r.get("received_at")),
                "tenant_id": str(r.get("tenant_id")) if r.get("tenant_id") else None,
                "statement_id": r.get("statement_id"),
                "account_id": r.get("account_id"),
                "state": r.get("state"),
                "urgency": r.get("urgency"),
                "risk_level": r.get("risk_level") or r.get("risk_score_level"),
                "risk_score": int(r.get("risk_score") or 0),
                "transcript_preview": str(r.get("transcript_text") or "")[:220],
                "intent_code": r.get("intent_code"),
            }
            for r in rows
        ]
    }


@router.get("/callbacks")
async def list_callback_tasks(
    state: str | None = None,
    limit: int = 50,
    current: CurrentUser = Depends(get_current_user),
    db: Session = Depends(db_session_dependency),
):
    _require_founder(current)
    sql = (
        """
        SELECT
            id,
            voicemail_id,
            tenant_id,
            callback_phone,
            callback_state,
            sla_due_at,
            priority,
            reason,
            created_at,
            updated_at
        FROM billing_callback_tasks
        """
    )
    params: dict[str, Any] = {"limit": max(1, min(limit, 200))}
    if state:
        sql += " WHERE callback_state = :state "
        params["state"] = state
    sql += " ORDER BY sla_due_at ASC NULLS LAST, created_at DESC LIMIT :limit"

    try:
        rows = db.execute(text(sql), params).mappings().all()
    except SQLAlchemyError as exc:
        logger.exception("billing_voice_callbacks_query_failed state=%s limit=%s", state, limit)
        raise HTTPException(status_code=503, detail="callback_query_unavailable") from exc
    return {
        "items": [
            {
                "id": str(r.get("id")),
                "voicemail_id": str(r.get("voicemail_id")) if r.get("voicemail_id") else None,
                "tenant_id": str(r.get("tenant_id")) if r.get("tenant_id") else None,
                "callback_phone": r.get("callback_phone"),
                "callback_state": r.get("callback_state"),
                "sla_due_at": _isoformat_or_none(r.get("sla_due_at")),
                "priority": r.get("priority"),
                "reason": r.get("reason"),
                "created_at": _isoformat_or_none(r.get("created_at")),
                "updated_at": _isoformat_or_none(r.get("updated_at")),
            }
            for r in rows
        ]
    }


@router.post("/escalations/{escalation_id}/takeover")
async def takeover_escalation(
    escalation_id: str,
    payload: dict[str, Any],
    current: CurrentUser = Depends(get_current_user),
    db: Session = Depends(db_session_dependency),
):
    _require_founder(current)
    row = db.execute(
        text("SELECT id, session_id, status FROM billing_call_escalations WHERE id = :id::uuid"),
        {"id": escalation_id},
    ).mappings().first()
    if row is None:
        raise HTTPException(status_code=404, detail="escalation_not_found")
    if row["status"] not in ("awaiting_human", "in_progress"):
        raise HTTPException(status_code=409, detail=f"cannot_takeover_from_status:{row['status']}")

    now = datetime.now(UTC).isoformat()
    db.execute(
        text(
            "UPDATE billing_call_escalations "
            "SET status = 'in_progress', taken_by_user_id = :uid::uuid, taken_at = :now, updated_at = :now "
            "WHERE id = :id::uuid"
        ),
        {"uid": str(current.user_id), "id": escalation_id, "now": now},
    )
    db.execute(
        text(
            "INSERT INTO human_takeovers (session_id, escalation_id, founder_user_id, takeover_channel, takeover_state, notes, created_at, updated_at) "
            "VALUES (:sid::uuid, :eid::uuid, :uid::uuid, :channel, 'connected', :notes, :now, :now)"
        ),
        {
            "sid": str(row["session_id"]),
            "eid": escalation_id,
            "uid": str(current.user_id),
            "channel": payload.get("channel", "softphone"),
            "notes": payload.get("notes"),
            "now": now,
        },
    )
    db.execute(
        text(
            "UPDATE billing_voice_sessions "
            "SET state = 'HUMAN_CONNECTED', updated_at = :now "
            "WHERE id = :sid::uuid"
        ),
        {"sid": str(row["session_id"]), "now": now},
    )
    db.commit()

    return {"status": "ok", "escalation_id": escalation_id, "session_id": str(row["session_id"])}


# ── Phone Stack Status + CNAM ────────────────────────────────────────────────


@router.get("/phone-status")
async def phone_stack_status(
    current: CurrentUser = Depends(get_current_user),
    db: Session = Depends(db_session_dependency),
) -> dict[str, Any]:
    """Live phone stack status: provisioned number, CNAM, voice config, routing health."""
    _require_founder(current)
    settings = get_settings()

    central_phone = (settings.central_billing_phone_e164 or "").strip()
    number_id = (settings.telnyx_central_billing_number_id or "").strip()
    cnam_name = (settings.cnam_display_name or "").strip()
    cnam_status = (settings.cnam_status or "").strip()
    escalation_phone = (settings.founder_billing_escalation_phone_e164 or "").strip()
    telnyx_from = (settings.telnyx_from_number or "").strip()
    telephony_engine = (settings.billing_telephony_engine or "telnyx").strip()

    # Live query: active billing lines from DB
    active_lines: list[dict[str, Any]] = []
    try:
        rows = db.execute(
            text(
                "SELECT id, line_label, phone_e164, is_active, purchased_at "
                "FROM central_billing_lines ORDER BY purchased_at DESC LIMIT 10"
            )
        ).mappings().all()
        active_lines = [
            {
                "id": str(r["id"]),
                "label": r.get("line_label") or "",
                "phone_e164": r.get("phone_e164") or "",
                "is_active": bool(r.get("is_active")),
                "purchased_at": _isoformat_or_none(r.get("purchased_at")),
            }
            for r in rows
        ]
    except SQLAlchemyError:
        logger.warning("central_billing_lines table not available — skipping live line query")

    # Per-tenant CNAM overrides
    tenant_overrides: list[dict[str, Any]] = []
    try:
        t_rows = db.execute(
            text(
                "SELECT tenant_id, policy_json->'cnam_override' AS cnam_override "
                "FROM billing_phone_policies "
                "WHERE policy_json->'cnam_override' IS NOT NULL "
                "LIMIT 50"
            )
        ).mappings().all()
        tenant_overrides = [
            {
                "tenant_id": str(r["tenant_id"]),
                "cnam_override": r.get("cnam_override"),
            }
            for r in t_rows
        ]
    except SQLAlchemyError:
        logger.warning("billing_phone_policies cnam_override query failed — skipping")

    provisioned = bool(central_phone and central_phone != "+18005550123")
    cnam_registered = cnam_status in ("submitted", "active", "approved")

    return {
        "provisioned": provisioned,
        "central_billing_phone_e164": central_phone,
        "telnyx_number_id": number_id,
        "telnyx_from_number": telnyx_from,
        "telephony_engine": telephony_engine,
        "cnam": {
            "display_name": cnam_name,
            "status": cnam_status or ("not_registered" if provisioned else "not_provisioned"),
            "registered": cnam_registered,
        },
        "escalation_phone_e164": escalation_phone,
        "active_lines": active_lines,
        "tenant_cnam_overrides": tenant_overrides,
        "health": {
            "telnyx_api_key_set": bool(settings.telnyx_api_key),
            "telnyx_public_key_set": bool(settings.telnyx_public_key),
            "ivr_audio_base_url_set": bool(settings.ivr_audio_base_url),
            "messaging_profile_set": bool(settings.telnyx_messaging_profile_id),
            "central_phone_provisioned": provisioned,
            "cnam_registered": cnam_registered,
        },
    }


@router.put("/tenant-cnam/{tenant_id}")
async def set_tenant_cnam_override(
    tenant_id: str,
    payload: dict[str, Any],
    current: CurrentUser = Depends(get_current_user),
    db: Session = Depends(db_session_dependency),
) -> dict[str, Any]:
    """Set per-tenant CNAM caller ID override. Default is FusionEMS Quantum."""
    _require_founder(current)

    cnam_name = str(payload.get("cnam_display_name") or "").strip()
    if not cnam_name:
        raise HTTPException(status_code=422, detail="cnam_display_name is required")
    if len(cnam_name) > 15:
        raise HTTPException(status_code=422, detail="CNAM display name must be 15 characters or fewer")

    try:
        UUID(tenant_id)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail="Invalid tenant_id UUID") from exc

    now = datetime.now(UTC).isoformat()

    # Upsert the cnam_override into the policy_json
    row = db.execute(
        text(
            "SELECT policy_json FROM billing_phone_policies WHERE tenant_id = :tid::uuid LIMIT 1"
        ),
        {"tid": tenant_id},
    ).mappings().first()

    if row is None:
        # Create new policy row with CNAM override
        policy_json = {"cnam_override": {"display_name": cnam_name, "updated_at": now}}
        db.execute(
            text(
                "INSERT INTO billing_phone_policies "
                "(tenant_id, billing_mode, allow_ai_balance_inquiry, allow_ai_payment_link_resend, "
                "allow_ai_statement_resend, allow_ai_address_confirmation, allow_ai_payment_plan_intake, "
                "collections_enabled, debt_setoff_enabled, require_human_for_disputes, "
                "require_human_for_legal_threat, escalation_priority, policy_json, created_at, updated_at) "
                "VALUES (:tid::uuid, 'FUSION_RCM', true, true, true, false, false, false, false, true, true, "
                "'normal', :pj::jsonb, :now, :now)"
            ),
            {"tid": tenant_id, "pj": json.dumps(policy_json), "now": now},
        )
    else:
        policy_json = dict(row.get("policy_json") or {})
        policy_json["cnam_override"] = {"display_name": cnam_name, "updated_at": now}
        db.execute(
            text(
                "UPDATE billing_phone_policies SET policy_json = :pj::jsonb, updated_at = :now "
                "WHERE tenant_id = :tid::uuid"
            ),
            {"tid": tenant_id, "pj": json.dumps(policy_json), "now": now},
        )

    db.commit()
    logger.info(
        "tenant_cnam_override_set tenant_id=%s cnam_display_name=%s",
        tenant_id,
        cnam_name,
    )

    return {
        "status": "ok",
        "tenant_id": tenant_id,
        "cnam_display_name": cnam_name,
    }


@router.get("/cnam/live-status")
async def cnam_live_status(
    current: CurrentUser = Depends(get_current_user),
) -> dict[str, Any]:
    """Query Telnyx API for live CNAM registration status of the central billing number."""
    from core_app.telnyx import client as telnyx_client

    _require_founder(current)
    settings = get_settings()

    number_id = (settings.telnyx_central_billing_number_id or "").strip()
    api_key = (settings.telnyx_api_key or "").strip()

    if not number_id or number_id in ("existing", "unknown"):
        return {
            "status": "not_queryable",
            "reason": "number_id not available — number was pre-provisioned or not yet purchased",
            "config_cnam_display_name": settings.cnam_display_name,
            "config_cnam_status": settings.cnam_status,
        }

    if not api_key:
        return {
            "status": "not_queryable",
            "reason": "TELNYX_API_KEY not configured",
            "config_cnam_display_name": settings.cnam_display_name,
            "config_cnam_status": settings.cnam_status,
        }

    try:
        live = telnyx_client.get_cnam_status(api_key=api_key, number_id=number_id)
    except (telnyx_client.TelnyxApiError, telnyx_client.TelnyxNotConfigured) as exc:
        logger.warning("cnam_live_status_query_failed number_id=%s error=%s", number_id, exc)
        return {
            "status": "query_failed",
            "error": str(exc),
            "config_cnam_display_name": settings.cnam_display_name,
            "config_cnam_status": settings.cnam_status,
        }

    return {
        "status": "ok",
        "live": live,
        "config_cnam_display_name": settings.cnam_display_name,
        "config_cnam_status": settings.cnam_status,
    }


@router.post("/cnam/update")
async def update_cnam_registration(
    payload: dict[str, Any],
    current: CurrentUser = Depends(get_current_user),
) -> dict[str, Any]:
    """Submit CNAM update to Telnyx for the central billing number."""
    from core_app.telnyx import client as telnyx_client

    _require_founder(current)
    settings = get_settings()

    display_name = str(payload.get("cnam_display_name") or "").strip()
    if not display_name:
        raise HTTPException(status_code=422, detail="cnam_display_name is required")
    if len(display_name) > 15:
        raise HTTPException(status_code=422, detail="CNAM display name must be 15 characters or fewer")

    number_id = (settings.telnyx_central_billing_number_id or "").strip()
    api_key = (settings.telnyx_api_key or "").strip()

    if not number_id or number_id in ("existing", "unknown"):
        raise HTTPException(status_code=409, detail="Cannot update CNAM: number_id not available")
    if not api_key:
        raise HTTPException(status_code=409, detail="Cannot update CNAM: TELNYX_API_KEY not configured")

    try:
        result = telnyx_client.update_cnam(api_key=api_key, number_id=number_id, display_name=display_name)
    except telnyx_client.TelnyxApiError as exc:
        logger.error("cnam_update_failed number_id=%s display_name=%s error=%s", number_id, display_name, exc)
        raise HTTPException(status_code=502, detail=f"Telnyx CNAM update failed: {exc}") from exc
    except telnyx_client.TelnyxNotConfigured as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc

    logger.info("cnam_update_submitted number_id=%s display_name=%s", number_id, display_name)
    return {
        "status": "ok",
        "submitted_display_name": display_name,
        "telnyx_response": result,
    }
