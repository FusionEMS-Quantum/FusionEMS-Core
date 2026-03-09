from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, Query, Request, Response
from sqlalchemy.orm import Session

from core_app.api.dependencies import db_session_dependency, require_role
from core_app.schemas.auth import CurrentUser
from core_app.schemas.legal_requests import (
    DeliveryAccessOut,
    DeliveryLinkCreateIn,
    DeliveryLinkOut,
    LegalCheckReceivedIn,
    LegalFeeQuoteOut,
    LegalPacketBuildOut,
    LegalPaymentCheckoutIn,
    LegalPaymentCheckoutOut,
    LegalPricingQuoteIn,
    LegalQueueItemOut,
    LegalRequestClassifyIn,
    LegalRequestClassifyOut,
    LegalRequestCloseOut,
    LegalRequestDetailOut,
    LegalRequestIntakeIn,
    LegalRequestIntakeOut,
    LegalRequestPaymentOut,
    LegalRequestReviewIn,
    LegalRequestReviewOut,
    LegalRequestsSummaryOut,
    LegalUploadCompleteIn,
    LegalUploadCompleteOut,
    LegalUploadPresignIn,
    LegalUploadPresignOut,
)
from core_app.services.legal_requests_service import LegalRequestsService

router = APIRouter(prefix="/api/v1/legal-requests", tags=["Legal Requests Command"])


@router.post("/intake", response_model=LegalRequestIntakeOut, status_code=201)
def create_legal_request_intake(
    payload: LegalRequestIntakeIn,
    request: Request,
    db: Session = Depends(db_session_dependency),
) -> LegalRequestIntakeOut:
    service = LegalRequestsService(db)
    tenant_id = service.system_tenant_id()
    row, intake_token, triage, missing_items, checklist = service.create_intake(
        tenant_id=tenant_id,
        payload=payload,
        correlation_id=getattr(request.state, "correlation_id", None),
    )
    db.commit()
    db.refresh(row)
    return LegalRequestIntakeOut(
        request_id=row.id,
        intake_token=intake_token,
        status=row.status.value,
        request_type=row.request_type.value,
        triage_summary=triage,
        missing_items=missing_items,
        required_document_checklist=checklist,
        workflow_state=row.workflow_state,
        payment_status=row.payment_status,
        payment_required=row.payment_required,
        margin_status=row.margin_status,
        fee_quote=row.fee_quote or {},
    )


@router.post("/classify", response_model=LegalRequestClassifyOut)
def classify_legal_request(
    payload: LegalRequestClassifyIn,
    db: Session = Depends(db_session_dependency),
) -> LegalRequestClassifyOut:
    service = LegalRequestsService(db)
    _classified, triage, missing_items, checklist = service.classify_intake(payload)
    return LegalRequestClassifyOut(
        triage_summary=triage,
        missing_items=missing_items,
        required_document_checklist=checklist,
    )


@router.post("/{request_id}/uploads/presign", response_model=LegalUploadPresignOut, status_code=201)
def create_upload_presign(
    request_id: uuid.UUID,
    payload: LegalUploadPresignIn,
    request: Request,
    db: Session = Depends(db_session_dependency),
) -> LegalUploadPresignOut:
    service = LegalRequestsService(db)
    tenant_id = service.system_tenant_id()
    upload_row, upload_url, key, expires_in = service.create_upload_presign(
        tenant_id=tenant_id,
        request_id=request_id,
        intake_token=payload.intake_token,
        document_kind=payload.document_kind,
        file_name=payload.file_name,
        content_type=payload.content_type,
        correlation_id=getattr(request.state, "correlation_id", None),
    )
    db.commit()
    db.refresh(upload_row)
    return LegalUploadPresignOut(
        upload_id=upload_row.id,
        upload_url=upload_url,
        key=key,
        expires_in_seconds=expires_in,
    )


@router.post("/{request_id}/uploads/complete", response_model=LegalUploadCompleteOut)
def complete_upload(
    request_id: uuid.UUID,
    payload: LegalUploadCompleteIn,
    request: Request,
    db: Session = Depends(db_session_dependency),
) -> LegalUploadCompleteOut:
    service = LegalRequestsService(db)
    tenant_id = service.system_tenant_id()
    row, triage, missing_items, checklist = service.complete_upload(
        tenant_id=tenant_id,
        request_id=request_id,
        intake_token=payload.intake_token,
        upload_id=payload.upload_id,
        byte_size=payload.byte_size,
        checksum_sha256=payload.checksum_sha256,
        correlation_id=getattr(request.state, "correlation_id", None),
    )
    db.commit()
    db.refresh(row)
    return LegalUploadCompleteOut(
        request_id=row.id,
        status=row.status.value,
        triage_summary=triage,
        missing_items=missing_items,
        required_document_checklist=checklist,
    )


