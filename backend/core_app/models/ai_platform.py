"""
AI Platform Models — Use-Case Registry, Workflow Orchestration,
Governance, Human Override, Domain Copilots, Explainability.

All models are tenant-scoped via TenantScopedMixin with UUID primary keys
following the established FusionEMS-Core pattern.
"""
# pylint: disable=not-callable,unsubscriptable-object
from __future__ import annotations

import uuid
from datetime import datetime
from enum import StrEnum

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from core_app.db.base import Base, TimestampMixin, UUIDPrimaryKeyMixin
from core_app.models.tenant import TenantScopedMixin

# ── Enumerations ─────────────────────────────────────────────────────────────

class AIRiskTier(StrEnum):
    LOW_RISK = "LOW_RISK"
    MODERATE_RISK = "MODERATE_RISK"
    HIGH_RISK = "HIGH_RISK"
    RESTRICTED = "RESTRICTED"


class AIWorkflowState(StrEnum):
    QUEUED = "QUEUED"
    CONTEXT_READY = "CONTEXT_READY"
    RUNNING = "RUNNING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    FALLBACK_USED = "FALLBACK_USED"
    HUMAN_REVIEW_REQUIRED = "HUMAN_REVIEW_REQUIRED"
    DISCARDED = "DISCARDED"


class AIGovernanceState(StrEnum):
    ALLOWED = "ALLOWED"
    LIMITED = "LIMITED"
    HUMAN_REVIEW_REQUIRED = "HUMAN_REVIEW_REQUIRED"
    BLOCKED = "BLOCKED"
    DISABLED = "DISABLED"


class AIOverrideState(StrEnum):
    AI_ACTIVE = "AI_ACTIVE"
    HUMAN_TAKEOVER = "HUMAN_TAKEOVER"
    REVIEW_PENDING = "REVIEW_PENDING"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"
    REGENERATE_REQUESTED = "REGENERATE_REQUESTED"
    AI_DISABLED_FOR_RECORD = "AI_DISABLED_FOR_RECORD"


class AIConfidenceLevel(StrEnum):
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"


class AIExplanationSeverity(StrEnum):
    BLOCKING = "BLOCKING"
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"
    INFORMATIONAL = "INFORMATIONAL"


class AIExplanationSource(StrEnum):
    AI_REVIEW = "AI_REVIEW"
    RULE_PLUS_AI = "RULE_PLUS_AI"
    PROVIDER_RESPONSE = "PROVIDER_RESPONSE"
    HUMAN_NOTE = "HUMAN_NOTE"


class AIHumanReviewRequirement(StrEnum):
    REQUIRED = "REQUIRED"
    RECOMMENDED = "RECOMMENDED"
    SAFE_TO_AUTO_PROCESS = "SAFE_TO_AUTO_PROCESS"


class AIPolicyEnforcement(StrEnum):
    BLOCK = "BLOCK"
    FLAG = "FLAG"
    LOG_ONLY = "LOG_ONLY"


# ── PART 3: AI USE-CASE REGISTRY ─────────────────────────────────────────────

class AIUseCase(Base, UUIDPrimaryKeyMixin, TenantScopedMixin, TimestampMixin):
    __tablename__ = "ai_use_cases"

    name: Mapped[str] = mapped_column(String(255), index=True, nullable=False)
    domain: Mapped[str] = mapped_column(String(100), index=True, nullable=False)
    purpose: Mapped[str] = mapped_column(Text, nullable=False)
    model_provider: Mapped[str] = mapped_column(String(100), nullable=False)
    prompt_template_id: Mapped[str] = mapped_column(String(100), nullable=False)
    risk_tier: Mapped[str] = mapped_column(
        String(20), nullable=False, default=AIRiskTier.MODERATE_RISK.value
    )
    is_enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    fallback_behavior: Mapped[str] = mapped_column(String(255), nullable=False)
    owner: Mapped[str] = mapped_column(String(255), nullable=False)
    allowed_data_scope: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    human_override_behavior: Mapped[str] = mapped_column(
        String(50), nullable=False, default="pause_and_review"
    )
    last_review_date: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    versions: Mapped[list[AIUseCaseVersion]] = relationship(
        back_populates="use_case", cascade="all, delete-orphan"
    )
    workflows: Mapped[list[AIWorkflowRun]] = relationship(
        back_populates="use_case", cascade="all, delete-orphan"
    )
    model_binding: Mapped[AIModelBinding | None] = relationship(
        back_populates="use_case", uselist=False, cascade="all, delete-orphan"
    )


