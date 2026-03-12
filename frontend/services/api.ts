import axios from 'axios';

export const API = axios.create({
  baseURL:
    process.env.NEXT_PUBLIC_API_BASE ||
    process.env.NEXT_PUBLIC_BACKEND_URL ||
    process.env.NEXT_PUBLIC_API_URL ||
    "",
});

export async function getExecutiveSummary() {
  const res = await API.get('/api/founder/executive-summary', {
    headers: {
      Authorization: `Bearer ${localStorage.getItem('token')}`,
      'X-Tenant-ID': 'founder'
    }
  });
  return res.data;
}

type JsonObject = Record<string, unknown>;

type CADCallState =
  | 'NEW'
  | 'TRIAGED'
  | 'DISPATCHED'
  | 'ENROUTE'
  | 'ON_SCENE'
  | 'TRANSPORTING'
  | 'AT_HOSPITAL'
  | 'CLEARED'
  | 'CLOSED'
  | 'CANCELLED';

type EPCRChartStatus = 'DRAFT' | 'IN_PROGRESS' | 'PENDING_QA' | 'APPROVED' | 'LOCKED' | 'EXPORTED';

type PortalMessageDirection = 'inbound' | 'outbound';

export interface CADCallApi {
  id: string;
  call_number: string;
  state: CADCallState;
  priority: string;
  chief_complaint: string;
  address: string;
  location_address: string;
  call_received_at: string;
  caller_name: string;
  caller_phone: string;
  triage_notes: string;
  assigned_unit: string;
}

export interface CADUnitApi {
  id: string;
  unit_name: string;
  unit_type: string;
  state: string;
  station: string;
  lat: number | null;
  lng: number | null;
  readiness_score: number | null;
  active_call_id: string | null;
}

export interface EPCRChartApi {
  id: string;
  status: EPCRChartStatus;
  patient_first_name: string;
  patient_last_name: string;
  patient_dob: string;
  patient_gender: string;
  chief_complaint: string;
  dispatch_complaint: string;
  incident_date: string;
  unit_id: string;
  narrative: string;
  completeness_score?: number;
  created_at: string;
  updated_at: string;
}

export interface FirePreplanApi {
  id: string;
  name: string;
  address: string;
  occupancy_type: string | null;
  stories: number | null;
  sprinkler_system: boolean;
  standpipe: boolean;
  fire_alarm_system: boolean;
  construction_type: string | null;
  last_reviewed_at: string | null;
  notes: string | null;
  hazards: JsonObject;
}

export interface FireHydrantApi {
  id: string;
  hydrant_number: string;
  latitude: number;
  longitude: number;
  in_service: boolean;
  flow_rate_gpm: number | null;
  static_pressure_psi: number | null;
  hydrant_type: string | null;
  color_code: string | null;
  last_tested_at: string | null;
  notes: string | null;
}

export interface PortalMessageApi {
  id: string;
  subject: string;
  body: string;
  direction: PortalMessageDirection;
  created_at: string;
}

export interface TransportLinkRequestSummaryApi {
  id: string;
  data: {
    status:
    | 'draft'
    | 'submitted'
    | 'awaiting_signatures'
    | 'missing_documentation'
    | 'sent_to_cad'
    | 'scheduled'
    | 'accepted'
    | 'rejected'
    | 'cancelled';
    priority?: string;
    patient_name?: string;
    patient_first?: string;
    patient_last?: string;
    mrn?: string;
    csn?: string;
    origin_facility?: string;
    destination_facility?: string;
    service_level?: string;
    requested_service_level?: string;
    payer?: string;
    medical_necessity_status?: string;
    requested_pickup_time?: string;
    created_at?: string;
    submitted_at?: string;
  };
}

export interface TransportLinkDocumentFieldApi {
  key: string;
  label: string;
  raw_value: string;
  confidence: number;
  suggestion: string;
  confirmed: boolean;
  rejected: boolean;
  confirmed_value: string;
}

export interface TransportLinkDocumentAuditApi {
  ts: string;
  actor: string;
  action: string;
  detail?: string;
}

export interface TransportLinkDocumentApi {
  id: string;
  request_id: string | null;
  filename: string;
  doc_type: 'facesheet' | 'pcs' | 'aob' | 'abn' | 'other';
  ocr_status: string;
  s3_key: string;
  uploaded_at: string;
  fields: TransportLinkDocumentFieldApi[];
  audit: TransportLinkDocumentAuditApi[];
}

export interface TransportLinkUploadUrlApi {
  request_id: string;
  upload: {
    method: string;
    url: string;
    key?: string;
    expires_in?: number;
  };
  document_id: string;
}

export interface TransportLinkRecordApi {
  id: string;
  data: JsonObject;
  version?: number;
  created_at?: string;
  updated_at?: string;
}

function isJsonObject(value: unknown): value is JsonObject {
  return typeof value === 'object' && value !== null && !Array.isArray(value);
}

function asJsonObject(value: unknown): JsonObject {
  return isJsonObject(value) ? value : {};
}

function asString(value: unknown, fallback = ''): string {
  return typeof value === 'string' ? value : fallback;
}

function asNumber(value: unknown): number | null {
  if (typeof value === 'number' && Number.isFinite(value)) return value;
  if (typeof value === 'string' && value.trim().length > 0) {
    const parsed = Number(value);
    return Number.isFinite(parsed) ? parsed : null;
  }
  return null;
}

function asBoolean(value: unknown, fallback = false): boolean {
  if (typeof value === 'boolean') return value;
  if (typeof value === 'string') {
    const v = value.trim().toLowerCase();
    if (v === 'true' || v === '1' || v === 'yes') return true;
    if (v === 'false' || v === '0' || v === 'no') return false;
  }
  return fallback;
}

function asIsoDateString(value: unknown): string {
  if (typeof value === 'string' && value.trim().length > 0) return value;
  if (value instanceof Date) return value.toISOString();
  return new Date().toISOString();
}

function asErrorMessage(value: unknown, fallback: string): string {
  if (!axios.isAxiosError(value)) {
    return fallback;
  }
  const payload = asJsonObject(value.response?.data);
  const detail = asString(payload.detail || payload.error || payload.message, '');
  return detail || fallback;
}

const TRANSPORTLINK_ALLOWED_STATUSES: ReadonlySet<string> = new Set([
  'draft',
  'submitted',
  'awaiting_signatures',
  'missing_documentation',
  'sent_to_cad',
  'scheduled',
  'accepted',
  'rejected',
  'cancelled',
]);

function normalizeTransportLinkStatus(value: unknown): TransportLinkRequestSummaryApi['data']['status'] {
  const status = asString(value, 'draft').toLowerCase();
  if (TRANSPORTLINK_ALLOWED_STATUSES.has(status)) {
    return status as TransportLinkRequestSummaryApi['data']['status'];
  }
  return 'draft';
}

function normalizeTransportLinkSummary(value: unknown): TransportLinkRequestSummaryApi {
  const row = asJsonObject(value);
  const data = asJsonObject(row.data);
  const serviceLevel = asString(
    data.requested_service_level || data.service_level || row.requested_service_level || row.service_level,
    ''
  );
  return {
    id: asString(row.id || data.id),
    data: {
      status: normalizeTransportLinkStatus(data.status || row.status),
      priority: asString(data.priority || row.priority) || undefined,
      patient_name: asString(data.patient_name || row.patient_name) || undefined,
      patient_first: asString(data.patient_first || row.patient_first) || undefined,
      patient_last: asString(data.patient_last || row.patient_last) || undefined,
      mrn: asString(data.mrn || row.mrn) || undefined,
      csn: asString(data.csn || row.csn) || undefined,
      origin_facility: asString(data.origin_facility || row.origin_facility) || undefined,
      destination_facility: asString(data.destination_facility || row.destination_facility) || undefined,
      service_level: serviceLevel || undefined,
      requested_service_level: serviceLevel || undefined,
      payer: asString(data.payer || row.payer) || undefined,
      medical_necessity_status: asString(data.medical_necessity_status || row.medical_necessity_status) || undefined,
      requested_pickup_time: asString(data.requested_pickup_time || row.requested_pickup_time) || undefined,
      created_at: asString(data.created_at || row.created_at) || undefined,
      submitted_at: asString(data.submitted_at || row.submitted_at) || undefined,
    },
  };
}

function normalizeTransportLinkRecord(value: unknown): TransportLinkRecordApi {
  const row = asJsonObject(value);
  const data = asJsonObject(row.data);
  const version = asNumber(row.version);
  return {
    id: asString(row.id || data.id),
    data,
    version: version == null ? undefined : version,
    created_at: asString(row.created_at) || undefined,
    updated_at: asString(row.updated_at) || undefined,
  };
}

function normalizeTransportLinkField(value: unknown): TransportLinkDocumentFieldApi {
  const field = asJsonObject(value);
  return {
    key: asString(field.key),
    label: asString(field.label || field.key),
    raw_value: asString(field.raw_value),
    confidence: asNumber(field.confidence) ?? 0,
    suggestion: asString(field.suggestion || field.raw_value),
    confirmed: asBoolean(field.confirmed),
    rejected: asBoolean(field.rejected),
    confirmed_value: asString(field.confirmed_value),
  };
}

function normalizeTransportLinkAudit(value: unknown): TransportLinkDocumentAuditApi {
  const audit = asJsonObject(value);
  return {
    ts: asString(audit.ts || audit.created_at, new Date().toISOString()),
    actor: asString(audit.actor, 'System'),
    action: asString(audit.action, 'updated'),
    detail: asString(audit.detail) || undefined,
  };
}

function normalizeTransportLinkDocument(value: unknown): TransportLinkDocumentApi {
  const row = asJsonObject(value);
  const data = asJsonObject(row.data);
  const docTypeRaw = asString(data.doc_type || row.doc_type, 'other');
  const docType = ['facesheet', 'pcs', 'aob', 'abn', 'other'].includes(docTypeRaw)
    ? (docTypeRaw as TransportLinkDocumentApi['doc_type'])
    : 'other';

  const fieldsSource = Array.isArray(data.fields)
    ? data.fields
    : Array.isArray(row.fields)
      ? row.fields
      : [];

  const auditSource = Array.isArray(data.audit)
    ? data.audit
    : Array.isArray(row.audit)
      ? row.audit
      : [];

  return {
    id: asString(row.id || data.id),
    request_id: asString(data.request_id || row.request_id) || null,
    filename: asString(data.filename || row.filename),
    doc_type: docType,
    ocr_status: asString(data.ocr_status || row.ocr_status, 'idle'),
    s3_key: asString(data.s3_key || row.s3_key),
    uploaded_at: asString(data.uploaded_at || row.uploaded_at, new Date().toISOString()),
    fields: fieldsSource.map((field) => normalizeTransportLinkField(field)),
    audit: auditSource.map((entry) => normalizeTransportLinkAudit(entry)),
  };
}

function normalizeDominationRecord(value: unknown): JsonObject {
  const row = asJsonObject(value);
  const data = asJsonObject(row.data);
  const normalizedId = asString(row.id || data.id, '');
  return {
    ...row,
    ...data,
    id: normalizedId,
  };
}

function normalizeDominationList(payload: unknown, collectionKey?: string): JsonObject[] {
  if (Array.isArray(payload)) {
    return payload.map((item) => normalizeDominationRecord(item));
  }
  const root = asJsonObject(payload);
  if (collectionKey && Array.isArray(root[collectionKey])) {
    return (root[collectionKey] as unknown[]).map((item) => normalizeDominationRecord(item));
  }
  if (Array.isArray(root.items)) {
    return (root.items as unknown[]).map((item) => normalizeDominationRecord(item));
  }
  return [];
}

function normalizeCADCallState(value: unknown): CADCallState {
  const raw = asString(value, 'NEW').toUpperCase();
  switch (raw) {
    case 'NEW':
    case 'TRIAGED':
    case 'DISPATCHED':
    case 'ENROUTE':
    case 'ON_SCENE':
    case 'TRANSPORTING':
    case 'AT_HOSPITAL':
    case 'CLEARED':
    case 'CLOSED':
    case 'CANCELLED':
      return raw;
    default:
      return 'NEW';
  }
}

function normalizeEPCRStatus(value: unknown): EPCRChartStatus {
  const raw = asString(value, '').toLowerCase();
  switch (raw) {
    case 'chart_created':
    case 'draft':
      return 'DRAFT';
    case 'in_progress':
      return 'IN_PROGRESS';
    case 'pending_qa':
    case 'clinical_review_required':
    case 'ready_for_lock':
    case 'submitted':
      return 'PENDING_QA';
    case 'approved':
      return 'APPROVED';
    case 'locked':
      return 'LOCKED';
    case 'exported':
    case 'closed':
      return 'EXPORTED';
    default:
      return 'DRAFT';
  }
}

function normalizeEPCRChartRecord(value: unknown): EPCRChartApi {
  const rec = normalizeDominationRecord(value);
  const patient = asJsonObject(rec.patient);
  const dispatch = asJsonObject(rec.dispatch);
  const assessments = Array.isArray(rec.assessments) ? rec.assessments : [];
  const firstAssessment = assessments.length > 0 ? asJsonObject(assessments[0]) : {};

  const completenessRaw = asNumber(rec.completeness_score);
  const completenessScore = completenessRaw == null ? undefined : (completenessRaw > 1 ? completenessRaw / 100 : completenessRaw);

  return {
    ...rec as unknown as EPCRChartApi,
    id: asString(rec.id),
    status: normalizeEPCRStatus(rec.status || rec.chart_status),
    patient_first_name: asString(rec.patient_first_name || patient.first_name, ''),
    patient_last_name: asString(rec.patient_last_name || patient.last_name, ''),
    patient_dob: asString(rec.patient_dob || patient.dob, ''),
    patient_gender: asString(rec.patient_gender || patient.gender, ''),
    chief_complaint: asString(rec.chief_complaint || firstAssessment.chief_complaint || dispatch.complaint_reported, ''),
    dispatch_complaint: asString(rec.dispatch_complaint || dispatch.complaint_reported, ''),
    incident_date: asString(rec.incident_date || dispatch.psap_call_time, ''),
    unit_id: asString(rec.unit_id || dispatch.responding_unit, ''),
    narrative: asString(rec.narrative, ''),
    completeness_score: completenessScore,
    created_at: asIsoDateString(rec.created_at),
    updated_at: asIsoDateString(rec.updated_at || rec.created_at),
  };
}

// ── AI Platform ─────────────────────────────────────────────────────────────

function aiHeaders() {
  return {
    Authorization: `Bearer ${localStorage.getItem('token')}`,
  };
}

function transportLinkHeaders(): Record<string, string> {
  if (typeof window === 'undefined') {
    return {};
  }
  const qsToken = localStorage.getItem('qs_token') || '';
  if (!qsToken) {
    return {};
  }
  return { Authorization: `Bearer ${qsToken}` };
}

export async function getAICommandMetrics() {
  const res = await API.get('/api/v1/ai-platform/command-center/metrics', { headers: aiHeaders() });
  return res.data;
}

export async function getAIUseCases() {
  const res = await API.get('/api/v1/ai-platform/registry/use-cases', { headers: aiHeaders() });
  return res.data;
}

export async function getAIReviewQueue() {
  const res = await API.get('/api/v1/ai-platform/reviews', { headers: aiHeaders() });
  return res.data;
}

export async function approveAIReview(reviewId: string, notes?: string) {
  const res = await API.post(`/api/v1/ai-platform/reviews/${reviewId}/approve`, { notes: notes || '' }, { headers: aiHeaders() });
  return res.data;
}

export async function rejectAIReview(reviewId: string, reason: string) {
  const res = await API.post(`/api/v1/ai-platform/reviews/${reviewId}/reject`, { reason }, { headers: aiHeaders() });
  return res.data;
}

export async function getAIGuardrailRules() {
  const res = await API.get('/api/v1/ai-platform/governance/guardrails', { headers: aiHeaders() });
  return res.data;
}

export async function getAIProtectedActions() {
  const res = await API.get('/api/v1/ai-platform/governance/protected-actions', { headers: aiHeaders() });
  return res.data;
}

export async function getAIPromptTemplates() {
  const res = await API.get('/api/v1/ai-platform/prompt-templates', { headers: aiHeaders() });
  return res.data;
}

export async function createAIPromptTemplate(payload: { template_key: string; domain: string; system_prompt: string; user_prompt_template: string }) {
  const res = await API.post('/api/v1/ai-platform/prompt-templates', payload, { headers: aiHeaders() });
  return res.data;
}

export async function updateAIPromptTemplate(templateId: string, payload: { system_prompt?: string; user_prompt_template?: string; is_active?: boolean }) {
  const res = await API.patch(`/api/v1/ai-platform/prompt-templates/${templateId}`, payload, { headers: aiHeaders() });
  return res.data;
}

export async function getAITenantSettings() {
  const res = await API.get('/api/v1/ai-platform/settings', { headers: aiHeaders() });
  return res.data;
}

export async function updateAITenantSettings(payload: { ai_enabled?: boolean; environment_ai_toggle?: boolean; default_risk_tier?: string; max_concurrent_workflows?: number; auto_approve_low_risk?: boolean; require_human_review_high_risk?: boolean; global_confidence_threshold?: number }) {
  const res = await API.patch('/api/v1/ai-platform/settings', payload, { headers: aiHeaders() });
  return res.data;
}

export async function getAIUserFacingSummary(workflowId: string) {
  const res = await API.get(`/api/v1/ai-platform/workflows/${workflowId}/summary`, { headers: aiHeaders() });
  return res.data;
}

export async function seedAIPlatform() {
  const res = await API.post('/api/v1/ai-platform/seed', {}, { headers: aiHeaders() });
  return res.data;
}

// ── Founder Operations Command Center ──────────────────────────────────────

function opsHeaders() {
  return aiHeaders();
}

export async function getFounderOpsSummary() {
  const res = await API.get('/api/v1/founder/ops/summary', { headers: opsHeaders() });
  return res.data;
}
export async function getDeploymentIssues() {
  const res = await API.get('/api/v1/founder/ops/deployment-issues', { headers: opsHeaders() });
  return res.data;
}
export async function getPaymentFailures() {
  const res = await API.get('/api/v1/founder/ops/payment-failures', { headers: opsHeaders() });
  return res.data;
}
export async function getClaimsPipeline() {
  const res = await API.get('/api/v1/founder/ops/claims-pipeline', { headers: opsHeaders() });
  return res.data;
}
export async function getHighRiskDenials() {
  const res = await API.get('/api/v1/founder/ops/high-risk-denials', { headers: opsHeaders() });
  return res.data;
}
export async function getPatientBalances() {
  const res = await API.get('/api/v1/founder/ops/patient-balances', { headers: opsHeaders() });
  return res.data;
}
export async function getCollectionsReview() {
  const res = await API.get('/api/v1/founder/ops/collections-review', { headers: opsHeaders() });
  return res.data;
}
export async function getDebtSetoffReview() {
  const res = await API.get('/api/v1/founder/ops/debt-setoff', { headers: opsHeaders() });
  return res.data;
}
export async function getProfileGaps() {
  const res = await API.get('/api/v1/founder/ops/profile-gaps', { headers: opsHeaders() });
  return res.data;
}
export async function getCommsHealth() {
  const res = await API.get('/api/v1/founder/ops/comms-health', { headers: opsHeaders() });
  return res.data;
}
export async function getCrewlinkHealth() {
  const res = await API.get('/api/v1/founder/ops/crewlink-health', { headers: opsHeaders() });
  return res.data;
}
export async function getTopActions() {
  const res = await API.get('/api/v1/founder/ops/top-actions', { headers: opsHeaders() });
  return res.data;
}

// ── Customer Success Platform ──────────────────────────────────────────────

function csHeaders() {
  return aiHeaders();
}

export interface FounderDashboardApi {
  mrr_cents: number;
  tenant_count: number;
  error_count_1h: number;
  as_of: string;
}

export interface FounderComplianceStatusApi {
  nemsis?: { certified?: boolean; status?: string };
  neris?: { onboarded?: boolean; status?: string };
  compliance_packs?: { active_count?: number };
  overall?: string;
}

export interface BillingARAgingBucketApi {
  label: string;
  count: number;
  total_cents: number;
}

export interface BillingARAgingApi {
  as_of_date: string;
  total_ar_cents: number;
  total_claims: number;
  avg_days_in_ar: number;
  buckets: BillingARAgingBucketApi[];
  payer_breakdown: Record<string, { count: number; total_cents: number; avg_days: number }>;
}

export async function getFounderDashboardMetrics(): Promise<FounderDashboardApi> {
  const res = await API.get('/api/v1/founder/dashboard', { headers: csHeaders() });
  return res.data as FounderDashboardApi;
}

export async function getFounderComplianceStatus(): Promise<FounderComplianceStatusApi> {
  const res = await API.get('/api/v1/founder/compliance/status', { headers: csHeaders() });
  return res.data as FounderComplianceStatusApi;
}

export async function getBillingARAgingReport(): Promise<BillingARAgingApi> {
  const res = await API.get('/api/v1/billing/ar-aging', { headers: csHeaders() });
  return res.data as BillingARAgingApi;
}

// Founder Success Command Center
export async function getFounderSuccessSummary() {
  const res = await API.get('/api/v1/founder/success-command/summary', { headers: csHeaders() });
  return res.data;
}
export async function getStalledImplementations() {
  const res = await API.get('/api/v1/founder/success-command/stalled-implementations', { headers: csHeaders() });
  return res.data;
}
export async function getHighSeverityTickets() {
  const res = await API.get('/api/v1/founder/success-command/high-severity-tickets', { headers: csHeaders() });
  return res.data;
}
export async function getAtRiskAccounts() {
  const res = await API.get('/api/v1/founder/success-command/at-risk-accounts', { headers: csHeaders() });
  return res.data;
}
export async function getTrainingGaps() {
  const res = await API.get('/api/v1/founder/success-command/training-gaps', { headers: csHeaders() });
  return res.data;
}
export async function getLowAdoptionModules() {
  const res = await API.get('/api/v1/founder/success-command/low-adoption-modules', { headers: csHeaders() });
  return res.data;
}
export async function getExpansionReadiness() {
  const res = await API.get('/api/v1/founder/success-command/expansion-readiness', { headers: csHeaders() });
  return res.data;
}
export async function getImplementationHealth() {
  const res = await API.get('/api/v1/founder/success-command/implementation-health', { headers: csHeaders() });
  return res.data;
}
export async function getSupportQueueHealth() {
  const res = await API.get('/api/v1/founder/success-command/support-queue-health', { headers: csHeaders() });
  return res.data;
}
export async function getTrainingCompletion() {
  const res = await API.get('/api/v1/founder/success-command/training-completion', { headers: csHeaders() });
  return res.data;
}

// Founder Specialty / Records / Integration Command Centers
export async function getFounderSpecialtyOpsSummary() {
  const res = await API.get('/api/v1/founder/specialty-ops-command/summary', { headers: csHeaders() });
  return res.data;
}

export async function getFounderPendingFlightMissions(limit = 50) {
  const res = await API.get('/api/v1/founder/specialty-ops-command/pending-flight-missions', {
    headers: csHeaders(),
    params: { limit },
  });
  return res.data;
}

export async function getFounderRecordsCommandSummary() {
  const res = await API.get('/api/v1/founder/records-command/summary', { headers: csHeaders() });
  return res.data;
}

export async function getFounderFailedRecordExports(limit = 50) {
  const res = await API.get('/api/v1/founder/records-command/failed-exports', {
    headers: csHeaders(),
    params: { limit },
  });
  return res.data;
}

export async function getFounderIntegrationCommandSummary() {
  const res = await API.get('/api/v1/founder/integration-command/summary', { headers: csHeaders() });
  return res.data;
}

export async function getFounderGrowthSummary() {
  const res = await API.get('/api/v1/founder/integration-command/growth-summary', { headers: csHeaders() });
  return res.data;
}

export async function getFounderGrowthSetupWizard() {
  const res = await API.get('/api/v1/founder/integration-command/growth-setup-wizard', { headers: csHeaders() });
  return res.data;
}

export async function startFounderLaunchOrchestrator(payload?: {
  mode?: 'autopilot' | 'approval-first' | 'draft-only';
  auto_queue_sync_jobs?: boolean;
}) {
  const res = await API.post(
    '/api/v1/founder/integration-command/launch-orchestrator/start',
    {
      mode: payload?.mode ?? 'approval-first',
      auto_queue_sync_jobs: payload?.auto_queue_sync_jobs ?? true,
    },
    { headers: csHeaders() }
  );
  return res.data;
}

export async function getFounderFailedSyncJobs(limit = 50) {
  const res = await API.get('/api/v1/founder/integration-command/failed-sync-jobs', {
    headers: csHeaders(),
    params: { limit },
  });
  return res.data;
}

export async function createFounderSyncJob(payload: {
  tenant_connector_install_id: string;
  direction: 'INBOUND' | 'OUTBOUND';
  state?: 'QUEUED';
  records_attempted?: number;
  records_succeeded?: number;
  records_failed?: number;
  error_summary?: Record<string, unknown>;
}) {
  const res = await API.post('/api/v1/founder/integration-command/sync-jobs', payload, {
    headers: csHeaders(),
  });
  return res.data;
}

export async function addFounderSyncDeadLetter(
  syncJobId: string,
  payload: { external_record_ref: string; reason: string; payload?: Record<string, unknown> }
) {
  const res = await API.post(
    `/api/v1/founder/integration-command/sync-jobs/${syncJobId}/dead-letters`,
    payload,
    { headers: csHeaders() }
  );
  return res.data;
}

// Implementation Services
export async function listImplementations(state?: string) {
  const params = state ? `?state=${state}` : '';
  const res = await API.get(`/api/v1/customer-success/implementations${params}`, { headers: csHeaders() });
  return res.data;
}
export async function getImplementation(projectId: string) {
  const res = await API.get(`/api/v1/customer-success/implementations/${projectId}`, { headers: csHeaders() });
  return res.data;
}
export async function createImplementation(payload: Record<string, unknown>) {
  const res = await API.post('/api/v1/customer-success/implementations', payload, { headers: csHeaders() });
  return res.data;
}
export async function updateImplementation(projectId: string, payload: Record<string, unknown>) {
  const res = await API.patch(`/api/v1/customer-success/implementations/${projectId}`, payload, { headers: csHeaders() });
  return res.data;
}
export async function approveGoLive(projectId: string, approved: boolean, reason?: string) {
  const res = await API.post(`/api/v1/customer-success/implementations/${projectId}/go-live`, { approved, reason }, { headers: csHeaders() });
  return res.data;
}
export async function listMilestones(projectId: string) {
  const res = await API.get(`/api/v1/customer-success/implementations/${projectId}/milestones`, { headers: csHeaders() });
  return res.data;
}
export async function createMilestone(projectId: string, payload: Record<string, unknown>) {
  const res = await API.post(`/api/v1/customer-success/implementations/${projectId}/milestones`, payload, { headers: csHeaders() });
  return res.data;
}

