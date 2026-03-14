'use client';

import { useEffect, useState } from 'react';
import { motion } from 'framer-motion';
import { Radio, Send, Users, Activity, ArrowLeft } from 'lucide-react';
import Link from 'next/link';
import {
  getActiveCrewPages,
  pushCrewPage,
  updateMyCrewAvailability,
  getCrewlinkHealth,
} from '@/services/api';

interface CrewPage {
  id: string;
  message: string;
  priority: string;
  sent_at: string;
  responses: { crew_id: string; response: string; responded_at: string }[];
}

interface CrewlinkHealthData {
  status?: string;
  active_connections?: number;
  latency_ms?: number;
  last_heartbeat?: string;
}

export default function CrewLinkPWAPage() {
  const [pages, setPages] = useState<CrewPage[]>([]);
  const [health, setHealth] = useState<CrewlinkHealthData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [showPage, setShowPage] = useState(false);
  const [pageMsg, setPageMsg] = useState('');
  const [pagePriority, setPagePriority] = useState('normal');

  useEffect(() => {
    async function loadData() {
      try {
        setLoading(true);
        const results = await Promise.allSettled([
          getActiveCrewPages(),
          getCrewlinkHealth(),
        ]);
        if (results[0].status === 'fulfilled') {
          const p = results[0].value;
          setPages(Array.isArray(p?.data) ? p.data : Array.isArray(p) ? p : []);
        }
        if (results[1].status === 'fulfilled') {
          const h = results[1].value;
          setHealth(h?.data ?? h);
        }
      } catch (err: unknown) {
        setError(err instanceof Error ? err.message : 'Failed to load CrewLink data');
      } finally {
        setLoading(false);
      }
    }
    loadData();
  }, []);

  async function handleSendPage() {
    if (!pageMsg.trim()) return;
    try {
      await pushCrewPage({ crew_ids: [], message: pageMsg.trim(), priority: pagePriority });
      setPageMsg('');
      setShowPage(false);
      const res = await getActiveCrewPages();
      setPages(Array.isArray(res?.data) ? res.data : Array.isArray(res) ? res : []);
    } catch { /* toast */ }
  }

  async function handleUpdateAvailability(status: string) {
    try {
      await updateMyCrewAvailability({ status });
    } catch { /* toast */ }
  }

  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-[60vh]">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-orange-500" />
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

  const highPriority = pages.filter((p) => p.priority === 'high' || p.priority === 'critical').length;
  const connStatus = health?.status ?? 'unknown';

  return (
    <div className="p-6 max-w-7xl mx-auto space-y-6">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <Link href="/founder/pwa" className="text-[var(--color-text-secondary)] hover:text-[var(--color-text-primary)]"><ArrowLeft className="h-5 w-5" /></Link>
          <Radio className="h-6 w-6 text-[var(--q-orange)]" />
          <h1 className="text-2xl font-bold text-white">CrewLink PWA</h1>
        </div>
        <div className="flex items-center gap-2">
          <button onClick={() => handleUpdateAvailability('available')} className="px-3 py-1.5 bg-green-600/80 hover:bg-green-600 rounded text-white text-xs font-medium">Available</button>
          <button onClick={() => handleUpdateAvailability('busy')} className="px-3 py-1.5 bg-yellow-600/80 hover:bg-yellow-600 rounded text-white text-xs font-medium">Busy</button>
          <button onClick={() => setShowPage(!showPage)} className="flex items-center gap-1 px-3 py-1.5 bg-orange-600 hover:bg-orange-700 rounded text-white text-xs font-medium">
            <Send className="h-3.5 w-3.5" /> Send Page
          </button>
        </div>
      </div>

      {showPage && (
        <motion.div initial={{ opacity: 0, y: -10 }} animate={{ opacity: 1, y: 0 }} className="bg-[var(--color-bg-raised)] border border-[var(--color-border-strong)] chamfer-8 p-4 space-y-3">
          <div>
            <label className="block text-xs text-[var(--color-text-secondary)] mb-1">Message</label>
            <input value={pageMsg} onChange={(e) => setPageMsg(e.target.value)} className="w-full px-3 py-2 bg-[var(--color-bg-panel)] border border-gray-600 rounded text-white text-sm" placeholder="Page message..." />
          </div>
          <div className="flex items-center gap-3">
            <select value={pagePriority} onChange={(e) => setPagePriority(e.target.value)} className="px-3 py-2 bg-[var(--color-bg-panel)] border border-gray-600 rounded text-white text-sm">
              <option value="normal">Normal</option>
              <option value="high">High</option>
              <option value="critical">Critical</option>
            </select>
            <button onClick={handleSendPage} className="px-4 py-2 bg-orange-600 hover:bg-orange-700 rounded text-white text-sm font-medium">Send</button>
          </div>
        </motion.div>
      )}

      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        {[
          { label: 'Active Pages', value: pages.length, icon: Radio, color: 'orange' },
          { label: 'High Priority', value: highPriority, icon: Send, color: highPriority > 0 ? 'red' : 'green' },
          { label: 'Connections', value: health?.active_connections ?? 0, icon: Users, color: 'blue' },
          { label: 'Link Status', value: connStatus, icon: Activity, color: connStatus === 'healthy' ? 'green' : 'yellow' },
        ].map((kpi) => (
          <motion.div key={kpi.label} initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} className={`bg-[var(--color-bg-raised)] border border-${kpi.color}-500/30 chamfer-8 p-4`}>
            <div className="flex items-center gap-2 text-[var(--color-text-secondary)] text-xs mb-1"><kpi.icon className="h-4 w-4" />{kpi.label}</div>
            <div className="text-2xl font-bold text-white">{kpi.value}</div>
          </motion.div>
        ))}
      </div>

      <div className="bg-[var(--color-bg-raised)] border border-[var(--color-border-strong)] chamfer-8 overflow-hidden">
        <div className="p-4 border-b border-[var(--color-border-strong)]">
          <h2 className="text-sm font-semibold text-white">Active Crew Pages</h2>
        </div>
        <div className="divide-y divide-gray-700">
          {pages.length === 0 ? (
            <div className="px-4 py-8 text-center text-[var(--color-text-muted)]">No active crew pages.</div>
          ) : pages.map((p) => (
            <div key={p.id} className="px-4 py-3 hover:bg-[var(--color-bg-overlay)]/50">
              <div className="flex items-center justify-between mb-1">
                <span className="text-sm text-white font-medium">{p.message}</span>
                <span className={`px-2 py-0.5 rounded text-xs font-medium ${p.priority === 'critical' ? 'bg-red-900/50 text-[var(--color-brand-red)]' : p.priority === 'high' ? 'bg-orange-900/50 text-[var(--q-orange)]' : 'bg-[var(--color-bg-overlay)] text-[var(--color-text-secondary)]'}`}>{p.priority}</span>
              </div>
              <div className="flex items-center justify-between text-xs text-[var(--color-text-secondary)]">
                <span>{p.sent_at ? new Date(p.sent_at).toLocaleString() : '—'}</span>
                <span>{p.responses?.length ?? 0} responses</span>
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
