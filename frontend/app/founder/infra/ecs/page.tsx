'use client';

import { useEffect, useState } from 'react';
import Link from 'next/link';
import { ArrowLeft, Box, RefreshCw, AlertTriangle, Activity, Server, Layers } from 'lucide-react';
import { getSystemHealthDashboard, getSystemHealthServices, getSystemHealthAlerts } from '@/services/api';

interface ServiceStatus { name: string; status: string; running_count?: number; desired_count?: number; cpu_pct?: number; memory_pct?: number; }
interface AlertItem { id: string; severity: string; message: string; created_at?: string; resolved?: boolean; }
interface HealthDash { overall_status?: string; service_count?: number; healthy_count?: number; }

export default function ECSServicesPage() {
  const [health, setHealth] = useState<HealthDash | null>(null);
  const [services, setServices] = useState<ServiceStatus[]>([]);
  const [alerts, setAlerts] = useState<AlertItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const loadData = async () => {
    setLoading(true);
    setError(null);
    try {
      const [hRes, sRes, aRes] = await Promise.allSettled([
        getSystemHealthDashboard(), getSystemHealthServices(), getSystemHealthAlerts(),
      ]);
      if (hRes.status === 'fulfilled') setHealth(hRes.value);
      if (sRes.status === 'fulfilled') {
        const s = sRes.value;
        setServices(Array.isArray(s?.services) ? s.services : Array.isArray(s) ? s : []);
      }
      if (aRes.status === 'fulfilled') {
        const a = aRes.value;
        setAlerts(Array.isArray(a?.alerts) ? a.alerts : Array.isArray(a) ? a : []);
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load ECS data');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { loadData(); }, []);

  const statusColor = (s: string) => {
    if (s === 'healthy' || s === 'running' || s === 'ACTIVE') return 'text-[var(--color-status-active)]';
    if (s === 'degraded' || s === 'warning') return 'text-[var(--q-yellow)]';
    return 'text-[var(--color-brand-red)]';
  };

  if (loading) return <div className="min-h-screen bg-[var(--color-bg-base)] text-white flex items-center justify-center"><RefreshCw className="w-8 h-8 animate-spin text-[var(--color-status-active)]" /></div>;

  return (
    <div className="min-h-screen bg-[var(--color-bg-base)] text-white p-6">
      <div className="max-w-7xl mx-auto space-y-8">
        <div className="flex items-center justify-between">
          <div>
            <Link href="/founder/infra" className="text-[var(--color-text-secondary)] hover:text-[var(--color-text-primary)] flex items-center gap-1 text-sm mb-2"><ArrowLeft className="w-4 h-4" /> Infrastructure Hub</Link>
            <h1 className="text-3xl font-bold flex items-center gap-3"><Box className="w-8 h-8 text-[var(--q-orange)]" /> ECS Service Management</h1>
            <p className="text-[var(--color-text-secondary)] mt-1">Container services, auto-scaling, and deployment pipeline monitoring</p>
          </div>
          <button onClick={loadData} className="px-4 py-2 bg-[var(--color-bg-raised)] hover:bg-[var(--color-bg-overlay)] chamfer-8 flex items-center gap-2 text-sm"><RefreshCw className="w-4 h-4" /> Refresh</button>
        </div>

        {error && <div className="bg-red-900/30 border border-[var(--color-brand-red)] chamfer-8 p-4 flex items-center gap-3"><AlertTriangle className="w-5 h-5 text-[var(--color-brand-red)]" /><span className="text-[var(--color-brand-red)]">{error}</span></div>}

        <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
          <div className="bg-[var(--color-bg-panel)] border border-[var(--color-border-default)] chamfer-8 p-5">
            <div className="text-[var(--color-text-secondary)] text-sm mb-1 flex items-center gap-1"><Activity className="w-4 h-4" /> Cluster Status</div>
            <div className={`text-2xl font-bold uppercase ${statusColor(health?.overall_status ?? 'unknown')}`}>{health?.overall_status ?? 'Unknown'}</div>
          </div>
          <div className="bg-[var(--color-bg-panel)] border border-[var(--color-border-default)] chamfer-8 p-5">
            <div className="text-[var(--color-text-secondary)] text-sm mb-1 flex items-center gap-1"><Server className="w-4 h-4" /> Total Services</div>
            <div className="text-2xl font-bold text-[var(--color-status-info)]">{health?.service_count ?? services.length}</div>
          </div>
          <div className="bg-[var(--color-bg-panel)] border border-[var(--color-border-default)] chamfer-8 p-5">
            <div className="text-[var(--color-text-secondary)] text-sm mb-1 flex items-center gap-1"><Layers className="w-4 h-4" /> Healthy</div>
            <div className="text-2xl font-bold text-[var(--color-status-active)]">{health?.healthy_count ?? services.filter(s => s.status === 'running' || s.status === 'healthy').length}</div>
          </div>
          <div className="bg-[var(--color-bg-panel)] border border-[var(--color-border-default)] chamfer-8 p-5">
            <div className="text-[var(--color-text-secondary)] text-sm mb-1 flex items-center gap-1"><AlertTriangle className="w-4 h-4" /> Active Alerts</div>
            <div className="text-2xl font-bold text-[var(--q-yellow)]">{alerts.filter(a => !a.resolved).length}</div>
          </div>
        </div>

        {/* Services Table */}
        <div className="bg-[var(--color-bg-panel)] border border-[var(--color-border-default)] chamfer-8 overflow-hidden">
          <div className="px-6 py-4 border-b border-[var(--color-border-default)]"><h2 className="text-lg font-semibold flex items-center gap-2"><Box className="w-5 h-5 text-[var(--q-orange)]" /> ECS Services</h2></div>
          {services.length === 0 ? (
            <div className="p-12 text-center text-[var(--color-text-muted)]">No ECS services detected. Data will populate when cluster telemetry connects.</div>
          ) : (
            <table className="w-full text-sm">
              <thead className="bg-[var(--color-bg-raised)]/50">
                <tr>
                  <th className="text-left px-6 py-3 text-[var(--color-text-secondary)] font-medium">Service</th>
                  <th className="text-left px-6 py-3 text-[var(--color-text-secondary)] font-medium">Status</th>
                  <th className="text-left px-6 py-3 text-[var(--color-text-secondary)] font-medium">Running</th>
                  <th className="text-left px-6 py-3 text-[var(--color-text-secondary)] font-medium">Desired</th>
                  <th className="text-left px-6 py-3 text-[var(--color-text-secondary)] font-medium">CPU</th>
                  <th className="text-left px-6 py-3 text-[var(--color-text-secondary)] font-medium">Memory</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-800">
                {services.map((s, i) => (
                  <tr key={i} className="hover:bg-[var(--color-bg-raised)]/30">
                    <td className="px-6 py-3 text-white font-medium">{s.name}</td>
                    <td className={`px-6 py-3 font-bold uppercase ${statusColor(s.status)}`}>{s.status}</td>
                    <td className="px-6 py-3 text-[var(--color-status-info)]">{s.running_count ?? '—'}</td>
                    <td className="px-6 py-3 text-[var(--color-text-secondary)]">{s.desired_count ?? '—'}</td>
                    <td className="px-6 py-3 text-[var(--color-status-info)]">{s.cpu_pct != null ? `${s.cpu_pct}%` : '—'}</td>
                    <td className="px-6 py-3 text-[var(--color-system-compliance)]">{s.memory_pct != null ? `${s.memory_pct}%` : '—'}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </div>

        {/* Alerts */}
        {alerts.length > 0 && (
          <div className="bg-[var(--color-bg-panel)] border border-[var(--color-border-default)] chamfer-8 overflow-hidden">
            <div className="px-6 py-4 border-b border-[var(--color-border-default)]"><h2 className="text-lg font-semibold flex items-center gap-2"><AlertTriangle className="w-5 h-5 text-[var(--q-yellow)]" /> Infrastructure Alerts</h2></div>
            <div className="divide-y divide-gray-800">
              {alerts.slice(0, 10).map((a) => (
                <div key={a.id} className="px-6 py-3 flex items-center justify-between">
                  <div>
                    <span className={`text-xs font-bold uppercase mr-2 ${a.severity === 'critical' ? 'text-[var(--color-brand-red)]' : a.severity === 'warning' ? 'text-[var(--q-yellow)]' : 'text-[var(--color-status-info)]'}`}>{a.severity}</span>
                    <span className="text-white text-sm">{a.message}</span>
                  </div>
                  <span className="text-[var(--color-text-muted)] text-xs">{a.created_at ? new Date(a.created_at).toLocaleString() : ''}</span>
                </div>
              ))}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
