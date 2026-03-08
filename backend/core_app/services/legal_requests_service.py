from __future__ import annotations

import hashlib
import json
import logging
import secrets
import uuid
from datetime import UTC, datetime, timedelta
from typing import Any

import boto3
from sqlalchemy import Select, select
from sqlalchemy.orm import Session

from core_app.ai.service import AiService
from core_app.core.config import get_settings
from core_app.core.errors import AppError, ErrorCodes
from core_app.documents.s3_storage import default_exports_bucket, put_bytes
from core_app.legal.pricing_engine import LegalPricingInput, LegalPricingResult, compute_legal_quote
from core_app.models.legal_requests import (
    DeliveryPreference,
    LegalDeliveryLink,
    LegalRequestCommand,
    LegalRequestPayment,
    LegalPaymentStatus,
    LegalRequestStatus,
    LegalRequestType,
    LegalWorkflowState,
    MarginRiskStatus,
    RequesterCategory,
    LegalRequestUpload,
    RedactionMode,
)
from core_app.models.records_media import (
    ChainOfCustodyEvent,
    ChainOfCustodyState,
    ClinicalRecord,
    RecordLifecycleState,
    RecordsAuditEvent,
)
from core_app.models.tenant import Tenant
from core_app.payments.stripe_service import (
    StripeConfig,
    StripeNotConfigured,
    create_connect_checkout_session,
)
from core_app.schemas.legal_requests import (
    AuditTimelineEvent,
    ChainOfCustodyTimelineEvent,
    DeliveryAccessOut,
    LegalFeeQuoteOut,
    LegalPaymentCheckoutOut,
    LegalRequestPaymentOut,
    LegalPricingQuoteIn,
    LegalQueueItemOut,
    LegalRequestClassifyIn,
    LegalRequestCloseOut,
    LegalRequestDetailOut,
    LegalRequestIntakeIn,
    LegalRequestReviewIn,
    LegalRequestReviewOut,
    LegalRequestsSummaryOut,
    LegalTriageSummary,
    LegalUploadOut,
    MissingItemCard,
    RequiredDocumentChecklistItem,
)

logger = logging.getLogger(__name__)

SYSTEM_TENANT_FALLBACK = uuid.UUID("00000000-0000-0000-0000-000000000001")


def _utcnow() -> datetime:
    return datetime.now(UTC)


