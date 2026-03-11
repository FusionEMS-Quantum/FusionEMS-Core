from __future__ import annotations

import json
import logging
import uuid
from datetime import UTC, datetime
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field
from sqlalchemy import text
from sqlalchemy.orm import Session
from starlette.responses import RedirectResponse

from core_app.api.dependencies import db_session_dependency, get_current_user
from core_app.core.brand import resolve_tenant_brand
from core_app.core.config import get_settings
from core_app.documents.s3_storage import presign_get
from core_app.schemas.auth import CurrentUser
from core_app.services.domination_service import DominationService
from core_app.services.event_publisher import get_event_publisher
from core_app.services.sqs_publisher import enqueue

router = APIRouter(prefix="/api/v1", tags=["Fax"])

logger = logging.getLogger(__name__)


def _set_tenant_rls_context(db: Session, tenant_id: uuid.UUID) -> None:
    """Ensure tenant RLS context is set for this DB session."""
    db.execute(
        text("SELECT set_config('app.tenant_id', :tid, true)"),
        {"tid": str(tenant_id)},
    )


def _resolve_fax_s3_location(
    *, fax_id: str, tenant_id: uuid.UUID, db: Session
) -> tuple[str, str] | None:
    """Resolve a fax PDF to (bucket, key) under tenant isolation."""
    _set_tenant_rls_context(db, tenant_id)
    settings = get_settings()
    default_bucket = settings.s3_bucket_docs
    if not default_bucket:
        return None

    # Try outbound job first (UUID)
    try:
        job_uuid = uuid.UUID(fax_id)
    except Exception:
        job_uuid = None

    if job_uuid is not None:
        row = (
            db.execute(
                text(
                    "SELECT data FROM fax_jobs WHERE tenant_id = :tid AND id = :id AND deleted_at IS NULL LIMIT 1"
                ),
                {"tid": str(tenant_id), "id": str(job_uuid)},
            )
            .mappings()
            .first()
        )
        if row and isinstance(row.get("data"), dict):
            data = row["data"]
            key = str(data.get("s3_key") or data.get("key") or "").strip()
            bucket = str(data.get("bucket") or data.get("s3_bucket") or "").strip() or default_bucket

            if not key:
                document_id = str(data.get("document_id") or "").strip()
                if document_id:
                    doc_row = (
                        db.execute(
                            text(
                                "SELECT data FROM documents WHERE tenant_id = :tid AND id = :id AND deleted_at IS NULL LIMIT 1"
                            ),
                            {"tid": str(tenant_id), "id": document_id},
                        )
                        .mappings()
                        .first()
                    )
                    if doc_row and isinstance(doc_row.get("data"), dict):
                        dd = doc_row["data"]
                        bucket = str(dd.get("bucket") or "").strip() or bucket
                        key = str(dd.get("s3_key") or dd.get("key") or "").strip()

            if key:
                return (bucket, key)

    # Inbound fax document fallback
    row2 = (
        db.execute(
            text(
                "SELECT s3_key_original FROM fax_documents "
                "WHERE tenant_id = :tid AND fax_id = :fid LIMIT 1"
            ),
            {"tid": str(tenant_id), "fid": fax_id},
        )
        .mappings()
        .first()
    )
    if row2 and row2.get("s3_key_original"):
        return (default_bucket, str(row2["s3_key_original"]))

    return None


