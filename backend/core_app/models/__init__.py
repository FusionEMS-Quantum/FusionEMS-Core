# Core Models
from . import (
    governance,  # noqa: F401  # ensure governance tables register with metadata
    growth_models,  # noqa: F401
    legal_requests,  # noqa: F401  # ensure legal request tables register with metadata
)
from .agency import (
    AgencyBillingPolicy,
    AgencyCollectionsPolicy,
    AgencyDebtSetoffPolicy,
    AgencyPaymentPlanPolicy,
    AgencyPublicSectorProfile,
    AgencyWriteoffPolicy,
)

# AI Platform Models
from .ai_platform import (
    AIApprovalEvent,
    AIApprovalRequirement,
    AIConfidenceRecord,
    AIContextSnapshot,
    AICopilotActionBoundary,
    AICopilotAuditEvent,
    AIDomainCopilot,
    AIDomainPolicy,
    AIExplanationRecord,
    AIFallbackDecision,
    AIGovernanceDecision,
    AIGuardrailRule,
    AIHumanOverrideEvent,
    AIModelBinding,
    AIOutputTag,
    AIPromptTemplate,
    AIProtectedAction,
    AIQueueItem,
    AIRejectionEvent,
    AIRestrictedOutputEvent,
    AIResumeEvent,
    AIReviewItem,
    AITenantSettings,
    AIUseCase,
    AIUseCaseAuditEvent,
    AIUseCaseVersion,
    AIUserFacingSummary,
    AIWorkflowFailure,
    AIWorkflowRun,
)

# Analytics Models
from .analytics import (
    ARAgingBucket,
    CashAtRiskSnapshot,
    ClinicalMetricSnapshot,
    ClinicalRiskTrendPoint,
    CoverageGapAggregate,
    CredentialRiskAggregate,
    DenialTrendAggregate,
    ExecutiveAlert,
    ExecutiveSummarySnapshot,
    FinancialMetricSnapshot,
    FleetReadinessAggregate,
    HealthScoreFactor,
    InventoryRiskAggregate,
    KPIComputationRun,
    KPITrendPoint,
    KPIValueSnapshot,
    MissionTimingAggregate,
    NarcoticsRiskAggregate,
    NemsisExportAggregate,
    OperationalMetricSnapshot,
    PagingPerformanceAggregate,
    PaymentLagAggregate,
    QAQueueAggregate,
    QueuePerformanceMetric,
    ReadinessMetricSnapshot,
    ReportArtifact,
    ReportAuditEvent,
    ReportDefinition,
    ReportDelivery,
    ReportFilterSet,
    ReportRun,
    ResponseTimeMetric,
    SubscriptionRevenueAggregate,
    SyncFailureAggregate,
    TelemetryUptimeAggregate,
    ValidationFailureAggregate,
)
from .audit_log import AuditLog
from .billing import (
    AppealReview,
    Claim,
    ClaimAuditEvent,
    ClaimIssue,
    ClaimState,
    CollectionsReview,
    HumanApprovalEvent,
    PatientBalanceLedger,
    PatientBalanceState,
    PaymentLinkEvent,
    ReminderEvent,
)

# ── CAD Models ────────────────────────────────────────────────────────────────
from .cad import (
    CADCall,
    CADCallPriority,
    CADCallState,
    CADTimelineEvent,
    CADUnit,
    CADUnitAssignment,
    CADUnitState,
    CADUnitStatusEvent,
)
from .communications import (
    AddressVerificationRecord,
    AgencyPhoneNumber,
    AIReplyDecision,
    CommunicationAuditEvent,
    CommunicationChannelStatus,
    CommunicationDeliveryEvent,
    CommunicationMessage,
    CommunicationPolicy,
    CommunicationTemplate,
    CommunicationThread,
    CommunicationThreadState,
    FaxDeliveryRecord,
    HumanTakeoverState,
    MailFulfillmentRecord,
    PatientCommunicationConsent,
    TelecomProvisioningRun,
)
from .contact_preference import (
    CommunicationOptOutEvent,
    ContactPolicyAuditEvent,
    ContactPreference,
    LanguagePreference,
)
from .crewlink import (
    AlertState,
    CrewMissionAssignment,
    CrewPagingAlert,
    CrewPagingAuditEvent,
    CrewPagingEscalationEvent,
    CrewPagingEscalationRule,
    CrewPagingRecipient,
    CrewPagingResponse,
    CrewPushDevice,
    CrewStatusEvent,
)

