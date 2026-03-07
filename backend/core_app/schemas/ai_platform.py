from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from core_app.models.ai_platform import (
    AIConfidenceLevel,
    AIExplanationSeverity,
    AIExplanationSource,
    AIGovernanceState,
    AIHumanReviewRequirement,
    AIOverrideState,
    AIRiskTier,
    AIWorkflowState,
)


# ── AI USE-CASE REGISTRY ─────────────────────────────────────────────────────

class AIUseCaseCreate(BaseModel):
    name: str = Field(..., max_length=255)
    domain: str = Field(..., max_length=100)
    purpose: str
    model_provider: str = Field(..., max_length=100)
    prompt_template_id: str = Field(..., max_length=100)
    risk_tier: AIRiskTier
    fallback_behavior: str = Field(..., max_length=255)
    owner: str = Field(..., max_length=255)
    allowed_data_scope: dict = Field(default_factory=dict)
    human_override_behavior: str = Field(default="pause_and_review", max_length=50)


class AIUseCaseUpdate(BaseModel):
    name: str | None = None
    purpose: str | None = None
    risk_tier: AIRiskTier | None = None
    is_enabled: bool | None = None
    fallback_behavior: str | None = None
    owner: str | None = None
    change_reason: str = Field(..., min_length=1)


class AIUseCaseResponse(BaseModel):
    id: uuid.UUID
    name: str
    domain: str
    purpose: str
    model_provider: str
    prompt_template_id: str
    risk_tier: str
    is_enabled: bool
    fallback_behavior: str
    owner: str
    allowed_data_scope: dict
    human_override_behavior: str
    last_review_date: datetime
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


# ── AI WORKFLOW ORCHESTRATION ─────────────────────────────────────────────────

class AIWorkflowStartRequest(BaseModel):
    use_case_id: uuid.UUID
    correlation_id: str = Field(..., max_length=255)
    context_snapshot: dict | None = None


class AIWorkflowRunResponse(BaseModel):
    id: uuid.UUID
    use_case_id: uuid.UUID
    correlation_id: str
    state: str
    governance_state: str
    override_state: str
    fallback_used: bool
    error_message: str | None = None
    confidence_level: str | None = None
    explanation_summary: str | None = None
    next_step: str | None = None
    created_at: datetime
    completed_at: datetime | None = None

    model_config = ConfigDict(from_attributes=True)


class AIInferenceResultRequest(BaseModel):
    provider_response: dict
    explanation: AIExplanationInput


class AIExplanationInput(BaseModel):
    title: str = Field(..., max_length=255)
    severity: AIExplanationSeverity
    source: AIExplanationSource
    what_is_wrong: str
    why_it_matters: str
    what_you_should_do: str
    domain_context: str
    human_review: AIHumanReviewRequirement
    confidence: AIConfidenceLevel
    simple_mode_summary: str | None = None


class AIExplanationResponse(BaseModel):
    id: uuid.UUID
    workflow_id: uuid.UUID
    title: str
    severity: str
    source: str
    what_is_wrong: str
    why_it_matters: str
    what_you_should_do: str
    domain_context: str
    human_review: str
    confidence: str
    simple_mode_summary: str | None = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


# ── HUMAN OVERRIDE ────────────────────────────────────────────────────────────

class AIHumanOverrideRequest(BaseModel):
    new_state: AIOverrideState
    reason: str = Field(..., min_length=1)


class AIReviewItemResponse(BaseModel):
    id: uuid.UUID
    workflow_id: uuid.UUID
    review_type: str
    priority: str
    assigned_to: uuid.UUID | None = None
    status: str
    resolved_at: datetime | None = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class AIReviewActionRequest(BaseModel):
    action: str = Field(..., pattern="^(approve|reject)$")
    reason: str | None = None
    regenerate_requested: bool = False


# ── GOVERNANCE ────────────────────────────────────────────────────────────────

class AIGuardrailRuleResponse(BaseModel):
    id: uuid.UUID
    domain: str
    rule_name: str
    description: str
    enforcement: str
    is_active: bool
    conditions: dict
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class AIProtectedActionResponse(BaseModel):
    id: uuid.UUID
    action_name: str
    domain: str
    risk_tier: str
    description: str
    requires_human: bool
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


# ── PROMPT TEMPLATES ──────────────────────────────────────────────────────────

class AIPromptTemplateCreate(BaseModel):
    template_key: str = Field(..., max_length=100)
    domain: str = Field(..., max_length=100)
    system_prompt: str
    user_prompt_template: str


class AIPromptTemplateUpdate(BaseModel):
    system_prompt: str | None = None
    user_prompt_template: str | None = None
    is_active: bool | None = None


class AIPromptTemplateResponse(BaseModel):
    id: uuid.UUID
    template_key: str
    domain: str
    system_prompt: str
    user_prompt_template: str
    version: int
    is_active: bool
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


# ── DOMAIN COPILOT ────────────────────────────────────────────────────────────

class AIDomainCopilotResponse(BaseModel):
    id: uuid.UUID
    domain: str
    name: str
    is_active: bool
    explanation_rules: dict
    data_scope_controls: dict
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


# ── FOUNDER COMMAND CENTER ────────────────────────────────────────────────────

class AICommandCenterMetrics(BaseModel):
    health_score: float
    total_use_cases: int
    enabled_use_cases: int
    disabled_workflows: int
    low_confidence_count: int
    review_queue_count: int
    failed_runs_count: int
    risk_tier_breakdown: dict[str, int]
    recent_reviews: list[AIReviewQueueEntry]
    top_actions: list[AIGovernanceAction]


class AIReviewQueueEntry(BaseModel):
    review_id: uuid.UUID
    workflow_id: uuid.UUID
    correlation_id: str
    use_case_name: str
    domain: str
    priority: str
    summary: str | None = None
    created_at: datetime


class AIGovernanceAction(BaseModel):
    action_type: str
    title: str
    description: str
    severity: str
    target_id: uuid.UUID | None = None


# Rebuild forward references
AICommandCenterMetrics.model_rebuild()
