"""AI Seed Service — ensure 6 mandated domain copilots and default tenant settings exist."""
from __future__ import annotations

import logging

from sqlalchemy.orm import Session

from core_app.models.ai_platform import (
    AICopilotActionBoundary,
    AIDomainCopilot,
    AIDomainPolicy,
    AITenantSettings,
)

logger = logging.getLogger(__name__)

# ── Domain definitions per directive Part 8 ───────────────────────────────────

COPILOT_DOMAINS: list[dict] = [
    {
        "domain": "billing",
        "name": "Billing Copilot",
        "explanation_rules": {
            "always_explain_denial_reason": True,
            "cite_payer_rule_source": True,
            "use_plain_language_for_boa": True,
        },
        "data_scope_controls": {
            "allowed_tables": ["claims", "patient_balance_ledgers", "payments"],
            "phi_fields_excluded": True,
        },
        "policies": [
            {"name": "No autonomous claim submission", "desc": "AI must not file or submit claims without human approval.", "level": "BLOCK"},
            {"name": "No financial mutation", "desc": "AI must not alter payment amounts, balances, or fees.", "level": "BLOCK"},
            {"name": "Explain denial codes", "desc": "Always provide payer-sourced denial reason with plain-language summary.", "level": "FLAG"},
        ],
        "allowed_actions": ["draft_appeal", "suggest_code_correction", "summarize_claim_status"],
        "banned_actions": ["submit_claim", "modify_payment", "void_charge", "set_balance"],
    },
    {
        "domain": "clinical",
        "name": "Clinical Documentation Copilot",
        "explanation_rules": {
            "always_cite_protocol": True,
            "flag_uncertain_assessments": True,
            "require_human_review_narratives": True,
        },
        "data_scope_controls": {
            "allowed_tables": ["incidents", "vitals", "patients", "medications"],
            "phi_fields_excluded": False,
        },
        "policies": [
            {"name": "No autonomous clinical decisions", "desc": "AI must not make or alter medical decisions.", "level": "BLOCK"},
            {"name": "Narrative always requires review", "desc": "AI-generated narratives must be reviewed before signing.", "level": "BLOCK"},
            {"name": "Protocol citation required", "desc": "Clinical suggestions must cite source protocol or guideline.", "level": "FLAG"},
        ],
        "allowed_actions": ["draft_narrative", "suggest_assessment", "check_protocol_compliance"],
        "banned_actions": ["sign_narrative", "alter_vital_record", "modify_medication_order"],
    },
    {
        "domain": "dispatch",
        "name": "Dispatch & Ops Copilot",
        "explanation_rules": {
            "explain_routing_decision": True,
            "flag_capacity_warnings": True,
            "cite_geospatial_source": True,
        },
        "data_scope_controls": {
            "allowed_tables": ["missions", "crews", "vehicles", "dispatch_events"],
            "phi_fields_excluded": True,
        },
        "policies": [
            {"name": "No autonomous dispatch", "desc": "AI must not dispatch units without dispatcher confirmation.", "level": "BLOCK"},
            {"name": "Capacity warning required", "desc": "AI must flag when unit availability is below threshold.", "level": "FLAG"},
        ],
        "allowed_actions": ["suggest_unit_assignment", "estimate_eta", "flag_coverage_gap"],
        "banned_actions": ["dispatch_unit", "cancel_mission", "modify_dispatch_record"],
    },
    {
        "domain": "readiness",
        "name": "Readiness & Logistics Copilot",
        "explanation_rules": {
            "explain_expiry_urgency": True,
            "flag_credential_gaps": True,
            "cite_compliance_requirement": True,
        },
        "data_scope_controls": {
            "allowed_tables": ["inventory", "credentials", "fleet", "narcotics_logs"],
            "phi_fields_excluded": True,
        },
        "policies": [
            {"name": "No autonomous inventory adjustments", "desc": "AI must not modify inventory counts without human confirmation.", "level": "BLOCK"},
            {"name": "Credential gap escalation", "desc": "AI must escalate credential expirations approaching threshold.", "level": "FLAG"},
        ],
        "allowed_actions": ["check_inventory_levels", "flag_expiring_items", "suggest_restock"],
        "banned_actions": ["adjust_inventory", "modify_credential_record", "alter_fleet_status"],
    },
    {
        "domain": "support",
        "name": "Support & Success Copilot",
        "explanation_rules": {
            "use_empathetic_language": True,
            "cite_knowledge_base_source": True,
            "escalate_access_requests": True,
        },
        "data_scope_controls": {
            "allowed_tables": ["support_tickets", "knowledge_base", "user_profiles"],
            "phi_fields_excluded": True,
        },
        "policies": [
            {"name": "No access grants", "desc": "AI must not grant, revoke, or modify user permissions.", "level": "BLOCK"},
            {"name": "No PHI in support responses", "desc": "AI must not include patient health information in support threads.", "level": "BLOCK"},
            {"name": "Escalate admin requests", "desc": "Requests involving admin access must be routed to human support lead.", "level": "FLAG"},
        ],
        "allowed_actions": ["suggest_kb_article", "draft_response", "categorize_ticket"],
        "banned_actions": ["grant_access", "revoke_access", "modify_user_role", "share_phi"],
    },
    {
        "domain": "founder",
        "name": "Founder Executive Summary Copilot",
        "explanation_rules": {
            "use_scannable_format": True,
            "always_show_top_3": True,
            "cards_first_details_on_expand": True,
        },
        "data_scope_controls": {
            "allowed_tables": ["all_aggregate_views"],
            "phi_fields_excluded": True,
        },
        "policies": [
            {"name": "No operational mutations", "desc": "Founder AI view is read-only; no state changes from executive summary.", "level": "BLOCK"},
            {"name": "Aggregate-only data", "desc": "Founder AI must use aggregated metrics, never raw patient records.", "level": "BLOCK"},
        ],
        "allowed_actions": ["generate_summary", "compute_health_score", "suggest_governance_actions"],
        "banned_actions": ["modify_any_record", "dispatch_unit", "submit_claim", "grant_access"],
    },
]


