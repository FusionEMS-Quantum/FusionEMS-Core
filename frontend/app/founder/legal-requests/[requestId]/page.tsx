'use client';

import { useEffect, useState } from 'react';
import { useParams } from 'next/navigation';
import { ErrorState } from '@/components/ui/ErrorState';
import { NextBestActionCard, type NextAction } from '@/components/ui/NextBestActionCard';
import { QuantumEmptyState } from '@/components/ui/QuantumEmptyState';
import { SeverityBadge } from '@/components/ui/SeverityBadge';
import { StatusChip } from '@/components/ui/StatusChip';
import { TimelinePanel } from '@/components/ui/TimelinePanel';
import { FounderStatusBar } from '@/components/shells/FounderCommand';
import {
  buildFounderLegalPacket,
  closeFounderLegalRequest,
  createFounderLegalDeliveryLink,
  getFounderLegalRequestDetail,
  reviewFounderLegalRequest,
} from '@/services/api';
import type { SeverityLevel } from '@/lib/design-system/tokens';

type Detail = {
  id: string;
  request_type: string;
  status: string;
  requester_name: string;
  requesting_party: string;
  requesting_entity?: string;
  patient_first_name?: string;
  patient_last_name?: string;
  patient_dob?: string;
  mrn?: string;
  csn?: string;
  deadline_at?: string;
  triage_summary: {
    urgency_level: string;
    deadline_risk: string;
    rationale: string;
    mismatch_signals: string[];
    likely_invalid_or_incomplete: boolean;
  };
  missing_items: Array<{ code: string; title: string; detail: string; severity: string }>;
  required_document_checklist: Array<{ code: string; label: string; satisfied: boolean }>;
  redaction_mode: string;
  review_gate: Record<string, unknown>;
  packet_manifest: Record<string, unknown>;
  uploads: Array<{ id: string; document_kind: string; file_name: string; uploaded_at: string }>;
  audit_timeline: Array<{ event_type: string; created_at: string; payload: Record<string, unknown> }>;
  custody_timeline: Array<{ event_type: string; state: string; created_at: string; evidence: Record<string, unknown> }>;
};

function mapDetailSeverity(detail: Detail): SeverityLevel {
  if (detail.status === 'missing_docs' || detail.triage_summary.deadline_risk === 'high') return 'BLOCKING';
  if (detail.status === 'under_review' || detail.status === 'packet_building') return 'HIGH';
  if (detail.missing_items.length > 0 || detail.triage_summary.deadline_risk === 'watch') return 'MEDIUM';
  if (detail.status === 'delivered' || detail.status === 'closed') return 'INFORMATIONAL';
  return 'LOW';
}

