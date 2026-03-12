import axios, { AxiosHeaders } from 'axios';

export const API = axios.create({
  baseURL:
    process.env.NEXT_PUBLIC_API_BASE ||
    process.env.NEXT_PUBLIC_BACKEND_URL ||
    process.env.NEXT_PUBLIC_API_URL ||
    "",
  withCredentials: true,
});

API.interceptors.request.use((config) => {
  if (typeof window === 'undefined') {
    return config;
  }

  const token = localStorage.getItem('token') || localStorage.getItem('qs_token') || '';
  const headers = config.headers instanceof AxiosHeaders
    ? config.headers
    : new AxiosHeaders(config.headers);
  const hasAuthHeader = Boolean(headers.get('Authorization'));

  if (token && !hasAuthHeader) {
    headers.set('Authorization', `Bearer ${token}`);
  }

  config.headers = headers;

  return config;
});

export async function getExecutiveSummary() {
  const res = await API.get('/api/v1/founder/executive-summary', {
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

export interface CADLatestUnitLocationApi {
  unit_id: string;
  lat: number | null;
  lng: number | null;
  recorded_at: string;
  record_id: string;
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

export function aiHeaders() {
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
  clinical_datasets?: {
    icd10?: { version?: string; term_count?: number };
    rxnorm?: { status?: string; source?: string };
    snomed?: { status?: string; source?: string };
    nemsis?: { version?: string; element_count?: number };
    npi?: { verification_supported?: boolean; source?: string };
  };
  integration_readiness?: {
    required_missing?: string[];
    required_missing_count?: number;
  };
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

export async function getQuantumVaultDocuments(): Promise<{ documents?: unknown[] }> {
  const res = await API.get('/api/quantum-founder/vault/documents');
  return res.data as { documents?: unknown[] };
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

// ── Founder Accounting: Bank Connections ─────────────────────────────────────

export async function getBankConnectionStatus() {
  const res = await API.get('/api/quantum-founder/accounting/bank/status');
  return res.data;
}

export async function connectSimpleFIN(setupToken: string) {
  const res = await API.post('/api/quantum-founder/accounting/bank/simplefin/connect', {
    setup_token: setupToken,
  });
  return res.data;
}

export async function getSimpleFINAccounts(daysBack = 90) {
  const res = await API.get('/api/quantum-founder/accounting/bank/simplefin/accounts', {
    params: { days_back: daysBack },
  });
  return res.data;
}

export async function importBankCSV(file: File, institution = 'generic', accountId = 'imported') {
  const formData = new FormData();
  formData.append('file', file);
  formData.append('institution', institution);
  formData.append('account_id', accountId);
  const res = await API.post('/api/quantum-founder/accounting/bank/import/csv', formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
  });
  return res.data;
}

export async function importBankOFX(file: File, institution = 'Imported') {
  const formData = new FormData();
  formData.append('file', file);
  formData.append('institution', institution);
  const res = await API.post('/api/quantum-founder/accounting/bank/import/ofx', formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
  });
  return res.data;
}

// ── Founder Accounting: E-file ────────────────────────────────────────────────

export async function getEfileStatus() {
  const res = await API.get('/api/quantum-founder/efile/realtime-status');
  return res.data;
}

export async function scanReceipt(imageFile: File) {
  const formData = new FormData();
  formData.append('receipt_image', imageFile);
  const res = await API.post('/api/quantum-founder/receipts/scan', formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
  });
  return res.data;
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
  return res.data;
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
  const token = localStorage.getItem('token') || localStorage.getItem('qs_token') || '';
  return {
    'Content-Type': 'application/json',
    ...(token ? { Authorization: `Bearer ${token}` } : {}),
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

export async function getLatestCADUnitLocations(limit: number = 500): Promise<CADLatestUnitLocationApi[]> {
  const res = await API.get('/api/v1/cad/units/locations/latest', {
    headers: aiHeaders(),
    params: { limit },
  });
  const items = Array.isArray(res.data?.items) ? (res.data.items as unknown[]) : [];
  return items
    .map((raw) => {
      const obj = (raw ?? {}) as Record<string, unknown>;
      return {
        unit_id: asString(obj.unit_id),
        lat: asNumber(obj.lat),
        lng: asNumber(obj.lng),
        recorded_at: asIsoDateString(obj.recorded_at),
        record_id: asString(obj.record_id),
      };
    })
    .filter((loc) => Boolean(loc.unit_id) && Boolean(loc.record_id) && loc.lat != null && loc.lng != null);
}

export async function listCADUnitsWithLatestLocations(): Promise<CADUnitApi[]> {
  const [units, locations] = await Promise.all([
    listCADUnits(),
    getLatestCADUnitLocations().catch(() => [] as CADLatestUnitLocationApi[]),
  ]);
  const byUnitId = new Map<string, CADLatestUnitLocationApi>();
  locations.forEach((loc) => byUnitId.set(loc.unit_id, loc));

  return units.map((unit) => {
    const loc = byUnitId.get(unit.id);
    if (!loc) return unit;
    return {
      ...unit,
      lat: loc.lat != null && Number.isFinite(loc.lat) ? loc.lat : unit.lat,
      lng: loc.lng != null && Number.isFinite(loc.lng) ? loc.lng : unit.lng,
    };
  });
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

// ── Analytics API ─────────────────────────────────────────────────────────────

export async function getAnalyticsExecutiveSummary(agencyId: string): Promise<Record<string, unknown>> {
  const res = await API.get(`/api/v1/analytics/${agencyId}/executive-summary`, { headers: aiHeaders() });
  return res.data;
}

export async function getAnalyticsOperationalMetrics(
  agencyId: string,
  periodStart?: string,
  periodEnd?: string,
): Promise<Record<string, unknown>> {
  const params: Record<string, string> = {};
  if (periodStart) params.period_start = periodStart;
  if (periodEnd) params.period_end = periodEnd;
  const res = await API.get(`/api/v1/analytics/${agencyId}/metrics/operational`, {
    headers: aiHeaders(),
    params,
  });
  return res.data;
}

export async function getAnalyticsFinancialMetrics(
  agencyId: string,
  periodStart?: string,
  periodEnd?: string,
): Promise<Record<string, unknown>> {
  const params: Record<string, string> = {};
  if (periodStart) params.period_start = periodStart;
  if (periodEnd) params.period_end = periodEnd;
  const res = await API.get(`/api/v1/analytics/${agencyId}/metrics/financial`, {
    headers: aiHeaders(),
    params,
  });
  return res.data;
}

export async function getAnalyticsClinicalMetrics(
  agencyId: string,
  periodStart?: string,
  periodEnd?: string,
): Promise<Record<string, unknown>> {
  const params: Record<string, string> = {};
  if (periodStart) params.period_start = periodStart;
  if (periodEnd) params.period_end = periodEnd;
  const res = await API.get(`/api/v1/analytics/${agencyId}/metrics/clinical`, {
    headers: aiHeaders(),
    params,
  });
  return res.data;
}

export async function getAnalyticsReadinessMetrics(
  agencyId: string,
  periodStart?: string,
  periodEnd?: string,
): Promise<Record<string, unknown>> {
  const params: Record<string, string> = {};
  if (periodStart) params.period_start = periodStart;
  if (periodEnd) params.period_end = periodEnd;
  const res = await API.get(`/api/v1/analytics/${agencyId}/metrics/readiness`, {
    headers: aiHeaders(),
    params,
  });
  return res.data;
}

export async function listAnalyticsReports(agencyId: string): Promise<Record<string, unknown>> {
  const res = await API.get(`/api/v1/analytics/${agencyId}/reports`, { headers: aiHeaders() });
  return res.data;
}

export async function generateAnalyticsReport(
  agencyId: string,
  reportDefinitionId: string,
): Promise<Record<string, unknown>> {
  const res = await API.post(
    `/api/v1/analytics/${agencyId}/reports/generate`,
    { report_definition_id: reportDefinitionId },
    { headers: aiHeaders() }
  );
  return res.data;
}

export async function getAnalyticsAlerts(
  agencyId: string,
  severity?: string,
): Promise<Record<string, unknown>> {
  const params: Record<string, string> = {};
  if (severity) params.severity = severity;
  const res = await API.get(`/api/v1/analytics/${agencyId}/alerts`, {
    headers: aiHeaders(),
    params,
  });
  return res.data;
}

















































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































































// === Auto-generated API stubs for build compatibility ===

export async function ackFleetAlert(...args: unknown[]) {
  const [payload, params] = args as [unknown, unknown];
  void payload; void params;
  const res = await API.post('/api/v1/ackFleetAlert', payload); return res.data;
}

export async function activateNERISPack(...args: unknown[]) {
  const [payload, params] = args as [unknown, unknown];
  void payload; void params;
  const res = await API.post('/api/v1/activateNERISPack', payload); return res.data;
}

export async function approveCopilotRun(...args: unknown[]) {
  const [payload, params] = args as [unknown, unknown];
  void payload; void params;
  const res = await API.post('/api/v1/approveCopilotRun', payload); return res.data;
}

export async function approveSchedulingAIDraft(...args: unknown[]) {
  const [payload, params] = args as [unknown, unknown];
  void payload; void params;
  const res = await API.post('/api/v1/approveSchedulingAIDraft', payload); return res.data;
}

export async function approveTemplate(...args: unknown[]) {
  const [payload, params] = args as [unknown, unknown];
  void payload; void params;
  const res = await API.post('/api/v1/approveTemplate', payload); return res.data;
}

export async function attachFaxToClaim(...args: unknown[]) {
  const [payload, params] = args as [unknown, unknown];
  void payload; void params;
  const res = await API.post('/api/v1/attachFaxToClaim', payload); return res.data;
}

export async function batchResubmitClaims(...args: unknown[]) {
  const [payload, params] = args as [unknown, unknown];
  void payload; void params;
  const res = await API.post('/api/v1/batchResubmitClaims', payload); return res.data;
}

export async function buildFounderLegalPacket(...args: unknown[]) {
  const [payload, params] = args as [unknown, unknown];
  void payload; void params;
  const res = await API.post('/api/v1/buildFounderLegalPacket', payload); return res.data;
}

export async function buildTRIPCandidates(...args: unknown[]) {
  const [payload, params] = args as [unknown, unknown];
  void payload; void params;
  const res = await API.post('/api/v1/buildTRIPCandidates', payload); return res.data;
}

export async function bulkGenerateTemplates(...args: unknown[]) {
  const [payload, params] = args as [unknown, unknown];
  void payload; void params;
  const res = await API.post('/api/v1/bulkGenerateTemplates', payload); return res.data;
}

export async function calculateROI(...args: unknown[]) {
  const [payload, params] = args as [unknown, unknown];
  void payload; void params;
  const res = await API.get('/api/v1/calculateROI', { params: params as Record<string, string> ?? undefined }); return res.data;
}

export async function cancelDispatchMission(...args: unknown[]) {
  const [payload, params] = args as [unknown, unknown];
  void payload; void params;
  const res = await API.post('/api/v1/cancelDispatchMission', payload); return res.data;
}

export async function checkVisibilityDataMinimization<T = any>(...args: unknown[]): Promise<T> {
  const [payload, params] = args as [unknown, unknown];
  void payload; void params;
  const res = await API.get('/api/v1/checkVisibilityDataMinimization', { params: params as Record<string, string> ?? undefined }); return res.data as T;
}

export async function checkVisibilityZeroTrust<T = any>(...args: unknown[]): Promise<T> {
  const [payload, params] = args as [unknown, unknown];
  void payload; void params;
  const res = await API.get('/api/v1/checkVisibilityZeroTrust', { params: params as Record<string, string> ?? undefined }); return res.data as T;
}

export async function classifyLegalRequest(...args: unknown[]) {
  const [payload, params] = args as [unknown, unknown];
  void payload; void params;
  const res = await API.post('/api/v1/classifyLegalRequest', payload); return res.data;
}

export async function cloneTemplate(...args: unknown[]) {
  const [payload, params] = args as [unknown, unknown];
  void payload; void params;
  const res = await API.post('/api/v1/cloneTemplate', payload); return res.data;
}

export async function closeFounderLegalRequest(...args: unknown[]) {
  const [payload, params] = args as [unknown, unknown];
  void payload; void params;
  const res = await API.post('/api/v1/closeFounderLegalRequest', payload); return res.data;
}

export async function compileNERISPack(...args: unknown[]) {
  const [payload, params] = args as [unknown, unknown];
  void payload; void params;
  const res = await API.post('/api/v1/compileNERISPack', payload); return res.data;
}

export async function completeLegalUpload(...args: unknown[]) {
  const [payload, params] = args as [unknown, unknown];
  void payload; void params;
  const res = await API.post('/api/v1/completeLegalUpload', payload); return res.data;
}

export async function completeTenantNERISOnboardingStep(...args: unknown[]) {
  const [payload, params] = args as [unknown, unknown];
  void payload; void params;
  const res = await API.post('/api/v1/completeTenantNERISOnboardingStep', payload); return res.data;
}

export async function createCopilotSession(...args: unknown[]) {
  const [payload, params] = args as [unknown, unknown];
  void payload; void params;
  const res = await API.post('/api/v1/createCopilotSession', payload); return res.data;
}

export async function createCrewlinkAlert(...args: unknown[]) {
  const [payload, params] = args as [unknown, unknown];
  void payload; void params;
  const res = await API.post('/api/v1/createCrewlinkAlert', payload); return res.data;
}

export async function createDEAEvidenceBundle(...args: unknown[]) {
  const [payload, params] = args as [unknown, unknown];
  void payload; void params;
  const res = await API.post('/api/v1/createDEAEvidenceBundle', payload); return res.data;
}

export async function createDatasetAIExpression(...args: unknown[]) {
  const [payload, params] = args as [unknown, unknown];
  void payload; void params;
  const res = await API.post('/api/v1/createDatasetAIExpression', payload); return res.data;
}

export async function createDispatchRequest(...args: unknown[]) {
  const [payload, params] = args as [unknown, unknown];
  void payload; void params;
  const res = await API.post('/api/v1/createDispatchRequest', payload); return res.data;
}

export async function createDispatchRequestPortal(...args: unknown[]) {
  const [payload, params] = args as [unknown, unknown];
  void payload; void params;
  const res = await API.post('/api/v1/createDispatchRequestPortal', payload); return res.data;
}

export async function createExpenseEntry(...args: unknown[]) {
  const [payload, params] = args as [unknown, unknown];
  void payload; void params;
  const res = await API.post('/api/v1/createExpenseEntry', payload); return res.data;
}

export async function createFireValidationIncident(...args: unknown[]) {
  const [payload, params] = args as [unknown, unknown];
  void payload; void params;
  const res = await API.post('/api/v1/createFireValidationIncident', payload); return res.data;
}

export async function createFounderLegalDeliveryLink(...args: unknown[]) {
  const [payload, params] = args as [unknown, unknown];
  void payload; void params;
  const res = await API.post('/api/v1/createFounderLegalDeliveryLink', payload); return res.data;
}

export async function createInvoice(...args: unknown[]) {
  const [payload, params] = args as [unknown, unknown];
  void payload; void params;
  const res = await API.post('/api/v1/createInvoice', payload); return res.data;
}

export async function createLegalPaymentCheckout(...args: unknown[]) {
  const [payload, params] = args as [unknown, unknown];
  void payload; void params;
  const res = await API.post('/api/v1/createLegalPaymentCheckout', payload); return res.data;
}

export async function createLegalRequestIntake(...args: unknown[]) {
  const [payload, params] = args as [unknown, unknown];
  void payload; void params;
  const res = await API.post('/api/v1/createLegalRequestIntake', payload); return res.data;
}

export async function createLegalUploadPresign(...args: unknown[]) {
  const [payload, params] = args as [unknown, unknown];
  void payload; void params;
  const res = await API.post('/api/v1/createLegalUploadPresign', payload); return res.data;
}

export async function createNEMSISPack(...args: unknown[]) {
  const [payload, params] = args as [unknown, unknown];
  void payload; void params;
  const res = await API.post('/api/v1/createNEMSISPack', payload); return res.data;
}

export async function createPolicy(...args: unknown[]) {
  const [payload, params] = args as [unknown, unknown];
  void payload; void params;
  const res = await API.post('/api/v1/createPolicy', payload); return res.data;
}

export async function createPortalCase(...args: unknown[]) {
  const [payload, params] = args as [unknown, unknown];
  void payload; void params;
  const res = await API.post('/api/v1/createPortalCase', payload); return res.data;
}

export async function createPortalFireIncident(...args: unknown[]) {
  const [payload, params] = args as [unknown, unknown];
  void payload; void params;
  const res = await API.post('/api/v1/createPortalFireIncident', payload); return res.data;
}

export async function createPortalFleetInspectionTemplate(...args: unknown[]) {
  const [payload, params] = args as [unknown, unknown];
  void payload; void params;
  const res = await API.post('/api/v1/createPortalFleetInspectionTemplate', payload); return res.data;
}

export async function createPortalFleetWorkOrder(...args: unknown[]) {
  const [payload, params] = args as [unknown, unknown];
  void payload; void params;
  const res = await API.post('/api/v1/createPortalFleetWorkOrder', payload); return res.data;
}

export async function createPortalSupportThread(...args: unknown[]) {
  const [payload, params] = args as [unknown, unknown];
  void payload; void params;
  const res = await API.post('/api/v1/createPortalSupportThread', payload); return res.data;
}

export async function createPortalSupportThreadMessage(...args: unknown[]) {
  const [payload, params] = args as [unknown, unknown];
  void payload; void params;
  const res = await API.post('/api/v1/createPortalSupportThreadMessage', payload); return res.data;
}

export async function createPricebookEntry(...args: unknown[]) {
  const [payload, params] = args as [unknown, unknown];
  void payload; void params;
  const res = await API.post('/api/v1/createPricebookEntry', payload); return res.data;
}

export async function createPublicOnboardingLegalPacket<T = any>(...args: unknown[]): Promise<T> {
  const [payload, params] = args as [unknown, unknown];
  void payload; void params;
  const res = await API.post('/api/v1/createPublicOnboardingLegalPacket', payload); return res.data as T;
}

export async function createRoleAssignment(...args: unknown[]) {
  const [payload, params] = args as [unknown, unknown];
  void payload; void params;
  const res = await API.post('/api/v1/createRoleAssignment', payload); return res.data;
}

export async function createTemplate(...args: unknown[]) {
  const [payload, params] = args as [unknown, unknown];
  void payload; void params;
  const res = await API.post('/api/v1/createTemplate', payload); return res.data;
}

export async function createVisibilityRule(...args: unknown[]) {
  const [payload, params] = args as [unknown, unknown];
  void payload; void params;
  const res = await API.post('/api/v1/createVisibilityRule', payload); return res.data;
}

export async function deidentifyVisibilityRecord<T = any>(...args: unknown[]): Promise<T> {
  const [payload, params] = args as [unknown, unknown];
  void payload; void params;
  const res = await API.post('/api/v1/deidentifyVisibilityRecord', payload); return res.data as T;
}

export async function deletePolicy(...args: unknown[]) {
  const [payload, params] = args as [unknown, unknown];
  void payload; void params;
  const res = await API.delete('/api/v1/deletePolicy', { data: payload }); return res.data;
}

export async function deleteRoleAssignment(...args: unknown[]) {
  const [payload, params] = args as [unknown, unknown];
  void payload; void params;
  const res = await API.delete('/api/v1/deleteRoleAssignment', { data: payload }); return res.data;
}

export async function deleteTelnyxCNAM(...args: unknown[]) {
  const [payload, params] = args as [unknown, unknown];
  void payload; void params;
  const res = await API.delete('/api/v1/deleteTelnyxCNAM', { data: payload }); return res.data;
}

export async function deleteVisibilityRule(...args: unknown[]) {
  const [payload, params] = args as [unknown, unknown];
  void payload; void params;
  const res = await API.delete('/api/v1/deleteVisibilityRule', { data: payload }); return res.data;
}

export async function detachFaxMatch(...args: unknown[]) {
  const [payload, params] = args as [unknown, unknown];
  void payload; void params;
  const res = await API.post('/api/v1/detachFaxMatch', payload); return res.data;
}

export async function escalateCrewlinkAlert(...args: unknown[]) {
  const [payload, params] = args as [unknown, unknown];
  void payload; void params;
  const res = await API.post('/api/v1/escalateCrewlinkAlert', payload); return res.data;
}

export async function evaluatePortalCaseCMSGate(...args: unknown[]) {
  const [payload, params] = args as [unknown, unknown];
  void payload; void params;
  const res = await API.get('/api/v1/evaluatePortalCaseCMSGate', { params: params as Record<string, string> ?? undefined }); return res.data;
}

export async function evaluateVisibilityContext<T = any>(...args: unknown[]): Promise<T> {
  const [payload, params] = args as [unknown, unknown];
  void payload; void params;
  const res = await API.get('/api/v1/evaluateVisibilityContext', { params: params as Record<string, string> ?? undefined }); return res.data as T;
}

export async function executeCopilotRun(...args: unknown[]) {
  const [payload, params] = args as [unknown, unknown];
  void payload; void params;
  const res = await API.post('/api/v1/executeCopilotRun', payload); return res.data;
}

export async function explainPortalEDIClaim(...args: unknown[]) {
  const [payload, params] = args as [unknown, unknown];
  void payload; void params;
  const res = await API.get('/api/v1/explainPortalEDIClaim', { params: params as Record<string, string> ?? undefined }); return res.data;
}

export async function exportPortalNerisIncident(...args: unknown[]) {
  const [payload, params] = args as [unknown, unknown];
  void payload; void params;
  const res = await API.post('/api/v1/exportPortalNerisIncident', payload); return res.data;
}

export async function flagCrewFatigue(...args: unknown[]) {
  const [payload, params] = args as [unknown, unknown];
  void payload; void params;
  const res = await API.post('/api/v1/flagCrewFatigue', payload); return res.data;
}

export async function generatePatchTasksFromResult(...args: unknown[]) {
  const [payload, params] = args as [unknown, unknown];
  void payload; void params;
  const res = await API.post('/api/v1/generatePatchTasksFromResult', payload); return res.data;
}

export async function generatePortalEDIBatch(...args: unknown[]) {
  const [payload, params] = args as [unknown, unknown];
  void payload; void params;
  const res = await API.post('/api/v1/generatePortalEDIBatch', payload); return res.data;
}

export async function generateTRIPExport(...args: unknown[]) {
  const [payload, params] = args as [unknown, unknown];
  void payload; void params;
  const res = await API.post('/api/v1/generateTRIPExport', payload); return res.data;
}

export async function getARConcentrationRisk(...args: unknown[]) {
  const [payload, params] = args as [unknown, unknown];
  void payload; void params;
  const res = await API.get('/api/v1/getARConcentrationRisk', { params: params as Record<string, string> ?? undefined }); return res.data;
}

export async function getActiveCrewPages(...args: unknown[]) {
  const [payload, params] = args as [unknown, unknown];
  void payload; void params;
  const res = await API.get('/api/v1/getActiveCrewPages', { params: params as Record<string, string> ?? undefined }); return res.data;
}

export async function getActiveNEMSISPacks(...args: unknown[]) {
  const [payload, params] = args as [unknown, unknown];
  void payload; void params;
  const res = await API.get('/api/v1/getActiveNEMSISPacks', { params: params as Record<string, string> ?? undefined }); return res.data;
}

export async function getActivePricebook(...args: unknown[]) {
  const [payload, params] = args as [unknown, unknown];
  void payload; void params;
  const res = await API.get('/api/v1/getActivePricebook', { params: params as Record<string, string> ?? undefined }); return res.data;
}

export async function getAgentStreamUrl(...args: unknown[]) {
  const [payload, params] = args as [unknown, unknown];
  void payload; void params;
  const res = await API.get('/api/v1/getAgentStreamUrl', { params: params as Record<string, string> ?? undefined }); return res.data;
}

export async function getBackupsStatus(...args: unknown[]) {
  const [payload, params] = args as [unknown, unknown];
  void payload; void params;
  const res = await API.get('/api/v1/getBackupsStatus', { params: params as Record<string, string> ?? undefined }); return res.data;
}

export async function getBillingAlerts(...args: unknown[]) {
  const [payload, params] = args as [unknown, unknown];
  void payload; void params;
  const res = await API.get('/api/v1/getBillingAlerts', { params: params as Record<string, string> ?? undefined }); return res.data;
}

export async function getBillingCommandDashboard(...args: unknown[]) {
  const [payload, params] = args as [unknown, unknown];
  void payload; void params;
  const res = await API.get('/api/v1/getBillingCommandDashboard', { params: params as Record<string, string> ?? undefined }); return res.data;
}

export async function getBillingExecutiveSummary(...args: unknown[]) {
  const [payload, params] = args as [unknown, unknown];
  void payload; void params;
  const res = await API.get('/api/v1/getBillingExecutiveSummary', { params: params as Record<string, string> ?? undefined }); return res.data;
}

export async function getBillingHealth(...args: unknown[]) {
  const [payload, params] = args as [unknown, unknown];
  void payload; void params;
  const res = await API.get('/api/v1/getBillingHealth', { params: params as Record<string, string> ?? undefined }); return res.data;
}

export async function getBillingKPIs(...args: unknown[]) {
  const [payload, params] = args as [unknown, unknown];
  void payload; void params;
  const res = await API.get('/api/v1/getBillingKPIs', { params: params as Record<string, string> ?? undefined }); return res.data;
}

export async function getCMSGateAuditHistory(...args: unknown[]) {
  const [payload, params] = args as [unknown, unknown];
  void payload; void params;
  const res = await API.get('/api/v1/getCMSGateAuditHistory', { params: params as Record<string, string> ?? undefined }); return res.data;
}

export async function getCMSGateAuditSummary(...args: unknown[]) {
  const [payload, params] = args as [unknown, unknown];
  void payload; void params;
  const res = await API.get('/api/v1/getCMSGateAuditSummary', { params: params as Record<string, string> ?? undefined }); return res.data;
}

export async function getChurnRisk(...args: unknown[]) {
  const [payload, params] = args as [unknown, unknown];
  void payload; void params;
  const res = await API.get('/api/v1/getChurnRisk', { params: params as Record<string, string> ?? undefined }); return res.data;
}

export async function getClaimThroughput(...args: unknown[]) {
  const [payload, params] = args as [unknown, unknown];
  void payload; void params;
  const res = await API.get('/api/v1/getClaimThroughput', { params: params as Record<string, string> ?? undefined }); return res.data;
}

export async function getComplianceCommandSummary(...args: unknown[]) {
  const [payload, params] = args as [unknown, unknown];
  void payload; void params;
  const res = await API.get('/api/v1/getComplianceCommandSummary', { params: params as Record<string, string> ?? undefined }); return res.data;
}

export async function getComplianceCommandSummaryPortal(...args: unknown[]) {
  const [payload, params] = args as [unknown, unknown];
  void payload; void params;
  const res = await API.get('/api/v1/getComplianceCommandSummaryPortal', { params: params as Record<string, string> ?? undefined }); return res.data;
}

export async function getCopilotMessages(...args: unknown[]) {
  const [payload, params] = args as [unknown, unknown];
  void payload; void params;
  const res = await API.get('/api/v1/getCopilotMessages', { params: params as Record<string, string> ?? undefined }); return res.data;
}

export async function getCopilotRun(...args: unknown[]) {
  const [payload, params] = args as [unknown, unknown];
  void payload; void params;
  const res = await API.get('/api/v1/getCopilotRun', { params: params as Record<string, string> ?? undefined }); return res.data;
}

export async function getCopilotSessions(...args: unknown[]) {
  const [payload, params] = args as [unknown, unknown];
  void payload; void params;
  const res = await API.get('/api/v1/getCopilotSessions', { params: params as Record<string, string> ?? undefined }); return res.data;
}

export async function getCostBudget(...args: unknown[]) {
  const [payload, params] = args as [unknown, unknown];
  void payload; void params;
  const res = await API.get('/api/v1/getCostBudget', { params: params as Record<string, string> ?? undefined }); return res.data;
}

export async function getCostByTenant(...args: unknown[]) {
  const [payload, params] = args as [unknown, unknown];
  void payload; void params;
  const res = await API.get('/api/v1/getCostByTenant', { params: params as Record<string, string> ?? undefined }); return res.data;
}

export async function getCrewAvailability(...args: unknown[]) {
  const [payload, params] = args as [unknown, unknown];
  void payload; void params;
  const res = await API.get('/api/v1/getCrewAvailability', { params: params as Record<string, string> ?? undefined }); return res.data;
}

export async function getCrewQualifications(...args: unknown[]) {
  const [payload, params] = args as [unknown, unknown];
  void payload; void params;
  const res = await API.get('/api/v1/getCrewQualifications', { params: params as Record<string, string> ?? undefined }); return res.data;
}

export async function getCrewlinkAlerts(...args: unknown[]) {
  const [payload, params] = args as [unknown, unknown];
  void payload; void params;
  const res = await API.get('/api/v1/getCrewlinkAlerts', { params: params as Record<string, string> ?? undefined }); return res.data;
}

export async function getDEAEvidenceBundleDetail(...args: unknown[]) {
  const [payload, params] = args as [unknown, unknown];
  void payload; void params;
  const res = await API.get('/api/v1/getDEAEvidenceBundleDetail', { params: params as Record<string, string> ?? undefined }); return res.data;
}

export async function getDEAEvidenceBundlesHistory(...args: unknown[]) {
  const [payload, params] = args as [unknown, unknown];
  void payload; void params;
  const res = await API.get('/api/v1/getDEAEvidenceBundlesHistory', { params: params as Record<string, string> ?? undefined }); return res.data;
}

export async function getDEANarcoticsAuditHistory(...args: unknown[]) {
  const [payload, params] = args as [unknown, unknown];
  void payload; void params;
  const res = await API.get('/api/v1/getDEANarcoticsAuditHistory', { params: params as Record<string, string> ?? undefined }); return res.data;
}

export async function getDatasetActiveDevices(...args: unknown[]) {
  const [payload, params] = args as [unknown, unknown];
  void payload; void params;
  const res = await API.get('/api/v1/getDatasetActiveDevices', { params: params as Record<string, string> ?? undefined }); return res.data;
}

export async function getDatasetExports(...args: unknown[]) {
  const [payload, params] = args as [unknown, unknown];
  void payload; void params;
  const res = await API.get('/api/v1/getDatasetExports', { params: params as Record<string, string> ?? undefined }); return res.data;
}

export async function getDatasetStatus(...args: unknown[]) {
  const [payload, params] = args as [unknown, unknown];
  void payload; void params;
  const res = await API.get('/api/v1/getDatasetStatus', { params: params as Record<string, string> ?? undefined }); return res.data;
}

export async function getDenialHeatmap(...args: unknown[]) {
  const [payload, params] = args as [unknown, unknown];
  void payload; void params;
  const res = await API.get('/api/v1/getDenialHeatmap', { params: params as Record<string, string> ?? undefined }); return res.data;
}

export async function getDispatchMissions(...args: unknown[]) {
  const [payload, params] = args as [unknown, unknown];
  void payload; void params;
  const res = await API.get('/api/v1/getDispatchMissions', { params: params as Record<string, string> ?? undefined }); return res.data;
}

export async function getDocument(...args: unknown[]) {
  const [payload, params] = args as [unknown, unknown];
  void payload; void params;
  const res = await API.get('/api/v1/getDocument', { params: params as Record<string, string> ?? undefined }); return res.data;
}

export async function getDocumentUploadUrl(...args: unknown[]): Promise<{ upload_url?: string; document_id?: string; s3_key?: string }> {
  const [payload, params] = args as [unknown, unknown];
  void payload; void params;
  const res = await API.get('/api/v1/getDocumentUploadUrl', { params: params as Record<string, string> ?? undefined }); return res.data as { upload_url?: string; document_id?: string; s3_key?: string };
}

export async function getEDIBatchDownloadUrl(...args: unknown[]) {
  const [payload, params] = args as [unknown, unknown];
  void payload; void params;
  const res = await API.get('/api/v1/getEDIBatchDownloadUrl', { params: params as Record<string, string> ?? undefined }); return res.data;
}

export async function getEventsFeed(...args: unknown[]) {
  const [payload, params] = args as [unknown, unknown];
  void payload; void params;
  const res = await API.get('/api/v1/getEventsFeed', { params: params as Record<string, string> ?? undefined }); return res.data;
}

export async function getEventsUnreadCount(...args: unknown[]) {
  const [payload, params] = args as [unknown, unknown];
  void payload; void params;
  const res = await API.get('/api/v1/getEventsUnreadCount', { params: params as Record<string, string> ?? undefined }); return res.data;
}

export async function getExpenseLedger(...args: unknown[]) {
  const [payload, params] = args as [unknown, unknown];
  void payload; void params;
  const res = await API.get('/api/v1/getExpenseLedger', { params: params as Record<string, string> ?? undefined }); return res.data;
}

export async function getExpiringCredentials(...args: unknown[]) {
  const [payload, params] = args as [unknown, unknown];
  void payload; void params;
  const res = await API.get('/api/v1/getExpiringCredentials', { params: params as Record<string, string> ?? undefined }); return res.data;
}

export async function getExportLatency(...args: unknown[]) {
  const [payload, params] = args as [unknown, unknown];
  void payload; void params;
  const res = await API.get('/api/v1/getExportLatency', { params: params as Record<string, string> ?? undefined }); return res.data;
}

export async function getExportPendingApproval(...args: unknown[]) {
  const [payload, params] = args as [unknown, unknown];
  void payload; void params;
  const res = await API.get('/api/v1/getExportPendingApproval', { params: params as Record<string, string> ?? undefined }); return res.data;
}

export async function getExportPerformanceScore(...args: unknown[]) {
  const [payload, params] = args as [unknown, unknown];
  void payload; void params;
  const res = await API.get('/api/v1/getExportPerformanceScore', { params: params as Record<string, string> ?? undefined }); return res.data;
}

export async function getExportQueue(...args: unknown[]) {
  const [payload, params] = args as [unknown, unknown];
  void payload; void params;
  const res = await API.get('/api/v1/getExportQueue', { params: params as Record<string, string> ?? undefined }); return res.data;
}

export async function getExportRejectionAlerts(...args: unknown[]) {
  const [payload, params] = args as [unknown, unknown];
  void payload; void params;
  const res = await API.get('/api/v1/getExportRejectionAlerts', { params: params as Record<string, string> ?? undefined }); return res.data;
}

export function getFaxDownloadUrl(...args: unknown[]): string {
  // Synchronous URL builder — used directly as href in anchor tags
  const fax_id = args[0] as string;
  return `/api/v1/faxes/${fax_id}/download`;
}

export function getFaxPreviewUrl(...args: unknown[]): string {
  // Synchronous URL builder — used directly as href in anchor tags
  const fax_id = args[0] as string;
  return `/api/v1/faxes/${fax_id}/preview`;
}

export async function getFleetDashboard(...args: unknown[]) {
  const [payload, params] = args as [unknown, unknown];
  void payload; void params;
  const res = await API.get('/api/v1/getFleetDashboard', { params: params as Record<string, string> ?? undefined }); return res.data;
}

export async function getFleetIntelligenceReadiness(...args: unknown[]) {
  const [payload, params] = args as [unknown, unknown];
  void payload; void params;
  const res = await API.get('/api/v1/getFleetIntelligenceReadiness', { params: params as Record<string, string> ?? undefined }); return res.data;
}

export async function getFounderBillingVoiceConfig(...args: unknown[]) {
  const [payload, params] = args as [unknown, unknown];
  void payload; void params;
  const res = await API.get('/api/v1/getFounderBillingVoiceConfig', { params: params as Record<string, string> ?? undefined }); return res.data;
}

export async function getFounderBillingVoiceSummary(...args: unknown[]) {
  const [payload, params] = args as [unknown, unknown];
  void payload; void params;
  const res = await API.get('/api/v1/getFounderBillingVoiceSummary', { params: params as Record<string, string> ?? undefined }); return res.data;
}

export async function getFounderContracts(...args: unknown[]) {
  const [payload, params] = args as [unknown, unknown];
  void payload; void params;
  const res = await API.get('/api/v1/getFounderContracts', { params: params as Record<string, string> ?? undefined }); return res.data;
}

export async function getFounderLegalQueue(...args: unknown[]) {
  const [payload, params] = args as [unknown, unknown];
  void payload; void params;
  const res = await API.get('/api/v1/getFounderLegalQueue', { params: params as Record<string, string> ?? undefined }); return res.data;
}

export async function getFounderLegalRequestDetail(...args: unknown[]) {
  const [payload, params] = args as [unknown, unknown];
  void payload; void params;
  const res = await API.get('/api/v1/getFounderLegalRequestDetail', { params: params as Record<string, string> ?? undefined }); return res.data;
}

export async function getFounderLegalSummary(...args: unknown[]) {
  const [payload, params] = args as [unknown, unknown];
  void payload; void params;
  const res = await API.get('/api/v1/getFounderLegalSummary', { params: params as Record<string, string> ?? undefined }); return res.data;
}

export async function getFounderReports(...args: unknown[]) {
  const [payload, params] = args as [unknown, unknown];
  void payload; void params;
  const res = await API.get('/api/v1/getFounderReports', { params: params as Record<string, string> ?? undefined }); return res.data;
}

export async function getFraudAnomalies(...args: unknown[]) {
  const [payload, params] = args as [unknown, unknown];
  void payload; void params;
  const res = await API.get('/api/v1/getFraudAnomalies', { params: params as Record<string, string> ?? undefined }); return res.data;
}

export async function getGovernanceInteropReadiness(...args: unknown[]) {
  const [payload, params] = args as [unknown, unknown];
  void payload; void params;
  const res = await API.get('/api/v1/getGovernanceInteropReadiness', { params: params as Record<string, string> ?? undefined }); return res.data;
}

export async function getGovernanceSummary(...args: unknown[]) {
  const [payload, params] = args as [unknown, unknown];
  void payload; void params;
  const res = await API.get('/api/v1/getGovernanceSummary', { params: params as Record<string, string> ?? undefined }); return res.data;
}

export async function getGraphDriveFolder(...args: unknown[]) {
  const [payload, params] = args as [unknown, unknown];
  void payload; void params;
  const res = await API.get('/api/v1/getGraphDriveFolder', { params: params as Record<string, string> ?? undefined }); return res.data;
}

export async function getGraphDriveItemDownloadUrl(...args: unknown[]) {
  const [payload, params] = args as [unknown, unknown];
  void payload; void params;
  const res = await API.get('/api/v1/getGraphDriveItemDownloadUrl', { params: params as Record<string, string> ?? undefined }); return res.data;
}

export async function getGraphDriveRoot(...args: unknown[]) {
  const [payload, params] = args as [unknown, unknown];
  void payload; void params;
  const res = await API.get('/api/v1/getGraphDriveRoot', { params: params as Record<string, string> ?? undefined }); return res.data;
}

export async function getGraphMail(...args: unknown[]) {
  const [payload, params] = args as [unknown, unknown];
  void payload; void params;
  const res = await API.get('/api/v1/getGraphMail', { params: params as Record<string, string> ?? undefined }); return res.data;
}

export async function getGraphMailAttachments(...args: unknown[]) {
  const [payload, params] = args as [unknown, unknown];
  void payload; void params;
  const res = await API.get('/api/v1/getGraphMailAttachments', { params: params as Record<string, string> ?? undefined }); return res.data;
}

export async function getGraphMailMessage(...args: unknown[]) {
  const [payload, params] = args as [unknown, unknown];
  void payload; void params;
  const res = await API.get('/api/v1/getGraphMailMessage', { params: params as Record<string, string> ?? undefined }); return res.data;
}

export async function getInvoiceSettings(...args: unknown[]) {
  const [payload, params] = args as [unknown, unknown];
  void payload; void params;
  const res = await API.get('/api/v1/getInvoiceSettings', { params: params as Record<string, string> ?? undefined }); return res.data;
}

export async function getInvoices(...args: unknown[]) {
  const [payload, params] = args as [unknown, unknown];
  void payload; void params;
  const res = await API.get('/api/v1/getInvoices', { params: params as Record<string, string> ?? undefined }); return res.data;
}

export async function getMarginRiskByTenant(...args: unknown[]) {
  const [payload, params] = args as [unknown, unknown];
  void payload; void params;
  const res = await API.get('/api/v1/getMarginRiskByTenant', { params: params as Record<string, string> ?? undefined }); return res.data;
}

export async function getNEMSISCertificationChecklist(...args: unknown[]) {
  const [payload, params] = args as [unknown, unknown];
  void payload; void params;
  const res = await API.get('/api/v1/getNEMSISCertificationChecklist', { params: params as Record<string, string> ?? undefined }); return res.data;
}

export async function getNEMSISPatchTasks(...args: unknown[]) {
  const [payload, params] = args as [unknown, unknown];
  void payload; void params;
  const res = await API.get('/api/v1/getNEMSISPatchTasks', { params: params as Record<string, string> ?? undefined }); return res.data;
}

export async function getNEMSISScenarios(...args: unknown[]) {
  const [payload, params] = args as [unknown, unknown];
  void payload; void params;
  const res = await API.get('/api/v1/getNEMSISScenarios', { params: params as Record<string, string> ?? undefined }); return res.data;
}

export async function getNERISPackDetail(...args: unknown[]) {
  const [payload, params] = args as [unknown, unknown];
  void payload; void params;
  const res = await API.get('/api/v1/getNERISPackDetail', { params: params as Record<string, string> ?? undefined }); return res.data;
}

export async function getOnboardingApplications(...args: unknown[]) {
  const [payload, params] = args as [unknown, unknown];
  void payload; void params;
  const res = await API.get('/api/v1/getOnboardingApplications', { params: params as Record<string, string> ?? undefined }); return res.data;
}

export async function getOnboardingSignEvents(...args: unknown[]) {
  const [payload, params] = args as [unknown, unknown];
  void payload; void params;
  const res = await API.get('/api/v1/getOnboardingSignEvents', { params: params as Record<string, string> ?? undefined }); return res.data;
}

export async function getOpsCommand(...args: unknown[]) {
  const [payload, params] = args as [unknown, unknown];
  void payload; void params;
  const res = await API.get('/api/v1/getOpsCommand', { params: params as Record<string, string> ?? undefined }); return res.data;
}

export async function getOpsDeploymentRunSteps(...args: unknown[]) {
  const [payload, params] = args as [unknown, unknown];
  void payload; void params;
  const res = await API.get('/api/v1/getOpsDeploymentRunSteps', { params: params as Record<string, string> ?? undefined }); return res.data;
}

export async function getOpsDeploymentRuns(...args: unknown[]) {
  const [payload, params] = args as [unknown, unknown];
  void payload; void params;
  const res = await API.get('/api/v1/getOpsDeploymentRuns', { params: params as Record<string, string> ?? undefined }); return res.data;
}

export async function getPatientStatements(...args: unknown[]) {
  const [payload, params] = args as [unknown, unknown];
  void payload; void params;
  const res = await API.get('/api/v1/getPatientStatements', { params: params as Record<string, string> ?? undefined }); return res.data;
}

export async function getPayerPerformance(...args: unknown[]) {
  const [payload, params] = args as [unknown, unknown];
  void payload; void params;
  const res = await API.get('/api/v1/getPayerPerformance', { params: params as Record<string, string> ?? undefined }); return res.data;
}

export async function getPolicyVersions(...args: unknown[]) {
  const [payload, params] = args as [unknown, unknown];
  void payload; void params;
  const res = await API.get('/api/v1/getPolicyVersions', { params: params as Record<string, string> ?? undefined }); return res.data;
}

export async function getPortalActivity(...args: unknown[]) {
  const [payload, params] = args as [unknown, unknown];
  void payload; void params;
  const res = await API.get('/api/v1/getPortalActivity', { params: params as Record<string, string> ?? undefined }); return res.data;
}

export async function getPortalAgencyMetrics(...args: unknown[]) {
  const [payload, params] = args as [unknown, unknown];
  void payload; void params;
  const res = await API.get('/api/v1/getPortalAgencyMetrics', { params: params as Record<string, string> ?? undefined }); return res.data;
}

export async function getPortalBillingSummary(...args: unknown[]) {
  const [payload, params] = args as [unknown, unknown];
  void payload; void params;
  const res = await API.get('/api/v1/getPortalBillingSummary', { params: params as Record<string, string> ?? undefined }); return res.data;
}

export async function getPortalDocuments(...args: unknown[]) {
  const [payload, params] = args as [unknown, unknown];
  void payload; void params;
  const res = await API.get('/api/v1/getPortalDocuments', { params: params as Record<string, string> ?? undefined }); return res.data;
}

export async function getPortalFirePackRules(...args: unknown[]) {
  const [payload, params] = args as [unknown, unknown];
  void payload; void params;
  const res = await API.get('/api/v1/getPortalFirePackRules', { params: params as Record<string, string> ?? undefined }); return res.data;
}

export async function getPortalFleetReadiness(...args: unknown[]) {
  const [payload, params] = args as [unknown, unknown];
  void payload; void params;
  const res = await API.get('/api/v1/getPortalFleetReadiness', { params: params as Record<string, string> ?? undefined }); return res.data;
}

export async function getPortalFleetUnitReadiness(...args: unknown[]) {
  const [payload, params] = args as [unknown, unknown];
  void payload; void params;
  const res = await API.get('/api/v1/getPortalFleetUnitReadiness', { params: params as Record<string, string> ?? undefined }); return res.data;
}

export async function getPortalHemsChecklistTemplate(...args: unknown[]) {
  const [payload, params] = args as [unknown, unknown];
  void payload; void params;
  const res = await API.get('/api/v1/getPortalHemsChecklistTemplate', { params: params as Record<string, string> ?? undefined }); return res.data;
}

export async function getPortalHemsSafetyTimeline(...args: unknown[]) {
  const [payload, params] = args as [unknown, unknown];
  void payload; void params;
  const res = await API.get('/api/v1/getPortalHemsSafetyTimeline', { params: params as Record<string, string> ?? undefined }); return res.data;
}

export async function getPortalMessages(...args: unknown[]) {
  const [payload, params] = args as [unknown, unknown];
  void payload; void params;
  const res = await API.get('/api/v1/getPortalMessages', { params: params as Record<string, string> ?? undefined }); return res.data;
}

export async function getPortalNerisOnboardingStatus(...args: unknown[]) {
  const [payload, params] = args as [unknown, unknown];
  void payload; void params;
  const res = await API.get('/api/v1/getPortalNerisOnboardingStatus', { params: params as Record<string, string> ?? undefined }); return res.data;
}

export async function getPortalNotifications(...args: unknown[]) {
  const [payload, params] = args as [unknown, unknown];
  void payload; void params;
  const res = await API.get('/api/v1/getPortalNotifications', { params: params as Record<string, string> ?? undefined }); return res.data;
}

export async function getPortalPaymentPlans(...args: unknown[]) {
  const [payload, params] = args as [unknown, unknown];
  void payload; void params;
  const res = await API.get('/api/v1/getPortalPaymentPlans', { params: params as Record<string, string> ?? undefined }); return res.data;
}

export async function getPortalPayments(...args: unknown[]) {
  const [payload, params] = args as [unknown, unknown];
  void payload; void params;
  const res = await API.get('/api/v1/getPortalPayments', { params: params as Record<string, string> ?? undefined }); return res.data;
}

export async function getPortalProfile(...args: unknown[]) {
  const [payload, params] = args as [unknown, unknown];
  void payload; void params;
  const res = await API.get('/api/v1/getPortalProfile', { params: params as Record<string, string> ?? undefined }); return res.data;
}

export async function getPortalStatements(...args: unknown[]) {
  const [payload, params] = args as [unknown, unknown];
  void payload; void params;
  const res = await API.get('/api/v1/getPortalStatements', { params: params as Record<string, string> ?? undefined }); return res.data;
}

export async function getPricebookCatalog(...args: unknown[]) {
  const [payload, params] = args as [unknown, unknown];
  void payload; void params;
  const res = await API.get('/api/v1/getPricebookCatalog', { params: params as Record<string, string> ?? undefined }); return res.data;
}

export async function getPublicOnboardingStatus<T = any>(...args: unknown[]): Promise<T> {
  const [payload, params] = args as [unknown, unknown];
  void payload; void params;
  const res = await API.get('/api/v1/getPublicOnboardingStatus', { params: params as Record<string, string> ?? undefined }); return res.data as T;
}

export async function getPublicPricingCatalog<T = any>(...args: unknown[]): Promise<T> {
  const [payload, params] = args as [unknown, unknown];
  void payload; void params;
  const res = await API.get('/api/v1/getPublicPricingCatalog', { params: params as Record<string, string> ?? undefined }); return res.data as T;
}

export async function getReleaseReadiness(...args: unknown[]) {
  const [payload, params] = args as [unknown, unknown];
  void payload; void params;
  const res = await API.get('/api/v1/getReleaseReadiness', { params: params as Record<string, string> ?? undefined }); return res.data;
}

export async function getRevenueLeakage(...args: unknown[]) {
  const [payload, params] = args as [unknown, unknown];
  void payload; void params;
  const res = await API.get('/api/v1/getRevenueLeakage', { params: params as Record<string, string> ?? undefined }); return res.data;
}

export async function getRevenueTrend(...args: unknown[]) {
  const [payload, params] = args as [unknown, unknown];
  void payload; void params;
  const res = await API.get('/api/v1/getRevenueTrend', { params: params as Record<string, string> ?? undefined }); return res.data;
}

export async function getSSLExpiration(...args: unknown[]) {
  const [payload, params] = args as [unknown, unknown];
  void payload; void params;
  const res = await API.get('/api/v1/getSSLExpiration', { params: params as Record<string, string> ?? undefined }); return res.data;
}

export async function getSchedulingAIDrafts(...args: unknown[]) {
  const [payload, params] = args as [unknown, unknown];
  void payload; void params;
  const res = await API.get('/api/v1/getSchedulingAIDrafts', { params: params as Record<string, string> ?? undefined }); return res.data;
}

export async function getSchedulingCoverageDashboard(...args: unknown[]) {
  const [payload, params] = args as [unknown, unknown];
  void payload; void params;
  const res = await API.get('/api/v1/getSchedulingCoverageDashboard', { params: params as Record<string, string> ?? undefined }); return res.data;
}

export async function getSchedulingFatigueReport(...args: unknown[]) {
  const [payload, params] = args as [unknown, unknown];
  void payload; void params;
  const res = await API.get('/api/v1/getSchedulingFatigueReport', { params: params as Record<string, string> ?? undefined }); return res.data;
}

export async function getStaffingAuditLog(...args: unknown[]) {
  const [payload, params] = args as [unknown, unknown];
  void payload; void params;
  const res = await API.get('/api/v1/getStaffingAuditLog', { params: params as Record<string, string> ?? undefined }); return res.data;
}

export async function getStaffingReadiness(...args: unknown[]) {
  const [payload, params] = args as [unknown, unknown];
  void payload; void params;
  const res = await API.get('/api/v1/getStaffingReadiness', { params: params as Record<string, string> ?? undefined }); return res.data;
}

export async function getStripeReconciliation(...args: unknown[]) {
  const [payload, params] = args as [unknown, unknown];
  void payload; void params;
  const res = await API.get('/api/v1/getStripeReconciliation', { params: params as Record<string, string> ?? undefined }); return res.data;
}

export async function getSystemHealthAlerts(...args: unknown[]) {
  const [payload, params] = args as [unknown, unknown];
  void payload; void params;
  const res = await API.get('/api/v1/getSystemHealthAlerts', { params: params as Record<string, string> ?? undefined }); return res.data;
}

export async function getSystemHealthDashboard(...args: unknown[]) {
  const [payload, params] = args as [unknown, unknown];
  void payload; void params;
  const res = await API.get('/api/v1/getSystemHealthDashboard', { params: params as Record<string, string> ?? undefined }); return res.data;
}

export async function getSystemHealthMetricsCPU(...args: unknown[]) {
  const [payload, params] = args as [unknown, unknown];
  void payload; void params;
  const res = await API.get('/api/v1/getSystemHealthMetricsCPU', { params: params as Record<string, string> ?? undefined }); return res.data;
}

export async function getSystemHealthMetricsErrors(...args: unknown[]) {
  const [payload, params] = args as [unknown, unknown];
  void payload; void params;
  const res = await API.get('/api/v1/getSystemHealthMetricsErrors', { params: params as Record<string, string> ?? undefined }); return res.data;
}

export async function getSystemHealthMetricsLatency(...args: unknown[]) {
  const [payload, params] = args as [unknown, unknown];
  void payload; void params;
  const res = await API.get('/api/v1/getSystemHealthMetricsLatency', { params: params as Record<string, string> ?? undefined }); return res.data;
}

export async function getSystemHealthMetricsMemory(...args: unknown[]) {
  const [payload, params] = args as [unknown, unknown];
  void payload; void params;
  const res = await API.get('/api/v1/getSystemHealthMetricsMemory', { params: params as Record<string, string> ?? undefined }); return res.data;
}

export async function getSystemHealthServices(...args: unknown[]) {
  const [payload, params] = args as [unknown, unknown];
  void payload; void params;
  const res = await API.get('/api/v1/getSystemHealthServices', { params: params as Record<string, string> ?? undefined }); return res.data;
}

export async function getTRIPReconciliation(...args: unknown[]) {
  const [payload, params] = args as [unknown, unknown];
  void payload; void params;
  const res = await API.get('/api/v1/getTRIPReconciliation', { params: params as Record<string, string> ?? undefined }); return res.data;
}

export async function getTRIPSettings(...args: unknown[]) {
  const [payload, params] = args as [unknown, unknown];
  void payload; void params;
  const res = await API.get('/api/v1/getTRIPSettings', { params: params as Record<string, string> ?? undefined }); return res.data;
}

export async function getTelnyxCNAMList(...args: unknown[]) {
  const [payload, params] = args as [unknown, unknown];
  void payload; void params;
  const res = await API.get('/api/v1/getTelnyxCNAMList', { params: params as Record<string, string> ?? undefined }); return res.data;
}

export async function getTemplateVersions(...args: unknown[]) {
  const [payload, params] = args as [unknown, unknown];
  void payload; void params;
  const res = await API.get('/api/v1/getTemplateVersions', { params: params as Record<string, string> ?? undefined }); return res.data;
}

export async function getTenantBillingRanking(...args: unknown[]) {
  const [payload, params] = args as [unknown, unknown];
  void payload; void params;
  const res = await API.get('/api/v1/getTenantBillingRanking', { params: params as Record<string, string> ?? undefined }); return res.data;
}

export async function getTenantNERISOnboardingStatus(...args: unknown[]) {
  const [payload, params] = args as [unknown, unknown];
  void payload; void params;
  const res = await API.get('/api/v1/getTenantNERISOnboardingStatus', { params: params as Record<string, string> ?? undefined }); return res.data;
}

export async function getUptimeSLA(...args: unknown[]) {
  const [payload, params] = args as [unknown, unknown];
  void payload; void params;
  const res = await API.get('/api/v1/getUptimeSLA', { params: params as Record<string, string> ?? undefined }); return res.data;
}

export async function getVisibilityDashboardBundle(...args: unknown[]) {
  const [payload, params] = args as [unknown, unknown];
  void payload; void params;
  const res = await API.get('/api/v1/getVisibilityDashboardBundle', { params: params as Record<string, string> ?? undefined }); return res.data;
}

export async function getVoiceAdvancedAbTests(...args: unknown[]) {
  const [payload, params] = args as [unknown, unknown];
  void payload; void params;
  const res = await API.get('/api/v1/getVoiceAdvancedAbTests', { params: params as Record<string, string> ?? undefined }); return res.data;
}

export async function getVoiceAdvancedCallbackSlots(...args: unknown[]) {
  const [payload, params] = args as [unknown, unknown];
  void payload; void params;
  const res = await API.get('/api/v1/getVoiceAdvancedCallbackSlots', { params: params as Record<string, string> ?? undefined }); return res.data;
}

export async function getVoiceAdvancedDashboard(...args: unknown[]) {
  const [payload, params] = args as [unknown, unknown];
  void payload; void params;
  const res = await API.get('/api/v1/getVoiceAdvancedDashboard', { params: params as Record<string, string> ?? undefined }); return res.data;
}

export async function getVoiceAdvancedImprovementTickets(...args: unknown[]) {
  const [payload, params] = args as [unknown, unknown];
  void payload; void params;
  const res = await API.get('/api/v1/getVoiceAdvancedImprovementTickets', { params: params as Record<string, string> ?? undefined }); return res.data;
}

export async function getVoiceAdvancedReviewQueue(...args: unknown[]) {
  const [payload, params] = args as [unknown, unknown];
  void payload; void params;
  const res = await API.get('/api/v1/getVoiceAdvancedReviewQueue', { params: params as Record<string, string> ?? undefined }); return res.data;
}

export async function importNERISPack(...args: unknown[]) {
  const [payload, params] = args as [unknown, unknown];
  void payload; void params;
  const res = await API.post('/api/v1/importNERISPack', payload); return res.data;
}

export async function ingestTelemetry(...args: unknown[]) {
  const [payload, params] = args as [unknown, unknown];
  void payload; void params;
  const res = await API.post('/api/v1/ingestTelemetry', payload); return res.data;
}

export async function injectDispatchRequest(...args: unknown[]) {
  const [payload, params] = args as [unknown, unknown];
  void payload; void params;
  const res = await API.post('/api/v1/injectDispatchRequest', payload); return res.data;
}

export async function injectDispatchRequestPortal(...args: unknown[]) {
  const [payload, params] = args as [unknown, unknown];
  void payload; void params;
  const res = await API.post('/api/v1/injectDispatchRequestPortal', payload); return res.data;
}

export async function listDispatchRequestsPortal(...args: unknown[]) {
  const [payload, params] = args as [unknown, unknown];
  void payload; void params;
  const res = await API.get('/api/v1/listDispatchRequestsPortal', { params: params as Record<string, string> ?? undefined }); return res.data;
}

export async function listEPCRCharts(...args: unknown[]) {
  const [payload, params] = args as [unknown, unknown];
  void payload; void params;
  const res = await API.get('/api/v1/listEPCRCharts', { params: params as Record<string, string> ?? undefined }); return res.data;
}

export async function listFaxEvents(...args: unknown[]) {
  const [payload, params] = args as [unknown, unknown];
  void payload; void params;
  const res = await API.get('/api/v1/listFaxEvents', { params: params as Record<string, string> ?? undefined }); return res.data;
}

export async function listFaxInbox(...args: unknown[]) {
  const [payload, params] = args as [unknown, unknown];
  void payload; void params;
  const res = await API.get('/api/v1/listFaxInbox', { params: params as Record<string, string> ?? undefined }); return res.data;
}

export async function listFounderBillingVoiceCallbacks(...args: unknown[]) {
  const [payload, params] = args as [unknown, unknown];
  void payload; void params;
  const res = await API.get('/api/v1/listFounderBillingVoiceCallbacks', { params: params as Record<string, string> ?? undefined }); return res.data;
}

export async function listFounderBillingVoiceEscalations(...args: unknown[]) {
  const [payload, params] = args as [unknown, unknown];
  void payload; void params;
  const res = await API.get('/api/v1/listFounderBillingVoiceEscalations', { params: params as Record<string, string> ?? undefined }); return res.data;
}

export async function listFounderBillingVoiceVoicemails(...args: unknown[]) {
  const [payload, params] = args as [unknown, unknown];
  void payload; void params;
  const res = await API.get('/api/v1/listFounderBillingVoiceVoicemails', { params: params as Record<string, string> ?? undefined }); return res.data;
}

export async function listNERISPacksAll(...args: unknown[]) {
  const [payload, params] = args as [unknown, unknown];
  void payload; void params;
  const res = await API.get('/api/v1/listNERISPacksAll', { params: params as Record<string, string> ?? undefined }); return res.data;
}

export async function listPatientPortalStatementsForInvoiceLookup(...args: unknown[]) {
  const [payload, params] = args as [unknown, unknown];
  void payload; void params;
  const res = await API.get('/api/v1/listPatientPortalStatementsForInvoiceLookup', { params: params as Record<string, string> ?? undefined }); return res.data;
}

export async function listPolicies(...args: unknown[]) {
  const [payload, params] = args as [unknown, unknown];
  void payload; void params;
  const res = await API.get('/api/v1/listPolicies', { params: params as Record<string, string> ?? undefined }); return res.data;
}

export async function listPortalCases(...args: unknown[]) {
  const [payload, params] = args as [unknown, unknown];
  void payload; void params;
  const res = await API.get('/api/v1/listPortalCases', { params: params as Record<string, string> ?? undefined }); return res.data;
}

export async function listPortalEDIBatches(...args: unknown[]) {
  const [payload, params] = args as [unknown, unknown];
  void payload; void params;
  const res = await API.get('/api/v1/listPortalEDIBatches', { params: params as Record<string, string> ?? undefined }); return res.data;
}

export async function listPortalFireDepartmentApparatus(...args: unknown[]) {
  const [payload, params] = args as [unknown, unknown];
  void payload; void params;
  const res = await API.get('/api/v1/listPortalFireDepartmentApparatus', { params: params as Record<string, string> ?? undefined }); return res.data;
}

export async function listPortalFireIncidents(...args: unknown[]) {
  const [payload, params] = args as [unknown, unknown];
  void payload; void params;
  const res = await API.get('/api/v1/listPortalFireIncidents', { params: params as Record<string, string> ?? undefined }); return res.data;
}

export async function listPortalFleetAlerts(...args: unknown[]) {
  const [payload, params] = args as [unknown, unknown];
  void payload; void params;
  const res = await API.get('/api/v1/listPortalFleetAlerts', { params: params as Record<string, string> ?? undefined }); return res.data;
}

export async function listPortalFleetInspectionTemplates(...args: unknown[]) {
  const [payload, params] = args as [unknown, unknown];
  void payload; void params;
  const res = await API.get('/api/v1/listPortalFleetInspectionTemplates', { params: params as Record<string, string> ?? undefined }); return res.data;
}

export async function listPortalFleetWorkOrders(...args: unknown[]) {
  const [payload, params] = args as [unknown, unknown];
  void payload; void params;
  const res = await API.get('/api/v1/listPortalFleetWorkOrders', { params: params as Record<string, string> ?? undefined }); return res.data;
}

export async function listPortalSupportThreadMessages(...args: unknown[]) {
  const [payload, params] = args as [unknown, unknown];
  void payload; void params;
  const res = await API.get('/api/v1/listPortalSupportThreadMessages', { params: params as Record<string, string> ?? undefined }); return res.data;
}

export async function listPortalSupportThreads(...args: unknown[]) {
  const [payload, params] = args as [unknown, unknown];
  void payload; void params;
  const res = await API.get('/api/v1/listPortalSupportThreads', { params: params as Record<string, string> ?? undefined }); return res.data;
}

export async function listPricebookEntries(...args: unknown[]) {
  const [payload, params] = args as [unknown, unknown];
  void payload; void params;
  const res = await API.get('/api/v1/listPricebookEntries', { params: params as Record<string, string> ?? undefined }); return res.data;
}

export async function listPricebooks(...args: unknown[]) {
  const [payload, params] = args as [unknown, unknown];
  void payload; void params;
  const res = await API.get('/api/v1/listPricebooks', { params: params as Record<string, string> ?? undefined }); return res.data;
}

export async function listPublicSystems<T = any>(...args: unknown[]): Promise<T> {
  const [payload, params] = args as [unknown, unknown];
  void payload; void params;
  const res = await API.get('/api/v1/listPublicSystems', { params: params as Record<string, string> ?? undefined }); return res.data as T;
}

export async function listRoleAssignments(...args: unknown[]) {
  const [payload, params] = args as [unknown, unknown];
  void payload; void params;
  const res = await API.get('/api/v1/listRoleAssignments', { params: params as Record<string, string> ?? undefined }); return res.data;
}

export async function listRoles(...args: unknown[]) {
  const [payload, params] = args as [unknown, unknown];
  void payload; void params;
  const res = await API.get('/api/v1/listRoles', { params: params as Record<string, string> ?? undefined }); return res.data;
}

export async function listSchedulingSwaps(...args: unknown[]) {
  const [payload, params] = args as [unknown, unknown];
  void payload; void params;
  const res = await API.get('/api/v1/listSchedulingSwaps', { params: params as Record<string, string> ?? undefined }); return res.data;
}

export async function listSupportInboxThreads(...args: unknown[]) {
  const [payload, params] = args as [unknown, unknown];
  void payload; void params;
  const res = await API.get('/api/v1/listSupportInboxThreads', { params: params as Record<string, string> ?? undefined }); return res.data;
}

export async function listSupportThreadMessages(...args: unknown[]) {
  const [payload, params] = args as [unknown, unknown];
  void payload; void params;
  const res = await API.get('/api/v1/listSupportThreadMessages', { params: params as Record<string, string> ?? undefined }); return res.data;
}

export async function listTRIPDebts(...args: unknown[]) {
  const [payload, params] = args as [unknown, unknown];
  void payload; void params;
  const res = await API.get('/api/v1/listTRIPDebts', { params: params as Record<string, string> ?? undefined }); return res.data;
}

export async function listTRIPExports(...args: unknown[]) {
  const [payload, params] = args as [unknown, unknown];
  void payload; void params;
  const res = await API.get('/api/v1/listTRIPExports', { params: params as Record<string, string> ?? undefined }); return res.data;
}

export async function listTemplates(...args: unknown[]) {
  const [payload, params] = args as [unknown, unknown];
  void payload; void params;
  const res = await API.get('/api/v1/listTemplates', { params: params as Record<string, string> ?? undefined }); return res.data;
}

export async function listTransportLinkFacilitySchedule(...args: unknown[]) {
  const [payload, params] = args as [unknown, unknown];
  void payload; void params;
  const res = await API.get('/api/v1/listTransportLinkFacilitySchedule', { params: params as Record<string, string> ?? undefined }); return res.data;
}

export async function lookupPublicOnboardingNpi<T = any>(...args: unknown[]): Promise<T> {
  const [payload, params] = args as [unknown, unknown];
  void payload; void params;
  const res = await API.get('/api/v1/lookupPublicOnboardingNpi', { params: params as Record<string, string> ?? undefined }); return res.data as T;
}

export async function manualProvisionApplication(...args: unknown[]) {
  const [payload, params] = args as [unknown, unknown];
  void payload; void params;
  const res = await API.post('/api/v1/manualProvisionApplication', payload); return res.data;
}

export async function markEventRead(...args: unknown[]) {
  const [payload, params] = args as [unknown, unknown];
  void payload; void params;
  const res = await API.post('/api/v1/markEventRead', payload); return res.data;
}

export async function markInvoicePaid(...args: unknown[]) {
  const [payload, params] = args as [unknown, unknown];
  void payload; void params;
  const res = await API.post('/api/v1/markInvoicePaid', payload); return res.data;
}

export async function markPortalNotificationRead(...args: unknown[]) {
  const [payload, params] = args as [unknown, unknown];
  void payload; void params;
  const res = await API.post('/api/v1/markPortalNotificationRead', payload); return res.data;
}

export async function markPortalNotificationsRead(...args: unknown[]) {
  const [payload, params] = args as [unknown, unknown];
  void payload; void params;
  const res = await API.post('/api/v1/markPortalNotificationsRead', payload); return res.data;
}

export async function mergeCopilotRun(...args: unknown[]) {
  const [payload, params] = args as [unknown, unknown];
  void payload; void params;
  const res = await API.post('/api/v1/mergeCopilotRun', payload); return res.data;
}

export async function nemsisCopilotExplain(...args: unknown[]) {
  const [payload, params] = args as [unknown, unknown];
  void payload; void params;
  const res = await API.post('/api/v1/nemsisCopilotExplain', payload); return res.data;
}

export async function nemsisStudioAiExplain(...args: unknown[]) {
  const [payload, params] = args as [unknown, unknown];
  void payload; void params;
  const res = await API.post('/api/v1/nemsisStudioAiExplain', payload); return res.data;
}

export async function nerisCopilotExplain(...args: unknown[]) {
  const [payload, params] = args as [unknown, unknown];
  void payload; void params;
  const res = await API.post('/api/v1/nerisCopilotExplain', payload); return res.data;
}

export async function payStatement(...args: unknown[]) {
  const [payload, params] = args as [unknown, unknown];
  void payload; void params;
  const res = await API.post('/api/v1/payStatement', payload); return res.data;
}

export async function postPortalHemsMissionAction(...args: unknown[]) {
  const [payload, params] = args as [unknown, unknown];
  void payload; void params;
  const res = await API.post('/api/v1/postPortalHemsMissionAction', payload); return res.data;
}

export async function previewLegalPricingQuote(...args: unknown[]) {
  const [payload, params] = args as [unknown, unknown];
  void payload; void params;
  const res = await API.get('/api/v1/previewLegalPricingQuote', { params: params as Record<string, string> ?? undefined }); return res.data;
}

export async function previewVisibilityRedaction<T = any>(...args: unknown[]): Promise<T> {
  const [payload, params] = args as [unknown, unknown];
  void payload; void params;
  const res = await API.get('/api/v1/previewVisibilityRedaction', { params: params as Record<string, string> ?? undefined }); return res.data as T;
}

export async function processDocument(...args: unknown[]) {
  const [payload, params] = args as [unknown, unknown];
  void payload; void params;
  const res = await API.post('/api/v1/processDocument', payload); return res.data;
}

export async function proposeCopilotRun(...args: unknown[]) {
  const [payload, params] = args as [unknown, unknown];
  void payload; void params;
  const res = await API.post('/api/v1/proposeCopilotRun', payload); return res.data;
}

export async function pushCrewPage(...args: unknown[]) {
  const [payload, params] = args as [unknown, unknown];
  void payload; void params;
  const res = await API.post('/api/v1/pushCrewPage', payload); return res.data;
}

export async function registerAuthRep(...args: unknown[]) {
  const [payload, params] = args as [unknown, unknown];
  void payload; void params;
  const res = await API.post('/api/v1/registerAuthRep', payload); return res.data;
}

export async function registerTelnyxCNAM(...args: unknown[]) {
  const [payload, params] = args as [unknown, unknown];
  void payload; void params;
  const res = await API.post('/api/v1/registerTelnyxCNAM', payload); return res.data;
}

export async function renderFounderBillingVoicePrompts(...args: unknown[]) {
  const [payload, params] = args as [unknown, unknown];
  void payload; void params;
  const res = await API.get('/api/v1/renderFounderBillingVoicePrompts', { params: params as Record<string, string> ?? undefined }); return res.data;
}

export async function replyGraphMail(...args: unknown[]) {
  const [payload, params] = args as [unknown, unknown];
  void payload; void params;
  const res = await API.post('/api/v1/replyGraphMail', payload); return res.data;
}

export async function requestPolicyApproval(...args: unknown[]) {
  const [payload, params] = args as [unknown, unknown];
  void payload; void params;
  const res = await API.post('/api/v1/requestPolicyApproval', payload); return res.data;
}

export async function requestPortalPaymentPlan(...args: unknown[]) {
  const [payload, params] = args as [unknown, unknown];
  void payload; void params;
  const res = await API.post('/api/v1/requestPortalPaymentPlan', payload); return res.data;
}

export async function requestSchedulingAIDraft(...args: unknown[]) {
  const [payload, params] = args as [unknown, unknown];
  void payload; void params;
  const res = await API.post('/api/v1/requestSchedulingAIDraft', payload); return res.data;
}

export async function resendOnboardingCheckout(...args: unknown[]) {
  const [payload, params] = args as [unknown, unknown];
  void payload; void params;
  const res = await API.post('/api/v1/resendOnboardingCheckout', payload); return res.data;
}

export async function resendOnboardingLegal(...args: unknown[]) {
  const [payload, params] = args as [unknown, unknown];
  void payload; void params;
  const res = await API.post('/api/v1/resendOnboardingLegal', payload); return res.data;
}

export async function resolvePortalFleetAlert(...args: unknown[]) {
  const [payload, params] = args as [unknown, unknown];
  void payload; void params;
  const res = await API.post('/api/v1/resolvePortalFleetAlert', payload); return res.data;
}

export async function resolveSupportInboxThread(...args: unknown[]) {
  const [payload, params] = args as [unknown, unknown];
  void payload; void params;
  const res = await API.post('/api/v1/resolveSupportInboxThread', payload); return res.data;
}

export async function retryExportJob(...args: unknown[]) {
  const [payload, params] = args as [unknown, unknown];
  void payload; void params;
  const res = await API.post('/api/v1/retryExportJob', payload); return res.data;
}

export async function reviewFounderLegalRequest(...args: unknown[]) {
  const [payload, params] = args as [unknown, unknown];
  void payload; void params;
  const res = await API.post('/api/v1/reviewFounderLegalRequest', payload); return res.data;
}

export async function revokeOnboardingApplication(...args: unknown[]) {
  const [payload, params] = args as [unknown, unknown];
  void payload; void params;
  const res = await API.delete('/api/v1/revokeOnboardingApplication', { data: payload }); return res.data;
}

export async function rollbackPolicy(...args: unknown[]) {
  const [payload, params] = args as [unknown, unknown];
  void payload; void params;
  const res = await API.post('/api/v1/rollbackPolicy', payload); return res.data;
}

export async function runDEANarcoticsAudit(...args: unknown[]) {
  const [payload, params] = args as [unknown, unknown];
  void payload; void params;
  const res = await API.post('/api/v1/runDEANarcoticsAudit', payload); return res.data;
}

export async function runNEMSISScenario(...args: unknown[]) {
  const [payload, params] = args as [unknown, unknown];
  void payload; void params;
  const res = await API.post('/api/v1/runNEMSISScenario', payload); return res.data;
}

export async function sandboxTestVisibilityRule<T = any>(...args: unknown[]): Promise<T> {
  const [payload, params] = args as [unknown, unknown];
  void payload; void params;
  const res = await API.post('/api/v1/sandboxTestVisibilityRule', payload); return res.data as T;
}

export async function saveTRIPSettings(...args: unknown[]) {
  const [payload, params] = args as [unknown, unknown];
  void payload; void params;
  const res = await API.patch('/api/v1/saveTRIPSettings', payload); return res.data;
}

export async function searchAuditLogs(...args: unknown[]) {
  const [payload, params] = args as [unknown, unknown];
  void payload; void params;
  const res = await API.get('/api/v1/searchAuditLogs', { params: params as Record<string, string> ?? undefined }); return res.data;
}

export async function sendAgentCommand(...args: unknown[]) {
  const [payload, params] = args as [unknown, unknown];
  void payload; void params;
  const res = await API.post('/api/v1/sendAgentCommand', payload); return res.data;
}

export async function sendCopilotMessage(...args: unknown[]) {
  const [payload, params] = args as [unknown, unknown];
  void payload; void params;
  const res = await API.post('/api/v1/sendCopilotMessage', payload); return res.data;
}

export async function sendFounderCopilotCommand(...args: unknown[]) {
  const [payload, params] = args as [unknown, unknown];
  void payload; void params;
  const res = await API.post('/api/v1/sendFounderCopilotCommand', payload); return res.data;
}

export async function sendGraphMail(...args: unknown[]) {
  const [payload, params] = args as [unknown, unknown];
  void payload; void params;
  const res = await API.post('/api/v1/sendGraphMail', payload); return res.data;
}

export async function sendInvoiceReminder(...args: unknown[]) {
  const [payload, params] = args as [unknown, unknown];
  void payload; void params;
  const res = await API.post('/api/v1/sendInvoiceReminder', payload); return res.data;
}

export async function sendPatientPortalBillingChatMessage(...args: unknown[]) {
  const [payload, params] = args as [unknown, unknown];
  void payload; void params;
  const res = await API.post('/api/v1/sendPatientPortalBillingChatMessage', payload); return res.data;
}

export async function sendPortalMessage(...args: unknown[]) {
  const [payload, params] = args as [unknown, unknown];
  void payload; void params;
  const res = await API.post('/api/v1/sendPortalMessage', payload); return res.data;
}

export async function sendSupportInboxReply(...args: unknown[]) {
  const [payload, params] = args as [unknown, unknown];
  void payload; void params;
  const res = await API.post('/api/v1/sendSupportInboxReply', payload); return res.data;
}

export async function setPortalHemsAircraftReadiness(...args: unknown[]) {
  const [payload, params] = args as [unknown, unknown];
  void payload; void params;
  const res = await API.patch('/api/v1/setPortalHemsAircraftReadiness', payload); return res.data;
}

export async function setVisibilityKillSwitch(...args: unknown[]) {
  const [payload, params] = args as [unknown, unknown];
  void payload; void params;
  const res = await API.patch('/api/v1/setVisibilityKillSwitch', payload); return res.data;
}

export async function signAuthRep(...args: unknown[]) {
  const [payload, params] = args as [unknown, unknown];
  void payload; void params;
  const res = await API.post('/api/v1/signAuthRep', payload); return res.data;
}

export async function signPublicOnboardingLegalPacket(...args: unknown[]) {
  const [payload, params] = args as [unknown, unknown];
  void payload; void params;
  const res = await API.post('/api/v1/signPublicOnboardingLegalPacket', payload); return res.data;
}

export async function simulateVisibilityRole<T = any>(...args: unknown[]): Promise<T> {
  const [payload, params] = args as [unknown, unknown];
  void payload; void params;
  const res = await API.get('/api/v1/simulateVisibilityRole', { params: params as Record<string, string> ?? undefined }); return res.data as T;
}

export async function simulateWisconsinNEMSIS(...args: unknown[]) {
  const [payload, params] = args as [unknown, unknown];
  void payload; void params;
  const res = await API.get('/api/v1/simulateWisconsinNEMSIS', { params: params as Record<string, string> ?? undefined }); return res.data;
}

export async function startPublicOnboardingCheckout<T = any>(...args: unknown[]): Promise<T> {
  const [payload, params] = args as [unknown, unknown];
  void payload; void params;
  const res = await API.post('/api/v1/startPublicOnboardingCheckout', payload); return res.data as T;
}

export async function startTenantNERISOnboarding(...args: unknown[]) {
  const [payload, params] = args as [unknown, unknown];
  void payload; void params;
  const res = await API.post('/api/v1/startTenantNERISOnboarding', payload); return res.data;
}

export async function submitEligibilityInquiry(...args: unknown[]) {
  const [payload, params] = args as [unknown, unknown];
  void payload; void params;
  const res = await API.post('/api/v1/submitEligibilityInquiry', payload); return res.data;
}

export async function submitPatientPortalSupportRequest(...args: unknown[]) {
  const [payload, params] = args as [unknown, unknown];
  void payload; void params;
  const res = await API.post('/api/v1/submitPatientPortalSupportRequest', payload); return res.data;
}

export async function submitPortalHemsMissionAcceptance(...args: unknown[]) {
  const [payload, params] = args as [unknown, unknown];
  void payload; void params;
  const res = await API.post('/api/v1/submitPortalHemsMissionAcceptance', payload); return res.data;
}

export async function submitPortalHemsWeatherBrief(...args: unknown[]) {
  const [payload, params] = args as [unknown, unknown];
  void payload; void params;
  const res = await API.post('/api/v1/submitPortalHemsWeatherBrief', payload); return res.data;
}

export async function submitPortalSupportRequest(...args: unknown[]) {
  const [payload, params] = args as [unknown, unknown];
  void payload; void params;
  const res = await API.post('/api/v1/submitPortalSupportRequest', payload); return res.data;
}

export async function submitPublicOnboardingApplication<T = any>(...args: unknown[]): Promise<T> {
  const [payload, params] = args as [unknown, unknown];
  void payload; void params;
  const res = await API.post('/api/v1/submitPublicOnboardingApplication', payload); return res.data as T;
}

export async function summarizeSupportInboxThread(...args: unknown[]) {
  const [payload, params] = args as [unknown, unknown];
  void payload; void params;
  const res = await API.post('/api/v1/summarizeSupportInboxThread', payload); return res.data;
}

export async function takeoverFounderBillingVoiceEscalation(...args: unknown[]) {
  const [payload, params] = args as [unknown, unknown];
  void payload; void params;
  const res = await API.post('/api/v1/takeoverFounderBillingVoiceEscalation', payload); return res.data;
}

export async function transitionDispatchMission(...args: unknown[]) {
  const [payload, params] = args as [unknown, unknown];
  void payload; void params;
  const res = await API.post('/api/v1/transitionDispatchMission', payload); return res.data;
}

export async function triggerFaxMatch(...args: unknown[]) {
  const [payload, params] = args as [unknown, unknown];
  void payload; void params;
  const res = await API.post('/api/v1/triggerFaxMatch', payload); return res.data;
}

export async function updateCrewAvailability(...args: unknown[]) {
  const [payload, params] = args as [unknown, unknown];
  void payload; void params;
  const res = await API.patch('/api/v1/updateCrewAvailability', payload); return res.data;
}

export async function updateFounderBillingVoiceConfig(...args: unknown[]) {
  const [payload, params] = args as [unknown, unknown];
  void payload; void params;
  const res = await API.patch('/api/v1/updateFounderBillingVoiceConfig', payload); return res.data;
}

export async function updateInvoiceSettings(...args: unknown[]) {
  const [payload, params] = args as [unknown, unknown];
  void payload; void params;
  const res = await API.patch('/api/v1/updateInvoiceSettings', payload); return res.data;
}

export async function updateMyCrewAvailability(...args: unknown[]) {
  const [payload, params] = args as [unknown, unknown];
  void payload; void params;
  const res = await API.patch('/api/v1/updateMyCrewAvailability', payload); return res.data;
}

export async function updateNEMSISPatchTask(...args: unknown[]) {
  const [payload, params] = args as [unknown, unknown];
  void payload; void params;
  const res = await API.patch('/api/v1/updateNEMSISPatchTask', payload); return res.data;
}

export async function updatePolicy(...args: unknown[]) {
  const [payload, params] = args as [unknown, unknown];
  void payload; void params;
  const res = await API.patch('/api/v1/updatePolicy', payload); return res.data;
}

export async function updatePortalCaseStatus(...args: unknown[]) {
  const [payload, params] = args as [unknown, unknown];
  void payload; void params;
  const res = await API.patch('/api/v1/updatePortalCaseStatus', payload); return res.data;
}

export async function updatePortalFireIncident(...args: unknown[]) {
  const [payload, params] = args as [unknown, unknown];
  void payload; void params;
  const res = await API.patch('/api/v1/updatePortalFireIncident', payload); return res.data;
}

export async function updatePortalFleetWorkOrder(...args: unknown[]) {
  const [payload, params] = args as [unknown, unknown];
  void payload; void params;
  const res = await API.patch('/api/v1/updatePortalFleetWorkOrder', payload); return res.data;
}

export async function updatePortalProfile(...args: unknown[]) {
  const [payload, params] = args as [unknown, unknown];
  void payload; void params;
  const res = await API.patch('/api/v1/updatePortalProfile', payload); return res.data;
}

export async function uploadAuthRepDocument(...args: unknown[]) {
  const [payload, params] = args as [unknown, unknown];
  void payload; void params;
  const res = await API.post('/api/v1/uploadAuthRepDocument', payload); return res.data;
}

export async function uploadLegalDocumentToPresignedUrl(...args: unknown[]) {
  const [payload, params] = args as [unknown, unknown];
  void payload; void params;
  const res = await API.post('/api/v1/uploadLegalDocumentToPresignedUrl', payload); return res.data;
}

export async function uploadNEMSISPackFile(...args: unknown[]) {
  const [payload, params] = args as [unknown, unknown];
  void payload; void params;
  const res = await API.post('/api/v1/uploadNEMSISPackFile', payload); return res.data;
}

export async function uploadNEMSISScenario(...args: unknown[]) {
  const [payload, params] = args as [unknown, unknown];
  void payload; void params;
  const res = await API.post('/api/v1/uploadNEMSISScenario', payload); return res.data;
}

export async function uploadPortalDocument(...args: unknown[]) {
  const [payload, params] = args as [unknown, unknown];
  void payload; void params;
  const res = await API.post('/api/v1/uploadPortalDocument', payload); return res.data;
}

export async function validateDispatchRequestPortal(...args: unknown[]) {
  const [payload, params] = args as [unknown, unknown];
  void payload; void params;
  const res = await API.get('/api/v1/validateDispatchRequestPortal', { params: params as Record<string, string> ?? undefined }); return res.data;
}

export async function validateFireValidationIncident(...args: unknown[]) {
  const [payload, params] = args as [unknown, unknown];
  void payload; void params;
  const res = await API.get('/api/v1/validateFireValidationIncident', { params: params as Record<string, string> ?? undefined }); return res.data;
}

export async function validateNEMSISRawXml(...args: unknown[]) {
  const [payload, params] = args as [unknown, unknown];
  void payload; void params;
  const res = await API.get('/api/v1/validateNEMSISRawXml', { params: params as Record<string, string> ?? undefined }); return res.data;
}

export async function validateNEMSISStudioFile(...args: unknown[]) {
  const [payload, params] = args as [unknown, unknown];
  void payload; void params;
  const res = await API.get('/api/v1/validateNEMSISStudioFile', { params: params as Record<string, string> ?? undefined }); return res.data;
}

export async function validateNERISBundle(...args: unknown[]) {
  const [payload, params] = args as [unknown, unknown];
  void payload; void params;
  const res = await API.get('/api/v1/validateNERISBundle', { params: params as Record<string, string> ?? undefined }); return res.data;
}

export async function validatePortalFireIncident(...args: unknown[]) {
  const [payload, params] = args as [unknown, unknown];
  void payload; void params;
  const res = await API.get('/api/v1/validatePortalFireIncident', { params: params as Record<string, string> ?? undefined }); return res.data;
}

export async function verifyAuthRepOtp(...args: unknown[]) {
  const [payload, params] = args as [unknown, unknown];
  void payload; void params;
  const res = await API.post('/api/v1/verifyAuthRepOtp', payload); return res.data;
}

export async function verifyDEAEvidenceBundleHash(...args: unknown[]) {
  const [payload, params] = args as [unknown, unknown];
  void payload; void params;
  const res = await API.post('/api/v1/verifyDEAEvidenceBundleHash', payload); return res.data;
}

export async function ingestPortalEDI277(...args: unknown[]) {
  const [payload, params] = args as [unknown, unknown];
  void params;
  const res = await API.post('/api/v1/billing/edi/277/ingest', payload); return res.data;
}

export async function ingestPortalEDI835(...args: unknown[]) {
  const [payload, params] = args as [unknown, unknown];
  void params;
  const res = await API.post('/api/v1/billing/edi/835/ingest', payload); return res.data;
}

export async function ingestPortalEDI999(...args: unknown[]) {
  const [payload, params] = args as [unknown, unknown];
  void params;
  const res = await API.post('/api/v1/billing/edi/999/ingest', payload); return res.data;
}

export interface EdiBatchApi {
  id: string;
  batch_type: string;
  created_at: string;
  file_name?: string;
  record_count?: number;
  [key: string]: unknown;
}

export interface EdiClaimExplanationApi {
  claim_id: string;
  explanation: string;
  adjustment_codes?: { code: string; description: string }[];
  [key: string]: unknown;
}

// ─── Missing API type exports ─────────────────────────────────────────────────

export interface FaxItemApi {
  id: string;
  from_number?: string;
  to_number?: string;
  status?: string;
  direction?: string;
  received_at?: string;
  created_at?: string;
  pages?: number;
  pdf_url?: string;
  page_count?: number;
  telnyx_fax_id?: string;
  error?: string;
  status_updated_at?: string;
  document_match_status?: string;
  data?: {
    confidence?: number;
    telnyx_fax_id?: string;
    error?: string;
    claim_id?: string;
    patient_name?: string;
    match_type?: string;
    match_suggestions?: { claim_id?: string; patient_name?: string; match_type?: string; confidence?: number }[];
    [key: string]: unknown;
  };
  [key: string]: unknown;
}

export interface FaxEventApi {
  id: string;
  event_type?: string;
  fax_id?: string;
  created_at?: string;
  received_at?: string;
  to_status?: string;
  status?: string;
  provider_event_type?: string;
  [key: string]: unknown;
}

export interface SupportThreadApi {
  id: string;
  subject?: string;
  status?: string;
  escalated?: boolean;
  unread?: boolean;
  updated_at?: string;
  created_at?: string;
  tenant_id?: string;
  agency_name?: string;
  data?: {
    context?: { agency_name?: string;[key: string]: unknown };
    title?: string;
    last_message?: string;
    [key: string]: unknown;
  };
  [key: string]: unknown;
}

export interface SupportThreadMessageApi {
  id: string;
  content?: string;
  sender_role?: string;
  created_at?: string;
  thread_id?: string;
  [key: string]: unknown;
}

export interface LegalQueueItem {
  id: string;
  request_type?: string;
  severity?: string;
  status?: string;
  created_at?: string;
  agency_name?: string;
  subject?: string;
  requester_name?: string;
  requesting_party?: string;
  missing_count?: number;
  deadline_risk?: string;
  deadline_at?: string;
  [key: string]: unknown;
}

export interface LegalSummary {
  total?: number;
  pending?: number;
  resolved?: number;
  avg_response_hours?: number;
  total_open?: number;
  urgent_deadlines?: number;
  high_risk_requests?: number;
  lane_counts?: Record<string, number>;
  [key: string]: unknown;
}

export interface LegalChecklistItem {
  id: string;
  label: string;
  code?: string;
  completed?: boolean;
  required?: boolean;
  [key: string]: unknown;
}

export interface LegalIntakePayload {
  request_type: string;
  requesting_party?: string;
  requester_name?: string;
  requesting_entity?: string;
  requester_category?: string;
  patient_first_name?: string;
  patient_last_name?: string;
  patient_dob?: string;
  mrn?: string;
  csn?: string;
  date_range_start?: string;
  date_range_end?: string;
  request_documents?: string[];
  requested_page_count?: number;
  jurisdiction_state?: string;
  print_mail_requested?: boolean;
  rush_requested?: boolean;
  delivery_preference?: string;
  deadline_at?: string;
  notes?: string;
  subject?: string;
  description?: string;
  contact_email?: string;
  [key: string]: unknown;
}

export interface LegalIntakeResponse {
  id: string;
  request_id?: string;
  status?: string;
  created_at?: string;
  triage_summary?: {
    classification?: string;
    urgency_level?: string;
    [key: string]: unknown;
  };
  required_document_checklist?: LegalChecklistItem[];
  missing_items?: string[];
  [key: string]: unknown;
}

export interface LegalPricingQuoteResponse {
  quote_id?: string;
  estimated_cost?: number;
  currency?: string;
  total_due_cents?: number;
  agency_payout_cents?: number;
  platform_fee_cents?: number;
  margin_status?: string;
  hold_reasons?: string[];
  [key: string]: unknown;
}

export interface CaseRecordApi {
  id: string;
  case_number?: string;
  status?: string;
  priority?: string;
  transport_mode?: string;
  created_at?: string;
  patient_name?: string;
  [key: string]: unknown;
}

export type CasePriorityApi = 'emergent' | 'urgent' | 'routine';
export type CaseTransportModeApi = 'ground' | 'rotor' | 'fixed_wing';

export interface CaseCMSGatePayload {
  case_id?: string;
  transport_mode?: string;
  patient_condition?: string;
  transport_reason?: string;
  transport_level?: string;
  origin_address?: string;
  destination_name?: string;
  pcs_on_file?: boolean;
  pcs_obtained?: boolean;
  medical_necessity_documented?: boolean;
  patient_signature?: boolean;
  signature_on_file?: boolean;
  primary_insurance_id?: string;
  medicare_id?: string;
  medicaid_id?: string;
  [key: string]: unknown;
}

export interface CaseCMSGateResultApi {
  approved?: boolean;
  reason?: string;
  codes?: string[];
  [key: string]: unknown;
}

export interface DatasetActiveDeviceApi {
  id: string;
  device_name?: string;
  device_type?: string;
  ip?: string;
  agency?: string;
  user?: string;
  status?: string;
  last_seen?: string;
  tenant_id?: string;
  [key: string]: unknown;
}

export interface DatasetAIExpressionApi {
  expression_id?: string;
  result?: Record<string, unknown>;
  confidence?: number;
  [key: string]: unknown;
}

export interface DatasetExportsApi {
  exports?: { id: string; format: string; created_at: string }[];
  total?: number;
  total_today?: number;
  successful?: number;
  failed?: number;
  in_queue?: number;
  agencies?: { name: string; state: string; status: string; success_rate: number; failed_charts: number }[];
  [key: string]: unknown;
}

export interface DatasetSystemStatusApi {
  healthy?: boolean;
  last_sync?: string;
  record_count?: number;
  nemsis?: { healthy?: boolean; last_sync?: string; record_count?: number; version?: string; last_update?: string };
  neris?: { healthy?: boolean; last_sync?: string; record_count?: number; version?: string; last_update?: string };
  rxnorm?: { healthy?: boolean; last_sync?: string; record_count?: number; term_count?: number };
  snomed?: { healthy?: boolean; last_sync?: string; record_count?: number; term_count?: number };
  icd10?: { healthy?: boolean; last_sync?: string; record_count?: number; version?: string };
  facilities?: { total?: number; active?: number; last_state_sync?: string; active_count?: number };
  [key: string]: unknown;
}

export interface DispatchRequestApi {
  id: string;
  request_type?: string;
  status?: string;
  priority?: string;
  created_at?: string;
  origin_address?: string;
  destination_address?: string;
  [key: string]: unknown;
}

export interface FounderBillingVoiceConfigApi {
  enabled?: boolean;
  phone_number?: string;
  ivr_flow?: string;
  escalation_threshold?: number;
  [key: string]: unknown;
}
