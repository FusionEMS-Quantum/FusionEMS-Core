from __future__ import annotations

import csv
import io
import uuid
from datetime import UTC, datetime, timedelta
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query, Request, Response
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from core_app.api.dependencies import db_session_dependency, get_current_user
from core_app.epcr.jcs_hash import jcs_sha256
from core_app.schemas.auth import CurrentUser
from core_app.services.domination_service import DominationService
from core_app.services.event_publisher import get_event_publisher

router = APIRouter(prefix="/api/v1/dea-compliance", tags=["DEA Compliance"])

ALLOWED_ROLES = {"founder", "agency_admin", "admin", "dispatcher", "ems", "compliance"}


class DEANarcoticsAuditRequest(BaseModel):
    lookback_days: int = Field(default=30, ge=1, le=365)
    unit_id: str | None = Field(default=None, max_length=128)
    min_count_events: int = Field(default=1, ge=0, le=100)
    case_id: uuid.UUID | None = None


class DEAEvidenceBundleRequest(BaseModel):
    lookback_days: int = Field(default=30, ge=1, le=365)
    include_raw_rows: bool = False
    max_dea_audits: int = Field(default=100, ge=1, le=1000)
    max_cms_results: int = Field(default=500, ge=1, le=5000)


def _svc(db: Session) -> DominationService:
    return DominationService(db, get_event_publisher())


def _check(current: CurrentUser) -> None:
    if current.role not in ALLOWED_ROLES:
        raise HTTPException(status_code=403, detail="Forbidden")


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


def _record_unit_id(record: dict[str, Any]) -> str | None:
    data = record.get("data") or {}
    return data.get("unit_id")


def _dea_scorecard(
    *,
    narc_counts: list[dict[str, Any]],
    narc_waste_events: list[dict[str, Any]],
    narc_discrepancies: list[dict[str, Any]],
    narc_seals: list[dict[str, Any]],
    min_count_events: int,
) -> dict[str, Any]:
    open_discrepancies = [
        d
        for d in narc_discrepancies
        if str((d.get("data") or {}).get("status", "open")).lower() == "open"
    ]
    unresolved_discrepancy_count = len(open_discrepancies)

    unwitnessed_waste_events = [
        e for e in narc_waste_events if not (e.get("data") or {}).get("witness_user_id")
    ]
    unwitnessed_waste_count = len(unwitnessed_waste_events)

    gates: list[dict[str, Any]] = []
    score = 0

    def add_gate(name: str, passed: bool, weight: int, detail: str) -> None:
        nonlocal score
        gates.append(
            {
                "name": name,
                "passed": passed,
                "weight": weight,
                "detail": detail,
            }
        )
        if passed:
            score += weight

    add_gate(
        "witnessed_waste_enforced",
        unwitnessed_waste_count == 0,
        35,
        "All waste events must include witness_user_id.",
    )
    add_gate(
        "discrepancies_resolved",
        unresolved_discrepancy_count == 0,
        35,
        "No open narcotics discrepancies allowed.",
    )
    add_gate(
        "count_frequency",
        len(narc_counts) >= min_count_events,
        20,
        f"At least {min_count_events} narc count events required in window.",
    )
    add_gate(
        "seal_verification_present",
        len(narc_seals) > 0,
        10,
        "At least one seal verification event required in window.",
    )

    hard_block = unresolved_discrepancy_count > 0 or unwitnessed_waste_count > 0
    passed = score >= 85 and not hard_block

    required_actions: list[str] = []
    if unwitnessed_waste_count > 0:
        required_actions.append(
            f"Resolve {unwitnessed_waste_count} unwitnessed waste event(s) with supervisor attestation."
        )
    if unresolved_discrepancy_count > 0:
        required_actions.append(
            f"Resolve {unresolved_discrepancy_count} open narcotics discrepancy event(s)."
        )
    if len(narc_counts) < min_count_events:
        required_actions.append("Run and record additional narcotics count checks.")
    if len(narc_seals) == 0:
        required_actions.append("Record seal scan verification for controlled-substance kit(s).")

    return {
        "score": score,
        "passed": passed,
        "hard_block": hard_block,
        "gates": gates,
        "required_actions": required_actions,
        "metrics": {
            "count_events": len(narc_counts),
            "waste_events": len(narc_waste_events),
            "unwitnessed_waste_events": unwitnessed_waste_count,
            "seal_events": len(narc_seals),
            "open_discrepancies": unresolved_discrepancy_count,
            "resolved_discrepancies": len(narc_discrepancies)
            - unresolved_discrepancy_count,
        },
    }


