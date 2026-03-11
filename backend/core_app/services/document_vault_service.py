"""
Document Vault Service — Production Implementation

Complete business logic for the Founder-Only Document Manager.
"""
from __future__ import annotations

import io
import logging
import uuid
import zipfile
from datetime import UTC, datetime, timedelta
from typing import Any

import boto3
from botocore.exceptions import BotoCoreError, ClientError
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from core_app.ai.service import AiService
from core_app.core.config import get_settings
from core_app.core.errors import AppError
from core_app.models.document_vault import (
    AuditAction,
    ClassificationStatus,
    DocumentLockState,
    DocumentRecord,
    DocumentVersion,
    ExportPackage,
    ExportPackageStatus,
    PackageManifestItem,
    SmartFolder,
    VaultAuditEntry,
    VaultDefinition,
    VaultRetentionPolicy,
)

logger = logging.getLogger(__name__)

WISCONSIN_DEFAULTS: dict[str, Any] = {
    "mode": "wisconsin_medicaid_billing",
    "classes": {
        "legal_founder": {"years": 99, "is_permanent": True, "description": "Permanent structural documents."},
        "tax_financial": {"years": 7, "description": "Federal/State tax supporting documents."},
        "hr_workforce": {"years": 3, "description": "Post-termination personnel records."},
        "epcr_adult": {"years": 7, "description": "Adult ePCR (Wisconsin Administrative Code HFS 106.02)."},
        "epcr_minor": {"years": 25, "description": "Pediatric ePCR: majority age + 7 years."},
        "hipaa_compliance": {"years": 6, "description": "HIPAA policies/procedures and BAAs (45 CFR 164.530(j))."},
        "billing_rcm": {"years": 5, "description": "Medicaid/Medicare documentation (Wisconsin DHS 106.02(9))."},
        "contracts": {"years": 7, "description": "Executed contracts: statute of limitations + 1."},
        "medical_direction": {"years": 7, "description": "Medical director agreements and clinical protocols."},
        "fleet_equipment": {"years": 5, "description": "Vehicle/equipment maintenance: DOT and insurance retention."},
        "accreditation": {"years": 10, "description": "CAAS/CASC accreditation documents and QA/QI reports."},
        "insurance": {"years": 10, "description": "Insurance policies and certificates."},
        "intellectual_prop": {"years": 99, "is_permanent": True, "description": "Patents, trademarks, trade secrets: perpetual."},
    },
}

