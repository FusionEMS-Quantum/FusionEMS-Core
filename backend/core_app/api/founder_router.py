from __future__ import annotations

import json
import uuid
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from core_app.api.dependencies import (
    db_session_dependency,
    get_current_user,
    require_founder_only_audited,
    require_role,
)
from core_app.core.config import get_settings
from core_app.schemas.auth import CurrentUser
from core_app.services.clinical_open_data_service import founder_clinical_snapshot
from core_app.services.domination_service import DominationService
from core_app.services.event_publisher import get_event_publisher

router = APIRouter(
    prefix="/api/v1/founder",
    tags=["Founder"],
    dependencies=[Depends(require_founder_only_audited())],
)


class FounderExpenseCreateRequest(BaseModel):
    vendor: str = Field(min_length=1, max_length=120)
    category: str = Field(min_length=1, max_length=80)
    amount_cents: int = Field(gt=0, le=5_000_000_00)
    description: str = Field(default="", max_length=500)
    expense_date: str | None = None
    receipt_attached: bool = False


class FounderInvoiceLineItemRequest(BaseModel):
    desc: str = Field(min_length=1, max_length=200)
    amount_cents: int = Field(ge=0, le=1_000_000_00)


class FounderInvoiceCreateRequest(BaseModel):
    client: str = Field(min_length=1, max_length=180)
    invoice_date: str
    due_date: str
    description: str = Field(default="", max_length=500)
    line_items: list[FounderInvoiceLineItemRequest] = Field(default_factory=list)


class FounderInvoiceReminderRequest(BaseModel):
    channel: str = Field(default="email", max_length=32)


class FounderInvoiceSettingsRequest(BaseModel):
    company: str = Field(min_length=1, max_length=180)
    address: str = Field(min_length=1, max_length=250)
    terms: str = Field(min_length=1, max_length=120)
    late_fee: str = Field(alias="lateFee", min_length=1, max_length=180)

    model_config = {"populate_by_name": True}


def _parse_ts(value: str) -> float:
    """Parse an ISO-8601 timestamp string to a UTC epoch float; returns 0.0 on parse failure."""
    try:
        return datetime.fromisoformat(value).timestamp()
    except (ValueError, TypeError):
        return 0.0


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[3]


