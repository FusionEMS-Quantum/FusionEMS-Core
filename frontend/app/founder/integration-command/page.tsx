'use client';

import { useCallback, useEffect, useState } from 'react';
import {
  addFounderSyncDeadLetter,
  createFounderSyncJob,
  getFounderFailedSyncJobs,
  getFounderGrowthSetupWizard,
  getFounderGrowthSummary,
  getFounderIntegrationCommandSummary,
  startFounderLaunchOrchestrator,
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

type GrowthSummaryMetric = {
  key: string;
  value: number;
};

type GrowthSummary = {
  generated_at: string;
  conversion_events_total: number;
  proposals_total: number;
  proposals_pending: number;
  active_subscriptions: number;
  proposal_to_paid_conversion_pct: number;
  pending_pipeline_cents: number;
  active_mrr_cents: number;
  pipeline_to_mrr_ratio: number;
  graph_mailbox_configured: boolean;
  funnel_stage_counts: GrowthSummaryMetric[];
  lead_tier_distribution: GrowthSummaryMetric[];
  lead_score_buckets: GrowthSummaryMetric[];
};

type GrowthConnectionStatus = {
  service_key: string;
  label: string;
  required: boolean;
  connected: boolean;
  install_state: string;
  permissions_state: string;
  permission_errors: string[];
  token_state: string;
  health_state: string;
  last_successful_activity?: string | null;
  last_failed_activity?: string | null;
  retry_count: number;
  available_automations: string[];
  blocking_reason?: string | null;
};

type GrowthSetupWizard = {
  generated_at: string;
  autopilot_ready: boolean;
  blocked_items: string[];
  services: GrowthConnectionStatus[];
};

type LaunchRunResponse = {
  run_id: string;
  mode: 'autopilot' | 'approval-first' | 'draft-only';
  queued_sync_jobs: number;
  blocked_items: string[];
  status: 'started' | 'blocked';
  generated_at: string;
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
  const [growthSummary, setGrowthSummary] = useState<GrowthSummary | null>(null);
  const [growthWizard, setGrowthWizard] = useState<GrowthSetupWizard | null>(null);
  const [launchRun, setLaunchRun] = useState<LaunchRunResponse | null>(null);
  const [failedJobs, setFailedJobs] = useState<SyncJob[]>([]);
  const [loadError, setLoadError] = useState<string | null>(null);
  const [actionMessage, setActionMessage] = useState<string | null>(null);
  const [creatingSyncJob, setCreatingSyncJob] = useState(false);
  const [startingLaunch, setStartingLaunch] = useState(false);
  const [launchMode, setLaunchMode] = useState<'autopilot' | 'approval-first' | 'draft-only'>('approval-first');
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
      const [summaryRes, growthSummaryRes, growthWizardRes, jobsRes] = await Promise.all([
        getFounderIntegrationCommandSummary(),
        getFounderGrowthSummary(),
        getFounderGrowthSetupWizard(),
        getFounderFailedSyncJobs(25),
      ]);
      setSummary(summaryRes as IntegrationSummary);
      setGrowthSummary(growthSummaryRes as GrowthSummary);
      setGrowthWizard(growthWizardRes as GrowthSetupWizard);
      setFailedJobs(Array.isArray(jobsRes) ? (jobsRes as SyncJob[]) : []);
    } catch {
      setSummary(null);
      setGrowthSummary(null);
      setGrowthWizard(null);
      setFailedJobs([]);
      setLoadError('Unable to load integration command center data.');
    }
  }, []);

  useEffect(() => {
    load().catch(() => {
      setLoadError('Unable to load integration command center data.');
    });
  }, [load]);

  useEffect(() => {
    const interval = setInterval(() => {
      load().catch(() => {
        setLoadError('Unable to refresh integration command center data.');
      });
    }, 15000);
    return () => clearInterval(interval);
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

  const handleStartLaunch = async () => {
    setActionMessage(null);
    setLoadError(null);
    setStartingLaunch(true);
    try {
      const response = await startFounderLaunchOrchestrator({
        mode: launchMode,
        auto_queue_sync_jobs: true,
      });
      const run = response as LaunchRunResponse;
      setLaunchRun(run);
      if (run.status === 'blocked') {
        setLoadError(`Launch blocked: ${run.blocked_items.join(' · ') || 'Missing required connected services.'}`);
      } else {
        setActionMessage(`Launch orchestrator started in ${run.mode} mode. Queued ${run.queued_sync_jobs} sync job(s).`);
      }
      await load();
    } catch {
      setLoadError('Failed to start launch orchestrator run.');
    } finally {
      setStartingLaunch(false);
    }
  };

  if (!summary || !growthSummary || !growthWizard) {
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

      <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
        <div className=" border border-white/10 bg-zinc-950/[0.03] p-4">
          <div className="mb-3 text-xs uppercase tracking-wider text-white/50">Growth Engine Runtime</div>
          <div className="grid grid-cols-2 gap-3 md:grid-cols-4">
            <Stat label="Conversions" value={growthSummary.conversion_events_total} />
            <Stat label="Proposals" value={growthSummary.proposals_total} />
            <Stat label="Active Subs" value={growthSummary.active_subscriptions} />
            <Stat label="Pending Pipeline" value={Math.round(growthSummary.pending_pipeline_cents / 100)} />
          </div>
          <div className="mt-3 text-xs text-white/60">
            Proposal→Paid: <span className="font-semibold text-white">{growthSummary.proposal_to_paid_conversion_pct}%</span>
            {' · '}
            Pipeline/MRR: <span className="font-semibold text-white">{growthSummary.pipeline_to_mrr_ratio}</span>
            {' · '}
            Graph Mailbox: <span className={`font-semibold ${growthSummary.graph_mailbox_configured ? 'text-green-300' : 'text-red-300'}`}>{growthSummary.graph_mailbox_configured ? 'configured' : 'missing'}</span>
          </div>
          <div className="mt-3 grid grid-cols-1 gap-2 md:grid-cols-3">
            <div className=" border border-white/10 bg-black/20 p-2">
              <div className="text-[10px] uppercase tracking-wider text-white/50">Funnel Stages</div>
              {growthSummary.funnel_stage_counts.slice(0, 4).map((item) => (
                <div key={item.key} className="mt-1 text-xs text-white/80">{item.key}: {item.value}</div>
              ))}
            </div>
            <div className=" border border-white/10 bg-black/20 p-2">
              <div className="text-[10px] uppercase tracking-wider text-white/50">Lead Tiers</div>
              {growthSummary.lead_tier_distribution.slice(0, 4).map((item) => (
                <div key={item.key} className="mt-1 text-xs text-white/80">{item.key}: {item.value}</div>
              ))}
            </div>
            <div className=" border border-white/10 bg-black/20 p-2">
              <div className="text-[10px] uppercase tracking-wider text-white/50">Score Buckets</div>
              {growthSummary.lead_score_buckets.map((item) => (
                <div key={item.key} className="mt-1 text-xs text-white/80">{item.key}: {item.value}</div>
              ))}
            </div>
          </div>
        </div>

        <div className=" border border-white/10 bg-zinc-950/[0.03] p-4">
          <div className="mb-3 text-xs uppercase tracking-wider text-white/50">Growth Setup Wizard + Launch Orchestrator</div>
          <div className="mb-3 text-sm">
            Autopilot readiness:{' '}
            <span className={`font-semibold ${growthWizard.autopilot_ready ? 'text-green-300' : 'text-red-300'}`}>
              {growthWizard.autopilot_ready ? 'READY' : 'BLOCKED'}
            </span>
          </div>
          {growthWizard.blocked_items.length > 0 && (
            <div className="mb-3 border border-red-500/30 bg-red-500/10 p-2 text-xs text-red-200">
              {growthWizard.blocked_items.map((item) => (
                <div key={item}>• {item}</div>
              ))}
            </div>
          )}
          <div className="grid grid-cols-1 gap-2 md:grid-cols-2">
            {growthWizard.services.map((service) => (
              <div key={service.service_key} className=" border border-white/10 bg-black/20 p-2">
                <div className="flex items-center justify-between">
                  <div className="text-xs font-semibold text-white">{service.label}</div>
                  <div className={`text-[10px] uppercase tracking-wider ${service.connected ? 'text-green-300' : 'text-red-300'}`}>
                    {service.connected ? 'connected' : 'disconnected'}
                  </div>
                </div>
                <div className="mt-1 text-[11px] text-white/60">
                  {service.install_state} · perms {service.permissions_state} · token {service.token_state} · health {service.health_state}
                </div>
                {service.blocking_reason && (
                  <div className="mt-1 text-[11px] text-red-200">{service.blocking_reason}</div>
                )}
              </div>
            ))}
          </div>

          <div className="mt-4 flex flex-col gap-2 md:flex-row md:items-center">
            <select
              value={launchMode}
              onChange={(event) => setLaunchMode(event.target.value as 'autopilot' | 'approval-first' | 'draft-only')}
              className=" border border-white/15 bg-black/30 px-3 py-2 text-sm text-white"
            >
              <option value="autopilot">autopilot</option>
              <option value="approval-first">approval-first</option>
              <option value="draft-only">draft-only</option>
            </select>
            <button
              type="button"
              onClick={handleStartLaunch}
              disabled={startingLaunch}
              className=" border border-orange-400/60 bg-[rgba(255,77,0,0.20)] px-3 py-2 text-sm font-semibold text-[#FF4D00] disabled:opacity-50"
            >
              {startingLaunch ? 'Starting…' : 'Start Launch Orchestrator'}
            </button>
          </div>

          {launchRun && (
            <div className="mt-3 border border-white/10 bg-black/20 p-2 text-xs text-white/80">
              run {launchRun.run_id.slice(0, 8)} · {launchRun.status} · queued sync jobs {launchRun.queued_sync_jobs}
            </div>
          )}
        </div>
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
