'use client';

import { useEffect, useState } from 'react';
import { ModuleDashboardShell } from '@/components/shells/PageShells';
import { getPlatformLiveStatus } from '@/services/api';

export default function CommunicationsPage() {
  const [telnyx, setTelnyx] = useState<Record<string, unknown>>({});
  const [error, setError] = useState('');

  useEffect(() => {
    getPlatformLiveStatus()
      .then((data) => setTelnyx(((data as Record<string, unknown>).telnyx as Record<string, unknown>) ?? {}))
      .catch((e: unknown) => setError(e instanceof Error ? e.message : 'Failed to load communications readiness'));
  }, []);

  const blockers = Array.isArray(telnyx.blockers) ? (telnyx.blockers as string[]) : [];

  return (
    <ModuleDashboardShell title="Communications Control" subtitle="Operator-grade Telnyx readiness and assignment controls" accentColor="var(--color-system-communications)">
      <div className="space-y-4">
        <div className="border border-[var(--color-border-default)] bg-[var(--color-bg-panel)] p-4 rounded-lg">
          <div className="text-sm text-[var(--color-text-muted)]">Tracked Number</div>
          <div className="text-xl font-bold mt-1">{String(telnyx.number ?? '+1-888-365-0144')}</div>
          <div className="text-sm mt-2">Configured Number: {String(telnyx.configured_number ?? 'unknown')}</div>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <div className="border border-[var(--color-border-default)] bg-[var(--color-bg-panel)] p-4 rounded-lg text-sm space-y-2">
            <div>Voice binding: {String(Boolean(telnyx.voice_binding))}</div>
            <div>Messaging profile assigned: {String(Boolean(telnyx.messaging_profile))}</div>
            <div>Webhook health: {String(Boolean(telnyx.webhook_health))}</div>
            <div>Stale binding detected: {String(Boolean(telnyx.stale_binding_detected))}</div>
          </div>
          <div className="border border-[var(--color-border-default)] bg-[var(--color-bg-panel)] p-4 rounded-lg">
            <div className="text-sm text-[var(--color-text-muted)]">Readiness blockers</div>
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
