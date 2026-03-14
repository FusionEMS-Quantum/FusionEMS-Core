'use client';

import { useEffect, useState } from 'react';
import { AlertTriangle, ArrowLeft, CheckCircle, Clock, FileOutput, RefreshCw, RotateCcw, XCircle } from 'lucide-react';
import Link from 'next/link';
import {
  getExportQueue,
  getExportRejectionAlerts,
  getExportPerformanceScore,
  getExportLatency,
  getExportPendingApproval,
  retryExportJob,
} from '@/services/api';

interface ExportJob {
  id?: string;
  status?: string;
  file_type?: string;
  tenant_id?: string;
  created_at?: string;
  error?: string;
}

interface RejectionAlert {
  job_id?: string;
  reason?: string;
  severity?: string;
  filed_at?: string;
}

interface PerfScore {
  score?: number;
  grade?: string;
  factors?: { name: string; value: number }[];
}

export default function ExportStatusPage() {
  const [queue, setQueue] = useState<ExportJob[]>([]);
  const [rejections, setRejections] = useState<RejectionAlert[]>([]);
  const [perf, setPerf] = useState<PerfScore | null>(null);
  const [latency, setLatency] = useState<Record<string, unknown> | null>(null);
  const [pending, setPending] = useState<ExportJob[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [retrying, setRetrying] = useState<string | null>(null);

  const loadData = async () => {
    setLoading(true);
    setError(null);
    try {
      const [qRes, rRes, pRes, lRes, paRes] = await Promise.allSettled([
        getExportQueue(),
        getExportRejectionAlerts(),
        getExportPerformanceScore(),
        getExportLatency(),
        getExportPendingApproval(),
      ]);
      if (qRes.status === 'fulfilled') {
        const qd = qRes.value;
        setQueue(Array.isArray(qd?.jobs) ? qd.jobs : Array.isArray(qd) ? qd : []);
      }
      if (rRes.status === 'fulfilled') {
        const rd = rRes.value;
        setRejections(Array.isArray(rd?.alerts) ? rd.alerts : Array.isArray(rd) ? rd : []);
      }
      if (pRes.status === 'fulfilled') setPerf(pRes.value);
      if (lRes.status === 'fulfilled') setLatency(lRes.value);
      if (paRes.status === 'fulfilled') {
        const pd = paRes.value;
        setPending(Array.isArray(pd?.jobs) ? pd.jobs : Array.isArray(pd) ? pd : []);
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load export status');
    } finally {
      setLoading(false);
    }
  };

  const handleRetry = async (jobId: string) => {
    setRetrying(jobId);
    try {
      await retryExportJob(jobId);
      await loadData();
    } catch {
      setError(`Failed to retry job ${jobId}`);
    } finally {
      setRetrying(null);
    }
  };

  useEffect(() => { loadData(); }, []);

  const statusIcon = (s?: string) => {
    if (s === 'completed' || s === 'success') return <CheckCircle className="w-4 h-4 text-[var(--color-status-active)]" />;
    if (s === 'failed' || s === 'rejected') return <XCircle className="w-4 h-4 text-[var(--color-brand-red)]" />;
    if (s === 'pending' || s === 'queued') return <Clock className="w-4 h-4 text-[var(--q-yellow)]" />;
    return <Clock className="w-4 h-4 text-[var(--color-text-secondary)]" />;
  };

  if (loading) {
    return (
      <div className="min-h-screen bg-[var(--color-bg-base)] text-white flex items-center justify-center">
        <RefreshCw className="w-8 h-8 animate-spin text-[var(--color-status-active)]" />
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-[var(--color-bg-base)] text-white p-6">
      <div className="max-w-7xl mx-auto space-y-8">
        <div className="flex items-center justify-between">
          <div>
            <Link href="/founder/compliance" className="text-[var(--color-text-secondary)] hover:text-[var(--color-text-primary)] flex items-center gap-1 text-sm mb-2">
              <ArrowLeft className="w-4 h-4" /> Back to Compliance
            </Link>
            <h1 className="text-3xl font-bold flex items-center gap-3">
              <FileOutput className="w-8 h-8 text-[var(--color-status-info)]" />
              Export Status
            </h1>
          </div>
          <button onClick={loadData} className="px-4 py-2 bg-[var(--color-bg-raised)] hover:bg-[var(--color-bg-overlay)] chamfer-8 flex items-center gap-2 text-sm">
            <RefreshCw className="w-4 h-4" /> Refresh
          </button>
        </div>

        {error && (
          <div className="bg-red-900/30 border border-[var(--color-brand-red)] chamfer-8 p-4 flex items-center gap-3">
            <AlertTriangle className="w-5 h-5 text-[var(--color-brand-red)]" />
            <span className="text-[var(--color-brand-red)]">{error}</span>
          </div>
        )}

        {/* Performance Score + Latency */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          <div className="bg-[var(--color-bg-panel)] border border-[var(--color-border-default)] chamfer-8 p-5 text-center">
            <div className="text-[var(--color-text-secondary)] text-sm mb-1">Performance Score</div>
            <div className={`text-4xl font-bold ${(perf?.score ?? 0) >= 80 ? 'text-[var(--color-status-active)]' : (perf?.score ?? 0) >= 60 ? 'text-[var(--q-yellow)]' : 'text-[var(--color-brand-red)]'}`}>
              {perf?.score ?? '—'}
            </div>
            <div className="text-[var(--color-text-secondary)] text-sm">{perf?.grade ?? ''}</div>
          </div>
          <div className="bg-[var(--color-bg-panel)] border border-[var(--color-border-default)] chamfer-8 p-5 text-center">
            <div className="text-[var(--color-text-secondary)] text-sm mb-1">Queue Size</div>
            <div className="text-4xl font-bold text-[var(--color-status-info)]">{queue.length}</div>
          </div>
          <div className="bg-[var(--color-bg-panel)] border border-[var(--color-border-default)] chamfer-8 p-5 text-center">
            <div className="text-[var(--color-text-secondary)] text-sm mb-1">Avg Latency</div>
            <div className="text-4xl font-bold text-[var(--color-system-compliance)]">
              {latency?.avg_latency_ms != null ? `${latency.avg_latency_ms}ms` : '—'}
            </div>
          </div>
        </div>

        {/* Rejection Alerts */}
        {rejections.length > 0 && (
          <div className="bg-[var(--color-bg-panel)] border border-red-800 chamfer-8 p-6">
            <h2 className="text-lg font-semibold mb-4 flex items-center gap-2 text-[var(--color-brand-red)]">
              <AlertTriangle className="w-5 h-5" /> Rejection Alerts ({rejections.length})
            </h2>
            <div className="space-y-2">
              {rejections.map((r, i) => (
                <div key={i} className="bg-red-900/20 chamfer-4 px-4 py-3 flex items-center justify-between">
                  <div>
                    <span className="font-mono text-sm text-[var(--color-text-secondary)]">{r.job_id ?? '—'}</span>
                    <span className="ml-3 text-sm text-[var(--color-brand-red)]">{r.reason ?? 'Unknown rejection'}</span>
                  </div>
                  <span className="text-xs text-[var(--color-text-muted)]">{r.filed_at ?? ''}</span>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Export Queue */}
        <div className="bg-[var(--color-bg-panel)] border border-[var(--color-border-default)] chamfer-8 p-6">
          <h2 className="text-lg font-semibold mb-4 flex items-center gap-2">
            <FileOutput className="w-5 h-5 text-[var(--color-status-info)]" /> Export Queue
          </h2>
          {queue.length > 0 ? (
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead><tr className="text-[var(--color-text-secondary)] border-b border-[var(--color-border-default)]">
                  <th className="text-left py-2">Job ID</th>
                  <th className="text-left py-2">Type</th>
                  <th className="text-left py-2">Status</th>
                  <th className="text-left py-2">Created</th>
                  <th className="text-right py-2">Actions</th>
                </tr></thead>
                <tbody>
                  {queue.map((j, i) => (
                    <tr key={i} className="border-b border-[var(--color-border-subtle)]">
                      <td className="py-2 font-mono text-xs">{j.id ? j.id.slice(0, 8) + '...' : '—'}</td>
                      <td className="py-2">{j.file_type ?? '—'}</td>
                      <td className="py-2 flex items-center gap-1">{statusIcon(j.status)}{j.status ?? '—'}</td>
                      <td className="py-2 text-[var(--color-text-secondary)]">{j.created_at ?? '—'}</td>
                      <td className="py-2 text-right">
                        {(j.status === 'failed' || j.status === 'rejected') && j.id && (
                          <button
                            onClick={() => handleRetry(j.id!)}
                            disabled={retrying === j.id}
                            className="text-xs px-2 py-1 bg-[var(--color-bg-overlay)] hover:bg-[var(--color-bg-overlay)] chamfer-4 flex items-center gap-1 ml-auto"
                          >
                            <RotateCcw className={`w-3 h-3 ${retrying === j.id ? 'animate-spin' : ''}`} /> Retry
                          </button>
                        )}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          ) : (
            <div className="text-[var(--color-text-muted)]">No export jobs in queue</div>
          )}
        </div>

        {/* Pending Approval */}
        {pending.length > 0 && (
          <div className="bg-[var(--color-bg-panel)] border border-amber-800 chamfer-8 p-6">
            <h2 className="text-lg font-semibold mb-4 text-[var(--q-yellow)]">Pending Approval ({pending.length})</h2>
            <div className="space-y-2">
              {pending.map((p, i) => (
                <div key={i} className="bg-amber-900/20 chamfer-4 px-4 py-3 flex items-center justify-between">
                  <span className="font-mono text-sm">{p.id ? p.id.slice(0, 8) + '...' : '—'}</span>
                  <span className="text-sm text-[var(--color-text-secondary)]">{p.file_type ?? 'NEMSIS'}</span>
                </div>
              ))}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