def _load_artifact_json(relative_path: str) -> dict[str, Any] | None:
    artifact_path = _repo_root() / relative_path
    if not artifact_path.exists() or not artifact_path.is_file():
        return None
    try:
        return json.loads(artifact_path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return None


def _expense_entries_for_tenant(
    svc: DominationService,
    tenant_id: uuid.UUID,
    *,
    limit: int,
) -> list[dict[str, Any]]:
    rows = svc.repo("ledger_entries").list(tenant_id=tenant_id, limit=max(limit, 50), offset=0)
    entries = [
        r
        for r in rows
        if (r.get("data") or {}).get("entry_type") == "founder.expense"
    ]
    entries.sort(
        key=lambda row: (row.get("data") or {}).get("expense_date") or row.get("created_at") or "",
        reverse=True,
    )
    return entries[:limit]


def _default_invoice_settings() -> dict[str, str]:
    return {
        "company": "FusionEMS Quantum LLC",
        "address": "123 Founder St, Austin, TX 78701",
        "terms": "Net 30",
        "lateFee": "1.5% per month after due date",
    }


def _find_invoice_settings_record(
    svc: DominationService,
    tenant_id: uuid.UUID,
) -> dict[str, Any] | None:
    configs = svc.repo("tenant_billing_config").list(tenant_id=tenant_id, limit=200, offset=0)
    for cfg in configs:
        data = cfg.get("data") or {}
        if data.get("key") == "founder_invoice_settings":
            return cfg
    return None


@router.get("/business/expense-ledger")
async def business_expense_ledger(
    limit: int = 250,
    current: CurrentUser = Depends(get_current_user),
    db: Session = Depends(db_session_dependency),
):
    require_role(current, ["founder"])
    svc = DominationService(db, get_event_publisher())

    safe_limit = min(max(limit, 1), 500)
    rows = _expense_entries_for_tenant(svc, current.tenant_id, limit=safe_limit)

    now = datetime.now(UTC)
    month_prefix = now.strftime("%Y-%m")

    total_cents = 0
    month_total_cents = 0
    receipt_missing = 0
    by_category: dict[str, int] = {}

    entries: list[dict[str, Any]] = []
    for row in rows:
        data = row.get("data") or {}
        amount_cents = int(data.get("amount_cents") or 0)
        category = str(data.get("category") or "Uncategorized")
        expense_date = str(data.get("expense_date") or row.get("created_at") or "")
        receipt_attached = bool(data.get("receipt_attached", False))

        total_cents += amount_cents
        if expense_date.startswith(month_prefix):
            month_total_cents += amount_cents
        if not receipt_attached:
            receipt_missing += 1
        by_category[category] = by_category.get(category, 0) + amount_cents

        entries.append(
            {
                "id": str(row.get("id")),
                "expense_date": expense_date,
                "vendor": str(data.get("vendor") or "Unknown"),
                "category": category,
                "amount_cents": amount_cents,
                "description": str(data.get("description") or ""),
                "receipt_attached": receipt_attached,
                "created_at": row.get("created_at"),
            }
        )

    category_rows = sorted(by_category.items(), key=lambda item: item[1], reverse=True)
    category_breakdown = [
        {
            "label": label,
            "amount_cents": amount,
            "pct": round((amount / total_cents * 100), 2) if total_cents > 0 else 0,
        }
        for label, amount in category_rows
    ]

    return {
        "summary": {
            "month_total_cents": month_total_cents,
            "total_cents": total_cents,
            "entry_count": len(entries),
            "receipt_missing_count": receipt_missing,
            "quickbooks_sync_status": "not_configured",
            "as_of": now.isoformat(),
        },
        "category_breakdown": category_breakdown,
        "entries": entries,
    }


@router.post("/business/expense-ledger/entries")
async def create_business_expense_entry(
    payload: FounderExpenseCreateRequest,
    request: Request,
    current: CurrentUser = Depends(get_current_user),
    db: Session = Depends(db_session_dependency),
):
    require_role(current, ["founder"])
    svc = DominationService(db, get_event_publisher())

    expense_date = payload.expense_date or datetime.now(UTC).date().isoformat()
    created = await svc.create(
        table="ledger_entries",
        tenant_id=current.tenant_id,
        actor_user_id=current.user_id,
        data={
            "entry_type": "founder.expense",
            "expense_date": expense_date,
            "vendor": payload.vendor,
            "category": payload.category,
            "amount_cents": payload.amount_cents,
            "description": payload.description,
            "receipt_attached": payload.receipt_attached,
            "created_by": str(current.user_id),
        },
        correlation_id=getattr(request.state, "correlation_id", None),
    )
    return {
        "id": str(created["id"]),
        "data": created.get("data", {}),
        "created_at": created.get("created_at"),
    }


@router.get("/business/invoices")
async def business_invoices(
    limit: int = 250,
    current: CurrentUser = Depends(get_current_user),
    db: Session = Depends(db_session_dependency),
):
    svc = DominationService(db, get_event_publisher())
    safe_limit = min(max(limit, 1), 500)

    rows = svc.repo("invoices").list(tenant_id=current.tenant_id, limit=safe_limit, offset=0)
    invoices: list[dict[str, Any]] = []

    now = datetime.now(UTC)
    month_prefix = now.strftime("%Y-%m")
    total_invoiced_cents = 0
    total_paid_cents = 0
    invoices_this_month = 0
    paid_count = 0
    outstanding_count = 0

    for row in rows:
        data = row.get("data") or {}
        total_cents = int(data.get("total_cents") or 0)
        paid_cents = int(data.get("paid_cents") or 0)
        status = str(data.get("status") or "outstanding").lower()
        invoice_date = str(data.get("invoice_date") or row.get("created_at") or "")

        total_invoiced_cents += total_cents
        total_paid_cents += paid_cents
        if invoice_date.startswith(month_prefix):
            invoices_this_month += 1
        if status == "paid":
            paid_count += 1
        elif status in {"outstanding", "overdue"}:
            outstanding_count += 1

        invoices.append(
            {
                "id": str(row.get("id")),
                "invoice_number": str(data.get("invoice_number") or ""),
                "client": str(data.get("client") or "Unknown"),
                "invoice_date": invoice_date,
                "due_date": str(data.get("due_date") or ""),
                "description": str(data.get("description") or ""),
                "line_items": data.get("line_items") or [],
                "total_cents": total_cents,
                "paid_cents": paid_cents,
                "status": status,
                "reminder_count": int(data.get("reminder_count") or 0),
                "last_reminder_at": data.get("last_reminder_at"),
                "created_at": row.get("created_at"),
                "updated_at": row.get("updated_at"),
            }
        )

    return {
        "summary": {
            "invoices_this_month": invoices_this_month,
            "total_invoiced_cents": total_invoiced_cents,
            "total_paid_cents": total_paid_cents,
            "paid_count": paid_count,
            "outstanding_count": outstanding_count,
            "as_of": now.isoformat(),
        },
        "invoices": invoices,
    }


@router.post("/business/invoices")
async def create_business_invoice(
    payload: FounderInvoiceCreateRequest,
    request: Request,
    current: CurrentUser = Depends(get_current_user),
    db: Session = Depends(db_session_dependency),
):
    svc = DominationService(db, get_event_publisher())

    total_cents = sum(int(item.amount_cents) for item in payload.line_items)
    invoice_number = f"INV-{datetime.now(UTC).strftime('%Y%m%d')}-{str(uuid.uuid4())[:8].upper()}"
    created = await svc.create(
        table="invoices",
        tenant_id=current.tenant_id,
        actor_user_id=current.user_id,
        data={
            "invoice_number": invoice_number,
            "client": payload.client,
            "invoice_date": payload.invoice_date,
            "due_date": payload.due_date,
            "description": payload.description,
            "line_items": [item.model_dump() for item in payload.line_items],
            "total_cents": total_cents,
            "paid_cents": 0,
            "status": "outstanding",
            "reminder_count": 0,
            "created_by": str(current.user_id),
        },
        correlation_id=getattr(request.state, "correlation_id", None),
    )

    return {
        "id": str(created.get("id")),
        "invoice_number": invoice_number,
        "total_cents": total_cents,
        "status": "outstanding",
        "created_at": created.get("created_at"),
    }


@router.post("/business/invoices/{invoice_id}/send-reminder")
async def send_invoice_reminder(
    invoice_id: uuid.UUID,
    payload: FounderInvoiceReminderRequest,
    request: Request,
    current: CurrentUser = Depends(get_current_user),
    db: Session = Depends(db_session_dependency),
):
    svc = DominationService(db, get_event_publisher())
    invoice = svc.repo("invoices").get(tenant_id=current.tenant_id, record_id=invoice_id)
    if not invoice:
        return {"error": "invoice_not_found"}

    data = dict(invoice.get("data") or {})
    data["reminder_count"] = int(data.get("reminder_count") or 0) + 1
    data["last_reminder_at"] = datetime.now(UTC).isoformat()
    data["last_reminder_channel"] = payload.channel
    if str(data.get("status") or "").lower() == "draft":
        data["status"] = "outstanding"

    updated = await svc.update(
        table="invoices",
        tenant_id=current.tenant_id,
        actor_user_id=current.user_id,
        record_id=invoice_id,
        expected_version=invoice.get("version", 1),
        patch=data,
        correlation_id=getattr(request.state, "correlation_id", None),
    )
    if not updated:
        return {"error": "invoice_update_conflict"}

    return {
        "status": "sent",
        "invoice_id": str(invoice_id),
        "channel": payload.channel,
        "reminder_count": data["reminder_count"],
        "last_reminder_at": data["last_reminder_at"],
    }


@router.post("/business/invoices/{invoice_id}/mark-paid")
async def mark_invoice_paid(
    invoice_id: uuid.UUID,
    request: Request,
    current: CurrentUser = Depends(get_current_user),
    db: Session = Depends(db_session_dependency),
):
    svc = DominationService(db, get_event_publisher())
    invoice = svc.repo("invoices").get(tenant_id=current.tenant_id, record_id=invoice_id)
    if not invoice:
        return {"error": "invoice_not_found"}

    data = dict(invoice.get("data") or {})
    total_cents = int(data.get("total_cents") or 0)
    data["status"] = "paid"
    data["paid_cents"] = total_cents
    data["paid_at"] = datetime.now(UTC).isoformat()

    updated = await svc.update(
        table="invoices",
        tenant_id=current.tenant_id,
        actor_user_id=current.user_id,
        record_id=invoice_id,
        expected_version=invoice.get("version", 1),
        patch=data,
        correlation_id=getattr(request.state, "correlation_id", None),
    )
    if not updated:
        return {"error": "invoice_update_conflict"}

    return {
        "status": "paid",
        "invoice_id": str(invoice_id),
        "paid_cents": total_cents,
        "paid_at": data["paid_at"],
    }


@router.get("/business/invoice-settings")
async def get_business_invoice_settings(
    current: CurrentUser = Depends(get_current_user),
    db: Session = Depends(db_session_dependency),
):
    svc = DominationService(db, get_event_publisher())
    existing = _find_invoice_settings_record(svc, current.tenant_id)
    if not existing:
        return _default_invoice_settings()

    data = existing.get("data") or {}
    settings = data.get("settings") or {}
    merged = {**_default_invoice_settings(), **settings}
    return merged


@router.put("/business/invoice-settings")
async def put_business_invoice_settings(
    payload: FounderInvoiceSettingsRequest,
    request: Request,
    current: CurrentUser = Depends(get_current_user),
    db: Session = Depends(db_session_dependency),
):
    svc = DominationService(db, get_event_publisher())
    settings_payload = payload.model_dump(by_alias=True)
    existing = _find_invoice_settings_record(svc, current.tenant_id)

    if existing:
        updated = await svc.update(
            table="tenant_billing_config",
            tenant_id=current.tenant_id,
            actor_user_id=current.user_id,
            record_id=uuid.UUID(str(existing["id"])),
            expected_version=existing.get("version", 1),
            patch={
                "key": "founder_invoice_settings",
                "settings": settings_payload,
                "updated_by": str(current.user_id),
            },
            correlation_id=getattr(request.state, "correlation_id", None),
        )
        if not updated:
            return {"error": "settings_update_conflict"}
        return {"updated": True, "settings": settings_payload}

    created = await svc.create(
        table="tenant_billing_config",
        tenant_id=current.tenant_id,
        actor_user_id=current.user_id,
        data={
            "key": "founder_invoice_settings",
            "settings": settings_payload,
            "created_by": str(current.user_id),
        },
        correlation_id=getattr(request.state, "correlation_id", None),
    )
    return {"updated": True, "settings": settings_payload, "id": str(created["id"])}


@router.get("/tenants")
async def tenants(
    request: Request,
    current: CurrentUser = Depends(get_current_user),
    db: Session = Depends(db_session_dependency),
):
    svc = DominationService(db, get_event_publisher())
    scores = svc.repo("governance_scores").list(
        tenant_id=current.tenant_id, limit=50, offset=0
    )
    return [{"tenant_id": str(current.tenant_id), "governance_scores": scores}]


@router.get(
    "/tenants/{tenant_id}/billing",
)
async def tenant_billing(
    tenant_id: uuid.UUID,
    request: Request,
    current: CurrentUser = Depends(get_current_user),
    db: Session = Depends(db_session_dependency),
):
    svc = DominationService(db, get_event_publisher())
    return {
        "billing_jobs": svc.repo("billing_jobs").list(
            tenant_id=current.tenant_id, limit=200, offset=0
        ),
        "claims": svc.repo("claims").list(
            tenant_id=current.tenant_id, limit=200, offset=0
        ),
    }


@router.get(
    "/tenants/{tenant_id}/compliance",
    dependencies=[Depends(require_role("founder"))],
)
async def tenant_compliance(
    tenant_id: uuid.UUID,
    request: Request,
    current: CurrentUser = Depends(get_current_user),
    db: Session = Depends(db_session_dependency),
):
    svc = DominationService(db, get_event_publisher())
    return {
        "nemsis": svc.repo("nemsis_validation_results").list(
            tenant_id=current.tenant_id, limit=50, offset=0
        ),
        "neris": svc.repo("neris_validation_results").list(
            tenant_id=current.tenant_id, limit=50, offset=0
        ),
        "scores": svc.repo("governance_scores").list(
            tenant_id=current.tenant_id, limit=50, offset=0
        ),
    }


@router.post(
    "/support/impersonate/start", dependencies=[Depends(require_role("founder"))]
)
async def impersonate(
    payload: dict[str, Any],
    request: Request,
    current: CurrentUser = Depends(get_current_user),
    db: Session = Depends(db_session_dependency),
):
    svc = DominationService(db, get_event_publisher())
    return await svc.create(
        table="support_sessions",
        tenant_id=current.tenant_id,
        actor_user_id=current.user_id,
        data={"type": "impersonate", **payload},
        correlation_id=getattr(request.state, "correlation_id", None),
    )


@router.post("/support/session/start", dependencies=[Depends(require_role("founder"))])
async def support_session(
    payload: dict[str, Any],
    request: Request,
    current: CurrentUser = Depends(get_current_user),
    db: Session = Depends(db_session_dependency),
):
    svc = DominationService(db, get_event_publisher())
    return await svc.create(
        table="support_sessions",
        tenant_id=current.tenant_id,
        actor_user_id=current.user_id,
        data={"type": "remote_support", **payload},
        correlation_id=getattr(request.state, "correlation_id", None),
    )


@router.post("/ai/chat", dependencies=[Depends(require_role("founder"))])
async def ai_chat(
    payload: dict[str, Any],
    request: Request,
    current: CurrentUser = Depends(get_current_user),
    db: Session = Depends(db_session_dependency),
):
    svc = DominationService(db, get_event_publisher())
    run = {
        "prompt": payload.get("message"),
        "model": payload.get("model", "gpt-4.1"),
        "status": "queued",
    }
    return await svc.create(
        table="ai_runs",
        tenant_id=current.tenant_id,
        actor_user_id=current.user_id,
        data=run,
        correlation_id=getattr(request.state, "correlation_id", None),
    )


@router.post("/docs/generate", dependencies=[Depends(require_role("founder"))])
async def docs(
    payload: dict[str, Any],
    request: Request,
    current: CurrentUser = Depends(get_current_user),
):
    return {
        "status": "accepted",
        "kind": payload.get("kind"),
        "name": payload.get("name"),
    }


@router.get("/dashboard")
async def founder_dashboard(
    current: CurrentUser = Depends(get_current_user),
    db: Session = Depends(db_session_dependency),
):
    require_role(current, ["founder"])
    svc = DominationService(db, get_event_publisher())

    tenants_list = svc.repo("tenants").list(tenant_id=current.tenant_id, limit=10000)
    active_tenants = [
        t for t in tenants_list if t.get("data", {}).get("status") == "active"
    ]

    subscriptions = svc.repo("tenant_subscriptions").list(
        tenant_id=current.tenant_id, limit=10000
    )
    mrr = sum(
        int(s.get("data", {}).get("monthly_amount_cents", 0))
        for s in subscriptions
        if s.get("data", {}).get("status") == "active"
    )

    one_hour_ago = (datetime.now(UTC).timestamp() - 3600)
    system_alerts = svc.repo("system_alerts").list(
        tenant_id=current.tenant_id, limit=10000
    )
    error_count_1h = sum(
        1
        for a in system_alerts
        if a.get("data", {}).get("severity") in ("error", "critical")
        and _parse_ts(a.get("data", {}).get("created_at", "")) >= one_hour_ago
    )

    settings = get_settings()
    integration_state = settings.integration_state_table()
    required_missing = [
        key
        for key, value in integration_state.items()
        if bool(value.get("required")) and not bool(value.get("configured"))
    ]

    return {
        "mrr_cents": mrr,
        "tenant_count": len(active_tenants),
        "error_count_1h": error_count_1h,
        "clinical_datasets": founder_clinical_snapshot(db),
        "integration_readiness": {
            "required_missing": required_missing,
            "required_missing_count": len(required_missing),
            "state": integration_state,
        },
        "as_of": datetime.now(UTC).isoformat(),
    }


@router.get("/webhook-health")
async def webhook_health(
    current: CurrentUser = Depends(get_current_user),
    db: Session = Depends(db_session_dependency),
):
    require_role(current, ["founder"])
    svc = DominationService(db, get_event_publisher())

    health: dict[str, str] = {}
    sources = ["stripe", "lob", "telnyx", "officeally"]

    for source in sources:
        try:
            dead_items = [
                r
                for r in svc.repo("webhook_dlq").list(
                    tenant_id=current.tenant_id, limit=100
                )
                if r.get("data", {}).get("source") == source
                and r.get("data", {}).get("status") == "dead"
            ]
            health[source] = "error" if dead_items else "ok"
        except Exception:
            health[source] = "unknown"

    return {"health": health, "as_of": datetime.now(UTC).isoformat()}


@router.get("/feature-flags")
async def get_feature_flags(
    current: CurrentUser = Depends(get_current_user),
    db: Session = Depends(db_session_dependency),
):
    require_role(current, ["founder"])
    svc = DominationService(db, get_event_publisher())
    tenants_list = svc.repo("tenants").list(tenant_id=current.tenant_id, limit=1)
    flags: dict = {}
    if tenants_list:
        flags = tenants_list[0].get("data", {}).get("feature_flags", {})
    return {"flags": flags}


@router.patch("/feature-flags")
async def update_feature_flags(
    payload: dict[str, Any],
    request: Request,
    current: CurrentUser = Depends(get_current_user),
    db: Session = Depends(db_session_dependency),
):
    require_role(current, ["founder"])
    svc = DominationService(db, get_event_publisher())
    tenants_list = svc.repo("tenants").list(tenant_id=current.tenant_id, limit=1)
    if not tenants_list:
        return {"error": "tenant_not_found"}
    tenant = tenants_list[0]
    current_flags = tenant.get("data", {}).get("feature_flags", {})
    updated_flags = {**current_flags, **payload}
    await svc.update(
        table="tenants",
        tenant_id=current.tenant_id,
        actor_user_id=current.user_id,
        record_id=uuid.UUID(str(tenant["id"])),
        expected_version=tenant.get("version", 1),
        patch={"feature_flags": updated_flags},
        correlation_id=getattr(request.state, "correlation_id", None),
    )
    return {"flags": updated_flags, "updated": True}


@router.get("/aws-cost")
async def aws_cost_summary(
    current: CurrentUser = Depends(get_current_user),
):
    require_role(current, ["founder"])
    try:
        import boto3

        settings = get_settings()
        client = boto3.client("ce", region_name=settings.aws_region or "us-east-1")
        from datetime import date, timedelta

        end = date.today().isoformat()
        start = (date.today() - timedelta(days=30)).isoformat()
        resp = client.get_cost_and_usage(
            TimePeriod={"Start": start, "End": end},
            Granularity="MONTHLY",
            Metrics=["UnblendedCost"],
            GroupBy=[{"Type": "DIMENSION", "Key": "SERVICE"}],
        )
        results = []
        for period in resp.get("ResultsByTime", []):
            for group in period.get("Groups", []):
                results.append(
                    {
                        "service": group["Keys"][0],
                        "amount": float(group["Metrics"]["UnblendedCost"]["Amount"]),
                        "unit": group["Metrics"]["UnblendedCost"]["Unit"],
                    }
                )
        total = sum(r["amount"] for r in results)
        return {
            "period": f"{start} to {end}",
            "total_usd": round(total, 2),
            "by_service": results,
        }
    except Exception as e:
        return {"error": str(e), "message": "AWS Cost Explorer not available"}


@router.get("/operations/multi-agent/status")
async def multi_agent_status(
    current: CurrentUser = Depends(get_current_user),
):
    require_role(current, ["founder"])

    execution_report = _load_artifact_json("artifacts/multi_agent_execution_report.json")
    compliance_manifest = _load_artifact_json("artifacts/compliance-evidence-manifest.json")
    nemsis_report = _load_artifact_json("artifacts/nemsis-ci-report.json")
    neris_report = _load_artifact_json("artifacts/neris-ci-report.json")

    lanes = execution_report.get("lanes", []) if execution_report else []
    failed_lanes = [lane for lane in lanes if lane.get("status") == "failed"]
    warning_lanes = [lane for lane in lanes if lane.get("status") == "warning"]

    return {
        "orchestration": {
            "status": execution_report.get("status", "not_available")
            if execution_report
            else "not_available",
            "mode": execution_report.get("meta", {}).get("mode")
            if execution_report
            else None,
            "generated_at_utc": execution_report.get("meta", {}).get("generated_at_utc")
            if execution_report
            else None,
            "lane_count": len(lanes),
            "failed_lane_count": len(failed_lanes),
            "warning_lane_count": len(warning_lanes),
            "failed_lanes": [
                {
                    "lane_id": lane.get("lane_id"),
                    "agent_label": lane.get("agent_label"),
                    "log_file": lane.get("log_file"),
                }
                for lane in failed_lanes
            ],
        },
        "compliance_program": {
            "status": compliance_manifest.get("status", "not_available")
            if compliance_manifest
            else "not_available",
            "generated_at_utc": compliance_manifest.get("generated_at_utc")
            if compliance_manifest
            else None,
            "missing_count": compliance_manifest.get("missing_count", 0)
            if compliance_manifest
            else None,
        },
        "nemsis": {
            "status": nemsis_report.get("status", "not_available")
            if nemsis_report
            else "not_available",
            "evidence": nemsis_report.get("evidence") if nemsis_report else None,
            "certification_status": nemsis_report.get("certification_status")
            if nemsis_report
            else None,
        },
        "neris": {
            "status": neris_report.get("status", "not_available")
            if neris_report
            else "not_available",
            "evidence": neris_report.get("evidence") if neris_report else None,
            "certification_status": neris_report.get("certification_status")
            if neris_report
            else None,
        },
        "as_of": datetime.now(UTC).isoformat(),
    }


@router.get("/compliance/status")
async def compliance_status(
    current: CurrentUser = Depends(get_current_user),
    db: Session = Depends(db_session_dependency),
):
    require_role(current, ["founder"])
    svc = DominationService(db, get_event_publisher())

    nemsis_jobs = svc.repo("nemsis_export_jobs").list(
        tenant_id=current.tenant_id, limit=1
    )
    nemsis_latest = nemsis_jobs[0] if nemsis_jobs else None

    neris_jobs = svc.repo("neris_export_jobs").list(
        tenant_id=current.tenant_id, limit=1
    )
    neris_latest = neris_jobs[0] if neris_jobs else None

    packs = svc.repo("compliance_packs").list(tenant_id=current.tenant_id, limit=100)
    active_packs = [p for p in packs if (p.get("data") or {}).get("active")]

    return {
        "nemsis": {
            "certified": nemsis_latest is not None,
            "last_export_at": (nemsis_latest or {}).get("created_at"),
            "status": (nemsis_latest or {}).get("data", {}).get("status", "none"),
        },
        "neris": {
            "onboarded": neris_latest is not None,
            "last_export_at": (neris_latest or {}).get("created_at"),
            "status": (neris_latest or {}).get("data", {}).get("status", "none"),
        },
        "compliance_packs": {
            "active_count": len(active_packs),
            "packs": [
                {"id": p.get("id"), "name": (p.get("data") or {}).get("name")}
                for p in active_packs
            ],
        },
        "overall": (
            "partial" if (nemsis_latest or neris_latest or active_packs) else "none"
        ),
    }


@router.get("/contracts")
async def get_contracts():
    return {
        "templates": [
            {
                "id": "msa",
                "name": "Master Service Agreement",
                "desc": "Full platform service agreement with SLA terms.",
                "used": 4,
            },
            {
                "id": "baa",
                "name": "HIPAA Business Associate Agreement",
                "desc": "BAA for all data handling relationships.",
                "used": 4,
            },
            {
                "id": "dpa",
                "name": "Data Processing Addendum",
                "desc": "GDPR/CCPA compliant DPA addendum.",
                "used": 2,
            },
            {
                "id": "renewal",
                "name": "Agency Renewal Agreement",
                "desc": "Simplified renewal for existing clients.",
                "used": 1,
            },
            {
                "id": "pilot",
                "name": "Pilot Program Agreement",
                "desc": "90-day pilot with conversion terms.",
                "used": 0,
            },
            {
                "id": "nda",
                "name": "NDA (Mutual)",
                "desc": "Standard mutual non-disclosure.",
                "used": 3,
            },
        ],
        "active_contracts": [
            {
                "id": "MSA-001",
                "agency": "Agency A",
                "type": "Service Agreement",
                "status": "Executed",
                "statusKey": "ok",
                "signed": "Jan 15, 2024",
                "expiry": "Jan 15, 2025",
            },
            {
                "id": "BAA-001",
                "agency": "Agency A",
                "type": "BAA",
                "status": "Executed",
                "statusKey": "ok",
                "signed": "Jan 15, 2024",
                "expiry": "Jan 15, 2025",
            },
            {
                "id": "MSA-002",
                "agency": "Agency B",
                "type": "Service Agreement",
                "status": "Executed",
                "statusKey": "ok",
                "signed": "Nov 10, 2023",
                "expiry": "Nov 10, 2024",
            },
            {
                "id": "BAA-002",
                "agency": "Agency B",
                "type": "BAA",
                "status": "Executed",
                "statusKey": "ok",
                "signed": "Nov 10, 2023",
                "expiry": "Nov 10, 2024",
            },
            {
                "id": "MSA-003",
                "agency": "Agency C",
                "type": "Service Agreement",
                "status": "Pending",
                "statusKey": "warn",
                "signed": "—",
                "expiry": "—",
            },
            {
                "id": "NDA-001",
                "agency": "Agency D",
                "type": "NDA",
                "status": "Executed",
                "statusKey": "ok",
                "signed": "Dec 5, 2023",
                "expiry": "Dec 5, 2024",
            },
        ],
        "template_vars": [
            "{{agency_name}}",
            "{{start_date}}",
            "{{monthly_fee}}",
            "{{state}}",
        ],
    }


@router.get("/reports")
async def get_reports():
    return {
        "templates": [
            {
                "id": "qa-ems",
                "name": "ePCR QA Audit (NEMSIS v3.5)",
                "desc": "Full protocol audit covering treatments, times, and signatures.",
                "freq": "Weekly",
            },
            {
                "id": "billing-denials",
                "name": "Denial Intelligence",
                "desc": "Payer-level denial reasons, CARC codes, and missing prior auths.",
                "freq": "Daily",
            },
            {
                "id": "fleet-fuel",
                "name": "Fleet Utilization",
                "desc": "Unit hours, dispatch volume, and maintenance cost per mile.",
                "freq": "Monthly",
            },
            {
                "id": "clinical-outcomes",
                "name": "Clinical Outcomes",
                "desc": "CAAS/CAMTS outcome metrics (STEMI, Stroke, Trauma, Airways).",
                "freq": "Monthly",
            },
            {
                "id": "staff-fatigue",
                "name": "Fatigue Matrix",
                "desc": "Time-on-task, late calls, and consecutive shifts without rest.",
                "freq": "Weekly",
            },
        ],
        "recent": [
            {
                "id": "REP-992",
                "name": "Q3 Payer Denials",
                "type": "Billing",
                "date": "Oct 1, 2024",
                "status": "Ready",
                "statusKey": "ok",
            },
            {
                "id": "REP-991",
                "name": "Sept Clinical Outcomes",
                "type": "Clinical",
                "date": "Oct 1, 2024",
                "status": "Ready",
                "statusKey": "ok",
            },
            {
                "id": "REP-990",
                "name": "Weekly QA Audit",
                "type": "Compliance",
                "date": "Sep 28, 2024",
                "status": "Ready",
                "statusKey": "ok",
            },
            {
                "id": "REP-989",
                "name": "Fatigue Matrix - Week 38",
                "type": "Operations",
                "date": "Sep 25, 2024",
                "status": "Review",
                "statusKey": "warn",
            },
            {
                "id": "REP-988",
                "name": "Fleet Util v2.1",
                "type": "Fleet",
                "date": "Sep 24, 2024",
                "status": "Failed",
                "statusKey": "error",
            },
        ],
        "scheduled": [
            {
                "name": "Daily Denial Sync",
                "format": "CSV to S3",
                "time": "02:00 UTC",
                "targets": "Billing Team",
            },
            {
                "name": "Weekly QA Flag Report",
                "format": "PDF Email",
                "time": "Mon 06:00 EST",
                "targets": "Medical Dir.",
            },
            {
                "name": "Monthly Board Deck",
                "format": "PDF Email",
                "time": "1st of Month",
                "targets": "Founder",
            },
        ],
        "archive": [
            {"year": "2024", "count": 142, "size": "1.2 GB"},
            {"year": "2023", "count": 418, "size": "3.8 GB"},
            {"year": "2022", "count": 210, "size": "1.9 GB"},
        ],
    }


@router.get("/executive-summary")
async def founder_executive_summary(
    current: CurrentUser = Depends(get_current_user),
    db: Session = Depends(db_session_dependency),
) -> dict[str, Any]:
    """Founder executive summary for the main dashboard tile."""
    svc = DominationService(db, get_event_publisher())

    subscriptions = svc.repo("tenant_subscriptions").list(
        tenant_id=current.tenant_id, limit=10000
    )
    mrr_cents = sum(
        int(s.get("data", {}).get("monthly_amount_cents", 0))
        for s in subscriptions
        if s.get("data", {}).get("status") == "active"
    )

    tenants_list = svc.repo("tenants").list(tenant_id=current.tenant_id, limit=10000)
    active_clients = sum(
        1 for t in tenants_list
        if t.get("data", {}).get("status") == "active"
    )

    system_alerts = svc.repo("system_alerts").list(tenant_id=current.tenant_id, limit=500)
    one_hour_ago = datetime.now(UTC).timestamp() - 3600
    recent_errors = sum(
        1 for a in system_alerts
        if a.get("data", {}).get("severity") in ("error", "critical")
        and _parse_ts(a.get("data", {}).get("created_at", "")) >= one_hour_ago
    )
    system_status = "critical" if recent_errors >= 5 else ("warning" if recent_errors >= 1 else "ok")

    return {
        "mrr": round(mrr_cents / 100, 2),
        "clients": active_clients,
        "system_status": system_status,
        "active_units": 0,
        "open_incidents": 0,
        "pending_claims": 0,
        "collection_rate": 0.0,
        "as_of": datetime.now(UTC).isoformat(),
    }
