'use client';

import { useEffect, useState } from 'react';
import { ModuleDashboardShell } from '@/components/shells/PageShells';
import { getPlatformLiveStatus } from '@/services/api';
import { StatusChip } from '@/components/ui/StatusChip';

export default function CommunicationsPage() {
  const [telnyx, setTelnyx] = useState<Record<string, unknown>>({});
  const [error, setError] = useState('');

  useEffect(() => {
    getPlatformLiveStatus()
      .then((data) => setTelnyx(((data as Record<string, unknown>).telnyx as Record<string, unknown>) ?? {}))
      .catch((e: unknown) => setError(e instanceof Error ? e.message : 'Failed to load communications readiness'));
  }, []);

  const blockers = Array.isArray(telnyx.blockers) ? (telnyx.blockers as string[]) : [];
  const configured = Boolean(telnyx.voice_binding) && Boolean(telnyx.messaging_profile);
  const healthStatus = error ? 'critical' : blockers.length > 0 ? 'warning' : configured ? 'active' : 'neutral';

  return (
    <ModuleDashboardShell title="Communications Control" subtitle="Operator-grade Telnyx readiness and assignment controls" accentColor="var(--color-brand-orange)">
      <div className="space-y-4">
        <div className="quantum-panel-strong px-5 py-5">
          <div className="flex flex-wrap items-start justify-between gap-4">
            <div>
              <div className="micro-caps">Tracked Number</div>
              <div className="mt-1 text-3xl font-black tracking-[-0.02em] text-zinc-100">{String(telnyx.number ?? '+1-888-365-0144')}</div>
              <div className="mt-2 text-body text-[var(--color-text-secondary)]">Configured Number: {String(telnyx.configured_number ?? 'unknown')}</div>
            </div>
            <StatusChip status={healthStatus} pulse={healthStatus === 'critical'}>
              {error ? 'Signal degraded' : blockers.length > 0 ? 'Action required' : configured ? 'Configured' : 'Awaiting configuration'}
            </StatusChip>
          </div>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <div className="quantum-panel-soft px-4 py-4 text-sm space-y-3">
            {[
              ['Voice binding', String(Boolean(telnyx.voice_binding))],
              ['Messaging profile assigned', String(Boolean(telnyx.messaging_profile))],
              ['Webhook health', String(Boolean(telnyx.webhook_health))],
              ['Stale binding detected', String(Boolean(telnyx.stale_binding_detected))],
            ].map(([label, value]) => (
              <div key={label} className="flex items-center justify-between gap-3 border-b border-[var(--color-border-subtle)] pb-2 last:border-b-0 last:pb-0">
                <span className="text-[var(--color-text-muted)]">{label}</span>
                <span className="font-label text-[var(--color-text-primary)] uppercase tracking-[0.08em]">{value}</span>
              </div>
            ))}
          </div>
          <div className="quantum-panel-soft px-4 py-4">
            <div className="micro-caps">Readiness blockers</div>
            {blockers.length === 0 ? <div className="text-sm mt-2">No blockers reported.</div> : (
              <ul className="list-disc pl-5 mt-2 text-sm text-[var(--color-brand-red)] space-y-1">
                {blockers.map((b) => <li key={b}>{b}</li>)}
              </ul>
            )}
            {error ? <div className="text-sm text-[var(--color-brand-red)] mt-2">{error}</div> : null}
          </div>
        </div>
      </div>
    </ModuleDashboardShell>
  );
}
