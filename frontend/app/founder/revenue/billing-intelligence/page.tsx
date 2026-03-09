'use client';

import { useEffect, useState } from 'react';
import { PlateCard } from '@/components/ui/PlateCard';
import {
  getBillingARAgingReport,
  getBillingExecutiveSummary,
  getBillingKPIs,
  getClaimThroughput,
  getDenialHeatmap,
  getPayerPerformance,
} from '@/services/api';

/* ─── Types ────────────────────────────────────────────────────────── */

interface RevenueMetric { label: string; value: string; color: string; dir: string }
interface DenialReason { reason: string; count: number; pct: number }
interface PayerRow { name: string; volume: number; avgDays: number; denialRate: string; netCollection: string }
interface ArBucket { bucket: string; amount: number; pct: number; color: string }
interface ProcCode { code: string; desc: string; volume: number; accuracy: number; error: number }
interface ProdMetric { label: string; value: string; sub: string; color: string }

function MetricRow({
  label,
  value,
  color,
  dir,
}: {
  label: string;
  value: string;
  color: string;
  dir: string;
}) {
  return (
    <div
      style={{
        background: 'var(--color-bg-panel-raised)',
        border: '1px solid var(--color-border-subtle)',
        clipPath: 'polygon(0 0, calc(100% - 6px) 0, 100% 6px, 100% 100%, 0 100%)',
        padding: '12px 14px',
        display: 'flex',
        justifyContent: 'space-between',
        alignItems: 'center',
      }}
    >
      <span
        style={{
          fontFamily: 'var(--font-label)',
          fontSize: 'var(--text-label)',
          fontWeight: 600,
          letterSpacing: 'var(--tracking-label)',
          textTransform: 'uppercase',
          color: 'var(--color-text-muted)',
        }}
      >
        {label}
      </span>
      <span
        style={{
          fontFamily: 'var(--font-mono)',
          fontSize: 'var(--text-body-lg)',
          fontWeight: 700,
          color,
        }}
      >
        {dir && (
          <span style={{ fontSize: 10, marginRight: 4, opacity: 0.8 }}>{dir}</span>
        )}
        {value}
      </span>
    </div>
  );
}

/* ─── Page ──────────────────────────────────────────────────────────── */

