'use client';
import { motion } from 'framer-motion';
import Link from 'next/link';
import { useCallback, useEffect, useMemo, useState, type ReactNode } from 'react';
import { QuantumEmptyState } from '@/components/ui';
import { NextBestActionCard, type NextAction } from '@/components/ui/NextBestActionCard';
import { SeverityBadge } from '@/components/ui/SeverityBadge';
import { DomainNavCard, FounderStatusBar } from '@/components/shells/FounderCommand';
import type { SeverityLevel } from '@/lib/design-system/tokens';

const API = process.env.NEXT_PUBLIC_API_BASE || process.env.NEXT_PUBLIC_API_URL || '';

type FetchStatus = 'idle' | 'loading' | 'ready' | 'error';

type FunnelStage = {
  stage: string;
  count: number;
};

type ConversionFunnelResponse = {
  funnel: FunnelStage[];
  total_events: number;
};

type ConversionKpisResponse = {
  total_events: number;
  total_proposals: number;
  active_subscriptions: number;
  proposal_to_paid_conversion_pct: number;
  as_of: string;
};

type RevenuePipelineResponse = {
  pending_pipeline_cents: number;
  active_mrr_cents: number;
  pipeline_to_mrr_ratio: number;
  as_of: string;
};

function SectionHeader({ number, title, sub }: { number: string; title: string; sub?: string }) {
  return (
    <div className="border-b border-border-subtle pb-2 mb-4">
      <div className="flex items-baseline gap-3">
          <span className="text-micro font-bold text-orange-dim font-mono">MODULE {number}</span>
        <h2 className="text-sm font-bold uppercase tracking-widest text-zinc-100">{title}</h2>
        {sub && <span className="text-xs text-zinc-500">{sub}</span>}
      </div>
    </div>
  );
}

function Panel({ children, className }: { children: ReactNode; className?: string }) {
  return (
    <div
      className={`bg-[#0A0A0B] border border-border-DEFAULT p-4 ${className ?? ''}`}
      style={{ clipPath: 'polygon(0 0,calc(100% - 10px) 0,100% 10px,100% 100%,0 100%)' }}
    >
      {children}
    </div>
  );
}

