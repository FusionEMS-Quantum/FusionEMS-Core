'use client';

import { useEffect, useState } from 'react';
import { ModuleDashboardShell } from '@/components/shells/PageShells';
import { getPlatformLiveStatus } from '@/services/api';

export default function LiveStatusPage() {
  const [data, setData] = useState<Record<string, unknown> | null>(null);
  const [error, setError] = useState('');

  useEffect(() => {
    getPlatformLiveStatus()
      .then((res) => setData(res as Record<string, unknown>))
      .catch((e: unknown) => setError(e instanceof Error ? e.message : 'Status unavailable'));
  }, []);

  const status = String(data?.overall_status ?? (error ? 'degraded' : 'unknown'));
  const statusColor = status === 'healthy' ? 'var(--color-status-active)' : status === 'blocked' || status === 'degraded' ? 'var(--color-brand-red)' : 'var(--color-status-warning)';
  const blockers = Array.isArray(data?.release_blockers) ? (data?.release_blockers as string[]) : [];
  const telnyx = (data?.telnyx ?? {}) as Record<string, unknown>;
  const release = (data?.release ?? {}) as Record<string, unknown>;

  return (
    <ModuleDashboardShell title="Live Status" subtitle="Canonical authenticated go-live readiness" accentColor="var(--color-system-system)">
      <div className="space-y-4">
        <div className="border border-[var(--color-border-default)] bg-[var(--color-bg-panel)] p-4 rounded-lg">
          <div className="text-sm text-[var(--color-text-muted)]">Overall</div>
          <div className="text-2xl font-bold" style={{ color: statusColor }}>{status.toUpperCase()}</div>
          {error ? <div className="text-sm text-[var(--color-brand-red)] mt-2">{error}</div> : null}
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <div className="border border-[var(--color-border-default)] bg-[var(--color-bg-panel)] p-4 rounded-lg">
            <div className="text-sm text-[var(--color-text-muted)]">Release</div>
            <div className="text-sm mt-2">Version: {String(release.version ?? 'unknown')}</div>
            <div className="text-sm">Last successful: {String(release.last_successful_release ?? 'unknown')}</div>
            <div className="text-sm">Rollback ready: {String(Boolean(release.rollback_ready))}</div>
          </div>
          <div className="border border-[var(--color-border-default)] bg-[var(--color-bg-panel)] p-4 rounded-lg">
            <div className="text-sm text-[var(--color-text-muted)]">Telnyx readiness ({String(telnyx.number ?? '+1-888-365-0144')})</div>
            <div className="text-sm mt-2">Voice binding: {String(Boolean(telnyx.voice_binding))}</div>
            <div className="text-sm">Messaging profile: {String(Boolean(telnyx.messaging_profile))}</div>
            <div className="text-sm">Webhook health: {String(Boolean(telnyx.webhook_health))}</div>
          </div>
        </div>

        <div className="border border-[var(--color-border-default)] bg-[var(--color-bg-panel)] p-4 rounded-lg">
          <div className="text-sm text-[var(--color-text-muted)]">Release blockers</div>
          {blockers.length === 0 ? (
            <div className="text-sm text-[var(--color-text-primary)] mt-2">No blockers reported.</div>
          ) : (
            <ul className="list-disc pl-5 mt-2 text-sm space-y-1 text-[var(--color-brand-red)]">
              {blockers.map((b) => <li key={b}>{b}</li>)}
            </ul>
          )}
        </div>
      </div>
    </ModuleDashboardShell>
  );
}
