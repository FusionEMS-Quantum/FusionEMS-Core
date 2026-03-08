'use client';

import React, { useEffect, useState, useCallback } from 'react';
import { QuantumTableSkeleton, QuantumEmptyState } from '@/components/ui';
import {
  listShiftInstances,
  listSchedulingSwaps,
  getSchedulingCoverageDashboard,
  getSchedulingAIDrafts,
  approveSchedulingAIDraft,
  requestSchedulingAIDraft,
  getSchedulingFatigueReport,
  getExpiringCredentials,
} from '@/services/api';

// ── Types ─────────────────────────────────────────────────────────────────────

interface ShiftInstance {
  id: string;
  unit_name?: string;
  template_id?: string;
  start_time: string;
  end_time: string;
  state: string;
  assigned_crew?: string[];
  station?: string;
}

interface SwapRequest {
  id: string;
  requester_name?: string;
  request_type: string;
  shift_date?: string;
  reason?: string;
  submitted_at?: string;
  state: string;
}

interface CoverageDashboard {
  coverage_pct?: number;
  uncovered_shifts?: number;
  on_call_available?: number;
  fatigue_flags?: number;
  by_day?: Record<string, number>;
}

interface AIDraft {
  id: string;
  horizon_days?: number;
  generated_at?: string;
  shifts_count?: number;
  state: string;
  score?: number;
}

interface FatigueReport {
  flagged_crew?: { name: string; hours_last_7d: number; risk_level: string }[];
  avg_hours_7d?: number;
}

interface ExpiringCredential {
  crew_member_name?: string;
  cert_type?: string;
  expiry_date?: string;
  days_until_expiry?: number;
}

// ── Constants ─────────────────────────────────────────────────────────────────

const DAYS = ['Sun', 'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat'];
const HOURS = Array.from({ length: 16 }, (_, i) => `${String(i + 6).padStart(2, '0')}:00`);

const SHIFT_COLORS: Record<string, string> = {
  ACTIVE: 'bg-green-500/20 border-green-500/40 text-green-300',
  DRAFT: 'bg-gray-700/50 border-gray-600 text-zinc-500',
  PUBLISHED: 'bg-blue-900/30 border-blue-500/40 text-blue-300',
  COMPLETED: 'bg-purple-900/30 border-purple-500/40 text-purple-300',
  CANCELLED: 'bg-red-900/20 border-red-500/30 text-red-400',
};

// ── Week Calendar ─────────────────────────────────────────────────────────────

function WeekCalendar({ shifts, weekOffset }: { shifts: ShiftInstance[]; weekOffset: number }) {
  const today = new Date();
  const startOfWeek = new Date(today);
  startOfWeek.setDate(today.getDate() - today.getDay() + weekOffset * 7);

  const dayDates = DAYS.map((_, i) => {
    const d = new Date(startOfWeek);
    d.setDate(startOfWeek.getDate() + i);
    return d;
  });

  const shiftsForDay = (date: Date) =>
    shifts.filter(s => new Date(s.start_time).toDateString() === date.toDateString());

  return (
    <div className="bg-[#0A0A0B] border border-border-subtle chamfer-8 overflow-hidden">
      <div className="grid grid-cols-8 border-b border-border-subtle">
        <div className="px-3 py-2 text-micro text-zinc-500">UTC</div>
        {dayDates.map((d, i) => {
          const isToday = d.toDateString() === today.toDateString();
          const dayShifts = shiftsForDay(d);
          return (
            <div key={i} className={`px-2 py-2 text-center border-l border-border-subtle ${isToday ? 'bg-brand-orange/5' : ''}`}>
              <div className={`text-micro uppercase tracking-wider ${isToday ? 'text-brand-orange' : 'text-zinc-500'}`}>{DAYS[i]}</div>
              <div className={`text-sm font-bold mt-0.5 ${isToday ? 'text-brand-orange' : 'text-zinc-400'}`}>{d.getDate()}</div>
              {dayShifts.length > 0 && (
                <div className="text-micro text-green-400 mt-0.5">{dayShifts.length} shift{dayShifts.length > 1 ? 's' : ''}</div>
              )}
            </div>
          );
        })}
      </div>
      <div className="overflow-y-auto" style={{ maxHeight: 360 }}>
        {HOURS.map((hour) => {
          const hourNum = parseInt(hour.split(':')[0], 10);
          return (
            <div key={hour} className="grid grid-cols-8 border-b border-border-subtle min-h-[40px]">
              <div className="px-3 py-1 text-micro text-zinc-500">{hour}</div>
              {dayDates.map((d, colIdx) => {
                const activeSifts = shiftsForDay(d).filter(s => {
                  const start = new Date(s.start_time).getHours();
                  return start === hourNum;
                });
                return (
                  <div
                    key={colIdx}
                    className="border-l border-border-subtle px-1 py-0.5"
                  >
                    {activeSifts.map(s => (
                      <div
                        key={s.id}
                        className={`text-micro px-1.5 py-0.5 chamfer-4 border mb-0.5 truncate ${SHIFT_COLORS[s.state] || SHIFT_COLORS.DRAFT}`}
                        title={`${s.unit_name || 'Unit'} — ${(s.assigned_crew || []).join(', ')}`}
                      >
                        {s.unit_name || s.id.slice(0, 6)}
                      </div>
                    ))}
                  </div>
                );
              })}
            </div>
          );
        })}
      </div>
    </div>
  );
}

