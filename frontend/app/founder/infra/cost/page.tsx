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

  if (loading) return <div className="min-h-screen bg-gray-950 text-white flex items-center justify-center"><RefreshCw className="w-8 h-8 animate-spin text-emerald-400" /></div>;

  return (
    <div className="min-h-screen bg-gray-950 text-white p-6">
      <div className="max-w-7xl mx-auto space-y-8">
        <div className="flex items-center justify-between">
          <div>
            <Link href="/founder/infra" className="text-gray-400 hover:text-white flex items-center gap-1 text-sm mb-2"><ArrowLeft className="w-4 h-4" /> Infrastructure Hub</Link>
            <h1 className="text-3xl font-bold flex items-center gap-3"><DollarSign className="w-8 h-8 text-emerald-400" /> AWS Cost Explorer</h1>
            <p className="text-gray-400 mt-1">Cloud spend monitoring, budget tracking, and per-tenant cost allocation</p>
          </div>
          <button onClick={loadData} className="px-4 py-2 bg-gray-800 hover:bg-gray-700 rounded-lg flex items-center gap-2 text-sm"><RefreshCw className="w-4 h-4" /> Refresh</button>
        </div>

        {error && <div className="bg-red-900/30 border border-red-700 rounded-lg p-4 flex items-center gap-3"><AlertTriangle className="w-5 h-5 text-red-400" /><span className="text-red-300">{error}</span></div>}

        <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
          <div className="bg-gray-900 border border-gray-800 rounded-lg p-5">
            <div className="text-gray-400 text-sm mb-1 flex items-center gap-1"><DollarSign className="w-4 h-4" /> Current Spend</div>
            <div className="text-2xl font-bold text-emerald-400">{formatCents(budget?.current_spend_cents)}</div>
          </div>
          <div className="bg-gray-900 border border-gray-800 rounded-lg p-5">
            <div className="text-gray-400 text-sm mb-1 flex items-center gap-1"><TrendingDown className="w-4 h-4" /> Forecast</div>
            <div className="text-2xl font-bold text-blue-400">{formatCents(budget?.forecast_cents)}</div>
          </div>
          <div className="bg-gray-900 border border-gray-800 rounded-lg p-5">
            <div className="text-gray-400 text-sm mb-1 flex items-center gap-1"><PieChart className="w-4 h-4" /> Budget Limit</div>
            <div className="text-2xl font-bold text-violet-400">{formatCents(budget?.budget_limit_cents)}</div>
          </div>
          <div className="bg-gray-900 border border-gray-800 rounded-lg p-5">
            <div className="text-gray-400 text-sm mb-1 flex items-center gap-1"><PieChart className="w-4 h-4" /> Utilization</div>
            <div className={`text-2xl font-bold ${(budget?.utilization_pct ?? (() => { throw new Error('Unsafe silent fallback. Dependency missing.'); })()) > 90 ? 'text-red-400' : (budget?.utilization_pct ?? (() => { throw new Error('Unsafe silent fallback. Dependency missing.'); })()) > 75 ? 'text-amber-400' : 'text-emerald-400'}`}>{budget?.utilization_pct ?? (() => { throw new Error('Unsafe silent fallback. Dependency missing.'); })()}%</div>
          </div>
        </div>

        {/* Budget Alerts */}
        {budget?.alerts && budget.alerts.length > 0 && (
          <div className="bg-amber-900/20 border border-amber-700 rounded-lg p-4">
            <h3 className="text-sm font-semibold text-amber-400 mb-2">Budget Alerts</h3>
            {budget.alerts.map((a, i) => (
              <div key={i} className="text-sm text-amber-300">{a.message} ({a.threshold_pct}% threshold)</div>
            ))}
          </div>
        )}

        {/* Per-Tenant Cost */}
        <div className="bg-gray-900 border border-gray-800 rounded-lg overflow-hidden">
          <div className="px-6 py-4 border-b border-gray-800"><h2 className="text-lg font-semibold flex items-center gap-2"><Building2 className="w-5 h-5 text-cyan-400" /> Per-Tenant Cost Allocation</h2></div>
          {tenantCosts.length === 0 ? (
            <div className="p-12 text-center text-gray-500">No tenant cost allocation data available. Data will populate when AWS Cost Explorer integration is active.</div>
          ) : (
            <table className="w-full text-sm">
              <thead className="bg-gray-800/50">
                <tr>
                  <th className="text-left px-6 py-3 text-gray-400 font-medium">Tenant</th>
                  <th className="text-left px-6 py-3 text-gray-400 font-medium">Cost</th>
                  <th className="text-left px-6 py-3 text-gray-400 font-medium">% of Total</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-800">
                {tenantCosts.map((t) => (
                  <tr key={t.tenant_id} className="hover:bg-gray-800/30">
                    <td className="px-6 py-3 text-white font-medium">{t.tenant_name ?? t.tenant_id}</td>
                    <td className="px-6 py-3 text-emerald-400 font-bold">{formatCents(t.cost_cents)}</td>
                    <td className="px-6 py-3 text-cyan-400">{t.pct_of_total ?? (() => { throw new Error('Unsafe silent fallback. Dependency missing.'); })()}%</td>
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
