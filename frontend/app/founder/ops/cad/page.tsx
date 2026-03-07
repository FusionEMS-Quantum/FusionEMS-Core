'use client';
import { useState, useEffect, useCallback } from 'react';
import Link from 'next/link';

const API = process.env.NEXT_PUBLIC_API_URL || '';
const getToken = () => typeof window !== 'undefined' ? 'Bearer ' + (localStorage.getItem('qs_token') || '') : '';

const STATE_COLORS: Record<string, { bg: string; text: string }> = {
  NEW_REQUEST:          { bg: 'rgba(120,130,140,0.2)', text: '#78909c' },
  TRIAGED:              { bg: 'rgba(41,182,246,0.15)', text: '#29b6f6' },
  READY_FOR_ASSIGNMENT: { bg: 'rgba(255,193,7,0.15)',  text: '#ffc107' },
  UNIT_RECOMMENDED:     { bg: 'rgba(255,193,7,0.15)',  text: '#ffc107' },
  CREW_RECOMMENDED:     { bg: 'rgba(255,193,7,0.15)',  text: '#ffc107' },
  ASSIGNED:             { bg: 'rgba(41,182,246,0.15)', text: '#29b6f6' },
  PAGE_SENT:            { bg: 'rgba(41,182,246,0.15)', text: '#29b6f6' },
  ACK_PENDING:          { bg: 'rgba(255,107,26,0.15)', text: '#ff6b1a' },
  ACCEPTED:             { bg: 'rgba(76,175,80,0.15)',  text: '#4caf50' },
  EN_ROUTE:             { bg: 'rgba(76,175,80,0.20)',  text: '#66bb6a' },
  ON_SCENE:             { bg: 'rgba(76,175,80,0.25)',  text: '#81c784' },
  TRANSPORTING:         { bg: 'rgba(41,182,246,0.20)', text: '#4fc3f7' },
  ARRIVED_DESTINATION:  { bg: 'rgba(76,175,80,0.15)',  text: '#4caf50' },
  HANDOFF_COMPLETE:     { bg: 'rgba(76,175,80,0.12)',  text: '#a5d6a7' },
  CHART_PENDING:        { bg: 'rgba(41,182,246,0.1)',  text: '#81d4fa' },
  CLOSED:               { bg: 'rgba(120,130,140,0.1)', text: '#546e7a' },
  CANCELLED:            { bg: 'rgba(229,57,53,0.1)',   text: '#ef9a9a' },
};

const PRIORITY_COLORS: Record<string, string> = {
  P1: '#ef5350', ECHO: '#ef5350', DELTA: '#ef5350',
  P2: '#ff6b1a', P3: '#ffc107', ROUTINE: '#78909c',
};

const STATE_SEQUENCE = [
  'NEW_REQUEST','TRIAGED','READY_FOR_ASSIGNMENT','ASSIGNED','PAGE_SENT',
  'ACK_PENDING','ACCEPTED','EN_ROUTE','ON_SCENE','TRANSPORTING',
  'ARRIVED_DESTINATION','HANDOFF_COMPLETE','CHART_PENDING','CLOSED',
];

function Panel({ children, className = '' }: { children: React.ReactNode; className?: string }) {
  return (
    <div className={`bg-white/[0.03] border border-white/[0.08] chamfer-8 p-4 ${className}`}>
      {children}
    </div>
  );
}

function StateBadge({ state }: { state: string }) {
  const c = STATE_COLORS[state] ?? { bg: 'rgba(120,130,140,0.2)', text: '#78909c' };
  return (
    <span className="inline-block px-2 py-0.5 chamfer-4 text-micro font-bold uppercase tracking-wider"
      style={{ background: c.bg, color: c.text }}>
      {state.replace(/_/g, ' ')}
    </span>
  );
}

interface Mission {
  id: string;
  data: {
    state: string;
    service_level: string;
    priority: string;
    chief_complaint: string;
    origin_address: string;
    destination_address?: string;
    assigned_unit_id?: string;
    created_at: string;
    state_updated_at: string;
  };
}

interface TransitionResult {
  current_state?: string;
  previous_state?: string;
  error?: string;
  reason?: string;
  override_available?: boolean;
}

