'use client';

import { useEffect, useState } from 'react';
import { AlertTriangle, BarChart3, DollarSign, RefreshCw, TrendingUp } from 'lucide-react';
import Link from 'next/link';
import {
  getBillingCommandDashboard,
  getBillingKPIs,
  getPayerPerformance,
  getRevenueLeakage,
  getRevenueTrend,
} from '@/services/api';

export default function BillingReportsPage() {
  const [dashboard, setDashboard] = useState<Record<string, unknown> | null>(null);
  const [kpis, setKpis] = useState<Record<string, unknown> | null>(null);
  const [payers, setPayers] = useState<Record<string, unknown>[]>([]);
  const [leakage, setLeakage] = useState<Record<string, unknown> | null>(null);
  const [_trend, setTrend] = useState<Record<string, unknown>[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const loadData = async () => {
    setLoading(true);
    setError(null);
    try {
      const [dRes, kRes, pRes, lRes, tRes] = await Promise.allSettled([
        getBillingCommandDashboard(),
        getBillingKPIs(),
        getPayerPerformance(),
        getRevenueLeakage(),
        getRevenueTrend(),
      ]);
      if (dRes.status === 'fulfilled') setDashboard(dRes.value);
      if (kRes.status === 'fulfilled') setKpis(kRes.value);
      if (pRes.status === 'fulfilled') {
        const pd = pRes.value;
        setPayers(Array.isArray(pd?.payers) ? pd.payers : Array.isArray(pd) ? pd : []);
      }
      if (lRes.status === 'fulfilled') setLeakage(lRes.value);
      if (tRes.status === 'fulfilled') {
        const td = tRes.value;
        setTrend(Array.isArray(td?.months) ? td.months : Array.isArray(td) ? td : []);
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load reports');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { loadData(); }, []);

  const formatCents = (c: unknown) =>
    typeof c === 'number' ? `$${(c / 100).toLocaleString('en-US', { minimumFractionDigits: 2 })}` : '$0.00';

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
            <Link href="/billing" className="text-gray-400 hover:text-white text-sm mb-2 block">← Billing Hub</Link>
            <h1 className="text-3xl font-bold flex items-center gap-3">
              <BarChart3 className="w-8 h-8 text-blue-400" /> Billing Reports & Analytics
            </h1>
          </div>
          <button onClick={loadData} className="px-4 py-2 bg-gray-800 hover:bg-gray-700 rounded-lg flex items-center gap-2 text-sm">
            <RefreshCw className="w-4 h-4" /> Refresh
          </button>
        </div>

        {error && (
          <div className="bg-red-900/30 border border-red-700 rounded-lg p-4 flex items-center gap-3">
            <AlertTriangle className="w-5 h-5 text-red-400" /><span className="text-red-300">{error}</span>
          </div>
        )}

        {/* KPI Cards */}
        {dashboard && (
          <div className="grid grid-cols-2 md:grid-cols-5 gap-4">
            {[
              { label: 'Total Claims', val: dashboard.total_claims, icon: BarChart3, color: 'text-blue-400' },
              { label: 'Revenue', val: formatCents(dashboard.revenue_cents), icon: DollarSign, color: 'text-emerald-400', raw: true },
              { label: 'Paid Claims', val: dashboard.paid_claims, icon: TrendingUp, color: 'text-cyan-400' },
              { label: 'Denial Rate', val: `${dashboard.denial_rate_pct ?? 0}%`, icon: AlertTriangle, color: 'text-amber-400', raw: true },
              { label: 'Clean Rate', val: `${dashboard.clean_claim_rate_pct ?? 0}%`, icon: TrendingUp, color: 'text-emerald-400', raw: true },
            ].map((c, i) => (
              <div key={i} className="bg-gray-900 border border-gray-800 rounded-lg p-4">
                <div className="text-gray-400 text-xs flex items-center gap-1"><c.icon className="w-3.5 h-3.5" />{c.label}</div>
                <div className={`text-xl font-bold ${c.color}`}>{c.raw ? c.val : String(c.val ?? 0)}</div>
              </div>
            ))}
          </div>
        )}

        {/* Revenue Leakage */}
        {leakage && (
          <div className="bg-gray-900 border border-gray-800 rounded-lg p-6">
            <h2 className="text-lg font-semibold mb-4">Revenue Leakage Analysis</h2>
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
              {Object.entries(leakage).filter(([k]) => k !== 'as_of').slice(0, 8).map(([k, v]) => (
                <div key={k}>
                  <div className="text-gray-400 text-xs">{k.replace(/_/g, ' ')}</div>
                  <div className="text-sm font-semibold text-gray-200">{typeof v === 'number' ? (k.includes('cents') ? formatCents(v) : v.toLocaleString()) : String(v ?? '—')}</div>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Payer Performance Table */}
        {payers.length > 0 && (
          <div className="bg-gray-900 border border-gray-800 rounded-lg p-6">
            <h2 className="text-lg font-semibold mb-4">Payer Performance</h2>
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead><tr className="text-gray-400 border-b border-gray-800">
                  <th className="text-left py-2">Payer</th>
                  <th className="text-right py-2">Claims</th>
                  <th className="text-right py-2">Revenue</th>
                  <th className="text-right py-2">Paid</th>
                  <th className="text-right py-2">Denied</th>
                </tr></thead>
                <tbody>
                  {payers.slice(0, 10).map((p, i) => (
                    <tr key={i} className="border-b border-gray-800/50">
                      <td className="py-2">{String(p.payer_name ?? p.name ?? `Payer ${i + 1}`)}</td>
                      <td className="py-2 text-right">{String(p.total_claims ?? 0)}</td>
                      <td className="py-2 text-right text-emerald-400">{formatCents(p.revenue_cents)}</td>
                      <td className="py-2 text-right text-blue-400">{String(p.paid ?? 0)}</td>
                      <td className="py-2 text-right text-red-400">{String(p.denied ?? 0)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        )}

        {/* Billing KPIs */}
        {kpis && (
          <div className="bg-gray-900 border border-gray-800 rounded-lg p-6">
            <h2 className="text-lg font-semibold mb-4">Billing KPIs</h2>
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
              {Object.entries(kpis).filter(([k]) => k !== 'as_of').slice(0, 12).map(([k, v]) => (
                <div key={k}>
                  <div className="text-gray-400 text-xs">{k.replace(/_/g, ' ')}</div>
                  <div className="text-sm font-semibold text-gray-200">{typeof v === 'number' ? v.toLocaleString() : String(v ?? '—')}</div>
                </div>
              ))}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
