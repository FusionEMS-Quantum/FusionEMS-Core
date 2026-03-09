# pyright: reportCallIssue=false
"""Service layer for founder command center domain aggregates."""
from __future__ import annotations

# ruff: noqa: I001

# pylint: disable=not-callable

import uuid
from collections import defaultdict
from datetime import UTC, datetime, timedelta
from typing import TypedDict

from sqlalchemy import select
from sqlalchemy.orm import Session

from core_app.core.config import get_settings
from core_app.core.errors import AppError
from core_app.models.integration_connectors import (
    ConnectorCatalog,
    APIClientCredential,
    APIClientUsageWindow,
    APIKeyState,
    ConnectorProfile,
    ConnectorInstallState,
    ConnectorSecretMaterialization,
    ConnectorSyncJob,
    ConnectorWebhookDelivery,
    ConnectorWebhookEndpoint,
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
    FounderGrowthSetupWizard,
    FounderGrowthSummary,
    GrowthConnectionStatus,
    GrowthSummaryMetric,
    IntegrationCommandSummary,
    LaunchOrchestratorRunResponse,
    RecordsCommandSummary,
    SpecialtyOpsSummary,
)
from core_app.repositories.domination_repository import DominationRepository


class _GrowthServiceDefinition(TypedDict):
    service_key: str
    label: str
    required: bool
    aliases: tuple[str, ...]
    available_automations: tuple[str, ...]


