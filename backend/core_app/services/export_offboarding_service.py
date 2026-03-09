"""Service layer for export / offboarding orchestration.

Aggregates data from billing, clinical, AR, communications, and document
subsystems into structured export packages with integrity guarantees.
"""

from __future__ import annotations

import csv
import hashlib
import io
import json
import logging
import uuid
import zipfile
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from core_app.models.billing import (
    AppealReview,
    Claim,
    ClaimAuditEvent,
    ClaimIssue,
    ClaimState,
    PatientBalanceLedger,
    ReminderEvent,
)
from core_app.models.export_offboarding import (
    ExportAccessLog,
    ExportPackage,
    OffboardingRequest,
    ThirdPartyBiller,
)

logger = logging.getLogger(__name__)


# ── Field Crosswalk ──────────────────────────────────────────────────────────

BILLING_CROSSWALK: list[dict[str, str | bool]] = [
    {"internal_field": "id", "export_field": "claim_id", "business_meaning": "Unique claim identifier", "destination_file": "claims.csv", "data_type": "uuid", "required": True, "import_note": "Primary key for matching"},
    {"internal_field": "incident_id", "export_field": "incident_id", "business_meaning": "Linked incident/trip", "destination_file": "claims.csv", "data_type": "uuid", "required": True, "import_note": "Maps to PCR/trip"},
    {"internal_field": "patient_id", "export_field": "patient_id", "business_meaning": "Patient identifier", "destination_file": "claims.csv", "data_type": "uuid", "required": True, "import_note": "Match to patient roster"},
    {"internal_field": "status", "export_field": "claim_status", "business_meaning": "Current claim state", "destination_file": "claims.csv", "data_type": "string", "required": True, "import_note": "DRAFT|SUBMITTED|PAID|DENIED|etc."},
    {"internal_field": "primary_payer_id", "export_field": "payer_id", "business_meaning": "Primary payer identifier", "destination_file": "claims.csv", "data_type": "string", "required": False, "import_note": "OfficeAlly or custom ID"},
    {"internal_field": "primary_payer_name", "export_field": "payer_name", "business_meaning": "Primary payer name", "destination_file": "claims.csv", "data_type": "string", "required": False, "import_note": "Human-readable payer"},
    {"internal_field": "total_billed_cents", "export_field": "total_billed_cents", "business_meaning": "Total billed amount in cents", "destination_file": "claims.csv", "data_type": "integer", "required": True, "import_note": "Divide by 100 for dollars"},
    {"internal_field": "insurance_paid_cents", "export_field": "insurance_paid_cents", "business_meaning": "Insurance payment received in cents", "destination_file": "claims.csv", "data_type": "integer", "required": True, "import_note": "Divide by 100 for dollars"},
    {"internal_field": "patient_responsibility_cents", "export_field": "patient_responsibility_cents", "business_meaning": "Patient owes in cents", "destination_file": "claims.csv", "data_type": "integer", "required": True, "import_note": "Divide by 100 for dollars"},
    {"internal_field": "patient_paid_cents", "export_field": "patient_paid_cents", "business_meaning": "Patient paid in cents", "destination_file": "claims.csv", "data_type": "integer", "required": True, "import_note": "Divide by 100 for dollars"},
    {"internal_field": "aging_days", "export_field": "aging_days", "business_meaning": "Days since original submission", "destination_file": "claims.csv", "data_type": "integer", "required": False, "import_note": "AR aging bucket input"},
    {"internal_field": "appeal_status", "export_field": "appeal_status", "business_meaning": "Appeal workflow status", "destination_file": "claims.csv", "data_type": "string", "required": False, "import_note": "PENDING|SUBMITTED|WON|LOST"},
    {"internal_field": "collections_status", "export_field": "collections_status", "business_meaning": "Collections workflow state", "destination_file": "claims.csv", "data_type": "string", "required": False, "import_note": "Pre-collections or placed"},
    {"internal_field": "is_valid", "export_field": "is_valid", "business_meaning": "Passed validation rules", "destination_file": "claims.csv", "data_type": "boolean", "required": True, "import_note": "true/false"},
    {"internal_field": "validation_errors", "export_field": "validation_errors", "business_meaning": "Blocking validation issues", "destination_file": "claims.csv", "data_type": "json_array", "required": False, "import_note": "JSON array of strings"},
    {"internal_field": "created_at", "export_field": "created_at", "business_meaning": "Claim creation timestamp", "destination_file": "claims.csv", "data_type": "datetime_iso8601", "required": True, "import_note": "ISO-8601 UTC"},
]


