"""Compliance Command Center — 7-domain aggregate summary endpoint.

Aggregates NEMSIS, HIPAA, PCR, Billing, Accreditation, DEA, and CMS
domain data into a single API response consumed by the frontend
Compliance Command Center page.
"""
from __future__ import annotations

import logging
import uuid
from datetime import UTC, datetime, timedelta
from typing import Any, Literal

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from pydantic import BaseModel, Field
from sqlalchemy import text
from sqlalchemy.orm import Session

from core_app.api.dependencies import db_session_dependency, get_current_user
from core_app.schemas.auth import CurrentUser
from core_app.services.domination_service import DominationService
from core_app.services.event_publisher import get_event_publisher

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/api/v1/compliance/command",
    tags=["Compliance Command"],
)

ALLOWED_ROLES = frozenset(
    {"founder", "agency_admin", "admin", "compliance", "ems"}
)

DomainKey = Literal[
    "nemsis", "hipaa", "pcr", "billing", "accreditation", "dea", "cms"
]


# ─── Response Models ──────────────────────────────────────────────────────

class DomainScore(BaseModel):
    domain: DomainKey
    score: int = Field(ge=0, le=100)
    passing: int = 0
    warning: int = 0
    critical: int = 0
    trend: Literal["up", "down", "stable"] = "stable"
    billing_risk: Literal["low", "medium", "high"] = "low"
    licensure_risk: Literal["low", "medium", "high"] = "low"
    operational_risk: Literal["low", "medium", "high"] = "low"
    last_reviewed: str = ""
    suggested_actions: list[str] = Field(default_factory=list)


class PriorityAlert(BaseModel):
    id: str
    severity: Literal["critical", "warning"]
    domain: DomainKey
    domain_label: str
    title: str
    reason: str
    next_action: str


class ActionQueueItem(BaseModel):
    id: str
    title: str
    owner: str
    due_date: str
    domain: DomainKey
    domain_label: str
    action_state: str
    impact: str


class ComplianceCommandSummary(BaseModel):
    overall_score: int = Field(ge=0, le=100)
    total_items: int = 0
    passing_items: int = 0
    warning_items: int = 0
    critical_items: int = 0
    domains: list[DomainScore] = Field(default_factory=list)
    priority_alerts: list[PriorityAlert] = Field(default_factory=list)
    action_queue: list[ActionQueueItem] = Field(default_factory=list)
    generated_at: str = ""


# ─── Helpers ──────────────────────────────────────────────────────────────

def _check(current: CurrentUser) -> None:
    if current.role not in ALLOWED_ROLES:
        raise HTTPException(status_code=403, detail="Forbidden")


def _svc(db: Session) -> DominationService:
    return DominationService(db, get_event_publisher())


def _parse_iso(value: Any) -> datetime | None:
    if not isinstance(value, str) or not value:
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None


def _in_window(ts: datetime | None, since: datetime) -> bool:
    if ts is None:
        return False
    if ts.tzinfo is None:
        ts = ts.replace(tzinfo=UTC)
    return ts >= since


def _clamp(val: int | float) -> int:
    return max(0, min(100, int(val)))


def _risk_tier(score: int) -> Literal["low", "medium", "high"]:
    if score >= 80:
        return "low"
    if score >= 60:
        return "medium"
    return "high"


# ─── Domain Aggregators ──────────────────────────────────────────────────

