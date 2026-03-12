"""
NEMSIS REST API endpoints for data submission and status tracking.

Provides HTTP endpoints for:
- Submitting EMS/DEM/State data
- Querying submission status
- Waiting for async results
"""

from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from pydantic import BaseModel

from core_app.api.auth import get_current_org_context
from core_app.core.logging_context import CorrelationIdHandler
from core_app.nemsis.models import NemsisDataSchema
from core_app.nemsis.production_client import NEMSISClientError
from core_app.nemsis.submission_service import NEMSISSubmissionService

router = APIRouter(prefix="/api/v1/nemsis", tags=["nemsis"])

# Initialize service with default client
_submission_service = NEMSISSubmissionService()


# Request/Response Models

class SubmitDataRequest(BaseModel):
    """Submit EMSDataSet or DEMDataSet."""
    schema_type: int  # 61=EMS, 62=DEM
    schema_version: str = "3.5.1"
    additional_info: Optional[str] = None
    national_only: bool = False


class SubmitStateDataRequest(BaseModel):
    """Submit StateDataSet."""
    schema_version: str = "3.5.1"
    additional_info: Optional[str] = None


class SubmitDataResponse(BaseModel):
    """Response from submission."""
    request_handle: str
    status_code: int
    status_message: str
    is_async: bool
    correlation_id: str


class RetrieveStatusRequest(BaseModel):
    """Retrieve status of async submission."""
    request_handle: str


class StatusResponse(BaseModel):
    """Status of submission."""
    status_code: int
    request_handle: str
    is_complete: bool
    correlation_id: str


# Endpoints

@router.post("/submit/ems", response_model=SubmitDataResponse)
async def submit_ems_data(
    file: UploadFile = File(...),
    schema_version: str = Form("3.5.1"),
    additional_info: str = Form(""),
    national_only: bool = Form(False),
    org_context = Depends(get_current_org_context),
) -> SubmitDataResponse:
    """
    Submit EMS dataset (EMSDataSet).
    
    - **file**: XML file containing EMSDataSet
    - **schema_version**: NEMSIS schema version (3.4.0, 3.5.0, 3.5.1)
    - **additional_info**: Optional notes/changelog
    - **national_only**: Submit only national-required elements
    """
    correlation_id = CorrelationIdHandler.get()
    
    try:
        xml_bytes = await file.read()
        
        result = await _submission_service.submit_ems_data(
            xml_bytes=xml_bytes,
            organization=org_context.organization_id,
            username=org_context.nemsis_username,
            password=org_context.nemsis_password,
            schema_version=schema_version,
            additional_info=additional_info or "",
            national_only=national_only,
            correlation_id=correlation_id,
        )
        
        return SubmitDataResponse(
            request_handle=result.request_handle,
            status_code=result.status_code,
            status_message=result.status_message,
            is_async=result.is_async,
            correlation_id=correlation_id,
        )
        
    except NEMSISClientError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Submission failed: {exc}")


@router.post("/submit/dem", response_model=SubmitDataResponse)
async def submit_dem_data(
    file: UploadFile = File(...),
    schema_version: str = Form("3.5.1"),
    additional_info: str = Form(""),
    national_only: bool = Form(False),
    org_context = Depends(get_current_org_context),
) -> SubmitDataResponse:
    """
    Submit DEM (Demographic) dataset (DEMDataSet).
    
    - **file**: XML file containing DEMDataSet
    - **schema_version**: NEMSIS schema version (3.4.0, 3.5.0, 3.5.1)
    - **additional_info**: Optional notes/changelog
    - **national_only**: Submit only national-required elements
    """
    correlation_id = CorrelationIdHandler.get()
    
    try:
        xml_bytes = await file.read()
        
        result = await _submission_service.submit_dem_data(
            xml_bytes=xml_bytes,
            organization=org_context.organization_id,
            username=org_context.nemsis_username,
            password=org_context.nemsis_password,
            schema_version=schema_version,
            additional_info=additional_info or "",
            national_only=national_only,
            correlation_id=correlation_id,
        )
        
        return SubmitDataResponse(
            request_handle=result.request_handle,
            status_code=result.status_code,
            status_message=result.status_message,
            is_async=result.is_async,
            correlation_id=correlation_id,
        )
        
    except NEMSISClientError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Submission failed: {exc}")


@router.post("/submit/state", response_model=SubmitDataResponse)
async def submit_state_data(
    file: UploadFile = File(...),
    schema_version: str = Form("3.5.1"),
    additional_info: str = Form(""),
    org_context = Depends(get_current_org_context),
) -> SubmitDataResponse:
    """
    Submit State dataset (StateDataSet).
    
    - **file**: XML file containing StateDataSet
    - **schema_version**: NEMSIS schema version (3.5.0, 3.5.1)
    - **additional_info**: Optional notes/changelog
    """
    correlation_id = CorrelationIdHandler.get()
    
    try:
        xml_bytes = await file.read()
        
        result = await _submission_service.submit_state_data(
            xml_bytes=xml_bytes,
            organization=org_context.organization_id,
            username=org_context.nemsis_username,
            password=org_context.nemsis_password,
            schema_version=schema_version,
            additional_info=additional_info or "",
            correlation_id=correlation_id,
        )
        
        return SubmitDataResponse(
            request_handle=result.request_handle,
            status_code=result.status_code,
            status_message=result.status_message,
            is_async=result.is_async,
            correlation_id=correlation_id,
        )
        
    except NEMSISClientError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Submission failed: {exc}")


@router.post("/status", response_model=StatusResponse)
async def get_submission_status(
    request: RetrieveStatusRequest,
    org_context = Depends(get_current_org_context),
) -> StatusResponse:
    """
    Retrieve status of async submission.
    
    Use this endpoint to poll for results when initial submission returns is_async=true.
    """
    correlation_id = CorrelationIdHandler.get()
    
    try:
        status = await _submission_service.retrieve_submission_status(
            request_handle=request.request_handle,
            organization=org_context.organization_id,
            username=org_context.nemsis_username,
            password=org_context.nemsis_password,
            correlation_id=correlation_id,
        )
        
        return StatusResponse(
            status_code=status["status_code"],
            request_handle=status["request_handle"],
            is_complete=status["is_complete"],
            correlation_id=correlation_id,
        )
        
    except NEMSISClientError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Status check failed: {exc}")


@router.post("/wait/{request_handle}", response_model=StatusResponse)
async def wait_for_submission(
    request_handle: str,
    poll_interval_seconds: float = 5.0,
    max_wait_seconds: float = 3600.0,
    org_context = Depends(get_current_org_context),
) -> StatusResponse:
    """
    Wait for async submission to complete (blocking).
    
    This endpoint will block until the submission is complete or timeout is reached.
    
    - **request_handle**: Handle from submission response
    - **poll_interval_seconds**: Time between status checks (default 5s)
    - **max_wait_seconds**: Maximum wait time (default 1 hour)
    """
    correlation_id = CorrelationIdHandler.get()
    
    try:
        status = await _submission_service.wait_for_submission(
            request_handle=request_handle,
            organization=org_context.organization_id,
            username=org_context.nemsis_username,
            password=org_context.nemsis_password,
            poll_interval_seconds=poll_interval_seconds,
            max_wait_seconds=max_wait_seconds,
            correlation_id=correlation_id,
        )
        
        return StatusResponse(
            status_code=status["status_code"],
            request_handle=status["request_handle"],
            is_complete=True,  # Always complete when this returns
            correlation_id=correlation_id,
        )
        
    except NEMSISClientError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Wait failed: {exc}")
