from __future__ import annotations

import json
import logging
import re
from datetime import UTC, datetime, timedelta
from typing import Any

from sqlalchemy import text
from sqlalchemy.orm import Session

from core_app.services.stt_service import STTConfig, transcribe_audio_url

logger = logging.getLogger(__name__)

_STATEMENT_RE = re.compile(r"\b(?:statement|stmt|account|acct)[\s:#-]*([A-Za-z0-9-]{6,24})\b", re.IGNORECASE)
_PHONE_RE = re.compile(r"\b(?:\+?1[-.\s]?)?\(?([2-9]\d{2})\)?[-.\s]?([2-9]\d{2})[-.\s]?(\d{4})\b")

_HIGH_RISK_PATTERNS = [
    re.compile(p, re.IGNORECASE)
    for p in [
        r"\blawyer\b",
        r"\battorney\b",
        r"\bfraud\b",
        r"\blawsuit\b",
        r"\bhipaa\b",
        r"\bcomplaint\b",
        r"\bmedia\b",
    ]
]


def _utcnow() -> datetime:
    return datetime.now(UTC)


def _extract_recording_url(ep: dict[str, Any]) -> str:
    direct = str(ep.get("recording_url") or ep.get("recording_urls") or "").strip()
    if direct:
        return direct

    media_urls = ep.get("media_urls")
    if isinstance(media_urls, list) and media_urls:
        return str(media_urls[0] or "").strip()

    recording_urls = ep.get("recording_urls")
    if isinstance(recording_urls, list) and recording_urls:
        return str(recording_urls[0] or "").strip()

    if isinstance(recording_urls, dict):
        for key in ("mp3", "wav", "m4a"):
            value = str(recording_urls.get(key) or "").strip()
            if value:
                return value

    return ""


def _extract_identifiers(transcript: str) -> dict[str, Any]:
    text_value = transcript or ""
    statement_match = _STATEMENT_RE.search(text_value)
    phone_match = _PHONE_RE.search(text_value)
    callback_phone = None
    if phone_match:
        callback_phone = f"+1{phone_match.group(1)}{phone_match.group(2)}{phone_match.group(3)}"

    return {
        "statement_or_account": statement_match.group(1) if statement_match else None,
        "callback_phone": callback_phone,
    }


def _resolve_account_context(db: Session, lookup_key: str | None) -> dict[str, str] | None:
    sid = (lookup_key or "").strip()
    if not sid:
        return None

    row = db.execute(
        text(
            "SELECT tenant_id::text AS tenant_id, id::text AS account_id, id::text AS statement_id "
            "FROM billing_cases WHERE id::text = :sid LIMIT 1"
        ),
        {"sid": sid},
    ).mappings().first()
    if row:
        return {
            "tenant_id": str(row.get("tenant_id") or ""),
            "account_id": str(row.get("account_id") or sid),
            "statement_id": str(row.get("statement_id") or sid),
        }

    row2 = db.execute(
        text(
            "SELECT tenant_id::text AS tenant_id, claim_id::text AS account_id, statement_id::text AS statement_id "
            "FROM lob_letters WHERE statement_id::text = :sid LIMIT 1"
        ),
        {"sid": sid},
    ).mappings().first()
    if row2:
        return {
            "tenant_id": str(row2.get("tenant_id") or ""),
            "account_id": str(row2.get("account_id") or sid),
            "statement_id": str(row2.get("statement_id") or sid),
        }

    return None


def _uuid_or_none(value: str | None) -> str | None:
    normalized = (value or "").strip()
    return normalized or None


def _intent_from_transcript(transcript: str) -> str:
    t = (transcript or "").lower()
    if any(k in t for k in ["payment", "pay", "link"]):
        return "payment_intent"
    if any(k in t for k in ["dispute", "wrong", "incorrect", "error"]):
        return "dispute_review"
    if any(k in t for k in ["call me", "callback", "call back"]):
        return "callback_request"
    return "general_billing"


