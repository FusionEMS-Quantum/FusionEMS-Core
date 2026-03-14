'use client';

import React, { useEffect, useState, useCallback } from 'react';
import { QuantumTableSkeleton, QuantumEmptyState } from '@/components/ui';
import { ModuleDashboardShell } from '@/components/shells/PageShells';
import {
  getBillingKPIs,
  getDenialHeatmap,
  getPayerPerformance,
  getRevenueLeakage,
  getBillingHealth,
  getBillingAlerts,
  getRevenueTrend,
  getFraudAnomalies,
  batchResubmitClaims,
} from '@/services/api';

// ── Types ─────────────────────────────────────────────────────────────────────

interface BillingKPI {
  label: string;
  value: string;
  trend?: number;
  color?: string;
}

interface DenialEntry {
  payer?: string;
  code?: string;
  reason?: string;
  count?: number;
  amount?: number;
}

interface PayerRow {
  payer_name?: string;
  clean_claim_rate?: number;
  avg_days_to_pay?: number;
  total_paid?: number;
  denial_rate?: number;
  volume?: number;
}

interface RevenueTrendPoint {
  period?: string;
  gross_billed?: number;
  collected?: number;
  adjustments?: number;
}

interface FraudAnomaly {
  claim_id?: string;
  type?: string;
  score?: number;
  detail?: string;
  flagged_at?: string;
}

interface BillingAlert {
  id?: string;
  severity?: string;
  message?: string;
  created_at?: string;
}

interface RevenueLeakage {
  total_leakage?: number;
  categories?: { label: string; amount: number; count: number }[];
}

// ── Helpers ───────────────────────────────────────────────────────────────────

function fmt$(n: number) {
  return new Intl.NumberFormat('en-US', { style: 'currency', currency: 'USD', maximumFractionDigits: 0 }).format(n);
}

function fmtPct(n: number) {
  return `${Math.round(n * 100) / 100}%`;
}

function asNumberOrZero(n: unknown): number {
  return typeof n === 'number' && Number.isFinite(n) ? n : 0;
}

function TrendBadge({ trend }: { trend: number }) {
  const up = trend >= 0;
  return (
    <span className={`text-micro font-bold ml-1 ${up ? 'text-[var(--color-status-active)]' : 'text-[var(--color-brand-red)]'}`}>
      {up ? '▲' : '▼'} {Math.abs(trend).toFixed(1)}%
    </span>
  );
}

function SeverityBadge({ severity }: { severity: string }) {
  const cls =
    severity === 'CRITICAL' ? 'bg-[var(--color-brand-red-ghost)] border-[color-mix(in_srgb,var(--color-brand-red)_40%,transparent)] text-[var(--color-brand-red)]' :
    severity === 'HIGH' ? 'bg-[var(--color-brand-orange-ghost)] border-[color-mix(in_srgb,var(--q-orange)_40%,transparent)] text-[var(--q-orange-bright)]' :
    severity === 'MEDIUM' ? 'bg-[color-mix(in_srgb,var(--q-yellow)_10%,transparent)] border-[color-mix(in_srgb,var(--q-yellow)_40%,transparent)] text-[var(--q-yellow)]' :
    'bg-[var(--color-bg-raised)] border-[var(--color-border-default)] text-[var(--color-text-muted)]';
  return (
    <span className={`text-xs font-semibold px-2 py-0.5 chamfer-4 border ${cls}`}>{severity}</span>
  );
}

// ── KPI Bar ───────────────────────────────────────────────────────────────────

function KPIBar({ kpis }: { kpis: BillingKPI[] }) {
  return (
    <div className="grid grid-cols-4 gap-3 mb-5">
      {kpis.map(kpi => (
        <div key={kpi.label} className="bg-[var(--color-bg-panel)] border border-border-subtle chamfer-8 px-4 py-3">
          <div className={`text-2xl font-black ${kpi.color || 'text-[var(--color-text-primary)]'}`}>
            {kpi.value}
            {kpi.trend != null && <TrendBadge trend={kpi.trend} />}
          </div>
          <div className="text-micro text-[var(--color-text-muted)] mt-0.5">{kpi.label}</div>
        </div>
      ))}
    </div>
  );
}

