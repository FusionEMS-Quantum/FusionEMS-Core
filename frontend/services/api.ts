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
  const res = await API.get('/api/v1/ai-platform/registry', { headers: aiHeaders() });
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