export default function FunnelPage() {
  const [status, setStatus] = useState<FetchStatus>('idle');
  const [error, setError] = useState<string | null>(null);
  const [funnelData, setFunnelData] = useState<FunnelStage[]>([]);
  const [kpis, setKpis] = useState<ConversionKpisResponse | null>(null);
  const [pipeline, setPipeline] = useState<RevenuePipelineResponse | null>(null);

  const fetchFunnelTelemetry = useCallback((): void => {
    const token = typeof window !== 'undefined' ? localStorage.getItem('token') : null;
    const headers = token ? { Authorization: `Bearer ${token}` } : undefined;

    const fetchJson = async <T,>(url: string): Promise<T> => {
      const res = await fetch(url, { headers });
      if (!res.ok) {
        throw new Error(`Request failed (${res.status}) ${url}`);
      }
      return res.json() as Promise<T>;
    };

    setStatus('loading');
    setError(null);

    void Promise.all([
      fetchJson<ConversionFunnelResponse>(`${API}/api/v1/roi-funnel/conversion-funnel`),
      fetchJson<ConversionKpisResponse>(`${API}/api/v1/roi-funnel/conversion-kpis`),
      fetchJson<RevenuePipelineResponse>(`${API}/api/v1/roi-funnel/revenue-pipeline`),
    ])
      .then(([funnelRes, kpisRes, pipelineRes]) => {
        setFunnelData(funnelRes.funnel ?? []);
        setKpis(kpisRes);
        setPipeline(pipelineRes);
        setStatus('ready');
      })
      .catch((fetchError: unknown) => {
        const message = fetchError instanceof Error ? fetchError.message : 'Unknown funnel telemetry error';
        setError(message);
        setStatus('error');
      });
  }, []);

  useEffect(() => {
    fetchFunnelTelemetry();
  }, [fetchFunnelTelemetry]);

  const conversionPct = kpis?.proposal_to_paid_conversion_pct ?? 0;
  const hasTelemetryError = status === 'error';
  const maxCount = Math.max(...funnelData.map((stage) => stage.count), 1);
  const funnelSeverity: SeverityLevel = hasTelemetryError
    ? 'BLOCKING'
    : conversionPct < 20
      ? 'HIGH'
      : conversionPct < 40
        ? 'MEDIUM'
        : 'LOW';

  const funnelActions = useMemo<NextAction[]>(() => {
    const actions: NextAction[] = [];

    if (hasTelemetryError) {
      actions.push({
        id: 'roi-funnel-recover-telemetry',
        title: 'Recover ROI funnel telemetry to restore conversion visibility.',
        severity: 'BLOCKING',
        domain: 'Funnel Telemetry',
        href: '/founder/roi/funnel',
      });
    }

    if (conversionPct < 30) {
      actions.push({
        id: 'roi-funnel-low-conversion',
        title: 'Conversion is below 30%; prioritize proposal follow-up and close-loop execution.',
        severity: 'HIGH',
        domain: 'Proposal Tracker',
        href: '/founder/roi/proposals',
      });
    }

    if ((pipeline?.pipeline_to_mrr_ratio ?? 0) > 2) {
      actions.push({
        id: 'roi-funnel-pipeline-balance',
        title: 'Pipeline-to-MRR ratio is elevated; convert pending pipeline into active subscriptions.',
        severity: 'MEDIUM',
        domain: 'Revenue Pipeline',
        href: '/founder/roi/proposals',
      });
    }

    if (actions.length === 0) {
      actions.push({
        id: 'roi-funnel-steady-state',
        title: 'Funnel posture is stable; continue weekly conversion monitoring.',
        severity: 'LOW',
        domain: 'ROI Funnel',
        href: '/founder/roi',
      });
    }

    return actions;
  }, [conversionPct, hasTelemetryError, pipeline?.pipeline_to_mrr_ratio]);

  const activeIncidents = hasTelemetryError || conversionPct < 20 ? 1 : 0;

  return (
    <div className="min-h-screen bg-black text-zinc-100 p-6 space-y-6">
      <FounderStatusBar isLive={!hasTelemetryError} activeIncidents={activeIncidents} />

      <motion.div initial={{ opacity: 0, y: -12 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.4 }}>
        <div className="flex items-center justify-between mb-1">
          <span className="text-micro font-bold text-orange-dim font-mono tracking-widest uppercase">
            MODULE 09 · ROI & GROWTH
          </span>
          <div className="flex items-center gap-3">
            <button
              onClick={fetchFunnelTelemetry}
              className="h-8 px-3 text-xs font-semibold border border-status-warning/35 text-status-warning hover:bg-status-warning/10 transition-colors"
            >
              Refresh Telemetry
            </button>
            <Link href="/founder/roi" className="text-body text-zinc-500 hover:text-[#FF4D00] transition-colors">
              ← Back to ROI
            </Link>
          </div>
        </div>
        <h1 className="text-2xl font-bold tracking-tight text-zinc-100" style={{ textShadow: '0 0 24px rgba(255,107,26,0.3)' }}>
          Funnel Intelligence
        </h1>
        <p className="text-xs text-zinc-500 mt-1">Lead tracking · conversion velocity · pipeline stages</p>
        <div className="mt-2">
          <SeverityBadge severity={funnelSeverity} size="sm" />
        </div>
      </motion.div>

      <NextBestActionCard actions={funnelActions} title="ROI Funnel Next Best Actions" maxVisible={4} />

      <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
        <DomainNavCard
          domain="billing"
          href="/founder/revenue/billing-intelligence"
          description="Tie funnel movement to live billing outcomes and realized collections."
        />
        <DomainNavCard
          domain="ops"
          href="/founder/ops/command"
          description="Confirm onboarding and delivery capacity for incoming conversions."
        />
        <DomainNavCard
          domain="support"
          href="/founder/success-command"
          description="Coordinate follow-up execution with customer success and support teams."
        />
      </div>

      <motion.div initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.05 }}>
        <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
          {[
            { label: 'Total Events', value: kpis?.total_events ?? '-' },
            { label: 'Total Proposals', value: kpis?.total_proposals ?? '-' },
            { label: 'Active Subs', value: kpis?.active_subscriptions ?? '-' },
            { label: 'Conversion Rate', value: kpis ? `${kpis.proposal_to_paid_conversion_pct.toFixed(2)}%` : '-' },
          ].map((s) => (
            <Panel key={s.label} className="flex flex-col gap-1">
              <span className="text-micro text-zinc-500 uppercase tracking-wider">{s.label}</span>
              <span className="text-xl font-bold" style={{ color: 'var(--color-status-info)' }}>{s.value}</span>
            </Panel>
          ))}
        </div>
      </motion.div>

      <motion.div initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.1 }}>
        <Panel>
          <SectionHeader number="2" title="Funnel Stages" />
          {status === 'loading' || status === 'idle' ? (
            <QuantumEmptyState title="Loading funnel telemetry..." description="Connecting to ROI funnel APIs." icon="activity" />
          ) : status === 'error' ? (
            <QuantumEmptyState title="Funnel telemetry unavailable" description={error ?? 'Unable to load ROI funnel telemetry.'} icon="activity" />
          ) : (
            <div className="space-y-4">
              {funnelData.length === 0 ? <p className="text-xs text-zinc-500">No events logged yet.</p> : null}
              {funnelData.map((s) => {
                const width = Math.max((s.count / maxCount) * 100, 5);
                return (
                  <div key={s.stage} className="flex items-center gap-4">
                    <div className="w-32 text-xs text-zinc-100 uppercase tracking-wider">{s.stage}</div>
                    <div className="flex-1 h-3 bg-zinc-950/5 chamfer-4 overflow-hidden relative">
                      <div
                        className="absolute top-0 left-0 h-full transition-all duration-1000"
                        style={{ width: `${width}%`, background: 'var(--color-brand-cyan)' }}
                      />
                    </div>
                    <div className="w-16 text-right font-mono text-xs">{s.count}</div>
                  </div>
                );
              })}
            </div>
          )}
        </Panel>
      </motion.div>

      <Panel>
        <SectionHeader number="3" title="Pipeline Snapshot" sub="Pending value · active MRR · leverage ratio" />
        {status === 'error' ? (
          <QuantumEmptyState
            title="Revenue pipeline telemetry unavailable"
            description="Pipeline metrics are currently unavailable due to degraded funnel telemetry."
            icon="activity"
          />
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
            <div className="bg-zinc-950/20 border border-border-subtle p-3">
              <div className="text-micro uppercase tracking-wider text-zinc-500 mb-1">Pending Pipeline</div>
              <div className="text-lg font-bold text-status-warning">
                ${((pipeline?.pending_pipeline_cents ?? 0) / 100).toLocaleString()}
              </div>
            </div>
            <div className="bg-zinc-950/20 border border-border-subtle p-3">
              <div className="text-micro uppercase tracking-wider text-zinc-500 mb-1">Active MRR</div>
              <div className="text-lg font-bold text-status-active">
                ${((pipeline?.active_mrr_cents ?? 0) / 100).toLocaleString()}
              </div>
            </div>
            <div className="bg-zinc-950/20 border border-border-subtle p-3">
              <div className="text-micro uppercase tracking-wider text-zinc-500 mb-1">Pipeline / MRR</div>
              <div className="text-lg font-bold text-system-billing">
                {(pipeline?.pipeline_to_mrr_ratio ?? 0).toFixed(2)}x
              </div>
            </div>
          </div>
        )}
      </Panel>

      <div className="pt-2">
        <Link href="/founder/roi" className="text-body text-zinc-500 hover:text-[#FF4D00] transition-colors">
          ← Back to ROI Overview
        </Link>
      </div>
    </div>
  );
}