// Support Operations
export async function listSupportTickets(status?: string, severity?: string) {
  const params = new URLSearchParams();
  if (status) params.append('status', status);
  if (severity) params.append('severity', severity);
  const q = params.toString() ? `?${params}` : '';
  const res = await API.get(`/api/v1/customer-success/support/tickets${q}`, { headers: csHeaders() });
  return res.data;
}
export async function getSupportTicket(ticketId: string) {
  const res = await API.get(`/api/v1/customer-success/support/tickets/${ticketId}`, { headers: csHeaders() });
  return res.data;
}
export async function createSupportTicket(payload: Record<string, unknown>) {
  const res = await API.post('/api/v1/customer-success/support/tickets', payload, { headers: csHeaders() });
  return res.data;
}
export async function transitionTicket(ticketId: string, newState: string, reason?: string) {
  const res = await API.post(`/api/v1/customer-success/support/tickets/${ticketId}/transition`, { new_state: newState, reason }, { headers: csHeaders() });
  return res.data;
}
export async function addTicketNote(ticketId: string, content: string, visibility?: string) {
  const res = await API.post(`/api/v1/customer-success/support/tickets/${ticketId}/notes`, { content, visibility: visibility || 'internal' }, { headers: csHeaders() });
  return res.data;
}
export async function escalateTicket(ticketId: string, reason: string, newSeverity?: string) {
  const res = await API.post(`/api/v1/customer-success/support/tickets/${ticketId}/escalate`, { reason, new_severity: newSeverity }, { headers: csHeaders() });
  return res.data;
}
export async function resolveTicket(ticketId: string, resolutionCode: string, summary: string) {
  const res = await API.post(`/api/v1/customer-success/support/tickets/${ticketId}/resolve`, { resolution_code: resolutionCode, summary }, { headers: csHeaders() });
  return res.data;
}

// Training & Enablement
export async function listTrainingTracks(role?: string) {
  const params = role ? `?role=${role}` : '';
  const res = await API.get(`/api/v1/customer-success/training/tracks${params}`, { headers: csHeaders() });
  return res.data;
}
export async function createTrainingTrack(payload: Record<string, unknown>) {
  const res = await API.post('/api/v1/customer-success/training/tracks', payload, { headers: csHeaders() });
  return res.data;
}
export async function listTrainingAssignments(userId?: string, status?: string) {
  const params = new URLSearchParams();
  if (userId) params.append('user_id', userId);
  if (status) params.append('status', status);
  const q = params.toString() ? `?${params}` : '';
  const res = await API.get(`/api/v1/customer-success/training/assignments${q}`, { headers: csHeaders() });
  return res.data;
}
export async function assignTraining(trackId: string, userId: string, dueDate?: string) {
  const res = await API.post('/api/v1/customer-success/training/assignments', { track_id: trackId, user_id: userId, due_date: dueDate }, { headers: csHeaders() });
  return res.data;
}
export async function recordTrainingCompletion(assignmentId: string, moduleKey: string, score?: number, evidence?: Record<string, unknown>) {
  const res = await API.post(`/api/v1/customer-success/training/assignments/${assignmentId}/completions`, { module_key: moduleKey, score, evidence }, { headers: csHeaders() });
  return res.data;
}

// Adoption & Health
export async function computeAccountHealth() {
  const res = await API.post('/api/v1/customer-success/health/compute', {}, { headers: csHeaders() });
  return res.data;
}
export async function getLatestHealth() {
  const res = await API.get('/api/v1/customer-success/health/latest', { headers: csHeaders() });
  return res.data;
}
export async function listAdoptionMetrics(moduleName?: string) {
  const params = moduleName ? `?module_name=${moduleName}` : '';
  const res = await API.get(`/api/v1/customer-success/adoption/metrics${params}`, { headers: csHeaders() });
  return res.data;
}
export async function listWorkflowAdoption() {
  const res = await API.get('/api/v1/customer-success/adoption/workflows', { headers: csHeaders() });
  return res.data;
}

// Renewal & Expansion
export async function listRenewalRisks() {
  const res = await API.get('/api/v1/customer-success/renewal/risks', { headers: csHeaders() });
  return res.data;
}
export async function listExpansionOpportunities(state?: string) {
  const params = state ? `?state=${state}` : '';
  const res = await API.get(`/api/v1/customer-success/expansion/opportunities${params}`, { headers: csHeaders() });
  return res.data;
}
export async function createExpansionOpportunity(payload: Record<string, unknown>) {
  const res = await API.post('/api/v1/customer-success/expansion/opportunities', payload, { headers: csHeaders() });
  return res.data;
}
export async function listStakeholderNotes() {
  const res = await API.get('/api/v1/customer-success/stakeholder-notes', { headers: csHeaders() });
  return res.data;
}
export async function addStakeholderNote(payload: Record<string, unknown>) {
  const res = await API.post('/api/v1/customer-success/stakeholder-notes', payload, { headers: csHeaders() });
  return res.data;
}
export async function listValueMilestones() {
  const res = await API.get('/api/v1/customer-success/value-milestones', { headers: csHeaders() });
  return res.data;
}
export async function createValueMilestone(payload: Record<string, unknown>) {
  const res = await API.post('/api/v1/customer-success/value-milestones', payload, { headers: csHeaders() });
  return res.data;
}

// ── Platform Core Administration ───────────────────────────────────────────

function platformHeaders() {
  return aiHeaders();
}

// Tenant Lifecycle
export interface PlatformAgencyApi {
  id: string;
  name: string;
  lifecycle_state: string;
  agency_type: string;
  created_at: string;
}

export async function listPlatformAgencies(): Promise<PlatformAgencyApi[]> {
  const res = await API.get('/api/v1/platform/agencies', { headers: platformHeaders() });
  return res.data as PlatformAgencyApi[];
}

export async function platformTransitionLifecycle(tenantId: string, payload: { new_state: string; reason: string }) {
  const res = await API.post(`/api/v1/platform/agencies/${tenantId}/lifecycle/transition`, payload, { headers: platformHeaders() });
  return res.data;
}
export async function listLifecycleEvents(tenantId: string) {
  const res = await API.get(`/api/v1/platform/agencies/${tenantId}/lifecycle/events`, { headers: platformHeaders() });
  return res.data;
}

// Implementation
export async function listPlatformImplementations(state?: string) {
  const params = state ? `?state=${state}` : '';
  const res = await API.get(`/api/v1/platform/implementations${params}`, { headers: platformHeaders() });
  return res.data;
}
export async function getPlatformImplementation(projectId: string) {
  const res = await API.get(`/api/v1/platform/implementations/${projectId}`, { headers: platformHeaders() });
  return res.data;
}
export async function createPlatformImplementation(payload: Record<string, unknown>) {
  const res = await API.post('/api/v1/platform/implementations', payload, { headers: platformHeaders() });
  return res.data;
}
export async function listPlatformBlockers(projectId: string) {
  const res = await API.get(`/api/v1/platform/implementations/${projectId}/blockers`, { headers: platformHeaders() });
  return res.data;
}

// Feature Flags
export async function listPlatformFeatureFlags() {
  const res = await API.get('/api/v1/platform/feature-flags', { headers: platformHeaders() });
  return res.data;
}
export async function createPlatformFeatureFlag(payload: Record<string, unknown>) {
  const res = await API.post('/api/v1/platform/feature-flags', payload, { headers: platformHeaders() });
  return res.data;
}
export async function listTenantFeatureStates(tenantId: string) {
  const res = await API.get(`/api/v1/platform/feature-flags/tenant/${tenantId}`, { headers: platformHeaders() });
  return res.data;
}
export async function setTenantFeatureState(payload: { tenant_id: string; feature_flag_id: string; new_state: string; reason: string }) {
  const res = await API.post('/api/v1/platform/feature-flags/tenant-state', payload, { headers: platformHeaders() });
  return res.data;
}

// Environments & Releases
export async function listPlatformEnvironments() {
  const res = await API.get('/api/v1/platform/environments', { headers: platformHeaders() });
  return res.data;
}
export async function listPlatformReleases() {
  const res = await API.get('/api/v1/platform/releases', { headers: platformHeaders() });
  return res.data;
}
export async function createPlatformRelease(payload: Record<string, unknown>) {
  const res = await API.post('/api/v1/platform/releases', payload, { headers: platformHeaders() });
  return res.data;
}
export async function listConfigDriftAlerts() {
  const res = await API.get('/api/v1/platform/config-drift-alerts', { headers: platformHeaders() });
  return res.data;
}

// System Configuration
export async function listTenantConfigurations(tenantId: string) {
  const res = await API.get(`/api/v1/platform/configuration/tenant/${tenantId}`, { headers: platformHeaders() });
  return res.data;
}
export async function setTenantConfiguration(payload: { tenant_id: string; config_key: string; config_value: string; description?: string }) {
  const res = await API.post('/api/v1/platform/configuration/tenant', payload, { headers: platformHeaders() });
  return res.data;
}
export async function listSystemConfigurations() {
  const res = await API.get('/api/v1/platform/configuration/system', { headers: platformHeaders() });
  return res.data;
}
export async function getConfigCompleteness(tenantId: string) {
  const res = await API.get(`/api/v1/platform/configuration/tenant/${tenantId}/completeness`, { headers: platformHeaders() });
  return res.data;
}

// Founder Command Center
export async function getPlatformCommandCenter() {
  const res = await API.get('/api/v1/platform/founder/command-center', { headers: platformHeaders() });
  return res.data;
}

// AI Platform Diagnostics
export async function getPlatformAIDiagnosis() {
  const res = await API.get('/api/v1/platform/ai/diagnose', { headers: platformHeaders() });
  return res.data;
}
export async function getTenantAIDiagnosis(tenantId: string) {
  const res = await API.get(`/api/v1/platform/ai/diagnose/${tenantId}`, { headers: platformHeaders() });
  return res.data;
}

export async function getPlatformHealth() {
  const res = await API.get('/api/v1/platform/health', { headers: platformHeaders() });
  return res.data;
}

export async function listPlatformIncidents(activeOnly = true) {
  const res = await API.get('/api/v1/platform/incidents', {
    headers: platformHeaders(),
    params: { active_only: activeOnly },
  });
  return res.data;
}

export async function getTechAssistantIssues(payload: {
  snapshot: Record<string, unknown>;
  incidents?: Array<Record<string, unknown>>;
  top_n?: number;
}) {
  const res = await API.post('/api/v1/tech_copilot/assistant/explain', payload, { headers: platformHeaders() });
  return res.data;
}
// ==========================================
// QUANTUM FOUNDER / TAX SHIELD APIs
// ==========================================
export async function getQuantumStrategies() {
  const res = await API.get('/api/quantum-founder/strategies/domination');
  return res.data;
}

export async function getQuantumVaultUploadUrl(fileName: string, entityBucket: string, docType: string) {
  const res = await API.get('/api/quantum-founder/vault/upload-url', {
    params: { file_name: fileName, bucket: entityBucket, doc_type: docType }
  });
  return res.data;
}

export async function uploadQuantumCSV(file: File) {
  const formData = new FormData();
  formData.append('csv_file', file);
  const res = await API.post('/api/quantum-founder/imports/csv', formData, {
    headers: { 'Content-Type': 'multipart/form-data' }
  });
  return res.data;
}

export async function getQuantumVaultDocuments() {
  const res = await API.get('/api/quantum-founder/vault/documents');
  return res.data;
}

function getAbsoluteApiBaseUrl(): string {
  const configuredBase = API.defaults.baseURL;
  if (typeof configuredBase === 'string' && configuredBase.trim().length > 0) {
    return configuredBase;
  }
  return (
    process.env.NEXT_PUBLIC_API_URL ||
    process.env.NEXT_PUBLIC_BACKEND_URL ||
    process.env.NEXT_PUBLIC_API_BASE ||
    'http://localhost:8000'
  );
}

export function getQuantumEfileRealtimeStatusStreamUrl(): string {
  return `${getAbsoluteApiBaseUrl()}/api/quantum-founder/efile/realtime-status`;
}

export function getQuantumVaultRenderUrl(documentId: string): string {
  return `${getAbsoluteApiBaseUrl()}/api/quantum-founder/vault/render/${encodeURIComponent(documentId)}`;
}

function roiHeaders(): Record<string, string> {
  if (typeof window === 'undefined') {
    return {};
  }
  const token = localStorage.getItem('token');
  return token ? { Authorization: `Bearer ${token}` } : {};
}

export interface ROIFunnelStage {
  stage: string;
  count: number;
}

export interface ROIFunnelConversionResponse {
  funnel: ROIFunnelStage[];
  total_events: number;
}

export interface ROIFunnelConversionKpisResponse {
  total_events: number;
  total_proposals: number;
  active_subscriptions: number;
  proposal_to_paid_conversion_pct: number;
  as_of: string;
}

export interface ROIFunnelRevenuePipelineResponse {
  pending_pipeline_cents: number;
  active_mrr_cents: number;
  pipeline_to_mrr_ratio: number;
  as_of: string;
}

export interface ROIFunnelProposalRecord {
  id: string;
  data?: {
    agency_name?: string;
    contact_name?: string;
    contact_email?: string;
    status?: string;
    created_at?: string;
    expiration_days?: number;
    roi_scenario_id?: string;
  };
  created_at?: string;
}

export interface ROIFunnelProposalsResponse {
  proposals: ROIFunnelProposalRecord[];
  total: number;
}

export interface ROIFunnelCreateProposalPayload {
  roi_scenario_id: string;
  agency_name: string;
  contact_name: string;
  contact_email: string;
  expiration_days: number;
  include_modules: string[];
}

export interface ROIFunnelPricingSimulationRequest {
  base_plan: string;
  modules: string[];
  call_volume: number;
  contract_length_months: number;
}

export interface ROIFunnelPricingSimulationResponse {
  plan: string;
  modules: string[];
  monthly_cents: number;
  annual_cents: number;
  annual_savings_pct: number;
  cost_per_transport: number | null;
}

export async function getROIFunnelConversionFunnel(): Promise<ROIFunnelConversionResponse> {
  const res = await API.get('/api/v1/roi-funnel/conversion-funnel', { headers: roiHeaders() });
  return res.data as ROIFunnelConversionResponse;
}

export async function getROIFunnelConversionKpis(): Promise<ROIFunnelConversionKpisResponse> {
  const res = await API.get('/api/v1/roi-funnel/conversion-kpis', { headers: roiHeaders() });
  return res.data as ROIFunnelConversionKpisResponse;
}

export async function getROIFunnelRevenuePipeline(): Promise<ROIFunnelRevenuePipelineResponse> {
  const res = await API.get('/api/v1/roi-funnel/revenue-pipeline', { headers: roiHeaders() });
  return res.data as ROIFunnelRevenuePipelineResponse;
}

export async function getROIFunnelProposals(): Promise<ROIFunnelProposalsResponse> {
  const res = await API.get('/api/v1/roi-funnel/proposals', { headers: roiHeaders() });
  return res.data as ROIFunnelProposalsResponse;
}

export async function createROIFunnelProposal(
  payload: ROIFunnelCreateProposalPayload,
): Promise<Record<string, unknown>> {
  const res = await API.post('/api/v1/roi-funnel/proposal', payload, {
    headers: {
      ...roiHeaders(),
      'Content-Type': 'application/json',
    },
  });
  return res.data as Record<string, unknown>;
}

export async function createROIFunnelPricingSimulation(
  payload: ROIFunnelPricingSimulationRequest,
): Promise<ROIFunnelPricingSimulationResponse> {
  const res = await API.post('/api/v1/roi-funnel/pricing-simulation', payload, {
    headers: {
      ...roiHeaders(),
      'Content-Type': 'application/json',
    },
  });
  return res.data as ROIFunnelPricingSimulationResponse;
}

// ── Standalone Page API Wrappers (No Fetch Bypass) ───────────────────────

export interface StandaloneTemplateDataApi {
  name: string;
  category: string;
  format: string;
  status: string;
  language: string;
  tags: string[];
  is_locked: boolean;
  security_classification: string;
  version: number;
  variables: string[];
}

export interface StandaloneTemplateApi {
  id: string;
  data: StandaloneTemplateDataApi;
  created_at: string;
}

export interface StandaloneTemplatesResponse {
  templates: StandaloneTemplateApi[];
}

export interface StandaloneTemplateTopPerformerApi {
  template_id: string;
  render_count: number;
}

export interface StandaloneTemplateTopPerformingResponse {
  top_templates: StandaloneTemplateTopPerformerApi[];
}

export interface StandaloneTemplateCreatePayload {
  name: string;
  category: string;
  format: string;
  content: string;
}

export async function getStandaloneTemplates(category?: string | null): Promise<StandaloneTemplatesResponse> {
  const res = await API.get('/api/v1/templates', {
    params: category ? { category } : undefined,
  });
  const payload = asJsonObject(res.data);
  return {
    templates: Array.isArray(payload.templates) ? (payload.templates as StandaloneTemplateApi[]) : [],
  };
}

export async function getStandaloneTemplateLifecycleManagement(): Promise<Record<string, number>> {
  const res = await API.get('/api/v1/templates/lifecycle/management');
  const payload = asJsonObject(res.data);
  const normalized: Record<string, number> = {};
  Object.entries(payload).forEach(([key, value]) => {
    normalized[key] = asNumber(value) ?? 0;
  });
  return normalized;
}

export async function getStandaloneTemplateTopPerforming(): Promise<StandaloneTemplateTopPerformingResponse> {
  const res = await API.get('/api/v1/templates/analytics/top-performing');
  const payload = asJsonObject(res.data);
  return {
    top_templates: Array.isArray(payload.top_templates)
      ? (payload.top_templates as StandaloneTemplateTopPerformerApi[])
      : [],
  };
}

export async function createStandaloneTemplate(payload: StandaloneTemplateCreatePayload): Promise<Record<string, unknown>> {
  const res = await API.post('/api/v1/templates', payload, {
    headers: { 'Content-Type': 'application/json' },
  });
  return asJsonObject(res.data);
}

export async function approveStandaloneTemplate(templateId: string): Promise<Record<string, unknown>> {
  const res = await API.post(
    `/api/v1/templates/${templateId}/approve`,
    { template_id: templateId, action: 'approve' },
    { headers: { 'Content-Type': 'application/json' } }
  );
  return asJsonObject(res.data);
}

export async function deleteStandaloneTemplate(templateId: string): Promise<Record<string, unknown>> {
  const res = await API.delete(`/api/v1/templates/${templateId}`);
  return asJsonObject(res.data);
}

export async function getStandaloneMobileOpsPwaDeployments(): Promise<Record<string, unknown>> {
  const res = await API.get('/api/v1/mobile-ops/pwa/deployments');
  return asJsonObject(res.data);
}

export async function getStandaloneMobileOpsDevices(): Promise<Record<string, unknown>> {
  const res = await API.get('/api/v1/mobile-ops/devices');
  return asJsonObject(res.data);
}

export async function getStandaloneMobileOpsVersionAdoption(): Promise<Record<string, unknown>> {
  const res = await API.get('/api/v1/mobile-ops/pwa/version-adoption');
  return asJsonObject(res.data);
}

export async function getStandaloneMobileOpsSyncHealth(): Promise<Record<string, unknown>> {
  const res = await API.get('/api/v1/mobile-ops/sync/health');
  return asJsonObject(res.data);
}

export async function getStandaloneMobileOpsPushAnalytics(): Promise<Record<string, unknown>> {
  const res = await API.get('/api/v1/mobile-ops/push/analytics');
  return asJsonObject(res.data);
}

export async function getStandaloneMobileOpsAdoptionKpis(): Promise<Record<string, unknown>> {
  const res = await API.get('/api/v1/mobile-ops/adoption/kpis');
  return asJsonObject(res.data);
}

export async function getStandaloneMobileOpsCredentialCompliance(): Promise<Record<string, unknown>> {
  const res = await API.get('/api/v1/mobile-ops/credentials/compliance');
  return asJsonObject(res.data);
}

export async function getStandaloneMobileOpsStaffingShortagePredictor(): Promise<Record<string, unknown>> {
  const res = await API.get('/api/v1/mobile-ops/staffing/shortage-predictor');
  return asJsonObject(res.data);
}

export interface ROIFunnelEstimatePayload {
  zip_code: string;
  call_volume: number;
  current_billing_pct: number;
  years: number;
}

export async function getStandaloneROIFunnelConversionFunnel(): Promise<ROIFunnelConversionResponse> {
  const res = await API.get('/api/v1/roi-funnel/conversion-funnel');
  return res.data as ROIFunnelConversionResponse;
}

export async function getStandaloneROIFunnelConversionKpis(): Promise<ROIFunnelConversionKpisResponse> {
  const res = await API.get('/api/v1/roi-funnel/conversion-kpis');
  return res.data as ROIFunnelConversionKpisResponse;
}

export async function getStandaloneROIFunnelRevenuePipeline(): Promise<ROIFunnelRevenuePipelineResponse> {
  const res = await API.get('/api/v1/roi-funnel/revenue-pipeline');
  return res.data as ROIFunnelRevenuePipelineResponse;
}

export async function createStandaloneROIFunnelEstimate(payload: ROIFunnelEstimatePayload): Promise<Record<string, unknown>> {
  const res = await API.post('/api/v1/roi-funnel/roi-estimate', payload, {
    headers: { 'Content-Type': 'application/json' },
  });
  return asJsonObject(res.data);
}

export interface StandaloneSystemHealthAlertsResponse {
  alerts?: Array<Record<string, unknown>>;
  total?: number;
}

export async function getStandaloneSystemHealthDashboard(): Promise<Record<string, unknown>> {
  const res = await API.get('/api/v1/system-health/dashboard');
  return asJsonObject(res.data);
}

export async function getStandaloneSystemHealthServices(): Promise<Record<string, unknown>[]> {
  const res = await API.get('/api/v1/system-health/services');
  const payload = asJsonObject(res.data);
  return Array.isArray(payload.services) ? (payload.services as Record<string, unknown>[]) : [];
}

export async function getStandaloneSystemHealthAlerts(): Promise<StandaloneSystemHealthAlertsResponse> {
  const res = await API.get('/api/v1/system-health/alerts');
  const payload = asJsonObject(res.data);
  return {
    alerts: Array.isArray(payload.alerts) ? (payload.alerts as Array<Record<string, unknown>>) : [],
    total: asNumber(payload.total) ?? 0,
  };
}

export async function getStandaloneSystemHealthUptimeSla(): Promise<Record<string, unknown>> {
  const res = await API.get('/api/v1/system-health/uptime/sla');
  return asJsonObject(res.data);
}

export async function getStandaloneSystemHealthResilienceScore(): Promise<Record<string, unknown>> {
  const res = await API.get('/api/v1/system-health/resilience-score');
  return asJsonObject(res.data);
}

export async function getStandaloneSystemHealthSslExpiration(): Promise<Record<string, unknown>> {
  const res = await API.get('/api/v1/system-health/ssl/expiration');
  return asJsonObject(res.data);
}

export async function getStandaloneSystemHealthBackupsStatus(): Promise<Record<string, unknown>> {
  const res = await API.get('/api/v1/system-health/backups/status');
  return asJsonObject(res.data);
}

export async function getStandaloneSystemHealthMonitoringCoverage(): Promise<Record<string, unknown>> {
  const res = await API.get('/api/v1/system-health/monitoring/coverage');
  return asJsonObject(res.data);
}

export async function resolveStandaloneSystemHealthAlert(alertId: string): Promise<Record<string, unknown>> {
  const res = await API.post(`/api/v1/system-health/alerts/${alertId}/resolve`);
  return asJsonObject(res.data);
}

function nemsisManagerHeaders(): Record<string, string> {
  if (typeof window === 'undefined') {
    return { 'Content-Type': 'application/json' };
  }
  const token = localStorage.getItem('access_token') || '';
  return {
    'Content-Type': 'application/json',
    Authorization: `Bearer ${token}`,
  };
}

async function requestStandaloneNemsisManager<T>(
  path: string,
  method: 'GET' | 'POST' = 'GET',
  body?: unknown,
): Promise<T> {
  const res = await API.request<T>({
    url: path,
    method,
    headers: nemsisManagerHeaders(),
    data: body,
  });
  return res.data;
}

export function getStandaloneNemsisManagerSchema() {
  return requestStandaloneNemsisManager<Record<string, unknown>>('/api/v1/nemsis-manager/schema');
}

export function getStandaloneNemsisManagerSchemaHierarchy() {
  return requestStandaloneNemsisManager<Record<string, unknown>>('/api/v1/nemsis-manager/schema/hierarchy');
}

export function getStandaloneNemsisManagerExportDashboard() {
  return requestStandaloneNemsisManager<Record<string, unknown>>('/api/v1/nemsis-manager/export/dashboard');
}

export function getStandaloneNemsisManagerCertificationReadiness() {
  return requestStandaloneNemsisManager<Record<string, unknown>>('/api/v1/nemsis-manager/certification-readiness');
}

export function getStandaloneNemsisManagerIntegrityScore() {
  return requestStandaloneNemsisManager<Record<string, unknown>>('/api/v1/nemsis-manager/integrity-score');
}

export function getStandaloneNemsisManagerSchemaDiff() {
  return requestStandaloneNemsisManager<Record<string, unknown>>('/api/v1/nemsis-manager/schema/diff');
}

export function postStandaloneNemsisManagerUpgradeImpact(payload: {
  from_version: string;
  to_version: string;
}) {
  return requestStandaloneNemsisManager<Record<string, unknown>>('/api/v1/nemsis-manager/upgrade-impact', 'POST', payload);
}

export function listStandaloneNemsisManagerExportBatches() {
  return requestStandaloneNemsisManager<unknown[]>('/api/v1/nemsis-manager/export/batches');
}

export function listStandaloneNemsisManagerStateRejections() {
  return requestStandaloneNemsisManager<unknown[]>('/api/v1/nemsis-manager/state-rejections');
}

export function listStandaloneNemsisManagerAuditLog() {
  return requestStandaloneNemsisManager<unknown[]>('/api/v1/nemsis-manager/audit-log');
}

export function postStandaloneNemsisManagerReadinessScore(payload: {
  provided_elements: string[];
  state_code: string;
}) {
  return requestStandaloneNemsisManager<Record<string, unknown>>('/api/v1/nemsis-manager/readiness-score', 'POST', payload);
}

export function postStandaloneNemsisManagerValidateLive(payload: { provided_elements: string[] }) {
  return requestStandaloneNemsisManager<Record<string, unknown>>('/api/v1/nemsis-manager/validate/live', 'POST', payload);
}

export function postStandaloneNemsisManagerValidateNarrative(payload: { narrative: string }) {
  return requestStandaloneNemsisManager<Record<string, unknown>>('/api/v1/nemsis-manager/validate/narrative', 'POST', payload);
}

export function postStandaloneNemsisManagerValidateMedicalNecessity(payload: { narrative: string }) {
  return requestStandaloneNemsisManager<Record<string, unknown>>('/api/v1/nemsis-manager/validate/medical-necessity', 'POST', payload);
}

export function postStandaloneNemsisManagerCodingSuggest(payload: { narrative: string }) {
  return requestStandaloneNemsisManager<Record<string, unknown>>('/api/v1/nemsis-manager/coding-suggest', 'POST', payload);
}

export function postStandaloneNemsisManagerValidateField(payload: {
  element_id: string;
  value: string;
}) {
  return requestStandaloneNemsisManager<Record<string, unknown>>('/api/v1/nemsis-manager/validate/field', 'POST', payload);
}

export function postStandaloneNemsisManagerAutoPopulate(payload: { incident: Record<string, unknown> }) {
  return requestStandaloneNemsisManager<Record<string, unknown>>('/api/v1/nemsis-manager/auto-populate', 'POST', payload);
}

export function postStandaloneNemsisManagerNormalize(payload: { record: Record<string, unknown> }) {
  return requestStandaloneNemsisManager<Record<string, unknown>>('/api/v1/nemsis-manager/normalize', 'POST', payload);
}

