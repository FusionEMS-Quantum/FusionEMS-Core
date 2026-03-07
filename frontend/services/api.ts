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
