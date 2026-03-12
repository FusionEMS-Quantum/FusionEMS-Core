'use client';

import { useEffect, useState } from 'react';
import { motion } from 'framer-motion';
import Link from 'next/link';
import { getFounderOpsSummary } from '@/services/api';

function Panel({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <div
      className="bg-[var(--color-bg-panel)] border border-border-DEFAULT p-4"
      style={{ clipPath: 'polygon(0 0, calc(100% - 10px) 0, 100% 10px, 100% 100%, 0 100%)' }}
    >
      <div className="text-micro font-semibold uppercase tracking-widest text-[var(--color-text-muted)] mb-3">{title}</div>
      {children}
    </div>
  );
}

function StatRow({ label, value, warn }: { label: string; value: number | string; warn?: boolean }) {
  return (
    <div className="flex items-center justify-between py-1.5 border-b border-white/5 last:border-0">
      <span className="text-xs text-[var(--color-text-secondary)]">{label}</span>
      <span className={`text-xs font-bold ${warn ? 'text-brand-red' : 'text-[var(--color-text-primary)]'}`}>{value}</span>
    </div>
  );
}

function SeverityBadge({ severity }: { severity: string }) {
  const colors: Record<string, string> = {
    critical: 'bg-red-600/20 text-[var(--color-brand-red)] border-red-600/30',
    high: 'bg-[rgba(230,69,0,0.20)] text-[var(--q-orange)] border-orange-600/30',
    medium: 'bg-yellow-600/20 text-[var(--q-yellow)] border-yellow-600/30',
    low: 'bg-green-600/20 text-[var(--color-status-active)] border-green-600/30',
  };
  return (
    <span className={`text-[10px] font-bold uppercase px-1.5 py-0.5 border ${colors[severity] || colors.medium}`}>
      {severity}
    </span>
  );
}