VAULT_CATALOG: list[dict[str, Any]] = [
    {"vault_id": "legal_corporate", "display_name": "Legal & Corporate", "description": "Articles of incorporation, bylaws, equity agreements, operating agreements, board resolutions.", "s3_prefix": "vaults/legal_corporate/", "retention_class": "legal_founder", "retention_years": 99, "is_permanent": True, "requires_legal_hold_review": True, "icon_key": "briefcase", "sort_order": 1},
    {"vault_id": "tax_financial", "display_name": "Tax & Financial", "description": "Federal/state tax returns, W-2s, 1099s, financial statements, audit reports.", "s3_prefix": "vaults/tax_financial/", "retention_class": "tax_financial", "retention_years": 7, "is_permanent": False, "requires_legal_hold_review": True, "icon_key": "receipt", "sort_order": 2},
    {"vault_id": "hr_workforce", "display_name": "HR & Workforce", "description": "Employment records, I-9s, background checks, credentialing, performance records.", "s3_prefix": "vaults/hr_workforce/", "retention_class": "hr_workforce", "retention_years": 3, "is_permanent": False, "requires_legal_hold_review": False, "icon_key": "users", "sort_order": 3},
    {"vault_id": "clinical_epcr", "display_name": "Clinical / ePCR", "description": "Patient care reports, clinical documentation, transport records, EKG strips.", "s3_prefix": "vaults/clinical_epcr/", "retention_class": "epcr_adult", "retention_years": 7, "is_permanent": False, "requires_legal_hold_review": True, "icon_key": "heart-pulse", "sort_order": 4},
    {"vault_id": "hipaa_compliance", "display_name": "HIPAA & Compliance", "description": "BAAs, privacy notices, HIPAA training records, risk assessments, sanction records.", "s3_prefix": "vaults/hipaa_compliance/", "retention_class": "hipaa_compliance", "retention_years": 6, "is_permanent": False, "requires_legal_hold_review": True, "icon_key": "shield", "sort_order": 5},
    {"vault_id": "billing_rcm", "display_name": "Billing & RCM", "description": "CMS-1500s, EOBs, remittances, appeals, prior authorizations, Medicaid correspondence.", "s3_prefix": "vaults/billing_rcm/", "retention_class": "billing_rcm", "retention_years": 5, "is_permanent": False, "requires_legal_hold_review": False, "icon_key": "dollar-sign", "sort_order": 6},
    {"vault_id": "contracts", "display_name": "Contracts", "description": "Vendor contracts, agency agreements, service contracts, NDAs, lease agreements.", "s3_prefix": "vaults/contracts/", "retention_class": "contracts", "retention_years": 7, "is_permanent": False, "requires_legal_hold_review": True, "icon_key": "file-signature", "sort_order": 7},
    {"vault_id": "medical_direction", "display_name": "Medical Direction", "description": "Medical director agreements, treatment protocols, standing orders, drug formularies.", "s3_prefix": "vaults/medical_direction/", "retention_class": "medical_direction", "retention_years": 7, "is_permanent": False, "requires_legal_hold_review": True, "icon_key": "stethoscope", "sort_order": 8},
    {"vault_id": "fleet_equipment", "display_name": "Fleet & Equipment", "description": "Vehicle titles, maintenance logs, equipment certifications, DOT inspections, GPS records.", "s3_prefix": "vaults/fleet_equipment/", "retention_class": "fleet_equipment", "retention_years": 5, "is_permanent": False, "requires_legal_hold_review": False, "icon_key": "truck", "sort_order": 9},
    {"vault_id": "accreditation", "display_name": "Accreditation", "description": "CAAS/CASC documents, QA/QI reports, accreditation certificates, performance improvement plans.", "s3_prefix": "vaults/accreditation/", "retention_class": "accreditation", "retention_years": 10, "is_permanent": False, "requires_legal_hold_review": False, "icon_key": "award", "sort_order": 10},
    {"vault_id": "insurance", "display_name": "Insurance", "description": "General liability, workers comp, vehicle insurance, D&O, certificates of insurance.", "s3_prefix": "vaults/insurance/", "retention_class": "insurance", "retention_years": 10, "is_permanent": False, "requires_legal_hold_review": False, "icon_key": "umbrella", "sort_order": 11},
    {"vault_id": "intellectual_prop", "display_name": "Intellectual Property", "description": "Patents, trademarks, trade secrets, proprietary technology documentation, product specs.", "s3_prefix": "vaults/intellectual_prop/", "retention_class": "intellectual_prop", "retention_years": 99, "is_permanent": True, "requires_legal_hold_review": True, "icon_key": "lightbulb", "sort_order": 12},
]

HOLD_STATES: frozenset[str] = frozenset({
    DocumentLockState.LEGAL_HOLD.value,
    DocumentLockState.TAX_HOLD.value,
    DocumentLockState.COMPLIANCE_HOLD.value,
    DocumentLockState.DESTROY_BLOCKED.value,
})

FORBIDDEN_TRANSITIONS: set[tuple[str, str]] = {
    (DocumentLockState.DESTROYED.value, DocumentLockState.ACTIVE.value),
    (DocumentLockState.DESTROYED.value, DocumentLockState.ARCHIVED.value),
}


class HoldStateError(AppError):
    def __init__(self, lock_state: str, operation: str = "modify") -> None:
        self.lock_state = lock_state
        super().__init__(
            status_code=403,
            message=f"Document is under '{lock_state}'. Cannot {operation}.",
            error_code="HOLD_STATE_VIOLATION",
        )


