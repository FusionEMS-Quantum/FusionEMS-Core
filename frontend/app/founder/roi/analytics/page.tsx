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
    cents != null && Number.isFinite(cents) ? `$${(cents / 100).toLocaleString('en-US', { minimumFractionDigits: 2 })}` : '—';

  const riskColor = (level: string | undefined) => {
    if (level === 'high' || level === 'critical') return 'text-[var(--color-brand-red)]';
    if (level === 'medium') return 'text-[var(--q-yellow)]';
    return 'text-[var(--color-status-active)]';
  };

  if (loading) {
    return (
      <div className="min-h-screen bg-[var(--color-bg-base)] text-white flex items-center justify-center">
        <RefreshCw className="w-8 h-8 animate-spin text-[var(--color-status-active)]" />
      </div>
    );
  }

  const roiPctCandidate = roi?.roi_pct;
  const efficiencyGainPctCandidate = roi?.efficiency_gain_pct;
  const roiPct = typeof roiPctCandidate === 'number' && Number.isFinite(roiPctCandidate) ? roiPctCandidate : null;
  const efficiencyGainPct = typeof efficiencyGainPctCandidate === 'number' && Number.isFinite(efficiencyGainPctCandidate) ? efficiencyGainPctCandidate : null;

  return (
    <div className="min-h-screen bg-[var(--color-bg-base)] text-white p-6">
      <div className="max-w-7xl mx-auto space-y-8">
        <div className="flex items-center justify-between">
          <div>
            <Link href="/founder/roi" className="text-[var(--color-text-secondary)] hover:text-[var(--color-text-primary)] flex items-center gap-1 text-sm mb-2">
              <ArrowLeft className="w-4 h-4" /> ROI Hub
            </Link>
            <h1 className="text-3xl font-bold flex items-center gap-3">
              <BarChart3 className="w-8 h-8 text-[var(--color-status-active)]" />
              ROI Analytics Engine
            </h1>
            <p className="text-[var(--color-text-secondary)] mt-1">Cost-per-transport modeling, revenue efficiency, and margin analysis</p>
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

        {/* ROI KPIs */}
        <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
          <div className="bg-[var(--color-bg-panel)] border border-[var(--color-border-default)] chamfer-8 p-5">
            <div className="flex items-center gap-2 text-[var(--color-text-secondary)] text-sm mb-1"><DollarSign className="w-4 h-4" /> Annual Savings</div>
            <div className="text-2xl font-bold text-[var(--color-status-active)]">{formatCents(roi?.annual_savings_cents)}</div>
          </div>
          <div className="bg-[var(--color-bg-panel)] border border-[var(--color-border-default)] chamfer-8 p-5">
            <div className="flex items-center gap-2 text-[var(--color-text-secondary)] text-sm mb-1"><TrendingUp className="w-4 h-4" /> ROI</div>
            <div className="text-2xl font-bold text-[var(--color-status-info)]">{roiPct != null ? `${roiPct}%` : '—'}</div>
          </div>
          <div className="bg-[var(--color-bg-panel)] border border-[var(--color-border-default)] chamfer-8 p-5">
            <div className="flex items-center gap-2 text-[var(--color-text-secondary)] text-sm mb-1"><Calculator className="w-4 h-4" /> Payback Period</div>
            <div className="text-2xl font-bold text-[var(--color-status-info)]">{roi?.payback_months ?? '—'} mo</div>
          </div>
          <div className="bg-[var(--color-bg-panel)] border border-[var(--color-border-default)] chamfer-8 p-5">
            <div className="flex items-center gap-2 text-[var(--color-text-secondary)] text-sm mb-1"><TrendingUp className="w-4 h-4" /> Revenue Uplift</div>
            <div className="text-2xl font-bold text-[var(--color-system-compliance)]">{formatCents(roi?.revenue_uplift_cents)}</div>
          </div>
        </div>

        {/* Efficiency Metrics */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <div className="bg-[var(--color-bg-panel)] border border-[var(--color-border-default)] chamfer-8 p-6">
            <h2 className="text-lg font-semibold mb-4 flex items-center gap-2">
              <BarChart3 className="w-5 h-5 text-[var(--color-status-active)]" /> Efficiency Breakdown
            </h2>
            <div className="space-y-4">
              <div className="flex justify-between items-center">
                <span className="text-[var(--color-text-secondary)]">Cost Reduction</span>
                <span className="text-[var(--color-status-active)] font-bold">{formatCents(roi?.cost_reduction_cents)}</span>
              </div>
              <div className="flex justify-between items-center">
                <span className="text-[var(--color-text-secondary)]">Efficiency Gain</span>
                <span className="text-[var(--color-status-info)] font-bold">{efficiencyGainPct != null ? `${efficiencyGainPct}%` : '—'}</span>
              </div>
              <div className="flex justify-between items-center">
                <span className="text-[var(--color-text-secondary)]">Annual Savings</span>
                <span className="text-[var(--color-status-info)] font-bold">{formatCents(roi?.annual_savings_cents)}</span>
              </div>
            </div>
          </div>
          <div className="bg-[var(--color-bg-panel)] border border-[var(--color-border-default)] chamfer-8 p-6">
            <h2 className="text-lg font-semibold mb-4 flex items-center gap-2">
              <Calculator className="w-5 h-5 text-[var(--color-system-compliance)]" /> Model Parameters
            </h2>
            <div className="space-y-3 text-sm">
              <div className="flex justify-between"><span className="text-[var(--color-text-secondary)]">Agency Type</span><span className="text-white">EMS</span></div>
              <div className="flex justify-between"><span className="text-[var(--color-text-secondary)]">Monthly Call Volume</span><span className="text-white">500</span></div>
              <div className="flex justify-between"><span className="text-[var(--color-text-secondary)]">Crew Count</span><span className="text-white">20</span></div>
              <div className="flex justify-between"><span className="text-[var(--color-text-secondary)]">ROI Timeframe</span><span className="text-white">{roi?.payback_months ?? '—'} months</span></div>
            </div>
          </div>
        </div>

        {/* Per-Tenant Margin Table */}
        <div className="bg-[var(--color-bg-panel)] border border-[var(--color-border-default)] chamfer-8 overflow-hidden">
          <div className="px-6 py-4 border-b border-[var(--color-border-default)]">
            <h2 className="text-lg font-semibold flex items-center gap-2">
              <DollarSign className="w-5 h-5 text-[var(--q-yellow)]" /> Per-Tenant Margin Risk
            </h2>
          </div>
          {margins.length === 0 ? (
            <div className="p-12 text-center text-[var(--color-text-muted)]">No tenant margin data available yet.</div>
          ) : (
            <table className="w-full text-sm">
              <thead className="bg-[var(--color-bg-raised)]">
                <tr>
                  <th className="text-left px-6 py-3 text-[var(--color-text-secondary)] font-medium">Tenant</th>
                  <th className="text-left px-6 py-3 text-[var(--color-text-secondary)] font-medium">Revenue</th>
                  <th className="text-left px-6 py-3 text-[var(--color-text-secondary)] font-medium">Cost</th>
                  <th className="text-left px-6 py-3 text-[var(--color-text-secondary)] font-medium">Margin</th>
                  <th className="text-left px-6 py-3 text-[var(--color-text-secondary)] font-medium">Risk</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-800">
                {margins.map((t) => (
                  <tr key={t.tenant_id} className="hover:bg-[var(--color-bg-raised)]/30">
                    <td className="px-6 py-3 text-white font-medium">{t.tenant_name ?? t.tenant_id}</td>
                    <td className="px-6 py-3 text-[var(--color-status-active)]">{formatCents(t.revenue_cents)}</td>
                    <td className="px-6 py-3 text-[var(--color-brand-red)]">{formatCents(t.cost_cents)}</td>
                    <td className="px-6 py-3 text-[var(--color-status-info)] font-bold">{t.margin_pct != null ? `${t.margin_pct}%` : '—'}</td>
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
