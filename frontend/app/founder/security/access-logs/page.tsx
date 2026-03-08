'use client';

import { useEffect, useState, useCallback } from 'react';
import { motion } from 'framer-motion';
import Link from 'next/link';

const API = process.env.NEXT_PUBLIC_API_BASE || process.env.NEXT_PUBLIC_API_URL || '';

const DOMAINS = [
  'all', 'auth_event', 'access_event', 'clinical_event', 'billing_event',
  'export_event', 'policy_change_event', 'fleet_event',
] as const;
type Domain = (typeof DOMAINS)[number];

interface AuditLog {
  id: string;
  tenant_id: string;
  action: string;
  entity_name: string;
  entity_id: string;
  actor_user_id: string;
  actor_email: string | null;
  ip_address: string | null;
  correlation_id: string | null;
  domain: string;
  metadata_json: Record<string, unknown>;
  created_at: string;
}

interface SearchResponse {
  items: AuditLog[];
  total: number;
  limit: number;
  offset: number;
}

const LEVEL_COLOR: Record<string, string> = {
  auth_event: '#FF4D00',
  access_event: 'var(--color-status-info)',
  clinical_event: 'var(--color-status-active)',
  billing_event: '#a78bfa',
  export_event: 'var(--color-status-warning)',
  policy_change_event: 'var(--color-brand-red)',
  fleet_event: '#67e8f9',
};

function domainColor(d: string) {
  return LEVEL_COLOR[d] ?? 'rgba(255,255,255,0.35)';
}

function formatTs(ts: string): string {
  try {
    return new Date(ts).toLocaleString([], { month: 'short', day: '2-digit', hour: '2-digit', minute: '2-digit', second: '2-digit', hour12: false });
  } catch {
    return ts;
  }
}

function LogRow({ log, index }: { log: AuditLog; index: number }) {
  const [expanded, setExpanded] = useState(false);
  const c = domainColor(log.domain);
  return (
    <motion.div
      initial={{ opacity: 0, y: 4 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ delay: index * 0.02 }}
      className="border-b border-white/5 last:border-0"
    >
      <button
        className="w-full text-left flex items-center gap-3 px-4 py-3 hover:bg-zinc-950/[0.03] transition-colors"
        onClick={() => setExpanded(e => !e)}
      >
        <span className="w-1.5 h-1.5  flex-shrink-0" style={{ background: c }} />
        <span className="text-micro font-mono text-zinc-500 w-36 flex-shrink-0">{formatTs(log.created_at)}</span>
        <span className="text-xs font-semibold w-28 flex-shrink-0" style={{ color: c }}>
          {log.domain.replace(/_/g, ' ')}
        </span>
        <span className="text-xs text-zinc-100 flex-1 truncate">{log.action}</span>
        <span className="text-micro text-zinc-500 font-mono truncate w-32 flex-shrink-0">
          {log.actor_email ?? log.actor_user_id.slice(0, 8) + '…'}
        </span>
        <span className="text-micro text-zinc-500 font-mono">{log.ip_address ?? '—'}</span>
        <svg width="12" height="12" viewBox="0 0 12 12" fill="none" stroke="currentColor" strokeWidth="1.5"
          className={`flex-shrink-0 transition-transform ${expanded ? 'rotate-180' : ''}`}>
          <path d="M2 4l4 4 4-4" />
        </svg>
      </button>
      {expanded && (
        <div className="px-4 pb-4 bg-zinc-950/[0.02]">
          <div className="grid grid-cols-2 gap-2 mb-2 text-micro">
            <div><span className="text-zinc-500">Entity: </span><span className="font-mono text-zinc-400">{log.entity_name} / {log.entity_id?.slice(0, 8)}…</span></div>
            <div><span className="text-zinc-500">Correlation: </span><span className="font-mono text-zinc-400">{log.correlation_id ?? '—'}</span></div>
            <div><span className="text-zinc-500">Actor ID: </span><span className="font-mono text-zinc-400">{log.actor_user_id}</span></div>
            <div><span className="text-zinc-500">Tenant: </span><span className="font-mono text-zinc-400">{log.tenant_id?.slice(0, 8)}…</span></div>
          </div>
          {Object.keys(log.metadata_json ?? {}).length > 0 && (
            <pre className="bg-bg-page text-micro font-mono text-zinc-400 p-2  overflow-auto max-h-40">
              {JSON.stringify(log.metadata_json, null, 2)}
            </pre>
          )}
        </div>
      )}
    </motion.div>
  );
}

