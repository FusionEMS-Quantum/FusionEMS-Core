# pyright: reportCallIssue=false
"""Service layer for founder command center domain aggregates."""
from __future__ import annotations

# ruff: noqa: I001

# pylint: disable=not-callable

import uuid
from datetime import UTC, datetime, timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session

from core_app.core.errors import AppError
from core_app.models.integration_connectors import (
    APIClientCredential,
    APIClientUsageWindow,
    APIKeyState,
    ConnectorInstallState,
    ConnectorSyncJob,
    ConnectorWebhookDelivery,
    IntegrationAuditEvent,
    SyncDeadLetter,
    SyncJobState,
    TenantConnectorInstall,
    WebhookDeliveryState,
)
from core_app.models.records_media import (
    ChainOfCustodyEvent,
    ChainOfCustodyState,
    ClinicalRecord,
    ExportDeliveryState,
    OCRConfidenceBand,
    OCRProcessingResult,
    QAException,
    QAExceptionState,
    RecordExport,
    RecordLifecycleState,
    ReleaseAuthorization,
    SignatureCapture,
    SignatureState,
)
from core_app.models.specialty_ops import (
    DutyTimeFlag,
    FireOpsState,
    FlightMission,
    FlightOpsState,
    HazardFlag,
    LandingZoneRecord,
    MissionFitScore,
    MissionPacket,
    MissionPacketState,
    PremisePreplan,
    SpecialtyTransportState,
)
from core_app.schemas.founder_command_domains import (
    FounderCommandAction,
    IntegrationCommandSummary,
    RecordsCommandSummary,
    SpecialtyOpsSummary,
)