// ── Revenue Trend ─────────────────────────────────────────────────────────────

function RevenueTrendView({ data }: { data: RevenueTrendPoint[] }) {
  if (data.length === 0) {
    return <QuantumEmptyState title="No revenue trend data" description="Revenue trend will populate as claims are processed." icon="chart" />;
  }

  const maxBilled = Math.max(...data.map(d => asNumberOrZero(d.gross_billed)), 1);

  return (
    <div className="bg-[var(--color-bg-panel)] border border-border-subtle chamfer-8 p-4">
      <div className="text-micro uppercase tracking-widest text-[var(--color-text-muted)] mb-4">Revenue Trend</div>
      <div className="space-y-2">
        {data.map((pt, i) => {
          const billedNum = typeof pt.gross_billed === 'number' && Number.isFinite(pt.gross_billed) ? pt.gross_billed : null;
          const collectedNum = typeof pt.collected === 'number' && Number.isFinite(pt.collected) ? pt.collected : null;
          const billed = billedNum ?? 0;
          const collected = collectedNum ?? 0;
          const collectionPctLabel = billedNum != null && collectedNum != null && billedNum > 0
            ? fmtPct((collectedNum / billedNum) * 100)
            : '—';
          return (
            <div key={i} className="flex items-center gap-3">
              <span className="text-micro font-mono text-[var(--color-text-muted)] w-16 text-right flex-shrink-0">{pt.period || '—'}</span>
              <div className="flex-1 space-y-0.5">
                <div className="flex items-center gap-2">
                  <div className="flex-1 h-2 bg-[var(--color-bg-base)]/[0.04] chamfer-4 overflow-hidden">
                    <div className="h-full bg-[var(--color-status-info)]/60 chamfer-4" style={{ width: `${(billed / maxBilled) * 100}%` }} />
                  </div>
                  <span className="text-micro text-[var(--color-text-muted)] w-20 text-right">{billedNum != null ? fmt$(billedNum) : '—'}</span>
                </div>
                <div className="flex items-center gap-2">
                  <div className="flex-1 h-2 bg-[var(--color-bg-base)]/[0.04] chamfer-4 overflow-hidden">
                    <div className="h-full bg-[var(--color-status-active)]/60 chamfer-4" style={{ width: `${(collected / maxBilled) * 100}%` }} />
                  </div>
                  <span className="text-micro text-[var(--color-text-muted)] w-20 text-right">{collectionPctLabel} coll.</span>
                </div>
              </div>
            </div>
          );
        })}
      </div>
      <div className="flex items-center gap-4 mt-3">
        <div className="flex items-center gap-1.5"><div className="w-3 h-2 bg-[var(--color-status-info)]/60 chamfer-4" /><span className="text-micro text-[var(--color-text-muted)]">Billed</span></div>
        <div className="flex items-center gap-1.5"><div className="w-3 h-2 bg-[var(--color-status-active)]/60 chamfer-4" /><span className="text-micro text-[var(--color-text-muted)]">Collected</span></div>
      </div>
    </div>
  );
}

// ── Payer Performance Table ───────────────────────────────────────────────────

