"""
Document Vault Router — Full CRUD

All endpoints are founder-only with audit logging.
"""
# pylint: disable=raise-missing-from

from __future__ import annotations

import uuid
from typing import Any

from fastapi import APIRouter, Body, Depends, HTTPException, Path, Query, status
from sqlalchemy.orm import Session

from core_app.api.dependencies import (
    db_session_dependency,
    require_founder_only_audited,
)
from core_app.schemas.auth import CurrentUser
from core_app.services.document_vault_service import (
    DocumentVaultService,
    HoldStateError,
)

router = APIRouter(prefix="/v1/founder/vault", tags=["Founder Document Vault"])

_founder_guard = require_founder_only_audited()


def _svc(db: Session) -> DocumentVaultService:
    return DocumentVaultService(db)


def _actor(u: CurrentUser) -> tuple[uuid.UUID | None, str | None]:
    return u.user_id, str(u.user_id)


# ── Vault tree / policies ─────────────────────────────────────────────────────

@router.get("/vaults", summary="Vault tree with document counts")
async def get_vault_tree(
    current_user: CurrentUser = Depends(_founder_guard),
    db: Session = Depends(db_session_dependency),
) -> list[dict[str, Any]]:
    return _svc(db).get_vault_tree()


@router.get("/policies", summary="Wisconsin retention defaults")
async def get_vault_policies(
    current_user: CurrentUser = Depends(_founder_guard),
    db: Session = Depends(db_session_dependency),
) -> dict[str, Any]:
    return _svc(db).get_policies()


# ── Documents — list / detail ─────────────────────────────────────────────────

