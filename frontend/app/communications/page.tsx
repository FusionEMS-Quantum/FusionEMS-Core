'use client';

import { useEffect, useState } from 'react';
import { ModuleDashboardShell } from '@/components/shells/PageShells';
import { getPlatformLiveStatus } from '@/services/api';

function StatusIndicator({ ok, label }: { ok: boolean; label: string }) {
  const color = ok ? 'var(--color-status-active)' : 'var(--color-status-warning)';
  return (
    <div className="flex items-center gap-3 py-2">
      <div className="w-2 h-2 flex-shrink-0" style={{ backgroundColor: color, boxShadow: `0 0 6px ${color}` }} />
      <span className="text-sm text-[var(--color-text-primary)]">{label}</span>
      <span className="ml-auto text-xs font-bold uppercase tracking-wider" style={{ color }}>{ok ? 'Active' : 'Unverified'}</span>
    </div>
  );
}

export default function CommunicationsPage() {
  const [telnyx, setTelnyx] = useState<Record<string, unknown>>({});
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    setLoading(true);
    getPlatformLiveStatus()
      .then((data) => {
        setTelnyx(((data as Record<string, unknown>).telnyx as Record<string, unknown>) ?? {});
      })
      .catch((e: unknown) => setError(e instanceof Error ? e.message : 'Failed to load communications readiness'))
      .finally(() => setLoading(false));
  }, []);

  const blockers = Array.isArray(telnyx.blockers) ? (telnyx.blockers as string[]) : [];
  const voiceOk = Boolean(telnyx.voice_binding);
  const messagingOk = Boolean(telnyx.messaging_profile);
  const webhookOk = Boolean(telnyx.webhook_health);
  const staleBinding = Boolean(telnyx.stale_binding_detected);
  const allClear = voiceOk && messagingOk && webhookOk && !staleBinding && blockers.length === 0;

  return (
    <ModuleDashboardShell title="Communications Control" subtitle="Operator-grade Telnyx readiness console for +1-888-365-0144" accentColor="var(--color-brand-orange)">
      <div className="space-y-6">
        {/* Overall readiness banner */}
        <div className="border border-[var(--color-border-default)] bg-[var(--color-bg-panel)] p-6 rounded-lg">
          <div className="flex items-center justify-between">
            <div>
              <div className="text-xs font-bold uppercase tracking-[0.15em] text-[var(--color-text-muted)] mb-2">Communications Readiness</div>
              <div className="flex items-center gap-3">
                <div className="w-3 h-3 flex-shrink-0" style={{
                  backgroundColor: loading ? 'var(--color-status-warning)' : allClear ? 'var(--color-status-active)' : 'var(--color-brand-red)',
                  boxShadow: `0 0 8px ${loading ? 'var(--color-status-warning)' : allClear ? 'var(--color-status-active)' : 'var(--color-brand-red)'}`
                }} />
                <div className="text-xl font-black uppercase tracking-wider" style={{
                  color: loading ? 'var(--color-status-warning)' : allClear ? 'var(--color-status-active)' : 'var(--color-brand-red)'
                }}>
                  {loading ? 'Loading...' : allClear ? 'Ready' : 'Action Required'}
                </div>
              </div>
            </div>
            <div className="text-right">
              <div className="text-lg font-bold text-[var(--color-text-primary)]">{String(telnyx.number ?? '+1-888-365-0144')}</div>
              <div className="text-xs text-[var(--color-text-muted)]">Primary billing number</div>
            </div>
          </div>
          {error && <div className="text-sm text-[var(--color-brand-red)] mt-3 p-3 bg-[var(--color-brand-red)]/10 border border-[var(--color-brand-red)]/30 rounded">{error}</div>}
        </div>

        {/* Binding status checks */}
        <div className="border border-[var(--color-border-default)] bg-[var(--color-bg-panel)] p-5 rounded-lg">
          <div className="text-xs font-bold uppercase tracking-[0.15em] text-[var(--color-text-muted)] mb-3">Binding & Profile Status</div>
          <div className="divide-y divide-[var(--color-border-default)]">
            <StatusIndicator ok={voiceOk} label="Voice binding for +1-888-365-0144" />
            <StatusIndicator ok={messagingOk} label="Messaging profile assigned" />
            <StatusIndicator ok={webhookOk} label="Webhook reachability" />
            <StatusIndicator ok={!staleBinding} label={staleBinding ? 'Stale binding detected — cleanup required' : 'No stale bindings detected'} />
          </div>
        </div>

        {/* Configuration detail */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <div className="border border-[var(--color-border-default)] bg-[var(--color-bg-panel)] p-5 rounded-lg">
            <div className="text-xs font-bold uppercase tracking-[0.15em] text-[var(--color-text-muted)] mb-3">Number Configuration</div>
            <div className="space-y-2 text-sm">
              <div className="flex justify-between"><span className="text-[var(--color-text-muted)]">Primary Number</span><span className="font-bold">{String(telnyx.number ?? '+1-888-365-0144')}</span></div>
              <div className="flex justify-between"><span className="text-[var(--color-text-muted)]">Configured Number</span><span className="font-bold">{String(telnyx.configured_number ?? 'unknown')}</span></div>
              <div className="flex justify-between"><span className="text-[var(--color-text-muted)]">Provider</span><span className="font-bold">Telnyx</span></div>
            </div>
          </div>

          {/* Readiness blockers */}
          <div className="border border-[var(--color-border-default)] bg-[var(--color-bg-panel)] p-5 rounded-lg">
            <div className="text-xs font-bold uppercase tracking-[0.15em] text-[var(--color-text-muted)] mb-3">Readiness Blockers</div>
            {blockers.length === 0 ? (
              <div className="text-sm text-[var(--color-text-primary)]">No blockers reported.</div>
            ) : (
              <ul className="list-disc pl-5 text-sm text-[var(--color-brand-red)] space-y-1">
                {blockers.map((b) => <li key={b}>{b}</li>)}
              </ul>
            )}
          </div>
        </div>

        {/* Release block status */}
        <div className="border border-[var(--color-border-default)] bg-[var(--color-bg-panel)] p-5 rounded-lg">
          <div className="text-xs font-bold uppercase tracking-[0.15em] text-[var(--color-text-muted)] mb-2">Release Block Status</div>
          <div className="text-sm">
            {loading ? (
              <span className="text-[var(--color-status-warning)]">Checking communications readiness...</span>
            ) : allClear ? (
              <span className="text-[var(--color-status-active)] font-bold">Communications: No release blocks</span>
            ) : (
              <span className="text-[var(--color-brand-red)] font-bold">Communications: Release blocked — resolve binding and webhook issues before go-live</span>
            )}
          </div>
        </div>
      </div>
    </ModuleDashboardShell>
  );
}
