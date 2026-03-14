"""Founder integration/connectors command center router."""
from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from core_app.api.dependencies import db_session_dependency, require_role
from core_app.schemas.auth import CurrentUser
from core_app.schemas.founder_command_domains import (
    ConnectorSyncJobCreateRequest,
    ConnectorSyncJobResponse,
    FounderGrowthSetupWizard,
    FounderGrowthSummary,
    IntegrationCommandSummary,
    LaunchOrchestratorRunResponse,
    LaunchOrchestratorStartRequest,
    SyncDeadLetterCreateRequest,
    SyncDeadLetterResponse,
)
from core_app.services.ai_growth_service import AIGrowthService
from core_app.services.founder_command_domain_service import FounderCommandDomainService

router = APIRouter(
    prefix="/api/v1/founder/integration-command",
    tags=["Founder Integration Command"],
)


@router.get("/summary", response_model=IntegrationCommandSummary)
def get_integration_command_summary(
    _current: CurrentUser = Depends(require_role("founder")),
    db: Session = Depends(db_session_dependency),
) -> IntegrationCommandSummary:
    svc = FounderCommandDomainService(db)
    return svc.get_integration_command_summary()


@router.get("/growth-summary", response_model=FounderGrowthSummary)
def get_growth_summary(
    current: CurrentUser = Depends(require_role("founder")),
    db: Session = Depends(db_session_dependency),
) -> FounderGrowthSummary:
    svc = FounderCommandDomainService(db)
    return svc.get_growth_summary(tenant_id=current.tenant_id)


@router.get("/growth-setup-wizard", response_model=FounderGrowthSetupWizard)
def get_growth_setup_wizard(
    current: CurrentUser = Depends(require_role("founder")),
    db: Session = Depends(db_session_dependency),
) -> FounderGrowthSetupWizard:
    svc = FounderCommandDomainService(db)
    return svc.get_growth_setup_wizard(tenant_id=current.tenant_id)


@router.post("/launch-orchestrator/start", response_model=LaunchOrchestratorRunResponse)
def start_launch_orchestrator(
    payload: LaunchOrchestratorStartRequest,
    current: CurrentUser = Depends(require_role("founder")),
    db: Session = Depends(db_session_dependency),
) -> LaunchOrchestratorRunResponse:
    svc = FounderCommandDomainService(db)
    run = svc.start_launch_orchestrator(
        tenant_id=current.tenant_id,
        actor_user_id=current.user_id,
        mode=payload.mode,
        auto_queue_sync_jobs=payload.auto_queue_sync_jobs,
    )

    # Real AI Growth Launch Sequence
    growth_svc = AIGrowthService(db)
    campaign = growth_svc.create_campaign(
        name=f"Launch Burst - {payload.mode.upper()}",
        objective="Drive signups and book demos via automated publishing",
        audience={"target": "EMS Agency Directors", "region": "US"}
    )
    growth_svc.generate_demo_assets(campaign.id, "Revenue Cycle Overhaul")

    db.commit()
    return run


@router.get("/failed-sync-jobs", response_model=list[ConnectorSyncJobResponse])
def list_failed_sync_jobs(
    limit: int = Query(default=50, ge=1, le=250),
    _current: CurrentUser = Depends(require_role("founder")),
    db: Session = Depends(db_session_dependency),
) -> list[ConnectorSyncJobResponse]:
    svc = FounderCommandDomainService(db)
    jobs = svc.list_failed_sync_jobs(limit=limit)
    return [ConnectorSyncJobResponse.model_validate(job) for job in jobs]


@router.post("/sync-jobs", response_model=ConnectorSyncJobResponse, status_code=201)
def create_sync_job(
    payload: ConnectorSyncJobCreateRequest,
    current: CurrentUser = Depends(require_role("founder")),
    db: Session = Depends(db_session_dependency),
) -> ConnectorSyncJobResponse:
    svc = FounderCommandDomainService(db)
    job = svc.create_connector_sync_job(
        tenant_id=current.tenant_id,
        actor_user_id=current.user_id,
        tenant_connector_install_id=payload.tenant_connector_install_id,
        direction=payload.direction,
        state=payload.state,
        records_attempted=payload.records_attempted,
        records_succeeded=payload.records_succeeded,
        records_failed=payload.records_failed,
        error_summary=payload.error_summary,
    )
    db.commit()
    db.refresh(job)
    return ConnectorSyncJobResponse.model_validate(job)


@router.post("/sync-jobs/{sync_job_id}/dead-letters", response_model=SyncDeadLetterResponse, status_code=201)
def add_sync_dead_letter(
    sync_job_id: UUID,
    payload: SyncDeadLetterCreateRequest,
    current: CurrentUser = Depends(require_role("founder")),
    db: Session = Depends(db_session_dependency),
) -> SyncDeadLetterResponse:
    svc = FounderCommandDomainService(db)
    dead_letter = svc.add_sync_dead_letter(
        tenant_id=current.tenant_id,
        actor_user_id=current.user_id,
        connector_sync_job_id=sync_job_id,
        external_record_ref=payload.external_record_ref,
        reason=payload.reason,
        payload=payload.payload,
    )
    db.commit()
    db.refresh(dead_letter)
    return SyncDeadLetterResponse.model_validate(dead_letter)