def _filter_records(
    records: list[dict[str, Any]],
    *,
    since: datetime,
    unit_id: str | None,
    ts_fields: tuple[str, ...],
) -> list[dict[str, Any]]:
    filtered: list[dict[str, Any]] = []
    for rec in records:
        data = rec.get("data") or {}
        if unit_id and _record_unit_id(rec) != unit_id:
            continue
        ts = None
        for field_name in ts_fields:
            ts = _parse_iso(data.get(field_name))
            if ts is not None:
                break
        if not _in_window(ts, since):
            continue
        filtered.append(rec)
    return filtered


def _compute_bundle_hash(bundle_core: dict[str, Any]) -> str:
    return jcs_sha256(bundle_core)


def _build_evidence_csv(
    *,
    dea_audits: list[dict[str, Any]],
    cms_results: list[dict[str, Any]],
) -> str:
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(
        [
            "section",
            "row_id",
            "timestamp",
            "domain",
            "status",
            "score",
            "hard_block",
            "reference",
            "notes",
        ]
    )

    for row in dea_audits:
        result = row.get("result") or {}
        metrics = result.get("metrics") or {}
        notes = (
            f"open_discrepancies={metrics.get('open_discrepancies', 0)};"
            f"unwitnessed_waste={metrics.get('unwitnessed_waste_events', 0)}"
        )
        writer.writerow(
            [
                "DEA_AUDIT",
                row.get("report_id", ""),
                row.get("generated_at", ""),
                "DEA",
                "PASS" if bool(result.get("passed")) else "FAIL",
                result.get("score", ""),
                "YES" if bool(result.get("hard_block")) else "NO",
                row.get("unit_id") or row.get("case_id") or "tenant",
                notes,
            ]
        )

    for row in cms_results:
        notes = f"bs_flag={bool(row.get('bs_flag'))};issues={len(row.get('issues') or [])}"
        writer.writerow(
            [
                "CMS_GATE",
                row.get("record_id", ""),
                row.get("evaluated_at", ""),
                "CMS",
                "PASS" if bool(row.get("passed")) else "FAIL",
                row.get("score", ""),
                "YES" if bool(row.get("hard_block")) else "NO",
                row.get("case_id") or "standalone",
                notes,
            ]
        )

    return output.getvalue()


def _build_pdf_payload(
    *,
    bundle_core: dict[str, Any],
    immutable_hash: str,
    csv_filename: str,
) -> dict[str, Any]:
    dea_summary = bundle_core.get("dea_summary") or {}
    cms_summary = bundle_core.get("cms_summary") or {}
    findings = bundle_core.get("findings") or {}

    return {
        "template_id": "fusionems.dea_cms_evidence_bundle.v1",
        "document_title": "FusionEMS Quantum — DEA/CMS Evidence Bundle",
        "document_subtitle": "Inspection-ready handoff package with immutable integrity proof",
        "branding": {
            "platform": "FusionEMS Quantum",
            "palette": {
                "bg": "#050505",
                "panel": "#0A0A0B",
                "accent": "#FF4D00",
                "critical": "#ef4444",
                "warning": "#f59e0b",
                "ok": "#22c55e",
                "info": "#38bdf8",
            },
        },
        "header": {
            "bundle_id": bundle_core.get("bundle_id"),
            "generated_at": bundle_core.get("generated_at"),
            "window_days": bundle_core.get("window_days"),
            "tenant_id": bundle_core.get("tenant_id"),
        },
        "sections": [
            {
                "type": "kpi_grid",
                "title": "Command Posture",
                "items": [
                    {
                        "label": "DEA pass rate",
                        "value": f"{dea_summary.get('pass_rate', 0)}%",
                        "severity": "ok" if dea_summary.get("pass_rate", 0) >= 85 else "warn",
                    },
                    {
                        "label": "DEA hard blocks",
                        "value": dea_summary.get("hard_block_count", 0),
                        "severity": "critical" if dea_summary.get("hard_block_count", 0) > 0 else "ok",
                    },
                    {
                        "label": "CMS pass rate",
                        "value": f"{cms_summary.get('pass_rate', 0)}%",
                        "severity": "ok" if cms_summary.get("pass_rate", 0) >= 70 else "warn",
                    },
                    {
                        "label": "CMS hard blocks",
                        "value": cms_summary.get("hard_block_count", 0),
                        "severity": "critical" if cms_summary.get("hard_block_count", 0) > 0 else "ok",
                    },
                ],
            },
            {
                "type": "table",
                "title": "Evidence Manifest",
                "columns": ["Artifact", "Value"],
                "rows": [
                    ["CSV artifact", csv_filename],
                    ["DEA audits included", str(dea_summary.get("total", 0))],
                    ["CMS results included", str(cms_summary.get("total", 0))],
                    ["Previous bundle hash", bundle_core.get("previous_bundle_hash") or "none"],
                ],
            },
            {
                "type": "bullet_list",
                "title": "Critical Findings",
                "items": findings.get("critical_findings", []),
            },
            {
                "type": "bullet_list",
                "title": "Required Actions",
                "items": findings.get("required_actions", []),
            },
            {
                "type": "integrity_block",
                "title": "Immutability & Chain-of-Custody",
                "body": [
                    "Hash algorithm: sha256-jcs",
                    f"Immutable hash: {immutable_hash}",
                    "Hash is computed from canonical JSON over bundle_core (deterministic order).",
                    "Any mutation of bundle_core will produce a hash mismatch on verification.",
                ],
            },
        ],
        "render_hints": {
            "paper_size": "letter",
            "orientation": "portrait",
            "watermark": "FusionEMS Evidence Integrity",
            "show_page_numbers": True,
        },
    }


