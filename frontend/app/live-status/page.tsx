'use client';

import { useEffect, useState } from 'react';
import { ModuleDashboardShell } from '@/components/shells/PageShells';
import { getPlatformLiveStatus } from '@/services/api';

interface HealthCheck {
  label: string;
  status: 'healthy' | 'degraded' | 'unknown' | 'blocked';
  detail: string;
}

function statusColor(s: string): string {
  if (s === 'healthy') return 'var(--color-status-active)';
  if (s === 'degraded' || s === 'blocked') return 'var(--color-brand-red)';
  return 'var(--color-status-warning)';
}

function StatusDot({ status }: { status: string }) {
  const color = statusColor(status);
  return <div className="w-2 h-2 flex-shrink-0" style={{ backgroundColor: color, boxShadow: `0 0 6px ${color}` }} />;
}

export default function LiveStatusPage() {
  const [data, setData] = useState<Record<string, unknown> | null>(null);
  const [error, setError] = useState('');

  useEffect(() => {
    getPlatformLiveStatus()
      .then((res) => setData(res as Record<string, unknown>))
      .catch((e: unknown) => setError(e instanceof Error ? e.message : 'Status unavailable'));
  }, []);

  const overallStatus = String(data?.overall_status ?? (error ? 'degraded' : 'unknown'));
  const blockers = Array.isArray(data?.release_blockers) ? (data?.release_blockers as string[]) : [];
  const telnyx = (data?.telnyx ?? {}) as Record<string, unknown>;
  const release = (data?.release ?? {}) as Record<string, unknown>;
  const auth = (data?.auth ?? {}) as Record<string, unknown>;
  const nemsis = (data?.nemsis ?? {}) as Record<string, unknown>;
  const services = (data?.services ?? {}) as Record<string, unknown>;

  const isLoaded = data !== null;
  const deriveStatus = (flag: unknown): 'healthy' | 'unknown' =>
    isLoaded && flag ? 'healthy' : 'unknown';

  const healthChecks: HealthCheck[] = [
    { label: 'Frontend Health', status: isLoaded ? 'healthy' : 'unknown', detail: isLoaded ? 'Rendering active' : 'Waiting for data' },
    { label: 'Backend Health', status: deriveStatus(services.backend ?? data?.overall_status), detail: String(services.backend ?? overallStatus) },
    { label: 'Auth / Session Health', status: deriveStatus(auth.ready), detail: auth.ready ? 'Microsoft Entra → JWT active' : 'Not verified' },
    { label: 'Microsoft Login Health', status: deriveStatus(auth.microsoft_ready ?? auth.ready), detail: auth.microsoft_ready ? 'Entra redirect verified' : 'Not verified' },
    { label: 'Telnyx Voice (+1-888-365-0144)', status: deriveStatus(telnyx.voice_binding), detail: telnyx.voice_binding ? 'Voice binding active' : 'Not bound' },
    { label: 'Telnyx Messaging', status: deriveStatus(telnyx.messaging_profile), detail: telnyx.messaging_profile ? 'Profile assigned' : 'Not assigned' },
    { label: 'Telnyx Webhooks', status: deriveStatus(telnyx.webhook_health), detail: telnyx.webhook_health ? 'Reachable' : 'Not verified' },
    { label: 'NEMSIS Readiness', status: deriveStatus(nemsis.ready), detail: nemsis.ready ? 'Schema validation active' : 'Not verified' },
    { label: 'Release Version', status: 'healthy', detail: String(release.version ?? 'unknown') },
    { label: 'Rollback Readiness', status: deriveStatus(release.rollback_ready), detail: release.rollback_ready ? 'Ready' : 'Not verified' },
  ];

  const degradedServices = healthChecks.filter((c) => c.status !== 'healthy');

  return (
    <ModuleDashboardShell title="Live Status" subtitle="Canonical authenticated go-live readiness — runtime truth only" accentColor="var(--color-brand-orange)">
      <div className="space-y-6">
        {/* Overall Status */}
        <div className="border border-[var(--color-border-default)] bg-[var(--color-bg-panel)] p-6 rounded-lg">
          <div className="flex items-center justify-between">
            <div>
              <div className="text-xs font-bold uppercase tracking-[0.15em] text-[var(--color-text-muted)] mb-2">Overall Platform Status</div>
              <div className="flex items-center gap-3">
                <StatusDot status={overallStatus} />
                <div className="text-2xl font-black uppercase tracking-wider" style={{ color: statusColor(overallStatus) }}>{overallStatus}</div>
              </div>
            </div>
            <div className="text-right">
              <div className="text-xs text-[var(--color-text-muted)]">Release: {String(release.version ?? 'unknown')}</div>
              <div className="text-xs text-[var(--color-text-muted)]">Last deploy: {String(release.last_successful_release ?? 'unknown')}</div>
            </div>
          </div>
          {error && <div className="text-sm text-[var(--color-brand-red)] mt-3 p-3 bg-[var(--color-brand-red)]/10 border border-[var(--color-brand-red)]/30 rounded">{error}</div>}
        </div>

        {/* Health Checks Grid */}
        <div>
          <div className="text-xs font-bold uppercase tracking-[0.15em] text-[var(--color-text-muted)] mb-3">System Health Checks</div>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
            {healthChecks.map((check) => (
              <div key={check.label} className="border border-[var(--color-border-default)] bg-[var(--color-bg-panel)] p-4 rounded-lg flex items-start gap-3">
                <StatusDot status={check.status} />
                <div className="min-w-0">
                  <div className="text-sm font-bold text-[var(--color-text-primary)]">{check.label}</div>
                  <div className="text-xs text-[var(--color-text-muted)] mt-0.5">{check.detail}</div>
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* Degraded Services */}
        {degradedServices.length > 0 && (
          <div className="border border-[var(--color-brand-red)]/30 bg-[var(--color-brand-red)]/5 p-4 rounded-lg">
            <div className="text-xs font-bold uppercase tracking-[0.15em] text-[var(--color-brand-red)] mb-2">Degraded / Unverified Services</div>
            <ul className="space-y-1">
              {degradedServices.map((s) => (
                <li key={s.label} className="text-sm text-[var(--color-text-primary)] flex items-center gap-2">
                  <StatusDot status={s.status} />
                  {s.label}: {s.detail}
                </li>
              ))}
            </ul>
          </div>
        )}

        {/* Release Blockers */}
        <div className="border border-[var(--color-border-default)] bg-[var(--color-bg-panel)] p-4 rounded-lg">
          <div className="text-xs font-bold uppercase tracking-[0.15em] text-[var(--color-text-muted)] mb-2">Release Blockers</div>
          {blockers.length === 0 ? (
            <div className="text-sm text-[var(--color-text-primary)]">No blockers reported.</div>
          ) : (
            <ul className="list-disc pl-5 text-sm space-y-1 text-[var(--color-brand-red)]">
              {blockers.map((b) => <li key={b}>{b}</li>)}
            </ul>
          )}
        </div>

        {/* Telnyx Detail Panel */}
        <div className="border border-[var(--color-border-default)] bg-[var(--color-bg-panel)] p-4 rounded-lg">
          <div className="text-xs font-bold uppercase tracking-[0.15em] text-[var(--color-text-muted)] mb-3">Telnyx Communications Detail</div>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-3 text-sm">
            <div>Number: {String(telnyx.number ?? '+1-888-365-0144')}</div>
            <div>Configured: {String(telnyx.configured_number ?? 'unknown')}</div>
            <div className="flex items-center gap-2"><StatusDot status={deriveStatus(telnyx.voice_binding)} /> Voice binding</div>
            <div className="flex items-center gap-2"><StatusDot status={deriveStatus(telnyx.messaging_profile)} /> Messaging profile</div>
            <div className="flex items-center gap-2"><StatusDot status={deriveStatus(telnyx.webhook_health)} /> Webhook reachability</div>
            <div className="flex items-center gap-2"><StatusDot status={telnyx.stale_binding_detected ? 'degraded' : deriveStatus(!telnyx.stale_binding_detected)} /> Stale binding: {String(Boolean(telnyx.stale_binding_detected))}</div>
          </div>
        </div>
      </div>
    </ModuleDashboardShell>
  );
}
