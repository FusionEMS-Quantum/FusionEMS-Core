"""Analytics AI Assistant — structured insight generation for FusionEMS analytics domains.

Wraps AiService to produce structured, confidence-scored insights from analytics snapshots.
AI failure is always non-fatal: every method returns a deterministic fallback result.

Design contract:
- Read-only: never writes, updates, or deletes domain data.
- AI-isolated: if AiService raises or is unconfigured, fallback insight is returned.
- Deterministic output: every method returns a validated AnalyticsInsight.
- PHI-free: no patient-identifiable content in prompts or logs.
"""
from __future__ import annotations

import json
import logging
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

from core_app.ai.service import AiService

logger = logging.getLogger(__name__)

RiskLevel = Literal["CRITICAL", "WARNING", "STABLE"]

_STRUCTURED_SCHEMA = """{
  "domain": "<analytics domain label>",
  "summary": "<2-3 sentence executive summary of the domain health>",
  "risk_level": "CRITICAL | WARNING | STABLE",
  "top_findings": ["<finding 1>", "<finding 2>", "<finding 3>"],
  "recommended_actions": ["<action 1>", "<action 2>", "<action 3>"],
  "confidence": 0.0
}"""

_BASE_SYSTEM = (
    "You are the FusionEMS analytics intelligence engine. "
    "Analyse the provided operational snapshot and return a JSON object that strictly follows this schema:\n"
    f"{_STRUCTURED_SCHEMA}\n\n"
    "Rules:\n"
    "- Return ONLY valid JSON. No markdown, no prose outside the JSON object.\n"
    "- risk_level must be exactly one of: CRITICAL, WARNING, STABLE.\n"
    "- confidence is a float in [0.0, 1.0] reflecting how certain you are given the data provided.\n"
    "- top_findings and recommended_actions must each have 1-3 items.\n"
    "- Never invent data not in the snapshot. If data is absent, state that in summary.\n"
    "- Never include PHI. Use aggregate/anonymised metrics only."
)

_DOMAIN_HINTS: dict[str, str] = {
    "executive": (
        "Domain: EXECUTIVE KPI INTELLIGENCE. "
        "Focus on: overall business health, revenue health, deployment/ops health, "
        "cash-at-risk visibility, and top strategic actions."
    ),
    "operational": (
        "Domain: OPERATIONAL ANALYTICS. "
        "Focus on: mission volume, response timing, paging performance, unit uptime, "
        "dispatch queue bottlenecks, and facility turnaround patterns."
    ),
    "financial": (
        "Domain: FINANCIAL / RCM ANALYTICS. "
        "Focus on: billed vs paid, outstanding AR, denial rates, payment lag, "
        "payer mix, cash-at-risk, autopay failure rates, and collections staging."
    ),
    "clinical": (
        "Domain: CLINICAL / QA ANALYTICS. "
        "Focus on: chart lock delays, validation failures, QA backlog, "
        "contradiction rates, protocol deviation flags, and documentation risk."
    ),
    "workforce": (
        "Domain: WORKFORCE / READINESS ANALYTICS. "
        "Focus on: staffing gaps, fatigue risk, credential expiration, "
        "out-of-service units, inventory shortages, and narcotics discrepancy trends."
    ),
    "reporting": (
        "Domain: REPORTING / EXPORT INTELLIGENCE. "
        "Focus on: pending report generation, regulatory export readiness, "
        "scheduled report completion rates, and outstanding export obligations."
    ),
}


class AnalyticsInsight(BaseModel):
    """Structured AI-generated insight for one analytics domain."""

    model_config = ConfigDict(frozen=True)

    domain: str
    summary: str
    risk_level: RiskLevel
    top_findings: list[str] = Field(min_length=1, max_length=3)
    recommended_actions: list[str] = Field(min_length=1, max_length=3)
    confidence: float = Field(ge=0.0, le=1.0)
    ai_provider: str = ""
    fallback_used: bool = False


def _fallback_insight(domain: str, reason: str) -> AnalyticsInsight:
    return AnalyticsInsight(
        domain=domain,
        summary=f"AI analysis unavailable for {domain} domain: {reason}",
        risk_level="STABLE",
        top_findings=["Automated insight unavailable — review metrics manually."],
        recommended_actions=["Verify AI provider configuration and retry."],
        confidence=0.0,
        ai_provider="none",
        fallback_used=True,
    )


