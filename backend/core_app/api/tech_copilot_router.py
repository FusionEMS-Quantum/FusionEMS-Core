"""Tech Copilot Router — AI-powered platform analysis.

Analyzes real system health data and returns structured incident assessments.
Falls back to deterministic heuristic analysis if AI is unavailable.
"""
from __future__ import annotations

import json
import logging
from typing import Any

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from core_app.ai.service import AiService
from core_app.api.dependencies import get_current_user
from core_app.schemas.auth import CurrentUser

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/tech_copilot", tags=["Tech Assistant"])

ANALYSIS_SYSTEM_PROMPT = """You are FusionEMS Tech Copilot — a sovereign-grade SRE assistant
for a mission-critical EMS SaaS platform. Analyze the provided system health
data and return ONLY valid JSON
with exactly these fields:
{
  "issue": "<concise issue title>",
  "severity": "CRITICAL|HIGH|MEDIUM|LOW|GREEN",
  "source": "<system component or subsystem>",
  "what_is_wrong": "<plain English explanation>",
  "why_it_matters": "<operational impact on EMS dispatch, billing, or patient care>",
  "what_to_do_next": "<specific, actionable remediation step>",
  "tech_context": "<technical detail for engineers>",
  "human_review": "REQUIRED|RECOMMENDED|SAFE TO AUTO-PROCESS",
  "confidence": "HIGH|MEDIUM|LOW"
}
If all systems are healthy, set severity to GREEN and issue to "All Systems Nominal".
Never invent problems. Only flag what the data shows."""


class AnalyzeRequest(BaseModel):
    type: str
    data: dict[str, Any] | None = None


class AssistantIssue(BaseModel):
    """Structured assistant issue format for analytics/executive screens."""

    issue: str
    severity: str  # BLOCKING | HIGH | MEDIUM | LOW | INFORMATIONAL
    source: str  # METRIC RUN | AI REVIEW | BILLING EVENT | CLINICAL EVENT | OPS EVENT | READINESS EVENT | HUMAN NOTE
    what_changed: str
    why_it_matters: str
    what_you_should_do: str
    executive_context: str
    human_review: str  # REQUIRED | RECOMMENDED | SAFE TO AUTO-PROCESS
    confidence: str  # HIGH | MEDIUM | LOW


class AssistantExplainRequest(BaseModel):
    snapshot: dict[str, Any] = {}
    incidents: list[dict[str, Any]] = []
    top_n: int = 3


def _severity_rank(severity: str) -> int:
    rank: dict[str, int] = {
        "BLOCKING": 5,
        "HIGH": 4,
        "MEDIUM": 3,
        "LOW": 2,
        "INFORMATIONAL": 1,
    }
    return rank.get(severity, 1)


def _normalized_severity(raw: str | None) -> str:
    if raw in {"CRITICAL", "RED", "BLOCKING"}:
        return "BLOCKING"
    if raw in {"HIGH", "ORANGE"}:
        return "HIGH"
    if raw in {"MEDIUM", "YELLOW"}:
        return "MEDIUM"
    if raw in {"LOW", "BLUE"}:
        return "LOW"
    return "INFORMATIONAL"


