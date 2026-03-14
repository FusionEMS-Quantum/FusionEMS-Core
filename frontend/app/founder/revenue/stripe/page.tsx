'use client';

import { useEffect, useState, useMemo } from 'react';
import { AlertTriangle, ArrowLeft, CreditCard, DollarSign, RefreshCw, TrendingUp, Users, BarChart3, ShieldCheck, ShieldAlert } from 'lucide-react';
import Link from 'next/link';
import { motion, AnimatePresence } from 'framer-motion';
import { QuantumCardSkeleton } from '@/components/ui';
import { ModuleDashboardShell } from '@/components/shells/PageShells';
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

function MetricPlate({ label, value, accent, icon: Icon }: { label: string; value: string; accent: string; icon?: typeof DollarSign }) {
  return (
    <div className="bg-[var(--color-bg-panel)] border border-[var(--color-border-default)] chamfer-8 p-4 relative overflow-hidden hover:border-[var(--color-border-strong)] transition-colors duration-fast">
      <div className="absolute top-0 left-0 right-0 h-0.5" style={{ backgroundColor: accent }} />
      <div className="flex items-center gap-2 mb-2">
        {Icon && <Icon className="w-3.5 h-3.5 text-[var(--color-text-muted)]" />}
        <span className="text-micro font-label uppercase tracking-wider text-[var(--color-text-muted)]">{label}</span>
      </div>
      <div className="text-h2 font-bold text-[var(--color-text-primary)]">{value}</div>
    </div>
  );
}

