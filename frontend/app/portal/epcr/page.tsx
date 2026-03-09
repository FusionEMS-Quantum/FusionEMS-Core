'use client';

import { useEffect, useState, useCallback } from 'react';
import Link from 'next/link';
import { listEPCRCharts, type EPCRChartApi } from '@/services/api';
import { FileText, ChevronLeft, Activity, Clock, AlertTriangle } from 'lucide-react';

const STATUS_STYLES: Record<string, { bg: string; text: string; label: string }> = {
  DRAFT: { bg: 'bg-zinc-500/10 border-zinc-500/30', text: 'text-zinc-400', label: 'Draft' },
  IN_PROGRESS: { bg: 'bg-yellow-500/10 border-yellow-500/30', text: 'text-yellow-400', label: 'In Progress' },
  SUBMITTED: { bg: 'bg-blue-500/10 border-blue-500/30', text: 'text-blue-400', label: 'Submitted' },
  LOCKED: { bg: 'bg-green-500/10 border-green-500/30', text: 'text-green-400', label: 'Finalized' },
  AMENDED: { bg: 'bg-purple-500/10 border-purple-500/30', text: 'text-purple-400', label: 'Amended' },
};

export default function PortalEPCRPage() {
  const [charts, setCharts] = useState<EPCRChartApi[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [statusFilter, setStatusFilter] = useState('');

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await listEPCRCharts(statusFilter || undefined);
      setCharts(data);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : 'Unable to load ePCR charts');
    } finally {
      setLoading(false);
    }
  }, [statusFilter]);

  useEffect(() => { load(); }, [load]);

  return (
    <div className="min-h-screen bg-[#060608] text-gray-200">
      <div className="max-w-5xl mx-auto px-4 py-8">
        {/* Header */}
        <div className="flex items-center justify-between mb-8 pb-4 border-b border-white/10">
          <div>
            <Link href="/portal" className="text-zinc-500 hover:text-white transition-colors flex items-center gap-1 text-xs font-bold tracking-widest uppercase mb-2">
              <ChevronLeft className="w-4 h-4" /> Patient Portal
            </Link>
            <h1 className="text-2xl font-black uppercase tracking-wider text-white flex items-center gap-3">
              <FileText className="w-6 h-6 text-[#FF4D00]" />
              ePCR Charts
            </h1>
            <p className="text-xs text-zinc-500 mt-1">Electronic patient care reports for your transport records</p>
          </div>
        </div>

        {/* Status Filters */}
        <div className="flex items-center gap-2 mb-6 flex-wrap">
          <span className="text-xs text-zinc-500">Filter:</span>
          {['', 'DRAFT', 'IN_PROGRESS', 'SUBMITTED', 'LOCKED'].map((s) => (
            <button key={s} onClick={() => setStatusFilter(s)}
              className={`text-[10px] px-3 py-1 border font-bold tracking-widest uppercase transition-colors ${
                statusFilter === s
                  ? 'border-[#FF4D00]/40 text-[#FF4D00] bg-[rgba(255,77,0,0.08)]'
                  : 'border-white/10 text-zinc-500 hover:text-zinc-300'
              }`}>
              {s || 'ALL'}
            </button>
          ))}
        </div>

        {/* Error */}
        {error && (
          <div className="flex items-center gap-3 p-4 mb-6 border border-red-500/30 bg-red-500/5 text-red-400 text-sm">
            <AlertTriangle className="w-4 h-4 shrink-0" />
            {error}
          </div>
        )}

        {/* Loading */}
        {loading && (
          <div className="space-y-3">
            {Array.from({ length: 4 }).map((_, i) => (
              <div key={i} className="h-20 bg-[#0A0A0B] border border-white/5 animate-pulse" />
            ))}
          </div>
        )}

        {/* Empty State */}
        {!loading && !error && charts.length === 0 && (
          <div className="bg-[#0A0A0B] border border-white/10 p-12 text-center">
            <FileText className="w-10 h-10 text-zinc-600 mx-auto mb-3" />
            <p className="text-zinc-500 text-sm">No ePCR charts found{statusFilter ? ` with status ${statusFilter}` : ''}.</p>
          </div>
        )}

        {/* Charts List */}
        {!loading && charts.length > 0 && (
          <div className="space-y-2">
            {charts.map((chart) => {
              const style = STATUS_STYLES[chart.status] ?? STATUS_STYLES.DRAFT;
              return (
                <div key={chart.id} className="bg-[#0A0A0B] border border-white/10 p-4 hover:border-white/20 transition-colors">
                  <div className="flex items-start justify-between">
                    <div className="flex-1">
                      <div className="flex items-center gap-3 mb-1">
                        <span className="text-sm font-bold text-white">
                          {chart.patient_last_name}, {chart.patient_first_name}
                        </span>
                        <span className={`text-[10px] font-bold tracking-wider uppercase px-2 py-0.5 border ${style.bg} ${style.text}`}>
                          {style.label}
                        </span>
                      </div>
                      <div className="flex items-center gap-4 text-xs text-zinc-500">
                        <span className="flex items-center gap-1">
                          <Activity className="w-3 h-3" />
                          {chart.chief_complaint || chart.dispatch_complaint || 'No complaint recorded'}
                        </span>
                        <span className="flex items-center gap-1">
                          <Clock className="w-3 h-3" />
                          {new Date(chart.incident_date).toLocaleDateString()}
                        </span>
                        {chart.completeness_score !== undefined && (
                          <span className={`font-mono ${chart.completeness_score >= 90 ? 'text-green-400' : chart.completeness_score >= 70 ? 'text-yellow-400' : 'text-red-400'}`}>
                            {chart.completeness_score}% complete
                          </span>
                        )}
                      </div>
                      {chart.narrative && (
                        <p className="text-xs text-zinc-600 mt-2 line-clamp-2">{chart.narrative}</p>
                      )}
                    </div>
                    <div className="text-[10px] font-mono text-zinc-600 ml-4 shrink-0">
                      Unit: {chart.unit_id}
                    </div>
                  </div>
                </div>
              );
            })}
          </div>
        )}
      </div>
    </div>
  );
}