def _assistant_issues_from_snapshot(
    snapshot: dict[str, Any], incidents: list[dict[str, Any]], top_n: int,
) -> list[AssistantIssue]:
    """Build deterministic assistant issues from live platform snapshot data."""
    issues: list[AssistantIssue] = []

    score = int(snapshot.get("score", 0))
    status = str(snapshot.get("status", "GRAY"))
    services = snapshot.get("services") if isinstance(snapshot.get("services"), list) else []
    integrations = snapshot.get("integrations") if isinstance(snapshot.get("integrations"), list) else []
    queues = snapshot.get("queues") if isinstance(snapshot.get("queues"), list) else []

    red_services = [s for s in services if str(s.get("status")) == "RED"]
    if red_services:
        names = ", ".join(str(s.get("name", "unknown")) for s in red_services)
        issues.append(
            AssistantIssue(
                issue="Critical service outage detected",
                severity="BLOCKING",
                source="OPS EVENT",
                what_changed=f"Service probe status flipped to RED for: {names}.",
                why_it_matters="Core workflows (dispatch, billing, or charting) may fail or stall under outage conditions.",
                what_you_should_do="Open incident bridge immediately, isolate failing dependency, and execute service recovery runbook.",
                executive_context="Outage risk is immediate and can impact agency go-live confidence and patient-care operations.",
                human_review="REQUIRED",
                confidence="HIGH",
            )
        )

    high_latency = [
        s for s in services
        if isinstance(s.get("latency_ms"), int) and int(s.get("latency_ms")) > 500
    ]
    if high_latency:
        latency_summary = ", ".join(
            f"{s.get('name', 'service')}={s.get('latency_ms', 0)}ms" for s in high_latency[:4]
        )
        issues.append(
            AssistantIssue(
                issue="Platform latency exceeded operating threshold",
                severity="HIGH",
                source="METRIC RUN",
                what_changed=f"Latency above 500ms observed: {latency_summary}.",
                why_it_matters="Delayed reads/writes can degrade dispatch responsiveness and billing workflow throughput.",
                what_you_should_do="Profile slow dependencies, inspect DB/Redis saturation, and scale or tune hot paths.",
                executive_context="Performance degradation can cascade into SLA misses and increase incident volume.",
                human_review="RECOMMENDED",
                confidence="HIGH",
            )
        )

    not_configured = [
        i for i in integrations if str(i.get("status")) in {"GRAY", "NOT_CONFIGURED"}
    ]
    if not_configured:
        names = ", ".join(str(i.get("name", "integration")) for i in not_configured)
        issues.append(
            AssistantIssue(
                issue="Integration coverage gap",
                severity="MEDIUM",
                source="OPS EVENT",
                what_changed=f"Integrations not configured or degraded: {names}.",
                why_it_matters="Missing vendor connectivity can block outbound communications, payments, or AI acceleration.",
                what_you_should_do="Validate secret rotation, webhook health, and environment configuration for each missing integration.",
                executive_context="Coverage gaps increase manual workload and reduce automation ROI.",
                human_review="RECOMMENDED",
                confidence="MEDIUM",
            )
        )

    deep_queues = [
        q for q in queues if isinstance(q.get("depth"), int) and int(q.get("depth")) > 100
    ]
    if deep_queues:
        queue_summary = ", ".join(
            f"{q.get('name', 'queue')}={q.get('depth', 0)}" for q in deep_queues[:4]
        )
        issues.append(
            AssistantIssue(
                issue="Background queue backlog building",
                severity="HIGH",
                source="OPS EVENT",
                what_changed=f"Queue depth above 100 observed: {queue_summary}.",
                why_it_matters="Backlog can delay exports, notifications, and downstream reconciliation timelines.",
                what_you_should_do="Scale workers, review failing jobs, and drain retry/dead-letter pressure points.",
                executive_context="Queue growth often precedes broad platform degradation if left unresolved.",
                human_review="RECOMMENDED",
                confidence="HIGH",
            )
        )

    active_incidents = [i for i in incidents if str(i.get("state", "")).upper() != "RESOLVED"]
    if active_incidents:
        highest = max(
            (_normalized_severity(str(i.get("severity", "INFORMATIONAL"))) for i in active_incidents),
            key=_severity_rank,
            default="LOW",
        )
        issues.append(
            AssistantIssue(
                issue="Active platform incidents require coordinated follow-through",
                severity=highest,
                source="HUMAN NOTE",
                what_changed=f"{len(active_incidents)} active incident(s) currently open.",
                why_it_matters="Open incidents can amplify operational risk and reduce confidence in current deploy posture.",
                what_you_should_do="Confirm ownership, ETA, and rollback guardrails for each open incident before next production push.",
                executive_context="Incident recovery quality is a direct predictor of customer trust and uptime confidence.",
                human_review="REQUIRED" if highest in {"BLOCKING", "HIGH"} else "RECOMMENDED",
                confidence="HIGH",
            )
        )

    if score < 70:
        issues.append(
            AssistantIssue(
                issue="Platform health score below minimum target",
                severity="HIGH" if score < 55 else "MEDIUM",
                source="METRIC RUN",
                what_changed=f"Health score is {score}% with overall status {status}.",
                why_it_matters="Sustained low health raises risk of deployment failures and customer-visible instability.",
                what_you_should_do="Freeze non-essential changes, execute stabilization checklist, then resume rollout.",
                executive_context="This is a reliability warning that should gate aggressive feature deployment.",
                human_review="RECOMMENDED",
                confidence="HIGH",
            )
        )

    if not issues:
        issues.append(
            AssistantIssue(
                issue="All analytics guardrails nominal",
                severity="INFORMATIONAL",
                source="METRIC RUN",
                what_changed="No blocking/high anomalies detected in current snapshot.",
                why_it_matters="System appears stable for normal operations with no immediate intervention needed.",
                what_you_should_do="Continue monitoring and proceed with planned execution cadence.",
                executive_context="Healthy baseline supports predictable operations and planned growth.",
                human_review="SAFE TO AUTO-PROCESS",
                confidence="HIGH",
            )
        )

    issues.sort(key=lambda item: _severity_rank(item.severity), reverse=True)
    safe_top_n = max(1, min(top_n, 10))
    return issues[:safe_top_n]


