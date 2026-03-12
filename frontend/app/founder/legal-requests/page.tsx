'use client';

import Link from 'next/link';
import { useEffect, useMemo, useState } from 'react';
import { ErrorState } from '@/components/ui/ErrorState';
import { NextBestActionCard, type NextAction } from '@/components/ui/NextBestActionCard';
import { QuantumEmptyState } from '@/components/ui/QuantumEmptyState';
import { SeverityBadge } from '@/components/ui/SeverityBadge';
import { StatusChip } from '@/components/ui/StatusChip';
import { FounderStatusBar } from '@/components/shells/FounderCommand';
import {
  getFounderLegalQueue,
  getFounderLegalSummary,
  type LegalQueueItem,
  type LegalSummary,
} from '@/services/api';
import type { SeverityLevel } from '@/lib/design-system/tokens';

const LANES = [
  { key: 'new_requests', label: 'New Requests' },
  { key: 'missing_docs', label: 'Missing Docs' },
  { key: 'deadline_risk', label: 'Deadline Risk' },
  { key: 'redaction_queue', label: 'Redaction Queue' },
  { key: 'delivery_queue', label: 'Delivery Queue' },
  { key: 'completed', label: 'Completed' },
  { key: 'high_risk', label: 'High Risk' },
] as const;

function Stat({ label, value }: { label: string; value: number }) {
  return (
    <div className="border border-white/10 bg-[var(--color-bg-base)]/[0.03] p-4">
      <div className="text-xs uppercase tracking-wider text-white/50">{label}</div>
      <div className="mt-2 text-3xl font-black text-white">{value}</div>
    </div>
  );
}

function getQueueSeverity(item: LegalQueueItem): SeverityLevel {
  const missingCount = item.missing_count ?? 0;
  if (item.deadline_risk === 'high' || (item.status === 'missing_docs' && missingCount > 0)) {
    return 'BLOCKING';
  }
  if (item.status === 'under_review' || item.status === 'packet_building') {
    return 'HIGH';
  }
  if (item.deadline_risk === 'watch' || missingCount > 0) {
    return 'MEDIUM';
  }
  if (item.status === 'delivered' || item.status === 'closed') {
    return 'INFORMATIONAL';
  }
  return 'LOW';
}

function getLaneSummarySeverity(laneKey: (typeof LANES)[number]['key']): SeverityLevel {
  if (laneKey === 'missing_docs' || laneKey === 'deadline_risk' || laneKey === 'high_risk') return 'BLOCKING';
  if (laneKey === 'redaction_queue' || laneKey === 'delivery_queue') return 'HIGH';
  if (laneKey === 'new_requests') return 'MEDIUM';
  return 'INFORMATIONAL';
}