def _score_nemsis(
    svc: DominationService,
    tenant_id: uuid.UUID,
    since: datetime,
) -> DomainScore:
    """Score NEMSIS domain from export jobs and validation results."""
    jobs = svc.repo("nemsis_export_jobs").list(tenant_id=tenant_id, limit=50)
    validations = svc.repo("nemsis_validation_results").list(
        tenant_id=tenant_id, limit=100,
    )

    recent_jobs = [
        j for j in jobs
        if _in_window(_parse_iso((j.get("data") or {}).get("submitted_at") or j.get("created_at", "")), since)
    ]
    recent_vals = [
        v for v in validations
        if _in_window(_parse_iso(v.get("created_at", "")), since)
    ]

    has_cert = len(jobs) > 0
    error_count = sum(
        len((v.get("data") or {}).get("errors", []))
        for v in recent_vals
    )
    warning_count = sum(
        len((v.get("data") or {}).get("warnings", []))
        for v in recent_vals
    )

    base = 50 if has_cert else 20
    penalty = min(40, error_count * 5 + warning_count * 2)
    recency_bonus = 10 if recent_jobs else 0
    score = _clamp(base + recency_bonus - penalty + (20 if error_count == 0 else 0))

    passing = len([v for v in recent_vals if not (v.get("data") or {}).get("errors")])
    critical = len([v for v in recent_vals if (v.get("data") or {}).get("errors")])

    actions: list[str] = []
    if not has_cert:
        actions.append("Complete initial NEMSIS export certification.")
    if error_count > 0:
        actions.append(f"Resolve {error_count} NEMSIS validation error(s).")
    if warning_count > 0:
        actions.append(f"Address {warning_count} NEMSIS validation warning(s).")

    return DomainScore(
        domain="nemsis",
        score=score,
        passing=passing,
        warning=warning_count,
        critical=critical,
        trend="down" if error_count > 0 else ("up" if score >= 80 else "stable"),
        billing_risk=_risk_tier(score),
        licensure_risk=_risk_tier(score),
        operational_risk=_risk_tier(score),
        last_reviewed=recent_jobs[0].get("created_at", "") if recent_jobs else "",
        suggested_actions=actions,
    )


def _score_hipaa(
    svc: DominationService,
    tenant_id: uuid.UUID,
    since: datetime,
) -> DomainScore:
    """Score HIPAA domain from audit logs and access reviews."""
    audit_logs = svc.repo("audit_log").list(tenant_id=tenant_id, limit=200)
    recent = [
        a for a in audit_logs
        if _in_window(_parse_iso(a.get("created_at", "")), since)
    ]

    phi_accesses = [
        a for a in recent
        if "phi" in str((a.get("data") or {}).get("action", "")).lower()
        or "patient" in str((a.get("data") or {}).get("entity_name", "")).lower()
    ]
    unauthorized = [
        a for a in recent
        if (a.get("data") or {}).get("action") == "access_denied"
    ]

    action_values = [
        str((a.get("data") or {}).get("action", "")).lower()
        for a in recent
    ]

    baa_exists = any(
        "baa" in action or "business_associate_agreement" in action
        for action in action_values
    )
    training_recent = any(
        "hipaa_training" in action
        or "compliance_training" in action
        or ("training" in action and "hipaa" in action)
        for action in action_values
    )

    base = 70
    penalty = min(30, len(unauthorized) * 5)
    bonus = 10 if baa_exists else 0
    bonus += 5 if training_recent else 0
    score = _clamp(base + bonus - penalty)

    actions: list[str] = []
    if len(unauthorized) > 0:
        actions.append(f"Investigate {len(unauthorized)} unauthorized access attempt(s).")
    if not baa_exists:
        actions.append("Execute BAA with all subprocessors.")
    if not training_recent:
        actions.append("Run HIPAA compliance training and record completion evidence.")

    return DomainScore(
        domain="hipaa",
        score=score,
        passing=max(0, len(phi_accesses) - len(unauthorized)),
        warning=0,
        critical=len(unauthorized),
        trend="down" if len(unauthorized) > 2 else "stable",
        billing_risk="low",
        licensure_risk=_risk_tier(score),
        operational_risk=_risk_tier(score),
        last_reviewed=recent[0].get("created_at", "") if recent else "",
        suggested_actions=actions,
    )


def _score_pcr(
    svc: DominationService,
    tenant_id: uuid.UUID,
    since: datetime,
) -> DomainScore:
    """Score PCR completion domain from ePCR records."""
    epcr_records = svc.repo("epcr_records").list(tenant_id=tenant_id, limit=200)
    recent = [
        r for r in epcr_records
        if _in_window(_parse_iso(r.get("created_at", "")), since)
    ]

    total = len(recent)
    complete = len([
        r for r in recent
        if (r.get("data") or {}).get("status") in ("finalized", "complete", "locked")
    ])
    incomplete = total - complete
    incomplete_critical = len([
        r for r in recent
        if (r.get("data") or {}).get("status") in ("draft", "incomplete")
        and _in_window(
            _parse_iso(r.get("created_at", "")),
            datetime.now(UTC) - timedelta(hours=48),
        )
    ])

    if total == 0:
        score = 50
    else:
        completion_rate = complete / total
        score = _clamp(int(completion_rate * 85) + (15 if incomplete_critical == 0 else 0))

    actions: list[str] = []
    if incomplete > 0:
        actions.append(f"Complete {incomplete} open PCR record(s).")
    if incomplete_critical > 0:
        actions.append(f"{incomplete_critical} PCR(s) overdue (>48h). Escalate immediately.")

    return DomainScore(
        domain="pcr",
        score=score,
        passing=complete,
        warning=incomplete - incomplete_critical,
        critical=incomplete_critical,
        trend="down" if incomplete_critical > 2 else ("up" if score >= 85 else "stable"),
        billing_risk=_risk_tier(score),
        licensure_risk=_risk_tier(score),
        operational_risk=_risk_tier(score),
        last_reviewed=recent[0].get("created_at", "") if recent else "",
        suggested_actions=actions,
    )


