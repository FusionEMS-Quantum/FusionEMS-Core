'use client';

import { useEffect, useState } from 'react';
import { motion } from 'framer-motion';
import { Rocket, Server, ShieldCheck, AlertCircle, ArrowLeft } from 'lucide-react';
import Link from 'next/link';
import {
  getSystemHealthDashboard,
  getSystemHealthServices,
  getSSLExpiration,
  getBackupsStatus,
} from '@/services/api';

interface ServiceRecord {
  name: string;
  status: string;
  version?: string;
  desired_count?: number;
  running_count?: number;
  last_deployed?: string;
}

interface DashboardData {
  total_services?: number;
  healthy?: number;
  degraded?: number;
  down?: number;
}

export default function PWADeploymentPage() {
  const [dashboard, setDashboard] = useState<DashboardData | null>(null);
  const [services, setServices] = useState<ServiceRecord[]>([]);
  const [ssl, setSsl] = useState<Record<string, unknown> | null>(null);
  const [backups, setBackups] = useState<Record<string, unknown> | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    async function loadData() {
      try {
        setLoading(true);
        const results = await Promise.allSettled([
          getSystemHealthDashboard(),
          getSystemHealthServices(),
          getSSLExpiration(),
          getBackupsStatus(),
        ]);
        if (results[0].status === 'fulfilled') {
          const d = results[0].value;
          setDashboard(d?.data ?? d);
        }
        if (results[1].status === 'fulfilled') {
          const s = results[1].value;
          setServices(Array.isArray(s?.data) ? s.data : Array.isArray(s) ? s : []);
        }
        if (results[2].status === 'fulfilled') {
          const s = results[2].value;
          setSsl(s?.data ?? s);
        }
        if (results[3].status === 'fulfilled') {
          const b = results[3].value;
          setBackups(b?.data ?? b);
        }
      } catch (err: unknown) {
        setError(err instanceof Error ? err.message : 'Failed to load deployment data');
      } finally {
        setLoading(false);
      }
    }
    loadData();
  }, []);

  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-[60vh]">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-cyan-500" />
      </div>
    );
  }

  if (error) {
    return (
      <div className="p-6 max-w-7xl mx-auto">
        <div className="bg-red-900/30 border border-[var(--color-brand-red)] chamfer-8 p-4 text-[var(--color-brand-red)]">{error}</div>
      </div>
    );
  }

  const totalSvc = dashboard?.total_services ?? services.length;
  const healthy = dashboard?.healthy ?? 0;
  const sslExpiry = ssl && typeof ssl === 'object' ? (ssl as Record<string, string>).expires_at ?? '—' : '—';
  const lastBackup = backups && typeof backups === 'object' ? (backups as Record<string, string>).last_backup_at ?? '—' : '—';

  return (
    <div className="p-6 max-w-7xl mx-auto space-y-6">
      <div className="flex items-center gap-3">
        <Link href="/founder/pwa" className="text-[var(--color-text-secondary)] hover:text-[var(--color-text-primary)]"><ArrowLeft className="h-5 w-5" /></Link>
        <Rocket className="h-6 w-6 text-[var(--color-status-info)]" />
        <h1 className="text-2xl font-bold text-white">PWA Deployment Manager</h1>
      </div>

      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        {[
          { label: 'Total Services', value: totalSvc, icon: Server, color: 'cyan' },
          { label: 'Healthy', value: healthy, icon: ShieldCheck, color: 'green' },
          { label: 'SSL Expiry', value: sslExpiry !== '—' ? new Date(sslExpiry).toLocaleDateString() : '—', icon: ShieldCheck, color: 'blue' },
          { label: 'Last Backup', value: lastBackup !== '—' ? new Date(lastBackup).toLocaleDateString() : '—', icon: AlertCircle, color: 'purple' },
        ].map((kpi) => (
          <motion.div key={kpi.label} initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} className={`bg-[var(--color-bg-raised)] border border-${kpi.color}-500/30 chamfer-8 p-4`}>
            <div className="flex items-center gap-2 text-[var(--color-text-secondary)] text-xs mb-1"><kpi.icon className="h-4 w-4" />{kpi.label}</div>
            <div className="text-2xl font-bold text-white">{kpi.value}</div>
          </motion.div>
        ))}
      </div>

      <div className="bg-[var(--color-bg-raised)] border border-[var(--color-border-strong)] chamfer-8 overflow-hidden">
        <div className="p-4 border-b border-[var(--color-border-strong)]">
          <h2 className="text-sm font-semibold text-white">Deployed Services</h2>
        </div>
        <table className="w-full text-sm">
          <thead className="bg-[var(--color-bg-panel)] text-[var(--color-text-secondary)] text-xs uppercase">
            <tr>
              <th className="px-4 py-3 text-left">Service</th>
              <th className="px-4 py-3 text-left">Status</th>
              <th className="px-4 py-3 text-left">Version</th>
              <th className="px-4 py-3 text-left">Running / Desired</th>
              <th className="px-4 py-3 text-left">Last Deployed</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-700">
            {services.length === 0 ? (
              <tr><td colSpan={5} className="px-4 py-8 text-center text-[var(--color-text-muted)]">No deployment data available.</td></tr>
            ) : services.map((s, i) => (
              <tr key={i} className="hover:bg-[var(--color-bg-overlay)]/50">
                <td className="px-4 py-3 text-white font-medium">{s.name}</td>
                <td className="px-4 py-3">
                  <span className={`px-2 py-0.5 rounded text-xs font-medium ${s.status === 'healthy' ? 'bg-green-900/50 text-[var(--color-status-active)]' : s.status === 'degraded' ? 'bg-yellow-900/50 text-yellow-300' : 'bg-red-900/50 text-[var(--color-brand-red)]'}`}>{s.status}</span>
                </td>
                <td className="px-4 py-3 text-[var(--color-text-secondary)]">{s.version ?? '—'}</td>
                <td className="px-4 py-3 text-[var(--color-text-secondary)]">{s.running_count ?? '—'} / {s.desired_count ?? '—'}</td>
                <td className="px-4 py-3 text-[var(--color-text-secondary)]">{s.last_deployed ? new Date(s.last_deployed).toLocaleString() : '—'}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
