'use client';

import React, { useEffect, useState, useCallback } from 'react';
import { QuantumTableSkeleton, QuantumEmptyState } from '@/components/ui';
import {
  getStaffingReadiness,
  getStaffingAuditLog,
  listShiftInstances,
} from '@/services/api';

// ── Types ─────────────────────────────────────────────────────────────────────

interface CrewMember {
  id: string;
  name: string;
  role: string;
  certification_level: string;
  station?: string;
  on_duty: boolean;
  fatigue_flagged?: boolean;
  readiness_score?: number;
  qualifications?: Qualification[];
}

interface Qualification {
  id: string;
  cert_type: string;
  cert_number?: string;
  issuing_body?: string;
  issued_date?: string;
  expiry_date?: string;
  status: 'ACTIVE' | 'EXPIRED' | 'EXPIRING_SOON' | 'PENDING';
}

interface ShiftInstance {
  id: string;
  unit_name?: string;
  start_time: string;
  end_time: string;
  assigned_crew?: string[];
  state: string;
}

interface ReadinessData {
  crew?: CrewMember[];
  summary?: {
    total_crew: number;
    on_duty: number;
    available: number;
    fatigue_flagged: number;
    expiring_credentials: number;
  };
}

// ── Helpers ───────────────────────────────────────────────────────────────────

function daysUntil(dateStr: string): number {
  return Math.ceil((new Date(dateStr).getTime() - Date.now()) / 86400000);
}

function CredentialChip({ qual }: { qual: Qualification }) {
  const days = qual.expiry_date ? daysUntil(qual.expiry_date) : null;
  const isExpired = days !== null && days <= 0;
  const isWarning = days !== null && days > 0 && days <= 30;

  return (
    <div className={`chamfer-4 border px-2 py-1 text-micro ${
      isExpired ? 'bg-red-900/30 border-[var(--color-brand-red)]/40 text-[var(--color-brand-red)]' :
      isWarning ? 'bg-yellow-900/30 border-yellow-500/40 text-yellow-300' :
      qual.status === 'PENDING' ? 'bg-blue-900/30 border-[var(--color-status-info)]/40 text-[var(--color-status-info)]' :
      'bg-green-900/20 border-[var(--color-status-active)]/30 text-[var(--color-status-active)]'
    }`}>
      <div className="font-bold">{qual.cert_type}</div>
      {qual.expiry_date && (
        <div className="opacity-80">
          {isExpired ? `Expired ${Math.abs(days!)}d ago` :
           isWarning ? `Expires in ${days}d` :
           `Exp ${new Date(qual.expiry_date).toLocaleDateString()}`}
        </div>
      )}
    </div>
  );
}

function ReadinessBar({ score }: { score: number }) {
  const pct = Math.round(score * 100);
  const color = pct >= 80 ? 'bg-[var(--color-status-active)]' : pct >= 50 ? 'bg-yellow-500' : 'bg-[var(--color-brand-red)]';
  return (
    <div className="flex items-center gap-2">
      <div className="flex-1 h-1.5 bg-[var(--color-bg-base)]/10  overflow-hidden">
        <div className={`h-full  transition-all ${color}`} style={{ width: `${pct}%` }} />
      </div>
      <span className="text-micro font-bold text-[var(--color-text-muted)] w-8">{pct}%</span>
    </div>
  );
}

// ── Roster Table ──────────────────────────────────────────────────────────────

