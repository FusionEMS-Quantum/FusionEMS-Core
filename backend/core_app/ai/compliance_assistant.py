import uuid
from typing import Any

from sqlalchemy.orm import Session

from core_app.services.governance_service import GovernanceService


class ComplianceAssistant:
    def __init__(self, db: Session):
        self.db = db
        self.gov_service = GovernanceService(db)

    def analyze_issue(self, tenant_id: uuid.UUID, issue_type: str, context: dict[str, Any]) -> dict[str, Any]:
        """
        AI Governance analysis of a security/compliance event.
        Returns a structured recommendation for the founder.
        """
        # In a real build, this would call a LLM.
        # Here we provide deterministic logic for key patterns mentioned in directive.

        if issue_type == "FAILED_LOGIN_SPIKE":
            return {
                "ISSUE": "Multiple failed login attempts detected",
                "SEVERITY": "HIGH",
                "SOURCE": "AUTH_EVENT",
                "WHAT_IS_WRONG": f"There have been {context.get('count')} failed login attempts from IP {context.get('ip')} in the last hour.",
                "WHY_IT_MATTERS": "This may indicate a brute-force attack or a credential stuffing attempt against your agency.",
                "WHAT_YOU_SHOULD_DO": "Consider locking the affected account or blocking the source IP if it is not a known provider location.",
                "TRUST_CONTEXT": "Authentication boundaries protect the front door of your clinical data.",
                "HUMAN_REVIEW": "REQUIRED",
                "CONFIDENCE": "HIGH"
            }

        if issue_type == "UNAUDITED_PHI_EXPORT":
            return {
                "ISSUE": "Sensitive PHI Export without clear clinical reason",
                "SEVERITY": "MEDIUM",
                "SOURCE": "EXPORT_EVENT",
                "WHAT_IS_WRONG": "A user exported 50+ patient records using a custom filter with no associated incident reference.",
                "WHY_IT_MATTERS": "Large scale data exports are high-risk events for HIPAA compliance and data sovereignty.",
                "WHAT_YOU_SHOULD_DO": "Review the export logs and verify the 'Actor Reason' provided by the user.",
                "TRUST_CONTEXT": "Export traceability is a non-negotiable part of PHI data protection.",
                "HUMAN_REVIEW": "RECOMMENDED",
                "CONFIDENCE": "MEDIUM"
            }

        return {
            "ISSUE": "General Compliance Review",
            "SEVERITY": "LOW",
            "SOURCE": "POLICY",
            "WHAT_IS_WRONG": "Routine policy review suggested for new tenant onboarding.",
            "WHY_IT_MATTERS": "Ensures all default security controls are aligned with agency SOPs.",
            "WHAT_YOU_SHOULD_DO": "Review tenant policy settings in the Governance Command Center.",
            "TRUST_CONTEXT": "Continuous compliance requires proactive policy verification.",
            "HUMAN_REVIEW": "SAFE_TO_AUTO_PROCESS",
            "CONFIDENCE": "HIGH"
        }