# Customer Success Platform Models
from .customer_success import (
    AccountHealthSnapshot,
    AdoptionMetric,
    CSImplementationProject,
    EnablementAuditEvent,
    ExpansionOpportunity,
    ExpansionReadinessSignal,
    HealthComputationLog,
    ImplementationMilestone,
    ImplementationRiskFlag,
    ImplementationTrainingLink,
    MilestoneUpdateLog,
    RenewalRiskSignal,
    StabilizationCheckpoint,
    StakeholderEngagementNote,
    SuccessAuditEvent,
    SuccessRiskFactor,
    SupportEscalation,
    SupportNote,
    SupportResolutionEvent,
    SupportSLAEvent,
    SupportStateTransition,
    SupportTicket,
    TrainingAssignment,
    TrainingCompletion,
    TrainingTrack,
    TrainingVerification,
    ValueMilestone,
    WorkflowAdoptionMetric,
)

# ZERO-ERROR DIRECTIVE Implementation Models
from .deployment import (
    DeploymentRun,
    DeploymentState,
    DeploymentStep,
    FailureAudit,
    ProvisioningAttempt,
    RetrySchedule,
    WebhookEventLog,
)
from .document_vault import (  # noqa: F401 — register vault tables with metadata
    DocumentRecord,
    DocumentVersion,
    ExportPackage,
    PackageManifestItem,
    SmartFolder,
    VaultAuditEntry,
    VaultDefinition,
    VaultRetentionPolicy,
)
from .facility import (
    Facility,
    FacilityAuditEvent,
    FacilityContact,
    FacilityFrictionFlag,
    FacilityRelationshipNote,
    FacilityServiceProfile,
)