function RosterTable({ crew }: { crew: CrewMember[] }) {
  const [search, setSearch] = useState('');

  const filtered = crew.filter(c =>
    !search || c.name.toLowerCase().includes(search.toLowerCase()) ||
    c.role.toLowerCase().includes(search.toLowerCase()) ||
    c.certification_level.toLowerCase().includes(search.toLowerCase())
  );

  return (
    <div className="space-y-3">
      <input
        value={search}
        onChange={e => setSearch(e.target.value)}
        className="w-full max-w-xs bg-[var(--color-bg-panel)] border border-border-subtle chamfer-4 px-3 py-2 text-sm text-[var(--color-text-primary)] focus:outline-none focus:border-brand-orange/60"
        placeholder="Search name, role, or certification…"
      />
      <div className="bg-[var(--color-bg-panel)] border border-border-subtle chamfer-8 overflow-hidden">
        <table className="w-full text-left">
          <thead>
            <tr className="border-b border-border-subtle">
              {['Name','Role','Cert Level','Station','Status','Readiness','Credentials'].map(h => (
                <th key={h} className="px-4 py-3 text-micro uppercase tracking-widest text-[var(--color-text-muted)]">{h}</th>
              ))}
            </tr>
          </thead>
          <tbody>
            {filtered.map(member => {
              const expiring = (member.qualifications || []).filter(q => {
                const d = q.expiry_date ? daysUntil(q.expiry_date) : null;
                return d !== null && d <= 30;
              });
              return (
                <tr key={member.id} className="border-b border-border-subtle hover:bg-[var(--color-bg-base)]/[0.02]">
                  <td className="px-4 py-3">
                    <div className="flex items-center gap-2">
                      {member.fatigue_flagged && (
                        <span title="Fatigue flagged" className="text-[#FF7A33] text-xs">⚠</span>
                      )}
                      <span className="text-sm font-semibold text-[var(--color-text-primary)]">{member.name}</span>
                    </div>
                  </td>
                  <td className="px-4 py-3 text-sm text-[var(--color-text-secondary)]">{member.role || '—'}</td>
                  <td className="px-4 py-3 text-sm font-mono text-[var(--color-text-secondary)]">{member.certification_level || '—'}</td>
                  <td className="px-4 py-3 text-sm text-[var(--color-text-secondary)]">{member.station || '—'}</td>
                  <td className="px-4 py-3">
                    <div className="flex items-center gap-1.5">
                      <div className={`w-2 h-2  ${member.on_duty ? 'bg-[var(--color-status-active)] animate-pulse' : 'bg-gray-500'}`} />
                      <span className={`text-xs font-semibold ${member.on_duty ? 'text-[var(--color-status-active)]' : 'text-[var(--color-text-muted)]'}`}>
                        {member.on_duty ? 'On Duty' : 'Off Duty'}
                      </span>
                    </div>
                  </td>
                  <td className="px-4 py-3 w-32">
                    {member.readiness_score != null
                      ? <ReadinessBar score={member.readiness_score} />
                      : <span className="text-micro text-[var(--color-text-muted)]">—</span>}
                  </td>
                  <td className="px-4 py-3">
                    <div className="flex flex-wrap gap-1">
                      {expiring.length > 0 ? (
                        expiring.map(q => <CredentialChip key={q.id} qual={q} />)
                      ) : (member.qualifications || []).length > 0 ? (
                        <span className="text-micro text-[var(--color-status-active)]">✓ {(member.qualifications || []).length} current</span>
                      ) : (
                        <span className="text-micro text-[var(--color-text-muted)]">—</span>
                      )}
                    </div>
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
        {filtered.length === 0 && (
          <div className="text-center py-8 text-sm text-[var(--color-text-muted)]">
            {search ? 'No crew members match your search.' : 'No crew members found.'}
          </div>
        )}
      </div>
    </div>
  );
}

// ── Shifts View ───────────────────────────────────────────────────────────────

function ShiftsView({ shifts }: { shifts: ShiftInstance[] }) {
  if (shifts.length === 0) {
    return (
      <QuantumEmptyState
        title="No shifts scheduled"
        description="Create shift templates and generate instances through the Scheduling module."
        icon="calendar"
      />
    );
  }

  return (
    <div className="bg-[var(--color-bg-panel)] border border-border-subtle chamfer-8 overflow-hidden">
      <table className="w-full text-left">
        <thead>
          <tr className="border-b border-border-subtle">
            {['Unit / Template','Start','End','Crew','State'].map(h => (
              <th key={h} className="px-4 py-3 text-micro uppercase tracking-widest text-[var(--color-text-muted)]">{h}</th>
            ))}
          </tr>
        </thead>
        <tbody>
          {shifts.map(shift => {
            const start = new Date(shift.start_time);
            const end = new Date(shift.end_time);
            const durationHrs = Math.round((end.getTime() - start.getTime()) / 3600000);
            return (
              <tr key={shift.id} className="border-b border-border-subtle hover:bg-[var(--color-bg-base)]/[0.02]">
                <td className="px-4 py-3 text-sm font-semibold text-[var(--color-text-primary)]">{shift.unit_name || shift.id.slice(0, 8)}</td>
                <td className="px-4 py-3 text-sm font-mono text-[var(--color-text-secondary)]">
                  {start.toLocaleDateString()} {start.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                </td>
                <td className="px-4 py-3 text-sm font-mono text-[var(--color-text-secondary)]">
                  {end.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                  <span className="text-micro text-[var(--color-text-muted)] ml-1">({durationHrs}h)</span>
                </td>
                <td className="px-4 py-3 text-sm text-[var(--color-text-secondary)]">
                  {(shift.assigned_crew || []).length > 0
                    ? (shift.assigned_crew || []).join(', ')
                    : <span className="text-[var(--color-text-muted)] text-micro italic">Unassigned</span>}
                </td>
                <td className="px-4 py-3">
                  <span className={`text-xs font-semibold px-2 py-0.5 chamfer-4 border ${
                    shift.state === 'ACTIVE' ? 'bg-green-900/30 border-[var(--color-status-active)]/40 text-[var(--color-status-active)]' :
                    shift.state === 'DRAFT' ? 'bg-[var(--color-bg-panel)]/50 border-gray-600 text-[var(--color-text-muted)]' :
                    'bg-blue-900/30 border-[var(--color-status-info)]/40 text-[var(--color-status-info)]'
                  }`}>
                    {shift.state}
                  </span>
                </td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}

// ── Credential Alert Banner ───────────────────────────────────────────────────

function CredentialAlerts({ crew }: { crew: CrewMember[] }) {
  const alerts: { name: string; cert: string; days: number }[] = [];

  for (const member of crew) {
    for (const qual of member.qualifications || []) {
      if (qual.expiry_date) {
        const days = daysUntil(qual.expiry_date);
        if (days <= 60) {
          alerts.push({ name: member.name, cert: qual.cert_type, days });
        }
      }
    }
  }

  alerts.sort((a, b) => a.days - b.days);

  if (alerts.length === 0) return null;

  return (
    <div className="bg-yellow-900/20 border border-yellow-500/30 chamfer-8 p-4 mb-5">
      <div className="flex items-center gap-2 mb-3">
        <div className="w-2 h-2  bg-yellow-400 animate-pulse" />
        <span className="text-sm font-bold text-[var(--q-yellow)]">
          {alerts.filter(a => a.days <= 0).length > 0
            ? `⚠ ${alerts.filter(a => a.days <= 0).length} expired + ${alerts.filter(a => a.days > 0).length} expiring credentials`
            : `${alerts.length} credentials expiring within 60 days`}
        </span>
      </div>
      <div className="flex flex-wrap gap-2">
        {alerts.slice(0, 8).map((a, i) => (
          <div key={i} className={`chamfer-4 border px-3 py-1.5 text-xs ${
            a.days <= 0 ? 'bg-red-900/30 border-[var(--color-brand-red)]/40 text-[var(--color-brand-red)]' :
            a.days <= 14 ? 'bg-[rgba(255,106,0,0.3)] border-orange-500/40 text-[#FF9A66]' :
            'bg-yellow-900/30 border-yellow-500/40 text-yellow-300'
          }`}>
            <span className="font-bold">{a.name}</span>
            <span className="mx-1 opacity-60">·</span>
            <span>{a.cert}</span>
            <span className="ml-1 font-mono">
              {a.days <= 0 ? `(${Math.abs(a.days)}d expired)` : `(${a.days}d)`}
            </span>
          </div>
        ))}
        {alerts.length > 8 && (
          <div className="chamfer-4 border border-yellow-500/30 px-3 py-1.5 text-xs text-[var(--q-yellow)]">
            +{alerts.length - 8} more
          </div>
        )}
      </div>
    </div>
  );
}

// ── Page ──────────────────────────────────────────────────────────────────────

type ActiveView = 'roster' | 'shifts' | 'audit';

export default function StaffPage() {
  const [readiness, setReadiness] = useState<ReadinessData | null>(null);
  const [shifts, setShifts] = useState<ShiftInstance[]>([]);
  const [auditLog, setAuditLog] = useState<Record<string, unknown>[]>([]);
  const [loading, setLoading] = useState(true);
  const [loadError, setLoadError] = useState<string | null>(null);
  const [activeView, setActiveView] = useState<ActiveView>('roster');

  const refresh = useCallback(async () => {
    setLoadError(null);
    let anyFailed = false;
    try {
      const [readData, shiftData] = await Promise.all([
        getStaffingReadiness().catch((err) => { anyFailed = true; console.error('[Staff] readiness failed:', err); return null; }),
        listShiftInstances().catch((err) => { anyFailed = true; console.error('[Staff] shifts failed:', err); return []; }),
      ]);
      if (anyFailed) setLoadError('Some staff data failed to load. Displayed data may be incomplete.');
      setReadiness(readData || {});
      setShifts(Array.isArray(shiftData) ? shiftData : shiftData?.shifts || []);
    } finally {
      setLoading(false);
    }
  }, []);

  const loadAudit = useCallback(async () => {
    try {
      const data = await getStaffingAuditLog();
      setAuditLog(Array.isArray(data) ? data : data?.events || []);
    } catch {
      setAuditLog([]);
    }
  }, []);

  useEffect(() => { refresh(); }, [refresh]);
  useEffect(() => {
    if (activeView === 'audit') loadAudit();
  }, [activeView, loadAudit]);

  const crew = readiness?.crew || [];
  const summary = readiness?.summary;

  const onDuty = summary?.on_duty ?? crew.filter(c => c.on_duty).length;
  const totalCrew = summary?.total_crew ?? crew.length;
  const fatigueFlagged = summary?.fatigue_flagged ?? crew.filter(c => c.fatigue_flagged).length;
  const expiringCreds = summary?.expiring_credentials ??
    crew.reduce((n, c) => n + (c.qualifications || []).filter(q => q.expiry_date && daysUntil(q.expiry_date) <= 30).length, 0);

  return (
    <div className="flex flex-col bg-[var(--color-bg-base)] min-h-screen">
      {loadError && (
        <div className="mx-5 mt-4 px-4 py-3 bg-red-900/20 border border-[var(--color-brand-red)]/30 text-[var(--color-brand-red)] text-sm font-medium chamfer-4">
          ⚠ {loadError}
        </div>
      )}
      {/* Header */}
      <div className="flex-shrink-0 border-b border-[var(--color-border-default)] bg-[var(--color-bg-panel)] px-5 py-4">
        <div className="flex items-center justify-between">
          <div>
            <div className="flex items-center gap-3">
              <div className="w-1 h-6 chamfer-4 flex-shrink-0 bg-[var(--q-orange)]" />
              <div className="text-body font-black text-[var(--color-text-primary)] uppercase tracking-wider">Personnel & Credentials Hub</div>
            </div>
            <div className="text-micro text-[var(--color-text-muted)] ml-4">Roster management · Credential tracking · Shift coverage · Fatigue monitoring</div>
          </div>
          <div className="flex items-center gap-3">
            {fatigueFlagged > 0 && (
              <div className="flex items-center gap-1.5 bg-[rgba(255,106,0,0.3)] border border-orange-500/40 chamfer-4 px-3 py-1.5">
                <span className="text-micro font-bold text-[#FF7A33]">⚠ {fatigueFlagged} fatigue flag{fatigueFlagged > 1 ? 's' : ''}</span>
              </div>
            )}
          </div>
        </div>

        {/* Summary Metrics */}
        <div className="grid grid-cols-4 gap-3 mt-4">
          {[
            { label: 'On Duty Now', value: `${onDuty} / ${totalCrew}`, color: 'text-[var(--color-status-active)]' },
            { label: 'Active Shifts', value: shifts.filter(s => s.state === 'ACTIVE').length.toString(), color: 'text-[var(--color-status-info)]' },
            { label: 'Fatigue Flags', value: fatigueFlagged.toString(), color: fatigueFlagged > 0 ? 'text-[#FF7A33]' : 'text-[var(--color-text-muted)]' },
            { label: 'Creds Expiring (30d)', value: expiringCreds.toString(), color: expiringCreds > 0 ? 'text-yellow-400' : 'text-[var(--color-text-muted)]' },
          ].map(m => (
            <div key={m.label} className="bg-[var(--color-bg-panel)] border border-border-subtle chamfer-8 px-4 py-3">
              <div className={`text-2xl font-black ${m.color}`}>{m.value}</div>
              <div className="text-micro text-[var(--color-text-muted)] mt-0.5">{m.label}</div>
            </div>
          ))}
        </div>

        {/* View Toggle */}
        <div className="flex items-center gap-1 mt-4">
          {(['roster','shifts','audit'] as const).map(v => (
            <button
              key={v}
              onClick={() => setActiveView(v)}
              className={`px-4 py-2 text-micro font-label font-bold capitalize border-b-2 transition-colors ${
                activeView === v ? 'border-[var(--q-orange)] text-[var(--q-orange)]' : 'border-transparent text-[var(--color-text-muted)] hover:text-[var(--color-text-secondary)]'
              }`}
            >
              {v === 'roster' ? 'Crew Roster' : v === 'shifts' ? 'Shift Schedule' : 'Audit Log'}
            </button>
          ))}
        </div>
      </div>

      {/* Content */}
      <div className="flex-1 p-5">
        {loading ? (
          <QuantumTableSkeleton rows={6} />
        ) : activeView === 'roster' ? (
          <>
            {crew.length > 0 && <CredentialAlerts crew={crew} />}
            {crew.length === 0 ? (
              <QuantumEmptyState
                title="No crew members on file"
                description="Crew members are added through user provisioning in tenant administration."
                icon="users"
              />
            ) : (
              <RosterTable crew={crew} />
            )}
          </>
        ) : activeView === 'shifts' ? (
          <ShiftsView shifts={shifts} />
        ) : (
          /* Audit Log */
          auditLog.length === 0 ? (
            <QuantumEmptyState title="No audit events" description="Staffing audit events will appear here." icon="document" />
          ) : (
            <div className="bg-[var(--color-bg-panel)] border border-border-subtle chamfer-8 overflow-hidden">
              <table className="w-full text-left">
                <thead>
                  <tr className="border-b border-border-subtle">
                    {['Timestamp','Actor','Action','Target','Details'].map(h => (
                      <th key={h} className="px-4 py-3 text-micro uppercase tracking-widest text-[var(--color-text-muted)]">{h}</th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {auditLog.slice(0, 100).map((event, i) => (
                    <tr key={i} className="border-b border-border-subtle hover:bg-[var(--color-bg-base)]/[0.02]">
                      <td className="px-4 py-3 text-xs font-mono text-[var(--color-text-muted)]">
                        {event.created_at ? new Date(event.created_at as string).toLocaleString() : '—'}
                      </td>
                      <td className="px-4 py-3 text-sm text-[var(--color-text-secondary)]">{(event.actor as string) || '—'}</td>
                      <td className="px-4 py-3 text-sm font-semibold text-brand-orange">{(event.action as string) || '—'}</td>
                      <td className="px-4 py-3 text-sm text-[var(--color-text-secondary)]">{(event.target as string) || '—'}</td>
                      <td className="px-4 py-3 text-xs text-[var(--color-text-muted)] max-w-xs truncate">
                        {event.details ? JSON.stringify(event.details) : '—'}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )
        )}
      </div>
    </div>
  );
}

