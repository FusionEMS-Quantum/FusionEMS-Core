'use client';

import { useEffect, useState } from 'react';
import Link from 'next/link';
import { ArrowLeft, DollarSign, RefreshCw, AlertTriangle, TrendingDown, PieChart, Building2 } from 'lucide-react';
import { getCostBudget, getCostByTenant } from '@/services/api';

interface CostBudget { budget_limit_cents?: number; current_spend_cents?: number; forecast_cents?: number; period?: string; utilization_pct?: number; alerts?: { message: string; threshold_pct: number }[]; }
interface TenantCost { tenant_id: string; tenant_name?: string; cost_cents?: number; pct_of_total?: number; service_breakdown?: Record<string, number>; }

export default function CostExplorerPage() {
  const [budget, setBudget] = useState<CostBudget | null>(null);
  const [tenantCosts, setTenantCosts] = useState<TenantCost[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const loadData = async () => {
    setLoading(true);
    setError(null);
    try {
      const [bRes, tRes] = await Promise.allSettled([getCostBudget(), getCostByTenant()]);
      if (bRes.status === 'fulfilled') setBudget(bRes.value);
      if (tRes.status === 'fulfilled') {
        const t = tRes.value;
        setTenantCosts(Array.isArray(t?.tenants) ? t.tenants : Array.isArray(t) ? t : []);
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load cost data');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { loadData(); }, []);

  const formatCents = (cents: number | undefined) =>
    cents != null ? `$${(cents / 100).toLocaleString('en-US', { minimumFractionDigits: 2 })}` : '$0.00';

  if (loading) return <div className="min-h-screen bg-[var(--color-bg-base)] text-white flex items-center justify-center"><RefreshCw className="w-8 h-8 animate-spin text-[var(--color-status-active)]" /></div>;

  return (
    <div className="min-h-screen bg-[var(--color-bg-base)] text-white p-6">
      <div className="max-w-7xl mx-auto space-y-8">
        <div className="flex items-center justify-between">
          <div>
            <Link href="/founder/infra" className="text-[var(--color-text-secondary)] hover:text-[var(--color-text-primary)] flex items-center gap-1 text-sm mb-2"><ArrowLeft className="w-4 h-4" /> Infrastructure Hub</Link>
            <h1 className="text-3xl font-bold flex items-center gap-3"><DollarSign className="w-8 h-8 text-[var(--color-status-active)]" /> AWS Cost Explorer</h1>
            <p className="text-[var(--color-text-secondary)] mt-1">Cloud spend monitoring, budget tracking, and per-tenant cost allocation</p>
          </div>
          <button onClick={loadData} className="px-4 py-2 bg-[var(--color-bg-raised)] hover:bg-[var(--color-bg-overlay)] chamfer-8 flex items-center gap-2 text-sm"><RefreshCw className="w-4 h-4" /> Refresh</button>
        </div>

        {error && <div className="bg-red-900/30 border border-[var(--color-brand-red)] chamfer-8 p-4 flex items-center gap-3"><AlertTriangle className="w-5 h-5 text-[var(--color-brand-red)]" /><span className="text-[var(--color-brand-red)]">{error}</span></div>}

        <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
          <div className="bg-[var(--color-bg-panel)] border border-[var(--color-border-default)] chamfer-8 p-5">
            <div className="text-[var(--color-text-secondary)] text-sm mb-1 flex items-center gap-1"><DollarSign className="w-4 h-4" /> Current Spend</div>
            <div className="text-2xl font-bold text-[var(--color-status-active)]">{formatCents(budget?.current_spend_cents)}</div>
          </div>
          <div className="bg-[var(--color-bg-panel)] border border-[var(--color-border-default)] chamfer-8 p-5">
            <div className="text-[var(--color-text-secondary)] text-sm mb-1 flex items-center gap-1"><TrendingDown className="w-4 h-4" /> Forecast</div>
            <div className="text-2xl font-bold text-[var(--color-status-info)]">{formatCents(budget?.forecast_cents)}</div>
          </div>
          <div className="bg-[var(--color-bg-panel)] border border-[var(--color-border-default)] chamfer-8 p-5">
            <div className="text-[var(--color-text-secondary)] text-sm mb-1 flex items-center gap-1"><PieChart className="w-4 h-4" /> Budget Limit</div>
            <div className="text-2xl font-bold text-[var(--color-system-compliance)]">{formatCents(budget?.budget_limit_cents)}</div>
          </div>
          <div className="bg-[var(--color-bg-panel)] border border-[var(--color-border-default)] chamfer-8 p-5">
            <div className="text-[var(--color-text-secondary)] text-sm mb-1 flex items-center gap-1"><PieChart className="w-4 h-4" /> Utilization</div>
            <div className={`text-2xl font-bold ${(budget?.utilization_pct ?? 0) > 90 ? 'text-[var(--color-brand-red)]' : (budget?.utilization_pct ?? 0) > 75 ? 'text-[var(--q-yellow)]' : 'text-[var(--color-status-active)]'}`}>{budget?.utilization_pct ?? 0}%</div>
          </div>
        </div>

        {/* Budget Alerts */}
        {budget?.alerts && budget.alerts.length > 0 && (
          <div className="bg-amber-900/20 border border-amber-700 chamfer-8 p-4">
            <h3 className="text-sm font-semibold text-[var(--q-yellow)] mb-2">Budget Alerts</h3>
            {budget.alerts.map((a, i) => (
              <div key={i} className="text-sm text-[var(--q-yellow)]">{a.message} ({a.threshold_pct}% threshold)</div>
            ))}
          </div>
        )}

        {/* Per-Tenant Cost */}
        <div className="bg-[var(--color-bg-panel)] border border-[var(--color-border-default)] chamfer-8 overflow-hidden">
          <div className="px-6 py-4 border-b border-[var(--color-border-default)]"><h2 className="text-lg font-semibold flex items-center gap-2"><Building2 className="w-5 h-5 text-[var(--color-status-info)]" /> Per-Tenant Cost Allocation</h2></div>
          {tenantCosts.length === 0 ? (
            <div className="p-12 text-center text-[var(--color-text-muted)]">No tenant cost allocation data available. Data will populate when AWS Cost Explorer integration is active.</div>
          ) : (
            <table className="w-full text-sm">
              <thead className="bg-[var(--color-bg-raised)]/50">
                <tr>
                  <th className="text-left px-6 py-3 text-[var(--color-text-secondary)] font-medium">Tenant</th>
                  <th className="text-left px-6 py-3 text-[var(--color-text-secondary)] font-medium">Cost</th>
                  <th className="text-left px-6 py-3 text-[var(--color-text-secondary)] font-medium">% of Total</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-800">
                {tenantCosts.map((t) => (
                  <tr key={t.tenant_id} className="hover:bg-[var(--color-bg-raised)]/30">
                    <td className="px-6 py-3 text-white font-medium">{t.tenant_name ?? t.tenant_id}</td>
                    <td className="px-6 py-3 text-[var(--color-status-active)] font-bold">{formatCents(t.cost_cents)}</td>
                    <td className="px-6 py-3 text-[var(--color-status-info)]">{t.pct_of_total ?? 0}%</td>
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