@router.post("/fax/send")
async def send_fax(
    payload: dict[str, Any],
    request: Request,
    current: CurrentUser = Depends(get_current_user),
    db: Session = Depends(db_session_dependency),
):
    # Outbound fax job record (actual Telnyx send happens in worker once configured)
    brand = resolve_tenant_brand(db, current.tenant_id)
    payload.setdefault("brand_sender_name", brand.display_name)
    payload.setdefault("brand_from_number", brand.billing_phone_e164)
    payload.setdefault("direction", "outbound")
    svc = DominationService(db, get_event_publisher())
    row = await svc.create(
        table="fax_jobs",
        tenant_id=current.tenant_id,
        actor_user_id=current.user_id,
        data=payload,
        correlation_id=getattr(request.state, "correlation_id", None),
    )

    settings = get_settings()
    queue_url = str(getattr(settings, "fax_outbound_queue_url", "") or "")
    if queue_url:
        try:
            dedup_id = row["id"] if queue_url.endswith(".fifo") else None
            enqueue(
                queue_url,
                {
                    "job_type": "fax_send",
                    "fax_job_id": row["id"],
                    "tenant_id": str(current.tenant_id),
                    "actor_user_id": str(current.user_id),
                    "correlation_id": getattr(request.state, "correlation_id", None),
                },
                deduplication_id=dedup_id,
            )
        except Exception as exc:
            logger.error(
                "fax_send_enqueue_failed fax_job_id=%s tenant_id=%s error=%s",
                row.get("id"),
                str(current.tenant_id),
                exc,
            )

    get_event_publisher().publish_sync(
        topic=f"tenant.{current.tenant_id}.fax.job.created",
        tenant_id=current.tenant_id,
        entity_type="fax_job",
        entity_id=row["id"],
        event_type="FAX_JOB_CREATED",
        payload={"fax_job_id": row["id"]},
        correlation_id=getattr(request.state, "correlation_id", None),
    )
    return row


@router.post("/webhooks/telnyx/fax/inbound", include_in_schema=True)
async def inbound_fax(
    payload: dict[str, Any],
    request: Request,
    db: Session = Depends(db_session_dependency),
):
    _ = payload
    _ = request
    _ = db
    raise HTTPException(status_code=410, detail="Use /api/v1/webhooks/telnyx/fax")