export default function FounderLegalRequestDetailPage() {
  const params = useParams<{ requestId: string }>();
  const requestId = params?.requestId;

  const [detail, setDetail] = useState<Detail | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);
  const [working, setWorking] = useState(false);
  const [deliveryUrl, setDeliveryUrl] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  const load = async () => {
    if (!requestId) return;
    try {
      setLoading(true);
      setError(null);
      const data = await getFounderLegalRequestDetail(requestId);
      setDetail(data as Detail);
    } catch {
      setDetail(null);
      setError('Unable to load legal request detail.');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    load().catch(() => {
      setError('Unable to load legal request detail.');
    });
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [requestId]);

  const runAction = async (fn: () => Promise<void>, successMessage: string) => {
    setWorking(true);
    setError(null);
    setNotice(null);
    try {
      await fn();
      await load();
      setNotice(successMessage);
    } catch {
      setError('Action failed. Please retry.');
    } finally {
      setWorking(false);
    }
  };

  if (loading) {
    return (
      <div className="mx-auto max-w-7xl p-6">
        <QuantumEmptyState
          title="Loading legal request command view"
          description="Pulling intake, custody, and release telemetry for this request."
        />
      </div>
    );
  }

  if (!detail) {
    return (
      <div className="mx-auto max-w-7xl p-6">
        <ErrorState
          title="Legal request detail unavailable"
          message={error || 'Unable to load legal request detail.'}
          onRetry={() => window.location.reload()}
          retryLabel="Reload Request"
        />
      </div>
    );
  }

  const detailSeverity = mapDetailSeverity(detail);
  const requestActions: NextAction[] = [
    ...(detail.missing_items.length > 0 ? [{
      id: 'request-missing-docs',
      title: `Resolve ${detail.missing_items.length} missing documentation blocker(s)`,
      severity: 'BLOCKING' as const,
      domain: 'Legal Intake',
    }] : []),
    ...(detail.status !== 'packet_building' && detail.status !== 'delivered' && detail.status !== 'closed' ? [{
      id: 'build-packet',
      title: 'Build secure release packet after review gate approval',
      severity: 'HIGH' as const,
      domain: 'Legal Fulfillment',
    }] : []),
    ...(detail.status === 'packet_building' ? [{
      id: 'delivery-link',
      title: 'Issue secure one-time delivery link',
      severity: 'MEDIUM' as const,
      domain: 'Legal Delivery',
    }] : []),
    ...(detail.status === 'delivered' || detail.status === 'closed' ? [{
      id: 'monitor-audit',
      title: 'Monitor audit and custody timeline for post-release risk',
      severity: 'INFORMATIONAL' as const,
      domain: 'Legal Audit',
    }] : []),
  ];

  return (
    <div className="mx-auto max-w-7xl space-y-6 p-6">
      <FounderStatusBar
        isLive
        activeIncidents={
          (detail.status === 'missing_docs' ? 1 : 0)
          + (detail.triage_summary.deadline_risk === 'high' ? 1 : 0)
          + detail.missing_items.length
        }
      />

      <div>
        <div className="text-xs uppercase tracking-[0.2em] text-[rgba(255,106,0,0.80)]">Legal Request Detail</div>
        <h1 className="text-2xl font-black text-white">
          {detail.request_type.replace('_', ' ').toUpperCase()} · {detail.requester_name}
        </h1>
        <div className="mt-3 flex flex-wrap items-center gap-2">
          <SeverityBadge severity={detailSeverity} size="sm" />
          <StatusChip status={detail.status === 'missing_docs' ? 'warning' : detail.status === 'delivered' ? 'active' : 'info'}>
            {detail.status}
          </StatusChip>
          <StatusChip status={detail.triage_summary.deadline_risk === 'high' ? 'critical' : detail.triage_summary.deadline_risk === 'watch' ? 'warning' : 'neutral'}>
            deadline {detail.triage_summary.deadline_risk}
          </StatusChip>
        </div>
      </div>

      <NextBestActionCard actions={requestActions} title="Request-Level Next Best Actions" maxVisible={4} />

      {error && <div className="border border-[var(--color-brand-red)]/40 bg-[var(--color-brand-red)]/10 p-3 text-sm text-[var(--color-brand-red)]">{error}</div>}
      {notice && <div className="border border-[var(--color-status-active)]/40 bg-[var(--color-status-active)]/10 p-3 text-sm text-[var(--color-status-active)]">{notice}</div>}
      {deliveryUrl && (
        <div className="border border-[var(--color-status-info)]/40 bg-[var(--color-status-info)]/10 p-3 text-sm text-[var(--color-status-info)] break-all">
          Secure one-time delivery URL: {deliveryUrl}
        </div>
      )}

      <div className="grid grid-cols-1 gap-4 lg:grid-cols-3">
        <div className="border border-white/10 bg-[var(--color-bg-base)]/[0.03] p-4">
          <div className="mb-2 text-xs uppercase tracking-wider text-white/50">Requester</div>
          <div className="text-sm text-[var(--color-text-primary)]">{detail.requester_name}</div>
          <div className="text-xs text-[var(--color-text-muted)]">{detail.requesting_party} · {detail.requesting_entity || 'n/a'}</div>
          <div className="mt-3 text-xs text-[var(--color-text-muted)]">
            Patient: {detail.patient_first_name || '—'} {detail.patient_last_name || '—'} · DOB {detail.patient_dob || '—'}
          </div>
          <div className="text-xs text-[var(--color-text-muted)]">MRN {detail.mrn || '—'} · CSN {detail.csn || '—'}</div>
        </div>

        <div className="border border-white/10 bg-[var(--color-bg-base)]/[0.03] p-4">
          <div className="mb-2 text-xs uppercase tracking-wider text-white/50">Status & Risk</div>
          <div className="flex flex-wrap gap-2">
            <SeverityBadge severity={detailSeverity} size="sm" />
            <StatusChip status={detail.status === 'missing_docs' ? 'warning' : detail.status === 'delivered' ? 'active' : 'info'}>
              {detail.status}
            </StatusChip>
            <StatusChip status={detail.triage_summary.deadline_risk === 'high' ? 'critical' : detail.triage_summary.deadline_risk === 'watch' ? 'warning' : 'neutral'}>
              deadline {detail.triage_summary.deadline_risk}
            </StatusChip>
            <StatusChip status={detail.triage_summary.urgency_level === 'critical' ? 'critical' : detail.triage_summary.urgency_level === 'high' ? 'warning' : 'neutral'}>
              urgency {detail.triage_summary.urgency_level}
            </StatusChip>
          </div>
          <div className="mt-3 text-sm text-[var(--color-text-secondary)]">{detail.triage_summary.rationale}</div>
        </div>

        <div className="border border-white/10 bg-[var(--color-bg-base)]/[0.03] p-4">
          <div className="mb-2 text-xs uppercase tracking-wider text-white/50">Review Gate</div>
          <div className="text-xs text-[var(--color-text-muted)]">Redaction mode: {detail.redaction_mode}</div>
          <div className="mt-2 flex flex-wrap gap-2">
            <button
              type="button"
              disabled={working}
              onClick={() =>
                runAction(
                  async () => {
                    await reviewFounderLegalRequest(detail.id, {
                      authority_valid: true,
                      identity_verified: true,
                      completeness_valid: true,
                      document_sufficient: true,
                      minimum_necessary_scope: true,
                      redaction_mode: 'court_safe_minimum_necessary',
                      delivery_method: 'secure_one_time_link',
                      decision: 'approve',
                      decision_notes: 'Approved for packet build under minimum necessary scope.',
                    });
                  },
                  'Review approved.'
                )
              }
              className="quantum-btn-sm"
            >
              Approve Review
            </button>
            <button
              type="button"
              disabled={working}
              onClick={() =>
                runAction(
                  async () => {
                    await reviewFounderLegalRequest(detail.id, {
                      authority_valid: false,
                      identity_verified: false,
                      completeness_valid: false,
                      document_sufficient: false,
                      minimum_necessary_scope: true,
                      redaction_mode: 'court_safe_minimum_necessary',
                      delivery_method: 'secure_one_time_link',
                      decision: 'request_more_docs',
                      decision_notes: 'Missing required legal support documents.',
                    });
                  },
                  'Moved to missing docs.'
                )
              }
              className="quantum-btn-sm"
            >
              Request More Docs
            </button>
          </div>
        </div>
      </div>

      <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
        <div className="border border-white/10 bg-[var(--color-bg-base)]/[0.03] p-4">
          <div className="mb-2 text-xs uppercase tracking-wider text-white/50">Missing Item Cards</div>
          {detail.missing_items.length === 0 ? (
            <QuantumEmptyState
              title="No missing-item blockers"
              description="All currently required legal intake artifacts are satisfied for this request."
              className="py-6"
            />
          ) : (
            <div className="space-y-2">
              {detail.missing_items.map((item) => (
                <div key={item.code} className="border border-[var(--color-brand-red)]/30 bg-[var(--color-brand-red)]/10 p-2 text-sm">
                  <div className="font-semibold text-[var(--color-brand-red)]">{item.title}</div>
                  <div className="text-[var(--color-brand-red)]/90">{item.detail}</div>
                </div>
              ))}
            </div>
          )}
        </div>

        <div className="border border-white/10 bg-[var(--color-bg-base)]/[0.03] p-4">
          <div className="mb-2 text-xs uppercase tracking-wider text-white/50">Required-Document Checklist</div>
          <div className="space-y-1">
            {detail.required_document_checklist.map((item) => (
              <div key={item.code} className="flex items-center justify-between text-sm">
                <span className="text-[var(--color-text-secondary)]">{item.label}</span>
                <StatusChip status={item.satisfied ? 'active' : 'warning'} size="sm">
                  {item.satisfied ? 'received' : 'missing'}
                </StatusChip>
              </div>
            ))}
          </div>
        </div>
      </div>

      <div className="border border-white/10 bg-[var(--color-bg-base)]/[0.03] p-4">
        <div className="mb-2 text-xs uppercase tracking-wider text-white/50">Packet & Delivery Controls</div>
        <div className="flex flex-wrap gap-2">
          <button
            type="button"
            disabled={working}
            onClick={() => runAction(async () => { await buildFounderLegalPacket(detail.id); }, 'Packet generated.')}
            className="quantum-btn-primary"
          >
            Build Packet
          </button>
          <button
            type="button"
            disabled={working}
            onClick={() =>
              runAction(
                async () => {
                  const result = await createFounderLegalDeliveryLink(detail.id, { expires_in_hours: 48 });
                  setDeliveryUrl(result.delivery_url || null);
                },
                'Secure one-time delivery link created.'
              )
            }
            className="quantum-btn"
          >
            Create One-Time Link
          </button>
          <button
            type="button"
            disabled={working}
            onClick={() => runAction(async () => { await closeFounderLegalRequest(detail.id); }, 'Request closed.')}
            className="quantum-btn"
          >
            Close Request
          </button>
        </div>

        <pre className="mt-3 max-h-60 overflow-auto border border-white/10 bg-[var(--color-bg-base)]/30 p-3 text-xs text-[var(--color-text-secondary)]">
          {JSON.stringify(detail.packet_manifest || {}, null, 2)}
        </pre>
      </div>

      <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
        <TimelinePanel
          title="Chain of Custody Timeline"
          events={detail.custody_timeline.map((event, index) => ({
            id: `${event.event_type}-${index}`,
            timestamp: new Date(event.created_at).toLocaleString(),
            title: event.event_type,
            description: event.state,
            status: event.state === 'ANOMALY' || event.state === 'REVIEW_REQUIRED' ? 'critical' : 'active',
            detail: <pre className="whitespace-pre-wrap text-xs">{JSON.stringify(event.evidence, null, 2)}</pre>,
          }))}
          emptyMessage="No chain-of-custody events logged."
        />

        <TimelinePanel
          title="Audit Log Timeline"
          events={detail.audit_timeline.map((event, index) => ({
            id: `${event.event_type}-${index}`,
            timestamp: new Date(event.created_at).toLocaleString(),
            title: event.event_type,
            status: 'info',
            detail: <pre className="whitespace-pre-wrap text-xs">{JSON.stringify(event.payload, null, 2)}</pre>,
          }))}
          emptyMessage="No audit events logged."
        />
      </div>
    </div>
  );
}
