'use client';

import React, { useCallback, useEffect, useState } from 'react';
import AppShell from '@/components/AppShell';
import {
  getStandaloneBillingDashboardArAging,
  getStandaloneBillingDashboardExecutiveSummary,
  getStandaloneBillingDashboardKpis,
  getStandaloneBillingDashboardPayerPerformance,
} from '@/services/api';

type FetchStatus = 'idle' | 'loading' | 'ready' | 'error';

interface BillingKpis {
  clean_claim_rate?: number;
  denial_rate?: number;
  total_claims?: number;
  total_revenue_cents?: number;
  avg_days_in_ar?: number;
  net_collection_rate?: number;
}

interface ExecSummary {
  mrr_cents?: number;
  total_revenue_cents?: number;
}

interface ArBucket {
  label: string;
  count: number;
  total_cents: number;
}

interface ArAgingResponse {
  buckets: ArBucket[];
  total_ar_cents?: number;
  total_claims?: number;
  avg_days_in_ar?: number;
}

interface PayerRow {
  payer: string;
  submitted_cents: number;
  paid_cents: number;
  denial_rate: number;
  avg_days_to_pay: number;
}

interface PayerPerformanceResponse {
  payers: PayerRow[];
}

function fmt$(cents: number): string {
  return `$${(cents / 100).toLocaleString('en-US', { maximumFractionDigits: 0 })}`;
}

const TH_STYLE: React.CSSProperties = {
  padding: '10px 12px',
  textAlign: 'left',
  fontFamily: 'var(--font-label)',
  fontSize: 'var(--text-label)',
  fontWeight: 600,
  letterSpacing: 'var(--tracking-label)',
  textTransform: 'uppercase',
  color: 'var(--color-text-muted)',
  background: 'var(--color-bg-panel-raised)',
  whiteSpace: 'nowrap',
};

const TD_STYLE: React.CSSProperties = {
  padding: '10px 12px',
  fontSize: 'var(--text-body)',
  color: 'var(--color-text-secondary)',
  borderTop: '1px solid var(--color-border-subtle)',
};

const TD_MONO: React.CSSProperties = {
  ...TD_STYLE,
  fontFamily: 'var(--font-mono)',
  color: 'var(--color-text-primary)',
};