class FounderCommandDomainService:
    """Read-optimized command center aggregate queries for founder operations."""

    _GROWTH_SERVICE_DEFINITIONS: tuple[_GrowthServiceDefinition, ...] = (
        {
            "service_key": "linkedin",
            "label": "LinkedIn Publishing",
            "required": True,
            "aliases": ("linkedin",),
            "available_automations": (
                "publish_company_posts",
                "launch_day_announcements",
                "engagement_followup_queue",
            ),
        },
        {
            "service_key": "x",
            "label": "X Publishing",
            "required": True,
            "aliases": ("x", "twitter"),
            "available_automations": (
                "publish_threads",
                "feature_burst_campaigns",
                "cta_click_tracking",
            ),
        },
        {
            "service_key": "facebook",
            "label": "Facebook Publishing",
            "required": True,
            "aliases": ("facebook", "meta"),
            "available_automations": (
                "publish_page_posts",
                "community_reply_queue",
                "campaign_tagging",
            ),
        },
        {
            "service_key": "instagram",
            "label": "Instagram Publishing",
            "required": True,
            "aliases": ("instagram",),
            "available_automations": (
                "publish_captions",
                "hashtag_rotation",
                "creative_variant_testing",
            ),
        },
        {
            "service_key": "youtube",
            "label": "YouTube Distribution",
            "required": False,
            "aliases": ("youtube",),
            "available_automations": (
                "demo_video_publish",
                "thumbnail_ab_rotation",
                "playlist_campaign_bundles",
            ),
        },
        {
            "service_key": "microsoft365_outlook",
            "label": "Microsoft 365 Outlook",
            "required": True,
            "aliases": ("graph", "microsoft", "outlook", "office365"),
            "available_automations": (
                "lead_sequence_dispatch",
                "demo_confirmation_flow",
                "reply_capture_to_lead_timeline",
            ),
        },
        {
            "service_key": "booking",
            "label": "Booking / Scheduling",
            "required": True,
            "aliases": ("booking", "calendar", "scheduling", "calendly"),
            "available_automations": (
                "booked_demo_to_sequence",
                "no_show_reengagement",
                "calendar_health_alerts",
            ),
        },
        {
            "service_key": "domain_dns",
            "label": "Domain + DNS",
            "required": True,
            "aliases": ("domain", "dns", "route53", "cloudflare"),
            "available_automations": (
                "landing_page_activation",
                "sender_identity_validation",
                "trust_page_publish",
            ),
        },
        {
            "service_key": "analytics",
            "label": "Analytics Pipeline",
            "required": True,
            "aliases": ("analytics", "ga4", "segment", "mixpanel"),
            "available_automations": (
                "campaign_attribution",
                "funnel_dropoff_alerts",
                "launch_recommendation_briefs",
            ),
        },
        {
            "service_key": "demo_provider",
            "label": "Demo Render Provider",
            "required": False,
            "aliases": ("demo", "render", "video"),
            "available_automations": (
                "guided_demo_generation",
                "scene_regeneration",
                "thumbnail_generation",
            ),
        },
        {
            "service_key": "lead_store",
            "label": "Lead Store / CRM Pipeline",
            "required": True,
            "aliases": ("lead", "crm", "pipeline"),
            "available_automations": (
                "lead_scoring_updates",
                "stage_transition_automation",
                "high_intent_alerting",
            ),
        },
    )

    def __init__(self, db: Session) -> None:
        self.db = db

    def _repo(self, table: str) -> DominationRepository:
        return DominationRepository(self.db, table=table)

    @staticmethod
    def _extract_data(row: dict[str, object]) -> dict[str, object]:
        data = row.get("data")
        return data if isinstance(data, dict) else {}

    @staticmethod
    def _safe_int(value: object, *, default: int = 0) -> int:
        try:
            return int(value)  # type: ignore[arg-type]
        except (TypeError, ValueError):
            return default

    @staticmethod
    def _safe_str(value: object, *, default: str = "") -> str:
        return str(value).strip() if value is not None else default

    @staticmethod
    def _bucket_for_lead_score(score: int) -> str:
        if score < 25:
            return "0-24"
        if score < 50:
            return "25-49"
        if score < 75:
            return "50-74"
        return "75-100"

    @staticmethod
    def _graph_mailbox_is_configured() -> bool:
        settings = get_settings()
        required = [
            settings.graph_tenant_id,
            settings.graph_client_id,
            settings.graph_client_secret,
            settings.graph_founder_email,
        ]
        return all(bool(str(item).strip()) for item in required)

    def _connector_install_snapshots(
        self,
        tenant_id: uuid.UUID,
    ) -> list[dict[str, object]]:
        rows = self.db.execute(
            select(TenantConnectorInstall, ConnectorProfile, ConnectorCatalog)
            .join(
                ConnectorProfile,
                TenantConnectorInstall.connector_profile_id == ConnectorProfile.id,
            )
            .join(
                ConnectorCatalog,
                ConnectorProfile.connector_catalog_id == ConnectorCatalog.id,
            )
            .where(TenantConnectorInstall.tenant_id == tenant_id)
        ).all()

        snapshots: list[dict[str, object]] = []
        for install, profile, catalog in rows:
            snapshots.append(
                {
                    "install": install,
                    "profile": profile,
                    "catalog": catalog,
                    "match_text": " ".join(
                        [
                            str(catalog.connector_key or "").lower(),
                            str(catalog.display_name or "").lower(),
                            str(profile.profile_name or "").lower(),
                        ]
                    ),
                }
            )
        return snapshots

    def _map_install_activity(
        self,
        tenant_id: uuid.UUID,
    ) -> tuple[
        dict[uuid.UUID, datetime],
        dict[uuid.UUID, datetime],
        dict[uuid.UUID, int],
        dict[uuid.UUID, ConnectorSecretMaterialization],
    ]:
        success_by_install: dict[uuid.UUID, datetime] = {}
        failure_by_install: dict[uuid.UUID, datetime] = {}

        sync_jobs = list(
            self.db.execute(
                select(ConnectorSyncJob).where(ConnectorSyncJob.tenant_id == tenant_id)
            ).scalars().all()
        )
        for job in sync_jobs:
            if job.state == SyncJobState.COMPLETED and job.updated_at is not None:
                previous = success_by_install.get(job.tenant_connector_install_id)
                if previous is None or previous < job.updated_at:
                    success_by_install[job.tenant_connector_install_id] = job.updated_at
            if job.state == SyncJobState.FAILED and job.updated_at is not None:
                previous = failure_by_install.get(job.tenant_connector_install_id)
                if previous is None or previous < job.updated_at:
                    failure_by_install[job.tenant_connector_install_id] = job.updated_at

        retry_counts: dict[uuid.UUID, int] = defaultdict(int)
        endpoints = list(
            self.db.execute(
                select(ConnectorWebhookEndpoint).where(ConnectorWebhookEndpoint.tenant_id == tenant_id)
            ).scalars().all()
        )
        endpoint_to_install = {
            endpoint.id: endpoint.tenant_connector_install_id
            for endpoint in endpoints
        }
        if endpoint_to_install:
            deliveries = list(
                self.db.execute(
                    select(ConnectorWebhookDelivery).where(
                        ConnectorWebhookDelivery.connector_webhook_endpoint_id.in_(
                            tuple(endpoint_to_install.keys())
                        )
                    )
                ).scalars().all()
            )
            for delivery in deliveries:
                install_id = endpoint_to_install.get(delivery.connector_webhook_endpoint_id)
                if install_id is None:
                    continue
                if delivery.state == WebhookDeliveryState.RETRYING:
                    retry_counts[install_id] += 1
                if (
                    delivery.state == WebhookDeliveryState.DEAD_LETTERED
                    and delivery.updated_at is not None
                ):
                    previous = failure_by_install.get(install_id)
                    if previous is None or previous < delivery.updated_at:
                        failure_by_install[install_id] = delivery.updated_at
                if (
                    delivery.state == WebhookDeliveryState.DELIVERED
                    and delivery.updated_at is not None
                ):
                    previous = success_by_install.get(install_id)
                    if previous is None or previous < delivery.updated_at:
                        success_by_install[install_id] = delivery.updated_at

        latest_secret_by_install: dict[uuid.UUID, ConnectorSecretMaterialization] = {}
        secrets = list(
            self.db.execute(
                select(ConnectorSecretMaterialization)
                .where(ConnectorSecretMaterialization.tenant_id == tenant_id)
                .order_by(ConnectorSecretMaterialization.materialized_at.desc())
            ).scalars().all()
        )
        for secret in secrets:
            latest_secret_by_install.setdefault(secret.tenant_connector_install_id, secret)

        return success_by_install, failure_by_install, dict(retry_counts), latest_secret_by_install

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

    def _integration_command_summary(
        self,
        *,
        tenant_id: uuid.UUID | None,
    ) -> IntegrationCommandSummary:
        since = datetime.now(UTC) - timedelta(hours=24)

        degraded_or_disabled_query = self.db.query(TenantConnectorInstall).filter(
            TenantConnectorInstall.install_state.in_([
                ConnectorInstallState.DEGRADED,
                ConnectorInstallState.DISABLED,
            ])
        )
        if tenant_id is not None:
            degraded_or_disabled_query = degraded_or_disabled_query.filter(
                TenantConnectorInstall.tenant_id == tenant_id
            )
        degraded_or_disabled_installs = degraded_or_disabled_query.count()

        failed_sync_jobs_query = self.db.query(ConnectorSyncJob).filter(
            ConnectorSyncJob.state == SyncJobState.FAILED,
            ConnectorSyncJob.created_at >= since,
        )
        if tenant_id is not None:
            failed_sync_jobs_query = failed_sync_jobs_query.filter(
                ConnectorSyncJob.tenant_id == tenant_id
            )
        failed_sync_jobs_24h = failed_sync_jobs_query.count()

        dead_letter_records_query = self.db.query(SyncDeadLetter).filter(
            SyncDeadLetter.created_at >= since
        )
        if tenant_id is not None:
            dead_letter_records_query = dead_letter_records_query.filter(
                SyncDeadLetter.tenant_id == tenant_id
            )
        dead_letter_records_24h = dead_letter_records_query.count()

        pending_webhook_retries_query = self.db.query(ConnectorWebhookDelivery).filter(
            ConnectorWebhookDelivery.state == WebhookDeliveryState.RETRYING
        )
        if tenant_id is not None:
            pending_webhook_retries_query = pending_webhook_retries_query.join(
                ConnectorWebhookEndpoint,
                ConnectorWebhookDelivery.connector_webhook_endpoint_id == ConnectorWebhookEndpoint.id,
            ).filter(ConnectorWebhookEndpoint.tenant_id == tenant_id)
        pending_webhook_retries = pending_webhook_retries_query.count()

        rotating_creds_query = self.db.query(APIClientCredential).filter(
            APIClientCredential.credential_state.in_([
                APIKeyState.ROTATING,
                APIKeyState.REVOKED,
            ])
        )
        if tenant_id is not None:
            rotating_creds_query = rotating_creds_query.filter(
                APIClientCredential.tenant_id == tenant_id
            )
        revoked_or_rotating_api_credentials = rotating_creds_query.count()

        quota_denial_query = self.db.query(APIClientUsageWindow).filter(
            APIClientUsageWindow.window_start >= since,
            APIClientUsageWindow.denied_count > 0,
        )
        if tenant_id is not None:
            quota_denial_query = quota_denial_query.filter(
                APIClientUsageWindow.tenant_id == tenant_id
            )
        quota_denial_windows_24h = quota_denial_query.count()

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

    def get_integration_command_summary(self) -> IntegrationCommandSummary:
        return self._integration_command_summary(tenant_id=None)

    def get_integration_command_summary_for_tenant(
        self,
        tenant_id: uuid.UUID,
    ) -> IntegrationCommandSummary:
        return self._integration_command_summary(tenant_id=tenant_id)

    def get_growth_summary(
        self,
        tenant_id: uuid.UUID,
    ) -> FounderGrowthSummary:
        now = datetime.now(UTC)

        conversion_repo = self._repo("conversion_events")
        proposals_repo = self._repo("proposals")
        subscriptions_repo = self._repo("tenant_subscriptions")
        lead_scores_repo = self._repo("lead_scores")

        conversion_events_total = conversion_repo.count(tenant_id=tenant_id)

        proposals = proposals_repo.list(tenant_id=tenant_id, limit=10000, offset=0)
        proposals_total = len(proposals)
        proposals_pending = 0
        pending_pipeline_cents = 0
        for proposal in proposals:
            proposal_data = self._extract_data(proposal)
            status = self._safe_str(proposal_data.get("status")).lower()
            if status == "pending":
                proposals_pending += 1
                pending_pipeline_cents += max(
                    self._safe_int(
                        proposal_data.get("estimated_value_cents")
                        or proposal_data.get("proposal_value_cents")
                        or proposal_data.get("monthly_amount_cents")
                        or 89900
                    ),
                    0,
                )

        subscriptions = subscriptions_repo.list(tenant_id=tenant_id, limit=10000, offset=0)
        active_subscriptions = 0
        active_mrr_cents = 0
        for subscription in subscriptions:
            subscription_data = self._extract_data(subscription)
            if self._safe_str(subscription_data.get("status")).lower() != "active":
                continue
            active_subscriptions += 1
            active_mrr_cents += max(self._safe_int(subscription_data.get("monthly_amount_cents")), 0)

        proposal_to_paid_conversion_pct = round(
            (active_subscriptions / max(proposals_total, 1)) * 100,
            2,
        )
        pipeline_to_mrr_ratio = round(
            pending_pipeline_cents / max(active_mrr_cents, 1),
            2,
        )

        stage_rows = conversion_repo.aggregate_json_field(
            tenant_id=tenant_id,
            group_field="funnel_stage",
        )
        funnel_stage_counts = [
            GrowthSummaryMetric(key=str(row["group_key"]), value=self._safe_int(row["count"]))
            for row in sorted(stage_rows, key=lambda row: str(row["group_key"]))
        ]

        lead_tier_rows = lead_scores_repo.aggregate_json_field(
            tenant_id=tenant_id,
            group_field="tier",
        )
        lead_tier_distribution = [
            GrowthSummaryMetric(key=str(row["group_key"]), value=self._safe_int(row["count"]))
            for row in sorted(lead_tier_rows, key=lambda row: str(row["group_key"]))
        ]

        lead_score_rows = lead_scores_repo.list(tenant_id=tenant_id, limit=10000, offset=0)
        lead_score_bucket_counts: dict[str, int] = {
            "0-24": 0,
            "25-49": 0,
            "50-74": 0,
            "75-100": 0,
        }
        for lead in lead_score_rows:
            lead_data = self._extract_data(lead)
            score = max(0, min(100, self._safe_int(lead_data.get("score"))))
            lead_score_bucket_counts[self._bucket_for_lead_score(score)] += 1

        lead_score_buckets = [
            GrowthSummaryMetric(key=bucket, value=count)
            for bucket, count in lead_score_bucket_counts.items()
        ]

        return FounderGrowthSummary(
            generated_at=now,
            conversion_events_total=conversion_events_total,
            proposals_total=proposals_total,
            proposals_pending=proposals_pending,
            active_subscriptions=active_subscriptions,
            proposal_to_paid_conversion_pct=proposal_to_paid_conversion_pct,
            pending_pipeline_cents=pending_pipeline_cents,
            active_mrr_cents=active_mrr_cents,
            pipeline_to_mrr_ratio=pipeline_to_mrr_ratio,
            graph_mailbox_configured=self._graph_mailbox_is_configured(),
            funnel_stage_counts=funnel_stage_counts,
            lead_tier_distribution=lead_tier_distribution,
            lead_score_buckets=lead_score_buckets,
            integration_health=self.get_integration_command_summary_for_tenant(tenant_id),
        )

    def get_growth_setup_wizard(
        self,
        tenant_id: uuid.UUID,
    ) -> FounderGrowthSetupWizard:
        now = datetime.now(UTC)
        install_snapshots = self._connector_install_snapshots(tenant_id)
        success_map, failure_map, retry_map, secret_map = self._map_install_activity(tenant_id)
        graph_configured = self._graph_mailbox_is_configured()

        lead_scores_count = self._repo("lead_scores").count(tenant_id=tenant_id)
        conversion_events_count = self._repo("conversion_events").count(tenant_id=tenant_id)

        statuses: list[GrowthConnectionStatus] = []
        blocked_items: list[str] = []

        for definition in self._GROWTH_SERVICE_DEFINITIONS:
            service_key = str(definition["service_key"])
            label = str(definition["label"])
            required = bool(definition["required"])
            aliases = tuple(str(alias).lower() for alias in definition["aliases"])
            available_automations = list(definition["available_automations"])

            matched_snapshot = next(
                (
                    snapshot
                    for snapshot in install_snapshots
                    if any(alias in str(snapshot["match_text"]) for alias in aliases)
                ),
                None,
            )

            install_state = "NOT_CONNECTED"
            permissions_state = "missing"
            token_state = "missing"
            health_state = "not_connected"
            connected = False
            permission_errors: list[str] = []
            last_successful_activity: datetime | None = None
            last_failed_activity: datetime | None = None
            retry_count = 0
            blocking_reason: str | None = None

            if service_key == "lead_store":
                connected = lead_scores_count > 0 or conversion_events_count > 0
                install_state = "INTERNAL"
                permissions_state = "sufficient"
                token_state = "not_applicable"
                health_state = "healthy" if connected else "degraded"
                if not connected:
                    blocking_reason = "Lead store has no captured lead or conversion records yet"
            elif service_key == "microsoft365_outlook" and matched_snapshot is None and graph_configured:
                connected = True
                install_state = "GRAPH_CONFIGURED"
                permissions_state = "sufficient"
                token_state = "configured"
                health_state = "healthy"
            elif matched_snapshot is not None:
                install = matched_snapshot["install"]
                if not isinstance(install, TenantConnectorInstall):
                    raise AppError(
                        code="INTEGRITY_ERROR",
                        message="Connector install snapshot returned invalid install model",
                        status_code=500,
                    )

                install_state = install.install_state.value
                connected = install.install_state in {
                    ConnectorInstallState.ACTIVE,
                    ConnectorInstallState.VALIDATED,
                }
                if connected:
                    permissions_state = "sufficient"
                elif install.install_state == ConnectorInstallState.DEGRADED:
                    permissions_state = "degraded"
                elif install.install_state == ConnectorInstallState.DISABLED:
                    permissions_state = "revoked"
                else:
                    permissions_state = "insufficient"

                if install.disabled_reason:
                    permission_errors.append(str(install.disabled_reason))

                last_successful_activity = success_map.get(install.id)
                last_failed_activity = failure_map.get(install.id)
                retry_count = retry_map.get(install.id, 0)

                secret = secret_map.get(install.id)
                if secret is None:
                    token_state = "missing"
                elif secret.expires_at is not None and secret.expires_at <= now:
                    token_state = "expired"
                else:
                    token_state = "valid"

                health_state = "healthy"
                if install.install_state in {ConnectorInstallState.DEGRADED, ConnectorInstallState.DISABLED} or last_failed_activity and (
                    last_successful_activity is None or last_failed_activity > last_successful_activity
                ):
                    health_state = "degraded"
                elif retry_count > 0:
                    health_state = "warning"

                if not connected:
                    blocking_reason = f"{label} is {install_state.lower()}"

            if required and (not connected or permissions_state != "sufficient"):
                blocked_items.append(blocking_reason or f"{label} is not fully connected")

            statuses.append(
                GrowthConnectionStatus(
                    service_key=service_key,
                    label=label,
                    required=required,
                    connected=connected,
                    install_state=install_state,
                    permissions_state=permissions_state,
                    permission_errors=permission_errors,
                    token_state=token_state,
                    health_state=health_state,
                    last_successful_activity=last_successful_activity,
                    last_failed_activity=last_failed_activity,
                    retry_count=retry_count,
                    available_automations=available_automations,
                    blocking_reason=blocking_reason,
                )
            )

        return FounderGrowthSetupWizard(
            generated_at=now,
            autopilot_ready=len(blocked_items) == 0,
            blocked_items=blocked_items,
            services=statuses,
        )

    def start_launch_orchestrator(
        self,
        tenant_id: uuid.UUID,
        actor_user_id: uuid.UUID,
        mode: str,
        *,
        auto_queue_sync_jobs: bool,
    ) -> LaunchOrchestratorRunResponse:
        run_id = uuid.uuid4()
        now = datetime.now(UTC)
        wizard = self.get_growth_setup_wizard(tenant_id)

        blocked_items = list(wizard.blocked_items)
        status: str = "started"
        if mode == "autopilot" and blocked_items:
            status = "blocked"

        queued_sync_jobs = 0
        if status == "started" and auto_queue_sync_jobs:
            candidate_installs = list(
                self.db.execute(
                    select(TenantConnectorInstall)
                    .where(TenantConnectorInstall.tenant_id == tenant_id)
                    .where(
                        TenantConnectorInstall.install_state.in_(
                            [ConnectorInstallState.ACTIVE, ConnectorInstallState.VALIDATED]
                        )
                    )
                ).scalars().all()
            )
            for install in candidate_installs:
                existing_job = self.db.execute(
                    select(ConnectorSyncJob).where(
                        ConnectorSyncJob.tenant_id == tenant_id,
                        ConnectorSyncJob.tenant_connector_install_id == install.id,
                        ConnectorSyncJob.state.in_([SyncJobState.QUEUED, SyncJobState.RUNNING]),
                    )
                ).scalar_one_or_none()
                if existing_job is not None:
                    continue
                self.create_connector_sync_job(
                    tenant_id=tenant_id,
                    actor_user_id=actor_user_id,
                    tenant_connector_install_id=install.id,
                    direction="OUTBOUND",
                    state=SyncJobState.QUEUED.value,
                    records_attempted=0,
                    records_succeeded=0,
                    records_failed=0,
                    error_summary={
                        "trigger": "launch_orchestrator",
                        "mode": mode,
                        "run_id": str(run_id),
                    },
                )
                queued_sync_jobs += 1

        launch_event_repo = self._repo("platform_events")
        launch_event_repo.create(
            tenant_id=tenant_id,
            data={
                "event_type": "growth.launch_orchestrator.started",
                "run_id": str(run_id),
                "mode": mode,
                "status": status,
                "queued_sync_jobs": queued_sync_jobs,
                "blocked_items": blocked_items,
                "actor_user_id": str(actor_user_id),
                "generated_at": now.isoformat(),
            },
        )

        return LaunchOrchestratorRunResponse(
            run_id=run_id,
            mode=mode,
            queued_sync_jobs=queued_sync_jobs,
            blocked_items=blocked_items,
            status="blocked" if status == "blocked" else "started",
            generated_at=now,
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