def _score_billing(
    svc: DominationService,
    tenant_id: uuid.UUID,
    since: datetime,
) -> DomainScore:
    """Score billing compliance from claims and rejections."""
    claims = svc.repo("claims").list(tenant_id=tenant_id, limit=300)
    recent = [
        c for c in claims
        if _in_window(_parse_iso(c.get("created_at", "")), since)
    ]

    total = len(recent)
    rejected = len([
        c for c in recent
        if (c.get("data") or {}).get("status") in ("rejected", "denied")
    ])
    pending = len([
        c for c in recent
        if (c.get("data") or {}).get("status") == "pending"
    ])
    paid = len([
        c for c in recent
        if (c.get("data") or {}).get("status") in ("paid", "accepted")
    ])

    if total == 0:
        score = 60
    else:
        denial_rate = rejected / total
        score = _clamp(int((1 - denial_rate) * 90) + (10 if rejected == 0 else 0))

    actions: list[str] = []
    if rejected > 0:
        actions.append(f"Review {rejected} rejected claim(s) for resubmission.")
    if pending > 5:
        actions.append(f"{pending} claims pending — review for aging issues.")

    return DomainScore(
        domain="billing",
        score=score,
        passing=paid,
        warning=pending,
        critical=rejected,
        trend="down" if rejected > 3 else ("up" if score >= 85 else "stable"),
        billing_risk=_risk_tier(score),
        licensure_risk="low",
        operational_risk=_risk_tier(score),
        last_reviewed=recent[0].get("created_at", "") if recent else "",
        suggested_actions=actions,
    )


def _score_accreditation(
    db: Session,
    tenant_id: uuid.UUID,
) -> DomainScore:
    """Score accreditation domain from accreditation_items table."""
    rows = (
        db.execute(
            text(
                "SELECT status, score_weight FROM accreditation_items "
                "WHERE tenant_id = :tid AND deleted_at IS NULL"
            ),
            {"tid": str(tenant_id)},
        )
        .mappings()
        .all()
    )

    total_weight = sum(int(r["score_weight"]) for r in rows) or 1
    complete_weight = sum(
        int(r["score_weight"]) for r in rows if r["status"] == "complete"
    )
    score = _clamp(int(100 * complete_weight / total_weight))

    complete_ct = sum(1 for r in rows if r["status"] == "complete")
    in_progress = sum(1 for r in rows if r["status"] == "in_progress")
    not_started = sum(1 for r in rows if r["status"] == "not_started")

    actions: list[str] = []
    if not_started > 0:
        actions.append(f"Begin work on {not_started} accreditation item(s) not yet started.")
    if in_progress > 0:
        actions.append(f"Complete {in_progress} in-progress accreditation item(s).")

    return DomainScore(
        domain="accreditation",
        score=score,
        passing=complete_ct,
        warning=in_progress,
        critical=not_started,
        trend="up" if score >= 80 else ("down" if score < 50 else "stable"),
        billing_risk="low",
        licensure_risk=_risk_tier(score),
        operational_risk=_risk_tier(score),
        last_reviewed="",
        suggested_actions=actions,
    )


