'use client';

import React, { useEffect, useState, useCallback, useRef } from 'react';
import { ModuleDashboardShell } from '@/components/shells/PageShells';
import {
  AIExplanationCard,
  MetricCard,
  QuantumTableSkeleton,
  QuantumEmptyState,
  SeverityBadge,
  SimpleModeSummary,
  StatusChip,
} from '@/components/ui';
import type { SeverityLevel, StatusVariant } from '@/lib/design-system/tokens';
import { CadLiveMap } from '@/components/CadLiveMap';
import {
  getActiveCADCalls,
  listCADUnitsWithLatestLocations,
  transitionCADCall,
  assignCADUnit,
  createCADCall,
} from '@/services/api';
import type { RealtimeEvent } from '@/services/websocket';
import { getWSClient } from '@/services/websocket';

// ── Types ────────────────────────────────────────────────────────────────────

type CallState =
  | 'NEW' | 'TRIAGED' | 'DISPATCHED' | 'ENROUTE'
  | 'ON_SCENE' | 'TRANSPORTING' | 'AT_HOSPITAL' | 'CLEARED' | 'CLOSED' | 'CANCELLED';

interface CADCall {
  id: string;
  call_number: string;
  state: CallState;
  priority: string;
  chief_complaint: string;
  address: string;
  location_address?: string;
  call_received_at: string;
  caller_name?: string;
  caller_phone?: string;
  triage_notes?: string;
  assigned_unit?: string;
  latitude?: number;
  longitude?: number;
}

interface CADUnit {
  id: string;
  unit_name: string;
  unit_type: string;
  state: string;
  station: string;
  lat: number | null;
  lng: number | null;
  readiness_score: number | null;
  active_call_id?: string | null;
}

// ── Constants ─────────────────────────────────────────────────────────────────

const PRIORITY_CONFIG: Record<string, {
  label: string; bg: string; border: string; text: string;
  ring: string; sortOrder: number;
}> = {
  ECHO:   { label: 'E', bg: 'bg-red-900/40',     border: 'border-[var(--color-brand-red)]',     text: 'text-[var(--color-brand-red)]',    ring: 'shadow-red-500/40',    sortOrder: 5 },
  DELTA:  { label: 'D', bg: 'bg-[rgba(255,106,0,0.4)]', border: 'border-orange-500',  text: 'text-[#FF9A66]', ring: 'shadow-orange-500/40', sortOrder: 4 },
  CHARLIE:{ label: 'C', bg: 'bg-yellow-900/40',   border: 'border-yellow-500',  text: 'text-yellow-300', ring: 'shadow-yellow-500/40', sortOrder: 3 },
  BRAVO:  { label: 'B', bg: 'bg-blue-900/40',     border: 'border-[var(--color-status-info)]',    text: 'text-[var(--color-status-info)]',   ring: 'shadow-blue-500/40',   sortOrder: 2 },
  ALPHA:  { label: 'A', bg: 'bg-green-900/40',    border: 'border-[var(--color-status-active)]',   text: 'text-[var(--color-status-active)]',  ring: 'shadow-green-500/40',  sortOrder: 1 },
  OMEGA:  { label: 'Ω', bg: 'bg-[var(--color-bg-panel)]/50',     border: 'border-gray-600',    text: 'text-[var(--color-text-muted)]',   ring: '',                     sortOrder: 0 },
};

const PRIORITY_SEVERITY_MAP: Record<string, SeverityLevel> = {
  ECHO: 'BLOCKING',
  DELTA: 'HIGH',
  CHARLIE: 'MEDIUM',
  BRAVO: 'LOW',
  ALPHA: 'INFORMATIONAL',
  OMEGA: 'INFORMATIONAL',
};

const STATE_TRANSITIONS: Record<CallState, CallState | null> = {
  NEW: 'TRIAGED', TRIAGED: 'DISPATCHED', DISPATCHED: 'ENROUTE',
  ENROUTE: 'ON_SCENE', ON_SCENE: 'TRANSPORTING', TRANSPORTING: 'AT_HOSPITAL',
  AT_HOSPITAL: 'CLEARED', CLEARED: 'CLOSED', CLOSED: null, CANCELLED: null,
};

const CALL_STATE_STATUS_MAP: Record<CallState, StatusVariant> = {
  NEW: 'info',
  TRIAGED: 'review',
  DISPATCHED: 'warning',
  ENROUTE: 'warning',
  ON_SCENE: 'warning',
  TRANSPORTING: 'warning',
  AT_HOSPITAL: 'info',
  CLEARED: 'active',
  CLOSED: 'neutral',
  CANCELLED: 'critical',
};

