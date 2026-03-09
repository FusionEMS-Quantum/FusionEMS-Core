'use client';

import { useEffect, useState } from 'react';
import { AlertTriangle, ArrowLeft, CreditCard, DollarSign, RefreshCw, TrendingUp, Users } from 'lucide-react';
import Link from 'next/link';
import {
  getStripeReconciliation,
  getBillingCommandDashboard,
  getRevenueTrend,
  getTenantBillingRanking,
} from '@/services/api';

interface ReconData {
  reconciliation_status?: string;
  matched_count?: number;
  unmatched_count?: number;
  total_stripe_payments?: number;
  total_claims_matched?: number;
  discrepancy_cents?: number;
  as_of?: string;
}

interface DashboardData {
  total_claims?: number;
  paid_claims?: number;
  denied_claims?: number;
  pending_claims?: number;
  revenue_cents?: number;
  clean_claim_rate_pct?: number;
  denial_rate_pct?: number;
  as_of?: string;
}

interface TrendEntry {
  month?: string;
  revenue_cents?: number;
  claim_count?: number;
}

interface TenantRank {
  name?: string;
  total_claims?: number;
  revenue_cents?: number;
  paid_claims?: number;
}

export default function StripeDashboardPage() {
  const [recon, setRecon] = useState<ReconData | null>(null);
  const [dashboard, setDashboard] = useState<DashboardData | null>(null);
  const [trend, setTrend] = useState<TrendEntry[]>([]);
  const [ranking, setRanking] = useState<TenantRank[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const loadData = async () => {
    setLoading(true);
    setError(null);
    try {
      const [reconRes, dashRes, trendRes, rankRes] = await Promise.allSettled([
        getStripeReconciliation(),
        getBillingCommandDashboard(),
        getRevenueTrend(),
        getTenantBillingRanking(),
      ]);
      if (reconRes.status === 'fulfilled') setRecon(reconRes.value);
      if (dashRes.status === 'fulfilled') setDashboard(dashRes.value);
      if (trendRes.status === 'fulfilled') {
        const tData = trendRes.value;
        setTrend(Array.isArray(tData?.months) ? tData.months : Array.isArray(tData) ? tData : []);
      }
      if (rankRes.status === 'fulfilled') {
        const rData = rankRes.value;
        setRanking(Array.isArray(rData?.tenants) ? rData.tenants : Array.isArray(rData) ? rData : []);
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load Stripe data');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { loadData(); }, []);

  const formatCents = (cents: number | undefined) =>
    cents != null ? `$${(cents / 100).toLocaleString('en-US', { minimumFractionDigits: 2 })}` : '$0.00';

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
        {/* Header */}
        <div className="flex items-center justify-between">
          <div>
            <Link href="/founder/revenue" className="text-gray-400 hover:text-white flex items-center gap-1 text-sm mb-2">
              <ArrowLeft className="w-4 h-4" /> Back to Revenue
            </Link>
            <h1 className="text-3xl font-bold flex items-center gap-3">
              <CreditCard className="w-8 h-8 text-violet-400" />
              Stripe Revenue Dashboard
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

        {/* KPI Cards */}
        <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
          <div className="bg-gray-900 border border-gray-800 rounded-lg p-5">
            <div className="flex items-center gap-2 text-gray-400 text-sm mb-1"><DollarSign className="w-4 h-4" /> Total Revenue</div>
            <div className="text-2xl font-bold text-emerald-400">{formatCents(dashboard?.revenue_cents)}</div>
          </div>
          <div className="bg-gray-900 border border-gray-800 rounded-lg p-5">
            <div className="flex items-center gap-2 text-gray-400 text-sm mb-1"><TrendingUp className="w-4 h-4" /> Paid Claims</div>
            <div className="text-2xl font-bold text-blue-400">{dashboard?.paid_claims ?? (() => { throw new Error('Unsafe silent fallback. Dependency missing.'); })()}</div>
          </div>
          <div className="bg-gray-900 border border-gray-800 rounded-lg p-5">
            <div className="flex items-center gap-2 text-gray-400 text-sm mb-1"><AlertTriangle className="w-4 h-4" /> Denial Rate</div>
            <div className="text-2xl font-bold text-amber-400">{dashboard?.denial_rate_pct ?? (() => { throw new Error('Unsafe silent fallback. Dependency missing.'); })()}%</div>
          </div>
          <div className="bg-gray-900 border border-gray-800 rounded-lg p-5">
            <div className="flex items-center gap-2 text-gray-400 text-sm mb-1"><Users className="w-4 h-4" /> Clean Claim Rate</div>
            <div className="text-2xl font-bold text-cyan-400">{dashboard?.clean_claim_rate_pct ?? (() => { throw new Error('Unsafe silent fallback. Dependency missing.'); })()}%</div>
          </div>
        </div>

        {/* Stripe Reconciliation */}
        <div className="bg-gray-900 border border-gray-800 rounded-lg p-6">
          <h2 className="text-lg font-semibold mb-4 flex items-center gap-2">
            <CreditCard className="w-5 h-5 text-violet-400" /> Stripe Reconciliation
          </h2>
          {recon ? (
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
              <div>
                <div className="text-gray-400 text-sm">Status</div>
                <div className={`font-semibold ${recon.reconciliation_status === 'matched' ? 'text-emerald-400' : 'text-amber-400'}`}>
                  {recon.reconciliation_status ?? 'Unknown'}
                </div>
              </div>
              <div>
                <div className="text-gray-400 text-sm">Matched Payments</div>
                <div className="font-semibold text-emerald-400">{recon.matched_count ?? (() => { throw new Error('Unsafe silent fallback. Dependency missing.'); })()}</div>
              </div>
              <div>
                <div className="text-gray-400 text-sm">Unmatched</div>
                <div className="font-semibold text-red-400">{recon.unmatched_count ?? (() => { throw new Error('Unsafe silent fallback. Dependency missing.'); })()}</div>
              </div>
              <div>
                <div className="text-gray-400 text-sm">Discrepancy</div>
                <div className="font-semibold text-amber-400">{formatCents(recon.discrepancy_cents)}</div>
              </div>
            </div>
          ) : (
            <div className="text-gray-500">No reconciliation data available</div>
          )}
        </div>

        {/* Revenue Trend */}
        <div className="bg-gray-900 border border-gray-800 rounded-lg p-6">
          <h2 className="text-lg font-semibold mb-4 flex items-center gap-2">
            <TrendingUp className="w-5 h-5 text-blue-400" /> Revenue Trend
          </h2>
          {trend.length > 0 ? (
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead><tr className="text-gray-400 border-b border-gray-800">
                  <th className="text-left py-2">Month</th>
                  <th className="text-right py-2">Revenue</th>
                  <th className="text-right py-2">Claims</th>
                </tr></thead>
                <tbody>
                  {trend.map((t, i) => (
                    <tr key={i} className="border-b border-gray-800/50 hover:bg-gray-800/30">
                      <td className="py-2">{t.month ?? `Month ${i + 1}`}</td>
                      <td className="py-2 text-right text-emerald-400">{formatCents(t.revenue_cents)}</td>
                      <td className="py-2 text-right text-gray-300">{t.claim_count ?? (() => { throw new Error('Unsafe silent fallback. Dependency missing.'); })()}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          ) : (
            <div className="text-gray-500">No trend data available</div>
          )}
        </div>

        {/* Tenant Billing Ranking */}
        <div className="bg-gray-900 border border-gray-800 rounded-lg p-6">
          <h2 className="text-lg font-semibold mb-4 flex items-center gap-2">
            <Users className="w-5 h-5 text-cyan-400" /> Tenant Billing Ranking
          </h2>
          {ranking.length > 0 ? (
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead><tr className="text-gray-400 border-b border-gray-800">
                  <th className="text-left py-2">Tenant</th>
                  <th className="text-right py-2">Revenue</th>
                  <th className="text-right py-2">Total Claims</th>
                  <th className="text-right py-2">Paid Claims</th>
                </tr></thead>
                <tbody>
                  {ranking.map((r, i) => (
                    <tr key={i} className="border-b border-gray-800/50 hover:bg-gray-800/30">
                      <td className="py-2 font-medium">{r.name ?? `Tenant ${i + 1}`}</td>
                      <td className="py-2 text-right text-emerald-400">{formatCents(r.revenue_cents)}</td>
                      <td className="py-2 text-right text-gray-300">{r.total_claims ?? (() => { throw new Error('Unsafe silent fallback. Dependency missing.'); })()}</td>
                      <td className="py-2 text-right text-blue-400">{r.paid_claims ?? (() => { throw new Error('Unsafe silent fallback. Dependency missing.'); })()}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          ) : (
            <div className="text-gray-500">No ranking data available</div>
          )}
        </div>

        {/* Footer */}
        <div className="text-center text-gray-600 text-xs">
          Last updated: {dashboard?.as_of ?? recon?.as_of ?? 'N/A'}
        </div>
      </div>
    </div>
  );
}
