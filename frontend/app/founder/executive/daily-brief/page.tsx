'use client';

import { useEffect, useState, useMemo } from 'react';
import { AlertTriangle, ArrowLeft, RefreshCw, Shield, TrendingUp, TrendingDown, Clock, Activity, Zap } from 'lucide-react';
import Link from 'next/link';
import { motion, AnimatePresence } from 'framer-motion';
import { QuantumCardSkeleton } from '@/components/ui';
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

function formatCents(cents: number | undefined): string {
  return cents != null
    ? `$${(cents / 100).toLocaleString('en-US', { minimumFractionDigits: 2 })}`
    : '$0.00';
}

function HealthGauge({ score, grade }: { score: number; grade?: string }) {
  const pct = Math.max(0, Math.min(100, score));
  const color = pct >= 80 ? 'var(--color-status-active)' : pct >= 60 ? 'var(--q-yellow)' : 'var(--color-brand-red)';
  const circumference = 2 * Math.PI * 52;
  const offset = circumference - (pct / 100) * circumference;
  return (
    <div className="relative w-32 h-32 flex-shrink-0">
      <svg viewBox="0 0 120 120" className="w-full h-full -rotate-90">
        <circle cx="60" cy="60" r="52" fill="none" stroke="var(--color-border-subtle)" strokeWidth="8" />
        <circle
          cx="60" cy="60" r="52" fill="none" stroke={color} strokeWidth="8"
          strokeDasharray={circumference} strokeDashoffset={offset}
          strokeLinecap="butt" className="transition-all duration-slow"
        />
      </svg>
      <div className="absolute inset-0 flex flex-col items-center justify-center">
        <span className="text-h1 font-bold" style={{ color }}>{pct}</span>
        {grade && <span className="text-micro font-label uppercase tracking-wider text-[var(--color-text-muted)]">{grade}</span>}
      </div>
    </div>
  );
}

function MetricPlate({ label, value, accent, trend }: { label: string; value: string; accent: string; trend?: 'up' | 'down' | 'flat' }) {
  return (
    <div className="bg-[var(--color-bg-panel)] border border-[var(--color-border-default)] chamfer-8 p-4 relative overflow-hidden group hover:border-[var(--color-border-strong)] transition-colors duration-fast">
      <div className="absolute top-0 left-0 right-0 h-0.5" style={{ backgroundColor: accent }} />
      <div className="flex items-center justify-between mb-2">
        <span className="text-micro font-label uppercase tracking-wider text-[var(--color-text-muted)]">{label}</span>
        {trend && (
          <span className={trend === 'up' ? 'text-[var(--color-status-active)]' : trend === 'down' ? 'text-[var(--color-brand-red)]' : 'text-[var(--color-text-disabled)]'}>
            {trend === 'up' ? <TrendingUp className="w-3.5 h-3.5" /> : trend === 'down' ? <TrendingDown className="w-3.5 h-3.5" /> : '—'}
          </span>
        )}
      </div>
      <div className="text-h2 font-bold text-[var(--color-text-primary)]">{value}</div>
    </div>
  );
}

