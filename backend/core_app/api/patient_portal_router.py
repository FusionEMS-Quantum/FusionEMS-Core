"""Patient Portal Router — patient-facing API endpoints.

Provides read-access to billing statements, payment history,
messages, authorized reps, and allows patient-initiated actions.
"""
from __future__ import annotations

import uuid
from typing import Any

from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session

from core_app.api.dependencies import db_session_dependency, get_current_user
from core_app.schemas.auth import CurrentUser
from core_app.services.domination_service import DominationService
from core_app.services.event_publisher import get_event_publisher

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
