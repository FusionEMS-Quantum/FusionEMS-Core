'use client';

import React, { useState, useEffect, useCallback } from 'react';
import Link from 'next/link';
import {
  ChevronLeft,
  ChevronRight,
  Calendar,
  Clock,
  Truck,
  AlertTriangle,
  CheckCircle2,
  Activity,
  FileWarning,
  RefreshCw,
  LayoutGrid,
  List,
  Eye,
} from 'lucide-react';
import { listTransportLinkRequests, type TransportLinkRequestSummaryApi } from '@/services/api';

interface TransportEvent {
  id: string;
  data: {
    status: string;
    priority?: string;
    patient_name?: string;
    patient_first?: string;
    patient_last?: string;
    mrn?: string;
    origin_facility?: string;
    destination_facility?: string;
    requested_service_level?: string;
    medical_necessity_status?: string;
    requested_pickup_time?: string;
    pcs_complete?: boolean;
    aob_complete?: boolean;
    facesheet_uploaded?: boolean;
    abn_needed?: boolean;
  };
}

function normalizeTransportEvent(item: TransportLinkRequestSummaryApi): TransportEvent {
  const requestedServiceLevel = item.data.requested_service_level ?? item.data.service_level;
  return {
    id: item.id,
    data: {
      status: item.data.status,
      priority: item.data.priority,
      patient_name: item.data.patient_name,
      patient_first: item.data.patient_first,
      patient_last: item.data.patient_last,
      mrn: item.data.mrn,
      origin_facility: item.data.origin_facility,
      destination_facility: item.data.destination_facility,
      requested_service_level: requestedServiceLevel,
      medical_necessity_status: item.data.medical_necessity_status,
      requested_pickup_time: item.data.requested_pickup_time,
    },
  };
}

const STATUS_COLORS: Record<string, { bg: string; border: string; text: string; bar: string }> = {
  draft:                 { bg: 'bg-[var(--color-bg-base)]/[0.03]',       border: 'border-white/[0.08]',        text: 'text-[var(--color-text-muted)]',     bar: '#475569' },
  submitted:             { bg: 'bg-status-info/[0.07]', border: 'border-status-info/25',       text: 'text-status-info',    bar: '#38bdf8' },
  awaiting_signatures:   { bg: 'bg-status-warning/[0.07]', border: 'border-status-warning/25', text: 'text-status-warning', bar: '#fbbf24' },
  missing_documentation: { bg: 'bg-red/[0.07]',          border: 'border-red/25',              text: 'text-red',            bar: '#ef4444' },
  sent_to_cad:           { bg: 'bg-[var(--q-orange)]/[0.08]',        border: 'border-orange/30',           text: 'text-[var(--q-orange)]',         bar: '#f97316' },
  scheduled:             { bg: 'bg-status-active/[0.07]', border: 'border-status-active/25',   text: 'text-[var(--color-status-active)]',  bar: '#22c55e' },
  accepted:              { bg: 'bg-status-active/[0.07]', border: 'border-status-active/25',   text: 'text-[var(--color-status-active)]',  bar: '#22c55e' },
  rejected:              { bg: 'bg-red/[0.07]',           border: 'border-red/25',              text: 'text-red',            bar: '#dc2626' },
  cancelled:             { bg: 'bg-[var(--color-bg-base)]/[0.02]',         border: 'border-white/[0.05]',        text: 'text-[var(--color-text-muted)]',     bar: '#334155' },
};

function patientName(e: TransportEvent) {
  return e.data.patient_name ||
    `${e.data.patient_first ?? ''} ${e.data.patient_last ?? ''}`.trim() ||
    'Unknown Patient';
}

function docComplete(e: TransportEvent) {
  return e.data.pcs_complete && e.data.aob_complete && e.data.facesheet_uploaded;
}

// ─────────────────────────────────────────────────────────────
// Calendar grid helpers
// ─────────────────────────────────────────────────────────────

function daysInMonth(year: number, month: number) {
  return new Date(year, month + 1, 0).getDate();
}

function firstDayOfMonth(year: number, month: number) {
  return new Date(year, month, 1).getDay();
}

const MONTHS = ['January','February','March','April','May','June','July','August','September','October','November','December'];
const DAYS = ['Sun','Mon','Tue','Wed','Thu','Fri','Sat'];

// ─────────────────────────────────────────────────────────────
// Event Card (compact, for calendar cells)
// ─────────────────────────────────────────────────────────────

