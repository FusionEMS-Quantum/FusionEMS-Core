'use client';

import { motion } from 'framer-motion';
import Link from 'next/link';
import { useCallback, useEffect, useMemo, useState, type ReactNode } from 'react';
import { QuantumEmptyState } from '@/components/ui';
import { NextBestActionCard, type NextAction } from '@/components/ui/NextBestActionCard';
import { SeverityBadge } from '@/components/ui/SeverityBadge';
import { DomainNavCard, FounderStatusBar } from '@/components/shells/FounderCommand';
import type { SeverityLevel } from '@/lib/design-system/tokens';
import {
  getROIFunnelProposals,
  getROIFunnelConversionKpis,
  getROIFunnelRevenuePipeline,
  createROIFunnelProposal,
  type ROIFunnelProposalRecord,
  type ROIFunnelConversionKpisResponse,
  type ROIFunnelRevenuePipelineResponse,
} from '@/services/api';

type FetchStatus = 'idle' | 'loading' | 'ready' | 'error';

type ProposalStatus = 'pending' | 'viewed' | 'in_negotiation' | 'accepted' | 'converted' | 'declined' | 'unknown';

type ProposalsFilter = 'All' | 'Open' | 'Accepted' | 'Declined';

type ProposalRow = {
  id: string;
  agency: string;
  sentDateLabel: string;
  valueLabel: string;
  status: ProposalStatus;
  statusLabel: string;
  statusKey: 'ok' | 'warn' | 'error' | 'info';
  daysOpen: number;
  actionLabel: string;
};

function SectionHeader({ number, title, sub }: { number: string; title: string; sub?: string }) {
  return (
    <div className="border-b border-border-subtle pb-2 mb-4">
      <div className="flex items-baseline gap-3">
        <span className="text-micro font-bold text-[#FF4D00]/70 font-mono">MODULE {number}</span>
        <h2 className="text-sm font-bold uppercase tracking-widest text-zinc-100">{title}</h2>
        {sub && <span className="text-xs text-zinc-500">{sub}</span>}
      </div>
    </div>
  );
}

function Badge({ label, status }: { label: string; status: 'ok' | 'warn' | 'error' | 'info' }) {
  const colors = {
    ok: 'var(--color-status-active)',
    warn: 'var(--color-status-warning)',
    error: 'var(--color-brand-red)',
    info: 'var(--color-status-info)',
  } as const;

  return (
    <span
      className="inline-flex items-center gap-1.5 px-2 py-0.5 chamfer-4 text-micro font-semibold uppercase tracking-wider border"
      style={{ borderColor: `${colors[status]}40`, color: colors[status], background: `${colors[status]}12` }}
    >
      <span className="w-1 h-1" style={{ background: colors[status] }} />
      {label}
    </span>
  );
}

function Panel({ children, className }: { children: ReactNode; className?: string }) {
  return (
    <div
      className={`bg-[#0A0A0B] border border-border-DEFAULT p-4 ${className ?? ''}`}
      style={{ clipPath: 'polygon(0 0,calc(100% - 10px) 0,100% 10px,100% 100%,0 100%)' }}
    >
      {children}
    </div>
  );
}

function StatCard({ label, value, sub, color }: { label: string; value: string | number; sub?: string; color?: string }) {
  return (
    <div
      className="bg-[#0A0A0B] border border-border-DEFAULT p-4"
      style={{ clipPath: 'polygon(0 0,calc(100% - 10px) 0,100% 10px,100% 100%,0 100%)' }}
    >
      <div className="text-micro font-semibold uppercase tracking-widest text-zinc-500 mb-1">{label}</div>
      <div className="text-xl font-bold" style={{ color: color ?? 'var(--color-text-primary)' }}>{value}</div>
      {sub && <div className="text-body text-zinc-500 mt-0.5">{sub}</div>}
    </div>
  );
}

