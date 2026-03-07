from fastapi import APIRouter, Depends, HTTPException
from typing import List, Dict, Any
from sqlalchemy.orm import Session

from core_app.api.deps import get_db, get_current_user_tenant
from core_app.schemas.ai_platform import (
    AIUseCaseCreate, 
    AIUseCaseResponse, 
    AIWorkflowRunResponse, 
    AIHumanOverrideRequest
)
from core_app.services.ai_platform.platform_service import AIPlatformService

router = APIRouter()

def get_ai_service(db: Session = Depends(get_db), tenant: Any = Depends(get_current_user_tenant)):
    # Dependency injection for AI Platform Service
    # Note: Using tenant.id for multi-tenant isolation
    return AIPlatformService(db, tenant.id)

@router.post("/registry/use-cases", response_model=AIUseCaseResponse)
def create_use_case(
    use_case: AIUseCaseCreate,
    service: AIPlatformService = Depends(get_ai_service),
    tenant: Any = Depends(get_current_user_tenant)
):
    """
    Register a new AI Use Case to the AI Governance System
    """
    # Assuming tenant object has user id representing the actor
    actor_id = getattr(tenant, "user_id", "system")
    return service.create_use_case(actor_id, use_case)

@router.get("/registry/use-cases", response_model=List[AIUseCaseResponse])
def get_use_cases(
    domain: str = None,
    service: AIPlatformService = Depends(get_ai_service)
):
    """
    List all AI feature usage mapping and prompt boundaries
    """
    return service.list_use_cases(domain=domain)

@router.post("/override", response_model=AIWorkflowRunResponse)
def override_ai_workflow(
    request: AIHumanOverrideRequest,
    service: AIPlatformService = Depends(get_ai_service)
):
    """
    Human override endpoint to pause, takeover or correct AI logic explicitly.
    """
    return service.process_override(request)

@router.get("/command-center/metrics", response_model=Dict[str, Any])
def get_dashboard_metrics(
    service: AIPlatformService = Depends(get_ai_service)
):
    """
    Aggregate metrics for the Founder AI Command Center
    """
    return service.get_dashboard_metrics()