export function postStandaloneNemsisManagerExportSimulate(payload: {
  incident: Record<string, string>;
  patient: Record<string, unknown>;
}) {
  return requestStandaloneNemsisManager<Record<string, unknown>>('/api/v1/nemsis-manager/export/simulate', 'POST', payload);
}

export function postStandaloneNemsisManagerReportableFlag(payload: { incident: Record<string, unknown> }) {
  return requestStandaloneNemsisManager<Record<string, unknown>>('/api/v1/nemsis-manager/reportable-flag', 'POST', payload);
}

export async function getStandaloneBillingCommandDashboard(): Promise<Record<string, unknown>> {
  const res = await API.get('/api/v1/billing-command/dashboard');
  return asJsonObject(res.data);
}

export async function getStandaloneBillingCommandBillingHealth(): Promise<Record<string, unknown>> {
  const res = await API.get('/api/v1/billing-command/billing-health');
  return asJsonObject(res.data);
}

export async function getStandaloneBillingCommandPayerPerformance(): Promise<Record<string, unknown>> {
  const res = await API.get('/api/v1/billing-command/payer-performance');
  return asJsonObject(res.data);
}

export async function getStandaloneBillingCommandRevenueLeakage(): Promise<Record<string, unknown>> {
  const res = await API.get('/api/v1/billing-command/revenue-leakage');
  return asJsonObject(res.data);
}

export async function getStandaloneBillingCommandArConcentrationRisk(): Promise<Record<string, unknown>> {
  const res = await API.get('/api/v1/billing-command/ar-concentration-risk');
  return asJsonObject(res.data);
}

export async function getStandaloneBillingCommandExecutiveSummary(): Promise<Record<string, unknown>> {
  const res = await API.get('/api/v1/billing-command/executive-summary');
  return asJsonObject(res.data);
}

export async function getStandaloneBillingCommandDenialHeatmap(): Promise<Record<string, unknown>> {
  const res = await API.get('/api/v1/billing-command/denial-heatmap');
  return asJsonObject(res.data);
}

function standaloneBillingDashboardHeaders(): Record<string, string> {
  if (typeof window === 'undefined') {
    return {};
  }
  const token = localStorage.getItem('token');
  return token ? { Authorization: `Bearer ${token}` } : {};
}

export interface StandaloneBillingDashboardKpisResponse {
  clean_claim_rate?: number;
  denial_rate?: number;
  total_claims?: number;
  total_revenue_cents?: number;
  avg_days_in_ar?: number;
  net_collection_rate?: number;
}

export interface StandaloneBillingDashboardExecutiveSummaryResponse {
  mrr_cents?: number;
  total_revenue_cents?: number;
}

export interface StandaloneBillingDashboardArBucketResponse {
  label: string;
  count: number;
  total_cents: number;
}

export interface StandaloneBillingDashboardArAgingResponse {
  buckets: StandaloneBillingDashboardArBucketResponse[];
  total_ar_cents?: number;
  total_claims?: number;
  avg_days_in_ar?: number;
}

export interface StandaloneBillingDashboardPayerRowResponse {
  payer: string;
  submitted_cents: number;
  paid_cents: number;
  denial_rate: number;
  avg_days_to_pay: number;
}

export interface StandaloneBillingDashboardPayerPerformanceResponse {
  payers: StandaloneBillingDashboardPayerRowResponse[];
}

export async function getStandaloneBillingDashboardKpis(): Promise<StandaloneBillingDashboardKpisResponse> {
  const res = await API.get('/api/v1/billing-command/billing-kpis', {
    headers: standaloneBillingDashboardHeaders(),
  });
  return res.data as StandaloneBillingDashboardKpisResponse;
}

export async function getStandaloneBillingDashboardExecutiveSummary(): Promise<StandaloneBillingDashboardExecutiveSummaryResponse> {
  const res = await API.get('/api/v1/billing-command/executive-summary', {
    headers: standaloneBillingDashboardHeaders(),
  });
  return res.data as StandaloneBillingDashboardExecutiveSummaryResponse;
}

export async function getStandaloneBillingDashboardArAging(): Promise<StandaloneBillingDashboardArAgingResponse> {
  const res = await API.get('/api/v1/billing/ar-aging', {
    headers: standaloneBillingDashboardHeaders(),
  });
  return res.data as StandaloneBillingDashboardArAgingResponse;
}

export async function getStandaloneBillingDashboardPayerPerformance(): Promise<StandaloneBillingDashboardPayerPerformanceResponse> {
  const res = await API.get('/api/v1/billing-command/payer-performance', {
    headers: standaloneBillingDashboardHeaders(),
  });
  return res.data as StandaloneBillingDashboardPayerPerformanceResponse;
}

export interface StandaloneBillingClaimsClaimApi {
  id: string;
  patient: string;
  dos: string;
  payer: string;
  amount: string;
  status: 'clean' | 'pending' | 'denied' | 'appealed';
}

export interface StandaloneBillingClaimsStatApi {
  label: string;
  value: string;
  color?: string;
}

export interface StandaloneBillingClaimsResponse {
  claims?: StandaloneBillingClaimsClaimApi[];
  stats?: StandaloneBillingClaimsStatApi[];
}

export async function getStandaloneBillingClaims(params: {
  status: string;
  payer: string;
}): Promise<StandaloneBillingClaimsResponse> {
  const res = await API.get('/api/v1/billing/claims', { params });
  const payload = asJsonObject(res.data);
  return {
    claims: Array.isArray(payload.claims) ? (payload.claims as StandaloneBillingClaimsClaimApi[]) : [],
    stats: Array.isArray(payload.stats) ? (payload.stats as StandaloneBillingClaimsStatApi[]) : [],
  };
}

// ── Relationship Command Center ────────────────────────────────────────────

function relHeaders() {
  return aiHeaders();
}

export async function getRelationshipCommandSummary() {
  const res = await API.get('/api/v1/founder/relationship-command/summary', { headers: relHeaders() });
  return res.data;
}

export interface FounderRelationshipCommandSummaryApi {
  identity_confidence?: Record<string, unknown>;
  responsible_party_completion?: Record<string, unknown>;
  facility_health?: Record<string, unknown>;
  communication_completeness?: Record<string, unknown>;
  duplicate_review_count?: number;
  facility_contact_gaps?: number;
  frequent_utilizer_count?: number;
  top_actions?: Array<Record<string, unknown>>;
  [key: string]: unknown;
}

export async function getRelationshipCommandSummaryPortal(): Promise<FounderRelationshipCommandSummaryApi> {
  const res = await API.get('/api/v1/founder/relationship-command/summary', { headers: transportLinkHeaders() });
  return asJsonObject(res.data) as FounderRelationshipCommandSummaryApi;
}

export async function getRelationshipIssues() {
  const res = await API.get('/api/v1/founder/relationship-command/issues', { headers: relHeaders() });
  return res.data;
}

// ── Patient Identity ───────────────────────────────────────────────────────

export async function listDuplicateCandidates() {
  const res = await API.get('/api/v1/identity/duplicates', { headers: relHeaders() });
  return res.data;
}

export async function resolveDuplicate(candidateId: string, payload: { resolution: string; notes?: string }) {
  const res = await API.patch(`/api/v1/identity/duplicates/${candidateId}`, payload, { headers: relHeaders() });
  return res.data;
}

export async function listMergeRequests() {
  const res = await API.get('/api/v1/identity/merges', { headers: relHeaders() });
  return res.data;
}

export async function createMergeRequest(payload: { source_patient_id: string; target_patient_id: string; merge_reason?: string }) {
  const res = await API.post('/api/v1/identity/merges', payload, { headers: relHeaders() });
  return res.data;
}

export async function reviewMergeRequest(mergeId: string, payload: { action: string; review_notes?: string }) {
  const res = await API.post(`/api/v1/identity/merges/${mergeId}/review`, payload, { headers: relHeaders() });
  return res.data;
}

export async function listPatientAliases(patientId: string) {
  const res = await API.get(`/api/v1/identity/${patientId}/aliases`, { headers: relHeaders() });
  return res.data;
}

export async function createPatientAlias(patientId: string, payload: { alias_type: string; first_name: string; last_name: string; is_preferred?: boolean }) {
  const res = await API.post(`/api/v1/identity/${patientId}/aliases`, payload, { headers: relHeaders() });
  return res.data;
}

export async function listPatientIdentifiers(patientId: string) {
  const res = await API.get(`/api/v1/identity/${patientId}/identifiers`, { headers: relHeaders() });
  return res.data;
}

export async function createPatientIdentifier(patientId: string, payload: { identifier_type: string; value: string; issuing_authority?: string }) {
  const res = await API.post(`/api/v1/identity/${patientId}/identifiers`, payload, { headers: relHeaders() });
  return res.data;
}

export async function listPatientFlags(patientId: string) {
  const res = await API.get(`/api/v1/identity/${patientId}/flags`, { headers: relHeaders() });
  return res.data;
}

// ── Responsible Parties ────────────────────────────────────────────────────

export async function listResponsibleParties() {
  const res = await API.get('/api/v1/responsible-parties', { headers: relHeaders() });
  return res.data;
}

export async function createResponsibleParty(payload: { first_name: string; last_name: string; phone?: string; email?: string }) {
  const res = await API.post('/api/v1/responsible-parties', payload, { headers: relHeaders() });
  return res.data;
}

export async function getResponsibleParty(partyId: string) {
  const res = await API.get(`/api/v1/responsible-parties/${partyId}`, { headers: relHeaders() });
  return res.data;
}

export async function updateResponsibleParty(partyId: string, payload: Record<string, unknown>) {
  const res = await API.patch(`/api/v1/responsible-parties/${partyId}`, payload, { headers: relHeaders() });
  return res.data;
}

export async function linkPatientToResponsibleParty(patientId: string, payload: { responsible_party_id: string; relationship_to_patient: string; is_primary?: boolean }) {
  const res = await API.post(`/api/v1/patients/${patientId}/responsible-parties`, payload, { headers: relHeaders() });
  return res.data;
}

export async function listPatientResponsiblePartyLinks(patientId: string) {
  const res = await API.get(`/api/v1/patients/${patientId}/responsible-parties`, { headers: relHeaders() });
  return res.data;
}

export async function createInsuranceSubscriber(partyId: string, payload: Record<string, unknown>) {
  const res = await API.post(`/api/v1/responsible-parties/${partyId}/insurance`, payload, { headers: relHeaders() });
  return res.data;
}

export async function listInsuranceSubscribers(partyId: string) {
  const res = await API.get(`/api/v1/responsible-parties/${partyId}/insurance`, { headers: relHeaders() });
  return res.data;
}

// ── Facilities ─────────────────────────────────────────────────────────────

export async function listFacilities() {
  const res = await API.get('/api/v1/facilities', { headers: relHeaders() });
  return res.data;
}

export async function createFacility(payload: Record<string, unknown>) {
  const res = await API.post('/api/v1/facilities', payload, { headers: relHeaders() });
  return res.data;
}

export async function getFacility(facilityId: string) {
  const res = await API.get(`/api/v1/facilities/${facilityId}`, { headers: relHeaders() });
  return res.data;
}

export async function updateFacility(facilityId: string, payload: Record<string, unknown>) {
  const res = await API.patch(`/api/v1/facilities/${facilityId}`, payload, { headers: relHeaders() });
  return res.data;
}

export async function listFacilityContacts(facilityId: string) {
  const res = await API.get(`/api/v1/facilities/${facilityId}/contacts`, { headers: relHeaders() });
  return res.data;
}

export async function createFacilityContact(facilityId: string, payload: Record<string, unknown>) {
  const res = await API.post(`/api/v1/facilities/${facilityId}/contacts`, payload, { headers: relHeaders() });
  return res.data;
}

export async function listFacilityNotes(facilityId: string) {
  const res = await API.get(`/api/v1/facilities/${facilityId}/notes`, { headers: relHeaders() });
  return res.data;
}

export async function createFacilityNote(facilityId: string, payload: Record<string, unknown>) {
  const res = await API.post(`/api/v1/facilities/${facilityId}/notes`, payload, { headers: relHeaders() });
  return res.data;
}

export async function listFacilityServices(facilityId: string) {
  const res = await API.get(`/api/v1/facilities/${facilityId}/services`, { headers: relHeaders() });
  return res.data;
}

export async function createFacilityService(facilityId: string, payload: Record<string, unknown>) {
  const res = await API.post(`/api/v1/facilities/${facilityId}/services`, payload, { headers: relHeaders() });
  return res.data;
}

export async function listFacilityFriction(facilityId: string) {
  const res = await API.get(`/api/v1/facilities/${facilityId}/friction`, { headers: relHeaders() });
  return res.data;
}

export async function createFacilityFriction(facilityId: string, payload: Record<string, unknown>) {
  const res = await API.post(`/api/v1/facilities/${facilityId}/friction`, payload, { headers: relHeaders() });
  return res.data;
}

export async function resolveFacilityFriction(facilityId: string, flagId: string, payload: { resolution_notes: string }) {
  const res = await API.post(`/api/v1/facilities/${facilityId}/friction/${flagId}/resolve`, payload, { headers: relHeaders() });
  return res.data;
}

// ── Contact Preferences ────────────────────────────────────────────────────

export async function getPatientContactPreference(patientId: string) {
  const res = await API.get(`/api/v1/patients/${patientId}/contact-preferences`, { headers: relHeaders() });
  return res.data;
}

export async function upsertPatientContactPreference(patientId: string, payload: Record<string, unknown>) {
  const res = await API.put(`/api/v1/patients/${patientId}/contact-preferences`, payload, { headers: relHeaders() });
  return res.data;
}

export async function listOptOutEvents(patientId: string) {
  const res = await API.get(`/api/v1/patients/${patientId}/contact-preferences/opt-out`, { headers: relHeaders() });
  return res.data;
}

export async function recordOptOut(patientId: string, payload: { channel: string; action: string; reason: string; notes?: string }) {
  const res = await API.post(`/api/v1/patients/${patientId}/contact-preferences/opt-out`, payload, { headers: relHeaders() });
  return res.data;
}

export async function getPatientLanguagePreference(patientId: string) {
  const res = await API.get(`/api/v1/patients/${patientId}/contact-preferences/language`, { headers: relHeaders() });
  return res.data;
}

export async function upsertPatientLanguagePreference(patientId: string, payload: Record<string, unknown>) {
  const res = await API.put(`/api/v1/patients/${patientId}/contact-preferences/language`, payload, { headers: relHeaders() });
  return res.data;
}

// ── Relationship History ───────────────────────────────────────────────────

export async function listPatientTimeline(patientId: string) {
  const res = await API.get(`/api/v1/patients/${patientId}/history/timeline`, { headers: relHeaders() });
  return res.data;
}

export async function listPatientNotes(patientId: string) {
  const res = await API.get(`/api/v1/patients/${patientId}/history/notes`, { headers: relHeaders() });
  return res.data;
}

export async function listPatientWarnings(patientId: string) {
  const res = await API.get(`/api/v1/patients/${patientId}/history/warnings`, { headers: relHeaders() });
  return res.data;
}

export async function createPatientWarning(patientId: string, payload: Record<string, unknown>) {
  const res = await API.post(`/api/v1/patients/${patientId}/history/warnings`, payload, { headers: relHeaders() });
  return res.data;
}

export async function listFacilityTimeline(facilityId: string) {
  const res = await API.get(`/api/v1/facilities/${facilityId}/history/timeline`, { headers: relHeaders() });
  return res.data;
}

export async function listFacilityWarnings(facilityId: string) {
  const res = await API.get(`/api/v1/facilities/${facilityId}/history/warnings`, { headers: relHeaders() });
  return res.data;
}

export async function createFacilityWarning(facilityId: string, payload: Record<string, unknown>) {
  const res = await API.post(`/api/v1/facilities/${facilityId}/history/warnings`, payload, { headers: relHeaders() });
  return res.data;
}

export async function resolveFacilityWarning(facilityId: string, flagId: string, payload: { resolution_notes: string }) {
  const res = await API.post(`/api/v1/facilities/${facilityId}/history/warnings/${flagId}/resolve`, payload, { headers: relHeaders() });
  return res.data;
}

// ── CAD / Dispatch ──────────────────────────────────────────────────────────

export async function createCADCall(payload: Record<string, unknown>) {
  const res = await API.post('/api/v1/cad/calls', payload, { headers: aiHeaders() });
  return normalizeDominationRecord(res.data);
}

export async function getActiveCADCalls(): Promise<CADCallApi[]> {
  const res = await API.get('/api/v1/cad/ops/board', { headers: aiHeaders() });
  const calls = normalizeDominationList(res.data, 'calls');
  return calls.map((call) => {
    const priority = asString(call.priority, 'ALPHA').toUpperCase();
    const state = normalizeCADCallState(call.state || call.status);
    return {
      ...call,
      id: asString(call.id),
      call_number: asString(call.call_number, `CALL-${asString(call.id).slice(0, 8).toUpperCase()}`),
      state,
      priority,
      chief_complaint: asString(call.chief_complaint),
      address: asString(call.address || call.location_address),
      location_address: asString(call.location_address || call.address),
      call_received_at: asIsoDateString(call.call_received_at || call.created_at),
      caller_name: asString(call.caller_name),
      caller_phone: asString(call.caller_phone),
      triage_notes: asString(call.triage_notes),
      assigned_unit: asString(call.assigned_unit),
    } as CADCallApi;
  });
}

export async function getCADCall(callId: string): Promise<CADCallApi | null> {
  const calls = await getActiveCADCalls();
  return calls.find((c) => c.id === callId) || null;
}

export async function transitionCADCall(callId: string, payload: { state: string }) {
  const res = await API.post(
    `/api/v1/cad/calls/${callId}/status`,
    { status: payload.state },
    { headers: aiHeaders() }
  );
  return res.data;
}

export async function assignCADUnit(callId: string, payload: { unit_id: string }) {
  const res = await API.post(`/api/v1/cad/calls/${callId}/assign`, payload, { headers: aiHeaders() });
  return res.data;
}

export async function getCADCallTimeline(callId: string): Promise<CADCallApi[]> {
  const call = await getCADCall(callId);
  return call ? [call] : [];
}

export async function listCADUnits(): Promise<CADUnitApi[]> {
  const res = await API.get('/api/v1/cad/units', { headers: aiHeaders() });
  const units = normalizeDominationList(res.data);
  return units.map((unit) => {
    const lat = asNumber(unit.lat ?? unit.latitude);
    const lng = asNumber(unit.lng ?? unit.longitude);
    return {
      ...unit,
      id: asString(unit.id),
      unit_name: asString(unit.unit_name || unit.name || unit.callsign, ''),
      unit_type: asString(unit.unit_type || unit.type, ''),
      state: asString(unit.state || unit.status, 'AVAILABLE').toUpperCase(),
      station: asString(unit.station, 'Unassigned'),
      lat,
      lng,
      readiness_score: asNumber(unit.readiness_score),
      active_call_id: asString(unit.active_call_id || unit.call_id) || null,
    };
  }) as CADUnitApi[];
}

export async function registerCADUnit(payload: Record<string, unknown>) {
  const res = await API.post('/api/v1/cad/units', payload, { headers: aiHeaders() });
  return res.data;
}

export async function updateCADUnitStatus(unitId: string, payload: { state: string; reason?: string }) {
  const res = await API.post(
    `/api/v1/cad/units/${unitId}/status`,
    { status: payload.state, reason: payload.reason },
    { headers: aiHeaders() }
  );
  return res.data;
}

export async function updateCADUnitGPS(unitId: string, payload: { lat: number; lng: number }) {
  const res = await API.post(
    `/api/v1/mdt/units/${unitId}/gps`,
    { points: [{ lat: payload.lat, lng: payload.lng, ts: new Date().toISOString() }] },
    { headers: aiHeaders() }
  );
  return res.data;
}

// ── Fire / NERIS ────────────────────────────────────────────────────────────

export async function createFireIncident(payload: Record<string, unknown>) {
  const res = await API.post('/api/v1/fire/ops/incidents', payload, { headers: aiHeaders() });
  return normalizeDominationRecord(res.data);
}

export async function getFireIncident(incidentId: string): Promise<JsonObject | null> {
  const incidents = await listFireIncidents();
  return incidents.find((incident) => asString((incident as JsonObject).id) === incidentId) || null;
}

export async function listFireIncidents(): Promise<JsonObject[]> {
  const res = await API.get('/api/v1/fire/ops/ops/board', { headers: aiHeaders() });
  return normalizeDominationList(res.data, 'fire_incidents');
}

export async function validateNERIS(incidentId: string) {
  const res = await API.post(`/api/v1/fire/ops/neris/validate/${incidentId}`, {}, { headers: aiHeaders() });
  return res.data;
}

export async function createNERISExport(payload: { incident_ids: string[] }) {
  const res = await API.post('/api/v1/fire/ops/neris/export', payload, { headers: aiHeaders() });
  return res.data;
}

export async function listNERISExports() {
  const res = await API.get('/api/v1/fire/ops/neris/exports', { headers: aiHeaders() });
  return res.data;
}

export async function createFirePreplan(payload: Record<string, unknown>) {
  const res = await API.post('/api/v1/fire/ops/preplans', payload, { headers: aiHeaders() });
  return normalizeDominationRecord(res.data);
}

export async function listFirePreplans(): Promise<FirePreplanApi[]> {
  const res = await API.get('/api/v1/fire/ops/preplans', { headers: aiHeaders() });
  const preplans = normalizeDominationList(res.data);
  return preplans.map((plan) => ({
    ...plan,
    id: asString(plan.id),
    name: asString(plan.name),
    address: asString(plan.address),
    occupancy_type: asString(plan.occupancy_type) || null,
    stories: asNumber(plan.stories),
    sprinkler_system: asBoolean(plan.sprinkler_system),
    standpipe: asBoolean(plan.standpipe),
    fire_alarm_system: asBoolean(plan.fire_alarm_system),
    construction_type: asString(plan.construction_type) || null,
    last_reviewed_at: asString(plan.last_reviewed_at) || null,
    notes: asString(plan.notes) || null,
    hazards: asJsonObject(plan.hazards),
  })) as FirePreplanApi[];
}

export async function createFireHydrant(payload: Record<string, unknown>) {
  const normalizedPayload: Record<string, unknown> = { ...payload };
  const latitude = asNumber(normalizedPayload.latitude);
  const longitude = asNumber(normalizedPayload.longitude);
  if (latitude != null && normalizedPayload.lat == null) normalizedPayload.lat = latitude;
  if (longitude != null && normalizedPayload.lng == null) normalizedPayload.lng = longitude;
  const res = await API.post('/api/v1/fire/ops/hydrants', normalizedPayload, { headers: aiHeaders() });
  return normalizeDominationRecord(res.data);
}

export async function listFireHydrants(): Promise<FireHydrantApi[]> {
  const res = await API.get('/api/v1/fire/ops/hydrants', { headers: aiHeaders() });
  const hydrants = normalizeDominationList(res.data);
  return hydrants.map((hydrant) => ({
    ...hydrant,
    id: asString(hydrant.id),
    hydrant_number: asString(hydrant.hydrant_number),
    latitude: asNumber(hydrant.latitude ?? hydrant.lat) ?? 0,
    longitude: asNumber(hydrant.longitude ?? hydrant.lng) ?? 0,
    in_service: asBoolean(hydrant.in_service, true),
    flow_rate_gpm: asNumber(hydrant.flow_rate_gpm),
    static_pressure_psi: asNumber(hydrant.static_pressure_psi),
    hydrant_type: asString(hydrant.hydrant_type) || null,
    color_code: asString(hydrant.color_code) || null,
    last_tested_at: asString(hydrant.last_tested_at) || null,
    notes: asString(hydrant.notes) || null,
  })) as FireHydrantApi[];
}

export async function createFireInspection(payload: Record<string, unknown>) {
  const res = await API.post('/api/v1/fire/ops/inspections', payload, { headers: aiHeaders() });
  return res.data;
}

export async function listFireInspections() {
  const res = await API.get('/api/v1/fire/ops/inspections', { headers: aiHeaders() });
  return res.data;
}

export async function addFireApparatus(incidentId: string, payload: Record<string, unknown>) {
  const res = await API.post(`/api/v1/fire/ops/incidents/${incidentId}/apparatus`, payload, { headers: aiHeaders() });
  return res.data;
}

// ── Scheduling ──────────────────────────────────────────────────────────────

export async function listShiftTemplates() {
  const res = await API.get('/api/v1/scheduling/templates', { headers: aiHeaders() });
  return res.data;
}

export async function createShiftTemplate(payload: Record<string, unknown>) {
  const res = await API.post('/api/v1/scheduling/templates', payload, { headers: aiHeaders() });
  return res.data;
}

export async function listShiftInstances(params?: Record<string, string>) {
  const res = await API.get('/api/v1/scheduling/shifts', { headers: aiHeaders(), params });
  return res.data;
}

export async function createShiftInstance(payload: Record<string, unknown>) {
  const res = await API.post('/api/v1/scheduling/shifts', payload, { headers: aiHeaders() });
  return res.data;
}

export async function requestShiftSwap(payload: { requester_shift_id: string; acceptor_shift_id: string; reason?: string }) {
  const res = await API.post('/api/v1/scheduling/swaps/request', payload, { headers: aiHeaders() });
  return res.data;
}

export async function approveSwap(swapId: string) {
  const res = await API.post(`/api/v1/scheduling/swaps/${swapId}/approve`, {}, { headers: aiHeaders() });
  return res.data;
}

export async function denySwap(swapId: string, payload: { reason: string }) {
  const res = await API.post(`/api/v1/scheduling/swaps/${swapId}/deny`, payload, { headers: aiHeaders() });
  return res.data;
}

export async function listSwaps(params?: Record<string, string>) {
  const res = await API.get('/api/v1/scheduling/swaps', { headers: aiHeaders(), params });
  return res.data;
}

export async function createCoverageRule(payload: Record<string, unknown>) {
  const res = await API.post('/api/v1/scheduling/coverage/rules', payload, { headers: aiHeaders() });
  return res.data;
}

export async function listCoverageRules() {
  const res = await API.get('/api/v1/scheduling/coverage/rules', { headers: aiHeaders() });
  return res.data;
}

export async function assessFatigue(payload: { user_id: string; hours_on_duty: number; hours_since_last_sleep: number; calls_this_shift?: number; kss_score?: number }) {
  const res = await API.post('/api/v1/scheduling/fatigue/assess', payload, { headers: aiHeaders() });
  return res.data;
}

// ── Patient Portal ──────────────────────────────────────────────────────────

export async function loginTransportLink(payload: { email: string; password: string }): Promise<string> {
  try {
    const res = await API.post('/api/v1/auth/login', payload, {
      headers: { 'Content-Type': 'application/json' },
    });
    const response = asJsonObject(res.data);
    const nested = asJsonObject(response.data);
    const token = asString(response.access_token || response.token || nested.access_token, '');
    if (!token) {
      throw new Error('Login succeeded but no token was returned. Contact support.');
    }
    if (typeof window !== 'undefined') {
      localStorage.setItem('qs_token', token);
    }
    return token;
  } catch (error) {
    if (error instanceof Error && error.message.includes('no token was returned')) {
      throw error;
    }
    throw new Error(asErrorMessage(error, 'Authentication failed. Verify your credentials.'));
  }
}

