'use client';

import { cn } from '@/lib/utils';
import type { SystemDomain } from '@/lib/design-system/tokens';
import { DOMAIN_COLOR_MAP, DOMAIN_LABEL } from '@/lib/design-system/tokens';

// ══════════════════════════════════════════════════════════════════
// FOUNDER COMMAND SHELL
// The top-level founder experience that makes switching between
// modules feel like one platform, one command system, one brain.
// ══════════════════════════════════════════════════════════════════

// ── Cross-Module Health Summary ──────────────────────────────────

export interface DomainHealth {
  readonly domain: SystemDomain;
  readonly score: number;
  readonly trend: 'up' | 'down' | 'stable';
  readonly alertCount: number;
  readonly topIssue?: string;
}

export interface CrossModuleHealthProps {
  readonly domains: readonly DomainHealth[];
  readonly compact?: boolean;
  readonly className?: string;
}

export function CrossModuleHealth({ domains, compact = false, className }: CrossModuleHealthProps) {
  return (
    <div className={cn('grid gap-2', compact ? 'grid-cols-3 lg:grid-cols-6' : 'grid-cols-2 md:grid-cols-3 lg:grid-cols-4 xl:grid-cols-6', className)}>
      {domains.map((d) => {
        const color = DOMAIN_COLOR_MAP[d.domain];
        const scoreColor = d.score >= 80 ? 'var(--color-status-active)'
          : d.score >= 60 ? 'var(--q-yellow)'
          : 'var(--color-brand-red)';

        return (
          <div
            key={d.domain}
            className="bg-bg-panel border border-[var(--color-border-default)] chamfer-4 p-3 relative overflow-hidden"
          >
            <div className="absolute top-0 left-0 right-0 h-0.5" style={{ backgroundColor: color }} />
            <div className="flex items-center justify-between mb-1.5">
              <span className="text-micro font-label uppercase tracking-wider text-text-muted truncate">
                {DOMAIN_LABEL[d.domain]}
              </span>
              {d.alertCount > 0 && (
                <span className="text-micro font-label px-1.5 py-0.5 bg-red-ghost text-red chamfer-4">
                  {d.alertCount}
                </span>
              )}
            </div>
            <div className="flex items-end gap-1.5">
              <span className="text-h3 font-bold" style={{ color: scoreColor }}>
                {d.score}%
              </span>
              <span className={cn(
                'text-micro mb-0.5',
                d.trend === 'up' && 'text-status-active',
                d.trend === 'down' && 'text-red',
                d.trend === 'stable' && 'text-text-muted'
              )}>
                {d.trend === 'up' ? '▲' : d.trend === 'down' ? '▼' : '—'}
              </span>
            </div>
            {d.topIssue && !compact && (
              <p className="text-micro text-text-disabled mt-1 truncate">{d.topIssue}</p>
            )}
          </div>
        );
      })}
    </div>
  );
}

// ── Cross-Module Top Actions ─────────────────────────────────────

export interface CrossModuleAction {
  readonly id: string;
  readonly label: string;
  readonly domain: SystemDomain;
  readonly severity: 'BLOCKING' | 'HIGH' | 'MEDIUM';
  readonly href?: string;
  readonly onClick?: () => void;
}

export interface CrossModuleActionsProps {
  readonly actions: readonly CrossModuleAction[];
  readonly maxVisible?: number;
  readonly className?: string;
}

export function CrossModuleActions({ actions, maxVisible = 3, className }: CrossModuleActionsProps) {
  const sorted = [...actions].sort((a, b) => {
    const order = { BLOCKING: 0, HIGH: 1, MEDIUM: 2 };
    return order[a.severity] - order[b.severity];
  });
  const visible = sorted.slice(0, maxVisible);

  if (visible.length === 0) {
    return (
      <div className={cn('bg-bg-panel border border-[var(--color-border-default)] chamfer-8 p-4 text-center', className)}>
        <p className="text-body text-text-muted">No critical actions right now. You are up to date.</p>
      </div>
    );
  }

  return (
    <div className={cn('space-y-2', className)}>
      <h3 className="font-label text-label uppercase tracking-wider text-text-secondary">
        Top Actions
      </h3>
      {visible.map((action) => {
        const domainColor = DOMAIN_COLOR_MAP[action.domain];
        const severityColor = action.severity === 'BLOCKING' ? 'var(--color-brand-red)'
          : action.severity === 'HIGH' ? 'var(--q-orange)'
          : 'var(--q-yellow)';

        const content = (
          <div
            className="flex items-center gap-3 p-3 bg-bg-panel border border-[var(--color-border-default)] chamfer-4
                       hover:bg-bg-overlay transition-colors duration-fast cursor-pointer"
          >
            <div className="w-1 h-8 chamfer-4 flex-shrink-0" style={{ backgroundColor: severityColor }} />
            <div className="flex-1 min-w-0">
              <p className="text-body text-text-primary truncate">{action.label}</p>
              <span className="text-micro font-label uppercase tracking-wider" style={{ color: domainColor }}>
                {DOMAIN_LABEL[action.domain]}
              </span>
            </div>
            <span
              className="text-micro font-label uppercase tracking-wider px-2 py-0.5 chamfer-4"
              style={{ color: severityColor, backgroundColor: `color-mix(in srgb, ${severityColor} 12%, transparent)` }}
            >
              {action.severity}
            </span>
          </div>
        );

        if (action.href) {
          return <a key={action.id} href={action.href} className="block no-underline">{content}</a>;
        }
        return <div key={action.id} onClick={action.onClick}>{content}</div>;
      })}
    </div>
  );
}