function ProgressBar({ value, max, color }: { value: number; max: number; color: string }) {
  const pct = max > 0 ? Math.min((value / max) * 100, 100) : 0;
  return (
    <div className="h-1.5 bg-zinc-950/[0.06] overflow-hidden">
      <motion.div
        className="h-full"
        style={{ background: color }}
        initial={{ width: 0 }}
        animate={{ width: `${pct}%` }}
        transition={{ duration: 0.8 }}
      />
    </div>
  );
}

function toProposalStatus(rawStatus: string | undefined): ProposalStatus {
  const normalized = rawStatus?.toLowerCase() ?? '';
  if (normalized === 'pending') return 'pending';
  if (normalized === 'viewed') return 'viewed';
  if (normalized === 'in_negotiation') return 'in_negotiation';
  if (normalized === 'accepted') return 'accepted';
  if (normalized === 'converted' || normalized === 'active') return 'converted';
  if (normalized === 'declined' || normalized === 'rejected') return 'declined';
  return 'unknown';
}

function statusPresentation(status: ProposalStatus): Pick<ProposalRow, 'statusLabel' | 'statusKey' | 'actionLabel'> {
  if (status === 'pending') return { statusLabel: 'Sent', statusKey: 'warn', actionLabel: 'Send Reminder' };
  if (status === 'viewed') return { statusLabel: 'Viewed', statusKey: 'info', actionLabel: 'Follow Up' };
  if (status === 'in_negotiation') return { statusLabel: 'In Negotiation', statusKey: 'info', actionLabel: 'Schedule Call' };
  if (status === 'accepted' || status === 'converted') return { statusLabel: 'Converted', statusKey: 'ok', actionLabel: 'Open Account' };
  if (status === 'declined') return { statusLabel: 'Declined', statusKey: 'error', actionLabel: 'Archive' };
  return { statusLabel: 'Unknown', statusKey: 'warn', actionLabel: 'Review' };
}

function formatDateLabel(value: string | undefined): string {
  if (!value) return '—';
  const d = new Date(value);
  if (Number.isNaN(d.getTime())) return '—';
  return d.toLocaleDateString(undefined, { month: 'short', day: '2-digit' });
}

function daysSince(value: string | undefined): number {
  if (!value) return 0;
  const d = new Date(value);
  if (Number.isNaN(d.getTime())) return 0;
  const diffMs = Date.now() - d.getTime();
  return Math.max(0, Math.floor(diffMs / (1000 * 60 * 60 * 24)));
}