def _parse_insight(payload: dict[str, Any], domain: str, ai_resp: Any) -> AnalyticsInsight:
    """Build a validated AnalyticsInsight from a parsed JSON payload."""
    risk_raw = str(payload.get("risk_level", "STABLE")).upper()
    risk_level: RiskLevel = (
        risk_raw if risk_raw in ("CRITICAL", "WARNING", "STABLE") else "STABLE"  # type: ignore[assignment]
    )
    findings = [str(f) for f in payload.get("top_findings", []) if str(f).strip()][:3] or [
        "No findings returned."
    ]
    actions = [str(a) for a in payload.get("recommended_actions", []) if str(a).strip()][:3] or [
        "No actions returned."
    ]
    return AnalyticsInsight(
        domain=payload.get("domain", domain),
        summary=str(payload.get("summary", "No summary returned.")),
        risk_level=risk_level,
        top_findings=findings,
        recommended_actions=actions,
        confidence=float(payload.get("confidence", ai_resp.confidence)),
        ai_provider=ai_resp.provider,
        fallback_used=ai_resp.fallback_used,
    )


class AnalyticsAssistant:
    """AI-powered analytics insight generator.

    Accepts a pre-built `AiService` instance so callers control lifecycle
    and configuration.  Pass ``ai=None`` to force deterministic-fallback mode
    (useful in tests and when AI is not configured for a tenant).
    """

    def __init__(self, ai: AiService | None = None) -> None:
        self._ai = ai

    # ------------------------------------------------------------------
    # Domain analysis methods
    # ------------------------------------------------------------------

    def analyze_executive_kpis(self, snapshot: dict[str, Any]) -> AnalyticsInsight:
        return self._analyze_domain("executive", snapshot)

    def analyze_operational(self, snapshot: dict[str, Any]) -> AnalyticsInsight:
        return self._analyze_domain("operational", snapshot)

    def analyze_financial(self, snapshot: dict[str, Any]) -> AnalyticsInsight:
        return self._analyze_domain("financial", snapshot)

    def analyze_clinical(self, snapshot: dict[str, Any]) -> AnalyticsInsight:
        return self._analyze_domain("clinical", snapshot)

    def analyze_workforce(self, snapshot: dict[str, Any]) -> AnalyticsInsight:
        return self._analyze_domain("workforce", snapshot)

    def analyze_reporting(self, snapshot: dict[str, Any]) -> AnalyticsInsight:
        return self._analyze_domain("reporting", snapshot)

    def analyze_full_platform(
        self, snapshots: dict[str, dict[str, Any]]
    ) -> list[AnalyticsInsight]:
        """Run all six domain analyses and return results in domain order.

        ``snapshots`` is a mapping of domain label → snapshot dict.
        Missing domains are analysed with an empty snapshot.
        """
        results: list[AnalyticsInsight] = []
        for domain in ("executive", "operational", "financial", "clinical", "workforce", "reporting"):
            try:
                results.append(self._analyze_domain(domain, snapshots.get(domain, {})))
            except Exception as exc:
                logger.exception(
                    "analytics_assistant full_platform domain=%s error=%s", domain, exc
                )
                results.append(_fallback_insight(domain, str(exc)))
        return results

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    def _analyze_domain(self, domain: str, snapshot: dict[str, Any]) -> AnalyticsInsight:
        if self._ai is None:
            return _fallback_insight(domain, "AiService not initialised")

        hint = _DOMAIN_HINTS.get(domain, f"Domain: {domain.upper()}")
        system_prompt = f"{_BASE_SYSTEM}\n\n{hint}"
        user_msg = (
            f"Analytics snapshot for domain '{domain}':\n"
            f"{json.dumps(snapshot, default=str, indent=2)}"
        )

        try:
            payload, ai_resp = self._ai.chat_structured(
                system=system_prompt,
                user=user_msg,
                max_tokens=600,
                temperature=0.2,
            )
            return _parse_insight(payload, domain, ai_resp)
        except Exception as exc:
            logger.warning(
                "analytics_assistant domain=%s ai_error=%s fallback=true", domain, exc
            )
            return _fallback_insight(domain, str(exc))