export async function submitTransportLinkAccessRequest(payload: {
  facility_name: string;
  department?: string;
  requestor_name: string;
  title?: string;
  work_email: string;
  callback_number?: string;
  facility_address?: string;
  ehr_platform?: string;
  expected_volume?: string;
  use_case?: string;
  notes?: string;
}) {
  const res = await API.post('/api/v1/transportlink/access-requests', payload, {
    headers: { 'Content-Type': 'application/json' },
  });
  return res.data;
}

export async function createTransportLinkRequest(payload: Record<string, unknown>): Promise<TransportLinkRecordApi> {
  const res = await API.post('/api/v1/transportlink/requests', payload, {
    headers: {
      ...transportLinkHeaders(),
      'Content-Type': 'application/json',
    },
  });
  return normalizeTransportLinkRecord(res.data);
}

export async function submitTransportLinkToCad(requestId: string, expectedVersion = 1): Promise<TransportLinkRecordApi> {
  const res = await API.post(
    `/api/v1/transportlink/requests/${requestId}/submit-to-cad`,
    { expected_version: expectedVersion },
    {
      headers: {
        ...transportLinkHeaders(),
        'Content-Type': 'application/json',
      },
    }
  );
  const payload = asJsonObject(res.data);
  const error = asString(payload.error, '');
  if (error) {
    throw new Error(`CAD submission failed (${error}).`);
  }
  return normalizeTransportLinkRecord(payload);
}

export async function requestTransportLinkUploadUrl(
  requestId: string,
  payload: { filename: string; content_type: string; doc_type: 'facesheet' | 'pcs' | 'aob' | 'abn' | 'other' }
): Promise<TransportLinkUploadUrlApi> {
  const res = await API.post(`/api/v1/transportlink/requests/${requestId}/upload-url`, payload, {
    headers: {
      ...transportLinkHeaders(),
      'Content-Type': 'application/json',
    },
  });
  const data = asJsonObject(res.data);
  const upload = asJsonObject(data.upload);
  return {
    request_id: asString(data.request_id),
    document_id: asString(data.document_id),
    upload: {
      method: asString(upload.method, 'PUT'),
      url: asString(upload.url),
      key: asString(upload.key) || undefined,
      expires_in: asNumber(upload.expires_in) ?? undefined,
    },
  };
}

export async function uploadTransportLinkDocumentToPresignedUrl(uploadUrl: string, file: File): Promise<void> {
  await fetch(uploadUrl, {
    method: 'PUT',
    headers: { 'Content-Type': file.type },
    body: file,
  });
}

export async function triggerTransportLinkDocumentOcr(documentId: string): Promise<{ queued: boolean; document_id: string }> {
  const res = await API.post(`/api/v1/transportlink/documents/${documentId}/process-ocr`, {}, {
    headers: transportLinkHeaders(),
  });
  const data = asJsonObject(res.data);
  return {
    queued: asBoolean(data.queued, true),
    document_id: asString(data.document_id || documentId),
  };
}

export async function listTransportLinkDocuments(requestId?: string): Promise<TransportLinkDocumentApi[]> {
  const res = await API.get('/api/v1/transportlink/documents', {
    headers: transportLinkHeaders(),
    params: requestId ? { request_id: requestId } : undefined,
  });
  const payload = res.data;
  const items = Array.isArray(payload)
    ? payload
    : Array.isArray(payload?.items)
      ? payload.items
      : Array.isArray(payload?.data)
        ? payload.data
        : [];
  return items.map((item: unknown) => normalizeTransportLinkDocument(item));
}

export async function applyTransportLinkOcrToRequest(
  documentId: string,
  payload: { request_id: string | null; confirmed_fields: Record<string, string> }
): Promise<{ applied: number; skipped: number }> {
  const res = await API.post(`/api/v1/transportlink/documents/${documentId}/apply-ocr`, payload, {
    headers: {
      ...transportLinkHeaders(),
      'Content-Type': 'application/json',
    },
  });
  const data = asJsonObject(res.data);
  return {
    applied: asNumber(data.applied) ?? 0,
    skipped: asNumber(data.skipped) ?? 0,
  };
}

export async function deleteTransportLinkDocument(documentId: string): Promise<boolean> {
  const res = await API.delete(`/api/v1/transportlink/documents/${documentId}`, {
    headers: transportLinkHeaders(),
  });
  const data = asJsonObject(res.data);
  return asBoolean(data.deleted, true);
}

export async function listTransportLinkRequests(limit = 30): Promise<TransportLinkRequestSummaryApi[]> {
  const res = await API.get('/api/v1/transportlink/requests', {
    headers: transportLinkHeaders(),
    params: { limit },
  });
  const payload = res.data;
  if (Array.isArray(payload)) {
    return payload.map((item) => normalizeTransportLinkSummary(item));
  }
  if (Array.isArray(payload?.items)) {
    return payload.items.map((item: unknown) => normalizeTransportLinkSummary(item));
  }
  if (Array.isArray(payload?.data)) {
    return payload.data.map((item: unknown) => normalizeTransportLinkSummary(item));
  }
  return [];
}

export interface PatientPortalRegisterPayload {
  first_name: string;
  last_name: string;
  date_of_birth: string;
  email: string;
  phone: string;
  statement_id: string;
  zip: string;
  password: string;
}

export interface PatientPortalLoginPayload {
  email: string;
  password: string;
}

export interface PatientPortalPasswordResetRequestPayload {
  email: string;
}

export interface PatientPortalPasswordResetConfirmPayload {
  token: string;
  new_password: string;
}

export interface PatientPortalRequestResult {
  ok: boolean;
  status: number;
  detail?: string;
  data: JsonObject;
}

export interface PatientPortalIdentityDuplicateCandidateApi {
  id: string;
  patient_a_id: string;
  patient_b_id: string;
  confidence_score: number;
  detection_method: string | null;
  resolution: string;
  notes: string | null;
}

export interface PatientPortalIdentityMergeRequestApi {
  id: string;
  source_patient_id: string;
  target_patient_id: string;
  status: string;
  merge_reason: string | null;
  requested_by_user_id: string;
  reviewed_by_user_id: string | null;
  created_at: string;
}

export interface PatientPortalSupportRequestPayload {
  category: string;
  subject: string;
  message: string;
  callback_requested: boolean;
  callback_phone: string;
  preferred_callback_time: string;
}

export interface PatientPortalChatResponse {
  reply?: string;
  message?: string;
}

export interface PatientPortalInvoiceStatementData {
  patient_name?: string;
  responsible_party?: string;
  agency_name?: string;
  incident_date?: string;
  transport_date?: string;
  service_type?: string;
  origin?: string;
  destination?: string;
  amount_billed_cents?: number;
  amount_due_cents?: number;
  amount_paid_cents?: number;
  adjustments_cents?: number;
  due_date?: string;
  status?: string;
  account_ref?: string;
}

export interface PatientPortalInvoiceStatementApi {
  id: string;
  data?: PatientPortalInvoiceStatementData;
}

function toPatientPortalRequestResult(status: number, payload: unknown): PatientPortalRequestResult {
  const data = asJsonObject(payload);
  return {
    ok: status >= 200 && status < 300,
    status,
    detail: asString(data.detail) || undefined,
    data,
  };
}

function patientPortalQsAuthHeaders(): Record<string, string> {
  if (typeof window === 'undefined') {
    return { Authorization: 'Bearer ' };
  }
  const token = localStorage.getItem('qs_token') || '';
  return { Authorization: `Bearer ${token}` };
}

export async function registerPatientPortalAccount(
  payload: PatientPortalRegisterPayload
): Promise<PatientPortalRequestResult> {
  const res = await API.post('/api/v1/portal/register', payload, {
    headers: { 'Content-Type': 'application/json' },
    validateStatus: () => true,
  });
  return toPatientPortalRequestResult(res.status, res.data);
}

export async function loginPatientPortalSession(
  payload: PatientPortalLoginPayload
): Promise<PatientPortalRequestResult> {
  const res = await API.post('/api/v1/auth/login', payload, {
    headers: { 'Content-Type': 'application/json' },
    withCredentials: true,
    validateStatus: () => true,
  });
  return toPatientPortalRequestResult(res.status, res.data);
}

export async function requestPatientPortalPasswordReset(
  payload: PatientPortalPasswordResetRequestPayload
): Promise<PatientPortalRequestResult> {
  const res = await API.post('/api/v1/auth/password-reset/request', payload, {
    headers: { 'Content-Type': 'application/json' },
    validateStatus: () => true,
  });
  return toPatientPortalRequestResult(res.status, res.data);
}

export async function confirmPatientPortalPasswordReset(
  payload: PatientPortalPasswordResetConfirmPayload
): Promise<PatientPortalRequestResult> {
  const res = await API.post('/api/v1/auth/password-reset/confirm', payload, {
    headers: { 'Content-Type': 'application/json' },
    validateStatus: () => true,
  });
  return toPatientPortalRequestResult(res.status, res.data);
}

export async function listPatientPortalIdentityDuplicates(): Promise<PatientPortalIdentityDuplicateCandidateApi[]> {
  const res = await API.get('/api/v1/identity/duplicates', {
    headers: patientPortalQsAuthHeaders(),
    validateStatus: () => true,
  });
  if (res.status < 200 || res.status >= 300) {
    return [];
  }
  const data = asJsonObject(res.data);
  const items = Array.isArray(data.items) ? data.items : [];
  return items.map((item) => {
    const row = asJsonObject(item);
    return {
      id: asString(row.id),
      patient_a_id: asString(row.patient_a_id),
      patient_b_id: asString(row.patient_b_id),
      confidence_score: asNumber(row.confidence_score) ?? 0,
      detection_method: asString(row.detection_method) || null,
      resolution: asString(row.resolution),
      notes: asString(row.notes) || null,
    };
  });
}

export async function listPatientPortalIdentityMerges(): Promise<PatientPortalIdentityMergeRequestApi[]> {
  const res = await API.get('/api/v1/identity/merges', {
    headers: patientPortalQsAuthHeaders(),
    validateStatus: () => true,
  });
  if (res.status < 200 || res.status >= 300) {
    return [];
  }
  const data = asJsonObject(res.data);
  const items = Array.isArray(data.items) ? data.items : [];
  return items.map((item) => {
    const row = asJsonObject(item);
    return {
      id: asString(row.id),
      source_patient_id: asString(row.source_patient_id),
      target_patient_id: asString(row.target_patient_id),
      status: asString(row.status),
      merge_reason: asString(row.merge_reason) || null,
      requested_by_user_id: asString(row.requested_by_user_id),
      reviewed_by_user_id: asString(row.reviewed_by_user_id) || null,
      created_at: asString(row.created_at),
    };
  });
}

export async function submitPatientPortalSupportRequest(
  payload: PatientPortalSupportRequestPayload
): Promise<void> {
  await API.post('/api/v1/portal/support', payload, {
    withCredentials: true,
    headers: { 'Content-Type': 'application/json' },
  });
}

export async function sendPatientPortalBillingChatMessage(payload: {
  message: string;
  context: 'patient_billing';
}): Promise<PatientPortalChatResponse> {
  const res = await API.post('/api/v1/ai/patient-chat', payload, {
    withCredentials: true,
    headers: { 'Content-Type': 'application/json' },
    validateStatus: () => true,
  });
  const data = asJsonObject(res.data);
  return {
    reply: asString(data.reply) || undefined,
    message: asString(data.message) || undefined,
  };
}

export async function listPatientPortalStatementsForInvoiceLookup(
  limit = 200
): Promise<PatientPortalInvoiceStatementApi[]> {
  const res = await API.get('/api/v1/portal/statements', {
    params: { limit },
    withCredentials: true,
    validateStatus: () => true,
  });
  if (res.status < 200 || res.status >= 300) {
    return [];
  }
  const data = asJsonObject(res.data);
  const statements = Array.isArray(data.statements) ? data.statements : [];
  return statements.map((statement) => {
    const row = asJsonObject(statement);
    const nestedData = asJsonObject(row.data);
    return {
      id: asString(row.id),
      data: {
        patient_name: asString(nestedData.patient_name) || undefined,
        responsible_party: asString(nestedData.responsible_party) || undefined,
        agency_name: asString(nestedData.agency_name) || undefined,
        incident_date: asString(nestedData.incident_date) || undefined,
        transport_date: asString(nestedData.transport_date) || undefined,
        service_type: asString(nestedData.service_type) || undefined,
        origin: asString(nestedData.origin) || undefined,
        destination: asString(nestedData.destination) || undefined,
        amount_billed_cents: asNumber(nestedData.amount_billed_cents) ?? undefined,
        amount_due_cents: asNumber(nestedData.amount_due_cents) ?? undefined,
        amount_paid_cents: asNumber(nestedData.amount_paid_cents) ?? undefined,
        adjustments_cents: asNumber(nestedData.adjustments_cents) ?? undefined,
        due_date: asString(nestedData.due_date) || undefined,
        status: asString(nestedData.status) || undefined,
        account_ref: asString(nestedData.account_ref) || undefined,
      },
    };
  });
}

export async function getPortalStatements() {
  const res = await API.get('/api/v1/portal/statements', { headers: aiHeaders() });
  const statements = normalizeDominationList(res.data, 'statements');
  return statements.map((statement) => ({
    ...statement,
    id: asString(statement.id),
    statement_number: asString(statement.statement_number),
    patient_account_id: asString(statement.patient_account_id),
    balance: asNumber(statement.balance) ?? 0,
    amount_due: asNumber(statement.amount_due) ?? 0,
    due_date: asString(statement.due_date),
    created_at: asIsoDateString(statement.created_at),
  }));
}

export async function getPortalPayments() {
  const res = await API.get('/api/v1/portal/payments', { headers: aiHeaders() });
  const payments = normalizeDominationList(res.data, 'payments');
  return payments.map((payment) => ({
    ...payment,
    id: asString(payment.id),
    patient_account_id: asString(payment.patient_account_id),
    amount: asNumber(payment.amount) ?? 0,
    method: asString(payment.method),
    created_at: asIsoDateString(payment.created_at),
  }));
}

export async function submitPortalPayment(payload: { statement_id: string; amount: number; method: string }) {
  const res = await API.post('/api/v1/portal/payments', payload, { headers: aiHeaders() });
  return normalizeDominationRecord(res.data);
}

export async function getPortalMessages(): Promise<PortalMessageApi[]> {
  const res = await API.get('/api/v1/portal/messages', { headers: aiHeaders() });
  const messages = normalizeDominationList(res.data, 'messages');
  return messages.map((message) => ({
    ...message,
    id: asString(message.id),
    subject: asString(message.subject),
    body: asString(message.body),
    direction: asString(message.direction, 'inbound') === 'outbound' ? 'outbound' : 'inbound',
    created_at: asIsoDateString(message.created_at),
  }));
}

export async function sendPortalMessage(payload: { subject: string; body: string }) {
  const res = await API.post('/api/v1/portal/messages', payload, { headers: aiHeaders() });
  return normalizeDominationRecord(res.data);
}

export async function getPortalAuthReps() {
  const res = await API.get('/api/v1/portal/auth-reps', { headers: aiHeaders() });
  const reps = normalizeDominationList(res.data, 'authorized_reps');
  return reps.map((rep) => ({
    ...rep,
    id: asString(rep.id),
    patient_account_id: asString(rep.patient_account_id),
    first_name: asString(rep.first_name),
    last_name: asString(rep.last_name),
    relationship: asString(rep.relationship),
  }));
}

export async function getPortalBillingSummary(patientAccountId?: string) {
  const res = await API.get('/api/v1/portal/billing/summary', {
    headers: aiHeaders(),
    params: patientAccountId ? { patient_account_id: patientAccountId } : undefined,
  });
  return res.data;
}

// ── Auth Representatives ────────────────────────────────────────────────────

export interface AuthRepRegisterPayload {
  full_name: string;
  relationship: string;
  patient_account_id: string;
  delivery_method: 'sms' | 'email' | string;
  email?: string;
  phone?: string;
}

export interface AuthRepVerifyOtpPayload {
  session_id: string;
  otp_code: string;
}

export interface AuthRepSignPayload {
  authorized_rep_id: string;
  signature_data: string;
  agreed_to_terms: boolean;
}

export interface AuthRepUploadDocumentPayload {
  file: File;
  document_type: string;
  session_id: string;
}

export interface AuthRepRequestResult {
  ok: boolean;
  status: number;
  detail?: string;
  data: JsonObject;
}

function toAuthRepRequestResult(status: number, payload: unknown): AuthRepRequestResult {
  const data = asJsonObject(payload);
  return {
    ok: status >= 200 && status < 300,
    status,
    detail: asString(data.detail) || undefined,
    data,
  };
}

function authRepOptionalBearerHeaders(token?: string): Record<string, string> {
  return token ? { Authorization: `Bearer ${token}` } : {};
}

export async function registerAuthRep(
  payload: AuthRepRegisterPayload,
  token?: string
): Promise<AuthRepRequestResult> {
  const res = await API.post('/api/v1/auth-rep/register', payload, {
    headers: {
      'Content-Type': 'application/json',
      ...authRepOptionalBearerHeaders(token),
    },
    validateStatus: () => true,
  });
  return toAuthRepRequestResult(res.status, res.data);
}

export async function verifyAuthRepOtp(
  payload: AuthRepVerifyOtpPayload
): Promise<AuthRepRequestResult> {
  const res = await API.post('/api/v1/auth-rep/verify-otp', payload, {
    headers: { 'Content-Type': 'application/json' },
    validateStatus: () => true,
  });
  return toAuthRepRequestResult(res.status, res.data);
}

export async function signAuthRep(
  payload: AuthRepSignPayload,
  token?: string
): Promise<AuthRepRequestResult> {
  const res = await API.post('/api/v1/auth-rep/sign', payload, {
    headers: {
      'Content-Type': 'application/json',
      ...authRepOptionalBearerHeaders(token),
    },
    validateStatus: () => true,
  });
  return toAuthRepRequestResult(res.status, res.data);
}

export async function uploadAuthRepDocument(
  payload: AuthRepUploadDocumentPayload,
  token?: string
): Promise<AuthRepRequestResult> {
  const formData = new FormData();
  formData.append('file', payload.file);
  formData.append('document_type', payload.document_type);
  formData.append('session_id', payload.session_id);

  const res = await API.post('/api/v1/auth-rep/upload-document', formData, {
    headers: {
      ...authRepOptionalBearerHeaders(token),
    },
    validateStatus: () => true,
  });
  return toAuthRepRequestResult(res.status, res.data);
}

export async function revokeAuthRep(payload: { rep_id: string; reason: string }) {
  const res = await API.post('/api/v1/auth-rep/revoke', payload, { headers: aiHeaders() });
  return res.data;
}

export async function logAuthRepConsent(payload: { rep_id: string; consent_type: string; detail: Record<string, unknown> }) {
  const res = await API.post('/api/v1/auth-rep/consent', payload, { headers: aiHeaders() });
  return res.data;
}

export async function getRepConsentEvents(repId: string) {
  const res = await API.get(`/api/v1/auth-rep/reps/${repId}/consent-events`, { headers: aiHeaders() });
  return res.data;
}

export async function getRepStatus(repId: string) {
  const res = await API.get(`/api/v1/auth-rep/reps/${repId}/status`, { headers: aiHeaders() });
  return res.data;
}

// ── Imports ─────────────────────────────────────────────────────────────────

export async function validateImportBatch(payload: { table: string; records: Record<string, unknown>[] }) {
  const res = await API.post('/api/v1/imports/validate', payload, { headers: aiHeaders() });
  return res.data;
}

export async function executeImportBatch(batchId: string) {
  const res = await API.post(`/api/v1/imports/execute/${batchId}`, {}, { headers: aiHeaders() });
  return res.data;
}

// ── NEMSIS Export ───────────────────────────────────────────────────────────

export async function exportNEMSIS(payload: { epcr_ids: string[] }) {
  const res = await API.post('/api/v1/nemsis/export', payload, { headers: aiHeaders() });
  return res.data;
}

export async function validateNEMSISCompleteness(epcrId: string) {
  const res = await API.get(`/api/v1/nemsis/validate/${epcrId}`, { headers: aiHeaders() });
  return res.data;
}

// ── Export Status ───────────────────────────────────────────────────────────

export async function getExportQueue() {
  const res = await API.get('/api/v1/export-status/queue', { headers: csHeaders() });
  return res.data;
}

export async function getExportRejectionAlerts() {
  const res = await API.get('/api/v1/export-status/rejection-alerts', { headers: csHeaders() });
  return res.data;
}

export async function getExportPerformanceScore() {
  const res = await API.get('/api/v1/export-status/performance-score', { headers: csHeaders() });
  return res.data;
}

export async function getExportAuditHistory() {
  const res = await API.get('/api/v1/export-status/audit-history', { headers: csHeaders() });
  return res.data;
}

export async function getExportLatency() {
  const res = await API.get('/api/v1/export-status/latency', { headers: csHeaders() });
  return res.data;
}

export async function getExportPendingApproval() {
  const res = await API.get('/api/v1/export-status/pending-approval', { headers: csHeaders() });
  return res.data;
}

export async function retryExportJob(jobId: string) {
  const res = await API.post(`/api/v1/export-status/retry/${jobId}`, {}, { headers: csHeaders() });
  return res.data;
}

// ── Compliance Command Center ───────────────────────────────────────────────

export async function getComplianceCommandSummary(days?: number) {
  const res = await API.get('/api/v1/compliance/command/summary', {
    headers: csHeaders(),
    params: typeof days === 'number' ? { days } : undefined,
  });
  return res.data;
}

export async function getComplianceCommandSummaryPortal(days = 30) {
  const headers: Record<string, string> = {};
  if (typeof window !== 'undefined') {
    const token = localStorage.getItem('token') || '';
    if (token) {
      headers.Authorization = `Bearer ${token}`;
    }
  }
  const res = await API.get('/api/v1/compliance/command/summary', {
    headers,
    params: { days },
  });
  return res.data;
}

// ── Webhooks ────────────────────────────────────────────────────────────────

export async function listDeadLetterQueue() {
  const res = await API.get('/api/v1/webhooks/dead-letter', { headers: aiHeaders() });
  return res.data;
}

export async function retryDeadLetter(deliveryId: string) {
  const res = await API.post(`/api/v1/webhooks/dead-letter/${deliveryId}/retry`, {}, { headers: aiHeaders() });
  return res.data;
}

// ── ePCR Charts ──────────────────────────────────────────────────────────────

export async function listEPCRCharts(status?: string): Promise<EPCRChartApi[]> {
  const params = status ? `?status=${status}` : '';
  const res = await API.get(`/api/v1/epcr/charts${params}`, { headers: aiHeaders() });
  const charts = normalizeDominationList(res.data);
  return charts.map((chart) => normalizeEPCRChartRecord(chart));
}

export async function createEPCRChart(payload: Record<string, unknown>): Promise<EPCRChartApi> {
  const res = await API.post('/api/v1/epcr/charts', payload, { headers: aiHeaders() });
  let chart = normalizeEPCRChartRecord(res.data);
  const chartId = chart.id;
  if (chartId && Object.keys(payload).length > 0) {
    try {
      const patchRes = await API.patch(`/api/v1/epcr/charts/${chartId}`, payload, { headers: aiHeaders() });
      chart = normalizeEPCRChartRecord(patchRes.data);
    } catch {
      // Preserve chart creation success even if non-critical enrichment patch fails.
    }
  }
  return chart;
}

export async function getEPCRChart(chartId: string): Promise<EPCRChartApi> {
  const res = await API.get(`/api/v1/epcr/charts/${chartId}`, { headers: aiHeaders() });
  return normalizeEPCRChartRecord(res.data);
}

export async function updateEPCRChart(chartId: string, payload: Record<string, unknown>): Promise<EPCRChartApi> {
  const res = await API.patch(`/api/v1/epcr/charts/${chartId}`, payload, { headers: aiHeaders() });
  return normalizeEPCRChartRecord(res.data);
}

export async function addEPCRVitals(chartId: string, payload: Record<string, unknown>) {
  const res = await API.post(`/api/v1/epcr/charts/${chartId}/vitals`, payload, { headers: aiHeaders() });
  return res.data;
}

export async function addEPCRMedication(chartId: string, payload: Record<string, unknown>) {
  const res = await API.post(`/api/v1/epcr/charts/${chartId}/medications`, payload, { headers: aiHeaders() });
  return res.data;
}

export async function addEPCRProcedure(chartId: string, payload: Record<string, unknown>) {
  const res = await API.post(`/api/v1/epcr/charts/${chartId}/procedures`, payload, { headers: aiHeaders() });
  return res.data;
}

export async function addEPCRAssessment(chartId: string, payload: Record<string, unknown>) {
  const res = await API.post(`/api/v1/epcr/charts/${chartId}/assessments`, payload, { headers: aiHeaders() });
  return res.data;
}

export async function generateEPCRAINarrative(chartId: string) {
  const res = await API.post(`/api/v1/epcr/charts/${chartId}/ai/narrative`, {}, { headers: aiHeaders() });
  return res.data;
}

export async function getEPCRCompleteness(chartId: string) {
  const res = await API.get(`/api/v1/epcr/charts/${chartId}/completeness`, { headers: aiHeaders() });
  const data = asJsonObject(res.data);
  const missing = Array.isArray(data.missing) ? data.missing.map((item) => asJsonObject(item)) : [];
  const scoreRaw = asNumber(data.score) ?? 0;
  const score = scoreRaw > 1 ? scoreRaw / 100 : scoreRaw;
  return {
    ...data,
    score,
    missing_fields: missing.map((m) => asString(m.label || m.field_path)).filter((v) => v.length > 0),
    critical_missing: missing
      .filter((m) => asString(m.severity).toLowerCase() === 'error')
      .map((m) => asString(m.label || m.field_path))
      .filter((v) => v.length > 0),
    warnings: missing
      .filter((m) => asString(m.severity).toLowerCase() !== 'error')
      .map((m) => asString(m.label || m.field_path))
      .filter((v) => v.length > 0),
  };
}

export async function submitEPCRChart(chartId: string) {
  const res = await API.post(`/api/v1/epcr/charts/${chartId}/submit`, {}, { headers: aiHeaders() });
  return res.data;
}

export async function lockEPCRChart(chartId: string) {
  const res = await API.post(`/api/v1/clinical/charts/${chartId}/lock`, {}, { headers: aiHeaders() });
  return res.data;
}

// ── Staffing / Personnel ──────────────────────────────────────────────────────

export async function getStaffingReadiness() {
  const res = await API.get('/api/v1/staffing/readiness', { headers: aiHeaders() });
  return res.data;
}

export async function getCrewQualifications(crewMemberId: string) {
  const res = await API.get(`/api/v1/staffing/crew/${crewMemberId}/qualifications`, { headers: aiHeaders() });
  return res.data;
}

export async function addCrewQualification(crewMemberId: string, payload: Record<string, unknown>) {
  const res = await API.post(`/api/v1/staffing/crew/${crewMemberId}/qualifications`, payload, { headers: aiHeaders() });
  return res.data;
}

export async function getCrewAvailability(crewMemberId: string) {
  const res = await API.get(`/api/v1/staffing/crew/${crewMemberId}/availability`, { headers: aiHeaders() });
  return res.data;
}

export async function updateCrewAvailability(crewMemberId: string, payload: Record<string, unknown>) {
  const res = await API.post(`/api/v1/staffing/crew/${crewMemberId}/availability`, payload, { headers: aiHeaders() });
  return res.data;
}