class AIUseCaseVersion(Base, UUIDPrimaryKeyMixin, TenantScopedMixin, TimestampMixin):
    __tablename__ = "ai_use_case_versions"

    use_case_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("ai_use_cases.id"), nullable=False, index=True
    )
    version_number: Mapped[int] = mapped_column(nullable=False)
    changed_by: Mapped[str] = mapped_column(String(255), nullable=False)
    change_reason: Mapped[str] = mapped_column(Text, nullable=False)
    snapshot: Mapped[dict] = mapped_column(JSONB, nullable=False)

    use_case: Mapped[AIUseCase] = relationship(back_populates="versions")


class AIModelBinding(Base, UUIDPrimaryKeyMixin, TenantScopedMixin, TimestampMixin):
    __tablename__ = "ai_model_bindings"

    use_case_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("ai_use_cases.id"), nullable=False, unique=True
    )
    provider: Mapped[str] = mapped_column(String(100), nullable=False)
    model_name: Mapped[str] = mapped_column(String(100), nullable=False)
    max_tokens: Mapped[int] = mapped_column(nullable=False, default=4096)
    temperature: Mapped[float | None] = mapped_column(nullable=True)
    timeout_seconds: Mapped[int] = mapped_column(nullable=False, default=30)

    use_case: Mapped[AIUseCase] = relationship(back_populates="model_binding")


class AIPromptTemplate(Base, UUIDPrimaryKeyMixin, TenantScopedMixin, TimestampMixin):
    __tablename__ = "ai_prompt_templates"

    template_key: Mapped[str] = mapped_column(String(100), index=True, nullable=False)
    domain: Mapped[str] = mapped_column(String(100), index=True, nullable=False)
    system_prompt: Mapped[str] = mapped_column(Text, nullable=False)
    user_prompt_template: Mapped[str] = mapped_column(Text, nullable=False)
    version: Mapped[int] = mapped_column(nullable=False, default=1)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)


class AIUseCaseAuditEvent(Base, UUIDPrimaryKeyMixin, TenantScopedMixin):
    __tablename__ = "ai_use_case_audit_events"

    use_case_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("ai_use_cases.id"), nullable=False, index=True
    )
    actor_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    action: Mapped[str] = mapped_column(String(50), nullable=False)
    detail: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )


# ── PART 4: AI WORKFLOW ORCHESTRATION ─────────────────────────────────────────

class AIWorkflowRun(Base, UUIDPrimaryKeyMixin, TenantScopedMixin, TimestampMixin):
    __tablename__ = "ai_workflow_runs"

    use_case_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("ai_use_cases.id"), nullable=False, index=True
    )
    correlation_id: Mapped[str] = mapped_column(String(255), index=True, nullable=False)
    state: Mapped[str] = mapped_column(
        String(30), nullable=False, default=AIWorkflowState.QUEUED.value
    )
    governance_state: Mapped[str] = mapped_column(
        String(30), nullable=False, default=AIGovernanceState.ALLOWED.value
    )
    override_state: Mapped[str] = mapped_column(
        String(30), nullable=False, default=AIOverrideState.AI_ACTIVE.value
    )

    context_snapshot: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    provider_response: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    fallback_used: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)

    confidence_level: Mapped[str | None] = mapped_column(String(10), nullable=True)
    explanation_summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    next_step: Mapped[str | None] = mapped_column(Text, nullable=True)

    completed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    use_case: Mapped[AIUseCase] = relationship(back_populates="workflows")
    override_events: Mapped[list[AIHumanOverrideEvent]] = relationship(
        back_populates="workflow", cascade="all, delete-orphan"
    )
    context_snapshots: Mapped[list[AIContextSnapshot]] = relationship(
        back_populates="workflow", cascade="all, delete-orphan"
    )
    failure_records: Mapped[list[AIWorkflowFailure]] = relationship(
        back_populates="workflow", cascade="all, delete-orphan"
    )
    fallback_decisions: Mapped[list[AIFallbackDecision]] = relationship(
        back_populates="workflow", cascade="all, delete-orphan"
    )
    explanation_records: Mapped[list[AIExplanationRecord]] = relationship(
        back_populates="workflow", cascade="all, delete-orphan"
    )
    review_items: Mapped[list[AIReviewItem]] = relationship(
        back_populates="workflow", cascade="all, delete-orphan"
    )