class AISeedService:
    """Idempotent seeder for the 6 mandated domain copilots and tenant settings."""

    def __init__(self, db: Session, tenant_id: str) -> None:
        self._db = db
        self._tenant_id = tenant_id

    def seed_domain_copilots(self) -> list[AIDomainCopilot]:
        """Create or return existing copilots for all 6 mandatory domains."""
        results: list[AIDomainCopilot] = []

        for spec in COPILOT_DOMAINS:
            existing = (
                self._db.query(AIDomainCopilot)
                .filter(
                    AIDomainCopilot.tenant_id == self._tenant_id,
                    AIDomainCopilot.domain == spec["domain"],
                )
                .first()
            )
            if existing:
                results.append(existing)
                continue

            copilot = AIDomainCopilot(
                tenant_id=self._tenant_id,
                domain=spec["domain"],
                name=spec["name"],
                is_active=True,
                explanation_rules=spec["explanation_rules"],
                data_scope_controls=spec["data_scope_controls"],
            )
            self._db.add(copilot)
            self._db.flush()

            # Create domain policies
            for pol in spec["policies"]:
                self._db.add(
                    AIDomainPolicy(
                        tenant_id=self._tenant_id,
                        copilot_id=copilot.id,
                        policy_name=pol["name"],
                        policy_description=pol["desc"],
                        enforcement_level=pol["level"],
                        is_active=True,
                    )
                )

            # Create action boundaries
            for action_name in spec["allowed_actions"]:
                self._db.add(
                    AICopilotActionBoundary(
                        tenant_id=self._tenant_id,
                        copilot_id=copilot.id,
                        action_name=action_name,
                        is_allowed=True,
                        requires_human_review=False,
                    )
                )
            for action_name in spec["banned_actions"]:
                self._db.add(
                    AICopilotActionBoundary(
                        tenant_id=self._tenant_id,
                        copilot_id=copilot.id,
                        action_name=action_name,
                        is_allowed=False,
                        requires_human_review=True,
                    )
                )

            results.append(copilot)
            logger.info(
                "Seeded AI domain copilot: domain=%s name=%s tenant=%s",
                spec["domain"],
                spec["name"],
                self._tenant_id,
            )

        self._db.commit()
        return results

    def ensure_tenant_settings(self) -> AITenantSettings:
        """Create default tenant AI settings if none exist."""
        existing = (
            self._db.query(AITenantSettings)
            .filter(AITenantSettings.tenant_id == self._tenant_id)
            .first()
        )
        if existing:
            return existing

        settings = AITenantSettings(
            tenant_id=self._tenant_id,
        )
        self._db.add(settings)
        self._db.commit()
        self._db.refresh(settings)
        logger.info("Seeded AI tenant settings: tenant=%s", self._tenant_id)
        return settings

    def seed_all(self) -> dict:
        """Run all seed operations. Idempotent."""
        copilots = self.seed_domain_copilots()
        tenant_settings = self.ensure_tenant_settings()
        return {
            "copilots_count": len(copilots),
            "tenant_settings_id": str(tenant_settings.id),
        }