export async function flagCrewFatigue(crewMemberId: string, payload: Record<string, unknown>) {
  const res = await API.post(`/api/v1/staffing/crew/${crewMemberId}/fatigue-flag`, payload, { headers: aiHeaders() });
  return res.data;
}

export async function clearCrewFatigue(crewMemberId: string, payload: Record<string, unknown>) {
  const res = await API.post(`/api/v1/staffing/crew/${crewMemberId}/fatigue-flag/clear`, payload, { headers: aiHeaders() });
  return res.data;
}

export async function getStaffingAuditLog() {
  const res = await API.get('/api/v1/staffing/audit', { headers: aiHeaders() });
  return res.data;
}

// ── Scheduling Extended ──────────────────────────────────────────────────────

export async function getSchedulingCoverageDashboard() {
  const res = await API.get('/api/v1/scheduling/coverage/dashboard', { headers: aiHeaders() });
  return res.data;
}

export async function getExpiringCredentials() {
  const res = await API.get('/api/v1/scheduling/credentials/expiring', { headers: aiHeaders() });
  return res.data;
}

export async function getSchedulingAIDrafts() {
  const res = await API.get('/api/v1/scheduling/ai/drafts', { headers: aiHeaders() });
  return res.data;
}

export async function approveSchedulingAIDraft(draftId: string) {
  const res = await API.post(`/api/v1/scheduling/ai/drafts/${draftId}/approve`, {}, { headers: aiHeaders() });
  return res.data;
}

export async function getSchedulingFatigueReport() {
  const res = await API.get('/api/v1/scheduling/fatigue/report', { headers: aiHeaders() });
  return res.data;
}

export async function listSchedulingSwaps(params?: Record<string, string>) {
  const res = await API.get('/api/v1/scheduling/swaps', { headers: aiHeaders(), params });
  return res.data;
}

export async function requestSchedulingAIDraft(payload: Record<string, unknown>) {
  const res = await API.post('/api/v1/scheduling/ai/draft', payload, { headers: aiHeaders() });
  return res.data;
}

// ── TRIP (Wisconsin Tax Refund Intercept Program) ────────────────────────────

export async function getTRIPSettings() {
  const res = await API.get('/api/v1/trip/settings', { headers: csHeaders() });
  return res.data;
}

export async function saveTRIPSettings(payload: Record<string, unknown>) {
  const res = await API.post('/api/v1/trip/settings', payload, { headers: csHeaders() });
  return res.data;
}

export async function listTRIPDebts(params?: Record<string, string>) {
  const res = await API.get('/api/v1/trip/debts', { headers: csHeaders(), params });
  return res.data;
}

export async function buildTRIPCandidates() {
  const res = await API.post('/api/v1/trip/debts/build-candidates', {}, { headers: csHeaders() });
  return res.data;
}

export async function updateTRIPDebt(debtId: string, payload: Record<string, unknown>) {
  const res = await API.patch(`/api/v1/trip/debts/${debtId}`, payload, { headers: csHeaders() });
  return res.data;
}

export async function generateTRIPExport() {
  const res = await API.post('/api/v1/trip/exports/generate', {}, { headers: csHeaders() });
  return res.data;
}

export async function listTRIPExports() {
  const res = await API.get('/api/v1/trip/exports', { headers: csHeaders() });
  return res.data;
}

export async function importTRIPRejects(payload: Record<string, unknown>) {
  const res = await API.post('/api/v1/trip/rejects/import', payload, { headers: csHeaders() });
  return res.data;
}

export async function importTRIPPostings(payload: Record<string, unknown>) {
  const res = await API.post('/api/v1/trip/postings/import', payload, { headers: csHeaders() });
  return res.data;
}

export async function getTRIPReconciliation() {
  const res = await API.get('/api/v1/trip/reports/reconciliation', { headers: csHeaders() });
  return res.data;
}

// ── Billing Command Center ────────────────────────────────────────────────────

export async function getBillingCommandDashboard() {
  const res = await API.get('/api/v1/billing-command/dashboard', { headers: csHeaders() });
  return res.data;
}

export async function getBillingKPIs() {
  const res = await API.get('/api/v1/billing-command/billing-kpis', { headers: csHeaders() });
  return res.data;
}

export async function getDenialHeatmap() {
  const res = await API.get('/api/v1/billing-command/denial-heatmap', { headers: csHeaders() });
  return res.data;
}

export async function getPayerPerformance() {
  const res = await API.get('/api/v1/billing-command/payer-performance', { headers: csHeaders() });
  return res.data;
}

export async function getRevenueLeakage() {
  const res = await API.get('/api/v1/billing-command/revenue-leakage', { headers: csHeaders() });
  return res.data;
}

export async function getBillingHealth() {
  const res = await API.get('/api/v1/billing-command/billing-health', { headers: csHeaders() });
  return res.data;
}

export async function getBillingExecutiveSummary() {
  const res = await API.get('/api/v1/billing-command/executive-summary', { headers: csHeaders() });
  return res.data;
}

export async function getFounderBillingVoiceSummary() {
  const res = await API.get('/api/v1/founder/billing-voice/summary', { headers: csHeaders() });
  return res.data;
}

export async function listFounderBillingVoiceEscalations(status = 'awaiting_human', limit = 50) {
  const res = await API.get('/api/v1/founder/billing-voice/escalations', {
    headers: csHeaders(),
    params: { status, limit },
  });
  return res.data;
}

export async function takeoverFounderBillingVoiceEscalation(escalationId: string, payload?: { channel?: string; notes?: string }) {
  const res = await API.post(`/api/v1/founder/billing-voice/escalations/${escalationId}/takeover`, payload || {}, { headers: csHeaders() });
  return res.data;
}

export interface FounderBillingVoiceConfigApi {
  voice_mode: 'human_audio' | 'tts' | string;
  tts_voice: string;
  tts_language: string;
  tts_primary_engine?: 'xtts' | 'piper' | string;
  tts_fallback_engine?: 'xtts' | 'piper' | string;
  stt_engine?: 'faster_whisper' | string;
  stt_model_size?: string;
  telephony_engine?: 'telnyx' | 'asterisk' | 'freeswitch' | string;
  emergency_forwarding_enabled?: boolean;
  emergency_forward_reasons?: string[];
  prompts: Record<string, string>;
  audio_urls: Record<string, string>;
}

export interface FounderBillingVoiceConfigResponseApi {
  config: FounderBillingVoiceConfigApi;
}

export interface FounderBillingVoiceVoicemailApi {
  id: string;
  caller_phone_number: string | null;
  received_at: string | null;
  tenant_id: string | null;
  statement_id: string | null;
  account_id: string | null;
  state: string;
  urgency: string;
  risk_level: string;
  risk_score: number;
  transcript_preview: string;
  intent_code: string | null;
}

export interface FounderBillingVoiceCallbackApi {
  id: string;
  voicemail_id: string | null;
  tenant_id: string | null;
  callback_phone: string | null;
  callback_state: string;
  sla_due_at: string | null;
  priority: string;
  reason: string | null;
  created_at: string | null;
  updated_at: string | null;
}

export interface FounderBillingVoiceBoardResponseApi<T> {
  items: T[];
}

export async function getFounderBillingVoiceConfig(): Promise<FounderBillingVoiceConfigResponseApi> {
  const res = await API.get('/api/v1/founder/billing-voice/config', { headers: csHeaders() });
  return res.data as FounderBillingVoiceConfigResponseApi;
}

export async function updateFounderBillingVoiceConfig(
  payload: FounderBillingVoiceConfigApi
): Promise<FounderBillingVoiceConfigResponseApi> {
  const res = await API.put('/api/v1/founder/billing-voice/config', payload, { headers: csHeaders() });
  return res.data as FounderBillingVoiceConfigResponseApi;
}

export async function renderFounderBillingVoicePrompts(payload: {
  preferred_engine?: 'xtts' | 'piper' | string;
}): Promise<FounderBillingVoiceConfigResponseApi> {
  const res = await API.post('/api/v1/founder/billing-voice/config/render-prompts', payload, { headers: csHeaders() });
  return res.data as FounderBillingVoiceConfigResponseApi;
}

export async function listFounderBillingVoiceVoicemails(
  limit = 50
): Promise<FounderBillingVoiceBoardResponseApi<FounderBillingVoiceVoicemailApi>> {
  const res = await API.get('/api/v1/founder/billing-voice/voicemails', {
    headers: csHeaders(),
    params: { limit },
  });
  return res.data as FounderBillingVoiceBoardResponseApi<FounderBillingVoiceVoicemailApi>;
}

export async function listFounderBillingVoiceCallbacks(
  limit = 50
): Promise<FounderBillingVoiceBoardResponseApi<FounderBillingVoiceCallbackApi>> {
  const res = await API.get('/api/v1/founder/billing-voice/callbacks', {
    headers: csHeaders(),
    params: { limit },
  });
  return res.data as FounderBillingVoiceBoardResponseApi<FounderBillingVoiceCallbackApi>;
}

export async function getBillingAlerts() {
  const res = await API.get('/api/v1/billing-command/billing-alerts', { headers: csHeaders() });
  return res.data;
}

export async function getPayerMix() {
  const res = await API.get('/api/v1/billing-command/payer-mix', { headers: csHeaders() });
  return res.data;
}

export async function getRevenueTrend() {
  const res = await API.get('/api/v1/billing-command/revenue-trend', { headers: csHeaders() });
  return res.data;
}

export async function getARConcentrationRisk() {
  const res = await API.get('/api/v1/billing-command/ar-concentration-risk', { headers: csHeaders() });
  return res.data;
}

export async function getClaimThroughput() {
  const res = await API.get('/api/v1/billing-command/claim-throughput', { headers: csHeaders() });
  return res.data;
}

export async function getAppealSuccessRate() {
  const res = await API.get('/api/v1/billing-command/appeal-success', { headers: csHeaders() });
  return res.data;
}

export async function getFraudAnomalies() {
  const res = await API.get('/api/v1/billing-command/fraud-anomaly', { headers: csHeaders() });
  return res.data;
}

export async function batchResubmitClaims(payload: Record<string, unknown>) {
  const res = await API.post('/api/v1/billing-command/batch-resubmit', payload, { headers: csHeaders() });
  return res.data;
}

export async function draftAppeal(payload: Record<string, unknown>) {
  const res = await API.post('/api/v1/billing-command/appeal-draft', payload, { headers: csHeaders() });
  return res.data;
}

export async function getDenialPredictor(payload: Record<string, unknown>) {
  const res = await API.post('/api/v1/billing-command/denial-predictor', payload, { headers: csHeaders() });
  return res.data;
}

export async function getStripeReconciliation() {
  const res = await API.get('/api/v1/billing-command/stripe-reconciliation', { headers: csHeaders() });
  return res.data;
}

export async function getChurnRisk() {
  const res = await API.get('/api/v1/billing-command/churn-risk', { headers: csHeaders() });
  return res.data;
}

export async function getDuplicateDetection() {
  const res = await API.get('/api/v1/billing-command/duplicate-detection', { headers: csHeaders() });
  return res.data;
}

export async function getTenantBillingRanking() {
  const res = await API.get('/api/v1/billing-command/tenant-billing-ranking', { headers: csHeaders() });
  return res.data;
}

export async function getRevenueByServiceLevel() {
  const res = await API.get('/api/v1/billing-command/revenue-by-service-level', { headers: csHeaders() });
  return res.data;
}

export async function getModifierImpact() {
  const res = await API.get('/api/v1/billing-command/modifier-impact', { headers: csHeaders() });
  return res.data;
}

// ── Legal Requests Command ───────────────────────────────────────────────────

export type LegalRequestType = 'hipaa_roi' | 'subpoena' | 'court_order';
export type LegalRequestStatus =
  | 'received'
  | 'triage_complete'
  | 'missing_docs'
  | 'under_review'
  | 'packet_building'
  | 'delivered'
  | 'closed';

export interface LegalMissingItemCard {
  code: string;
  title: string;
  detail: string;
  severity: 'high' | 'medium' | 'low';
}

export interface LegalChecklistItem {
  code: string;
  label: string;
  required: boolean;
  satisfied: boolean;
}

export interface LegalTriageSummary {
  classification: LegalRequestType;
  classification_confidence: number;
  likely_invalid_or_incomplete: boolean;
  urgency_level: 'low' | 'normal' | 'high' | 'critical';
  deadline_risk: 'none' | 'watch' | 'high';
  mismatch_signals: string[];
  rationale: string;
}

export interface LegalIntakePayload {
  request_type?: LegalRequestType;
  requesting_party: string;
  requester_name: string;
  requesting_entity?: string;
  requester_category?:
  | 'patient'
  | 'patient_representative'
  | 'attorney'
  | 'insurance'
  | 'government_agency'
  | 'employer'
  | 'other_third_party_manual_review';
  patient_first_name?: string;
  patient_last_name?: string;
  patient_dob?: string;
  mrn?: string;
  csn?: string;
  date_range_start?: string;
  date_range_end?: string;
  request_documents?: string[];
  delivery_preference?: 'secure_one_time_link' | 'encrypted_email' | 'manual_pickup';
  requested_page_count?: number;
  jurisdiction_state?: string;
  print_mail_requested?: boolean;
  rush_requested?: boolean;
  deadline_at?: string;
  notes?: string;
}

export interface LegalIntakeResponse {
  request_id: string;
  intake_token: string;
  status: LegalRequestStatus;
  request_type: LegalRequestType;
  triage_summary: LegalTriageSummary;
  missing_items: LegalMissingItemCard[];
  required_document_checklist: LegalChecklistItem[];
  workflow_state?: string;
  payment_status?: string;
  payment_required?: boolean;
  margin_status?: string;
  fee_quote?: Record<string, unknown>;
}

export interface LegalPricingQuoteResponse {
  request_id: string;
  currency: string;
  total_due_cents: number;
  agency_payout_cents: number;
  platform_fee_cents: number;
  margin_status: string;
  payment_required: boolean;
  workflow_state: string;
  requester_category: string;
  delivery_mode: 'secure_digital' | 'print_and_mail' | 'manual_pickup';
  line_items: Array<{ code: string; label: string; amount_cents: number; payee: string; note?: string }>;
  costs: {
    estimated_processor_fee_cents: number;
    estimated_labor_cost_cents: number;
    estimated_lob_cost_cents: number;
    estimated_platform_margin_cents: number;
  };
  hold_reasons: string[];
}

export interface LegalCheckoutResponse {
  request_id: string;
  payment_id: string;
  payment_status: string;
  workflow_state: string;
  checkout_url: string;
  checkout_session_id: string;
  connected_account_id: string;
  amount_due_cents: number;
  agency_payout_cents: number;
  platform_fee_cents: number;
}

export interface LegalPaymentRecord {
  payment_id: string;
  request_id: string;
  status: string;
  amount_due_cents: number;
  amount_collected_cents: number;
  platform_fee_cents: number;
  agency_payout_cents: number;
  currency: string;
  stripe_connected_account_id?: string;
  stripe_checkout_session_id?: string;
  stripe_payment_intent_id?: string;
  check_reference?: string;
  paid_at?: string;
  failed_at?: string;
  refunded_at?: string;
}

export interface LegalQueueItem {
  id: string;
  request_type: LegalRequestType;
  status: LegalRequestStatus;
  requester_name: string;
  requesting_party: string;
  requesting_entity?: string;
  deadline_at?: string;
  deadline_risk: 'none' | 'watch' | 'high';
  missing_count: number;
  redaction_mode: string;
  created_at: string;
  updated_at: string;
}

export interface LegalSummary {
  total_open: number;
  lane_counts: Record<string, number>;
  urgent_deadlines: number;
  high_risk_requests: number;
}

export async function classifyLegalRequest(payload: {
  request_type?: LegalRequestType;
  notes?: string;
  request_documents?: string[];
  deadline_at?: string;
  date_range_start?: string;
  date_range_end?: string;
}) {
  const res = await API.post('/api/v1/legal-requests/classify', payload);
  return res.data;
}

export async function createLegalRequestIntake(payload: LegalIntakePayload): Promise<LegalIntakeResponse> {
  const res = await API.post('/api/v1/legal-requests/intake', payload);
  return res.data as LegalIntakeResponse;
}

export async function createLegalUploadPresign(
  requestId: string,
  payload: { intake_token: string; document_kind: string; file_name: string; content_type: string }
) {
  const res = await API.post(`/api/v1/legal-requests/${requestId}/uploads/presign`, payload);
  return res.data;
}

export async function uploadLegalDocumentToPresignedUrl(uploadUrl: string, file: File): Promise<void> {
  await fetch(uploadUrl, {
    method: 'PUT',
    headers: { 'Content-Type': file.type },
    body: file,
  });
}

export async function completeLegalUpload(
  requestId: string,
  payload: { intake_token: string; upload_id: string; byte_size: number; checksum_sha256?: string }
) {
  const res = await API.post(`/api/v1/legal-requests/${requestId}/uploads/complete`, payload);
  return res.data;
}

export async function previewLegalPricingQuote(
  requestId: string,
  payload: {
    intake_token: string;
    requested_page_count?: number;
    print_mail_requested?: boolean;
    rush_requested?: boolean;
  }
): Promise<LegalPricingQuoteResponse> {
  const res = await API.post(`/api/v1/legal-requests/${requestId}/pricing/quote`, payload);
  return res.data as LegalPricingQuoteResponse;
}

export async function createLegalPaymentCheckout(
  requestId: string,
  payload: { intake_token: string; success_url?: string; cancel_url?: string }
): Promise<LegalCheckoutResponse> {
  const res = await API.post(`/api/v1/legal-requests/${requestId}/payment/checkout`, payload);
  return res.data as LegalCheckoutResponse;
}

export async function getFounderLegalSummary(): Promise<LegalSummary> {
  const res = await API.get('/api/v1/legal-requests/founder/summary', { headers: aiHeaders() });
  return res.data as LegalSummary;
}

export async function getFounderLegalQueue(lane?: string, limit = 100): Promise<LegalQueueItem[]> {
  const res = await API.get('/api/v1/legal-requests/founder/queue', {
    headers: aiHeaders(),
    params: { lane, limit },
  });
  return Array.isArray(res.data) ? (res.data as LegalQueueItem[]) : [];
}

export async function getFounderLegalRequestDetail(requestId: string) {
  const res = await API.get(`/api/v1/legal-requests/founder/requests/${requestId}`, {
    headers: aiHeaders(),
  });
  return res.data;
}

export async function reviewFounderLegalRequest(
  requestId: string,
  payload: {
    authority_valid: boolean;
    identity_verified: boolean;
    completeness_valid: boolean;
    document_sufficient: boolean;
    minimum_necessary_scope: boolean;
    redaction_mode:
    | 'court_safe_minimum_necessary'
    | 'expanded_disclosure_reviewed'
    | 'expanded_disclosure_patient_authorized'
    | 'expanded_disclosure_legal_override';
    delivery_method: 'secure_one_time_link' | 'encrypted_email' | 'manual_pickup';
    decision: 'approve' | 'request_more_docs' | 'reject';
    decision_notes?: string;
  }
) {
  const res = await API.post(`/api/v1/legal-requests/founder/requests/${requestId}/review`, payload, {
    headers: aiHeaders(),
  });
  return res.data;
}

export async function buildFounderLegalPacket(requestId: string) {
  const res = await API.post(`/api/v1/legal-requests/founder/requests/${requestId}/packet-build`, {}, {
    headers: aiHeaders(),
  });
  return res.data;
}

export async function createFounderLegalDeliveryLink(
  requestId: string,
  payload: { expires_in_hours?: number; recipient_hint?: string }
) {
  const res = await API.post(`/api/v1/legal-requests/founder/requests/${requestId}/delivery-links`, payload, {
    headers: aiHeaders(),
  });
  return res.data;
}

export async function revokeFounderLegalDeliveryLink(linkId: string) {
  await API.post(`/api/v1/legal-requests/founder/delivery-links/${linkId}/revoke`, {}, {
    headers: aiHeaders(),
  });
}

export async function closeFounderLegalRequest(requestId: string) {
  const res = await API.post(`/api/v1/legal-requests/founder/requests/${requestId}/close`, {}, {
    headers: aiHeaders(),
  });
  return res.data;
}

export async function getFounderLegalPaymentRecord(requestId: string): Promise<LegalPaymentRecord> {
  const res = await API.get(`/api/v1/legal-requests/founder/requests/${requestId}/payment`, {
    headers: aiHeaders(),
  });
  return res.data as LegalPaymentRecord;
}

export async function markFounderLegalCheckReceived(
  requestId: string,
  payload: { check_reference: string }
): Promise<LegalPaymentRecord> {
  const res = await API.post(`/api/v1/legal-requests/founder/requests/${requestId}/payment/check-received`, payload, {
    headers: aiHeaders(),
  });
  return res.data as LegalPaymentRecord;
}

export async function consumeLegalDeliveryLink(token: string) {
  const res = await API.get(`/api/v1/legal-requests/delivery/${token}`);
  return res.data;
}

// ── Office Ally Clearinghouse: Eligibility / Claim Status / ERA ──────────

export async function submitEligibilityInquiry(payload: {
  patient_id: string;
  member_id: string;
  payer_id?: string;
  service_date?: string;
}) {
  const res = await API.post('/api/v1/billing/eligibility/inquire', payload, {
    headers: aiHeaders(),
  });
  return res.data;
}

export async function pollEligibilityResponses() {
  const res = await API.post('/api/v1/billing/eligibility/poll', {}, {
    headers: aiHeaders(),
  });
  return res.data;
}

export async function submitClaimStatusInquiry(payload: {
  claim_id: string;
  member_id?: string;
  payer_id?: string;
}) {
  const res = await API.post('/api/v1/billing/claims/status-inquiry', payload, {
    headers: aiHeaders(),
  });
  return res.data;
}

export async function pollClaimStatusResponses() {
  const res = await API.post('/api/v1/billing/claims/status-poll', {}, {
    headers: aiHeaders(),
  });
  return res.data;
}

export async function pollERAFiles() {
  const res = await API.post('/api/v1/billing/eras/poll', {}, {
    headers: aiHeaders(),
  });
  return res.data;
}

// ── Release Readiness Gate ───────────────────────────────────────────────

export async function getReleaseReadiness() {
  const res = await API.get('/api/v1/platform/release-readiness', {
    headers: aiHeaders(),
  });
  return res.data;
}

// ── Margin Risk Analytics ────────────────────────────────────────────────

export async function getMarginRiskByTenant() {
  const res = await API.get('/api/v1/billing-command/margin-risk', {
    headers: aiHeaders(),
  });
  return res.data;
}

// ── Telnyx CNAM / Voice Operations ──────────────────────────────────────

export async function getTelnyxCNAMList() {
  const res = await API.get('/api/v1/founder/billing-voice/cnam/list', {
    headers: aiHeaders(),
  });
  return res.data;
}

export async function registerTelnyxCNAM(payload: {
  phone_number: string;
  display_name: string;
}) {
  const res = await API.post('/api/v1/founder/billing-voice/cnam/register', payload, {
    headers: aiHeaders(),
  });
  return res.data;
}

export async function deleteTelnyxCNAM(phoneNumber: string) {
  const res = await API.delete(`/api/v1/founder/billing-voice/cnam/${encodeURIComponent(phoneNumber)}`, {
    headers: aiHeaders(),
  });
  return res.data;
}

// ── Pricing Catalog / Pricebook ─────────────────────────────────────────

export async function listPricebookEntries() {
  const res = await API.get('/api/v1/pricebook/entries', {
    headers: aiHeaders(),
  });
  return res.data;
}

export async function createPricebookEntry(payload: {
  code: string;
  description: string;
  unit_price_cents: number;
  category?: string;
}) {
  const res = await API.post('/api/v1/pricebook/entries', payload, {
    headers: aiHeaders(),
  });
  return res.data;
}

export async function updatePricebookEntry(entryId: string, payload: {
  description?: string;
  unit_price_cents?: number;
  category?: string;
}) {
  const res = await API.patch(`/api/v1/pricebook/entries/${entryId}`, payload, {
    headers: aiHeaders(),
  });
  return res.data;
}

// ── Public Signup / Onboarding (Unauthenticated) ──────────────────────────

export interface PublicOnboardingLegalPacketCreatePayload {
  application_id: string;
  signer_email: string;
  signer_name: string;
  agency_name: string;
}

export interface PublicOnboardingLegalPacketSignPayload {
  signer_name: string;
  consents: {
    msa: boolean;
    baa: boolean;
    authority: boolean;
  };
  ip_address: string;
  user_agent: string;
  signature_text: string;
}

export async function getPublicPricingCatalog<T = Record<string, unknown>>() {
  try {
    const res = await API.get('/public/pricing/catalog');
    return res.data as T;
  } catch (error) {
    throw new Error(asErrorMessage(error, 'Failed to load pricing'));
  }
}

export async function lookupPublicOnboardingNpi<T = Record<string, unknown>>(npiNumber: string) {
  try {
    const res = await API.get(`/public/onboarding/nppes/lookup/${encodeURIComponent(npiNumber)}`);
    return res.data as T;
  } catch (error) {
    throw new Error(asErrorMessage(error, 'NPI lookup failed'));
  }
}

export async function submitPublicOnboardingApplication<T = Record<string, unknown>>(payload: Record<string, unknown>) {
  try {
    const res = await API.post('/public/onboarding/apply', payload, {
      headers: { 'Content-Type': 'application/json' },
    });
    return res.data as T;
  } catch (error) {
    throw new Error(asErrorMessage(error, 'Failed to submit onboarding application'));
  }
}

export async function createPublicOnboardingLegalPacket<T = Record<string, unknown>>(
  payload: PublicOnboardingLegalPacketCreatePayload
) {
  try {
    const res = await API.post('/public/onboarding/legal/packet/create', payload, {
      headers: { 'Content-Type': 'application/json' },
    });
    return res.data as T;
  } catch (error) {
    throw new Error(asErrorMessage(error, 'Failed to initialize legal packet'));
  }
}

export async function signPublicOnboardingLegalPacket<T = Record<string, unknown>>(
  packetId: string,
  payload: PublicOnboardingLegalPacketSignPayload
) {
  try {
    const res = await API.post(`/public/onboarding/legal/packet/${packetId}/sign`, payload, {
      headers: { 'Content-Type': 'application/json' },
    });
    return res.data as T;
  } catch (error) {
    throw new Error(asErrorMessage(error, 'Failed to sign legal packet'));
  }
}

export async function startPublicOnboardingCheckout<T = Record<string, unknown>>(payload: { application_id: string }) {
  try {
    const res = await API.post('/public/onboarding/checkout/start', payload, {
      headers: { 'Content-Type': 'application/json' },
    });
    return res.data as T;
  } catch (error) {
    throw new Error(asErrorMessage(error, 'Failed to start checkout session'));
  }
}

export async function getPublicOnboardingStatus<T = Record<string, unknown>>(applicationId: string) {
  try {
    const res = await API.get(`/public/onboarding/status/${applicationId}`);
    return res.data as T;
  } catch (error) {
    throw new Error(asErrorMessage(error, 'Unable to retrieve onboarding status'));
  }
}

export async function listPublicSystems<T = Array<Record<string, unknown>>>() {
  try {
    const res = await API.get('/api/v1/systems', {
      headers: {},
    });
    return res.data as T;
  } catch (error) {
    throw new Error(asErrorMessage(error, 'Failed to load systems'));
  }
}

