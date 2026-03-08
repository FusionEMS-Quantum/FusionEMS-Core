'use client';

import { useCallback, useEffect, useState } from 'react';
import {
  addFounderSyncDeadLetter,
  createFounderSyncJob,
  getFounderFailedSyncJobs,
  getFounderIntegrationCommandSummary,
} from '@/services/api';

type FounderCommandAction = {
  domain: string;
  severity: string;
  summary: string;
  recommended_action: string;
};

type IntegrationSummary = {
  degraded_or_disabled_installs: number;
  failed_sync_jobs_24h: number;
  dead_letter_records_24h: number;
  pending_webhook_retries: number;
  revoked_or_rotating_api_credentials: number;
  quota_denial_windows_24h: number;
  top_actions: FounderCommandAction[];
};

type SyncJob = {
  id: string;
  direction: string;
  state: string;
  records_attempted: number;
  records_failed: number;
  updated_at: string;
};

type SyncJobFormState = {
  tenantConnectorInstallId: string;
  direction: 'INBOUND' | 'OUTBOUND';
  errorSummaryJson: string;
};

function Stat({ label, value }: { label: string; value: number }) {
  return (
    <div className=" border border-white/10 bg-zinc-950/[0.03] p-4">
      <div className="text-xs uppercase tracking-wider text-white/50">{label}</div>
      <div className="mt-2 text-3xl font-black text-white">{value}</div>
    </div>
  );
}