// ── Domain Navigation Card ───────────────────────────────────────
// Quick-access domain cards for the founder command overview.

export interface DomainNavCardProps {
  readonly domain: SystemDomain;
  readonly href: string;
  readonly description?: string;
  readonly score?: number;
  readonly alertCount?: number;
  readonly className?: string;
}

export function DomainNavCard({ domain, href, description, score, alertCount, className }: DomainNavCardProps) {
  const color = DOMAIN_COLOR_MAP[domain];

  return (
    <a
      href={href}
      className={cn(
        'block bg-bg-panel border border-[var(--color-border-default)] chamfer-8 p-4 relative overflow-hidden',
        'hover:bg-bg-overlay hover:border-[var(--color-border-strong)] transition-all duration-fast',
        'group',
        className
      )}
    >
      <div className="absolute top-0 left-0 right-0 h-0.5" style={{ backgroundColor: color }} />

      <div className="flex items-center justify-between mb-2">
        <span className="text-h3 font-sans font-bold text-text-primary group-hover:text-orange transition-colors duration-fast">
          {DOMAIN_LABEL[domain]}
        </span>
        {alertCount !== undefined && alertCount > 0 && (
          <span className="text-micro font-label px-1.5 py-0.5 bg-red-ghost text-red chamfer-4">
            {alertCount}
          </span>
        )}
      </div>

      {description && (
        <p className="text-label text-text-muted mb-3">{description}</p>
      )}

      {score !== undefined && (
        <div className="flex items-center gap-2">
          <div className="flex-1 h-1 bg-[var(--color-border-subtle)] chamfer-4 overflow-hidden">
            <div
              className="h-full chamfer-4 transition-all duration-slow"
              style={{
                width: `${score}%`,
                backgroundColor: score >= 80 ? 'var(--color-status-active)' : score >= 60 ? 'var(--q-yellow)' : 'var(--color-brand-red)',
              }}
            />
          </div>
          <span className="text-micro font-label text-text-muted">{score}%</span>
        </div>
      )}
    </a>
  );
}

// ── Founder Status Bar ───────────────────────────────────────────
// Status bar showing live platform vitals.

export interface FounderStatusBarProps {
  readonly isLive?: boolean;
  readonly activeIncidents?: number;
  readonly apiHealth?: number;
  readonly tenantCount?: number;
  readonly className?: string;
}

export function FounderStatusBar({
  isLive = true,
  activeIncidents = 0,
  apiHealth,
  tenantCount,
  className,
}: FounderStatusBarProps) {
  return (
    <div className={cn(
      'flex items-center gap-4 px-4 py-1.5 border-b border-[var(--color-border-subtle)] bg-bg-void text-micro',
      className
    )}>
      {/* Live indicator */}
      <div className="flex items-center gap-1.5">
        <span className={cn(
          'h-1.5 w-1.5 rounded-full',
          isLive ? 'bg-status-active animate-pulse' : 'bg-red'
        )} />
        <span className={cn(
          'font-label uppercase tracking-wider',
          isLive ? 'text-status-active' : 'text-red'
        )}>
          {isLive ? 'LIVE' : 'OFFLINE'}
        </span>
      </div>

      {/* Incidents */}
      {activeIncidents > 0 && (
        <div className="flex items-center gap-1.5">
          <span className="h-1.5 w-1.5 rounded-full bg-red animate-pulse" />
          <span className="font-label uppercase tracking-wider text-red">
            {activeIncidents} INCIDENT{activeIncidents > 1 ? 'S' : ''}
          </span>
        </div>
      )}

      {/* API Health */}
      {apiHealth !== undefined && (
        <div className="flex items-center gap-1.5 text-text-muted">
          <span className="font-label uppercase tracking-wider text-text-disabled">API</span>
          <span className={cn(
            'font-label',
            apiHealth >= 99 ? 'text-status-active' : apiHealth >= 95 ? 'text-yellow-400' : 'text-red'
          )}>
            {apiHealth}%
          </span>
        </div>
      )}

      {/* Tenant count */}
      {tenantCount !== undefined && (
        <div className="flex items-center gap-1.5 text-text-muted ml-auto">
          <span className="font-label uppercase tracking-wider text-text-disabled">TENANTS</span>
          <span className="text-text-secondary">{tenantCount}</span>
        </div>
      )}
    </div>
  );
}