function EventChip({
  event,
  onClick,
}: {
  event: TransportEvent;
  onClick: () => void;
}) {
  const status = event.data.status ?? 'draft';
  const c = STATUS_COLORS[status] ?? STATUS_COLORS.draft;
  const isUrgent = event.data.priority === 'URGENT';
  const docsOk = docComplete(event);

  return (
    <button
      type="button"
      onClick={onClick}
      className={`w-full text-left text-[9px] px-1.5 py-1 border font-semibold leading-tight truncate transition-colors hover:brightness-110 ${c.bg} ${c.border} ${c.text}`}
      style={{
        borderLeft: `2px solid ${c.bar}`,
        clipPath: 'polygon(0 0, calc(100% - 3px) 0, 100% 3px, 100% 100%, 0 100%)',
      }}
      title={`${patientName(event)} — ${event.data.origin_facility} → ${event.data.destination_facility}`}
    >
      <div className="flex items-center gap-1">
        {isUrgent && <div className="w-1 h-1  bg-red flex-shrink-0" />}
        {!docsOk && <FileWarning className="w-2.5 h-2.5 flex-shrink-0 text-status-warning" />}
        <span className="truncate">{patientName(event)}</span>
      </div>
      {event.data.requested_service_level && (
        <span className="opacity-60">{event.data.requested_service_level}</span>
      )}
    </button>
  );
}

// ─────────────────────────────────────────────────────────────
// Event Detail Drawer
// ─────────────────────────────────────────────────────────────

function EventDrawer({ event, onClose }: { event: TransportEvent; onClose: () => void }) {
  const d = event.data;
  const status = d.status ?? 'draft';
  const c = STATUS_COLORS[status] ?? STATUS_COLORS.draft;
  const docsOk = docComplete(event);

  return (
    <div className="fixed inset-0 z-50 flex items-start justify-end" onClick={onClose}>
      <div
        className="h-full w-full max-w-sm bg-[#0D0D0F] border-l border-white/[0.08] overflow-y-auto shadow-[0_0_15px_rgba(0,0,0,0.6)]"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="px-5 py-4 border-b border-white/[0.05] flex items-center justify-between bg-gradient-to-r from-orange/[0.05]">
          <div>
            <div className="text-[9px] font-bold tracking-widest text-[var(--q-orange)] uppercase">Transport Detail</div>
            <div className="text-[11px] font-black text-white mt-0.5">{patientName(event)}</div>
          </div>
          <button onClick={onClose} className="text-[var(--color-text-muted)] hover:text-[var(--color-text-primary)] text-[10px] font-bold uppercase tracking-wider px-2 py-1 border border-white/[0.08] hover:border-white/[0.14] transition-colors">
            Close
          </button>
        </div>

        <div className="p-5 space-y-4">
          {/* Status */}
          <div>
            <div className="text-[9px] font-black uppercase tracking-widest text-[var(--color-text-muted)] mb-1">Status</div>
            <span className={`inline-block px-2 py-0.5 text-[9px] font-bold uppercase tracking-widest border ${c.bg} ${c.text} ${c.border}`}
              style={{ clipPath: 'polygon(0 0, calc(100% - 4px) 0, 100% 4px, 100% 100%, 0 100%)' }}>
              {status.replace(/_/g, ' ')}
            </span>
          </div>

          {/* Transport info */}
          {[
            { label: 'MRN', value: d.mrn },
            { label: 'Level of Care', value: d.requested_service_level },
            { label: 'Origin', value: d.origin_facility },
            { label: 'Destination', value: d.destination_facility },
            { label: 'Pickup Time', value: d.requested_pickup_time ? new Date(d.requested_pickup_time).toLocaleString() : null },
            { label: 'Priority', value: d.priority },
          ].filter(({ value }) => value).map(({ label, value }) => (
            <div key={label}>
              <div className="text-[9px] font-bold uppercase tracking-widest text-[var(--color-text-muted)]">{label}</div>
              <div className="text-[11px] text-[var(--color-text-primary)] mt-0.5">{value}</div>
            </div>
          ))}

          {/* Medical necessity */}
          {d.medical_necessity_status && (
            <div className="p-3 border border-white/[0.06] bg-[var(--color-bg-base)]/[0.02]"
              style={{ clipPath: 'polygon(0 0, calc(100% - 5px) 0, 100% 5px, 100% 100%, 0 100%)' }}>
              <div className="text-[9px] font-black uppercase tracking-widest text-[var(--color-text-muted)] mb-1">Medical Necessity</div>
              <div className="text-[10px] font-semibold text-[var(--color-text-primary)]">{d.medical_necessity_status.replace(/_/g, ' ')}</div>
            </div>
          )}

          {/* Docs */}
          <div>
            <div className="text-[9px] font-black uppercase tracking-widest text-[var(--color-text-muted)] mb-2">Documentation</div>
            <div className="space-y-1.5">
              {[
                { label: 'PCS', ok: d.pcs_complete },
                { label: 'AOB', ok: d.aob_complete },
                { label: 'Facesheet', ok: d.facesheet_uploaded },
              ].map(({ label, ok }) => (
                <div key={label} className="flex items-center gap-2 text-[10px]">
                  {ok ? <CheckCircle2 className="w-3 h-3 text-[var(--color-status-active)]" /> : <AlertTriangle className="w-3 h-3 text-status-warning" />}
                  <span className={ok ? 'text-[var(--color-text-secondary)]' : 'text-status-warning'}>{label}</span>
                </div>
              ))}
            </div>
          </div>

          {d.abn_needed && (
            <div className="flex items-center gap-2 p-2 border border-status-warning/20 bg-status-warning/[0.05]"
              style={{ clipPath: 'polygon(0 0, calc(100% - 4px) 0, 100% 4px, 100% 100%, 0 100%)' }}>
              <AlertTriangle className="w-3 h-3 text-status-warning flex-shrink-0" />
              <span className="text-[10px] text-status-warning font-semibold">ABN Required</span>
            </div>
          )}

          {!docsOk && (
            <div className="flex items-center gap-2 p-2 border border-red/20 bg-red/[0.04]"
              style={{ clipPath: 'polygon(0 0, calc(100% - 4px) 0, 100% 4px, 100% 100%, 0 100%)' }}>
              <FileWarning className="w-3 h-3 text-red flex-shrink-0" />
              <span className="text-[10px] text-red font-semibold">Incomplete Documentation</span>
            </div>
          )}

          <Link
            href={`/transportlink/requests/${event.id}`}
            className="flex items-center gap-1.5 h-9 w-full px-4 text-[10px] font-black uppercase tracking-wider text-white bg-[var(--q-orange)] hover:bg-[#FF6A1A] transition-colors justify-center"
            style={{ clipPath: 'polygon(0 0, calc(100% - 5px) 0, 100% 5px, 100% 100%, 0 100%)' }}
          >
            <Eye className="w-3.5 h-3.5" />
            Open Full Request
          </Link>
        </div>
      </div>
    </div>
  );
}

