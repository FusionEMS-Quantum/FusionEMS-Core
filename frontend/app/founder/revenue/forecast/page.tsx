'use client';

import { useEffect, useState } from 'react';
import { AlertTriangle, ArrowLeft, BarChart3, DollarSign, RefreshCw, TrendingUp } from 'lucide-react';
import Link from 'next/link';
import { getRevenueTrend, getBillingCommandDashboard } from '@/services/api';

interface MonthData {
  month?: string;
  period?: string;
  revenue_cents?: number;
  claim_count?: number;
  projected_revenue_cents?: number;
}

interface ForecastData {
  months?: MonthData[];
  historical?: MonthData[];
  projected?: MonthData[];
  total_projected_cents?: number;
  growth_rate_pct?: number;
}

export default function ForecastPage() {
  const [forecast, setForecast] = useState<ForecastData | null>(null);
  const [dashboard, setDashboard] = useState<Record<string, unknown> | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const loadData = async () => {
    setLoading(true);
    setError(null);
    try {
      const [fRes, dRes] = await Promise.allSettled([
        getRevenueTrend(),
        getBillingCommandDashboard(),
      ]);
      if (fRes.status === 'fulfilled') setForecast(fRes.value);
      if (dRes.status === 'fulfilled') setDashboard(dRes.value);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load forecast');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { loadData(); }, []);

  const formatCents = (cents: number | undefined) =>
    cents != null && Number.isFinite(cents) ? `$${(cents / 100).toLocaleString('en-US', { minimumFractionDigits: 2 })}` : '—';

  const dashboardRevenueCentsCandidate = dashboard ? dashboard['revenue_cents'] : undefined;
  const currentRevenueCents = typeof dashboardRevenueCentsCandidate === 'number' && Number.isFinite(dashboardRevenueCentsCandidate)
    ? dashboardRevenueCentsCandidate
    : null;
  const growthRatePctCandidate = forecast?.growth_rate_pct;
  const growthRatePct = typeof growthRatePctCandidate === 'number' && Number.isFinite(growthRatePctCandidate)
    ? growthRatePctCandidate
    : null;

  const months: MonthData[] = forecast?.months ?? forecast?.historical ?? [];

  if (loading) {
    return (
      <div className="min-h-screen bg-[var(--color-bg-base)] text-white flex items-center justify-center">
        <RefreshCw className="w-8 h-8 animate-spin text-[var(--color-status-active)]" />
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-[var(--color-bg-base)] text-white p-6">
      <div className="max-w-7xl mx-auto space-y-8">
        <div className="flex items-center justify-between">
          <div>
            <Link href="/founder/revenue" className="text-[var(--color-text-secondary)] hover:text-[var(--color-text-primary)] flex items-center gap-1 text-sm mb-2">
              <ArrowLeft className="w-4 h-4" /> Back to Revenue
            </Link>
            <h1 className="text-3xl font-bold flex items-center gap-3">
              <TrendingUp className="w-8 h-8 text-[var(--color-status-active)]" />
              Revenue Forecast
            </h1>
          </div>
          <button onClick={loadData} className="px-4 py-2 bg-[var(--color-bg-raised)] hover:bg-[var(--color-bg-overlay)] chamfer-8 flex items-center gap-2 text-sm">
            <RefreshCw className="w-4 h-4" /> Refresh
          </button>
        </div>

        {error && (
          <div className="bg-red-900/30 border border-[var(--color-brand-red)] chamfer-8 p-4 flex items-center gap-3">
            <AlertTriangle className="w-5 h-5 text-[var(--color-brand-red)]" />
            <span className="text-[var(--color-brand-red)]">{error}</span>
          </div>
        )}

        {/* Summary */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          <div className="bg-[var(--color-bg-panel)] border border-[var(--color-border-default)] chamfer-8 p-5">
            <div className="text-[var(--color-text-secondary)] text-sm flex items-center gap-2"><DollarSign className="w-4 h-4" /> Current Revenue</div>
            <div className="text-2xl font-bold text-[var(--color-status-active)]">{currentRevenueCents != null ? formatCents(currentRevenueCents) : '—'}</div>
          </div>
          <div className="bg-[var(--color-bg-panel)] border border-[var(--color-border-default)] chamfer-8 p-5">
            <div className="text-[var(--color-text-secondary)] text-sm flex items-center gap-2"><TrendingUp className="w-4 h-4" /> Growth Rate</div>
            <div className="text-2xl font-bold text-[var(--color-status-info)]">{growthRatePct != null ? `${growthRatePct}%` : '—'}</div>
          </div>
          <div className="bg-[var(--color-bg-panel)] border border-[var(--color-border-default)] chamfer-8 p-5">
            <div className="text-[var(--color-text-secondary)] text-sm flex items-center gap-2"><BarChart3 className="w-4 h-4" /> Projected Total</div>
            <div className="text-2xl font-bold text-[var(--color-system-compliance)]">{formatCents(forecast?.total_projected_cents)}</div>
          </div>
        </div>

        {/* Monthly Trend Table */}
        <div className="bg-[var(--color-bg-panel)] border border-[var(--color-border-default)] chamfer-8 p-6">
          <h2 className="text-lg font-semibold mb-4 flex items-center gap-2">
            <BarChart3 className="w-5 h-5 text-[var(--color-status-info)]" /> Monthly Revenue Trend
          </h2>
          {months.length > 0 ? (
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead><tr className="text-[var(--color-text-secondary)] border-b border-[var(--color-border-default)]">
                  <th className="text-left py-2">Period</th>
                  <th className="text-right py-2">Revenue</th>
                  <th className="text-right py-2">Claims</th>
                  <th className="text-right py-2">Projected</th>
                </tr></thead>
                <tbody>
                  {months.map((m, i) => (
                    <tr key={i} className="border-b border-[var(--color-border-subtle)] hover:bg-[var(--color-bg-raised)]/30">
                      <td className="py-2">{m.month ?? m.period ?? `Month ${i + 1}`}</td>
                      <td className="py-2 text-right text-[var(--color-status-active)]">{formatCents(m.revenue_cents)}</td>
                      <td className="py-2 text-right text-[var(--color-text-secondary)]">{m.claim_count ?? '—'}</td>
                      <td className="py-2 text-right text-[var(--color-system-compliance)]">{m.projected_revenue_cents ? formatCents(m.projected_revenue_cents) : '—'}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          ) : (
            <div className="text-[var(--color-text-muted)]">No trend data available yet. Revenue data will appear once claims are processed.</div>
          )}
        </div>
      </div>
    </div>
  );
}
