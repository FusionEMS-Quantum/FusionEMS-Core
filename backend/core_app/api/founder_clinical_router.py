from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.orm import Session

from core_app.api.dependencies import db_session_dependency, require_founder_only_audited
from core_app.schemas.auth import CurrentUser

router = APIRouter(prefix="/api/v1/clinical/command", tags=["Founder Clinical Command"])

# ─────────────────────────────────────────────────────────────
# COLOR SYSTEM (returned in all responses for UI rendering)
# RED = BLOCKING | ORANGE = HIGH_RISK | YELLOW = NEEDS_ATTENTION
# BLUE = IN_REVIEW | GREEN = READY | GRAY = CLOSED
# ─────────────────────────────────────────────────────────────


@router.get("/dashboard")
async def clinical_dashboard(
    current: CurrentUser = Depends(require_founder_only_audited()),
    db: Session = Depends(db_session_dependency),
):
    """
    Founder Clinical Command Center — real-time aggregations from the DB.
    Returns sync health, chart readiness, QA backlog, NEMSIS failures, and top actions.
    """
    tid = str(current.tenant_id)

    # ── Chart status counts
    chart_counts = _chart_status_counts(db, tid)

    # ── Sync queue health
    sync_counts = _sync_queue_counts(db, tid)

    # ── QA backlog
    qa_counts = _qa_review_counts(db, tid)

    # ── NEMSIS export failures
    nemsis_counts = _nemsis_export_counts(db, tid)

    # ── Handoff failures
    handoff_counts = _handoff_counts(db, tid)

    # ── Validation blockers
    validation_counts = _validation_counts(db, tid)

    # ── Aging: unlocked charts older than 24h
    aging = _aging_chart_counts(db, tid)

    # ── Compute top actions
    top_actions = _build_top_actions(
        chart_counts, sync_counts, qa_counts, nemsis_counts, handoff_counts, aging
    )

    # ── Overall risk meter
    risk_level = _compute_risk_level(sync_counts, qa_counts, nemsis_counts, chart_counts)

    return {
        "tenant_id": tid,
        "risk_level": risk_level,
        "risk_color": _risk_color(risk_level),
        "top_actions": top_actions,
        "widgets": {
            "chart_readiness": {
                "label": "Chart Readiness",
                "color_hint": "green" if chart_counts.get("ready_for_lock", 0) > 0 else "yellow",
                "counts": chart_counts,
            },
            "sync_health": {
                "label": "Sync Health",
                "color_hint": "red" if sync_counts.get("failed", 0) > 0 else ("yellow" if sync_counts.get("queued", 0) > 0 else "green"),
                "backlog": sync_counts.get("queued", 0),
                "failures": sync_counts.get("failed", 0),
                "synced_today": sync_counts.get("completed_today", 0),
            },
            "qa_backlog": {
                "label": "QA Backlog",
                "color_hint": "orange" if qa_counts.get("in_review", 0) > 5 else ("yellow" if qa_counts.get("in_review", 0) > 0 else "green"),
                "in_review": qa_counts.get("in_review", 0),
                "needs_correction": qa_counts.get("needs_correction", 0),
                "escalated": qa_counts.get("escalated", 0),
            },
            "nemsis_health": {
                "label": "NEMSIS Export Health",
                "color_hint": "red" if nemsis_counts.get("failed", 0) > 0 else "green",
                "failed": nemsis_counts.get("failed", 0),
                "pending": nemsis_counts.get("queued", 0),
                "completed": nemsis_counts.get("complete", 0),
            },
            "handoff_health": {
                "label": "Handoff Delivery",
                "color_hint": "red" if handoff_counts.get("failed", 0) > 0 else "green",
                "failed": handoff_counts.get("failed", 0),
                "sent": handoff_counts.get("sent", 0),
            },
            "validation_blockers": {
                "label": "Validation Blockers",
                "color_hint": "red" if validation_counts.get("blocked", 0) > 0 else "green",
                "blocked": validation_counts.get("blocked", 0),
            },
            "aging_unlocked": {
                "label": "Aging Unlocked Charts",
                "color_hint": "orange" if aging.get("over_24h", 0) > 0 else "green",
                "over_24h": aging.get("over_24h", 0),
                "over_48h": aging.get("over_48h", 0),
                "over_72h": aging.get("over_72h", 0),
            },
        },
    }