def _collect_dea_audit_rows(
    *,
    rows: list[dict[str, Any]],
    since: datetime,
    max_rows: int,
) -> list[dict[str, Any]]:
    filtered: list[dict[str, Any]] = []
    for row in rows:
        data = row.get("data") or {}
        if data.get("report_type") != "DEA_NARCOTICS_AUDIT":
            continue
        ts = _parse_iso(data.get("generated_at"))
        if not _in_window(ts, since):
            continue
        filtered.append(
            {
                "report_id": str(row.get("id")),
                "generated_at": data.get("generated_at"),
                "lookback_days": data.get("lookback_days"),
                "unit_id": data.get("unit_id"),
                "case_id": data.get("case_id"),
                "result": data.get("result") or {},
            }
        )
    filtered.sort(key=lambda r: r.get("generated_at") or "", reverse=True)
    return filtered[:max_rows]


def _collect_cms_rows(
    *,
    rows: list[dict[str, Any]],
    since: datetime,
    max_rows: int,
) -> list[dict[str, Any]]:
    filtered: list[dict[str, Any]] = []
    for row in rows:
        data = row.get("data") or {}
        ts = _parse_iso(data.get("evaluated_at"))
        if not _in_window(ts, since):
            continue
        filtered.append(
            {
                "record_id": str(row.get("id")),
                "evaluated_at": data.get("evaluated_at"),
                "case_id": data.get("case_id"),
                "score": data.get("score"),
                "passed": bool(data.get("passed")),
                "hard_block": bool(data.get("hard_block")),
                "bs_flag": bool(data.get("bs_flag")),
                "issues": data.get("issues") or [],
                "gates": data.get("gates") or [],
            }
        )
    filtered.sort(key=lambda r: r.get("evaluated_at") or "", reverse=True)
    return filtered[:max_rows]


def _summarize_dea_audits(rows: list[dict[str, Any]]) -> dict[str, Any]:
    total = len(rows)
    if total == 0:
        return {
            "total": 0,
            "pass_count": 0,
            "fail_count": 0,
            "hard_block_count": 0,
            "pass_rate": 0.0,
            "avg_score": 0.0,
            "open_discrepancy_events": 0,
            "unwitnessed_waste_events": 0,
        }

    pass_count = sum(1 for r in rows if bool((r.get("result") or {}).get("passed")))
    hard_block_count = sum(
        1 for r in rows if bool((r.get("result") or {}).get("hard_block"))
    )
    scores = [
        int((r.get("result") or {}).get("score", 0))
        for r in rows
        if isinstance((r.get("result") or {}).get("score"), int)
    ]
    avg_score = round(sum(scores) / len(scores), 2) if scores else 0.0

    open_discrepancy_events = sum(
        int(((r.get("result") or {}).get("metrics") or {}).get("open_discrepancies", 0))
        for r in rows
    )
    unwitnessed_waste_events = sum(
        int(
            ((r.get("result") or {}).get("metrics") or {}).get(
                "unwitnessed_waste_events", 0
            )
        )
        for r in rows
    )

    return {
        "total": total,
        "pass_count": pass_count,
        "fail_count": total - pass_count,
        "hard_block_count": hard_block_count,
        "pass_rate": round(pass_count / total * 100, 2),
        "avg_score": avg_score,
        "open_discrepancy_events": open_discrepancy_events,
        "unwitnessed_waste_events": unwitnessed_waste_events,
    }


