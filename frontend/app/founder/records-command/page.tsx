'use client';

import { useEffect, useState } from 'react';
import {
  getFounderFailedRecordExports,
  getFounderRecordsCommandSummary,
} from '@/services/api';

type FounderCommandAction = {
  domain: string;
  severity: string;
  summary: string;
  recommended_action: string;
};

type RecordsSummary = {
  draft_or_unsealed_records: number;
  signature_gaps: number;
  low_confidence_ocr_results: number;
  chain_of_custody_anomalies: number;
  pending_release_authorizations: number;
  failed_record_exports: number;
  open_qa_exceptions: number;
  top_actions: FounderCommandAction[];
};

type RecordExport = {
  id: string;
  destination_system: string;
  state: string;
  failure_reason: string | null;
  queued_at: string;
};

function Stat({ label, value }: { label: string; value: number }) {
  return (
    <div className=" border border-white/10 bg-[var(--color-bg-base)]/[0.03] p-4">
      <div className="text-xs uppercase tracking-wider text-white/50">{label}</div>
      <div className="mt-2 text-3xl font-black text-white">{value}</div>
    </div>
  );
}

export default function FounderRecordsCommandPage() {
  const [summary, setSummary] = useState<RecordsSummary | null>(null);
  const [failedExports, setFailedExports] = useState<RecordExport[]>([]);
  const [loadError, setLoadError] = useState<string | null>(null);

  useEffect(() => {
    const load = async () => {
      const [summaryRes, exportsRes] = await Promise.all([
        getFounderRecordsCommandSummary(),
        getFounderFailedRecordExports(25),
      ]);
      setSummary(summaryRes as RecordsSummary);
      setFailedExports(Array.isArray(exportsRes) ? (exportsRes as RecordExport[]) : []);
    };
    load().catch(() => {
      setSummary(null);
      setFailedExports([]);
      setLoadError('Unable to load records command center. Check API connectivity.');
    });
  }, []);

  if (!summary) {
    return (
      <div className="mx-auto max-w-7xl p-6">
        <div
          className={`border p-4 text-sm ${
            loadError
              ? 'border-[var(--color-brand-red)]/30 bg-[var(--color-brand-red)]/[0.08] text-[var(--color-brand-red)]'
              : 'border-white/10 bg-[var(--color-bg-base)]/[0.03] text-white/70'
          }`}
        >
          {loadError ?? 'Loading records command center…'}
        </div>
      </div>
    );
  }

  return (
    <div className="mx-auto max-w-7xl space-y-6 p-6">
      <div>
          <div className="text-xs uppercase tracking-[0.2em] text-[rgba(255,106,0,0.80)]">Founder Command</div>
        <h1 className="text-2xl font-black text-white">Records & Media Command Center</h1>
      </div>

      <div className="grid grid-cols-1 gap-3 md:grid-cols-3 lg:grid-cols-7">
        <Stat label="Draft / Unsealed" value={summary.draft_or_unsealed_records} />
        <Stat label="Signature Gaps" value={summary.signature_gaps} />
        <Stat label="Low OCR" value={summary.low_confidence_ocr_results} />
        <Stat label="Custody Anomalies" value={summary.chain_of_custody_anomalies} />
        <Stat label="Pending Releases" value={summary.pending_release_authorizations} />
        <Stat label="Failed Exports" value={summary.failed_record_exports} />
        <Stat label="QA Exceptions" value={summary.open_qa_exceptions} />
      </div>

      <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
        <div className=" border border-white/10 bg-[var(--color-bg-base)]/[0.03] p-4">
          <div className="mb-3 text-xs uppercase tracking-wider text-white/50">Top Actions</div>
          <div className="space-y-2">
            {summary.top_actions.length === 0 && <div className="text-sm text-white/60">No blocking records actions.</div>}
            {summary.top_actions.map((action, idx) => (
              <div key={`${action.summary}-${idx}`} className=" border border-white/10 bg-[var(--color-bg-base)]/20 p-3">
                  <div className="text-xs font-bold uppercase tracking-wider text-[var(--q-orange)]">{action.severity}</div>
                <div className="mt-1 text-sm font-semibold text-white">{action.summary}</div>
                <div className="mt-1 text-sm text-white/70">{action.recommended_action}</div>
              </div>
            ))}
          </div>
        </div>

        <div className=" border border-white/10 bg-[var(--color-bg-base)]/[0.03] p-4">
          <div className="mb-3 text-xs uppercase tracking-wider text-white/50">Failed Record Exports</div>
          <div className="space-y-2">
            {failedExports.length === 0 && <div className="text-sm text-white/60">No failed exports.</div>}
            {failedExports.map((record) => (
              <div key={record.id} className=" border border-white/10 bg-[var(--color-bg-base)]/20 p-3">
                <div className="flex items-center justify-between">
                  <div className="text-sm font-semibold text-white">{record.destination_system}</div>
                  <div className="text-xs uppercase tracking-wider text-[var(--color-brand-red)]">{record.state}</div>
                </div>
                {record.failure_reason && <div className="mt-1 text-xs text-white/60">{record.failure_reason}</div>}
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}
