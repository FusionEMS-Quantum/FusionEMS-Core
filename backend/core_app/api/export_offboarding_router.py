"""Export and offboarding command API.

Provides export package creation, approval, secure delivery, offboarding
initiation, risk analysis, and founder oversight endpoints.
"""

from __future__ import annotations

import uuid
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy.orm import Session

from core_app.api.dependencies import db_session_dependency, get_current_user, require_role
from core_app.schemas.auth import CurrentUser
from core_app.schemas.export_offboarding import (
    ExportPackageApproveRequest,
    ExportPackageCreateRequest,
    OffboardingStartRequest,
    SecureLinkAccessRequest,
)
from core_app.services.export_offboarding_service import ExportOffboardingService

router = APIRouter(
    prefix="/api/v1/portal/billing/exports",
    tags=["Export & Offboarding"],
)

PORTAL_ROLES = ("founder", "admin", "agency_admin", "billing")
APPROVAL_ROLES = ("founder", "admin", "agency_admin")


# ── Export Packages ──────────────────────────────────────────────────────────

@router.post("")
async def create_export_package(
    payload: ExportPackageCreateRequest,
    request: Request,
    current: CurrentUser = Depends(require_role(*PORTAL_ROLES)),
    db: Session = Depends(db_session_dependency),
) -> dict[str, Any]:
    """Request a new export package."""
    svc = ExportOffboardingService(db)
    pkg = svc.create_export_package(
        tenant_id=current.tenant_id,
        requested_by=current.user_id,
        modules=[m.value for m in payload.modules],
        date_range_start=payload.date_range_start,
        date_range_end=payload.date_range_end,
        patient_scope=payload.patient_scope,
        account_scope=payload.account_scope,
        include_attachments=payload.include_attachments,
        include_field_crosswalk=payload.include_field_crosswalk,
        delivery_method=payload.delivery_method.value,
        delivery_target=payload.delivery_target,
        notes=payload.notes,
    )
    db.commit()
    return {
        "id": str(pkg.id),
        "state": pkg.state,
        "modules": pkg.modules,
        "delivery_method": pkg.delivery_method,
        "created_at": pkg.created_at.isoformat() if pkg.created_at else None,
    }


@router.get("")
async def list_export_packages(
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    current: CurrentUser = Depends(require_role(*PORTAL_ROLES)),
    db: Session = Depends(db_session_dependency),
) -> dict[str, Any]:
    """List all export packages for this tenant."""
    svc = ExportOffboardingService(db)
    packages = svc.list_export_packages(current.tenant_id, limit=limit, offset=offset)
    return {
        "packages": [
            {
                "id": str(p.id),
                "state": p.state,
                "modules": p.modules,
                "risk_level": p.risk_level,
                "file_count": p.file_count,
                "total_size_bytes": p.total_size_bytes,
                "delivery_method": p.delivery_method,
                "created_at": p.created_at.isoformat() if p.created_at else None,
                "integrity_hash": p.integrity_hash,
            }
            for p in packages
        ],
        "count": len(packages),
    }


@router.get("/{package_id}")
async def get_export_package(
    package_id: uuid.UUID,
    current: CurrentUser = Depends(require_role(*PORTAL_ROLES)),
    db: Session = Depends(db_session_dependency),
) -> dict[str, Any]:
    """Get detailed export package info."""
    svc = ExportOffboardingService(db)
    pkg = svc.get_export_package(current.tenant_id, package_id)
    if not pkg:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Package not found")
    return {
        "id": str(pkg.id),
        "state": pkg.state,
        "modules": pkg.modules,
        "date_range_start": pkg.date_range_start.isoformat() if pkg.date_range_start else None,
        "date_range_end": pkg.date_range_end.isoformat() if pkg.date_range_end else None,
        "include_attachments": pkg.include_attachments,
        "include_field_crosswalk": pkg.include_field_crosswalk,
        "delivery_method": pkg.delivery_method,
        "delivery_target": pkg.delivery_target,
        "requested_by": str(pkg.requested_by),
        "approved_by": str(pkg.approved_by) if pkg.approved_by else None,
        "approved_at": pkg.approved_at.isoformat() if pkg.approved_at else None,
        "package_s3_key": pkg.package_s3_key,
        "manifest": pkg.manifest,
        "integrity_hash": pkg.integrity_hash,
        "risk_level": pkg.risk_level,
        "risk_details": pkg.risk_details,
        "file_count": pkg.file_count,
        "total_size_bytes": pkg.total_size_bytes,
        "notes": pkg.notes,
        "created_at": pkg.created_at.isoformat() if pkg.created_at else None,
        "updated_at": pkg.updated_at.isoformat() if pkg.updated_at else None,
    }


# ── Approval Flow ────────────────────────────────────────────────────────────

@router.post("/{package_id}/approve")
async def approve_export_package(
    package_id: uuid.UUID,
    payload: ExportPackageApproveRequest,
    current: CurrentUser = Depends(require_role(*APPROVAL_ROLES)),
    db: Session = Depends(db_session_dependency),
) -> dict[str, Any]:
    """Approve or reject an export package (requires admin+ role)."""
    svc = ExportOffboardingService(db)
    pkg = svc.approve_export_package(
        tenant_id=current.tenant_id,
        package_id=package_id,
        reviewer_id=current.user_id,
        approved=payload.approved,
        reviewer_notes=payload.reviewer_notes,
    )
    if not pkg:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Package not found")
    db.commit()
    return {"id": str(pkg.id), "state": pkg.state, "approved_at": pkg.approved_at.isoformat() if pkg.approved_at else None}


# ── Build Package ────────────────────────────────────────────────────────────

