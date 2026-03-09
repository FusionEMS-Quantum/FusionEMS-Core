'use client';
import { QuantumTableSkeleton } from '@/components/ui';
import axios from 'axios';
import {
  attachFaxToClaim,
  detachFaxMatch,
  getFaxDownloadUrl,
  listFaxInbox,
  triggerFaxMatch,
  type FaxItemApi,
  type FaxMatchSuggestionApi,
} from '@/services/api';

import { useEffect, useState, useCallback } from 'react';

function getErrorMessage(error: unknown, fallback: string): string {
  if (axios.isAxiosError(error)) {
    const payload = error.response?.data as Record<string, unknown> | undefined;
    const detail = payload?.detail;
    if (typeof detail === 'string' && detail.length > 0) return detail;
    if (Array.isArray(detail) && detail.length > 0) {
      return detail
        .map((item) => (typeof item === 'string' ? item : JSON.stringify(item)))
        .join('; ');
    }
    if (typeof error.message === 'string' && error.message.length > 0) return error.message;
  }
  return error instanceof Error ? error.message : fallback;
}

// type MatchSuggestion = FaxMatchSuggestionApi;

type FaxItem = FaxItemApi;

type FilterTab = 'all' | 'unmatched' | 'matched' | 'review';

function relativeTime(iso?: string): string {
  if (!iso) return 'N/A';
  const diff = Date.now() - new Date(iso).getTime();
  const m = Math.floor(diff / 60000);
  if (m < 1) return 'just now';
  if (m < 60) return `${m}m ago`;
  const h = Math.floor(m / 60);
  if (h < 24) return `${h}h ago`;
  return `${Math.floor(h / 24)}d ago`;
}

function MatchChip({ fax }: { fax: FaxItem }) {
  const status = fax.document_match_status ?? fax.status ?? '';
  if (status === 'matched') {
    return (
      <span className="inline-flex items-center gap-1 px-2 py-0.5 chamfer-4 text-micro font-bold bg-status-active/20 text-status-active border border-status-active/30">
        AUTO-MATCHED
      </span>
    );
  }
  if (status === 'review') {
    return (
      <span className="inline-flex items-center gap-1 px-2 py-0.5 chamfer-4 text-micro font-bold bg-status-warning/20 text-status-warning border border-status-warning/30">
        NEEDS REVIEW
      </span>
    );
  }
  return (
    <span className="inline-flex items-center gap-1 px-2 py-0.5 chamfer-4 text-micro font-bold bg-zinc-950/10 text-zinc-100/50 border border-white/10">
      UNMATCHED
    </span>
  );
}

function FaxIcon() {
  return (
    <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
      <path d="M6 18H4a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h16a2 2 0 0 1 2 2v8a2 2 0 0 1-2 2h-2" />
      <rect x="6" y="14" width="12" height="8" rx="1" />
      <path d="M6 2h12v4H6z" />
    </svg>
  );
}