@router.get("/charts/at-risk")
async def charts_at_risk(
    limit: int = 25,
    current: CurrentUser = Depends(require_founder_only_audited()),
    db: Session = Depends(db_session_dependency),
):
    """
    Charts with blocking issues, sync failures, or pending QA — ordered by risk severity.
    """
    tid = str(current.tenant_id)

    rows = db.execute(
        text("""
            SELECT
                c.id,
                c.data->>'chart_id' AS chart_id,
                c.data->>'chart_status' AS chart_status,
                c.data->>'chart_mode' AS chart_mode,
                c.data->'patient'->>'last_name' AS patient_last,
                c.data->'patient'->>'first_name' AS patient_first,
                c.data->>'completeness_score' AS completeness_score,
                c.created_at,
                c.updated_at,
                q.status AS qa_status,
                sq.status AS sync_status,
                vs.validation_status,
                vs.has_blocking
            FROM epcr_charts c
            LEFT JOIN LATERAL (
                SELECT status FROM epcr_qa_reviews
                WHERE chart_id = (c.data->>'chart_id')::uuid
                  AND tenant_id = c.tenant_id
                  AND deleted_at IS NULL
                ORDER BY created_at DESC LIMIT 1
            ) q ON true
            LEFT JOIN LATERAL (
                SELECT status FROM epcr_sync_queue
                WHERE chart_id = (c.data->>'chart_id')::uuid
                  AND tenant_id = c.tenant_id
                  AND deleted_at IS NULL
                ORDER BY created_at DESC LIMIT 1
            ) sq ON true
            LEFT JOIN LATERAL (
                SELECT validation_status, has_blocking FROM epcr_validation_snapshots
                WHERE chart_id = (c.data->>'chart_id')::uuid
                  AND tenant_id = c.tenant_id
                  AND deleted_at IS NULL
                ORDER BY created_at DESC LIMIT 1
            ) vs ON true
            WHERE c.tenant_id = :tid
              AND c.deleted_at IS NULL
              AND c.data->>'chart_status' NOT IN ('locked', 'closed', 'cancelled')
              AND (
                vs.has_blocking = true
                OR q.status IN ('in_review', 'needs_correction', 'escalated')
                OR sq.status = 'failed'
              )
            ORDER BY c.created_at DESC
            LIMIT :limit
        """),
        {"tid": tid, "limit": limit},
    ).mappings().all()

    result = []
    for r in rows:
        risk_flags = []
        if r.get("has_blocking"):
            risk_flags.append({"type": "VALIDATION_BLOCKER", "color": "red", "label": "Blocking issues prevent lock"})
        if r.get("qa_status") in ("in_review", "needs_correction", "escalated"):
            risk_flags.append({"type": "QA_PENDING", "color": "blue", "label": f"QA: {r['qa_status']}"})
        if r.get("sync_status") == "failed":
            risk_flags.append({"type": "SYNC_FAILED", "color": "red", "label": "Sync failure"})
        result.append({
            "id": str(r["id"]),
            "chart_id": r.get("chart_id"),
            "chart_status": r.get("chart_status"),
            "chart_mode": r.get("chart_mode"),
            "patient_name": f"{r.get('patient_first', '')} {r.get('patient_last', '')}".strip(),
            "completeness_score": _safe_float(r.get("completeness_score")),
            "updated_at": str(r.get("updated_at", "")),
            "risk_flags": risk_flags,
            "risk_count": len(risk_flags),
        })
    return sorted(result, key=lambda x: x["risk_count"], reverse=True)


