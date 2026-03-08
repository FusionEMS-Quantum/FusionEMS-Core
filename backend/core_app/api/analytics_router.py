from __future__ import annotations

# pylint: disable=not-callable
import uuid
from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy import desc
from sqlalchemy.orm import Session

from core_app.api.dependencies import (
    db_session_dependency,
    get_current_user,
    require_role,
)
from core_app.models.billing import Claim
from core_app.models.deployment import DeploymentRun, DeploymentState, FailureAudit
from core_app.models.records_media import (
    ExportDeliveryState,
    QAException,
    QAExceptionState,
    RecordExport,
    RecordsAuditEvent,
)
from core_app.models.state_debt_setoff import DebtSetoffExportBatch
from core_app.schemas.auth import CurrentUser
from core_app.services.billing_command_service import BillingCommandService
from core_app.services.founder_command_domain_service import FounderCommandDomainService
from core_app.services.founder_ops_service import FounderOpsService

router = APIRouter(
    prefix="/analytics",
    tags=["analytics"],
    dependencies=[Depends(require_role("founder", "admin"))],
)

_SEVERITY_RANK: dict[str, int] = {
    "BLOCKING": 0,
    "CRITICAL": 0,
    "HIGH": 1,
    "MEDIUM": 2,
    "LOW": 3,
    "INFORMATIONAL": 4,
}


def _assert_agency_scope(agency_id: UUID, current: CurrentUser) -> None:
    if agency_id != current.tenant_id:
        raise HTTPException(status_code=403, detail="agency_scope_forbidden")


def _normalize_period(
    period_start: datetime | None,
    period_end: datetime | None,
) -> tuple[datetime, datetime]:
    now = datetime.now(UTC)
    end = period_end or now
    start = period_start or (end - timedelta(days=30))

    if start.tzinfo is None:
        start = start.replace(tzinfo=UTC)
    if end.tzinfo is None:
        end = end.replace(tzinfo=UTC)

    if start > end:
        raise HTTPException(status_code=422, detail="period_start_must_be_before_period_end")
    return start, end


def _top_actions(
    ops_actions: list[dict[str, Any]],
    domain_actions: list[dict[str, Any]],
    limit: int = 3,
) -> list[dict[str, Any]]:
    combined = [*ops_actions, *domain_actions]
    combined.sort(
        key=lambda item: _SEVERITY_RANK.get(str(item.get("severity", "LOW")).upper(), 3)
    )
    return combined[:limit]


def _report_definitions() -> dict[UUID, dict[str, str]]:
    defs = {
        "founder_ops_snapshot": {
            "name": "Founder Ops Snapshot",
            "description": "Current cross-domain founder operations intelligence snapshot",
        },
        "record_export_activity": {
            "name": "Clinical Record Export Activity",
            "description": "Record export throughput and failure profile",
        },
        "debt_setoff_batches": {
            "name": "State Debt Setoff Batch Activity",
            "description": "Debt setoff submission pipeline and status summary",
        },
    }
    return {
        uuid.uuid5(uuid.NAMESPACE_URL, f"fusionems:report-def:{slug}"): {
            "id": str(uuid.uuid5(uuid.NAMESPACE_URL, f"fusionems:report-def:{slug}")),
            "slug": slug,
            **meta,
        }
        for slug, meta in defs.items()
    }


