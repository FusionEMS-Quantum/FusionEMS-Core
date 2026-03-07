'use client';
import { useState, useEffect, useCallback } from 'react';
import Link from 'next/link';

const API = process.env.NEXT_PUBLIC_API_URL || '';
const getToken = () => typeof window !== 'undefined' ? 'Bearer ' + (localStorage.getItem('qs_token') || '') : '';

const PAGE_STATE_COLORS: Record<string, { bg: string; text: string }> = {
  ALERT_CREATED:     { bg: 'rgba(120,130,140,0.2)', text: '#78909c' },
  TARGETS_RESOLVED:  { bg: 'rgba(41,182,246,0.15)', text: '#29b6f6' },
  PUSH_SENT:         { bg: 'rgba(41,182,246,0.2)',  text: '#4fc3f7' },
  PUSH_DELIVERED:    { bg: 'rgba(41,182,246,0.25)', text: '#81d4fa' },
  ACKNOWLEDGED:      { bg: 'rgba(255,193,7,0.15)',  text: '#ffc107' },
  ACCEPTED:          { bg: 'rgba(76,175,80,0.2)',   text: '#4caf50' },
  DECLINED:          { bg: 'rgba(229,57,53,0.15)',  text: '#ef5350' },
  NO_RESPONSE:       { bg: 'rgba(229,57,53,0.12)',  text: '#ef9a9a' },
  ESCALATED:         { bg: 'rgba(229,57,53,0.2)',   text: '#f44336' },
  BACKUP_ALERT_SENT: { bg: 'rgba(255,107,26,0.2)',  text: '#ff6b1a' },
  CLOSED:            { bg: 'rgba(120,130,140,0.1)', text: '#546e7a' },
};

const PAGING_FLOW = ['ALERT_CREATED','TARGETS_RESOLVED','PUSH_SENT','PUSH_DELIVERED','ACKNOWLEDGED','ACCEPTED'];

function Panel({ children, className = '' }: { children: React.ReactNode; className?: string }) {
  return (
    <div className={`bg-white/[0.03] border border-white/[0.08] chamfer-8 p-4 ${className}`}>
      {children}
    </div>
  );
}

function StateBadge({ state }: { state: string }) {
  const c = PAGE_STATE_COLORS[state] ?? { bg: 'rgba(120,130,140,0.2)', text: '#78909c' };
  return (
    <span className="inline-block px-2 py-0.5 chamfer-4 text-micro font-bold uppercase tracking-wider"
      style={{ background: c.bg, color: c.text }}>
      {state.replace(/_/g, ' ')}
    </span>
  );
}

interface Alert {
  id: string;
  data: {
    state: string;
    mission_id: string;
    mission_title: string;
    mission_address: string;
    service_level: string;
    priority: string;
    chief_complaint: string;
    target_crew_ids: string[];
    accepted_by?: string;
    escalated_at?: string;
    ack_deadline: string;
    accept_deadline: string;
    is_backup?: boolean;
    created_at: string;
  };
}