class DocumentVaultService:
    """Founder-Only Document Vault — complete business logic layer."""

    def __init__(self, db: Session) -> None:
        self.db = db
        self._settings = get_settings()
        self._s3 = boto3.client("s3")

    # ── Vault catalog ────────────────────────────────────────────────────────

    def seed_vault_catalog(self) -> None:
        for entry in VAULT_CATALOG:
            exists = self.db.execute(
                select(VaultDefinition.id).where(VaultDefinition.vault_id == entry["vault_id"])
            ).first()
            if not exists:
                self.db.add(VaultDefinition(**entry))
        self.db.commit()

    def get_vault_tree(self) -> list[dict[str, Any]]:
        vaults = self.db.execute(
            select(VaultDefinition).order_by(VaultDefinition.sort_order)
        ).scalars().all()
        result: list[dict[str, Any]] = []
        for vault in vaults:
            count = self.db.scalar(
                select(func.count(DocumentRecord.id)).where(
                    DocumentRecord.vault_id == vault.vault_id,
                    DocumentRecord.deleted_at.is_(None),
                )
            ) or 0
            result.append({
                "id": str(vault.id),
                "vault_id": vault.vault_id,
                "display_name": vault.display_name,
                "description": vault.description,
                "s3_prefix": vault.s3_prefix,
                "retention_class": vault.retention_class,
                "retention_years": vault.retention_years,
                "retention_days": vault.retention_days,
                "is_permanent": vault.is_permanent,
                "requires_legal_hold_review": vault.requires_legal_hold_review,
                "icon_key": vault.icon_key,
                "sort_order": vault.sort_order,
                "document_count": count,
            })
        return result

    def get_policies(self) -> dict[str, Any]:
        return WISCONSIN_DEFAULTS

    # ── S3 upload flow ───────────────────────────────────────────────────────

    def initiate_upload(
        self,
        *,
        vault_id: str,
        title: str,
        original_filename: str,
        content_type: str,
        file_size_bytes: int | None,
        doc_metadata: dict[str, Any],
        actor_user_id: uuid.UUID | None,
        actor_display: str | None,
    ) -> dict[str, Any]:
        vault = self._require_vault(vault_id)
        doc_uuid = uuid.uuid4()
        s3_key = f"{vault.s3_prefix}{doc_uuid}/{original_filename}"
        bucket = self._settings.s3_bucket_docs or "fusionems-documents"

        presigned = self._s3.generate_presigned_post(
            Bucket=bucket,
            Key=s3_key,
            Fields={"Content-Type": content_type},
            Conditions=[
                {"Content-Type": content_type},
                ["content-length-range", 1, 104_857_600],
            ],
            ExpiresIn=3600,
        )

        doc = DocumentRecord(
            id=doc_uuid,
            vault_id=vault_id,
            title=title,
            original_filename=original_filename,
            content_type=content_type,
            file_size_bytes=file_size_bytes,
            s3_bucket=bucket,
            s3_key=s3_key,
            lock_state=DocumentLockState.ACTIVE.value,
            retention_class=vault.retention_class,
            retain_until=self._compute_retain_until(vault),
            ocr_status=ClassificationStatus.PENDING.value,
            ai_classification_status=ClassificationStatus.PENDING.value,
            doc_metadata=doc_metadata,
            addenda=[],
            lock_history=[],
            uploaded_by_user_id=actor_user_id,
            uploaded_by_display=actor_display,
        )
        self.db.add(doc)
        self._write_audit(
            document=doc,
            action=AuditAction.UPLOAD.value,
            actor_user_id=actor_user_id,
            actor_display=actor_display,
            detail={"phase": "initiated", "s3_key": s3_key},
        )
        self.db.commit()

        return {
            "document_id": str(doc_uuid),
            "presigned_url": presigned["url"],
            "presigned_fields": presigned["fields"],
            "s3_bucket": bucket,
            "s3_key": s3_key,
            "expires_in_seconds": 3600,
        }

    def confirm_upload(
        self,
        *,
        document_id: uuid.UUID,
        s3_version_id: str | None,
        checksum_sha256: str | None,
        file_size_bytes: int | None,
        actor_user_id: uuid.UUID | None,
        actor_display: str | None,
    ) -> dict[str, Any]:
        doc = self._require_document(document_id)
        if s3_version_id:
            doc.s3_version_id = s3_version_id
        if checksum_sha256:
            doc.checksum_sha256 = checksum_sha256
        if file_size_bytes:
            doc.file_size_bytes = file_size_bytes

        version_count = self.db.scalar(
            select(func.count(DocumentVersion.id)).where(
                DocumentVersion.document_id == document_id
            )
        ) or 0
        version = DocumentVersion(
            document_id=document_id,
            version_number=version_count + 1,
            s3_bucket=doc.s3_bucket,
            s3_key=doc.s3_key,
            s3_version_id=s3_version_id,
            checksum_sha256=checksum_sha256,
            file_size_bytes=file_size_bytes,
            uploaded_by_user_id=actor_user_id,
        )
        self.db.add(version)
        doc.ocr_status = ClassificationStatus.PROCESSING.value
        self.db.flush()
        self._start_ocr_job(doc)
        self._write_audit(
            document=doc,
            action=AuditAction.UPLOAD.value,
            actor_user_id=actor_user_id,
            actor_display=actor_display,
            detail={"phase": "confirmed", "s3_version_id": s3_version_id},
        )
        self.db.commit()
        return {"document_id": str(document_id), "status": "ocr_queued"}

    # ── Presigned download ───────────────────────────────────────────────────

    def get_presigned_download(
        self,
        *,
        document_id: uuid.UUID,
        actor_user_id: uuid.UUID | None,
        actor_display: str | None,
    ) -> dict[str, Any]:
        doc = self._require_document(document_id)
        expires = 900
        url = self._s3.generate_presigned_url(
            "get_object",
            Params={"Bucket": doc.s3_bucket, "Key": doc.s3_key},
            ExpiresIn=expires,
        )
        self._write_audit(
            document=doc,
            action=AuditAction.DOWNLOAD.value,
            actor_user_id=actor_user_id,
            actor_display=actor_display,
        )
        self.db.commit()
        return {"document_id": str(document_id), "presigned_url": url, "expires_in_seconds": expires}

    # ── Document list / detail ───────────────────────────────────────────────

    def list_documents(
        self,
        *,
        vault_id: str | None = None,
        lock_state: str | None = None,
        query: str | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> list[DocumentRecord]:
        stmt = select(DocumentRecord).where(DocumentRecord.deleted_at.is_(None))
        if vault_id:
            stmt = stmt.where(DocumentRecord.vault_id == vault_id)
        if lock_state:
            stmt = stmt.where(DocumentRecord.lock_state == lock_state)
        if query:
            stmt = stmt.where(
                or_(
                    DocumentRecord.title.ilike(f"%{query}%"),
                    DocumentRecord.ocr_text.ilike(f"%{query}%"),
                )
            )
        stmt = stmt.order_by(DocumentRecord.created_at.desc()).limit(min(limit, 500)).offset(offset)
        return list(self.db.execute(stmt).scalars().all())

    def get_document(self, document_id: uuid.UUID) -> DocumentRecord:
        return self._require_document(document_id)

    def update_document_metadata(
        self,
        *,
        document_id: uuid.UUID,
        title: str | None,
        doc_metadata: dict[str, Any] | None,
        actor_user_id: uuid.UUID | None,
        actor_display: str | None,
    ) -> DocumentRecord:
        doc = self._require_document(document_id)
        if title:
            doc.title = title
        if doc_metadata is not None:
            doc.doc_metadata = {**(doc.doc_metadata or {}), **doc_metadata}
        self._write_audit(
            document=doc,
            action=AuditAction.METADATA_UPDATE.value,
            actor_user_id=actor_user_id,
            actor_display=actor_display,
            detail={"fields_updated": list((doc_metadata or {}).keys())},
        )
        self.db.commit()
        self.db.refresh(doc)
        return doc

    # ── Lock state machine ───────────────────────────────────────────────────

    def set_lock_state(
        self,
        document_id: uuid.UUID,
        new_state: str,
        reason: str,
        actor_user_id: uuid.UUID | None = None,
        actor_display: str | None = None,
    ) -> dict[str, Any]:
        valid_states = {s.value for s in DocumentLockState}
        if new_state not in valid_states:
            raise ValueError(f"Invalid lock state: {new_state!r}")
        doc = self._require_document(document_id)
        old_state = doc.lock_state
        if (old_state, new_state) in FORBIDDEN_TRANSITIONS:
            raise ValueError(f"Transition {old_state!r} -> {new_state!r} is not permitted.")
        history = list(doc.lock_history or [])
        history.append({
            "from_state": old_state,
            "to_state": new_state,
            "timestamp": datetime.now(UTC).isoformat(),
            "reason": reason,
            "actor": actor_display,
        })
        doc.lock_history = history
        doc.lock_state = new_state
        self._write_audit(
            document=doc,
            action=AuditAction.LOCK_STATE_CHANGE.value,
            actor_user_id=actor_user_id,
            actor_display=actor_display,
            detail={"from_state": old_state, "to_state": new_state, "reason": reason},
        )
        self.db.commit()
        logger.info("vault.lock_state_change document_id=%s %s->%s", document_id, old_state, new_state)
        return {"id": str(document_id), "lock_state": new_state}

    # ── Addendum ─────────────────────────────────────────────────────────────

    def append_addendum(
        self,
        document_id: uuid.UUID,
        addendum_data: dict[str, Any],
        reason: str,
        actor_user_id: uuid.UUID | None = None,
        actor_display: str | None = None,
    ) -> dict[str, Any]:
        doc = self._require_document(document_id)
        addenda = list(doc.addenda or [])
        addenda.append({
            "addendum_id": str(uuid.uuid4()),
            "timestamp": datetime.now(UTC).isoformat(),
            "reason": reason,
            "data": addendum_data,
            "actor": actor_display,
        })
        doc.addenda = addenda
        self._write_audit(
            document=doc,
            action=AuditAction.ADDENDUM_APPEND.value,
            actor_user_id=actor_user_id,
            actor_display=actor_display,
            detail={"reason": reason, "addendum_count": len(addenda)},
        )
        self.db.commit()
        return {"document_id": str(document_id), "addendum_count": len(addenda)}

    # ── OCR pipeline ─────────────────────────────────────────────────────────

    def _start_ocr_job(self, doc: DocumentRecord) -> None:
        try:
            textract = boto3.client("textract", region_name=self._settings.aws_region or "us-east-1")
            resp = textract.start_document_text_detection(
                DocumentLocation={"S3Object": {"Bucket": doc.s3_bucket, "Name": doc.s3_key}}
            )
            doc.ocr_job_id = resp["JobId"]
            doc.ocr_status = ClassificationStatus.PROCESSING.value
            logger.info("vault.ocr_started document_id=%s job_id=%s", doc.id, resp["JobId"])
        except (BotoCoreError, ClientError) as exc:
            doc.ocr_status = ClassificationStatus.FAILED.value
            logger.error("vault.ocr_start_failed document_id=%s error=%s", doc.id, exc)

    def poll_ocr_job(
        self,
        document_id: uuid.UUID,
        actor_user_id: uuid.UUID | None = None,
    ) -> dict[str, Any]:
        doc = self._require_document(document_id)
        if not doc.ocr_job_id:
            raise ValueError("No active OCR job found for this document.")
        try:
            textract = boto3.client("textract", region_name=self._settings.aws_region or "us-east-1")
            resp = textract.get_document_text_detection(JobId=doc.ocr_job_id, MaxResults=1000)
        except (BotoCoreError, ClientError) as exc:
            logger.error("vault.ocr_poll_failed document_id=%s error=%s", doc.id, exc)
            raise RuntimeError(f"Textract poll failed: {exc}") from exc

        status = resp.get("JobStatus", "UNKNOWN")
        if status == "SUCCEEDED":
            blocks = resp.get("Blocks", []) or []
            lines = [b.get("Text", "") for b in blocks if b.get("BlockType") == "LINE" and b.get("Text")]
            doc.ocr_text = "\n".join(lines)[:200_000]
            doc.ocr_completed_at = datetime.now(UTC)
            doc.ocr_status = ClassificationStatus.CLASSIFIED.value
            self._write_audit(document=doc, action=AuditAction.OCR_COMPLETE.value, actor_user_id=actor_user_id, detail={"lines_extracted": len(lines)})
            if doc.ocr_text:
                self._run_ai_classification(doc)
        elif status == "FAILED":
            doc.ocr_status = ClassificationStatus.FAILED.value
        self.db.commit()
        return {"document_id": str(document_id), "ocr_status": doc.ocr_status}

    # ── AI classification ─────────────────────────────────────────────────────

    def _run_ai_classification(self, doc: DocumentRecord) -> None:
        if not AiService.is_configured():
            doc.ai_classification_status = ClassificationStatus.FAILED.value
            logger.warning("vault.ai_classify_skipped AI not configured document_id=%s", doc.id)
            return
        system_prompt = (
            "You are an expert EMS and healthcare records classifier. "
            "Analyze the document text and classify it precisely. "
            "Respond ONLY with a valid JSON object. "
            'Schema: {"document_type": string, "tags": [string], "summary": string, "confidence": float}. '
            "document_type must be exactly one of: epcr, billing_record, contract, hipaa_baa, "
            "medical_protocol, tax_document, hr_record, insurance_certificate, "
            "legal_corporate, fleet_maintenance, accreditation_doc, ip_document, other. "
            "tags: up to 8 short lowercase tags. summary: 1-2 concise sentences. confidence: 0.0-1.0."
        )
        user_text = (
            f"Document title: {doc.title}\nVault: {doc.vault_id}\n\n"
            f"OCR text (first 4000 chars):\n{(doc.ocr_text or '')[:4000]}"
        )
        try:
            doc.ai_classification_status = ClassificationStatus.PROCESSING.value
            svc = AiService()
            payload, response = svc.chat_structured(system=system_prompt, user=user_text, max_tokens=512, temperature=0.05)
            doc.ai_document_type = payload.get("document_type")
            doc.ai_tags = payload.get("tags", [])
            doc.ai_summary = payload.get("summary")
            doc.ai_confidence = response.confidence
            doc.ai_classified_at = datetime.now(UTC)
            doc.ai_classification_status = ClassificationStatus.CLASSIFIED.value
            logger.info("vault.ai_classified document_id=%s type=%s confidence=%.2f", doc.id, doc.ai_document_type, doc.ai_confidence or 0.0)
        except Exception as exc:
            doc.ai_classification_status = ClassificationStatus.FAILED.value
            logger.error("vault.ai_classify_failed document_id=%s error=%s", doc.id, exc)

    def classify_document(
        self,
        document_id: uuid.UUID,
        actor_user_id: uuid.UUID | None = None,
        actor_display: str | None = None,
    ) -> dict[str, Any]:
        doc = self._require_document(document_id)
        if not doc.ocr_text:
            raise ValueError("Document has no OCR text. Run OCR first.")
        self._run_ai_classification(doc)
        self._write_audit(document=doc, action=AuditAction.AI_CLASSIFY.value, actor_user_id=actor_user_id, actor_display=actor_display)
        self.db.commit()
        return {
            "document_id": str(document_id),
            "ai_document_type": doc.ai_document_type,
            "ai_tags": doc.ai_tags,
            "ai_summary": doc.ai_summary,
            "ai_confidence": doc.ai_confidence,
            "ai_classification_status": doc.ai_classification_status,
            "ai_classified_at": doc.ai_classified_at.isoformat() if doc.ai_classified_at else None,
        }

    # ── Smart folders ────────────────────────────────────────────────────────

    def create_smart_folder(
        self,
        *,
        vault_id: str,
        name: str,
        description: str | None,
        color: str | None,
        icon_key: str | None,
        document_ids: list[uuid.UUID],
        actor_user_id: uuid.UUID | None,
    ) -> SmartFolder:
        self._require_vault(vault_id)
        folder = SmartFolder(
            vault_id=vault_id,
            name=name,
            description=description,
            color=color,
            icon_key=icon_key,
            document_ids=[str(d) for d in document_ids],
            is_ai_generated=False,
            created_by_user_id=actor_user_id,
        )
        self.db.add(folder)
        self.db.commit()
        self.db.refresh(folder)
        return folder

    def list_smart_folders(self, vault_id: str) -> list[SmartFolder]:
        return list(self.db.execute(select(SmartFolder).where(SmartFolder.vault_id == vault_id).order_by(SmartFolder.created_at.asc())).scalars().all())

    # ── Retention management ─────────────────────────────────────────────────

    def update_retention_policy(
        self,
        *,
        vault_id: str,
        retention_years: int | None,
        retention_days: int | None,
        is_permanent: bool,
        notes: str | None,
        actor_user_id: uuid.UUID | None,
    ) -> VaultRetentionPolicy:
        policy = self.db.execute(select(VaultRetentionPolicy).where(VaultRetentionPolicy.vault_id == vault_id)).scalar_one_or_none()
        if policy is None:
            policy = VaultRetentionPolicy(vault_id=vault_id, retention_years=retention_years, retention_days=retention_days, is_permanent=is_permanent, notes=notes, updated_by_user_id=actor_user_id)
            self.db.add(policy)
        else:
            policy.retention_years = retention_years
            policy.retention_days = retention_days
            policy.is_permanent = is_permanent
            policy.notes = notes
            policy.updated_by_user_id = actor_user_id
        self.db.commit()
        self.db.refresh(policy)
        return policy

    # ── Export package ───────────────────────────────────────────────────────

    def create_export_package(
        self,
        *,
        package_name: str,
        export_reason: str,
        document_ids: list[uuid.UUID],
        actor_user_id: uuid.UUID | None,
    ) -> ExportPackage:
        pkg = ExportPackage(package_name=package_name, export_reason=export_reason, status=ExportPackageStatus.PENDING.value, document_count=len(document_ids), requested_by_user_id=actor_user_id)
        self.db.add(pkg)
        self.db.flush()
        total_bytes = 0
        for doc_id in document_ids:
            doc = self._require_document(doc_id)
            item = PackageManifestItem(package_id=pkg.id, document_id=doc_id, path_in_zip=f"{doc.vault_id}/{doc.original_filename}", s3_bucket=doc.s3_bucket, s3_key=doc.s3_key, file_size_bytes=doc.file_size_bytes)
            self.db.add(item)
            total_bytes += doc.file_size_bytes or 0
        pkg.total_bytes = total_bytes
        self.db.commit()
        self.db.refresh(pkg)
        return pkg

    def build_export_zip(self, package_id: uuid.UUID) -> dict[str, Any]:
        pkg = self.db.execute(select(ExportPackage).where(ExportPackage.id == package_id)).scalar_one_or_none()
        if not pkg:
            raise ValueError("Export package not found.")
        pkg.status = ExportPackageStatus.BUILDING.value
        self.db.commit()
        items = self.db.execute(select(PackageManifestItem).where(PackageManifestItem.package_id == package_id)).scalars().all()
        try:
            buf = io.BytesIO()
            with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
                for item in items:
                    try:
                        obj = self._s3.get_object(Bucket=item.s3_bucket, Key=item.s3_key)
                        zf.writestr(item.path_in_zip, obj["Body"].read())
                    except (BotoCoreError, ClientError) as exc:
                        logger.warning("vault.export_zip_skip s3_key=%s error=%s", item.s3_key, exc)
            buf.seek(0)
            exports_bucket = self._settings.s3_bucket_exports or "fusionems-exports"
            zip_key = f"vault_exports/{package_id}.zip"
            self._s3.put_object(Bucket=exports_bucket, Key=zip_key, Body=buf.getvalue(), ContentType="application/zip")
            expires = 86400
            presigned_url = self._s3.generate_presigned_url("get_object", Params={"Bucket": exports_bucket, "Key": zip_key}, ExpiresIn=expires)
            pkg.s3_bucket = exports_bucket
            pkg.s3_key = zip_key
            pkg.status = ExportPackageStatus.READY.value
            pkg.expires_at = datetime.now(UTC) + timedelta(seconds=expires)
            self.db.commit()
            return {"package_id": str(package_id), "status": "ready", "presigned_url": presigned_url, "expires_in_seconds": expires}
        except Exception as exc:
            pkg.status = ExportPackageStatus.FAILED.value
            pkg.error_detail = str(exc)[:1024]
            self.db.commit()
            logger.error("vault.export_zip_failed package_id=%s error=%s", package_id, exc)
            raise

    # ── Audit trail ──────────────────────────────────────────────────────────

    def get_audit_trail(self, document_id: uuid.UUID, limit: int = 100) -> list[VaultAuditEntry]:
        return list(self.db.execute(select(VaultAuditEntry).where(VaultAuditEntry.document_id == document_id).order_by(VaultAuditEntry.occurred_at.desc()).limit(min(limit, 500))).scalars().all())

    # ── Internal helpers ─────────────────────────────────────────────────────

    def _require_vault(self, vault_id: str) -> VaultDefinition:
        vault = self.db.execute(select(VaultDefinition).where(VaultDefinition.vault_id == vault_id)).scalar_one_or_none()
        if not vault:
            raise ValueError(f"Vault not found: {vault_id!r}")
        return vault

    def _require_document(self, document_id: uuid.UUID) -> DocumentRecord:
        doc = self.db.execute(select(DocumentRecord).where(DocumentRecord.id == document_id, DocumentRecord.deleted_at.is_(None))).scalar_one_or_none()
        if not doc:
            raise ValueError(f"Document not found: {document_id}")
        return doc

    def _compute_retain_until(self, vault: VaultDefinition) -> datetime | None:
        if vault.is_permanent:
            return None
        if vault.retention_years:
            return datetime.now(UTC) + timedelta(days=vault.retention_years * 365)
        if vault.retention_days:
            return datetime.now(UTC) + timedelta(days=vault.retention_days)
        return None

    def _write_audit(self, *, document: DocumentRecord, action: str, actor_user_id: uuid.UUID | None = None, actor_display: str | None = None, detail: dict[str, Any] | None = None) -> None:
        self.db.add(VaultAuditEntry(document_id=document.id, vault_id=document.vault_id, action=action, actor_user_id=actor_user_id, actor_display=actor_display, detail=detail))

    # ── Legacy compat ────────────────────────────────────────────────────────

    def search_documents(self, query: str = "", filters: dict[str, Any] | None = None, limit: int = 50) -> list[dict[str, Any]]:
        docs = self.list_documents(query=query or None, limit=limit)
        return [{"id": str(d.id), "vault_id": d.vault_id, "title": d.title, "lock_state": d.lock_state, "s3_key": d.s3_key, "created_at": d.created_at.isoformat() if d.created_at else None} for d in docs]

    def append_addendum_to_epcr(self, document_id: str, addendum_data: dict[str, Any], reason: str) -> dict[str, Any]:
        return self.append_addendum(document_id=uuid.UUID(document_id), addendum_data=addendum_data, reason=reason)
