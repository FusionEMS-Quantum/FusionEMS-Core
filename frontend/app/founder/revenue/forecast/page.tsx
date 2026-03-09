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
    cents != null ? `$${(cents / 100).toLocaleString('en-US', { minimumFractionDigits: 2 })}` : '$0.00';

  const months: MonthData[] = forecast?.months ?? forecast?.historical ?? [];

  if (loading) {
    return (
      <div className="min-h-screen bg-gray-950 text-white flex items-center justify-center">
        <RefreshCw className="w-8 h-8 animate-spin text-emerald-400" />
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gray-950 text-white p-6">
      <div className="max-w-7xl mx-auto space-y-8">
        <div className="flex items-center justify-between">
          <div>
            <Link href="/founder/revenue" className="text-gray-400 hover:text-white flex items-center gap-1 text-sm mb-2">
              <ArrowLeft className="w-4 h-4" /> Back to Revenue
            </Link>
            <h1 className="text-3xl font-bold flex items-center gap-3">
              <TrendingUp className="w-8 h-8 text-emerald-400" />
              Revenue Forecast
            </h1>
          </div>
          <button onClick={loadData} className="px-4 py-2 bg-gray-800 hover:bg-gray-700 rounded-lg flex items-center gap-2 text-sm">
            <RefreshCw className="w-4 h-4" /> Refresh
          </button>
        </div>

        {error && (
          <div className="bg-red-900/30 border border-red-700 rounded-lg p-4 flex items-center gap-3">
            <AlertTriangle className="w-5 h-5 text-red-400" />
            <span className="text-red-300">{error}</span>
          </div>
        )}

        {/* Summary */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          <div className="bg-gray-900 border border-gray-800 rounded-lg p-5">
            <div className="text-gray-400 text-sm flex items-center gap-2"><DollarSign className="w-4 h-4" /> Current Revenue</div>
            <div className="text-2xl font-bold text-emerald-400">{formatCents((dashboard?.revenue_cents as number) ?? (() => { throw new Error('Unsafe silent fallback. Dependency missing.'); })())}</div>
          </div>
          <div className="bg-gray-900 border border-gray-800 rounded-lg p-5">
            <div className="text-gray-400 text-sm flex items-center gap-2"><TrendingUp className="w-4 h-4" /> Growth Rate</div>
            <div className="text-2xl font-bold text-blue-400">{forecast?.growth_rate_pct ?? (() => { throw new Error('Unsafe silent fallback. Dependency missing.'); })()}%</div>
          </div>
          <div className="bg-gray-900 border border-gray-800 rounded-lg p-5">
            <div className="text-gray-400 text-sm flex items-center gap-2"><BarChart3 className="w-4 h-4" /> Projected Total</div>
            <div className="text-2xl font-bold text-violet-400">{formatCents(forecast?.total_projected_cents)}</div>
          </div>
        </div>

        {/* Monthly Trend Table */}
        <div className="bg-gray-900 border border-gray-800 rounded-lg p-6">
          <h2 className="text-lg font-semibold mb-4 flex items-center gap-2">
            <BarChart3 className="w-5 h-5 text-blue-400" /> Monthly Revenue Trend
          </h2>
          {months.length > 0 ? (
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead><tr className="text-gray-400 border-b border-gray-800">
                  <th className="text-left py-2">Period</th>
                  <th className="text-right py-2">Revenue</th>
                  <th className="text-right py-2">Claims</th>
                  <th className="text-right py-2">Projected</th>
                </tr></thead>
                <tbody>
                  {months.map((m, i) => (
                    <tr key={i} className="border-b border-gray-800/50 hover:bg-gray-800/30">
                      <td className="py-2">{m.month ?? m.period ?? `Month ${i + 1}`}</td>
                      <td className="py-2 text-right text-emerald-400">{formatCents(m.revenue_cents)}</td>
                      <td className="py-2 text-right text-gray-300">{m.claim_count ?? '—'}</td>
                      <td className="py-2 text-right text-violet-400">{m.projected_revenue_cents ? formatCents(m.projected_revenue_cents) : '—'}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          ) : (
            <div className="text-gray-500">No trend data available yet. Revenue data will appear once claims are processed.</div>
          )}
        </div>
      </div>
    </div>
  );
}