// ── Tenant Onboarding ───────────────────────────────────────────────────

export async function getOnboardingStatus(tenantId: string) {
  const res = await API.get(`/api/v1/onboarding/${tenantId}/status`, {
    headers: aiHeaders(),
  });
  return res.data;
}

export async function advanceOnboardingStep(tenantId: string, payload: {
  step: string;
  data?: Record<string, unknown>;
}) {
  const res = await API.post(`/api/v1/onboarding/${tenantId}/advance`, payload, {
    headers: aiHeaders(),
  });
  return res.data;
}

// ── Visibility Rule Maker ──────────────────────────────────────────────────

type VisibilityMethod = 'GET' | 'POST' | 'DELETE';

async function visibilityRequest<T>(
  path: string,
  method: VisibilityMethod = 'GET',
  body?: Record<string, unknown>
): Promise<T | null> {
  const token = typeof window !== 'undefined' ? (localStorage.getItem('access_token') || '') : '';
  const headers: Record<string, string> = {
    'Content-Type': 'application/json',
    ...(token ? { Authorization: `Bearer ${token}` } : {}),
  };

  const res = await API.request<T>({
    url: path,
    method,
    headers,
    data: body,
    validateStatus: () => true,
  });

  if (res.status < 200 || res.status >= 300) {
    return null;
  }
  return res.data;
}

export async function getVisibilityDashboardBundle() {
  const [
    dashboard,
    rules,
    viewModes,
    moduleGates,
    phiFields,
    roleMatrix,
    killSwitchStatus,
    accessScore,
    heatmap,
    endpointRestrictions,
    alerts,
    anomalies,
    approvals,
    complianceLocks,
    timeWindows,
    elevatedAccess,
    policies,
  ] = await Promise.all([
    visibilityRequest<unknown>('/api/v1/visibility/dashboard'),
    visibilityRequest<unknown>('/api/v1/visibility/rules'),
    visibilityRequest<unknown>('/api/v1/visibility/view-modes'),
    visibilityRequest<unknown>('/api/v1/visibility/module-gates'),
    visibilityRequest<unknown>('/api/v1/visibility/phi-fields'),
    visibilityRequest<unknown>('/api/v1/visibility/role-matrix'),
    visibilityRequest<unknown>('/api/v1/visibility/kill-switch/status'),
    visibilityRequest<unknown>('/api/v1/visibility/access-score'),
    visibilityRequest<unknown>('/api/v1/visibility/heatmap'),
    visibilityRequest<unknown>('/api/v1/visibility/endpoint-restrictions'),
    visibilityRequest<unknown>('/api/v1/visibility/access-alerts'),
    visibilityRequest<unknown>('/api/v1/visibility/anomaly-events'),
    visibilityRequest<unknown>('/api/v1/visibility/approval-requests'),
    visibilityRequest<unknown>('/api/v1/visibility/compliance-lock/status'),
    visibilityRequest<unknown>('/api/v1/visibility/time-windows'),
    visibilityRequest<unknown>('/api/v1/visibility/elevated-access'),
    visibilityRequest<unknown>('/api/v1/visibility/policies'),
  ]);

  return {
    dashboard,
    rules,
    viewModes,
    moduleGates,
    phiFields,
    roleMatrix,
    killSwitchStatus,
    accessScore,
    heatmap,
    endpointRestrictions,
    alerts,
    anomalies,
    approvals,
    complianceLocks,
    timeWindows,
    elevatedAccess,
    policies,
  };
}

export async function createVisibilityRule<T = Record<string, unknown>>(payload: Record<string, unknown>) {
  return visibilityRequest<T>('/api/v1/visibility/rules', 'POST', payload);
}

export async function deleteVisibilityRule(ruleId: string) {
  return visibilityRequest<Record<string, unknown>>(`/api/v1/visibility/rules/${ruleId}`, 'DELETE');
}

export async function evaluateVisibilityContext<T = Record<string, unknown>>(payload: Record<string, unknown>) {
  return visibilityRequest<T>('/api/v1/visibility/evaluate', 'POST', payload);
}

export async function sandboxTestVisibilityRule<T = Record<string, unknown>>(payload: Record<string, unknown>) {
  return visibilityRequest<T>('/api/v1/visibility/rules/sandbox-test', 'POST', payload);
}

export async function checkVisibilityZeroTrust<T = Record<string, unknown>>(payload: Record<string, unknown>) {
  return visibilityRequest<T>('/api/v1/visibility/zero-trust/check', 'POST', payload);
}

export async function previewVisibilityRedaction<T = Record<string, unknown>>(payload: Record<string, unknown>) {
  return visibilityRequest<T>('/api/v1/visibility/redaction-preview', 'POST', payload);
}

export async function deidentifyVisibilityRecord<T = Record<string, unknown>>(payload: Record<string, unknown>) {
  return visibilityRequest<T>('/api/v1/visibility/deidentify', 'POST', payload);
}

export async function simulateVisibilityRole<T = Record<string, unknown>>(payload: Record<string, unknown>) {
  return visibilityRequest<T>('/api/v1/visibility/role-simulation', 'POST', payload);
}

export async function checkVisibilityDataMinimization<T = Record<string, unknown>>(payload: Record<string, unknown>) {
  return visibilityRequest<T>('/api/v1/visibility/data-minimization/check', 'POST', payload);
}

export async function setVisibilityKillSwitch<T = Record<string, unknown>>(payload: { activated: boolean; reason: string }) {
  return visibilityRequest<T>('/api/v1/visibility/kill-switch', 'POST', payload);
}

// ── EDI Batch Operations ────────────────────────────────────────────────

export async function generateEDIBatch(payload: {
  claim_ids: string[];
  submitter_config?: Record<string, unknown>;
}) {
  const res = await API.post('/api/v1/edi/batches/generate', payload, {
    headers: aiHeaders(),
  });
  return res.data;
}

export async function listEDIBatches(limit = 50, offset = 0) {
  const res = await API.get(`/api/v1/edi/batches?limit=${limit}&offset=${offset}`, {
    headers: aiHeaders(),
  });
  return res.data;
}

export async function submitEDIBatchSFTP(batchId: string) {
  const res = await API.post(`/api/v1/edi/batches/${batchId}/submit-sftp`, {}, {
    headers: aiHeaders(),
  });
  return res.data;
}

export async function ingestEDI999(payload: {
  x12_content: string;
  batch_id: string;
}) {
  const res = await API.post('/api/v1/edi/ingest/999', payload, {
    headers: aiHeaders(),
  });
  return res.data;
}

export async function ingestEDI835(payload: { x12_content: string }) {
  const res = await API.post('/api/v1/edi/ingest/835', payload, {
    headers: aiHeaders(),
  });
  return res.data;
}

// ── Document Management ────────────────────────────────────────────────────

export async function getDocumentUploadUrl(payload: { filename: string; content_type: string }) {
  const res = await API.post('/api/v1/documents/upload-url', payload, { headers: aiHeaders() });
  return res.data;
}

export async function processDocument(payload: { document_id: string; s3_key: string }) {
  const res = await API.post('/api/v1/documents/process', payload, { headers: aiHeaders() });
  return res.data;
}

export async function getDocument(documentId: string) {
  const res = await API.get(`/api/v1/documents/${documentId}`, { headers: aiHeaders() });
  return res.data;
}

export async function attachDocumentMetadata(documentId: string, payload: { s3_key: string; filename: string; content_type: string }) {
  const res = await API.post(`/api/v1/documents/${documentId}/attach`, payload, { headers: aiHeaders() });
  return res.data;
}

export async function refreshDocumentExtraction(extractionId: string) {
  const res = await API.post(`/api/v1/documents/extractions/${extractionId}/refresh`, {}, { headers: aiHeaders() });
  return res.data;
}

// ── Template Management ────────────────────────────────────────────────────

export async function listTemplates(params?: Record<string, string>) {
  const res = await API.get('/api/v1/templates', { headers: aiHeaders(), params });
  return res.data;
}

export async function createTemplate(payload: Record<string, unknown>) {
  const res = await API.post('/api/v1/templates', payload, { headers: aiHeaders() });
  return res.data;
}

export async function getTemplate(templateId: string) {
  const res = await API.get(`/api/v1/templates/${templateId}`, { headers: aiHeaders() });
  return res.data;
}

export async function updateTemplate(templateId: string, payload: Record<string, unknown>) {
  const res = await API.patch(`/api/v1/templates/${templateId}`, payload, { headers: aiHeaders() });
  return res.data;
}

export async function deleteTemplate(templateId: string) {
  const res = await API.delete(`/api/v1/templates/${templateId}`, { headers: aiHeaders() });
  return res.data;
}

export async function cloneTemplate(payload: { source_template_id: string; new_name?: string }) {
  const res = await API.post('/api/v1/templates/clone', payload, { headers: aiHeaders() });
  return res.data;
}

export async function getTemplateVersions(templateId: string) {
  const res = await API.get(`/api/v1/templates/${templateId}/versions`, { headers: aiHeaders() });
  return res.data;
}

export async function bulkGenerateTemplates(payload: { template_id: string; variable_sets: Record<string, unknown>[] }) {
  const res = await API.post('/api/v1/templates/bulk-generate', payload, { headers: aiHeaders() });
  return res.data;
}

export async function approveTemplate(templateId: string) {
  const res = await API.post(`/api/v1/templates/${templateId}/approve`, {}, { headers: aiHeaders() });
  return res.data;
}

// ── ROI Calculator ─────────────────────────────────────────────────────────

export async function calculateROI(payload: Record<string, unknown>) {
  const res = await API.post('/public/roi/calc', payload);
  return res.data;
}

export async function generateROIProposalPDF(payload: Record<string, unknown>) {
  const res = await API.post('/public/roi/proposal-pdf', payload);
  return res.data;
}

// ── System Health & Infrastructure ─────────────────────────────────────────

export async function getSystemHealthDashboard() {
  const res = await API.get('/api/v1/system-health/dashboard', { headers: aiHeaders() });
  return res.data;
}

export async function getSystemHealthServices() {
  const res = await API.get('/api/v1/system-health/services', { headers: aiHeaders() });
  return res.data;
}

export async function getSystemHealthMetricsCPU() {
  const res = await API.get('/api/v1/system-health/metrics/cpu', { headers: aiHeaders() });
  return res.data;
}

export async function getSystemHealthMetricsMemory() {
  const res = await API.get('/api/v1/system-health/metrics/memory', { headers: aiHeaders() });
  return res.data;
}

export async function getSystemHealthMetricsLatency() {
  const res = await API.get('/api/v1/system-health/metrics/api-latency', { headers: aiHeaders() });
  return res.data;
}

export async function getSystemHealthMetricsErrors() {
  const res = await API.get('/api/v1/system-health/metrics/error-rate', { headers: aiHeaders() });
  return res.data;
}

export async function getSystemHealthAlerts() {
  const res = await API.get('/api/v1/system-health/alerts', { headers: aiHeaders() });
  return res.data;
}

export async function createSystemHealthAlert(payload: Record<string, unknown>) {
  const res = await API.post('/api/v1/system-health/alerts', payload, { headers: aiHeaders() });
  return res.data;
}

export async function resolveSystemHealthAlert(alertId: string) {
  const res = await API.post(`/api/v1/system-health/alerts/${alertId}/resolve`, {}, { headers: aiHeaders() });
  return res.data;
}

export async function getSelfHealingRules() {
  const res = await API.get('/api/v1/system-health/self-healing/rules', { headers: aiHeaders() });
  return res.data;
}

export async function getSelfHealingAudit() {
  const res = await API.get('/api/v1/system-health/self-healing/audit', { headers: aiHeaders() });
  return res.data;
}

export async function getUptimeSLA() {
  const res = await API.get('/api/v1/system-health/uptime/sla', { headers: aiHeaders() });
  return res.data;
}

export async function getSSLExpiration() {
  const res = await API.get('/api/v1/system-health/ssl/expiration', { headers: aiHeaders() });
  return res.data;
}

export async function getBackupsStatus() {
  const res = await API.get('/api/v1/system-health/backups/status', { headers: aiHeaders() });
  return res.data;
}

export async function getCostBudget() {
  const res = await API.get('/api/v1/system-health/cost/budget', { headers: aiHeaders() });
  return res.data;
}

export async function getCostByTenant() {
  const res = await API.get('/api/v1/system-health/cost/by-tenant', { headers: aiHeaders() });
  return res.data;
}

export async function getIncidentPostmortems() {
  const res = await API.get('/api/v1/system-health/incident/postmortems', { headers: aiHeaders() });
  return res.data;
}

// ── Policy Governance ──────────────────────────────────────────────────────

export async function listPolicies() {
  const res = await API.get('/api/v1/policies', { headers: aiHeaders() });
  return res.data;
}

export async function createPolicy(payload: Record<string, unknown>) {
  const res = await API.post('/api/v1/policies', payload, { headers: aiHeaders() });
  return res.data;
}

export async function getPolicy(policyId: string) {
  const res = await API.get(`/api/v1/policies/${policyId}`, { headers: aiHeaders() });
  return res.data;
}

export async function updatePolicy(policyId: string, payload: Record<string, unknown>) {
  const res = await API.patch(`/api/v1/policies/${policyId}`, payload, { headers: aiHeaders() });
  return res.data;
}

export async function deletePolicy(policyId: string) {
  const res = await API.delete(`/api/v1/policies/${policyId}`, { headers: aiHeaders() });
  return res.data;
}

export async function getPolicyVersions(policyId: string) {
  const res = await API.get(`/api/v1/policies/${policyId}/versions`, { headers: aiHeaders() });
  return res.data;
}

export async function listPolicyApprovals(policyId: string) {
  const res = await API.get(`/api/v1/policies/${policyId}/approvals`, { headers: aiHeaders() });
  return res.data;
}

export async function requestPolicyApproval(policyId: string, payload: Record<string, unknown>) {
  const res = await API.post(`/api/v1/policies/${policyId}/approvals`, payload, { headers: aiHeaders() });
  return res.data;
}

export async function rollbackPolicy(policyId: string, versionNumber: number) {
  const res = await API.post(`/api/v1/policies/${policyId}/rollback/${versionNumber}`, {}, { headers: aiHeaders() });
  return res.data;
}

// ── CrewLink Field Operations ──────────────────────────────────────────────

export async function pushCrewPage(payload: { crew_ids: string[]; message: string; priority?: string }) {
  const res = await API.post('/api/v1/crewlink/page', payload, { headers: aiHeaders() });
  return res.data;
}

export async function respondCrewPage(payload: { page_id: string; response: string }) {
  const res = await API.post('/api/v1/crewlink/respond', payload, { headers: aiHeaders() });
  return res.data;
}

export async function getActiveCrewPages() {
  const res = await API.get('/api/v1/crewlink/pages/active', { headers: aiHeaders() });
  return res.data;
}

export async function updateMyCrewAvailability(payload: { status: string; note?: string }) {
  const res = await API.post('/api/v1/crewlink/availability/me', payload, { headers: aiHeaders() });
  return res.data;
}

// ── Patient Portal Extended ────────────────────────────────────────────────

export async function getPortalProfile() {
  const res = await API.get('/api/v1/portal/profile', { headers: aiHeaders() });
  return res.data;
}

export async function updatePortalProfile(payload: Record<string, unknown>) {
  const res = await API.patch('/api/v1/portal/profile', payload, { headers: aiHeaders() });
  return res.data;
}

export async function getPortalPaymentPlans() {
  const res = await API.get('/api/v1/portal/payment-plans', { headers: aiHeaders() });
  return res.data;
}

export async function requestPortalPaymentPlan(payload: { statement_id: string; proposed_monthly_amount: number; duration_months: number }) {
  const res = await API.post('/api/v1/portal/payment-plans', payload, { headers: aiHeaders() });
  return res.data;
}

export async function getPortalDocuments() {
  const res = await API.get('/api/v1/portal/documents', { headers: aiHeaders() });
  return res.data;
}

export async function getPortalNotifications() {
  const res = await API.get('/api/v1/portal/notifications', { headers: aiHeaders() });
  return res.data;
}

export async function markPortalNotificationsRead() {
  const res = await API.post('/api/v1/portal/notifications/read-all', {}, { headers: aiHeaders() });
  return res.data;
}

export async function getPortalActivity() {
  const res = await API.get('/api/v1/portal/activity', { headers: aiHeaders() });
  return res.data;
}

export async function submitPortalSupportRequest(payload: { subject: string; body: string; category?: string }) {
  const res = await API.post('/api/v1/portal/support', payload, { headers: aiHeaders() });
  return res.data;
}

export async function markPortalNotificationRead(notificationId: string) {
  const res = await API.post(`/api/v1/portal/notifications/${notificationId}/read`, {}, { headers: aiHeaders() });
  return res.data;
}

export async function uploadPortalDocument(formData: FormData) {
  const res = await API.post('/api/v1/portal/documents', formData, {
    headers: { ...aiHeaders(), 'Content-Type': 'multipart/form-data' },
  });
  return res.data;
}

export async function getPatientStatements(limit = 50) {
  const res = await API.get(`/api/v1/patient/statements?limit=${limit}`, { headers: aiHeaders() });
  return res.data;
}

export async function payStatement(statementId: string, payload: Record<string, unknown>) {
  const res = await API.post(`/api/v1/statements/${statementId}/pay`, payload, { headers: aiHeaders() });
  return res.data;
}

// ── Founder Copilot ────────────────────────────────────────────────────────

export async function sendFounderCopilotCommand(payload: { command: string; context?: Record<string, unknown> }) {
  const res = await API.post('/api/founder/copilot/command', payload, { headers: aiHeaders() });
  return res.data;
}

// ── Pricebook Extended ─────────────────────────────────────────────────────

export async function getPricebookCatalog() {
  const res = await API.get('/api/v1/pricebooks/catalog', { headers: aiHeaders() });
  return res.data;
}

export async function listPricebooks() {
  const res = await API.get('/api/v1/pricebooks/', { headers: aiHeaders() });
  return res.data;
}

export async function createPricebook(payload: Record<string, unknown>) {
  const res = await API.post('/api/v1/pricebooks/', payload, { headers: aiHeaders() });
  return res.data;
}

export async function activatePricebook(pricebookId: string) {
  const res = await API.post(`/api/v1/pricebooks/${pricebookId}/activate`, {}, { headers: aiHeaders() });
  return res.data;
}

export async function getActivePricebook() {
  const res = await API.get('/api/v1/pricebooks/active', { headers: aiHeaders() });
  return res.data;
}

export async function getTenantEntitlements(tenantId: string) {
  const res = await API.get(`/api/v1/pricebooks/entitlements/${tenantId}`, { headers: aiHeaders() });
  return res.data;
}

export async function setTenantEntitlements(payload: { tenant_id: string; entitlements: Record<string, unknown> }) {
  const res = await API.post('/api/v1/pricebooks/entitlements', payload, { headers: aiHeaders() });
  return res.data;
}

// ── Founder Datasets ──────────────────────────────────────────────────────

export interface DatasetSystemStatusApi {
  nemsis: { version: string; last_update: string };
  neris: { version: string; last_update: string };
  rxnorm: { term_count: number };
  snomed: { term_count: number };
  icd10: { version: string };
  facilities: { last_state_sync: string; active_count: number };
}

export interface DatasetExportAgencyApi {
  name: string;
  state: string;
  status: string;
  success_rate: number;
  failed_charts: number;
}

export interface DatasetExportsApi {
  total_today: number;
  successful: number;
  failed: number;
  in_queue: number;
  agencies: DatasetExportAgencyApi[];
}

export interface DatasetActiveDeviceApi {
  id: string;
  device_type: string;
  ip: string;
  agency: string;
  user: string;
  status: string;
}

export interface DatasetAIExpressionApi {
  generated_xpath: string;
  schematron_rule: string;
  human_readable: string;
}

export async function getDatasetStatus(): Promise<DatasetSystemStatusApi> {
  const res = await API.get('/api/datasets/status');
  const payload = asJsonObject(res.data);
  const nemsis = asJsonObject(payload.nemsis);
  const neris = asJsonObject(payload.neris);
  const rxnorm = asJsonObject(payload.rxnorm);
  const snomed = asJsonObject(payload.snomed);
  const icd10 = asJsonObject(payload.icd10);
  const facilities = asJsonObject(payload.facilities);
  return {
    nemsis: {
      version: asString(nemsis.version),
      last_update: asString(nemsis.last_update),
    },
    neris: {
      version: asString(neris.version),
      last_update: asString(neris.last_update),
    },
    rxnorm: {
      term_count: asNumber(rxnorm.term_count) ?? 0,
    },
    snomed: {
      term_count: asNumber(snomed.term_count) ?? 0,
    },
    icd10: {
      version: asString(icd10.version),
    },
    facilities: {
      last_state_sync: asString(facilities.last_state_sync),
      active_count: asNumber(facilities.active_count) ?? 0,
    },
  };
}

export async function getDatasetExports(): Promise<DatasetExportsApi> {
  const res = await API.get('/api/datasets/exports');
  const payload = asJsonObject(res.data);
  const agenciesRaw = Array.isArray(payload.agencies) ? payload.agencies : [];
  return {
    total_today: asNumber(payload.total_today) ?? 0,
    successful: asNumber(payload.successful) ?? 0,
    failed: asNumber(payload.failed) ?? 0,
    in_queue: asNumber(payload.in_queue) ?? 0,
    agencies: agenciesRaw.map((agency) => {
      const row = asJsonObject(agency);
      return {
        name: asString(row.name),
        state: asString(row.state),
        status: asString(row.status),
        success_rate: asNumber(row.success_rate) ?? 0,
        failed_charts: asNumber(row.failed_charts) ?? 0,
      };
    }),
  };
}

export async function getDatasetActiveDevices(): Promise<DatasetActiveDeviceApi[]> {
  const res = await API.get('/api/datasets/active-devices');
  const payload = Array.isArray(res.data) ? res.data : [];
  return payload.map((device) => {
    const row = asJsonObject(device);
    return {
      id: asString(row.id),
      device_type: asString(row.device_type),
      ip: asString(row.ip),
      agency: asString(row.agency),
      user: asString(row.user),
      status: asString(row.status),
    };
  });
}

export async function createDatasetAIExpression(payload: { natural_language: string }): Promise<DatasetAIExpressionApi> {
  const res = await API.post('/api/datasets/ai-expression-builder', payload, {
    headers: { 'Content-Type': 'application/json' },
  });
  const data = asJsonObject(res.data);
  return {
    generated_xpath: asString(data.generated_xpath),
    schematron_rule: asString(data.schematron_rule),
    human_readable: asString(data.human_readable),
  };
}

// ── Support Inbox ──────────────────────────────────────────────────────────

export type SupportThreadStatusApi = 'open' | 'escalated' | 'resolved';

export interface SupportThreadApi {
  id: string;
  status: SupportThreadStatusApi;
  unread: boolean;
  escalated: boolean;
  updated_at: string;
  data: {
    title?: string;
    context?: {
      agency_name?: string;
    };
    last_message?: string;
  };
}

export interface SupportThreadMessageApi {
  id: string;
  sender_role: 'agency' | 'founder' | 'ai';
  content: string;
  created_at: string;
}

function normalizeSupportThreadStatus(value: unknown): SupportThreadStatusApi {
  const status = asString(value).toLowerCase();
  if (status === 'escalated' || status === 'resolved') return status;
  return 'open';
}

export async function listSupportInboxThreads(params?: {
  status?: string;
  limit?: number;
}): Promise<SupportThreadApi[]> {
  const res = await API.get('/api/v1/support/inbox', {
    headers: transportLinkHeaders(),
    params,
  });
  const payload = res.data;
  const rows = Array.isArray(payload)
    ? payload
    : Array.isArray(payload?.threads)
      ? payload.threads
      : [];
  return rows.map((thread: unknown) => {
    const row = asJsonObject(thread);
    const data = asJsonObject(row.data);
    const context = asJsonObject(data.context);
    return {
      id: asString(row.id),
      status: normalizeSupportThreadStatus(row.status),
      unread: asBoolean(row.unread),
      escalated: asBoolean(row.escalated),
      updated_at: asString(row.updated_at),
      data: {
        title: asString(data.title) || undefined,
        context: {
          agency_name: asString(context.agency_name) || undefined,
        },
        last_message: asString(data.last_message) || undefined,
      },
    };
  });
}

export async function listSupportThreadMessages(threadId: string): Promise<SupportThreadMessageApi[]> {
  const res = await API.get(`/api/v1/support/threads/${threadId}/messages`, {
    headers: transportLinkHeaders(),
  });
  const payload = res.data;
  const rows = Array.isArray(payload)
    ? payload
    : Array.isArray(payload?.messages)
      ? payload.messages
      : [];
  return rows.map((message: unknown) => {
    const row = asJsonObject(message);
    const senderRole = asString(row.sender_role).toLowerCase();
    return {
      id: asString(row.id),
      sender_role: senderRole === 'agency' || senderRole === 'ai' ? senderRole : 'founder',
      content: asString(row.content),
      created_at: asString(row.created_at),
    };
  });
}

export async function sendSupportInboxReply(threadId: string, payload: { content: string }) {
  const res = await API.post(`/api/v1/support/inbox/${threadId}/reply`, payload, {
    headers: {
      ...transportLinkHeaders(),
      'Content-Type': 'application/json',
    },
  });
  return res.data;
}

export async function resolveSupportInboxThread(threadId: string) {
  const res = await API.post(`/api/v1/support/inbox/${threadId}/resolve`, {}, {
    headers: transportLinkHeaders(),
  });
  return res.data;
}

export async function summarizeSupportInboxThread(threadId: string): Promise<string> {
  const res = await API.post(`/api/v1/support/inbox/${threadId}/summarize`, {}, {
    headers: transportLinkHeaders(),
  });
  const payload = asJsonObject(res.data);
  const summary = asString(payload.summary || payload.content, '');
  return summary || JSON.stringify(payload);
}

// ── Portal Module Wrappers (Agency-facing Pages) ─────────────────────────

export interface PortalStatCardApi {
  label: string;
  value: number | string;
  href: string;
}

export interface PortalMetricsApi {
  portal?: {
    stat_cards?: PortalStatCardApi[];
  };
  [key: string]: unknown;
}

export async function getPortalAgencyMetrics(): Promise<PortalMetricsApi> {
  const res = await API.get('/api/v1/metrics', {
    headers: transportLinkHeaders(),
  });
  return asJsonObject(res.data) as PortalMetricsApi;
}

export type PortalFireIncidentStatusApi = 'draft' | 'validated' | 'exported' | string;

export interface PortalFireIncidentApi extends Record<string, unknown> {
  id: string;
  incident_number: string;
  incident_type_code: string;
  start_datetime: string;
  status: PortalFireIncidentStatusApi;
}

export interface PortalFireValidationIssueApi {
  severity: 'error' | 'warning';
  field_label?: string;
  path?: string;
  ui_section?: string;
  message: string;
  suggested_fix?: string;
}

export interface PortalFireValidationResultApi {
  valid: boolean;
  issues: PortalFireValidationIssueApi[];
}

export interface PortalFirePackRulesApi {
  department_id?: string;
  sections?: Array<Record<string, unknown>>;
  value_sets?: Record<string, string[]>;
  [key: string]: unknown;
}

export interface PortalFireApparatusApi {
  id: string;
  unit_id: string;
  unit_type_code: string;
  [key: string]: unknown;
}

