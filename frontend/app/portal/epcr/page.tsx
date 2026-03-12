'use client';

import { useEffect, useState, useCallback } from 'react';
import Link from 'next/link';
import { listEPCRCharts, type EPCRChartApi } from '@/services/api';
import { FileText, ChevronLeft, Activity, Clock, AlertTriangle } from 'lucide-react';
import { QuantumCardSkeleton } from '@/components/ui';

const STATUS_STYLES: Record<string, { color: string; label: string }> = {
  DRAFT: { color: 'var(--color-text-muted)', label: 'Draft' },
  IN_PROGRESS: { color: 'var(--q-yellow)', label: 'In Progress' },
  SUBMITTED: { color: 'var(--color-status-info)', label: 'Submitted' },
  LOCKED: { color: 'var(--color-status-active)', label: 'Finalized' },
  AMENDED: { color: 'var(--color-system-compliance)', label: 'Amended' },
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
    <div className="flex flex-col h-full min-h-0">
      <div className="flex-1 min-h-0 overflow-y-auto">
        <div className="max-w-5xl mx-auto px-4 py-8">
          {/* Header */}
          <div className="flex items-center justify-between mb-8 pb-4 border-b border-[var(--color-border-default)]">
            <div>
              <Link href="/portal" className="text-[var(--color-text-muted)] hover:text-[var(--color-text-primary)] transition-colors flex items-center gap-1 text-micro font-label font-bold tracking-wider uppercase mb-2">
                <ChevronLeft className="w-4 h-4" /> Patient Portal
              </Link>
              <div className="flex items-center gap-3">
                <div className="w-1 h-6 chamfer-4 flex-shrink-0 bg-[var(--q-orange)]" />
                <h1 className="text-h1 font-black uppercase tracking-wider text-[var(--color-text-primary)]">
                  ePCR Charts
                </h1>
              </div>
              <p className="text-micro text-[var(--color-text-muted)] mt-1 ml-4">Electronic patient care reports for your transport records</p>
            </div>
          </div>

          {/* Status Filters */}
          <div className="flex items-center gap-2 mb-6 flex-wrap">
            <span className="text-micro text-[var(--color-text-muted)]">Filter:</span>
            {['', 'DRAFT', 'IN_PROGRESS', 'SUBMITTED', 'LOCKED'].map((s) => (
              <button key={s} onClick={() => setStatusFilter(s)}
                className={`text-micro font-label font-bold tracking-wider uppercase px-3 py-1 border chamfer-4 transition-colors ${
                  statusFilter === s
                    ? 'border-[color-mix(in_srgb,var(--q-orange)_40%,transparent)] text-[var(--q-orange)] bg-[var(--color-brand-orange-ghost)]'
                    : 'border-[var(--color-border-default)] text-[var(--color-text-muted)] hover:text-[var(--color-text-secondary)] hover:border-[var(--color-border-strong)]'
                }`}>
                {s || 'ALL'}
              </button>
            ))}
          </div>

          {/* Error */}
          {error && (
            <div className="flex items-center gap-3 p-4 mb-6 border border-[var(--color-brand-red)] bg-[var(--color-brand-red-ghost)] chamfer-8 text-body text-[var(--color-brand-red)]">
              <AlertTriangle className="w-4 h-4 shrink-0" />
              {error}
            </div>
          )}

          {/* Loading */}
          {loading && (
            <div className="space-y-3">
              {Array.from({ length: 4 }).map((_, i) => (
                <QuantumCardSkeleton key={i} />
              ))}
            </div>
          )}

          {/* Empty State */}
          {!loading && !error && charts.length === 0 && (
            <div className="bg-[var(--color-bg-panel)] border border-[var(--color-border-default)] chamfer-12 p-12 text-center">
              <FileText className="w-10 h-10 text-[var(--color-text-disabled)] mx-auto mb-3" />
              <p className="text-body text-[var(--color-text-muted)]">No ePCR charts found{statusFilter ? ` with status ${statusFilter}` : ''}.</p>
            </div>
          )}

          {/* Charts List */}
          {!loading && charts.length > 0 && (
            <div className="space-y-2">
              {charts.map((chart) => {
                const style = STATUS_STYLES[chart.status] ?? STATUS_STYLES.DRAFT;
                return (
                  <div key={chart.id} className="bg-[var(--color-bg-panel)] border border-[var(--color-border-default)] chamfer-8 p-4 hover:border-[var(--color-border-strong)] transition-colors">
                    <div className="flex items-start justify-between">
                      <div className="flex-1">
                        <div className="flex items-center gap-3 mb-1">
                          <span className="text-body font-bold text-[var(--color-text-primary)]">
                            {chart.patient_last_name}, {chart.patient_first_name}
                          </span>
                          <span
                            className="text-micro font-label font-bold tracking-wider uppercase px-2 py-0.5 chamfer-4"
                            style={{ color: style.color, backgroundColor: `color-mix(in srgb, ${style.color} 12%, transparent)`, border: `1px solid color-mix(in srgb, ${style.color} 30%, transparent)` }}
                          >
                            {style.label}
                          </span>
                        </div>
                        <div className="flex items-center gap-4 text-micro text-[var(--color-text-muted)]">
                          <span className="flex items-center gap-1">
                            <Activity className="w-3 h-3" />
                            {chart.chief_complaint || chart.dispatch_complaint || 'No complaint recorded'}
                          </span>
                          <span className="flex items-center gap-1">
                            <Clock className="w-3 h-3" />
                            {new Date(chart.incident_date).toLocaleDateString()}
                          </span>
                          {chart.completeness_score !== undefined && (
                            <span className="font-mono" style={{
                              color: chart.completeness_score >= 90 ? 'var(--color-status-active)' : chart.completeness_score >= 70 ? 'var(--q-yellow)' : 'var(--color-brand-red)'
                            }}>
                              {chart.completeness_score}% complete
                            </span>
                          )}
                        </div>
                        {chart.narrative && (
                          <p className="text-micro text-[var(--color-text-disabled)] mt-2 line-clamp-2">{chart.narrative}</p>
                        )}
                      </div>
                      <div className="text-micro font-mono text-[var(--color-text-disabled)] ml-4 shrink-0">
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
    </div>
  );
}