const STATE_LABEL: Record<CallState, string> = {
  NEW: 'New', TRIAGED: 'Triaged', DISPATCHED: 'Dispatched', ENROUTE: 'En Route',
  ON_SCENE: 'On Scene', TRANSPORTING: 'Transporting', AT_HOSPITAL: 'At Hospital',
  CLEARED: 'Cleared', CLOSED: 'Closed', CANCELLED: 'Cancelled',
};

const NEXT_ACTION_LABEL: Record<string, string> = {
  NEW: 'Triage', TRIAGED: 'Dispatch', DISPATCHED: 'Mark En Route',
  ENROUTE: 'On Scene', ON_SCENE: 'Begin Transport', TRANSPORTING: 'At Hospital',
  AT_HOSPITAL: 'Clear Unit', CLEARED: 'Close Call',
};

const UNIT_STATE_STATUS_MAP: Record<string, StatusVariant> = {
  AVAILABLE: 'active',
  DISPATCHED: 'warning',
  ENROUTE: 'warning',
  ON_SCENE: 'warning',
  TRANSPORTING: 'warning',
  AT_HOSPITAL: 'info',
  OUT_OF_SERVICE: 'critical',
  OFF_DUTY: 'neutral',
};

function getReadinessSeverity(readiness: number): SeverityLevel {
  if (readiness < 50) return 'HIGH';
  if (readiness < 80) return 'MEDIUM';
  return 'INFORMATIONAL';
}

// ── Elapsed Timer ─────────────────────────────────────────────────────────────

function ElapsedTimer({ startTime, critical }: { startTime: string; critical?: number }) {
  const [elapsed, setElapsed] = useState('');
  const intervalRef = useRef<ReturnType<typeof setInterval> | null>(null);

  useEffect(() => {
    const update = () => {
      const ms = Date.now() - new Date(startTime).getTime();
      const s = Math.floor(ms / 1000);
      const m = Math.floor(s / 60);
      const h = Math.floor(m / 60);
      if (h > 0) setElapsed(`${h}h ${m % 60}m`);
      else if (m > 0) setElapsed(`${m}m ${s % 60}s`);
      else setElapsed(`${s}s`);
    };
    update();
    intervalRef.current = setInterval(update, 1000);
    return () => { if (intervalRef.current) clearInterval(intervalRef.current); };
  }, [startTime]);

  const ms = Date.now() - new Date(startTime).getTime();
  const minutes = ms / 60000;
  const isCritical = critical !== undefined && minutes >= critical;

  return (
    <span className={`font-mono text-xs font-bold ${isCritical ? 'text-[var(--color-brand-red)] animate-pulse' : minutes > 8 ? 'text-[#FF7A33]' : 'text-[var(--color-text-muted)]'}`}>
      {elapsed}
    </span>
  );
}

// ── Active Call Card ──────────────────────────────────────────────────────────

interface CallCardProps {
  call: CADCall;
  isSelected: boolean;
  onSelect: () => void;
  onTransition: (_state: string) => void;
  units: CADUnit[];
  onAssign: (_unitId: string) => void;
}

