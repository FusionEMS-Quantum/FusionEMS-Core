"""Patient Identity Service — alias, identifier, duplicate, merge workflows.

All identity mutations are auditable. No silent merges. Duplicate detection
suggests but does not auto-resolve.
"""
from __future__ import annotations

import logging
import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from core_app.core.errors import AppError, ErrorCodes
from core_app.models.audit_log import AuditLog
from core_app.models.patient_identity import (
    DuplicateResolution,
    MergeRequestStatus,
    PatientAlias,
    PatientDuplicateCandidate,
    PatientIdentifier,
    PatientMergeAuditEvent,
    PatientMergeRequest,
    PatientRelationshipFlag,
)
from core_app.schemas.patient_identity import (
    DuplicateCandidateListResponse,
    DuplicateCandidateResponse,
    DuplicateResolutionUpdate,
    MergeRequestCreate,
    MergeRequestListResponse,
    MergeRequestResponse,
    MergeRequestReview,
    PatientAliasCreate,
    PatientAliasListResponse,
    PatientAliasResponse,
    PatientIdentifierCreate,
    PatientIdentifierListResponse,
    PatientIdentifierResponse,
    RelationshipFlagCreate,
    RelationshipFlagListResponse,
    RelationshipFlagResolve,
    RelationshipFlagResponse,
)

logger = logging.getLogger(__name__)