function AlertRow({ alert, index }: { alert: AlertItem; index: number }) {
  const sev = alert.severity ?? 'info';
  const sevColor = sev === 'critical' ? 'var(--color-brand-red)' : sev === 'high' ? 'var(--q-orange)' : sev === 'medium' ? 'var(--q-yellow)' : 'var(--color-status-info)';
  return (
    <motion.div
      initial={{ opacity: 0, x: -8 }} animate={{ opacity: 1, x: 0 }}
      transition={{ delay: index * 0.04, duration: 0.2 }}
      className="flex items-center gap-3 p-3 bg-[var(--color-bg-panel)] border border-[var(--color-border-default)] chamfer-4 hover:bg-[var(--color-bg-overlay)] transition-colors duration-fast"
    >
      <div className="w-1 h-8 chamfer-4 flex-shrink-0" style={{ backgroundColor: sevColor }} />
      <span
        className="text-micro font-label uppercase tracking-wider px-2 py-0.5 chamfer-4 flex-shrink-0"
        style={{ color: sevColor, backgroundColor: `color-mix(in srgb, ${sevColor} 12%, transparent)` }}
      >
        {sev}
      </span>
      <span className="text-body text-[var(--color-text-primary)] flex-1 truncate">{alert.message ?? alert.metric ?? 'Alert'}</span>
      {alert.value != null && (
        <span className="text-micro font-mono text-[var(--color-text-muted)] flex-shrink-0">
          {alert.value}{alert.threshold != null ? ` / ${alert.threshold}` : ''}
        </span>
      )}
    </motion.div>
  );
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

  const briefDate = summary?.as_of ?? health?.as_of ?? new Date().toISOString().split('T')[0];

  const criticalAlerts = useMemo(() => alerts.filter(a => a.severity === 'critical' || a.severity === 'high'), [alerts]);
  const otherAlerts = useMemo(() => alerts.filter(a => a.severity !== 'critical' && a.severity !== 'high'), [alerts]);

  /* AI-generated narrative summary from available data */
  const narrative = useMemo(() => {
    const parts: string[] = [];
    if (health?.score != null) {
      const grade = health.score >= 80 ? 'strong' : health.score >= 60 ? 'moderate' : 'critical attention';
      parts.push(`Billing health is at ${health.score}/100 (${grade}).`);
    }
    if (summary?.revenue_cents != null) parts.push(`Revenue this period: ${formatCents(summary.revenue_cents)}.`);
    if (summary?.denial_rate_pct != null && summary.denial_rate_pct > 5)
      parts.push(`Denial rate at ${summary.denial_rate_pct}% — above acceptable threshold.`);
    if (summary?.clean_claim_rate_pct != null && summary.clean_claim_rate_pct < 95)
      parts.push(`Clean claim rate at ${summary.clean_claim_rate_pct}% — needs improvement.`);
    if (criticalAlerts.length > 0) parts.push(`${criticalAlerts.length} critical/high alert${criticalAlerts.length > 1 ? 's' : ''} require immediate action.`);
    if (parts.length === 0) parts.push('All systems nominal. No anomalies detected in latest telemetry cycle.');
    return parts.join(' ');
  }, [health, summary, criticalAlerts]);

  if (loading) {
    return (
      <div className="flex flex-col gap-4 p-6">
        <QuantumCardSkeleton />
        <div className="grid grid-cols-2 md:grid-cols-5 gap-3">
          {Array.from({ length: 5 }).map((_, i) => <QuantumCardSkeleton key={i} />)}
        </div>
        <QuantumCardSkeleton />
        <QuantumCardSkeleton />
      </div>
    );
  }

  return (
    <div className="flex flex-col h-full min-h-0">
      {/* Header */}
      <header className="flex-shrink-0 px-4 pt-4 pb-2 xl:px-6">
        <div className="flex items-start justify-between gap-4">
          <div className="min-w-0">
            <Link href="/founder/executive" className="text-[var(--color-text-muted)] hover:text-[var(--color-text-primary)] flex items-center gap-1 text-micro font-label uppercase tracking-wider mb-3 transition-colors duration-fast">
              <ArrowLeft className="w-3.5 h-3.5" /> Executive Command
            </Link>
            <div className="flex items-center gap-3">
              <div className="w-1 h-6 chamfer-4 flex-shrink-0 bg-[var(--q-orange)]" />
              <h1 className="text-h1 font-sans font-bold text-[var(--color-text-primary)]">Daily AI Brief</h1>
            </div>
            <p className="text-body text-[var(--color-text-muted)] mt-1 ml-4">
              Automated operational intelligence — {briefDate}
            </p>
          </div>
          <button onClick={loadData} className="quantum-btn flex items-center gap-2">
            <RefreshCw className="w-3.5 h-3.5" /> Refresh
          </button>
        </div>
      </header>

      {/* Content */}
      <div className="flex-1 min-h-0 overflow-y-auto px-4 py-4 xl:px-6 space-y-5">
        {/* Error banner */}
        <AnimatePresence>
          {error && (
            <motion.div
              initial={{ opacity: 0, y: -8 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0, y: -8 }}
              className="flex items-center gap-3 p-4 bg-[var(--color-brand-red-ghost)] border border-[var(--color-brand-red)] chamfer-8"
            >
              <AlertTriangle className="w-5 h-5 text-[var(--color-brand-red)] flex-shrink-0" />
              <span className="text-body text-[var(--color-text-primary)]">{error}</span>
            </motion.div>
          )}
        </AnimatePresence>

        {/* AI Narrative + Health Gauge */}
        <div className="bg-[var(--color-bg-panel)] border border-[var(--color-border-default)] chamfer-12 p-5 hud-rail">
          <div className="flex items-start gap-6">
            {/* Health Gauge */}
            {health?.score != null && <HealthGauge score={health.score} grade={health.grade} />}

            {/* Narrative */}
            <div className="flex-1 min-w-0">
              <div className="flex items-center gap-2 mb-3">
                <Zap className="w-4 h-4 text-[var(--q-orange)]" />
                <span className="label-caps">AI Intelligence Summary</span>
              </div>
              <p className="text-body-lg text-[var(--color-text-primary)] leading-relaxed">{narrative}</p>

              {/* Health Factors */}
              {health?.factors && health.factors.length > 0 && (
                <div className="mt-4 grid grid-cols-2 lg:grid-cols-3 gap-2">
                  {health.factors.slice(0, 6).map((f, i) => (
                    <div key={i} className="flex items-center gap-2 text-body">
                      <span className="w-1.5 h-1.5" style={{
                        backgroundColor: f.status === 'healthy' ? 'var(--color-status-active)' : f.status === 'warning' ? 'var(--q-yellow)' : 'var(--color-brand-red)',
                      }} />
                      <span className="text-[var(--color-text-secondary)] truncate">{f.name}</span>
                    </div>
                  ))}
                </div>
              )}
            </div>
          </div>
        </div>

        {/* KPI Metric Plates */}
        <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-5 gap-3">
          <MetricPlate
            label="Revenue" value={formatCents(summary?.revenue_cents)}
            accent="var(--color-status-active)"
            trend={summary?.revenue_cents != null && summary.revenue_cents > 0 ? 'up' : 'flat'}
          />
          <MetricPlate
            label="Total Claims" value={String(summary?.total_claims ?? '—')}
            accent="var(--color-system-billing)"
          />
          <MetricPlate
            label="Clean Claim Rate"
            value={summary?.clean_claim_rate_pct != null ? `${summary.clean_claim_rate_pct}%` : '—'}
            accent="var(--color-status-info)"
            trend={summary?.clean_claim_rate_pct != null && summary.clean_claim_rate_pct >= 95 ? 'up' : summary?.clean_claim_rate_pct != null ? 'down' : undefined}
          />
          <MetricPlate
            label="Denial Rate"
            value={summary?.denial_rate_pct != null ? `${summary.denial_rate_pct}%` : '—'}
            accent="var(--q-yellow)"
            trend={summary?.denial_rate_pct != null && summary.denial_rate_pct > 5 ? 'down' : summary?.denial_rate_pct != null ? 'up' : undefined}
          />
          <MetricPlate
            label="Days to Payment"
            value={summary?.avg_days_to_payment != null ? `${summary.avg_days_to_payment}d` : '—'}
            accent="var(--color-system-compliance)"
          />
        </div>

        {/* Alert Panels — split critical from non-critical */}
        <div className="grid grid-cols-1 xl:grid-cols-2 gap-4">
          {/* Critical/High Alerts */}
          <div className="bg-[var(--color-bg-panel)] border border-[var(--color-border-default)] chamfer-8 p-4">
            <div className="flex items-center gap-2 mb-3">
              <AlertTriangle className="w-4 h-4 text-[var(--color-brand-red)]" />
              <span className="label-caps">Priority Alerts</span>
              {criticalAlerts.length > 0 && (
                <span className="text-micro font-label px-1.5 py-0.5 chamfer-4 bg-[var(--color-brand-red-ghost)] text-[var(--color-brand-red)]">
                  {criticalAlerts.length}
                </span>
              )}
            </div>
            {criticalAlerts.length > 0 ? (
              <div className="space-y-2">
                {criticalAlerts.map((a, i) => <AlertRow key={i} alert={a} index={i} />)}
              </div>
            ) : (
              <div className="flex items-center gap-2 py-4 text-body text-[var(--color-status-active)]">
                <Shield className="w-4 h-4" /> No critical alerts — systems nominal
              </div>
            )}
          </div>

          {/* Standard Alerts */}
          <div className="bg-[var(--color-bg-panel)] border border-[var(--color-border-default)] chamfer-8 p-4">
            <div className="flex items-center gap-2 mb-3">
              <Activity className="w-4 h-4 text-[var(--color-status-info)]" />
              <span className="label-caps">Operational Notices</span>
              {otherAlerts.length > 0 && (
                <span className="text-micro font-label px-1.5 py-0.5 chamfer-4 bg-[var(--color-bg-overlay)] text-[var(--color-text-muted)]">
                  {otherAlerts.length}
                </span>
              )}
            </div>
            {otherAlerts.length > 0 ? (
              <div className="space-y-2">
                {otherAlerts.map((a, i) => <AlertRow key={i} alert={a} index={i} />)}
              </div>
            ) : (
              <div className="py-4 text-body text-[var(--color-text-muted)]">No additional notices</div>
            )}
          </div>
        </div>

        {/* KPI Deep Dive */}
        {kpis && (
          <div className="bg-[var(--color-bg-panel)] border border-[var(--color-border-default)] chamfer-8 p-4">
            <div className="flex items-center gap-2 mb-3">
              <Clock className="w-4 h-4 text-[var(--color-system-billing)]" />
              <span className="label-caps">Billing KPI Telemetry</span>
            </div>
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
              {Object.entries(kpis).filter(([k]) => k !== 'as_of').slice(0, 8).map(([key, val]) => (
                <div key={key} className="border-l-2 border-[var(--color-border-subtle)] pl-3 py-1">
                  <div className="text-micro font-label uppercase tracking-wider text-[var(--color-text-muted)]">{key.replace(/_/g, ' ')}</div>
                  <div className="text-body font-semibold text-[var(--color-text-primary)]">
                    {typeof val === 'number' ? val.toLocaleString() : String(val ?? '—')}
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Footer */}
        <div className="text-center text-micro text-[var(--color-text-disabled)] pb-4">
          Brief generated: {briefDate} · AI intelligence cycle complete
        </div>
      </div>
    </div>
  );
}