// ── Coverage View ─────────────────────────────────────────────────────────────

function CoverageView({ coverage, fatigue }: { coverage: CoverageDashboard; fatigue: FatigueReport | null }) {
  const pct = coverage.coverage_pct ?? 0;
  const byDay = coverage.by_day ?? {};

  return (
    <div className="space-y-5">
      <div className="grid grid-cols-4 gap-3">
        {[
          { label: 'Coverage %', value: `${Math.round(pct)}%`, color: pct >= 80 ? 'text-green-400' : pct >= 60 ? 'text-yellow-400' : 'text-red-400' },
          { label: 'Uncovered Shifts', value: (coverage.uncovered_shifts ?? 0).toString(), color: 'text-zinc-100' },
          { label: 'On-Call Available', value: (coverage.on_call_available ?? 0).toString(), color: 'text-blue-400' },
          { label: 'Fatigue Flags', value: (coverage.fatigue_flags ?? 0).toString(), color: (coverage.fatigue_flags ?? 0) > 0 ? 'text-[#FF7A33]' : 'text-zinc-500' },
        ].map(m => (
          <div key={m.label} className="bg-[#0A0A0B] border border-border-subtle chamfer-8 px-4 py-3">
            <div className={`text-2xl font-black ${m.color}`}>{m.value}</div>
            <div className="text-micro text-zinc-500 mt-0.5">{m.label}</div>
          </div>
        ))}
      </div>

      <div className="grid grid-cols-2 gap-4">
        <div className="bg-[#0A0A0B] border border-border-subtle chamfer-8 p-4">
          <div className="text-micro uppercase tracking-widest text-zinc-500 mb-3">Coverage by Day</div>
          <div className="space-y-2">
            {DAYS.map(day => {
              const v = byDay[day] ?? 0;
              return (
                <div key={day} className="flex items-center gap-3">
                  <span className="text-micro text-zinc-500 w-8">{day}</span>
                  <div className="flex-1 h-4 bg-zinc-950/[0.04] chamfer-4 overflow-hidden">
                    <div
                      className={`h-full chamfer-4 transition-all ${v >= 80 ? 'bg-green-500/50' : v >= 60 ? 'bg-yellow-500/50' : v > 0 ? 'bg-red-500/40' : 'bg-gray-600/30'}`}
                      style={{ width: `${v}%` }}
                    />
                  </div>
                  <span className="text-micro text-zinc-500 w-10 text-right">{v}%</span>
                </div>
              );
            })}
          </div>
        </div>

        <div className="bg-[#0A0A0B] border border-border-subtle chamfer-8 p-4">
          <div className="text-micro uppercase tracking-widest text-zinc-500 mb-3">Fatigue & Hours Risk</div>
          {(fatigue?.flagged_crew || []).length === 0 ? (
            <div className="flex flex-col items-center justify-center h-40 text-sm text-zinc-500">
              ✓ No fatigue flags this period
            </div>
          ) : (
            <div className="space-y-2">
              {(fatigue?.flagged_crew || []).map((fc, i) => (
                <div key={i} className="flex items-center justify-between px-3 py-2 bg-zinc-950/[0.03] chamfer-4 border border-border-subtle">
                  <span className="text-sm text-zinc-400">{fc.name}</span>
                  <div className="flex items-center gap-2">
                    <span className="text-micro text-zinc-500">{fc.hours_last_7d}h/7d</span>
                    <span className={`text-micro font-bold px-1.5 py-0.5 chamfer-4 border ${
                      fc.risk_level === 'HIGH' ? 'bg-red-900/30 border-red-500/40 text-red-300' :
                      'bg-yellow-900/30 border-yellow-500/40 text-yellow-300'
                    }`}>{fc.risk_level}</span>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

// ── Swap Requests View ────────────────────────────────────────────────────────

function SwapRequestsView({ swaps, onRefresh }: { swaps: SwapRequest[]; onRefresh: () => void }) {
  const [filter, setFilter] = useState<'all' | 'swap' | 'timeoff' | 'trade'>('all');

  const filtered = swaps.filter(s => filter === 'all' || s.request_type?.toLowerCase() === filter);

  return (
    <div className="space-y-4">
      <div className="grid grid-cols-4 gap-3">
        {[
          { label: 'Pending', value: swaps.filter(s => s.state === 'PENDING').length },
          { label: 'Swaps', value: swaps.filter(s => s.request_type === 'swap').length },
          { label: 'Time Off', value: swaps.filter(s => s.request_type === 'timeoff').length },
          { label: 'Approved', value: swaps.filter(s => s.state === 'APPROVED').length },
        ].map(m => (
          <div key={m.label} className="bg-[#0A0A0B] border border-border-subtle chamfer-8 px-4 py-3">
            <div className="text-2xl font-black text-zinc-100">{m.value}</div>
            <div className="text-micro text-zinc-500 mt-0.5">{m.label}</div>
          </div>
        ))}
      </div>

      <div className="flex items-center gap-1">
        {(['all', 'swap', 'timeoff', 'trade'] as const).map(f => (
          <button
            key={f}
            onClick={() => setFilter(f)}
            className={`px-3 py-1.5 text-micro font-semibold capitalize chamfer-4 border transition-colors ${
              filter === f ? 'bg-brand-orange/15 border-brand-orange/35 text-brand-orange' :
              'bg-zinc-950/[0.03] border-border-subtle text-zinc-500 hover:text-zinc-400'
            }`}
          >
            {f === 'timeoff' ? 'Time Off' : f.charAt(0).toUpperCase() + f.slice(1)}
          </button>
        ))}
        <button onClick={onRefresh} className="ml-auto quantum-btn-sm text-zinc-500 hover:text-zinc-100">↺ Refresh</button>
      </div>

      {filtered.length === 0 ? (
        <QuantumEmptyState title="No requests" description="No pending scheduling requests match your filter." icon="calendar" />
      ) : (
        <div className="bg-[#0A0A0B] border border-border-subtle chamfer-8 overflow-hidden">
          <table className="w-full text-left">
            <thead>
              <tr className="border-b border-border-subtle">
                {['Crew Member', 'Type', 'Shift Date', 'Reason', 'Submitted', 'Status'].map(h => (
                  <th key={h} className="px-4 py-3 text-micro uppercase tracking-widest text-zinc-500">{h}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {filtered.map(swap => (
                <tr key={swap.id} className="border-b border-border-subtle hover:bg-zinc-950/[0.02]">
                  <td className="px-4 py-3 text-sm font-semibold text-zinc-100">{swap.requester_name || '—'}</td>
                  <td className="px-4 py-3 text-sm text-zinc-400 capitalize">{swap.request_type}</td>
                  <td className="px-4 py-3 text-sm font-mono text-zinc-400">
                    {swap.shift_date ? new Date(swap.shift_date).toLocaleDateString() : '—'}
                  </td>
                  <td className="px-4 py-3 text-sm text-zinc-500 max-w-xs truncate">{swap.reason || '—'}</td>
                  <td className="px-4 py-3 text-xs font-mono text-zinc-500">
                    {swap.submitted_at ? new Date(swap.submitted_at).toLocaleDateString() : '—'}
                  </td>
                  <td className="px-4 py-3">
                    <span className={`text-xs font-semibold px-2 py-0.5 chamfer-4 border ${
                      swap.state === 'PENDING' ? 'bg-yellow-900/30 border-yellow-500/40 text-yellow-300' :
                      swap.state === 'APPROVED' ? 'bg-green-900/30 border-green-500/40 text-green-300' :
                      swap.state === 'DENIED' ? 'bg-red-900/30 border-red-500/40 text-red-300' :
                      'bg-zinc-900/50 border-gray-600 text-zinc-500'
                    }`}>
                      {swap.state}
                    </span>
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

// ── AI Drafts View ────────────────────────────────────────────────────────────

function AIDraftsView({
  drafts,
  onApprove,
  onGenerate,
}: {
  drafts: AIDraft[];
  onApprove: (_draftId: string) => Promise<void>;
  onGenerate: () => Promise<void>;
}) {
  const [generating, setGenerating] = useState(false);
  const [approvingId, setApprovingId] = useState<string | null>(null);

  async function handleGenerate() {
    setGenerating(true);
    try { await onGenerate(); } finally { setGenerating(false); }
  }

  async function handleApprove(draftId: string) {
    setApprovingId(draftId);
    try { await onApprove(draftId); } finally { setApprovingId(null); }
  }

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <div>
          <div className="text-sm text-zinc-400">AI-generated schedule drafts — review completeness scores before approving</div>
          <div className="text-micro text-zinc-500 mt-0.5">Drafts are generated by GPT-4o-mini and require human approval before publishing</div>
        </div>
        <button
          onClick={handleGenerate}
          disabled={generating}
          className="quantum-btn-primary disabled:opacity-50"
        >
          {generating ? 'Generating…' : '+ Generate Draft'}
        </button>
      </div>

      <div className="grid grid-cols-3 gap-3">
        {[
          { label: 'Pending Review', value: drafts.filter(d => d.state === 'PENDING').length },
          { label: 'Approved This Cycle', value: drafts.filter(d => d.state === 'APPROVED').length },
          { label: 'Total Drafts', value: drafts.length },
        ].map(m => (
          <div key={m.label} className="bg-[#0A0A0B] border border-border-subtle chamfer-8 px-4 py-3">
            <div className="text-2xl font-black text-zinc-100">{m.value}</div>
            <div className="text-micro text-zinc-500 mt-0.5">{m.label}</div>
          </div>
        ))}
      </div>

      {drafts.length === 0 ? (
        <QuantumEmptyState title="No AI drafts" description="Generate a draft to get started. AI will propose optimal shift coverage based on historical patterns." icon="sparkles" />
      ) : (
        <div className="bg-[#0A0A0B] border border-border-subtle chamfer-8 overflow-hidden">
          <table className="w-full text-left">
            <thead>
              <tr className="border-b border-border-subtle">
                {['Draft ID', 'Horizon', 'Generated', 'Shifts', 'Score', 'Status', 'Action'].map(h => (
                  <th key={h} className="px-4 py-3 text-micro uppercase tracking-widest text-zinc-500">{h}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {drafts.map(draft => (
                <tr key={draft.id} className="border-b border-border-subtle hover:bg-zinc-950/[0.02]">
                  <td className="px-4 py-3 text-xs font-mono text-zinc-500">{draft.id.slice(0, 12)}</td>
                  <td className="px-4 py-3 text-sm text-zinc-400">{draft.horizon_days ?? '—'}d</td>
                  <td className="px-4 py-3 text-xs font-mono text-zinc-500">
                    {draft.generated_at ? new Date(draft.generated_at).toLocaleString() : '—'}
                  </td>
                  <td className="px-4 py-3 text-sm text-zinc-400">{draft.shifts_count ?? '—'}</td>
                  <td className="px-4 py-3">
                    {draft.score != null ? (
                      <div className="flex items-center gap-2">
                        <div className="w-16 h-1.5 bg-zinc-950/10  overflow-hidden">
                          <div className={`h-full  ${draft.score >= 80 ? 'bg-green-500' : draft.score >= 60 ? 'bg-yellow-500' : 'bg-red-500'}`}
                               style={{ width: `${draft.score}%` }} />
                        </div>
                        <span className="text-micro text-zinc-500">{draft.score}%</span>
                      </div>
                    ) : '—'}
                  </td>
                  <td className="px-4 py-3">
                    <span className={`text-xs font-semibold px-2 py-0.5 chamfer-4 border ${
                      draft.state === 'PENDING' ? 'bg-yellow-900/30 border-yellow-500/40 text-yellow-300' :
                      draft.state === 'APPROVED' ? 'bg-green-900/30 border-green-500/40 text-green-300' :
                      'bg-zinc-900/50 border-gray-600 text-zinc-500'
                    }`}>
                      {draft.state}
                    </span>
                  </td>
                  <td className="px-4 py-3">
                    {draft.state === 'PENDING' && (
                      <button
                        onClick={() => handleApprove(draft.id)}
                        disabled={approvingId === draft.id}
                        className="quantum-btn-sm disabled:opacity-50 text-green-400 border-green-500/40 hover:bg-green-500/10"
                      >
                        {approvingId === draft.id ? '…' : 'Approve'}
                      </button>
                    )}
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

// ── Credential Alerts Strip ───────────────────────────────────────────────────

function CredentialStrip({ creds }: { creds: ExpiringCredential[] }) {
  if (creds.length === 0) return null;
  return (
    <div className="bg-yellow-900/20 border border-yellow-500/30 chamfer-8 p-3 mb-4 flex items-center gap-3 flex-wrap">
      <span className="text-micro font-bold text-yellow-400 flex-shrink-0">⚡ Expiring Credentials:</span>
      {creds.slice(0, 6).map((c, i) => (
        <span key={i} className={`text-micro px-2 py-1 chamfer-4 border ${
          (c.days_until_expiry ?? 999) <= 0 ? 'bg-red-900/30 border-red-500/40 text-red-300' :
          (c.days_until_expiry ?? 999) <= 14 ? 'bg-[rgba(255,77,0,0.3)] border-orange-500/40 text-[#FF9A66]' :
          'bg-yellow-900/30 border-yellow-500/40 text-yellow-300'
        }`}>
          {c.crew_member_name} · {c.cert_type}{c.days_until_expiry != null ? ` (${c.days_until_expiry <= 0 ? 'EXPIRED' : `${c.days_until_expiry}d`})` : ''}
        </span>
      ))}
    </div>
  );
}

// ── Page ──────────────────────────────────────────────────────────────────────

type ActiveView = 'calendar' | 'requests' | 'coverage' | 'ai_drafts';

export default function SchedulingPage() {
  const [activeView, setActiveView] = useState<ActiveView>('calendar');
  const [shifts, setShifts] = useState<ShiftInstance[]>([]);
  const [swaps, setSwaps] = useState<SwapRequest[]>([]);
  const [coverage, setCoverage] = useState<CoverageDashboard>({});
  const [drafts, setDrafts] = useState<AIDraft[]>([]);
  const [fatigue, setFatigue] = useState<FatigueReport | null>(null);
  const [expiringCreds, setExpiringCreds] = useState<ExpiringCredential[]>([]);
  const [loading, setLoading] = useState(true);
  const [weekOffset, setWeekOffset] = useState(0);

  const loadData = useCallback(async () => {
    setLoading(true);
    try {
      const [shiftData, swapData, covData, credData] = await Promise.all([
        listShiftInstances().catch(() => []),
        listSchedulingSwaps().catch(() => []),
        getSchedulingCoverageDashboard().catch(() => ({})),
        getExpiringCredentials().catch(() => []),
      ]);
      setShifts(Array.isArray(shiftData) ? shiftData : shiftData?.shifts || []);
      setSwaps(Array.isArray(swapData) ? swapData : swapData?.swaps || []);
      setCoverage(covData || {});
      setExpiringCreds(Array.isArray(credData) ? credData : credData?.credentials || []);
    } finally {
      setLoading(false);
    }
  }, []);

  const loadViewData = useCallback(async (view: ActiveView) => {
    if (view === 'ai_drafts') {
      const data = await getSchedulingAIDrafts().catch(() => []);
      setDrafts(Array.isArray(data) ? data : data?.drafts || []);
    }
    if (view === 'coverage') {
      const data = await getSchedulingFatigueReport().catch(() => null);
      setFatigue(data);
    }
  }, []);

  useEffect(() => { loadData(); }, [loadData]);
  useEffect(() => { loadViewData(activeView); }, [activeView, loadViewData]);

  async function handleApprove(draftId: string) {
    await approveSchedulingAIDraft(draftId);
    const data = await getSchedulingAIDrafts().catch(() => []);
    setDrafts(Array.isArray(data) ? data : data?.drafts || []);
  }

  async function handleGenerate() {
    await requestSchedulingAIDraft({ horizon_days: 14 });
    const data = await getSchedulingAIDrafts().catch(() => []);
    setDrafts(Array.isArray(data) ? data : data?.drafts || []);
  }

  const today = new Date();
  const startOfWeek = new Date(today);
  startOfWeek.setDate(today.getDate() - today.getDay() + weekOffset * 7);
  const endOfWeek = new Date(startOfWeek);
  endOfWeek.setDate(startOfWeek.getDate() + 6);
  const fmt = (d: Date) => d.toLocaleDateString('en-US', { month: 'short', day: 'numeric' });

  const weekShifts = shifts.filter(s => {
    const d = new Date(s.start_time);
    return d >= startOfWeek && d <= endOfWeek;
  });

  return (
    <div className="flex flex-col bg-black min-h-screen">
      {/* Header */}
      <div className="flex-shrink-0 border-b border-border-subtle bg-[#0A0A0B]/50 px-5 py-4">
        <div className="flex items-center justify-between">
          <div>
            <div className="text-xs font-black text-zinc-100 uppercase tracking-widest">Scheduling Command</div>
            <div className="text-micro text-zinc-500">Shift calendar · Swap requests · Coverage monitoring · AI drafts · Fatigue tracking</div>
          </div>
          <div className="flex items-center gap-2">
            {expiringCreds.length > 0 && (
              <div className="text-micro text-yellow-400 border border-yellow-500/30 chamfer-4 px-3 py-1.5">
                ⚡ {expiringCreds.length} expiring cred{expiringCreds.length > 1 ? 's' : ''}
              </div>
            )}
          </div>
        </div>

        <div className="grid grid-cols-4 gap-3 mt-4">
          {[
            { label: "This Week's Shifts", value: weekShifts.length.toString(), color: 'text-zinc-100' },
            { label: 'Active Swaps Pending', value: swaps.filter(s => s.state === 'PENDING').length.toString(), color: swaps.filter(s => s.state === 'PENDING').length > 0 ? 'text-yellow-400' : 'text-zinc-500' },
            { label: 'Coverage %', value: `${Math.round(coverage.coverage_pct ?? 0)}%`, color: (coverage.coverage_pct ?? 0) >= 80 ? 'text-green-400' : 'text-red-400' },
            { label: 'AI Drafts Pending', value: drafts.filter(d => d.state === 'PENDING').length.toString(), color: 'text-blue-400' },
          ].map(m => (
            <div key={m.label} className="bg-[#0A0A0B] border border-border-subtle chamfer-8 px-4 py-3">
              <div className={`text-2xl font-black ${m.color}`}>{m.value}</div>
              <div className="text-micro text-zinc-500 mt-0.5">{m.label}</div>
            </div>
          ))}
        </div>

        <div className="flex items-center gap-1 mt-4">
          {(['calendar', 'requests', 'coverage', 'ai_drafts'] as const).map(v => (
            <button
              key={v}
              onClick={() => setActiveView(v)}
              className={`px-4 py-2 text-micro font-semibold border-b-2 transition-colors ${
                activeView === v ? 'border-brand-orange text-brand-orange' : 'border-transparent text-zinc-500 hover:text-zinc-400'
              }`}
            >
              {v === 'calendar' ? 'Shift Calendar' : v === 'requests' ? 'Swap Requests' : v === 'coverage' ? 'Coverage' : 'AI Drafts'}
            </button>
          ))}
        </div>
      </div>

      {/* Content */}
      <div className="flex-1 p-5">
        {loading ? (
          <QuantumTableSkeleton rows={6} />
        ) : activeView === 'calendar' ? (
          <div className="space-y-4">
            <CredentialStrip creds={expiringCreds} />
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2">
                <button onClick={() => setWeekOffset(w => w - 1)} className="quantum-btn-sm">‹</button>
                <span className="text-sm font-semibold text-zinc-100 min-w-[160px] text-center">
                  {fmt(startOfWeek)} — {fmt(endOfWeek)}
                </span>
                <button onClick={() => setWeekOffset(w => w + 1)} className="quantum-btn-sm">›</button>
                <button onClick={() => setWeekOffset(0)} className="quantum-btn-sm text-zinc-500">Today</button>
              </div>
              <div className="text-micro text-zinc-500">{weekShifts.length} shift{weekShifts.length !== 1 ? 's' : ''} this week</div>
            </div>
            <WeekCalendar shifts={weekShifts} weekOffset={weekOffset} />
          </div>
        ) : activeView === 'requests' ? (
          <SwapRequestsView swaps={swaps} onRefresh={loadData} />
        ) : activeView === 'coverage' ? (
          <CoverageView coverage={coverage} fatigue={fatigue} />
        ) : (
          <AIDraftsView drafts={drafts} onApprove={handleApprove} onGenerate={handleGenerate} />
        )}
      </div>
    </div>
  );
}