@router.get("/sync/failures")
async def sync_failures(
    limit: int = 50,
    current: CurrentUser = Depends(require_founder_only_audited()),
    db: Session = Depends(db_session_dependency),
):
    """
    Charts stuck in sync failures — need manual review or retry.
    """
    rows = db.execute(
        text(
            "SELECT id, chart_id, data, created_at, updated_at FROM epcr_sync_queue "
            "WHERE tenant_id = :tid AND status = 'failed' AND deleted_at IS NULL "
            "ORDER BY updated_at DESC LIMIT :limit"
        ),
        {"tid": str(current.tenant_id), "limit": limit},
    ).mappings().all()
    return [
        {
            "queue_id": str(r["id"]),
            "chart_id": str(r["chart_id"]) if r.get("chart_id") else r["data"].get("chart_id"),
            "last_error": r["data"].get("last_error", ""),
            "retry_count": r["data"].get("retry_count", 0),
            "device_id": r["data"].get("device_id", ""),
            "queued_at": r["data"].get("queued_at", ""),
            "color": "red",
            "action": "Review and retry sync or manually resolve conflict",
        }
        for r in rows
    ]


@router.get("/nemsis/failures")
async def nemsis_failures(
    limit: int = 50,
    current: CurrentUser = Depends(require_founder_only_audited()),
    db: Session = Depends(db_session_dependency),
):
    """
    NEMSIS export failures — needs chart correction or manual export.
    """
    rows = db.execute(
        text(
            "SELECT id, data, created_at FROM nemsis_export_jobs "
            "WHERE tenant_id = :tid AND data->>'valid' = 'false' AND deleted_at IS NULL "
            "ORDER BY created_at DESC LIMIT :limit"
        ),
        {"tid": str(current.tenant_id), "limit": limit},
    ).mappings().all()
    return [
        {
            "job_id": r["data"].get("job_id"),
            "chart_id": r["data"].get("chart_id"),
            "errors": r["data"].get("export_errors", []),
            "exported_at": r["data"].get("exported_at"),
            "color": "red",
            "action": "Fix NEMSIS validation errors then re-export",
        }
        for r in rows
    ]


@router.get("/charts/billing-blocked")
async def charts_billing_blocked(
    limit: int = 50,
    current: CurrentUser = Depends(require_founder_only_audited()),
    db: Session = Depends(db_session_dependency),
):
    """
    Charts not yet locked or not yet synced — cannot be submitted to billing.
    """
    rows = db.execute(
        text("""
            SELECT id, data, created_at, updated_at
            FROM epcr_charts
            WHERE tenant_id = :tid
              AND deleted_at IS NULL
              AND data->>'chart_status' NOT IN ('locked', 'amended', 'closed', 'submitted')
              AND created_at < now() - interval '4 hours'
            ORDER BY created_at ASC
            LIMIT :limit
        """),
        {"tid": str(current.tenant_id), "limit": limit},
    ).mappings().all()
    return [
        {
            "chart_id": r["data"].get("chart_id"),
            "chart_status": r["data"].get("chart_status"),
            "patient_name": f"{r['data'].get('patient', {}).get('first_name', '')} {r['data'].get('patient', {}).get('last_name', '')}".strip(),
            "completeness_score": r["data"].get("completeness_score"),
            "created_at": str(r["created_at"]),
            "color": "orange",
            "reason": "Chart not locked — cannot submit to billing",
            "action": "Complete validation, resolve QA flags, then lock chart",
        }
        for r in rows
    ]


# ─────────────────────────────────────────────────────────────
# SQL HELPERS
# ─────────────────────────────────────────────────────────────


def _chart_status_counts(db: Session, tid: str) -> dict[str, int]:
    rows = db.execute(
        text(
            "SELECT data->>'chart_status' AS status, COUNT(*)::int AS cnt "
            "FROM epcr_charts "
            "WHERE tenant_id = :tid AND deleted_at IS NULL "
            "GROUP BY data->>'chart_status'"
        ),
        {"tid": tid},
    ).fetchall()
    return {r[0] or "unknown": r[1] for r in rows}


