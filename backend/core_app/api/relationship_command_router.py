"""Relationship Command Center API — founder dashboard aggregation."""
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from core_app.api.dependencies import require_role
from core_app.db.session import get_async_db_session
from core_app.schemas.auth import CurrentUser
from core_app.schemas.relationship_command import (
    RelationshipCommandSummary,
    RelationshipIssueList,
)
from core_app.services.relationship_ai_service import (
    RelationshipAIService,
)

router = APIRouter(
    prefix="/api/v1/founder/relationship-command",
    tags=["relationship-command"],
)


def _svc(
    db: AsyncSession = Depends(get_async_db_session),
) -> RelationshipAIService:
    return RelationshipAIService(db=db)


@router.get("/summary", response_model=RelationshipCommandSummary)
async def command_summary(
    current_user: CurrentUser = Depends(require_role("founder", "admin")),
    svc: RelationshipAIService = Depends(_svc),
) -> RelationshipCommandSummary:
    return await svc.build_command_summary(
        tenant_id=str(current_user.tenant_id)
    )


@router.get("/issues", response_model=RelationshipIssueList)
async def generate_issues(
    current_user: CurrentUser = Depends(require_role("founder", "admin")),
    svc: RelationshipAIService = Depends(_svc),
) -> RelationshipIssueList:
    """Generate structured relationship issues per directive Part 9 format."""
    return await svc.generate_issues(
        tenant_id=str(current_user.tenant_id)
    )