# ── Fire / NERIS Models ──────────────────────────────────────────────────────
from .fire import (
    FireApparatusRecord,
    FireHydrant,
    FireIncident,
    FireInspection,
    FireInspectionStatus,
    FirePersonnelAssignment,
    FirePreplan,
    NERISExportJob,
    NERISExportState,
    NERISIncidentType,
)
from .fire_rms import InspectionViolation
from .founder_communications import (  # noqa: F401 — register founder comms tables
    BAATemplate,
    FounderAlertRecord,
    FounderAudioAlertConfig,
    FounderCallRecord,
    FounderCommunicationTemplate,
    FounderFaxRecord,
    FounderPrintMailRecord,
    FounderSMSThread,
    WisconsinDocTemplate,
)
from .incident import Incident
from .integration_connectors import (
    APIClientCredential,
    APIClientQuota,
    APIClientUsageWindow,
    APIKeyState,
    ConnectorCatalog,
    ConnectorInstallState,
    ConnectorProfile,
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
from .patient import Patient

# ── Terminology Service Models ───────────────────────────────────────────────
from .terminology import (
    TerminologyCodeSystem,
    TerminologyConcept,
    TerminologyDatasetVersion,
    TerminologyMapping,
    TerminologyRefreshSchedule,
    TerminologySynonym,
)

# Patient Identity + CRM Models
from .patient_identity import (
    PatientAlias,
    PatientDuplicateCandidate,
    PatientIdentifier,
    PatientMergeAuditEvent,
    PatientMergeRequest,
    PatientRelationshipFlag,
)

# Platform Core Models
from .platform_core import (
    AgencyContractLink,
    AgencyEnvironmentScope,
    AgencyImplementationOwner,
    AgencyLifecycleEvent,
    AgencyStatusAudit,
    AgencyType,
    ConfigDriftAlert,
    ConfigurationChangeAudit,
    ConfigurationValidationIssue,
    ConfigurationVersion,
    DeploymentRecord,
    DeploymentValidation,
    Environment,
    EnvironmentName,
    FeatureFlag,
    FeatureFlagAuditEvent,
    FeatureFlagState,
    GoLiveApproval,
    ImplementationAuditEvent,
    ImplementationBlocker,
    LaunchReadinessReview,
    ModuleActivationEvent,
    ModuleEntitlement,
    ReleaseAuditEvent,
    ReleaseState,
    ReleaseVersion,
    RollbackRecord,
    RolloutDecision,
    SystemConfiguration,
    TenantConfiguration,
    TenantFeatureState,
    TenantLifecycleState,
    UserAccessAuditEvent,
    UserAccessState,
    UserModuleVisibility,
    UserOrgMembership,
    UserProvisioningEvent,
    UserRoleAssignment,
)
from .platform_core import (
    ImplementationChecklistItem as PlatformChecklistItem,
)
from .platform_core import (
    ImplementationProject as PlatformImplementationProject,
)
from .platform_core import (
    ImplementationState as PlatformImplementationState,
)
from .pricing import (
    BillingInvoiceMirror,
    ContractOverride,
    Module,
    Price,
    PriceChangeAudit,
    Product,
    SubscriptionItem,
    SubscriptionPlan,
    UsageMeter,
)
from .records_media import (
    ChainOfCustodyEvent,
    ChainOfCustodyState,
    ClinicalRecord,
    CompliancePacket,
    DocumentArtifact,
    ExportDeliveryState,
    LegalHold,
    OCRConfidenceBand,
    OCRProcessingResult,
    QAException,
    QAExceptionState,
    RecordExport,
    RecordLifecycleState,
    RecordsAuditEvent,
    RecordSection,
    ReleaseAuthorization,
    SignatureCapture,
    SignatureState,
)
from .relationship_history import (
    FacilityWarningFlag,
    InternalAccountNote,
    PatientWarningFlag,
    RelationshipSummarySnapshot,
    RelationshipTimelineEvent,
)
from .responsible_party import (
    InsuranceSubscriberProfile,
    PatientResponsiblePartyLink,
    ResponsibilityAuditEvent,
    ResponsibleParty,
)

# ── Scheduling Models ─────────────────────────────────────────────────────────
from .scheduling import (
    AvailabilityBlock,
    CoverageRule,
    CredentialState,
    CrewCredential,
    FatigueAssessment,
    ShiftInstance,
    ShiftSwapRequest,
    ShiftSwapState,
    ShiftTemplate,
    TimeOffRequest,
)
from .specialty_ops import (
    AirAsset,
    DutyTimeFlag,
    FireOpsAuditEvent,
    FireOpsState,
    FlightLegEvent,
    FlightMission,
    FlightOpsAuditEvent,
    FlightOpsState,
    HazardFlag,
    HydrantReference,
    LandingZoneRecord,
    MissionFitScore,
    MissionPacket,
    MissionPacketAuditEvent,
    MissionPacketDelivery,
    MissionPacketSection,
    MissionPacketState,
    PremisePreplan,
    SpecialtyEquipmentCheck,
    SpecialtyMissionRequirement,
    SpecialtyTransportAuditEvent,
    SpecialtyTransportState,
    WaterSupplyNote,
)
from .state_debt_setoff import (
    AgencyDebtSetoffEnrollment,
    DebtSetoffEligibilityDecision,
    DebtSetoffExportBatch,
    DebtSetoffNoticeRecord,
    DebtSetoffRecoveryRecord,
    DebtSetoffResponseRecord,
    DebtSetoffReversalRecord,
    DebtSetoffRulePack,
    DebtSetoffSubmissionRecord,
    StateDebtSetoffProfile,
)
from .tenant import Tenant
from .user import User
from .vital import Vital
