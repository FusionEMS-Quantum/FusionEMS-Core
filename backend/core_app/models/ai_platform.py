from enum import Enum
from typing import Optional, Dict, Any, List
from datetime import datetime, timezone
from sqlalchemy import String, Integer, Boolean, DateTime, ForeignKey, JSON, Text, Column
from sqlalchemy.orm import mapped_column, Mapped, relationship

from core_app.models.tenant import TenantMixin
from core_app.db.base import Base

class AIRiskTier(str, Enum):
    LOW_RISK = "LOW_RISK"
    MODERATE_RISK = "MODERATE_RISK"
    HIGH_RISK = "HIGH_RISK"
    RESTRICTED = "RESTRICTED"

class AIWorkflowState(str, Enum):
    QUEUED = "QUEUED"
    CONTEXT_READY = "CONTEXT_READY"
    RUNNING = "RUNNING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    FALLBACK_USED = "FALLBACK_USED"
    HUMAN_REVIEW_REQUIRED = "HUMAN_REVIEW_REQUIRED"
    DISCARDED = "DISCARDED"

class AIGovernanceState(str, Enum):
    ALLOWED = "ALLOWED"
    LIMITED = "LIMITED"
    HUMAN_REVIEW_REQUIRED = "HUMAN_REVIEW_REQUIRED"
    BLOCKED = "BLOCKED"
    DISABLED = "DISABLED"

class AIOverrideState(str, Enum):
    AI_ACTIVE = "AI_ACTIVE"
    HUMAN_TAKEOVER = "HUMAN_TAKEOVER"
    REVIEW_PENDING = "REVIEW_PENDING"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"
    REGENERATE_REQUESTED = "REGENERATE_REQUESTED"
    AI_DISABLED_FOR_RECORD = "AI_DISABLED_FOR_RECORD"

class AIConfidenceLevel(str, Enum):
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"

class AIUseCase(Base, TenantMixin):
    __tablename__ = "ai_use_cases"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String, index=True, nullable=False)
    domain: Mapped[str] = mapped_column(String, index=True, nullable=False)
    purpose: Mapped[str] = mapped_column(Text, nullable=False)
    model_provider: Mapped[str] = mapped_column(String, nullable=False)
    prompt_template_id: Mapped[str] = mapped_column(String, nullable=False)
    risk_tier: Mapped[AIRiskTier] = mapped_column(String, nullable=False, default=AIRiskTier.MODERATE_RISK)
    is_enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    fallback_behavior: Mapped[str] = mapped_column(String, nullable=False)
    owner: Mapped[str] = mapped_column(String, nullable=False)
    last_review_date: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.now(timezone.utc))

    workflows: Mapped[List["AIWorkflowRun"]] = relationship("AIWorkflowRun", back_populates="use_case", cascade="all, delete-orphan")


class AIWorkflowRun(Base, TenantMixin):
    __tablename__ = "ai_workflow_runs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    use_case_id: Mapped[int] = mapped_column(Integer, ForeignKey("ai_use_cases.id"), nullable=False)
    correlation_id: Mapped[str] = mapped_column(String, index=True, nullable=False)
    state: Mapped[AIWorkflowState] = mapped_column(String, nullable=False, default=AIWorkflowState.QUEUED)
    governance_state: Mapped[AIGovernanceState] = mapped_column(String, nullable=False, default=AIGovernanceState.ALLOWED)
    override_state: Mapped[AIOverrideState] = mapped_column(String, nullable=False, default=AIOverrideState.AI_ACTIVE)
    
    context_snapshot: Mapped[Dict[str, Any]] = mapped_column(JSON, nullable=True)
    provider_response: Mapped[Dict[str, Any]] = mapped_column(JSON, nullable=True)
    fallback_used: Mapped[bool] = mapped_column(Boolean, default=False)
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    
    confidence_level: Mapped[Optional[AIConfidenceLevel]] = mapped_column(String, nullable=True)
    explanation_summary: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    next_step: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.now(timezone.utc))
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    use_case: Mapped["AIUseCase"] = relationship("AIUseCase", back_populates="workflows")
    override_events: Mapped[List["AIHumanOverrideEvent"]] = relationship("AIHumanOverrideEvent", back_populates="workflow", cascade="all, delete-orphan")


class AIHumanOverrideEvent(Base, TenantMixin):
    __tablename__ = "ai_human_override_events"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    workflow_id: Mapped[int] = mapped_column(Integer, ForeignKey("ai_workflow_runs.id"), nullable=False)
    actor_id: Mapped[str] = mapped_column(String, nullable=False)
    previous_state: Mapped[str] = mapped_column(String, nullable=False)
    new_state: Mapped[str] = mapped_column(String, nullable=False)
    reason: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.now(timezone.utc))

    workflow: Mapped["AIWorkflowRun"] = relationship("AIWorkflowRun", back_populates="override_events")


class AIDomainCopilot(Base, TenantMixin):
    __tablename__ = "ai_domain_copilots"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    domain: Mapped[str] = mapped_column(String, index=True, nullable=False)
    name: Mapped[str] = mapped_column(String, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    base_prompt_template_id: Mapped[str] = mapped_column(String, nullable=False)


class AIDomainPolicy(Base, TenantMixin):
    __tablename__ = "ai_domain_policies"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    copilot_id: Mapped[int] = mapped_column(Integer, ForeignKey("ai_domain_copilots.id"), nullable=False)
    policy_name: Mapped[str] = mapped_column(String, nullable=False)
    policy_description: Mapped[Text] = mapped_column(Text, nullable=False)
    enforcement_level: Mapped[str] = mapped_column(String, nullable=False) # e.g., BLOCK, FLAG


class AICopilotActionBoundary(Base, TenantMixin):
    __tablename__ = "ai_copilot_action_boundaries"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    copilot_id: Mapped[int] = mapped_column(Integer, ForeignKey("ai_domain_copilots.id"), nullable=False)
    action_name: Mapped[str] = mapped_column(String, nullable=False)
    is_allowed: Mapped[bool] = mapped_column(Boolean, default=False)
    requires_human_review: Mapped[bool] = mapped_column(Boolean, default=True)


class AICopilotAuditEvent(Base, TenantMixin):
    __tablename__ = "ai_copilot_audit_events"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    copilot_id: Mapped[int] = mapped_column(Integer, ForeignKey("ai_domain_copilots.id"), nullable=False)
    actor_id: Mapped[str] = mapped_column(String, nullable=False)
    action_attempted: Mapped[str] = mapped_column(String, nullable=False)
    was_blocked: Mapped[bool] = mapped_column(Boolean, nullable=False)
    reason: Mapped[str] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.now(timezone.utc))