// ─────────────────────────────────────────────────────────────
// Legend
// ─────────────────────────────────────────────────────────────

const LEGEND_ITEMS = [
  { label: 'Scheduled', bar: '#22c55e' },
  { label: 'Sent to CAD', bar: '#f97316' },
  { label: 'Awaiting Signatures', bar: '#fbbf24' },
  { label: 'Missing Docs', bar: '#ef4444' },
  { label: 'Submitted', bar: '#38bdf8' },
  { label: 'Draft', bar: '#475569' },
];

function Legend() {
  return (
    <div className="flex items-center gap-4 flex-wrap">
      {LEGEND_ITEMS.map(({ label, bar }) => (
        <div key={label} className="flex items-center gap-1.5">
          <div className="w-2.5 h-2.5  flex-shrink-0" style={{ backgroundColor: bar }} />
          <span className="text-[9px] text-[var(--color-text-muted)]">{label}</span>
        </div>
      ))}
    </div>
  );
}

// ─────────────────────────────────────────────────────────────
// Timeline / List View
// ─────────────────────────────────────────────────────────────

function TimelineView({ events }: { events: TransportEvent[] }) {
  const [selected, setSelected] = useState<TransportEvent | null>(null);

  const sorted = [...events].sort((a, b) => {
    const ta = a.data.requested_pickup_time ? new Date(a.data.requested_pickup_time).getTime() : 0;
    const tb = b.data.requested_pickup_time ? new Date(b.data.requested_pickup_time).getTime() : 0;
    return ta - tb;
  });

  return (
    <>
      {selected && <EventDrawer event={selected} onClose={() => setSelected(null)} />}
      <div className="space-y-2">
        {sorted.map((ev) => {
          const d = ev.data;
          const status = d.status ?? 'draft';
          const c = STATUS_COLORS[status] ?? STATUS_COLORS.draft;
          const pickupDt = d.requested_pickup_time ? new Date(d.requested_pickup_time) : null;
          const isUrgent = d.priority === 'URGENT';

          return (
            <button
              key={ev.id}
              type="button"
              onClick={() => setSelected(ev)}
              className={`w-full text-left flex items-center gap-3 px-4 py-3 border transition-colors hover:brightness-110 ${c.bg} ${c.border}`}
              style={{
                borderLeft: `3px solid ${c.bar}`,
                clipPath: 'polygon(0 0, calc(100% - 6px) 0, 100% 6px, 100% 100%, 0 100%)',
              }}
            >
              {/* Time */}
              <div className="flex-shrink-0 w-24 text-right">
                {pickupDt ? (
                  <>
                    <div className="text-[10px] font-bold text-[var(--color-text-primary)]">{pickupDt.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}</div>
                    <div className="text-[9px] text-[var(--color-text-muted)]">{pickupDt.toLocaleDateString()}</div>
                  </>
                ) : (
                  <div className="text-[9px] text-[var(--color-text-muted)]">Unscheduled</div>
                )}
              </div>

              <div className="flex-1 min-w-0">
                <div className="flex items-center gap-2 flex-wrap">
                  {isUrgent && (
                    <span className="text-[8px] font-black uppercase text-red bg-red/10 border border-red/20 px-1.5"
                      style={{ clipPath: 'polygon(0 0, calc(100% - 3px) 0, 100% 3px, 100% 100%, 0 100%)' }}>
                      URGENT
                    </span>
                  )}
                  <span className={`text-[11px] font-bold ${c.text}`}>{patientName(ev)}</span>
                  {d.mrn && <span className="text-[9px] text-[var(--color-text-muted)] font-mono">MRN {d.mrn}</span>}
                  {d.requested_service_level && (
                    <span className="text-[9px] font-bold text-[var(--q-orange)] border border-orange/20 bg-[var(--q-orange)]/[0.06] px-1.5"
                      style={{ clipPath: 'polygon(0 0, calc(100% - 3px) 0, 100% 3px, 100% 100%, 0 100%)' }}>
                      {d.requested_service_level}
                    </span>
                  )}
                </div>
                <div className="flex items-center gap-1.5 mt-0.5 text-[10px] text-[var(--color-text-muted)]">
                  <span>{d.origin_facility || '—'}</span>
                  <ChevronRight className="w-2.5 h-2.5 text-[var(--color-text-muted)]/30" />
                  <span>{d.destination_facility || '—'}</span>
                </div>
              </div>

              <div className="flex-shrink-0 flex items-center gap-2">
                {!docComplete(ev) && <FileWarning className="w-3.5 h-3.5 text-status-warning" />}
                {d.abn_needed && <AlertTriangle className="w-3.5 h-3.5 text-status-warning" />}
                <span className={`text-[9px] font-bold uppercase ${c.text}`}>{status.replace(/_/g, ' ')}</span>
              </div>
            </button>
          );
        })}

        {sorted.length === 0 && (
          <div className="flex flex-col items-center justify-center py-16 gap-3">
            <Calendar className="w-10 h-10 text-[var(--color-text-muted)]/20" />
            <p className="text-[11px] text-[var(--color-text-muted)]">No transports in this period.</p>
          </div>
        )}
      </div>
    </>
  );
}