def _score_dea(
    svc: DominationService,
    tenant_id: uuid.UUID,
    since: datetime,
) -> DomainScore:
    """Score DEA domain from narcotics audit reports."""
    audits = svc.repo("dea_audit_reports").list(tenant_id=tenant_id, limit=100)
    recent = [
        a for a in audits
        if _in_window(_parse_iso((a.get("data") or {}).get("generated_at", "")), since)
    ]

    if not recent:
        return DomainScore(
            domain="dea",
            score=30,
            critical=1,
            trend="down",
            billing_risk="low",
            licensure_risk="high",
            operational_risk="high",
            suggested_actions=["Run initial DEA narcotics audit to establish baseline."],
        )

    total = len(recent)
    passed = sum(
        1 for a in recent
        if bool((a.get("data") or {}).get("result", {}).get("passed"))
    )
    hard_blocks = sum(
        1 for a in recent
        if bool((a.get("data") or {}).get("result", {}).get("hard_block"))
    )
    failed = total - passed

    scores = [
        int((a.get("data") or {}).get("result", {}).get("score", 0))
        for a in recent
    ]
    avg = sum(scores) / len(scores) if scores else 0
    score = _clamp(int(avg))

    actions: list[str] = []
    if hard_blocks > 0:
        actions.append(f"URGENT: Resolve {hard_blocks} DEA hard block(s) — unwitnessed waste or open discrepancies.")
    if failed > 0:
        actions.append(f"Review {failed} failed DEA audit(s) for corrective action.")

    return DomainScore(
        domain="dea",
        score=score,
        passing=passed,
        warning=0,
        critical=failed,
        trend="down" if hard_blocks > 0 else ("up" if score >= 85 else "stable"),
        billing_risk="low",
        licensure_risk=_risk_tier(score),
        operational_risk=_risk_tier(score),
        last_reviewed=recent[0].get("created_at", "") if recent else "",
        suggested_actions=actions,
    )


def _score_cms(
    svc: DominationService,
    tenant_id: uuid.UUID,
    since: datetime,
) -> DomainScore:
    """Score CMS domain from gate evaluation results."""
    results = svc.repo("cms_gate_results").list(tenant_id=tenant_id, limit=200)
    recent = [
        r for r in results
        if _in_window(_parse_iso((r.get("data") or {}).get("evaluated_at", "")), since)
    ]

    if not recent:
        return DomainScore(
            domain="cms",
            score=40,
            critical=1,
            trend="down",
            billing_risk="high",
            licensure_risk="medium",
            operational_risk="medium",
            suggested_actions=["Run CMS gate evaluations on recent transports to establish baseline."],
        )

    total = len(recent)
    passed = sum(1 for r in recent if bool((r.get("data") or {}).get("passed")))
    hard_blocks = sum(1 for r in recent if bool((r.get("data") or {}).get("hard_block")))
    bs_flags = sum(1 for r in recent if bool((r.get("data") or {}).get("bs_flag")))
    failed = total - passed

    scores_list = [
        int((r.get("data") or {}).get("score", 0))
        for r in recent
        if isinstance((r.get("data") or {}).get("score"), int)
    ]
    avg = sum(scores_list) / len(scores_list) if scores_list else 0
    score = _clamp(int(avg))

    actions: list[str] = []
    if hard_blocks > 0:
        actions.append(f"URGENT: {hard_blocks} CMS hard block(s) — missing PCS or medical necessity.")
    if bs_flags > 0:
        actions.append(f"Review {bs_flags} transport(s) flagged for questionable necessity language.")
    if failed > passed and total > 3:
        actions.append("CMS pass rate below 50% — systemic documentation review required.")

    return DomainScore(
        domain="cms",
        score=score,
        passing=passed,
        warning=bs_flags,
        critical=failed,
        trend="down" if hard_blocks > 0 else ("up" if score >= 80 else "stable"),
        billing_risk=_risk_tier(score),
        licensure_risk=_risk_tier(score),
        operational_risk=_risk_tier(score),
        last_reviewed=recent[0].get("created_at", "") if recent else "",
        suggested_actions=actions,
    )


# ─── Alert & Action Queue Builders ───────────────────────────────────────

_DOMAIN_LABELS: dict[DomainKey, str] = {
    "nemsis": "NEMSIS",
    "hipaa": "HIPAA",
    "pcr": "PCR Completion",
    "billing": "Billing Compliance",
    "accreditation": "Accreditation",
    "dea": "DEA Controlled Substances",
    "cms": "CMS Medical Necessity",
}