@router.get("/fax/inbox")
async def fax_inbox(
    request: Request,
    folder: str | None = None,
    status: str | None = None,
    limit: int = 50,
    current: CurrentUser = Depends(get_current_user),
    db: Session = Depends(db_session_dependency),
):
    _ = request
    _set_tenant_rls_context(db, current.tenant_id)
    # Backwards-compatible default: existing behavior returns fax_jobs.
    folder_norm = (folder or "").strip().lower()

    if folder_norm == "inbox":
        # Inbound faxes come from fax_documents (Telnyx webhook → S3).
        rows = (
            db.execute(
                text(
                    "SELECT fax_id, from_phone, to_phone, s3_key_original, sha256_original, status, created_at "
                    "FROM fax_documents WHERE tenant_id = :tid ORDER BY created_at DESC LIMIT :limit"
                ),
                {"tid": str(current.tenant_id), "limit": int(limit)},
            )
            .mappings()
            .all()
        )

        # Match state is stored in the domination table document_matches as JSONB.
        match_rows = (
            db.execute(
                text(
                    "SELECT data, updated_at FROM document_matches "
                    "WHERE tenant_id = :tid AND deleted_at IS NULL "
                    "ORDER BY updated_at DESC LIMIT 500"
                ),
                {"tid": str(current.tenant_id)},
            )
            .mappings()
            .all()
        )
        match_by_fax_id: dict[str, dict[str, Any]] = {}
        for mr in match_rows:
            data = mr.get("data")
            if not isinstance(data, dict):
                continue
            fid = str(data.get("fax_id") or "").strip()
            if not fid:
                continue
            if fid not in match_by_fax_id:
                match_by_fax_id[fid] = data

        def _normalize_match_status(match_data: dict[str, Any] | None) -> str:
            if not match_data:
                return "unmatched"
            raw = str(match_data.get("match_status") or "").strip().lower()
            if raw in {"matched", "review", "unmatched"}:
                return raw
            if raw in {"suggested"}:
                return "review"
            if raw in {"auto_matched", "auto-matched"}:
                return "matched"
            return "unmatched"

        return [
            {
                "id": str(r.get("fax_id")),
                "from_number": r.get("from_phone"),
                "to_number": r.get("to_phone"),
                "received_at": (r.get("created_at").isoformat() if r.get("created_at") else None),
                "status": r.get("status"),
                "document_match_status": _normalize_match_status(
                    match_by_fax_id.get(str(r.get("fax_id")))
                ),
                "telnyx_fax_id": str(r.get("fax_id")),
                "data": {
                    "direction": "inbound",
                    "s3_key": r.get("s3_key_original"),
                    "sha256": r.get("sha256_original"),
                    "match_suggestions": (
                        (match_by_fax_id.get(str(r.get("fax_id"))) or {}).get("suggested_matches")
                        if isinstance((match_by_fax_id.get(str(r.get("fax_id"))) or {}).get("suggested_matches"), list)
                        else []
                    ),
                    "claim_id": (
                        (match_by_fax_id.get(str(r.get("fax_id"))) or {}).get("matched_claim_id")
                        if isinstance((match_by_fax_id.get(str(r.get("fax_id"))) or {}).get("matched_claim_id"), str)
                        else None
                    ),
                    "patient_name": (
                        (match_by_fax_id.get(str(r.get("fax_id"))) or {}).get("patient_name")
                        if isinstance((match_by_fax_id.get(str(r.get("fax_id"))) or {}).get("patient_name"), str)
                        else None
                    ),
                    "match_type": (
                        (match_by_fax_id.get(str(r.get("fax_id"))) or {}).get("match_type")
                        if isinstance((match_by_fax_id.get(str(r.get("fax_id"))) or {}).get("match_type"), str)
                        else None
                    ),
                    "confidence": (
                        (match_by_fax_id.get(str(r.get("fax_id"))) or {}).get("confidence")
                        if isinstance((match_by_fax_id.get(str(r.get("fax_id"))) or {}).get("confidence"), (int, float))
                        else None
                    ),
                },
            }
            for r in rows
        ]

    svc = DominationService(db, get_event_publisher())
    rows = svc.repo("fax_jobs").list(tenant_id=current.tenant_id, limit=limit, offset=0)

    def _enrich(row: dict[str, Any]) -> dict[str, Any]:
        data = (row.get("data") or {}) if isinstance(row.get("data"), dict) else {}
        out = dict(row)
        out.setdefault("status", data.get("status"))
        out.setdefault(
            "from_number",
            data.get("from")
            or data.get("from_number")
            or data.get("source")
            or data.get("brand_from_number"),
        )
        out.setdefault(
            "to_number",
            data.get("to")
            or data.get("to_number")
            or data.get("destination")
            or data.get("destination_number"),
        )
        out.setdefault(
            "received_at",
            data.get("received_at")
            or data.get("sent_at")
            or data.get("created_at")
            or out.get("created_at"),
        )
        out.setdefault("page_count", data.get("page_count"))
        out.setdefault("document_match_status", data.get("document_match_status"))
        out.setdefault("telnyx_fax_id", data.get("telnyx_fax_id"))
        out.setdefault("status_updated_at", data.get("status_updated_at") or out.get("updated_at"))
        out.setdefault("error", data.get("error"))
        return out

    enriched = [_enrich(r) for r in rows]
    if status and status != "all":
        enriched = [r for r in enriched if (r.get("status") or "") == status]

    if folder_norm == "outbox":
        enriched = [
            r
            for r in enriched
            if ((r.get("data") or {}) if isinstance(r.get("data"), dict) else {}).get("direction")
            in {None, "outbound"}
        ]
    return enriched


