import json
from typing import List, Optional, Dict, Any
from datetime import datetime, timezone
from sqlalchemy.orm import Session
from fastapi import HTTPException

from core_app.models.ai_platform import (
    AIUseCase,
    AIWorkflowRun,
    AIHumanOverrideEvent,
    AIRiskTier,
    AIWorkflowState,
    AIGovernanceState,
    AIOverrideState,
    AIConfidenceLevel
)
from core_app.schemas.ai_platform import (
    AIUseCaseCreate,
    AIUseCaseResponse,
    AIExplanationResponse,
    AIHumanOverrideRequest
)

class AIPlatformService:
    def __init__(self, db: Session, tenant_id: int):
        self.db = db
        self.tenant_id = tenant_id

    # --- USE-CASE REGISTRY ---
    def create_use_case(self, actor_id: str, use_case_in: AIUseCaseCreate) -> AIUseCase:
        # Enforce that a human is responsible
        if not use_case_in.owner:
            raise HTTPException(status_code=400, detail="Every AI use case must have an explicit owner.")
            
        use_case = AIUseCase(
            tenant_id=self.tenant_id,
            name=use_case_in.name,
            domain=use_case_in.domain,
            purpose=use_case_in.purpose,
            model_provider=use_case_in.model_provider,
            prompt_template_id=use_case_in.prompt_template_id,
            risk_tier=use_case_in.risk_tier,
            fallback_behavior=use_case_in.fallback_behavior,
            owner=use_case_in.owner,
            is_enabled=True,
            last_review_date=datetime.now(timezone.utc)
        )
        self.db.add(use_case)
        self.db.commit()
        self.db.refresh(use_case)
        return use_case
    
    def list_use_cases(self, domain: Optional[str] = None) -> List[AIUseCase]:
        query = self.db.query(AIUseCase).filter(AIUseCase.tenant_id == self.tenant_id)
        if domain:
            query = query.filter(AIUseCase.domain == domain)
        return query.all()

    # --- WORKFLOW ORCHESTRATION & GOVERNANCE ---
    def start_workflow(self, use_case_id: int, correlation_id: str, context: Dict[str, Any]) -> AIWorkflowRun:
        use_case = self.db.query(AIUseCase).filter(AIUseCase.id == use_case_id, AIUseCase.tenant_id == self.tenant_id).first()
        if not use_case:
            raise HTTPException(status_code=404, detail="AI Use Case not found.")
            
        if not use_case.is_enabled:
            raise HTTPException(status_code=403, detail="This AI workflow is currently disabled.")

        governance_state = AIGovernanceState.ALLOWED
        # Implicitly flag high risk workflows for human review
        if use_case.risk_tier in [AIRiskTier.HIGH_RISK, AIRiskTier.RESTRICTED]:
            governance_state = AIGovernanceState.HUMAN_REVIEW_REQUIRED

        run = AIWorkflowRun(
            tenant_id=self.tenant_id,
            use_case_id=use_case.id,
            correlation_id=correlation_id,
            state=AIWorkflowState.QUEUED,
            governance_state=governance_state,
            context_snapshot=context
        )
        self.db.add(run)
        self.db.commit()
        self.db.refresh(run)
        return run

    def record_inference_result(self, workflow_id: int, provider_response: Dict[str, Any], explanation: AIExplanationResponse) -> AIWorkflowRun:
        run = self.db.query(AIWorkflowRun).filter(AIWorkflowRun.id == workflow_id, AIWorkflowRun.tenant_id == self.tenant_id).first()
        if not run:
            raise HTTPException(status_code=404, detail="Workflow Run not found.")

        run.provider_response = provider_response
        run.state = AIWorkflowState.COMPLETED
        run.completed_at = datetime.now(timezone.utc)
        
        # Populate Explainability / Issue Card
        run.confidence_level = explanation.confidence
        run.explanation_summary = f"{explanation.why_it_matters}\n\n{explanation.what_is_wrong}"
        run.next_step = explanation.what_you_should_do

        # Update governance rules based on inference confidence
        if explanation.confidence == AIConfidenceLevel.LOW and run.governance_state == AIGovernanceState.ALLOWED:
            run.governance_state = AIGovernanceState.HUMAN_REVIEW_REQUIRED
            run.override_state = AIOverrideState.REVIEW_PENDING

        self.db.commit()
        self.db.refresh(run)
        return run

    def handle_fallback(self, workflow_id: int, error_message: str) -> AIWorkflowRun:
        run = self.db.query(AIWorkflowRun).filter(AIWorkflowRun.id == workflow_id, AIWorkflowRun.tenant_id == self.tenant_id).first()
        if not run:
            raise HTTPException(status_code=404, detail="Workflow Run not found.")
            
        run.state = AIWorkflowState.FALLBACK_USED
        run.fallback_used = True
        run.error_message = error_message
        run.completed_at = datetime.now(timezone.utc)
        self.db.commit()
        self.db.refresh(run)
        return run

    # --- HUMAN OVERRIDE ---
    def process_override(self, request: AIHumanOverrideRequest) -> AIWorkflowRun:
        run = self.db.query(AIWorkflowRun).filter(AIWorkflowRun.id == request.workflow_id, AIWorkflowRun.tenant_id == self.tenant_id).first()
        if not run:
            raise HTTPException(status_code=404, detail="Workflow Run not found.")

        prev_state = run.override_state
        run.override_state = request.new_state
        
        # Determine logical consequence of override
        if request.new_state == AIOverrideState.HUMAN_TAKEOVER:
            run.governance_state = AIGovernanceState.LIMITED
        elif request.new_state == AIOverrideState.APPROVED:
            run.governance_state = AIGovernanceState.ALLOWED
        elif request.new_state == AIOverrideState.REJECTED:
            run.governance_state = AIGovernanceState.BLOCKED

        event = AIHumanOverrideEvent(
            tenant_id=self.tenant_id,
            workflow_id=run.id,
            actor_id=request.actor_id,
            previous_state=str(prev_state),
            new_state=str(request.new_state),
            reason=request.reason
        )
        self.db.add(event)
        self.db.commit()
        self.db.refresh(run)
        return run

    # --- FOUNDER COMMAND DASHBOARD ---
    def get_dashboard_metrics(self) -> Dict[str, Any]:
        use_cases = self.db.query(AIUseCase).filter(AIUseCase.tenant_id == self.tenant_id).all()
        runs = self.db.query(AIWorkflowRun).filter(AIWorkflowRun.tenant_id == self.tenant_id).order_by(AIWorkflowRun.created_at.desc()).limit(100).all()

        disabled_cases = [uc for uc in use_cases if not uc.is_enabled]
        low_confidence_runs = [r for r in runs if r.confidence_level == AIConfidenceLevel.LOW]
        failed_runs = [r for r in runs if r.state in (AIWorkflowState.FAILED, AIWorkflowState.FALLBACK_USED)]
        review_queue = [r for r in runs if r.governance_state == AIGovernanceState.HUMAN_REVIEW_REQUIRED and r.override_state != AIOverrideState.APPROVED]

        health_score = 100
        if len(runs) > 0:
            failed_ratio = len(failed_runs) / len(runs)
            health_score = max(0, 100 - (failed_ratio * 100))

        return {
            "health_score": round(health_score, 1),
            "disabled_workflows": len(disabled_cases),
            "low_confidence_count": len(low_confidence_runs),
            "review_queue_count": len(review_queue),
            "failed_runs_count": len(failed_runs),
            "recent_reviews_required": [
                {
                    "run_id": r.id, 
                    "correlation_id": r.correlation_id, 
                    "summary": r.explanation_summary,
                    "use_case": r.use_case.name
                } for r in review_queue[:5]
            ]
        }
