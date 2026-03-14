import logging
import uuid
from typing import Any

from sqlalchemy.orm import Session

from core_app.ai.service import AiService
from core_app.services.governance_service import GovernanceService

logger = logging.getLogger(__name__)


class ComplianceAssistant:
    def __init__(self, db: Session):
        self.db = db
        self.gov_service = GovernanceService(db)

    def analyze_issue(self, _tenant_id: uuid.UUID, issue_type: str, context: dict[str, Any]) -> dict[str, Any]:  # pylint: disable=unused-argument
        """
        AI Governance analysis of a security/compliance event.
        Calls LLM when configured; returns degraded response otherwise.
        """
        if not AiService.is_configured():
            logger.warning("Compliance LLM analysis unavailable — AI provider not configured")
            return {
                "status": "degraded",
                "reason": "LLM API not configured",
                "issue_type": issue_type,
                "recommendations": [],
            }

        try:
            svc = AiService()
            prompt = (
                f"You are a HIPAA compliance and security analyst for an EMS SaaS platform.\n"
                f"Analyze this security/compliance event and return a JSON object with keys: "
                f"ISSUE, SEVERITY (HIGH/MEDIUM/LOW), SOURCE, WHAT_IS_WRONG, WHY_IT_MATTERS, "
                f"WHAT_YOU_SHOULD_DO, TRUST_CONTEXT, HUMAN_REVIEW (REQUIRED/RECOMMENDED/SAFE_TO_AUTO_PROCESS), CONFIDENCE.\n\n"
                f"Issue type: {issue_type}\n"
                f"Context: {context}\n"
            )
            import json

            content = svc.chat(
                system="Return ONLY valid JSON. No markdown.",
                user=prompt,
                temperature=0.1,
                max_tokens=700,
            ).content
            return json.loads(content or "{}")
        except Exception:
            logger.exception("LLM compliance analysis failed, returning degraded response")
            return {
                "status": "degraded",
                "reason": "LLM analysis call failed",
                "issue_type": issue_type,
                "recommendations": [],
            }