@router.get("/fax/{fax_id}/download")
async def download_fax(
    fax_id: str,
    current: CurrentUser = Depends(get_current_user),
    db: Session = Depends(db_session_dependency),
):
    """Authenticated download for inbound or outbound fax PDFs.

    - If fax_id is a fax_jobs UUID: resolve document bucket/key from job or linked document_id.
    - Otherwise: treat as inbound fax_documents.fax_id.
    Returns a short-lived S3 presigned URL via redirect.
    """
    resolved = _resolve_fax_s3_location(fax_id=fax_id, tenant_id=current.tenant_id, db=db)
    if not resolved:
        raise HTTPException(status_code=404, detail="fax_document_not_found")
    (bucket, key) = resolved
    url = presign_get(bucket=bucket, key=key, expires_seconds=300)
    return RedirectResponse(url=url, status_code=302)


@router.get("/fax/{fax_id}/preview-url")
async def fax_preview_url(
    fax_id: str,
    current: CurrentUser = Depends(get_current_user),
    db: Session = Depends(db_session_dependency),
):
    resolved = _resolve_fax_s3_location(fax_id=fax_id, tenant_id=current.tenant_id, db=db)
    if not resolved:
        raise HTTPException(status_code=404, detail="fax_document_not_found")
    (bucket, key) = resolved
    url = presign_get(bucket=bucket, key=key, expires_seconds=300)
    return {"url": url, "expires_seconds": 300}


@router.get("/fax/{fax_id}/events")
async def fax_events(
    fax_id: str,
    limit: int = 50,
    current: CurrentUser = Depends(get_current_user),
    db: Session = Depends(db_session_dependency),
):
    _set_tenant_rls_context(db, current.tenant_id)
    svc = DominationService(db, get_event_publisher())
    try:
        uuid.UUID(fax_id)
        field = "fax_job_id"
    except Exception:
        field = "fax_id"
    rows = svc.repo("fax_events").list_raw_by_field(
        field, str(fax_id), tenant_id=current.tenant_id, limit=limit
    )
    return rows


class AttachFaxToClaimRequest(BaseModel):
    fax_id: str = Field(min_length=1)
    attachment_type: str = Field(default="manual", min_length=1)


@router.post("/fax/{fax_id}/match/trigger")
async def trigger_fax_match(
    fax_id: str,
    request: Request,
    current: CurrentUser = Depends(get_current_user),
    db: Session = Depends(db_session_dependency),
):
    _set_tenant_rls_context(db, current.tenant_id)
    svc = DominationService(db, get_event_publisher())

    if _is_uuid(fax_id):
        raise HTTPException(status_code=400, detail="outbound_fax_match_not_supported")

    # Best-effort: enqueue classification for this fax if configured.
    resolved = _resolve_fax_s3_location(fax_id=fax_id, tenant_id=current.tenant_id, db=db)
    settings = get_settings()
    queue_url = str(getattr(settings, "fax_classify_queue_url", "") or "")
    if queue_url and resolved:
        (_, key) = resolved
        try:
            dedup_id = fax_id if queue_url.endswith(".fifo") else None
            enqueue(
                queue_url,
                {
                    "job_type": "fax_classify_extract",
                    "fax_id": fax_id,
                    "tenant_id": str(current.tenant_id),
                    "s3_key": key,
                    "correlation_id": getattr(request.state, "correlation_id", None),
                    "source": "manual_trigger",
                },
                deduplication_id=dedup_id,
            )
        except Exception as exc:
            logger.error(
                "fax_match_trigger_enqueue_failed fax_id=%s tenant_id=%s error=%s",
                fax_id,
                str(current.tenant_id),
                exc,
            )

    row = await svc.create(
        table="fax_events",
        tenant_id=current.tenant_id,
        actor_user_id=current.user_id,
        data={
            "fax_job_id": (fax_id if _is_uuid(fax_id) else None),
            "fax_id": fax_id,
            "event_type": "match_triggered",
            "triggered_by": str(current.user_id),
        },
        correlation_id=getattr(request.state, "correlation_id", None),
    )
    get_event_publisher().publish_sync(
        topic=f"tenant.{current.tenant_id}.fax.match.trigger",
        tenant_id=current.tenant_id,
        entity_type="fax",
        entity_id=str(fax_id),
        event_type="FAX_MATCH_TRIGGERED",
        payload={"fax_id": str(fax_id), "fax_event_id": row["id"]},
        correlation_id=getattr(request.state, "correlation_id", None),
    )
    return {"status": "triggered", "fax_event_id": row["id"]}