@router.post("/{package_id}/build")
async def build_export_package(
    package_id: uuid.UUID,
    current: CurrentUser = Depends(require_role(*APPROVAL_ROLES)),
    db: Session = Depends(db_session_dependency),
) -> dict[str, Any]:
    """Build the actual export archive for an approved package."""
    svc = ExportOffboardingService(db)
    pkg = svc.build_export_package(current.tenant_id, package_id)
    if not pkg:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Package not found or not approved")
    db.commit()
    return {
        "id": str(pkg.id),
        "state": pkg.state,
        "file_count": pkg.file_count,
        "total_size_bytes": pkg.total_size_bytes,
        "integrity_hash": pkg.integrity_hash,
        "risk_level": pkg.risk_level,
        "risk_details": pkg.risk_details,
    }


# ── Secure Link ──────────────────────────────────────────────────────────────

@router.post("/{package_id}/secure-link")
async def manage_secure_link(
    package_id: uuid.UUID,
    payload: SecureLinkAccessRequest,
    request: Request,
    current: CurrentUser = Depends(require_role(*PORTAL_ROLES)),
    db: Session = Depends(db_session_dependency),
) -> dict[str, Any]:
    """Generate, revoke, or reissue a secure download link."""
    svc = ExportOffboardingService(db)

    if payload.action == "generate" or payload.action == "reissue":
        result = svc.generate_secure_link(
            tenant_id=current.tenant_id,
            package_id=package_id,
            user_id=current.user_id,
            expires_hours=payload.expires_hours,
        )
    elif payload.action == "revoke":
        ok = svc.revoke_secure_link(current.tenant_id, package_id, current.user_id)
        result = {"revoked": ok}
    else:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid action")

    db.commit()
    return result


# ── Access Logs ──────────────────────────────────────────────────────────────

@router.get("/{package_id}/access-logs")
async def get_access_logs(
    package_id: uuid.UUID,
    current: CurrentUser = Depends(require_role(*APPROVAL_ROLES)),
    db: Session = Depends(db_session_dependency),
) -> dict[str, Any]:
    """View access/download log for an export package."""
    svc = ExportOffboardingService(db)
    logs = svc.get_access_logs(current.tenant_id, package_id)
    return {"logs": logs, "count": len(logs)}


# ── Offboarding ──────────────────────────────────────────────────────────────

offboarding_router = APIRouter(
    prefix="/api/v1/portal/billing/offboarding",
    tags=["Offboarding"],
)


@offboarding_router.post("/start")
async def start_offboarding(
    payload: OffboardingStartRequest,
    current: CurrentUser = Depends(require_role(*APPROVAL_ROLES)),
    db: Session = Depends(db_session_dependency),
) -> dict[str, Any]:
    """Initiate a full offboarding sequence."""
    svc = ExportOffboardingService(db)
    result = svc.start_offboarding(
        tenant_id=current.tenant_id,
        requested_by=current.user_id,
        reason=payload.reason,
        target_vendor=payload.target_vendor,
        requested_completion_date=payload.requested_completion_date,
        delivery_method=payload.delivery_method.value,
        delivery_target=payload.delivery_target,
        contact_name=payload.contact_name,
        contact_email=payload.contact_email,
        modules=[m.value for m in payload.modules],
    )
    db.commit()
    return result


@offboarding_router.get("/status")
async def offboarding_status(
    current: CurrentUser = Depends(require_role(*PORTAL_ROLES)),
    db: Session = Depends(db_session_dependency),
) -> dict[str, Any]:
    """Get current offboarding status."""
    svc = ExportOffboardingService(db)
    result = svc.get_offboarding_status(current.tenant_id)
    if not result:
        return {"status": "NO_ACTIVE_OFFBOARDING"}
    return result


# ── Founder Oversight ────────────────────────────────────────────────────────

founder_export_router = APIRouter(
    prefix="/api/v1/founder/exports",
    tags=["Founder Export Oversight"],
)


@founder_export_router.get("/overview")
async def founder_export_overview(
    current: CurrentUser = Depends(require_role("founder", "admin")),
    db: Session = Depends(db_session_dependency),
) -> dict[str, Any]:
    """Cross-tenant export/offboarding overview for founder dashboard."""
    svc = ExportOffboardingService(db)
    return svc.get_founder_export_overview()


@founder_export_router.get("/billers")
async def founder_list_billers(
    current: CurrentUser = Depends(require_role("founder", "admin")),
    db: Session = Depends(db_session_dependency),
) -> dict[str, Any]:
    """List all third-party billers across tenants (founder only)."""
    svc = ExportOffboardingService(db)
    billers = svc.list_billers(current.tenant_id)
    return {"billers": billers, "count": len(billers)}


@founder_export_router.get("/risk-analysis")
async def founder_risk_analysis(
    tenant_id: uuid.UUID = Query(...),
    current: CurrentUser = Depends(require_role("founder", "admin")),
    db: Session = Depends(db_session_dependency),
) -> dict[str, Any]:
    """Run handoff risk analysis for a specific tenant (founder only)."""
    svc = ExportOffboardingService(db)
    risk_level, risk_details = svc._analyze_risk(tenant_id, ["FULL_OFFBOARDING"])
    return {"tenant_id": str(tenant_id), "risk_level": risk_level, "risk_details": risk_details}


@founder_export_router.get("/field-crosswalk")
async def founder_field_crosswalk(
    current: CurrentUser = Depends(require_role("founder", "admin")),
    db: Session = Depends(db_session_dependency),
) -> dict[str, Any]:
    """Get the field crosswalk mapping (founder view)."""
    svc = ExportOffboardingService(db)
    return {"crosswalk": svc.get_field_crosswalk()}