export interface PortalNerisOnboardingStatusApi extends Record<string, unknown> {
  department?: {
    id?: string;
    [key: string]: unknown;
  };
}

export async function listPortalFireIncidents(params?: {
  status?: string;
}): Promise<PortalFireIncidentApi[]> {
  const res = await API.get('/api/v1/incidents/fire', {
    headers: transportLinkHeaders(),
    params: params?.status ? { status: params.status } : undefined,
  });
  const payload = res.data;
  if (Array.isArray(payload)) {
    return payload as PortalFireIncidentApi[];
  }
  return Array.isArray(payload?.incidents)
    ? (payload.incidents as PortalFireIncidentApi[])
    : [];
}

export async function createPortalFireIncident(payload: Record<string, unknown>): Promise<PortalFireIncidentApi> {
  const res = await API.post('/api/v1/incidents/fire', payload, {
    headers: {
      ...transportLinkHeaders(),
      'Content-Type': 'application/json',
    },
  });
  return asJsonObject(res.data) as PortalFireIncidentApi;
}

export async function updatePortalFireIncident(
  incidentId: string,
  payload: Record<string, unknown>
): Promise<PortalFireIncidentApi> {
  const res = await API.patch(`/api/v1/incidents/fire/${incidentId}`, payload, {
    headers: {
      ...transportLinkHeaders(),
      'Content-Type': 'application/json',
    },
  });
  return asJsonObject(res.data) as PortalFireIncidentApi;
}

export async function validatePortalFireIncident(incidentId: string): Promise<PortalFireValidationResultApi> {
  const res = await API.post(`/api/v1/incidents/fire/${incidentId}/validate`, {}, {
    headers: transportLinkHeaders(),
  });
  return asJsonObject(res.data) as unknown as PortalFireValidationResultApi;
}

export async function getPortalFirePackRules(): Promise<PortalFirePackRulesApi | null> {
  try {
    const res = await API.get('/api/v1/incidents/fire/pack-rules', {
      headers: transportLinkHeaders(),
    });
    return asJsonObject(res.data) as PortalFirePackRulesApi;
  } catch {
    return null;
  }
}

export async function getPortalNerisOnboardingStatus(): Promise<PortalNerisOnboardingStatusApi | null> {
  try {
    const res = await API.get('/api/v1/tenant/neris/onboarding/status', {
      headers: transportLinkHeaders(),
    });
    return asJsonObject(res.data) as PortalNerisOnboardingStatusApi;
  } catch {
    return null;
  }
}

export async function listPortalFireDepartmentApparatus(departmentId: string): Promise<PortalFireApparatusApi[]> {
  const res = await API.get(`/api/v1/incidents/fire/departments/${departmentId}/apparatus`, {
    headers: transportLinkHeaders(),
  });
  if (Array.isArray(res.data)) {
    return res.data as PortalFireApparatusApi[];
  }
  return Array.isArray(res.data?.apparatus)
    ? (res.data.apparatus as PortalFireApparatusApi[])
    : [];
}

export async function exportPortalNerisIncident(payload: {
  department_id: string | null;
  incident_ids: string[];
}): Promise<Blob> {
  const res = await API.post('/api/v1/neris/exports', payload, {
    headers: {
      ...transportLinkHeaders(),
      'Content-Type': 'application/json',
    },
    responseType: 'blob',
  });
  return res.data as Blob;
}

export type PortalFleetAlertSeverityApi = 'critical' | 'warning' | 'info';
export type PortalFleetWorkOrderStatusApi = 'open' | 'in_progress' | 'completed';

export interface PortalFleetReadinessApi extends Record<string, unknown> {
  units?: PortalFleetUnitScoreApi[];
  fleet_count?: number;
  avg_readiness?: number;
  units_ready?: number;
  units_limited?: number;
  units_no_go?: number;
}

export interface PortalFleetUnitScoreApi extends Record<string, unknown> {
  unit_id: string;
  readiness_score: number;
  alert_count: number;
  mdt_online: boolean;
  open_maintenance: number;
}

export interface PortalFleetUnitDetailApi extends Record<string, unknown> {
  unit_id: string;
}

export interface PortalFleetAlertApi extends Record<string, unknown> {
  alert_id: string;
  severity: PortalFleetAlertSeverityApi;
  unit_id: string;
  message: string;
  detected_at: string;
  resolved?: boolean;
}

export interface PortalFleetWorkOrderApi extends Record<string, unknown> {
  work_order_id: string;
  unit_id: string;
  title: string;
  description?: string;
  priority: string;
  status: PortalFleetWorkOrderStatusApi;
  due_date?: string;
}

export interface PortalFleetInspectionTemplateApi extends Record<string, unknown> {
  template_id: string;
  name: string;
  vehicle_type: string;
  frequency: string;
}

export async function getPortalFleetReadiness(): Promise<PortalFleetReadinessApi> {
  const res = await API.get('/api/v1/fleet-intelligence/readiness/fleet', {
    headers: transportLinkHeaders(),
  });
  return asJsonObject(res.data) as PortalFleetReadinessApi;
}

export async function getPortalFleetUnitReadiness(unitId: string): Promise<PortalFleetUnitDetailApi> {
  const res = await API.get(`/api/v1/fleet-intelligence/readiness/units/${unitId}`, {
    headers: transportLinkHeaders(),
  });
  return asJsonObject(res.data) as PortalFleetUnitDetailApi;
}

export async function listPortalFleetAlerts(unresolvedOnly = true): Promise<PortalFleetAlertApi[]> {
  const res = await API.get('/api/v1/fleet-intelligence/alerts', {
    headers: transportLinkHeaders(),
    params: { unresolved_only: unresolvedOnly },
  });
  const payload = res.data;
  if (Array.isArray(payload)) {
    return payload as PortalFleetAlertApi[];
  }
  return Array.isArray(payload?.alerts)
    ? (payload.alerts as PortalFleetAlertApi[])
    : [];
}

export async function resolvePortalFleetAlert(alertId: string, payload: { note: string }) {
  const res = await API.patch(`/api/v1/fleet-intelligence/alerts/${alertId}/resolve`, payload, {
    headers: {
      ...transportLinkHeaders(),
      'Content-Type': 'application/json',
    },
  });
  return res.data;
}

export async function listPortalFleetWorkOrders(): Promise<PortalFleetWorkOrderApi[]> {
  const res = await API.get('/api/v1/fleet-intelligence/maintenance/work-orders', {
    headers: transportLinkHeaders(),
  });
  const payload = res.data;
  if (Array.isArray(payload)) {
    return payload as PortalFleetWorkOrderApi[];
  }
  return Array.isArray(payload?.work_orders)
    ? (payload.work_orders as PortalFleetWorkOrderApi[])
    : [];
}

export async function createPortalFleetWorkOrder(payload: {
  unit_id: string;
  title: string;
  description?: string;
  priority: string;
  due_date?: string;
}) {
  const res = await API.post('/api/v1/fleet-intelligence/maintenance/work-orders', payload, {
    headers: {
      ...transportLinkHeaders(),
      'Content-Type': 'application/json',
    },
  });
  return res.data;
}

export async function updatePortalFleetWorkOrder(
  workOrderId: string,
  payload: { status: PortalFleetWorkOrderStatusApi }
) {
  const res = await API.patch(`/api/v1/fleet-intelligence/maintenance/work-orders/${workOrderId}`, payload, {
    headers: {
      ...transportLinkHeaders(),
      'Content-Type': 'application/json',
    },
  });
  return res.data;
}

export async function listPortalFleetInspectionTemplates(): Promise<PortalFleetInspectionTemplateApi[]> {
  const res = await API.get('/api/v1/fleet-intelligence/inspections/templates', {
    headers: transportLinkHeaders(),
  });
  const payload = res.data;
  if (Array.isArray(payload)) {
    return payload as PortalFleetInspectionTemplateApi[];
  }
  return Array.isArray(payload?.templates)
    ? (payload.templates as PortalFleetInspectionTemplateApi[])
    : [];
}

export async function createPortalFleetInspectionTemplate(payload: {
  name: string;
  vehicle_type: string;
  frequency: string;
}) {
  const res = await API.post('/api/v1/fleet-intelligence/inspections/templates', payload, {
    headers: {
      ...transportLinkHeaders(),
      'Content-Type': 'application/json',
    },
  });
  return res.data;
}

export interface PortalHemsSafetyEventApi {
  event_type: string;
  timestamp: string;
  details?: Record<string, unknown>;
}

export interface PortalHemsChecklistTemplateApi {
  items?: string[];
  risk_factors?: string[];
}

export async function getPortalHemsSafetyTimeline(missionId: string): Promise<PortalHemsSafetyEventApi[]> {
  const res = await API.get(`/api/v1/hems/missions/${missionId}/safety-timeline`, {
    headers: transportLinkHeaders(),
  });
  const payload = res.data;
  if (Array.isArray(payload)) {
    return payload as PortalHemsSafetyEventApi[];
  }
  return Array.isArray(payload?.events)
    ? (payload.events as PortalHemsSafetyEventApi[])
    : [];
}

export async function getPortalHemsChecklistTemplate(): Promise<PortalHemsChecklistTemplateApi | null> {
  try {
    const res = await API.get('/api/v1/hems/checklist-template', {
      headers: transportLinkHeaders(),
    });
    return asJsonObject(res.data) as PortalHemsChecklistTemplateApi;
  } catch {
    return null;
  }
}

export async function postPortalHemsMissionAction(
  missionId: string,
  endpoint: string,
  payload: Record<string, unknown>
) {
  const res = await API.post(`/api/v1/hems/missions/${missionId}/${endpoint}`, payload, {
    headers: {
      ...transportLinkHeaders(),
      'Content-Type': 'application/json',
    },
  });
  return res.data;
}

export async function setPortalHemsAircraftReadiness(
  aircraftId: string,
  payload: { state: string; reason: string }
) {
  const res = await API.post(`/api/v1/hems/aircraft/${aircraftId}/readiness`, payload, {
    headers: {
      ...transportLinkHeaders(),
      'Content-Type': 'application/json',
    },
  });
  return res.data;
}

export async function submitPortalHemsMissionAcceptance(
  missionId: string,
  payload: {
    aircraft_id?: string;
    checklist: Record<string, boolean>;
    risk_factors: Record<string, boolean>;
    risk_score: number;
  }
) {
  const res = await API.post(`/api/v1/hems/missions/${missionId}/acceptance`, payload, {
    headers: {
      ...transportLinkHeaders(),
      'Content-Type': 'application/json',
    },
  });
  return res.data;
}

export async function submitPortalHemsWeatherBrief(
  missionId: string,
  payload: {
    ceiling_ft?: number;
    visibility_sm?: number;
    wind_direction?: number;
    wind_speed_kt?: number;
    gusts_kt?: number;
    precip: boolean;
    icing: boolean;
    turbulence: string;
    go_no_go: string;
    source?: string;
  }
) {
  const res = await API.post(`/api/v1/hems/missions/${missionId}/weather-brief`, payload, {
    headers: {
      ...transportLinkHeaders(),
      'Content-Type': 'application/json',
    },
  });
  return res.data;
}

export type PortalSupportThreadTypeApi =
  | 'General Support'
  | 'Billing Question'
  | 'Technical Issue'
  | 'Compliance';

export type PortalSupportThreadStatusApi = 'open' | 'escalated' | 'resolved';

export interface PortalSupportThreadApi {
  id: string;
  title: string;
  thread_type: PortalSupportThreadTypeApi;
  status: PortalSupportThreadStatusApi;
  last_message_preview: string;
  last_message_at: string;
  unread_count?: number;
}

export interface PortalSupportMessageApi {
  id: string;
  sender_type: 'agency' | 'ai' | 'founder';
  sender_label: string;
  content: string;
  created_at: string;
}

export async function listPortalSupportThreads(): Promise<PortalSupportThreadApi[]> {
  const res = await API.get('/api/v1/support/threads', {
    headers: transportLinkHeaders(),
  });
  return (Array.isArray(res.data) ? res.data : []) as PortalSupportThreadApi[];
}

export async function createPortalSupportThread(payload: {
  thread_type: PortalSupportThreadTypeApi;
  title: string;
  initial_message: string;
}): Promise<PortalSupportThreadApi> {
  const res = await API.post('/api/v1/support/threads', payload, {
    headers: {
      ...transportLinkHeaders(),
      'Content-Type': 'application/json',
    },
  });
  return asJsonObject(res.data) as unknown as PortalSupportThreadApi;
}

export async function listPortalSupportThreadMessages(threadId: string): Promise<PortalSupportMessageApi[]> {
  const res = await API.get(`/api/v1/support/threads/${threadId}/messages`, {
    headers: transportLinkHeaders(),
  });
  return (Array.isArray(res.data) ? res.data : []) as PortalSupportMessageApi[];
}

export async function createPortalSupportThreadMessage(
  threadId: string,
  payload: { content: string }
): Promise<PortalSupportMessageApi> {
  const res = await API.post(`/api/v1/support/threads/${threadId}/messages`, payload, {
    headers: {
      ...transportLinkHeaders(),
      'Content-Type': 'application/json',
    },
  });
  return asJsonObject(res.data) as unknown as PortalSupportMessageApi;
}

// ── Voice Advanced ─────────────────────────────────────────────────────────

export async function getVoiceAdvancedDashboard(): Promise<Record<string, unknown> | null> {
  const res = await API.get('/api/v1/voice-advanced/dashboard', { headers: aiHeaders() });
  const payload = asJsonObject(res.data);
  return Object.keys(payload).length > 0 ? payload : null;
}

export async function getVoiceAdvancedReviewQueue(): Promise<Record<string, unknown>[]> {
  const res = await API.get('/api/v1/voice-advanced/review-queue', { headers: aiHeaders() });
  return Array.isArray(res.data) ? (res.data as Record<string, unknown>[]) : [];
}

export async function getVoiceAdvancedImprovementTickets(): Promise<Record<string, unknown>[]> {
  const res = await API.get('/api/v1/voice-advanced/improvement-tickets', { headers: aiHeaders() });
  return Array.isArray(res.data) ? (res.data as Record<string, unknown>[]) : [];
}

export async function getVoiceAdvancedCallbackSlots(): Promise<Record<string, unknown>[]> {
  const res = await API.get('/api/v1/voice-advanced/callback-optimizer/slots', { headers: aiHeaders() });
  return Array.isArray(res.data) ? (res.data as Record<string, unknown>[]) : [];
}

export async function getVoiceAdvancedAbTests(): Promise<Record<string, unknown>[]> {
  const res = await API.get('/api/v1/voice-advanced/ab-tests', { headers: aiHeaders() });
  return Array.isArray(res.data) ? (res.data as Record<string, unknown>[]) : [];
}

// ── Dispatch Requests (Portal / TransportLink Auth) ───────────────────────

export interface DispatchRequestApi {
  id: string;
  data: Record<string, unknown>;
}

function normalizeDispatchRequestRecord(value: unknown): DispatchRequestApi {
  const row = asJsonObject(value);
  const data = asJsonObject(row.data);
  return {
    id: asString(row.id || data.id),
    data,
  };
}

export async function listDispatchRequestsPortal(limit = 100): Promise<DispatchRequestApi[]> {
  const res = await API.get('/api/v1/dispatch/requests', {
    headers: transportLinkHeaders(),
    params: { limit },
  });
  const payload = res.data;
  const rows = Array.isArray(payload)
    ? payload
    : Array.isArray(payload?.requests)
      ? payload.requests
      : Array.isArray(payload?.data)
        ? payload.data
        : [];
  return rows.map((row: unknown) => normalizeDispatchRequestRecord(row));
}

export async function listTransportLinkFacilitySchedule(facilityId: string): Promise<DispatchRequestApi[]> {
  const res = await API.get(`/api/v1/transportlink/facilities/${facilityId}/schedule`, {
    headers: transportLinkHeaders(),
  });
  const rows = Array.isArray(res.data) ? res.data : [];
  return rows.map((row: unknown) => normalizeDispatchRequestRecord(row));
}

export async function createDispatchRequestPortal(payload: Record<string, unknown>) {
  const res = await API.post('/api/v1/dispatch/requests', payload, {
    headers: {
      ...transportLinkHeaders(),
      'Content-Type': 'application/json',
    },
  });
  return res.data;
}

export async function injectDispatchRequestPortal(requestId: string) {
  const res = await API.post(`/api/v1/dispatch/requests/${requestId}/inject`, {}, {
    headers: {
      ...transportLinkHeaders(),
      'Content-Type': 'application/json',
    },
  });
  return res.data;
}

export async function validateDispatchRequestPortal(requestId: string) {
  const res = await API.post(`/api/v1/dispatch/requests/${requestId}/validate`, {}, {
    headers: {
      ...transportLinkHeaders(),
      'Content-Type': 'application/json',
    },
  });
  return res.data;
}

// ── Dispatch Missions (Founder Ops CAD) ────────────────────────────────────

export async function getDispatchMissions(limit = 100) {
  const res = await API.get(`/api/v1/dispatch/missions?limit=${limit}`, { headers: aiHeaders() });
  return res.data;
}

export async function transitionDispatchMission(missionId: string, payload: { state: string; reason?: string }) {
  const res = await API.patch(`/api/v1/dispatch/missions/${missionId}/transition`, payload, { headers: aiHeaders() });
  return res.data;
}

export async function cancelDispatchMission(missionId: string, payload?: Record<string, unknown>) {
  const res = await API.post(`/api/v1/dispatch/missions/${missionId}/cancel`, payload ?? {}, { headers: aiHeaders() });
  return res.data;
}

export async function createDispatchRequest(payload: Record<string, unknown>) {
  const res = await API.post('/api/v1/dispatch/requests', payload, { headers: aiHeaders() });
  return res.data;
}

export async function injectDispatchRequest(requestId: string) {
  const res = await API.post(`/api/v1/dispatch/requests/${requestId}/inject`, {}, { headers: aiHeaders() });
  return res.data;
}

// ── Fleet Intelligence (Founder Ops Fleet) ─────────────────────────────────

export async function getFleetIntelligenceReadiness() {
  const res = await API.get('/api/v1/fleet-intelligence/readiness/fleet', { headers: aiHeaders() });
  return res.data;
}

export async function getFleetDashboard() {
  const res = await API.get('/api/v1/fleet/dashboard', { headers: aiHeaders() });
  return res.data;
}

export async function ackFleetAlert(alertId: string, payload?: Record<string, unknown>) {
  const res = await API.post(`/api/v1/fleet/alerts/${alertId}/ack`, payload ?? {}, { headers: aiHeaders() });
  return res.data;
}

export async function ingestTelemetry(payload: Record<string, unknown>) {
  const res = await API.post('/api/v1/ops/telemetry/ingest', payload, { headers: aiHeaders() });
  return res.data;
}

// ── CrewLink Alerts (Founder Ops CrewLink) ─────────────────────────────────

export async function getCrewlinkAlerts(params?: { active?: boolean; limit?: number }) {
  const url = params?.active ? '/api/v1/crewlink/alerts/active' : `/api/v1/crewlink/alerts?limit=${params?.limit ?? 100}`;
  const res = await API.get(url, { headers: aiHeaders() });
  return res.data;
}

export async function createCrewlinkAlert(payload: Record<string, unknown>) {
  const res = await API.post('/api/v1/crewlink/alerts', payload, { headers: aiHeaders() });
  return res.data;
}

export async function escalateCrewlinkAlert(alertId: string, payload: { reason: string; triggered_by: string }) {
  const res = await API.post(`/api/v1/crewlink/alerts/${alertId}/escalate`, payload, { headers: aiHeaders() });
  return res.data;
}

// ── Roles & Assignments (Security Role Builder) ────────────────────────────

export async function listRoles() {
  const res = await API.get('/api/v1/roles', { headers: aiHeaders() });
  return res.data;
}

export async function listRoleAssignments() {
  const res = await API.get('/api/v1/roles/assignments', { headers: aiHeaders() });
  return res.data;
}

export async function createRoleAssignment(payload: Record<string, unknown>) {
  const res = await API.post('/api/v1/roles/assignments', payload, { headers: aiHeaders() });
  return res.data;
}

export async function deleteRoleAssignment(assignmentId: string) {
  const res = await API.delete(`/api/v1/roles/assignments/${assignmentId}`, { headers: aiHeaders() });
  return res.data;
}

// ── Audit Logs (Security Access Logs) ──────────────────────────────────────

export async function searchAuditLogs(payload: Record<string, unknown>) {
  const res = await API.post('/api/v1/audit/logs/search', payload, { headers: aiHeaders() });
  return res.data;
}

// ── Governance (Security Governance) ───────────────────────────────────────

export async function getGovernanceSummary() {
  const res = await API.get('/api/v1/governance/summary', { headers: aiHeaders() });
  return res.data;
}

export async function getGovernanceInteropReadiness() {
  const res = await API.get('/api/v1/governance/interop-readiness', { headers: aiHeaders() });
  return res.data;
}

// ── Events Feed (Executive Events Feed) ────────────────────────────────────

export async function getEventsFeed(params?: Record<string, string>) {
  const qs = params ? '?' + new URLSearchParams(params).toString() : '';
  const res = await API.get(`/api/v1/events/feed${qs}`, { headers: aiHeaders() });
  return res.data;
}

export async function getEventsUnreadCount() {
  const res = await API.get('/api/v1/events/unread-count', { headers: aiHeaders() });
  return res.data;
}

export async function markEventRead(eventId: string) {
  const res = await API.post(`/api/v1/events/${eventId}/read`, {}, { headers: aiHeaders() });
  return res.data;
}

// ── Onboarding Control (Founder Tools) ─────────────────────────────────────

export async function getOnboardingApplications(params?: Record<string, string>) {
  const qs = params ? '?' + new URLSearchParams(params).toString() : '';
  const res = await API.get(`/api/v1/founder/documents/onboarding-applications${qs}`, { headers: aiHeaders() });
  return res.data;
}

export async function getOnboardingSignEvents(applicationId: string) {
  const res = await API.get(`/api/v1/founder/documents/sign-events?application_id=${applicationId}`, { headers: aiHeaders() });
  return res.data;
}

export async function resendOnboardingLegal(applicationId: string) {
  const res = await API.post(`/api/v1/founder/documents/onboarding-applications/${applicationId}/resend-legal`, {}, { headers: aiHeaders() });
  return res.data;
}

export async function resendOnboardingCheckout(applicationId: string) {
  const res = await API.post(`/api/v1/founder/documents/onboarding-applications/${applicationId}/resend-checkout`, {}, { headers: aiHeaders() });
  return res.data;
}

export async function manualProvisionApplication(applicationId: string) {
  const res = await API.post(`/api/v1/founder/documents/onboarding-applications/${applicationId}/manual-provision`, { confirm: true }, { headers: aiHeaders() });
  return res.data;
}

export async function revokeOnboardingApplication(applicationId: string, payload: { reason: string }) {
  const res = await API.post(`/api/v1/founder/documents/onboarding-applications/${applicationId}/revoke`, payload, { headers: aiHeaders() });
  return res.data;
}

// ── Expense Ledger (Founder Tools) ─────────────────────────────────────────

export async function getExpenseLedger(limit = 500) {
  const res = await API.get(`/api/v1/founder/business/expense-ledger?limit=${limit}`, { headers: aiHeaders() });
  return res.data;
}

export async function createExpenseEntry(payload: Record<string, unknown>) {
  const res = await API.post('/api/v1/founder/business/expense-ledger/entries', payload, { headers: aiHeaders() });
  return res.data;
}

// ── Invoice Creator (Founder Tools) ────────────────────────────────────────

export async function getInvoices(limit = 500) {
  const res = await API.get(`/api/v1/founder/business/invoices?limit=${limit}`, { headers: aiHeaders() });
  return res.data;
}

export async function createInvoice(payload: Record<string, unknown>) {
  const res = await API.post('/api/v1/founder/business/invoices', payload, { headers: aiHeaders() });
  return res.data;
}

export async function sendInvoiceReminder(invoiceId: string, payload: { channel: string }) {
  const res = await API.post(`/api/v1/founder/business/invoices/${invoiceId}/send-reminder`, payload, { headers: aiHeaders() });
  return res.data;
}

export async function markInvoicePaid(invoiceId: string) {
  const res = await API.post(`/api/v1/founder/business/invoices/${invoiceId}/mark-paid`, {}, { headers: aiHeaders() });
  return res.data;
}

export async function getInvoiceSettings() {
  const res = await API.get('/api/v1/founder/business/invoice-settings', { headers: aiHeaders() });
  return res.data;
}

export async function updateInvoiceSettings(payload: Record<string, unknown>) {
  const res = await API.put('/api/v1/founder/business/invoice-settings', payload, { headers: aiHeaders() });
  return res.data;
}

// ── Graph Mail (Founder Tools Email) ───────────────────────────────────────

export async function getGraphMail(folder = 'inbox', top = 30) {
  const res = await API.get(`/api/v1/founder/graph/mail?folder=${folder}&top=${top}`, { headers: aiHeaders() });
  return res.data;
}

export async function getGraphMailMessage(messageId: string) {
  const res = await API.get(`/api/v1/founder/graph/mail/${messageId}`, { headers: aiHeaders() });
  return res.data;
}

export async function getGraphMailAttachments(messageId: string) {
  const res = await API.get(`/api/v1/founder/graph/mail/${messageId}/attachments`, { headers: aiHeaders() });
  return res.data;
}

export async function sendGraphMail(payload: { to: string[]; cc?: string[]; subject: string; body_html: string }) {
  const res = await API.post('/api/v1/founder/graph/mail/send', payload, { headers: aiHeaders() });
  return res.data;
}

export async function replyGraphMail(messageId: string, payload: { body_html: string }) {
  const res = await API.post(`/api/v1/founder/graph/mail/${messageId}/reply`, payload, { headers: aiHeaders() });
  return res.data;
}

// ── Graph Drive (Founder Tools Files) ──────────────────────────────────────

export async function getGraphDriveRoot() {
  const res = await API.get('/api/v1/founder/graph/drive', { headers: aiHeaders() });
  return res.data;
}

export async function getGraphDriveFolder(folderId: string) {
  const res = await API.get(`/api/v1/founder/graph/drive/folders/${folderId}`, { headers: aiHeaders() });
  return res.data;
}

export function getGraphDriveItemDownloadUrl(itemId: string): string {
  return `${API.defaults.baseURL ?? ''}/api/v1/founder/graph/drive/items/${itemId}/download`;
}

// ── Founder Reports (Templates) ────────────────────────────────────────────

export async function getFounderReports() {
  const res = await API.get('/api/v1/founder/reports', { headers: aiHeaders() });
  return res.data;
}

// ── Founder Contracts (Templates) ──────────────────────────────────────────

export async function getFounderContracts() {
  const res = await API.get('/api/v1/founder/contracts', { headers: aiHeaders() });
  return res.data;
}

// ── Founder Copilot Sessions ───────────────────────────────────────────────

export async function getCopilotSessions() {
  const res = await API.get('/api/v1/founder/copilot/sessions', { headers: aiHeaders() });
  return res.data;
}

export async function createCopilotSession(payload: { title: string }) {
  const res = await API.post('/api/v1/founder/copilot/sessions', payload, { headers: aiHeaders() });
  return res.data;
}

export async function getCopilotMessages(sessionId: string) {
  const res = await API.get(`/api/v1/founder/copilot/sessions/${sessionId}/messages`, { headers: aiHeaders() });
  return res.data;
}