@router.post("/fax/{fax_id}/match/detach")
async def detach_fax_match(
    fax_id: str,
    request: Request,
    current: CurrentUser = Depends(get_current_user),
    db: Session = Depends(db_session_dependency),
):
    _set_tenant_rls_context(db, current.tenant_id)

    # Best-effort: clear match state.
    patch = {
        "match_status": "unmatched",
        "matched_claim_id": None,
        "suggested_matches": [],
        "match_type": None,
        "confidence": None,
        "patient_name": None,
        "updated_by": str(current.user_id),
    }
    try:
        row = (
            db.execute(
                text(
                    "SELECT id FROM document_matches "
                    "WHERE tenant_id = :tid AND deleted_at IS NULL AND data->>'fax_id' = :fid "
                    "ORDER BY updated_at DESC LIMIT 1"
                ),
                {"tid": str(current.tenant_id), "fid": fax_id},
            )
            .mappings()
            .first()
        )
        if row and row.get("id"):
            db.execute(
                text(
                    "UPDATE document_matches "
                    "SET data = data || :patch::jsonb, version = version + 1, updated_at = now() "
                    "WHERE tenant_id = :tid AND id = :id"
                ),
                {
                    "tid": str(current.tenant_id),
                    "id": str(row["id"]),
                    "patch": json.dumps(patch, default=str),
                },
            )
            db.commit()
    except Exception as exc:
        logger.warning(
            "fax_match_detach_state_update_failed fax_id=%s tenant_id=%s error=%s",
            fax_id,
            str(current.tenant_id),
            exc,
        )

    svc = DominationService(db, get_event_publisher())
    row = await svc.create(
        table="fax_events",
        tenant_id=current.tenant_id,
        actor_user_id=current.user_id,
        data={
            "fax_job_id": (fax_id if _is_uuid(fax_id) else None),
            "fax_id": fax_id,
            "event_type": "match_detached",
            "detached_by": str(current.user_id),
        },
        correlation_id=getattr(request.state, "correlation_id", None),
    )
    return {"status": "detached", "fax_event_id": row["id"]}