class AIContextSnapshot(Base, UUIDPrimaryKeyMixin, TenantScopedMixin):
    __tablename__ = "ai_context_snapshots"

    workflow_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("ai_workflow_runs.id"), nullable=False, index=True
    )
    context_type: Mapped[str] = mapped_column(String(50), nullable=False)
    context_data: Mapped[dict] = mapped_column(JSONB, nullable=False)
    data_scope_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    workflow: Mapped[AIWorkflowRun] = relationship(back_populates="context_snapshots")


class AIWorkflowFailure(Base, UUIDPrimaryKeyMixin, TenantScopedMixin):
    __tablename__ = "ai_workflow_failures"

    workflow_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("ai_workflow_runs.id"), nullable=False, index=True
    )
    failure_type: Mapped[str] = mapped_column(String(50), nullable=False)
    error_code: Mapped[str | None] = mapped_column(String(50), nullable=True)
    error_message: Mapped[str] = mapped_column(Text, nullable=False)
    provider_metadata: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    workflow: Mapped[AIWorkflowRun] = relationship(back_populates="failure_records")


class AIFallbackDecision(Base, UUIDPrimaryKeyMixin, TenantScopedMixin):
    __tablename__ = "ai_fallback_decisions"

    workflow_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("ai_workflow_runs.id"), nullable=False, index=True
    )
    fallback_type: Mapped[str] = mapped_column(String(50), nullable=False)
    original_error: Mapped[str] = mapped_column(Text, nullable=False)
    fallback_output: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    workflow: Mapped[AIWorkflowRun] = relationship(back_populates="fallback_decisions")


# ── PART 5: AI SAFETY + GOVERNANCE ────────────────────────────────────────────

class AIGuardrailRule(Base, UUIDPrimaryKeyMixin, TenantScopedMixin, TimestampMixin):
    __tablename__ = "ai_guardrail_rules"

    domain: Mapped[str] = mapped_column(String(100), index=True, nullable=False)
    rule_name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    enforcement: Mapped[str] = mapped_column(
        String(20), nullable=False, default=AIPolicyEnforcement.BLOCK.value
    )
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    conditions: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)


class AIApprovalRequirement(Base, UUIDPrimaryKeyMixin, TenantScopedMixin, TimestampMixin):
    __tablename__ = "ai_approval_requirements"

    use_case_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("ai_use_cases.id"), nullable=True, index=True
    )
    domain: Mapped[str] = mapped_column(String(100), index=True, nullable=False)
    action_name: Mapped[str] = mapped_column(String(255), nullable=False)
    required_role: Mapped[str] = mapped_column(String(50), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)


class AIProtectedAction(Base, UUIDPrimaryKeyMixin, TenantScopedMixin, TimestampMixin):
    __tablename__ = "ai_protected_actions"

    action_name: Mapped[str] = mapped_column(String(255), nullable=False)
    domain: Mapped[str] = mapped_column(String(100), index=True, nullable=False)
    risk_tier: Mapped[str] = mapped_column(String(20), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    requires_human: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)


class AIGovernanceDecision(Base, UUIDPrimaryKeyMixin, TenantScopedMixin):
    __tablename__ = "ai_governance_decisions"

    workflow_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("ai_workflow_runs.id"), nullable=False, index=True
    )
    rule_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("ai_guardrail_rules.id"), nullable=True
    )
    decision: Mapped[str] = mapped_column(String(30), nullable=False)
    reason: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )


class AIRestrictedOutputEvent(Base, UUIDPrimaryKeyMixin, TenantScopedMixin):
    __tablename__ = "ai_restricted_output_events"

    workflow_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("ai_workflow_runs.id"), nullable=False, index=True
    )
    output_class: Mapped[str] = mapped_column(String(100), nullable=False)
    redacted_fields: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    reason: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )


# ── PART 6: AI EXPLAINABILITY + CONFIDENCE ────────────────────────────────────

class AIExplanationRecord(Base, UUIDPrimaryKeyMixin, TenantScopedMixin):
    __tablename__ = "ai_explanation_records"

    workflow_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("ai_workflow_runs.id"), nullable=False, index=True
    )
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    severity: Mapped[str] = mapped_column(String(20), nullable=False)
    source: Mapped[str] = mapped_column(String(30), nullable=False)
    what_is_wrong: Mapped[str] = mapped_column(Text, nullable=False)
    why_it_matters: Mapped[str] = mapped_column(Text, nullable=False)
    what_you_should_do: Mapped[str] = mapped_column(Text, nullable=False)
    domain_context: Mapped[str] = mapped_column(Text, nullable=False)
    human_review: Mapped[str] = mapped_column(String(30), nullable=False)
    confidence: Mapped[str] = mapped_column(String(10), nullable=False)
    simple_mode_summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    workflow: Mapped[AIWorkflowRun] = relationship(back_populates="explanation_records")


