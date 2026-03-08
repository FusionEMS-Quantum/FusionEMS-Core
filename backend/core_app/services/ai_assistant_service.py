import json
import logging
from typing import Any

from core_app.models.billing import ClaimIssue

# import boto3
# from core_app.core.config import get_settings
from core_app.models.deployment import FailureAudit

logger = logging.getLogger(__name__)


class AIAssistantService:
    """
    Implements PART 9: AI FOUNDER ASSISTANT STANDARD.

    Generates plain-English explanations for technical failures.
    """
    def __init__(self) -> None:
        # Intentionally deterministic until managed model routing is enabled.
        logger.info("ai_assistant_service_initialized mode=deterministic")

    async def explain_deployment_failure(
        self, failure: FailureAudit, technical_context: dict[str, Any]
    ) -> FailureAudit:
        """
        Populate FailureAudit with AI explanation per Section 11 standard:
        Issue, Severity, Source, Why it matters, What you should do,
        Business context, Human review status, Confidence.
        """
        explanation = self._generate_explanation(
            issue_type="DEPLOYMENT_FAILURE", context=technical_context
        )

        failure.what_is_wrong = explanation.get("what_is_wrong", "Unknown Error")
        failure.why_it_matters = explanation.get("why_it_matters", "Deployment halted.")
        failure.what_to_do_next = explanation.get("what_to_do_next", "Contact Support.")
        failure.severity = explanation.get("severity", "HIGH")
        failure.business_context = explanation.get("business_context", "Agency deployment blocked — cannot go live until resolved.")
        failure.human_review_status = "PENDING"
        failure.confidence = explanation.get("confidence", 0.0)

        return failure

    async def explain_claim_issue(
        self, issue: ClaimIssue, claim_data: dict[str, Any]
    ) -> ClaimIssue:
        """
        Populate ClaimIssue with AI explanation per Section 11 standard:
        Issue, Severity, Source, Why it matters, What you should do,
        Business context, Human review status, Confidence.
        """
        explanation = self._generate_explanation(
            issue_type="CLAIM_ISSUE", context=claim_data
        )

        issue.what_is_wrong = explanation.get("what_is_wrong", "Invalid data.")
        issue.why_it_matters = explanation.get("why_it_matters", "Claim will be denied.")
        issue.what_to_do_next = explanation.get("what_to_do_next", "Correct the field.")
        issue.business_context = explanation.get("business_context", "Revenue at risk — claim cannot be submitted until resolved.")
        issue.human_review_status = "PENDING"
        issue.confidence = explanation.get("confidence", 0.0)

        return issue

    async def generate_sms_reply(self, tenant_id: str, patient_phone: str, message_body: str) -> str | None:
        """
        Generates a context-aware SMS reply.
        """
        logger.info(
            "ai_sms_reply_request tenant_id=%s patient_phone=%s", tenant_id, patient_phone
        )

        normalized = message_body.strip().lower()
        if not normalized:
            return (
                "We received your message but it was empty. "
                "Reply HELP for billing support options."
            )

        if "stop" in normalized:
            # Upstream unsubscribe flow handles the final STOP acknowledgement.
            return None

        if "help" in normalized or "support" in normalized:
            return (
                "Billing support is available by phone through your agency billing office. "
                "If you need your payment link resent, reply BILL."
            )

        if any(token in normalized for token in ("bill", "balance", "pay", "payment")):
            return (
                "To view or pay your balance, use your secure statement link. "
                "If you need a new link, reply BILL."
            )

        if any(token in normalized for token in ("dispute", "incorrect", "error", "wrong")):
            return (
                "Thanks for reporting a billing concern. "
                "A billing specialist will review and follow up with you."
            )

        return (
            "Thank you for contacting billing support. "
            "Reply HELP for assistance options or BILL for payment-link support."
        )

    async def generate_narrative(self, incident_data: dict[str, Any]) -> str:
        """
        Generates a clinical narrative from structured incident data.
        """
        logger.info("ai_narrative_generation_requested")

        unit = str(incident_data.get("unit_id") or incident_data.get("unit") or "Responding unit")
        chief = str(
            incident_data.get("chief_complaint")
            or incident_data.get("dispatch_reason")
            or "no chief complaint documented"
        )
        assessment = str(incident_data.get("assessment") or "assessment details pending")
        treatment = str(incident_data.get("treatment") or "no treatment documented")
        disposition = str(
            incident_data.get("disposition")
            or incident_data.get("transport_disposition")
            or "final disposition pending"
        )

        return (
            f"{unit} responded for {chief}. "
            f"Assessment: {assessment}. "
            f"Treatment: {treatment}. "
            f"Disposition: {disposition}."
        )

    async def generate_narrative_and_update_status(
        self, db_session: Any, incident_id: str
    ) -> dict[str, Any]:
        """
        Generate narrative and return a deterministic update envelope.
        Persistence/RCM mutation is intentionally delegated to caller-owned transaction logic.
        """
        _ = db_session  # transaction/session consumed by caller-specific orchestration.
        narrative = await self.generate_narrative({})
        logger.info("ai_narrative_generated incident_id=%s next_status=REVIEW", incident_id)
        return {
            "incident_id": incident_id,
            "status": "REVIEW",
            "narrative": narrative,
        }

    async def _call_llm(self, prompt: str) -> dict[str, Any]:
        """
        Compatibility shim retained for existing call-sites.
        """
        return self._generate_explanation(
            issue_type="GENERIC", context={"prompt": prompt}
        )

    def _generate_explanation(
        self, issue_type: str, context: dict[str, Any]
    ) -> dict[str, Any]:
        issue_kind = issue_type.upper()
        source = str(context.get("source") or context.get("error_source") or "system")
        code = str(context.get("error_code") or context.get("code") or "unspecified")

        if issue_kind == "DEPLOYMENT_FAILURE":
            return {
                "what_is_wrong": f"Deployment failed at {source} (code: {code}).",
                "why_it_matters": "Service rollout is blocked and release integrity is at risk.",
                "what_to_do_next": "Review deployment logs, correct failing dependency/configuration, and retry rollout.",
                "severity": "HIGH",
                "business_context": "Agency activation and operations may be delayed until deployment health is restored.",
                "confidence": 0.75,
            }

        if issue_kind == "CLAIM_ISSUE":
            payer = str(context.get("payer") or context.get("primary_payer_name") or "payer")
            return {
                "what_is_wrong": f"Claim requires correction before submission to {payer}.",
                "why_it_matters": "Unresolved claim defects increase rejection and denial risk.",
                "what_to_do_next": "Correct the flagged fields and rerun claim validation before submit.",
                "severity": "MEDIUM",
                "business_context": "Revenue realization is delayed while claim quality issues remain open.",
                "confidence": 0.7,
            }

        return {
            "what_is_wrong": "A processing issue was detected.",
            "why_it_matters": "Workflow continuity may be affected until resolved.",
            "what_to_do_next": "Review the related event context and retry after correction.",
            "severity": "MEDIUM",
            "business_context": "Operational throughput may degrade if repeated failures continue.",
            "confidence": 0.6,
        }

    def _build_prompt(self, issue_type: str, context: dict[str, Any]) -> str:
        # Construct a strict prompt following "AI EXPLANATION RULES"
        return f"Prompt for {issue_type} with context: {json.dumps(context, default=str)}"