export default function FaxInboxPage() {
  const [faxes, setFaxes] = useState<FaxItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [filter, setFilter] = useState<FilterTab>('all');
  const [selected, setSelected] = useState<FaxItem | null>(null);
  const [actionLoading, setActionLoading] = useState('');
  const [actionMsg, setActionMsg] = useState('');

  const fetchFaxes = useCallback(async (): Promise<FaxItem[]> => {
    setLoading(true);
    setError('');
    try {
      const items = await listFaxInbox({ status: 'all', limit: 50 });
      setFaxes(items);
      return items;
    } catch (e: unknown) {
      setError(getErrorMessage(e, 'Failed to load faxes'));
      return [];
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { void fetchFaxes(); }, [fetchFaxes]);

  const filteredFaxes = faxes.filter((f) => {
    const s = f.document_match_status ?? f.status ?? '';
    if (filter === 'all') return true;
    if (filter === 'matched') return s === 'matched';
    if (filter === 'review') return s === 'review';
    if (filter === 'unmatched') return s !== 'matched' && s !== 'review';
    return true;
  });

  async function triggerMatch(faxId: string) {
    setActionLoading('trigger-' + faxId);
    setActionMsg('');
    try {
      await triggerFaxMatch(faxId);
      setActionMsg('Match triggered successfully.');
      const updatedRows = await fetchFaxes();
      const updated = updatedRows.find((f) => f.id === faxId);
      if (updated) {
        setSelected(updated);
      }
    } catch (e: unknown) {
      setActionMsg(getErrorMessage(e, 'Error triggering match'));
    } finally {
      setActionLoading('');
    }
  }

  async function attachFax(claimId: string, faxId: string) {
    setActionLoading('attach-' + faxId);
    setActionMsg('');
    try {
      await attachFaxToClaim(claimId, { fax_id: faxId, attachment_type: 'manual' });
      setActionMsg('Fax attached to claim.');
      const updatedRows = await fetchFaxes();
      const updated = updatedRows.find((f) => f.id === faxId);
      if (updated) {
        setSelected(updated);
      }
    } catch (e: unknown) {
      setActionMsg(getErrorMessage(e, 'Error attaching fax'));
    } finally {
      setActionLoading('');
    }
  }

  async function detachFax(faxId: string) {
    setActionLoading('detach-' + faxId);
    setActionMsg('');
    try {
      await detachFaxMatch(faxId);
      setActionMsg('Match detached.');
      const updatedRows = await fetchFaxes();
      const updated = updatedRows.find((f) => f.id === faxId);
      setSelected(updated ?? null);
    } catch (e: unknown) {
      setActionMsg(getErrorMessage(e, 'Error detaching'));
    } finally {
      setActionLoading('');
    }
  }

  const TABS: { key: FilterTab; label: string }[] = [
    { key: 'all', label: 'All' },
    { key: 'unmatched', label: 'Unmatched' },
    { key: 'matched', label: 'Matched' },
    { key: 'review', label: 'Review' },
  ];

  return (
    <div className="min-h-screen bg-black text-zinc-100 flex flex-col">
      <div className="flex flex-1 overflow-hidden" style={{ height: 'calc(100vh - 0px)' }}>
        {/* Left Panel */}
        <div className="w-[340px] shrink-0 flex flex-col border-r border-border-DEFAULT bg-[#050505]">
          {/* Header */}
          <div className="px-4 pt-5 pb-3 border-b border-border-DEFAULT">
            <div className="flex items-center gap-2">
              <span className="text-xs font-bold tracking-widest text-zinc-100/70 uppercase">Fax Inbox</span>
              <span className="ml-1 bg-[#FF4D00]/20 text-[#FF4D00] border border-orange/30 text-micro font-bold px-2 py-0.5 ">
                {faxes.length}
              </span>
            </div>
            {/* Filter Tabs */}
            <div className="flex gap-1 mt-3">
              {TABS.map((t) => (
                <button
                  key={t.key}
                  onClick={() => setFilter(t.key)}
                  className={`px-2.5 py-1 chamfer-4 text-body font-semibold transition-colors ${
                    filter === t.key
                      ? 'bg-[#FF4D00]/20 text-[#FF4D00] border border-orange/40'
                      : 'text-zinc-100/40 hover:text-zinc-100/70 border border-transparent'
                  }`}
                >
                  {t.label}
                </button>
              ))}
            </div>
          </div>

          {/* Fax List */}
          <div className="flex-1 overflow-y-auto">
            {loading && (
              <div className="p-6"><QuantumTableSkeleton rows={6} cols={4} /></div>
            )}
            {!loading && error && (
              <div className="m-4 p-3 chamfer-4 bg-red/10 border border-red/30 text-red text-xs">{error}</div>
            )}
            {!loading && !error && filteredFaxes.length === 0 && (
              <div className="flex items-center justify-center h-32 text-zinc-100/30 text-sm">No faxes</div>
            )}
            {!loading && filteredFaxes.map((fax) => {
              const isSelected = selected?.id === fax.id;
              const confidence = fax.data?.confidence;
              return (
                <button
                  key={fax.id}
                  onClick={() => { setSelected(fax); setActionMsg(''); }}
                  className={`w-full text-left px-4 py-3 border-b border-border-subtle transition-colors flex gap-3 items-start ${
                    isSelected ? 'bg-[#FF4D00]/10' : 'hover:bg-zinc-950/[0.03]'
                  }`}
                >
                  {/* Thumbnail */}
                  <div className="w-12 h-16 shrink-0 chamfer-4 bg-zinc-950/10 border border-white/10 flex items-center justify-center text-zinc-100/30">
                    <FaxIcon />
                  </div>
                  {/* Info */}
                  <div className="flex-1 min-w-0">
                    <div className="text-xs font-mono text-zinc-100/80 truncate">{fax.from_number ?? 'N/A'}</div>
                    <div className="text-micro text-zinc-100/40 mt-0.5">{relativeTime(fax.received_at)}</div>
                    <div className="text-micro text-zinc-100/30 mt-0.5">{fax.page_count ?? (() => { throw new Error('Unsafe silent fallback. Dependency missing.'); })()} page{(fax.page_count ?? (() => { throw new Error('Unsafe silent fallback. Dependency missing.'); })()) !== 1 ? 's' : ''}</div>
                    <div className="flex flex-wrap gap-1 mt-1.5 items-center">
                      <MatchChip fax={fax} />
                      {confidence != null && (
                        <span className="text-micro text-system-billing font-mono">{Math.round(confidence * 100)}% match</span>
                      )}
                    </div>
                  </div>
                </button>
              );
            })}
          </div>
        </div>

        {/* Right Panel */}
        <div className="flex-1 overflow-y-auto bg-black p-6">
          {!selected ? (
            <div className="flex flex-col items-center justify-center h-full text-zinc-100/20">
              <FaxIcon />
              <p className="mt-3 text-sm">Select a fax to view details</p>
            </div>
          ) : (
            <div className="max-w-2xl mx-auto space-y-5">
              {/* Header */}
              <div className="flex items-start justify-between gap-4">
                <div>
                  <h2 className="text-base font-bold text-zinc-100">Fax Detail</h2>
                  <p className="text-xs text-zinc-100/40 font-mono mt-0.5">{selected.id}</p>
                </div>
                <a
                  href={getFaxDownloadUrl(selected.id)}
                  target="_blank"
                  rel="noreferrer"
                  className="px-4 py-1.5 chamfer-4 bg-[#FF4D00]/20 border border-orange/40 text-[#FF4D00] text-xs font-semibold hover:bg-[#FF4D00]/30 transition-colors"
                >
                  Download
                </a>
              </div>

              {/* Metadata */}
              <div className="bg-[#050505] border border-border-DEFAULT chamfer-4 p-4 grid grid-cols-2 gap-3">
                {[
                  ['From', selected.from_number ?? 'N/A'],
                  ['To', selected.to_number ?? 'N/A'],
                  ['Received', selected.received_at ? new Date(selected.received_at).toLocaleString() : 'N/A'],
                  ['Pages', String(selected.page_count ?? 'N/A')],
                ].map(([label, value]) => (
                  <div key={label}>
                    <p className="text-micro text-zinc-100/40 uppercase tracking-wider">{label}</p>
                    <p className="text-sm text-zinc-100/80 font-mono mt-0.5">{value}</p>
                  </div>
                ))}
              </div>

              {/* Action message */}
              {actionMsg && (
                <div className={`p-3 chamfer-4 text-xs border ${
                  actionMsg.includes('success') || actionMsg.includes('attached') || actionMsg.includes('triggered') || actionMsg.includes('detached')
                    ? 'bg-status-active/10 border-status-active/30 text-status-active'
                    : 'bg-red/10 border-red/30 text-red'
                }`}>
                  {actionMsg}
                </div>
              )}

              {/* Match Section */}
              <div className="bg-[#050505] border border-border-DEFAULT chamfer-4 p-4 space-y-4">
                <h3 className="text-xs font-bold tracking-widest text-zinc-100/60 uppercase">Match</h3>

                {(selected.document_match_status ?? selected.status) === 'matched' ? (
                  <div className="space-y-3">
                    <div className="grid grid-cols-2 gap-3">
                      {[
                        ['Claim ID', selected.data?.claim_id ?? 'N/A'],
                        ['Patient', selected.data?.patient_name ?? 'N/A'],
                        ['Match Type', selected.data?.match_type ?? 'N/A'],
                        ['Confidence', selected.data?.confidence != null ? `${Math.round(selected.data.confidence * 100)}%` : 'N/A'],
                      ].map(([label, value]) => (
                        <div key={label}>
                          <p className="text-micro text-zinc-100/40 uppercase tracking-wider">{label}</p>
                          <p className="text-sm text-zinc-100/80 font-mono mt-0.5">{value}</p>
                        </div>
                      ))}
                    </div>
                    <button
                      onClick={() => detachFax(selected.id)}
                      disabled={!!actionLoading}
                      className="px-4 py-1.5 chamfer-4 bg-red/10 border border-red/30 text-red text-xs font-semibold hover:bg-red/20 transition-colors disabled:opacity-40"
                    >
                      {actionLoading === 'detach-' + selected.id ? 'Detaching...' : 'Detach'}
                    </button>
                  </div>
                ) : (
                  <div className="space-y-3">
                    <button
                      onClick={() => triggerMatch(selected.id)}
                      disabled={!!actionLoading}
                      className="px-4 py-1.5 chamfer-4 bg-system-billing/10 border border-system-billing/30 text-system-billing text-xs font-semibold hover:bg-system-billing/20 transition-colors disabled:opacity-40"
                    >
                      {actionLoading === 'trigger-' + selected.id ? 'Searching...' : 'Find Match'}
                    </button>
                  </div>
                )}

                {/* Match Suggestions */}
                {(selected.data?.match_suggestions?.length ?? (() => { throw new Error('Unsafe silent fallback. Dependency missing.'); })()) > 0 && (
                  <div className="space-y-2 pt-2 border-t border-white/[0.06]">
                    <p className="text-micro text-zinc-100/40 uppercase tracking-wider">Suggestions</p>
                    {selected.data!.match_suggestions!.map((s, i) => {
                      const pct = s.score != null ? Math.round(s.score * 100) : null;
                      return (
                        <div key={i} className="flex items-center gap-3 bg-zinc-950/[0.03] chamfer-4 p-3 border border-white/[0.06]">
                          <div className="flex-1 min-w-0">
                            <p className="text-xs font-mono text-zinc-100/80 truncate">{s.claim_id}</p>
                            <p className="text-micro text-zinc-100/40 mt-0.5">{s.patient_name ?? 'N/A'}</p>
                            {pct != null && (
                              <div className="mt-1.5 flex items-center gap-2">
                                <div className="flex-1 h-1.5 bg-zinc-950/10  overflow-hidden">
                                  <div
                                    className="h-full  bg-system-billing"
                                    style={{ width: `${pct}%` }}
                                  />
                                </div>
                                <span className="text-micro text-system-billing font-mono">{pct}%</span>
                              </div>
                            )}
                          </div>
                          <button
                            onClick={() => attachFax(s.claim_id, selected.id)}
                            disabled={!!actionLoading}
                            className="px-3 py-1 chamfer-4 bg-status-active/10 border border-status-active/30 text-status-active text-body font-semibold hover:bg-status-active/20 transition-colors disabled:opacity-40 shrink-0"
                          >
                            {actionLoading === 'attach-' + selected.id ? '...' : 'Attach'}
                          </button>
                        </div>
                      );
                    })}
                  </div>
                )}
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
