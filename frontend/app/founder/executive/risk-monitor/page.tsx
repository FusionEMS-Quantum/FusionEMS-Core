'use client';

import { useEffect, useState } from 'react';
import { AlertTriangle, ArrowLeft, RefreshCw, Shield, ShieldAlert, TrendingDown, Users } from 'lucide-react';
import Link from 'next/link';
import {
  getChurnRisk,
  getBillingAlerts,
  getARConcentrationRisk,
  getFraudAnomalies,
  getMarginRiskByTenant,
} from '@/services/api';

interface ChurnSignal {
  tenant_id?: string;
  name?: string;
  risk_score?: number;
  signals?: string[];
  last_activity?: string;
}

interface AlertItem {
  type?: string;
  severity?: string;
  message?: string;
  metric?: string;
}

interface ARRisk {
  payer_name?: string;
  exposure_cents?: number;
  concentration_pct?: number;
  aging_bucket?: string;
}

interface FraudAnomaly {
  claim_id?: string;
  anomaly_type?: string;
  confidence?: number;
  detail?: string;
}

interface MarginTenant {
  tenant_id?: string;
  name?: string;
  risk_level?: string;
  margin_pct?: number;
  denial_rate_pct?: number;
  revenue_cents?: number;
}

export default function RiskMonitorPage() {
  const [churn, setChurn] = useState<ChurnSignal[]>([]);
  const [alerts, setAlerts] = useState<AlertItem[]>([]);
  const [arRisk, setArRisk] = useState<ARRisk[]>([]);
  const [fraud, setFraud] = useState<FraudAnomaly[]>([]);
  const [marginTenants, setMarginTenants] = useState<MarginTenant[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const loadData = async () => {
    setLoading(true);
    setError(null);
    try {
      const [churnRes, alertRes, arRes, fraudRes, marginRes] = await Promise.allSettled([
        getChurnRisk(),
        getBillingAlerts(),
        getARConcentrationRisk(),
        getFraudAnomalies(),
        getMarginRiskByTenant(),
      ]);
      if (churnRes.status === 'fulfilled') {
        const cd = churnRes.value;
        setChurn(Array.isArray(cd?.signals) ? cd.signals : Array.isArray(cd?.tenants) ? cd.tenants : Array.isArray(cd) ? cd : []);
      }
      if (alertRes.status === 'fulfilled') {
        const ad = alertRes.value;
        setAlerts(Array.isArray(ad?.alerts) ? ad.alerts : Array.isArray(ad) ? ad : []);
      }
      if (arRes.status === 'fulfilled') {
        const ar = arRes.value;
        setArRisk(Array.isArray(ar?.payers) ? ar.payers : Array.isArray(ar) ? ar : []);
      }
      if (fraudRes.status === 'fulfilled') {
        const fd = fraudRes.value;
        setFraud(Array.isArray(fd?.anomalies) ? fd.anomalies : Array.isArray(fd) ? fd : []);
      }
      if (marginRes.status === 'fulfilled') {
        const md = marginRes.value;
        const highRisk = (Array.isArray(md?.tenants) ? md.tenants : [])
          .filter((t: MarginTenant) => t.risk_level === 'high' || t.risk_level === 'critical');
        setMarginTenants(highRisk);
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load risk data');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { loadData(); }, []);

  const riskColor = (level?: string) => {
    if (level === 'critical') return 'text-[var(--color-brand-red)]';
    if (level === 'high') return 'text-[var(--q-orange)]';
    if (level === 'medium') return 'text-[var(--q-yellow)]';
    return 'text-[var(--color-status-active)]';
  };

  const formatCents = (cents: number | undefined) =>
    cents != null ? `$${(cents / 100).toLocaleString('en-US', { minimumFractionDigits: 2 })}` : '$0.00';

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
        {/* Header */}
        <div className="flex items-center justify-between">
          <div>
            <Link href="/founder/executive" className="text-[var(--color-text-secondary)] hover:text-[var(--color-text-primary)] flex items-center gap-1 text-sm mb-2">
              <ArrowLeft className="w-4 h-4" /> Back to Executive
            </Link>
            <h1 className="text-3xl font-bold flex items-center gap-3">
              <ShieldAlert className="w-8 h-8 text-[var(--color-brand-red)]" />
              Risk Monitor
            </h1>
            <p className="text-[var(--color-text-secondary)] mt-1">Real-time risk intelligence — churn, revenue, compliance, fraud</p>
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

        {/* Risk Summary Cards */}
        <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
          <div className="bg-[var(--color-bg-panel)] border border-[var(--color-border-default)] chamfer-8 p-5 text-center">
            <Users className="w-6 h-6 text-[var(--q-yellow)] mx-auto mb-2" />
            <div className="text-2xl font-bold text-[var(--q-yellow)]">{churn.length}</div>
            <div className="text-[var(--color-text-secondary)] text-sm">Churn Signals</div>
          </div>
          <div className="bg-[var(--color-bg-panel)] border border-[var(--color-border-default)] chamfer-8 p-5 text-center">
            <AlertTriangle className="w-6 h-6 text-[var(--color-brand-red)] mx-auto mb-2" />
            <div className="text-2xl font-bold text-[var(--color-brand-red)]">{alerts.length}</div>
            <div className="text-[var(--color-text-secondary)] text-sm">Active Alerts</div>
          </div>
          <div className="bg-[var(--color-bg-panel)] border border-[var(--color-border-default)] chamfer-8 p-5 text-center">
            <TrendingDown className="w-6 h-6 text-[var(--q-orange)] mx-auto mb-2" />
            <div className="text-2xl font-bold text-[var(--q-orange)]">{marginTenants.length}</div>
            <div className="text-[var(--color-text-secondary)] text-sm">High-Risk Tenants</div>
          </div>
          <div className="bg-[var(--color-bg-panel)] border border-[var(--color-border-default)] chamfer-8 p-5 text-center">
            <Shield className="w-6 h-6 text-[var(--color-system-compliance)] mx-auto mb-2" />
            <div className="text-2xl font-bold text-[var(--color-system-compliance)]">{fraud.length}</div>
            <div className="text-[var(--color-text-secondary)] text-sm">Fraud Anomalies</div>
          </div>
        </div>

        {/* Churn Risk */}
        {churn.length > 0 && (
          <div className="bg-[var(--color-bg-panel)] border border-[var(--color-border-default)] chamfer-8 p-6">
            <h2 className="text-lg font-semibold mb-4 flex items-center gap-2">
              <Users className="w-5 h-5 text-[var(--q-yellow)]" /> Churn Risk Signals
            </h2>
            <div className="space-y-2">
              {churn.map((c, i) => (
                <div key={i} className="flex items-center justify-between bg-[var(--color-bg-raised)]/50 rounded px-4 py-3">
                  <div>
                    <span className="font-medium">{c.name ?? c.tenant_id ?? `Signal ${i + 1}`}</span>
                    {c.signals && <span className="text-[var(--color-text-secondary)] text-sm ml-3">{c.signals.join(', ')}</span>}
                  </div>
                  <span className={`font-mono text-sm ${(c.risk_score ?? 0) > 70 ? 'text-[var(--color-brand-red)]' : 'text-[var(--q-yellow)]'}`}>
                    {c.risk_score ?? 0}%
                  </span>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Margin-At-Risk Tenants */}
        {marginTenants.length > 0 && (
          <div className="bg-[var(--color-bg-panel)] border border-[var(--color-border-default)] chamfer-8 p-6">
            <h2 className="text-lg font-semibold mb-4 flex items-center gap-2">
              <TrendingDown className="w-5 h-5 text-[var(--q-orange)]" /> High-Risk Margin Tenants
            </h2>
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead><tr className="text-[var(--color-text-secondary)] border-b border-[var(--color-border-default)]">
                  <th className="text-left py-2">Tenant</th>
                  <th className="text-right py-2">Revenue</th>
                  <th className="text-right py-2">Margin</th>
                  <th className="text-right py-2">Denial Rate</th>
                  <th className="text-right py-2">Risk</th>
                </tr></thead>
                <tbody>
                  {marginTenants.map((t, i) => (
                    <tr key={i} className="border-b border-[var(--color-border-default)]/50">
                      <td className="py-2">{t.name ?? 'Unknown'}</td>
                      <td className="py-2 text-right text-[var(--color-status-active)]">{formatCents(t.revenue_cents)}</td>
                      <td className="py-2 text-right">{t.margin_pct ?? 0}%</td>
                      <td className="py-2 text-right text-[var(--q-yellow)]">{t.denial_rate_pct ?? 0}%</td>
                      <td className={`py-2 text-right font-semibold uppercase ${riskColor(t.risk_level)}`}>{t.risk_level}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        )}

        {/* AR Concentration */}
        {arRisk.length > 0 && (
          <div className="bg-[var(--color-bg-panel)] border border-[var(--color-border-default)] chamfer-8 p-6">
            <h2 className="text-lg font-semibold mb-4">AR Concentration Risk</h2>
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead><tr className="text-[var(--color-text-secondary)] border-b border-[var(--color-border-default)]">
                  <th className="text-left py-2">Payer</th>
                  <th className="text-right py-2">Exposure</th>
                  <th className="text-right py-2">Concentration</th>
                  <th className="text-right py-2">Aging</th>
                </tr></thead>
                <tbody>
                  {arRisk.map((a, i) => (
                    <tr key={i} className="border-b border-[var(--color-border-default)]/50">
                      <td className="py-2">{a.payer_name ?? 'Unknown'}</td>
                      <td className="py-2 text-right text-[var(--color-status-active)]">{formatCents(a.exposure_cents)}</td>
                      <td className="py-2 text-right">{a.concentration_pct ?? 0}%</td>
                      <td className="py-2 text-right text-[var(--color-text-secondary)]">{a.aging_bucket ?? '—'}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        )}

        {/* Fraud Anomalies */}
        {fraud.length > 0 && (
          <div className="bg-[var(--color-bg-panel)] border border-[var(--color-border-default)] chamfer-8 p-6">
            <h2 className="text-lg font-semibold mb-4 flex items-center gap-2">
              <Shield className="w-5 h-5 text-[var(--color-system-compliance)]" /> Fraud Anomalies
            </h2>
            <div className="space-y-2">
              {fraud.map((f, i) => (
                <div key={i} className="flex items-center justify-between bg-[var(--color-bg-raised)]/50 rounded px-4 py-3">
                  <div>
                    <span className="font-mono text-sm text-[var(--color-text-secondary)]">{f.claim_id ?? '—'}</span>
                    <span className="ml-3 text-sm">{f.anomaly_type ?? f.detail ?? 'Anomaly detected'}</span>
                  </div>
                  <span className="text-sm font-mono text-[var(--color-system-compliance)]">{f.confidence != null ? `${(f.confidence * 100).toFixed(0)}%` : '—'}</span>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* No Risks State */}
        {churn.length === 0 && alerts.length === 0 && marginTenants.length === 0 && fraud.length === 0 && (
          <div className="bg-[var(--color-bg-panel)] border border-emerald-800 chamfer-8 p-8 text-center">
            <Shield className="w-12 h-12 text-[var(--color-status-active)] mx-auto mb-3" />
            <h3 className="text-lg font-semibold text-[var(--color-status-active)]">All Systems Nominal</h3>
            <p className="text-[var(--color-text-secondary)] mt-1">No active risk signals detected across all monitored domains.</p>
          </div>
        )}
      </div>
    </div>
  );
}
