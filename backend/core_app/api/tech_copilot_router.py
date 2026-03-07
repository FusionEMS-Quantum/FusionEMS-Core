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

from core_app.api.dependencies import get_current_user
from core_app.core.config import get_settings
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
    current: CurrentUser = Depends(get_current_user),
) -> dict[str, Any]:
    """Analyze platform health using AI with deterministic fallback."""
    settings = get_settings()

    # Try AI analysis if OpenAI is configured
    if settings.openai_api_key:
        try:
            from openai import OpenAI

            client = OpenAI(api_key=settings.openai_api_key)
            user_msg = json.dumps({"type": payload.type, "data": payload.data}, default=str)
            resp = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": ANALYSIS_SYSTEM_PROMPT},
                    {"role": "user", "content": user_msg},
                ],
                temperature=0.1,
                max_tokens=500,
            )
            content = resp.choices[0].message.content or ""
            result = json.loads(content)
            # Validate required fields exist
            required = {"issue", "severity", "source", "what_is_wrong", "why_it_matters",
                        "what_to_do_next", "tech_context", "human_review", "confidence"}
            if required.issubset(result.keys()):
                logger.info(
                    "Tech Copilot AI analysis completed",
                    extra={"extra_fields": {"type": payload.type}},
                )
                return result
            logger.warning("AI response missing fields, falling back to heuristic")
        except Exception as exc:
            logger.warning("AI analysis failed, using heuristic fallback: %s", exc)

    # Deterministic fallback
    return _heuristic_analysis(payload.data)

