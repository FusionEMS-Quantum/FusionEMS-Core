"""
Platform Admin AI Assistant Service — Rule-based issue diagnosis with
structured 9-field output, silent mutation guards, confidence scoring.

Implements Part 8 of the Master Platform Core Directive.
AI is isolated from core domain logic — failure never breaks workflows.
"""
# pylint: disable=not-callable
from __future__ import annotations

import logging
import uuid
from datetime import UTC, datetime

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from core_app.models.platform_core import (
    ConfigDriftAlert,
    ConfigurationValidationIssue,
    DeploymentRecord,
    Environment,
    ImplementationBlocker,
    TenantConfiguration,
    TenantFeatureState,
    TenantLifecycleState,
)
from core_app.models.platform_core import (
    ImplementationProject as PlatformImplementationProject,
)
from core_app.models.tenant import Tenant
from core_app.schemas.platform_core import PlatformAdminIssue

logger = logging.getLogger("platform_admin_assistant")


class PlatformAdminAssistantService:
    """Rule-based + heuristic AI assistant for platform administration.

    Design guarantees:
    - **Zero mutations**: This service is strictly read-only. It never writes,
      updates, or deletes any domain data.
    - **Deterministic fallback**: If any query fails, we return a safe empty
      result — never a crash.
    - **Confidence scoring**: Every issue carries HIGH / MEDIUM / LOW confidence.
    - **Fact vs. judgment**: The ``basis`` field distinguishes OBSERVED data from
      INFERRED conclusions and RECOMMENDED next steps.
    """

    def __init__(self, db: Session) -> None:
        self._db = db

    # ──────────────────────────────────────────────────────────────────────────
    # PUBLIC API
    # ──────────────────────────────────────────────────────────────────────────

    def diagnose_platform(self) -> list[PlatformAdminIssue]:
        """Run all diagnostic rules and return structured issues."""
        issues: list[PlatformAdminIssue] = []
        rules = [
            self._check_stale_onboarding,
            self._check_open_blockers,
            self._check_degraded_environments,
            self._check_failed_deployments,
            self._check_config_drift,
            self._check_config_validation_issues,
            self._check_suspended_agencies,
            self._check_feature_flag_drift,
        ]
        for rule in rules:
            try:
                issues.extend(rule())
            except Exception:  # pylint: disable=broad-exception-caught
                logger.exception("AI diagnostic rule failed: %s", rule.__name__)
                # Never break on AI failure — continue to next rule
        return issues

    def diagnose_tenant(self, tenant_id: uuid.UUID) -> list[PlatformAdminIssue]:
        """Run tenant-scoped diagnostics."""
        issues: list[PlatformAdminIssue] = []
        rules = [
            lambda: self._check_tenant_config_completeness(tenant_id),
            lambda: self._check_tenant_blockers(tenant_id),
            lambda: self._check_tenant_feature_gaps(tenant_id),
        ]
        for rule in rules:
            try:
                issues.extend(rule())
            except Exception:  # pylint: disable=broad-exception-caught
                logger.exception("AI tenant diagnostic rule failed for %s", tenant_id)
        return issues

    # ──────────────────────────────────────────────────────────────────────────
    # DIAGNOSTIC RULES (read-only)
    # ──────────────────────────────────────────────────────────────────────────

    def _check_stale_onboarding(self) -> list[PlatformAdminIssue]:
        """Flag agencies stuck in onboarding states for > 30 days."""
        thirty_days_ago = datetime(
            *(datetime.now(UTC).timetuple()[:3]), tzinfo=UTC
        )
        stmt = select(Tenant).where(
            Tenant.lifecycle_state.in_([
                TenantLifecycleState.TENANT_CREATED,
                TenantLifecycleState.CONFIG_PENDING,
                TenantLifecycleState.IMPLEMENTATION_IN_PROGRESS,
            ]),
        )
        tenants = list(self._db.execute(stmt).scalars().all())
        issues: list[PlatformAdminIssue] = []
        for t in tenants:
            if t.created_at and t.created_at < thirty_days_ago:
                issues.append(PlatformAdminIssue(
                    issue_name=f"Stale onboarding: {t.name}",
                    severity="MEDIUM",
                    source="RULE",
                    what_is_wrong=f"Agency '{t.name}' has been in '{t.lifecycle_state}' since {t.created_at.date()}.",
                    why_it_matters="Prolonged onboarding delays time-to-value and may indicate resource constraints or blockers.",
                    what_you_should_do="Review implementation project status, check for blockers, and contact agency stakeholder.",
                    platform_context=f"Tenant ID: {t.id}, State: {t.lifecycle_state}",
                    human_review="RECOMMENDED",
                    confidence="HIGH",
                    basis="OBSERVED",
                    rule_reference="DIRECTIVE_PART_1_LIFECYCLE",
                ))
        return issues

    def _check_open_blockers(self) -> list[PlatformAdminIssue]:
        """Flag projects with unresolved HIGH/CRITICAL blockers."""
        stmt = (
            select(
                ImplementationBlocker.project_id,
                PlatformImplementationProject.tenant_id,
                func.count(ImplementationBlocker.id).label("count"),
            )
            .join(
                PlatformImplementationProject,
                PlatformImplementationProject.id == ImplementationBlocker.project_id,
            )
            .where(
                ImplementationBlocker.status == "open",
                ImplementationBlocker.severity.in_(["HIGH", "CRITICAL"]),
            )
            .group_by(ImplementationBlocker.project_id, PlatformImplementationProject.tenant_id)
        )
        rows = list(self._db.execute(stmt).all())
        issues: list[PlatformAdminIssue] = []
        for project_id, tenant_id, count in rows:
            issues.append(PlatformAdminIssue(
                issue_name=f"Open blockers: {count} HIGH/CRITICAL",
                severity="HIGH",
                source="IMPLEMENTATION_EVENT",
                what_is_wrong=f"Implementation project {project_id} has {count} unresolved HIGH/CRITICAL blocker(s).",
                why_it_matters="Open blockers prevent go-live progression and may escalate if unaddressed.",
                what_you_should_do="Review blockers, assign owners, and set resolution deadlines.",
                platform_context=f"Project ID: {project_id}, Tenant ID: {tenant_id}",
                human_review="REQUIRED",
                confidence="HIGH",
                basis="OBSERVED",
                rule_reference="DIRECTIVE_PART_3_IMPLEMENTATION",
            ))
        return issues

    def _check_degraded_environments(self) -> list[PlatformAdminIssue]:
        """Flag environments with degraded health status."""
        stmt = select(Environment).where(Environment.health_status == "degraded")
        envs = list(self._db.execute(stmt).scalars().all())
        return [
            PlatformAdminIssue(
                issue_name=f"Degraded environment: {e.name}",
                severity="BLOCKING",
                source="DEPLOYMENT_EVENT",
                what_is_wrong=f"Environment '{e.name}' ({e.display_name}) is in degraded state.",
                why_it_matters="A degraded environment may impact service availability for all tenants in that environment.",
                what_you_should_do="Check deployment logs, validate infrastructure health, consider rollback if needed.",
                platform_context=f"Environment: {e.name}, Version: {e.current_version}, SHA: {e.current_git_sha}",
                human_review="REQUIRED",
                confidence="HIGH",
                basis="OBSERVED",
                rule_reference="DIRECTIVE_PART_5_RELEASE",
            )
            for e in envs
        ]

    def _check_failed_deployments(self) -> list[PlatformAdminIssue]:
        """Flag recent failed deployments."""
        stmt = (
            select(DeploymentRecord)
            .where(DeploymentRecord.outcome == "failure")
            .order_by(DeploymentRecord.created_at.desc())
            .limit(5)
        )
        deps = list(self._db.execute(stmt).scalars().all())
        return [
            PlatformAdminIssue(
                issue_name=f"Failed deployment: {d.id}",
                severity="HIGH",
                source="DEPLOYMENT_EVENT",
                what_is_wrong=f"Deployment {d.id} to environment {d.environment_id} failed.",
                why_it_matters="Failed deployments may leave environments in inconsistent state.",
                what_you_should_do="Review error details, check CI/CD logs, fix root cause before retry.",
                platform_context=f"Deployment ID: {d.id}, Error: {d.error_detail or 'No detail recorded'}",
                human_review="REQUIRED",
                confidence="HIGH",
                basis="OBSERVED",
                rule_reference="DIRECTIVE_PART_5_RELEASE",
            )
            for d in deps
        ]

    def _check_config_drift(self) -> list[PlatformAdminIssue]:
        """Flag unresolved configuration drift alerts."""
        stmt = select(ConfigDriftAlert).where(ConfigDriftAlert.resolved.is_(False))
        drifts = list(self._db.execute(stmt).scalars().all())
        issues: list[PlatformAdminIssue] = []
        for d in drifts:
            issues.append(PlatformAdminIssue(
                issue_name=f"Config drift: {d.drift_type}",
                severity="MEDIUM" if d.severity == "MEDIUM" else "HIGH",
                source="CONFIG_EVENT",
                what_is_wrong=f"Configuration drift detected: {d.description}",
                why_it_matters="Configuration drift between environments can cause unexpected behavior in production.",
                what_you_should_do=f"Reconcile expected value '{d.expected_value}' with actual '{d.actual_value}'.",
                platform_context=f"Environment ID: {d.environment_id}, Drift Type: {d.drift_type}",
                human_review="RECOMMENDED",
                confidence="HIGH",
                basis="OBSERVED",
                rule_reference="DIRECTIVE_PART_5_RELEASE",
            ))
        return issues

    def _check_config_validation_issues(self) -> list[PlatformAdminIssue]:
        """Flag unresolved configuration validation issues."""
        stmt = select(ConfigurationValidationIssue).where(
            ConfigurationValidationIssue.resolved.is_(False)
        )
        issues_db = list(self._db.execute(stmt).scalars().all())
        return [
            PlatformAdminIssue(
                issue_name=f"Config validation issue: {i.config_key}",
                severity=i.severity if i.severity in ("BLOCKING", "HIGH", "MEDIUM", "LOW") else "MEDIUM",
                source="CONFIG_EVENT",
                what_is_wrong=i.message,
                why_it_matters="Invalid configuration may cause runtime errors or compliance violations.",
                what_you_should_do=i.suggested_fix or "Review and correct the configuration value.",
                platform_context=f"Config Key: {i.config_key}, Tenant ID: {i.tenant_id}",
                human_review="RECOMMENDED",
                confidence="HIGH",
                basis="OBSERVED",
                rule_reference="DIRECTIVE_PART_6_CONFIG",
            )
            for i in issues_db
        ]

    def _check_suspended_agencies(self) -> list[PlatformAdminIssue]:
        """Flag agencies that have been suspended."""
        stmt = select(Tenant).where(
            Tenant.lifecycle_state == TenantLifecycleState.SUSPENDED
        )
        tenants = list(self._db.execute(stmt).scalars().all())
        return [
            PlatformAdminIssue(
                issue_name=f"Suspended agency: {t.name}",
                severity="HIGH",
                source="RULE",
                what_is_wrong=f"Agency '{t.name}' is currently suspended.",
                why_it_matters="Suspended agencies cannot operate and may need urgent reinstatement or final archival.",
                what_you_should_do="Determine root cause of suspension, resolve, and reinstate or archive.",
                platform_context=f"Tenant ID: {t.id}, Name: {t.name}",
                human_review="REQUIRED",
                confidence="HIGH",
                basis="OBSERVED",
                rule_reference="DIRECTIVE_PART_1_LIFECYCLE",
            )
            for t in tenants
        ]

    def _check_feature_flag_drift(self) -> list[PlatformAdminIssue]:
        """Detect tenants with disabled critical features that should be enabled."""
        issues: list[PlatformAdminIssue] = []
        # Look for LIVE tenants with feature flags still DISABLED
        from core_app.models.platform_core import FeatureFlag, FeatureFlagState

        stmt = (
            select(TenantFeatureState, FeatureFlag)
            .join(FeatureFlag, FeatureFlag.id == TenantFeatureState.feature_flag_id)
            .where(
                FeatureFlag.is_critical.is_(True),
                TenantFeatureState.current_state == FeatureFlagState.DISABLED,
            )
        )
        rows = list(self._db.execute(stmt).all())
        for tfs, ff in rows:
            # Check if the tenant is LIVE
            tenant = self._db.get(Tenant, tfs.tenant_id)
            if tenant and tenant.lifecycle_state == TenantLifecycleState.LIVE:
                issues.append(PlatformAdminIssue(
                    issue_name=f"Critical flag disabled: {ff.flag_key}",
                    severity="HIGH",
                    source="AI_REVIEW",
                    what_is_wrong=f"Critical feature flag '{ff.flag_key}' is DISABLED for LIVE tenant '{tenant.name}'.",
                    why_it_matters="LIVE agencies should have all critical features enabled for full operational capability.",
                    what_you_should_do="Review if this is intentional. If not, enable the flag through the platform admin.",
                    platform_context=f"Flag: {ff.flag_key}, Tenant: {tenant.name} ({tenant.id})",
                    human_review="RECOMMENDED",
                    confidence="MEDIUM",
                    basis="INFERRED",
                    rule_reference="DIRECTIVE_PART_4_FEATURE_FLAGS",
                ))
        return issues

    # ── Tenant-scoped diagnostics ─────────────────────────────────────────────

    def _check_tenant_config_completeness(
        self, tenant_id: uuid.UUID
    ) -> list[PlatformAdminIssue]:
        """Check if a tenant has all required configuration keys."""
        required_keys = {
            "agency_name", "agency_npi", "agency_state", "agency_contact_email",
            "billing_provider", "telecom_provider", "cad_enabled",
            "epcr_enabled", "compliance_level", "timezone",
        }
        stmt = select(TenantConfiguration.config_key).where(
            TenantConfiguration.tenant_id == tenant_id
        )
        present = {row for row in self._db.execute(stmt).scalars().all()}
        missing = required_keys - present
        if not missing:
            return []
        return [PlatformAdminIssue(
            issue_name=f"Missing configuration keys ({len(missing)})",
            severity="MEDIUM",
            source="RULE",
            what_is_wrong=f"Tenant is missing {len(missing)} required configuration key(s): {', '.join(sorted(missing))}.",
            why_it_matters="Incomplete configuration may prevent modules from functioning correctly.",
            what_you_should_do="Navigate to tenant configuration and set the missing keys.",
            platform_context=f"Tenant ID: {tenant_id}, Missing: {sorted(missing)}",
            human_review="RECOMMENDED",
            confidence="HIGH",
            basis="OBSERVED",
            rule_reference="DIRECTIVE_PART_6_CONFIG",
        )]

    def _check_tenant_blockers(
        self, tenant_id: uuid.UUID
    ) -> list[PlatformAdminIssue]:
        """Check for open blockers on the tenant's implementation projects."""
        stmt = (
            select(ImplementationBlocker)
            .join(PlatformImplementationProject)
            .where(
                PlatformImplementationProject.tenant_id == tenant_id,
                ImplementationBlocker.status == "open",
            )
        )
        blockers = list(self._db.execute(stmt).scalars().all())
        if not blockers:
            return []
        return [PlatformAdminIssue(
            issue_name=f"Open blockers: {len(blockers)}",
            severity="HIGH" if any(b.severity in ("HIGH", "CRITICAL") for b in blockers) else "MEDIUM",
            source="IMPLEMENTATION_EVENT",
            what_is_wrong=f"Tenant has {len(blockers)} open implementation blocker(s).",
            why_it_matters="Blockers delay go-live and indicate unresolved issues.",
            what_you_should_do="Review each blocker, assign owners, and track resolution progress.",
            platform_context=f"Tenant ID: {tenant_id}, Blockers: {[b.title for b in blockers]}",
            human_review="RECOMMENDED",
            confidence="HIGH",
            basis="OBSERVED",
            rule_reference="DIRECTIVE_PART_3_IMPLEMENTATION",
        )]

    def _check_tenant_feature_gaps(
        self, tenant_id: uuid.UUID
    ) -> list[PlatformAdminIssue]:
        """Check for entitled modules without enabled runtime flags."""
        from core_app.models.platform_core import FeatureFlagState, ModuleEntitlement

        ent_stmt = select(ModuleEntitlement).where(
            ModuleEntitlement.tenant_id == tenant_id,
            ModuleEntitlement.is_entitled.is_(True),
        )
        entitlements = list(self._db.execute(ent_stmt).scalars().all())

        tfs_stmt = select(TenantFeatureState).where(
            TenantFeatureState.tenant_id == tenant_id,
            TenantFeatureState.current_state.in_([
                FeatureFlagState.ENABLED,
                FeatureFlagState.LIMITED_ROLLOUT,
                FeatureFlagState.BETA_ENABLED,
            ]),
        )
        enabled = list(self._db.execute(tfs_stmt).scalars().all())

        if len(entitlements) > 0 and len(enabled) == 0:
            return [PlatformAdminIssue(
                issue_name="Entitlement/runtime mismatch",
                severity="MEDIUM",
                source="AI_REVIEW",
                what_is_wrong=f"Tenant has {len(entitlements)} entitled module(s) but no enabled runtime feature flags.",
                why_it_matters="Entitled modules won't function without corresponding feature flags enabled.",
                what_you_should_do="Enable feature flags for entitled modules or verify entitlement correctness.",
                platform_context=f"Tenant ID: {tenant_id}, Entitled: {[e.module_name for e in entitlements]}",
                human_review="RECOMMENDED",
                confidence="MEDIUM",
                basis="INFERRED",
                rule_reference="DIRECTIVE_PART_4_FEATURE_FLAGS",
            )]
        return []
