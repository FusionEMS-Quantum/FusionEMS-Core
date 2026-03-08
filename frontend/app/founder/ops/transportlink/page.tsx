'use client';
import { useState, useEffect, useCallback } from 'react';
import Link from 'next/link';

const API = process.env.NEXT_PUBLIC_API_URL || '';
const getToken = () => typeof window !== 'undefined' ? 'Bearer ' + (localStorage.getItem('qs_token') || '') : '';

const REQUEST_STATE_COLORS: Record<string, { bg: string; text: string }> = {
  REQUEST_CREATED:    { bg: 'rgba(120,130,140,0.2)', text: '#78909c' },
  REQUEST_VALIDATED:  { bg: 'rgba(41,182,246,0.15)', text: '#29b6f6' },
  REQUEST_REJECTED:   { bg: 'rgba(229,57,53,0.15)',  text: '#ef5350' },
  REQUEST_ACCEPTED:   { bg: 'rgba(76,175,80,0.15)',  text: '#4caf50' },
  DISPATCH_INJECTED:  { bg: 'rgba(255,107,26,0.15)', text: '#ff6b1a' },
  ASSIGNMENT_PENDING: { bg: 'rgba(255,193,7,0.15)',  text: '#ffc107' },
  CLOSED:             { bg: 'rgba(120,130,140,0.1)', text: '#546e7a' },
};

function Panel({ children, className = '' }: { children: React.ReactNode; className?: string }) {
  return (
    <div className={`bg-zinc-950/[0.03] border border-white/[0.08] chamfer-8 p-4 ${className}`}>
      {children}
    </div>
  );
}

function StateBadge({ state }: { state: string }) {
  const c = REQUEST_STATE_COLORS[state] ?? { bg: 'rgba(120,130,140,0.2)', text: '#78909c' };
  return (
    <span className="inline-block px-2 py-0.5 chamfer-4 text-micro font-bold uppercase tracking-wider"
      style={{ background: c.bg, color: c.text }}>
      {state.replace(/_/g, ' ')}
    </span>
  );
}

interface TransportRequest {
  id: string;
  data: {
    state: string;
    service_level: string;
    priority: string;
    origin_facility: string;
    destination_facility: string;
    origin_address: string;
    destination_address: string;
    chief_complaint: string;
    contact_name: string;
    contact_phone: string;
    submitted_at?: string;
    mission_id?: string;
  };
}