def _summarize_cms_results(rows: list[dict[str, Any]]) -> dict[str, Any]:
    total = len(rows)
    if total == 0:
        return {
            "total": 0,
            "pass_count": 0,
            "fail_count": 0,
            "hard_block_count": 0,
            "bs_flag_count": 0,
            "pass_rate": 0.0,
            "avg_score": 0.0,
        }

    pass_count = sum(1 for r in rows if bool(r.get("passed")))
    hard_block_count = sum(1 for r in rows if bool(r.get("hard_block")))
    bs_flag_count = sum(1 for r in rows if bool(r.get("bs_flag")))
    scores = [int(r.get("score", 0)) for r in rows if isinstance(r.get("score"), int)]
    avg_score = round(sum(scores) / len(scores), 2) if scores else 0.0

    return {
        "total": total,
        "pass_count": pass_count,
        "fail_count": total - pass_count,
        "hard_block_count": hard_block_count,
        "bs_flag_count": bs_flag_count,
        "pass_rate": round(pass_count / total * 100, 2),
        "avg_score": avg_score,
    }


def _build_findings(
    *,
    dea_rows: list[dict[str, Any]],
    cms_rows: list[dict[str, Any]],
    dea_summary: dict[str, Any],
    cms_summary: dict[str, Any],
) -> dict[str, list[str]]:
    critical_findings: list[str] = []
    required_actions: list[str] = []

    if dea_summary.get("hard_block_count", 0) > 0:
        critical_findings.append(
            f"DEA hard blocks present in {dea_summary['hard_block_count']} audit(s)."
        )
    if cms_summary.get("hard_block_count", 0) > 0:
        critical_findings.append(
            f"CMS hard blocks present in {cms_summary['hard_block_count']} gate check(s)."
        )
    if cms_summary.get("bs_flag_count", 0) > 0:
        critical_findings.append(
            f"CMS anti-abuse language flags detected in {cms_summary['bs_flag_count']} case(s)."
        )

    for row in dea_rows[:10]:
        actions = (row.get("result") or {}).get("required_actions") or []
        for action in actions:
            if action not in required_actions:
                required_actions.append(action)

    cms_issue_count = sum(len(r.get("issues") or []) for r in cms_rows)
    if cms_issue_count > 0:
        required_actions.append(
            "Resolve CMS gate documentation gaps (medical necessity, signatures, and address completeness)."
        )

    if not critical_findings:
        critical_findings.append("No critical DEA/CMS hard-block findings in the selected evidence window.")
    if not required_actions:
        required_actions.append("Maintain current control posture and continue periodic compliance validation.")

    return {
        "critical_findings": critical_findings,
        "required_actions": required_actions,
    }


