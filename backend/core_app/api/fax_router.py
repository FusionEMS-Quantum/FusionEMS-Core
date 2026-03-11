from __future__ import annotations

import hashlib
import logging
import uuid
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy import text
from sqlalchemy.orm import Session
from starlette.responses import RedirectResponse

from core_app.api.dependencies import db_session_dependency, get_current_user
from core_app.core.brand import resolve_tenant_brand
from core_app.core.config import get_settings
from core_app.documents.s3_storage import default_docs_bucket, presign_get, put_bytes
from core_app.fax.telnyx_service import (
    TelnyxConfig,
    TelnyxNotConfigured,
    download_media,
)
from core_app.schemas.auth import CurrentUser
from core_app.services.domination_service import DominationService
from core_app.services.event_publisher import get_event_publisher
from core_app.services.sqs_publisher import enqueue

router = APIRouter(prefix="/api/v1", tags=["Fax"])

logger = logging.getLogger(__name__)


def _resolve_fax_s3_location(
    *, fax_id: str, tenant_id: uuid.UUID, db: Session
) -> tuple[str, str] | None:
    """Resolve a fax PDF to (bucket, key) under tenant isolation."""
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
    """
    Telnyx inbound fax webhook (billing/docs). Stores an idempotent receipt, creates a fax_event,
    and creates a document record. If Telnyx API key is configured, downloads media and uploads to S3.
    """
    tenant_id_raw = payload.get("tenant_id")
    if not tenant_id_raw:
        raise HTTPException(status_code=400, detail="tenant_id_required")

    try:
        tenant_id = uuid.UUID(str(tenant_id_raw))
    except Exception as exc:
        raise HTTPException(status_code=400, detail="invalid_tenant_id") from exc

    if not tenant_id:
        raise HTTPException(status_code=400, detail="tenant_id_required")

    settings = get_settings()
    publisher = get_event_publisher()
    svc = DominationService(db, publisher)

    event_id = (
        payload.get("data", {}).get("id") or payload.get("id") or str(uuid.uuid4())
    )
    raw = (str(payload)).encode("utf-8")
    payload_hash = hashlib.sha256(raw).hexdigest()

    # Idempotency receipt
    existing = svc.repo("telnyx_webhook_receipts").list(tenant_id, limit=2000)
    if any(r["data"].get("event_id") == event_id for r in existing):
        return {"status": "duplicate", "event_id": event_id}

    await svc.create(
        table="telnyx_webhook_receipts",
        tenant_id=tenant_id,
        actor_user_id=None,
        data={"event_id": event_id, "payload_hash": payload_hash, "payload": payload},
        correlation_id=getattr(request.state, "correlation_id", None),
    )

    fax_event = await svc.create(
        table="fax_events",
        tenant_id=tenant_id,
        actor_user_id=None,
        data=payload,
        correlation_id=getattr(request.state, "correlation_id", None),
    )

    # Try to fetch fax media if available
    media_url = payload.get("data", {}).get("payload", {}).get(
        "media_url"
    ) or payload.get("media_url")
    bucket = default_docs_bucket()
    doc_key = None
    if bucket and media_url and settings.telnyx_api_key:
        try:
            tel_cfg = TelnyxConfig(
                api_key=settings.telnyx_api_key,
                messaging_profile_id=settings.telnyx_messaging_profile_id or None,
            )
            content = download_media(cfg=tel_cfg, media_url=media_url)
            doc_key = f"tenants/{tenant_id}/fax/inbound/{event_id}.pdf"
            put_bytes(
                bucket=bucket,
                key=doc_key,
                content=content,
                content_type="application/pdf",
            )
        except TelnyxNotConfigured:
            doc_key = None

    doc_row = await svc.create(
        table="documents",
        tenant_id=tenant_id,
        actor_user_id=None,
        data={
            "source": "telnyx_fax",
            "fax_event_id": fax_event["id"],
            "bucket": bucket,
            "s3_key": doc_key,
            "media_url": media_url,
            "doc_type": "fax_inbound",
            "status": "stored" if doc_key else "pending_fetch",
        },
        correlation_id=getattr(request.state, "correlation_id", None),
    )

    publisher.publish_sync(
        topic=f"tenant.{tenant_id}.documents.fax.received",
        tenant_id=tenant_id,
        entity_type="document",
        entity_id=doc_row["id"],
        event_type="FAX_DOCUMENT_RECEIVED",
        payload={"document_id": doc_row["id"], "fax_event_id": fax_event["id"]},
        correlation_id=getattr(request.state, "correlation_id", None),
    )

    return {
        "status": "ok",
        "fax_event_id": fax_event["id"],
        "document_id": doc_row["id"],
    }