def _heuristic_analysis(health_data: dict[str, Any] | None) -> dict[str, Any]:
    """Deterministic fallback when AI is unavailable."""
    if not health_data:
        return {
            "issue": "No Health Data Available",
            "severity": "MEDIUM",
            "source": "PLATFORM MONITOR",
            "what_is_wrong": "Platform health data was not provided or is empty.",
            "why_it_matters": "Without health data, we cannot assess system reliability.",
            "what_to_do_next": "Check /api/v1/platform/health endpoint is reachable.",
            "tech_context": "The analyze endpoint received an empty payload.",
            "human_review": "RECOMMENDED",
            "confidence": "HIGH",
        }

    score = health_data.get("score", 0)
    services = health_data.get("services", [])

    red_services = [s for s in services if s.get("status") == "RED"]
    slow_services = [s for s in services if s.get("latency_ms", 0) > 500]

    if red_services:
        names = ", ".join(s["name"] for s in red_services)
        return {
            "issue": f"Service Outage: {names}",
            "severity": "CRITICAL",
            "source": red_services[0]["name"],
            "what_is_wrong": f"{names} {'is' if len(red_services) == 1 else 'are'} unreachable.",
            "why_it_matters": "Service outages block dispatch, billing, and patient records.",
            "what_to_do_next": (
                f"Investigate {red_services[0]['name']} connectivity"
                " and restart if needed."
            ),
            "tech_context": f"Probe returned RED for: {names}",
            "human_review": "REQUIRED",
            "confidence": "HIGH",
        }

    if slow_services:
        names = ", ".join(s["name"] for s in slow_services)
        return {
            "issue": f"High Latency: {names}",
            "severity": "HIGH",
            "source": slow_services[0]["name"],
            "what_is_wrong": f"{names} responding above 500ms threshold.",
            "why_it_matters": "High latency degrades real-time dispatch and crew communication.",
            "what_to_do_next": "Check connection pooling, query performance, and network routes.",
            "tech_context": "Latencies: " + ", ".join(
                f"{s['name']}={s['latency_ms']}ms" for s in slow_services
            ),
            "human_review": "RECOMMENDED",
            "confidence": "HIGH",
        }

    if score < 70:
        return {
            "issue": "Degraded Platform Health",
            "severity": "MEDIUM",
            "source": "PLATFORM AGGREGATE",
            "what_is_wrong": f"Platform health score is {score}%, below the 70% threshold.",
            "why_it_matters": "Degraded health increases risk of cascading failures.",
            "what_to_do_next": (
                "Review individual service statuses"
                " for gray or unconfigured services."
            ),
            "tech_context": f"Score={score}, services={len(services)}",
            "human_review": "RECOMMENDED",
            "confidence": "HIGH",
        }

    return {
        "issue": "All Systems Nominal",
        "severity": "GREEN",
        "source": "PLATFORM MONITOR",
        "what_is_wrong": "No issues detected.",
        "why_it_matters": "All systems operating within acceptable parameters.",
        "what_to_do_next": "Continue normal operations.",
        "tech_context": f"Score={score}, all probes GREEN",
        "human_review": "SAFE TO AUTO-PROCESS",
        "confidence": "HIGH",
    }


@router.post("/analyze")
async def analyze_issue(
    payload: AnalyzeRequest,
    _current: CurrentUser = Depends(get_current_user),
) -> dict[str, Any]:
    """Analyze platform health using AI with deterministic fallback."""
    # Try AI analysis if any provider is configured (Bedrock/OpenAI)
    if AiService.is_configured():
        try:
            svc = AiService()
            user_msg = json.dumps({"type": payload.type, "data": payload.data}, default=str)
            _resp = svc.chat(
                system=ANALYSIS_SYSTEM_PROMPT,
                user=user_msg,
                temperature=0.1,
                max_tokens=500,
            )
            content = _resp.content
            result = json.loads(content)
            required = {
                "issue",
                "severity",
                "source",
                "what_is_wrong",
                "why_it_matters",
                "what_to_do_next",
                "tech_context",
                "human_review",
                "confidence",
            }
            if required.issubset(result.keys()):
                logger.info(
                    "Tech Copilot AI analysis completed",
                    extra={"extra_fields": {"type": payload.type, "provider": _resp.provider}},
                )
                return result
            logger.warning("AI response missing fields, falling back to heuristic")
        except (json.JSONDecodeError, TypeError, ValueError, KeyError, IndexError) as exc:
            logger.warning("AI analysis failed, using heuristic fallback: %s", exc)
        except Exception as exc:
            logger.warning("AI analysis failed, using heuristic fallback: %s", exc)

    # Deterministic fallback
    return _heuristic_analysis(payload.data)


@router.post("/assistant/explain", response_model=list[AssistantIssue])
async def assistant_explain(
    payload: AssistantExplainRequest,
    _current: CurrentUser = Depends(get_current_user),
) -> list[AssistantIssue]:
    """Structured executive AI assistant output for analytics/platform dashboards."""
    return _assistant_issues_from_snapshot(
        snapshot=payload.snapshot,
        incidents=payload.incidents,
        top_n=payload.top_n,
    )