@router.post("/audits/narcotics")
async def run_narcotics_audit(
    payload: DEANarcoticsAuditRequest,
    request: Request,
    current: CurrentUser = Depends(get_current_user),
    db: Session = Depends(db_session_dependency),
):
    _check(current)
    svc = _svc(db)
    correlation_id = getattr(request.state, "correlation_id", None)
    now = datetime.now(UTC)
    since = now - timedelta(days=payload.lookback_days)

    counts = svc.repo("narc_counts").list(tenant_id=current.tenant_id, limit=2000)
    waste_events = svc.repo("narc_waste_events").list(
        tenant_id=current.tenant_id, limit=2000
    )
    discrepancies = svc.repo("narc_discrepancies").list(
        tenant_id=current.tenant_id, limit=2000
    )
    seals = svc.repo("narc_seals").list(tenant_id=current.tenant_id, limit=2000)

    filtered_counts = _filter_records(
        counts,
        since=since,
        unit_id=payload.unit_id,
        ts_fields=("created_at", "counted_at"),
    )
    filtered_waste = _filter_records(
        waste_events,
        since=since,
        unit_id=payload.unit_id,
        ts_fields=("wasted_at", "created_at"),
    )
    filtered_discrepancies = _filter_records(
        discrepancies,
        since=since,
        unit_id=payload.unit_id,
        ts_fields=("created_at",),
    )
    filtered_seals = _filter_records(
        seals,
        since=since,
        unit_id=payload.unit_id,
        ts_fields=("scanned_at", "created_at"),
    )

    result = _dea_scorecard(
        narc_counts=filtered_counts,
        narc_waste_events=filtered_waste,
        narc_discrepancies=filtered_discrepancies,
        narc_seals=filtered_seals,
        min_count_events=payload.min_count_events,
    )

    report_data = {
        "report_type": "DEA_NARCOTICS_AUDIT",
        "generated_at": now.isoformat(),
        "lookback_days": payload.lookback_days,
        "unit_id": payload.unit_id,
        "case_id": str(payload.case_id) if payload.case_id else None,
        "result": result,
    }
    report = await svc.create(
        table="compliance_reports",
        tenant_id=current.tenant_id,
        actor_user_id=current.user_id,
        data=report_data,
        correlation_id=correlation_id,
    )

    return {
        "report_id": str(report["id"]),
        "generated_at": report_data["generated_at"],
        **result,
    }


@router.get("/audits/narcotics/history")
async def narcotics_audit_history(
    limit: int = Query(default=25, ge=1, le=200),
    current: CurrentUser = Depends(get_current_user),
    db: Session = Depends(db_session_dependency),
):
    _check(current)
    svc = _svc(db)
    rows = svc.repo("compliance_reports").list(
        tenant_id=current.tenant_id,
        limit=min(limit * 4, 800),
    )
    audits = [
        r
        for r in rows
        if (r.get("data") or {}).get("report_type") == "DEA_NARCOTICS_AUDIT"
    ]
    audits_sorted = sorted(
        audits,
        key=lambda row: (row.get("data") or {}).get("generated_at", ""),
        reverse=True,
    )
    return [
        {
            "report_id": str(r["id"]),
            **(r.get("data") or {}),
        }
        for r in audits_sorted[:limit]
    ]


@router.get("/audits/narcotics/latest")
async def latest_narcotics_audit(
    current: CurrentUser = Depends(get_current_user),
    db: Session = Depends(db_session_dependency),
):
    _check(current)
    history = await narcotics_audit_history(limit=1, current=current, db=db)
    if not history:
        raise HTTPException(status_code=404, detail="No DEA narcotics audits found")
    return history[0]


