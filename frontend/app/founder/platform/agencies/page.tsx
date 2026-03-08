'use client';

import { useEffect, useState } from 'react';
import { motion } from 'framer-motion';
import { listLifecycleEvents, platformTransitionLifecycle } from '@/services/api';

interface Tenant {
  id: string;
  name: string;
  lifecycle_state: string;
  agency_type: string;
  created_at: string;
}

interface LifecycleEvent {
  id: string;
  tenant_id: string;
  from_state: string;
  to_state: string;
  reason: string;
  performed_by: string;
  created_at: string;
}

const LIFECYCLE_STATES = [
  'TENANT_CREATED', 'CONFIG_PENDING', 'IMPLEMENTATION_IN_PROGRESS',
  'GO_LIVE_REVIEW', 'LIVE', 'SUSPENDED', 'OFFBOARDING', 'ARCHIVED',
];

const STATE_COLORS: Record<string, string> = {
  TENANT_CREATED: 'text-blue-400 bg-blue-400/10',
  CONFIG_PENDING: 'text-yellow-400 bg-yellow-400/10',
  IMPLEMENTATION_IN_PROGRESS: 'text-[#FF4D00] bg-[rgba(255,77,0,0.10)]',
  GO_LIVE_REVIEW: 'text-purple-400 bg-purple-400/10',
  LIVE: 'text-green-400 bg-green-400/10',
  SUSPENDED: 'text-red-400 bg-red-400/10',
  OFFBOARDING: 'text-zinc-400 bg-zinc-400/10',
  ARCHIVED: 'text-zinc-500 bg-zinc-500/10',
};

const API_BASE = process.env.NEXT_PUBLIC_API_BASE || process.env.NEXT_PUBLIC_API_URL || '';

function getToken(): string {
  if (typeof window === 'undefined') return '';
  return localStorage.getItem('token') || '';
}