export default function AccessLogsPage() {
  const [logs, setLogs] = useState<AuditLog[]>([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Filters
  const [domain, setDomain] = useState<Domain>('all');
  const [action, setAction] = useState('');
  const [actor, setActor] = useState('');
  const [fromDt, setFromDt] = useState('');
  const [toDt, setToDt] = useState('');
  const [offset, setOffset] = useState(0);
  const LIMIT = 50;

  const fetchLogs = useCallback(async (resetOffset = false) => {
    setLoading(true);
    setError(null);
    const currentOffset = resetOffset ? 0 : offset;
    if (resetOffset) setOffset(0);

    const body: Record<string, unknown> = { limit: LIMIT, offset: currentOffset };
    if (domain !== 'all') body.domain = domain;
    if (action.trim()) body.action = action.trim();
    if (actor.trim()) body.actor_user_id = actor.trim();
    if (fromDt) body.from_dt = new Date(fromDt).toISOString();
    if (toDt) body.to_dt = new Date(toDt).toISOString();

    try {
      const token = typeof window !== 'undefined' ? localStorage.getItem('token') ?? '' : '';
      const res = await fetch(`${API}/api/v1/audit/logs/search`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${token}` },
        body: JSON.stringify(body),
      });
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const data: SearchResponse = await res.json();
      setLogs(data.items);
      setTotal(data.total);
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Failed to load logs');
    } finally {
      setLoading(false);
    }
  }, [domain, action, actor, fromDt, toDt, offset]);

  useEffect(() => { fetchLogs(true); }, [domain]); // eslint-disable-line react-hooks/exhaustive-deps

  const handleSearch = (e: React.FormEvent) => { e.preventDefault(); fetchLogs(true); };

  const exportCsv = () => {
    const rows = [['timestamp', 'domain', 'action', 'actor', 'entity', 'ip', 'correlation_id'].join(',')];
    logs.forEach(l => rows.push([
      l.created_at, l.domain, `"${l.action}"`,
      l.actor_email ?? l.actor_user_id, l.entity_name, l.ip_address ?? '', l.correlation_id ?? '',
    ].join(',')));
    const blob = new Blob([rows.join('\n')], { type: 'text/csv' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a'); a.href = url; a.download = 'audit-logs.csv'; a.click();
    URL.revokeObjectURL(url);
  };

  return (
    <div className="p-5 min-h-screen">
      {/* Header */}
      <div className="hud-rail pb-3 mb-6 flex items-end justify-between">
        <div>
          <div className="micro-caps mb-1 text-zinc-500">Security</div>
          <h1 className="text-h2 font-bold text-zinc-100">Access Logs</h1>
          <p className="text-body text-zinc-500 mt-1">
            Immutable audit trail — {total.toLocaleString()} total entries
          </p>
        </div>
        <div className="flex gap-2">
          <button onClick={exportCsv} disabled={logs.length === 0}
            className="px-3 py-1.5 text-micro font-semibold uppercase tracking-widest border border-border-DEFAULT text-zinc-400 hover:text-zinc-100 hover:border-orange transition-colors disabled:opacity-40">
            Export CSV
          </button>
          <Link href="/founder/security"
            className="px-3 py-1.5 text-micro font-semibold uppercase tracking-widest border border-border-DEFAULT text-zinc-500 hover:text-zinc-100 transition-colors">
            ← Security
          </Link>
        </div>
      </div>

      {/* Domain tabs */}
      <div className="flex gap-1 mb-4 overflow-x-auto pb-1">
        {DOMAINS.map(d => (
          <button key={d} onClick={() => setDomain(d)}
            className={`px-3 py-1 text-micro font-semibold uppercase tracking-widest whitespace-nowrap transition-colors border ${domain === d ? 'border-orange text-[#FF4D00] bg-[#FF4D00]/10' : 'border-border-DEFAULT text-zinc-500 hover:text-zinc-100'}`}>
            {d === 'all' ? 'All' : d.replace(/_event$/, '').replace(/_/g, ' ')}
          </button>
        ))}
      </div>

      {/* Search bar */}
      <form onSubmit={handleSearch} className="flex flex-wrap gap-2 mb-4 bg-[#0A0A0B] border border-border-DEFAULT p-3"
        style={{ clipPath: 'polygon(0 0, calc(100% - 8px) 0, 100% 8px, 100% 100%, 0 100%)' }}>
        <input value={action} onChange={e => setAction(e.target.value)} placeholder="Action keyword…"
          className="flex-1 min-w-0 bg-bg-page border border-border-DEFAULT px-3 py-1.5 text-xs text-zinc-100 placeholder:text-zinc-500 focus:outline-none focus:border-orange" />
        <input value={actor} onChange={e => setActor(e.target.value)} placeholder="Actor user ID…"
          className="w-48 bg-bg-page border border-border-DEFAULT px-3 py-1.5 text-xs text-zinc-100 placeholder:text-zinc-500 focus:outline-none focus:border-orange" />
        <input type="datetime-local" value={fromDt} onChange={e => setFromDt(e.target.value)}
          className="w-48 bg-bg-page border border-border-DEFAULT px-3 py-1.5 text-xs text-zinc-100 focus:outline-none focus:border-orange" />
        <input type="datetime-local" value={toDt} onChange={e => setToDt(e.target.value)}
          className="w-48 bg-bg-page border border-border-DEFAULT px-3 py-1.5 text-xs text-zinc-100 focus:outline-none focus:border-orange" />
        <button type="submit"
          className="px-4 py-1.5 text-micro font-semibold uppercase tracking-widest bg-[#FF4D00] text-bg-page hover:bg-[#E64500] transition-colors">
          Search
        </button>
      </form>

      {/* Table */}
      <div className="bg-[#0A0A0B] border border-border-DEFAULT"
        style={{ clipPath: 'polygon(0 0, calc(100% - 10px) 0, 100% 10px, 100% 100%, 0 100%)' }}>
        {/* Column headers */}
        <div className="flex items-center gap-3 px-4 py-2 border-b border-white/10 bg-zinc-950/[0.02]">
          <div className="w-1.5 flex-shrink-0" />
          <span className="text-micro uppercase tracking-widest text-zinc-500 w-36 flex-shrink-0">Time</span>
          <span className="text-micro uppercase tracking-widest text-zinc-500 w-28 flex-shrink-0">Domain</span>
          <span className="text-micro uppercase tracking-widest text-zinc-500 flex-1">Action</span>
          <span className="text-micro uppercase tracking-widest text-zinc-500 w-32 flex-shrink-0">Actor</span>
          <span className="text-micro uppercase tracking-widest text-zinc-500">IP</span>
          <div className="w-3 flex-shrink-0" />
        </div>

        {error && (
          <div className="px-4 py-6 text-center text-sm text-red-400 border-b border-white/5">{error}</div>
        )}

        {loading && !logs.length && (
          <div className="px-4 py-12 text-center text-zinc-500 text-sm">Loading audit logs…</div>
        )}

        {!loading && !error && logs.length === 0 && (
          <div className="px-4 py-12 text-center text-zinc-500 text-sm">No logs match the current filters.</div>
        )}

        {logs.map((log, i) => <LogRow key={log.id} log={log} index={i} />)}
      </div>

      {/* Pagination */}
      {total > LIMIT && (
        <div className="flex items-center justify-between mt-4 text-micro text-zinc-500">
          <span>Showing {offset + 1}–{Math.min(offset + LIMIT, total)} of {total.toLocaleString()}</span>
          <div className="flex gap-2">
            <button disabled={offset === 0} onClick={() => { setOffset(o => Math.max(0, o - LIMIT)); fetchLogs(); }}
              className="px-3 py-1 border border-border-DEFAULT hover:border-orange disabled:opacity-40 transition-colors text-zinc-400 hover:text-zinc-100">
              ← Prev
            </button>
            <button disabled={offset + LIMIT >= total} onClick={() => { setOffset(o => o + LIMIT); fetchLogs(); }}
              className="px-3 py-1 border border-border-DEFAULT hover:border-orange disabled:opacity-40 transition-colors text-zinc-400 hover:text-zinc-100">
              Next →
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