@router.get("/{agency_id}/executive-summary")
async def get_executive_summary(
    agency_id: UUID,
    current: CurrentUser = Depends(get_current_user),
    db: Session = Depends(db_session_dependency),
) -> dict[str, Any]:
    """Return a real executive summary assembled from canonical billing/ops/command data."""
    _assert_agency_scope(agency_id, current)

    billing_svc = BillingCommandService(db)
    ops_svc = FounderOpsService(db)
    domain_svc = FounderCommandDomainService(db)

    billing_exec = billing_svc.get_executive_summary(agency_id)
    billing_health = billing_svc.get_billing_health(agency_id)
    ops_summary = ops_svc.get_ops_summary()
    specialty = domain_svc.get_specialty_ops_summary()
    records = domain_svc.get_records_command_summary()
    integrations = domain_svc.get_integration_command_summary()

    revenue_score = float(billing_health.get("health_score", 0))
    ops_penalty = min(
        100,
        int(ops_summary["deployment_issues"]["failed_deployments"]) * 8
        + int(ops_summary["claims_pipeline"]["blocking_issues"]) * 2
        + int(ops_summary["crewlink_health"]["escalations_last_24h"]),
    )
    clinical_penalty = min(
        100,
        records.chain_of_custody_anomalies * 8
        + records.failed_record_exports * 4
        + records.open_qa_exceptions * 2,
    )
    workforce_penalty = min(
        100,
        specialty.duty_time_warnings * 5
        + specialty.specialty_missions_blocked * 4
        + specialty.pending_lz_confirmations * 3,
    )
    compliance_penalty = min(
        100,
        records.chain_of_custody_anomalies * 8
        + records.pending_release_authorizations * 2
        + integrations.degraded_or_disabled_installs * 5,
    )

    ops_actions = [
        {
            "domain": a.get("domain"),
            "severity": str(a.get("severity", "MEDIUM")).upper(),
            "summary": a.get("action"),
            "recommended_action": a.get("reason"),
        }
        for a in ops_summary.get("top_actions", [])
    ]
    domain_actions = [
        *[a.model_dump() for a in specialty.top_actions],
        *[a.model_dump() for a in records.top_actions],
        *[a.model_dump() for a in integrations.top_actions],
    ]

    return {
        "agency_id": str(agency_id),
        "snapshot_time": datetime.now(UTC).isoformat(),
        "scores": {
            "revenue_score": round(max(0.0, min(100.0, revenue_score)), 2),
            "ops_score": round(max(0.0, 100.0 - ops_penalty), 2),
            "clinical_score": round(max(0.0, 100.0 - clinical_penalty), 2),
            "workforce_score": round(max(0.0, 100.0 - workforce_penalty), 2),
            "compliance_score": round(max(0.0, 100.0 - compliance_penalty), 2),
        },
        "financial": billing_exec,
        "ops": {
            "deployment_issues": ops_summary["deployment_issues"],
            "claims_pipeline": ops_summary["claims_pipeline"],
            "crewlink_health": ops_summary["crewlink_health"],
        },
        "clinical": {
            "signature_gaps": records.signature_gaps,
            "open_qa_exceptions": records.open_qa_exceptions,
            "failed_record_exports": records.failed_record_exports,
            "chain_of_custody_anomalies": records.chain_of_custody_anomalies,
        },
        "workforce": {
            "duty_time_warnings": specialty.duty_time_warnings,
            "pending_lz_confirmations": specialty.pending_lz_confirmations,
            "specialty_missions_blocked": specialty.specialty_missions_blocked,
        },
        "compliance": {
            "chain_of_custody_anomalies": records.chain_of_custody_anomalies,
            "pending_release_authorizations": records.pending_release_authorizations,
            "degraded_or_disabled_installs": integrations.degraded_or_disabled_installs,
        },
        "top_actions": _top_actions(ops_actions, domain_actions),
    }


