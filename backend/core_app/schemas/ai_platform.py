from pydantic import BaseModel, Field
from typing import Optional, Dict, Any, List
from datetime import datetime
from enum import Enum

from .ai_platform import AIRiskTier, AIWorkflowState, AIGovernanceState, AIOverrideState, AIConfidenceLevel

class AIExplanationResponse(BaseModel):
    title: str = Field(..., description="Short title")
    severity: str = Field(..., description="BLOCKING, HIGH, MEDIUM, LOW, or INFORMATIONAL")
    source: str = Field(..., description="AI REVIEW, RULE + AI, PROVIDER RESPONSE, or HUMAN NOTE")
    what_is_wrong: str = Field(..., description="Exact problem")
    why_it_matters: str = Field(..., description="Plain-English impact")
    what_you_should_do: str = Field(..., description="Concrete next step")
    domain_context: str = Field(..., description="Short explanation")
    human_review: str = Field(..., description="REQUIRED, RECOMMENDED, or SAFE TO AUTO-PROCESS")
    confidence: AIConfidenceLevel = Field(..., description="HIGH, MEDIUM, or LOW")

class AIUseCaseCreate(BaseModel):
    name: str = Field(..., max_length=255)
    domain: str = Field(..., max_length=100)
    purpose: str
    model_provider: str = Field(..., max_length=100)
    prompt_template_id: str = Field(..., max_length=100)
    risk_tier: AIRiskTier
    fallback_behavior: str
    owner: str = Field(..., max_length=100)

class AIUseCaseResponse(AIUseCaseCreate):
    id: int
    is_enabled: bool
    last_review_date: datetime

    class Config:
        from_attributes = True

class AIWorkflowRunBase(BaseModel):
    use_case_id: int
    correlation_id: str
    context_snapshot: Optional[Dict[str, Any]] = None

class AIWorkflowRunResponse(AIWorkflowRunBase):
    id: int
    state: AIWorkflowState
    governance_state: AIGovernanceState
    override_state: AIOverrideState
    fallback_used: bool
    error_message: Optional[str] = None
    confidence_level: Optional[AIConfidenceLevel] = None
    explanation_summary: Optional[str] = None
    next_step: Optional[str] = None
    created_at: datetime
    completed_at: Optional[datetime] = None

    class Config:
        from_attributes = True

class AIHumanOverrideRequest(BaseModel):
    workflow_id: int
    actor_id: str
    new_state: AIOverrideState
    reason: str
