from __future__ import annotations

import hashlib
import json
import logging
import uuid
from contextlib import suppress
from datetime import UTC, datetime
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy import text
from sqlalchemy.orm import Session

from core_app.api.dependencies import db_session_dependency  # pylint: disable=no-name-in-module
from core_app.core.config import get_settings  # pylint: disable=no-name-in-module
from core_app.documents.s3_storage import put_bytes
from core_app.observability.metrics import (  # pylint: disable=no-name-in-module
    FAX_JOB_STATUS_TRANSITIONS_TOTAL,
    FAX_TELNYX_WEBHOOK_EVENTS_TOTAL,
)
from core_app.services import sqs_publisher
from core_app.telnyx.client import TelnyxApiError, download_media
from core_app.telnyx.signature import verify_telnyx_webhook

logger = logging.getLogger(__name__)

router = APIRouter(tags=["Telnyx Fax"])


def _utcnow() -> str:
    return datetime.now(UTC).isoformat()


def _s3_fax_key(tenant_id: str, fax_id: str) -> str:
    now = datetime.now(UTC)
    return f"tenant/{tenant_id}/fax/{now.year}/{now.month:02d}/{now.day:02d}/{fax_id}/original.pdf"


def _resolve_tenant_by_did(db: Session, to_number: str) -> str | None:
    row = db.execute(
        text(
            "SELECT tenant_id FROM tenant_phone_numbers "
            "WHERE phone_e164 = :phone AND purpose = 'billing_fax' LIMIT 1"
        ),
        {"phone": to_number},
    ).fetchone()
    return str(row.tenant_id) if row else None


def _mask_phone(raw: str) -> str:
    s = (raw or "").strip()
    if not s:
        return ""
    tail = s[-4:] if len(s) >= 4 else s
    return f"***{tail}"


def _set_tenant_rls_context(db: Session, tenant_id: str) -> None:
    # Enforce tenant isolation for domination (RLS) tables.
    db.execute(text("SELECT set_config('app.tenant_id', :tid, true)"), {"tid": tenant_id})


def _outbound_platform_event_type(status: str) -> str:
    s = (status or "").strip().lower()
    if s == "delivered":
        return "fax.outbound.delivered"
    if s == "failed":
        return "fax.outbound.failed"
    if s == "canceled":
        return "fax.outbound.canceled"
    if s == "sending":
        return "fax.outbound.sending"
    if s == "sent":
        return "fax.outbound.sent"
    return "fax.outbound.status_updated"


async def _best_effort_emit_platform_event(
    *,
    db: Session,
    tenant_id: str,
    event_type: str,
    entity_type: str,
    entity_id: str,
    payload: dict[str, Any],
    idempotency_key: str,
    correlation_id: str | None,
) -> None:
    # Platform events are used by founder control planes; they must never break webhook ingestion.
    try:
        from core_app.api.events_router import emit_platform_event  # noqa: I001  # pylint: disable=no-name-in-module

        await emit_platform_event(
            db,
            tenant_id=tenant_id,
            event_type=event_type,
            entity_type=entity_type,
            entity_id=entity_id,
            payload=payload,
            idempotency_key=idempotency_key,
            correlation_id=correlation_id,
        )
    except Exception:
        # Avoid leaking payload contents; keep logs minimal.
        logger.warning(
            "platform_event_emit_failed event_type=%s entity_type=%s entity_id=%s",
            event_type,
            entity_type,
            entity_id,
        )


def _first_row(result: Any) -> Any | None:
    fetchone = getattr(result, "fetchone", None)
    if callable(fetchone):
        return fetchone()
    return None


def _row_value(row: Any, key: str) -> Any:
    if row is None:
        return None
    if isinstance(row, dict):
        return row.get(key)
    mapping = getattr(row, "_mapping", None)
    if mapping is not None and hasattr(mapping, "get"):
        return mapping.get(key)
    if hasattr(row, key):
        return getattr(row, key)
    try:
        return row[key]
    except Exception:
        return None


def _parse_client_state(raw: str) -> dict[str, Any]:
    if not raw or not isinstance(raw, str):
        return {}
    s = raw.strip()
    if not s:
        return {}
    try:
        parsed = json.loads(s)
        return parsed if isinstance(parsed, dict) else {}
    except Exception:
        return {}