export default function CadDispatchPage() {
  const [missions, setMissions] = useState<Mission[]>([]);
  const [loading, setLoading] = useState(true);
  const [selected, setSelected] = useState<Mission | null>(null);
  const [transitioning, setTransitioning] = useState(false);
  const [transitionResult, setTransitionResult] = useState<TransitionResult | null>(null);
  const [overrideReason, setOverrideReason] = useState('');
  const [filterState, setFilterState] = useState('');
  const [creating, setCreating] = useState(false);
  const [newRequest, setNewRequest] = useState({ service_level: 'BLS', priority: 'P2', origin_address: '', chief_complaint: '' });
  const [toast, setToast] = useState('');

  const showToast = (msg: string) => { setToast(msg); setTimeout(() => setToast(''), 3000); };

  const load = useCallback(async () => {
    try {
      const r = await fetch(`${API}/api/v1/dispatch/missions?limit=100`, { headers: { Authorization: getToken() } });
      if (r.ok) { const j = await r.json(); setMissions(j.missions ?? []); }
    } finally { setLoading(false); }
  }, []);

  useEffect(() => { load(); const iv = setInterval(load, 10000); return () => clearInterval(iv); }, [load]);

  const transition = async (missionId: string, state: string, override = false) => {
    setTransitioning(true);
    setTransitionResult(null);
    try {
      const body: Record<string, unknown> = { state };
      if (override) { body.override = true; body.override_reason = overrideReason; }
      const r = await fetch(`${API}/api/v1/dispatch/missions/${missionId}/transition`, {
        method: 'POST', headers: { Authorization: getToken(), 'Content-Type': 'application/json' },
        body: JSON.stringify(body),
      });
      const j = await r.json();
      setTransitionResult(j);
      if (!j.error) { showToast(`Transitioned to ${state}`); load(); }
    } finally { setTransitioning(false); }
  };

  const createRequest = async () => {
    if (!newRequest.origin_address) return;
    setCreating(true);
    try {
      // 1. Create request
      const r1 = await fetch(`${API}/api/v1/dispatch/requests`, {
        method: 'POST', headers: { Authorization: getToken(), 'Content-Type': 'application/json' },
        body: JSON.stringify(newRequest),
      });
      const req = await r1.json();
      if (req.id) {
        // 2. Inject to CAD
        await fetch(`${API}/api/v1/dispatch/requests/${req.id}/inject`, {
          method: 'POST', headers: { Authorization: getToken(), 'Content-Type': 'application/json' },
          body: JSON.stringify({}),
        });
        showToast('Mission created and injected to CAD');
        setNewRequest({ service_level: 'BLS', priority: 'P2', origin_address: '', chief_complaint: '' });
        load();
      }
    } finally { setCreating(false); }
  };

  const filtered = filterState
    ? missions.filter(m => m.data?.state === filterState)
    : missions;

  const unassigned = missions.filter(m => ['NEW_REQUEST','TRIAGED','READY_FOR_ASSIGNMENT'].includes(m.data?.state));
  const active = missions.filter(m => !['CLOSED','CANCELLED'].includes(m.data?.state));

  return (
    <div className="p-6 space-y-6 max-w-[1600px] mx-auto">
      {toast && (
        <div className="fixed top-4 right-4 z-50 bg-green-600 text-white px-4 py-2 chamfer-8 text-sm font-medium shadow-lg">{toast}</div>
      )}

      {/* ── Header ── */}
      <div className="flex items-center justify-between">
        <div>
          <Link href="/founder/ops" className="text-body text-orange-400 hover:text-orange-300 mb-1 block">← Ops Command</Link>
          <h1 className="text-2xl font-black text-white">CAD / Dispatch</h1>
          <p className="text-sm text-text-muted mt-1">Mission intake · State machine · Unit & crew assignment · Full audit trail</p>
        </div>
        <div className="flex items-center gap-3">
          <div className="px-3 py-1.5 bg-brand-orange/[0.1] border border-brand-orange/[0.3] chamfer-8">
            <span className="text-orange-400 text-sm font-bold">{active.length}</span>
            <span className="text-micro text-text-muted ml-1">ACTIVE</span>
          </div>
          <div className="px-3 py-1.5 bg-red-600/[0.1] border border-red-600/[0.3] chamfer-8">
            <span className="text-red-400 text-sm font-bold">{unassigned.length}</span>
            <span className="text-micro text-text-muted ml-1">UNASSIGNED</span>
          </div>
          <button onClick={load} className="px-3 py-1.5 bg-white/[0.06] border border-white/[0.12] text-body chamfer-8 hover:bg-white/10">
            ↻ Refresh
          </button>
        </div>
      </div>

      {/* ── CAD State Machine Legend ── */}
      <Panel>
        <div className="text-micro uppercase tracking-widest text-text-muted mb-3">Mission State Machine</div>
        <div className="flex flex-wrap gap-1.5">
          {STATE_SEQUENCE.map((s, i) => (
            <span key={s} className="flex items-center gap-1">
              <StateBadge state={s} />
              {i < STATE_SEQUENCE.length - 1 && <span className="text-text-muted text-xs">→</span>}
            </span>
          ))}
        </div>
      </Panel>

      {/* ── New Mission Intake ── */}
      <Panel>
        <div className="text-micro uppercase tracking-widest text-text-muted mb-3">New Dispatch Request</div>
        <div className="grid grid-cols-2 md:grid-cols-4 gap-3 mb-3">
          <select value={newRequest.service_level} onChange={e => setNewRequest(p => ({ ...p, service_level: e.target.value }))}
            className="h-9 bg-white/[0.06] border border-white/[0.12] px-3 text-sm text-white chamfer-8 focus:outline-none focus:border-orange-400">
            {['BLS','ALS','CCT','HEMS'].map(s => <option key={s} value={s}>{s}</option>)}
          </select>
          <select value={newRequest.priority} onChange={e => setNewRequest(p => ({ ...p, priority: e.target.value }))}
            className="h-9 bg-white/[0.06] border border-white/[0.12] px-3 text-sm text-white chamfer-8 focus:outline-none focus:border-orange-400">
            {['P1','P2','P3','ROUTINE','ECHO','DELTA'].map(s => <option key={s} value={s}>{s}</option>)}
          </select>
          <input value={newRequest.origin_address} onChange={e => setNewRequest(p => ({ ...p, origin_address: e.target.value }))}
            placeholder="Origin address *"
            className="h-9 bg-white/[0.06] border border-white/[0.12] px-3 text-sm text-white chamfer-8 focus:outline-none focus:border-orange-400 placeholder-text-text-muted" />
          <input value={newRequest.chief_complaint} onChange={e => setNewRequest(p => ({ ...p, chief_complaint: e.target.value }))}
            placeholder="Chief complaint"
            className="h-9 bg-white/[0.06] border border-white/[0.12] px-3 text-sm text-white chamfer-8 focus:outline-none focus:border-orange-400 placeholder-text-text-muted" />
        </div>
        <button onClick={createRequest} disabled={creating || !newRequest.origin_address}
          className="px-6 py-2 bg-orange-600 text-white text-sm font-bold chamfer-8 hover:bg-orange-500 disabled:opacity-40 transition-colors">
          {creating ? 'Creating…' : '+ Create Mission'}
        </button>
      </Panel>

      {/* ── Filter ── */}
      <div className="flex items-center gap-2">
        <span className="text-micro uppercase tracking-widest text-text-muted">Filter by state:</span>
        <button onClick={() => setFilterState('')} className={`px-2 py-1 chamfer-4 text-micro font-bold ${!filterState ? 'bg-orange-600 text-white' : 'bg-white/[0.06] text-text-secondary'}`}>ALL</button>
        {['NEW_REQUEST','READY_FOR_ASSIGNMENT','ASSIGNED','EN_ROUTE','ON_SCENE','TRANSPORTING'].map(s => (
          <button key={s} onClick={() => setFilterState(s)} className={`px-2 py-1 chamfer-4 text-micro font-bold ${filterState === s ? 'bg-orange-600 text-white' : 'bg-white/[0.06] text-text-secondary'}`}>
            {s.replace(/_/g, ' ')}
          </button>
        ))}
      </div>

      {/* ── Mission List ── */}
      <div className="space-y-2">
        {loading && <div className="text-sm text-text-muted p-4">Loading missions…</div>}
        {!loading && filtered.length === 0 && (
          <div className="text-center py-10 chamfer-4-xl border border-white/[0.08]">
            <div className="text-3xl mb-2">📡</div>
            <div className="text-sm text-text-muted">No missions found. Create a new dispatch request above.</div>
          </div>
        )}
        {filtered.map(m => {
          const d = m.data ?? {};
          const isSelected = selected?.id === m.id;
          const stateColor = STATE_COLORS[d.state] ?? { bg: 'rgba(120,130,140,0.1)', text: '#78909c' };
          const priorityColor = PRIORITY_COLORS[d.priority] ?? '#78909c';

          return (
            <div key={m.id} className="chamfer-4-xl border border-white/[0.08] overflow-hidden">
              <button onClick={() => setSelected(isSelected ? null : m)}
                className="w-full flex items-center gap-4 p-4 text-left hover:bg-white/[0.03] transition-colors">
                <div className="flex-shrink-0">
                  <div className="text-micro font-bold uppercase tracking-widest" style={{ color: priorityColor }}>{d.priority}</div>
                  <div className="text-body font-bold text-white mt-0.5">{d.service_level}</div>
                </div>
                <div className="flex-1 min-w-0">
                  <div className="text-sm font-semibold text-white truncate">{d.chief_complaint || 'No complaint recorded'}</div>
                  <div className="text-body text-text-muted truncate">{d.origin_address}</div>
                </div>
                <div className="flex items-center gap-2 flex-shrink-0">
                  <StateBadge state={d.state} />
                  {d.assigned_unit_id && <span className="text-micro text-green-400">Unit: {d.assigned_unit_id.slice(0, 8)}</span>}
                  <span className="text-text-muted text-sm">{isSelected ? '▲' : '▼'}</span>
                </div>
              </button>

              {isSelected && (
                <div className="px-4 pb-4 border-t border-white/[0.06] space-y-4">
                  {/* State transition controls */}
                  <div className="mt-4">
                    <div className="text-micro uppercase tracking-widest text-text-muted mb-2">Transition State</div>
                    <div className="flex flex-wrap gap-2">
                      {STATE_SEQUENCE
                        .filter(s => s !== d.state && !['CANCELLED','CLOSED'].includes(d.state))
                        .slice(0, 6)
                        .map(s => (
                          <button key={s} onClick={() => transition(m.id, s)}
                            disabled={transitioning}
                            className="px-3 py-1.5 chamfer-8 text-body font-semibold border border-white/[0.12] text-white hover:bg-white/[0.08] disabled:opacity-40 transition-colors">
                            → {s.replace(/_/g, ' ')}
                          </button>
                        ))
                      }
                    </div>
                    {transitionResult?.error === 'invalid_transition' && (
                      <div className="mt-3 space-y-2">
                        <div className="text-body text-yellow-400">{transitionResult.reason}</div>
                        <input value={overrideReason} onChange={e => setOverrideReason(e.target.value)}
                          placeholder="Override reason (required for manual override)"
                          className="w-full h-8 bg-brand-orange/[0.1] border border-brand-orange/[0.3] px-3 text-body text-white chamfer-8 focus:outline-none placeholder-text-text-muted" />
                        <button onClick={() => transition(m.id, selected?.data?.state || '', true)}
                          disabled={!overrideReason}
                          className="px-4 py-1.5 bg-orange-700 text-white text-body font-bold chamfer-8 hover:bg-orange-600 disabled:opacity-40">
                          Apply Manual Override
                        </button>
                      </div>
                    )}
                    {transitionResult && !transitionResult.error && (
                      <div className="mt-2 text-body text-green-400">
                        ✓ {transitionResult.previous_state} → {transitionResult.current_state}
                      </div>
                    )}
                  </div>

                  {/* Mission details */}
                  <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
                    <div>
                      <div className="text-micro uppercase tracking-wider text-text-muted">Mission ID</div>
                      <div className="text-body text-white font-mono">{m.id.slice(0, 16)}</div>
                    </div>
                    <div>
                      <div className="text-micro uppercase tracking-wider text-text-muted">Destination</div>
                      <div className="text-body text-white">{d.destination_address || 'Not set'}</div>
                    </div>
                    <div>
                      <div className="text-micro uppercase tracking-wider text-text-muted">Created</div>
                      <div className="text-body text-white">{d.created_at ? new Date(d.created_at).toLocaleString() : '—'}</div>
                    </div>
                    <div>
                      <div className="text-micro uppercase tracking-wider text-text-muted">Last State Change</div>
                      <div className="text-body text-white">{d.state_updated_at ? new Date(d.state_updated_at).toLocaleString() : '—'}</div>
                    </div>
                  </div>

                  {/* Cancel */}
                  {!['CLOSED','CANCELLED'].includes(d.state) && (
                    <div>
                      <button
                        onClick={async () => {
                          const reason = window.prompt('Cancel reason (required):');
                          if (reason) {
                            await fetch(`${API}/api/v1/dispatch/missions/${m.id}/cancel`, {
                              method: 'POST', headers: { Authorization: getToken(), 'Content-Type': 'application/json' },
                              body: JSON.stringify({ reason }),
                            });
                            showToast('Mission cancelled'); load();
                          }
                        }}
                        className="px-4 py-1.5 bg-red-600/[0.1] border border-red-600/[0.3] text-red-400 text-body font-bold chamfer-8 hover:bg-red-600/[0.15]">
                        Cancel Mission
                      </button>
                    </div>
                  )}
                </div>
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
}
