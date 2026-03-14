'use client';

import { useEffect, useState } from 'react';
import Link from 'next/link';
import { ArrowLeft, Cpu, RefreshCw, AlertTriangle, Activity, Zap, Server } from 'lucide-react';
import { getSystemHealthDashboard, getSystemHealthServices, getSystemHealthMetricsCPU, getSystemHealthMetricsMemory } from '@/services/api';

interface ServiceStatus { name: string; status: string; latency_ms?: number; region?: string; }
interface MetricPoint { timestamp?: string; value?: number; unit?: string; }
interface HealthDash { overall_status?: string; service_count?: number; healthy_count?: number; degraded_count?: number; }

export default function AIGPUMonitorPage() {
  const [health, setHealth] = useState<HealthDash | null>(null);
  const [services, setServices] = useState<ServiceStatus[]>([]);
  const [cpu, setCpu] = useState<MetricPoint[]>([]);
  const [memory, setMemory] = useState<MetricPoint[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const loadData = async () => {
    setLoading(true);
    setError(null);
    try {
      const [hRes, sRes, cRes, mRes] = await Promise.allSettled([
        getSystemHealthDashboard(),
        getSystemHealthServices(),
        getSystemHealthMetricsCPU(),
        getSystemHealthMetricsMemory(),
      ]);
      if (hRes.status === 'fulfilled') setHealth(hRes.value);
      if (sRes.status === 'fulfilled') {
        const s = sRes.value;
        setServices(Array.isArray(s?.services) ? s.services : Array.isArray(s) ? s : []);
      }
      if (cRes.status === 'fulfilled') {
        const c = cRes.value;
        setCpu(Array.isArray(c?.datapoints) ? c.datapoints : Array.isArray(c) ? c : []);
      }
      if (mRes.status === 'fulfilled') {
        const m = mRes.value;
        setMemory(Array.isArray(m?.datapoints) ? m.datapoints : Array.isArray(m) ? m : []);
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Data load failed');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { loadData(); }, []);

  const statusColor = (s: string) => {
    if (s === 'healthy' || s === 'running') return 'text-[var(--color-status-active)]';
    if (s === 'degraded' || s === 'warning') return 'text-[var(--q-yellow)]';
    return 'text-[var(--color-brand-red)]';
  };

  if (loading) {
    return <div className="min-h-screen bg-[var(--color-bg-base)] text-white flex items-center justify-center"><RefreshCw className="w-8 h-8 animate-spin text-[var(--color-status-active)]" /></div>;
  }

  return (
    <div className="min-h-screen bg-[var(--color-bg-base)] text-white p-6">
      <div className="max-w-7xl mx-auto space-y-8">
        <div className="flex items-center justify-between">
          <div>
            <Link href="/founder/infra" className="text-[var(--color-text-secondary)] hover:text-[var(--color-text-primary)] flex items-center gap-1 text-sm mb-2"><ArrowLeft className="w-4 h-4" /> Infrastructure Hub</Link>
            <h1 className="text-3xl font-bold flex items-center gap-3"><Cpu className="w-8 h-8 text-[var(--color-system-compliance)]" /> AI / GPU Infrastructure</h1>
            <p className="text-[var(--color-text-secondary)] mt-1">GPU utilization, SageMaker endpoints, and Bedrock inference monitoring</p>
          </div>
          <button onClick={loadData} className="px-4 py-2 bg-[var(--color-bg-raised)] hover:bg-[var(--color-bg-overlay)] chamfer-8 flex items-center gap-2 text-sm"><RefreshCw className="w-4 h-4" /> Refresh</button>
        </div>

        {error && <div className="bg-red-900/30 border border-[var(--color-brand-red)] chamfer-8 p-4 flex items-center gap-3"><AlertTriangle className="w-5 h-5 text-[var(--color-brand-red)]" /><span className="text-[var(--color-brand-red)]">{error}</span></div>}

        <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
          <div className="bg-[var(--color-bg-panel)] border border-[var(--color-border-default)] chamfer-8 p-5">
            <div className="flex items-center gap-2 text-[var(--color-text-secondary)] text-sm mb-1"><Activity className="w-4 h-4" /> Overall Status</div>
            <div className={`text-2xl font-bold uppercase ${statusColor(health?.overall_status ?? 'unknown')}`}>{health?.overall_status ?? 'Unknown'}</div>
          </div>
          <div className="bg-[var(--color-bg-panel)] border border-[var(--color-border-default)] chamfer-8 p-5">
            <div className="flex items-center gap-2 text-[var(--color-text-secondary)] text-sm mb-1"><Server className="w-4 h-4" /> Services</div>
            <div className="text-2xl font-bold text-[var(--color-status-info)]">{health?.service_count ?? services.length}</div>
          </div>
          <div className="bg-[var(--color-bg-panel)] border border-[var(--color-border-default)] chamfer-8 p-5">
            <div className="flex items-center gap-2 text-[var(--color-text-secondary)] text-sm mb-1"><Zap className="w-4 h-4" /> Avg CPU</div>
            <div className="text-2xl font-bold text-[var(--color-status-info)]">{cpu.length > 0 ? `${(cpu.reduce((a, c) => a + (c.value ?? 0), 0) / cpu.length).toFixed(1)}%` : '—'}</div>
          </div>
          <div className="bg-[var(--color-bg-panel)] border border-[var(--color-border-default)] chamfer-8 p-5">
            <div className="flex items-center gap-2 text-[var(--color-text-secondary)] text-sm mb-1"><Zap className="w-4 h-4" /> Avg Memory</div>
            <div className="text-2xl font-bold text-[var(--color-system-compliance)]">{memory.length > 0 ? `${(memory.reduce((a, m) => a + (m.value ?? 0), 0) / memory.length).toFixed(1)}%` : '—'}</div>
          </div>
        </div>

        {/* AI/GPU Services */}
        <div className="bg-[var(--color-bg-panel)] border border-[var(--color-border-default)] chamfer-8 overflow-hidden">
          <div className="px-6 py-4 border-b border-[var(--color-border-default)]"><h2 className="text-lg font-semibold flex items-center gap-2"><Cpu className="w-5 h-5 text-[var(--color-system-compliance)]" /> AI Service Status</h2></div>
          {services.length === 0 ? (
            <div className="p-12 text-center text-[var(--color-text-muted)]">No AI/GPU services detected. Infrastructure telemetry will populate when services are deployed.</div>
          ) : (
            <table className="w-full text-sm">
              <thead className="bg-[var(--color-bg-raised)]/50">
                <tr>
                  <th className="text-left px-6 py-3 text-[var(--color-text-secondary)] font-medium">Service</th>
                  <th className="text-left px-6 py-3 text-[var(--color-text-secondary)] font-medium">Status</th>
                  <th className="text-left px-6 py-3 text-[var(--color-text-secondary)] font-medium">Latency</th>
                  <th className="text-left px-6 py-3 text-[var(--color-text-secondary)] font-medium">Region</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-800">
                {services.map((s, i) => (
                  <tr key={i} className="hover:bg-[var(--color-bg-raised)]/30">
                    <td className="px-6 py-3 text-white font-medium">{s.name}</td>
                    <td className={`px-6 py-3 font-bold uppercase ${statusColor(s.status)}`}>{s.status}</td>
                    <td className="px-6 py-3 text-[var(--color-text-secondary)]">{s.latency_ms != null ? `${s.latency_ms}ms` : '—'}</td>
                    <td className="px-6 py-3 text-[var(--color-text-secondary)]">{s.region ?? '—'}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </div>
      </div>
    </div>
  );
}