@router.get("/{agency_id}/metrics/operational")
async def get_operational_metrics(
    agency_id: UUID,
    period_start: datetime | None = Query(None),
    period_end: datetime | None = Query(None),
    current: CurrentUser = Depends(get_current_user),
    db: Session = Depends(db_session_dependency),
) -> dict[str, Any]:
    """Return operational metrics derived from live deployment/claim/comms/crewlink sources."""
    _assert_agency_scope(agency_id, current)
    start, end = _normalize_period(period_start, period_end)

    ops = FounderOpsService(db).get_ops_summary()
    records = FounderCommandDomainService(db).get_records_command_summary()

    request_volume = db.query(Claim).filter(
        Claim.tenant_id == agency_id,
        Claim.created_at >= start,
        Claim.created_at <= end,
    ).count() or 0

    deployment_failures = db.query(DeploymentRun).filter(
        DeploymentRun.agency_id == agency_id,
        DeploymentRun.current_state == DeploymentState.DEPLOYMENT_FAILED,
        DeploymentRun.created_at >= start,
        DeploymentRun.created_at <= end,
    ).count() or 0

    recent_failures = db.query(FailureAudit).filter(
        FailureAudit.created_at >= start,
        FailureAudit.created_at <= end,
    ).order_by(desc(FailureAudit.created_at)).limit(20).all()

    failed_deliveries = int(ops["comms_health"]["failed_messages"]) + records.failed_record_exports
    escalation_base = int(ops["claims_pipeline"]["ready_to_submit"]) + int(ops["claims_pipeline"]["submitted"])
    escalation_rate = (
        round((int(ops["crewlink_health"]["escalations_last_24h"]) / escalation_base) * 100, 2)
        if escalation_base > 0
        else 0.0
    )

    return {
        "agency_id": str(agency_id),
        "period_start": start.isoformat(),
        "period_end": end.isoformat(),
        "operational_snapshot": {
            "request_volume": int(request_volume),
            "escalation_rate_pct": escalation_rate,
            "failed_deliveries": int(failed_deliveries),
            "deployment_failures": int(deployment_failures),
            "active_alerts": int(ops["crewlink_health"]["active_alerts"]),
        },
        "response_timing": {
            "pending_no_response": int(ops["crewlink_health"]["pending_no_response"]),
            "completed_last_24h": int(ops["crewlink_health"]["completed_last_24h"]),
            "average_response_ms": None,
        },
        "recent_failure_events": [
            {
                "id": str(item.id),
                "severity": item.severity,
                "source": item.source,
                "what_is_wrong": item.what_is_wrong,
                "created_at": item.created_at.isoformat() if item.created_at else None,
            }
            for item in recent_failures
        ],
    }


@router.get("/{agency_id}/metrics/financial")
async def get_financial_metrics(
    agency_id: UUID,
    period_start: datetime | None = Query(None),
    period_end: datetime | None = Query(None),
    current: CurrentUser = Depends(get_current_user),
    db: Session = Depends(db_session_dependency),
) -> dict[str, Any]:
    """Return financial/RCM metrics from billing command canonical data."""
    _assert_agency_scope(agency_id, current)
    start, end = _normalize_period(period_start, period_end)

    svc = BillingCommandService(db)
    dashboard = svc.get_dashboard_metrics(agency_id)
    executive = svc.get_executive_summary(agency_id)
    payer_mix = svc.get_payer_mix(agency_id)
    ar_concentration = svc.get_ar_concentration_risk(agency_id)
    leakage = svc.get_revenue_leakage(agency_id)
    stripe = svc.get_stripe_reconciliation(agency_id)
    appeals = svc.get_appeal_success(agency_id)

    return {
        "agency_id": str(agency_id),
        "period_start": start.isoformat(),
        "period_end": end.isoformat(),
        "financial_snapshot": {
            "total_billed_claims": dashboard["total_claims"],
            "total_paid_claims": dashboard["paid_claims"],
            "total_revenue_cents": dashboard["revenue_cents"],
            "denial_rate_pct": dashboard["denial_rate_pct"],
            "clean_claim_rate_pct": dashboard["clean_claim_rate_pct"],
            "mrr_cents": executive["mrr_cents"],
            "arr_cents": executive["arr_cents"],
        },
        "payer_mix": payer_mix,
        "ar_concentration": ar_concentration,
        "revenue_leakage": leakage,
        "stripe_reconciliation": stripe,
        "appeal_success": appeals,
    }


