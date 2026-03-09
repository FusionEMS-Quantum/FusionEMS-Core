'use client';

import { useEffect, useState } from 'react';
import { AlertTriangle, ArrowLeft, BarChart3, Clock, DollarSign, FileText, RefreshCw, Shield, TrendingUp } from 'lucide-react';
import Link from 'next/link';
import {
  getBillingExecutiveSummary,
  getBillingHealth,
  getBillingAlerts,
  getBillingKPIs,
} from '@/services/api';

interface ExecSummary {
  total_claims?: number;
  paid_claims?: number;
  denied_claims?: number;
  pending_claims?: number;
  revenue_cents?: number;
  clean_claim_rate_pct?: number;
  denial_rate_pct?: number;
  appeal_count?: number;
  collection_rate_pct?: number;
  avg_days_to_payment?: number;
  as_of?: string;
}

interface HealthData {
  score?: number;
  grade?: string;
  factors?: { name: string; status: string; detail?: string }[];
  as_of?: string;
}

interface AlertItem {
  type?: string;
  severity?: string;
  message?: string;
  metric?: string;
  value?: number;
  threshold?: number;
}

export default function DailyBriefPage() {
  const [summary, setSummary] = useState<ExecSummary | null>(null);
  const [health, setHealth] = useState<HealthData | null>(null);
  const [alerts, setAlerts] = useState<AlertItem[]>([]);
  const [kpis, setKpis] = useState<Record<string, unknown> | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const loadData = async () => {
    setLoading(true);
    setError(null);
    try {
      const [sumRes, healthRes, alertRes, kpiRes] = await Promise.allSettled([
        getBillingExecutiveSummary(),
        getBillingHealth(),
        getBillingAlerts(),
        getBillingKPIs(),
      ]);
      if (sumRes.status === 'fulfilled') setSummary(sumRes.value);
      if (healthRes.status === 'fulfilled') setHealth(healthRes.value);
      if (alertRes.status === 'fulfilled') {
        const ad = alertRes.value;
        setAlerts(Array.isArray(ad?.alerts) ? ad.alerts : Array.isArray(ad) ? ad : []);
      }
      if (kpiRes.status === 'fulfilled') setKpis(kpiRes.value);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load briefing');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { loadData(); }, []);

  const formatCents = (cents: number | undefined) =>
    cents != null ? `$${(cents / 100).toLocaleString('en-US', { minimumFractionDigits: 2 })}` : '$0.00';

  const severityColor = (sev?: string) => {
    if (sev === 'critical') return 'text-red-400 bg-red-900/20';
    if (sev === 'high') return 'text-orange-400 bg-orange-900/20';
    if (sev === 'medium') return 'text-amber-400 bg-amber-900/20';
    return 'text-blue-400 bg-blue-900/20';
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
        {/* Header */}
        <div className="flex items-center justify-between">
          <div>
            <Link href="/founder/executive" className="text-gray-400 hover:text-white flex items-center gap-1 text-sm mb-2">
              <ArrowLeft className="w-4 h-4" /> Back to Executive
            </Link>
            <h1 className="text-3xl font-bold flex items-center gap-3">
              <FileText className="w-8 h-8 text-blue-400" />
              Executive Daily Brief
            </h1>
            <p className="text-gray-400 mt-1">Automated operational intelligence — {summary?.as_of ?? new Date().toISOString().split('T')[0]}</p>
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

        {/* Billing Health Score */}
        <div className="bg-gray-900 border border-gray-800 rounded-lg p-6">
          <h2 className="text-lg font-semibold mb-4 flex items-center gap-2">
            <Shield className="w-5 h-5 text-emerald-400" /> Billing Health Score
          </h2>
          {health ? (
            <div className="flex items-center gap-8">
              <div className="text-center">
                <div className={`text-5xl font-bold ${(health.score ?? 0) >= 80 ? 'text-emerald-400' : (health.score ?? 0) >= 60 ? 'text-amber-400' : 'text-red-400'}`}>
                  {health.score ?? 0}
                </div>
                <div className="text-gray-400 text-sm mt-1">Score</div>
              </div>
              <div className="text-center">
                <div className="text-3xl font-bold text-blue-400">{health.grade ?? 'N/A'}</div>
                <div className="text-gray-400 text-sm mt-1">Grade</div>
              </div>
              {health.factors && health.factors.length > 0 && (
                <div className="flex-1 grid grid-cols-2 gap-2">
                  {health.factors.slice(0, 6).map((f, i) => (
                    <div key={i} className="text-sm flex items-center gap-2">
                      <span className={f.status === 'healthy' ? 'text-emerald-400' : 'text-amber-400'}>●</span>
                      <span className="text-gray-300">{f.name}</span>
                    </div>
                  ))}
                </div>
              )}
            </div>
          ) : (
            <div className="text-gray-500">Health score unavailable</div>
          )}
        </div>

        {/* Key Metrics */}
        <div className="grid grid-cols-1 md:grid-cols-5 gap-4">
          <div className="bg-gray-900 border border-gray-800 rounded-lg p-4">
            <div className="flex items-center gap-2 text-gray-400 text-xs mb-1"><DollarSign className="w-3.5 h-3.5" /> Revenue</div>
            <div className="text-xl font-bold text-emerald-400">{formatCents(summary?.revenue_cents)}</div>
          </div>
          <div className="bg-gray-900 border border-gray-800 rounded-lg p-4">
            <div className="flex items-center gap-2 text-gray-400 text-xs mb-1"><BarChart3 className="w-3.5 h-3.5" /> Total Claims</div>
            <div className="text-xl font-bold text-blue-400">{summary?.total_claims ?? 0}</div>
          </div>
          <div className="bg-gray-900 border border-gray-800 rounded-lg p-4">
            <div className="flex items-center gap-2 text-gray-400 text-xs mb-1"><TrendingUp className="w-3.5 h-3.5" /> Clean Rate</div>
            <div className="text-xl font-bold text-cyan-400">{summary?.clean_claim_rate_pct ?? 0}%</div>
          </div>
          <div className="bg-gray-900 border border-gray-800 rounded-lg p-4">
            <div className="flex items-center gap-2 text-gray-400 text-xs mb-1"><AlertTriangle className="w-3.5 h-3.5" /> Denial Rate</div>
            <div className="text-xl font-bold text-amber-400">{summary?.denial_rate_pct ?? 0}%</div>
          </div>
          <div className="bg-gray-900 border border-gray-800 rounded-lg p-4">
            <div className="flex items-center gap-2 text-gray-400 text-xs mb-1"><Clock className="w-3.5 h-3.5" /> Avg Days to Pay</div>
            <div className="text-xl font-bold text-violet-400">{summary?.avg_days_to_payment ?? '—'}</div>
          </div>
        </div>

        {/* Active Alerts */}
        <div className="bg-gray-900 border border-gray-800 rounded-lg p-6">
          <h2 className="text-lg font-semibold mb-4 flex items-center gap-2">
            <AlertTriangle className="w-5 h-5 text-amber-400" /> Active Alerts
          </h2>
          {alerts.length > 0 ? (
            <div className="space-y-2">
              {alerts.map((a, i) => (
                <div key={i} className={`rounded-lg px-4 py-3 flex items-center justify-between ${severityColor(a.severity)}`}>
                  <div className="flex items-center gap-3">
                    <span className="text-xs font-mono uppercase">{a.severity ?? 'info'}</span>
                    <span className="text-sm">{a.message ?? a.metric ?? 'Alert'}</span>
                  </div>
                  {a.value != null && (
                    <span className="text-xs font-mono">
                      {a.value}{a.threshold != null ? ` / ${a.threshold}` : ''}
                    </span>
                  )}
                </div>
              ))}
            </div>
          ) : (
            <div className="text-emerald-400 text-sm">No active alerts — all systems nominal</div>
          )}
        </div>

        {/* KPI Snapshot */}
        {kpis && (
          <div className="bg-gray-900 border border-gray-800 rounded-lg p-6">
            <h2 className="text-lg font-semibold mb-4 flex items-center gap-2">
              <BarChart3 className="w-5 h-5 text-cyan-400" /> Billing KPIs
            </h2>
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
              {Object.entries(kpis).filter(([k]) => k !== 'as_of').slice(0, 8).map(([key, val]) => (
                <div key={key}>
                  <div className="text-gray-400 text-xs">{key.replace(/_/g, ' ')}</div>
                  <div className="text-sm font-semibold text-gray-200">{typeof val === 'number' ? val.toLocaleString() : String(val ?? '—')}</div>
                </div>
              ))}
            </div>
          </div>
        )}

        <div className="text-center text-gray-600 text-xs">
          Brief generated: {summary?.as_of ?? health?.as_of ?? 'N/A'}
        </div>
      </div>
    </div>
  );
}
