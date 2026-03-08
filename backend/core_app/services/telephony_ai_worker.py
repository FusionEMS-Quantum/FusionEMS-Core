from __future__ import annotations

from dataclasses import dataclass
from typing import Any

HIGH_RISK_KEYWORDS = {
    "lawyer",
    "attorney",
    "fraud",
    "regulator",
    "lawsuit",
    "sue",
    "harassment",
    "identity theft",
    "wrong person",
}


@dataclass(frozen=True)
class TelephonyActionDecision:
    intent: str
    confidence: float
    action: str
    reason: str


def classify_intent(utterance: str) -> tuple[str, float]:
    text = (utterance or "").strip().lower()
    if not text:
        return ("unknown", 0.0)

    if any(k in text for k in HIGH_RISK_KEYWORDS):
        return ("high_risk", 0.98)
    if "dispute" in text or "insurance" in text:
        return ("dispute", 0.85)
    if "balance" in text or "bill" in text:
        return ("balance_inquiry", 0.9)
    if "payment link" in text or "text me" in text:
        return ("payment_link", 0.9)
    if "statement" in text or "mail" in text:
        return ("statement_resend", 0.85)
    if "plan" in text:
        return ("payment_plan", 0.8)

    return ("faq", 0.6)


def decide_next_action(
    *,
    utterance: str,
    verification_ok: bool,
    policy: dict[str, Any],
) -> TelephonyActionDecision:
    intent, confidence = classify_intent(utterance)

    if not verification_ok:
        return TelephonyActionDecision(
            intent=intent,
            confidence=confidence,
            action="escalate_to_founder",
            reason="verification_incomplete",
        )

    if intent in {"high_risk", "dispute"}:
        return TelephonyActionDecision(
            intent=intent,
            confidence=confidence,
            action="escalate_to_founder",
            reason="high_risk_or_dispute",
        )

    if intent == "payment_plan" and not bool(policy.get("allow_ai_payment_plan_intake", False)):
        return TelephonyActionDecision(
            intent=intent,
            confidence=confidence,
            action="escalate_to_founder",
            reason="policy_blocks_payment_plan_intake",
        )

    if intent == "payment_link" and bool(policy.get("allow_ai_payment_link_resend", True)):
        return TelephonyActionDecision(
            intent=intent,
            confidence=confidence,
            action="send_sms_link",
            reason="policy_allows",
        )

    if intent == "statement_resend" and bool(policy.get("allow_ai_statement_resend", True)):
        return TelephonyActionDecision(
            intent=intent,
            confidence=confidence,
            action="resend_statement",
            reason="policy_allows",
        )

    if intent == "balance_inquiry" and bool(policy.get("allow_ai_balance_inquiry", True)):
        return TelephonyActionDecision(
            intent=intent,
            confidence=confidence,
            action="explain_balance",
            reason="policy_allows",
        )

    return TelephonyActionDecision(
        intent=intent,
        confidence=confidence,
        action="escalate_to_founder",
        reason="unknown_or_blocked",
    )
