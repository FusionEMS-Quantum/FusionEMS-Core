'use client';

import { useEffect, useState } from 'react';
import { ModuleDashboardShell } from '@/components/shells/PageShells';
import { getPlatformLiveStatus } from '@/services/api';
import { StatusChip } from '@/components/ui/StatusChip';

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
  const chipStatus = status === 'healthy' ? 'active' : status === 'blocked' || status === 'degraded' ? 'critical' : 'warning';
  const blockers = Array.isArray(data?.release_blockers) ? (data?.release_blockers as string[]) : [];
  const telnyx = (data?.telnyx ?? {}) as Record<string, unknown>;
  const nemsis = (data?.nemsis ?? {}) as Record<string, unknown>;
  const neris = (data?.neris ?? {}) as Record<string, unknown>;
  const release = (data?.release ?? {}) as Record<string, unknown>;
  const integrationState = ((data?.integration_state ?? {}) as Record<string, {
    required?: boolean;
    configured?: boolean;
    status?: string;
    missing?: string[];
    placeholder_fields?: string[];
  }>);
  const integrations = Object.entries(integrationState);

  const renderBool = (value: unknown) => (value ? 'YES' : 'NO');

  return (
    <ModuleDashboardShell title="Live Status" subtitle="Canonical authenticated go-live readiness" accentColor="var(--color-brand-orange)">
      <div className="space-y-4">
        <div className="quantum-panel-strong px-5 py-5">
          <div className="flex flex-wrap items-start justify-between gap-4">
            <div>
              <div className="micro-caps">Overall</div>
              <div className="text-3xl font-black tracking-[-0.02em]" style={{ color: statusColor }}>{status.toUpperCase()}</div>
            </div>
            <StatusChip status={chipStatus} pulse={chipStatus === 'critical'}>
              {status === 'healthy' ? 'Verified telemetry' : status === 'unknown' ? 'Awaiting signal' : 'Operator attention'}
            </StatusChip>
          </div>
          {error ? <div className="text-sm text-[var(--color-brand-red)] mt-2">{error}</div> : null}
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <div className="quantum-panel-soft px-4 py-4">
            <div className="micro-caps">Release</div>
            <div className="text-sm mt-2">Version: {String(release.version ?? 'unknown')}</div>
            <div className="text-sm">Last successful: {String(release.last_successful_release ?? 'unknown')}</div>
            <div className="text-sm">Rollback ready: {renderBool(release.rollback_ready)}</div>
          </div>
          <div className="quantum-panel-soft px-4 py-4">
            <div className="micro-caps">Telnyx readiness ({String(telnyx.number ?? '+1-888-365-0144')})</div>
            <div className="text-sm mt-2">Voice binding: {renderBool(telnyx.voice_binding)}</div>
            <div className="text-sm">Messaging profile: {renderBool(telnyx.messaging_profile)}</div>
            <div className="text-sm">Webhook health: {renderBool(telnyx.webhook_health)}</div>
          </div>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <div className="quantum-panel-soft px-4 py-4">
            <div className="micro-caps">NEMSIS readiness</div>
            <div className="text-sm mt-2">Validation: {String(nemsis.validation_status ?? 'not_available')}</div>
            <div className="text-sm">Certification: {String(nemsis.certification_status ?? 'not_available')}</div>
            <div className="text-sm">CTA endpoint ready: {renderBool(nemsis.cta_endpoint_ready)}</div>
            <div className="text-sm">Local schematron configured: {renderBool(nemsis.local_schematron_configured)}</div>
          </div>
          <div className="quantum-panel-soft px-4 py-4">
            <div className="micro-caps">NERIS readiness</div>
            <div className="text-sm mt-2">Validation: {String(neris.validation_status ?? 'not_available')}</div>
            <div className="text-sm">Acceptance: {String(neris.certification_status ?? 'not_available')}</div>
            <div className="text-sm">Submission API ready: {renderBool(neris.submission_api_ready)}</div>
          </div>
        </div>

        <div className="quantum-panel-soft px-4 py-4">
          <div className="micro-caps">Integration wiring</div>
          {integrations.length === 0 ? (
            <div className="text-sm text-[var(--color-text-primary)] mt-2">No integration telemetry reported.</div>
          ) : (
            <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-3 mt-3">
              {integrations.map(([name, integration]) => {
                const missing = Array.isArray(integration.missing) ? integration.missing : [];
                const placeholders = Array.isArray(integration.placeholder_fields) ? integration.placeholder_fields : [];
                const integrationHealthy = Boolean(integration.configured);
                const color = integrationHealthy
                  ? 'var(--color-status-active)'
                  : integration.required
                    ? 'var(--color-brand-red)'
                    : 'var(--color-status-warning)';

                return (
                  <div key={name} className="border border-[var(--color-border-subtle)] bg-[var(--color-surface-elevated)] px-4 py-3 rounded-[14px]">
                    <div className="flex items-center justify-between gap-3">
                      <div className="text-sm font-semibold uppercase tracking-[0.14em] text-[var(--color-text-primary)]">{name.replace(/_/g, ' ')}</div>
                      <div className="text-xs font-semibold uppercase tracking-[0.14em]" style={{ color }}>
                        {String(integration.status ?? (integrationHealthy ? 'active' : 'unknown')).replace(/_/g, ' ')}
                      </div>
                    </div>
                    <div className="text-xs text-[var(--color-text-secondary)] mt-2">Required: {renderBool(integration.required)}</div>
                    {missing.length > 0 ? <div className="text-xs text-[var(--color-brand-red)] mt-1">Missing: {missing.join(', ')}</div> : null}
                    {placeholders.length > 0 ? <div className="text-xs text-[var(--color-status-warning)] mt-1">Placeholder values: {placeholders.join(', ')}</div> : null}
                  </div>
                );
              })}
            </div>
          )}
        </div>

        <div className="quantum-panel-soft px-4 py-4">
          <div className="micro-caps">Release blockers</div>
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
