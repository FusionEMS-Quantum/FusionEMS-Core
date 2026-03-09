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
    if (s === 'healthy' || s === 'available') return 'text-emerald-400';
    if (s === 'degraded') return 'text-amber-400';
    return 'text-red-400';
  };

  if (loading) return <div className="min-h-screen bg-gray-950 text-white flex items-center justify-center"><RefreshCw className="w-8 h-8 animate-spin text-emerald-400" /></div>;

  return (
    <div className="min-h-screen bg-gray-950 text-white p-6">
      <div className="max-w-7xl mx-auto space-y-8">
        <div className="flex items-center justify-between">
          <div>
            <Link href="/founder/infra" className="text-gray-400 hover:text-white flex items-center gap-1 text-sm mb-2"><ArrowLeft className="w-4 h-4" /> Infrastructure Hub</Link>
            <h1 className="text-3xl font-bold flex items-center gap-3"><Database className="w-8 h-8 text-blue-400" /> RDS Database Monitor</h1>
            <p className="text-gray-400 mt-1">PostgreSQL performance, backup status, and replica health</p>
          </div>
          <button onClick={loadData} className="px-4 py-2 bg-gray-800 hover:bg-gray-700 rounded-lg flex items-center gap-2 text-sm"><RefreshCw className="w-4 h-4" /> Refresh</button>
        </div>

        {error && <div className="bg-red-900/30 border border-red-700 rounded-lg p-4 flex items-center gap-3"><AlertTriangle className="w-5 h-5 text-red-400" /><span className="text-red-300">{error}</span></div>}

        <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
          <div className="bg-gray-900 border border-gray-800 rounded-lg p-5">
            <div className="text-gray-400 text-sm mb-1 flex items-center gap-1"><Database className="w-4 h-4" /> DB Status</div>
            <div className={`text-2xl font-bold uppercase ${statusColor(health?.db_status ?? health?.overall_status)}`}>{health?.db_status ?? health?.overall_status ?? 'Unknown'}</div>
          </div>
          <div className="bg-gray-900 border border-gray-800 rounded-lg p-5">
            <div className="text-gray-400 text-sm mb-1 flex items-center gap-1"><HardDrive className="w-4 h-4" /> DB Size</div>
            <div className="text-2xl font-bold text-blue-400">{health?.db_size_mb ? `${health.db_size_mb} MB` : '—'}</div>
          </div>
          <div className="bg-gray-900 border border-gray-800 rounded-lg p-5">
            <div className="text-gray-400 text-sm mb-1 flex items-center gap-1"><Shield className="w-4 h-4" /> SLA Uptime</div>
            <div className="text-2xl font-bold text-emerald-400">{sla?.uptime_pct != null ? `${sla.uptime_pct}%` : '—'}</div>
          </div>
          <div className="bg-gray-900 border border-gray-800 rounded-lg p-5">
            <div className="text-gray-400 text-sm mb-1 flex items-center gap-1"><Clock className="w-4 h-4" /> Avg Latency</div>
            <div className="text-2xl font-bold text-cyan-400">{latency.length > 0 ? `${(latency.reduce((a, l) => a + (l.value ?? 0), 0) / latency.length).toFixed(1)}ms` : '—'}</div>
          </div>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          {/* Backup Status */}
          <div className="bg-gray-900 border border-gray-800 rounded-lg p-6">
            <h2 className="text-lg font-semibold mb-4 flex items-center gap-2"><Shield className="w-5 h-5 text-emerald-400" /> Backup Status</h2>
            <div className="space-y-3 text-sm">
              <div className="flex justify-between"><span className="text-gray-400">Last Backup</span><span className="text-white">{backup?.last_backup ? new Date(backup.last_backup).toLocaleString() : '—'}</span></div>
              <div className="flex justify-between"><span className="text-gray-400">Status</span><span className={statusColor(backup?.status)}>{backup?.status ?? 'unknown'}</span></div>
              <div className="flex justify-between"><span className="text-gray-400">Size</span><span className="text-white">{backup?.size_mb ? `${backup.size_mb} MB` : '—'}</span></div>
              <div className="flex justify-between"><span className="text-gray-400">Automated</span><span className="text-white">{backup?.automated ? 'Yes' : 'No'}</span></div>
              <div className="flex justify-between"><span className="text-gray-400">Retention</span><span className="text-white">{backup?.retention_days ? `${backup.retention_days} days` : '—'}</span></div>
            </div>
          </div>

          {/* SLA Details */}
          <div className="bg-gray-900 border border-gray-800 rounded-lg p-6">
            <h2 className="text-lg font-semibold mb-4 flex items-center gap-2"><Clock className="w-5 h-5 text-blue-400" /> SLA Report</h2>
            <div className="space-y-3 text-sm">
              <div className="flex justify-between"><span className="text-gray-400">Current Uptime</span><span className="text-emerald-400 font-bold">{sla?.uptime_pct ?? '—'}%</span></div>
              <div className="flex justify-between"><span className="text-gray-400">Target</span><span className="text-white">{sla?.target_pct ?? 99.99}%</span></div>
              <div className="flex justify-between"><span className="text-gray-400">Downtime</span><span className="text-amber-400">{sla?.downtime_minutes ?? 0} min</span></div>
              <div className="flex justify-between"><span className="text-gray-400">Period</span><span className="text-white">{sla?.period ?? 'Current Month'}</span></div>
              <div className="flex justify-between"><span className="text-gray-400">Connections</span><span className="text-white">{health?.db_connections ?? '—'}</span></div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