export default function TransportLinkPage() {
  const [requests, setRequests] = useState<TransportRequest[]>([]);
  const [loading, setLoading] = useState(true);
  const [selected, setSelected] = useState<TransportRequest | null>(null);
  const [newReq, setNewReq] = useState({
    origin_facility: '', destination_facility: '',
    origin_address: '', destination_address: '',
    service_level: 'BLS', priority: 'P2',
    chief_complaint: '', contact_name: '', contact_phone: '',
  });
  const [creating, setCreating] = useState(false);
  const [toast, setToast] = useState('');
  const [activeTab, setActiveTab] = useState<'requests' | 'new'>('requests');

  const showToast = (msg: string) => { setToast(msg); setTimeout(() => setToast(''), 3000); };

  const load = useCallback(async () => {
    try {
      const r = await fetch(`${API}/api/v1/dispatch/requests?limit=100`, { headers: { Authorization: getToken() } });
      if (r.ok) {
        const j = await r.json();
        // Filter to facility/interfacility requests
        const all = Array.isArray(j) ? j : (j.requests ?? j.data ?? []);
        setRequests(all.filter((r: TransportRequest) => r.data?.origin_facility));
      }
    } finally { setLoading(false); }
  }, []);

  // Also get from transportlink endpoint
  const loadTransportlink = useCallback(async () => {
    try {
      const r = await fetch(`${API}/api/v1/transportlink/facilities/00000000-0000-0000-0000-000000000000/schedule`, { headers: { Authorization: getToken() } });
      if (r.ok) {
        const all = await r.json();
        if (Array.isArray(all)) setRequests(prev => {
          const ids = new Set(prev.map(p => p.id));
          return [...prev, ...all.filter((r: TransportRequest) => !ids.has(r.id))];
        });
      }
    } catch { /* ignore */ }
  }, []);

  useEffect(() => { load(); loadTransportlink(); const iv = setInterval(load, 15000); return () => clearInterval(iv); }, [load, loadTransportlink]);

  const createRequest = async () => {
    if (!newReq.origin_address || !newReq.origin_facility) return;
    setCreating(true);
    try {
      const r = await fetch(`${API}/api/v1/dispatch/requests`, {
        method: 'POST', headers: { Authorization: getToken(), 'Content-Type': 'application/json' },
        body: JSON.stringify({
          ...newReq,
          request_type: 'INTERFACILITY',
          state: 'REQUEST_CREATED',
        }),
      });
      if (r.ok) {
        showToast('Facility transport request created');
        setNewReq({ origin_facility: '', destination_facility: '', origin_address: '', destination_address: '', service_level: 'BLS', priority: 'P2', chief_complaint: '', contact_name: '', contact_phone: '' });
        setActiveTab('requests');
        load();
      }
    } finally { setCreating(false); }
  };

  const injectToCad = async (requestId: string) => {
    const r = await fetch(`${API}/api/v1/dispatch/requests/${requestId}/inject`, {
      method: 'POST', headers: { Authorization: getToken(), 'Content-Type': 'application/json' },
      body: JSON.stringify({}),
    });
    const j = await r.json();
    if (!j.error) { showToast('Injected to CAD — mission created'); load(); }
    else showToast(`Error: ${j.error}`);
  };

  const validate = async (requestId: string) => {
    const r = await fetch(`${API}/api/v1/dispatch/requests/${requestId}/validate`, {
      method: 'POST', headers: { Authorization: getToken(), 'Content-Type': 'application/json' },
      body: JSON.stringify({}),
    });
    if (r.ok) { showToast('Request validated'); load(); }
  };

  const pending = requests.filter(r => ['REQUEST_CREATED', 'REQUEST_VALIDATED'].includes(r.data?.state));
  const injected = requests.filter(r => r.data?.state === 'DISPATCH_INJECTED');

  return (
    <div className="p-6 space-y-6 max-w-[1600px] mx-auto">
      {toast && (
        <div className="fixed top-4 right-4 z-50 bg-purple-600 text-white px-4 py-2 chamfer-8 text-sm font-medium shadow-[0_0_15px_rgba(0,0,0,0.6)]">{toast}</div>
      )}

      {/* ── Header ── */}
      <div className="flex items-center justify-between">
        <div>
          <Link href="/founder/ops" className="text-body text-[#FF4D00]-400 hover:text-[#FF4D00]-300 mb-1 block">← Ops Command</Link>
          <h1 className="text-2xl font-black text-white">TransportLink — Interfacility Intake</h1>
          <p className="text-sm text-zinc-500 mt-1">
            Facility request intake · Validation · CAD injection · Request audit trail
          </p>
        </div>
        <div className="flex flex-col items-end gap-2">
          <div className="flex items-center gap-2">
            <Link
              href="/founder/ops/transportlink/transport-billing-payment"
              className="px-3 py-1.5 bg-[#FF4D00]-500/[0.12] border border-orange-400/[0.35] text-[#FF4D00]-300 text-body font-bold chamfer-8 hover:bg-[#FF4D00]-500/[0.2]"
            >
              Transport Billing Payment
            </Link>
            <Link
              href="/founder/ops/transportlink/third-party-payment"
              className="px-3 py-1.5 bg-indigo-500/[0.12] border border-indigo-400/[0.35] text-indigo-300 text-body font-bold chamfer-8 hover:bg-indigo-500/[0.2]"
            >
              Third-Party Payment
            </Link>
            <Link
              href="/founder/ops/transportlink"
              className="px-3 py-1.5 bg-purple-500/[0.12] border border-purple-400/[0.35] text-purple-300 text-body font-bold chamfer-8 hover:bg-purple-500/[0.2]"
            >
              TransportLink
            </Link>
          </div>
          <div className="flex items-center gap-2">
            <Link
              href="/founder/ops/transportlink/hospitals"
              className="px-3 py-1.5 bg-blue-500/[0.12] border border-blue-400/[0.35] text-blue-300 text-body font-bold chamfer-8 hover:bg-blue-500/[0.2]"
            >
              Hospital Scheduling
            </Link>
            <Link
              href="/founder/ops/transportlink/assisted-living"
              className="px-3 py-1.5 bg-emerald-500/[0.12] border border-emerald-400/[0.35] text-emerald-300 text-body font-bold chamfer-8 hover:bg-emerald-500/[0.2]"
            >
              Assisted Living Scheduling
            </Link>
            <div className="px-3 py-1.5 bg-amber-400/[0.1] border border-amber-400/[0.3] chamfer-8">
              <span className="text-yellow-400 text-sm font-bold">{pending.length}</span>
              <span className="text-micro text-zinc-500 ml-1">PENDING REVIEW</span>
            </div>
            <div className="px-3 py-1.5 bg-brand-orange/[0.1] border border-brand-orange/[0.3] chamfer-8">
              <span className="text-[#FF4D00]-400 text-sm font-bold">{injected.length}</span>
              <span className="text-micro text-zinc-500 ml-1">IN CAD</span>
            </div>
          </div>
        </div>
      </div>

      {/* ── Request Flow ── */}
      <Panel>
        <div className="text-micro uppercase tracking-widest text-zinc-500 mb-3">Request State Flow</div>
        <div className="flex flex-wrap gap-1.5">
          {['REQUEST_CREATED','REQUEST_VALIDATED','REQUEST_ACCEPTED','DISPATCH_INJECTED','ASSIGNMENT_PENDING','CLOSED'].map((s, i, arr) => (
            <span key={s} className="flex items-center gap-1">
              <StateBadge state={s} />
              {i < arr.length - 1 && <span className="text-zinc-500 text-xs">→</span>}
            </span>
          ))}
          <span className="text-zinc-500 text-xs mx-1">or</span>
          <StateBadge state="REQUEST_REJECTED" />
        </div>
        <div className="mt-3 text-body text-zinc-500">
          Facility requests MUST be validated before CAD injection. Rejected requests are audited with reason. 
          Injected requests create standard CAD missions — no side-channel records.
        </div>
      </Panel>

      {/* ── Tabs ── */}
      <div className="flex gap-2">
        {(['requests', 'new'] as const).map(tab => (
          <button key={tab} onClick={() => setActiveTab(tab)} className={`px-4 py-2 chamfer-8 text-body font-bold uppercase tracking-wider ${activeTab === tab ? 'bg-purple-700 text-white' : 'bg-zinc-950/[0.06] text-zinc-400'}`}>
            {tab === 'requests' ? `Requests (${requests.length})` : 'New Request'}
          </button>
        ))}
      </div>

      {/* ── Requests List ── */}
      {activeTab === 'requests' && (
        <div className="space-y-2">
          {loading && <div className="text-sm text-zinc-500 p-4">Loading requests…</div>}
          {!loading && requests.length === 0 && (
            <div className="text-center py-10 chamfer-4-xl border border-white/[0.08]">
              <div className="text-3xl mb-2">🏥</div>
              <div className="text-sm text-zinc-500">No facility transport requests. Create one using the New Request tab.</div>
            </div>
          )}
          {requests.map(req => {
            const d = req.data ?? {};
            const isSelected = selected?.id === req.id;
            return (
              <div key={req.id} className="chamfer-4-xl border border-white/[0.08] overflow-hidden">
                <button onClick={() => setSelected(isSelected ? null : req)}
                  className="w-full flex items-center gap-4 p-4 text-left hover:bg-zinc-950/[0.03] transition-colors">
                  <div className="flex-shrink-0">
                    <StateBadge state={d.state} />
                    <div className="text-micro text-zinc-500 mt-1">{d.service_level} · {d.priority}</div>
                  </div>
                  <div className="flex-1 min-w-0">
                    <div className="text-sm font-semibold text-white">{d.origin_facility} → {d.destination_facility}</div>
                    <div className="text-body text-zinc-400">{d.chief_complaint || 'No complaint noted'}</div>
                    <div className="text-body text-zinc-500">{d.origin_address}</div>
                  </div>
                  <div className="flex-shrink-0 text-right">
                    <div className="text-micro text-zinc-500">{d.contact_name}</div>
                    <div className="text-micro text-zinc-500">{d.contact_phone}</div>
                  </div>
                  <span className="text-zinc-500 text-sm ml-2">{isSelected ? '▲' : '▼'}</span>
                </button>

                {isSelected && (
                  <div className="px-4 pb-4 border-t border-white/[0.06] space-y-4">
                    <div className="grid grid-cols-2 md:grid-cols-4 gap-3 mt-4">
                      <div>
                        <div className="text-micro uppercase tracking-wider text-zinc-500">Request ID</div>
                        <div className="text-body text-white font-mono">{req.id.slice(0, 16)}</div>
                      </div>
                      <div>
                        <div className="text-micro uppercase tracking-wider text-zinc-500">Origin</div>
                        <div className="text-body text-white">{d.origin_address}</div>
                      </div>
                      <div>
                        <div className="text-micro uppercase tracking-wider text-zinc-500">Destination</div>
                        <div className="text-body text-white">{d.destination_address || d.destination_facility}</div>
                      </div>
                      <div>
                        <div className="text-micro uppercase tracking-wider text-zinc-500">Mission ID</div>
                        <div className="text-body text-white">{d.mission_id ? d.mission_id.slice(0, 12) : 'Not yet injected'}</div>
                      </div>
                    </div>

                    <div className="flex gap-2">
                      {d.state === 'REQUEST_CREATED' && (
                        <button onClick={() => validate(req.id)}
                          className="px-4 py-1.5 bg-blue-400/[0.15] border border-blue-400/[0.3] text-blue-400 text-body font-bold chamfer-8 hover:bg-blue-400/[0.2]">
                          ✓ Validate Request
                        </button>
                      )}
                      {['REQUEST_CREATED', 'REQUEST_VALIDATED'].includes(d.state) && (
                        <button onClick={() => injectToCad(req.id)}
                          className="px-4 py-1.5 bg-brand-orange/[0.15] border border-brand-orange/[0.3] text-[#FF4D00]-400 text-body font-bold chamfer-8 hover:bg-brand-orange/[0.2]">
                          📡 Inject to CAD
                        </button>
                      )}
                      {d.mission_id && (
                        <Link href="/founder/ops/cad" className="px-4 py-1.5 bg-green-500/[0.1] border border-green-500/30 text-green-400 text-body font-bold chamfer-8 hover:bg-green-500/[0.15]">
                          View in CAD →
                        </Link>
                      )}
                    </div>
                  </div>
                )}
              </div>
            );
          })}
        </div>
      )}

      {/* ── New Request Form ── */}
      {activeTab === 'new' && (
        <Panel>
          <div className="text-micro uppercase tracking-widest text-zinc-500 mb-4">
            New Interfacility Transport Request
          </div>
          <div className="text-body text-zinc-400 mb-4">
            This request will be created in REQUEST_CREATED state. It must be validated before CAD injection.
            All fields are audited. Requests cannot silently enter CAD without validation.
          </div>
          <div className="grid grid-cols-2 md:grid-cols-3 gap-3 mb-4">
            <input value={newReq.origin_facility} onChange={e => setNewReq(p => ({ ...p, origin_facility: e.target.value }))}
              placeholder="Origin facility name *"
              className="h-9 bg-zinc-950/[0.06] border border-white/[0.12] px-3 text-sm text-white chamfer-8 focus:outline-none focus:border-purple-400 placeholder-text-zinc-500" />
            <input value={newReq.destination_facility} onChange={e => setNewReq(p => ({ ...p, destination_facility: e.target.value }))}
              placeholder="Destination facility"
              className="h-9 bg-zinc-950/[0.06] border border-white/[0.12] px-3 text-sm text-white chamfer-8 focus:outline-none focus:border-purple-400 placeholder-text-zinc-500" />
            <input value={newReq.origin_address} onChange={e => setNewReq(p => ({ ...p, origin_address: e.target.value }))}
              placeholder="Pickup address *"
              className="h-9 bg-zinc-950/[0.06] border border-white/[0.12] px-3 text-sm text-white chamfer-8 focus:outline-none focus:border-purple-400 placeholder-text-zinc-500" />
            <input value={newReq.destination_address} onChange={e => setNewReq(p => ({ ...p, destination_address: e.target.value }))}
              placeholder="Drop-off address"
              className="h-9 bg-zinc-950/[0.06] border border-white/[0.12] px-3 text-sm text-white chamfer-8 focus:outline-none focus:border-purple-400 placeholder-text-zinc-500" />
            <select value={newReq.service_level} onChange={e => setNewReq(p => ({ ...p, service_level: e.target.value }))}
              className="h-9 bg-zinc-950/[0.06] border border-white/[0.12] px-3 text-sm text-white chamfer-8 focus:outline-none focus:border-purple-400">
              {['BLS','ALS','CCT','HEMS'].map(s => <option key={s} value={s}>{s}</option>)}
            </select>
            <select value={newReq.priority} onChange={e => setNewReq(p => ({ ...p, priority: e.target.value }))}
              className="h-9 bg-zinc-950/[0.06] border border-white/[0.12] px-3 text-sm text-white chamfer-8 focus:outline-none focus:border-purple-400">
              {['P1','P2','P3','ROUTINE'].map(s => <option key={s} value={s}>{s}</option>)}
            </select>
            <input value={newReq.chief_complaint} onChange={e => setNewReq(p => ({ ...p, chief_complaint: e.target.value }))}
              placeholder="Chief complaint / reason for transport"
              className="h-9 bg-zinc-950/[0.06] border border-white/[0.12] px-3 text-sm text-white chamfer-8 focus:outline-none focus:border-purple-400 placeholder-text-zinc-500" />
            <input value={newReq.contact_name} onChange={e => setNewReq(p => ({ ...p, contact_name: e.target.value }))}
              placeholder="Contact name"
              className="h-9 bg-zinc-950/[0.06] border border-white/[0.12] px-3 text-sm text-white chamfer-8 focus:outline-none focus:border-purple-400 placeholder-text-zinc-500" />
            <input value={newReq.contact_phone} onChange={e => setNewReq(p => ({ ...p, contact_phone: e.target.value }))}
              placeholder="Contact phone"
              className="h-9 bg-zinc-950/[0.06] border border-white/[0.12] px-3 text-sm text-white chamfer-8 focus:outline-none focus:border-purple-400 placeholder-text-zinc-500" />
          </div>
          <button onClick={createRequest} disabled={creating || !newReq.origin_address || !newReq.origin_facility}
            className="px-6 py-2 bg-purple-700 text-white text-sm font-bold chamfer-8 hover:bg-purple-600 disabled:opacity-40 transition-colors">
            {creating ? 'Creating…' : '🏥 Submit Facility Request'}
          </button>
        </Panel>
      )}
    </div>
  );
}