function CallCard({ call, isSelected, onSelect, onTransition, units, onAssign }: CallCardProps) {
  const cfg = PRIORITY_CONFIG[call.priority] || PRIORITY_CONFIG.ALPHA;
  const nextState = STATE_TRANSITIONS[call.state];
  const availableUnits = units.filter(u => u.state === 'AVAILABLE');
  const [assignOpen, setAssignOpen] = useState(false);
  const PROGRESS_STATES: CallState[] = ['NEW','TRIAGED','DISPATCHED','ENROUTE','ON_SCENE','TRANSPORTING','AT_HOSPITAL','CLEARED'];
  const currentIdx = PROGRESS_STATES.indexOf(call.state);

  return (
    <div
      onClick={onSelect}
      className={`relative border chamfer-8 p-4 cursor-pointer transition-all ${cfg.bg} ${cfg.border} ${
        isSelected ? `shadow-[0_0_15px_rgba(0,0,0,0.6)] ring-1 ring-inset ring-white/5` : 'hover:brightness-110'
      }`}
    >
      {/* Priority Badge + Call # + Elapsed */}
      <div className="flex items-center justify-between mb-2">
        <div className="flex items-center gap-2">
          <span
            className={`w-8 h-8 flex items-center justify-center font-black text-sm border ${cfg.border} ${cfg.text} bg-[var(--color-bg-base)]/30`}
            style={{ clipPath: 'polygon(0 0, calc(100% - 4px) 0, 100% 4px, 100% 100%, 0 100%)' }}
          >
            {cfg.label}
          </span>
          <div>
            <div className="text-sm font-bold text-[var(--color-text-primary)]">#{call.call_number}</div>
            <div className="flex items-center gap-2 mt-0.5">
              <span className={`text-micro font-semibold ${cfg.text}`}>{call.priority}</span>
              <SeverityBadge severity={PRIORITY_SEVERITY_MAP[call.priority] ?? 'INFORMATIONAL'} size="sm" />
            </div>
          </div>
        </div>
        <div className="text-right">
          <ElapsedTimer
            startTime={call.call_received_at}
            critical={call.priority === 'ECHO' ? 4 : call.priority === 'DELTA' ? 8 : 15}
          />
          <div className="text-micro text-[var(--color-text-muted)] mt-0.5">elapsed</div>
        </div>
      </div>

      {/* Complaint + Address */}
      <div className="mb-2">
        <div className="text-sm font-semibold text-[var(--color-text-primary)]">{call.chief_complaint || 'No complaint noted'}</div>
        <div className="text-micro text-[var(--color-text-muted)] mt-0.5 truncate mb-1.5">
          📍 {call.address || call.location_address || 'Address pending'}
        </div>
        <StatusChip status={CALL_STATE_STATUS_MAP[call.state]} size="sm">
          {STATE_LABEL[call.state]}
        </StatusChip>
      </div>

      {/* State progress bar */}
      <div className="flex items-center gap-1 mb-3">
        {PROGRESS_STATES.map((s, idx) => {
          const activeBg = cfg.text.replace('text-','bg-').replace('-300','-500');
          const currentBg = cfg.text.replace('text-','bg-').replace('-300','-400');
          return (
            <div
              key={s}
              title={STATE_LABEL[s]}
              className={`h-1 flex-1  transition-all ${
                idx < currentIdx ? `${activeBg} opacity-80` :
                idx === currentIdx ? currentBg :
                'bg-[var(--color-bg-base)]/10'
              }`}
            />
          );
        })}
      </div>

      {/* Expanded details */}
      {isSelected && (
        <div className="border-t border-white/10 pt-3 mt-1 space-y-2">
          {call.caller_name && (
            <div className="text-sm text-[var(--color-text-secondary)]">
              📞 {call.caller_name}{call.caller_phone ? ` · ${call.caller_phone}` : ''}
            </div>
          )}
          {call.triage_notes && (
            <div className="text-xs text-[var(--color-text-muted)] bg-[var(--color-bg-base)]/20 chamfer-4 p-2">{call.triage_notes}</div>
          )}
          {call.assigned_unit && (
            <div className="text-xs text-[var(--color-text-secondary)]">
              🚑 Assigned: <span className="font-semibold text-[var(--color-text-primary)]">{call.assigned_unit}</span>
            </div>
          )}
        </div>
      )}

      {/* Action Buttons */}
      <div className="flex items-center gap-2 mt-3" onClick={e => e.stopPropagation()}>
        {nextState && NEXT_ACTION_LABEL[call.state] && (
          <button
            onClick={() => onTransition(nextState)}
            className={`px-3 py-1.5 text-micro font-bold uppercase border ${cfg.border} ${cfg.text} bg-[var(--color-bg-base)]/20 hover:bg-[var(--color-bg-base)]/40 transition-colors chamfer-4`}
          >
            {NEXT_ACTION_LABEL[call.state]} →
          </button>
        )}
        {(call.state === 'NEW' || call.state === 'TRIAGED') && (
          <div className="relative">
            <button
              onClick={() => setAssignOpen(o => !o)}
              className="px-3 py-1.5 text-micro font-bold uppercase border border-brand-orange/40 text-brand-orange bg-brand-orange/10 hover:bg-brand-orange/20 transition-colors chamfer-4"
            >
              Assign {availableUnits.length > 0 ? `(${availableUnits.length})` : '—'}
            </button>
            {assignOpen && availableUnits.length > 0 && (
              <div className="absolute bottom-full left-0 mb-1 w-48 bg-[var(--color-bg-base)] border border-border-subtle chamfer-8 z-50 shadow-[0_0_15px_rgba(0,0,0,0.6)]">
                {availableUnits.map(u => (
                  <button
                    key={u.id}
                    onClick={() => { onAssign(u.id); setAssignOpen(false); }}
                    className="w-full text-left px-3 py-2 text-xs text-[var(--color-text-secondary)] hover:bg-brand-orange/10 hover:text-brand-orange transition-colors border-b border-border-subtle last:border-0"
                  >
                    <span className="font-bold text-[var(--color-text-primary)]">{u.unit_name}</span>
                    <span className="text-[var(--color-text-muted)] ml-2">{u.unit_type}</span>
                  </button>
                ))}
              </div>
            )}
          </div>
        )}
        <button
          onClick={() => onTransition('CANCELLED')}
          className="ml-auto px-2 py-1.5 text-micro text-[var(--color-text-muted)] hover:text-[var(--color-brand-red)] transition-colors"
          title="Cancel call"
        >
          ✕
        </button>
      </div>
    </div>
  );
}

