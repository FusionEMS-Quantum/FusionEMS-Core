'use client';

import React, { Suspense, useEffect, useState } from 'react';
import AppShell from '@/components/AppShell';
import { MetricPlate, PlateCard } from '@/components/ui/PlateCard';
import { StatusChip } from '@/components/ui/StatusChip';
import { LiveEventFeed } from '@/components/LiveEventFeed';
import { getExecutiveSummary } from '@/services/api';

// ─── Types ───────────────────────────────────────────────────────────────────

interface ExecutiveSummary {
  mrr:             number;
  clients:         number;
  system_status:   string;
  active_units:    number;
  open_incidents:  number;
  pending_claims:  number;
  collection_rate: number;
}

type ModuleStatus = 'active' | 'warning' | 'critical' | 'info' | 'neutral';

interface SystemModule {
  name:   string;
  status: ModuleStatus;
  detail: string;
}

// ─── System module list (status transitions to API telemetry) ─────────────────

const SYSTEM_MODULES: SystemModule[] = [
  { name: 'Billing Engine',    status: 'active',   detail: 'Operational'      },
  { name: 'Compliance Layer',  status: 'active',   detail: 'Monitoring'       },
  { name: 'CAD Integration',   status: 'warning',  detail: 'Latency elevated' },
  { name: 'Fleet Tracking',    status: 'active',   detail: 'Operational'      },
  { name: 'Auth System',       status: 'active',   detail: 'Operational'      },
  { name: 'NEMSIS Export',     status: 'info',     detail: 'Batch pending'    },
];

// ─── Skeleton ────────────────────────────────────────────────────────────────

function SkeletonPlate() {
  return (
    <div
      className="chamfer-8 border animate-pulse"
      style={{
        height:          96,
        backgroundColor: 'var(--color-bg-panel)',
        borderColor:     'var(--color-border-subtle)',
      }}
    />
  );
}

// ─── Page ────────────────────────────────────────────────────────────────────

