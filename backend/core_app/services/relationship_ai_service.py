"""Relationship AI Service — AI-powered relationship intelligence.

AI acts as an experienced relationship and account-history assistant.
AI may detect duplicates, summarize history, and prioritize issues.
AI may NOT silently merge, rewrite identity, or infer financial responsibility.
"""
from __future__ import annotations

import logging

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from core_app.models.contact_preference import ContactPreference
from core_app.models.facility import (
    Facility,
    FacilityContact,
)
from core_app.models.patient_identity import (
    DuplicateResolution,
    PatientDuplicateCandidate,
    PatientMergeRequest,
)
from core_app.models.relationship_history import (
    PatientWarningFlag,
)
from core_app.models.responsible_party import (
    PatientResponsiblePartyLink,
    ResponsibilityState,
)
from core_app.schemas.relationship_command import (
    CommunicationPreferenceCompleteness,
    FacilityRelationshipHealth,
    IdentityConfidenceScore,
    RelationshipAction,
    RelationshipCommandSummary,
    ResponsiblePartyCompletion,
)

logger = logging.getLogger(__name__)

RELATIONSHIP_SYSTEM_PROMPT = """You are FusionEMS Relationship AI — an experienced
relationship and account-history assistant helping a paramedic founder.
For every issue, answer: what is wrong, why it matters, what to do next,
how serious it is, whether human review is needed, and the source.
Never invent identity facts. Never auto-merge patients. Never assume
financial responsibility. Never give false certainty. Distinguish hard
fact from model judgment. Return ONLY valid JSON."""


