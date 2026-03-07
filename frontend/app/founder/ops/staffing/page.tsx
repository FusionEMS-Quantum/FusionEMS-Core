'use client';
import { useState, useEffect, useCallback } from 'react';
import Link from 'next/link';

const API = process.env.NEXT_PUBLIC_API_URL || '';
const getToken = () => typeof window !== 'undefined' ? 'Bearer ' + (localStorage.getItem('qs_token') || '') : '';

const CERT_LEVELS = ['EMT', 'AEMT', 'Paramedic', 'Flight_Paramedic', 'Critical_Care_Paramedic'];
const SERVICE_LEVELS = ['BLS', 'ALS', 'CCT', 'HEMS'];
const CERT_FOR_LEVEL: Record<string, string> = { BLS: 'EMT', ALS: 'AEMT', CCT: 'Paramedic', HEMS: 'Flight_Paramedic' };

function Panel({ children, className = '' }: { children: React.ReactNode; className?: string }) {
  return (
    <div className={`bg-white/[0.03] border border-white/[0.08] chamfer-8 p-4 ${className}`}>
      {children}
    </div>
  );
}

function StateBadge({ state, color }: { state: string; color?: string }) {
  const colors: Record<string, string> = {
    CREW_AVAILABLE: '#4caf50', CREW_ASSIGNED: '#29b6f6', CREW_UNAVAILABLE: '#78909c',
    CREW_CONFLICT: '#ef5350', CREW_UNQUALIFIED: '#ff6b1a', CREW_FATIGUE_WARNING: '#ffc107',
    CREW_BACKUP_REQUIRED: '#f44336', READY: '#4caf50', WARNING: '#ffc107', CRITICAL: '#ef5350',
  };
  const c = color ?? colors[state] ?? '#78909c';
  return (
    <span className="inline-block px-2 py-0.5 chamfer-4 text-micro font-bold uppercase tracking-wider"
      style={{ background: c + '22', color: c, border: `1px solid ${c}44` }}>
      {state.replace(/_/g, ' ')}
    </span>
  );
}

interface StaffingSummary {
  total_crew: number;
  available: number;
  assigned: number;
  unavailable: number;
  fatigue_flags: number;
  active_conflicts: number;
  qualified_by_service_level: Record<string, number>;
  staffing_gaps: Array<{ type: string; message: string }>;
  overall_readiness: string;
}