class AIConfidenceRecord(Base, UUIDPrimaryKeyMixin, TenantScopedMixin):
    __tablename__ = "ai_confidence_records"

    workflow_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("ai_workflow_runs.id"), nullable=False, index=True
    )
    confidence_level: Mapped[str] = mapped_column(String(10), nullable=False)
    confidence_score: Mapped[float | None] = mapped_column(nullable=True)
    reasoning: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )


class AIOutputTag(Base, UUIDPrimaryKeyMixin, TenantScopedMixin):
    __tablename__ = "ai_output_tags"

    workflow_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("ai_workflow_runs.id"), nullable=False, index=True
    )
    tag_key: Mapped[str] = mapped_column(String(100), nullable=False)
    tag_value: Mapped[str] = mapped_column(String(255), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )


# ── PART 7: HUMAN OVERRIDE + REVIEW ──────────────────────────────────────────

class AIHumanOverrideEvent(Base, UUIDPrimaryKeyMixin, TenantScopedMixin):
    __tablename__ = "ai_human_override_events"

    workflow_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("ai_workflow_runs.id"), nullable=False, index=True
    )
    actor_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    previous_state: Mapped[str] = mapped_column(String(30), nullable=False)
    new_state: Mapped[str] = mapped_column(String(30), nullable=False)
    reason: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    workflow: Mapped[AIWorkflowRun] = relationship(back_populates="override_events")


class AIReviewItem(Base, UUIDPrimaryKeyMixin, TenantScopedMixin, TimestampMixin):
    __tablename__ = "ai_review_items"

    workflow_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("ai_workflow_runs.id"), nullable=False, index=True
    )
    review_type: Mapped[str] = mapped_column(String(50), nullable=False)
    priority: Mapped[str] = mapped_column(String(20), nullable=False, default="MEDIUM")
    assigned_to: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), nullable=True
    )
    status: Mapped[str] = mapped_column(
        String(30), nullable=False, default=AIOverrideState.REVIEW_PENDING.value
    )
    resolved_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    workflow: Mapped[AIWorkflowRun] = relationship(back_populates="review_items")
    approval_events: Mapped[list[AIApprovalEvent]] = relationship(
        back_populates="review_item", cascade="all, delete-orphan"
    )
    rejection_events: Mapped[list[AIRejectionEvent]] = relationship(
        back_populates="review_item", cascade="all, delete-orphan"
    )


class AIApprovalEvent(Base, UUIDPrimaryKeyMixin, TenantScopedMixin):
    __tablename__ = "ai_approval_events"

    review_item_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("ai_review_items.id"), nullable=False, index=True
    )
    actor_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    review_item: Mapped[AIReviewItem] = relationship(back_populates="approval_events")


class AIRejectionEvent(Base, UUIDPrimaryKeyMixin, TenantScopedMixin):
    __tablename__ = "ai_rejection_events"

    review_item_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("ai_review_items.id"), nullable=False, index=True
    )
    actor_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    reason: Mapped[str] = mapped_column(Text, nullable=False)
    regenerate_requested: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    review_item: Mapped[AIReviewItem] = relationship(back_populates="rejection_events")


class AIResumeEvent(Base, UUIDPrimaryKeyMixin, TenantScopedMixin):
    __tablename__ = "ai_resume_events"

    workflow_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("ai_workflow_runs.id"), nullable=False, index=True
    )
    actor_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    reason: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )


# ── PART 8: DOMAIN COPILOTS ──────────────────────────────────────────────────

class AIDomainCopilot(Base, UUIDPrimaryKeyMixin, TenantScopedMixin, TimestampMixin):
    __tablename__ = "ai_domain_copilots"

    domain: Mapped[str] = mapped_column(String(100), index=True, nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    base_prompt_template_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("ai_prompt_templates.id"), nullable=True
    )
    explanation_rules: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    data_scope_controls: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)

    policies: Mapped[list[AIDomainPolicy]] = relationship(
        back_populates="copilot", cascade="all, delete-orphan"
    )
    action_boundaries: Mapped[list[AICopilotActionBoundary]] = relationship(
        back_populates="copilot", cascade="all, delete-orphan"
    )
    audit_events: Mapped[list[AICopilotAuditEvent]] = relationship(
        back_populates="copilot", cascade="all, delete-orphan"
    )