export default function AgencyLifecyclePage() {
  const [tenants, setTenants] = useState<Tenant[]>([]);
  const [events, setEvents] = useState<LifecycleEvent[]>([]);
  const [selectedTenantId, setSelectedTenantId] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [transitionState, setTransitionState] = useState('');
  const [transitionReason, setTransitionReason] = useState('');
  const [submitting, setSubmitting] = useState(false);

  useEffect(() => {
    async function load() {
      try {
        const res = await fetch(`${API_BASE}/api/v1/platform/agencies`, {
          headers: { Authorization: `Bearer ${getToken()}` },
        });
        if (!res.ok) throw new Error(`Failed: ${res.status}`);
        setTenants(await res.json());
      } catch (err: unknown) {
        setError(err instanceof Error ? err.message : 'Failed to load agencies');
      } finally {
        setLoading(false);
      }
    }
    load();
  }, []);

  async function loadEvents(tenantId: string) {
    setSelectedTenantId(tenantId);
    try {
      const evts = await listLifecycleEvents(tenantId);
      setEvents(evts);
    } catch {
      setEvents([]);
    }
  }

  async function handleTransition() {
    if (!selectedTenantId || !transitionState || !transitionReason) return;
    setSubmitting(true);
    try {
      await platformTransitionLifecycle(selectedTenantId, {
        new_state: transitionState,
        reason: transitionReason,
      });
      setTransitionState('');
      setTransitionReason('');
      await loadEvents(selectedTenantId);
      // Reload tenant list
      const res = await fetch(`${API_BASE}/api/v1/platform/agencies`, {
        headers: { Authorization: `Bearer ${getToken()}` },
      });
      if (res.ok) setTenants(await res.json());
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : 'Transition failed');
    } finally {
      setSubmitting(false);
    }
  }

  if (loading) {
    return <div className="p-6 text-zinc-500 animate-pulse">Loading agencies…</div>;
  }
  if (error) {
    return <div className="p-6 text-red-400 text-sm">{error}</div>;
  }

  return (
    <div className="p-6 space-y-6">
      <div className="hud-rail pb-2">
        <h1 className="text-h1 font-bold text-zinc-100">Agency Lifecycle Management</h1>
        <p className="text-body text-zinc-500 mt-1">Manage tenant onboarding, go-live, suspension, and archival</p>
      </div>

      {/* KPI Strip */}
      <div className="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-8 gap-2">
        {LIFECYCLE_STATES.map((state) => {
          const count = tenants.filter((t) => t.lifecycle_state === state).length;
          return (
            <motion.div key={state} initial={{ opacity: 0, y: 4 }} animate={{ opacity: 1, y: 0 }}
              className="bg-[#0A0A0B] border border-border-DEFAULT p-3 text-center">
              <div className="text-[10px] font-semibold uppercase tracking-widest text-zinc-500 mb-1">{state.replace(/_/g, ' ')}</div>
              <div className={`text-lg font-bold ${STATE_COLORS[state]?.split(' ')[0] || 'text-zinc-100'}`}>{count}</div>
            </motion.div>
          );
        })}
      </div>

      <div className="flex gap-6">
        {/* Tenant List */}
        <div className="flex-1 space-y-2">
          <h2 className="text-sm font-bold uppercase tracking-widest text-zinc-500">All Agencies</h2>
          {tenants.length === 0 && <div className="text-xs text-zinc-500">No agencies found</div>}
          {tenants.map((t) => (
            <button
              key={t.id}
              onClick={() => loadEvents(t.id)}
              className={`w-full text-left p-3 border transition-colors ${
                selectedTenantId === t.id
                  ? 'border-brand-orange/40 bg-brand-orange/5'
                  : 'border-border-DEFAULT bg-[#0A0A0B] hover:border-brand-orange/20'
              }`}
            >
              <div className="flex items-center justify-between">
                <span className="text-sm font-semibold text-zinc-100">{t.name}</span>
                <span className={`text-[10px] px-2 py-0.5  font-semibold ${STATE_COLORS[t.lifecycle_state] || 'text-zinc-500 bg-zinc-500/10'}`}>
                  {t.lifecycle_state}
                </span>
              </div>
              <div className="text-[10px] text-zinc-500 mt-1">{t.agency_type || 'Unknown'} · Created {new Date(t.created_at).toLocaleDateString()}</div>
            </button>
          ))}
        </div>

        {/* Events & Transition Panel */}
        {selectedTenantId && (
          <div className="w-96 space-y-4">
            <div className="bg-[#0A0A0B] border border-border-DEFAULT p-4">
              <h3 className="text-sm font-bold uppercase tracking-widest text-zinc-500 mb-3">Transition State</h3>
              <select
                value={transitionState}
                onChange={(e) => setTransitionState(e.target.value)}
                className="w-full bg-bg-surface border border-border-DEFAULT p-2 text-sm text-zinc-100 mb-2"
              >
                <option value="">Select new state…</option>
                {LIFECYCLE_STATES.map((s) => (
                  <option key={s} value={s}>{s.replace(/_/g, ' ')}</option>
                ))}
              </select>
              <textarea
                value={transitionReason}
                onChange={(e) => setTransitionReason(e.target.value)}
                placeholder="Reason for transition…"
                className="w-full bg-bg-surface border border-border-DEFAULT p-2 text-sm text-zinc-100 mb-2 h-20 resize-none"
              />
              <button
                onClick={handleTransition}
                disabled={submitting || !transitionState || !transitionReason}
                className="w-full py-2 bg-brand-orange text-black text-sm font-semibold disabled:opacity-40 transition-opacity"
              >
                {submitting ? 'Processing…' : 'Apply Transition'}
              </button>
            </div>

            <div className="bg-[#0A0A0B] border border-border-DEFAULT p-4 max-h-96 overflow-y-auto">
              <h3 className="text-sm font-bold uppercase tracking-widest text-zinc-500 mb-3">Lifecycle Events</h3>
              {events.length === 0 && <div className="text-xs text-zinc-500">No events recorded</div>}
              {events.map((e) => (
                <div key={e.id} className="py-2 border-b border-white/5 last:border-0">
                  <div className="flex items-center gap-2 text-xs">
                    <span className={STATE_COLORS[e.from_state]?.split(' ')[0] || 'text-zinc-500'}>{e.from_state}</span>
                    <span className="text-zinc-500">→</span>
                    <span className={STATE_COLORS[e.to_state]?.split(' ')[0] || 'text-zinc-500'}>{e.to_state}</span>
                  </div>
                  <div className="text-[10px] text-zinc-500 mt-0.5">{e.reason}</div>
                  <div className="text-[10px] text-zinc-500">{new Date(e.created_at).toLocaleString()}</div>
                </div>
              ))}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