export default function FounderLegalRequestsCommandPage() {
  const [summary, setSummary] = useState<LegalSummary | null>(null);
  const [lane, setLane] = useState<(typeof LANES)[number]['key']>('new_requests');
  const [queue, setQueue] = useState<LegalQueueItem[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  const laneCount = useMemo(() => summary?.lane_counts?.[lane] ?? 0, [summary, lane]);

  const nextActions = useMemo<NextAction[]>(() => {
    const actions: NextAction[] = [];
    if (!summary) return actions;
    const laneCounts = summary.lane_counts ?? {};

    if ((laneCounts.missing_docs ?? 0) > 0) {
      actions.push({
        id: 'resolve-missing-docs',
        title: `Resolve ${laneCounts.missing_docs ?? 0} missing-document request(s)`,
        severity: 'BLOCKING',
        domain: 'Legal Requests',
        href: '/founder/legal-requests',
      });
    }

    if ((laneCounts.deadline_risk ?? 0) > 0) {
      actions.push({
        id: 'deadline-risk',
        title: `Triage ${laneCounts.deadline_risk ?? 0} deadline-risk request(s)`,
        severity: 'HIGH',
        domain: 'Legal Requests',
        href: '/founder/legal-requests',
      });
    }

    if ((laneCounts.delivery_queue ?? 0) > 0) {
      actions.push({
        id: 'delivery-queue',
        title: `Advance ${laneCounts.delivery_queue ?? 0} request(s) to secure delivery`,
        severity: 'MEDIUM',
        domain: 'Legal Fulfillment',
        href: '/founder/legal-requests',
      });
    }

    if ((laneCounts.high_risk ?? 0) === 0 && (summary.total_open ?? 0) === 0) {
      actions.push({
        id: 'stable-posture',
        title: 'Legal command posture stable — no active blockers',
        severity: 'INFORMATIONAL',
        domain: 'Legal Requests',
        href: '/founder/legal-requests',
      });
    }

    return actions;
  }, [summary]);

  useEffect(() => {
    const load = async () => {
      try {
        setLoading(true);
        setError(null);
        const [summaryRes, queueRes] = await Promise.all([
          getFounderLegalSummary(),
          getFounderLegalQueue(lane, 100),
        ]);
        setSummary(summaryRes);
        setQueue(queueRes);
      } catch {
        setSummary(null);
        setQueue([]);
        setError('Unable to load Legal Requests Command Center.');
      } finally {
        setLoading(false);
      }
    };
    load().catch(() => {
      setError('Unable to load Legal Requests Command Center.');
    });
  }, [lane]);

  if (loading) {
    return (
      <div className="mx-auto max-w-7xl p-6">
        <QuantumEmptyState
          title="Loading legal requests command center"
          description="Synchronizing legal intake, fulfillment, and risk telemetry."
        />
      </div>
    );
  }

  if (!summary) {
    return (
      <div className="mx-auto max-w-7xl p-6">
        <ErrorState
          title="Legal command unavailable"
          message={error || 'Unable to load legal requests command center.'}
          onRetry={() => window.location.reload()}
          retryLabel="Reload Command"
        />
      </div>
    );
  }

  const laneCounts = summary.lane_counts ?? {};
  const urgentDeadlines = summary.urgent_deadlines ?? 0;
  const highRiskRequests = summary.high_risk_requests ?? 0;
  const totalOpen = summary.total_open ?? 0;

  return (
    <div className="mx-auto max-w-7xl space-y-6 p-6">
      <FounderStatusBar
        isLive
        activeIncidents={(laneCounts.missing_docs ?? 0) + urgentDeadlines + highRiskRequests}
      />

      <div>
        <div className="text-xs uppercase tracking-[0.2em] text-[rgba(255,106,0,0.80)]">Founder Command</div>
        <h1 className="text-2xl font-black text-white">Legal Requests Command Center</h1>
        <p className="mt-2 text-sm text-[var(--color-text-secondary)]">
          Intake-to-delivery command board for HIPAA ROI, subpoena, and court-order workflows.
        </p>
        <div className="mt-3 flex flex-wrap items-center gap-2">
          <SeverityBadge severity={highRiskRequests > 0 ? 'BLOCKING' : 'LOW'} size="sm" />
          <StatusChip status={urgentDeadlines > 0 ? 'critical' : 'active'} size="sm">
            urgent deadlines {urgentDeadlines}
          </StatusChip>
          <StatusChip status="info" size="sm">open queue {totalOpen}</StatusChip>
        </div>
      </div>

      <NextBestActionCard actions={nextActions} title="Legal Command Next Best Actions" maxVisible={4} />

      <div className="grid grid-cols-1 gap-3 md:grid-cols-4 lg:grid-cols-6">
        <Stat label="Open Requests" value={totalOpen} />
        <Stat label="Urgent Deadlines" value={urgentDeadlines} />
        <Stat label="High Risk" value={highRiskRequests} />
        <Stat label="Missing Docs" value={laneCounts.missing_docs ?? 0} />
        <Stat label="Ready to Send" value={laneCounts.delivery_queue ?? 0} />
        <Stat label="Delivered/Closed" value={laneCounts.completed ?? 0} />
      </div>

      <div className="border border-white/10 bg-[var(--color-bg-base)]/[0.03] p-4">
        <div className="mb-3 text-xs uppercase tracking-wider text-white/50">Visual Command Board</div>
        <div className="flex flex-wrap gap-2">
          {LANES.map((entry) => (
            <button
              type="button"
              key={entry.key}
              onClick={() => setLane(entry.key)}
              className={`border px-3 py-1.5 text-xs uppercase tracking-wider transition-colors ${
                lane === entry.key
                  ? 'border-orange-400/60 bg-[rgba(255,106,0,0.16)] text-[var(--q-orange)]'
                  : 'border-white/15 bg-[var(--color-bg-base)]/20 text-white/70 hover:text-white'
              }`}
            >
              {entry.label} ({laneCounts[entry.key] ?? 0})
            </button>
          ))}
        </div>
      </div>

      <div className="border border-white/10 bg-[var(--color-bg-base)]/[0.03] p-4">
        <div className="mb-3 flex items-center justify-between">
          <div className="flex items-center gap-2">
            <div className="text-xs uppercase tracking-wider text-white/50">{LANES.find((x) => x.key === lane)?.label}</div>
            <SeverityBadge severity={getLaneSummarySeverity(lane)} size="sm" />
          </div>
          <StatusChip status="info">{laneCount} request(s)</StatusChip>
        </div>

        <div className="space-y-2">
          {queue.length === 0 ? (
            <QuantumEmptyState
              title="No requests in this lane"
              description="This command lane currently has no actionable legal requests."
              className="py-8"
            />
          ) : (
            queue.map((item) => (
              <Link
                key={item.id}
                href={`/founder/legal-requests/${item.id}`}
                className="block border border-white/10 bg-[var(--color-bg-base)]/20 p-3 hover:border-orange-400/50"
              >
                <div className="flex flex-wrap items-center justify-between gap-2">
                  <div>
                    <div className="text-sm font-semibold text-white">
                      {(item.request_type ?? 'unknown').replace('_', ' ').toUpperCase()} · {String(item.requester_name ?? 'Unknown requester')}
                    </div>
                    <div className="text-xs text-[var(--color-text-secondary)]">
                      party: {String(item.requesting_party ?? 'Unknown')} · missing: {item.missing_count ?? 0}
                      {item.deadline_at ? ` · deadline: ${new Date(item.deadline_at).toLocaleString()}` : ''}
                    </div>
                  </div>
                  <div className="flex flex-wrap items-center gap-2">
                    <SeverityBadge severity={getQueueSeverity(item)} size="sm" />
                    <StatusChip status={item.status === 'missing_docs' ? 'warning' : item.status === 'delivered' ? 'active' : 'info'} size="sm">
                      {item.status}
                    </StatusChip>
                    <StatusChip status={item.deadline_risk === 'high' ? 'critical' : item.deadline_risk === 'watch' ? 'warning' : 'neutral'} size="sm">
                      deadline {item.deadline_risk}
                    </StatusChip>
                  </div>
                </div>
              </Link>
            ))
          )}
        </div>
      </div>
    </div>
  );
}