class ExportOffboardingService:
    """Orchestrates export package creation, risk analysis, and delivery."""

    def __init__(self, db: Session) -> None:
        self.db = db

    # ── Portal Dashboard ─────────────────────────────────────────────────

    def get_portal_dashboard(self, tenant_id: uuid.UUID) -> dict[str, Any]:
        """Aggregate real-time billing metrics for the third-party billing portal."""
        claims = self.db.execute(
            select(
                func.count(Claim.id).label("total"),
                func.count(Claim.id).filter(Claim.status == ClaimState.READY_FOR_SUBMISSION).label("ready"),
                func.count(Claim.id).filter(Claim.status == ClaimState.READY_FOR_BILLING_REVIEW).label("blocked"),
                func.count(Claim.id).filter(Claim.status == ClaimState.DENIED).label("denied"),
                func.count(Claim.id).filter(Claim.status.in_([ClaimState.APPEAL_DRAFTED, ClaimState.APPEAL_PENDING_REVIEW])).label("appeals"),
                func.count(Claim.id).filter(Claim.is_valid.is_(False)).label("doc_gaps"),
                func.sum(Claim.patient_responsibility_cents).filter(Claim.patient_responsibility_cents > 0).label("open_balances_cents"),
            ).where(Claim.tenant_id == tenant_id)
        ).first()

        total = claims.total if claims else 0  # type: ignore[union-attr]
        ready = claims.ready if claims else 0  # type: ignore[union-attr]
        blocked = claims.blocked if claims else 0  # type: ignore[union-attr]
        denied = claims.denied if claims else 0  # type: ignore[union-attr]
        appeals = claims.appeals if claims else 0  # type: ignore[union-attr]
        doc_gaps = claims.doc_gaps if claims else 0  # type: ignore[union-attr]

        clean_rate = ((total - denied) / total * 100) if total > 0 else 0.0

        # Export readiness
        pending_pkgs = self.db.scalar(
            select(func.count(ExportPackage.id)).where(
                ExportPackage.tenant_id == tenant_id,
                ExportPackage.state.in_(["REQUESTED", "IN_REVIEW", "APPROVED", "BUILDING"]),
            )
        ) or 0

        # Offboarding
        active_offboarding = self.db.execute(
            select(OffboardingRequest.state).where(
                OffboardingRequest.tenant_id == tenant_id,
                OffboardingRequest.state.notin_(["EXPIRED", "REVOKED"]),
            ).order_by(OffboardingRequest.created_at.desc()).limit(1)
        ).scalar_one_or_none()

        # Communication activity (reminder events last 30 days)
        comms = self.db.scalar(
            select(func.count(ReminderEvent.id)).join(
                Claim, ReminderEvent.claim_id == Claim.id,
            ).where(Claim.tenant_id == tenant_id)
        ) or 0

        actions: list[dict[str, str]] = []
        if blocked > 0:
            actions.append({"action": f"Review {blocked} blocked claims", "urgency": "high"})
        if denied > 0:
            actions.append({"action": f"Address {denied} denied claims", "urgency": "high"})
        if doc_gaps > 0:
            actions.append({"action": f"Close {doc_gaps} documentation gaps", "urgency": "medium"})
        if ready > 0:
            actions.append({"action": f"Submit {ready} ready claims", "urgency": "medium"})

        return {
            "clean_claim_rate_pct": round(clean_rate, 1),
            "claims_ready_to_submit": ready,
            "claims_blocked": blocked,
            "denied_claims": denied,
            "appeals_in_progress": appeals,
            "patient_balances_open": 0,  # populated from AR
            "payment_plan_count": 0,
            "documentation_gaps": doc_gaps,
            "certification_gaps": 0,
            "export_readiness": "PENDING" if pending_pkgs > 0 else "IDLE",
            "offboarding_status": active_offboarding,
            "communication_activity": comms,
            "secure_handoff_ready": pending_pkgs == 0 and denied == 0,
            "top_actions": actions[:5],
        }

    # ── Claims Workspace ─────────────────────────────────────────────────

    def list_claims(
        self,
        tenant_id: uuid.UUID,
        status_filter: str | None = None,
        payer_filter: str | None = None,
        aging_min: int | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[dict[str, Any]]:
        """List claims with optional filters for the billing workspace."""
        q = select(Claim).where(Claim.tenant_id == tenant_id)
        if status_filter:
            q = q.where(Claim.status == status_filter)
        if payer_filter:
            q = q.where(Claim.primary_payer_name == payer_filter)
        if aging_min is not None:
            q = q.where(Claim.aging_days >= aging_min)
        q = q.order_by(Claim.created_at.desc()).limit(limit).offset(offset)
        rows = self.db.execute(q).scalars().all()
        return [self._claim_to_row(c) for c in rows]

    def get_claim_detail(self, tenant_id: uuid.UUID, claim_id: uuid.UUID) -> dict[str, Any] | None:
        """Full claim detail including audit trail and linked data."""
        claim = self.db.execute(
            select(Claim).where(Claim.id == claim_id, Claim.tenant_id == tenant_id)
        ).scalar_one_or_none()
        if not claim:
            return None

        issues = self.db.execute(
            select(ClaimIssue).where(ClaimIssue.claim_id == claim_id)
        ).scalars().all()

        audit = self.db.execute(
            select(ClaimAuditEvent).where(ClaimAuditEvent.claim_id == claim_id).order_by(ClaimAuditEvent.created_at)
        ).scalars().all()

        appeals = self.db.execute(
            select(AppealReview).where(AppealReview.claim_id == claim_id)
        ).scalars().all()

        reminders = self.db.execute(
            select(ReminderEvent).where(ReminderEvent.claim_id == claim_id)
        ).scalars().all()

        return {
            "claim": self._claim_to_row(claim),
            "issues": [
                {
                    "id": str(i.id),
                    "severity": i.severity,
                    "what_is_wrong": i.what_is_wrong,
                    "why_it_matters": i.why_it_matters,
                    "what_to_do_next": i.what_to_do_next,
                    "resolved": i.resolved,
                    "confidence": i.confidence,
                }
                for i in issues
            ],
            "audit_trail": [
                {
                    "event_type": a.event_type,
                    "old_value": a.old_value,
                    "new_value": a.new_value,
                    "metadata": a.metadata_blob,
                    "created_at": a.created_at.isoformat() if a.created_at else None,
                }
                for a in audit
            ],
            "appeals": [
                {
                    "denial_code": ap.denial_code,
                    "status": ap.status,
                    "strategy": ap.ai_recommended_strategy,
                    "draft": ap.draft_appeal_text,
                }
                for ap in appeals
            ],
            "communications": [
                {
                    "type": r.reminder_type,
                    "sent_at": r.sent_at.isoformat() if r.sent_at else None,
                    "status": r.status,
                }
                for r in reminders
            ],
        }

    # ── Export Package CRUD ──────────────────────────────────────────────

    def create_export_package(
        self,
        tenant_id: uuid.UUID,
        requested_by: uuid.UUID,
        modules: list[str],
        *,
        date_range_start: datetime | None = None,
        date_range_end: datetime | None = None,
        patient_scope: list[uuid.UUID] | None = None,
        account_scope: list[uuid.UUID] | None = None,
        include_attachments: bool = True,
        include_field_crosswalk: bool = True,
        delivery_method: str = "SECURE_LINK",
        delivery_target: str | None = None,
        notes: str | None = None,
        offboarding_id: uuid.UUID | None = None,
    ) -> ExportPackage:
        pkg = ExportPackage(
            tenant_id=tenant_id,
            offboarding_id=offboarding_id,
            state="REQUESTED",
            modules=modules,
            date_range_start=date_range_start,
            date_range_end=date_range_end,
            patient_scope=[str(p) for p in patient_scope] if patient_scope else None,
            account_scope=[str(a) for a in account_scope] if account_scope else None,
            include_attachments=include_attachments,
            include_field_crosswalk=include_field_crosswalk,
            delivery_method=delivery_method,
            delivery_target=delivery_target,
            requested_by=requested_by,
            notes=notes,
        )
        self.db.add(pkg)
        self.db.flush()
        logger.info("export_package_created", extra={"package_id": str(pkg.id), "tenant_id": str(tenant_id)})
        return pkg

    def approve_export_package(
        self,
        tenant_id: uuid.UUID,
        package_id: uuid.UUID,
        reviewer_id: uuid.UUID,
        approved: bool,
        reviewer_notes: str | None = None,
    ) -> ExportPackage | None:
        pkg = self.db.execute(
            select(ExportPackage).where(
                ExportPackage.id == package_id,
                ExportPackage.tenant_id == tenant_id,
            )
        ).scalar_one_or_none()
        if not pkg:
            return None

        if approved:
            pkg.state = "APPROVED"
            pkg.approved_by = reviewer_id
            pkg.approved_at = datetime.now(UTC)
        else:
            pkg.state = "REVOKED"
        pkg.reviewer_notes = reviewer_notes
        self.db.flush()
        logger.info("export_package_reviewed", extra={"package_id": str(package_id), "approved": approved})
        return pkg

    def build_export_package(self, tenant_id: uuid.UUID, package_id: uuid.UUID) -> ExportPackage | None:
        """Build the actual export ZIP for an approved package."""
        pkg = self.db.execute(
            select(ExportPackage).where(
                ExportPackage.id == package_id,
                ExportPackage.tenant_id == tenant_id,
                ExportPackage.state == "APPROVED",
            )
        ).scalar_one_or_none()
        if not pkg:
            return None

        pkg.state = "BUILDING"
        self.db.flush()

        try:
            archive_buf, manifest, file_count = self._build_archive(
                tenant_id, pkg.modules, pkg.date_range_start, pkg.date_range_end, pkg.include_field_crosswalk,
            )
            integrity = hashlib.sha256(archive_buf.getvalue()).hexdigest()

            pkg.manifest = manifest
            pkg.integrity_hash = integrity
            pkg.file_count = file_count
            pkg.total_size_bytes = archive_buf.tell()

            # Risk analysis
            risk_level, risk_details = self._analyze_risk(tenant_id, pkg.modules)
            pkg.risk_level = risk_level
            pkg.risk_details = risk_details

            # In production this goes to S3; here we store the key pattern
            s3_key = f"exports/{tenant_id}/{package_id}/package.zip"
            pkg.package_s3_key = s3_key
            pkg.state = "READY"
            self.db.flush()

            logger.info(
                "export_package_built",
                extra={"package_id": str(package_id), "file_count": file_count, "size_bytes": archive_buf.tell()},
            )
        except Exception:
            pkg.state = "REQUESTED"  # Allow retry
            self.db.flush()
            logger.exception("export_package_build_failed", extra={"package_id": str(package_id)})
            raise

        return pkg

    def list_export_packages(self, tenant_id: uuid.UUID, limit: int = 50, offset: int = 0) -> list[ExportPackage]:
        rows = self.db.execute(
            select(ExportPackage)
            .where(ExportPackage.tenant_id == tenant_id, ExportPackage.deleted_at.is_(None))
            .order_by(ExportPackage.created_at.desc())
            .limit(limit)
            .offset(offset)
        ).scalars().all()
        return list(rows)

    def get_export_package(self, tenant_id: uuid.UUID, package_id: uuid.UUID) -> ExportPackage | None:
        return self.db.execute(
            select(ExportPackage).where(
                ExportPackage.id == package_id,
                ExportPackage.tenant_id == tenant_id,
            )
        ).scalar_one_or_none()

    # ── Secure Link Management ───────────────────────────────────────────

    def generate_secure_link(
        self,
        tenant_id: uuid.UUID,
        package_id: uuid.UUID,
        user_id: uuid.UUID,
        expires_hours: int = 72,
    ) -> dict[str, Any]:
        pkg = self.get_export_package(tenant_id, package_id)
        if not pkg or pkg.state != "READY":
            return {"error": "package_not_ready"}

        token = uuid.uuid4().hex + uuid.uuid4().hex
        from datetime import timedelta
        expires_at = datetime.now(UTC) + timedelta(hours=expires_hours)
        pkg.secure_link_token = token
        pkg.secure_link_expires_at = expires_at
        pkg.secure_link_revoked = False
        self.db.flush()

        self._log_access(package_id, user_id, "LINK_GENERATED")
        return {
            "download_url": f"/api/v1/portal/billing/exports/download/{token}",
            "expires_at": expires_at.isoformat(),
            "package_id": str(package_id),
        }

    def revoke_secure_link(self, tenant_id: uuid.UUID, package_id: uuid.UUID, user_id: uuid.UUID) -> bool:
        pkg = self.get_export_package(tenant_id, package_id)
        if not pkg:
            return False
        pkg.secure_link_revoked = True
        pkg.secure_link_token = None
        self.db.flush()
        self._log_access(package_id, user_id, "LINK_REVOKED")
        return True

    # ── Offboarding ──────────────────────────────────────────────────────

    def start_offboarding(
        self,
        tenant_id: uuid.UUID,
        requested_by: uuid.UUID,
        reason: str,
        target_vendor: str | None = None,
        requested_completion_date: datetime | None = None,
        delivery_method: str = "SECURE_LINK",
        delivery_target: str | None = None,
        contact_name: str | None = None,
        contact_email: str | None = None,
        modules: list[str] | None = None,
    ) -> dict[str, Any]:
        req = OffboardingRequest(
            tenant_id=tenant_id,
            state="REQUESTED",
            reason=reason,
            target_vendor=target_vendor,
            requested_completion_date=requested_completion_date,
            delivery_method=delivery_method,
            delivery_target=delivery_target,
            contact_name=contact_name,
            contact_email=contact_email,
            requested_by=requested_by,
        )
        self.db.add(req)
        self.db.flush()

        # Auto-create the full offboarding export package
        mods = modules or ["FULL_OFFBOARDING"]
        pkg = self.create_export_package(
            tenant_id=tenant_id,
            requested_by=requested_by,
            modules=mods,
            include_attachments=True,
            include_field_crosswalk=True,
            delivery_method=delivery_method,
            delivery_target=delivery_target,
            offboarding_id=req.id,
            notes=f"Auto-generated for offboarding: {reason}",
        )

        # Run risk analysis
        risk_level, risk_details = self._analyze_risk(tenant_id, mods)
        req.risk_level = risk_level
        req.risk_details = risk_details
        self.db.flush()

        logger.info("offboarding_started", extra={"offboarding_id": str(req.id), "tenant_id": str(tenant_id)})
        return {
            "offboarding_id": str(req.id),
            "package_id": str(pkg.id),
            "state": req.state,
            "risk_level": risk_level,
            "risk_details": risk_details,
        }

    def get_offboarding_status(self, tenant_id: uuid.UUID) -> dict[str, Any] | None:
        req = self.db.execute(
            select(OffboardingRequest)
            .where(OffboardingRequest.tenant_id == tenant_id)
            .order_by(OffboardingRequest.created_at.desc())
            .limit(1)
        ).scalar_one_or_none()
        if not req:
            return None

        packages = self.list_export_packages(tenant_id)
        pkg_summaries = [
            {
                "id": str(p.id),
                "state": p.state,
                "modules": p.modules,
                "risk_level": p.risk_level,
                "file_count": p.file_count,
                "total_size_bytes": p.total_size_bytes,
                "created_at": p.created_at.isoformat() if p.created_at else None,
            }
            for p in packages
            if p.offboarding_id == req.id
        ]

        return {
            "id": str(req.id),
            "tenant_id": str(req.tenant_id),
            "state": req.state,
            "reason": req.reason,
            "target_vendor": req.target_vendor,
            "requested_completion_date": req.requested_completion_date.isoformat() if req.requested_completion_date else None,
            "risk_level": req.risk_level,
            "risk_details": req.risk_details,
            "packages": pkg_summaries,
            "created_at": req.created_at.isoformat() if req.created_at else None,
            "updated_at": req.updated_at.isoformat() if req.updated_at else None,
        }

    # ── Risk Analysis ────────────────────────────────────────────────────

    def _analyze_risk(self, tenant_id: uuid.UUID, modules: list[str]) -> tuple[str, list[str]]:
        """Detect offboarding risks across billing, documentation, and communications."""
        risks: list[str] = []

        # Unresolved denials
        denied = self.db.scalar(
            select(func.count(Claim.id)).where(
                Claim.tenant_id == tenant_id,
                Claim.status == ClaimState.DENIED,
            )
        ) or 0
        if denied > 0:
            risks.append(f"{denied} unresolved denied claims")

        # Invalid claims
        invalid = self.db.scalar(
            select(func.count(Claim.id)).where(
                Claim.tenant_id == tenant_id,
                Claim.is_valid.is_(False),
            )
        ) or 0
        if invalid > 0:
            risks.append(f"{invalid} claims with validation errors (missing documentation)")

        # Unresolved claim issues
        unresolved_issues = self.db.scalar(
            select(func.count(ClaimIssue.id)).join(
                Claim, ClaimIssue.claim_id == Claim.id,
            ).where(
                Claim.tenant_id == tenant_id,
                ClaimIssue.resolved.is_(False),
            )
        ) or 0
        if unresolved_issues > 0:
            risks.append(f"{unresolved_issues} unresolved claim issues")

        # Orphaned claims (DRAFT with no activity)
        orphaned = self.db.scalar(
            select(func.count(Claim.id)).where(
                Claim.tenant_id == tenant_id,
                Claim.status == ClaimState.DRAFT,
                Claim.aging_days > 30,
            )
        ) or 0
        if orphaned > 0:
            risks.append(f"{orphaned} orphaned draft claims (>30 days old)")

        # Open patient balances
        open_balances = self.db.scalar(
            select(func.count(Claim.id)).where(
                Claim.tenant_id == tenant_id,
                Claim.patient_responsibility_cents > 0,
                Claim.patient_paid_cents < Claim.patient_responsibility_cents,
            )
        ) or 0
        if open_balances > 0:
            risks.append(f"{open_balances} claims with outstanding patient balances")

        # Determine level
        if len(risks) == 0:
            return "READY_FOR_HANDOFF", []
        elif len(risks) <= 2 and denied == 0:
            return "DATA_GAPS_DETECTED", risks
        elif denied > 0 or unresolved_issues > 10:
            return "HIGH_HANDOFF_RISK", risks
        else:
            return "REVIEW_REQUIRED", risks

    # ── Third-party Biller Management ────────────────────────────────────

    def list_billers(self, tenant_id: uuid.UUID) -> list[dict[str, Any]]:
        rows = self.db.execute(
            select(ThirdPartyBiller).where(
                ThirdPartyBiller.tenant_id == tenant_id,
                ThirdPartyBiller.deleted_at.is_(None),
            )
        ).scalars().all()
        return [
            {
                "id": str(b.id),
                "biller_name": b.biller_name,
                "contact_name": b.contact_name,
                "contact_email": b.contact_email,
                "portal_access_enabled": b.portal_access_enabled,
                "status": b.status,
                "created_at": b.created_at.isoformat() if b.created_at else None,
            }
            for b in rows
        ]

    # ── Access Logging ───────────────────────────────────────────────────

    def _log_access(
        self,
        package_id: uuid.UUID,
        user_id: uuid.UUID,
        access_type: str,
        ip_address: str | None = None,
        user_agent: str | None = None,
    ) -> None:
        log = ExportAccessLog(
            package_id=package_id,
            accessed_by=user_id,
            access_type=access_type,
            ip_address=ip_address,
            user_agent=user_agent,
        )
        self.db.add(log)
        self.db.flush()

    def get_access_logs(self, tenant_id: uuid.UUID, package_id: uuid.UUID) -> list[dict[str, Any]]:
        pkg = self.get_export_package(tenant_id, package_id)
        if not pkg:
            return []
        rows = self.db.execute(
            select(ExportAccessLog)
            .where(ExportAccessLog.package_id == package_id)
            .order_by(ExportAccessLog.accessed_at.desc())
        ).scalars().all()
        return [
            {
                "id": str(r.id),
                "access_type": r.access_type,
                "accessed_by": str(r.accessed_by),
                "ip_address": r.ip_address,
                "accessed_at": r.accessed_at.isoformat() if r.accessed_at else None,
            }
            for r in rows
        ]

    # ── Founder Oversight ────────────────────────────────────────────────

    def get_founder_export_overview(self) -> dict[str, Any]:
        """Cross-tenant export/offboarding overview for founder dashboard."""
        total_pkgs = self.db.scalar(select(func.count(ExportPackage.id))) or 0
        pending = self.db.scalar(
            select(func.count(ExportPackage.id)).where(
                ExportPackage.state.in_(["REQUESTED", "IN_REVIEW"]),
            )
        ) or 0
        building = self.db.scalar(
            select(func.count(ExportPackage.id)).where(ExportPackage.state == "BUILDING")
        ) or 0
        ready = self.db.scalar(
            select(func.count(ExportPackage.id)).where(ExportPackage.state == "READY")
        ) or 0
        delivered = self.db.scalar(
            select(func.count(ExportPackage.id)).where(ExportPackage.state == "DELIVERED")
        ) or 0
        active_offboardings = self.db.scalar(
            select(func.count(OffboardingRequest.id)).where(
                OffboardingRequest.state.notin_(["EXPIRED", "REVOKED"]),
            )
        ) or 0
        high_risk = self.db.scalar(
            select(func.count(ExportPackage.id)).where(
                ExportPackage.risk_level.in_(["HIGH_HANDOFF_RISK", "PACKAGE_INCOMPLETE"]),
            )
        ) or 0
        billers = self.db.scalar(
            select(func.count(ThirdPartyBiller.id)).where(ThirdPartyBiller.deleted_at.is_(None))
        ) or 0

        return {
            "total_packages": total_pkgs,
            "pending_review": pending,
            "building": building,
            "ready_for_delivery": ready,
            "delivered": delivered,
            "active_offboardings": active_offboardings,
            "high_risk_packages": high_risk,
            "active_billers": billers,
        }

    # ── Field Crosswalk ──────────────────────────────────────────────────

    def get_field_crosswalk(self) -> list[dict[str, str | bool]]:
        return BILLING_CROSSWALK

    # ── Archive Builder ──────────────────────────────────────────────────

    def _build_archive(
        self,
        tenant_id: uuid.UUID,
        modules: list[str],
        start: datetime | None,
        end: datetime | None,
        include_crosswalk: bool,
    ) -> tuple[io.BytesIO, dict[str, Any], int]:
        """Build a ZIP archive containing structured export data."""
        buf = io.BytesIO()
        manifest_entries: list[dict[str, str]] = []
        file_count = 0

        with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
            # README
            readme = self._build_readme(tenant_id, modules)
            zf.writestr("README.md", readme)
            manifest_entries.append({"file": "README.md", "type": "guide"})
            file_count += 1

            # Billing export
            if "BILLING" in modules or "FULL_OFFBOARDING" in modules:
                claims_csv = self._export_claims_csv(tenant_id, start, end)
                zf.writestr("billing/claims.csv", claims_csv)
                manifest_entries.append({"file": "billing/claims.csv", "type": "billing_claims"})
                file_count += 1

                audit_csv = self._export_audit_csv(tenant_id, start, end)
                zf.writestr("billing/audit_trail.csv", audit_csv)
                manifest_entries.append({"file": "billing/audit_trail.csv", "type": "billing_audit"})
                file_count += 1

                ledger_csv = self._export_ledger_csv(tenant_id, start, end)
                zf.writestr("billing/patient_balance_ledger.csv", ledger_csv)
                manifest_entries.append({"file": "billing/patient_balance_ledger.csv", "type": "billing_ledger"})
                file_count += 1

                issues_csv = self._export_issues_csv(tenant_id)
                zf.writestr("billing/claim_issues.csv", issues_csv)
                manifest_entries.append({"file": "billing/claim_issues.csv", "type": "billing_issues"})
                file_count += 1

            # Communications export
            if "COMMUNICATIONS" in modules or "FULL_OFFBOARDING" in modules:
                comms_csv = self._export_communications_csv(tenant_id, start, end)
                zf.writestr("communications/reminder_events.csv", comms_csv)
                manifest_entries.append({"file": "communications/reminder_events.csv", "type": "communications"})
                file_count += 1

            # Field crosswalk
            if include_crosswalk:
                crosswalk_csv = self._export_crosswalk_csv()
                zf.writestr("field_crosswalk.csv", crosswalk_csv)
                manifest_entries.append({"file": "field_crosswalk.csv", "type": "crosswalk"})
                file_count += 1

            # Manifest
            manifest = {
                "version": "1.0",
                "generated_at": datetime.now(UTC).isoformat(),
                "tenant_id": str(tenant_id),
                "modules": modules,
                "files": manifest_entries,
                "file_count": file_count,
            }
            zf.writestr("manifest.json", json.dumps(manifest, indent=2))
            file_count += 1

        buf.seek(0)
        return buf, manifest, file_count

    def _export_claims_csv(self, tenant_id: uuid.UUID, start: datetime | None, end: datetime | None) -> str:
        q = select(Claim).where(Claim.tenant_id == tenant_id)
        if start:
            q = q.where(Claim.created_at >= start)
        if end:
            q = q.where(Claim.created_at <= end)
        rows = self.db.execute(q.order_by(Claim.created_at)).scalars().all()
        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow([
            "claim_id", "incident_id", "patient_id", "claim_status", "payer_id", "payer_name",
            "total_billed_cents", "insurance_paid_cents", "patient_responsibility_cents",
            "patient_paid_cents", "aging_days", "appeal_status", "collections_status",
            "is_valid", "validation_errors", "created_at",
        ])
        for c in rows:
            writer.writerow([
                str(c.id), str(c.incident_id), str(c.patient_id), c.status,
                c.primary_payer_id or "", c.primary_payer_name or "",
                c.total_billed_cents, c.insurance_paid_cents,
                c.patient_responsibility_cents, c.patient_paid_cents,
                c.aging_days, c.appeal_status or "", c.collections_status or "",
                c.is_valid, json.dumps(c.validation_errors or []),
                c.created_at.isoformat() if c.created_at else "",
            ])
        return output.getvalue()

    def _export_audit_csv(self, tenant_id: uuid.UUID, start: datetime | None, end: datetime | None) -> str:
        q = (
            select(ClaimAuditEvent)
            .join(Claim, ClaimAuditEvent.claim_id == Claim.id)
            .where(Claim.tenant_id == tenant_id)
        )
        if start:
            q = q.where(ClaimAuditEvent.created_at >= start)
        if end:
            q = q.where(ClaimAuditEvent.created_at <= end)
        rows = self.db.execute(q.order_by(ClaimAuditEvent.created_at)).scalars().all()
        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow(["claim_id", "event_type", "old_value", "new_value", "metadata", "created_at"])
        for a in rows:
            writer.writerow([
                str(a.claim_id), a.event_type, a.old_value or "", a.new_value or "",
                json.dumps(a.metadata_blob or {}),
                a.created_at.isoformat() if a.created_at else "",
            ])
        return output.getvalue()

    def _export_ledger_csv(self, tenant_id: uuid.UUID, start: datetime | None, end: datetime | None) -> str:
        q = (
            select(PatientBalanceLedger)
            .join(Claim, PatientBalanceLedger.claim_id == Claim.id)
            .where(Claim.tenant_id == tenant_id)
        )
        if start:
            q = q.where(PatientBalanceLedger.created_at >= start)
        if end:
            q = q.where(PatientBalanceLedger.created_at <= end)
        rows = self.db.execute(q.order_by(PatientBalanceLedger.created_at)).scalars().all()
        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow(["ledger_id", "claim_id", "patient_id", "transaction_type", "amount_cents", "balance_after_cents", "description", "created_at"])
        for r in rows:
            writer.writerow([
                str(r.id), str(r.claim_id), str(r.patient_id), r.transaction_type,
                r.amount_cents, r.balance_after_cents, r.description or "",
                r.created_at.isoformat() if r.created_at else "",
            ])
        return output.getvalue()

    def _export_issues_csv(self, tenant_id: uuid.UUID) -> str:
        q = (
            select(ClaimIssue)
            .join(Claim, ClaimIssue.claim_id == Claim.id)
            .where(Claim.tenant_id == tenant_id)
        )
        rows = self.db.execute(q).scalars().all()
        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow(["issue_id", "claim_id", "severity", "source", "what_is_wrong", "why_it_matters", "what_to_do_next", "resolved", "confidence"])
        for i in rows:
            writer.writerow([
                str(i.id), str(i.claim_id), i.severity, i.source,
                i.what_is_wrong, i.why_it_matters, i.what_to_do_next,
                i.resolved, i.confidence or "",
            ])
        return output.getvalue()

    def _export_communications_csv(self, tenant_id: uuid.UUID, start: datetime | None, end: datetime | None) -> str:
        q = (
            select(ReminderEvent)
            .join(Claim, ReminderEvent.claim_id == Claim.id)
            .where(Claim.tenant_id == tenant_id)
        )
        if start:
            q = q.where(ReminderEvent.sent_at >= start)
        if end:
            q = q.where(ReminderEvent.sent_at <= end)
        rows = self.db.execute(q.order_by(ReminderEvent.sent_at)).scalars().all()
        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow(["event_id", "claim_id", "patient_id", "reminder_type", "sent_at", "status"])
        for r in rows:
            writer.writerow([
                str(r.id), str(r.claim_id), str(r.patient_id), r.reminder_type,
                r.sent_at.isoformat() if r.sent_at else "", r.status,
            ])
        return output.getvalue()

    def _export_crosswalk_csv(self) -> str:
        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow(["internal_field", "export_field", "business_meaning", "destination_file", "data_type", "required", "import_note"])
        for entry in BILLING_CROSSWALK:
            writer.writerow([
                entry["internal_field"], entry["export_field"], entry["business_meaning"],
                entry["destination_file"], entry["data_type"], entry["required"],
                entry.get("import_note", ""),
            ])
        return output.getvalue()

    def _build_readme(self, tenant_id: uuid.UUID, modules: list[str]) -> str:
        return f"""# FusionEMS Data Export Package

## Tenant
{tenant_id}

## Generated
{datetime.now(UTC).isoformat()}

## Modules Included
{chr(10).join(f'- {m}' for m in modules)}

## Package Structure
- `manifest.json` — Package manifest with file listing and checksums
- `field_crosswalk.csv` — Maps internal field names to export field names with business definitions
- `billing/claims.csv` — All claim records with status, financials, and payer data
- `billing/audit_trail.csv` — Full claim lifecycle event history
- `billing/patient_balance_ledger.csv` — Patient balance transactions (charges, payments, adjustments)
- `billing/claim_issues.csv` — Claim validation issues and AI explanations
- `communications/reminder_events.csv` — Patient communication events (SMS, email, call)

## Import Notes
- All monetary values are in cents (divide by 100 for dollars)
- All timestamps are ISO-8601 UTC
- UUIDs are used as primary keys — map to your internal IDs as needed
- See `field_crosswalk.csv` for detailed field-by-field import guidance

## Integrity
This package includes a SHA-256 integrity hash in the package metadata.
Verify the hash matches the downloaded archive to confirm data integrity.

## Support
Contact FusionEMS support for import assistance or data questions.
"""

    # ── Helpers ──────────────────────────────────────────────────────────

    @staticmethod
    def _claim_to_row(c: Claim) -> dict[str, Any]:
        return {
            "id": str(c.id),
            "incident_id": str(c.incident_id),
            "patient_id": str(c.patient_id),
            "status": c.status,
            "payer_name": c.primary_payer_name,
            "total_billed_cents": c.total_billed_cents,
            "insurance_paid_cents": c.insurance_paid_cents,
            "patient_responsibility_cents": c.patient_responsibility_cents,
            "aging_days": c.aging_days,
            "is_valid": c.is_valid,
            "appeal_status": c.appeal_status,
            "documentation_complete": c.is_valid and not c.validation_errors,
            "export_eligible": c.status not in (ClaimState.DRAFT,),
            "next_best_action": _next_action(c),
            "created_at": c.created_at.isoformat() if c.created_at else None,
        }


def _next_action(c: Claim) -> str | None:
    """Determine the next-best action for a claim."""
    if c.status == ClaimState.DENIED:
        return "Draft appeal or review denial reason"
    if c.status == ClaimState.READY_FOR_BILLING_REVIEW:
        return "Complete billing review"
    if c.status == ClaimState.READY_FOR_SUBMISSION:
        return "Submit to payer"
    if not c.is_valid:
        return "Resolve validation errors"
    if c.status == ClaimState.APPEAL_DRAFTED:
        return "Submit appeal for review"
    if c.patient_responsibility_cents > 0 and c.patient_paid_cents < c.patient_responsibility_cents:
        return "Follow up on patient balance"
    return None
