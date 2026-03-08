'use client';

import React, { useCallback, useEffect, useMemo, useState } from 'react';

type SummaryPayload = {
  active_billing_calls: number;
  awaiting_human_followup: number;
  unresolved_voice_sessions: number;
  top_billing_phone_actions: Array<{ action: string; count: number }>;
};

type EscalationItem = {
  id: string;
  session_id: string | null;
  tenant_id: string | null;
  caller_phone_number: string | null;
  statement_id: string | null;
  account_id: string | null;
  verification_state: string | null;
  ai_intent: string | null;
  ai_summary: string | null;
  escalation_reason: string;
  recommended_next_action: string | null;
  status: string;
  created_at: string | null;
};

type EscalationsPayload = { items: EscalationItem[] };

const API_BASE = process.env.NEXT_PUBLIC_API_URL || '';

function cardTone(reason: string): { border: string; bg: string; text: string } {
  const r = (reason || '').toLowerCase();
  if (r.includes('legal') || r.includes('fraud') || r.includes('identity')) {
    return { border: 'rgba(229,57,53,0.45)', bg: 'rgba(229,57,53,0.10)', text: 'var(--color-brand-red)' };
  }
  if (r.includes('dispute') || r.includes('policy') || r.includes('lookup')) {
    return { border: 'rgba(255,152,0,0.45)', bg: 'rgba(255,152,0,0.10)', text: 'var(--color-brand-orange)' };
  }
  return { border: 'rgba(76,175,80,0.35)', bg: 'rgba(76,175,80,0.08)', text: 'var(--color-status-active)' };
}

