'use client';

import * as React from 'react';
import Link from 'next/link';
import { clsx } from 'clsx';

/* ─── Types ──────────────────────────────────────────────────────────────── */

export type DependencyStatus =
  | 'not_configured'
  | 'not_entitled'
  | 'degraded'
  | 'offline'
  | 'auth_required'
  | 'rate_limited'
  | 'pending_deployment'
  | 'pending_migration';

export interface DependencyInfo {
  name: string;
  status: DependencyStatus;
  detail?: string;
}

export interface ModuleUnavailableProps {
  /** Module display name */
  module: string;
  /** Why this module is currently unavailable */
  reason: DependencyStatus;
  /** Human-readable explanation */
  description?: string;
  /** Specific dependencies blocking this module */
  dependencies?: DependencyInfo[];
  /** Back navigation */
  backHref?: string;
  backLabel?: string;
  /** Contact or escalation action */
  contactHref?: string;
  /** Additional CSS */
  className?: string;
}

/* ─── Status Metadata ────────────────────────────────────────────────────── */

const STATUS_META: Record<DependencyStatus, { label: string; color: string; icon: string }> = {
  not_configured:    { label: 'Not Configured',      color: 'var(--color-status-warning)', icon: '⚙' },
  not_entitled:      { label: 'Not in Current Plan', color: 'var(--color-status-info)',    icon: '🔒' },
  degraded:          { label: 'Degraded',            color: 'var(--color-status-warning)', icon: '⚠' },
  offline:           { label: 'Offline',             color: 'var(--color-brand-red)',      icon: '✕' },
  auth_required:     { label: 'Authentication Required', color: 'var(--color-status-info)', icon: '🔑' },
  rate_limited:      { label: 'Rate Limited',        color: 'var(--color-status-warning)', icon: '⏳' },
  pending_deployment:{ label: 'Pending Deployment',  color: 'var(--color-status-info)',    icon: '🚀' },
  pending_migration: { label: 'Pending Migration',   color: 'var(--color-status-info)',    icon: '📦' },
};

/* ─── Component ──────────────────────────────────────────────────────────── */

export function ModuleUnavailable({
  module,
  reason,
  description,
  dependencies,
  backHref,
  backLabel,
  contactHref = '/contact',
  className,
}: ModuleUnavailableProps) {
  const meta = STATUS_META[reason];

  return (
    <div className={clsx('min-h-[60vh] flex items-center justify-center p-6', className)}>
      <div className="max-w-lg w-full text-center space-y-6">
        {/* Status indicator */}
        <div
          className="inline-flex items-center gap-2 px-3 py-1.5 text-micro font-bold uppercase tracking-[0.14em] border chamfer-4"
          style={{
            color: meta.color,
            borderColor: `color-mix(in srgb, ${meta.color} 40%, transparent)`,
            background: `color-mix(in srgb, ${meta.color} 8%, transparent)`,
          }}
        >
          <span>{meta.icon}</span>
          <span>{meta.label}</span>
        </div>

        {/* Module name */}
        <h1 className="text-xl font-black uppercase tracking-wider text-zinc-100">
          {module}
        </h1>

        {/* Explanation */}
        <p className="text-body text-zinc-400 max-w-md mx-auto">
          {description ?? `This module is currently ${meta.label.toLowerCase()}. It requires additional configuration, entitlement, or infrastructure before it can display live operational data.`}
        </p>

        {/* Dependency detail table */}
        {dependencies && dependencies.length > 0 && (
          <div className="border border-border-subtle bg-[rgba(10,10,11,0.5)] chamfer-8 overflow-hidden text-left">
            <div className="px-4 py-2 border-b border-border-subtle">
              <span className="text-micro font-bold uppercase tracking-[0.14em] text-zinc-500">
                Dependency Status
              </span>
            </div>
            <div className="divide-y divide-border-subtle">
              {dependencies.map((dep) => {
                const depMeta = STATUS_META[dep.status];
                return (
                  <div key={dep.name} className="px-4 py-2.5 flex items-center justify-between gap-3">
                    <div>
                      <div className="text-sm text-zinc-200 font-medium">{dep.name}</div>
                      {dep.detail && (
                        <div className="text-xs text-zinc-500 mt-0.5">{dep.detail}</div>
                      )}
                    </div>
                    <span
                      className="shrink-0 inline-flex items-center gap-1 px-2 py-0.5 text-micro font-semibold uppercase tracking-wider border chamfer-4"
                      style={{
                        color: depMeta.color,
                        borderColor: `color-mix(in srgb, ${depMeta.color} 30%, transparent)`,
                        background: `color-mix(in srgb, ${depMeta.color} 6%, transparent)`,
                      }}
                    >
                      {depMeta.label}
                    </span>
                  </div>
                );
              })}
            </div>
          </div>
        )}

        {/* Actions */}
        <div className="flex items-center justify-center gap-3 flex-wrap">
          {backHref && (
            <Link
              href={backHref}
              className="px-4 py-2 text-label font-label uppercase tracking-[var(--tracking-label)] text-zinc-400 hover:text-zinc-200 transition-colors"
            >
              &larr; {backLabel ?? 'Back'}
            </Link>
          )}
          <Link
            href={contactHref}
            className="px-4 py-2 text-label font-label uppercase tracking-[var(--tracking-label)] text-[#FF4D00] hover:text-[#FF6A00] transition-colors"
          >
            Contact Support
          </Link>
        </div>
      </div>
    </div>
  );
}