class FounderCommandDomainService:
    """Read-optimized command center aggregate queries for founder operations."""

    def __init__(self, db: Session) -> None:
        self.db = db

    @staticmethod
    def _severity_rank(severity: str) -> int:
        return {"critical": 0, "high": 1, "medium": 2, "low": 3}.get(severity.lower(), 3)

    def _top_actions(self, actions: list[FounderCommandAction], limit: int = 5) -> list[FounderCommandAction]:
        actions.sort(key=lambda item: self._severity_rank(item.severity))
        return actions[:limit]

    def get_specialty_ops_summary(self) -> SpecialtyOpsSummary:
        preplan_gaps = self.db.query(PremisePreplan).filter(
            PremisePreplan.state.in_([
                FireOpsState.PREPLAN_MISSING,
                FireOpsState.COMMAND_REVIEW_REQUIRED,
            ])
        ).count()

        active_hazard_flags = self.db.query(HazardFlag).filter(HazardFlag.is_active.is_(True)).count()

        pending_lz_confirmations = self.db.query(LandingZoneRecord).filter(
            LandingZoneRecord.state == FlightOpsState.LZ_PENDING
        ).count()

        duty_time_warnings = self.db.query(DutyTimeFlag).filter(DutyTimeFlag.is_active.is_(True)).count()

        specialty_missions_blocked = self.db.query(MissionFitScore).filter(
            MissionFitScore.state == SpecialtyTransportState.BLOCKED
        ).count()

        mission_packet_failures = self.db.query(MissionPacket).filter(
            MissionPacket.state == MissionPacketState.FAILED
        ).count()

        actions: list[FounderCommandAction] = []
        if preplan_gaps > 0:
            actions.append(
                FounderCommandAction(
                    domain="specialty_ops",
                    severity="high",
                    summary=f"{preplan_gaps} premises need preplan completion or command review",
                    recommended_action="Escalate fire preplan completion and command validation backlog",
                )
            )
        if active_hazard_flags > 0:
            actions.append(
                FounderCommandAction(
                    domain="specialty_ops",
                    severity="critical",
                    summary=f"{active_hazard_flags} active hazard flags require command attention",
                    recommended_action="Open hazard board and assign immediate mitigation ownership",
                )
            )
        if pending_lz_confirmations > 0:
            actions.append(
                FounderCommandAction(
                    domain="hems",
                    severity="high",
                    summary=f"{pending_lz_confirmations} landing zones remain unconfirmed",
                    recommended_action="Route LZ verification tasks to on-shift flight operations",
                )
            )
        if duty_time_warnings > 0:
            actions.append(
                FounderCommandAction(
                    domain="hems",
                    severity="high",
                    summary=f"{duty_time_warnings} duty-time warnings are active",
                    recommended_action="Rebalance crew assignments to avoid duty violations",
                )
            )
        if specialty_missions_blocked > 0:
            actions.append(
                FounderCommandAction(
                    domain="specialty_transport",
                    severity="high",
                    summary=f"{specialty_missions_blocked} specialty missions are blocked",
                    recommended_action="Resolve crew/equipment fit blockers before dispatch",
                )
            )
        if mission_packet_failures > 0:
            actions.append(
                FounderCommandAction(
                    domain="mission_packets",
                    severity="medium",
                    summary=f"{mission_packet_failures} mission packets failed delivery",
                    recommended_action="Inspect packet delivery failures and requeue with trace",
                )
            )

        return SpecialtyOpsSummary(
            preplan_gaps=preplan_gaps,
            active_hazard_flags=active_hazard_flags,
            pending_lz_confirmations=pending_lz_confirmations,
            duty_time_warnings=duty_time_warnings,
            specialty_missions_blocked=specialty_missions_blocked,
            mission_packet_failures=mission_packet_failures,
            top_actions=self._top_actions(actions),
        )

    def get_records_command_summary(self) -> RecordsCommandSummary:
        draft_or_unsealed_records = self.db.query(ClinicalRecord).filter(
            ClinicalRecord.lifecycle_state.in_([
                RecordLifecycleState.DRAFT,
                RecordLifecycleState.READY,
            ])
        ).count()

        signature_gaps = self.db.query(SignatureCapture).filter(
            SignatureCapture.signature_state != SignatureState.VERIFIED
        ).count()

        low_confidence_ocr_results = self.db.query(OCRProcessingResult).filter(
            OCRProcessingResult.confidence_band == OCRConfidenceBand.LOW
        ).count()

        chain_of_custody_anomalies = self.db.query(ChainOfCustodyEvent).filter(
            ChainOfCustodyEvent.state.in_([
                ChainOfCustodyState.ANOMALY,
                ChainOfCustodyState.REVIEW_REQUIRED,
            ])
        ).count()

        pending_release_authorizations = self.db.query(ReleaseAuthorization).filter(
            ReleaseAuthorization.approved_at.is_(None)
        ).count()

        failed_record_exports = self.db.query(RecordExport).filter(
            RecordExport.state == ExportDeliveryState.FAILED
        ).count()

        open_qa_exceptions = self.db.query(QAException).filter(
            QAException.state == QAExceptionState.OPEN
        ).count()

        actions: list[FounderCommandAction] = []
        if signature_gaps > 0:
            actions.append(
                FounderCommandAction(
                    domain="records",
                    severity="high",
                    summary=f"{signature_gaps} records have unverified signatures",
                    recommended_action="Trigger signature reconciliation workflow and notify field supervisors",
                )
            )
        if chain_of_custody_anomalies > 0:
            actions.append(
                FounderCommandAction(
                    domain="records",
                    severity="critical",
                    summary=f"{chain_of_custody_anomalies} chain-of-custody anomalies detected",
                    recommended_action="Escalate anomalies to compliance and lock affected release operations",
                )
            )
        if low_confidence_ocr_results > 0:
            actions.append(
                FounderCommandAction(
                    domain="records",
                    severity="medium",
                    summary=f"{low_confidence_ocr_results} OCR outputs are low-confidence",
                    recommended_action="Queue manual validation for OCR-extracted fields before persistence",
                )
            )
        if failed_record_exports > 0:
            actions.append(
                FounderCommandAction(
                    domain="records",
                    severity="high",
                    summary=f"{failed_record_exports} record exports failed delivery",
                    recommended_action="Review export failures by destination and replay with audit trace",
                )
            )
        if open_qa_exceptions > 0:
            actions.append(
                FounderCommandAction(
                    domain="records",
                    severity="medium",
                    summary=f"{open_qa_exceptions} QA exceptions remain unresolved",
                    recommended_action="Prioritize exceptions by severity and assign remediation owner",
                )
            )

        return RecordsCommandSummary(
            draft_or_unsealed_records=draft_or_unsealed_records,
            signature_gaps=signature_gaps,
            low_confidence_ocr_results=low_confidence_ocr_results,
            chain_of_custody_anomalies=chain_of_custody_anomalies,
            pending_release_authorizations=pending_release_authorizations,
            failed_record_exports=failed_record_exports,
            open_qa_exceptions=open_qa_exceptions,
            top_actions=self._top_actions(actions),
        )

    def get_integration_command_summary(self) -> IntegrationCommandSummary:
        since = datetime.now(UTC) - timedelta(hours=24)

        degraded_or_disabled_installs = self.db.query(TenantConnectorInstall).filter(
            TenantConnectorInstall.install_state.in_([
                ConnectorInstallState.DEGRADED,
                ConnectorInstallState.DISABLED,
            ])
        ).count()

        failed_sync_jobs_24h = self.db.query(ConnectorSyncJob).filter(
            ConnectorSyncJob.state == SyncJobState.FAILED,
            ConnectorSyncJob.created_at >= since,
        ).count()

        dead_letter_records_24h = self.db.query(SyncDeadLetter).filter(
            SyncDeadLetter.created_at >= since
        ).count()

        pending_webhook_retries = self.db.query(ConnectorWebhookDelivery).filter(
            ConnectorWebhookDelivery.state == WebhookDeliveryState.RETRYING
        ).count()

        revoked_or_rotating_api_credentials = self.db.query(APIClientCredential).filter(
            APIClientCredential.credential_state.in_([
                APIKeyState.ROTATING,
                APIKeyState.REVOKED,
            ])
        ).count()

        quota_denial_windows_24h = self.db.query(APIClientUsageWindow).filter(
            APIClientUsageWindow.window_start >= since,
            APIClientUsageWindow.denied_count > 0,
        ).count()

        actions: list[FounderCommandAction] = []
        if degraded_or_disabled_installs > 0:
            actions.append(
                FounderCommandAction(
                    domain="integrations",
                    severity="critical",
                    summary=f"{degraded_or_disabled_installs} connector installs are degraded or disabled",
                    recommended_action="Open connector incident runbook and restore degraded installs",
                )
            )
        if failed_sync_jobs_24h > 0:
            actions.append(
                FounderCommandAction(
                    domain="integrations",
                    severity="high",
                    summary=f"{failed_sync_jobs_24h} sync jobs failed in the last 24h",
                    recommended_action="Inspect failed sync jobs and replay after error classification",
                )
            )
        if dead_letter_records_24h > 0:
            actions.append(
                FounderCommandAction(
                    domain="integrations",
                    severity="high",
                    summary=f"{dead_letter_records_24h} records moved to dead-letter queue",
                    recommended_action="Drain dead-letter queue with deterministic reprocessing policy",
                )
            )
        if pending_webhook_retries > 0:
            actions.append(
                FounderCommandAction(
                    domain="integrations",
                    severity="medium",
                    summary=f"{pending_webhook_retries} webhooks are still retrying",
                    recommended_action="Validate endpoint health and rotate signing keys if needed",
                )
            )
        if revoked_or_rotating_api_credentials > 0:
            actions.append(
                FounderCommandAction(
                    domain="integrations",
                    severity="medium",
                    summary=f"{revoked_or_rotating_api_credentials} API credentials are rotating/revoked",
                    recommended_action="Confirm all clients have cut over to current credential generation",
                )
            )
        if quota_denial_windows_24h > 0:
            actions.append(
                FounderCommandAction(
                    domain="integrations",
                    severity="high",
                    summary=f"{quota_denial_windows_24h} usage windows hit quota denials in 24h",
                    recommended_action="Adjust per-client quotas or optimize burst consumption behavior",
                )
            )

        return IntegrationCommandSummary(
            degraded_or_disabled_installs=degraded_or_disabled_installs,
            failed_sync_jobs_24h=failed_sync_jobs_24h,
            dead_letter_records_24h=dead_letter_records_24h,
            pending_webhook_retries=pending_webhook_retries,
            revoked_or_rotating_api_credentials=revoked_or_rotating_api_credentials,
            quota_denial_windows_24h=quota_denial_windows_24h,
            top_actions=self._top_actions(actions),
        )

    def list_pending_flight_missions(self, limit: int = 50) -> list[FlightMission]:
        stmt = (
            select(FlightMission)
            .where(
                FlightMission.state.in_([
                    FlightOpsState.LZ_PENDING,
                    FlightOpsState.MISSION_DELAYED,
                ])
            )
            .order_by(FlightMission.updated_at.desc())
            .limit(limit)
        )
        return list(self.db.execute(stmt).scalars().all())

    def list_failed_record_exports(self, limit: int = 50) -> list[RecordExport]:
        stmt = (
            select(RecordExport)
            .where(RecordExport.state == ExportDeliveryState.FAILED)
            .order_by(RecordExport.updated_at.desc())
            .limit(limit)
        )
        return list(self.db.execute(stmt).scalars().all())

    def list_failed_sync_jobs(self, limit: int = 50) -> list[ConnectorSyncJob]:
        stmt = (
            select(ConnectorSyncJob)
            .where(ConnectorSyncJob.state == SyncJobState.FAILED)
            .order_by(ConnectorSyncJob.updated_at.desc())
            .limit(limit)
        )
        return list(self.db.execute(stmt).scalars().all())

    def create_connector_sync_job(
        self,
        tenant_id: uuid.UUID,
        actor_user_id: uuid.UUID,
        tenant_connector_install_id: uuid.UUID,
        direction: str,
        state: str,
        records_attempted: int,
        records_succeeded: int,
        records_failed: int,
        error_summary: dict[str, object],
    ) -> ConnectorSyncJob:
        install = self.db.execute(
            select(TenantConnectorInstall).where(
                TenantConnectorInstall.id == tenant_connector_install_id,
                TenantConnectorInstall.tenant_id == tenant_id,
            )
        ).scalar_one_or_none()
        if install is None:
            raise AppError(
                code="NOT_FOUND",
                message="Connector install not found for tenant",
                status_code=404,
            )

        if install.install_state not in {
            ConnectorInstallState.ACTIVE,
            ConnectorInstallState.VALIDATED,
        }:
            raise AppError(
                code="VALIDATION_ERROR",
                message="Connector install must be ACTIVE or VALIDATED before queuing sync jobs",
                status_code=400,
            )

        normalized_direction = direction.strip().upper()
        if normalized_direction not in {"INBOUND", "OUTBOUND"}:
            raise AppError(
                code="VALIDATION_ERROR",
                message="direction must be INBOUND or OUTBOUND",
                status_code=400,
            )

        try:
            normalized_state = SyncJobState(state)
        except ValueError as exc:
            raise AppError(
                code="VALIDATION_ERROR",
                message=f"Invalid sync job state: {state}",
                status_code=400,
            ) from exc

        if normalized_state != SyncJobState.QUEUED:
            raise AppError(
                code="VALIDATION_ERROR",
                message="New sync jobs must be created in QUEUED state",
                status_code=400,
            )

        if records_attempted != 0 or records_succeeded != 0 or records_failed != 0:
            raise AppError(
                code="VALIDATION_ERROR",
                message="New sync jobs must start with zeroed record counters",
                status_code=400,
            )

        job = ConnectorSyncJob(
            tenant_id=tenant_id,
            tenant_connector_install_id=tenant_connector_install_id,
            direction=normalized_direction,
            state=SyncJobState.QUEUED,
            records_attempted=0,
            records_succeeded=0,
            records_failed=0,
            error_summary=error_summary,
            started_at=None,
        )
        self.db.add(job)
        self.db.flush()

        audit = IntegrationAuditEvent(
            tenant_id=tenant_id,
            entity_type="ConnectorSyncJob",
            entity_id=job.id,
            event_type="SYNC_JOB_CREATED",
            actor_user_id=actor_user_id,
            event_payload={
                "direction": normalized_direction,
                "state": SyncJobState.QUEUED.value,
                "records_attempted": 0,
                "records_succeeded": 0,
                "records_failed": 0,
            },
        )
        self.db.add(audit)
        self.db.flush()
        return job

    def add_sync_dead_letter(
        self,
        tenant_id: uuid.UUID,
        actor_user_id: uuid.UUID,
        connector_sync_job_id: uuid.UUID,
        external_record_ref: str,
        reason: str,
        payload: dict[str, object],
    ) -> SyncDeadLetter:
        sync_job = self.db.execute(
            select(ConnectorSyncJob).where(
                ConnectorSyncJob.id == connector_sync_job_id,
                ConnectorSyncJob.tenant_id == tenant_id,
            )
        ).scalar_one_or_none()
        if sync_job is None:
            raise AppError(
                code="NOT_FOUND",
                message="Sync job not found for tenant",
                status_code=404,
            )

        dead_letter = SyncDeadLetter(
            tenant_id=tenant_id,
            connector_sync_job_id=connector_sync_job_id,
            external_record_ref=external_record_ref,
            reason=reason,
            payload=payload,
        )
        self.db.add(dead_letter)
        self.db.flush()

        audit = IntegrationAuditEvent(
            tenant_id=tenant_id,
            entity_type="SyncDeadLetter",
            entity_id=dead_letter.id,
            event_type="SYNC_DEAD_LETTER_CREATED",
            actor_user_id=actor_user_id,
            event_payload={
                "connector_sync_job_id": str(connector_sync_job_id),
                "external_record_ref": external_record_ref,
                "reason": reason,
            },
        )
        self.db.add(audit)
        self.db.flush()
        return dead_letter