class AIDomainPolicy(Base, UUIDPrimaryKeyMixin, TenantScopedMixin, TimestampMixin):
    __tablename__ = "ai_domain_policies"

    copilot_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("ai_domain_copilots.id"), nullable=False, index=True
    )
    policy_name: Mapped[str] = mapped_column(String(255), nullable=False)
    policy_description: Mapped[str] = mapped_column(Text, nullable=False)
    enforcement_level: Mapped[str] = mapped_column(
        String(20), nullable=False, default=AIPolicyEnforcement.BLOCK.value
    )
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    copilot: Mapped[AIDomainCopilot] = relationship(back_populates="policies")


class AICopilotActionBoundary(Base, UUIDPrimaryKeyMixin, TenantScopedMixin, TimestampMixin):
    __tablename__ = "ai_copilot_action_boundaries"

    copilot_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("ai_domain_copilots.id"), nullable=False, index=True
    )
    action_name: Mapped[str] = mapped_column(String(255), nullable=False)
    is_allowed: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    requires_human_review: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    copilot: Mapped[AIDomainCopilot] = relationship(back_populates="action_boundaries")


class AICopilotAuditEvent(Base, UUIDPrimaryKeyMixin, TenantScopedMixin):
    __tablename__ = "ai_copilot_audit_events"

    copilot_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("ai_domain_copilots.id"), nullable=False, index=True
    )
    actor_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    action_attempted: Mapped[str] = mapped_column(String(255), nullable=False)
    was_blocked: Mapped[bool] = mapped_column(Boolean, nullable=False)
    block_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    copilot: Mapped[AIDomainCopilot] = relationship(back_populates="audit_events")


# ── AI QUEUE ITEM (Directive Part 4 — explicit queue object) ──────────────────

class AIQueueItem(Base, UUIDPrimaryKeyMixin, TenantScopedMixin):
    __tablename__ = "ai_queue_items"

    workflow_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("ai_workflow_runs.id"), nullable=False, index=True
    )
    use_case_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("ai_use_cases.id"), nullable=False, index=True
    )
    queue_name: Mapped[str] = mapped_column(
        String(50), nullable=False, default="default"
    )
    priority: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    payload: Mapped[dict] = mapped_column(JSONB, nullable=False, server_default="{}")
    status: Mapped[str] = mapped_column(
        String(30), nullable=False, default="PENDING"
    )
    max_retries: Mapped[int] = mapped_column(Integer, nullable=False, default=3)
    retry_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    scheduled_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    picked_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    started_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    completed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )


# ── AI USER-FACING SUMMARY (Directive Part 6 — explicit summary object) ──────

class AIUserFacingSummary(Base, UUIDPrimaryKeyMixin, TenantScopedMixin):
    __tablename__ = "ai_user_facing_summaries"

    workflow_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("ai_workflow_runs.id"), nullable=False, index=True
    )
    what_happened: Mapped[str] = mapped_column(Text, nullable=False)
    why_it_matters: Mapped[str] = mapped_column(Text, nullable=False)
    do_this_next: Mapped[str] = mapped_column(Text, nullable=False)
    confidence: Mapped[str] = mapped_column(String(10), nullable=False)
    domain: Mapped[str] = mapped_column(String(100), nullable=False)
    is_simple_mode: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )


# ── AI TENANT SETTINGS (Directive Part 5 — tenant-level AI config) ───────────

class AITenantSettings(Base, UUIDPrimaryKeyMixin, TenantScopedMixin, TimestampMixin):
    __tablename__ = "ai_tenant_settings"

    ai_enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    default_risk_tier: Mapped[str] = mapped_column(
        String(20), nullable=False, default=AIRiskTier.MODERATE_RISK.value
    )
    auto_approve_low_risk: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    require_human_review_high_risk: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    max_concurrent_workflows: Mapped[int] = mapped_column(Integer, nullable=False, default=10)
    global_confidence_threshold: Mapped[str] = mapped_column(
        String(10), nullable=False, default=AIConfidenceLevel.MEDIUM.value
    )
    allowed_domains: Mapped[dict] = mapped_column(
        JSONB, nullable=False, default=lambda: {"billing": True, "clinical": True, "dispatch": True, "readiness": True, "support": True, "founder": True}
    )
    environment_ai_toggle: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