@router.get("/vaults/{vault_id}/documents", summary="List documents in vault")
async def list_documents(
    vault_id: str = Path(...),
    lock_state: str | None = Query(None),
    q: str | None = Query(None),
    limit: int = Query(default=50, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
    current_user: CurrentUser = Depends(_founder_guard),
    db: Session = Depends(db_session_dependency),
) -> dict[str, Any]:
    docs = _svc(db).list_documents(vault_id=vault_id, lock_state=lock_state, query=q, limit=limit, offset=offset)
    return {
        "vault_id": vault_id,
        "count": len(docs),
        "offset": offset,
        "documents": [
            {
                "id": str(d.id),
                "title": d.title,
                "original_filename": d.original_filename,
                "content_type": d.content_type,
                "file_size_bytes": d.file_size_bytes,
                "lock_state": d.lock_state,
                "retention_class": d.retention_class,
                "retain_until": d.retain_until.isoformat() if d.retain_until else None,
                "ocr_status": d.ocr_status,
                "ai_classification_status": d.ai_classification_status,
                "ai_document_type": d.ai_document_type,
                "ai_tags": d.ai_tags,
                "ai_summary": d.ai_summary,
                "created_at": d.created_at.isoformat() if d.created_at else None,
                "uploaded_by_display": d.uploaded_by_display,
            }
            for d in docs
        ],
    }


@router.get("/documents/{document_id}", summary="Get document detail")
async def get_document(
    document_id: uuid.UUID = Path(...),
    current_user: CurrentUser = Depends(_founder_guard),
    db: Session = Depends(db_session_dependency),
) -> dict[str, Any]:
    try:
        doc = _svc(db).get_document(document_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return {
        "id": str(doc.id),
        "vault_id": doc.vault_id,
        "title": doc.title,
        "original_filename": doc.original_filename,
        "content_type": doc.content_type,
        "file_size_bytes": doc.file_size_bytes,
        "s3_bucket": doc.s3_bucket,
        "s3_key": doc.s3_key,
        "s3_version_id": doc.s3_version_id,
        "checksum_sha256": doc.checksum_sha256,
        "lock_state": doc.lock_state,
        "lock_history": doc.lock_history,
        "retention_class": doc.retention_class,
        "retain_until": doc.retain_until.isoformat() if doc.retain_until else None,
        "ocr_status": doc.ocr_status,
        "ocr_text": doc.ocr_text,
        "ai_classification_status": doc.ai_classification_status,
        "ai_document_type": doc.ai_document_type,
        "ai_tags": doc.ai_tags,
        "ai_summary": doc.ai_summary,
        "ai_confidence": doc.ai_confidence,
        "ai_classified_at": doc.ai_classified_at.isoformat() if doc.ai_classified_at else None,
        "doc_metadata": doc.doc_metadata,
        "addenda": doc.addenda,
        "created_at": doc.created_at.isoformat() if doc.created_at else None,
        "uploaded_by_display": doc.uploaded_by_display,
    }


@router.patch("/documents/{document_id}", summary="Update document metadata")
async def update_document_metadata(
    document_id: uuid.UUID = Path(...),
    title: str | None = Body(None),
    doc_metadata: dict[str, Any] | None = Body(None),
    current_user: CurrentUser = Depends(_founder_guard),
    db: Session = Depends(db_session_dependency),
) -> dict[str, Any]:
    actor_id, actor_display = _actor(current_user)
    try:
        doc = _svc(db).update_document_metadata(document_id=document_id, title=title, doc_metadata=doc_metadata, actor_user_id=actor_id, actor_display=actor_display)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return {"id": str(doc.id), "title": doc.title, "doc_metadata": doc.doc_metadata}


# ── Upload flow ───────────────────────────────────────────────────────────────

@router.post("/vaults/{vault_id}/upload/initiate", status_code=status.HTTP_201_CREATED, summary="Initiate S3 upload — get presigned POST")
async def initiate_upload(
    vault_id: str = Path(...),
    title: str = Body(...),
    original_filename: str = Body(...),
    content_type: str = Body(...),
    file_size_bytes: int | None = Body(None),
    doc_metadata: dict[str, Any] = Body(default={}),
    current_user: CurrentUser = Depends(_founder_guard),
    db: Session = Depends(db_session_dependency),
) -> dict[str, Any]:
    actor_id, actor_display = _actor(current_user)
    try:
        return _svc(db).initiate_upload(
            vault_id=vault_id,
            title=title,
            original_filename=original_filename,
            content_type=content_type,
            file_size_bytes=file_size_bytes,
            doc_metadata=doc_metadata,
            actor_user_id=actor_id,
            actor_display=actor_display,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/documents/{document_id}/upload/confirm", summary="Confirm upload complete — trigger OCR")
async def confirm_upload(
    document_id: uuid.UUID = Path(...),
    s3_version_id: str | None = Body(None),
    checksum_sha256: str | None = Body(None),
    file_size_bytes: int | None = Body(None),
    current_user: CurrentUser = Depends(_founder_guard),
    db: Session = Depends(db_session_dependency),
) -> dict[str, Any]:
    actor_id, actor_display = _actor(current_user)
    try:
        return _svc(db).confirm_upload(
            document_id=document_id,
            s3_version_id=s3_version_id,
            checksum_sha256=checksum_sha256,
            file_size_bytes=file_size_bytes,
            actor_user_id=actor_id,
            actor_display=actor_display,
        )
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


# ── Download ──────────────────────────────────────────────────────────────────

@router.post("/documents/{document_id}/download", summary="Get presigned download URL")
async def get_presigned_download(
    document_id: uuid.UUID = Path(...),
    current_user: CurrentUser = Depends(_founder_guard),
    db: Session = Depends(db_session_dependency),
) -> dict[str, Any]:
    actor_id, actor_display = _actor(current_user)
    try:
        return _svc(db).get_presigned_download(document_id=document_id, actor_user_id=actor_id, actor_display=actor_display)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


# ── Lock state ────────────────────────────────────────────────────────────────

@router.post("/documents/{document_id}/lock", summary="Change lock state")
async def update_lock_state(
    document_id: uuid.UUID = Path(...),
    lock_state: str = Body(..., embed=True),
    reason: str = Body(..., embed=True),
    current_user: CurrentUser = Depends(_founder_guard),
    db: Session = Depends(db_session_dependency),
) -> dict[str, Any]:
    actor_id, actor_display = _actor(current_user)
    try:
        return _svc(db).set_lock_state(document_id, lock_state, reason, actor_user_id=actor_id, actor_display=actor_display)
    except HoldStateError as exc:
        raise HTTPException(status_code=403, detail=exc.message) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


# ── Addendum ──────────────────────────────────────────────────────────────────

@router.post("/documents/{document_id}/addendum", summary="Append addendum (append-only)")
async def append_addendum(
    document_id: uuid.UUID = Path(...),
    addendum_data: dict[str, Any] = Body(...),
    reason: str = Body(..., embed=True),
    current_user: CurrentUser = Depends(_founder_guard),
    db: Session = Depends(db_session_dependency),
) -> dict[str, Any]:
    actor_id, actor_display = _actor(current_user)
    try:
        return _svc(db).append_addendum(document_id, addendum_data=addendum_data, reason=reason, actor_user_id=actor_id, actor_display=actor_display)
    except HoldStateError as exc:
        raise HTTPException(status_code=403, detail=exc.message) from exc
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


# ── OCR / AI classify ─────────────────────────────────────────────────────────

@router.post("/documents/{document_id}/ocr/poll", summary="Poll Textract OCR job")
async def poll_ocr(
    document_id: uuid.UUID = Path(...),
    current_user: CurrentUser = Depends(_founder_guard),
    db: Session = Depends(db_session_dependency),
) -> dict[str, Any]:
    actor_id, _ = _actor(current_user)
    try:
        return _svc(db).poll_ocr_job(document_id, actor_user_id=actor_id)
    except (ValueError, RuntimeError) as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/documents/{document_id}/classify", summary="Trigger AI classification")
async def classify_document(
    document_id: uuid.UUID = Path(...),
    current_user: CurrentUser = Depends(_founder_guard),
    db: Session = Depends(db_session_dependency),
) -> dict[str, Any]:
    actor_id, actor_display = _actor(current_user)
    try:
        return _svc(db).classify_document(document_id, actor_user_id=actor_id, actor_display=actor_display)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


# ── Audit trail ───────────────────────────────────────────────────────────────

@router.get("/documents/{document_id}/audit", summary="Get document audit trail")
async def get_audit_trail(
    document_id: uuid.UUID = Path(...),
    limit: int = Query(default=100, ge=1, le=500),
    current_user: CurrentUser = Depends(_founder_guard),
    db: Session = Depends(db_session_dependency),
) -> dict[str, Any]:
    entries = _svc(db).get_audit_trail(document_id, limit=limit)
    return {
        "document_id": str(document_id),
        "entries": [
            {
                "id": str(e.id),
                "action": e.action,
                "actor_display": e.actor_display,
                "occurred_at": e.occurred_at.isoformat() if e.occurred_at else None,
                "detail": e.detail,
            }
            for e in entries
        ],
    }


# ── Smart folders ─────────────────────────────────────────────────────────────

@router.get("/vaults/{vault_id}/folders", summary="List smart folders")
async def list_smart_folders(
    vault_id: str = Path(...),
    current_user: CurrentUser = Depends(_founder_guard),
    db: Session = Depends(db_session_dependency),
) -> dict[str, Any]:
    folders = _svc(db).list_smart_folders(vault_id)
    return {
        "vault_id": vault_id,
        "folders": [
            {
                "id": str(f.id),
                "name": f.name,
                "description": f.description,
                "color": f.color,
                "icon_key": f.icon_key,
                "document_ids": f.document_ids,
                "is_ai_generated": f.is_ai_generated,
                "created_at": f.created_at.isoformat() if f.created_at else None,
            }
            for f in folders
        ],
    }


@router.post("/vaults/{vault_id}/folders", status_code=status.HTTP_201_CREATED, summary="Create smart folder")
async def create_smart_folder(
    vault_id: str = Path(...),
    name: str = Body(...),
    description: str | None = Body(None),
    color: str | None = Body(None),
    icon_key: str | None = Body(None),
    document_ids: list[uuid.UUID] = Body(default=[]),
    current_user: CurrentUser = Depends(_founder_guard),
    db: Session = Depends(db_session_dependency),
) -> dict[str, Any]:
    actor_id, _ = _actor(current_user)
    try:
        folder = _svc(db).create_smart_folder(vault_id=vault_id, name=name, description=description, color=color, icon_key=icon_key, document_ids=document_ids, actor_user_id=actor_id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return {"id": str(folder.id), "vault_id": folder.vault_id, "name": folder.name}


# ── Retention ─────────────────────────────────────────────────────────────────

@router.put("/vaults/{vault_id}/retention", summary="Update vault retention policy")
async def update_retention_policy(
    vault_id: str = Path(...),
    retention_years: int | None = Body(None),
    retention_days: int | None = Body(None),
    is_permanent: bool = Body(default=False),
    notes: str | None = Body(None),
    current_user: CurrentUser = Depends(_founder_guard),
    db: Session = Depends(db_session_dependency),
) -> dict[str, Any]:
    actor_id, _ = _actor(current_user)
    policy = _svc(db).update_retention_policy(vault_id=vault_id, retention_years=retention_years, retention_days=retention_days, is_permanent=is_permanent, notes=notes, actor_user_id=actor_id)
    return {"id": str(policy.id), "vault_id": policy.vault_id, "retention_years": policy.retention_years, "retention_days": policy.retention_days, "is_permanent": policy.is_permanent, "notes": policy.notes}


# ── Export packages ───────────────────────────────────────────────────────────

@router.post("/packages", status_code=status.HTTP_201_CREATED, summary="Create export package manifest")
async def create_export_package(
    package_name: str = Body(...),
    export_reason: str = Body(...),
    document_ids: list[uuid.UUID] = Body(...),
    current_user: CurrentUser = Depends(_founder_guard),
    db: Session = Depends(db_session_dependency),
) -> dict[str, Any]:
    actor_id, _ = _actor(current_user)
    try:
        pkg = _svc(db).create_export_package(package_name=package_name, export_reason=export_reason, document_ids=document_ids, actor_user_id=actor_id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return {"id": str(pkg.id), "package_name": pkg.package_name, "status": pkg.status, "document_count": pkg.document_count, "total_bytes": pkg.total_bytes}


@router.post("/packages/{package_id}/build", summary="Build ZIP — triggers S3 assembly")
async def build_export_package(
    package_id: uuid.UUID = Path(...),
    current_user: CurrentUser = Depends(_founder_guard),
    db: Session = Depends(db_session_dependency),
) -> dict[str, Any]:
    try:
        return _svc(db).build_export_zip(package_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.get("/packages/{package_id}/download", summary="Get package download URL")
async def get_package_download(
    package_id: uuid.UUID = Path(...),
    current_user: CurrentUser = Depends(_founder_guard),
    db: Session = Depends(db_session_dependency),
) -> dict[str, Any]:
    from sqlalchemy import select as sa_select

    from core_app.models.document_vault import ExportPackage
    pkg = db.execute(sa_select(ExportPackage).where(ExportPackage.id == package_id)).scalar_one_or_none()
    if not pkg:
        raise HTTPException(status_code=404, detail="Package not found.")
    if pkg.status != "ready" or not pkg.s3_key:
        raise HTTPException(status_code=409, detail=f"Package not ready. Status: {pkg.status}")
    import boto3
    s3 = boto3.client("s3")
    url = s3.generate_presigned_url("get_object", Params={"Bucket": pkg.s3_bucket, "Key": pkg.s3_key}, ExpiresIn=86400)
    return {"package_id": str(package_id), "presigned_url": url, "expires_in_seconds": 86400}


# ── Legacy search compat ──────────────────────────────────────────────────────

@router.post("/search", summary="Full-text search (legacy compat)")
async def search_vault(
    query: str = Body(default=""),
    filters: dict[str, Any] | None = Body(default=None),
    limit: int = Body(default=50),
    current_user: CurrentUser = Depends(_founder_guard),
    db: Session = Depends(db_session_dependency),
) -> dict[str, Any]:
    results = _svc(db).search_documents(query=query, filters=filters, limit=limit)
    return {"status": "success", "count": len(results), "data": results}