function DashboardPageInner() {
  const [summary, setSummary] = useState<ExecutiveSummary | null>(null);
  const [loading, setLoading] = useState(true);
  const [error,   setError]   = useState('');

  const today = new Date().toLocaleDateString('en-US', {
    weekday: 'long',
    year:    'numeric',
    month:   'long',
    day:     'numeric',
  });

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    setError('');

    Promise.all([getExecutiveSummary()])
      .then(([summaryData]) => {
        if (cancelled) return;
        setSummary(summaryData as ExecutiveSummary);
      })
      .catch(() => {
        if (cancelled) return;
        setError('Failed to load dashboard data. Check your connection and try again.');
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });

    return () => { cancelled = true; };
  }, []);

  return (
    <AppShell>
      <div className="mb-4 flex flex-wrap items-center gap-4 border border-white/[0.06] bg-[var(--color-surface-secondary)] px-4 py-2.5">
        <span className="inline-flex items-center gap-2 text-[10px] font-bold uppercase tracking-[0.2em] text-[var(--color-success)]">
          <span className="h-1.5 w-1.5 bg-[var(--color-success)] shadow-[0_0_5px_#4E9F6E]" />
          Operations live
        </span>
        <span className="inline-flex items-center gap-2 text-[10px] font-bold uppercase tracking-[0.2em] text-[var(--color-info)]">
          <span className="h-1.5 w-1.5 bg-[var(--color-info)] shadow-[0_0_5px_#5C8DB8]" />
          Dispatch telemetry active
        </span>
        <span className="inline-flex items-center gap-2 text-[10px] font-bold uppercase tracking-[0.2em] text-[var(--color-brand-orange)]">
          <span className="h-1.5 w-1.5 bg-[var(--color-brand-orange)] shadow-[0_0_5px_#F36A21]" />
          Founder visibility online
        </span>
      </div>

      {/* ── Page header ────────────────────────────────────────────────── */}
      <div
        className="hud-rail mb-6 flex items-center justify-between pb-4"
        style={{ borderBottom: '1px solid rgba(255,255,255,0.06)' }}
      >
        <div>
          <div className="mb-1 text-[11px] font-bold uppercase tracking-[0.2em] text-[var(--color-brand-orange)]">Command Dashboard</div>
          <h1 className="text-3xl font-black tracking-[0.01em] text-[var(--color-text-primary)] md:text-[2.2rem]">Operations Control Surface</h1>
          <p
            className="mt-1 text-[11px] font-bold uppercase tracking-[0.14em]"
            style={{ color: 'var(--color-text-muted)' }}
          >
            {today}
          </p>
        </div>

        <div
          className="px-3 py-1.5"
          style={{
            backgroundColor: 'var(--color-brand-orange-ghost)',
            border:          '1px solid var(--color-brand-orange-glow)',
          }}
        >
          <span
            className="micro-caps"
            style={{ color: 'var(--q-orange)' }}
          >
            Live
          </span>
        </div>
      </div>

      {/* ── Error state ────────────────────────────────────────────────── */}
      {error && (
        <PlateCard critical padding="md" className="mb-6">
          <p
            className="micro-caps"
            style={{ color: 'var(--color-brand-red)' }}
          >
            {error}
          </p>
        </PlateCard>
      )}

      {/* ── KPI row ────────────────────────────────────────────────────── */}
      <div className="mb-6 grid grid-cols-2 gap-4 sm:grid-cols-3 lg:grid-cols-6">
        {loading ? (
          Array.from({ length: 6 }).map((_, i) => <SkeletonPlate key={i} />)
        ) : summary ? (
          <>
            <MetricPlate
              label="MRR"
              value={`$${(summary.mrr / 1000).toFixed(0)}K`}
              accent="billing"
            />
            <MetricPlate
              label="Active Clients"
              value={summary.clients}
              accent="compliance"
            />
            <MetricPlate
              label="Active Units"
              value={summary.active_units}
              accent="fleet"
            />
            <MetricPlate
              label="Open Incidents"
              value={summary.open_incidents}
              accent="cad"
              trendDirection={summary.open_incidents > 0 ? 'up' : 'neutral'}
              trendPositive={false}
              trend={summary.open_incidents > 0 ? `${summary.open_incidents} open` : undefined}
            />
            <MetricPlate
              label="Pending Claims"
              value={summary.pending_claims}
              accent="billing"
            />
            <MetricPlate
              label="Collection Rate"
              value={`${summary.collection_rate}%`}
              accent="active"
              trendDirection="up"
              trendPositive
              trend="vs prior period"
            />
          </>
        ) : null}
      </div>

      {/* ── Main content: two-column ────────────────────────────────────── */}
      <div className="grid grid-cols-1 gap-4 lg:grid-cols-3">

        {/* Left 2/3 — Live event feed */}
        <div className="lg:col-span-2">
          <PlateCard
            header="Live Event Feed"
            accent="cad"
            padding="md"
          >
            {loading ? (
              <div className="flex flex-col gap-2">
                {Array.from({ length: 5 }).map((_, i) => (
                  <div
                    key={i}
                    className="chamfer-4 animate-pulse"
                    style={{
                      height:          48,
                      backgroundColor: 'var(--color-bg-input)',
                    }}
                  />
                ))}
              </div>
            ) : (
              <LiveEventFeed maxEvents={20} />
            )}
          </PlateCard>
        </div>

        {/* Right 1/3 — System Status */}
        <div className="lg:col-span-1">
          <PlateCard
            header="System Status"
            accent="compliance"
            padding="none"
          >
            <div className="flex flex-col divide-y" style={{ borderColor: 'var(--color-border-subtle)' }}>
              {SYSTEM_MODULES.map((mod) => (
                <div
                  key={mod.name}
                  className="flex items-center justify-between px-4 py-3 gap-3"
                >
                  <div className="min-w-0">
                    <p
                      className="truncate"
                      style={{
                        fontFamily: 'var(--font-sans)',
                        fontSize:   'var(--text-body)',
                        color:      'var(--color-text-primary)',
                      }}
                    >
                      {mod.name}
                    </p>
                    <p
                      className="micro-caps mt-0.5"
                      style={{ color: 'var(--color-text-muted)' }}
                    >
                      {mod.detail}
                    </p>
                  </div>
                  <StatusChip status={mod.status} size="sm">
                    {mod.status}
                  </StatusChip>
                </div>
              ))}
            </div>
          </PlateCard>
        </div>

      </div>
    </AppShell>
  );
}

export default function DashboardPage() {
  return (
    <Suspense>
      <DashboardPageInner />
    </Suspense>
  );
}