export default function StaffingPage() {
  const [summary, setSummary] = useState<StaffingSummary | null>(null);
  const [loading, setLoading] = useState(true);
  const [activeTab, setActiveTab] = useState<'summary' | 'check' | 'availability' | 'fatigue'>('summary');
  const [checkCrew, setCheckCrew] = useState({ crew_member_id: '', service_level: 'BLS' });
  const [checkResult, setCheckResult] = useState<Record<string, unknown> | null>(null);
  const [checking, setChecking] = useState(false);
  const [availForm, setAvailForm] = useState({ crew_member_id: '', status: 'AVAILABLE', note: '' });
  const [fatigueForm, setFatigueForm] = useState({ crew_member_id: '', reason: '', hours_on_duty: '' });
  const [submitting, setSubmitting] = useState(false);
  const [toast, setToast] = useState('');

  const showToast = (msg: string) => { setToast(msg); setTimeout(() => setToast(''), 3000); };

  const load = useCallback(async () => {
    try {
      const r = await fetch(`${API}/api/v1/staffing/readiness`, { headers: { Authorization: getToken() } });
      if (r.ok) setSummary(await r.json());
    } finally { setLoading(false); }
  }, []);

  useEffect(() => { load(); const iv = setInterval(load, 15000); return () => clearInterval(iv); }, [load]);

  const runCheck = async () => {
    if (!checkCrew.crew_member_id) return;
    setChecking(true);
    setCheckResult(null);
    try {
      const [qr, ar] = await Promise.all([
        fetch(`${API}/api/v1/staffing/crew/${checkCrew.crew_member_id}/qualification?service_level=${checkCrew.service_level}`, { headers: { Authorization: getToken() } }),
        fetch(`${API}/api/v1/staffing/crew/${checkCrew.crew_member_id}/availability`, { headers: { Authorization: getToken() } }),
      ]);
      const qj = qr.ok ? await qr.json() : {};
      const aj = ar.ok ? await ar.json() : {};
      setCheckResult({ qualification: qj, availability: aj });
    } finally { setChecking(false); }
  };

  const setAvailability = async () => {
    if (!availForm.crew_member_id) return;
    setSubmitting(true);
    try {
      const r = await fetch(`${API}/api/v1/staffing/crew/${availForm.crew_member_id}/availability`, {
        method: 'POST', headers: { Authorization: getToken(), 'Content-Type': 'application/json' },
        body: JSON.stringify(availForm),
      });
      if (r.ok) { showToast('Availability updated'); load(); setAvailForm({ crew_member_id: '', status: 'AVAILABLE', note: '' }); }
    } finally { setSubmitting(false); }
  };

  const flagFatigue = async () => {
    if (!fatigueForm.crew_member_id || !fatigueForm.reason) return;
    setSubmitting(true);
    try {
      const r = await fetch(`${API}/api/v1/staffing/crew/${fatigueForm.crew_member_id}/fatigue-flag`, {
        method: 'POST', headers: { Authorization: getToken(), 'Content-Type': 'application/json' },
        body: JSON.stringify({ reason: fatigueForm.reason, hours_on_duty: fatigueForm.hours_on_duty ? parseFloat(fatigueForm.hours_on_duty) : undefined }),
      });
      if (r.ok) { showToast('Fatigue flag set — crew will be flagged before assignment'); load(); setFatigueForm({ crew_member_id: '', reason: '', hours_on_duty: '' }); }
    } finally { setSubmitting(false); }
  };

  const overallColor = summary?.overall_readiness === 'READY' ? '#4caf50' : summary?.overall_readiness === 'WARNING' ? '#ffc107' : '#ef5350';

  return (
    <div className="p-6 space-y-6 max-w-[1600px] mx-auto">
      {toast && (
        <div className="fixed top-4 right-4 z-50 bg-blue-600 text-white px-4 py-2 chamfer-8 text-sm font-medium shadow-lg">{toast}</div>
      )}

      {/* ── Header ── */}
      <div className="flex items-center justify-between">
        <div>
          <Link href="/founder/ops" className="text-body text-orange-400 hover:text-orange-300 mb-1 block">← Ops Command</Link>
          <h1 className="text-2xl font-black text-white">Staffing & Response Readiness</h1>
          <p className="text-sm text-text-muted mt-1">
            Crew qualifications · Availability · Conflict detection · Fatigue flags · Audit
          </p>
        </div>
        {summary && <StateBadge state={summary.overall_readiness} color={overallColor} />}
      </div>

      {/* ── Hard Rules Notice ── */}
      <div className="p-3 chamfer-4-xl border border-amber-400/[0.3] bg-amber-400/[0.06]">
        <div className="text-micro uppercase tracking-widest text-yellow-400 mb-1">Deterministic Staffing Rules</div>
        <div className="text-body text-text-primary">
          No unit will be assigned to crew lacking required certification. No silent override of staffing conflicts.
          All overrides create a permanent audit record. AI may explain risk — hard rules are not AI decisions.
        </div>
      </div>

      {/* ── Summary Cards ── */}
      {summary && (
        <div className="grid grid-cols-2 md:grid-cols-6 gap-3">
          {[
            { label: 'Total Crew', value: summary.total_crew, color: 'white' },
            { label: 'Available', value: summary.available, color: '#4caf50' },
            { label: 'Assigned', value: summary.assigned, color: '#29b6f6' },
            { label: 'Unavailable', value: summary.unavailable, color: '#78909c' },
            { label: 'Fatigue Flags', value: summary.fatigue_flags, color: summary.fatigue_flags > 0 ? '#ffc107' : '#4caf50' },
            { label: 'Conflicts', value: summary.active_conflicts, color: summary.active_conflicts > 0 ? '#ef5350' : '#4caf50' },
          ].map(item => (
            <div key={item.label} className="chamfer-4-xl p-4 border border-white/[0.08] bg-white/[0.03] text-center">
              <div className="text-3xl font-black" style={{ color: item.color }}>{item.value}</div>
              <div className="text-micro uppercase tracking-widest text-text-muted mt-1">{item.label}</div>
            </div>
          ))}
        </div>
      )}

      {/* ── Qualified by Service Level ── */}
      {summary?.qualified_by_service_level && (
        <Panel>
          <div className="text-micro uppercase tracking-widest text-text-muted mb-3">
            Qualified Crew by Service Level
          </div>
          <div className="grid grid-cols-4 gap-3">
            {SERVICE_LEVELS.map(level => {
              const count = summary.qualified_by_service_level[level] ?? 0;
              const cert = CERT_FOR_LEVEL[level];
              return (
                <div key={level} className="text-center p-3 chamfer-8 bg-white/[0.04]">
                  <div className="text-2xl font-black" style={{ color: count > 0 ? '#4caf50' : '#ef5350' }}>{count}</div>
                  <div className="text-sm font-bold text-white mt-0.5">{level}</div>
                  <div className="text-micro text-text-muted">Min: {cert}</div>
                </div>
              );
            })}
          </div>
        </Panel>
      )}

      {/* ── Staffing Gaps ── */}
      {(summary?.staffing_gaps ?? []).length > 0 && (
        <div className="space-y-2">
          <div className="text-micro uppercase tracking-widest text-text-muted">Active Staffing Gaps</div>
          {summary!.staffing_gaps.map((gap, i) => (
            <div key={i} className="p-3 chamfer-4-xl border border-brand-orange/[0.3] bg-brand-orange/[0.08]">
              <div className="text-micro font-bold uppercase text-orange-400 mb-0.5">{gap.type.replace(/_/g, ' ')}</div>
              <div className="text-sm text-white">{gap.message}</div>
            </div>
          ))}
        </div>
      )}

      {/* ── Tabs ── */}
      <div className="flex gap-2">
        {(['summary', 'check', 'availability', 'fatigue'] as const).map(tab => (
          <button key={tab} onClick={() => setActiveTab(tab)} className={`px-4 py-2 chamfer-8 text-body font-bold uppercase tracking-wider ${activeTab === tab ? 'bg-yellow-700 text-white' : 'bg-white/[0.06] text-text-secondary'}`}>
            {tab === 'summary' ? 'Summary' : tab === 'check' ? 'Qualification Check' : tab === 'availability' ? 'Set Availability' : 'Fatigue Flag'}
          </button>
        ))}
      </div>

      {/* ── Qualification Check ── */}
      {activeTab === 'check' && (
        <Panel>
          <div className="text-micro uppercase tracking-widest text-text-muted mb-3">
            Deterministic Qualification Check
          </div>
          <div className="text-body text-text-secondary mb-4">
            This check cannot be silently overridden. Results reflect actual active certifications.
          </div>
          <div className="grid grid-cols-3 gap-3 mb-3">
            <input value={checkCrew.crew_member_id} onChange={e => setCheckCrew(p => ({ ...p, crew_member_id: e.target.value }))}
              placeholder="Crew Member ID *"
              className="h-9 bg-white/[0.06] border border-white/[0.12] px-3 text-sm text-white chamfer-8 focus:outline-none focus:border-yellow-400 placeholder-text-text-muted" />
            <select value={checkCrew.service_level} onChange={e => setCheckCrew(p => ({ ...p, service_level: e.target.value }))}
              className="h-9 bg-white/[0.06] border border-white/[0.12] px-3 text-sm text-white chamfer-8 focus:outline-none focus:border-yellow-400">
              {SERVICE_LEVELS.map(s => <option key={s} value={s}>{s} — requires {CERT_FOR_LEVEL[s]}</option>)}
            </select>
            <button onClick={runCheck} disabled={checking || !checkCrew.crew_member_id}
              className="h-9 px-6 bg-yellow-700 text-white text-sm font-bold chamfer-8 hover:bg-yellow-600 disabled:opacity-40">
              {checking ? 'Checking…' : 'Run Check'}
            </button>
          </div>
          {checkResult && (
            <div className="space-y-3 mt-4">
              <div className="grid grid-cols-2 gap-3">
                <div className="p-4 chamfer-4-xl border" style={{
                  borderColor: ((checkResult.qualification as Record<string, unknown>)?.qualified ? '#4caf50' : '#ef5350') + '44',
                  background: ((checkResult.qualification as Record<string, unknown>)?.qualified ? '#4caf50' : '#ef5350') + '0a',
                }}>
                  <div className="text-micro uppercase tracking-wider text-text-muted mb-2">Qualification</div>
                  <div className="text-lg font-black" style={{ color: (checkResult.qualification as Record<string, unknown>)?.qualified ? '#4caf50' : '#ef5350' }}>
                    {(checkResult.qualification as Record<string, unknown>)?.qualified ? '✓ QUALIFIED' : '✗ NOT QUALIFIED'}
                  </div>
                  <div className="text-body text-text-secondary mt-1">
                    Highest cert: {String((checkResult.qualification as Record<string, unknown>)?.highest_active_certification ?? 'NONE')}
                  </div>
                  {((checkResult.qualification as Record<string, unknown>)?.blocking_reasons as string[])?.map((r: string, i: number) => (
                    <div key={i} className="text-body text-red-400 mt-1">{r}</div>
                  ))}
                </div>
                <div className="p-4 chamfer-4-xl border" style={{
                  borderColor: ((checkResult.availability as Record<string, unknown>)?.available ? '#4caf50' : '#ef5350') + '44',
                  background: ((checkResult.availability as Record<string, unknown>)?.available ? '#4caf50' : '#ef5350') + '0a',
                }}>
                  <div className="text-micro uppercase tracking-wider text-text-muted mb-2">Availability</div>
                  <div className="text-lg font-black" style={{ color: (checkResult.availability as Record<string, unknown>)?.available ? '#4caf50' : '#ef5350' }}>
                    {String((checkResult.availability as Record<string, unknown>)?.state ?? 'UNKNOWN').replace(/_/g, ' ')}
                  </div>
                  <div className="text-body text-text-secondary mt-1">
                    Status: {String((checkResult.availability as Record<string, unknown>)?.availability_status ?? '—')}
                  </div>
                  {((checkResult.availability as Record<string, unknown>)?.warnings as string[])?.map((w: string, i: number) => (
                    <div key={i} className="text-body text-yellow-400 mt-1">⚠ {w}</div>
                  ))}
                </div>
              </div>
            </div>
          )}
        </Panel>
      )}

      {/* ── Set Availability ── */}
      {activeTab === 'availability' && (
        <Panel>
          <div className="text-micro uppercase tracking-widest text-text-muted mb-3">Update Crew Availability</div>
          <div className="grid grid-cols-3 gap-3 mb-3">
            <input value={availForm.crew_member_id} onChange={e => setAvailForm(p => ({ ...p, crew_member_id: e.target.value }))}
              placeholder="Crew Member ID *"
              className="h-9 bg-white/[0.06] border border-white/[0.12] px-3 text-sm text-white chamfer-8 focus:outline-none focus:border-yellow-400 placeholder-text-text-muted" />
            <select value={availForm.status} onChange={e => setAvailForm(p => ({ ...p, status: e.target.value }))}
              className="h-9 bg-white/[0.06] border border-white/[0.12] px-3 text-sm text-white chamfer-8 focus:outline-none focus:border-yellow-400">
              {['AVAILABLE','ASSIGNED','UNAVAILABLE','OFF_DUTY','ON_STANDBY','SICK'].map(s => <option key={s} value={s}>{s}</option>)}
            </select>
            <input value={availForm.note} onChange={e => setAvailForm(p => ({ ...p, note: e.target.value }))}
              placeholder="Note (optional)"
              className="h-9 bg-white/[0.06] border border-white/[0.12] px-3 text-sm text-white chamfer-8 focus:outline-none focus:border-yellow-400 placeholder-text-text-muted" />
          </div>
          <button onClick={setAvailability} disabled={submitting || !availForm.crew_member_id}
            className="px-6 py-2 bg-yellow-700 text-white text-sm font-bold chamfer-8 hover:bg-yellow-600 disabled:opacity-40">
            {submitting ? 'Updating…' : 'Update Availability'}
          </button>
        </Panel>
      )}

      {/* ── Fatigue Flag ── */}
      {activeTab === 'fatigue' && (
        <Panel>
          <div className="text-micro uppercase tracking-widest text-text-muted mb-3">Flag Crew for Fatigue Review</div>
          <div className="text-body text-text-secondary mb-4">
            Fatigue flags prevent silent assignment. Flagged crew must be explicitly cleared with a reason before dispatch.
            All actions are audited permanently.
          </div>
          <div className="grid grid-cols-3 gap-3 mb-3">
            <input value={fatigueForm.crew_member_id} onChange={e => setFatigueForm(p => ({ ...p, crew_member_id: e.target.value }))}
              placeholder="Crew Member ID *"
              className="h-9 bg-white/[0.06] border border-white/[0.12] px-3 text-sm text-white chamfer-8 focus:outline-none focus:border-orange-400 placeholder-text-text-muted" />
            <input value={fatigueForm.reason} onChange={e => setFatigueForm(p => ({ ...p, reason: e.target.value }))}
              placeholder="Reason for flag *"
              className="h-9 bg-white/[0.06] border border-white/[0.12] px-3 text-sm text-white chamfer-8 focus:outline-none focus:border-orange-400 placeholder-text-text-muted" />
            <input value={fatigueForm.hours_on_duty} onChange={e => setFatigueForm(p => ({ ...p, hours_on_duty: e.target.value }))}
              placeholder="Hours on duty (optional)"
              type="number"
              className="h-9 bg-white/[0.06] border border-white/[0.12] px-3 text-sm text-white chamfer-8 focus:outline-none focus:border-orange-400 placeholder-text-text-muted" />
          </div>
          <button onClick={flagFatigue} disabled={submitting || !fatigueForm.crew_member_id || !fatigueForm.reason}
            className="px-6 py-2 bg-orange-700 text-white text-sm font-bold chamfer-8 hover:bg-orange-600 disabled:opacity-40">
            {submitting ? 'Flagging…' : '⚠ Flag for Fatigue Review'}
          </button>
        </Panel>
      )}
    </div>
  );
}