class PatientIdentityService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    # ── ALIASES ───────────────────────────────────────────────────────────

    async def create_alias(
        self,
        *,
        tenant_id: uuid.UUID,
        patient_id: uuid.UUID,
        actor_user_id: uuid.UUID,
        payload: PatientAliasCreate,
        correlation_id: str | None = None,
    ) -> PatientAliasResponse:
        alias = PatientAlias(
            tenant_id=tenant_id,
            patient_id=patient_id,
            alias_type=payload.alias_type,
            first_name=payload.first_name,
            middle_name=payload.middle_name,
            last_name=payload.last_name,
            effective_date=payload.effective_date,
            notes=payload.notes,
        )
        self.db.add(alias)
        await self._audit(
            tenant_id=tenant_id,
            actor_user_id=actor_user_id,
            action="patient_alias_created",
            entity_name="PatientAlias",
            entity_id=alias.id,
            correlation_id=correlation_id,
        )
        await self.db.commit()
        await self.db.refresh(alias)
        return PatientAliasResponse.model_validate(alias)

    async def list_aliases(
        self, *, tenant_id: uuid.UUID, patient_id: uuid.UUID
    ) -> PatientAliasListResponse:
        stmt = (
            select(PatientAlias)
            .where(
                PatientAlias.tenant_id == tenant_id,
                PatientAlias.patient_id == patient_id,
            )
            .order_by(PatientAlias.created_at.desc())
        )
        result = await self.db.execute(stmt)
        items = list(result.scalars().all())
        return PatientAliasListResponse(
            items=[PatientAliasResponse.model_validate(a) for a in items],
            total=len(items),
        )

    # ── IDENTIFIERS ───────────────────────────────────────────────────────

    async def create_identifier(
        self,
        *,
        tenant_id: uuid.UUID,
        patient_id: uuid.UUID,
        actor_user_id: uuid.UUID,
        payload: PatientIdentifierCreate,
        correlation_id: str | None = None,
    ) -> PatientIdentifierResponse:
        identifier = PatientIdentifier(
            tenant_id=tenant_id,
            patient_id=patient_id,
            source=payload.source,
            identifier_value=payload.identifier_value,
            issuing_authority=payload.issuing_authority,
            provenance=payload.provenance,
        )
        self.db.add(identifier)
        await self._audit(
            tenant_id=tenant_id,
            actor_user_id=actor_user_id,
            action="patient_identifier_created",
            entity_name="PatientIdentifier",
            entity_id=identifier.id,
            correlation_id=correlation_id,
        )
        await self.db.commit()
        await self.db.refresh(identifier)
        return PatientIdentifierResponse.model_validate(identifier)

    async def list_identifiers(
        self, *, tenant_id: uuid.UUID, patient_id: uuid.UUID
    ) -> PatientIdentifierListResponse:
        stmt = (
            select(PatientIdentifier)
            .where(
                PatientIdentifier.tenant_id == tenant_id,
                PatientIdentifier.patient_id == patient_id,
            )
            .order_by(PatientIdentifier.created_at.desc())
        )
        result = await self.db.execute(stmt)
        items = list(result.scalars().all())
        return PatientIdentifierListResponse(
            items=[
                PatientIdentifierResponse.model_validate(i) for i in items
            ],
            total=len(items),
        )

    # ── DUPLICATE CANDIDATES ──────────────────────────────────────────────

    async def list_duplicate_candidates(
        self, *, tenant_id: uuid.UUID
    ) -> DuplicateCandidateListResponse:
        stmt = (
            select(PatientDuplicateCandidate)
            .where(
                PatientDuplicateCandidate.tenant_id == tenant_id,
                PatientDuplicateCandidate.resolution
                == DuplicateResolution.UNRESOLVED,
            )
            .order_by(
                PatientDuplicateCandidate.confidence_score.desc()
            )
        )
        result = await self.db.execute(stmt)
        items = list(result.scalars().all())
        return DuplicateCandidateListResponse(
            items=[
                DuplicateCandidateResponse.model_validate(d) for d in items
            ],
            total=len(items),
        )

    async def resolve_duplicate(
        self,
        *,
        tenant_id: uuid.UUID,
        candidate_id: uuid.UUID,
        actor_user_id: uuid.UUID,
        payload: DuplicateResolutionUpdate,
        correlation_id: str | None = None,
    ) -> DuplicateCandidateResponse:
        stmt = select(PatientDuplicateCandidate).where(
            PatientDuplicateCandidate.id == candidate_id,
            PatientDuplicateCandidate.tenant_id == tenant_id,
        )
        result = await self.db.execute(stmt)
        candidate = result.scalar_one_or_none()
        if not candidate:
            raise AppError(
                code=ErrorCodes.NOT_FOUND,
                message="Duplicate candidate not found",
            )
        candidate.resolution = payload.resolution
        candidate.resolved_by_user_id = actor_user_id
        candidate.notes = payload.notes
        await self._audit(
            tenant_id=tenant_id,
            actor_user_id=actor_user_id,
            action="duplicate_resolved",
            entity_name="PatientDuplicateCandidate",
            entity_id=candidate_id,
            correlation_id=correlation_id,
        )
        await self.db.commit()
        await self.db.refresh(candidate)
        return DuplicateCandidateResponse.model_validate(candidate)

    # ── MERGE REQUESTS ────────────────────────────────────────────────────

    async def create_merge_request(
        self,
        *,
        tenant_id: uuid.UUID,
        actor_user_id: uuid.UUID,
        payload: MergeRequestCreate,
        correlation_id: str | None = None,
    ) -> MergeRequestResponse:
        if payload.source_patient_id == payload.target_patient_id:
            raise AppError(
                code=ErrorCodes.VALIDATION_ERROR,
                message="Source and target patients must differ",
            )
        merge_req = PatientMergeRequest(
            tenant_id=tenant_id,
            source_patient_id=payload.source_patient_id,
            target_patient_id=payload.target_patient_id,
            requested_by_user_id=actor_user_id,
            merge_reason=payload.merge_reason,
            field_resolution_map=payload.field_resolution_map,
        )
        self.db.add(merge_req)
        audit_event = PatientMergeAuditEvent(
            tenant_id=tenant_id,
            merge_request_id=merge_req.id,
            action="requested",
            actor_user_id=actor_user_id,
            detail={"reason": payload.merge_reason},
            correlation_id=correlation_id,
        )
        self.db.add(audit_event)
        await self.db.commit()
        await self.db.refresh(merge_req)
        return MergeRequestResponse.model_validate(merge_req)

    async def list_merge_requests(
        self, *, tenant_id: uuid.UUID
    ) -> MergeRequestListResponse:
        stmt = (
            select(PatientMergeRequest)
            .where(PatientMergeRequest.tenant_id == tenant_id)
            .order_by(PatientMergeRequest.created_at.desc())
        )
        result = await self.db.execute(stmt)
        items = list(result.scalars().all())
        return MergeRequestListResponse(
            items=[
                MergeRequestResponse.model_validate(m) for m in items
            ],
            total=len(items),
        )

    async def review_merge_request(
        self,
        *,
        tenant_id: uuid.UUID,
        merge_request_id: uuid.UUID,
        actor_user_id: uuid.UUID,
        payload: MergeRequestReview,
        correlation_id: str | None = None,
    ) -> MergeRequestResponse:
        stmt = select(PatientMergeRequest).where(
            PatientMergeRequest.id == merge_request_id,
            PatientMergeRequest.tenant_id == tenant_id,
        )
        result = await self.db.execute(stmt)
        merge_req = result.scalar_one_or_none()
        if not merge_req:
            raise AppError(
                code=ErrorCodes.NOT_FOUND,
                message="Merge request not found",
            )
        if merge_req.status != MergeRequestStatus.PENDING_REVIEW:
            raise AppError(
                code=ErrorCodes.VALIDATION_ERROR,
                message="Merge request is not in PENDING_REVIEW state",
            )
        new_status = (
            MergeRequestStatus.APPROVED
            if payload.action == "approve"
            else MergeRequestStatus.REJECTED
        )
        merge_req.status = new_status
        merge_req.reviewed_by_user_id = actor_user_id
        merge_req.review_notes = payload.review_notes
        audit_event = PatientMergeAuditEvent(
            tenant_id=tenant_id,
            merge_request_id=merge_request_id,
            action=payload.action + "d",  # approved / rejected
            actor_user_id=actor_user_id,
            detail={"review_notes": payload.review_notes},
            correlation_id=correlation_id,
        )
        self.db.add(audit_event)
        await self.db.commit()
        await self.db.refresh(merge_req)
        return MergeRequestResponse.model_validate(merge_req)

    # ── RELATIONSHIP FLAGS ────────────────────────────────────────────────

    async def create_flag(
        self,
        *,
        tenant_id: uuid.UUID,
        patient_id: uuid.UUID,
        actor_user_id: uuid.UUID,
        payload: RelationshipFlagCreate,
        correlation_id: str | None = None,
    ) -> RelationshipFlagResponse:
        flag = PatientRelationshipFlag(
            tenant_id=tenant_id,
            patient_id=patient_id,
            flag_type=payload.flag_type,
            severity=payload.severity,
            title=payload.title,
            description=payload.description,
            created_by_user_id=actor_user_id,
        )
        self.db.add(flag)
        await self._audit(
            tenant_id=tenant_id,
            actor_user_id=actor_user_id,
            action="relationship_flag_created",
            entity_name="PatientRelationshipFlag",
            entity_id=flag.id,
            correlation_id=correlation_id,
        )
        await self.db.commit()
        await self.db.refresh(flag)
        return RelationshipFlagResponse.model_validate(flag)

    async def list_flags(
        self, *, tenant_id: uuid.UUID, patient_id: uuid.UUID
    ) -> RelationshipFlagListResponse:
        stmt = (
            select(PatientRelationshipFlag)
            .where(
                PatientRelationshipFlag.tenant_id == tenant_id,
                PatientRelationshipFlag.patient_id == patient_id,
            )
            .order_by(PatientRelationshipFlag.created_at.desc())
        )
        result = await self.db.execute(stmt)
        items = list(result.scalars().all())
        return RelationshipFlagListResponse(
            items=[
                RelationshipFlagResponse.model_validate(f) for f in items
            ],
            total=len(items),
        )

    async def resolve_flag(
        self,
        *,
        tenant_id: uuid.UUID,
        flag_id: uuid.UUID,
        actor_user_id: uuid.UUID,
        payload: RelationshipFlagResolve,
        correlation_id: str | None = None,
    ) -> RelationshipFlagResponse:
        stmt = select(PatientRelationshipFlag).where(
            PatientRelationshipFlag.id == flag_id,
            PatientRelationshipFlag.tenant_id == tenant_id,
        )
        result = await self.db.execute(stmt)
        flag = result.scalar_one_or_none()
        if not flag:
            raise AppError(
                code=ErrorCodes.NOT_FOUND,
                message="Relationship flag not found",
            )
        flag.is_active = False
        flag.resolved_by_user_id = actor_user_id
        flag.resolution_notes = payload.resolution_notes
        await self._audit(
            tenant_id=tenant_id,
            actor_user_id=actor_user_id,
            action="relationship_flag_resolved",
            entity_name="PatientRelationshipFlag",
            entity_id=flag_id,
            correlation_id=correlation_id,
        )
        await self.db.commit()
        await self.db.refresh(flag)
        return RelationshipFlagResponse.model_validate(flag)

    # ── AUDIT ─────────────────────────────────────────────────────────────

    async def _audit(
        self,
        *,
        tenant_id: uuid.UUID,
        actor_user_id: uuid.UUID,
        action: str,
        entity_name: str,
        entity_id: uuid.UUID,
        correlation_id: str | None = None,
    ) -> None:
        log = AuditLog(
            tenant_id=tenant_id,
            actor_user_id=actor_user_id,
            action=action,
            entity_name=entity_name,
            entity_id=entity_id,
            correlation_id=correlation_id,
        )
        self.db.add(log)