def _risk_score(transcript: str) -> tuple[int, str]:
    t = transcript or ""
    score = 15
    for pattern in _HIGH_RISK_PATTERNS:
        if pattern.search(t):
            score += 25
    if len(t) > 350:
        score += 10
    score = max(0, min(100, score))
    level = "high" if score >= 70 else ("medium" if score >= 35 else "low")
    return score, level


def ingest_voicemail_event(
    *,
    db: Session,
    event_payload: dict[str, Any],
    from_phone: str,
    to_phone: str,
    call_control_id: str,
    system_tenant_id: str | None,
    stt_engine: str,
    stt_model_size: str,
) -> dict[str, Any]:
    """Create structured voicemail records and downstream callback/escalation tasks."""
    recording_url = _extract_recording_url(event_payload)
    now = _utcnow()

    voicemail = db.execute(
        text(
            """
            INSERT INTO billing_voicemails (
                call_control_id, caller_phone_number, central_line_phone,
                recording_url, state, urgency, risk_level, received_at, created_at, updated_at
            ) VALUES (
                :cid, :from_phone, :to_phone,
                :recording_url, 'VOICEMAIL_RECEIVED', 'normal', 'low', :now, :now, :now
            )
            RETURNING id
            """
        ),
        {
            "cid": call_control_id,
            "from_phone": from_phone,
            "to_phone": to_phone,
            "recording_url": recording_url,
            "now": now,
        },
    ).mappings().first()
    if not voicemail:
        db.commit()
        return {"status": "voicemail_insert_failed"}

    voicemail_id = str(voicemail["id"])

    transcript = ""
    if recording_url:
        db.execute(
            text(
                "UPDATE billing_voicemails SET state = 'TRANSCRIPTION_PENDING', updated_at = :now WHERE id = :id::uuid"
            ),
            {"id": voicemail_id, "now": now},
        )
        db.commit()
        try:
            transcript = transcribe_audio_url(
                recording_url,
                STTConfig(engine=stt_engine or "faster_whisper", model_size=stt_model_size or "small"),
            )
        except Exception as exc:
            logger.warning("voicemail_transcription_failed voicemail_id=%s error=%s", voicemail_id, exc)
            db.execute(
                text(
                    "UPDATE billing_voicemails SET state = 'FAILED', updated_at = :now WHERE id = :id::uuid"
                ),
                {"id": voicemail_id, "now": _utcnow()},
            )
            db.commit()
            return {"status": "transcription_failed", "voicemail_id": voicemail_id}

    extracted = _extract_identifiers(transcript)
    account_context = _resolve_account_context(db, extracted.get("statement_or_account"))
    intent_code = _intent_from_transcript(transcript)
    risk_score, risk_level = _risk_score(transcript)
    lane_state = "MATCHED" if account_context else "UNMATCHED"

    db.execute(
        text(
            """
            INSERT INTO billing_voicemail_transcripts (
                voicemail_id, engine, transcript_text, confidence,
                state, created_at
            ) VALUES (
                :vid::uuid, :engine, :transcript, :confidence,
                'TRANSCRIBED', :now
            )
            """
        ),
        {
            "vid": voicemail_id,
            "engine": stt_engine or "faster_whisper",
            "transcript": transcript,
            "confidence": 0.82,
            "now": _utcnow(),
        },
    )

    matched_tenant_id = _uuid_or_none((account_context or {}).get("tenant_id")) or _uuid_or_none(system_tenant_id)

    db.execute(
        text(
            """
            INSERT INTO billing_voicemail_extractions (
                voicemail_id, extracted_statement_id, extracted_account_id,
                extracted_callback_phone, extraction_json, created_at
            ) VALUES (
                :vid::uuid, :statement_id, :account_id,
                :callback_phone, :payload::jsonb, :now
            )
            """
        ),
        {
            "vid": voicemail_id,
            "statement_id": (account_context or {}).get("statement_id") or extracted.get("statement_or_account"),
            "account_id": (account_context or {}).get("account_id") or extracted.get("statement_or_account"),
            "callback_phone": extracted.get("callback_phone") or from_phone,
            "payload": json.dumps(
                {
                    "source": "faster_whisper",
                    "has_statement_like_value": bool(extracted.get("statement_or_account")),
                    "has_callback_phone": bool(extracted.get("callback_phone")),
                }
            ),
            "now": _utcnow(),
        },
    )

    db.execute(
        text(
            """
            INSERT INTO billing_voicemail_intents (voicemail_id, intent_code, confidence, created_at)
            VALUES (:vid::uuid, :intent, :confidence, :now)
            """
        ),
        {
            "vid": voicemail_id,
            "intent": intent_code,
            "confidence": 0.78,
            "now": _utcnow(),
        },
    )

    db.execute(
        text(
            """
            INSERT INTO billing_voicemail_risk_scores (voicemail_id, risk_score, risk_level, reason, created_at)
            VALUES (:vid::uuid, :score, :level, :reason, :now)
            """
        ),
        {
            "vid": voicemail_id,
            "score": risk_score,
            "level": risk_level,
            "reason": "keyword_risk_and_intent_analysis",
            "now": _utcnow(),
        },
    )

    if account_context:
        db.execute(
            text(
                """
                INSERT INTO billing_voicemail_matches (
                    voicemail_id, tenant_id, statement_id, account_id, match_confidence, state, created_at
                ) VALUES (
                    :vid::uuid, :tenant_id::uuid, :statement_id, :account_id, :confidence, 'MATCHED', :now
                )
                """
            ),
            {
                "vid": voicemail_id,
                "tenant_id": matched_tenant_id,
                "statement_id": account_context.get("statement_id"),
                "account_id": account_context.get("account_id"),
                "confidence": 0.88,
                "now": _utcnow(),
            },
        )

    due_at = _utcnow() + timedelta(hours=2 if risk_level == "high" else 24)
    callback_reason = "high_risk_voicemail" if risk_level == "high" else "standard_voicemail_followup"
    db.execute(
        text(
            """
            INSERT INTO billing_callback_tasks (
                voicemail_id, tenant_id, callback_phone, callback_state,
                sla_due_at, priority, reason, created_at, updated_at
            ) VALUES (
                :vid::uuid, :tenant_id::uuid, :phone, 'CALLBACK_READY',
                :sla_due_at, :priority, :reason, :now, :now
            )
            """
        ),
        {
            "vid": voicemail_id,
            "tenant_id": matched_tenant_id,
            "phone": extracted.get("callback_phone") or from_phone,
            "sla_due_at": due_at,
            "priority": "urgent" if risk_level == "high" else "normal",
            "reason": callback_reason,
            "now": _utcnow(),
        },
    )

    if risk_level == "high":
        db.execute(
            text(
                """
                INSERT INTO billing_voicemail_escalations (
                    voicemail_id, escalation_reason, status, created_at, updated_at
                ) VALUES (
                    :vid::uuid, :reason, 'awaiting_human', :now, :now
                )
                """
            ),
            {
                "vid": voicemail_id,
                "reason": "high_risk_legal_or_fraud_signal",
                "now": _utcnow(),
            },
        )

    db.execute(
        text(
            """
            UPDATE billing_voicemails
            SET
                tenant_id = COALESCE(:tenant_id::uuid, tenant_id),
                statement_id = :statement_id,
                account_id = :account_id,
                state = :state,
                urgency = :urgency,
                risk_level = :risk_level,
                updated_at = :now
            WHERE id = :id::uuid
            """
        ),
        {
            "tenant_id": matched_tenant_id,
            "statement_id": (account_context or {}).get("statement_id"),
            "account_id": (account_context or {}).get("account_id"),
            "state": lane_state,
            "urgency": "high" if risk_level == "high" else "normal",
            "risk_level": risk_level,
            "now": _utcnow(),
            "id": voicemail_id,
        },
    )

    db.commit()
    return {
        "status": "ok",
        "voicemail_id": voicemail_id,
        "state": lane_state,
        "intent": intent_code,
        "risk_level": risk_level,
        "statement_id": (account_context or {}).get("statement_id"),
        "account_id": (account_context or {}).get("account_id"),
    }