@router.post("/{request_id}/pricing/quote", response_model=LegalFeeQuoteOut)
def preview_legal_quote(
    request_id: uuid.UUID,
    payload: LegalPricingQuoteIn,
    request: Request,
    db: Session = Depends(db_session_dependency),
) -> LegalFeeQuoteOut:
    service = LegalRequestsService(db)
    tenant_id = service.system_tenant_id()
    out = service.preview_quote(
        tenant_id=tenant_id,
        request_id=request_id,
        payload=payload,
        correlation_id=getattr(request.state, "correlation_id", None),
    )
    db.commit()
    return out


@router.post("/{request_id}/payment/checkout", response_model=LegalPaymentCheckoutOut)
def create_legal_payment_checkout(
    request_id: uuid.UUID,
    payload: LegalPaymentCheckoutIn,
    request: Request,
    db: Session = Depends(db_session_dependency),
) -> LegalPaymentCheckoutOut:
    service = LegalRequestsService(db)
    tenant_id = service.system_tenant_id()
    out = service.create_payment_checkout(
        tenant_id=tenant_id,
        request_id=request_id,
        intake_token=payload.intake_token,
        success_url=payload.success_url,
        cancel_url=payload.cancel_url,
        correlation_id=getattr(request.state, "correlation_id", None),
    )
    db.commit()
    return out


@router.get("/delivery/{token}", response_model=DeliveryAccessOut)
def consume_delivery_link(
    token: str,
    request: Request,
    db: Session = Depends(db_session_dependency),
) -> DeliveryAccessOut:
    service = LegalRequestsService(db)
    out = service.consume_delivery_link(
        token=token,
        requester_ip=request.client.host if request.client else None,
        requester_user_agent=request.headers.get("user-agent"),
        correlation_id=getattr(request.state, "correlation_id", None),
    )
    db.commit()
    return out


@router.get("/founder/summary", response_model=LegalRequestsSummaryOut)
def founder_legal_summary(
    current: CurrentUser = Depends(require_role("founder", "agency_admin", "compliance", "supervisor")),
    db: Session = Depends(db_session_dependency),
) -> LegalRequestsSummaryOut:
    service = LegalRequestsService(db)
    return service.get_summary(tenant_id=current.tenant_id)


@router.get("/founder/queue", response_model=list[LegalQueueItemOut])
def founder_legal_queue(
    lane: str | None = Query(default=None),
    limit: int = Query(default=100, ge=1, le=500),
    current: CurrentUser = Depends(require_role("founder", "agency_admin", "compliance", "supervisor")),
    db: Session = Depends(db_session_dependency),
) -> list[LegalQueueItemOut]:
    service = LegalRequestsService(db)
    return service.list_queue(tenant_id=current.tenant_id, lane=lane, limit=limit)


@router.get("/founder/requests/{request_id}", response_model=LegalRequestDetailOut)
def founder_get_request_detail(
    request_id: uuid.UUID,
    current: CurrentUser = Depends(require_role("founder", "agency_admin", "compliance", "supervisor")),
    db: Session = Depends(db_session_dependency),
) -> LegalRequestDetailOut:
    service = LegalRequestsService(db)
    return service.get_request_detail(tenant_id=current.tenant_id, request_id=request_id)


@router.post("/founder/requests/{request_id}/review", response_model=LegalRequestReviewOut)
def founder_review_request(
    request_id: uuid.UUID,
    payload: LegalRequestReviewIn,
    request: Request,
    current: CurrentUser = Depends(require_role("founder", "agency_admin", "compliance", "supervisor")),
    db: Session = Depends(db_session_dependency),
) -> LegalRequestReviewOut:
    service = LegalRequestsService(db)
    out = service.review_request(
        tenant_id=current.tenant_id,
        actor_user_id=current.user_id,
        request_id=request_id,
        payload=payload,
        correlation_id=getattr(request.state, "correlation_id", None),
    )
    db.commit()
    return out