@router.get("/{agency_id}/metrics/clinical")
async def get_clinical_metrics(
    agency_id: UUID,
    period_start: datetime | None = Query(None),
    period_end: datetime | None = Query(None),
    current: CurrentUser = Depends(get_current_user),
    db: Session = Depends(db_session_dependency),
) -> dict[str, Any]:
    """Return clinical/QA metrics from records command canonical tables."""
    _assert_agency_scope(agency_id, current)
    start, end = _normalize_period(period_start, period_end)

    records = FounderCommandDomainService(db).get_records_command_summary()

    total_exports = db.query(RecordExport).filter(
        RecordExport.tenant_id == agency_id,
        RecordExport.queued_at >= start,
        RecordExport.queued_at <= end,
    ).count() or 0
    failed_exports = db.query(RecordExport).filter(
        RecordExport.tenant_id == agency_id,
        RecordExport.queued_at >= start,
        RecordExport.queued_at <= end,
        RecordExport.state == ExportDeliveryState.FAILED,
    ).count() or 0
    export_failure_rate = round((failed_exports / total_exports) * 100, 2) if total_exports > 0 else 0.0

    open_qa = db.query(QAException).filter(
        QAException.tenant_id == agency_id,
        QAException.state == QAExceptionState.OPEN,
    ).count() or 0

    return {
        "agency_id": str(agency_id),
        "period_start": start.isoformat(),
        "period_end": end.isoformat(),
        "clinical_snapshot": {
            "charts_waiting_sync": records.draft_or_unsealed_records,
            "charts_blocked_lock": records.signature_gaps,
            "contradiction_flags": records.chain_of_custody_anomalies,
            "missing_signature_rate": None,
            "qa_backlog_count": int(open_qa),
            "failed_record_exports": int(failed_exports),
            "export_failure_rate_pct": export_failure_rate,
            "low_confidence_ocr_results": records.low_confidence_ocr_results,
        },
        "top_actions": [a.model_dump() for a in records.top_actions],
    }


@router.get("/{agency_id}/metrics/readiness")
async def get_readiness_metrics(
    agency_id: UUID,
    period_start: datetime | None = Query(None),
    period_end: datetime | None = Query(None),
    current: CurrentUser = Depends(get_current_user),
    db: Session = Depends(db_session_dependency),
) -> dict[str, Any]:
    """Return workforce/readiness metrics from specialty ops + crewlink signals."""
    _assert_agency_scope(agency_id, current)
    start, end = _normalize_period(period_start, period_end)

    specialty = FounderCommandDomainService(db).get_specialty_ops_summary()
    crewlink = FounderOpsService(db).get_crewlink_health()

    return {
        "agency_id": str(agency_id),
        "period_start": start.isoformat(),
        "period_end": end.isoformat(),
        "readiness_snapshot": {
            "open_shifts_count": int(crewlink["pending_no_response"]),
            "understaffed_units_count": int(specialty.specialty_missions_blocked),
            "fatigue_warnings_count": int(specialty.duty_time_warnings),
            "out_of_service_count": int(specialty.active_hazard_flags),
            "pm_overdue_count": int(specialty.preplan_gaps),
            "pending_lz_confirmations": int(specialty.pending_lz_confirmations),
            "mission_packet_failures": int(specialty.mission_packet_failures),
            "crewlink_active_alerts": int(crewlink["active_alerts"]),
        },
        "top_actions": [a.model_dump() for a in specialty.top_actions],
    }


@router.get("/{agency_id}/reports")
async def list_reports(
    agency_id: UUID,
    current: CurrentUser = Depends(get_current_user),
    db: Session = Depends(db_session_dependency),
) -> dict[str, Any]:
    """List real generated report/export runs from canonical export workflows and supported definitions."""
    _assert_agency_scope(agency_id, current)

    definitions = _report_definitions()

    record_exports = db.query(RecordExport).filter(
        RecordExport.tenant_id == agency_id,
    ).order_by(desc(RecordExport.created_at)).limit(100).all()

    setoff_batches = db.query(DebtSetoffExportBatch).filter(
        DebtSetoffExportBatch.tenant_id == agency_id,
    ).order_by(desc(DebtSetoffExportBatch.created_at)).limit(100).all()

    runs: list[dict[str, Any]] = []
    for item in record_exports:
        runs.append(
            {
                "id": str(item.id),
                "report_kind": "clinical_record_export",
                "status": str(item.state),
                "created_at": item.created_at.isoformat() if item.created_at else None,
                "artifact_ref": {
                    "destination_system": item.destination_system,
                    "clinical_record_id": str(item.clinical_record_id),
                },
            }
        )
    for item in setoff_batches:
        runs.append(
            {
                "id": str(item.id),
                "report_kind": "state_debt_setoff_export",
                "status": item.status,
                "created_at": item.created_at.isoformat() if item.created_at else None,
                "artifact_ref": {
                    "batch_reference": item.batch_reference,
                    "record_count": item.record_count,
                    "total_amount_cents": item.total_amount_cents,
                },
            }
        )
    runs.sort(key=lambda r: r.get("created_at") or "", reverse=True)

    return {
        "agency_id": str(agency_id),
        "definitions": list(definitions.values()),
        "runs": runs[:200],
        "counts": {
            "record_exports": len(record_exports),
            "setoff_batches": len(setoff_batches),
            "total_runs": len(runs),
        },
    }