def _sha256(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


class LegalRequestsService:
    def __init__(self, db: Session) -> None:
        self.db = db

    def system_tenant_id(self) -> uuid.UUID:
        raw = str(get_settings().system_tenant_id or "").strip()
        if not raw:
            return SYSTEM_TENANT_FALLBACK
        try:
            return uuid.UUID(raw)
        except ValueError:
            logger.warning("invalid_system_tenant_id_fallback", extra={"extra_fields": {"raw": raw}})
            return SYSTEM_TENANT_FALLBACK

    def classify_intake(
        self,
        payload: LegalRequestClassifyIn,
        uploaded_document_kinds: set[str] | None = None,
    ) -> tuple[
        LegalRequestType,
        LegalTriageSummary,
        list[MissingItemCard],
        list[RequiredDocumentChecklistItem],
    ]:
        normalized_docs = set(uploaded_document_kinds or set()) | {
            str(item).strip().lower() for item in payload.request_documents
        }

        classified_type = self._classify_type(payload)
        required_checklist = self._required_document_checklist(classified_type, normalized_docs)
        missing_items = self._compute_missing_items(
            classified_type=classified_type,
            payload=payload,
            required_checklist=required_checklist,
            uploaded_document_kinds=normalized_docs,
        )
        fallback_triage = self._build_fallback_triage(
            classified_type=classified_type,
            payload=payload,
            missing_items=missing_items,
            uploaded_document_kinds=normalized_docs,
        )
        ai_triage = self._try_ai_triage(
            classified_type=classified_type,
            payload=payload,
            missing_items=missing_items,
            required_checklist=required_checklist,
        )
        triage = ai_triage or fallback_triage
        return classified_type, triage, missing_items, required_checklist

    def create_intake(
        self,
        *,
        tenant_id: uuid.UUID,
        payload: LegalRequestIntakeIn,
        correlation_id: str | None,
    ) -> tuple[
        LegalRequestCommand,
        str,
        LegalTriageSummary,
        list[MissingItemCard],
        list[RequiredDocumentChecklistItem],
    ]:
        classified_type, triage, missing_items, checklist = self.classify_intake(
            LegalRequestClassifyIn(
                request_type=payload.request_type,
                notes=payload.notes,
                request_documents=payload.request_documents,
                deadline_at=payload.deadline_at,
                date_range_start=payload.date_range_start,
                date_range_end=payload.date_range_end,
            )
        )
        intake_token = secrets.token_urlsafe(32)
        intake_token_hash = _sha256(intake_token)

        now = _utcnow()
        clinical_record = ClinicalRecord(
            tenant_id=tenant_id,
            incident_number=f"LEGAL-{uuid.uuid4().hex[:12].upper()}",
            patient_external_ref=payload.mrn or payload.csn,
            lifecycle_state=RecordLifecycleState.READY,
            source_system="legal_requests_command",
            source_timestamp=now,
        )
        self.db.add(clinical_record)
        self.db.flush()

        status = (
            LegalRequestStatus.MISSING_DOCS
            if missing_items
            else LegalRequestStatus.TRIAGE_COMPLETE
        )
        requester_category = RequesterCategory(payload.requester_category)
        quote = self._compute_quote(
            request_type=classified_type.value,
            requester_category=requester_category.value,
            estimated_page_count=payload.requested_page_count,
            print_mail_requested=payload.print_mail_requested,
            rush_requested=payload.rush_requested,
            jurisdiction_state=payload.jurisdiction_state,
            has_missing_items=bool(missing_items),
        )
        request_row = LegalRequestCommand(
            tenant_id=tenant_id,
            clinical_record_id=clinical_record.id,
            request_type=classified_type,
            status=status,
            requesting_party=payload.requesting_party,
            requester_name=payload.requester_name,
            requesting_entity=payload.requesting_entity,
            patient_first_name=payload.patient_first_name,
            patient_last_name=payload.patient_last_name,
            patient_dob=payload.patient_dob,
            mrn=payload.mrn,
            csn=payload.csn,
            requested_date_from=payload.date_range_start,
            requested_date_to=payload.date_range_end,
            deadline_at=payload.deadline_at,
            delivery_preference=DeliveryPreference(payload.delivery_preference),
            triage_summary=triage.model_dump(),
            missing_items=[item.model_dump() for item in missing_items],
            required_document_checklist=[item.model_dump() for item in checklist],
            review_gate={},
            redaction_mode=RedactionMode.COURT_SAFE_MINIMUM_NECESSARY,
            intake_token_hash=intake_token_hash,
            requester_category=requester_category.value,
            workflow_state=quote.workflow_state,
            payment_status=(
                LegalPaymentStatus.PAYMENT_REQUIRED.value
                if quote.payment_required
                else LegalPaymentStatus.NOT_REQUIRED.value
            ),
            payment_required=quote.payment_required,
            margin_status=quote.margin_status,
            delivery_mode=quote.delivery_mode,
            print_mail_requested=payload.print_mail_requested,
            rush_requested=payload.rush_requested,
            estimated_page_count=payload.requested_page_count,
            jurisdiction_state=payload.jurisdiction_state.upper(),
            fee_quote=self._quote_to_payload(quote),
            financial_snapshot=self._financial_snapshot_from_quote(quote),
            fulfillment_gate={"hold_reasons": quote.hold_reasons},
        )
        self.db.add(request_row)
        self.db.flush()

        self._audit_event(
            tenant_id=tenant_id,
            entity_id=request_row.id,
            event_type="REQUEST_RECEIVED",
            actor_user_id=None,
            correlation_id=correlation_id,
            event_payload={
                "request_type": classified_type.value,
                "status": request_row.status.value,
                "missing_count": len(missing_items),
                "workflow_state": request_row.workflow_state,
                "payment_status": request_row.payment_status,
            },
        )
        self._custody_event(
            tenant_id=tenant_id,
            clinical_record_id=request_row.clinical_record_id,
            event_type="request_received",
            actor_user_id=None,
            state=ChainOfCustodyState.CLEAN,
            evidence={
                "request_id": str(request_row.id),
                "status": request_row.status.value,
            },
        )
        if missing_items:
            self._custody_event(
                tenant_id=tenant_id,
                clinical_record_id=request_row.clinical_record_id,
                event_type="missing_docs_detected",
                actor_user_id=None,
                state=ChainOfCustodyState.REVIEW_REQUIRED,
                evidence={
                    "missing_codes": [item.code for item in missing_items],
                },
            )

        return request_row, intake_token, triage, missing_items, checklist

    def create_upload_presign(
        self,
        *,
        tenant_id: uuid.UUID,
        request_id: uuid.UUID,
        intake_token: str,
        document_kind: str,
        file_name: str,
        content_type: str,
        correlation_id: str | None,
    ) -> tuple[LegalRequestUpload, str, str, int]:
        request_row = self._get_request_for_tenant(tenant_id=tenant_id, request_id=request_id)
        self._assert_intake_token(request_row=request_row, intake_token=intake_token)

        safe_name = file_name.replace("/", "_").replace("..", "_")
        object_key = (
            f"legal-requests/{tenant_id}/{request_id}/"
            f"{uuid.uuid4().hex}-{safe_name}"
        )
        bucket = get_settings().s3_bucket_docs
        expires_seconds = 900
        upload_url = ""
        if bucket:
            s3 = boto3.client("s3")
            upload_url = s3.generate_presigned_url(
                "put_object",
                Params={
                    "Bucket": bucket,
                    "Key": object_key,
                    "ContentType": content_type,
                },
                ExpiresIn=expires_seconds,
            )

        storage_uri = f"s3://{bucket}/{object_key}" if bucket else f"local://{object_key}"
        upload_row = LegalRequestUpload(
            tenant_id=tenant_id,
            legal_request_id=request_id,
            document_kind=document_kind.strip().lower(),
            file_name=safe_name,
            mime_type=content_type,
            storage_uri=storage_uri,
            byte_size=0,
            metadata_payload={"presigned": bool(upload_url)},
        )
        self.db.add(upload_row)
        self.db.flush()

        self._audit_event(
            tenant_id=tenant_id,
            entity_id=request_id,
            event_type="UPLOAD_URL_ISSUED",
            actor_user_id=None,
            correlation_id=correlation_id,
            event_payload={
                "upload_id": str(upload_row.id),
                "document_kind": upload_row.document_kind,
                "storage_uri": storage_uri,
            },
        )

        return upload_row, upload_url, object_key, expires_seconds

    def complete_upload(
        self,
        *,
        tenant_id: uuid.UUID,
        request_id: uuid.UUID,
        intake_token: str,
        upload_id: uuid.UUID,
        byte_size: int,
        checksum_sha256: str | None,
        correlation_id: str | None,
    ) -> tuple[
        LegalRequestCommand,
        LegalTriageSummary,
        list[MissingItemCard],
        list[RequiredDocumentChecklistItem],
    ]:
        request_row = self._get_request_for_tenant(tenant_id=tenant_id, request_id=request_id)
        self._assert_intake_token(request_row=request_row, intake_token=intake_token)

        upload_row = self.db.execute(
            select(LegalRequestUpload).where(
                LegalRequestUpload.id == upload_id,
                LegalRequestUpload.tenant_id == tenant_id,
                LegalRequestUpload.legal_request_id == request_id,
            )
        ).scalar_one_or_none()
        if upload_row is None:
            raise AppError(
                code=ErrorCodes.NOT_FOUND,
                message="Upload not found",
                status_code=404,
            )

        upload_row.byte_size = byte_size
        upload_row.checksum_sha256 = checksum_sha256
        upload_row.uploaded_at = _utcnow()

        uploaded_doc_kinds = self._uploaded_document_kinds(request_id=request_id, tenant_id=tenant_id)
        classified_type, triage, missing_items, checklist = self.classify_intake(
            LegalRequestClassifyIn(
                request_type=request_row.request_type.value,
                notes=None,
                request_documents=list(uploaded_doc_kinds),
                deadline_at=request_row.deadline_at,
                date_range_start=request_row.requested_date_from,
                date_range_end=request_row.requested_date_to,
            ),
            uploaded_document_kinds=uploaded_doc_kinds,
        )
        request_row.request_type = classified_type
        request_row.triage_summary = triage.model_dump()
        request_row.missing_items = [item.model_dump() for item in missing_items]
        request_row.required_document_checklist = [item.model_dump() for item in checklist]
        request_row.status = (
            LegalRequestStatus.MISSING_DOCS if missing_items else LegalRequestStatus.TRIAGE_COMPLETE
        )
        quote = self._compute_quote(
            request_type=request_row.request_type.value,
            requester_category=request_row.requester_category,
            estimated_page_count=request_row.estimated_page_count,
            print_mail_requested=request_row.print_mail_requested,
            rush_requested=request_row.rush_requested,
            jurisdiction_state=request_row.jurisdiction_state,
            has_missing_items=bool(missing_items),
        )
        request_row.workflow_state = quote.workflow_state
        request_row.payment_required = quote.payment_required
        request_row.payment_status = (
            LegalPaymentStatus.PAYMENT_REQUIRED.value
            if quote.payment_required
            else LegalPaymentStatus.NOT_REQUIRED.value
        )
        request_row.margin_status = quote.margin_status
        request_row.delivery_mode = quote.delivery_mode
        request_row.fee_quote = self._quote_to_payload(quote)
        request_row.financial_snapshot = self._financial_snapshot_from_quote(quote)
        request_row.fulfillment_gate = {"hold_reasons": quote.hold_reasons}

        self._audit_event(
            tenant_id=tenant_id,
            entity_id=request_row.id,
            event_type="DOCUMENT_UPLOADED",
            actor_user_id=None,
            correlation_id=correlation_id,
            event_payload={
                "upload_id": str(upload_row.id),
                "document_kind": upload_row.document_kind,
                "status": request_row.status.value,
            },
        )
        self._custody_event(
            tenant_id=tenant_id,
            clinical_record_id=request_row.clinical_record_id,
            event_type="document_uploaded",
            actor_user_id=None,
            state=ChainOfCustodyState.CLEAN,
            evidence={
                "upload_id": str(upload_row.id),
                "document_kind": upload_row.document_kind,
            },
        )
        return request_row, triage, missing_items, checklist

    def get_summary(self, tenant_id: uuid.UUID) -> LegalRequestsSummaryOut:
        rows = self._list_requests_for_tenant(tenant_id=tenant_id)
        open_rows = [r for r in rows if r.status != LegalRequestStatus.CLOSED]
        lane_counts = {
            "new_requests": len([r for r in rows if r.status in {LegalRequestStatus.RECEIVED, LegalRequestStatus.TRIAGE_COMPLETE}]),
            "missing_docs": len([r for r in rows if r.status == LegalRequestStatus.MISSING_DOCS]),
            "deadline_risk": len([r for r in rows if self._deadline_risk_for_row(r) == "high"]),
            "redaction_queue": len([r for r in rows if r.status == LegalRequestStatus.UNDER_REVIEW]),
            "delivery_queue": len([r for r in rows if r.status == LegalRequestStatus.PACKET_BUILDING]),
            "completed": len([r for r in rows if r.status in {LegalRequestStatus.DELIVERED, LegalRequestStatus.CLOSED}]),
            "high_risk": len([r for r in rows if self._is_high_risk(r)]),
        }
        urgent_deadlines = len(
            [
                r
                for r in open_rows
                if r.deadline_at and (r.deadline_at - _utcnow()) <= timedelta(hours=24)
            ]
        )
        return LegalRequestsSummaryOut(
            total_open=len(open_rows),
            lane_counts=lane_counts,
            urgent_deadlines=urgent_deadlines,
            high_risk_requests=lane_counts["high_risk"],
        )

    def list_queue(
        self,
        *,
        tenant_id: uuid.UUID,
        lane: str | None,
        limit: int,
    ) -> list[LegalQueueItemOut]:
        rows = self._list_requests_for_tenant(tenant_id=tenant_id)
        filtered = self._filter_lane(rows=rows, lane=lane)
        limited = filtered[:limit]
        return [
            LegalQueueItemOut(
                id=row.id,
                request_type=row.request_type.value,
                status=row.status.value,
                requester_name=row.requester_name,
                requesting_party=row.requesting_party,
                requesting_entity=row.requesting_entity,
                deadline_at=row.deadline_at,
                deadline_risk=self._deadline_risk_for_row(row),
                missing_count=len(row.missing_items or []),
                redaction_mode=row.redaction_mode.value,
                workflow_state=row.workflow_state,
                payment_status=row.payment_status,
                payment_required=row.payment_required,
                margin_status=row.margin_status,
                created_at=row.created_at,
                updated_at=row.updated_at,
            )
            for row in limited
        ]

    def get_request_detail(self, *, tenant_id: uuid.UUID, request_id: uuid.UUID) -> LegalRequestDetailOut:
        row = self._get_request_for_tenant(tenant_id=tenant_id, request_id=request_id)

        uploads = list(
            self.db.execute(
                select(LegalRequestUpload)
                .where(
                    LegalRequestUpload.tenant_id == tenant_id,
                    LegalRequestUpload.legal_request_id == request_id,
                )
                .order_by(LegalRequestUpload.uploaded_at.desc())
            ).scalars().all()
        )

        audit_rows = list(
            self.db.execute(
                select(RecordsAuditEvent)
                .where(
                    RecordsAuditEvent.tenant_id == tenant_id,
                    RecordsAuditEvent.entity_type == "legal_request_command",
                    RecordsAuditEvent.entity_id == request_id,
                )
                .order_by(RecordsAuditEvent.created_at.desc())
            ).scalars().all()
        )

        custody_rows = list(
            self.db.execute(
                select(ChainOfCustodyEvent)
                .where(
                    ChainOfCustodyEvent.tenant_id == tenant_id,
                    ChainOfCustodyEvent.clinical_record_id == row.clinical_record_id,
                )
                .order_by(ChainOfCustodyEvent.created_at.desc())
            ).scalars().all()
        )

        triage = self._triage_from_row(row)
        missing_items = self._missing_items_from_row(row)
        checklist = self._checklist_from_row(row)

        return LegalRequestDetailOut(
            id=row.id,
            clinical_record_id=row.clinical_record_id,
            request_type=row.request_type.value,
            status=row.status.value,
            requesting_party=row.requesting_party,
            requester_name=row.requester_name,
            requesting_entity=row.requesting_entity,
            patient_first_name=row.patient_first_name,
            patient_last_name=row.patient_last_name,
            patient_dob=row.patient_dob,
            mrn=row.mrn,
            csn=row.csn,
            requested_date_from=row.requested_date_from,
            requested_date_to=row.requested_date_to,
            delivery_preference=row.delivery_preference.value,
            deadline_at=row.deadline_at,
            triage_summary=triage,
            missing_items=missing_items,
            required_document_checklist=checklist,
            review_gate=row.review_gate or {},
            redaction_mode=row.redaction_mode.value,
            requester_category=row.requester_category,
            workflow_state=row.workflow_state,
            payment_status=row.payment_status,
            payment_required=row.payment_required,
            margin_status=row.margin_status,
            delivery_mode=row.delivery_mode,
            fee_quote=row.fee_quote or {},
            financial_snapshot=row.financial_snapshot or {},
            fulfillment_gate=row.fulfillment_gate or {},
            review_notes=row.review_notes,
            packet_manifest=row.packet_manifest or {},
            uploads=[LegalUploadOut.model_validate(upload) for upload in uploads],
            audit_timeline=[
                AuditTimelineEvent(
                    event_type=event.event_type,
                    created_at=event.created_at,
                    actor_user_id=event.actor_user_id,
                    correlation_id=event.correlation_id,
                    payload=event.event_payload,
                )
                for event in audit_rows
            ],
            custody_timeline=[
                ChainOfCustodyTimelineEvent(
                    event_type=event.event_type,
                    state=event.state.value,
                    created_at=event.created_at,
                    actor_user_id=event.actor_user_id,
                    evidence=event.evidence,
                )
                for event in custody_rows
            ],
            created_at=row.created_at,
            updated_at=row.updated_at,
        )

    def review_request(
        self,
        *,
        tenant_id: uuid.UUID,
        actor_user_id: uuid.UUID,
        request_id: uuid.UUID,
        payload: LegalRequestReviewIn,
        correlation_id: str | None,
    ) -> LegalRequestReviewOut:
        row = self._get_request_for_tenant(tenant_id=tenant_id, request_id=request_id)
        row.review_gate = {
            "authority_valid": payload.authority_valid,
            "identity_verified": payload.identity_verified,
            "completeness_valid": payload.completeness_valid,
            "document_sufficient": payload.document_sufficient,
            "minimum_necessary_scope": payload.minimum_necessary_scope,
            "delivery_method": payload.delivery_method,
            "decision": payload.decision,
        }
        row.redaction_mode = RedactionMode(payload.redaction_mode)
        row.reviewed_by_user_id = actor_user_id
        row.reviewed_at = _utcnow()
        row.review_notes = payload.decision_notes

        if payload.decision == "request_more_docs":
            row.status = LegalRequestStatus.MISSING_DOCS
        elif payload.decision == "reject":
            row.status = LegalRequestStatus.CLOSED
            row.closed_at = _utcnow()
        else:
            row.status = LegalRequestStatus.UNDER_REVIEW

        self._audit_event(
            tenant_id=tenant_id,
            entity_id=row.id,
            event_type="REVIEW_GATE_DECISION",
            actor_user_id=actor_user_id,
            correlation_id=correlation_id,
            event_payload={
                "decision": payload.decision,
                "status": row.status.value,
                "redaction_mode": row.redaction_mode.value,
            },
        )
        self._custody_event(
            tenant_id=tenant_id,
            clinical_record_id=row.clinical_record_id,
            event_type="reviewed_by",
            actor_user_id=actor_user_id,
            state=ChainOfCustodyState.CLEAN,
            evidence={
                "decision": payload.decision,
                "redaction_mode": row.redaction_mode.value,
            },
        )

        return LegalRequestReviewOut(
            request_id=row.id,
            status=row.status.value,
            redaction_mode=row.redaction_mode.value,
            review_gate=row.review_gate,
            workflow_state=row.workflow_state,
            payment_status=row.payment_status,
        )

    def build_packet(
        self,
        *,
        tenant_id: uuid.UUID,
        actor_user_id: uuid.UUID,
        request_id: uuid.UUID,
        correlation_id: str | None,
    ) -> tuple[LegalRequestCommand, dict[str, object]]:
        row = self._get_request_for_tenant(tenant_id=tenant_id, request_id=request_id)
        if row.status == LegalRequestStatus.CLOSED:
            raise AppError(
                code=ErrorCodes.VALIDATION_ERROR,
                message="Closed requests cannot build packets",
                status_code=400,
            )
        if row.payment_required and row.payment_status not in {
            LegalPaymentStatus.PAYMENT_COMPLETED.value,
            LegalPaymentStatus.CHECK_CLEARED.value,
            LegalPaymentStatus.CHECK_POSTED.value,
        }:
            raise AppError(
                code=ErrorCodes.VALIDATION_ERROR,
                message="Fulfillment hold: required payment has not cleared",
                status_code=409,
            )
        if row.margin_status in {
            MarginRiskStatus.AT_RISK_OF_LOSS.value,
            MarginRiskStatus.MANUAL_REVIEW_REQUIRED.value,
        } and not bool((row.review_gate or {}).get("financial_override_approved")):
            raise AppError(
                code=ErrorCodes.VALIDATION_ERROR,
                message="Fulfillment hold: financial review approval required",
                status_code=409,
            )

        row.status = LegalRequestStatus.PACKET_BUILDING
        row.workflow_state = LegalWorkflowState.READY_FOR_FULFILLMENT_REVIEW.value
        now = _utcnow()
        watermark = (
            f"FusionEMS Legal Request {row.id} | tenant={tenant_id} | generated={now.isoformat()}"
        )
        packet_payload = {
            "request_id": str(row.id),
            "request_type": row.request_type.value,
            "redaction_mode": row.redaction_mode.value,
            "minimum_necessary": row.redaction_mode == RedactionMode.COURT_SAFE_MINIMUM_NECESSARY,
            "requested_date_from": row.requested_date_from.isoformat() if row.requested_date_from else None,
            "requested_date_to": row.requested_date_to.isoformat() if row.requested_date_to else None,
            "watermark": watermark,
        }
        manifest = self._persist_packet_artifacts(
            tenant_id=tenant_id,
            request_id=row.id,
            packet_payload=packet_payload,
        )
        row.packet_manifest = manifest
        row.packet_generated_at = now

        self._audit_event(
            tenant_id=tenant_id,
            entity_id=row.id,
            event_type="PACKET_GENERATED",
            actor_user_id=actor_user_id,
            correlation_id=correlation_id,
            event_payload={"manifest": manifest},
        )
        self._custody_event(
            tenant_id=tenant_id,
            clinical_record_id=row.clinical_record_id,
            event_type="packet_generated",
            actor_user_id=actor_user_id,
            state=ChainOfCustodyState.CLEAN,
            evidence={"manifest": manifest},
        )
        return row, manifest

    def create_delivery_link(
        self,
        *,
        tenant_id: uuid.UUID,
        actor_user_id: uuid.UUID,
        request_id: uuid.UUID,
        expires_in_hours: int,
        recipient_hint: str | None,
        correlation_id: str | None,
    ) -> tuple[LegalDeliveryLink, str]:
        row = self._get_request_for_tenant(tenant_id=tenant_id, request_id=request_id)
        if not row.packet_manifest:
            raise AppError(
                code=ErrorCodes.VALIDATION_ERROR,
                message="Packet must be built before generating a delivery link",
                status_code=400,
            )

        token = secrets.token_urlsafe(30)
        link = LegalDeliveryLink(
            tenant_id=tenant_id,
            legal_request_id=request_id,
            token_hash=_sha256(token),
            expires_at=_utcnow() + timedelta(hours=expires_in_hours),
            max_uses=1,
            recipient_hint=recipient_hint,
            created_by_user_id=actor_user_id,
        )
        self.db.add(link)
        self.db.flush()

        row.status = LegalRequestStatus.DELIVERED
        row.delivered_at = _utcnow()
        row.workflow_state = LegalWorkflowState.DELIVERED.value

        self._audit_event(
            tenant_id=tenant_id,
            entity_id=request_id,
            event_type="SECURE_LINK_CREATED",
            actor_user_id=actor_user_id,
            correlation_id=correlation_id,
            event_payload={
                "delivery_link_id": str(link.id),
                "expires_at": link.expires_at.isoformat(),
            },
        )
        self._custody_event(
            tenant_id=tenant_id,
            clinical_record_id=row.clinical_record_id,
            event_type="secure_link_created",
            actor_user_id=actor_user_id,
            state=ChainOfCustodyState.CLEAN,
            evidence={
                "delivery_link_id": str(link.id),
                "expires_at": link.expires_at.isoformat(),
            },
        )

        base = str(get_settings().api_base_url).rstrip("/")
        delivery_url = f"{base}/api/v1/legal-requests/delivery/{token}"
        return link, delivery_url

    def consume_delivery_link(
        self,
        *,
        token: str,
        requester_ip: str | None,
        requester_user_agent: str | None,
        correlation_id: str | None,
    ) -> DeliveryAccessOut:
        token_hash = _sha256(token)
        link = self.db.execute(
            select(LegalDeliveryLink).where(LegalDeliveryLink.token_hash == token_hash)
        ).scalar_one_or_none()
        if link is None:
            raise AppError(
                code=ErrorCodes.NOT_FOUND,
                message="Delivery link not found",
                status_code=404,
            )

        now = _utcnow()
        if link.revoked_at is not None:
            raise AppError(
                code=ErrorCodes.VALIDATION_ERROR,
                message="Delivery link has been revoked",
                status_code=410,
            )
        if link.expires_at <= now:
            raise AppError(
                code=ErrorCodes.VALIDATION_ERROR,
                message="Delivery link has expired",
                status_code=410,
            )
        if link.use_count >= link.max_uses:
            raise AppError(
                code=ErrorCodes.VALIDATION_ERROR,
                message="Delivery link already consumed",
                status_code=410,
            )

        request_row = self._get_request_for_tenant(tenant_id=link.tenant_id, request_id=link.legal_request_id)

        link.use_count += 1
        link.download_ip = requester_ip
        link.download_user_agent = requester_user_agent
        if link.use_count >= link.max_uses:
            link.consumed_at = now

        self._audit_event(
            tenant_id=link.tenant_id,
            entity_id=request_row.id,
            event_type="SECURE_LINK_ACCESSED",
            actor_user_id=None,
            correlation_id=correlation_id,
            event_payload={
                "delivery_link_id": str(link.id),
                "requester_ip": requester_ip,
                "user_agent": requester_user_agent,
                "use_count": link.use_count,
            },
        )
        self._custody_event(
            tenant_id=link.tenant_id,
            clinical_record_id=request_row.clinical_record_id,
            event_type="accessed_by",
            actor_user_id=None,
            state=ChainOfCustodyState.CLEAN,
            evidence={
                "delivery_link_id": str(link.id),
                "requester_ip": requester_ip,
                "user_agent": requester_user_agent,
            },
        )

        return DeliveryAccessOut(
            request_id=request_row.id,
            status=request_row.status.value,
            packet_manifest=request_row.packet_manifest or {},
            redaction_mode=request_row.redaction_mode.value,
        )

    def revoke_delivery_link(
        self,
        *,
        tenant_id: uuid.UUID,
        actor_user_id: uuid.UUID,
        delivery_link_id: uuid.UUID,
        correlation_id: str | None,
    ) -> None:
        link = self.db.execute(
            select(LegalDeliveryLink).where(
                LegalDeliveryLink.id == delivery_link_id,
                LegalDeliveryLink.tenant_id == tenant_id,
            )
        ).scalar_one_or_none()
        if link is None:
            raise AppError(
                code=ErrorCodes.NOT_FOUND,
                message="Delivery link not found",
                status_code=404,
            )
        if link.revoked_at is None:
            link.revoked_at = _utcnow()

        row = self._get_request_for_tenant(tenant_id=tenant_id, request_id=link.legal_request_id)
        self._audit_event(
            tenant_id=tenant_id,
            entity_id=row.id,
            event_type="SECURE_LINK_REVOKED",
            actor_user_id=actor_user_id,
            correlation_id=correlation_id,
            event_payload={"delivery_link_id": str(link.id)},
        )
        self._custody_event(
            tenant_id=tenant_id,
            clinical_record_id=row.clinical_record_id,
            event_type="secure_link_revoked",
            actor_user_id=actor_user_id,
            state=ChainOfCustodyState.REVIEW_REQUIRED,
            evidence={"delivery_link_id": str(link.id)},
        )

    def close_request(
        self,
        *,
        tenant_id: uuid.UUID,
        actor_user_id: uuid.UUID,
        request_id: uuid.UUID,
        correlation_id: str | None,
    ) -> LegalRequestCloseOut:
        row = self._get_request_for_tenant(tenant_id=tenant_id, request_id=request_id)
        row.status = LegalRequestStatus.CLOSED
        row.closed_at = _utcnow()
        row.workflow_state = LegalWorkflowState.MANUAL_APPROVAL_REQUIRED.value

        self._audit_event(
            tenant_id=tenant_id,
            entity_id=row.id,
            event_type="REQUEST_CLOSED",
            actor_user_id=actor_user_id,
            correlation_id=correlation_id,
            event_payload={"status": row.status.value},
        )
        self._custody_event(
            tenant_id=tenant_id,
            clinical_record_id=row.clinical_record_id,
            event_type="expired_or_closed",
            actor_user_id=actor_user_id,
            state=ChainOfCustodyState.CLEAN,
            evidence={"status": row.status.value},
        )
        return LegalRequestCloseOut(request_id=row.id, status=row.status.value)

    def preview_quote(
        self,
        *,
        tenant_id: uuid.UUID,
        request_id: uuid.UUID,
        payload: LegalPricingQuoteIn,
        correlation_id: str | None,
    ) -> LegalFeeQuoteOut:
        row = self._get_request_for_tenant(tenant_id=tenant_id, request_id=request_id)
        self._assert_intake_token(request_row=row, intake_token=payload.intake_token)

        if payload.requested_page_count is not None:
            row.estimated_page_count = payload.requested_page_count
        if payload.print_mail_requested is not None:
            row.print_mail_requested = payload.print_mail_requested
        if payload.rush_requested is not None:
            row.rush_requested = payload.rush_requested

        quote = self._compute_quote(
            request_type=row.request_type.value,
            requester_category=row.requester_category,
            estimated_page_count=row.estimated_page_count,
            print_mail_requested=row.print_mail_requested,
            rush_requested=row.rush_requested,
            jurisdiction_state=row.jurisdiction_state,
            has_missing_items=bool(row.missing_items),
        )

        row.payment_required = quote.payment_required
        row.margin_status = quote.margin_status
        row.workflow_state = quote.workflow_state
        row.payment_status = (
            LegalPaymentStatus.PAYMENT_REQUIRED.value if quote.payment_required else LegalPaymentStatus.NOT_REQUIRED.value
        )
        row.delivery_mode = quote.delivery_mode
        row.fee_quote = self._quote_to_payload(quote)
        row.financial_snapshot = self._financial_snapshot_from_quote(quote)
        row.fulfillment_gate = {"hold_reasons": quote.hold_reasons}

        self._audit_event(
            tenant_id=tenant_id,
            entity_id=row.id,
            event_type="LEGAL_FEE_QUOTE_REFRESHED",
            actor_user_id=None,
            correlation_id=correlation_id,
            event_payload={
                "total_due_cents": quote.total_due_cents,
                "margin_status": quote.margin_status,
                "workflow_state": quote.workflow_state,
            },
        )

        return self._quote_out(request_id=row.id, requester_category=row.requester_category, quote=quote)

    def create_payment_checkout(
        self,
        *,
        tenant_id: uuid.UUID,
        request_id: uuid.UUID,
        intake_token: str,
        success_url: str | None,
        cancel_url: str | None,
        correlation_id: str | None,
    ) -> LegalPaymentCheckoutOut:
        row = self._get_request_for_tenant(tenant_id=tenant_id, request_id=request_id)
        self._assert_intake_token(request_row=row, intake_token=intake_token)

        quote = self._compute_quote(
            request_type=row.request_type.value,
            requester_category=row.requester_category,
            estimated_page_count=row.estimated_page_count,
            print_mail_requested=row.print_mail_requested,
            rush_requested=row.rush_requested,
            jurisdiction_state=row.jurisdiction_state,
            has_missing_items=bool(row.missing_items),
        )
        row.fee_quote = self._quote_to_payload(quote)
        row.financial_snapshot = self._financial_snapshot_from_quote(quote)
        row.fulfillment_gate = {"hold_reasons": quote.hold_reasons}
        row.margin_status = quote.margin_status
        row.payment_required = quote.payment_required
        row.delivery_mode = quote.delivery_mode

        if not quote.payment_required or quote.total_due_cents <= 0:
            raise AppError(
                code=ErrorCodes.VALIDATION_ERROR,
                message="Payment checkout is not required for this request",
                status_code=409,
            )

        connected_account = self.db.execute(
            select(Tenant.stripe_connected_account_id).where(Tenant.id == tenant_id)
        ).scalar_one_or_none()
        if not connected_account:
            raise AppError(
                code=ErrorCodes.VALIDATION_ERROR,
                message="Tenant Stripe connected account is not configured",
                status_code=422,
            )

        settings = get_settings()
        cfg = StripeConfig(secret_key=settings.stripe_secret_key)
        base = str(get_settings().api_base_url).rstrip("/")
        success = success_url or f"{base}/legal/payment/success?request_id={row.id}"
        cancel = cancel_url or f"{base}/legal/payment/cancel?request_id={row.id}"

        try:
            checkout = create_connect_checkout_session(
                cfg=cfg,
                connected_account_id=connected_account,
                amount_cents=quote.total_due_cents,
                currency=quote.currency,
                statement_id=str(row.id),
                tenant_id=str(tenant_id),
                patient_account_ref=row.requester_name,
                lob_letter_id=None,
                success_url=success,
                cancel_url=cancel,
                application_fee_amount_cents=quote.platform_fee_cents,
                product_name="FusionEMS Legal Records Request",
                product_description=f"Legal request {row.id}",
                metadata_extra={
                    "legal_request_id": str(row.id),
                    "legal_request_tenant_id": str(tenant_id),
                },
            )
        except StripeNotConfigured as exc:
            raise AppError(
                code=ErrorCodes.VALIDATION_ERROR,
                message=f"Stripe checkout unavailable: {exc}",
                status_code=503,
            ) from exc

        payment = LegalRequestPayment(
            tenant_id=tenant_id,
            legal_request_id=row.id,
            provider="stripe",
            status=LegalPaymentStatus.PAYMENT_LINK_CREATED.value,
            amount_due_cents=quote.total_due_cents,
            amount_collected_cents=0,
            platform_fee_cents=quote.platform_fee_cents,
            agency_payout_cents=quote.agency_payout_cents,
            currency=quote.currency,
            stripe_connected_account_id=connected_account,
            stripe_checkout_session_id=str(checkout.get("checkout_session_id") or ""),
            metadata_payload={
                "checkout_url": str(checkout.get("checkout_url") or ""),
                "margin_status": quote.margin_status,
            },
        )
        self.db.add(payment)
        self.db.flush()

        row.payment_status = LegalPaymentStatus.PAYMENT_LINK_CREATED.value
        row.workflow_state = LegalWorkflowState.PAYMENT_LINK_CREATED.value

        self._audit_event(
            tenant_id=tenant_id,
            entity_id=row.id,
            event_type="LEGAL_PAYMENT_CHECKOUT_CREATED",
            actor_user_id=None,
            correlation_id=correlation_id,
            event_payload={
                "payment_id": str(payment.id),
                "checkout_session_id": payment.stripe_checkout_session_id,
                "amount_due_cents": payment.amount_due_cents,
            },
        )

        checkout_session_id = payment.stripe_checkout_session_id or ""
        checkout_url = str(checkout.get("checkout_url") or "")
        return LegalPaymentCheckoutOut(
            request_id=row.id,
            payment_id=payment.id,
            payment_status=row.payment_status,
            workflow_state=row.workflow_state,
            checkout_url=checkout_url,
            checkout_session_id=checkout_session_id,
            connected_account_id=connected_account,
            amount_due_cents=payment.amount_due_cents,
            agency_payout_cents=payment.agency_payout_cents,
            platform_fee_cents=payment.platform_fee_cents,
        )

    def get_request_payment(self, *, tenant_id: uuid.UUID, request_id: uuid.UUID) -> LegalRequestPaymentOut:
        row = self._get_request_for_tenant(tenant_id=tenant_id, request_id=request_id)
        payment = self._latest_payment_for_request(tenant_id=tenant_id, request_id=request_id)
        if payment is None:
            raise AppError(
                code=ErrorCodes.NOT_FOUND,
                message="No payment record exists for this legal request",
                status_code=404,
            )
        return self._payment_out(payment=payment, request_id=row.id)

    def mark_check_received(
        self,
        *,
        tenant_id: uuid.UUID,
        actor_user_id: uuid.UUID,
        request_id: uuid.UUID,
        check_reference: str,
        correlation_id: str | None,
    ) -> LegalRequestPaymentOut:
        row = self._get_request_for_tenant(tenant_id=tenant_id, request_id=request_id)
        payment = self._latest_payment_for_request(tenant_id=tenant_id, request_id=request_id)
        if payment is None:
            payment = LegalRequestPayment(
                tenant_id=tenant_id,
                legal_request_id=request_id,
                provider="check",
                status=LegalPaymentStatus.CHECK_RECEIVED_BY_AGENCY.value,
                amount_due_cents=int((row.fee_quote or {}).get("total_due_cents", 0)),
                amount_collected_cents=int((row.fee_quote or {}).get("total_due_cents", 0)),
                platform_fee_cents=int((row.fee_quote or {}).get("platform_fee_cents", 0)),
                agency_payout_cents=int((row.fee_quote or {}).get("agency_payout_cents", 0)),
                currency=str((row.fee_quote or {}).get("currency", "usd")),
            )
            self.db.add(payment)
            self.db.flush()

        payment.status = LegalPaymentStatus.CHECK_RECEIVED_BY_AGENCY.value
        payment.check_reference = check_reference
        payment.check_received_at = _utcnow()
        payment.paid_at = _utcnow()
        if payment.amount_collected_cents <= 0:
            payment.amount_collected_cents = payment.amount_due_cents

        row.payment_status = LegalPaymentStatus.CHECK_CLEARED.value
        row.workflow_state = LegalWorkflowState.PAYMENT_COMPLETED.value

        self._audit_event(
            tenant_id=tenant_id,
            entity_id=row.id,
            event_type="LEGAL_CHECK_RECEIVED_BY_AGENCY",
            actor_user_id=actor_user_id,
            correlation_id=correlation_id,
            event_payload={
                "payment_id": str(payment.id),
                "check_reference": check_reference,
            },
        )
        return self._payment_out(payment=payment, request_id=row.id)

    def apply_stripe_webhook_event(self, *, event: dict[str, object], correlation_id: str | None) -> None:
        event_type = str(event.get("type") or "")
        data_obj = event.get("data")
        if not isinstance(data_obj, dict):
            return
        object_obj = data_obj.get("object")
        if not isinstance(object_obj, dict):
            return
        metadata = object_obj.get("metadata")
        if not isinstance(metadata, dict):
            return

        legal_request_id_raw = metadata.get("legal_request_id")
        tenant_id_raw = metadata.get("legal_request_tenant_id") or metadata.get("tenant_id")
        if not legal_request_id_raw or not tenant_id_raw:
            return

        try:
            legal_request_id = uuid.UUID(str(legal_request_id_raw))
            tenant_id = uuid.UUID(str(tenant_id_raw))
        except ValueError:
            return

        row = self.db.execute(
            select(LegalRequestCommand).where(
                LegalRequestCommand.id == legal_request_id,
                LegalRequestCommand.tenant_id == tenant_id,
            )
        ).scalar_one_or_none()
        if row is None:
            return

        payment = self._latest_payment_for_request(tenant_id=tenant_id, request_id=legal_request_id)
        if payment is None:
            return

        if event_type == "checkout.session.completed":
            payment.status = LegalPaymentStatus.PAYMENT_COMPLETED.value
            payment.amount_collected_cents = payment.amount_due_cents
            payment.paid_at = _utcnow()
            payment.stripe_checkout_session_id = str(object_obj.get("id") or payment.stripe_checkout_session_id or "")

            pi_ref = object_obj.get("payment_intent")
            if isinstance(pi_ref, str) and pi_ref:
                payment.stripe_payment_intent_id = pi_ref

            row.payment_status = LegalPaymentStatus.PAYMENT_COMPLETED.value
            row.workflow_state = LegalWorkflowState.PAYMENT_COMPLETED.value
            row.fulfillment_gate = {"hold_reasons": []}
            self._audit_event(
                tenant_id=tenant_id,
                entity_id=row.id,
                event_type="LEGAL_PAYMENT_COMPLETED",
                actor_user_id=None,
                correlation_id=correlation_id,
                event_payload={
                    "payment_id": str(payment.id),
                    "checkout_session_id": payment.stripe_checkout_session_id,
                },
            )
            return

        if event_type == "payment_intent.payment_failed":
            payment.status = LegalPaymentStatus.PAYMENT_FAILED.value
            payment.failed_at = _utcnow()
            row.payment_status = LegalPaymentStatus.PAYMENT_FAILED.value
            row.workflow_state = LegalWorkflowState.PAYMENT_REQUIRED.value
            row.fulfillment_gate = {
                "hold_reasons": ["Payment failed. Fulfillment remains blocked until payment succeeds."]
            }
            self._audit_event(
                tenant_id=tenant_id,
                entity_id=row.id,
                event_type="LEGAL_PAYMENT_FAILED",
                actor_user_id=None,
                correlation_id=correlation_id,
                event_payload={"payment_id": str(payment.id)},
            )
            return

        if event_type == "charge.refunded":
            payment.status = LegalPaymentStatus.REFUNDED.value
            payment.refunded_at = _utcnow()
            row.payment_status = LegalPaymentStatus.REFUNDED.value
            row.workflow_state = LegalWorkflowState.REFUNDED.value
            row.fulfillment_gate = {"hold_reasons": ["Refund posted. Manual review required before further release."]}
            self._audit_event(
                tenant_id=tenant_id,
                entity_id=row.id,
                event_type="LEGAL_PAYMENT_REFUNDED",
                actor_user_id=None,
                correlation_id=correlation_id,
                event_payload={"payment_id": str(payment.id)},
            )

    def _get_request_for_tenant(self, *, tenant_id: uuid.UUID, request_id: uuid.UUID) -> LegalRequestCommand:
        row = self.db.execute(
            select(LegalRequestCommand).where(
                LegalRequestCommand.id == request_id,
                LegalRequestCommand.tenant_id == tenant_id,
            )
        ).scalar_one_or_none()
        if row is None:
            raise AppError(
                code=ErrorCodes.NOT_FOUND,
                message="Legal request not found",
                status_code=404,
            )
        return row

    def _assert_intake_token(self, *, request_row: LegalRequestCommand, intake_token: str) -> None:
        provided_hash = _sha256(intake_token)
        if provided_hash != request_row.intake_token_hash:
            raise AppError(
                code=ErrorCodes.VALIDATION_ERROR,
                message="Invalid intake token",
                status_code=403,
            )

    def _classify_type(self, payload: LegalRequestClassifyIn) -> LegalRequestType:
        if payload.request_type is not None:
            return LegalRequestType(payload.request_type)
        corpus = " ".join(
            [
                payload.notes or "",
                " ".join(payload.request_documents),
            ]
        ).lower()
        if "court" in corpus and "order" in corpus:
            return LegalRequestType.COURT_ORDER
        if "subpoena" in corpus:
            return LegalRequestType.SUBPOENA
        return LegalRequestType.HIPAA_ROI

    def _required_document_checklist(
        self,
        request_type: LegalRequestType,
        uploaded_document_kinds: set[str],
    ) -> list[RequiredDocumentChecklistItem]:
        base: dict[LegalRequestType, list[tuple[str, str]]] = {
            LegalRequestType.HIPAA_ROI: [
                ("authorization", "Valid HIPAA authorization"),
                ("identity_proof", "Identity proof for patient/authorized rep"),
            ],
            LegalRequestType.SUBPOENA: [
                ("subpoena", "Signed subpoena"),
                ("service_proof", "Service proof / receipt"),
            ],
            LegalRequestType.COURT_ORDER: [
                ("court_order", "Signed court order"),
                ("jurisdiction_details", "Jurisdiction and scope details"),
            ],
        }
        expected = base.get(request_type, [])
        return [
            RequiredDocumentChecklistItem(
                code=code,
                label=label,
                required=True,
                satisfied=code in uploaded_document_kinds,
            )
            for code, label in expected
        ]

    def _compute_missing_items(
        self,
        *,
        classified_type: LegalRequestType,
        payload: LegalRequestClassifyIn,
        required_checklist: list[RequiredDocumentChecklistItem],
        uploaded_document_kinds: set[str],
    ) -> list[MissingItemCard]:
        missing: list[MissingItemCard] = []

        for item in required_checklist:
            if item.satisfied:
                continue
            if item.code == "authorization":
                missing.append(
                    MissingItemCard(
                        code="missing_authorization",
                        title="No valid authorization",
                        detail="A valid HIPAA release authorization is required for ROI processing.",
                        severity="high",
                    )
                )
            elif item.code == "subpoena":
                missing.append(
                    MissingItemCard(
                        code="missing_subpoena",
                        title="No subpoena document",
                        detail="A subpoena workflow requires an uploaded subpoena artifact.",
                        severity="high",
                    )
                )
            elif item.code == "court_order":
                missing.append(
                    MissingItemCard(
                        code="missing_court_order",
                        title="No court order",
                        detail="A court order workflow requires an uploaded signed order.",
                        severity="high",
                    )
                )

        if not any([payload.date_range_start, payload.date_range_end]):
            missing.append(
                MissingItemCard(
                    code="missing_date_range",
                    title="Date range missing",
                    detail="Request must include a bounded date range for minimum necessary disclosure.",
                    severity="medium",
                )
            )

        if (
            payload.date_range_start
            and payload.date_range_end
            and (payload.date_range_end - payload.date_range_start).days > 365
        ):
            missing.append(
                MissingItemCard(
                    code="scope_too_broad",
                    title="Scope too broad",
                    detail="Requested date range exceeds one year; narrow scope for court-safe release.",
                    severity="high",
                )
            )

        if not any([payload.request_type, payload.notes, payload.request_documents]):
            missing.append(
                MissingItemCard(
                    code="patient_mismatch",
                    title="Patient mismatch",
                    detail="Submission lacks enough context to verify request-to-patient alignment.",
                    severity="medium",
                )
            )

        # Support mismatch checks between claimed type and uploaded evidence.
        if classified_type == LegalRequestType.HIPAA_ROI and (
            "subpoena" in uploaded_document_kinds or "court_order" in uploaded_document_kinds
        ):
            missing.append(
                MissingItemCard(
                    code="type_document_mismatch",
                    title="Type/document mismatch",
                    detail="Attached legal support does not match selected HIPAA ROI type.",
                    severity="medium",
                )
            )
        if classified_type == LegalRequestType.SUBPOENA and "court_order" in uploaded_document_kinds:
            missing.append(
                MissingItemCard(
                    code="type_document_mismatch",
                    title="Type/document mismatch",
                    detail="Court-order support attached but request is classified as subpoena.",
                    severity="low",
                )
            )

        deduped: dict[str, MissingItemCard] = {item.code: item for item in missing}
        return list(deduped.values())

    def _build_fallback_triage(
        self,
        *,
        classified_type: LegalRequestType,
        payload: LegalRequestClassifyIn,
        missing_items: list[MissingItemCard],
        uploaded_document_kinds: set[str],
    ) -> LegalTriageSummary:
        urgency = "normal"
        deadline_risk = "none"
        now = _utcnow()
        if payload.deadline_at:
            delta = payload.deadline_at - now
            if delta <= timedelta(hours=24):
                urgency = "critical"
                deadline_risk = "high"
            elif delta <= timedelta(hours=72):
                urgency = "high"
                deadline_risk = "high"
            elif delta <= timedelta(days=7):
                urgency = "normal"
                deadline_risk = "watch"

        high_missing = any(item.severity == "high" for item in missing_items)
        if high_missing and urgency in {"low", "normal"}:
            urgency = "high"

        mismatch_signals = [
            item.title
            for item in missing_items
            if item.code in {"type_document_mismatch", "scope_too_broad", "patient_mismatch"}
        ]
        confidence = 0.91 if payload.request_type else 0.68
        rationale = (
            f"Deterministic triage from request fields and {len(uploaded_document_kinds)} uploaded document kinds."
        )

        return LegalTriageSummary(
            classification=classified_type.value,
            classification_confidence=confidence,
            likely_invalid_or_incomplete=bool(missing_items),
            urgency_level=urgency,
            deadline_risk=deadline_risk,
            mismatch_signals=mismatch_signals,
            rationale=rationale,
        )

    def _try_ai_triage(
        self,
        *,
        classified_type: LegalRequestType,
        payload: LegalRequestClassifyIn,
        missing_items: list[MissingItemCard],
        required_checklist: list[RequiredDocumentChecklistItem],
    ) -> LegalTriageSummary | None:
        settings = get_settings()
        if not settings.openai_api_key:
            return None

        try:
            service = AiService()
        except RuntimeError:
            return None

        system_prompt = (
            "You are a legal intake triage assistant for healthcare records release. "
            "Return JSON only with keys: classification_confidence, urgency_level, deadline_risk, "
            "mismatch_signals, rationale. Never generate legal advice."
        )
        user_payload = {
            "classified_type": classified_type.value,
            "notes": payload.notes,
            "documents": payload.request_documents,
            "deadline_at": payload.deadline_at.isoformat() if payload.deadline_at else None,
            "date_range_start": payload.date_range_start.isoformat() if payload.date_range_start else None,
            "date_range_end": payload.date_range_end.isoformat() if payload.date_range_end else None,
            "missing_items": [item.model_dump() for item in missing_items],
            "required_checklist": [item.model_dump() for item in required_checklist],
        }
        try:
            content, _meta = service.chat(
                system=system_prompt,
                user=json.dumps(user_payload, separators=(",", ":")),
                max_tokens=450,
            )
            parsed = json.loads(content)
            confidence = float(parsed.get("classification_confidence", 0.75))
            urgency_level = str(parsed.get("urgency_level", "normal")).lower()
            deadline_risk = str(parsed.get("deadline_risk", "watch")).lower()
            mismatch_signals = [str(v) for v in parsed.get("mismatch_signals", []) if str(v).strip()]
            rationale = str(parsed.get("rationale", "AI triage applied with governance constraints."))

            if urgency_level not in {"low", "normal", "high", "critical"}:
                urgency_level = "normal"
            if deadline_risk not in {"none", "watch", "high"}:
                deadline_risk = "watch"
            confidence = max(0.0, min(1.0, confidence))

            return LegalTriageSummary(
                classification=classified_type.value,
                classification_confidence=confidence,
                likely_invalid_or_incomplete=bool(missing_items),
                urgency_level=urgency_level,
                deadline_risk=deadline_risk,
                mismatch_signals=mismatch_signals,
                rationale=rationale,
            )
        except Exception as exc:  # noqa: BLE001
            logger.warning(
                "legal_ai_triage_fallback",
                extra={"extra_fields": {"error": str(exc)}},
            )
            return None

    def _persist_packet_artifacts(
        self,
        *,
        tenant_id: uuid.UUID,
        request_id: uuid.UUID,
        packet_payload: dict[str, Any],
    ) -> dict[str, object]:
        packet_json = json.dumps(packet_payload, indent=2).encode("utf-8")
        redacted_json = json.dumps(
            {
                **packet_payload,
                "redaction_reason": "court_safe_minimum_necessary",
            },
            indent=2,
        ).encode("utf-8")
        disclosure_json = json.dumps(
            {
                "request_id": str(request_id),
                "tenant_id": str(tenant_id),
                "released_at": _utcnow().isoformat(),
                "minimum_necessary": True,
            },
            indent=2,
        ).encode("utf-8")

        bucket = default_exports_bucket()
        if not bucket:
            return {
                "response_packet_uri": f"inline://legal/{request_id}/response.json",
                "redacted_packet_uri": f"inline://legal/{request_id}/redacted.json",
                "disclosure_record_uri": f"inline://legal/{request_id}/disclosure.json",
                "audit_log_uri": f"inline://legal/{request_id}/audit.json",
                "chain_of_custody_uri": f"inline://legal/{request_id}/custody.json",
                "watermarking": True,
            }

        base_key = f"legal-requests/{tenant_id}/{request_id}"
        response_ref = put_bytes(
            bucket=bucket,
            key=f"{base_key}/response_packet.json",
            content=packet_json,
            content_type="application/json",
        )
        redacted_ref = put_bytes(
            bucket=bucket,
            key=f"{base_key}/redacted_packet.json",
            content=redacted_json,
            content_type="application/json",
        )
        disclosure_ref = put_bytes(
            bucket=bucket,
            key=f"{base_key}/disclosure_record.json",
            content=disclosure_json,
            content_type="application/json",
        )
        return {
            "response_packet_uri": f"s3://{response_ref.bucket}/{response_ref.key}",
            "redacted_packet_uri": f"s3://{redacted_ref.bucket}/{redacted_ref.key}",
            "disclosure_record_uri": f"s3://{disclosure_ref.bucket}/{disclosure_ref.key}",
            "audit_log_uri": f"s3://{bucket}/{base_key}/audit_log.json",
            "chain_of_custody_uri": f"s3://{bucket}/{base_key}/chain_of_custody.json",
            "watermarking": True,
        }

    def _audit_event(
        self,
        *,
        tenant_id: uuid.UUID,
        entity_id: uuid.UUID,
        event_type: str,
        actor_user_id: uuid.UUID | None,
        correlation_id: str | None,
        event_payload: dict[str, object],
    ) -> None:
        self.db.add(
            RecordsAuditEvent(
                tenant_id=tenant_id,
                entity_type="legal_request_command",
                entity_id=entity_id,
                event_type=event_type,
                actor_user_id=actor_user_id,
                correlation_id=correlation_id,
                event_payload=event_payload,
            )
        )

    def _custody_event(
        self,
        *,
        tenant_id: uuid.UUID,
        clinical_record_id: uuid.UUID,
        event_type: str,
        actor_user_id: uuid.UUID | None,
        state: ChainOfCustodyState,
        evidence: dict[str, object],
    ) -> None:
        self.db.add(
            ChainOfCustodyEvent(
                tenant_id=tenant_id,
                clinical_record_id=clinical_record_id,
                state=state,
                event_type=event_type,
                actor_user_id=actor_user_id,
                evidence=evidence,
            )
        )

    def _list_requests_for_tenant(self, *, tenant_id: uuid.UUID) -> list[LegalRequestCommand]:
        stmt: Select[tuple[LegalRequestCommand]] = (
            select(LegalRequestCommand)
            .where(LegalRequestCommand.tenant_id == tenant_id)
            .order_by(LegalRequestCommand.deadline_at.asc().nulls_last(), LegalRequestCommand.updated_at.desc())
        )
        return list(self.db.execute(stmt).scalars().all())

    def _filter_lane(
        self,
        *,
        rows: list[LegalRequestCommand],
        lane: str | None,
    ) -> list[LegalRequestCommand]:
        if not lane:
            return rows
        normalized_lane = lane.strip().lower()
        if normalized_lane == "new_requests":
            return [r for r in rows if r.status in {LegalRequestStatus.RECEIVED, LegalRequestStatus.TRIAGE_COMPLETE}]
        if normalized_lane == "missing_docs":
            return [r for r in rows if r.status == LegalRequestStatus.MISSING_DOCS]
        if normalized_lane == "deadline_risk":
            return [r for r in rows if self._deadline_risk_for_row(r) == "high"]
        if normalized_lane == "redaction_queue":
            return [r for r in rows if r.status == LegalRequestStatus.UNDER_REVIEW]
        if normalized_lane == "delivery_queue":
            return [r for r in rows if r.status == LegalRequestStatus.PACKET_BUILDING]
        if normalized_lane == "completed":
            return [r for r in rows if r.status in {LegalRequestStatus.DELIVERED, LegalRequestStatus.CLOSED}]
        if normalized_lane == "high_risk":
            return [r for r in rows if self._is_high_risk(r)]
        return rows

    def _deadline_risk_for_row(self, row: LegalRequestCommand) -> str:
        triage = row.triage_summary or {}
        value = str(triage.get("deadline_risk", "none")).lower()
        if value in {"none", "watch", "high"}:
            return value
        return "none"

    def _is_high_risk(self, row: LegalRequestCommand) -> bool:
        triage = row.triage_summary or {}
        urgency = str(triage.get("urgency_level", "normal")).lower()
        deadline_risk = self._deadline_risk_for_row(row)
        return urgency in {"high", "critical"} or deadline_risk == "high"

    def _uploaded_document_kinds(self, *, request_id: uuid.UUID, tenant_id: uuid.UUID) -> set[str]:
        rows = self.db.execute(
            select(LegalRequestUpload.document_kind).where(
                LegalRequestUpload.tenant_id == tenant_id,
                LegalRequestUpload.legal_request_id == request_id,
            )
        ).all()
        return {str(kind).strip().lower() for (kind,) in rows if kind}

    def _triage_from_row(self, row: LegalRequestCommand) -> LegalTriageSummary:
        data = row.triage_summary or {}
        mismatch = data.get("mismatch_signals")
        mismatch_signals = [str(item) for item in mismatch] if isinstance(mismatch, list) else []
        classification = str(data.get("classification", row.request_type.value)).lower()
        if classification not in {"hipaa_roi", "subpoena", "court_order"}:
            classification = row.request_type.value

        urgency_level = str(data.get("urgency_level", "normal")).lower()
        if urgency_level not in {"low", "normal", "high", "critical"}:
            urgency_level = "normal"

        deadline_risk = str(data.get("deadline_risk", "none")).lower()
        if deadline_risk not in {"none", "watch", "high"}:
            deadline_risk = "none"

        return LegalTriageSummary(
            classification=classification,
            classification_confidence=float(data.get("classification_confidence", 0.0) or 0.0),
            likely_invalid_or_incomplete=bool(data.get("likely_invalid_or_incomplete", False)),
            urgency_level=urgency_level,
            deadline_risk=deadline_risk,
            mismatch_signals=mismatch_signals,
            rationale=str(data.get("rationale", "No triage rationale available")),
        )

    def _missing_items_from_row(self, row: LegalRequestCommand) -> list[MissingItemCard]:
        items = row.missing_items or []
        return [MissingItemCard.model_validate(item) for item in items if isinstance(item, dict)]

    def _checklist_from_row(self, row: LegalRequestCommand) -> list[RequiredDocumentChecklistItem]:
        items = row.required_document_checklist or []
        return [RequiredDocumentChecklistItem.model_validate(item) for item in items if isinstance(item, dict)]

    def _compute_quote(
        self,
        *,
        request_type: str,
        requester_category: str,
        estimated_page_count: int,
        print_mail_requested: bool,
        rush_requested: bool,
        jurisdiction_state: str,
        has_missing_items: bool,
    ) -> LegalPricingResult:
        quote = compute_legal_quote(
            LegalPricingInput(
                request_type=request_type,
                requester_category=requester_category,
                estimated_page_count=estimated_page_count,
                print_mail_requested=print_mail_requested,
                rush_requested=rush_requested,
                jurisdiction_state=jurisdiction_state,
            )
        )
        if has_missing_items:
            hold_reasons = list(quote.hold_reasons)
            hold_reasons.append("Required legal documentation is missing.")
            return LegalPricingResult(
                currency=quote.currency,
                total_due_cents=quote.total_due_cents,
                agency_payout_cents=quote.agency_payout_cents,
                platform_fee_cents=quote.platform_fee_cents,
                margin_status=quote.margin_status,
                payment_required=quote.payment_required,
                workflow_state=LegalWorkflowState.MISSING_INFORMATION.value,
                delivery_mode=quote.delivery_mode,
                line_items=quote.line_items,
                costs=quote.costs,
                hold_reasons=hold_reasons,
            )
        return quote

    def _quote_to_payload(self, quote: LegalPricingResult) -> dict[str, object]:
        return {
            "currency": quote.currency,
            "total_due_cents": quote.total_due_cents,
            "agency_payout_cents": quote.agency_payout_cents,
            "platform_fee_cents": quote.platform_fee_cents,
            "margin_status": quote.margin_status,
            "payment_required": quote.payment_required,
            "workflow_state": quote.workflow_state,
            "delivery_mode": quote.delivery_mode,
            "line_items": quote.line_items,
            "costs": quote.costs,
            "hold_reasons": quote.hold_reasons,
        }

    def _financial_snapshot_from_quote(self, quote: LegalPricingResult) -> dict[str, object]:
        return {
            "margin_status": quote.margin_status,
            "costs": quote.costs,
            "platform_fee_cents": quote.platform_fee_cents,
            "agency_payout_cents": quote.agency_payout_cents,
            "total_due_cents": quote.total_due_cents,
        }

    def _quote_out(
        self,
        *,
        request_id: uuid.UUID,
        requester_category: str,
        quote: LegalPricingResult,
    ) -> LegalFeeQuoteOut:
        return LegalFeeQuoteOut(
            request_id=request_id,
            currency=quote.currency,
            total_due_cents=quote.total_due_cents,
            agency_payout_cents=quote.agency_payout_cents,
            platform_fee_cents=quote.platform_fee_cents,
            margin_status=quote.margin_status,
            payment_required=quote.payment_required,
            workflow_state=quote.workflow_state,
            requester_category=requester_category,
            delivery_mode=quote.delivery_mode,
            line_items=quote.line_items,
            costs=quote.costs,
            hold_reasons=quote.hold_reasons,
        )

    def _latest_payment_for_request(
        self,
        *,
        tenant_id: uuid.UUID,
        request_id: uuid.UUID,
    ) -> LegalRequestPayment | None:
        return self.db.execute(
            select(LegalRequestPayment)
            .where(
                LegalRequestPayment.tenant_id == tenant_id,
                LegalRequestPayment.legal_request_id == request_id,
            )
            .order_by(LegalRequestPayment.created_at.desc())
        ).scalar_one_or_none()

    def _payment_out(self, *, payment: LegalRequestPayment, request_id: uuid.UUID) -> LegalRequestPaymentOut:
        return LegalRequestPaymentOut(
            payment_id=payment.id,
            request_id=request_id,
            status=payment.status,
            amount_due_cents=payment.amount_due_cents,
            amount_collected_cents=payment.amount_collected_cents,
            platform_fee_cents=payment.platform_fee_cents,
            agency_payout_cents=payment.agency_payout_cents,
            currency=payment.currency,
            stripe_connected_account_id=payment.stripe_connected_account_id,
            stripe_checkout_session_id=payment.stripe_checkout_session_id,
            stripe_payment_intent_id=payment.stripe_payment_intent_id,
            check_reference=payment.check_reference,
            paid_at=payment.paid_at,
            failed_at=payment.failed_at,
            refunded_at=payment.refunded_at,
        )
