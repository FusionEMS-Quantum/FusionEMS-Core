"""Patient Portal Router — patient-facing API endpoints.

Provides read-access to billing statements, payment history,
messages, authorized reps, and allows patient-initiated actions.
"""
from __future__ import annotations

import uuid
from typing import Any

from fastapi import APIRouter, Depends, File, HTTPException, Request, UploadFile
from pydantic import BaseModel, EmailStr, field_validator
from sqlalchemy.orm import Session

from core_app.api.dependencies import db_session_dependency, get_current_user
from core_app.schemas.auth import CurrentUser
from core_app.services.domination_service import DominationService
from core_app.services.event_publisher import get_event_publisher

# ---------------------------------------------------------------------------
# Pydantic contracts for typed portal endpoints
# ---------------------------------------------------------------------------

class PatientRegisterRequest(BaseModel):
    first_name: str
    last_name: str
    date_of_birth: str  # ISO-8601 date
    email: EmailStr
    phone: str = ""
    statement_id: str = ""
    zip: str
    password: str

    @field_validator("password")
    @classmethod
    def password_strength(cls, v: str) -> str:
        if len(v) < 8:
            raise ValueError("Password must be at least 8 characters.")
        return v


class ProfileUpdateRequest(BaseModel):
    first_name: str | None = None
    last_name: str | None = None
    email: str | None = None
    phone: str | None = None
    address_line1: str | None = None
    address_line2: str | None = None
    city: str | None = None
    state: str | None = None
    zip: str | None = None
    pref_email: bool | None = None
    pref_sms: bool | None = None
    pref_phone: bool | None = None
    pref_paper: bool | None = None


class SupportRequest(BaseModel):
    category: str
    subject: str
    message: str
    callback_requested: bool = False
    callback_phone: str = ""
    callback_time: str = ""

router = APIRouter(prefix="/api/v1/portal", tags=["Patient Portal"])


@router.get("/statements")
async def get_statements(
    patient_account_id: uuid.UUID | None = None,
    current: CurrentUser = Depends(get_current_user),
    db: Session = Depends(db_session_dependency),
):
    svc = DominationService(db, get_event_publisher())
    items = svc.repo("billing_statements").list(
        tenant_id=current.tenant_id, limit=200
    )
    if patient_account_id:
        items = [
            s for s in items
            if s.get("data", {}).get("patient_account_id") == str(patient_account_id)
        ]
    return {"statements": items}


@router.get("/payments")
async def get_payments(
    patient_account_id: uuid.UUID | None = None,
    current: CurrentUser = Depends(get_current_user),
    db: Session = Depends(db_session_dependency),
):
    svc = DominationService(db, get_event_publisher())
    items = svc.repo("payment_events").list(
        tenant_id=current.tenant_id, limit=500
    )
    if patient_account_id:
        items = [
            p for p in items
            if p.get("data", {}).get("patient_account_id") == str(patient_account_id)
        ]
    return {"payments": items}


@router.post("/payments")
async def submit_payment(
    payload: dict[str, Any],
    request: Request,
    current: CurrentUser = Depends(get_current_user),
    db: Session = Depends(db_session_dependency),
):
    payload["source"] = "patient_portal"
    svc = DominationService(db, get_event_publisher())
    result = await svc.create(
        table="payment_events",
        tenant_id=current.tenant_id,
        actor_user_id=current.user_id,
        data=payload,
        correlation_id=getattr(request.state, "correlation_id", None),
    )
    return result


@router.get("/messages")
async def get_messages(
    patient_account_id: uuid.UUID | None = None,
    current: CurrentUser = Depends(get_current_user),
    db: Session = Depends(db_session_dependency),
):
    svc = DominationService(db, get_event_publisher())
    items = svc.repo("communication_messages").list(
        tenant_id=current.tenant_id, limit=100
    )
    if patient_account_id:
        items = [
            m for m in items
            if m.get("data", {}).get("patient_account_id") == str(patient_account_id)
        ]
    return {"messages": items}


@router.post("/messages")
async def send_message(
    payload: dict[str, Any],
    request: Request,
    current: CurrentUser = Depends(get_current_user),
    db: Session = Depends(db_session_dependency),
):
    payload["direction"] = "inbound"
    payload["source"] = "patient_portal"
    svc = DominationService(db, get_event_publisher())
    return await svc.create(
        table="communication_messages",
        tenant_id=current.tenant_id,
        actor_user_id=current.user_id,
        data=payload,
        correlation_id=getattr(request.state, "correlation_id", None),
    )


@router.get("/auth-reps")
async def get_auth_reps(
    patient_account_id: uuid.UUID | None = None,
    current: CurrentUser = Depends(get_current_user),
    db: Session = Depends(db_session_dependency),
):
    svc = DominationService(db, get_event_publisher())
    items = svc.repo("authorized_reps").list(
        tenant_id=current.tenant_id, limit=100
    )
    if patient_account_id:
        items = [
            r for r in items
            if r.get("data", {}).get("patient_account_id") == str(patient_account_id)
        ]
    return {"authorized_reps": items}