// ── New Call Form ─────────────────────────────────────────────────────────────

interface NewCallFormProps {
  onClose: () => void;
  onCreated: () => void;
}

function NewCallForm({ onClose, onCreated }: NewCallFormProps) {
  const [form, setForm] = useState({
    caller_name: '', caller_phone: '', location_address: '',
    chief_complaint: '', priority: 'ALPHA', triage_notes: '',
  });
  const [submitting, setSubmitting] = useState(false);

  const handleSubmit = async () => {
    setSubmitting(true);
    try {
      await createCADCall(form);
      onCreated();
      onClose();
    } catch (err) {
      console.error('Failed to create CAD call', err);
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-[var(--color-bg-base)]/80" onClick={onClose}>
      <div className="bg-[var(--color-bg-base)] border border-brand-orange/40 chamfer-16 p-6 w-full max-w-lg" onClick={e => e.stopPropagation()}>
        <div className="flex items-center justify-between mb-5">
          <div>
            <h2 className="text-base font-black text-[var(--color-text-primary)] uppercase tracking-wider">New CAD Call</h2>
            <div className="text-micro text-[var(--color-text-muted)]">All fields captured for NEMSIS compliance</div>
          </div>
          <button onClick={onClose} className="text-[var(--color-text-muted)] hover:text-[var(--color-text-primary)]">✕</button>
        </div>
        <div className="space-y-3">
          <div>
            <label className="block text-micro text-[var(--color-text-muted)] mb-1 uppercase tracking-wider">PRIORITY *</label>
            <div className="flex gap-2">
              {(['ECHO','DELTA','CHARLIE','BRAVO','ALPHA'] as const).map(prio => {
                const cfg = PRIORITY_CONFIG[prio];
                return (
                  <button
                    key={prio}
                    onClick={() => setForm(f => ({ ...f, priority: prio }))}
                    className={`flex-1 py-2 text-xs font-black uppercase border transition-all chamfer-4 ${
                      form.priority === prio
                        ? `${cfg.bg} ${cfg.border} ${cfg.text}`
                        : 'border-border-subtle text-[var(--color-text-muted)] hover:border-white/20'
                    }`}
                  >
                    {prio}
                  </button>
                );
              })}
            </div>
          </div>
          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="block text-micro text-[var(--color-text-muted)] mb-1 uppercase tracking-wider">CALLER NAME</label>
              <input
                value={form.caller_name}
                onChange={e => setForm(f => ({ ...f, caller_name: e.target.value }))}
                className="w-full bg-[var(--color-bg-panel)] border border-border-subtle chamfer-4 px-3 py-2 text-sm text-[var(--color-text-primary)] focus:outline-none focus:border-brand-orange/60"
                placeholder="Jane Smith"
              />
            </div>
            <div>
              <label className="block text-micro text-[var(--color-text-muted)] mb-1 uppercase tracking-wider">CALLER PHONE</label>
              <input
                value={form.caller_phone}
                onChange={e => setForm(f => ({ ...f, caller_phone: e.target.value }))}
                className="w-full bg-[var(--color-bg-panel)] border border-border-subtle chamfer-4 px-3 py-2 text-sm text-[var(--color-text-primary)] focus:outline-none focus:border-brand-orange/60"
                placeholder="(555) 000-0000"
              />
            </div>
          </div>
          <div>
            <label className="block text-micro text-[var(--color-text-muted)] mb-1 uppercase tracking-wider">LOCATION ADDRESS *</label>
            <input
              value={form.location_address}
              onChange={e => setForm(f => ({ ...f, location_address: e.target.value }))}
              className="w-full bg-[var(--color-bg-panel)] border border-border-subtle chamfer-4 px-3 py-2 text-sm text-[var(--color-text-primary)] focus:outline-none focus:border-brand-orange/60"
              placeholder="123 Main St, Anytown, WI 53703"
            />
          </div>
          <div>
            <label className="block text-micro text-[var(--color-text-muted)] mb-1 uppercase tracking-wider">CHIEF COMPLAINT *</label>
            <input
              value={form.chief_complaint}
              onChange={e => setForm(f => ({ ...f, chief_complaint: e.target.value }))}
              className="w-full bg-[var(--color-bg-panel)] border border-border-subtle chamfer-4 px-3 py-2 text-sm text-[var(--color-text-primary)] focus:outline-none focus:border-brand-orange/60"
              placeholder="Chest pain, difficulty breathing…"
            />
          </div>
          <div>
            <label className="block text-micro text-[var(--color-text-muted)] mb-1 uppercase tracking-wider">EMD TRIAGE NOTES</label>
            <textarea
              value={form.triage_notes}
              onChange={e => setForm(f => ({ ...f, triage_notes: e.target.value }))}
              rows={2}
              className="w-full bg-[var(--color-bg-panel)] border border-border-subtle chamfer-4 px-3 py-2 text-sm text-[var(--color-text-primary)] focus:outline-none focus:border-brand-orange/60 resize-none"
              placeholder="Patient is conscious and breathing, denies prior cardiac history…"
            />
          </div>
          <div className="flex gap-3 pt-2">
            <button onClick={onClose} className="flex-1 quantum-btn-sm py-2">Cancel</button>
            <button
              onClick={handleSubmit}
              disabled={submitting || !form.location_address || !form.chief_complaint}
              className="flex-1 quantum-btn-primary py-2 text-sm font-bold disabled:opacity-50"
            >
              {submitting ? 'Creating…' : '🚨 Create Call'}
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}

// ── Unit Status Board ─────────────────────────────────────────────────────────

function UnitBoard({ units }: { units: CADUnit[] }) {
  const byStation = units.reduce<Record<string, CADUnit[]>>((acc, u) => {
    const station = u.station || 'Unassigned';
    if (!acc[station]) acc[station] = [];
    acc[station].push(u);
    return acc;
  }, {});

  const available = units.filter(u => u.state === 'AVAILABLE').length;
  const busy = units.filter(u => !['AVAILABLE','OFF_DUTY','OUT_OF_SERVICE'].includes(u.state)).length;
  const oos = units.filter(u => u.state === 'OUT_OF_SERVICE').length;

  return (
    <div className="space-y-3">
      <div className="grid grid-cols-3 gap-2">
        <div className="bg-green-900/20 border border-[var(--color-status-active)]/30 chamfer-8 p-2 text-center">
          <div className="text-xl font-black text-[var(--color-status-active)]">{available}</div>
          <div className="text-micro text-[var(--color-text-muted)]">Available</div>
        </div>
        <div className="bg-[rgba(255,106,0,0.2)] border border-orange-500/30 chamfer-8 p-2 text-center">
          <div className="text-xl font-black text-[#FF7A33]">{busy}</div>
          <div className="text-micro text-[var(--color-text-muted)]">Committed</div>
        </div>
        <div className="bg-[var(--color-bg-panel)]/30 border border-gray-600/30 chamfer-8 p-2 text-center">
          <div className="text-xl font-black text-[var(--color-text-muted)]">{oos}</div>
          <div className="text-micro text-[var(--color-text-muted)]">OOS</div>
        </div>
      </div>
      {Object.entries(byStation).map(([station, stationUnits]) => (
        <div key={station} className="bg-[var(--color-bg-panel)] border border-border-subtle chamfer-8 overflow-hidden">
          <div className="px-3 py-2 border-b border-border-subtle flex items-center justify-between">
            <span className="text-micro font-bold text-[var(--color-text-muted)] uppercase tracking-widest">{station}</span>
            <span className="text-micro text-[var(--color-text-muted)]">
              {stationUnits.filter(u => u.state === 'AVAILABLE').length}/{stationUnits.length} avail
            </span>
          </div>
          <div className="divide-y divide-border-subtle">
            {stationUnits.map(unit => {
              const statusVariant = UNIT_STATE_STATUS_MAP[unit.state] ?? 'neutral';
              const readinessPct = unit.readiness_score != null ? Math.round(unit.readiness_score * 100) : null;
              return (
                <div key={unit.id} className="px-3 py-2 flex items-center justify-between hover:bg-[var(--color-bg-base)]/[0.02]">
                  <div className="flex items-center gap-2">
                    <div>
                      <div className="text-sm font-bold text-[var(--color-text-primary)]">{unit.unit_name}</div>
                      <div className="text-micro text-[var(--color-text-muted)]">{unit.unit_type}</div>
                    </div>
                  </div>
                  <div className="text-right">
                    <StatusChip status={statusVariant} size="sm">{unit.state.replace(/_/g,' ')}</StatusChip>
                    {readinessPct != null && (
                      <div className="mt-1">
                        <SeverityBadge severity={getReadinessSeverity(readinessPct)} size="sm" label={`${readinessPct}% ready`} />
                      </div>
                    )}
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      ))}
      {units.length === 0 && (
        <div className="text-center py-6 text-sm text-[var(--color-text-muted)]">
          No units registered. Add units through Fleet Management.
        </div>
      )}
    </div>
  );
}

// ── Page ─────────────────────────────────────────────────────────────────────

export default function CADDispatchPage() {
  const [calls, setCalls] = useState<CADCall[]>([]);
  const [units, setUnits] = useState<CADUnit[]>([]);
  const [loading, setLoading] = useState(true);
  const [loadError, setLoadError] = useState<string | null>(null);
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [showNewCall, setShowNewCall] = useState(false);
  const [activeView, setActiveView] = useState<'dispatch' | 'units' | 'history'>('dispatch');
  const [priorityFilter, setPriorityFilter] = useState<string>('ALL');
  const intervalRef = useRef<ReturnType<typeof setInterval> | null>(null);

  const handleRealtimeEvent = useCallback((event: RealtimeEvent) => {
    if (event.event_type !== 'unit_locations.created' && event.event_type !== 'unit_locations.updated') return;
    const record = (event.payload?.record ?? null) as unknown;
    if (!record || typeof record !== 'object') return;
    const recObj = record as Record<string, unknown>;
    const data = recObj.data as unknown;
    if (!data || typeof data !== 'object') return;
    const dataObj = data as Record<string, unknown>;
    const unitId = typeof dataObj.unit_id === 'string' ? dataObj.unit_id : null;
    if (!unitId) return;
    const points = Array.isArray(dataObj.points) ? (dataObj.points as unknown[]) : null;
    const first = points && points.length > 0 ? (points[0] as Record<string, unknown>) : null;
    const lat = first && typeof first.lat === 'number' ? first.lat : null;
    const lng = first && typeof first.lng === 'number' ? first.lng : null;
    if (lat == null || lng == null) return;

    setUnits((prev) => prev.map((u) => (u.id === unitId ? { ...u, lat, lng } : u)));
  }, []);

  const refresh = useCallback(async () => {
    setLoadError(null);
    let anyFailed = false;
    try {
      const [callData, unitData] = await Promise.all([
        getActiveCADCalls().catch((err) => { anyFailed = true; console.error('[CAD] calls load failed:', err); return [] as CADCall[]; }),
        listCADUnitsWithLatestLocations().catch((err) => { anyFailed = true; console.error('[CAD] units load failed:', err); return [] as CADUnit[]; }),
      ]);
      if (anyFailed) {
        setLoadError('Some CAD data failed to load — displayed calls or units may be incomplete. Refresh immediately.');
      }
      setCalls(callData as CADCall[]);
      setUnits(unitData as CADUnit[]);
    } catch (err) {
      setLoadError('CAD data failed to load. Please refresh immediately.');
      console.error('[CAD] refresh failed:', err);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    refresh();
    intervalRef.current = setInterval(refresh, 10_000);
    return () => { if (intervalRef.current) clearInterval(intervalRef.current); };
  }, [refresh]);

  useEffect(() => {
    let detach: (() => void) | null = null;
    const tryAttach = () => {
      if (detach) return;
      const client = getWSClient();
      if (!client) return;
      detach = client.addHandler(handleRealtimeEvent);
    };

    tryAttach();
    const timer = setInterval(tryAttach, 500);
    return () => {
      clearInterval(timer);
      detach?.();
    };
  }, [handleRealtimeEvent]);

  const handleTransition = async (callId: string, state: string) => {
    try {
      await transitionCADCall(callId, { state });
      await refresh();
    } catch (err) {
      console.error('Transition failed', err);
    }
  };

  const handleAssign = async (callId: string, unitId: string) => {
    try {
      await assignCADUnit(callId, { unit_id: unitId });
      await refresh();
    } catch (err) {
      console.error('Assignment failed', err);
    }
  };

  const sortedCalls = [...calls].sort((a, b) => {
    const pa = PRIORITY_CONFIG[a.priority]?.sortOrder ?? 0;
    const pb = PRIORITY_CONFIG[b.priority]?.sortOrder ?? 0;
    if (pa !== pb) return pb - pa;
    return new Date(a.call_received_at).getTime() - new Date(b.call_received_at).getTime();
  });

  const filtered = priorityFilter === 'ALL' ? sortedCalls : sortedCalls.filter(c => c.priority === priorityFilter);
  const activeCalls = filtered.filter(c => !['CLOSED','CANCELLED'].includes(c.state));
  const historyCalls = filtered.filter(c => ['CLOSED','CANCELLED'].includes(c.state));
  const echoDelta = calls.filter(c => ['ECHO','DELTA'].includes(c.priority) && !['CLOSED','CANCELLED'].includes(c.state)).length;
  const availableUnits = units.filter(u => u.state === 'AVAILABLE').length;
  const blockingCalls = calls.filter(c => c.priority === 'ECHO' && !['CLOSED', 'CANCELLED'].includes(c.state)).length;

  const mapUnits = units
    .filter((u) => u.lat != null && u.lng != null)
    .map((u) => ({
      unit_id: u.id,
      unit_number: u.unit_name,
      lat: u.lat as number,
      lng: u.lng as number,
      status: (u.state || '').toLowerCase(),
    }));

  return (
    <>
      {loadError && (
        <div className="mx-5 mt-4 px-4 py-3 bg-red-900/20 border border-[var(--color-brand-red)]/30 text-[var(--color-brand-red)] text-sm font-medium chamfer-4">
          ⚠ {loadError}
        </div>
      )}
      <ModuleDashboardShell
        title="CAD Dispatch Command"
        subtitle="Live incident orchestration · Unit assignment · Audit-ready dispatch lifecycle"
        accentColor="var(--color-system-cad)"
        headerActions={
          <button onClick={() => setShowNewCall(true)} className="quantum-btn-primary px-4 py-1.5 text-sm font-bold">
            🚨 New Call
          </button>
        }
        kpiStrip={
          <>
            <MetricCard label="Active Calls" value={activeCalls.length} domain="cad" compact />
            <MetricCard label="High Priority" value={echoDelta} domain="cad" compact />
            <MetricCard label="Blocking" value={blockingCalls} domain="cad" compact />
            <MetricCard label="Units Available" value={`${availableUnits}/${units.length}`} domain="cad" compact />
            <MetricCard label="Closed/Cancelled" value={historyCalls.length} domain="cad" compact />
          </>
        }
        toolbar={
          <div className="flex items-center justify-between gap-3 flex-wrap">
            <div className="flex border border-border-subtle chamfer-4 overflow-hidden">
              {(['dispatch','units','history'] as const).map(v => (
                <button
                  key={v}
                  onClick={() => setActiveView(v)}
                  className={`px-3 py-1.5 text-micro font-semibold capitalize transition-colors ${
                    activeView === v ? 'bg-brand-orange text-white' : 'text-[var(--color-text-muted)] hover:text-[var(--color-text-secondary)] hover:bg-[var(--color-bg-base)]/5'
                  }`}
                >
                  {v}
                </button>
              ))}
            </div>
            {activeView === 'dispatch' && (
              <div className="flex items-center gap-2 flex-wrap">
                <span className="text-micro text-[var(--color-text-muted)] mr-1 uppercase tracking-widest">Priority:</span>
                {['ALL','ECHO','DELTA','CHARLIE','BRAVO','ALPHA'].map(p => {
                  const cfg = PRIORITY_CONFIG[p];
                  return (
                    <button
                      key={p}
                      onClick={() => setPriorityFilter(p)}
                      className={`px-2.5 py-1 text-micro font-bold transition-all chamfer-4 border ${
                        priorityFilter === p
                          ? cfg ? `${cfg.bg} ${cfg.border} ${cfg.text}` : 'bg-brand-orange border-brand-orange text-white'
                          : cfg ? `${cfg.border} ${cfg.text} opacity-50 hover:opacity-80` : 'border-border-subtle text-[var(--color-text-muted)] hover:border-brand-orange/40'
                      }`}
                    >
                      {p}
                    </button>
                  );
                })}
              </div>
            )}
          </div>
        }
        sidePanel={
          <div className="space-y-3">
            <SimpleModeSummary
              screenName="CAD Dispatch"
              domain="cad"
              whatThisDoes="This screen coordinates active emergency calls, transitions call lifecycle states, and assigns available units."
              whatIsWrong={echoDelta > 0 ? `${echoDelta} high-priority calls need immediate dispatch lifecycle attention.` : undefined}
              whatMatters="Delays in transition or assignment increase response-time risk and operational exposure."
              whatToClickNext={activeView === 'dispatch' ? 'Open dispatch view, filter to ECHO/DELTA, then assign available units and advance call states.' : 'Switch to Dispatch view to action active incidents first.'}
              requiresReview={echoDelta > 0}
            />
            <AIExplanationCard
              domain="cad"
              severity={echoDelta > 0 ? 'HIGH' : 'INFORMATIONAL'}
              what={echoDelta > 0
                ? `Dispatch pressure elevated: ${echoDelta} high-priority calls are currently open.`
                : 'Dispatch pressure is stable with no elevated high-priority backlog.'}
              why="Priority call backlog is a direct indicator of operational risk and response reliability."
              next={echoDelta > 0
                ? 'Assign available units to ECHO/DELTA incidents first and progress each call to ENROUTE/ON_SCENE.'
                : 'Maintain cadence by clearing in-flight calls and preserving unit availability.'}
              requiresReview={echoDelta > 0}
            />
            {(activeView === 'dispatch' || activeView === 'units') && (
              <CadLiveMap units={mapUnits} className="chamfer-8" />
            )}
            {activeView === 'dispatch' && <UnitBoard units={units} />}
          </div>
        }
      >
        {loading ? (
          <QuantumTableSkeleton rows={4} />
        ) : activeView === 'dispatch' ? (
          activeCalls.length === 0 ? (
            <QuantumEmptyState
              title="No active calls"
              description="No incidents currently in progress. Create a new call when service is requested."
              icon="radio"
            />
          ) : (
            <div className="grid grid-cols-1 lg:grid-cols-2 xl:grid-cols-2 2xl:grid-cols-3 gap-3">
              {activeCalls.map(call => (
                <CallCard
                  key={call.id}
                  call={call}
                  isSelected={selectedId === call.id}
                  onSelect={() => setSelectedId(id => id === call.id ? null : call.id)}
                  onTransition={state => handleTransition(call.id, state)}
                  units={units}
                  onAssign={unitId => handleAssign(call.id, unitId)}
                />
              ))}
            </div>
          )
        ) : activeView === 'units' ? (
          <UnitBoard units={units} />
        ) : (
          historyCalls.length === 0 ? (
            <QuantumEmptyState title="No closed calls" description="Closed and cancelled calls will appear here." icon="archive" />
          ) : (
            <div className="bg-[var(--color-bg-panel)] border border-border-subtle chamfer-8 overflow-hidden">
              <table className="w-full text-left">
                <thead>
                  <tr className="border-b border-border-subtle">
                    {['Call #','Priority','Complaint','Address','Status','Received'].map(h => (
                      <th key={h} className="px-4 py-3 text-micro uppercase tracking-widest text-[var(--color-text-muted)]">{h}</th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {historyCalls.map(call => {
                    const cfg = PRIORITY_CONFIG[call.priority] || PRIORITY_CONFIG.ALPHA;
                    return (
                      <tr key={call.id} className="border-b border-border-subtle hover:bg-[var(--color-bg-base)]/[0.02]">
                        <td className="px-4 py-3 text-sm font-bold text-[var(--color-text-primary)]">#{call.call_number}</td>
                        <td className={`px-4 py-3 text-sm font-semibold ${cfg.text}`}>{call.priority}</td>
                        <td className="px-4 py-3 text-sm text-[var(--color-text-secondary)]">{call.chief_complaint || '—'}</td>
                        <td className="px-4 py-3 text-sm text-[var(--color-text-muted)] truncate max-w-xs">{call.address || call.location_address || '—'}</td>
                        <td className="px-4 py-3 text-sm text-[var(--color-text-muted)]">
                          <StatusChip status={CALL_STATE_STATUS_MAP[call.state]} size="sm">{STATE_LABEL[call.state]}</StatusChip>
                        </td>
                        <td className="px-4 py-3 text-sm font-mono text-[var(--color-text-muted)]">
                          {call.call_received_at ? new Date(call.call_received_at).toLocaleTimeString() : '—'}
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          )
        )}
      </ModuleDashboardShell>

      {showNewCall && <NewCallForm onClose={() => setShowNewCall(false)} onCreated={refresh} />}
    </>
  );
}