def _sync_queue_counts(db: Session, tid: str) -> dict[str, int]:
    rows = db.execute(
        text(
            "SELECT status, COUNT(*)::int AS cnt "
            "FROM epcr_sync_queue "
            "WHERE tenant_id = :tid AND deleted_at IS NULL "
            "GROUP BY status"
        ),
        {"tid": tid},
    ).fetchall()
    counts = {r[0] or "unknown": r[1] for r in rows}

    completed_today = db.execute(
        text(
            "SELECT COUNT(*)::int FROM epcr_sync_queue "
            "WHERE tenant_id = :tid AND status = 'completed' "
            "AND updated_at > now() - interval '24 hours' AND deleted_at IS NULL"
        ),
        {"tid": tid},
    ).scalar() or 0
    counts["completed_today"] = completed_today
    return counts


def _qa_review_counts(db: Session, tid: str) -> dict[str, int]:
    rows = db.execute(
        text(
            "SELECT status, COUNT(*)::int AS cnt "
            "FROM epcr_qa_reviews "
            "WHERE tenant_id = :tid AND deleted_at IS NULL "
            "GROUP BY status"
        ),
        {"tid": tid},
    ).fetchall()
    return {r[0] or "unknown": r[1] for r in rows}


def _nemsis_export_counts(db: Session, tid: str) -> dict[str, int]:
    total = db.execute(
        text("SELECT COUNT(*)::int FROM nemsis_export_jobs WHERE tenant_id = :tid AND deleted_at IS NULL"),
        {"tid": tid},
    ).scalar() or 0
    failed = db.execute(
        text("SELECT COUNT(*)::int FROM nemsis_export_jobs WHERE tenant_id = :tid AND data->>'valid' = 'false' AND deleted_at IS NULL"),
        {"tid": tid},
    ).scalar() or 0
    return {"total": total, "failed": failed, "complete": total - failed}


def _handoff_counts(db: Session, tid: str) -> dict[str, int]:
    rows = db.execute(
        text(
            "SELECT status, COUNT(*)::int AS cnt "
            "FROM epcr_handoff_packets "
            "WHERE tenant_id = :tid AND deleted_at IS NULL "
            "GROUP BY status"
        ),
        {"tid": tid},
    ).fetchall()
    return {r[0] or "unknown": r[1] for r in rows}


def _validation_counts(db: Session, tid: str) -> dict[str, int]:
    rows = db.execute(
        text(
            "SELECT validation_status, COUNT(*)::int AS cnt "
            "FROM epcr_validation_snapshots "
            "WHERE tenant_id = :tid AND deleted_at IS NULL "
            "GROUP BY validation_status"
        ),
        {"tid": tid},
    ).fetchall()
    counts = {r[0] or "unknown": r[1] for r in rows}
    counts["blocked"] = db.execute(
        text(
            "SELECT COUNT(*)::int FROM epcr_validation_snapshots "
            "WHERE tenant_id = :tid AND has_blocking = true AND deleted_at IS NULL"
        ),
        {"tid": tid},
    ).scalar() or 0
    return counts


def _aging_chart_counts(db: Session, tid: str) -> dict[str, int]:
    over_24 = db.execute(
        text(
            "SELECT COUNT(*)::int FROM epcr_charts "
            "WHERE tenant_id = :tid AND deleted_at IS NULL "
            "AND data->>'chart_status' NOT IN ('locked','closed','cancelled','submitted') "
            "AND created_at < now() - interval '24 hours'"
        ),
        {"tid": tid},
    ).scalar() or 0
    over_48 = db.execute(
        text(
            "SELECT COUNT(*)::int FROM epcr_charts "
            "WHERE tenant_id = :tid AND deleted_at IS NULL "
            "AND data->>'chart_status' NOT IN ('locked','closed','cancelled','submitted') "
            "AND created_at < now() - interval '48 hours'"
        ),
        {"tid": tid},
    ).scalar() or 0
    over_72 = db.execute(
        text(
            "SELECT COUNT(*)::int FROM epcr_charts "
            "WHERE tenant_id = :tid AND deleted_at IS NULL "
            "AND data->>'chart_status' NOT IN ('locked','closed','cancelled','submitted') "
            "AND created_at < now() - interval '72 hours'"
        ),
        {"tid": tid},
    ).scalar() or 0
    return {"over_24h": over_24, "over_48h": over_48, "over_72h": over_72}