def _get_telnyx_event_processed_at(db: Session, event_id: str) -> Any | None:
    result = db.execute(
        text("SELECT processed_at FROM telnyx_events WHERE event_id = :eid"),
        {"eid": event_id},
    )
    row = _first_row(result)
    return _row_value(row, "processed_at")


def _ensure_event_receipt(
    db: Session, event_id: str, event_type: str, tenant_id: str | None, raw: dict
) -> bool:
    """Insert into telnyx_events; allow replay if previously inserted but not processed."""
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
    rowcount = int(getattr(result, "rowcount", 0) or 0)
    if rowcount > 0:
        return True

    processed_at = _get_telnyx_event_processed_at(db, event_id)
    # If processed_at is NULL, the prior attempt likely crashed after receipt.
    # Allow a safe replay to avoid losing terminal delivery truth.
    return processed_at is None


def _mark_event_processed(db: Session, event_id: str) -> None:
    db.execute(
        text("UPDATE telnyx_events SET processed_at = :now WHERE event_id = :eid"),
        {"now": _utcnow(), "eid": event_id},
    )
    db.commit()


def _load_fax_job_by_id(
    db: Session, *, tenant_id: str, fax_job_id: str
) -> dict[str, Any] | None:
    result = db.execute(
        text(
            "SELECT id, tenant_id, version, data FROM fax_jobs "
            "WHERE tenant_id = :tid AND id = :id AND deleted_at IS NULL LIMIT 1"
        ),
        {"tid": tenant_id, "id": fax_job_id},
    )
    row = _first_row(result)
    if row is None:
        return None
    return {
        "id": str(_row_value(row, "id")),
        "tenant_id": str(_row_value(row, "tenant_id")),
        "version": int(_row_value(row, "version") or 0),
        "data": _row_value(row, "data") or {},
    }


def _load_fax_job_by_telnyx_id(
    db: Session, *, tenant_id: str, telnyx_fax_id: str
) -> dict[str, Any] | None:
    if not telnyx_fax_id:
        return None
    result = db.execute(
        text(
            "SELECT id, tenant_id, version, data FROM fax_jobs "
            "WHERE tenant_id = :tid AND deleted_at IS NULL "
            "AND data->>'telnyx_fax_id' = :fid "
            "ORDER BY created_at DESC LIMIT 1"
        ),
        {"tid": tenant_id, "fid": telnyx_fax_id},
    )
    row = _first_row(result)
    if row is None:
        return None
    return {
        "id": str(_row_value(row, "id")),
        "tenant_id": str(_row_value(row, "tenant_id")),
        "version": int(_row_value(row, "version") or 0),
        "data": _row_value(row, "data") or {},
    }


def _insert_audit_log(
    db: Session,
    *,
    tenant_id: str,
    actor_user_id: str | None,
    action: str,
    entity_name: str,
    entity_id: str,
    field_changes: dict[str, Any],
    correlation_id: str | None,
) -> None:
    db.execute(
        text(
            "INSERT INTO audit_logs (tenant_id, actor_user_id, action, entity_name, entity_id, field_changes, correlation_id) "
            "VALUES (:tid, :actor, :action, :ename, :eid::uuid, :changes::jsonb, :cid)"
        ),
        {
            "tid": tenant_id,
            "actor": actor_user_id,
            "action": action,
            "ename": entity_name,
            "eid": entity_id,
            "changes": json.dumps(field_changes, default=str),
            "cid": correlation_id,
        },
    )


def _insert_fax_event(
    db: Session,
    *,
    tenant_id: str,
    event_data: dict[str, Any],
) -> None:
    db.execute(
        text(
            "INSERT INTO fax_events (tenant_id, data) "
            "VALUES (:tid::uuid, :data::jsonb)"
        ),
        {"tid": tenant_id, "data": json.dumps(event_data, default=str)},
    )


_STATUS_RANK: dict[str, int] = {
    "created": 0,
    "pending_configuration": 5,
    "sending": 10,
    "sent": 20,
    "delivered": 30,
    "failed": 30,
    "canceled": 30,
    "cancelled": 30,
}