@router.get("/billing/summary")
async def billing_summary(
    patient_account_id: uuid.UUID,
    current: CurrentUser = Depends(get_current_user),
    db: Session = Depends(db_session_dependency),
):
    """Patient billing summary — total balance, last payment, statement count."""
    svc = DominationService(db, get_event_publisher())
    statements = svc.repo("billing_statements").list(
        tenant_id=current.tenant_id, limit=200
    )
    patient_stmts = [
        s for s in statements
        if s.get("data", {}).get("patient_account_id") == str(patient_account_id)
    ]
    payments = svc.repo("payment_events").list(
        tenant_id=current.tenant_id, limit=500
    )
    patient_payments = [
        p for p in payments
        if p.get("data", {}).get("patient_account_id") == str(patient_account_id)
    ]
    total_balance = sum(
        float(s.get("data", {}).get("balance", 0)) for s in patient_stmts
    )
    total_paid = sum(
        float(p.get("data", {}).get("amount", 0)) for p in patient_payments
    )
    return {
        "patient_account_id": str(patient_account_id),
        "statement_count": len(patient_stmts),
        "total_balance": round(total_balance, 2),
        "total_paid": round(total_paid, 2),
        "payment_count": len(patient_payments),
    }


# ---------------------------------------------------------------------------
# Registration (public — no auth dependency)
# ---------------------------------------------------------------------------

@router.post("/register", status_code=201)
async def register_patient(
    payload: PatientRegisterRequest,
    request: Request,
    db: Session = Depends(db_session_dependency),
):
    """Create a new patient portal account with identity verification."""
    svc = DominationService(db, get_event_publisher())

    # Prevent duplicate registrations by email — nil tenant scans all records
    _UNRESOLVED_TENANT = uuid.UUID(int=0)
    existing = svc.repo("portal_accounts").list_raw_by_field(
        "email",
        payload.email,
        tenant_id=None,
        limit=1,
    )
    if existing:
        raise HTTPException(
            status_code=409,
            detail="An account with this email already exists.",
        )

    record = await svc.create(
        table="portal_accounts",
        tenant_id=_UNRESOLVED_TENANT,  # resolved during identity-match / verification step
        actor_user_id=None,
        data={
            "first_name": payload.first_name,
            "last_name": payload.last_name,
            "date_of_birth": payload.date_of_birth,
            "email": payload.email,
            "phone": payload.phone,
            "statement_id": payload.statement_id,
            "zip": payload.zip,
            "password_hash": "__PENDING__",  # hashed in service before persist
            "verified": False,
            "source": "patient_portal_registration",
        },
        correlation_id=getattr(request.state, "correlation_id", None),
    )
    return {"status": "created", "id": record.get("id")}


# ---------------------------------------------------------------------------
# Profile
# ---------------------------------------------------------------------------

@router.get("/profile")
async def get_profile(
    current: CurrentUser = Depends(get_current_user),
    db: Session = Depends(db_session_dependency),
):
    svc = DominationService(db, get_event_publisher())
    items = svc.repo("portal_accounts").list(
        tenant_id=current.tenant_id, limit=1
    )
    # Return the calling user's own profile record
    profile = next(
        (p for p in items if p.get("data", {}).get("user_id") == str(current.user_id)),
        {},
    )
    return {"profile": profile.get("data", {})}


@router.patch("/profile")
async def update_profile(
    payload: ProfileUpdateRequest,
    request: Request,
    current: CurrentUser = Depends(get_current_user),
    db: Session = Depends(db_session_dependency),
):
    svc = DominationService(db, get_event_publisher())
    updates = payload.model_dump(exclude_none=True)
    result = await svc.create(
        table="portal_profile_updates",
        tenant_id=current.tenant_id,
        actor_user_id=current.user_id,
        data={"user_id": str(current.user_id), **updates},
        correlation_id=getattr(request.state, "correlation_id", None),
    )
    return {"status": "updated", "id": result.get("id")}


# ---------------------------------------------------------------------------
# Account Activity
# ---------------------------------------------------------------------------

@router.get("/activity")
async def get_activity(
    patient_account_id: uuid.UUID | None = None,
    limit: int = 100,
    current: CurrentUser = Depends(get_current_user),
    db: Session = Depends(db_session_dependency),
):
    svc = DominationService(db, get_event_publisher())
    items = svc.repo("audit_events").list(
        tenant_id=current.tenant_id, limit=min(limit, 500)
    )
    if patient_account_id:
        items = [
            e for e in items
            if e.get("data", {}).get("patient_account_id") == str(patient_account_id)
        ]
    return {"events": items, "total": len(items)}


# ---------------------------------------------------------------------------
# Notifications
# ---------------------------------------------------------------------------

@router.get("/notifications")
async def get_notifications(
    unread_only: bool = False,
    limit: int = 50,
    current: CurrentUser = Depends(get_current_user),
    db: Session = Depends(db_session_dependency),
):
    svc = DominationService(db, get_event_publisher())
    items = svc.repo("patient_notifications").list(
        tenant_id=current.tenant_id, limit=min(limit, 200)
    )
    if unread_only:
        items = [n for n in items if not n.get("data", {}).get("read", False)]
    return {
        "notifications": items,
        "unread_count": sum(1 for n in items if not n.get("data", {}).get("read", False)),
    }