@router.post("/evidence-bundles")
async def create_evidence_bundle(
    payload: DEAEvidenceBundleRequest,
    request: Request,
    current: CurrentUser = Depends(get_current_user),
    db: Session = Depends(db_session_dependency),
):
    _check(current)
    svc = _svc(db)
    correlation_id = getattr(request.state, "correlation_id", None)

    now = datetime.now(UTC)
    since = now - timedelta(days=payload.lookback_days)

    compliance_rows = svc.repo("compliance_reports").list(
        tenant_id=current.tenant_id,
        limit=4000,
    )
    cms_rows_all = svc.repo("cms_gate_results").list(
        tenant_id=current.tenant_id,
        limit=payload.max_cms_results,
    )

    dea_rows = _collect_dea_audit_rows(
        rows=compliance_rows,
        since=since,
        max_rows=payload.max_dea_audits,
    )
    cms_rows = _collect_cms_rows(
        rows=cms_rows_all,
        since=since,
        max_rows=payload.max_cms_results,
    )

    dea_summary = _summarize_dea_audits(dea_rows)
    cms_summary = _summarize_cms_results(cms_rows)
    findings = _build_findings(
        dea_rows=dea_rows,
        cms_rows=cms_rows,
        dea_summary=dea_summary,
        cms_summary=cms_summary,
    )

    previous_bundles = [
        r
        for r in compliance_rows
        if (r.get("data") or {}).get("report_type") == "DEA_CMS_EVIDENCE_BUNDLE"
    ]
    previous_bundles.sort(
        key=lambda row: (row.get("data") or {}).get("generated_at", ""),
        reverse=True,
    )
    previous_bundle_hash = (
        (previous_bundles[0].get("data") or {}).get("immutable_hash")
        if previous_bundles
        else None
    )

    bundle_id = str(uuid.uuid4())
    bundle_core = {
        "schema_version": "dea_cms_evidence_bundle.v1",
        "bundle_id": bundle_id,
        "generated_at": now.isoformat(),
        "window_days": payload.lookback_days,
        "tenant_id": str(current.tenant_id),
        "generated_by": str(current.user_id),
        "source_manifest": {
            "dea_audit_report_ids": [r.get("report_id") for r in dea_rows],
            "cms_gate_result_ids": [r.get("record_id") for r in cms_rows],
            "dea_audit_count": len(dea_rows),
            "cms_gate_count": len(cms_rows),
        },
        "dea_summary": dea_summary,
        "cms_summary": cms_summary,
        "findings": findings,
        "previous_bundle_hash": previous_bundle_hash,
    }
    immutable_hash = _compute_bundle_hash(bundle_core)

    csv_text = _build_evidence_csv(dea_audits=dea_rows, cms_results=cms_rows)
    csv_filename = f"dea_cms_evidence_{bundle_id}.csv"
    pdf_payload = _build_pdf_payload(
        bundle_core=bundle_core,
        immutable_hash=immutable_hash,
        csv_filename=csv_filename,
    )

    stored_data: dict[str, Any] = {
        "report_type": "DEA_CMS_EVIDENCE_BUNDLE",
        "generated_at": bundle_core["generated_at"],
        "bundle_core": bundle_core,
        "immutable_hash": immutable_hash,
        "hash_algorithm": "sha256-jcs",
        "csv_artifact": {
            "filename": csv_filename,
            "content_type": "text/csv",
            "row_count": max(csv_text.count("\n") - 1, 0),
            "content": csv_text,
        },
        "pdf_payload": pdf_payload,
    }

    if payload.include_raw_rows:
        stored_data["raw_rows"] = {
            "dea_audits": dea_rows,
            "cms_results": cms_rows,
        }

    created = await svc.create(
        table="compliance_reports",
        tenant_id=current.tenant_id,
        actor_user_id=current.user_id,
        data=stored_data,
        correlation_id=correlation_id,
    )

    return {
        "bundle_id": str(created.get("id")),
        "generated_at": bundle_core["generated_at"],
        "hash_algorithm": "sha256-jcs",
        "immutable_hash": immutable_hash,
        "bundle_core": bundle_core,
        "csv_artifact": {
            "filename": csv_filename,
            "content_type": "text/csv",
            "content": csv_text,
        },
        "pdf_payload": pdf_payload,
        "verify_endpoint": f"/api/v1/dea-compliance/evidence-bundles/{created.get('id')}/verify-hash",
    }


@router.get("/evidence-bundles/history")
async def evidence_bundle_history(
    limit: int = Query(default=20, ge=1, le=200),
    current: CurrentUser = Depends(get_current_user),
    db: Session = Depends(db_session_dependency),
):
    _check(current)
    svc = _svc(db)
    rows = svc.repo("compliance_reports").list(
        tenant_id=current.tenant_id,
        limit=min(limit * 6, 1200),
    )
    bundles = [
        r
        for r in rows
        if (r.get("data") or {}).get("report_type") == "DEA_CMS_EVIDENCE_BUNDLE"
    ]
    bundles.sort(
        key=lambda row: (row.get("data") or {}).get("generated_at", ""),
        reverse=True,
    )
    return [
        {
            "bundle_id": str(row.get("id")),
            "generated_at": (row.get("data") or {}).get("generated_at"),
            "immutable_hash": (row.get("data") or {}).get("immutable_hash"),
            "hash_algorithm": (row.get("data") or {}).get("hash_algorithm"),
            "dea_total": ((row.get("data") or {}).get("bundle_core") or {}).get(
                "dea_summary", {}
            ).get("total", 0),
            "cms_total": ((row.get("data") or {}).get("bundle_core") or {}).get(
                "cms_summary", {}
            ).get("total", 0),
        }
        for row in bundles[:limit]
    ]


