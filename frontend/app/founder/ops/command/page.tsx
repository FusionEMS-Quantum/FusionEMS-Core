'use client';

import { useEffect, useState } from 'react';
import { motion } from 'framer-motion';
import Link from 'next/link';
import { getFounderOpsSummary } from '@/services/api';

function Panel({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <div
      className="bg-[#0A0A0B] border border-border-DEFAULT p-4"
      style={{ clipPath: 'polygon(0 0, calc(100% - 10px) 0, 100% 10px, 100% 100%, 0 100%)' }}
    >
      <div className="text-micro font-semibold uppercase tracking-widest text-zinc-500 mb-3">{title}</div>
      {children}
    </div>
  );
}

function StatRow({ label, value, warn }: { label: string; value: number | string; warn?: boolean }) {
  return (
    <div className="flex items-center justify-between py-1.5 border-b border-white/5 last:border-0">
      <span className="text-xs text-zinc-400">{label}</span>
      <span className={`text-xs font-bold ${warn ? 'text-brand-red' : 'text-zinc-100'}`}>{value}</span>
    </div>
  );
}

function SeverityBadge({ severity }: { severity: string }) {
  const colors: Record<string, string> = {
    critical: 'bg-red-600/20 text-red-400 border-red-600/30',
    high: 'bg-[rgba(230,69,0,0.20)] text-[#FF4D00] border-orange-600/30',
    medium: 'bg-yellow-600/20 text-yellow-400 border-yellow-600/30',
    low: 'bg-green-600/20 text-green-400 border-green-600/30',
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
        <div className="text-zinc-500 text-sm animate-pulse">Loading Operations Intelligence...</div>
      </div>
    );
  }

  if (!data) {
    return (
      <div className="p-5 min-h-screen flex items-center justify-center">
        <div className="text-zinc-500 text-sm">Unable to connect to operations API.</div>
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
          <h1 className="text-xl font-black uppercase tracking-wider text-zinc-100">Operations Command Center</h1>
          <p className="text-xs text-zinc-500 mt-0.5">
            Real-time operational intelligence across all domains · Generated {data.generated_at ? new Date(data.generated_at).toLocaleTimeString() : 'now'}
          </p>
        </div>
        <Link href="/founder" className="h-8 px-3 bg-zinc-950/5 border border-border-DEFAULT text-zinc-500 text-xs font-semibold hover:bg-zinc-950/10 transition-colors flex items-center">
          Back to Dashboard
        </Link>
      </div>

      {/* Top Actions */}
      {actions.length > 0 && (
        <motion.div
          initial={{ opacity: 0, y: 8 }}
          animate={{ opacity: 1, y: 0 }}
          className="bg-[#0A0A0B] border border-brand-orange/[0.2] p-4"
          style={{ clipPath: 'polygon(0 0, calc(100% - 14px) 0, 100% 14px, 100% 100%, 0 100%)' }}
        >
          <div className="flex items-center gap-2 mb-3">
            <span className="w-1.5 h-1.5  bg-[#FF4D00] animate-pulse" />
            <span className="text-micro font-bold uppercase tracking-widest text-brand-orange">Top Priority Actions</span>
          </div>
          <div className="space-y-2">
            {actions.map((a: any, i: number) => (
              <div key={i} className="flex items-center gap-3 py-2 border-b border-white/5 last:border-0">
                  <span className="text-micro font-bold text-orange-dim font-mono w-5">{i + 1}</span>
                <SeverityBadge severity={a.severity} />
                <span className="flex-1 text-xs text-zinc-100">{a.action}</span>
                <span className="text-micro uppercase tracking-wider text-zinc-500 bg-zinc-950/5 px-2 py-0.5">{a.domain}</span>
                <span className="text-[10px] text-zinc-500">{a.reason}</span>
              </div>
            ))}
          </div>
        </motion.div>
      )}

      {/* Grid: Deployment + Payments */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        <Panel title="Deployment Issues">
          <StatRow label="Failed Deployments" value={dep.failed_deployments ?? (() => { throw new Error('Unsafe silent fallback. Dependency missing.'); })()} warn={(dep.failed_deployments ?? (() => { throw new Error('Unsafe silent fallback. Dependency missing.'); })()) > 0} />
          <StatRow label="Retrying Deployments" value={dep.retrying_deployments ?? (() => { throw new Error('Unsafe silent fallback. Dependency missing.'); })()} />
          {(dep.recent_failures || []).length > 0 && (
            <div className="mt-3">
              <div className="text-[10px] text-zinc-500 uppercase mb-1">Recent Failures</div>
              {dep.recent_failures.slice(0, 3).map((f: any) => (
                <div key={f.id} className="text-xs text-zinc-400 py-1 border-b border-white/5">
                  <SeverityBadge severity={f.severity?.toLowerCase() || 'high'} />
                  <span className="ml-2">{f.what_is_wrong}</span>
                </div>
              ))}
            </div>
          )}
        </Panel>

        <Panel title="Payment Failures">
          <StatRow label="Past-Due Subscriptions" value={pay.past_due_subscriptions ?? (() => { throw new Error('Unsafe silent fallback. Dependency missing.'); })()} warn={(pay.past_due_subscriptions ?? (() => { throw new Error('Unsafe silent fallback. Dependency missing.'); })()) > 0} />
          <StatRow label="Canceled Subscriptions" value={pay.canceled_subscriptions ?? (() => { throw new Error('Unsafe silent fallback. Dependency missing.'); })()} warn={(pay.canceled_subscriptions ?? (() => { throw new Error('Unsafe silent fallback. Dependency missing.'); })()) > 0} />
          <StatRow label="Expired Payment Links" value={pay.expired_payment_links ?? (() => { throw new Error('Unsafe silent fallback. Dependency missing.'); })()} />
          <StatRow label="Pending Approvals" value={pay.pending_approval_actions ?? (() => { throw new Error('Unsafe silent fallback. Dependency missing.'); })()} />
        </Panel>
      </div>

      {/* Grid: Claims Pipeline + High-Risk Denials */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        <Panel title="Claims Pipeline">
          <StatRow label="Ready to Submit" value={claims.ready_to_submit ?? (() => { throw new Error('Unsafe silent fallback. Dependency missing.'); })()} warn={(claims.ready_to_submit ?? (() => { throw new Error('Unsafe silent fallback. Dependency missing.'); })()) > 10} />
          <StatRow label="Blocked for Review" value={claims.blocked_for_review ?? (() => { throw new Error('Unsafe silent fallback. Dependency missing.'); })()} warn={(claims.blocked_for_review ?? (() => { throw new Error('Unsafe silent fallback. Dependency missing.'); })()) > 0} />
          <StatRow label="Submitted" value={claims.submitted ?? (() => { throw new Error('Unsafe silent fallback. Dependency missing.'); })()} />
          <StatRow label="Denied" value={claims.denied ?? (() => { throw new Error('Unsafe silent fallback. Dependency missing.'); })()} warn={(claims.denied ?? (() => { throw new Error('Unsafe silent fallback. Dependency missing.'); })()) > 0} />
          <StatRow label="Rejected" value={claims.rejected ?? (() => { throw new Error('Unsafe silent fallback. Dependency missing.'); })()} warn={(claims.rejected ?? (() => { throw new Error('Unsafe silent fallback. Dependency missing.'); })()) > 0} />
          <StatRow label="Appeals Drafted" value={claims.appeals_drafted ?? (() => { throw new Error('Unsafe silent fallback. Dependency missing.'); })()} />
          <StatRow label="Appeals Pending Review" value={claims.appeals_pending_review ?? (() => { throw new Error('Unsafe silent fallback. Dependency missing.'); })()} />
          <StatRow label="Blocking Issues" value={claims.blocking_issues ?? (() => { throw new Error('Unsafe silent fallback. Dependency missing.'); })()} warn={(claims.blocking_issues ?? (() => { throw new Error('Unsafe silent fallback. Dependency missing.'); })()) > 0} />
        </Panel>

        <Panel title="High-Risk Denials">
          <StatRow label="High-Value Denials" value={denials.high_value_denials ?? (() => { throw new Error('Unsafe silent fallback. Dependency missing.'); })()} warn={(denials.high_value_denials ?? (() => { throw new Error('Unsafe silent fallback. Dependency missing.'); })()) > 0} />
          <StatRow label="Total Denied Value" value={`$${((denials.total_denied_value_cents ?? (() => { throw new Error('Unsafe silent fallback. Dependency missing.'); })()) / 100).toLocaleString()}`} warn={(denials.total_denied_value_cents ?? (() => { throw new Error('Unsafe silent fallback. Dependency missing.'); })()) > 50000} />
          {(denials.top_denials || []).length > 0 && (
            <div className="mt-3">
              <div className="text-[10px] text-zinc-500 uppercase mb-1">Largest Denials</div>
              {denials.top_denials.map((d: any) => (
                <div key={d.id} className="flex justify-between text-xs py-1 border-b border-white/5">
                  <span className="text-zinc-400">{d.payer}</span>
                  <span className="text-zinc-100 font-bold">${(d.total_billed_cents / 100).toLocaleString()}</span>
                </div>
              ))}
            </div>
          )}
        </Panel>
      </div>

      {/* Grid: Patient Balances + Collections + Debt Setoff */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <Panel title="Patient Balances">
          <StatRow label="Open Balances" value={balances.open_balances ?? (() => { throw new Error('Unsafe silent fallback. Dependency missing.'); })()} />
          <StatRow label="Autopay Pending" value={balances.autopay_pending ?? (() => { throw new Error('Unsafe silent fallback. Dependency missing.'); })()} />
          <StatRow label="Payment Plan Active" value={balances.payment_plan_active ?? (() => { throw new Error('Unsafe silent fallback. Dependency missing.'); })()} />
          <StatRow label="Collections Ready" value={balances.collections_ready ?? (() => { throw new Error('Unsafe silent fallback. Dependency missing.'); })()} warn={(balances.collections_ready ?? (() => { throw new Error('Unsafe silent fallback. Dependency missing.'); })()) > 0} />
          <StatRow label="Sent to Collections" value={balances.sent_to_collections ?? (() => { throw new Error('Unsafe silent fallback. Dependency missing.'); })()} />
          <StatRow label="Written Off" value={balances.written_off ?? (() => { throw new Error('Unsafe silent fallback. Dependency missing.'); })()} />
          <StatRow label="Total Outstanding" value={`$${((balances.total_outstanding_cents ?? (() => { throw new Error('Unsafe silent fallback. Dependency missing.'); })()) / 100).toLocaleString()}`} />
        </Panel>

        <Panel title="Collections Review">
          <StatRow label="Pending Reviews" value={collections.pending_reviews ?? (() => { throw new Error('Unsafe silent fallback. Dependency missing.'); })()} warn={(collections.pending_reviews ?? (() => { throw new Error('Unsafe silent fallback. Dependency missing.'); })()) > 0} />
          <StatRow label="Approved for Collections" value={collections.approved_for_collections ?? (() => { throw new Error('Unsafe silent fallback. Dependency missing.'); })()} />
          <StatRow label="Total at Collections Stage" value={collections.total_at_collections_stage ?? (() => { throw new Error('Unsafe silent fallback. Dependency missing.'); })()} />
        </Panel>

        <Panel title="Debt Setoff Program">
          <StatRow label="Active Enrollments" value={setoff.active_enrollments ?? (() => { throw new Error('Unsafe silent fallback. Dependency missing.'); })()} />
          <StatRow label="Pending Batches" value={setoff.pending_batches ?? (() => { throw new Error('Unsafe silent fallback. Dependency missing.'); })()} />
          <StatRow label="Submitted Batches" value={setoff.submitted_batches ?? (() => { throw new Error('Unsafe silent fallback. Dependency missing.'); })()} />
          <StatRow label="Claims at Setoff Stage" value={setoff.claims_at_setoff_stage ?? (() => { throw new Error('Unsafe silent fallback. Dependency missing.'); })()} />
          <StatRow label="Pending Amount" value={`$${((setoff.total_pending_amount_cents ?? (() => { throw new Error('Unsafe silent fallback. Dependency missing.'); })()) / 100).toLocaleString()}`} />
        </Panel>
      </div>

      {/* Grid: Agency Gaps + Comms Health + CrewLink */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <Panel title="Agency Profile Gaps">
          <StatRow label="Total Tenants" value={gaps.total_tenants ?? (() => { throw new Error('Unsafe silent fallback. Dependency missing.'); })()} />
          <StatRow label="Missing Tax Profile" value={gaps.missing_tax_profile ?? (() => { throw new Error('Unsafe silent fallback. Dependency missing.'); })()} warn={(gaps.missing_tax_profile ?? (() => { throw new Error('Unsafe silent fallback. Dependency missing.'); })()) > 0} />
          <StatRow label="Missing Public Sector" value={gaps.missing_public_sector_profile ?? (() => { throw new Error('Unsafe silent fallback. Dependency missing.'); })()} warn={(gaps.missing_public_sector_profile ?? (() => { throw new Error('Unsafe silent fallback. Dependency missing.'); })()) > 0} />
          <StatRow label="Missing Billing Policy" value={gaps.missing_billing_policy ?? (() => { throw new Error('Unsafe silent fallback. Dependency missing.'); })()} warn={(gaps.missing_billing_policy ?? (() => { throw new Error('Unsafe silent fallback. Dependency missing.'); })()) > 0} />
        </Panel>

        <Panel title="Communications Health">
          <StatRow label="Total Channels" value={comms.total_channels ?? (() => { throw new Error('Unsafe silent fallback. Dependency missing.'); })()} />
          <StatRow label="Degraded Channels" value={comms.degraded_channels ?? (() => { throw new Error('Unsafe silent fallback. Dependency missing.'); })()} warn={(comms.degraded_channels ?? (() => { throw new Error('Unsafe silent fallback. Dependency missing.'); })()) > 0} />
          <StatRow label="Open Threads" value={comms.open_threads ?? (() => { throw new Error('Unsafe silent fallback. Dependency missing.'); })()} />
          <StatRow label="Messages (24h)" value={comms.messages_last_24h ?? (() => { throw new Error('Unsafe silent fallback. Dependency missing.'); })()} />
          <StatRow label="Failed Messages" value={comms.failed_messages ?? (() => { throw new Error('Unsafe silent fallback. Dependency missing.'); })()} warn={(comms.failed_messages ?? (() => { throw new Error('Unsafe silent fallback. Dependency missing.'); })()) > 0} />
        </Panel>

        <Panel title="CrewLink Paging Health">
          <StatRow label="Active Alerts" value={crew.active_alerts ?? (() => { throw new Error('Unsafe silent fallback. Dependency missing.'); })()} />
          <StatRow label="Escalations (24h)" value={crew.escalations_last_24h ?? (() => { throw new Error('Unsafe silent fallback. Dependency missing.'); })()} warn={(crew.escalations_last_24h ?? (() => { throw new Error('Unsafe silent fallback. Dependency missing.'); })()) > 0} />
          <StatRow label="Pending No Response" value={crew.pending_no_response ?? (() => { throw new Error('Unsafe silent fallback. Dependency missing.'); })()} warn={(crew.pending_no_response ?? (() => { throw new Error('Unsafe silent fallback. Dependency missing.'); })()) > 0} />
          <StatRow label="Completed (24h)" value={crew.completed_last_24h ?? (() => { throw new Error('Unsafe silent fallback. Dependency missing.'); })()} />
        </Panel>
      </div>
    </div>
  );
}