function PayerPerformanceTable({ rows }: { rows: PayerRow[] }) {
  if (rows.length === 0) {
    return <QuantumEmptyState title="No payer data" description="Payer performance data will appear as claims are paid." icon="building" />;
  }

  return (
    <div className="bg-[var(--color-bg-panel)] border border-border-subtle chamfer-8 overflow-hidden">
      <table className="w-full text-left">
        <thead>
          <tr className="border-b border-border-subtle">
            {['Payer', 'Volume', 'Clean Rate', 'Denial Rate', 'Avg Days to Pay', 'Total Paid'].map(h => (
              <th key={h} className="px-4 py-3 text-micro uppercase tracking-widest text-[var(--color-text-muted)]">{h}</th>
            ))}
          </tr>
        </thead>
        <tbody>
          {rows.map((row, i) => {
            const cleanRate = typeof row.clean_claim_rate === 'number' && Number.isFinite(row.clean_claim_rate) ? row.clean_claim_rate : null;
            const cleanBarColor = cleanRate == null
              ? 'bg-[var(--color-bg-overlay)]/40'
              : cleanRate >= 90
                ? 'bg-[var(--color-status-active)]'
                : cleanRate >= 75
                  ? 'bg-yellow-500'
                  : 'bg-[var(--color-brand-red)]';
            const cleanRateForBar = Math.max(0, Math.min(100, cleanRate ?? 0));

            const denialRate = typeof row.denial_rate === 'number' && Number.isFinite(row.denial_rate) ? row.denial_rate : null;
            const denialTextColor = denialRate == null
              ? 'text-[var(--color-text-muted)]'
              : denialRate > 10
                ? 'text-[var(--color-brand-red)]'
                : denialRate > 5
                  ? 'text-yellow-400'
                  : 'text-[var(--color-status-active)]';

            return (
              <tr key={i} className="border-b border-border-subtle hover:bg-[var(--color-bg-base)]/[0.02]">
              <td className="px-4 py-3 text-sm font-semibold text-[var(--color-text-primary)]">{row.payer_name || '—'}</td>
              <td className="px-4 py-3 text-sm text-[var(--color-text-secondary)]">{row.volume ?? '—'}</td>
              <td className="px-4 py-3">
                <div className="flex items-center gap-2">
                  <div className="w-16 h-1.5 bg-[var(--color-bg-base)]/10  overflow-hidden">
                    <div
                      className={`h-full  ${cleanBarColor}`}
                      style={{ width: `${cleanRateForBar}%` }}
                    />
                  </div>
                  <span className="text-micro text-[var(--color-text-muted)]">{row.clean_claim_rate != null ? fmtPct(row.clean_claim_rate) : '—'}</span>
                </div>
              </td>
              <td className="px-4 py-3">
                <span className={`text-sm font-semibold ${denialTextColor}`}>
                  {row.denial_rate != null ? fmtPct(row.denial_rate) : '—'}
                </span>
              </td>
              <td className="px-4 py-3 text-sm text-[var(--color-text-secondary)]">{row.avg_days_to_pay != null ? `${row.avg_days_to_pay}d` : '—'}</td>
              <td className="px-4 py-3 text-sm font-mono text-[var(--color-text-secondary)]">{row.total_paid != null ? fmt$(row.total_paid) : '—'}</td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}

// ── Denial Heatmap ────────────────────────────────────────────────────────────

function DenialHeatmap({ denials }: { denials: DenialEntry[] }) {
  if (denials.length === 0) {
    return <QuantumEmptyState title="No denial data" description="Denial patterns will appear as claims are processed." icon="x-circle" />;
  }

  const topDenials = [...denials]
    .sort((a, b) => asNumberOrZero(b.count) - asNumberOrZero(a.count))
    .slice(0, 10);
  const max = Math.max(...topDenials.map(d => asNumberOrZero(d.count)), 1);

  return (
    <div className="bg-[var(--color-bg-panel)] border border-border-subtle chamfer-8 p-4">
      <div className="text-micro uppercase tracking-widest text-[var(--color-text-muted)] mb-4">Top Denial Reasons</div>
      <div className="space-y-2">
        {topDenials.map((d, i) => {
          const count = asNumberOrZero(d.count);
          return (
            <div key={i} className="flex items-center gap-3">
            <span className="text-micro font-mono text-[var(--color-text-muted)] w-14 text-right flex-shrink-0">{d.code || '—'}</span>
            <div className="flex-1 h-6 bg-[var(--color-bg-base)]/[0.04] chamfer-4 overflow-hidden relative">
              <div
                className="h-full bg-[var(--color-brand-red)]/40 chamfer-4 flex items-center px-2 transition-all"
                style={{ width: `${(count / max) * 100}%` }}
              >
                <span className="text-micro text-[var(--color-brand-red)] whitespace-nowrap overflow-hidden">{d.reason || d.payer || '—'}</span>
              </div>
            </div>
            <div className="text-right w-20 flex-shrink-0">
              <div className="text-micro font-bold text-[var(--color-brand-red)]">{count}</div>
              {d.amount != null && <div className="text-micro text-[var(--color-text-muted)]">{fmt$(d.amount)}</div>}
            </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}

// ── Revenue Leakage ───────────────────────────────────────────────────────────

function RevenueLeakageView({ data }: { data: RevenueLeakage | null }) {
  if (!data) return <QuantumEmptyState title="No leakage data" description="Revenue leakage analysis will appear here." icon="alert" />;

  const totalLeakage = typeof data.total_leakage === 'number' && Number.isFinite(data.total_leakage) ? data.total_leakage : null;

  return (
    <div className="space-y-4">
      <div className="bg-red-900/20 border border-[var(--color-brand-red)]/30 chamfer-8 p-4">
        <div className="text-sm text-[var(--color-text-muted)] mb-1">Estimated Total Revenue Leakage</div>
        <div className="text-3xl font-black text-[var(--color-brand-red)]">{totalLeakage != null ? fmt$(totalLeakage) : '—'}</div>
      </div>
      {(data.categories || []).length > 0 && (
        <div className="bg-[var(--color-bg-panel)] border border-border-subtle chamfer-8 overflow-hidden">
          <table className="w-full text-left">
            <thead>
              <tr className="border-b border-border-subtle">
                {['Category', 'Count', 'Est. Amount'].map(h => (
                  <th key={h} className="px-4 py-3 text-micro uppercase tracking-widest text-[var(--color-text-muted)]">{h}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {(data.categories || []).map((cat, i) => (
                <tr key={i} className="border-b border-border-subtle hover:bg-[var(--color-bg-base)]/[0.02]">
                  <td className="px-4 py-3 text-sm font-semibold text-[var(--color-text-primary)]">{cat.label}</td>
                  <td className="px-4 py-3 text-sm text-[var(--color-text-secondary)]">{cat.count}</td>
                  <td className="px-4 py-3 text-sm font-mono text-[var(--color-brand-red)]">{fmt$(cat.amount)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}

// ── Fraud Anomalies ───────────────────────────────────────────────────────────

function FraudAnomaliesView({ anomalies }: { anomalies: FraudAnomaly[] }) {
  if (anomalies.length === 0) {
    return <QuantumEmptyState title="No fraud anomalies detected" description="Claims are continuously monitored for unusual billing patterns." icon="shield" />;
  }

  return (
    <div className="bg-[var(--color-bg-panel)] border border-border-subtle chamfer-8 overflow-hidden">
      <table className="w-full text-left">
        <thead>
          <tr className="border-b border-border-subtle">
            {['Claim ID', 'Type', 'Risk Score', 'Detail', 'Flagged'].map(h => (
              <th key={h} className="px-4 py-3 text-micro uppercase tracking-widest text-[var(--color-text-muted)]">{h}</th>
            ))}
          </tr>
        </thead>
        <tbody>
          {anomalies.map((a, i) => (
            <tr key={i} className="border-b border-border-subtle hover:bg-[var(--color-bg-base)]/[0.02]">
              <td className="px-4 py-3 text-xs font-mono text-[var(--color-text-muted)]">{a.claim_id?.slice(0, 12) || '—'}</td>
              <td className="px-4 py-3 text-sm text-[var(--color-text-secondary)]">{a.type || '—'}</td>
              <td className="px-4 py-3">
                {a.score != null ? (
                  <div className="flex items-center gap-2">
                    <div className="w-16 h-1.5 bg-[var(--color-bg-base)]/10  overflow-hidden">
                      <div className={`h-full  ${a.score >= 80 ? 'bg-[var(--color-brand-red)]' : a.score >= 50 ? 'bg-[var(--q-orange)]' : 'bg-yellow-500'}`}
                           style={{ width: `${a.score}%` }} />
                    </div>
                    <span className="text-micro font-bold text-[var(--color-brand-red)]">{a.score}</span>
                  </div>
                ) : '—'}
              </td>
              <td className="px-4 py-3 text-sm text-[var(--color-text-muted)] max-w-xs truncate">{a.detail || '—'}</td>
              <td className="px-4 py-3 text-xs font-mono text-[var(--color-text-muted)]">
                {a.flagged_at ? new Date(a.flagged_at).toLocaleString() : '—'}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

// ── Page ──────────────────────────────────────────────────────────────────────

type ActiveView = 'overview' | 'payers' | 'denials' | 'leakage' | 'fraud' | 'alerts';

export default function BillingOpsPage() {
  const [activeView, setActiveView] = useState<ActiveView>('overview');
  const [kpis, setKPIs] = useState<BillingKPI[]>([]);
  const [revenueTrend, setRevenueTrend] = useState<RevenueTrendPoint[]>([]);
  const [payerPerf, setPayerPerf] = useState<PayerRow[]>([]);
  const [denials, setDenials] = useState<DenialEntry[]>([]);
  const [leakage, setLeakage] = useState<RevenueLeakage | null>(null);
  const [fraud, setFraud] = useState<FraudAnomaly[]>([]);
  const [alerts, setAlerts] = useState<BillingAlert[]>([]);
  const [loading, setLoading] = useState(true);
  const [loadError, setLoadError] = useState<string | null>(null);
  const [batchSubmitting, setBatchSubmitting] = useState(false);

  const loadData = useCallback(async () => {
    setLoading(true);
    setLoadError(null);
    let anyFailed = false;
    try {
      const [kpiData, trendData, healthData, alertData] = await Promise.all([
        getBillingKPIs().catch((err) => { anyFailed = true; console.error('[BillingOps] KPIs failed:', err); return null; }),
        getRevenueTrend().catch((err) => { anyFailed = true; console.error('[BillingOps] trend failed:', err); return []; }),
        getBillingHealth().catch((err) => { anyFailed = true; console.error('[BillingOps] health failed:', err); return null; }),
        getBillingAlerts().catch((err) => { anyFailed = true; console.error('[BillingOps] alerts failed:', err); return []; }),
      ]);
      if (anyFailed) setLoadError('Some billing data failed to load. Displayed metrics may be incomplete.');

      const rawKPIs = kpiData?.kpis || kpiData || {};
      const denialRateForColor = typeof rawKPIs.denial_rate === 'number' && Number.isFinite(rawKPIs.denial_rate)
        ? rawKPIs.denial_rate
        : null;
      const healthScoreForColor = typeof healthData?.score === 'number' && Number.isFinite(healthData.score)
        ? healthData.score
        : null;
      setKPIs([
        { label: 'Clean Claim Rate', value: rawKPIs.clean_claim_rate != null ? fmtPct(rawKPIs.clean_claim_rate) : '—', color: 'text-[var(--color-status-active)]', trend: rawKPIs.clean_claim_trend },
        { label: 'Collection Rate', value: rawKPIs.collection_rate != null ? fmtPct(rawKPIs.collection_rate) : '—', color: 'text-[var(--color-status-info)]', trend: rawKPIs.collection_trend },
        { label: 'Avg Days in AR', value: rawKPIs.avg_days_ar != null ? `${rawKPIs.avg_days_ar}d` : '—', color: 'text-[var(--color-text-primary)]' },
        { label: 'Denial Rate', value: rawKPIs.denial_rate != null ? fmtPct(rawKPIs.denial_rate) : '—', color: denialRateForColor != null && denialRateForColor > 10 ? 'text-[var(--color-brand-red)]' : 'text-[var(--color-text-primary)]' },
        { label: 'Total Billed (MTD)', value: rawKPIs.total_billed_mtd != null ? fmt$(rawKPIs.total_billed_mtd) : '—' },
        { label: 'Total Collected (MTD)', value: rawKPIs.total_collected_mtd != null ? fmt$(rawKPIs.total_collected_mtd) : '—', color: 'text-[var(--color-status-active)]' },
        { label: 'Open AR Balance', value: rawKPIs.open_ar != null ? fmt$(rawKPIs.open_ar) : '—', color: 'text-yellow-400' },
        { label: 'Billing Health Score', value: healthData?.score != null ? `${healthData.score}/100` : '—', color: healthScoreForColor != null ? (healthScoreForColor >= 80 ? 'text-[var(--color-status-active)]' : 'text-yellow-400') : 'text-[var(--color-text-primary)]' },
      ]);

      setRevenueTrend(Array.isArray(trendData) ? trendData : trendData?.trend || []);
      setAlerts(Array.isArray(alertData) ? alertData : alertData?.alerts || []);
    } finally {
      setLoading(false);
    }
  }, []);

  const loadViewData = useCallback(async (view: ActiveView) => {
    if (view === 'payers') {
      const data = await getPayerPerformance().catch(() => []);
      setPayerPerf(Array.isArray(data) ? data : data?.payers || []);
    }
    if (view === 'denials') {
      const data = await getDenialHeatmap().catch(() => []);
      setDenials(Array.isArray(data) ? data : data?.denials || []);
    }
    if (view === 'leakage') {
      const data = await getRevenueLeakage().catch(() => null);
      setLeakage(data);
    }
    if (view === 'fraud') {
      const data = await getFraudAnomalies().catch(() => []);
      setFraud(Array.isArray(data) ? data : data?.anomalies || []);
    }
  }, []);

  useEffect(() => { loadData(); }, [loadData]);
  useEffect(() => { loadViewData(activeView); }, [activeView, loadViewData]);

  async function handleBatchResubmit() {
    setBatchSubmitting(true);
    try {
      await batchResubmitClaims({ filter: 'DENIED' });
      await loadData();
    } finally {
      setBatchSubmitting(false);
    }
  }

  const criticalAlerts = alerts.filter(a => a.severity === 'CRITICAL' || a.severity === 'HIGH');

  return (
    <ModuleDashboardShell
        title="Billing Command Center"
        subtitle="KPIs · Payer performance · Denial intelligence · Revenue leakage · Fraud detection"
        accentColor="var(--q-orange)"
        headerActions={
          <div className="flex items-center gap-2">
            {criticalAlerts.length > 0 && (
              <div className="flex items-center gap-1.5 bg-red-900/30 border border-[var(--color-brand-red)]/40 chamfer-4 px-3 py-1.5">
                <div className="w-1.5 h-1.5 bg-red-400 animate-pulse" />
                <span className="text-micro font-bold text-[var(--color-brand-red)]">{criticalAlerts.length} critical alert{criticalAlerts.length > 1 ? 's' : ''}</span>
              </div>
            )}
            <button
              onClick={handleBatchResubmit}
              disabled={batchSubmitting}
              className="quantum-btn-sm disabled:opacity-50"
            >
              {batchSubmitting ? 'Resubmitting…' : '↺ Batch Resubmit Denials'}
            </button>
          </div>
        }
        toolbar={
          <div className="flex items-center gap-1">
          {([
            { id: 'overview', label: 'Overview' },
            { id: 'payers', label: 'Payer Intelligence' },
            { id: 'denials', label: 'Denial Heatmap' },
            { id: 'leakage', label: 'Revenue Leakage' },
            { id: 'fraud', label: 'Fraud Detection' },
            { id: 'alerts', label: `Alerts${alerts.length > 0 ? ` (${alerts.length})` : ''}` },
          ] as const).map(t => (
            <button
              key={t.id}
              onClick={() => setActiveView(t.id)}
              className={`px-4 py-2 text-micro font-label font-bold border-b-2 transition-colors ${
                activeView === t.id ? 'border-[var(--q-orange)] text-[var(--q-orange)]' : 'border-transparent text-[var(--color-text-muted)] hover:text-[var(--color-text-secondary)]'
              }`}
            >
              {t.label}
            </button>
          ))}
        </div>
        }
      >
        {loadError && (
          <div className="mb-4 px-4 py-3 bg-red-900/20 border border-[var(--color-brand-red)]/30 text-[var(--color-brand-red)] text-sm font-medium chamfer-4">
            ⚠ {loadError}
          </div>
        )}
      {/* Content */}
      <div className="flex-1 p-1">
        {loading ? (
          <QuantumTableSkeleton rows={4} />
        ) : activeView === 'overview' ? (
          <div className="space-y-5">
            <div className="grid grid-cols-4 gap-3">
              {kpis.slice(0, 4).map(kpi => (
                <div key={kpi.label} className="bg-[var(--color-bg-panel)] border border-border-subtle chamfer-8 px-4 py-3">
                  <div className={`text-2xl font-black ${kpi.color || 'text-[var(--color-text-primary)]'}`}>
                    {kpi.value}
                    {kpi.trend != null && <TrendBadge trend={kpi.trend} />}
                  </div>
                  <div className="text-micro text-[var(--color-text-muted)] mt-0.5">{kpi.label}</div>
                </div>
              ))}
            </div>
            <div className="grid grid-cols-4 gap-3">
              {kpis.slice(4).map(kpi => (
                <div key={kpi.label} className="bg-[var(--color-bg-panel)] border border-border-subtle chamfer-8 px-4 py-3">
                  <div className={`text-2xl font-black ${kpi.color || 'text-[var(--color-text-primary)]'}`}>
                    {kpi.value}
                    {kpi.trend != null && <TrendBadge trend={kpi.trend} />}
                  </div>
                  <div className="text-micro text-[var(--color-text-muted)] mt-0.5">{kpi.label}</div>
                </div>
              ))}
            </div>
            <RevenueTrendView data={revenueTrend} />
          </div>
        ) : activeView === 'payers' ? (
          <div className="space-y-5">
            <KPIBar kpis={kpis.slice(0, 4)} />
            <PayerPerformanceTable rows={payerPerf} />
          </div>
        ) : activeView === 'denials' ? (
          <DenialHeatmap denials={denials} />
        ) : activeView === 'leakage' ? (
          <RevenueLeakageView data={leakage} />
        ) : activeView === 'fraud' ? (
          <FraudAnomaliesView anomalies={fraud} />
        ) : (
          /* Alerts */
          alerts.length === 0 ? (
            <QuantumEmptyState title="No billing alerts" description="Billing alerts will appear here when thresholds are exceeded." icon="bell" />
          ) : (
            <div className="space-y-3">
              {alerts.map((alert, i) => (
                <div key={alert.id || i} className={`chamfer-8 border px-4 py-3 flex items-start gap-3 ${
                  alert.severity === 'CRITICAL' ? 'bg-red-900/20 border-[var(--color-brand-red)]/30' :
                  alert.severity === 'HIGH' ? 'bg-[rgba(255,106,0,0.2)] border-orange-500/30' :
                  alert.severity === 'MEDIUM' ? 'bg-yellow-900/20 border-yellow-500/30' :
                  'bg-[var(--color-bg-panel)] border-border-subtle'
                }`}>
                  <SeverityBadge severity={alert.severity || 'INFO'} />
                  <div className="flex-1 min-w-0">
                    <div className="text-sm text-[var(--color-text-primary)]">{alert.message || '—'}</div>
                    {alert.created_at && (
                      <div className="text-micro text-[var(--color-text-muted)] mt-0.5">{new Date(alert.created_at).toLocaleString()}</div>
                    )}
                  </div>
                </div>
              ))}
            </div>
          )
        )}
      </div>
    </ModuleDashboardShell>
  );
}