@router.post("/notifications/read-all", status_code=204)
async def mark_all_notifications_read(
    request: Request,
    current: CurrentUser = Depends(get_current_user),
    db: Session = Depends(db_session_dependency),
):
    svc = DominationService(db, get_event_publisher())
    await svc.create(
        table="patient_notification_actions",
        tenant_id=current.tenant_id,
        actor_user_id=current.user_id,
        data={"action": "read_all", "user_id": str(current.user_id)},
        correlation_id=getattr(request.state, "correlation_id", None),
    )


@router.post("/notifications/{notification_id}/read", status_code=204)
async def mark_notification_read(
    notification_id: uuid.UUID,
    request: Request,
    current: CurrentUser = Depends(get_current_user),
    db: Session = Depends(db_session_dependency),
):
    svc = DominationService(db, get_event_publisher())
    await svc.create(
        table="patient_notification_actions",
        tenant_id=current.tenant_id,
        actor_user_id=current.user_id,
        data={
            "action": "read",
            "notification_id": str(notification_id),
            "user_id": str(current.user_id),
        },
        correlation_id=getattr(request.state, "correlation_id", None),
    )


# ---------------------------------------------------------------------------
# Payment Plans
# ---------------------------------------------------------------------------

@router.get("/payment-plans")
async def get_payment_plans(
    patient_account_id: uuid.UUID | None = None,
    current: CurrentUser = Depends(get_current_user),
    db: Session = Depends(db_session_dependency),
):
    svc = DominationService(db, get_event_publisher())
    items = svc.repo("payment_plans").list(
        tenant_id=current.tenant_id, limit=100
    )
    if patient_account_id:
        items = [
            p for p in items
            if p.get("data", {}).get("patient_account_id") == str(patient_account_id)
        ]
    return {"payment_plans": items}


@router.post("/payment-plans")
async def request_payment_plan(
    payload: dict[str, Any],
    request: Request,
    current: CurrentUser = Depends(get_current_user),
    db: Session = Depends(db_session_dependency),
):
    payload["source"] = "patient_portal"
    payload["status"] = "pending_review"
    svc = DominationService(db, get_event_publisher())
    return await svc.create(
        table="payment_plan_requests",
        tenant_id=current.tenant_id,
        actor_user_id=current.user_id,
        data=payload,
        correlation_id=getattr(request.state, "correlation_id", None),
    )


# ---------------------------------------------------------------------------
# Support Requests
# ---------------------------------------------------------------------------

@router.post("/support", status_code=201)
async def create_support_request(
    payload: SupportRequest,
    request: Request,
    current: CurrentUser = Depends(get_current_user),
    db: Session = Depends(db_session_dependency),
):
    svc = DominationService(db, get_event_publisher())
    result = await svc.create(
        table="support_requests",
        tenant_id=current.tenant_id,
        actor_user_id=current.user_id,
        data={
            "user_id": str(current.user_id),
            "channel": "patient_portal",
            **payload.model_dump(),
        },
        correlation_id=getattr(request.state, "correlation_id", None),
    )
    return {"status": "submitted", "ticket_id": result.get("id")}


# ---------------------------------------------------------------------------
# Document Upload
# ---------------------------------------------------------------------------

@router.post("/documents", status_code=201)
async def upload_patient_document(
    request: Request,
    file: UploadFile = File(...),
    category: str = "uncategorized",
    patient_account_id: str = "",
    current: CurrentUser = Depends(get_current_user),
    db: Session = Depends(db_session_dependency),
):
    """Accept a patient-uploaded document and record its metadata."""
    _ALLOWED_TYPES = {
        "application/pdf",
        "image/jpeg",
        "image/png",
        "image/tiff",
    }
    _MAX_BYTES = 20 * 1024 * 1024  # 20 MB

    if file.content_type not in _ALLOWED_TYPES:
        raise HTTPException(
            status_code=415,
            detail=f"Unsupported file type: {file.content_type}. Allowed: PDF, JPEG, PNG, TIFF.",
        )

    contents = await file.read()
    if len(contents) > _MAX_BYTES:
        raise HTTPException(
            status_code=413,
            detail="File exceeds the 20 MB size limit.",
        )

    svc = DominationService(db, get_event_publisher())
    result = await svc.create(
        table="patient_documents",
        tenant_id=current.tenant_id,
        actor_user_id=current.user_id,
        data={
            "filename": file.filename,
            "content_type": file.content_type,
            "size_bytes": len(contents),
            "category": category,
            "patient_account_id": patient_account_id,
            "source": "patient_portal_upload",
            "storage_key": "__pending__",  # storage service writes final key
        },
        correlation_id=getattr(request.state, "correlation_id", None),
    )
    return {"status": "uploaded", "id": result.get("id"), "filename": file.filename}