export default function CrewLinkPagingPage() {
  const [alerts, setAlerts] = useState<Alert[]>([]);
  const [loading, setLoading] = useState(true);
  const [selected, setSelected] = useState<Alert | null>(null);
  const [newAlert, setNewAlert] = useState({
    mission_id: '', mission_title: '', mission_address: '',
    service_level: 'BLS', priority: 'P2', chief_complaint: '',
    target_crew_ids: '',
  });
  const [creating, setCreating] = useState(false);
  const [toast, setToast] = useState('');
  const [filterState, setFilterState] = useState('active');

  const showToast = (msg: string) => { setToast(msg); setTimeout(() => setToast(''), 3000); };

  const load = useCallback(async () => {
    try {
      const endpoint = filterState === 'active'
        ? `${API}/api/v1/crewlink/alerts/active`
        : `${API}/api/v1/crewlink/alerts?limit=100`;
      const r = await fetch(endpoint, { headers: { Authorization: getToken() } });
      if (r.ok) { const j = await r.json(); setAlerts(j.alerts ?? j ?? []); }
    } finally { setLoading(false); }
  }, [filterState]);

  useEffect(() => { load(); const iv = setInterval(load, 10000); return () => clearInterval(iv); }, [load]);

  const createAlert = async () => {
    if (!newAlert.mission_id || !newAlert.mission_address) return;
    setCreating(true);
    try {
      const crewIds = newAlert.target_crew_ids.split(',').map(s => s.trim()).filter(Boolean);
      const r = await fetch(`${API}/api/v1/crewlink/alerts`, {
        method: 'POST', headers: { Authorization: getToken(), 'Content-Type': 'application/json' },
        body: JSON.stringify({ ...newAlert, target_crew_ids: crewIds }),
      });
      const j = await r.json();
      if (j.alert_id) {
        showToast(`Alert created — ${crewIds.length} crew paged`);
        setNewAlert({ mission_id: '', mission_title: '', mission_address: '', service_level: 'BLS', priority: 'P2', chief_complaint: '', target_crew_ids: '' });
        load();
      }
    } finally { setCreating(false); }
  };

  const escalate = async (alertId: string) => {
    const r = await fetch(`${API}/api/v1/crewlink/alerts/${alertId}/escalate`, {
      method: 'POST', headers: { Authorization: getToken(), 'Content-Type': 'application/json' },
      body: JSON.stringify({ reason: 'MANUAL_ESCALATION_BY_DISPATCHER', triggered_by: 'DISPATCHER' }),
    });
    const j = await r.json();
    if (!j.error) { showToast('Alert escalated'); load(); }
  };

  const escalated = alerts.filter(a => a.data?.state === 'ESCALATED');
  const noResponse = alerts.filter(a => a.data?.state === 'NO_RESPONSE');
  const accepted = alerts.filter(a => a.data?.state === 'ACCEPTED');
  const pending = alerts.filter(a => ['PUSH_SENT','PUSH_DELIVERED','ACKNOWLEDGED','ACK_PENDING','TARGETS_RESOLVED','ALERT_CREATED'].includes(a.data?.state));

  return (
    <div className="p-6 space-y-6 max-w-[1600px] mx-auto">
      {toast && (
        <div className="fixed top-4 right-4 z-50 bg-blue-600 text-white px-4 py-2 chamfer-8 text-sm font-medium shadow-lg">{toast}</div>
      )}

      {/* ── Header ── */}
      <div className="flex items-center justify-between">
        <div>
          <Link href="/founder/ops" className="text-body text-orange-400 hover:text-orange-300 mb-1 block">← Ops Command</Link>
          <h1 className="text-2xl font-black text-white">CrewLink Paging</h1>
          <p className="text-sm text-text-muted mt-1">
            Android push paging · ACK/Accept/Decline · Escalation · Backup crew · Audit
          </p>
        </div>
        <div className="px-3 py-2 chamfer-4-xl border border-brand-orange/[0.4] bg-brand-orange/[0.1]">
          <div className="text-micro uppercase tracking-wider text-orange-400">Boundary Enforced</div>
          <div className="text-body text-white">Operations only · No billing content</div>
        </div>
      </div>

      {/* ── Paging Flow ── */}
      <Panel>
        <div className="text-micro uppercase tracking-widest text-text-muted mb-3">Paging State Flow</div>
        <div className="flex flex-wrap gap-1.5">
          {PAGING_FLOW.map((s, i) => (
            <span key={s} className="flex items-center gap-1">
              <StateBadge state={s} />
              {i < PAGING_FLOW.length - 1 && <span className="text-text-muted text-xs">→</span>}
            </span>
          ))}
          <span className="text-text-muted text-xs mx-1">or</span>
          <StateBadge state="DECLINED" />
          <span className="text-text-muted text-xs">→</span>
          <StateBadge state="ESCALATED" />
          <span className="text-text-muted text-xs">→</span>
          <StateBadge state="BACKUP_ALERT_SENT" />
        </div>
      </Panel>

      {/* ── Status Cards ── */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
        {[
          { label: 'Escalated', value: escalated.length, color: '#ef5350', bg: 'rgba(229,57,53,0.12)' },
          { label: 'No Response', value: noResponse.length, color: '#ff6b1a', bg: 'rgba(255,107,26,0.12)' },
          { label: 'Awaiting Response', value: pending.length, color: '#ffc107', bg: 'rgba(255,193,7,0.1)' },
          { label: 'Accepted', value: accepted.length, color: '#4caf50', bg: 'rgba(76,175,80,0.1)' },
        ].map(item => (
          <div key={item.label} className="chamfer-4-xl p-4 border text-center" style={{ background: item.bg, borderColor: item.color + '44' }}>
            <div className="text-3xl font-black" style={{ color: item.color }}>{item.value}</div>
            <div className="text-micro uppercase tracking-widest text-text-secondary mt-1">{item.label}</div>
          </div>
        ))}
      </div>

      {/* ── New Alert ── */}
      <Panel>
        <div className="text-micro uppercase tracking-widest text-text-muted mb-3">Send CrewLink Page</div>
        <div className="grid grid-cols-2 md:grid-cols-3 gap-3 mb-3">
          <input value={newAlert.mission_id} onChange={e => setNewAlert(p => ({ ...p, mission_id: e.target.value }))}
            placeholder="Mission ID *"
            className="h-9 bg-white/[0.06] border border-white/[0.12] px-3 text-sm text-white chamfer-8 focus:outline-none focus:border-blue-400 placeholder-text-text-muted" />
          <input value={newAlert.mission_title} onChange={e => setNewAlert(p => ({ ...p, mission_title: e.target.value }))}
            placeholder="Mission title"
            className="h-9 bg-white/[0.06] border border-white/[0.12] px-3 text-sm text-white chamfer-8 focus:outline-none focus:border-blue-400 placeholder-text-text-muted" />
          <input value={newAlert.mission_address} onChange={e => setNewAlert(p => ({ ...p, mission_address: e.target.value }))}
            placeholder="Incident address *"
            className="h-9 bg-white/[0.06] border border-white/[0.12] px-3 text-sm text-white chamfer-8 focus:outline-none focus:border-blue-400 placeholder-text-text-muted" />
          <select value={newAlert.service_level} onChange={e => setNewAlert(p => ({ ...p, service_level: e.target.value }))}
            className="h-9 bg-white/[0.06] border border-white/[0.12] px-3 text-sm text-white chamfer-8 focus:outline-none focus:border-blue-400">
            {['BLS','ALS','CCT','HEMS'].map(s => <option key={s} value={s}>{s}</option>)}
          </select>
          <input value={newAlert.chief_complaint} onChange={e => setNewAlert(p => ({ ...p, chief_complaint: e.target.value }))}
            placeholder="Chief complaint"
            className="h-9 bg-white/[0.06] border border-white/[0.12] px-3 text-sm text-white chamfer-8 focus:outline-none focus:border-blue-400 placeholder-text-text-muted" />
          <input value={newAlert.target_crew_ids} onChange={e => setNewAlert(p => ({ ...p, target_crew_ids: e.target.value }))}
            placeholder="Crew IDs (comma separated)"
            className="h-9 bg-white/[0.06] border border-white/[0.12] px-3 text-sm text-white chamfer-8 focus:outline-none focus:border-blue-400 placeholder-text-text-muted" />
        </div>
        <button onClick={createAlert} disabled={creating || !newAlert.mission_id || !newAlert.mission_address}
          className="px-6 py-2 bg-blue-700 text-white text-sm font-bold chamfer-8 hover:bg-blue-600 disabled:opacity-40 transition-colors">
          {creating ? 'Sending…' : '📟 Send Page'}
        </button>
      </Panel>

      {/* ── Filter ── */}
      <div className="flex items-center gap-2">
        {['active','all'].map(f => (
          <button key={f} onClick={() => setFilterState(f)} className={`px-3 py-1.5 chamfer-8 text-body font-bold uppercase tracking-wide ${filterState === f ? 'bg-blue-700 text-white' : 'bg-white/[0.06] text-text-secondary'}`}>
            {f}
          </button>
        ))}
      </div>

      {/* ── Alert List ── */}
      <div className="space-y-2">
        {loading && <div className="text-sm text-text-muted p-4">Loading alerts…</div>}
        {!loading && alerts.length === 0 && (
          <div className="text-center py-10 chamfer-4-xl border border-white/[0.08]">
            <div className="text-3xl mb-2">📟</div>
            <div className="text-sm text-text-muted">No paging alerts. Use the form above to send a page.</div>
          </div>
        )}
        {alerts.map(alert => {
          const d = alert.data ?? {};
          const isSelected = selected?.id === alert.id;
          const isEscalated = d.state === 'ESCALATED';
          const isAccepted = d.state === 'ACCEPTED';

          return (
            <div key={alert.id} className={`chamfer-4-xl border overflow-hidden ${isEscalated ? 'border-red-500/40' : isAccepted ? 'border-green-500/30' : 'border-white/[0.08]'}`}>
              <button onClick={() => setSelected(isSelected ? null : alert)}
                className="w-full flex items-center gap-4 p-4 text-left hover:bg-white/[0.03] transition-colors">
                <div className="flex-shrink-0 text-center w-16">
                  <StateBadge state={d.state} />
                  {d.is_backup && <div className="text-[9px] text-orange-400 mt-1 uppercase font-bold">BACKUP</div>}
                </div>
                <div className="flex-1 min-w-0">
                  <div className="text-sm font-semibold text-white">{d.mission_title || d.mission_id?.slice(0, 8)}</div>
                  <div className="text-body text-text-secondary">{d.mission_address}</div>
                  {d.chief_complaint && <div className="text-body text-text-muted">{d.chief_complaint}</div>}
                </div>
                <div className="flex items-center gap-3 flex-shrink-0">
                  <div className="text-right">
                    <div className="text-micro text-text-muted">{d.service_level} · {d.priority}</div>
                    <div className="text-micro text-text-muted">{d.target_crew_ids?.length ?? 0} crew paged</div>
                  </div>
                  {isEscalated && !isSelected && (
                    <button onClick={e => { e.stopPropagation(); escalate(alert.id); }}
                      className="px-3 py-1 bg-red-700 text-white text-micro font-bold chamfer-8 hover:bg-red-600">
                      ESCALATE
                    </button>
                  )}
                  <span className="text-text-muted text-sm">{isSelected ? '▲' : '▼'}</span>
                </div>
              </button>

              {isSelected && (
                <div className="px-4 pb-4 border-t border-white/[0.06] space-y-4">
                  <div className="grid grid-cols-2 md:grid-cols-4 gap-3 mt-4">
                    <div>
                      <div className="text-micro uppercase tracking-wider text-text-muted">Alert ID</div>
                      <div className="text-body text-white font-mono">{alert.id.slice(0, 16)}</div>
                    </div>
                    <div>
                      <div className="text-micro uppercase tracking-wider text-text-muted">ACK Deadline</div>
                      <div className="text-body text-white">{d.ack_deadline ? new Date(d.ack_deadline).toLocaleTimeString() : '—'}</div>
                    </div>
                    <div>
                      <div className="text-micro uppercase tracking-wider text-text-muted">Accept Deadline</div>
                      <div className="text-body text-white">{d.accept_deadline ? new Date(d.accept_deadline).toLocaleTimeString() : '—'}</div>
                    </div>
                    <div>
                      <div className="text-micro uppercase tracking-wider text-text-muted">Accepted By</div>
                      <div className="text-body text-green-400">{d.accepted_by || '—'}</div>
                    </div>
                  </div>

                  <div className="flex gap-2">
                    {!['ACCEPTED','CLOSED'].includes(d.state) && (
                      <button onClick={() => escalate(alert.id)}
                        className="px-4 py-1.5 bg-red-600/[0.15] border border-red-600/[0.3] text-red-400 text-body font-bold chamfer-8 hover:bg-red-600/[0.2]">
                        🔺 Escalate Now
                      </button>
                    )}
                    <Link href={`/founder/ops/crewlink`} className="px-4 py-1.5 bg-blue-400/[0.1] border border-blue-400/[0.3] text-blue-400 text-body font-bold chamfer-8 hover:bg-blue-400/[0.15]">
                      View Full Audit →
                    </Link>
                  </div>
                </div>
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
}
