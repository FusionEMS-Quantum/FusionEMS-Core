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
    if (s === 'healthy' || s === 'running' || s === 'ACTIVE') return 'text-emerald-400';
    if (s === 'degraded' || s === 'warning') return 'text-amber-400';
    return 'text-red-400';
  };

  if (loading) return <div className="min-h-screen bg-gray-950 text-white flex items-center justify-center"><RefreshCw className="w-8 h-8 animate-spin text-emerald-400" /></div>;

  return (
    <div className="min-h-screen bg-gray-950 text-white p-6">
      <div className="max-w-7xl mx-auto space-y-8">
        <div className="flex items-center justify-between">
          <div>
            <Link href="/founder/infra" className="text-gray-400 hover:text-white flex items-center gap-1 text-sm mb-2"><ArrowLeft className="w-4 h-4" /> Infrastructure Hub</Link>
            <h1 className="text-3xl font-bold flex items-center gap-3"><Box className="w-8 h-8 text-orange-400" /> ECS Service Management</h1>
            <p className="text-gray-400 mt-1">Container services, auto-scaling, and deployment pipeline monitoring</p>
          </div>
          <button onClick={loadData} className="px-4 py-2 bg-gray-800 hover:bg-gray-700 rounded-lg flex items-center gap-2 text-sm"><RefreshCw className="w-4 h-4" /> Refresh</button>
        </div>

        {error && <div className="bg-red-900/30 border border-red-700 rounded-lg p-4 flex items-center gap-3"><AlertTriangle className="w-5 h-5 text-red-400" /><span className="text-red-300">{error}</span></div>}

        <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
          <div className="bg-gray-900 border border-gray-800 rounded-lg p-5">
            <div className="text-gray-400 text-sm mb-1 flex items-center gap-1"><Activity className="w-4 h-4" /> Cluster Status</div>
            <div className={`text-2xl font-bold uppercase ${statusColor(health?.overall_status ?? 'unknown')}`}>{health?.overall_status ?? 'Unknown'}</div>
          </div>
          <div className="bg-gray-900 border border-gray-800 rounded-lg p-5">
            <div className="text-gray-400 text-sm mb-1 flex items-center gap-1"><Server className="w-4 h-4" /> Total Services</div>
            <div className="text-2xl font-bold text-blue-400">{health?.service_count ?? services.length}</div>
          </div>
          <div className="bg-gray-900 border border-gray-800 rounded-lg p-5">
            <div className="text-gray-400 text-sm mb-1 flex items-center gap-1"><Layers className="w-4 h-4" /> Healthy</div>
            <div className="text-2xl font-bold text-emerald-400">{health?.healthy_count ?? services.filter(s => s.status === 'running' || s.status === 'healthy').length}</div>
          </div>
          <div className="bg-gray-900 border border-gray-800 rounded-lg p-5">
            <div className="text-gray-400 text-sm mb-1 flex items-center gap-1"><AlertTriangle className="w-4 h-4" /> Active Alerts</div>
            <div className="text-2xl font-bold text-amber-400">{alerts.filter(a => !a.resolved).length}</div>
          </div>
        </div>

        {/* Services Table */}
        <div className="bg-gray-900 border border-gray-800 rounded-lg overflow-hidden">
          <div className="px-6 py-4 border-b border-gray-800"><h2 className="text-lg font-semibold flex items-center gap-2"><Box className="w-5 h-5 text-orange-400" /> ECS Services</h2></div>
          {services.length === 0 ? (
            <div className="p-12 text-center text-gray-500">No ECS services detected. Data will populate when cluster telemetry connects.</div>
          ) : (
            <table className="w-full text-sm">
              <thead className="bg-gray-800/50">
                <tr>
                  <th className="text-left px-6 py-3 text-gray-400 font-medium">Service</th>
                  <th className="text-left px-6 py-3 text-gray-400 font-medium">Status</th>
                  <th className="text-left px-6 py-3 text-gray-400 font-medium">Running</th>
                  <th className="text-left px-6 py-3 text-gray-400 font-medium">Desired</th>
                  <th className="text-left px-6 py-3 text-gray-400 font-medium">CPU</th>
                  <th className="text-left px-6 py-3 text-gray-400 font-medium">Memory</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-800">
                {services.map((s, i) => (
                  <tr key={i} className="hover:bg-gray-800/30">
                    <td className="px-6 py-3 text-white font-medium">{s.name}</td>
                    <td className={`px-6 py-3 font-bold uppercase ${statusColor(s.status)}`}>{s.status}</td>
                    <td className="px-6 py-3 text-blue-400">{s.running_count ?? '—'}</td>
                    <td className="px-6 py-3 text-gray-400">{s.desired_count ?? '—'}</td>
                    <td className="px-6 py-3 text-cyan-400">{s.cpu_pct != null ? `${s.cpu_pct}%` : '—'}</td>
                    <td className="px-6 py-3 text-violet-400">{s.memory_pct != null ? `${s.memory_pct}%` : '—'}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </div>

        {/* Alerts */}
        {alerts.length > 0 && (
          <div className="bg-gray-900 border border-gray-800 rounded-lg overflow-hidden">
            <div className="px-6 py-4 border-b border-gray-800"><h2 className="text-lg font-semibold flex items-center gap-2"><AlertTriangle className="w-5 h-5 text-amber-400" /> Infrastructure Alerts</h2></div>
            <div className="divide-y divide-gray-800">
              {alerts.slice(0, 10).map((a) => (
                <div key={a.id} className="px-6 py-3 flex items-center justify-between">
                  <div>
                    <span className={`text-xs font-bold uppercase mr-2 ${a.severity === 'critical' ? 'text-red-400' : a.severity === 'warning' ? 'text-amber-400' : 'text-blue-400'}`}>{a.severity}</span>
                    <span className="text-white text-sm">{a.message}</span>
                  </div>
                  <span className="text-gray-500 text-xs">{a.created_at ? new Date(a.created_at).toLocaleString() : ''}</span>
                </div>
              ))}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
