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

export async function getFounderFailedSyncJobs(limit = 50) {
  const res = await API.get('/api/v1/founder/integration-command/failed-sync-jobs', {
    headers: csHeaders(),
    params: { limit },
  });
  return res.data;
}

export async function createFounderSyncJob(payload: {
  tenant_connector_install_id: string;
  direction: string;
  state?: string;
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

// ── Relationship Command Center ────────────────────────────────────────────

function relHeaders() {
  return aiHeaders();
}

export async function getRelationshipCommandSummary() {
  const res = await API.get('/api/v1/founder/relationship-command/summary', { headers: relHeaders() });
  return res.data;
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
