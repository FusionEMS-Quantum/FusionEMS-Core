"""Centralized billing telephony AI worker tests.

Verifies intent classification and policy-aware action gating for
one-number FusionEMS RCM voice workflows.
"""
from __future__ import annotations

from core_app.services.telephony_ai_worker import classify_intent, decide_next_action


class TestTelephonyIntentClassification:
    def test_classify_high_risk_keyword(self) -> None:
        intent, confidence = classify_intent("I will call my lawyer")
        assert intent == "high_risk"
        assert confidence >= 0.9

    def test_classify_balance_inquiry(self) -> None:
        intent, confidence = classify_intent("What is this bill for?")
        assert intent == "balance_inquiry"
        assert confidence >= 0.8

    def test_classify_payment_link(self) -> None:
        intent, confidence = classify_intent("text me the payment link")
        assert intent == "payment_link"
        assert confidence >= 0.8


class TestTelephonyPolicyDecisions:
    def test_escalates_when_verification_missing(self) -> None:
        decision = decide_next_action(
            utterance="text me the payment link",
            verification_ok=False,
            policy={"allow_ai_payment_link_resend": True},
        )
        assert decision.action == "escalate_to_founder"
        assert decision.reason == "verification_incomplete"

    def test_escalates_for_dispute(self) -> None:
        decision = decide_next_action(
            utterance="I need to dispute this insurance balance",
            verification_ok=True,
            policy={"allow_ai_balance_inquiry": True},
        )
        assert decision.action == "escalate_to_founder"
        assert decision.reason == "high_risk_or_dispute"

    def test_blocks_payment_plan_when_policy_disallows(self) -> None:
        decision = decide_next_action(
            utterance="Can I get a payment plan?",
            verification_ok=True,
            policy={"allow_ai_payment_plan_intake": False},
        )
        assert decision.intent == "payment_plan"
        assert decision.action == "escalate_to_founder"
        assert decision.reason == "policy_blocks_payment_plan_intake"

    def test_allows_payment_link_resend(self) -> None:
        decision = decide_next_action(
            utterance="text me the payment link",
            verification_ok=True,
            policy={"allow_ai_payment_link_resend": True},
        )
        assert decision.action == "send_sms_link"
        assert decision.reason == "policy_allows"

    def test_allows_statement_resend(self) -> None:
        decision = decide_next_action(
            utterance="mail me the statement",
            verification_ok=True,
            policy={"allow_ai_statement_resend": True},
        )
        assert decision.action == "resend_statement"

    def test_allows_balance_explanation(self) -> None:
        decision = decide_next_action(
            utterance="what is my balance",
            verification_ok=True,
            policy={"allow_ai_balance_inquiry": True},
        )
        assert decision.action == "explain_balance"

    def test_unknown_intent_escalates(self) -> None:
        decision = decide_next_action(
            utterance="I want something unusual",
            verification_ok=True,
            policy={},
        )
        assert decision.action == "escalate_to_founder"
        assert decision.reason == "unknown_or_blocked"