export default function BillingIntelligencePage() {
  const [revBars, setRevBars] = useState<number[]>([]);
  const [revenueMetrics, setRevenueMetrics] = useState<RevenueMetric[]>([]);
  const [denialReasons, setDenialReasons] = useState<DenialReason[]>([]);
  const [payers, setPayers] = useState<PayerRow[]>([]);
  const [arAging, setArAging] = useState<ArBucket[]>([]);
  const [totalAr, setTotalAr] = useState<number>(0);
  const [procCodes, setProcCodes] = useState<ProcCode[]>([]);
  const [productivity, setProductivity] = useState<ProdMetric[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    setLoading(true);

    const safe = async <T,>(fn: () => Promise<T>): Promise<T | null> => {
      try {
        return await fn();
      } catch { return null; }
    };

    Promise.all([
      safe(() => getBillingExecutiveSummary()),
      safe(() => getDenialHeatmap()),
      safe(() => getPayerPerformance()),
      safe(() => getBillingARAgingReport()),
      safe(() => getClaimThroughput()),
      safe(() => getBillingKPIs()),
    ]).then(([exec, denial, payerData, arData, throughput, kpis]) => {
      // Revenue metrics from executive-summary
      if (exec) {
        const fmtPct = (v: number | undefined) => v != null ? `${v >= 0 ? '+' : ''}${v.toFixed(1)}%` : '—';
        const fmtDollars = (cents: number | undefined) => {
          if (cents == null) return '—';
          const d = cents / 100;
          return d >= 1_000_000 ? `$${(d / 1_000_000).toFixed(2)}M` : d >= 1_000 ? `$${(d / 1_000).toFixed(0)}K` : `$${d.toFixed(0)}`;
        };
        setRevenueMetrics([
          { label: 'MoM Growth', value: fmtPct(exec.mom_growth_pct), color: 'var(--color-status-active)', dir: exec.mom_growth_pct != null && exec.mom_growth_pct >= 0 ? '▲' : '▼' },
          { label: 'QoQ Growth', value: fmtPct(exec.qoq_growth_pct), color: 'var(--color-status-active)', dir: exec.qoq_growth_pct != null && exec.qoq_growth_pct >= 0 ? '▲' : '▼' },
          { label: 'YoY Growth', value: fmtPct(exec.yoy_growth_pct), color: 'var(--color-status-active)', dir: exec.yoy_growth_pct != null && exec.yoy_growth_pct >= 0 ? '▲' : '▼' },
          { label: 'Run Rate (ARR)', value: fmtDollars(exec.arr_cents), color: '#FF4D00', dir: '' },
        ]);
        if (Array.isArray(exec.monthly_revenue_cents) && exec.monthly_revenue_cents.length > 0) {
          const maxVal = Math.max(...exec.monthly_revenue_cents, 1);
          setRevBars(exec.monthly_revenue_cents.map((v: number) => Math.round((v / maxVal) * 100)));
        }
      }

      // Denial heatmap
      if (Array.isArray((denial as { heatmap?: Array<{ reason?: string; reason_code?: string; count?: number; percentage?: number }> } | null)?.heatmap)) {
        setDenialReasons((denial as { heatmap: Array<{ reason?: string; reason_code?: string; count?: number; percentage?: number }> }).heatmap.map((d) => ({
          reason: d.reason || d.reason_code || 'Unknown',
          count: d.count ?? (() => { throw new Error('Unsafe silent fallback. Dependency missing.'); })(),
          pct: Math.round(d.percentage ?? (() => { throw new Error('Unsafe silent fallback. Dependency missing.'); })()),
        })));
      }

      // Payer performance
      const payerRows = (payerData as { payers?: Array<{ payer_name: string; submitted_count?: number; avg_days_to_payment?: number; denial_rate?: number; net_collection_rate?: number }> } | null)?.payers;
      if (Array.isArray(payerRows)) {
        setPayers(payerRows.map((p) => ({
          name: p.payer_name,
          volume: p.submitted_count ?? (() => { throw new Error('Unsafe silent fallback. Dependency missing.'); })(),
          avgDays: p.avg_days_to_payment ?? (() => { throw new Error('Unsafe silent fallback. Dependency missing.'); })(),
          denialRate: p.denial_rate != null ? `${p.denial_rate.toFixed(1)}%` : '—',
          netCollection: p.net_collection_rate != null ? `${p.net_collection_rate.toFixed(1)}%` : '—',
        })));
      }

      // AR aging
      if (arData?.buckets && Array.isArray(arData.buckets)) {
        const totalCents = arData.total_ar_cents ?? arData.buckets.reduce((s, b) => s + b.total_cents, 0);
        setTotalAr(totalCents);
        const colors = ['var(--color-status-active)', 'var(--color-status-active)', 'var(--color-status-warning)', 'var(--color-brand-orange-bright)', 'var(--color-brand-red)'];
        setArAging(arData.buckets.map((b, i) => ({
          bucket: b.label,
          amount: b.total_cents,
          pct: totalCents > 0 ? Math.round((b.total_cents / totalCents) * 100) : 0,
          color: colors[Math.min(i, colors.length - 1)],
        })));
      }

      // Coding accuracy / throughput
      if (throughput?.throughput && Array.isArray(throughput.throughput)) {
        setProcCodes(throughput.throughput.map((t: any) => ({
          code: t.code,
          desc: t.description,
          volume: t.volume,
          accuracy: t.accuracy_pct ?? (() => { throw new Error('Unsafe silent fallback. Dependency missing.'); })(),
          error: t.error_pct ?? (() => { throw new Error('Unsafe silent fallback. Dependency missing.'); })(),
        })));
      }

      // Productivity / KPIs
      if (kpis) {
        setProductivity([
          { label: 'Claims / Day', value: kpis.claims_per_day != null ? kpis.claims_per_day.toFixed(1) : '—', sub: 'avg last 30d', color: 'var(--color-system-billing)' },
          { label: 'Clean Claim %', value: kpis.clean_claim_rate != null ? `${kpis.clean_claim_rate.toFixed(1)}%` : '—', sub: '', color: 'var(--color-status-active)' },
          { label: 'Denial Rate', value: kpis.denial_rate != null ? `${kpis.denial_rate.toFixed(1)}%` : '—', sub: '', color: 'var(--color-status-warning)' },
          { label: 'Collection Rate', value: kpis.collection_rate != null ? `${kpis.collection_rate.toFixed(1)}%` : '—', sub: '', color: 'var(--color-status-active)' },
        ]);
      }

      setLoading(false);
    }).catch(() => {
      setError('Failed to load billing intelligence data');
      setLoading(false);
    });
  }, []);

  if (loading) {
    return (
      <div style={{ padding: '20px 24px', minHeight: '100%' }}>
        <div className="space-y-4">
          {[1, 2, 3].map(i => (
            <div key={i} className="h-32 bg-white/5 animate-pulse rounded" />
          ))}
        </div>
      </div>
    );
  }

  return (
    <div style={{ padding: '20px 24px', minHeight: '100%' }}>
      {error && (
        <div style={{ padding: '10px 14px', marginBottom: 16, border: '1px solid rgba(245,158,11,0.3)', background: 'rgba(245,158,11,0.1)', color: '#F59E0B', fontSize: 11, fontWeight: 700, letterSpacing: '0.1em', textTransform: 'uppercase' as const }}>
          {error}
        </div>
      )}
      {/* Page header */}
      <div
        className="hud-rail"
        style={{
          paddingBottom: 14,
          marginBottom: 24,
          borderBottom: '1px solid var(--color-border-default)',
        }}
      >
        <div
          style={{
            fontFamily: 'var(--font-label)',
            fontSize: 'var(--text-micro)',
            fontWeight: 600,
            letterSpacing: 'var(--tracking-micro)',
            textTransform: 'uppercase',
            color: 'rgba(34, 211, 238, 0.7)',
            marginBottom: 4,
          }}
        >
          2 · Revenue
        </div>
        <h1
          style={{
            fontFamily: 'var(--font-sans)',
            fontSize: 'var(--text-h1)',
            fontWeight: 900,
            letterSpacing: '0.04em',
            textTransform: 'uppercase',
            color: 'var(--color-text-primary)',
            lineHeight: 'var(--leading-tight)',
          }}
        >
          Billing Intelligence
        </h1>
        <p
          style={{
            fontSize: 'var(--text-body)',
            color: 'var(--color-text-muted)',
            marginTop: 4,
          }}
        >
          Tenant profitability · Module revenue breakdown · Revenue leakage detection
        </p>
      </div>

      <div style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>

        {/* ── 1. Revenue Velocity ──────────────────────────────────────── */}
        <PlateCard
          accent="billing"
          header="Revenue Velocity"
          headerRight={
            <span
              style={{
                fontFamily: 'var(--font-mono)',
                fontSize: 10,
                color: 'var(--color-status-active)',
                letterSpacing: '0.05em',
              }}
            >
              ▲ TRENDING UP
            </span>
          }
        >
          <div
            style={{
              height: 120,
              background: 'var(--color-bg-overlay)',
              border: '1px solid var(--color-border-subtle)',
              clipPath: 'polygon(0 0, calc(100% - 8px) 0, 100% 8px, 100% 100%, 0 100%)',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              marginBottom: 16,
              position: 'relative',
              overflow: 'hidden',
            }}
          >
            <div
              style={{
                position: 'absolute',
                inset: 0,
                display: 'flex',
                alignItems: 'flex-end',
                gap: 3,
                padding: '12px 16px 0',
                opacity: 0.35,
              }}
            >
              {(revBars.length ? revBars : []).map((h, i) => (
                <div
                  key={i}
                  style={{
                    flex: 1,
                    height: `${h}%`,
                    background: 'var(--color-system-billing)',
                    clipPath: 'polygon(0 0, calc(100% - 2px) 0, 100% 2px, 100% 100%, 0 100%)',
                  }}
                />
              ))}
            </div>
            <span
              style={{
                fontFamily: 'var(--font-label)',
                fontSize: 'var(--text-micro)',
                fontWeight: 600,
                letterSpacing: 'var(--tracking-micro)',
                textTransform: 'uppercase',
                color: 'var(--color-text-muted)',
                zIndex: 1,
              }}
            >
              Revenue Trend — Last 12 Months
            </span>
          </div>

          <div
            style={{
              display: 'grid',
              gridTemplateColumns: 'repeat(2, 1fr)',
              gap: 8,
            }}
          >
            {revenueMetrics.map((m) => (
              <MetricRow key={m.label} {...m} />
            ))}
          </div>
        </PlateCard>

        {/* ── 2. Denial Intelligence ───────────────────────────────────── */}
        <PlateCard
          accent="red"
          header="Denial Intelligence"
          headerRight={
            <span style={{ fontSize: 11, color: 'var(--color-text-muted)' }}>
              {denialReasons.length} reason categories
            </span>
          }
        >
          <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
            {denialReasons.map((d) => (
              <div key={d.reason}>
                <div
                  style={{
                    display: 'flex',
                    justifyContent: 'space-between',
                    marginBottom: 4,
                  }}
                >
                  <span
                    style={{
                      fontSize: 'var(--text-body)',
                      color: 'var(--color-text-secondary)',
                    }}
                  >
                    {d.reason}
                  </span>
                  <div style={{ display: 'flex', gap: 10 }}>
                    <span
                      style={{
                        fontFamily: 'var(--font-mono)',
                        fontSize: 11,
                        color: 'var(--color-text-muted)',
                      }}
                    >
                      {d.count} claims
                    </span>
                    <span
                      style={{
                        fontFamily: 'var(--font-mono)',
                        fontSize: 11,
                        fontWeight: 700,
                        color: 'var(--color-brand-red)',
                        minWidth: 32,
                        textAlign: 'right',
                      }}
                    >
                      {d.pct}%
                    </span>
                  </div>
                </div>
                <div
                  style={{
                    height: 6,
                    background: 'var(--color-bg-overlay)',
                    clipPath: 'polygon(0 0, calc(100% - 3px) 0, 100% 3px, 100% 100%, 0 100%)',
                    overflow: 'hidden',
                  }}
                >
                  <div
                    style={{
                      height: '100%',
                      width: `${d.pct}%`,
                      background: `linear-gradient(90deg, var(--color-brand-red-dim), var(--color-brand-red))`,
                      transition: 'width 0.4s ease',
                    }}
                  />
                </div>
              </div>
            ))}
          </div>
        </PlateCard>

        {/* ── 3. Payer Intelligence ────────────────────────────────────── */}
        <PlateCard
          accent="billing"
          header="Payer Intelligence"
          headerRight={
            <span style={{ fontSize: 11, color: 'var(--color-text-muted)' }}>
              {payers.reduce((s, p) => s + p.volume, 0).toLocaleString()} total claims
            </span>
          }
        >
          <div style={{ overflowX: 'auto' }}>
            <table
              style={{
                width: '100%',
                borderCollapse: 'collapse',
                fontSize: 'var(--text-body)',
              }}
            >
              <thead>
                <tr>
                  {['Payer', 'Volume', 'Avg Days', 'Denial Rate', 'Net Collection'].map((h) => (
                    <th
                      key={h}
                      style={{
                        padding: '8px 10px',
                        textAlign: h === 'Payer' ? 'left' : 'right',
                        fontFamily: 'var(--font-label)',
                        fontSize: 'var(--text-micro)',
                        fontWeight: 600,
                        letterSpacing: 'var(--tracking-micro)',
                        textTransform: 'uppercase',
                        color: 'var(--color-text-muted)',
                        borderBottom: '1px solid var(--color-border-default)',
                      }}
                    >
                      {h}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {payers.map((p, i) => (
                  <tr
                    key={p.name}
                    style={{
                      background:
                        i % 2 === 0 ? 'transparent' : 'rgba(255,255,255,0.015)',
                      borderBottom: '1px solid var(--color-border-subtle)',
                    }}
                  >
                    <td
                      style={{
                        padding: '9px 10px',
                        fontWeight: 600,
                        color: 'var(--color-text-primary)',
                      }}
                    >
                      {p.name}
                    </td>
                    <td
                      style={{
                        padding: '9px 10px',
                        textAlign: 'right',
                        fontFamily: 'var(--font-mono)',
                        color: 'var(--color-text-secondary)',
                      }}
                    >
                      {p.volume.toLocaleString()}
                    </td>
                    <td
                      style={{
                        padding: '9px 10px',
                        textAlign: 'right',
                        fontFamily: 'var(--font-mono)',
                        color:
                          p.avgDays > 30
                            ? 'var(--color-status-warning)'
                            : 'var(--color-text-secondary)',
                      }}
                    >
                      {p.avgDays}d
                    </td>
                    <td
                      style={{
                        padding: '9px 10px',
                        textAlign: 'right',
                        fontFamily: 'var(--font-mono)',
                        color:
                          p.denialRate === '—'
                            ? 'var(--color-text-muted)'
                            : parseFloat(p.denialRate) > 10
                            ? 'var(--color-brand-red)'
                            : parseFloat(p.denialRate) > 6
                            ? 'var(--color-status-warning)'
                            : 'var(--color-status-active)',
                        fontWeight: 700,
                      }}
                    >
                      {p.denialRate}
                    </td>
                    <td
                      style={{
                        padding: '9px 10px',
                        textAlign: 'right',
                        fontFamily: 'var(--font-mono)',
                        color:
                          parseFloat(p.netCollection) >= 95
                            ? 'var(--color-status-active)'
                            : parseFloat(p.netCollection) >= 85
                            ? 'var(--color-system-billing)'
                            : 'var(--color-status-warning)',
                        fontWeight: 700,
                      }}
                    >
                      {p.netCollection}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </PlateCard>

        {/* ── 4. AR Risk Analysis ──────────────────────────────────────── */}
        <PlateCard
          accent="warning"
          header="AR Risk Analysis"
          headerRight={
            <span
              style={{
                fontFamily: 'var(--font-mono)',
                fontSize: 11,
                color: 'var(--color-text-muted)',
              }}
            >
              Total AR:{' '}
              <span style={{ color: 'var(--color-text-primary)', fontWeight: 700 }}>
                ${(totalAr / 100).toLocaleString(undefined, { maximumFractionDigits: 0 })}
              </span>
            </span>
          }
        >
          <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
            {arAging.map((bucket) => (
              <div key={bucket.bucket}>
                <div
                  style={{
                    display: 'flex',
                    justifyContent: 'space-between',
                    marginBottom: 5,
                  }}
                >
                  <span
                    style={{
                      fontFamily: 'var(--font-label)',
                      fontSize: 'var(--text-label)',
                      fontWeight: 600,
                      letterSpacing: 'var(--tracking-label)',
                      textTransform: 'uppercase',
                      color: 'var(--color-text-secondary)',
                    }}
                  >
                    {bucket.bucket}
                  </span>
                  <div style={{ display: 'flex', gap: 12, alignItems: 'center' }}>
                    <span
                      style={{
                        fontFamily: 'var(--font-mono)',
                        fontSize: 11,
                        color: 'var(--color-text-muted)',
                      }}
                    >
                      ${bucket.amount.toLocaleString()}
                    </span>
                    <span
                      style={{
                        fontFamily: 'var(--font-mono)',
                        fontSize: 11,
                        fontWeight: 700,
                        color: bucket.color,
                        minWidth: 32,
                        textAlign: 'right',
                      }}
                    >
                      {bucket.pct}%
                    </span>
                  </div>
                </div>
                <div
                  style={{
                    height: 8,
                    background: 'var(--color-bg-overlay)',
                    clipPath: 'polygon(0 0, calc(100% - 4px) 0, 100% 4px, 100% 100%, 0 100%)',
                    overflow: 'hidden',
                  }}
                >
                  <div
                    style={{
                      height: '100%',
                      width: `${bucket.pct}%`,
                      background: bucket.color,
                      opacity: 0.85,
                    }}
                  />
                </div>
              </div>
            ))}
          </div>
        </PlateCard>

        {/* ── 5. Coding Accuracy ───────────────────────────────────────── */}
        <PlateCard
          accent="compliance"
          header="Coding Accuracy"
          headerRight={
            <span
              style={{
                fontFamily: 'var(--font-mono)',
                fontSize: 11,
                color: 'var(--color-status-active)',
              }}
            >
              {procCodes.length > 0 ? `${procCodes.length} procedure codes` : '—'}
            </span>
          }
        >
          <div style={{ overflowX: 'auto' }}>
            <table
              style={{
                width: '100%',
                borderCollapse: 'collapse',
                fontSize: 'var(--text-body)',
              }}
            >
              <thead>
                <tr>
                  {['Code', 'Description', 'Volume', 'Accuracy', 'Error Rate'].map((h) => (
                    <th
                      key={h}
                      style={{
                        padding: '8px 10px',
                        textAlign: h === 'Code' || h === 'Description' ? 'left' : 'right',
                        fontFamily: 'var(--font-label)',
                        fontSize: 'var(--text-micro)',
                        fontWeight: 600,
                        letterSpacing: 'var(--tracking-micro)',
                        textTransform: 'uppercase',
                        color: 'var(--color-text-muted)',
                        borderBottom: '1px solid var(--color-border-default)',
                      }}
                    >
                      {h}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {procCodes.map((row, i) => (
                  <tr
                    key={row.code}
                    style={{
                      background:
                        i % 2 === 0 ? 'transparent' : 'rgba(255,255,255,0.015)',
                      borderBottom: '1px solid var(--color-border-subtle)',
                    }}
                  >
                    <td
                      style={{
                        padding: '9px 10px',
                        fontFamily: 'var(--font-mono)',
                        fontSize: 12,
                        fontWeight: 700,
                        color: 'var(--color-system-compliance)',
                      }}
                    >
                      {row.code}
                    </td>
                    <td
                      style={{
                        padding: '9px 10px',
                        color: 'var(--color-text-secondary)',
                        fontSize: 12,
                      }}
                    >
                      {row.desc}
                    </td>
                    <td
                      style={{
                        padding: '9px 10px',
                        textAlign: 'right',
                        fontFamily: 'var(--font-mono)',
                        color: 'var(--color-text-secondary)',
                      }}
                    >
                      {row.volume}
                    </td>
                    <td
                      style={{
                        padding: '9px 10px',
                        textAlign: 'right',
                        fontFamily: 'var(--font-mono)',
                        fontWeight: 700,
                        color:
                          row.accuracy >= 97
                            ? 'var(--color-status-active)'
                            : row.accuracy >= 94
                            ? 'var(--color-status-warning)'
                            : 'var(--color-brand-red)',
                      }}
                    >
                      {row.accuracy}%
                    </td>
                    <td
                      style={{
                        padding: '9px 10px',
                        textAlign: 'right',
                        fontFamily: 'var(--font-mono)',
                        fontWeight: 700,
                        color:
                          row.error < 3
                            ? 'var(--color-text-muted)'
                            : row.error < 6
                            ? 'var(--color-status-warning)'
                            : 'var(--color-brand-red)',
                      }}
                    >
                      {row.error}%
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </PlateCard>

        {/* ── 6. Productivity Metrics ──────────────────────────────────── */}
        <PlateCard
          accent="orange"
          header="Productivity Metrics"
          headerRight={
            <span
              style={{
                fontFamily: 'var(--font-label)',
                fontSize: 'var(--text-micro)',
                fontWeight: 600,
                letterSpacing: 'var(--tracking-micro)',
                textTransform: 'uppercase',
                color: 'var(--color-text-muted)',
              }}
            >
              30-Day Rolling
            </span>
          }
        >
          <div
            style={{
              display: 'grid',
              gridTemplateColumns: 'repeat(2, 1fr)',
              gap: 10,
            }}
          >
            {productivity.map((m) => (
              <div
                key={m.label}
                style={{
                  background: 'var(--color-bg-panel-raised)',
                  border: '1px solid var(--color-border-subtle)',
                  borderLeft: `3px solid ${m.color}`,
                  clipPath: 'polygon(0 0, calc(100% - 8px) 0, 100% 8px, 100% 100%, 0 100%)',
                  padding: '14px 16px',
                }}
              >
                <div
                  style={{
                    fontFamily: 'var(--font-label)',
                    fontSize: 'var(--text-label)',
                    fontWeight: 600,
                    letterSpacing: 'var(--tracking-label)',
                    textTransform: 'uppercase',
                    color: 'var(--color-text-muted)',
                    marginBottom: 6,
                  }}
                >
                  {m.label}
                </div>
                <div
                  style={{
                    fontFamily: 'var(--font-mono)',
                    fontSize: 'var(--text-h2)',
                    fontWeight: 700,
                    color: m.color,
                    lineHeight: 1,
                    marginBottom: 4,
                  }}
                >
                  {m.value}
                </div>
                <div
                  style={{
                    fontSize: 11,
                    color: 'var(--color-text-muted)',
                  }}
                >
                  {m.sub}
                </div>
              </div>
            ))}
          </div>
        </PlateCard>

      </div>
    </div>
  );
}