// ─────────────────────────────────────────────────────────────
// Month Calendar View
// ─────────────────────────────────────────────────────────────

function MonthView({ year, month, events }: { year: number; month: number; events: TransportEvent[] }) {
  const [selected, setSelected] = useState<TransportEvent | null>(null);
  const numDays = daysInMonth(year, month);
  const firstDay = firstDayOfMonth(year, month);
  const today = new Date();

  const eventsByDay: Record<number, TransportEvent[]> = {};
  events.forEach((ev) => {
    const pt = ev.data.requested_pickup_time;
    if (!pt) return;
    const dt = new Date(pt);
    if (dt.getFullYear() === year && dt.getMonth() === month) {
      const day = dt.getDate();
      (eventsByDay[day] = eventsByDay[day] ?? []).push(ev);
    }
  });

  const cells: (number | null)[] = [
    ...Array(firstDay).fill(null),
    ...Array.from({ length: numDays }, (_, i) => i + 1),
  ];
  while (cells.length % 7 !== 0) cells.push(null);

  return (
    <>
      {selected && <EventDrawer event={selected} onClose={() => setSelected(null)} />}
      <div>
        {/* Day headers */}
        <div className="grid grid-cols-7 border-b border-white/[0.06]">
          {DAYS.map((d) => (
            <div key={d} className="px-2 py-2 text-[9px] font-black uppercase tracking-widest text-[var(--color-text-muted)] text-center border-r border-white/[0.04] last:border-0">
              {d}
            </div>
          ))}
        </div>

        {/* Weeks */}
        <div className="grid grid-cols-7 divide-x divide-white/[0.04]">
          {cells.map((day, i) => {
            const isToday = day !== null && today.getFullYear() === year && today.getMonth() === month && today.getDate() === day;
            const evs = day ? (eventsByDay[day] ?? []) : [];
            const hasUrgent = evs.some((e) => e.data.priority === 'URGENT');
            const hasMissingDocs = evs.some((e) => !docComplete(e));

            return (
              <div
                key={i}
                className={`min-h-[90px] p-1.5 border-b border-white/[0.04] relative ${day ? 'hover:bg-[var(--color-bg-base)]/[0.02]' : 'bg-[var(--color-bg-base)]/20'} transition-colors`}
              >
                {day && (
                  <>
                    <div className="flex items-center justify-between mb-1">
                      <span
                        className={`text-[10px] font-bold w-5 h-5 flex items-center justify-center ${isToday ? 'bg-[var(--q-orange)] text-white' : 'text-[var(--color-text-muted)]'}`}
                        style={isToday ? { clipPath: 'polygon(0 0, calc(100% - 3px) 0, 100% 3px, 100% 100%, 0 100%)' } : {}}
                      >
                        {day}
                      </span>
                      {hasUrgent && <div className="w-1.5 h-1.5  bg-red" />}
                      {hasMissingDocs && !hasUrgent && <FileWarning className="w-2.5 h-2.5 text-status-warning" />}
                    </div>
                    <div className="space-y-0.5">
                      {evs.slice(0, 3).map((ev) => (
                        <EventChip key={ev.id} event={ev} onClick={() => setSelected(ev)} />
                      ))}
                      {evs.length > 3 && (
                        <div className="text-[8px] text-[var(--color-text-muted)] text-center py-0.5">+{evs.length - 3} more</div>
                      )}
                    </div>
                  </>
                )}
              </div>
            );
          })}
        </div>
      </div>
    </>
  );
}