@router.get("/evidence-bundles/{bundle_id}")
async def get_evidence_bundle(
    bundle_id: uuid.UUID,
    include_artifacts: bool = Query(default=True),
    current: CurrentUser = Depends(get_current_user),
    db: Session = Depends(db_session_dependency),
):
    _check(current)
    svc = _svc(db)
    row = svc.repo("compliance_reports").get(
        tenant_id=current.tenant_id,
        record_id=bundle_id,
    )
    if not row:
        raise HTTPException(status_code=404, detail="Evidence bundle not found")
    data = row.get("data") or {}
    if data.get("report_type") != "DEA_CMS_EVIDENCE_BUNDLE":
        raise HTTPException(status_code=404, detail="Record is not an evidence bundle")

    response: dict[str, Any] = {
        "bundle_id": str(row.get("id")),
        "generated_at": data.get("generated_at"),
        "immutable_hash": data.get("immutable_hash"),
        "hash_algorithm": data.get("hash_algorithm"),
        "bundle_core": data.get("bundle_core") or {},
    }
    if include_artifacts:
        response["csv_artifact"] = data.get("csv_artifact") or {}
        response["pdf_payload"] = data.get("pdf_payload") or {}
    return response


@router.get("/evidence-bundles/{bundle_id}/csv")
async def download_evidence_bundle_csv(
    bundle_id: uuid.UUID,
    current: CurrentUser = Depends(get_current_user),
    db: Session = Depends(db_session_dependency),
):
    _check(current)
    svc = _svc(db)
    row = svc.repo("compliance_reports").get(
        tenant_id=current.tenant_id,
        record_id=bundle_id,
    )
    if not row:
        raise HTTPException(status_code=404, detail="Evidence bundle not found")
    data = row.get("data") or {}
    if data.get("report_type") != "DEA_CMS_EVIDENCE_BUNDLE":
        raise HTTPException(status_code=404, detail="Record is not an evidence bundle")

    csv_artifact = data.get("csv_artifact") or {}
    csv_content = csv_artifact.get("content")
    if not isinstance(csv_content, str) or not csv_content:
        raise HTTPException(status_code=404, detail="CSV artifact not found")

    filename = csv_artifact.get("filename") or f"dea_cms_evidence_{bundle_id}.csv"
    return Response(
        content=csv_content,
        media_type="text/csv",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.get("/evidence-bundles/{bundle_id}/pdf-payload")
async def get_evidence_bundle_pdf_payload(
    bundle_id: uuid.UUID,
    current: CurrentUser = Depends(get_current_user),
    db: Session = Depends(db_session_dependency),
):
    _check(current)
    svc = _svc(db)
    row = svc.repo("compliance_reports").get(
        tenant_id=current.tenant_id,
        record_id=bundle_id,
    )
    if not row:
        raise HTTPException(status_code=404, detail="Evidence bundle not found")
    data = row.get("data") or {}
    if data.get("report_type") != "DEA_CMS_EVIDENCE_BUNDLE":
        raise HTTPException(status_code=404, detail="Record is not an evidence bundle")

    payload = data.get("pdf_payload")
    if not isinstance(payload, dict):
        raise HTTPException(status_code=404, detail="PDF payload not found")
    return {
        "bundle_id": str(bundle_id),
        "immutable_hash": data.get("immutable_hash"),
        "hash_algorithm": data.get("hash_algorithm"),
        "pdf_payload": payload,
    }


@router.get("/evidence-bundles/{bundle_id}/verify-hash")
async def verify_evidence_bundle_hash(
    bundle_id: uuid.UUID,
    current: CurrentUser = Depends(get_current_user),
    db: Session = Depends(db_session_dependency),
):
    _check(current)
    svc = _svc(db)
    row = svc.repo("compliance_reports").get(
        tenant_id=current.tenant_id,
        record_id=bundle_id,
    )
    if not row:
        raise HTTPException(status_code=404, detail="Evidence bundle not found")

    data = row.get("data") or {}
    if data.get("report_type") != "DEA_CMS_EVIDENCE_BUNDLE":
        raise HTTPException(status_code=404, detail="Record is not an evidence bundle")

    bundle_core = data.get("bundle_core") or {}
    expected_hash = str(data.get("immutable_hash") or "")
    recomputed_hash = _compute_bundle_hash(bundle_core)
    hash_valid = recomputed_hash == expected_hash

    return {
        "bundle_id": str(bundle_id),
        "hash_algorithm": data.get("hash_algorithm", "sha256-jcs"),
        "stored_hash": expected_hash,
        "recomputed_hash": recomputed_hash,
        "hash_valid": hash_valid,
        "verification_status": "VALID" if hash_valid else "MISMATCH",
        "verified_at": datetime.now(UTC).isoformat(),
    }