export async function sendCopilotMessage(sessionId: string, payload: { content: string }) {
  const res = await API.post(`/api/v1/founder/copilot/sessions/${sessionId}/messages`, payload, { headers: aiHeaders() });
  return res.data;
}

export async function proposeCopilotRun(sessionId: string, payload: Record<string, unknown>) {
  const res = await API.post(`/api/v1/founder/copilot/sessions/${sessionId}/runs/propose`, payload, { headers: aiHeaders() });
  return res.data;
}

export async function getCopilotRun(runId: string) {
  const res = await API.get(`/api/v1/founder/copilot/runs/${runId}`, { headers: aiHeaders() });
  return res.data;
}

export async function executeCopilotRun(runId: string, payload: { ref: string }) {
  const res = await API.post(`/api/v1/founder/copilot/runs/${runId}/execute`, payload, { headers: aiHeaders() });
  return res.data;
}

export async function approveCopilotRun(runId: string) {
  const res = await API.post(`/api/v1/founder/copilot/runs/${runId}/approve`, {}, { headers: aiHeaders() });
  return res.data;
}

export async function mergeCopilotRun(runId: string) {
  const res = await API.post(`/api/v1/founder/copilot/runs/${runId}/merge`, {}, { headers: aiHeaders() });
  return res.data;
}

// ── Founder Agent Command ──────────────────────────────────────────────────

export async function sendAgentCommand(payload: { command: string }) {
  const res = await API.post('/api/v1/founder/agents/command', payload, { headers: aiHeaders() });
  return res.data;
}

export function getAgentStreamUrl(): string {
  const token = typeof window !== 'undefined' ? localStorage.getItem('qs_token') ?? '' : '';
  return `${API.defaults.baseURL ?? ''}/api/v1/founder/agents/stream?token=${encodeURIComponent(token)}`;
}

// ── DEA/CMS Compliance Command ─────────────────────────────────────────────

export async function getDEANarcoticsAuditHistory(limit = 10) {
  const { data } = await API.get('/api/v1/dea-compliance/audits/narcotics/history', {
    params: { limit },
    headers: transportLinkHeaders(),
  });
  return data;
}

export async function getCMSGateAuditSummary(days = 30) {
  const { data } = await API.get('/api/v1/cms-gate/audit/summary', {
    params: { days },
    headers: transportLinkHeaders(),
  });
  return data;
}

export async function getCMSGateAuditHistory(limit = 10) {
  const { data } = await API.get('/api/v1/cms-gate/audit/history', {
    params: { limit },
    headers: transportLinkHeaders(),
  });
  return data;
}

export async function getDEAEvidenceBundlesHistory(limit = 10) {
  const { data } = await API.get('/api/v1/dea-compliance/evidence-bundles/history', {
    params: { limit },
    headers: transportLinkHeaders(),
  });
  return data;
}

export async function runDEANarcoticsAudit(payload: { lookback_days: number; min_count_events: number }) {
  const { data } = await API.post('/api/v1/dea-compliance/audits/narcotics', payload, {
    headers: transportLinkHeaders(),
  });
  return data;
}

export async function createDEAEvidenceBundle(payload: { lookback_days: number; include_raw_rows: boolean }) {
  const { data } = await API.post('/api/v1/dea-compliance/evidence-bundles', payload, {
    headers: transportLinkHeaders(),
  });
  return data;
}

export async function getDEAEvidenceBundleDetail(bundleId: string) {
  const { data } = await API.get(`/api/v1/dea-compliance/evidence-bundles/${bundleId}`, {
    params: { include_artifacts: true },
    headers: transportLinkHeaders(),
  });
  return data;
}

export async function verifyDEAEvidenceBundleHash(bundleId: string) {
  const { data } = await API.get(`/api/v1/dea-compliance/evidence-bundles/${bundleId}/verify-hash`, {
    headers: transportLinkHeaders(),
  });
  return data;
}

// ── NEMSIS Validation ──────────────────────────────────────────────────────

export async function simulateWisconsinNEMSIS() {
  const { data } = await API.post('/api/v1/nemsis/simulate_wisconsin', {}, {
    headers: transportLinkHeaders(),
  });
  return data;
}

export async function validateNEMSISRawXml(xmlContent: string) {
  const { data } = await API.post('/api/v1/nemsis/validate_raw_xml', xmlContent, {
    headers: { ...transportLinkHeaders(), 'Content-Type': 'application/xml' },
  });
  return data;
}

export async function nemsisCopilotExplain(payload: { issues: unknown[]; context?: unknown }) {
  const { data } = await API.post('/api/v1/nemsis/copilot/explain', payload, {
    headers: transportLinkHeaders(),
  });
  return data;
}

// ── NERIS Pack Management ──────────────────────────────────────────────────

export async function importNERISPack(payload: { source_type: string; repo: string; ref: string; name: string }) {
  const { data } = await API.post('/api/v1/founder/neris/packs/import', payload, {
    headers: transportLinkHeaders(),
  });
  return data;
}

export async function compileNERISPack(packId: string) {
  const { data } = await API.post(`/api/v1/founder/neris/packs/${packId}/compile`, {}, {
    headers: transportLinkHeaders(),
  });
  return data;
}

export async function activateNERISPack(packId: string) {
  const { data } = await API.post(`/api/v1/founder/neris/packs/${packId}/activate`, {}, {
    headers: transportLinkHeaders(),
  });
  return data;
}

export async function validateNERISBundle(payload: { pack_id: string; entity_type: string; payload: unknown }) {
  const { data } = await API.post('/api/v1/founder/neris/validate/bundle', payload, {
    headers: transportLinkHeaders(),
  });
  return data;
}

export async function nerisCopilotExplain(payload: { issues: unknown[] }) {
  const { data } = await API.post('/api/v1/neris/copilot/explain', payload, {
    headers: transportLinkHeaders(),
  });
  return data;
}

export async function getNERISPackDetail(packId: string) {
  const { data } = await API.get(`/api/v1/founder/neris/packs/${packId}`, {
    headers: transportLinkHeaders(),
  });
  return data;
}

export async function listNERISPacksAll() {
  const { data } = await API.get('/api/v1/founder/neris/packs', {
    headers: transportLinkHeaders(),
  });
  return data;
}

// ── NEMSIS Compliance Studio ───────────────────────────────────────────────

export async function getActiveNEMSISPacks() {
  const { data } = await API.get('/api/v1/nemsis/packs', {
    params: { active: true },
    withCredentials: true,
  });
  return data;
}

export async function getNEMSISCertificationChecklist() {
  const { data } = await API.get('/api/v1/nemsis/studio/certification-checklist', {
    withCredentials: true,
  });
  return data;
}

export async function createNEMSISPack(payload: { pack_name: string; pack_type: string }) {
  const { data } = await API.post('/api/v1/nemsis/packs', payload, {
    withCredentials: true,
  });
  return data;
}

export async function uploadNEMSISPackFile(packId: string, formData: FormData) {
  const { data } = await API.post(`/api/v1/nemsis/packs/${packId}/files/upload`, formData, {
    withCredentials: true,
    headers: { 'Content-Type': 'multipart/form-data' },
  });
  return data;
}

export async function validateNEMSISStudioFile(formData: FormData) {
  const { data } = await API.post('/api/v1/nemsis/studio/validate-file', formData, {
    withCredentials: true,
  });
  return data;
}

export async function nemsisStudioAiExplain(payload: { validation_result_id: string; issue_index: number }) {
  const { data } = await API.post('/api/v1/nemsis/studio/ai-explain', payload, {
    withCredentials: true,
  });
  return data;
}

export async function generatePatchTasksFromResult(payload: { validation_result_id: string }) {
  const { data } = await API.post('/api/v1/nemsis/studio/patch-tasks/generate-from-result', payload, {
    withCredentials: true,
  });
  return data;
}

export interface NEMSISCtaCaseApi {
  case_id: string;
  short_name: string;
  description: string;
  dataset_type: 'DEM' | 'EMS';
  expected_result: string;
  schema_version: string;
  request_data_schema: number;
  test_key_element: string;
}

export interface NEMSISCtaRunApi {
  id: string;
  status: string;
  case_id: string;
  case_label: string;
  dataset_type: 'DEM' | 'EMS';
  schema_version: string;
  request_data_schema: number;
  request_handle: string | null;
  submit_status_code: number | null;
  retrieve_status_code: number | null;
  plain_summary: string;
  current_state_label: string;
  validation_blocking_count: number;
  resolved_test_key: string | null;
  organization: string | null;
  last_checked_at: string | null;
  created_at: string;
  updated_at: string;
  history: Array<{ status: string; at: string; summary?: string }>;
  details: Record<string, unknown>;
}

export interface NEMSISCtaCredentialsApi {
  username: string;
  password: string;
  organization: string;
}

export interface RunNEMSISCtaCasePayload {
  case_id: string;
  endpoint_url?: string;
  additional_info?: string;
  credentials?: Partial<NEMSISCtaCredentialsApi>;
}

export async function getNEMSISCtaCases() {
  const { data } = await API.get('/api/v1/nemsis/studio/cta/cases', {
    withCredentials: true,
  });
  return data as { cases: NEMSISCtaCaseApi[] };
}

export async function getNEMSISCtaRuns() {
  const { data } = await API.get('/api/v1/nemsis/studio/cta/runs', {
    withCredentials: true,
  });
  return data as { runs: NEMSISCtaRunApi[] };
}

export async function getNEMSISCtaRun(runId: string) {
  const { data } = await API.get(`/api/v1/nemsis/studio/cta/runs/${runId}`, {
    withCredentials: true,
  });
  return data as NEMSISCtaRunApi;
}

export async function runNEMSISCtaCase(payload: RunNEMSISCtaCasePayload) {
  const { data } = await API.post('/api/v1/nemsis/studio/cta/runs', payload, {
    withCredentials: true,
  });
  return data as NEMSISCtaRunApi;
}

export async function checkNEMSISCtaRunStatus(
  runId: string,
  payload: Omit<RunNEMSISCtaCasePayload, 'case_id'>
) {
  const { data } = await API.post(`/api/v1/nemsis/studio/cta/runs/${runId}/check-status`, payload, {
    withCredentials: true,
  });
  return data as NEMSISCtaRunApi;
}

// ── NEMSIS Patch Tasks ─────────────────────────────────────────────────────

export async function getNEMSISPatchTasks() {
  const { data } = await API.get('/api/v1/nemsis/studio/patch-tasks', {
    withCredentials: true,
  });
  return data;
}

export async function updateNEMSISPatchTask(taskId: string, payload: { status: string }) {
  const { data } = await API.patch(`/api/v1/nemsis/studio/patch-tasks/${taskId}`, payload, {
    withCredentials: true,
  });
  return data;
}

// ── NEMSIS Test Scenarios ──────────────────────────────────────────────────

export async function getNEMSISScenarios() {
  const { data } = await API.get('/api/v1/nemsis/studio/scenarios', {
    withCredentials: true,
  });
  return data;
}

export async function uploadNEMSISScenario(formData: FormData) {
  const { data } = await API.post('/api/v1/nemsis/studio/scenarios/upload', formData, {
    withCredentials: true,
    headers: { 'Content-Type': 'multipart/form-data' },
  });
  return data;
}

export async function runNEMSISScenario(scenarioId: string) {
  const { data } = await API.post(`/api/v1/nemsis/studio/scenarios/${scenarioId}/run`, {}, {
    withCredentials: true,
  });
  return data;
}

// ── Ops Command ────────────────────────────────────────────────────────────

export async function getOpsDeploymentRuns(limit = 20) {
  const { data } = await API.get('/api/v1/ops/deployment-runs', {
    params: { limit },
    headers: transportLinkHeaders(),
  });
  return data;
}

export async function getOpsDeploymentRunSteps(runId: string) {
  const { data } = await API.get(`/api/v1/ops/deployment-runs/${runId}/steps`, {
    headers: transportLinkHeaders(),
  });
  return data;
}

export async function getOpsCommand() {
  const { data } = await API.get('/api/v1/ops/command', {
    headers: transportLinkHeaders(),
  });
  return data;
}

// ── NERIS Tenant Onboarding (Portal) ──────────────────────────────────────

export type NERISOnboardingStepStatusApi = 'pending' | 'in_progress' | 'complete' | 'skipped';

export interface NERISOnboardingStepApi {
  id: string;
  label: string;
  status: NERISOnboardingStepStatusApi;
  required?: boolean;
}

export interface NERISOnboardingDepartmentApi {
  id: string;
  data?: {
    name?: string;
    reporting_mode?: string;
    [key: string]: unknown;
  };
}

export interface NERISOnboardingStatusApi {
  onboarding_id: string;
  department?: NERISOnboardingDepartmentApi;
  steps?: NERISOnboardingStepApi[];
  progress_percent?: number;
  required_complete?: number;
  required_total?: number;
  production_ready?: boolean;
  completed_at?: string | null;
  wi_dsps_checklist?: Record<string, boolean>;
  golive_items?: string[];
}

export interface NERISOnboardingStartPayload {
  department_name: string;
  state: string;
}

export interface FireIncidentAddressPayload {
  street: string;
  city: string;
  state: string;
  zip: string;
}

export interface FireValidationIncidentCreatePayload {
  incident_number: string;
  start_datetime: string;
  incident_type_code: string;
  address: FireIncidentAddressPayload;
}

export interface FireValidationIssueApi {
  severity: 'error' | 'warning';
  field_label?: string;
  path?: string;
  message: string;
  suggested_fix?: string;
}

export interface FireValidationIncidentApi {
  id?: string;
  incident_id?: string;
  [key: string]: unknown;
}

export interface FireValidationIncidentResultApi {
  issues?: FireValidationIssueApi[];
  [key: string]: unknown;
}

export async function getTenantNERISOnboardingStatus(): Promise<NERISOnboardingStatusApi | null> {
  try {
    const { data } = await API.get('/api/v1/tenant/neris/onboarding/status', {
      headers: transportLinkHeaders(),
    });
    return data as NERISOnboardingStatusApi;
  } catch (error: unknown) {
    if (axios.isAxiosError(error) && error.response?.status === 404) {
      return null;
    }
    throw error;
  }
}

export async function startTenantNERISOnboarding(
  payload: NERISOnboardingStartPayload,
): Promise<NERISOnboardingStatusApi> {
  const { data } = await API.post('/api/v1/tenant/neris/onboarding/start', payload, {
    headers: {
      ...transportLinkHeaders(),
      'Content-Type': 'application/json',
    },
  });
  return data as NERISOnboardingStatusApi;
}

export async function completeTenantNERISOnboardingStep(
  stepId: string,
  payload: { data: unknown },
): Promise<Record<string, unknown>> {
  const { data } = await API.post(`/api/v1/tenant/neris/onboarding/step/${stepId}/complete`, payload, {
    headers: {
      ...transportLinkHeaders(),
      'Content-Type': 'application/json',
    },
  });
  return asJsonObject(data);
}

export async function createFireValidationIncident(
  payload: FireValidationIncidentCreatePayload,
): Promise<FireValidationIncidentApi> {
  const { data } = await API.post('/api/v1/incidents/fire', payload, {
    headers: {
      ...transportLinkHeaders(),
      'Content-Type': 'application/json',
    },
  });
  return asJsonObject(data) as FireValidationIncidentApi;
}

export async function validateFireValidationIncident(
  incidentId: string,
): Promise<FireValidationIncidentResultApi> {
  const { data } = await API.post(`/api/v1/incidents/fire/${incidentId}/validate`, undefined, {
    headers: transportLinkHeaders(),
  });
  return asJsonObject(data) as FireValidationIncidentResultApi;
}

// ── Fax Inbox (Portal) ─────────────────────────────────────────────────────

export interface FaxMatchSuggestionApi {
  claim_id: string;
  patient_name?: string;
  score?: number;
}

export interface FaxItemApi {
  id: string;
  from_number?: string;
  to_number?: string;
  received_at?: string;
  page_count?: number;
  document_match_status?: string;
  status?: string;
  data?: {
    match_suggestions?: FaxMatchSuggestionApi[];
    claim_id?: string;
    patient_name?: string;
    match_type?: string;
    confidence?: number;
  };
}

function normalizeFaxItem(value: unknown): FaxItemApi {
  const row = asJsonObject(value);
  const data = asJsonObject(row.data);
  const suggestionsRaw = Array.isArray(data.match_suggestions) ? data.match_suggestions : [];
  return {
    id: asString(row.id),
    from_number: asString(row.from_number) || undefined,
    to_number: asString(row.to_number) || undefined,
    received_at: asString(row.received_at) || undefined,
    page_count: asNumber(row.page_count) ?? undefined,
    document_match_status: asString(row.document_match_status) || undefined,
    status: asString(row.status) || undefined,
    data: {
      match_suggestions: suggestionsRaw.map((suggestion) => {
        const item = asJsonObject(suggestion);
        return {
          claim_id: asString(item.claim_id),
          patient_name: asString(item.patient_name) || undefined,
          score: asNumber(item.score) ?? undefined,
        } as FaxMatchSuggestionApi;
      }),
      claim_id: asString(data.claim_id) || undefined,
      patient_name: asString(data.patient_name) || undefined,
      match_type: asString(data.match_type) || undefined,
      confidence: asNumber(data.confidence) ?? undefined,
    },
  };
}

export async function listFaxInbox(params?: {
  status?: string;
  limit?: number;
}): Promise<FaxItemApi[]> {
  const { data } = await API.get('/api/v1/fax/inbox', {
    headers: transportLinkHeaders(),
    params,
  });
  const rows = Array.isArray(data)
    ? data
    : Array.isArray(data?.items)
      ? data.items
      : Array.isArray(data?.faxes)
        ? data.faxes
        : [];
  return rows.map((row: unknown) => normalizeFaxItem(row));
}

export async function triggerFaxMatch(faxId: string): Promise<Record<string, unknown>> {
  const { data } = await API.post(`/api/v1/fax/${faxId}/match/trigger`, undefined, {
    headers: {
      ...transportLinkHeaders(),
      'Content-Type': 'application/json',
    },
  });
  return asJsonObject(data);
}

export async function attachFaxToClaim(
  claimId: string,
  payload: { fax_id: string; attachment_type: string },
): Promise<Record<string, unknown>> {
  const { data } = await API.post(`/api/v1/claims/${claimId}/documents/attach-fax`, payload, {
    headers: {
      ...transportLinkHeaders(),
      'Content-Type': 'application/json',
    },
  });
  return asJsonObject(data);
}

export async function detachFaxMatch(faxId: string): Promise<Record<string, unknown>> {
  const { data } = await API.post(`/api/v1/fax/${faxId}/match/detach`, undefined, {
    headers: {
      ...transportLinkHeaders(),
      'Content-Type': 'application/json',
    },
  });
  return asJsonObject(data);
}

export function getFaxDownloadUrl(faxId: string): string {
  return `${API.defaults.baseURL ?? ''}/api/v1/fax/${faxId}/download`;
}

// ── EDI (Portal) ───────────────────────────────────────────────────────────

export type EdiBatchStatusApi = 'pending' | 'submitted' | 'accepted' | 'rejected' | 'partial';

export interface EdiBatchApi {
  id: string;
  created_at?: string;
  claim_count?: number;
  status?: EdiBatchStatusApi | string;
  claim_ids?: string[];
  validation_errors?: string[];
  metadata?: Record<string, unknown>;
}

export interface EdiGenerateBatchPayload {
  claim_ids: string[];
  submitter_config: {
    npi: string;
    name: string;
    ein: string;
  };
}

export interface EdiIngest999Payload {
  x12_content: string;
  batch_id?: string;
}

export interface EdiIngest277Payload {
  x12_content: string;
}

export interface EdiIngest835Payload {
  x12_content: string;
}

export interface EdiClaimExplanationApi {
  explanation?: {
    overall_status?: string;
    adjustment_reasons?: { code: string; description: string }[];
    denial_analysis?: string;
    recommended_actions?: string[];
    next_steps?: string;
  };
  [key: string]: unknown;
}

function normalizeEdiBatch(value: unknown): EdiBatchApi {
  const row = asJsonObject(value);
  const claimIdsRaw = Array.isArray(row.claim_ids) ? row.claim_ids : [];
  const validationErrorsRaw = Array.isArray(row.validation_errors) ? row.validation_errors : [];
  return {
    id: asString(row.id),
    created_at: asString(row.created_at) || undefined,
    claim_count: asNumber(row.claim_count) ?? undefined,
    status: asString(row.status) || undefined,
    claim_ids: claimIdsRaw.map((claimId) => asString(claimId)).filter((claimId) => claimId.length > 0),
    validation_errors: validationErrorsRaw
      .map((error) => asString(error))
      .filter((error) => error.length > 0),
    metadata: isJsonObject(row.metadata) ? row.metadata : undefined,
  };
}

export async function listPortalEDIBatches(limit = 50): Promise<EdiBatchApi[]> {
  const { data } = await API.get('/api/v1/edi/batches', {
    headers: transportLinkHeaders(),
    params: { limit },
  });
  const rows = Array.isArray(data)
    ? data
    : Array.isArray(data?.items)
      ? data.items
      : Array.isArray(data?.batches)
        ? data.batches
        : [];
  return rows.map((row: unknown) => normalizeEdiBatch(row));
}

export async function generatePortalEDIBatch(payload: EdiGenerateBatchPayload): Promise<EdiBatchApi> {
  const { data } = await API.post('/api/v1/edi/batches/generate', payload, {
    headers: {
      ...transportLinkHeaders(),
      'Content-Type': 'application/json',
    },
  });
  return normalizeEdiBatch(data);
}

export async function ingestPortalEDI999(payload: EdiIngest999Payload): Promise<Record<string, unknown>> {
  const { data } = await API.post('/api/v1/edi/ingest/999', payload, {
    headers: {
      ...transportLinkHeaders(),
      'Content-Type': 'application/json',
    },
  });
  return asJsonObject(data);
}

export async function ingestPortalEDI277(payload: EdiIngest277Payload): Promise<Record<string, unknown>> {
  const { data } = await API.post('/api/v1/edi/ingest/277', payload, {
    headers: {
      ...transportLinkHeaders(),
      'Content-Type': 'application/json',
    },
  });
  return asJsonObject(data);
}

export async function ingestPortalEDI835(payload: EdiIngest835Payload): Promise<Record<string, unknown>> {
  const { data } = await API.post('/api/v1/edi/ingest/835', payload, {
    headers: {
      ...transportLinkHeaders(),
      'Content-Type': 'application/json',
    },
  });
  return asJsonObject(data);
}

export async function explainPortalEDIClaim(claimId: string): Promise<EdiClaimExplanationApi> {
  const { data } = await API.get(`/api/v1/edi/claims/${claimId}/explain`, {
    headers: transportLinkHeaders(),
  });
  return asJsonObject(data) as EdiClaimExplanationApi;
}

export function getEDIBatchDownloadUrl(batchId: string): string {
  return `${API.defaults.baseURL ?? ''}/api/v1/edi/batches/${batchId}/download`;
}

// ── Cases + CMS Gate (Portal) ─────────────────────────────────────────────

export type CaseTransportModeApi = 'ground' | 'rotor' | 'fixed_wing';
export type CasePriorityApi = 'routine' | 'urgent' | 'emergent';

export interface CaseTimelineEventApi {
  event: string;
  timestamp: string;
  [key: string]: unknown;
}

export interface CaseRecordApi {
  case_id: string;
  transport_mode: CaseTransportModeApi;
  status: string;
  priority: CasePriorityApi;
  patient_name?: string;
  opened_at: string;
  transport_request_id?: string;
  cad_call_id?: string;
  timeline?: CaseTimelineEventApi[];
  [key: string]: unknown;
}

export interface CaseCreatePayload {
  transport_mode: CaseTransportModeApi;
  priority: CasePriorityApi;
  patient_name: string;
  origin_address: string;
  destination_address?: string;
  transport_request_id?: string;
  cad_call_id?: string;
}

export interface CaseCMSGatePayload {
  patient_condition: string;
  transport_reason: string;
  transport_level: 'BLS' | 'ALS' | 'SCT' | 'SPECIALTY';
  origin_address: string;
  destination_name: string;
  pcs_on_file: boolean;
  pcs_obtained: boolean;
  medical_necessity_documented: boolean;
  patient_signature: boolean;
  signature_on_file: boolean;
  primary_insurance_id: string;
  medicare_id: string;
  medicaid_id: string;
}

export interface CaseCMSGateResultApi {
  score: number;
  passed: boolean;
  hard_block?: boolean;
  bs_flag?: boolean;
  gates?: { name: string; passed: boolean; weight: number }[];
  issues?: string[];
  [key: string]: unknown;
}

function normalizeCaseRecord(value: unknown): CaseRecordApi {
  const row = asJsonObject(value);
  const timelineRaw = Array.isArray(row.timeline) ? row.timeline : [];
  const transportModeRaw = asString(row.transport_mode, 'ground').toLowerCase();
  const priorityRaw = asString(row.priority, 'routine').toLowerCase();
  const transport_mode: CaseTransportModeApi =
    transportModeRaw === 'rotor' || transportModeRaw === 'fixed_wing' ? (transportModeRaw as CaseTransportModeApi) : 'ground';
  const priority: CasePriorityApi =
    priorityRaw === 'urgent' || priorityRaw === 'emergent' ? (priorityRaw as CasePriorityApi) : 'routine';

  return {
    ...(row as CaseRecordApi),
    case_id: asString(row.case_id || row.id),
    transport_mode,
    status: asString(row.status),
    priority,
    patient_name: asString(row.patient_name) || undefined,
    opened_at: asString(row.opened_at || row.created_at),
    transport_request_id: asString(row.transport_request_id) || undefined,
    cad_call_id: asString(row.cad_call_id) || undefined,
    timeline: timelineRaw.map((event) => {
      const item = asJsonObject(event);
      return {
        ...(item as CaseTimelineEventApi),
        event: asString(item.event),
        timestamp: asString(item.timestamp),
      };
    }),
  };
}

export async function listPortalCases(): Promise<CaseRecordApi[]> {
  const { data } = await API.get('/api/v1/cases/', {
    headers: transportLinkHeaders(),
  });
  const rows = Array.isArray(data) ? data : Array.isArray(data?.cases) ? data.cases : [];
  return rows.map((row: unknown) => normalizeCaseRecord(row));
}

export async function updatePortalCaseStatus(
  caseId: string,
  payload: { status: string },
): Promise<Record<string, unknown>> {
  const { data } = await API.patch(`/api/v1/cases/${caseId}/status`, payload, {
    headers: {
      ...transportLinkHeaders(),
      'Content-Type': 'application/json',
    },
  });
  return asJsonObject(data);
}

export async function createPortalCase(payload: CaseCreatePayload): Promise<CaseRecordApi> {
  const { data } = await API.post('/api/v1/cases/', payload, {
    headers: {
      ...transportLinkHeaders(),
      'Content-Type': 'application/json',
    },
  });
  return normalizeCaseRecord(data);
}

export async function evaluatePortalCaseCMSGate(
  caseId: string,
  payload: CaseCMSGatePayload,
): Promise<CaseCMSGateResultApi> {
  const { data } = await API.post(`/api/v1/cms-gate/cases/${caseId}/evaluate`, payload, {
    headers: {
      ...transportLinkHeaders(),
      'Content-Type': 'application/json',
    },
  });
  return asJsonObject(data) as CaseCMSGateResultApi;
}
