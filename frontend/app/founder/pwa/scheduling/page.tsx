'use client';

import { useEffect, useState } from 'react';
import { motion } from 'framer-motion';
import { Calendar, Users, AlertTriangle, Clock, ArrowLeft } from 'lucide-react';
import Link from 'next/link';
import {
  getSchedulingCoverageDashboard,
  listShiftTemplates,
  getSchedulingAIDrafts,
  getSchedulingFatigueReport,
} from '@/services/api';

interface CoverageDashboard {
  total_slots?: number;
  filled_slots?: number;
  open_slots?: number;
  coverage_percent?: number;
}

interface ShiftTemplate {
  id: string;
  name: string;
  start_time: string;
  end_time: string;
  crew_required: number;
  days_of_week?: string[];
}

interface AIDraft {
  id: string;
  shift_date: string;
  crew_member: string;
  shift_name: string;
  ai_confidence?: number;
  status: string;
}

interface FatigueEntry {
  crew_member: string;
  hours_last_48: number;
  fatigue_risk: string;
}

export default function PWASchedulingPage() {
  const [coverage, setCoverage] = useState<CoverageDashboard | null>(null);
  const [templates, setTemplates] = useState<ShiftTemplate[]>([]);
  const [drafts, setDrafts] = useState<AIDraft[]>([]);
  const [fatigue, setFatigue] = useState<FatigueEntry[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    async function loadData() {
      try {
        setLoading(true);
        const results = await Promise.allSettled([
          getSchedulingCoverageDashboard(),
          listShiftTemplates(),
          getSchedulingAIDrafts(),
          getSchedulingFatigueReport(),
        ]);
        if (results[0].status === 'fulfilled') {
          const d = results[0].value;
          setCoverage(d?.data ?? d);
        }
        if (results[1].status === 'fulfilled') {
          const t = results[1].value;
          setTemplates(Array.isArray(t?.data) ? t.data : Array.isArray(t) ? t : []);
        }
        if (results[2].status === 'fulfilled') {
          const d = results[2].value;
          setDrafts(Array.isArray(d?.data) ? d.data : Array.isArray(d) ? d : []);
        }
        if (results[3].status === 'fulfilled') {
          const f = results[3].value;
          setFatigue(Array.isArray(f?.data) ? f.data : Array.isArray(f) ? f : []);
        }
      } catch (err: unknown) {
        setError(err instanceof Error ? err.message : 'Failed to load scheduling data');
      } finally {
        setLoading(false);
      }
    }
    loadData();
  }, []);

  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-[60vh]">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-violet-500" />
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

  const pct = coverage?.coverage_percent ?? (coverage?.total_slots ? Math.round(((coverage.filled_slots ?? (() => { throw new Error('Unsafe silent fallback. Dependency missing.'); })()) / coverage.total_slots) * 100) : 0);
  const highFatigue = fatigue.filter((f) => f.fatigue_risk === 'high').length;

  return (
    <div className="p-6 max-w-7xl mx-auto space-y-6">
      <div className="flex items-center gap-3">
        <Link href="/founder/pwa" className="text-gray-400 hover:text-white"><ArrowLeft className="h-5 w-5" /></Link>
        <Calendar className="h-6 w-6 text-violet-400" />
        <h1 className="text-2xl font-bold text-white">PWA Scheduling</h1>
      </div>

      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        {[
          { label: 'Coverage', value: `${pct}%`, icon: Users, color: pct >= 90 ? 'green' : pct >= 70 ? 'yellow' : 'red' },
          { label: 'Open Slots', value: coverage?.open_slots ?? (() => { throw new Error('Unsafe silent fallback. Dependency missing.'); })(), icon: Calendar, color: 'blue' },
          { label: 'AI Drafts', value: drafts.length, icon: Clock, color: 'purple' },
          { label: 'Fatigue Alerts', value: highFatigue, icon: AlertTriangle, color: highFatigue > 0 ? 'red' : 'green' },
        ].map((kpi) => (
          <motion.div key={kpi.label} initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} className={`bg-gray-800 border border-${kpi.color}-500/30 rounded-lg p-4`}>
            <div className="flex items-center gap-2 text-gray-400 text-xs mb-1"><kpi.icon className="h-4 w-4" />{kpi.label}</div>
            <div className="text-2xl font-bold text-white">{kpi.value}</div>
          </motion.div>
        ))}
      </div>

      <div className="bg-gray-800 border border-gray-700 rounded-lg overflow-hidden">
        <div className="p-4 border-b border-gray-700">
          <h2 className="text-sm font-semibold text-white">Shift Templates</h2>
        </div>
        <table className="w-full text-sm">
          <thead className="bg-gray-900 text-gray-400 text-xs uppercase">
            <tr>
              <th className="px-4 py-3 text-left">Template</th>
              <th className="px-4 py-3 text-left">Start</th>
              <th className="px-4 py-3 text-left">End</th>
              <th className="px-4 py-3 text-left">Crew Required</th>
              <th className="px-4 py-3 text-left">Days</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-700">
            {templates.length === 0 ? (
              <tr><td colSpan={5} className="px-4 py-8 text-center text-gray-500">No shift templates configured.</td></tr>
            ) : templates.map((t) => (
              <tr key={t.id} className="hover:bg-gray-700/50">
                <td className="px-4 py-3 text-white font-medium">{t.name}</td>
                <td className="px-4 py-3 text-gray-300">{t.start_time}</td>
                <td className="px-4 py-3 text-gray-300">{t.end_time}</td>
                <td className="px-4 py-3 text-gray-300">{t.crew_required}</td>
                <td className="px-4 py-3 text-gray-400">{t.days_of_week?.join(', ') ?? 'All'}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {drafts.length > 0 && (
        <div className="bg-gray-800 border border-purple-500/30 rounded-lg overflow-hidden">
          <div className="p-4 border-b border-gray-700">
            <h2 className="text-sm font-semibold text-white">AI Schedule Drafts</h2>
          </div>
          <table className="w-full text-sm">
            <thead className="bg-gray-900 text-gray-400 text-xs uppercase">
              <tr>
                <th className="px-4 py-3 text-left">Crew</th>
                <th className="px-4 py-3 text-left">Shift</th>
                <th className="px-4 py-3 text-left">Date</th>
                <th className="px-4 py-3 text-left">Confidence</th>
                <th className="px-4 py-3 text-left">Status</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-700">
              {drafts.map((d) => (
                <tr key={d.id} className="hover:bg-gray-700/50">
                  <td className="px-4 py-3 text-white">{d.crew_member}</td>
                  <td className="px-4 py-3 text-gray-300">{d.shift_name}</td>
                  <td className="px-4 py-3 text-gray-300">{d.shift_date}</td>
                  <td className="px-4 py-3 text-gray-300">{d.ai_confidence ? `${(d.ai_confidence * 100).toFixed(0)}%` : '—'}</td>
                  <td className="px-4 py-3"><span className="px-2 py-0.5 rounded text-xs font-medium bg-purple-900/50 text-purple-300">{d.status}</span></td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {fatigue.length > 0 && (
        <div className="bg-gray-800 border border-red-500/30 rounded-lg overflow-hidden">
          <div className="p-4 border-b border-gray-700">
            <h2 className="text-sm font-semibold text-white">Fatigue Report</h2>
          </div>
          <table className="w-full text-sm">
            <thead className="bg-gray-900 text-gray-400 text-xs uppercase">
              <tr>
                <th className="px-4 py-3 text-left">Crew Member</th>
                <th className="px-4 py-3 text-left">Hours (48h)</th>
                <th className="px-4 py-3 text-left">Risk Level</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-700">
              {fatigue.map((f, i) => (
                <tr key={i} className="hover:bg-gray-700/50">
                  <td className="px-4 py-3 text-white">{f.crew_member}</td>
                  <td className="px-4 py-3 text-gray-300">{f.hours_last_48}h</td>
                  <td className="px-4 py-3">
                    <span className={`px-2 py-0.5 rounded text-xs font-medium ${f.fatigue_risk === 'high' ? 'bg-red-900/50 text-red-300' : f.fatigue_risk === 'medium' ? 'bg-yellow-900/50 text-yellow-300' : 'bg-green-900/50 text-green-300'}`}>{f.fatigue_risk}</span>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