export default function OpsCommandPage() {
  const [data, setData] = useState<any>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    getFounderOpsSummary()
      .then(setData)
      .catch((e: unknown) => console.warn('[ops fetch]', e))
      .finally(() => setLoading(false));
  }, []);

  if (loading) {
    return (
      <div className="p-5 min-h-screen flex items-center justify-center">
        <div className="text-[var(--color-text-muted)] text-sm animate-pulse">Loading Operations Intelligence...</div>
      </div>
    );
  }

  if (!data) {
    return (
      <div className="p-5 min-h-screen flex items-center justify-center">
        <div className="text-[var(--color-text-muted)] text-sm">Unable to connect to operations API.</div>
      </div>
    );
  }

  const dep = data.deployment_issues || {};
  const pay = data.payment_failures || {};
  const claims = data.claims_pipeline || {};
  const denials = data.high_risk_denials || {};
  const balances = data.patient_balance_review || {};
  const collections = data.collections_review || {};
  const setoff = data.debt_setoff_review || {};
  const gaps = data.profile_gaps || {};
  const comms = data.comms_health || {};
  const crew = data.crewlink_health || {};
  const actions = data.top_actions || [];

  return (
    <div className="p-5 space-y-6 min-h-screen">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
            <div className="text-micro font-bold uppercase tracking-[0.2em] text-orange-dim mb-1">MODULE 6</div>
          <h1 className="text-xl font-black uppercase tracking-wider text-[var(--color-text-primary)]">Operations Command Center</h1>
          <p className="text-xs text-[var(--color-text-muted)] mt-0.5">
            Real-time operational intelligence across all domains · Generated {data.generated_at ? new Date(data.generated_at).toLocaleTimeString() : 'now'}
          </p>
        </div>
        <Link href="/founder" className="h-8 px-3 bg-[var(--color-bg-base)]/5 border border-border-DEFAULT text-[var(--color-text-muted)] text-xs font-semibold hover:bg-[var(--color-bg-base)]/10 transition-colors flex items-center">
          Back to Dashboard
        </Link>
      </div>

      {/* Top Actions */}
      {actions.length > 0 && (
        <motion.div
          initial={{ opacity: 0, y: 8 }}
          animate={{ opacity: 1, y: 0 }}
          className="bg-[var(--color-bg-panel)] border border-brand-orange/[0.2] p-4"
          style={{ clipPath: 'polygon(0 0, calc(100% - 14px) 0, 100% 14px, 100% 100%, 0 100%)' }}
        >
          <div className="flex items-center gap-2 mb-3">
            <span className="w-1.5 h-1.5  bg-[var(--q-orange)] animate-pulse" />
            <span className="text-micro font-bold uppercase tracking-widest text-brand-orange">Top Priority Actions</span>
          </div>
          <div className="space-y-2">
            {actions.map((a: any, i: number) => (
              <div key={i} className="flex items-center gap-3 py-2 border-b border-white/5 last:border-0">
                  <span className="text-micro font-bold text-orange-dim font-mono w-5">{i + 1}</span>
                <SeverityBadge severity={a.severity} />
                <span className="flex-1 text-xs text-[var(--color-text-primary)]">{a.action}</span>
                <span className="text-micro uppercase tracking-wider text-[var(--color-text-muted)] bg-[var(--color-bg-base)]/5 px-2 py-0.5">{a.domain}</span>
                <span className="text-[10px] text-[var(--color-text-muted)]">{a.reason}</span>
              </div>
            ))}
          </div>
        </motion.div>
      )}

      {/* Grid: Deployment + Payments */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        <Panel title="Deployment Issues">
          <StatRow label="Failed Deployments" value={dep.failed_deployments ?? '—'} warn={(dep.failed_deployments ?? 0) > 0} />
          <StatRow label="Retrying Deployments" value={dep.retrying_deployments ?? '—'} />
          {(dep.recent_failures || []).length > 0 && (
            <div className="mt-3">
              <div className="text-[10px] text-[var(--color-text-muted)] uppercase mb-1">Recent Failures</div>
              {dep.recent_failures.slice(0, 3).map((f: any) => (
                <div key={f.id} className="text-xs text-[var(--color-text-secondary)] py-1 border-b border-white/5">
                  <SeverityBadge severity={f.severity?.toLowerCase() || 'high'} />
                  <span className="ml-2">{f.what_is_wrong}</span>
                </div>
              ))}
            </div>
          )}
        </Panel>

        <Panel title="Payment Failures">
          <StatRow label="Past-Due Subscriptions" value={pay.past_due_subscriptions ?? '—'} warn={(pay.past_due_subscriptions ?? 0) > 0} />
          <StatRow label="Canceled Subscriptions" value={pay.canceled_subscriptions ?? '—'} warn={(pay.canceled_subscriptions ?? 0) > 0} />
          <StatRow label="Expired Payment Links" value={pay.expired_payment_links ?? '—'} />
          <StatRow label="Pending Approvals" value={pay.pending_approval_actions ?? '—'} />
        </Panel>
      </div>

      {/* Grid: Claims Pipeline + High-Risk Denials */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        <Panel title="Claims Pipeline">
          <StatRow label="Ready to Submit" value={claims.ready_to_submit ?? '—'} warn={(claims.ready_to_submit ?? 0) > 10} />
          <StatRow label="Blocked for Review" value={claims.blocked_for_review ?? '—'} warn={(claims.blocked_for_review ?? 0) > 0} />
          <StatRow label="Submitted" value={claims.submitted ?? '—'} />
          <StatRow label="Denied" value={claims.denied ?? '—'} warn={(claims.denied ?? 0) > 0} />
          <StatRow label="Rejected" value={claims.rejected ?? '—'} warn={(claims.rejected ?? 0) > 0} />
          <StatRow label="Appeals Drafted" value={claims.appeals_drafted ?? '—'} />
          <StatRow label="Appeals Pending Review" value={claims.appeals_pending_review ?? '—'} />
          <StatRow label="Blocking Issues" value={claims.blocking_issues ?? '—'} warn={(claims.blocking_issues ?? 0) > 0} />
        </Panel>

        <Panel title="High-Risk Denials">
          <StatRow label="High-Value Denials" value={denials.high_value_denials ?? '—'} warn={(denials.high_value_denials ?? 0) > 0} />
          <StatRow
            label="Total Denied Value"
            value={denials.total_denied_value_cents != null ? `$${(denials.total_denied_value_cents / 100).toLocaleString()}` : '—'}
            warn={(denials.total_denied_value_cents ?? 0) > 50000}
          />
          {(denials.top_denials || []).length > 0 && (
            <div className="mt-3">
              <div className="text-[10px] text-[var(--color-text-muted)] uppercase mb-1">Largest Denials</div>
              {denials.top_denials.map((d: any) => (
                <div key={d.id} className="flex justify-between text-xs py-1 border-b border-white/5">
                  <span className="text-[var(--color-text-secondary)]">{d.payer}</span>
                  <span className="text-[var(--color-text-primary)] font-bold">${(d.total_billed_cents / 100).toLocaleString()}</span>
                </div>
              ))}
            </div>
          )}
        </Panel>
      </div>

      {/* Grid: Patient Balances + Collections + Debt Setoff */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <Panel title="Patient Balances">
          <StatRow label="Open Balances" value={balances.open_balances ?? '—'} />
          <StatRow label="Autopay Pending" value={balances.autopay_pending ?? '—'} />
          <StatRow label="Payment Plan Active" value={balances.payment_plan_active ?? '—'} />
          <StatRow label="Collections Ready" value={balances.collections_ready ?? '—'} warn={(balances.collections_ready ?? 0) > 0} />
          <StatRow label="Sent to Collections" value={balances.sent_to_collections ?? '—'} />
          <StatRow label="Written Off" value={balances.written_off ?? '—'} />
          <StatRow label="Total Outstanding" value={balances.total_outstanding_cents != null ? `$${(balances.total_outstanding_cents / 100).toLocaleString()}` : '—'} />
        </Panel>

        <Panel title="Collections Review">
          <StatRow label="Pending Reviews" value={collections.pending_reviews ?? '—'} warn={(collections.pending_reviews ?? 0) > 0} />
          <StatRow label="Approved for Collections" value={collections.approved_for_collections ?? '—'} />
          <StatRow label="Total at Collections Stage" value={collections.total_at_collections_stage ?? '—'} />
        </Panel>

        <Panel title="Debt Setoff Program">
          <StatRow label="Active Enrollments" value={setoff.active_enrollments ?? '—'} />
          <StatRow label="Pending Batches" value={setoff.pending_batches ?? '—'} />
          <StatRow label="Submitted Batches" value={setoff.submitted_batches ?? '—'} />
          <StatRow label="Claims at Setoff Stage" value={setoff.claims_at_setoff_stage ?? '—'} />
          <StatRow label="Pending Amount" value={setoff.total_pending_amount_cents != null ? `$${(setoff.total_pending_amount_cents / 100).toLocaleString()}` : '—'} />
        </Panel>
      </div>

      {/* Grid: Agency Gaps + Comms Health + CrewLink */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <Panel title="Agency Profile Gaps">
          <StatRow label="Total Tenants" value={gaps.total_tenants ?? '—'} />
          <StatRow label="Missing Tax Profile" value={gaps.missing_tax_profile ?? '—'} warn={(gaps.missing_tax_profile ?? 0) > 0} />
          <StatRow label="Missing Public Sector" value={gaps.missing_public_sector_profile ?? '—'} warn={(gaps.missing_public_sector_profile ?? 0) > 0} />
          <StatRow label="Missing Billing Policy" value={gaps.missing_billing_policy ?? '—'} warn={(gaps.missing_billing_policy ?? 0) > 0} />
        </Panel>

        <Panel title="Communications Health">
          <StatRow label="Total Channels" value={comms.total_channels ?? '—'} />
          <StatRow label="Degraded Channels" value={comms.degraded_channels ?? '—'} warn={(comms.degraded_channels ?? 0) > 0} />
          <StatRow label="Open Threads" value={comms.open_threads ?? '—'} />
          <StatRow label="Messages (24h)" value={comms.messages_last_24h ?? '—'} />
          <StatRow label="Failed Messages" value={comms.failed_messages ?? '—'} warn={(comms.failed_messages ?? 0) > 0} />
        </Panel>

        <Panel title="CrewLink Paging Health">
          <StatRow label="Active Alerts" value={crew.active_alerts ?? '—'} />
          <StatRow label="Escalations (24h)" value={crew.escalations_last_24h ?? '—'} warn={(crew.escalations_last_24h ?? 0) > 0} />
          <StatRow label="Pending No Response" value={crew.pending_no_response ?? '—'} warn={(crew.pending_no_response ?? 0) > 0} />
          <StatRow label="Completed (24h)" value={crew.completed_last_24h ?? '—'} />
        </Panel>
      </div>
    </div>
  );
}
