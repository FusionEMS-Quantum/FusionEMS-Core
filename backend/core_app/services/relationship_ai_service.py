"""Relationship AI Service — AI-powered relationship intelligence.

AI acts as an experienced relationship and account-history assistant.
AI may detect duplicates, summarize history, and prioritize issues.
AI may NOT silently merge, rewrite identity, or infer financial responsibility.
"""
# pylint: disable=not-callable  # SQLAlchemy func.count() is a known pylint false positive
from __future__ import annotations

import datetime
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
    RelationshipIssue,
    RelationshipIssueList,
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

    # ── ISSUE GENERATION ──────────────────────────────────────────────────

    async def generate_issues(
        self, *, tenant_id: str
    ) -> RelationshipIssueList:
        """Generate structured relationship issues per directive Part 9 format.

        AI rules enforced:
        - never invent identity facts
        - never auto-merge patients
        - never assume financial responsibility
        - never give false certainty
        - distinguish hard fact from model judgment
        """
        issues: list[RelationshipIssue] = []

        identity = await self._identity_confidence(tenant_id)
        resp_party = await self._responsible_party_completion(tenant_id)
        facility = await self._facility_health(tenant_id)
        comm = await self._communication_completeness(tenant_id)
        dup_count = await self._unresolved_duplicate_count(tenant_id)
        contact_gaps = await self._facility_contact_gap_count(tenant_id)
        freq_util = await self._frequent_utilizer_count(tenant_id)

        # ── Duplicate candidates ──────────────────────────────────
        if dup_count > 0:
            issues.append(RelationshipIssue(
                issue=f"{dup_count} unresolved duplicate patient candidates",
                severity="BLOCKING" if dup_count > 5 else "HIGH",
                source="RULE",
                what_is_wrong=(
                    f"There are {dup_count} patient records flagged as potential "
                    "duplicates that have not been reviewed."
                ),
                why_it_matters=(
                    "Duplicate records cause billing errors, split clinical "
                    "history, and compliance risk. Each unresolved duplicate "
                    "is a data integrity liability."
                ),
                what_you_should_do=(
                    "Open the Identity Manager, review each duplicate candidate, "
                    "and either confirm as true duplicate or mark as false positive."
                ),
                relationship_context=(
                    "Duplicate detection is rule-based on name, DOB, and external "
                    "identifiers. Human review is mandatory before any merge."
                ),
                human_review="REQUIRED",
                confidence="HIGH",
                category="IDENTITY",
            ))

        # ── Pending merge requests ────────────────────────────────
        if identity.merge_pending_count > 0:
            issues.append(RelationshipIssue(
                issue=f"{identity.merge_pending_count} patient merge requests pending review",
                severity="HIGH",
                source="RULE",
                what_is_wrong=(
                    f"{identity.merge_pending_count} merge requests are awaiting "
                    "approval. Patient records cannot be unified until reviewed."
                ),
                why_it_matters=(
                    "Pending merges block billing continuity for affected patients "
                    "and may cause duplicate claims."
                ),
                what_you_should_do=(
                    "Review each pending merge request in the Identity Manager. "
                    "Approve or reject based on matching criteria."
                ),
                relationship_context=(
                    "Merge requests are created from duplicate candidates. "
                    "No auto-merge is performed — human approval required."
                ),
                human_review="REQUIRED",
                confidence="HIGH",
                category="IDENTITY",
            ))

        # ── Disputed responsibility ───────────────────────────────
        if resp_party.disputed_count > 0:
            issues.append(RelationshipIssue(
                issue=f"{resp_party.disputed_count} disputed financial responsibility records",
                severity="HIGH",
                source="BILLING_EVENT",
                what_is_wrong=(
                    f"{resp_party.disputed_count} patient-responsible party links "
                    "are in DISPUTED state."
                ),
                why_it_matters=(
                    "Disputed responsibility blocks claim submission. The system "
                    "cannot bill a responsible party whose identity or relationship "
                    "is under dispute."
                ),
                what_you_should_do=(
                    "Review each disputed record, verify the responsible party's "
                    "identity and relationship, and resolve the dispute."
                ),
                relationship_context=(
                    "Financial responsibility is never auto-assigned. Disputes "
                    "must be resolved by billing staff or founder review."
                ),
                human_review="REQUIRED",
                confidence="HIGH",
                category="RESPONSIBILITY",
            ))

        # ── Unknown responsibility ────────────────────────────────
        if resp_party.unknown_responsibility > 0:
            issues.append(RelationshipIssue(
                issue=f"{resp_party.unknown_responsibility} patients with unknown financial responsibility",
                severity="MEDIUM",
                source="RULE",
                what_is_wrong=(
                    f"{resp_party.unknown_responsibility} patient links have "
                    "responsibility state set to UNKNOWN."
                ),
                why_it_matters=(
                    "Claims for these patients may be delayed because the "
                    "financially responsible party cannot be determined."
                ),
                what_you_should_do=(
                    "Identify the guarantor or subscriber for each patient "
                    "and update their responsibility state."
                ),
                relationship_context=(
                    "Responsibility starts as UNKNOWN by default. "
                    "It must be explicitly verified — the system never guesses."
                ),
                human_review="RECOMMENDED",
                confidence="MEDIUM",
                category="RESPONSIBILITY",
            ))

        # ── High-friction facilities ──────────────────────────────
        if facility.high_friction_count > 0:
            issues.append(RelationshipIssue(
                issue=f"{facility.high_friction_count} high-friction facility relationships",
                severity="HIGH",
                source="FACILITY_EVENT",
                what_is_wrong=(
                    f"{facility.high_friction_count} facilities are in "
                    "HIGH_FRICTION relationship state."
                ),
                why_it_matters=(
                    "High-friction facilities cause operational delays, "
                    "extended turnaround times, and crew frustration."
                ),
                what_you_should_do=(
                    "Review friction flags for each facility. Address "
                    "communication issues, billing disputes, or safety concerns."
                ),
                relationship_context=(
                    "Friction flags are created by staff and tracked with "
                    "category, resolution status, and audit trail."
                ),
                human_review="RECOMMENDED",
                confidence="HIGH",
                category="FACILITY",
            ))

        # ── Facility contact gaps ─────────────────────────────────
        if contact_gaps > 0:
            issues.append(RelationshipIssue(
                issue=f"{contact_gaps} facilities with no registered contacts",
                severity="MEDIUM",
                source="RULE",
                what_is_wrong=(
                    f"{contact_gaps} active facilities have zero intake or "
                    "operational contacts on file."
                ),
                why_it_matters=(
                    "Facilities without contacts cannot receive transport "
                    "notifications, billing inquiries, or handoff communications."
                ),
                what_you_should_do=(
                    "Add at least one intake coordinator or primary contact "
                    "for each facility."
                ),
                relationship_context=(
                    "Contacts are tracked per facility with role, "
                    "preferred contact method, and active status."
                ),
                human_review="RECOMMENDED",
                confidence="HIGH",
                category="FACILITY",
            ))

        # ── Communication preference gaps ─────────────────────────
        if comm.completeness_pct < 50:
            issues.append(RelationshipIssue(
                issue="Low patient communication preference coverage",
                severity="MEDIUM",
                source="RULE",
                what_is_wrong=(
                    f"Only {comm.completeness_pct}% of patients "
                    f"({comm.with_preferences}/{comm.total_patients}) have "
                    "contact preferences configured."
                ),
                why_it_matters=(
                    "Without explicit preferences, billing communications "
                    "default to system policy. This increases opt-out risk "
                    "and compliance exposure."
                ),
                what_you_should_do=(
                    "Capture contact preferences during intake. "
                    "SMS/call/email/mail preferences should be explicit."
                ),
                relationship_context=(
                    "Preferences are opt-in by default. Billing communications "
                    "must respect preference state before sending."
                ),
                human_review="SAFE_TO_AUTO_PROCESS",
                confidence="HIGH",
                category="COMMUNICATION",
            ))

        # ── Frequent utilizers ────────────────────────────────────
        if freq_util > 0:
            issues.append(RelationshipIssue(
                issue=f"{freq_util} active frequent utilizer alerts",
                severity="MEDIUM" if freq_util < 5 else "HIGH",
                source="PATIENT_EVENT",
                what_is_wrong=(
                    f"{freq_util} patients are flagged as frequent utilizers "
                    "with active warning flags."
                ),
                why_it_matters=(
                    "Frequent utilizers may need care coordination, "
                    "community paramedicine referrals, or proactive "
                    "relationship management."
                ),
                what_you_should_do=(
                    "Review each frequent utilizer flag. Consider outreach, "
                    "care plan coordination, or community resource referral."
                ),
                relationship_context=(
                    "Frequent utilizer flags are created based on trip "
                    "frequency thresholds. Flags are auditable and can be "
                    "resolved with notes."
                ),
                human_review="RECOMMENDED",
                confidence="MEDIUM",
                category="IDENTITY",
            ))

        # ── Facility review required ──────────────────────────────
        if facility.review_required_count > 0:
            issues.append(RelationshipIssue(
                issue=f"{facility.review_required_count} facilities need relationship review",
                severity="LOW",
                source="FACILITY_EVENT",
                what_is_wrong=(
                    f"{facility.review_required_count} facilities are in "
                    "REVIEW_REQUIRED state."
                ),
                why_it_matters=(
                    "Facilities flagged for review may have outdated contacts, "
                    "changed service capabilities, or relationship status changes."
                ),
                what_you_should_do=(
                    "Review each facility's profile, contacts, and service "
                    "notes. Update relationship state when satisfied."
                ),
                relationship_context=(
                    "Facility relationship states transition through "
                    "ACTIVE → LIMITED_RELATIONSHIP → HIGH_FRICTION → "
                    "REVIEW_REQUIRED → INACTIVE."
                ),
                human_review="RECOMMENDED",
                confidence="HIGH",
                category="FACILITY",
            ))

        # ── Nominal ───────────────────────────────────────────────
        if not issues:
            issues.append(RelationshipIssue(
                issue="All relationship systems nominal",
                severity="INFORMATIONAL",
                source="RULE",
                what_is_wrong="No relationship issues detected.",
                why_it_matters="System is operating within expected parameters.",
                what_you_should_do="No action required.",
                relationship_context="All metrics within healthy thresholds.",
                human_review="SAFE_TO_AUTO_PROCESS",
                confidence="HIGH",
                category="STATUS",
            ))

        return RelationshipIssueList(
            issues=issues,
            generated_at=datetime.datetime.now(datetime.UTC).isoformat(),
            tenant_id=tenant_id,
        )