export default function ProposalTrackerPage() {
  const [filter, setFilter] = useState<ProposalsFilter>('All');
  const [status, setStatus] = useState<FetchStatus>('idle');
  const [error, setError] = useState<string | null>(null);
  const [proposals, setProposals] = useState<ROIFunnelProposalRecord[]>([]);
  const [kpis, setKpis] = useState<ROIFunnelConversionKpisResponse | null>(null);
  const [pipeline, setPipeline] = useState<ROIFunnelRevenuePipelineResponse | null>(null);

  const [newAgency, setNewAgency] = useState('');
  const [newEmail, setNewEmail] = useState('');
  const [newScenarioId, setNewScenarioId] = useState('');
  const [creating, setCreating] = useState(false);
  const [createError, setCreateError] = useState<string | null>(null);

  const fetchTelemetry = useCallback((): void => {
    setStatus('loading');
    setError(null);

    void Promise.all([
      getROIFunnelProposals(),
      getROIFunnelConversionKpis(),
      getROIFunnelRevenuePipeline(),
    ])
      .then(([proposalPayload, kpiPayload, pipelinePayload]) => {
        setProposals(proposalPayload.proposals ?? []);
        setKpis(kpiPayload);
        setPipeline(pipelinePayload);
        setStatus('ready');
      })
      .catch((fetchError: unknown) => {
        const message = fetchError instanceof Error ? fetchError.message : 'Unknown proposal telemetry error';
        setError(message);
        setStatus('error');
      });
  }, []);

  useEffect(() => {
    fetchTelemetry();
  }, [fetchTelemetry]);

  const proposalRows = useMemo<ProposalRow[]>(() => proposals.map((proposal) => {
    const proposalStatus = toProposalStatus(proposal.data?.status);
    const presentation = statusPresentation(proposalStatus);
    const createdAt = proposal.data?.created_at ?? proposal.created_at;

    return {
      id: proposal.id,
      agency: proposal.data?.agency_name || 'Unspecified agency',
      sentDateLabel: formatDateLabel(createdAt),
      valueLabel: '$89,900',
      status: proposalStatus,
      statusLabel: presentation.statusLabel,
      statusKey: presentation.statusKey,
      daysOpen: daysSince(createdAt),
      actionLabel: presentation.actionLabel,
    };
  }), [proposals]);

  const filteredRows = useMemo<ProposalRow[]>(() => proposalRows.filter((proposal) => {
    if (filter === 'All') return true;
    if (filter === 'Open') return ['pending', 'viewed', 'in_negotiation', 'unknown'].includes(proposal.status);
    if (filter === 'Accepted') return ['accepted', 'converted'].includes(proposal.status);
    if (filter === 'Declined') return proposal.status === 'declined';
    return true;
  }), [filter, proposalRows]);

  const acceptedRows = useMemo(() => proposalRows.filter((proposal) => ['accepted', 'converted'].includes(proposal.status)), [proposalRows]);
  const followUpRows = useMemo(() => proposalRows.filter((proposal) => proposal.daysOpen >= 7 && ['pending', 'viewed', 'in_negotiation', 'unknown'].includes(proposal.status)), [proposalRows]);

  const proposalSeverity: SeverityLevel = status === 'error'
    ? 'BLOCKING'
    : followUpRows.length > 3
      ? 'HIGH'
      : followUpRows.length > 0
        ? 'MEDIUM'
        : 'LOW';

  const proposalActions = useMemo<NextAction[]>(() => {
    const actions: NextAction[] = [];

    if (status === 'error') {
      actions.push({
        id: 'proposal-telemetry-recover',
        title: 'Recover proposal telemetry before making close and pipeline commitments.',
        severity: 'BLOCKING',
        domain: 'Proposal Telemetry',
        href: '/founder/roi/proposals',
      });
    }

    if (followUpRows.length > 0) {
      actions.push({
        id: 'proposal-followup-queue',
        title: `Execute follow-up sequence for ${followUpRows.length} aged proposal(s).`,
        severity: followUpRows.length > 3 ? 'HIGH' : 'MEDIUM',
        domain: 'Follow-Up Queue',
        href: '/founder/roi/proposals',
      });
    }

    if ((kpis?.proposal_to_paid_conversion_pct ?? (() => { throw new Error('Unsafe silent fallback. Dependency missing.'); })()) < 25) {
      actions.push({
        id: 'proposal-conversion-boost',
        title: 'Conversion is below target; align pricing assumptions and outreach sequence.',
        severity: 'HIGH',
        domain: 'Conversion Posture',
        href: '/founder/roi/analytics',
      });
    }

    if (actions.length === 0) {
      actions.push({
        id: 'proposal-command-stable',
        title: 'Proposal command posture is stable; maintain daily cadence and SLA checks.',
        severity: 'LOW',
        domain: 'Proposal Tracker',
        href: '/founder/roi/proposals',
      });
    }

    return actions;
  }, [followUpRows.length, kpis?.proposal_to_paid_conversion_pct, status]);

  const handleCreateProposal = async (): Promise<void> => {
    if (!newAgency || !newEmail || !newScenarioId) {
      setCreateError('Agency, contact email, and ROI scenario ID are required.');
      return;
    }

    setCreating(true);
    setCreateError(null);

    try {
      await createROIFunnelProposal({
        roi_scenario_id: newScenarioId,
        agency_name: newAgency,
        contact_name: 'Founder Command',
        contact_email: newEmail,
        expiration_days: 30,
        include_modules: ['billing', 'analytics', 'compliance'],
      });

      setNewAgency('');
      setNewEmail('');
      setNewScenarioId('');
      fetchTelemetry();
    } catch (submitError: unknown) {
      const message = submitError instanceof Error ? submitError.message : 'Unknown proposal creation error';
      setCreateError(message);
    } finally {
      setCreating(false);
    }
  };

  return (
    <div className="min-h-screen bg-black text-zinc-100 p-6 space-y-6">
      <FounderStatusBar isLive={status !== 'error'} activeIncidents={status === 'error' ? 1 : 0} />

      <div className="border-b border-border-subtle pb-4">
        <div className="flex items-center justify-between">
          <div>
            <p className="text-micro font-bold tracking-widest font-mono mb-1" style={{ color: 'rgba(255,152,0,0.6)' }}>
              MODULE 8 · ROI &amp; SALES
            </p>
            <h1 className="text-2xl font-bold tracking-tight" style={{ color: 'var(--q-yellow)' }}>Proposal Tracker</h1>
            <p className="text-xs text-zinc-500 mt-1">Track sent proposals · follow-up cadence · conversion posture</p>
            <div className="mt-2">
              <SeverityBadge severity={proposalSeverity} size="sm" />
            </div>
          </div>
          <div className="flex items-center gap-3">
            <button
              onClick={fetchTelemetry}
              className="h-8 px-3 text-xs font-semibold border border-status-warning/35 text-status-warning hover:bg-status-warning/10 transition-colors"
            >
              Refresh Proposals
            </button>
            <Link href="/founder/roi" className="text-body text-zinc-500 hover:text-status-warning transition-colors font-mono">
              ← Back to ROI Command
            </Link>
          </div>
        </div>
      </div>

      <NextBestActionCard actions={proposalActions} title="Proposal Command Next Best Actions" maxVisible={4} />

      <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
        <DomainNavCard
          domain="billing"
          href="/founder/revenue/billing-intelligence"
          description="Connect closed proposals to realized revenue and billing performance."
        />
        <DomainNavCard
          domain="ops"
          href="/founder/ops/command"
          description="Align proposal commitments with operational readiness and onboarding slots."
        />
        <DomainNavCard
          domain="support"
          href="/founder/success-command"
          description="Coordinate post-signature success motions and retention safeguards."
        />
      </div>

      <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
        <StatCard label="Total Sent" value={kpis?.total_proposals ?? proposalRows.length} color="var(--color-text-primary)" />
        <StatCard label="Open" value={proposalRows.filter((proposal) => ['pending', 'viewed', 'in_negotiation', 'unknown'].includes(proposal.status)).length} color="var(--color-status-warning)" />
        <StatCard label="Accepted" value={acceptedRows.length} color="var(--color-status-active)" />
        <StatCard label="Declined" value={proposalRows.filter((proposal) => proposal.status === 'declined').length} color="var(--color-brand-red)" />
      </div>

      <Panel>
        <SectionHeader number="2" title="Active Proposals" sub={`${proposalRows.length} proposal records`} />
        <div className="flex gap-2 mb-3">
          {(['All', 'Open', 'Accepted', 'Declined'] as const).map((option) => (
            <button
              key={option}
              onClick={() => setFilter(option)}
              className="text-micro font-semibold px-3 py-1 chamfer-4 transition-all"
              style={{
                background: filter === option ? 'color-mix(in srgb, var(--color-status-warning) 9%, transparent)' : 'transparent',
                color: filter === option ? 'var(--color-status-warning)' : 'rgba(255,255,255,0.4)',
                border: `1px solid ${filter === option ? 'color-mix(in srgb, var(--color-status-warning) 25%, transparent)' : 'rgba(255,255,255,0.08)'}`,
              }}
            >
              {option}
            </button>
          ))}
        </div>

        {status === 'loading' || status === 'idle' ? (
          <QuantumEmptyState title="Loading proposals..." description="Connecting to ROI proposal telemetry." icon="activity" />
        ) : status === 'error' ? (
          <QuantumEmptyState title="Proposal telemetry unavailable" description={error ?? 'Unable to load proposal telemetry.'} icon="activity" />
        ) : filteredRows.length === 0 ? (
          <QuantumEmptyState title="No proposals in this view" description="No records currently match this filter." icon="activity" />
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-body">
              <thead>
                <tr className="border-b border-border-subtle">
                  {['Agency', 'Sent Date', 'Value/yr', 'Status', 'Days Open', 'Action'].map((header) => (
                    <th key={header} className="text-left py-2 pr-4 text-zinc-500 font-semibold uppercase tracking-wider text-micro">{header}</th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {filteredRows.map((proposal) => (
                  <tr key={proposal.id} className="border-b border-border-subtle hover:bg-zinc-950/[0.02]">
                    <td className="py-2 pr-4 font-semibold text-zinc-100">{proposal.agency}</td>
                    <td className="py-2 pr-4 text-zinc-400">{proposal.sentDateLabel}</td>
                    <td className="py-2 pr-4 font-mono text-status-warning">{proposal.valueLabel}</td>
                    <td className="py-2 pr-4"><Badge label={proposal.statusLabel} status={proposal.statusKey} /></td>
                    <td className="py-2 pr-4 text-zinc-400">{proposal.daysOpen} days</td>
                    <td className="py-2 pr-4">
                      <button
                        className="text-micro font-semibold px-2 py-0.5 chamfer-4"
                        style={{
                          background: proposal.statusKey === 'error' ? 'color-mix(in srgb, var(--color-brand-red) 6%, transparent)' : 'color-mix(in srgb, var(--color-status-warning) 6%, transparent)',
                          color: proposal.statusKey === 'error' ? 'var(--color-brand-red)' : 'var(--color-status-warning)',
                          border: `1px solid ${proposal.statusKey === 'error' ? 'color-mix(in srgb, var(--color-brand-red) 14%, transparent)' : 'color-mix(in srgb, var(--color-status-warning) 14%, transparent)'}`,
                        }}
                      >
                        {proposal.actionLabel}
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </Panel>

      <Panel>
        <SectionHeader number="3" title="Proposal Analytics" sub="Conversion and pipeline posture" />
        <div className="grid grid-cols-4 gap-3">
          <StatCard label="Total Events" value={kpis?.total_events ?? (() => { throw new Error('Unsafe silent fallback. Dependency missing.'); })()} color="var(--color-status-info)" />
          <StatCard label="Active Subs" value={kpis?.active_subscriptions ?? (() => { throw new Error('Unsafe silent fallback. Dependency missing.'); })()} color="var(--color-status-active)" />
          <StatCard label="Accept Rate" value={kpis ? `${kpis.proposal_to_paid_conversion_pct.toFixed(2)}%` : '—'} color="var(--color-status-active)" />
          <StatCard label="Pipeline Value" value={`$${((pipeline?.pending_pipeline_cents ?? (() => { throw new Error('Unsafe silent fallback. Dependency missing.'); })()) / 100).toLocaleString()}`} color="var(--color-status-warning)" />
        </div>
        <div className="mt-4 space-y-3">
          <div>
            <div className="flex justify-between mb-1.5">
              <span className="text-body text-zinc-400">Accept Rate</span>
              <span className="text-body font-bold text-status-active">{kpis ? `${kpis.proposal_to_paid_conversion_pct.toFixed(2)}%` : '—'}</span>
            </div>
            <ProgressBar value={kpis?.proposal_to_paid_conversion_pct ?? (() => { throw new Error('Unsafe silent fallback. Dependency missing.'); })()} max={100} color="var(--color-status-active)" />
          </div>
          <div>
            <div className="flex justify-between mb-1.5">
              <span className="text-body text-zinc-400">Pipeline / MRR Ratio</span>
              <span className="text-body font-bold text-status-warning">{(pipeline?.pipeline_to_mrr_ratio ?? (() => { throw new Error('Unsafe silent fallback. Dependency missing.'); })()).toFixed(2)}x</span>
            </div>
            <ProgressBar value={Math.min((pipeline?.pipeline_to_mrr_ratio ?? (() => { throw new Error('Unsafe silent fallback. Dependency missing.'); })()) * 20, 100)} max={100} color="var(--color-status-warning)" />
          </div>
        </div>
      </Panel>

      <Panel>
        <SectionHeader number="4" title="Follow-Up Queue" sub={`${followUpRows.length} proposal(s) flagged`} />
        {followUpRows.length === 0 ? (
          <QuantumEmptyState title="No aged follow-ups" description="No proposal is currently beyond follow-up SLA threshold." icon="activity" />
        ) : (
          <div className="space-y-2">
            {followUpRows.map((proposal) => (
              <div key={`followup-${proposal.id}`} className="flex items-center justify-between p-3 bg-bg-input border border-amber-500/[0.1] chamfer-4">
                <div>
                  <div className="flex items-center gap-2 mb-0.5">
                    <span className="text-[12px] font-semibold text-zinc-100">{proposal.agency}</span>
                    <Badge label={proposal.statusLabel} status={proposal.statusKey} />
                  </div>
                  <div className="flex items-center gap-3">
                    <span className="text-micro text-zinc-500">Sent {proposal.sentDateLabel}</span>
                    <span className="text-micro text-zinc-500">·</span>
                    <span className="text-micro text-zinc-500">Open: {proposal.daysOpen} day(s)</span>
                    <span className="text-micro font-mono text-status-warning">{proposal.valueLabel}/yr</span>
                  </div>
                </div>
                <button
                  className="text-micro font-semibold px-3 py-1.5 chamfer-4"
                  style={{ background: 'color-mix(in srgb, var(--color-status-warning) 9%, transparent)', color: 'var(--q-yellow)', border: '1px solid color-mix(in srgb, var(--color-status-warning) 19%, transparent)' }}
                >
                  Send Email
                </button>
              </div>
            ))}
          </div>
        )}
      </Panel>

      <Panel>
        <SectionHeader number="5" title="Create Proposal" sub="Create a tracked proposal from an ROI scenario" />
        <div className="grid grid-cols-3 gap-3 mb-3">
          <div>
            <label className="text-micro text-zinc-500 block mb-1">Agency Name</label>
            <input
              value={newAgency}
              onChange={(event) => setNewAgency(event.target.value)}
              placeholder="Agency H"
              className="w-full bg-bg-input border border-border-DEFAULT text-body text-zinc-100 px-3 py-2 chamfer-4 outline-none focus:border-status-warning"
            />
          </div>
          <div>
            <label className="text-micro text-zinc-500 block mb-1">Contact Email</label>
            <input
              type="email"
              value={newEmail}
              onChange={(event) => setNewEmail(event.target.value)}
              placeholder="contact@agencyh.com"
              className="w-full bg-bg-input border border-border-DEFAULT text-body text-zinc-100 px-3 py-2 chamfer-4 outline-none focus:border-status-warning"
            />
          </div>
          <div>
            <label className="text-micro text-zinc-500 block mb-1">ROI Scenario ID</label>
            <input
              value={newScenarioId}
              onChange={(event) => setNewScenarioId(event.target.value)}
              placeholder="scenario-uuid"
              className="w-full bg-bg-input border border-border-DEFAULT text-body text-zinc-100 px-3 py-2 chamfer-4 outline-none focus:border-status-warning"
            />
          </div>
        </div>

        {createError && <div className="text-xs text-red-400 mb-3">{createError}</div>}

        <button
          disabled={creating || !newAgency || !newEmail || !newScenarioId}
          onClick={() => { void handleCreateProposal(); }}
          className="text-body font-bold px-6 py-2.5 chamfer-4 transition-all disabled:opacity-30 hover:opacity-90"
          style={{ background: 'var(--color-status-warning)', color: '#000' }}
        >
          {creating ? 'Creating Proposal…' : 'Create ROI Proposal'}
        </button>
      </Panel>
    </div>
  );
}
