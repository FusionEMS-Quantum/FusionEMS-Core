'use client';

import { useEffect, useState } from 'react';
import Link from 'next/link';
import { ArrowLeft, BarChart3, Calculator, DollarSign, RefreshCw, TrendingUp, AlertTriangle } from 'lucide-react';
import { calculateROI, getMarginRiskByTenant } from '@/services/api';

interface ROIResult {
  annual_savings_cents?: number;
  roi_pct?: number;
  payback_months?: number;
  revenue_uplift_cents?: number;
  cost_reduction_cents?: number;
  efficiency_gain_pct?: number;
}

interface TenantMargin {
  tenant_id: string;
  tenant_name?: string;
  revenue_cents?: number;
  cost_cents?: number;
  margin_pct?: number;
  risk_level?: string;
}

export default function ROIAnalyticsPage() {
  const [roi, setROI] = useState<ROIResult | null>(null);
  const [margins, setMargins] = useState<TenantMargin[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const loadData = async () => {
    setLoading(true);
    setError(null);
    try {
      const [roiRes, marginRes] = await Promise.allSettled([
        calculateROI({ agency_type: 'ems', call_volume_monthly: 500, crew_count: 20 }),
        getMarginRiskByTenant(),
      ]);
      if (roiRes.status === 'fulfilled') setROI(roiRes.value);
      if (marginRes.status === 'fulfilled') {
        const m = marginRes.value;
        setMargins(Array.isArray(m?.tenants) ? m.tenants : Array.isArray(m) ? m : []);
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load ROI data');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { loadData(); }, []);

  const formatCents = (cents: number | undefined) =>
    cents != null ? `$${(cents / 100).toLocaleString('en-US', { minimumFractionDigits: 2 })}` : '$0.00';

  const riskColor = (level: string | undefined) => {
    if (level === 'high' || level === 'critical') return 'text-red-400';
    if (level === 'medium') return 'text-amber-400';
    return 'text-emerald-400';
  };

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
            <Link href="/founder/roi" className="text-gray-400 hover:text-white flex items-center gap-1 text-sm mb-2">
              <ArrowLeft className="w-4 h-4" /> ROI Hub
            </Link>
            <h1 className="text-3xl font-bold flex items-center gap-3">
              <BarChart3 className="w-8 h-8 text-emerald-400" />
              ROI Analytics Engine
            </h1>
            <p className="text-gray-400 mt-1">Cost-per-transport modeling, revenue efficiency, and margin analysis</p>
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

        {/* ROI KPIs */}
        <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
          <div className="bg-gray-900 border border-gray-800 rounded-lg p-5">
            <div className="flex items-center gap-2 text-gray-400 text-sm mb-1"><DollarSign className="w-4 h-4" /> Annual Savings</div>
            <div className="text-2xl font-bold text-emerald-400">{formatCents(roi?.annual_savings_cents)}</div>
          </div>
          <div className="bg-gray-900 border border-gray-800 rounded-lg p-5">
            <div className="flex items-center gap-2 text-gray-400 text-sm mb-1"><TrendingUp className="w-4 h-4" /> ROI</div>
            <div className="text-2xl font-bold text-blue-400">{roi?.roi_pct ?? 0}%</div>
          </div>
          <div className="bg-gray-900 border border-gray-800 rounded-lg p-5">
            <div className="flex items-center gap-2 text-gray-400 text-sm mb-1"><Calculator className="w-4 h-4" /> Payback Period</div>
            <div className="text-2xl font-bold text-cyan-400">{roi?.payback_months ?? '—'} mo</div>
          </div>
          <div className="bg-gray-900 border border-gray-800 rounded-lg p-5">
            <div className="flex items-center gap-2 text-gray-400 text-sm mb-1"><TrendingUp className="w-4 h-4" /> Revenue Uplift</div>
            <div className="text-2xl font-bold text-violet-400">{formatCents(roi?.revenue_uplift_cents)}</div>
          </div>
        </div>

        {/* Efficiency Metrics */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <div className="bg-gray-900 border border-gray-800 rounded-lg p-6">
            <h2 className="text-lg font-semibold mb-4 flex items-center gap-2">
              <BarChart3 className="w-5 h-5 text-emerald-400" /> Efficiency Breakdown
            </h2>
            <div className="space-y-4">
              <div className="flex justify-between items-center">
                <span className="text-gray-400">Cost Reduction</span>
                <span className="text-emerald-400 font-bold">{formatCents(roi?.cost_reduction_cents)}</span>
              </div>
              <div className="flex justify-between items-center">
                <span className="text-gray-400">Efficiency Gain</span>
                <span className="text-blue-400 font-bold">{roi?.efficiency_gain_pct ?? 0}%</span>
              </div>
              <div className="flex justify-between items-center">
                <span className="text-gray-400">Annual Savings</span>
                <span className="text-cyan-400 font-bold">{formatCents(roi?.annual_savings_cents)}</span>
              </div>
            </div>
          </div>
          <div className="bg-gray-900 border border-gray-800 rounded-lg p-6">
            <h2 className="text-lg font-semibold mb-4 flex items-center gap-2">
              <Calculator className="w-5 h-5 text-violet-400" /> Model Parameters
            </h2>
            <div className="space-y-3 text-sm">
              <div className="flex justify-between"><span className="text-gray-400">Agency Type</span><span className="text-white">EMS</span></div>
              <div className="flex justify-between"><span className="text-gray-400">Monthly Call Volume</span><span className="text-white">500</span></div>
              <div className="flex justify-between"><span className="text-gray-400">Crew Count</span><span className="text-white">20</span></div>
              <div className="flex justify-between"><span className="text-gray-400">ROI Timeframe</span><span className="text-white">{roi?.payback_months ?? '—'} months</span></div>
            </div>
          </div>
        </div>

        {/* Per-Tenant Margin Table */}
        <div className="bg-gray-900 border border-gray-800 rounded-lg overflow-hidden">
          <div className="px-6 py-4 border-b border-gray-800">
            <h2 className="text-lg font-semibold flex items-center gap-2">
              <DollarSign className="w-5 h-5 text-amber-400" /> Per-Tenant Margin Risk
            </h2>
          </div>
          {margins.length === 0 ? (
            <div className="p-12 text-center text-gray-500">No tenant margin data available yet.</div>
          ) : (
            <table className="w-full text-sm">
              <thead className="bg-gray-800/50">
                <tr>
                  <th className="text-left px-6 py-3 text-gray-400 font-medium">Tenant</th>
                  <th className="text-left px-6 py-3 text-gray-400 font-medium">Revenue</th>
                  <th className="text-left px-6 py-3 text-gray-400 font-medium">Cost</th>
                  <th className="text-left px-6 py-3 text-gray-400 font-medium">Margin</th>
                  <th className="text-left px-6 py-3 text-gray-400 font-medium">Risk</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-800">
                {margins.map((t) => (
                  <tr key={t.tenant_id} className="hover:bg-gray-800/30">
                    <td className="px-6 py-3 text-white font-medium">{t.tenant_name ?? t.tenant_id}</td>
                    <td className="px-6 py-3 text-emerald-400">{formatCents(t.revenue_cents)}</td>
                    <td className="px-6 py-3 text-red-400">{formatCents(t.cost_cents)}</td>
                    <td className="px-6 py-3 text-cyan-400 font-bold">{t.margin_pct ?? 0}%</td>
                    <td className={`px-6 py-3 font-bold uppercase ${riskColor(t.risk_level)}`}>{t.risk_level ?? 'low'}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </div>
      </div>
    </div>
  );
}