@router.post("/{agency_id}/reports/generate")
async def generate_report(
    agency_id: UUID,
    report_definition_id: UUID,
    request: Request,
    current: CurrentUser = Depends(get_current_user),
    db: Session = Depends(db_session_dependency),
) -> dict[str, Any]:
    """Generate a real on-demand report payload from canonical data and persist an audit event."""
    _assert_agency_scope(agency_id, current)

    definitions = _report_definitions()
    definition = definitions.get(report_definition_id)
    if definition is None:
        raise HTTPException(status_code=404, detail="report_definition_not_found")

    slug = definition["slug"]
    generated_at = datetime.now(UTC)

    if slug == "founder_ops_snapshot":
        payload = FounderOpsService(db).get_ops_summary()
    elif slug == "record_export_activity":
        exports = db.query(RecordExport).filter(
            RecordExport.tenant_id == agency_id,
        ).order_by(desc(RecordExport.created_at)).limit(200).all()
        failed = sum(1 for item in exports if item.state == ExportDeliveryState.FAILED)
        payload = {
            "total_exports": len(exports),
            "failed_exports": failed,
            "failure_rate_pct": round((failed / len(exports)) * 100, 2) if exports else 0.0,
            "destinations": sorted({item.destination_system for item in exports}),
        }
    elif slug == "debt_setoff_batches":
        batches = db.query(DebtSetoffExportBatch).filter(
            DebtSetoffExportBatch.tenant_id == agency_id,
        ).order_by(desc(DebtSetoffExportBatch.created_at)).limit(200).all()
        payload = {
            "total_batches": len(batches),
            "pending_batches": sum(1 for item in batches if item.status == "PENDING"),
            "submitted_batches": sum(1 for item in batches if item.status == "SUBMITTED"),
            "accepted_batches": sum(1 for item in batches if item.status in {"ACCEPTED", "PARTIALLY_ACCEPTED"}),
            "total_amount_cents": sum(int(item.total_amount_cents or 0) for item in batches),
        }
    else:
        raise HTTPException(status_code=422, detail="unsupported_report_definition")

    audit_event = RecordsAuditEvent(
        tenant_id=agency_id,
        entity_type="analytics_report",
        entity_id=report_definition_id,
        event_type="GENERATE_ON_DEMAND",
        actor_user_id=current.user_id,
        correlation_id=getattr(request.state, "correlation_id", None),
        event_payload={
            "definition_id": str(report_definition_id),
            "definition_slug": slug,
            "generated_at": generated_at.isoformat(),
            "result_keys": sorted(payload.keys()),
        },
    )
    db.add(audit_event)
    db.commit()
    db.refresh(audit_event)

    return {
        "agency_id": str(agency_id),
        "report_run_id": str(audit_event.id),
        "definition": definition,
        "status": "completed",
        "generated_at": generated_at.isoformat(),
        "payload": payload,
    }