def _normalize_status(event_type: str, payload: dict[str, Any]) -> str | None:
    et = (event_type or "").strip().lower()
    if not et.startswith("fax."):
        return None
    if et.endswith(".delivered") or et == "fax.delivered":
        return "delivered"
    if et.endswith(".failed") or et == "fax.failed":
        return "failed"
    if et.endswith(".canceled") or et.endswith(".cancelled"):
        return "canceled"
    if et.endswith(".sent"):
        return "sent"
    if et.endswith(".initiated") or et.endswith(".queued") or et.endswith(".media.processed"):
        return "sending"
    # Some providers also include an explicit status field.
    raw_status = str(payload.get("status") or "").strip().lower()
    if raw_status in _STATUS_RANK:
        return "canceled" if raw_status == "cancelled" else raw_status
    return None


def _should_apply_transition(current_status: str, new_status: str) -> bool:
    cur = (current_status or "").strip().lower() or "created"
    nxt = (new_status or "").strip().lower()
    if nxt not in _STATUS_RANK:
        return False
    if cur not in _STATUS_RANK:
        cur = "created"
    # Never regress (ignore stale/out-of-order events).
    return _STATUS_RANK[nxt] >= _STATUS_RANK[cur]


def _patch_fax_job_retry_safe(
    db: Session,
    *,
    tenant_id: str,
    fax_job_id: str,
    patch: dict[str, Any],
    correlation_id: str | None,
) -> bool:
    # Optimistic concurrency: refetch once on conflict.
    job = _load_fax_job_by_id(db, tenant_id=tenant_id, fax_job_id=fax_job_id)
    if not job:
        return False

    def _attempt(expected_version: int) -> bool:
        result = db.execute(
            text(
                "UPDATE fax_jobs "
                "SET version = version + 1, updated_at = now(), data = data || :patch::jsonb "
                "WHERE tenant_id = :tid AND id = :id AND deleted_at IS NULL AND version = :v"
            ),
            {
                "patch": json.dumps(patch, default=str),
                "tid": tenant_id,
                "id": fax_job_id,
                "v": expected_version,
            },
        )
        db.commit()
        rowcount = int(getattr(result, "rowcount", 0) or 0)
        if rowcount > 0:
            _insert_audit_log(
                db,
                tenant_id=tenant_id,
                actor_user_id=None,
                action="update",
                entity_name="fax_jobs",
                entity_id=fax_job_id,
                field_changes={"patch": patch, "expected_version": expected_version},
                correlation_id=correlation_id,
            )
            db.commit()
            return True
        return False

    if _attempt(int(job["version"])):
        return True
    job2 = _load_fax_job_by_id(db, tenant_id=tenant_id, fax_job_id=fax_job_id)
    if not job2:
        return False
    return _attempt(int(job2["version"]))


def _insert_event(
    db: Session, event_id: str, event_type: str, tenant_id: str | None, raw: dict
) -> bool:
    # Backwards-compatible wrapper for existing call sites.
    return _ensure_event_receipt(db, event_id, event_type, tenant_id, raw)


def _route_fax_to_case(
    db: Session, tenant_id: str, fax_id: str, from_phone: str
) -> str | None:
    """
    Attempt to route the fax to an open billing case.
    Strategy: look for most recent open billing case for the tenant with no fax_id yet.
    Returns case_id or None (UNROUTED).
    """
    row = db.execute(
        text(
            "SELECT id FROM billing_cases "
            "WHERE tenant_id = :tid AND status = 'open' "
            "ORDER BY created_at DESC LIMIT 1"
        ),
        {"tid": tenant_id},
    ).fetchone()
    return str(row.id) if row else None