function ReconStatusBadge({ status }: { status: string }) {
  const matched = status === 'matched' || status === 'reconciled';
  return (
    <span className="text-micro font-label uppercase tracking-wider px-2 py-0.5 chamfer-4 inline-flex items-center gap-1.5"
      style={{
        color: matched ? 'var(--color-status-active)' : 'var(--q-yellow)',
        backgroundColor: matched
          ? 'color-mix(in srgb, var(--color-status-active) 12%, transparent)'
          : 'color-mix(in srgb, var(--q-yellow) 12%, transparent)',
      }}>
      {matched ? <ShieldCheck className="w-3 h-3" /> : <ShieldAlert className="w-3 h-3" />}
      {status}
    </span>
  );
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
    cents != null && Number.isFinite(cents) ? `$${(cents / 100).toLocaleString('en-US', { minimumFractionDigits: 2 })}` : '—';

  const paidClaims = typeof dashboard?.paid_claims === 'number' && Number.isFinite(dashboard.paid_claims) ? dashboard.paid_claims : null;
  const denialRatePct = typeof dashboard?.denial_rate_pct === 'number' && Number.isFinite(dashboard.denial_rate_pct) ? dashboard.denial_rate_pct : null;
  const cleanClaimRatePct = typeof dashboard?.clean_claim_rate_pct === 'number' && Number.isFinite(dashboard.clean_claim_rate_pct) ? dashboard.clean_claim_rate_pct : null;
  const reconMatchedCount = typeof recon?.matched_count === 'number' && Number.isFinite(recon.matched_count) ? recon.matched_count : null;
  const reconUnmatchedCount = typeof recon?.unmatched_count === 'number' && Number.isFinite(recon.unmatched_count) ? recon.unmatched_count : null;

  /* Revenue bar chart — normalized to max */
  const maxRevenue = useMemo(() => Math.max(...trend.map(t => t.revenue_cents ?? 0), 1), [trend]);

  if (loading) {
    return (
      <div className="flex flex-col gap-4 p-6">
        <QuantumCardSkeleton />
        <div className="grid grid-cols-4 gap-3">{Array.from({ length: 4 }).map((_, i) => <QuantumCardSkeleton key={i} />)}</div>
        <QuantumCardSkeleton />
        <QuantumCardSkeleton />
      </div>
    );
  }

  return (
    <ModuleDashboardShell
      title="Stripe Revenue Dashboard"
      subtitle="Stripe reconciliation, claim settlement, and revenue performance"
      accentColor="var(--color-system-billing)"
      headerActions={
        <>
          <Link
            href="/founder/revenue"
            className="text-[var(--color-text-muted)] hover:text-[var(--color-text-primary)] flex items-center gap-1 text-micro font-label uppercase tracking-wider transition-colors duration-fast"
          >
            <ArrowLeft className="w-3.5 h-3.5" /> Back to Revenue
          </Link>
          <button onClick={loadData} className="quantum-btn flex items-center gap-2">
            <RefreshCw className="w-3.5 h-3.5" /> Refresh
          </button>
        </>
      }
    >
      <div className="space-y-5 px-1 py-1">
        {/* Error */}
        <AnimatePresence>
          {error && (
            <motion.div initial={{ opacity: 0, y: -8 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0, y: -8 }}
              className="flex items-center gap-3 p-4 bg-[var(--color-brand-red-ghost)] border border-[var(--color-brand-red)] chamfer-8">
              <AlertTriangle className="w-5 h-5 text-[var(--color-brand-red)] flex-shrink-0" />
              <span className="text-body text-[var(--color-text-primary)]">{error}</span>
            </motion.div>
          )}
        </AnimatePresence>

        {/* KPI Cards */}
        <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
          <MetricPlate label="Total Revenue" value={formatCents(dashboard?.revenue_cents)} accent="var(--color-status-active)" icon={DollarSign} />
          <MetricPlate label="Paid Claims" value={String(paidClaims ?? '—')} accent="var(--color-status-info)" icon={TrendingUp} />
          <MetricPlate label="Denial Rate" value={denialRatePct != null ? `${denialRatePct}%` : '—'} accent="var(--q-yellow)" icon={AlertTriangle} />
          <MetricPlate label="Clean Claim Rate" value={cleanClaimRatePct != null ? `${cleanClaimRatePct}%` : '—'} accent="var(--color-system-billing)" icon={Users} />
        </div>

        {/* Stripe Reconciliation */}
        <div className="bg-[var(--color-bg-panel)] border border-[var(--color-border-default)] chamfer-12 p-5 hud-rail">
          <div className="flex items-center gap-2 mb-4">
            <CreditCard className="w-4 h-4 text-[var(--color-system-billing)]" />
            <span className="label-caps">Stripe Reconciliation</span>
          </div>
          {recon ? (
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
              <div className="border-l-2 border-[var(--color-border-subtle)] pl-3">
                <div className="text-micro font-label uppercase tracking-wider text-[var(--color-text-muted)] mb-1">Status</div>
                <ReconStatusBadge status={recon.reconciliation_status ?? 'unknown'} />
              </div>
              <div className="border-l-2 border-[var(--color-border-subtle)] pl-3">
                <div className="text-micro font-label uppercase tracking-wider text-[var(--color-text-muted)] mb-1">Matched</div>
                <div className="text-body font-semibold text-[var(--color-status-active)]">{reconMatchedCount ?? '—'}</div>
              </div>
              <div className="border-l-2 border-[var(--color-border-subtle)] pl-3">
                <div className="text-micro font-label uppercase tracking-wider text-[var(--color-text-muted)] mb-1">Unmatched</div>
                <div className="text-body font-semibold text-[var(--color-brand-red)]">{reconUnmatchedCount ?? '—'}</div>
              </div>
              <div className="border-l-2 border-[var(--color-border-subtle)] pl-3">
                <div className="text-micro font-label uppercase tracking-wider text-[var(--color-text-muted)] mb-1">Discrepancy</div>
                <div className="text-body font-semibold text-[var(--q-yellow)]">{formatCents(recon.discrepancy_cents)}</div>
              </div>
            </div>
          ) : (
            <div className="text-body text-[var(--color-text-muted)]">No reconciliation data available</div>
          )}
        </div>

        {/* Revenue Trend (visual bar chart) */}
        <div className="bg-[var(--color-bg-panel)] border border-[var(--color-border-default)] chamfer-12 p-5">
          <div className="flex items-center gap-2 mb-4">
            <BarChart3 className="w-4 h-4 text-[var(--color-status-info)]" />
            <span className="label-caps">Revenue Trend</span>
          </div>
          {trend.length > 0 ? (
            <div className="space-y-2">
              {trend.map((t, i) => {
                const pct = ((t.revenue_cents ?? 0) / maxRevenue) * 100;
                return (
                  <motion.div key={i} initial={{ opacity: 0, x: -12 }} animate={{ opacity: 1, x: 0 }} transition={{ delay: i * 0.04 }}
                    className="flex items-center gap-3">
                    <span className="w-20 text-micro font-label text-[var(--color-text-muted)] text-right flex-shrink-0">{t.month ?? `M${i + 1}`}</span>
                    <div className="flex-1 bg-[var(--color-bg-overlay)] chamfer-4 h-6 relative overflow-hidden">
                      <div
                        className="h-full chamfer-4 transition-all duration-slow"
                        style={{ width: `${Math.max(pct, 2)}%`, background: 'linear-gradient(90deg, var(--color-status-active) 0%, var(--q-orange) 100%)' }}
                      />
                    </div>
                    <span className="w-24 text-body font-semibold text-[var(--color-text-primary)] text-right flex-shrink-0">{formatCents(t.revenue_cents)}</span>
                    <span className="w-16 text-micro text-[var(--color-text-muted)] text-right flex-shrink-0">{t.claim_count != null ? `${t.claim_count}c` : '—'}</span>
                  </motion.div>
                );
              })}
            </div>
          ) : (
            <div className="text-body text-[var(--color-text-muted)]">No trend data available</div>
          )}
        </div>

        {/* Tenant Billing Ranking */}
        <div className="bg-[var(--color-bg-panel)] border border-[var(--color-border-default)] chamfer-12 overflow-hidden">
          <div className="px-5 py-3 border-b border-[var(--color-border-default)] hud-rail flex items-center gap-2">
            <Users className="w-4 h-4 text-[var(--color-system-billing)]" />
            <span className="label-caps">Tenant Billing Ranking</span>
          </div>
          {ranking.length > 0 ? (
            <div className="overflow-x-auto">
              <table className="w-full text-body">
                <thead>
                  <tr className="bg-[var(--color-bg-overlay)]">
                    <th className="text-left px-5 py-2.5 label-caps">#</th>
                    <th className="text-left px-5 py-2.5 label-caps">Tenant</th>
                    <th className="text-right px-5 py-2.5 label-caps">Revenue</th>
                    <th className="text-right px-5 py-2.5 label-caps">Total Claims</th>
                    <th className="text-right px-5 py-2.5 label-caps">Paid</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-[var(--color-border-subtle)]">
                  {ranking.map((r, i) => (
                    <motion.tr key={i} initial={{ opacity: 0 }} animate={{ opacity: 1 }} transition={{ delay: i * 0.03 }}
                      className="hover:bg-[var(--color-bg-overlay)] transition-colors duration-fast">
                      <td className="px-5 py-3 text-[var(--color-text-muted)] font-mono text-micro">{i + 1}</td>
                      <td className="px-5 py-3 text-[var(--color-text-primary)] font-medium">{r.name ?? `Tenant ${i + 1}`}</td>
                      <td className="px-5 py-3 text-right text-[var(--color-status-active)] font-semibold">{formatCents(r.revenue_cents)}</td>
                      <td className="px-5 py-3 text-right text-[var(--color-text-secondary)]">{r.total_claims != null ? r.total_claims.toLocaleString() : '—'}</td>
                      <td className="px-5 py-3 text-right text-[var(--color-status-info)]">{r.paid_claims != null ? r.paid_claims.toLocaleString() : '—'}</td>
                    </motion.tr>
                  ))}
                </tbody>
              </table>
            </div>
          ) : (
            <div className="p-8 text-center text-body text-[var(--color-text-muted)]">No ranking data available</div>
          )}
        </div>

        {/* Footer */}
        <div className="text-center text-micro text-[var(--color-text-disabled)] pb-4">
          Last updated: {dashboard?.as_of ?? recon?.as_of ?? 'N/A'}
        </div>
      </div>
    </ModuleDashboardShell>
  );
}
