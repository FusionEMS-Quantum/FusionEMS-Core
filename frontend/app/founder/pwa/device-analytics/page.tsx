'use client';

import { useEffect, useState } from 'react';
import { motion } from 'framer-motion';
import { Smartphone, Wifi, AlertTriangle, Activity, ArrowLeft } from 'lucide-react';
import Link from 'next/link';
import {
  getSystemHealthDashboard,
  getSystemHealthServices,
  getSystemHealthMetricsErrors,
} from '@/services/api';

interface ServiceRecord {
  name: string;
  status: string;
  cpu_percent?: number;
  memory_mb?: number;
  uptime_hours?: number;
  last_check?: string;
}

interface DashboardData {
  total_services?: number;
  healthy?: number;
  degraded?: number;
  down?: number;
  avg_latency_ms?: number;
}

export default function DeviceAnalyticsPage() {
  const [dashboard, setDashboard] = useState<DashboardData | null>(null);
  const [services, setServices] = useState<ServiceRecord[]>([]);
  const [errorMetrics, setErrorMetrics] = useState<Record<string, unknown> | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    async function loadData() {
      try {
        setLoading(true);
        const results = await Promise.allSettled([
          getSystemHealthDashboard(),
          getSystemHealthServices(),
          getSystemHealthMetricsErrors(),
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
          const e = results[2].value;
          setErrorMetrics(e?.data ?? e);
        }
      } catch (err: unknown) {
        setError(err instanceof Error ? err.message : 'Failed to load device analytics');
      } finally {
        setLoading(false);
      }
    }
    loadData();
  }, []);

  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-[60vh]">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-indigo-500" />
      </div>
    );
  }

  if (error) {
    return (
      <div className="p-6 max-w-7xl mx-auto">
        <div className="bg-red-900/30 border border-red-700 rounded-lg p-4 text-red-300">{error}</div>
      </div>
    );
  }

  const totalDevices = dashboard?.total_services ?? services.length;
  const online = dashboard?.healthy ?? services.filter((s) => s.status === 'healthy').length;
  const degraded = dashboard?.degraded ?? services.filter((s) => s.status === 'degraded').length;
  const offline = dashboard?.down ?? services.filter((s) => s.status === 'down').length;
  const errorRate = errorMetrics && typeof errorMetrics === 'object' ? (errorMetrics as Record<string, number>).rate ?? 0 : 0;

  return (
    <div className="p-6 max-w-7xl mx-auto space-y-6">
      <div className="flex items-center gap-3">
        <Link href="/founder/pwa" className="text-gray-400 hover:text-white"><ArrowLeft className="h-5 w-5" /></Link>
        <Smartphone className="h-6 w-6 text-indigo-400" />
        <h1 className="text-2xl font-bold text-white">Device Analytics</h1>
      </div>

      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        {[
          { label: 'Registered Devices', value: totalDevices, icon: Smartphone, color: 'indigo' },
          { label: 'Online', value: online, icon: Wifi, color: 'green' },
          { label: 'Degraded', value: degraded, icon: AlertTriangle, color: 'yellow' },
          { label: 'Offline', value: offline, icon: Activity, color: 'red' },
        ].map((kpi) => (
          <motion.div key={kpi.label} initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} className={`bg-gray-800 border border-${kpi.color}-500/30 rounded-lg p-4`}>
            <div className="flex items-center gap-2 text-gray-400 text-xs mb-1"><kpi.icon className="h-4 w-4" />{kpi.label}</div>
            <div className="text-2xl font-bold text-white">{kpi.value}</div>
          </motion.div>
        ))}
      </div>

      {errorRate > 0 && (
        <div className="bg-red-900/20 border border-red-700/40 rounded-lg p-3 text-sm text-red-300">
          Error rate: {typeof errorRate === 'number' ? errorRate.toFixed(2) : errorRate}% across fleet
        </div>
      )}

      <div className="bg-gray-800 border border-gray-700 rounded-lg overflow-hidden">
        <div className="p-4 border-b border-gray-700">
          <h2 className="text-sm font-semibold text-white">Device Telemetry</h2>
        </div>
        <table className="w-full text-sm">
          <thead className="bg-gray-900 text-gray-400 text-xs uppercase">
            <tr>
              <th className="px-4 py-3 text-left">Device / Service</th>
              <th className="px-4 py-3 text-left">Status</th>
              <th className="px-4 py-3 text-left">CPU %</th>
              <th className="px-4 py-3 text-left">Memory (MB)</th>
              <th className="px-4 py-3 text-left">Uptime (h)</th>
              <th className="px-4 py-3 text-left">Last Check</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-700">
            {services.length === 0 ? (
              <tr><td colSpan={6} className="px-4 py-8 text-center text-gray-500">No device telemetry data available.</td></tr>
            ) : services.map((s, i) => (
              <tr key={i} className="hover:bg-gray-700/50">
                <td className="px-4 py-3 text-white font-medium">{s.name}</td>
                <td className="px-4 py-3">
                  <span className={`px-2 py-0.5 rounded text-xs font-medium ${s.status === 'healthy' ? 'bg-green-900/50 text-green-300' : s.status === 'degraded' ? 'bg-yellow-900/50 text-yellow-300' : 'bg-red-900/50 text-red-300'}`}>{s.status}</span>
                </td>
                <td className="px-4 py-3 text-gray-300">{s.cpu_percent?.toFixed(1) ?? '—'}%</td>
                <td className="px-4 py-3 text-gray-300">{s.memory_mb?.toFixed(0) ?? '—'}</td>
                <td className="px-4 py-3 text-gray-300">{s.uptime_hours?.toFixed(1) ?? '—'}</td>
                <td className="px-4 py-3 text-gray-400">{s.last_check ? new Date(s.last_check).toLocaleString() : '—'}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