@router.get("/{agency_id}/alerts")
async def get_alerts(
    agency_id: UUID,
    severity: str | None = Query(None),
    current: CurrentUser = Depends(get_current_user),
    db: Session = Depends(db_session_dependency),
) -> dict[str, Any]:
    """Get deterministic executive alerts for founder command center from live operational signals."""
    _assert_agency_scope(agency_id, current)

    severity_filter = severity.upper() if severity else None
    if severity_filter and severity_filter not in {
        "BLOCKING",
        "HIGH",
        "MEDIUM",
        "LOW",
        "INFORMATIONAL",
    }:
        raise HTTPException(status_code=422, detail="invalid_severity")

    ops = FounderOpsService(db).get_ops_summary()
    records = FounderCommandDomainService(db).get_records_command_summary()
    integrations = FounderCommandDomainService(db).get_integration_command_summary()

    candidates: list[dict[str, Any]] = []

    failed_deployments = int(ops["deployment_issues"]["failed_deployments"])
    if failed_deployments > 0:
        candidates.append(
            {
                "title": f"{failed_deployments} deployment failure(s) require intervention",
                "severity": "BLOCKING",
                "source": "OPS_EVENT",
                "what_changed": "Deployment runs are in failed state",
                "why_it_matters": "Deployment blockers prevent agencies from reaching live readiness",
                "what_you_should_do": "Open deployment failure board and clear blockers in sequence",
            }
        )

    denied_claims = int(ops["claims_pipeline"]["denied"])
    if denied_claims > 0:
        candidates.append(
            {
                "title": f"{denied_claims} denied claims currently reducing collectible revenue",
                "severity": "HIGH",
                "source": "BILLING_EVENT",
                "what_changed": "Denied claim volume is non-zero",
                "why_it_matters": "Unresolved denials increase cash-at-risk",
                "what_you_should_do": "Prioritize denial triage and appeal queue",
            }
        )

    if records.chain_of_custody_anomalies > 0:
        candidates.append(
            {
                "title": f"{records.chain_of_custody_anomalies} chain-of-custody anomalies detected",
                "severity": "HIGH",
                "source": "CLINICAL_EVENT",
                "what_changed": "Records chain-of-custody anomaly count is above zero",
                "why_it_matters": "Custody anomalies create compliance and legal exposure",
                "what_you_should_do": "Escalate anomalies to compliance review",
            }
        )

    if integrations.degraded_or_disabled_installs > 0:
        candidates.append(
            {
                "title": f"{integrations.degraded_or_disabled_installs} connectors degraded/disabled",
                "severity": "HIGH",
                "source": "OPS_EVENT",
                "what_changed": "Integration install health degraded",
                "why_it_matters": "Data synchronization reliability is at risk",
                "what_you_should_do": "Restore degraded connectors and validate sync jobs",
            }
        )

    if records.open_qa_exceptions > 0:
        candidates.append(
            {
                "title": f"{records.open_qa_exceptions} QA exceptions remain unresolved",
                "severity": "MEDIUM",
                "source": "CLINICAL_EVENT",
                "what_changed": "Clinical QA queue remains open",
                "why_it_matters": "Sustained QA backlog can delay chart closure and downstream billing",
                "what_you_should_do": "Prioritize QA remediation by severity",
            }
        )

    if records.pending_release_authorizations > 0:
        candidates.append(
            {
                "title": f"{records.pending_release_authorizations} release authorizations pending",
                "severity": "INFORMATIONAL",
                "source": "HUMAN_NOTE",
                "what_changed": "Unapproved release authorizations detected",
                "why_it_matters": "Pending authorization blocks release completion",
                "what_you_should_do": "Review pending authorizations in records command",
            }
        )

    alerts: list[dict[str, Any]] = []
    now = datetime.now(UTC)
    for item in candidates:
        if severity_filter and item["severity"] != severity_filter:
            continue
        alert_id = uuid.uuid5(
            uuid.NAMESPACE_URL,
            f"fusionems:analytics-alert:{agency_id}:{item['title']}:{item['severity']}",
        )
        alerts.append(
            {
                "id": str(alert_id),
                "agency_id": str(agency_id),
                "title": item["title"],
                "severity": item["severity"],
                "source": item["source"],
                "what_changed": item["what_changed"],
                "why_it_matters": item["why_it_matters"],
                "what_you_should_do": item["what_you_should_do"],
                "created_at": now.isoformat(),
                "resolved_at": None,
            }
        )

    alerts.sort(key=lambda a: _SEVERITY_RANK.get(a["severity"], 3))
    return {
        "agency_id": str(agency_id),
        "severity_filter": severity_filter,
        "total": len(alerts),
        "alerts": alerts,
    }