def _insert_fax_document(
    db: Session,
    *,
    fax_id: str,
    tenant_id: str | None,
    from_phone: str,
    to_phone: str,
    s3_key: str | None,
    sha256: str | None,
    case_id: str | None,
    status: str,
) -> None:
    db.execute(
        text(
            "INSERT INTO fax_documents "
            "(fax_id, tenant_id, from_phone, to_phone, s3_key_original, sha256_original, "
            "doc_type, case_id, status, created_at) "
            "VALUES (:fid, :tid, :from_, :to_, :s3, :sha256, NULL, :case_id, :status, :now) "
            "ON CONFLICT (fax_id) DO UPDATE SET "
            "s3_key_original = EXCLUDED.s3_key_original, "
            "sha256_original = EXCLUDED.sha256_original, "
            "status = EXCLUDED.status"
        ),
        {
            "fid": fax_id,
            "tid": tenant_id,
            "from_": from_phone,
            "to_": to_phone,
            "s3": s3_key,
            "sha256": sha256,
            "case_id": case_id,
            "status": status,
            "now": _utcnow(),
        },
    )
    db.commit()


@router.post("/webhooks/telnyx/fax")
async def telnyx_fax_webhook(
    request: Request,
    db: Session = Depends(db_session_dependency),
) -> dict[str, Any]:
    raw_body = await request.body()
    settings = get_settings()

    if not getattr(settings, "telnyx_public_key", None):
        logger.critical("telnyx_fax_webhook_not_configured missing=TELNYX_PUBLIC_KEY")
        raise HTTPException(status_code=503, detail="telnyx_webhook_not_configured")

    if not verify_telnyx_webhook(
        raw_body=raw_body,
        signature_ed25519=request.headers.get("telnyx-signature-ed25519"),
        timestamp=request.headers.get("telnyx-timestamp"),
        public_key_base64=settings.telnyx_public_key,
        tolerance_seconds=settings.telnyx_webhook_tolerance_seconds,
    ):
        logger.warning("telnyx_fax_webhook_invalid_signature")
        raise HTTPException(status_code=400, detail="invalid_telnyx_signature")

    try:
        payload = json.loads(raw_body)
    except Exception as exc:
        raise HTTPException(status_code=400, detail="invalid_json") from exc

    data = payload.get("data", {})
    event_id: str = data.get("id") or str(uuid.uuid4())
    event_type: str = data.get("event_type", "")
    ep = data.get("payload", {})

    to_number: str = ep.get("to", "")
    from_number: str = ep.get("from", "")
    telnyx_fax_id: str = ep.get("fax_id") or ep.get("id") or event_id
    media_url: str = ep.get("media_url") or ""

    client_state_raw = str(ep.get("client_state") or "").strip()
    client_state = _parse_client_state(client_state_raw)
    client_tenant_id = str(client_state.get("tenant_id") or "").strip()
    client_fax_job_id = str(client_state.get("fax_job_id") or "").strip()
    correlation_id = str(client_state.get("correlation_id") or "").strip() or None

    tenant_id = None
    if client_tenant_id:
        tenant_id = client_tenant_id
    else:
        tenant_id = _resolve_tenant_by_did(db, to_number) or _resolve_tenant_by_did(
            db, from_number
        )

    FAX_TELNYX_WEBHOOK_EVENTS_TOTAL.labels(event_type=event_type or "", outcome="received").inc()

    should_process = _ensure_event_receipt(db, event_id, event_type, tenant_id, payload)
    if not should_process:
        logger.info("telnyx_fax_duplicate_processed event_id=%s", event_id)
        FAX_TELNYX_WEBHOOK_EVENTS_TOTAL.labels(event_type=event_type or "", outcome="duplicate").inc()
        return {"status": "duplicate"}

    logger.info(
        "telnyx_fax event_type=%s telnyx_fax_id=%s from=%s to=%s tenant_id=%s",
        event_type,
        telnyx_fax_id,
        _mask_phone(from_number),
        _mask_phone(to_number),
        tenant_id,
    )

    if event_type != "fax.received":
        new_status = _normalize_status(event_type, ep if isinstance(ep, dict) else {})
        if not tenant_id or not new_status:
            _mark_event_processed(db, event_id)
            FAX_TELNYX_WEBHOOK_EVENTS_TOTAL.labels(
                event_type=event_type or "", outcome="ignored"
            ).inc()
            return {"status": "ok", "detail": "non_received_event_ignored"}

        _set_tenant_rls_context(db, tenant_id)

        fax_job: dict[str, Any] | None = None
        if client_fax_job_id:
            fax_job = _load_fax_job_by_id(db, tenant_id=tenant_id, fax_job_id=client_fax_job_id)
        if fax_job is None:
            fax_job = _load_fax_job_by_telnyx_id(db, tenant_id=tenant_id, telnyx_fax_id=telnyx_fax_id)

        if fax_job is None:
            _mark_event_processed(db, event_id)
            FAX_TELNYX_WEBHOOK_EVENTS_TOTAL.labels(
                event_type=event_type or "", outcome="job_not_found"
            ).inc()
            return {"status": "ok", "detail": "fax_job_not_found"}

        fax_job_id = str(fax_job["id"])
        job_data = fax_job.get("data") if isinstance(fax_job.get("data"), dict) else {}
        current_status = str((job_data or {}).get("status") or "created")

        if not _should_apply_transition(current_status, new_status):
            _insert_fax_event(
                db,
                tenant_id=tenant_id,
                event_data={
                    "fax_job_id": fax_job_id,
                    "event_type": "fax_status_ignored",
                    "source": "telnyx_webhook",
                    "provider": "telnyx",
                    "provider_event_id": event_id,
                    "provider_event_type": event_type,
                    "provider_fax_id": telnyx_fax_id,
                    "status": new_status,
                    "ignored_reason": "status_regression",
                    "current_status": current_status,
                    "received_at": _utcnow(),
                },
            )
            db.commit()
            _mark_event_processed(db, event_id)
            FAX_TELNYX_WEBHOOK_EVENTS_TOTAL.labels(
                event_type=event_type or "", outcome="regression_ignored"
            ).inc()
            return {"status": "ok", "detail": "status_regression_ignored"}

        patch: dict[str, Any] = {
            "status": new_status,
            "status_updated_at": _utcnow(),
            "provider": "telnyx",
            "telnyx_fax_id": telnyx_fax_id,
            "telnyx_last_event_id": event_id,
            "telnyx_last_event_type": event_type,
        }

        if new_status == "delivered":
            patch.setdefault("delivered_at", _utcnow())
        elif new_status == "failed":
            patch.setdefault("failed_at", _utcnow())
            # Telnyx error fields vary; preserve best-effort details without logging PII.
            fail_reason = ep.get("failure_reason") or ep.get("reason") or ep.get("error")
            fail_code = ep.get("failure_code") or ep.get("code")
            if fail_reason:
                patch["provider_failure_reason"] = str(fail_reason)
            if fail_code:
                patch["provider_failure_code"] = str(fail_code)
        elif new_status == "canceled":
            patch.setdefault("canceled_at", _utcnow())

        updated = _patch_fax_job_retry_safe(
            db,
            tenant_id=tenant_id,
            fax_job_id=fax_job_id,
            patch=patch,
            correlation_id=correlation_id,
        )

        _insert_fax_event(
            db,
            tenant_id=tenant_id,
            event_data={
                "fax_job_id": fax_job_id,
                "event_type": "fax_status_updated" if updated else "fax_status_update_failed",
                "source": "telnyx_webhook",
                "provider": "telnyx",
                "provider_event_id": event_id,
                "provider_event_type": event_type,
                "provider_fax_id": telnyx_fax_id,
                "from_status": current_status,
                "to_status": new_status,
                "received_at": _utcnow(),
            },
        )
        db.commit()

        if updated:
            with suppress(Exception):
                await _best_effort_emit_platform_event(
                    db=db,
                    tenant_id=tenant_id,
                    event_type=_outbound_platform_event_type(new_status),
                    entity_type="fax_job",
                    entity_id=fax_job_id,
                    payload={
                        "fax_job_id": fax_job_id,
                        "provider": "telnyx",
                        "provider_fax_id": telnyx_fax_id,
                        "provider_event_id": event_id,
                        "provider_event_type": event_type,
                        "from_status": current_status,
                        "to_status": new_status,
                        "occurred_at": _utcnow(),
                        "folder": "outbox",
                    },
                    idempotency_key=f"telnyx:{event_id}:platform_event",
                    correlation_id=correlation_id,
                )
            FAX_JOB_STATUS_TRANSITIONS_TOTAL.labels(
                source="telnyx_webhook",
                from_status=current_status or "",
                to_status=new_status,
            ).inc()
            FAX_TELNYX_WEBHOOK_EVENTS_TOTAL.labels(
                event_type=event_type or "", outcome="processed"
            ).inc()
        else:
            FAX_TELNYX_WEBHOOK_EVENTS_TOTAL.labels(
                event_type=event_type or "", outcome="update_failed"
            ).inc()

        _mark_event_processed(db, event_id)
        return {"status": "ok", "detail": "non_received_event_processed", "fax_job_id": fax_job_id}

    s3_key: str | None = None
    sha256_hex: str | None = None
    store_status = "pending_fetch"
    case_id: str | None = None

    api_key = settings.telnyx_api_key
    bucket = settings.s3_bucket_docs

    if api_key and bucket and media_url:
        try:
            pdf_bytes = download_media(api_key=api_key, media_url=media_url)
            sha256_hex = hashlib.sha256(pdf_bytes).hexdigest()
            s3_key = _s3_fax_key(tenant_id or "unrouted", telnyx_fax_id)
            put_bytes(
                bucket=bucket,
                key=s3_key,
                content=pdf_bytes,
                content_type="application/pdf",
            )
            store_status = "stored"
            logger.info(
                "telnyx_fax_stored fax_id=%s s3_key=%s sha256=%s",
                telnyx_fax_id,
                s3_key,
                sha256_hex,
            )
        except TelnyxApiError as exc:
            logger.error("telnyx_fax_download_failed fax_id=%s error=%s", telnyx_fax_id, exc)
            store_status = "download_failed"
        except Exception as exc:
            logger.error("telnyx_fax_s3_failed fax_id=%s error=%s", telnyx_fax_id, exc)
            store_status = "s3_failed"
    else:
        missing = []
        if not api_key:
            missing.append("TELNYX_API_KEY")
        if not bucket:
            missing.append("S3_BUCKET_DOCS")
        if not media_url:
            missing.append("media_url_in_payload")
        logger.warning(
            "telnyx_fax_skipping_download fax_id=%s missing=%s", telnyx_fax_id, missing
        )

    if tenant_id and store_status == "stored":
        case_id = _route_fax_to_case(db, tenant_id, telnyx_fax_id, from_number)
        if not case_id:
            logger.info(
                "telnyx_fax_unrouted fax_id=%s tenant_id=%s", telnyx_fax_id, tenant_id
            )

    _insert_fax_document(
        db,
        fax_id=telnyx_fax_id,
        tenant_id=tenant_id,
        from_phone=from_number,
        to_phone=to_number,
        s3_key=s3_key,
        sha256=sha256_hex,
        case_id=case_id,
        status=store_status if tenant_id else "unrouted_tenant",
    )

    if tenant_id:
        _set_tenant_rls_context(db, tenant_id)
        with suppress(Exception):
            await _best_effort_emit_platform_event(
                db=db,
                tenant_id=tenant_id,
                event_type="fax.inbound.received",
                entity_type="fax_document",
                entity_id=telnyx_fax_id,
                payload={
                    "fax_id": telnyx_fax_id,
                    "provider": "telnyx",
                    "provider_event_id": event_id,
                    "provider_event_type": event_type,
                    "store_status": store_status,
                    "case_id": case_id,
                    "occurred_at": _utcnow(),
                    "folder": "inbox",
                },
                idempotency_key=f"telnyx:{event_id}:platform_event",
                correlation_id=None,
            )

    if store_status == "stored" and s3_key:
        queue_url = settings.fax_classify_queue_url
        if queue_url:
            job = {
                "job_type": "fax_classify_extract",
                "fax_id": telnyx_fax_id,
                "tenant_id": tenant_id,
                "s3_key": s3_key,
                "sha256": sha256_hex,
                "case_id": case_id,
            }
            sqs_publisher.enqueue(
                queue_url,
                job,
                deduplication_id=telnyx_fax_id,
            )
            logger.info("telnyx_fax_enqueued_classify fax_id=%s", telnyx_fax_id)

    _mark_event_processed(db, event_id)
    FAX_TELNYX_WEBHOOK_EVENTS_TOTAL.labels(event_type=event_type or "", outcome="processed").inc()

    return {"status": "ok", "fax_id": telnyx_fax_id, "store_status": store_status}