export default function FounderBillingVoicePage() {
  const [summary, setSummary] = useState<SummaryPayload | null>(null);
  const [escalations, setEscalations] = useState<EscalationItem[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string>('');
  const [takeoverId, setTakeoverId] = useState<string>('');

  const load = useCallback(async () => {
    setLoading(true);
    setError('');
    try {
      const [summaryRes, escalationsRes] = await Promise.all([
        fetch(`${API_BASE}/api/v1/founder/billing-voice/summary`, { credentials: 'include' }),
        fetch(`${API_BASE}/api/v1/founder/billing-voice/escalations?status=awaiting_human&limit=50`, { credentials: 'include' }),
      ]);

      if (!summaryRes.ok) throw new Error(`Summary failed (${summaryRes.status})`);
      if (!escalationsRes.ok) throw new Error(`Escalations failed (${escalationsRes.status})`);

      const summaryJson: SummaryPayload = await summaryRes.json();
      const escalationsJson: EscalationsPayload = await escalationsRes.json();
      setSummary(summaryJson);
      setEscalations(escalationsJson.items || []);
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : 'Failed to load billing voice command data');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    load();
    const id = window.setInterval(load, 10000);
    return () => window.clearInterval(id);
  }, [load]);

  const highPriorityCount = useMemo(
    () => escalations.filter((i) => /legal|fraud|identity/i.test(i.escalation_reason || '')).length,
    [escalations],
  );

  async function takeover(escalationId: string) {
    setTakeoverId(escalationId);
    setError('');
    try {
      const res = await fetch(`${API_BASE}/api/v1/founder/billing-voice/escalations/${encodeURIComponent(escalationId)}/takeover`, {
        method: 'POST',
        credentials: 'include',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ channel: 'softphone' }),
      });
      if (!res.ok) {
        const body = await res.json().catch(() => ({}));
        throw new Error(body?.detail || `Takeover failed (${res.status})`);
      }
      await load();
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : 'Takeover failed');
    } finally {
      setTakeoverId('');
    }
  }

  return (
    <div className="min-h-screen bg-bg-void text-text-primary px-4 md:px-8 py-6 space-y-6">
      <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-2">
        <div>
          <h1 className="text-2xl font-bold">Central Billing Voice Command</h1>
          <p className="text-xs text-text-muted">WHAT HAPPENED · WHY IT MATTERS · DO THIS NEXT</p>
        </div>
        <button
          onClick={load}
          className="px-3 py-2 text-xs font-semibold border border-border-strong chamfer-4 hover:bg-[rgba(255,255,255,0.06)]"
          disabled={loading}
        >
          {loading ? 'Refreshing…' : 'Refresh'}
        </button>
      </div>

      {error && (
        <div className="p-3 text-sm border chamfer-4" style={{ borderColor: 'rgba(229,57,53,0.45)', backgroundColor: 'rgba(229,57,53,0.10)', color: 'var(--color-brand-red)' }}>
          {error}
        </div>
      )}

      <div className="grid grid-cols-1 md:grid-cols-4 gap-3">
        <div className="p-4 border border-border-subtle bg-[rgba(255,255,255,0.02)] chamfer-4">
          <div className="text-xs text-text-muted">Active Calls</div>
          <div className="text-2xl font-bold">{summary?.active_billing_calls ?? '—'}</div>
        </div>
        <div className="p-4 border border-border-subtle bg-[rgba(255,255,255,0.02)] chamfer-4">
          <div className="text-xs text-text-muted">Awaiting Human</div>
          <div className="text-2xl font-bold text-orange">{summary?.awaiting_human_followup ?? '—'}</div>
        </div>
        <div className="p-4 border border-border-subtle bg-[rgba(255,255,255,0.02)] chamfer-4">
          <div className="text-xs text-text-muted">Unresolved Sessions</div>
          <div className="text-2xl font-bold">{summary?.unresolved_voice_sessions ?? '—'}</div>
        </div>
        <div className="p-4 border border-border-subtle bg-[rgba(255,255,255,0.02)] chamfer-4">
          <div className="text-xs text-text-muted">High-Risk Escalations</div>
          <div className="text-2xl font-bold text-red-400">{highPriorityCount}</div>
        </div>
      </div>

      <div className="p-4 border border-border-subtle bg-[rgba(255,255,255,0.02)] chamfer-4">
        <div className="text-xs uppercase tracking-wider text-text-muted mb-3">Top 3 Billing Phone Actions</div>
        <div className="flex flex-wrap gap-2">
          {(summary?.top_billing_phone_actions || []).map((a) => (
            <span key={a.action} className="text-xs px-2 py-1 rounded border border-border-subtle bg-[rgba(255,255,255,0.03)]">
              {a.action} · {a.count}
            </span>
          ))}
          {(!summary?.top_billing_phone_actions || summary.top_billing_phone_actions.length === 0) && (
            <span className="text-xs text-text-muted">No action data yet.</span>
          )}
        </div>
      </div>

      <div className="space-y-3">
        <div className="text-xs uppercase tracking-wider text-text-muted">Calls Awaiting Founder Takeover</div>
        {escalations.length === 0 && (
          <div className="p-4 border border-border-subtle bg-[rgba(255,255,255,0.02)] chamfer-4 text-sm text-text-muted">
            No pending escalations. AI is holding the line. ☕
          </div>
        )}

        {escalations.map((e) => {
          const tone = cardTone(e.escalation_reason || '');
          return (
            <div key={e.id} className="p-4 border chamfer-4" style={{ borderColor: tone.border, backgroundColor: tone.bg }}>
              <div className="flex flex-col md:flex-row md:items-start md:justify-between gap-3">
                <div className="space-y-1">
                  <div className="text-sm font-semibold" style={{ color: tone.text }}>
                    {e.escalation_reason || 'escalation'}
                  </div>
                  <div className="text-xs text-text-secondary">
                    Caller: {e.caller_phone_number || 'unknown'} · Statement: {e.statement_id || 'unknown'} · Account: {e.account_id || 'unknown'}
                  </div>
                  <div className="text-xs text-text-secondary">
                    Verification: {e.verification_state || 'unknown'} · Intent: {e.ai_intent || 'unknown'}
                  </div>
                  {e.ai_summary && <div className="text-sm text-text-primary">{e.ai_summary}</div>}
                  {e.recommended_next_action && (
                    <div className="text-xs text-text-muted">Do this next: {e.recommended_next_action}</div>
                  )}
                </div>
                <button
                  onClick={() => takeover(e.id)}
                  disabled={takeoverId === e.id}
                  className="px-3 py-2 text-xs font-bold bg-orange text-text-inverse chamfer-4 disabled:opacity-50"
                >
                  {takeoverId === e.id ? 'Connecting…' : 'Accept Call'}
                </button>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