// ─────────────────────────────────────────────────────────────
// Main Calendar Page
// ─────────────────────────────────────────────────────────────

type ViewMode = 'month' | 'timeline';

export default function TransportCalendarPage() {
  const today = new Date();
  const [year, setYear] = useState(today.getFullYear());
  const [month, setMonth] = useState(today.getMonth());
  const [viewMode, setViewMode] = useState<ViewMode>('month');
  const [events, setEvents] = useState<TransportEvent[]>([]);
  const [loading, setLoading] = useState(true);
  const [loadError, setLoadError] = useState('');

  const load = useCallback(async () => {
    setLoading(true);
    setLoadError('');
    try {
      const items = await listTransportLinkRequests(500);
      setEvents(items.map((item) => normalizeTransportEvent(item)));
    } catch (err) {
      setLoadError(err instanceof Error ? err.message : 'Unable to load calendar right now.');
      setEvents([]);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { load(); }, [load]);

  const prevMonth = () => {
    setMonth((m) => {
      if (m === 0) { setYear((y) => y - 1); return 11; }
      return m - 1;
    });
  };
  const nextMonth = () => {
    setMonth((m) => {
      if (m === 11) { setYear((y) => y + 1); return 0; }
      return m + 1;
    });
  };

  // Filter events to current month for month view, all for timeline
  const monthEvents = events.filter((ev) => {
    const pt = ev.data.requested_pickup_time;
    if (!pt) return viewMode === 'timeline';
    const dt = new Date(pt);
    return dt.getFullYear() === year && dt.getMonth() === month;
  });

  const counts = {
    urgent: events.filter((e) => e.data.priority === 'URGENT').length,
    missingDocs: events.filter((e) => !docComplete(e) && e.data.status !== 'cancelled').length,
    sentToCad: events.filter((e) => e.data.status === 'sent_to_cad').length,
    scheduled: events.filter((e) => ['scheduled', 'accepted'].includes(e.data.status)).length,
  };

  return (
    <div className="p-5 max-w-7xl mx-auto">
      {/* Header */}
      <div className="flex items-start justify-between flex-wrap gap-3 mb-5">
        <div>
          <div className="text-[9px] font-bold tracking-[0.3em] text-[var(--q-orange)] uppercase mb-1">TransportLink · Calendar</div>
          <h1 className="text-h1 font-black text-white">Transport Calendar</h1>
        </div>
        <div className="flex items-center gap-2">
          <button
            onClick={load}
            disabled={loading}
            className="flex items-center gap-1.5 h-9 px-3 text-[10px] font-bold uppercase tracking-wider border border-white/[0.08] text-[var(--color-text-muted)] hover:text-[var(--color-text-primary)] transition-colors"
            style={{ clipPath: 'polygon(0 0, calc(100% - 4px) 0, 100% 4px, 100% 100%, 0 100%)' }}
          >
            <RefreshCw className={`w-3 h-3 ${loading ? 'animate-spin' : ''}`} />
            Refresh
          </button>
        </div>
      </div>

      {loadError && (
        <div
          className="mb-4 flex items-start gap-2 border border-red/25 bg-red/[0.06] p-3"
          style={{ clipPath: 'polygon(0 0, calc(100% - 4px) 0, 100% 4px, 100% 100%, 0 100%)' }}
        >
          <AlertTriangle className="mt-0.5 h-3.5 w-3.5 flex-shrink-0 text-red" />
          <span className="text-[10px] text-red">{loadError}</span>
        </div>
      )}

      {/* Urgency/status summary bar */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-2 mb-4">
        {[
          { label: 'Scheduled', value: counts.scheduled, icon: CheckCircle2, color: 'text-[var(--color-status-active)]', border: 'border-status-active/20', bg: 'bg-status-active/[0.04]' },
          { label: 'Sent to CAD', value: counts.sentToCad, icon: Activity, color: 'text-[var(--q-orange)]', border: 'border-orange/20', bg: 'bg-[var(--q-orange)]/[0.04]' },
          { label: 'Missing Docs', value: counts.missingDocs, icon: FileWarning, color: 'text-status-warning', border: 'border-status-warning/20', bg: 'bg-status-warning/[0.04]', alert: counts.missingDocs > 0 },
          { label: 'Urgent', value: counts.urgent, icon: AlertTriangle, color: 'text-red', border: 'border-red/20', bg: 'bg-red/[0.04]', alert: counts.urgent > 0 },
        ].map(({ label, value, icon: Icon, color, border, bg }) => (
          <div key={label} className={`flex items-center gap-2 p-3 border ${bg} ${border}`}
            style={{ clipPath: 'polygon(0 0, calc(100% - 6px) 0, 100% 6px, 100% 100%, 0 100%)' }}>
            <Icon className={`w-4 h-4 ${color} flex-shrink-0`} />
            <div>
              <div className={`text-[14px] font-black leading-none ${color}`}>{value}</div>
              <div className="text-[9px] text-[var(--color-text-muted)] uppercase tracking-widest font-bold mt-0.5">{label}</div>
            </div>
          </div>
        ))}
      </div>

      {/* Calendar panel */}
      <div
        className="border border-white/[0.06] bg-[#0D0D0F] overflow-hidden"
        style={{ clipPath: 'polygon(0 0, calc(100% - 12px) 0, 100% 12px, 100% 100%, 12px 100%, 0 calc(100% - 12px))' }}
      >
        {/* Toolbar */}
        <div className="px-4 py-3 border-b border-white/[0.05] flex items-center justify-between flex-wrap gap-3 bg-[var(--color-bg-base)]/[0.02]">
          <div className="flex items-center gap-3">
            <button
              onClick={prevMonth}
              className="w-8 h-8 flex items-center justify-center border border-white/[0.08] text-[var(--color-text-muted)] hover:text-[var(--color-text-primary)] hover:border-white/[0.14] transition-colors"
              style={{ clipPath: 'polygon(0 0, calc(100% - 4px) 0, 100% 4px, 100% 100%, 0 100%)' }}
            >
              <ChevronLeft className="w-3.5 h-3.5" />
            </button>
            <div className="flex items-center gap-2">
              <span className="text-[14px] font-black text-white">{MONTHS[month]}</span>
              <span className="text-[12px] font-bold text-[var(--color-text-muted)]">{year}</span>
            </div>
            <button
              onClick={nextMonth}
              className="w-8 h-8 flex items-center justify-center border border-white/[0.08] text-[var(--color-text-muted)] hover:text-[var(--color-text-primary)] hover:border-white/[0.14] transition-colors"
              style={{ clipPath: 'polygon(0 0, calc(100% - 4px) 0, 100% 4px, 100% 100%, 0 100%)' }}
            >
              <ChevronRight className="w-3.5 h-3.5" />
            </button>
            <button
              onClick={() => { setYear(today.getFullYear()); setMonth(today.getMonth()); }}
              className="h-7 px-2 text-[9px] font-bold uppercase tracking-widest border border-orange/25 bg-[var(--q-orange)]/[0.06] text-[var(--q-orange)] hover:bg-[var(--q-orange)]/15 transition-colors"
              style={{ clipPath: 'polygon(0 0, calc(100% - 4px) 0, 100% 4px, 100% 100%, 0 100%)' }}
            >
              Today
            </button>
          </div>

          <div className="flex items-center gap-2">
            <Legend />
            <div className="w-px h-5 bg-[var(--color-bg-base)]/[0.06]" />
            <div className="flex items-center border border-white/[0.08]"
              style={{ clipPath: 'polygon(0 0, calc(100% - 4px) 0, 100% 4px, 100% 100%, 0 100%)' }}>
              <button
                onClick={() => setViewMode('month')}
                className={`flex items-center gap-1.5 h-7 px-3 text-[9px] font-bold uppercase tracking-wider transition-colors ${viewMode === 'month' ? 'bg-[var(--q-orange)]/15 text-[var(--q-orange)]' : 'text-[var(--color-text-muted)] hover:text-[var(--color-text-primary)]'}`}
              >
                <LayoutGrid className="w-3 h-3" />
                <span className="hidden sm:inline">Month</span>
              </button>
              <button
                onClick={() => setViewMode('timeline')}
                className={`flex items-center gap-1.5 h-7 px-3 text-[9px] font-bold uppercase tracking-wider border-l border-white/[0.08] transition-colors ${viewMode === 'timeline' ? 'bg-[var(--q-orange)]/15 text-[var(--q-orange)]' : 'text-[var(--color-text-muted)] hover:text-[var(--color-text-primary)]'}`}
              >
                <List className="w-3 h-3" />
                <span className="hidden sm:inline">Timeline</span>
              </button>
            </div>
          </div>
        </div>

        {loading ? (
          <div className="flex items-center justify-center h-64">
            <div className="flex items-center gap-2 text-[var(--color-text-muted)] text-[11px]">
              <RefreshCw className="w-3.5 h-3.5 animate-spin" />
              Loading calendar…
            </div>
          </div>
        ) : viewMode === 'month' ? (
          <MonthView year={year} month={month} events={events} />
        ) : (
          <div className="p-4">
            <div className="text-[9px] font-black uppercase tracking-widest text-[var(--color-text-muted)] mb-3 flex items-center gap-2">
              <Clock className="w-3 h-3 text-[var(--color-text-muted)]" />
              {viewMode === 'timeline' ? `All Requests — ${monthEvents.length} in ${MONTHS[month]}` : ''}
            </div>
            <TimelineView events={monthEvents} />
          </div>
        )}
      </div>

      {/* Quick links */}
      <div className="flex flex-wrap gap-2 mt-4">
        {[
          { href: '/transportlink/requests/new', label: 'New Request' },
          { href: '/transportlink/requests?filter=awaiting_signatures', label: 'Awaiting Signatures' },
          { href: '/transportlink/requests?filter=sent_to_cad', label: 'Sent to CAD' },
          { href: '/transportlink/requests?filter=missing_documentation', label: 'Missing Docs' },
        ].map(({ href, label }) => (
          <Link
            key={href}
            href={href}
            className="flex items-center gap-1.5 h-8 px-3 text-[10px] font-semibold uppercase tracking-wider text-[var(--color-text-muted)] border border-white/[0.06] hover:text-[var(--color-text-primary)] hover:border-white/[0.12] transition-colors"
            style={{ clipPath: 'polygon(0 0, calc(100% - 4px) 0, 100% 4px, 100% 100%, 0 100%)' }}
          >
            <Truck className="w-3 h-3" />
            {label}
          </Link>
        ))}
      </div>
    </div>
  );
}
