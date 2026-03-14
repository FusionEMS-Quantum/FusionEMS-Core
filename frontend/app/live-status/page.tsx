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

function StatusIndicator({ status, size = 'sm' }: { status: string; size?: 'sm' | 'md' | 'lg' }) {
  const color = statusColor(status);
  const px = size === 'lg' ? 10 : size === 'md' ? 6 : 5;
  return (
    <div className="relative flex-shrink-0" style={{ width: px, height: px }}>
      <div className="absolute inset-0" style={{ backgroundColor: color, boxShadow: `0 0 8px ${color}` }} />
    </div>
  );
}

/* Shared panel styling for HUD-consistent cards */
function HudPanel({ children, className = '', accent = false }: { children: React.ReactNode; className?: string; accent?: boolean }) {
  return (
    <div className={`chamfer-4 relative ${className}`}
      style={{
        background: 'var(--color-surface-primary)',
        border: '1px solid var(--color-border-default)',
      }}>
      {accent && <div className="absolute top-0 left-0 right-0 h-[2px]" style={{ background: 'linear-gradient(90deg, var(--color-brand-orange), transparent)' }} />}
      {children}
    </div>
  );
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
      <div className="space-y-5">

        {/* ── OVERALL STATUS ── */}
        <HudPanel accent>
          <div className="p-5 lg:p-6">
            <div className="flex items-start justify-between gap-4 flex-wrap">
              <div>
                <div className="text-[0.6rem] font-bold uppercase tracking-[0.2em] mb-3" style={{ color: 'var(--color-text-disabled)' }}>Overall Platform Status</div>
                <div className="flex items-center gap-3">
                  <StatusIndicator status={overallStatus} size="lg" />
                  <div className="text-[1.6rem] font-black uppercase tracking-[0.08em]" style={{ color: statusColor(overallStatus) }}>{overallStatus}</div>
                </div>
              </div>
              <div className="text-right space-y-1">
                <div className="text-[0.65rem] font-bold uppercase tracking-[0.1em]" style={{ color: 'var(--color-text-muted)' }}>
                  Release <span style={{ color: 'var(--color-text-primary)' }}>{String(release.version ?? 'unknown')}</span>
                </div>
                <div className="text-[0.6rem]" style={{ color: 'var(--color-text-disabled)' }}>
                  Last deploy: {String(release.last_successful_release ?? 'unknown')}
                </div>
              </div>
            </div>
            {error && (
              <div className="chamfer-4 mt-4 p-3 text-sm font-medium"
                style={{ background: 'var(--color-brand-red-ghost)', border: '1px solid rgba(201,59,44,0.3)', color: 'var(--color-brand-red)' }}>
                {error}
              </div>
            )}
          </div>
        </HudPanel>

        {/* ── HEALTH CHECKS GRID ── */}
        <div>
          <div className="flex items-center gap-3 mb-3">
            <div className="w-6 h-[2px]" style={{ background: 'var(--color-brand-orange)' }} />
            <span className="text-[0.6rem] font-bold uppercase tracking-[0.2em]" style={{ color: 'var(--color-text-muted)' }}>System Health Checks</span>
          </div>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-2">
            {healthChecks.map((check) => (
              <HudPanel key={check.label}>
                <div className="p-3.5 flex items-center gap-3">
                  <StatusIndicator status={check.status} />
                  <div className="min-w-0 flex-1">
                    <div className="text-[0.75rem] font-bold" style={{ color: 'var(--color-text-primary)' }}>{check.label}</div>
                    <div className="text-[0.65rem] mt-0.5" style={{ color: 'var(--color-text-disabled)' }}>{check.detail}</div>
                  </div>
                  <div className="text-[0.55rem] font-bold uppercase tracking-[0.15em] flex-shrink-0 px-2 py-0.5 chamfer-4"
                    style={{
                      color: statusColor(check.status),
                      background: check.status === 'healthy' ? 'rgba(34,197,94,0.08)' : check.status === 'unknown' ? 'rgba(245,158,11,0.08)' : 'rgba(201,59,44,0.08)',
                      border: `1px solid ${statusColor(check.status)}33`,
                    }}>
                    {check.status}
                  </div>
                </div>
              </HudPanel>
            ))}
          </div>
        </div>

        {/* ── DEGRADED SERVICES ── */}
        {degradedServices.length > 0 && (
          <div className="chamfer-4 p-4"
            style={{ background: 'var(--color-dark-red-surface)', border: '1px solid rgba(201,59,44,0.25)' }}>
            <div className="flex items-center gap-2 mb-3">
              <StatusIndicator status="degraded" />
              <span className="text-[0.6rem] font-bold uppercase tracking-[0.2em]" style={{ color: 'var(--color-brand-red)' }}>
                Degraded / Unverified Services
              </span>
            </div>
            <div className="space-y-1.5">
              {degradedServices.map((s) => (
                <div key={s.label} className="flex items-center gap-2 text-[0.75rem]">
                  <StatusIndicator status={s.status} />
                  <span style={{ color: 'var(--color-text-primary)' }}>{s.label}</span>
                  <span style={{ color: 'var(--color-text-disabled)' }}>— {s.detail}</span>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* ── RELEASE BLOCKERS ── */}
        <HudPanel>
          <div className="p-4">
            <div className="text-[0.6rem] font-bold uppercase tracking-[0.2em] mb-2" style={{ color: 'var(--color-text-muted)' }}>Release Blockers</div>
            {blockers.length === 0 ? (
              <div className="flex items-center gap-2 text-[0.75rem]">
                <StatusIndicator status="healthy" />
                <span style={{ color: 'var(--color-text-primary)' }}>No blockers reported</span>
              </div>
            ) : (
              <div className="space-y-1.5">
                {blockers.map((b) => (
                  <div key={b} className="flex items-center gap-2 text-[0.75rem]">
                    <StatusIndicator status="blocked" />
                    <span style={{ color: 'var(--color-brand-red)' }}>{b}</span>
                  </div>
                ))}
              </div>
            )}
          </div>
        </HudPanel>

        {/* ── TELNYX COMMUNICATIONS DETAIL ── */}
        <HudPanel accent>
          <div className="p-4 lg:p-5">
            <div className="flex items-center gap-3 mb-4">
              <div className="w-6 h-[2px]" style={{ background: 'var(--color-brand-orange)' }} />
              <span className="text-[0.6rem] font-bold uppercase tracking-[0.2em]" style={{ color: 'var(--color-text-muted)' }}>Telnyx Communications Detail</span>
            </div>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
              {[
                { label: 'Primary Number', value: String(telnyx.number ?? '+1-888-365-0144') },
                { label: 'Configured', value: String(telnyx.configured_number ?? 'unknown') },
              ].map((item) => (
                <div key={item.label} className="flex items-center justify-between py-2 px-3 chamfer-4" style={{ background: 'var(--color-surface-secondary)' }}>
                  <span className="text-[0.65rem] uppercase tracking-[0.1em]" style={{ color: 'var(--color-text-disabled)' }}>{item.label}</span>
                  <span className="text-[0.8rem] font-bold" style={{ color: 'var(--color-text-primary)' }}>{item.value}</span>
                </div>
              ))}
              {[
                { label: 'Voice binding', flag: telnyx.voice_binding },
                { label: 'Messaging profile', flag: telnyx.messaging_profile },
                { label: 'Webhook reachability', flag: telnyx.webhook_health },
                { label: 'Stale binding', flag: !telnyx.stale_binding_detected, invert: true },
              ].map((item) => (
                <div key={item.label} className="flex items-center gap-2 py-2 px-3 chamfer-4" style={{ background: 'var(--color-surface-secondary)' }}>
                  <StatusIndicator status={item.invert ? deriveStatus(item.flag) : deriveStatus(item.flag)} />
                  <span className="text-[0.7rem]" style={{ color: 'var(--color-text-muted)' }}>{item.label}</span>
                </div>
              ))}
            </div>
          </div>
        </HudPanel>

      </div>
    </ModuleDashboardShell>
  );
}