export default function FounderIntegrationCommandPage() {
  const [summary, setSummary] = useState<IntegrationSummary | null>(null);
  const [failedJobs, setFailedJobs] = useState<SyncJob[]>([]);
  const [loadError, setLoadError] = useState<string | null>(null);
  const [actionMessage, setActionMessage] = useState<string | null>(null);
  const [creatingSyncJob, setCreatingSyncJob] = useState(false);
  const [addingDeadLetterForJobId, setAddingDeadLetterForJobId] = useState<string | null>(null);
  const [syncJobForm, setSyncJobForm] = useState<SyncJobFormState>({
    tenantConnectorInstallId: '',
    direction: 'OUTBOUND',
    errorSummaryJson: '{}',
  });
  const [deadLetterForm, setDeadLetterForm] = useState({
    syncJobId: '',
    externalRecordRef: '',
    reason: '',
    payloadJson: '{}',
  });

  const load = useCallback(async () => {
    try {
      setLoadError(null);
      const [summaryRes, jobsRes] = await Promise.all([
        getFounderIntegrationCommandSummary(),
        getFounderFailedSyncJobs(25),
      ]);
      setSummary(summaryRes as IntegrationSummary);
      setFailedJobs(Array.isArray(jobsRes) ? (jobsRes as SyncJob[]) : []);
    } catch {
      setSummary(null);
      setFailedJobs([]);
      setLoadError('Unable to load integration command center data.');
    }
  }, []);

  useEffect(() => {
    load().catch(() => {
      setLoadError('Unable to load integration command center data.');
    });
  }, [load]);

  const handleCreateSyncJob = async () => {
    setActionMessage(null);
    setLoadError(null);

    let errorSummary: Record<string, unknown> = {};
    try {
      errorSummary = JSON.parse(syncJobForm.errorSummaryJson);
    } catch {
      setLoadError('Sync job error summary must be valid JSON.');
      return;
    }

    setCreatingSyncJob(true);
    try {
      await createFounderSyncJob({
        tenant_connector_install_id: syncJobForm.tenantConnectorInstallId,
        direction: syncJobForm.direction,
        state: 'QUEUED',
        records_attempted: 0,
        records_succeeded: 0,
        records_failed: 0,
        error_summary: errorSummary,
      });
      setActionMessage('Sync job created successfully.');
      setSyncJobForm((prev) => ({
        ...prev,
        errorSummaryJson: '{}',
      }));
      await load();
    } catch {
      setLoadError('Failed to create sync job. Verify connector install ID and try again.');
    } finally {
      setCreatingSyncJob(false);
    }
  };

  const openDeadLetterForm = (jobId: string) => {
    setDeadLetterForm({
      syncJobId: jobId,
      externalRecordRef: '',
      reason: '',
      payloadJson: '{}',
    });
    setActionMessage(null);
    setLoadError(null);
  };

  const handleAddDeadLetter = async () => {
    if (!deadLetterForm.syncJobId) {
      return;
    }

    setActionMessage(null);
    setLoadError(null);

    let payload: Record<string, unknown> = {};
    try {
      payload = JSON.parse(deadLetterForm.payloadJson);
    } catch {
      setLoadError('Dead-letter payload must be valid JSON.');
      return;
    }

    setAddingDeadLetterForJobId(deadLetterForm.syncJobId);
    try {
      await addFounderSyncDeadLetter(deadLetterForm.syncJobId, {
        external_record_ref: deadLetterForm.externalRecordRef,
        reason: deadLetterForm.reason,
        payload,
      });
      setActionMessage('Dead-letter record added successfully.');
      setDeadLetterForm({
        syncJobId: '',
        externalRecordRef: '',
        reason: '',
        payloadJson: '{}',
      });
      await load();
    } catch {
      setLoadError('Failed to add dead-letter record for this sync job.');
    } finally {
      setAddingDeadLetterForJobId(null);
    }
  };

  if (!summary) {
    return (
      <div className="mx-auto max-w-7xl p-6">
        <div className=" border border-white/10 bg-zinc-950/[0.03] p-4 text-sm text-white/70">
          {loadError || 'Loading integration command center…'}
        </div>
      </div>
    );
  }

  return (
    <div className="mx-auto max-w-7xl space-y-6 p-6">
      <div>
          <div className="text-xs uppercase tracking-[0.2em] text-[rgba(255,77,0,0.80)]">Founder Command</div>
        <h1 className="text-2xl font-black text-white">Integration & Connectors Command Center</h1>
      </div>

      {loadError && (
        <div className=" border border-red-500/30 bg-red-500/10 p-3 text-sm text-red-300">{loadError}</div>
      )}
      {actionMessage && (
        <div className=" border border-green-500/30 bg-green-500/10 p-3 text-sm text-green-300">{actionMessage}</div>
      )}

      <div className="grid grid-cols-1 gap-3 md:grid-cols-3 lg:grid-cols-6">
        <Stat label="Degraded Installs" value={summary.degraded_or_disabled_installs} />
        <Stat label="Failed Sync (24h)" value={summary.failed_sync_jobs_24h} />
        <Stat label="Dead Letters (24h)" value={summary.dead_letter_records_24h} />
        <Stat label="Webhook Retries" value={summary.pending_webhook_retries} />
        <Stat label="Key Rotation/Revoked" value={summary.revoked_or_rotating_api_credentials} />
        <Stat label="Quota Denials (24h)" value={summary.quota_denial_windows_24h} />
      </div>

      <div className=" border border-white/10 bg-zinc-950/[0.03] p-4">
        <div className="mb-3 text-xs uppercase tracking-wider text-white/50">Create Connector Sync Job</div>
        <div className="grid grid-cols-1 gap-3 md:grid-cols-2 lg:grid-cols-4">
          <input
            value={syncJobForm.tenantConnectorInstallId}
            onChange={(event) =>
              setSyncJobForm((prev) => ({ ...prev, tenantConnectorInstallId: event.target.value }))
            }
            placeholder="Tenant Connector Install UUID"
            className=" border border-white/15 bg-black/30 px-3 py-2 text-sm text-white"
          />
          <select
            value={syncJobForm.direction}
            onChange={(event) => setSyncJobForm((prev) => ({ ...prev, direction: event.target.value as 'INBOUND' | 'OUTBOUND' }))}
            className=" border border-white/15 bg-black/30 px-3 py-2 text-sm text-white"
          >
            <option value="OUTBOUND">OUTBOUND</option>
            <option value="INBOUND">INBOUND</option>
          </select>
          <button
            type="button"
            onClick={handleCreateSyncJob}
            disabled={creatingSyncJob || !syncJobForm.tenantConnectorInstallId}
              className=" border border-orange-400/60 bg-[rgba(255,77,0,0.20)] px-3 py-2 text-sm font-semibold text-[#FF4D00] disabled:opacity-50"
          >
            {creatingSyncJob ? 'Creating…' : 'Create Sync Job'}
          </button>
          <textarea
            value={syncJobForm.errorSummaryJson}
            onChange={(event) => setSyncJobForm((prev) => ({ ...prev, errorSummaryJson: event.target.value }))}
            placeholder='Sync Payload JSON (example: {"x12_payload_base64":"...","file_name":"batch-001.x12"})'
            className=" border border-white/15 bg-black/30 px-3 py-2 text-sm text-white md:col-span-2 lg:col-span-2"
          />
        </div>
      </div>

      <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
        <div className=" border border-white/10 bg-zinc-950/[0.03] p-4">
          <div className="mb-3 text-xs uppercase tracking-wider text-white/50">Top Actions</div>
          <div className="space-y-2">
            {summary.top_actions.length === 0 && <div className="text-sm text-white/60">No immediate integration actions.</div>}
            {summary.top_actions.map((action, idx) => (
              <div key={`${action.summary}-${idx}`} className=" border border-white/10 bg-black/20 p-3">
                  <div className="text-xs font-bold uppercase tracking-wider text-[#FF4D00]">{action.severity}</div>
                <div className="mt-1 text-sm font-semibold text-white">{action.summary}</div>
                <div className="mt-1 text-sm text-white/70">{action.recommended_action}</div>
              </div>
            ))}
          </div>
        </div>

        <div className=" border border-white/10 bg-zinc-950/[0.03] p-4">
          <div className="mb-3 text-xs uppercase tracking-wider text-white/50">Failed Sync Jobs</div>
          <div className="space-y-2">
            {failedJobs.length === 0 && <div className="text-sm text-white/60">No failed sync jobs.</div>}
            {failedJobs.map((job) => (
              <div key={job.id} className=" border border-white/10 bg-black/20 p-3">
                <div className="flex items-center justify-between">
                  <div className="text-sm font-semibold text-white">{job.direction}</div>
                  <div className="text-xs uppercase tracking-wider text-red-300">{job.state}</div>
                </div>
                <div className="mt-1 text-xs text-white/60">
                  attempted: {job.records_attempted} • failed: {job.records_failed}
                </div>
                <div className="mt-3">
                  <button
                    type="button"
                    onClick={() => openDeadLetterForm(job.id)}
                    className=" border border-red-400/50 bg-red-500/10 px-2 py-1 text-xs font-semibold text-red-300"
                  >
                    Add Dead Letter
                  </button>
                </div>
                {deadLetterForm.syncJobId === job.id && (
                  <div className="mt-3 space-y-2  border border-white/10 bg-black/30 p-3">
                    <input
                      value={deadLetterForm.externalRecordRef}
                      onChange={(event) =>
                        setDeadLetterForm((prev) => ({ ...prev, externalRecordRef: event.target.value }))
                      }
                      placeholder="External Record Reference"
                      className="w-full  border border-white/15 bg-black/40 px-3 py-2 text-xs text-white"
                    />
                    <input
                      value={deadLetterForm.reason}
                      onChange={(event) =>
                        setDeadLetterForm((prev) => ({ ...prev, reason: event.target.value }))
                      }
                      placeholder="Failure Reason"
                      className="w-full  border border-white/15 bg-black/40 px-3 py-2 text-xs text-white"
                    />
                    <textarea
                      value={deadLetterForm.payloadJson}
                      onChange={(event) =>
                        setDeadLetterForm((prev) => ({ ...prev, payloadJson: event.target.value }))
                      }
                      placeholder='Payload JSON (example: {"field":"value"})'
                      className="w-full  border border-white/15 bg-black/40 px-3 py-2 text-xs text-white"
                    />
                    <button
                      type="button"
                      onClick={handleAddDeadLetter}
                      disabled={
                        addingDeadLetterForJobId === job.id ||
                        !deadLetterForm.externalRecordRef ||
                        !deadLetterForm.reason
                      }
                      className=" border border-red-400/60 bg-red-500/20 px-3 py-1.5 text-xs font-semibold text-red-200 disabled:opacity-50"
                    >
                      {addingDeadLetterForJobId === job.id ? 'Adding…' : 'Submit Dead Letter'}
                    </button>
                  </div>
                )}
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}