export default function BillingDashboardPage() {
  const [kpis, setKpis] = useState<BillingKpis | null>(null);
  const [exec, setExec] = useState<ExecSummary | null>(null);
  const [aging, setAging] = useState<ArAgingResponse | null>(null);
  const [payers, setPayers] = useState<PayerPerformanceResponse | null>(null);

  const [kpiStatus, setKpiStatus] = useState<FetchStatus>('idle');
  const [agingStatus, setAgingStatus] = useState<FetchStatus>('idle');
  const [payerStatus, setPayerStatus] = useState<FetchStatus>('idle');

  const fetchAll = useCallback(() => {
    setKpiStatus('loading');
    Promise.all([
      getStandaloneBillingDashboardKpis(),
      getStandaloneBillingDashboardExecutiveSummary(),
    ])
      .then(([k, e]) => { setKpis(k); setExec(e); setKpiStatus('ready'); })
      .catch(() => setKpiStatus('error'));

    setAgingStatus('loading');
    getStandaloneBillingDashboardArAging()
      .then((d) => { setAging(d); setAgingStatus('ready'); })
      .catch(() => setAgingStatus('error'));

    setPayerStatus('loading');
    getStandaloneBillingDashboardPayerPerformance()
      .then((d) => { setPayers(d); setPayerStatus('ready'); })
      .catch(() => setPayerStatus('error'));
  }, []);

  useEffect(() => { fetchAll(); }, [fetchAll]);

  const mrrDisplay = exec?.mrr_cents != null ? fmt$(exec.mrr_cents) : '—';
  const ytdDisplay = exec?.total_revenue_cents != null ? fmt$(exec.total_revenue_cents) : '—';
  const cleanClaimDisplay = kpis?.clean_claim_rate != null ? `${kpis.clean_claim_rate.toFixed(1)}%` : '—';
  const avgDaysDisplay = kpis?.avg_days_in_ar != null ? kpis.avg_days_in_ar.toFixed(1) : (aging?.avg_days_in_ar != null ? aging.avg_days_in_ar.toFixed(1) : '—');
  const denialDisplay = kpis?.denial_rate != null ? `${kpis.denial_rate.toFixed(1)}%` : '—';
  const collectionDisplay = kpis?.net_collection_rate != null ? `${kpis.net_collection_rate.toFixed(1)}%` : '—';

  const kpiCards = [
    { label: 'MRR', value: mrrDisplay, sub: 'Monthly Recurring Revenue', accent: 'var(--color-status-info)' },
    { label: 'YTD Revenue', value: ytdDisplay, sub: 'Year-to-date collected', accent: 'var(--color-status-info)' },
    { label: 'Clean Claim Rate', value: cleanClaimDisplay, sub: 'First-pass acceptance', accent: 'var(--color-status-active)' },
    { label: 'Avg Days in AR', value: avgDaysDisplay, sub: 'Days outstanding', accent: 'var(--color-status-warning)' },
    { label: 'Denial Rate', value: denialDisplay, sub: 'Claims denied by payer', accent: 'var(--color-brand-red)' },
    { label: 'Collection Rate', value: collectionDisplay, sub: 'Net collection efficiency', accent: 'var(--color-status-info)' },
  ];

  const totalArCents = aging?.buckets?.reduce((s, b) => s + b.total_cents, 0) ?? 0;

  return (
    <AppShell>
      <div style={{ color: 'var(--color-text-primary)', fontFamily: 'var(--font-sans)' }}>
        {/* Header */}
        <div
          className="hud-rail mb-8 pb-4"
          style={{ borderBottom: '1px solid var(--color-border-default)' }}
        >
          <div className="micro-caps mb-1" style={{ color: 'var(--color-system-billing)' }}>
            Revenue Cycle
          </div>
          <h1
            style={{
              fontFamily: 'var(--font-label)',
              fontSize: 'var(--text-h1)',
              fontWeight: 700,
              letterSpacing: 'var(--tracking-label)',
              textTransform: 'uppercase',
              color: 'var(--color-text-primary)',
              margin: 0,
            }}
          >
            Billing Dashboard
          </h1>
        </div>

        {/* KPI Cards */}
        {kpiStatus === 'error' && (
          <div className="mb-4 px-4 py-2 border border-[#F59E0B]/30 bg-[#F59E0B]/10 text-[#F59E0B] text-xs font-bold uppercase tracking-wider">
            Live billing KPIs unavailable — connect to backend
          </div>
        )}
        <div className="grid grid-cols-2 gap-4 lg:grid-cols-3 mb-10">
          {kpiCards.map((kpi) => (
            <div
              key={kpi.label}
              style={{
                background: '#0A0A0B',
                clipPath: 'var(--chamfer-8)',
                borderLeft: `3px solid ${kpi.accent}`,
                padding: '20px',
                boxShadow: 'var(--elevation-1)',
              }}
            >
              <div className="micro-caps mb-1" style={{ color: 'var(--color-text-muted)' }}>
                {kpi.label}
              </div>
              <div
                style={{
                  fontFamily: 'var(--font-mono)',
                  fontSize: 'var(--text-h2)',
                  fontWeight: 700,
                  color: kpi.accent,
                  lineHeight: 1.1,
                  marginBottom: '4px',
                }}
              >
                {kpiStatus === 'loading' ? '...' : kpi.value}
              </div>
              <div
                style={{
                  fontSize: 'var(--text-body)',
                  color: 'var(--color-text-muted)',
                }}
              >
                {kpi.sub}
              </div>
            </div>
          ))}
        </div>

        {/* AR Aging */}
        <div className="mb-8">
          <div className="label-caps mb-4" style={{ color: 'var(--color-text-muted)', letterSpacing: 'var(--tracking-label)' }}>
            AR Aging
          </div>
          {agingStatus === 'error' && (
            <div className="mb-3 px-4 py-2 border border-[#F59E0B]/30 bg-[#F59E0B]/10 text-[#F59E0B] text-xs font-bold uppercase tracking-wider">
              AR aging data unavailable
            </div>
          )}
          <div
            style={{
              background: '#0A0A0B',
              clipPath: 'var(--chamfer-8)',
              overflow: 'hidden',
              boxShadow: 'var(--elevation-1)',
            }}
          >
            <table style={{ width: '100%', borderCollapse: 'collapse' }}>
              <thead>
                <tr>
                  <th style={TH_STYLE}>Age Bucket</th>
                  <th style={{ ...TH_STYLE, textAlign: 'right' }}>Count</th>
                  <th style={{ ...TH_STYLE, textAlign: 'right' }}>Amount</th>
                  <th style={{ ...TH_STYLE, textAlign: 'right' }}>% of Total</th>
                </tr>
              </thead>
              <tbody>
                {agingStatus === 'loading' && (
                  <tr><td colSpan={4} style={{ ...TD_STYLE, textAlign: 'center' }}>Loading...</td></tr>
                )}
                {agingStatus === 'ready' && aging && aging.buckets.length === 0 && (
                  <tr><td colSpan={4} style={{ ...TD_STYLE, textAlign: 'center', color: 'var(--color-text-muted)' }}>No AR aging data</td></tr>
                )}
                {aging?.buckets?.map((row, i) => {
                  const pct = totalArCents > 0 ? ((row.total_cents / totalArCents) * 100).toFixed(1) : '0.0';
                  return (
                    <tr
                      key={row.label}
                      style={{
                        background:
                          i % 2 === 0 ? 'transparent' : 'rgba(255,255,255,0.015)',
                      }}
                    >
                      <td style={TD_STYLE}>{row.label}</td>
                      <td style={{ ...TD_MONO, textAlign: 'right' }}>{row.count.toLocaleString()}</td>
                      <td style={{ ...TD_MONO, textAlign: 'right', color: 'var(--color-system-billing)' }}>{fmt$(row.total_cents)}</td>
                      <td style={{ ...TD_STYLE, textAlign: 'right' }}>{pct}%</td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        </div>

        {/* Payer Performance */}
        <div className="mb-8">
          <div className="label-caps mb-4" style={{ color: 'var(--color-text-muted)', letterSpacing: 'var(--tracking-label)' }}>
            Payer Performance
          </div>
          {payerStatus === 'error' && (
            <div className="mb-3 px-4 py-2 border border-[#F59E0B]/30 bg-[#F59E0B]/10 text-[#F59E0B] text-xs font-bold uppercase tracking-wider">
              Payer performance data unavailable
            </div>
          )}
          <div
            style={{
              background: '#0A0A0B',
              clipPath: 'var(--chamfer-8)',
              overflow: 'hidden',
              boxShadow: 'var(--elevation-1)',
            }}
          >
            <table style={{ width: '100%', borderCollapse: 'collapse' }}>
              <thead>
                <tr>
                  <th style={TH_STYLE}>Payer Name</th>
                  <th style={{ ...TH_STYLE, textAlign: 'right' }}>Submitted</th>
                  <th style={{ ...TH_STYLE, textAlign: 'right' }}>Paid</th>
                  <th style={{ ...TH_STYLE, textAlign: 'right' }}>Denial Rate</th>
                  <th style={{ ...TH_STYLE, textAlign: 'right' }}>Avg Days</th>
                </tr>
              </thead>
              <tbody>
                {payerStatus === 'loading' && (
                  <tr><td colSpan={5} style={{ ...TD_STYLE, textAlign: 'center' }}>Loading...</td></tr>
                )}
                {payerStatus === 'ready' && payers && payers.payers.length === 0 && (
                  <tr><td colSpan={5} style={{ ...TD_STYLE, textAlign: 'center', color: 'var(--color-text-muted)' }}>No payer data</td></tr>
                )}
                {payers?.payers?.map((row, i) => {
                  const denialColor =
                    row.denial_rate > 5
                      ? 'var(--color-brand-red)'
                      : row.denial_rate > 3
                      ? 'var(--color-status-warning)'
                      : 'var(--color-status-active)';
                  return (
                    <tr
                      key={row.payer}
                      style={{
                        background:
                          i % 2 === 0 ? 'transparent' : 'rgba(255,255,255,0.015)',
                      }}
                    >
                      <td
                        style={{
                          ...TD_STYLE,
                          fontWeight: 600,
                          color: 'var(--color-text-primary)',
                        }}
                      >
                        {row.payer}
                      </td>
                      <td style={{ ...TD_MONO, textAlign: 'right' }}>{fmt$(row.submitted_cents)}</td>
                      <td style={{ ...TD_MONO, textAlign: 'right', color: 'var(--color-status-active)' }}>
                        {fmt$(row.paid_cents)}
                      </td>
                      <td
                        style={{
                          ...TD_MONO,
                          textAlign: 'right',
                          color: denialColor,
                        }}
                      >
                        {row.denial_rate.toFixed(1)}%
                      </td>
                      <td style={{ ...TD_MONO, textAlign: 'right' }}>{row.avg_days_to_pay}d</td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        </div>
      </div>
    </AppShell>
  );
}