def _build_top_actions(
    charts: dict,
    sync: dict,
    qa: dict,
    nemsis: dict,
    handoff: dict,
    aging: dict,
) -> list[dict[str, Any]]:
    actions: list[dict] = []

    if sync.get("failed", 0) > 0:
        actions.append({
            "priority": 1,
            "color": "red",
            "type": "SYNC_FAILURE",
            "title": f"{sync['failed']} sync failure(s) need resolution",
            "why": "Charts stuck in sync failure cannot be locked or billed",
            "do_next": "Go to Sync → Failures and resolve conflicts or retry",
            "endpoint": "/api/v1/clinical/sync/failures",
        })

    if nemsis.get("failed", 0) > 0:
        actions.append({
            "priority": 2,
            "color": "red",
            "type": "NEMSIS_FAILURE",
            "title": f"{nemsis['failed']} NEMSIS export(s) failed",
            "why": "Failed NEMSIS exports must be corrected before state submission",
            "do_next": "Fix chart errors identified in the NEMSIS failure report",
            "endpoint": "/api/v1/clinical/nemsis/failures",
        })

    if qa.get("escalated", 0) > 0:
        actions.append({
            "priority": 3,
            "color": "orange",
            "type": "QA_ESCALATED",
            "title": f"{qa['escalated']} QA review(s) escalated",
            "why": "Escalated QA reviews indicate potential protocol deviations or documentation risk",
            "do_next": "Review escalated charts in QA Queue",
            "endpoint": "/api/v1/clinical/qa/queue?status=escalated",
        })

    if qa.get("needs_correction", 0) > 0:
        actions.append({
            "priority": 4,
            "color": "orange",
            "type": "QA_NEEDS_CORRECTION",
            "title": f"{qa['needs_correction']} chart(s) need correction",
            "why": "QA reviewer has flagged documentation that requires crew action",
            "do_next": "Assign corrections to chart authors",
            "endpoint": "/api/v1/clinical/qa/queue?status=needs_correction",
        })

    if aging.get("over_48h", 0) > 0:
        actions.append({
            "priority": 5,
            "color": "orange",
            "type": "AGING_CHARTS",
            "title": f"{aging['over_48h']} chart(s) unlocked for over 48h",
            "why": "Aging unlocked charts create billing delays and compliance risk",
            "do_next": "Complete and lock aging charts",
            "endpoint": "/api/v1/clinical/charts/billing-blocked",
        })

    if handoff.get("handoff_failed", 0) > 0:
        actions.append({
            "priority": 6,
            "color": "red",
            "type": "HANDOFF_FAILED",
            "title": f"{handoff['handoff_failed']} handoff(s) failed to deliver",
            "why": "Receiving facility may not have patient information",
            "do_next": "Retry or manually deliver failed handoff packets",
            "endpoint": "/api/v1/clinical/command/dashboard",
        })

    # Always return top 3
    return sorted(actions, key=lambda x: x["priority"])[:3]


def _compute_risk_level(sync: dict, qa: dict, nemsis: dict, charts: dict) -> str:
    if sync.get("failed", 0) > 0 or nemsis.get("failed", 0) > 0 or qa.get("escalated", 0) > 0:
        return "HIGH"
    if qa.get("needs_correction", 0) > 0 or qa.get("in_review", 0) > 3:
        return "MEDIUM"
    if qa.get("in_review", 0) > 0:
        return "LOW"
    return "NOMINAL"


def _risk_color(level: str) -> str:
    return {"HIGH": "red", "MEDIUM": "orange", "LOW": "yellow", "NOMINAL": "green"}.get(level, "gray")


def _safe_float(val: Any) -> float | None:
    try:
        return float(val)
    except (TypeError, ValueError):
        return None
