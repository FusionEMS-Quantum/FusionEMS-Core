'use client';

import { useEffect, useState } from 'react';
import Link from 'next/link';
import { ArrowLeft, Database, RefreshCw, AlertTriangle, Shield, HardDrive, Clock } from 'lucide-react';
import { getSystemHealthDashboard, getBackupsStatus, getUptimeSLA, getSystemHealthMetricsLatency } from '@/services/api';

interface HealthDash { overall_status?: string; db_status?: string; db_connections?: number; db_size_mb?: number; }
interface BackupInfo { last_backup?: string; status?: string; size_mb?: number; automated?: boolean; retention_days?: number; }
interface SLAReport { uptime_pct?: number; target_pct?: number; downtime_minutes?: number; period?: string; }
interface LatencyPoint { timestamp?: string; value?: number; }

export default function RDSMonitorPage() {
  const [health, setHealth] = useState<HealthDash | null>(null);
  const [backup, setBackup] = useState<BackupInfo | null>(null);
  const [sla, setSLA] = useState<SLAReport | null>(null);
  const [latency, setLatency] = useState<LatencyPoint[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const loadData = async () => {
    setLoading(true);
    setError(null);
    try {
      const [hRes, bRes, sRes, lRes] = await Promise.allSettled([
        getSystemHealthDashboard(), getBackupsStatus(), getUptimeSLA(), getSystemHealthMetricsLatency(),
      ]);
      if (hRes.status === 'fulfilled') setHealth(hRes.value);
      if (bRes.status === 'fulfilled') setBackup(bRes.value);
      if (sRes.status === 'fulfilled') setSLA(sRes.value);
      if (lRes.status === 'fulfilled') {
        const l = lRes.value;
        setLatency(Array.isArray(l?.datapoints) ? l.datapoints : Array.isArray(l) ? l : []);
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load RDS data');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { loadData(); }, []);

  const statusColor = (s: string | undefined) => {
    if (s === 'healthy' || s === 'available') return 'text-[var(--color-status-active)]';
    if (s === 'degraded') return 'text-[var(--q-yellow)]';
    return 'text-[var(--color-brand-red)]';
  };

  if (loading) return <div className="min-h-screen bg-[var(--color-bg-base)] text-white flex items-center justify-center"><RefreshCw className="w-8 h-8 animate-spin text-[var(--color-status-active)]" /></div>;

  return (
    <div className="min-h-screen bg-[var(--color-bg-base)] text-white p-6">
      <div className="max-w-7xl mx-auto space-y-8">
        <div className="flex items-center justify-between">
          <div>
            <Link href="/founder/infra" className="text-[var(--color-text-secondary)] hover:text-[var(--color-text-primary)] flex items-center gap-1 text-sm mb-2"><ArrowLeft className="w-4 h-4" /> Infrastructure Hub</Link>
            <h1 className="text-3xl font-bold flex items-center gap-3"><Database className="w-8 h-8 text-[var(--color-status-info)]" /> RDS Database Monitor</h1>
            <p className="text-[var(--color-text-secondary)] mt-1">PostgreSQL performance, backup status, and replica health</p>
          </div>
          <button onClick={loadData} className="px-4 py-2 bg-[var(--color-bg-raised)] hover:bg-[var(--color-bg-overlay)] chamfer-8 flex items-center gap-2 text-sm"><RefreshCw className="w-4 h-4" /> Refresh</button>
        </div>

        {error && <div className="bg-red-900/30 border border-[var(--color-brand-red)] chamfer-8 p-4 flex items-center gap-3"><AlertTriangle className="w-5 h-5 text-[var(--color-brand-red)]" /><span className="text-[var(--color-brand-red)]">{error}</span></div>}

        <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
          <div className="bg-[var(--color-bg-panel)] border border-[var(--color-border-default)] chamfer-8 p-5">
            <div className="text-[var(--color-text-secondary)] text-sm mb-1 flex items-center gap-1"><Database className="w-4 h-4" /> DB Status</div>
            <div className={`text-2xl font-bold uppercase ${statusColor(health?.db_status ?? health?.overall_status)}`}>{health?.db_status ?? health?.overall_status ?? 'Unknown'}</div>
          </div>
          <div className="bg-[var(--color-bg-panel)] border border-[var(--color-border-default)] chamfer-8 p-5">
            <div className="text-[var(--color-text-secondary)] text-sm mb-1 flex items-center gap-1"><HardDrive className="w-4 h-4" /> DB Size</div>
            <div className="text-2xl font-bold text-[var(--color-status-info)]">{health?.db_size_mb ? `${health.db_size_mb} MB` : '—'}</div>
          </div>
          <div className="bg-[var(--color-bg-panel)] border border-[var(--color-border-default)] chamfer-8 p-5">
            <div className="text-[var(--color-text-secondary)] text-sm mb-1 flex items-center gap-1"><Shield className="w-4 h-4" /> SLA Uptime</div>
            <div className="text-2xl font-bold text-[var(--color-status-active)]">{sla?.uptime_pct != null ? `${sla.uptime_pct}%` : '—'}</div>
          </div>
          <div className="bg-[var(--color-bg-panel)] border border-[var(--color-border-default)] chamfer-8 p-5">
            <div className="text-[var(--color-text-secondary)] text-sm mb-1 flex items-center gap-1"><Clock className="w-4 h-4" /> Avg Latency</div>
            <div className="text-2xl font-bold text-[var(--color-status-info)]">{latency.length > 0 ? `${(latency.reduce((a, l) => a + (l.value ?? 0), 0) / latency.length).toFixed(1)}ms` : '—'}</div>
          </div>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          {/* Backup Status */}
          <div className="bg-[var(--color-bg-panel)] border border-[var(--color-border-default)] chamfer-8 p-6">
            <h2 className="text-lg font-semibold mb-4 flex items-center gap-2"><Shield className="w-5 h-5 text-[var(--color-status-active)]" /> Backup Status</h2>
            <div className="space-y-3 text-sm">
              <div className="flex justify-between"><span className="text-[var(--color-text-secondary)]">Last Backup</span><span className="text-white">{backup?.last_backup ? new Date(backup.last_backup).toLocaleString() : '—'}</span></div>
              <div className="flex justify-between"><span className="text-[var(--color-text-secondary)]">Status</span><span className={statusColor(backup?.status)}>{backup?.status ?? 'unknown'}</span></div>
              <div className="flex justify-between"><span className="text-[var(--color-text-secondary)]">Size</span><span className="text-white">{backup?.size_mb ? `${backup.size_mb} MB` : '—'}</span></div>
              <div className="flex justify-between"><span className="text-[var(--color-text-secondary)]">Automated</span><span className="text-white">{backup?.automated ? 'Yes' : 'No'}</span></div>
              <div className="flex justify-between"><span className="text-[var(--color-text-secondary)]">Retention</span><span className="text-white">{backup?.retention_days ? `${backup.retention_days} days` : '—'}</span></div>
            </div>
          </div>

          {/* SLA Details */}
          <div className="bg-[var(--color-bg-panel)] border border-[var(--color-border-default)] chamfer-8 p-6">
            <h2 className="text-lg font-semibold mb-4 flex items-center gap-2"><Clock className="w-5 h-5 text-[var(--color-status-info)]" /> SLA Report</h2>
            <div className="space-y-3 text-sm">
              <div className="flex justify-between"><span className="text-[var(--color-text-secondary)]">Current Uptime</span><span className="text-[var(--color-status-active)] font-bold">{sla?.uptime_pct ?? '—'}%</span></div>
              <div className="flex justify-between"><span className="text-[var(--color-text-secondary)]">Target</span><span className="text-white">{sla?.target_pct ?? 99.99}%</span></div>
              <div className="flex justify-between"><span className="text-[var(--color-text-secondary)]">Downtime</span><span className="text-[var(--q-yellow)]">{sla?.downtime_minutes ?? 0} min</span></div>
              <div className="flex justify-between"><span className="text-[var(--color-text-secondary)]">Period</span><span className="text-white">{sla?.period ?? 'Current Month'}</span></div>
              <div className="flex justify-between"><span className="text-[var(--color-text-secondary)]">Connections</span><span className="text-white">{health?.db_connections ?? '—'}</span></div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