def _build_priority_alerts(domains: list[DomainScore]) -> list[PriorityAlert]:
    alerts: list[PriorityAlert] = []
    for d in domains:
        if d.critical > 0 and d.score < 60:
            alerts.append(PriorityAlert(
                id=f"alert-{d.domain}-critical",
                severity="critical",
                domain=d.domain,
                domain_label=_DOMAIN_LABELS[d.domain],
                title=f"{_DOMAIN_LABELS[d.domain]} — Critical Deficiency",
                reason=f"Score {d.score}% with {d.critical} critical item(s).",
                next_action=d.suggested_actions[0] if d.suggested_actions else "Investigate immediately.",
            ))
        elif d.score < 70 or d.warning > 2:
            alerts.append(PriorityAlert(
                id=f"alert-{d.domain}-warning",
                severity="warning",
                domain=d.domain,
                domain_label=_DOMAIN_LABELS[d.domain],
                title=f"{_DOMAIN_LABELS[d.domain]} — Attention Required",
                reason=f"Score {d.score}% with {d.warning} warning(s).",
                next_action=d.suggested_actions[0] if d.suggested_actions else "Review domain status.",
            ))
    alerts.sort(key=lambda a: (0 if a.severity == "critical" else 1, a.domain))
    return alerts[:8]


def _build_action_queue(domains: list[DomainScore]) -> list[ActionQueueItem]:
    """Generate action queue items from domain suggested actions."""
    items: list[ActionQueueItem] = []
    now = datetime.now(UTC)
    idx = 0
    for d in sorted(domains, key=lambda x: x.score):
        for action_text in d.suggested_actions[:2]:
            idx += 1
            urgency_days = 7 if d.score >= 60 else 3
            items.append(ActionQueueItem(
                id=f"action-{d.domain}-{idx}",
                title=action_text,
                owner="Compliance Officer",
                due_date=(now + timedelta(days=urgency_days)).strftime("%Y-%m-%d"),
                domain=d.domain,
                domain_label=_DOMAIN_LABELS[d.domain],
                action_state="blocking" if d.score < 50 else ("review-required" if d.score < 70 else "monitor"),
                impact="High" if d.score < 60 else ("Medium" if d.score < 80 else "Low"),
            ))
    return items[:12]


# ─── Main Endpoint ────────────────────────────────────────────────────────

@router.get(
    "/summary",
    response_model=ComplianceCommandSummary,
    summary="7-domain compliance command summary",
)
async def compliance_command_summary(
    request: Request,
    days: int = Query(default=30, ge=1, le=365, description="Lookback window in days"),
    current: CurrentUser = Depends(get_current_user),
    db: Session = Depends(db_session_dependency),
) -> ComplianceCommandSummary:
    """Aggregate compliance data across all 7 domains into a single summary.

    Returns domain scores, priority alerts, and an action queue for the
    Compliance Command Center frontend.
    """
    _check(current)
    correlation_id = getattr(request.state, "correlation_id", None)
    logger.info(
        "compliance_command_summary requested",
        extra={
            "tenant_id": str(current.tenant_id),
            "user_id": str(current.user_id),
            "days": days,
            "correlation_id": correlation_id,
        },
    )

    svc = _svc(db)
    since = datetime.now(UTC) - timedelta(days=days)

    # Aggregate all 7 domains — each aggregator is isolated and fault-tolerant
    domain_scores: list[DomainScore] = []
    for scorer in [
        lambda: _score_nemsis(svc, current.tenant_id, since),
        lambda: _score_hipaa(svc, current.tenant_id, since),
        lambda: _score_pcr(svc, current.tenant_id, since),
        lambda: _score_billing(svc, current.tenant_id, since),
        lambda: _score_accreditation(db, current.tenant_id),
        lambda: _score_dea(svc, current.tenant_id, since),
        lambda: _score_cms(svc, current.tenant_id, since),
    ]:
        try:
            domain_scores.append(scorer())
        except Exception:
            logger.exception(
                "Domain scorer failed — returning degraded score",
                extra={
                    "tenant_id": str(current.tenant_id),
                    "correlation_id": correlation_id,
                },
            )
            # Graceful degradation: if a scorer fails, skip it rather than
            # crashing the entire summary.

    total_items = sum(d.passing + d.warning + d.critical for d in domain_scores)
    passing_items = sum(d.passing for d in domain_scores)
    warning_items = sum(d.warning for d in domain_scores)
    critical_items = sum(d.critical for d in domain_scores)

    overall = (
        int(sum(d.score for d in domain_scores) / len(domain_scores))
        if domain_scores
        else 0
    )

    return ComplianceCommandSummary(
        overall_score=_clamp(overall),
        total_items=total_items,
        passing_items=passing_items,
        warning_items=warning_items,
        critical_items=critical_items,
        domains=domain_scores,
        priority_alerts=_build_priority_alerts(domain_scores),
        action_queue=_build_action_queue(domain_scores),
        generated_at=datetime.now(UTC).isoformat(),
    )