@router.post("/founder/requests/{request_id}/packet-build", response_model=LegalPacketBuildOut)
def founder_build_packet(
    request_id: uuid.UUID,
    request: Request,
    current: CurrentUser = Depends(require_role("founder", "agency_admin", "compliance", "supervisor")),
    db: Session = Depends(db_session_dependency),
) -> LegalPacketBuildOut:
    service = LegalRequestsService(db)
    row, manifest = service.build_packet(
        tenant_id=current.tenant_id,
        actor_user_id=current.user_id,
        request_id=request_id,
        correlation_id=getattr(request.state, "correlation_id", None),
    )
    db.commit()
    db.refresh(row)
    return LegalPacketBuildOut(
        request_id=row.id,
        status=row.status.value,
        packet_manifest=manifest,
    )


@router.post("/founder/requests/{request_id}/delivery-links", response_model=DeliveryLinkOut, status_code=201)
def founder_create_delivery_link(
    request_id: uuid.UUID,
    payload: DeliveryLinkCreateIn,
    request: Request,
    current: CurrentUser = Depends(require_role("founder", "agency_admin", "compliance", "supervisor")),
    db: Session = Depends(db_session_dependency),
) -> DeliveryLinkOut:
    service = LegalRequestsService(db)
    link, delivery_url = service.create_delivery_link(
        tenant_id=current.tenant_id,
        actor_user_id=current.user_id,
        request_id=request_id,
        expires_in_hours=payload.expires_in_hours,
        recipient_hint=payload.recipient_hint,
        correlation_id=getattr(request.state, "correlation_id", None),
    )
    db.commit()
    db.refresh(link)
    return DeliveryLinkOut(
        delivery_link_id=link.id,
        delivery_url=delivery_url,
        expires_at=link.expires_at,
    )


@router.post(
    "/founder/delivery-links/{delivery_link_id}/revoke",
    status_code=204,
    response_model=None,
    response_class=Response,
)
def founder_revoke_delivery_link(
    delivery_link_id: uuid.UUID,
    request: Request,
    current: CurrentUser = Depends(require_role("founder", "agency_admin", "compliance", "supervisor")),
    db: Session = Depends(db_session_dependency),
) -> None:
    service = LegalRequestsService(db)
    service.revoke_delivery_link(
        tenant_id=current.tenant_id,
        actor_user_id=current.user_id,
        delivery_link_id=delivery_link_id,
        correlation_id=getattr(request.state, "correlation_id", None),
    )
    db.commit()


@router.post("/founder/requests/{request_id}/close", response_model=LegalRequestCloseOut)
def founder_close_request(
    request_id: uuid.UUID,
    request: Request,
    current: CurrentUser = Depends(require_role("founder", "agency_admin", "compliance", "supervisor")),
    db: Session = Depends(db_session_dependency),
) -> LegalRequestCloseOut:
    service = LegalRequestsService(db)
    out = service.close_request(
        tenant_id=current.tenant_id,
        actor_user_id=current.user_id,
        request_id=request_id,
        correlation_id=getattr(request.state, "correlation_id", None),
    )
    db.commit()
    return out


@router.get("/founder/requests/{request_id}/status-tracker", response_model=LegalRequestDetailOut)
def founder_status_tracker(
    request_id: uuid.UUID,
    current: CurrentUser = Depends(require_role("founder", "agency_admin", "compliance", "supervisor")),
    db: Session = Depends(db_session_dependency),
) -> LegalRequestDetailOut:
    service = LegalRequestsService(db)
    return service.get_request_detail(tenant_id=current.tenant_id, request_id=request_id)


@router.get("/founder/requests/{request_id}/payment", response_model=LegalRequestPaymentOut)
def founder_get_request_payment(
    request_id: uuid.UUID,
    current: CurrentUser = Depends(require_role("founder", "agency_admin", "compliance", "supervisor")),
    db: Session = Depends(db_session_dependency),
) -> LegalRequestPaymentOut:
    service = LegalRequestsService(db)
    return service.get_request_payment(tenant_id=current.tenant_id, request_id=request_id)


@router.post("/founder/requests/{request_id}/payment/check-received", response_model=LegalRequestPaymentOut)
def founder_mark_check_received(
    request_id: uuid.UUID,
    payload: LegalCheckReceivedIn,
    request: Request,
    current: CurrentUser = Depends(require_role("founder", "agency_admin", "compliance", "supervisor")),
    db: Session = Depends(db_session_dependency),
) -> LegalRequestPaymentOut:
    service = LegalRequestsService(db)
    out = service.mark_check_received(
        tenant_id=current.tenant_id,
        actor_user_id=current.user_id,
        request_id=request_id,
        check_reference=payload.check_reference,
        correlation_id=getattr(request.state, "correlation_id", None),
    )
    db.commit()
    return out