class RelationshipAIService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def build_command_summary(
        self, *, tenant_id: str
    ) -> RelationshipCommandSummary:
        """Build the founder relationship command center summary."""
        identity = await self._identity_confidence(tenant_id)
        resp_party = await self._responsible_party_completion(tenant_id)
        facility = await self._facility_health(tenant_id)
        comm = await self._communication_completeness(tenant_id)
        dup_count = await self._unresolved_duplicate_count(tenant_id)
        contact_gaps = await self._facility_contact_gap_count(tenant_id)
        freq_util = await self._frequent_utilizer_count(tenant_id)
        actions = self._compute_top_actions(
            identity=identity,
            resp_party=resp_party,
            facility=facility,
            comm=comm,
            dup_count=dup_count,
            contact_gaps=contact_gaps,
        )

        return RelationshipCommandSummary(
            identity_confidence=identity,
            responsible_party_completion=resp_party,
            facility_health=facility,
            communication_completeness=comm,
            duplicate_review_count=dup_count,
            facility_contact_gaps=contact_gaps,
            frequent_utilizer_count=freq_util,
            top_actions=actions[:3],
        )

    # ── METRICS ───────────────────────────────────────────────────────────

    async def _identity_confidence(
        self, tenant_id: str
    ) -> IdentityConfidenceScore:
        from core_app.models.patient import Patient

        total_q = select(func.count()).select_from(Patient).where(
            Patient.tenant_id == tenant_id
        )
        total = (await self.db.execute(total_q)).scalar() or 0

        dup_q = (
            select(func.count())
            .select_from(PatientDuplicateCandidate)
            .where(
                PatientDuplicateCandidate.tenant_id == tenant_id,
                PatientDuplicateCandidate.resolution
                == DuplicateResolution.UNRESOLVED,
            )
        )
        dup_count = (await self.db.execute(dup_q)).scalar() or 0

        merge_q = (
            select(func.count())
            .select_from(PatientMergeRequest)
            .where(
                PatientMergeRequest.tenant_id == tenant_id,
                PatientMergeRequest.status == "PENDING_REVIEW",
            )
        )
        merge_count = (await self.db.execute(merge_q)).scalar() or 0

        verified = max(0, total - dup_count - merge_count)
        pct = (verified / total * 100) if total > 0 else 0.0

        return IdentityConfidenceScore(
            total_patients=total,
            verified_count=verified,
            incomplete_count=0,
            duplicate_candidate_count=dup_count,
            merge_pending_count=merge_count,
            confidence_pct=round(pct, 1),
        )

    async def _responsible_party_completion(
        self, tenant_id: str
    ) -> ResponsiblePartyCompletion:
        from core_app.models.patient import Patient

        total_q = select(func.count()).select_from(Patient).where(
            Patient.tenant_id == tenant_id
        )
        total = (await self.db.execute(total_q)).scalar() or 0

        with_rp_q = (
            select(
                func.count(
                    func.distinct(PatientResponsiblePartyLink.patient_id)
                )
            )
            .select_from(PatientResponsiblePartyLink)
            .where(
                PatientResponsiblePartyLink.tenant_id == tenant_id,
            )
        )
        with_rp = (await self.db.execute(with_rp_q)).scalar() or 0

        unknown_q = (
            select(func.count())
            .select_from(PatientResponsiblePartyLink)
            .where(
                PatientResponsiblePartyLink.tenant_id == tenant_id,
                PatientResponsiblePartyLink.responsibility_state
                == ResponsibilityState.UNKNOWN,
            )
        )
        unknown = (await self.db.execute(unknown_q)).scalar() or 0

        disputed_q = (
            select(func.count())
            .select_from(PatientResponsiblePartyLink)
            .where(
                PatientResponsiblePartyLink.tenant_id == tenant_id,
                PatientResponsiblePartyLink.responsibility_state
                == ResponsibilityState.DISPUTED,
            )
        )
        disputed = (await self.db.execute(disputed_q)).scalar() or 0

        pct = (with_rp / total * 100) if total > 0 else 0.0
        return ResponsiblePartyCompletion(
            total_patients=total,
            with_responsible_party=with_rp,
            unknown_responsibility=unknown,
            disputed_count=disputed,
            completion_pct=round(pct, 1),
        )

    async def _facility_health(
        self, tenant_id: str
    ) -> FacilityRelationshipHealth:
        total_q = select(func.count()).select_from(Facility).where(
            Facility.tenant_id == tenant_id,
            Facility.deleted_at.is_(None),
        )
        total = (await self.db.execute(total_q)).scalar() or 0

        active_q = select(func.count()).select_from(Facility).where(
            Facility.tenant_id == tenant_id,
            Facility.deleted_at.is_(None),
            Facility.relationship_state == "ACTIVE",
        )
        active = (await self.db.execute(active_q)).scalar() or 0

        friction_q = select(func.count()).select_from(Facility).where(
            Facility.tenant_id == tenant_id,
            Facility.deleted_at.is_(None),
            Facility.relationship_state == "HIGH_FRICTION",
        )
        friction = (await self.db.execute(friction_q)).scalar() or 0

        review_q = select(func.count()).select_from(Facility).where(
            Facility.tenant_id == tenant_id,
            Facility.deleted_at.is_(None),
            Facility.relationship_state == "REVIEW_REQUIRED",
        )
        review = (await self.db.execute(review_q)).scalar() or 0

        inactive_q = select(func.count()).select_from(Facility).where(
            Facility.tenant_id == tenant_id,
            Facility.deleted_at.is_(None),
            Facility.relationship_state == "INACTIVE",
        )
        inactive = (await self.db.execute(inactive_q)).scalar() or 0

        pct = (active / total * 100) if total > 0 else 100.0
        return FacilityRelationshipHealth(
            total_facilities=total,
            active_count=active,
            high_friction_count=friction,
            review_required_count=review,
            inactive_count=inactive,
            health_pct=round(pct, 1),
        )

    async def _communication_completeness(
        self, tenant_id: str
    ) -> CommunicationPreferenceCompleteness:
        from core_app.models.patient import Patient

        total_q = select(func.count()).select_from(Patient).where(
            Patient.tenant_id == tenant_id
        )
        total = (await self.db.execute(total_q)).scalar() or 0

        with_pref_q = (
            select(
                func.count(
                    func.distinct(ContactPreference.patient_id)
                )
            )
            .select_from(ContactPreference)
            .where(ContactPreference.tenant_id == tenant_id)
        )
        with_pref = (await self.db.execute(with_pref_q)).scalar() or 0

        pct = (with_pref / total * 100) if total > 0 else 0.0
        return CommunicationPreferenceCompleteness(
            total_patients=total,
            with_preferences=with_pref,
            completeness_pct=round(pct, 1),
        )

    async def _unresolved_duplicate_count(
        self, tenant_id: str
    ) -> int:
        q = (
            select(func.count())
            .select_from(PatientDuplicateCandidate)
            .where(
                PatientDuplicateCandidate.tenant_id == tenant_id,
                PatientDuplicateCandidate.resolution
                == DuplicateResolution.UNRESOLVED,
            )
        )
        return (await self.db.execute(q)).scalar() or 0

    async def _facility_contact_gap_count(
        self, tenant_id: str
    ) -> int:
        # Facilities with zero contacts
        facilities_q = select(Facility.id).where(
            Facility.tenant_id == tenant_id,
            Facility.deleted_at.is_(None),
        )
        all_ids_result = await self.db.execute(facilities_q)
        all_ids = {row[0] for row in all_ids_result.fetchall()}

        contacts_q = (
            select(func.distinct(FacilityContact.facility_id))
            .where(FacilityContact.tenant_id == tenant_id)
        )
        with_contacts_result = await self.db.execute(contacts_q)
        with_contacts = {
            row[0] for row in with_contacts_result.fetchall()
        }

        return len(all_ids - with_contacts)

    async def _frequent_utilizer_count(
        self, tenant_id: str
    ) -> int:
        q = (
            select(func.count())
            .select_from(PatientWarningFlag)
            .where(
                PatientWarningFlag.tenant_id == tenant_id,
                PatientWarningFlag.flag_type == "frequent_utilizer",
                PatientWarningFlag.is_active.is_(True),
            )
        )
        return (await self.db.execute(q)).scalar() or 0

    # ── TOP ACTIONS ───────────────────────────────────────────────────────

    def _compute_top_actions(
        self,
        *,
        identity: IdentityConfidenceScore,
        resp_party: ResponsiblePartyCompletion,
        facility: FacilityRelationshipHealth,
        comm: CommunicationPreferenceCompleteness,
        dup_count: int,
        contact_gaps: int,
    ) -> list[RelationshipAction]:
        actions: list[RelationshipAction] = []
        priority = 1

        if dup_count > 0:
            actions.append(RelationshipAction(
                priority=priority,
                category="IDENTITY",
                title=f"Review {dup_count} duplicate candidates",
                description=(
                    "Unresolved duplicate patients need human review"
                ),
                severity="BLOCKING" if dup_count > 5 else "HIGH",
                action_url="/founder/relationships",
            ))
            priority += 1

        if resp_party.disputed_count > 0:
            actions.append(RelationshipAction(
                priority=priority,
                category="RESPONSIBILITY",
                title=(
                    f"{resp_party.disputed_count} disputed"
                    " responsibility records"
                ),
                description=(
                    "Financial responsibility disputes"
                    " require resolution"
                ),
                severity="HIGH",
                action_url="/founder/relationships",
            ))
            priority += 1

        if facility.high_friction_count > 0:
            actions.append(RelationshipAction(
                priority=priority,
                category="FACILITY",
                title=(
                    f"{facility.high_friction_count}"
                    " high-friction facilities"
                ),
                description=(
                    "High-friction facilities degrade operations"
                ),
                severity="HIGH",
                action_url="/founder/relationships",
            ))
            priority += 1

        if contact_gaps > 0:
            actions.append(RelationshipAction(
                priority=priority,
                category="FACILITY",
                title=(
                    f"{contact_gaps} facilities missing contacts"
                ),
                description=(
                    "Facilities without contacts"
                    " have communication gaps"
                ),
                severity="MEDIUM",
                action_url="/founder/relationships",
            ))
            priority += 1

        if comm.completeness_pct < 50:
            actions.append(RelationshipAction(
                priority=priority,
                category="COMMUNICATION",
                title="Low communication preference coverage",
                description=(
                    f"Only {comm.completeness_pct}% of patients"
                    " have contact preferences set"
                ),
                severity="MEDIUM",
                action_url="/founder/relationships",
            ))
            priority += 1

        if identity.merge_pending_count > 0:
            actions.append(RelationshipAction(
                priority=priority,
                category="IDENTITY",
                title=(
                    f"{identity.merge_pending_count}"
                    " pending merge requests"
                ),
                description="Patient merge requests await review",
                severity="MEDIUM",
                action_url="/founder/relationships",
            ))
            priority += 1

        if not actions:
            actions.append(RelationshipAction(
                priority=1,
                category="STATUS",
                title="All relationship systems nominal",
                description=(
                    "No critical relationship issues detected"
                ),
                severity="GREEN",
            ))

        return actions