@router.get("/fax/inbox")
async def fax_inbox(
    request: Request,
    folder: str | None = None,
    status: str | None = None,
    limit: int = 50,
    current: CurrentUser = Depends(get_current_user),
    db: Session = Depends(db_session_dependency),
):
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
        return [
            {
                "id": str(r.get("fax_id")),
                "from_number": r.get("from_phone"),
                "to_number": r.get("to_phone"),
                "received_at": (r.get("created_at").isoformat() if r.get("created_at") else None),
                "status": r.get("status"),
                "telnyx_fax_id": str(r.get("fax_id")),
                "data": {
                    "direction": "inbound",
                    "s3_key": r.get("s3_key_original"),
                    "sha256": r.get("sha256_original"),
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
    fax_id: uuid.UUID,
    limit: int = 50,
    current: CurrentUser = Depends(get_current_user),
    db: Session = Depends(db_session_dependency),
):
    svc = DominationService(db, get_event_publisher())
    rows = svc.repo("fax_events").list_raw_by_field(
        "fax_job_id", str(fax_id), tenant_id=current.tenant_id, limit=limit
    )
    return rows


@router.post("/fax/{fax_id}/match/trigger")
async def trigger_fax_match(
    fax_id: uuid.UUID,
    payload: dict[str, Any],
    request: Request,
    current: CurrentUser = Depends(get_current_user),
    db: Session = Depends(db_session_dependency),
):
    svc = DominationService(db, get_event_publisher())
    row = await svc.create(
        table="fax_events",
        tenant_id=current.tenant_id,
        actor_user_id=current.user_id,
        data={
            "fax_job_id": str(fax_id),
            "event_type": "match_triggered",
            "triggered_by": str(current.user_id),
            "payload": payload,
        },
        correlation_id=getattr(request.state, "correlation_id", None),
    )
    get_event_publisher().publish_sync(
        topic=f"tenant.{current.tenant_id}.fax.match.trigger",
        tenant_id=current.tenant_id,
        entity_type="fax_job",
        entity_id=str(fax_id),
        event_type="FAX_MATCH_TRIGGERED",
        payload={"fax_job_id": str(fax_id), "fax_event_id": row["id"]},
        correlation_id=getattr(request.state, "correlation_id", None),
    )
    return {"status": "triggered", "fax_event_id": row["id"]}


@router.post("/fax/{fax_id}/match/detach")
async def detach_fax_match(
    fax_id: uuid.UUID,
    request: Request,
    current: CurrentUser = Depends(get_current_user),
    db: Session = Depends(db_session_dependency),
):
    svc = DominationService(db, get_event_publisher())
    row = await svc.create(
        table="fax_events",
        tenant_id=current.tenant_id,
        actor_user_id=current.user_id,
        data={
            "fax_job_id": str(fax_id),
            "event_type": "match_detached",
            "detached_by": str(current.user_id),
        },
        correlation_id=getattr(request.state, "correlation_id", None),
    )
    return {"status": "detached", "fax_event_id": row["id"]}


@router.post("/claims/{claim_id}/documents/attach-fax")
async def attach_fax_to_claim(
    claim_id: uuid.UUID,
    payload: dict[str, Any],
    request: Request,
    current: CurrentUser = Depends(get_current_user),
    db: Session = Depends(db_session_dependency),
):
    svc = DominationService(db, get_event_publisher())
    fax_job_id = payload.get("fax_job_id")
    document_id = payload.get("document_id")

    row = await svc.create(
        table="fax_events",
        tenant_id=current.tenant_id,
        actor_user_id=current.user_id,
        data={
            "claim_id": str(claim_id),
            "fax_job_id": str(fax_job_id) if fax_job_id else None,
            "document_id": str(document_id) if document_id else None,
            "event_type": "attached_to_claim",
            "attached_by": str(current.user_id),
        },
        correlation_id=getattr(request.state, "correlation_id", None),
    )
    get_event_publisher().publish_sync(
        topic=f"tenant.{current.tenant_id}.claims.fax.attached",
        tenant_id=current.tenant_id,
        entity_type="claim",
        entity_id=str(claim_id),
        event_type="FAX_ATTACHED_TO_CLAIM",
        payload={"claim_id": str(claim_id), "fax_job_id": str(fax_job_id)},
        correlation_id=getattr(request.state, "correlation_id", None),
    )
    return {"status": "attached", "fax_event_id": row["id"]}