@router.post("/claims/{claim_id}/documents/attach-fax")
async def attach_fax_to_claim(
    claim_id: uuid.UUID,
    payload: AttachFaxToClaimRequest,
    request: Request,
    current: CurrentUser = Depends(get_current_user),
    db: Session = Depends(db_session_dependency),
):
    _set_tenant_rls_context(db, current.tenant_id)

    # Validate claim exists under tenant isolation.
    claim_row = (
        db.execute(
            text(
                "SELECT id FROM billing_cases WHERE tenant_id = :tid AND id = :id AND deleted_at IS NULL LIMIT 1"
            ),
            {"tid": str(current.tenant_id), "id": str(claim_id)},
        )
        .mappings()
        .first()
    )
    if not claim_row:
        raise HTTPException(status_code=404, detail="claim_not_found")

    fax_id = payload.fax_id
    # Require the fax document to exist (inbox item).
    fax_doc = (
        db.execute(
            text(
                "SELECT fax_id FROM fax_documents WHERE tenant_id = :tid AND fax_id = :fid LIMIT 1"
            ),
            {"tid": str(current.tenant_id), "fid": fax_id},
        )
        .mappings()
        .first()
    )
    if not fax_doc:
        raise HTTPException(status_code=404, detail="fax_document_not_found")

    now_iso = datetime.now(UTC).isoformat()

    # Upsert into claim_documents (domination JSONB table).
    try:
        existing = (
            db.execute(
                text(
                    "SELECT id FROM claim_documents "
                    "WHERE tenant_id = :tid AND deleted_at IS NULL "
                    "AND data->>'fax_id' = :fid AND data->>'claim_id' = :cid "
                    "ORDER BY updated_at DESC LIMIT 1"
                ),
                {"tid": str(current.tenant_id), "fid": fax_id, "cid": str(claim_id)},
            )
            .mappings()
            .first()
        )
        base_data = {
            "fax_id": fax_id,
            "claim_id": str(claim_id),
            "attachment_type": payload.attachment_type,
            "attached_by": str(current.user_id),
            "attached_at": now_iso,
        }
        if existing and existing.get("id"):
            db.execute(
                text(
                    "UPDATE claim_documents "
                    "SET data = data || :patch::jsonb, version = version + 1, updated_at = now() "
                    "WHERE tenant_id = :tid AND id = :id"
                ),
                {
                    "tid": str(current.tenant_id),
                    "id": str(existing["id"]),
                    "patch": json.dumps(base_data, default=str),
                },
            )
        else:
            db.execute(
                text(
                    "INSERT INTO claim_documents (tenant_id, data) VALUES (:tid, :data::jsonb)"
                ),
                {"tid": str(current.tenant_id), "data": json.dumps(base_data, default=str)},
            )

        # Update match state to matched.
        match_patch = {
            "fax_id": fax_id,
            "match_status": "matched",
            "matched_claim_id": str(claim_id),
            "match_type": "manual_attach",
            "confidence": 1.0,
            "updated_by": str(current.user_id),
            "updated_at": now_iso,
        }
        dm = (
            db.execute(
                text(
                    "SELECT id FROM document_matches "
                    "WHERE tenant_id = :tid AND deleted_at IS NULL AND data->>'fax_id' = :fid "
                    "ORDER BY updated_at DESC LIMIT 1"
                ),
                {"tid": str(current.tenant_id), "fid": fax_id},
            )
            .mappings()
            .first()
        )
        if dm and dm.get("id"):
            db.execute(
                text(
                    "UPDATE document_matches "
                    "SET data = data || :patch::jsonb, version = version + 1, updated_at = now() "
                    "WHERE tenant_id = :tid AND id = :id"
                ),
                {
                    "tid": str(current.tenant_id),
                    "id": str(dm["id"]),
                    "patch": json.dumps(match_patch, default=str),
                },
            )
        else:
            db.execute(
                text(
                    "INSERT INTO document_matches (tenant_id, data) VALUES (:tid, :data::jsonb)"
                ),
                {"tid": str(current.tenant_id), "data": json.dumps(match_patch, default=str)},
            )

        db.commit()
    except Exception as exc:
        logger.error(
            "attach_fax_to_claim_persist_failed claim_id=%s fax_id=%s tenant_id=%s error=%s",
            str(claim_id),
            fax_id,
            str(current.tenant_id),
            exc,
        )
        raise HTTPException(status_code=500, detail="attach_fax_persist_failed") from exc

    svc = DominationService(db, get_event_publisher())
    row = await svc.create(
        table="fax_events",
        tenant_id=current.tenant_id,
        actor_user_id=current.user_id,
        data={
            "claim_id": str(claim_id),
            "fax_id": fax_id,
            "event_type": "attached_to_claim",
            "attached_by": str(current.user_id),
            "attachment_type": payload.attachment_type,
        },
        correlation_id=getattr(request.state, "correlation_id", None),
    )
    get_event_publisher().publish_sync(
        topic=f"tenant.{current.tenant_id}.claims.fax.attached",
        tenant_id=current.tenant_id,
        entity_type="claim",
        entity_id=str(claim_id),
        event_type="FAX_ATTACHED_TO_CLAIM",
        payload={"claim_id": str(claim_id), "fax_id": fax_id},
        correlation_id=getattr(request.state, "correlation_id", None),
    )
    return {"status": "attached", "fax_event_id": row["id"]}


def _is_uuid(value: str) -> bool:
    try:
        uuid.UUID(value)
        return True
    except Exception:
        return False
