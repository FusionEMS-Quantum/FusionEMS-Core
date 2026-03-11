'use client';
import { QuantumTableSkeleton } from '@/components/ui';
import axios from 'axios';
import {
  attachFaxToClaim,
  detachFaxMatch,
  getFaxDownloadUrl,
  listFaxInbox,
  listFaxEvents,
  triggerFaxMatch,
  type FaxItemApi,
  type FaxEventApi,
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

type FaxItem = FaxItemApi;

type FilterTab = 'all' | 'unmatched' | 'matched' | 'review';
type FolderTab = 'inbox' | 'outbox';

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

function MatchChip({ fax, folder }: { fax: FaxItem; folder: FolderTab }) {
  if (folder === 'outbox') {
    return (
      <span className="inline-flex items-center gap-1 px-2 py-0.5 chamfer-4 text-micro font-bold bg-[var(--color-bg-base)]/10 text-[var(--color-text-primary)]/60 border border-white/10">
        OUTBOUND
      </span>
    );
  }

  const status = fax.document_match_status ?? fax.status ?? '';
  if (status === 'matched') {
    return (
      <span className="inline-flex items-center gap-1 px-2 py-0.5 chamfer-4 text-micro font-bold bg-status-active/20 text-[var(--color-status-active)] border border-status-active/30">
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
    <span className="inline-flex items-center gap-1 px-2 py-0.5 chamfer-4 text-micro font-bold bg-[var(--color-bg-base)]/10 text-[var(--color-text-primary)]/50 border border-white/10">
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
  const [folder, setFolder] = useState<FolderTab>('inbox');
  const [filter, setFilter] = useState<FilterTab>('all');
  const [selected, setSelected] = useState<FaxItem | null>(null);
  const [actionLoading, setActionLoading] = useState('');
  const [actionMsg, setActionMsg] = useState('');
  const [events, setEvents] = useState<FaxEventApi[]>([]);
  const [eventsLoading, setEventsLoading] = useState(false);

  const fetchFaxes = useCallback(async (): Promise<FaxItem[]> => {
    setLoading(true);
    setError('');
    try {
      const items = await listFaxInbox({ folder, status: 'all', limit: 50 });
      setFaxes(items);
      return items;
    } catch (e: unknown) {
      setError(getErrorMessage(e, 'Failed to load faxes'));
      return [];
    } finally {
      setLoading(false);
    }
  }, [folder]);

  useEffect(() => { void fetchFaxes(); }, [fetchFaxes]);

  useEffect(() => {
    setSelected(null);
    setEvents([]);
    setActionMsg('');
    if (folder === 'outbox' && filter !== 'all') {
      setFilter('all');
    }
  }, [folder]);

  // Realtime refresh: Poll for new platform events every 8 seconds
  // When fax.inbound.received or fax.outbound.* events fire, refresh the list
  useEffect(() => {
    let cancelled = false;
    const pollInterval = setInterval(async () => {
      if (cancelled) return;
      try {
        // Silently refresh fax list in background
        const items = await listFaxInbox({ folder, status: 'all', limit: 50 });
        if (!cancelled) {
          setFaxes(items);
          // If selected fax was updated, update the selection
          if (selected && items.length > 0) {
            const updatedSelected = items.find((f) => f.id === selected.id);
            if (updatedSelected) {
              setSelected(updatedSelected);
            }
          }
        }
      } catch {
        // Fail silently on polling errors; user can manually refresh
      }
    }, 8000); // Refresh every 8 seconds

    return () => {
      cancelled = true;
      clearInterval(pollInterval);
    };
  }, [folder, selected]);

  useEffect(() => {
    let cancelled = false;
    async function loadEvents() {
      if (!selected?.id) {
        setEvents([]);
        return;
      }
      setEventsLoading(true);
      try {
        const rows = await listFaxEvents(selected.id, { limit: 50 });
        if (!cancelled) setEvents(rows);
      } catch {
        if (!cancelled) setEvents([]);
      } finally {
        if (!cancelled) setEventsLoading(false);
      }
    }
    void loadEvents();
    return () => { cancelled = true; };
  }, [selected?.id]);

  const filteredFaxes = faxes.filter((f) => {
    if (folder === 'outbox') return true;
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

  const FOLDER_TABS: { key: FolderTab; label: string }[] = [
    { key: 'inbox', label: 'Inbox' },
    { key: 'outbox', label: 'Outbox' },
  ];

  return (
    <div className="min-h-screen bg-[var(--color-bg-base)] text-[var(--color-text-primary)] flex flex-col">
      <div className="flex flex-1 overflow-hidden" style={{ height: 'calc(100vh - 0px)' }}>
        {/* Left Panel */}
        <div className="w-[340px] shrink-0 flex flex-col border-r border-border-DEFAULT bg-[var(--color-bg-base)]">
          {/* Header */}
          <div className="px-4 pt-5 pb-3 border-b border-border-DEFAULT">
            <div className="flex items-center gap-2">
              <span className="text-xs font-bold tracking-widest text-[var(--color-text-primary)]/70 uppercase">Fax</span>
              <span className="ml-1 bg-[var(--q-orange)]/20 text-[var(--q-orange)] border border-orange/30 text-micro font-bold px-2 py-0.5 ">
                {faxes.length}
              </span>
            </div>
            {/* Folder Tabs */}
            <div className="flex gap-1 mt-3">
              {FOLDER_TABS.map((t) => (
                <button
                  key={t.key}
                  onClick={() => setFolder(t.key)}
                  className={`px-2.5 py-1 chamfer-4 text-body font-semibold transition-colors ${
                    folder === t.key
                      ? 'bg-[var(--q-orange)]/20 text-[var(--q-orange)] border border-orange/40'
                      : 'text-[var(--color-text-primary)]/40 hover:text-[var(--color-text-primary)]/70 border border-transparent'
                  }`}
                >
                  {t.label}
                </button>
              ))}
            </div>
            {/* Filter Tabs */}
            {folder === 'inbox' && (
              <div className="flex gap-1 mt-3">
                {TABS.map((t) => (
                  <button
                    key={t.key}
                    onClick={() => setFilter(t.key)}
                    className={`px-2.5 py-1 chamfer-4 text-body font-semibold transition-colors ${
                      filter === t.key
                        ? 'bg-[var(--q-orange)]/20 text-[var(--q-orange)] border border-orange/40'
                        : 'text-[var(--color-text-primary)]/40 hover:text-[var(--color-text-primary)]/70 border border-transparent'
                    }`}
                  >
                    {t.label}
                  </button>
                ))}
              </div>
            )}
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
              <div className="flex items-center justify-center h-32 text-[var(--color-text-primary)]/30 text-sm">No faxes</div>
            )}
            {!loading && filteredFaxes.map((fax) => {
              const isSelected = selected?.id === fax.id;
              const confidence = fax.data?.confidence;
              const pageCount = typeof fax.page_count === 'number' && Number.isFinite(fax.page_count) ? fax.page_count : null;
              return (
                <button
                  key={fax.id}
                  onClick={() => { setSelected(fax); setActionMsg(''); }}
                  className={`w-full text-left px-4 py-3 border-b border-border-subtle transition-colors flex gap-3 items-start ${
                    isSelected ? 'bg-[var(--q-orange)]/10' : 'hover:bg-[var(--color-bg-base)]/[0.03]'
                  }`}
                >
                  {/* Thumbnail */}
                  <div className="w-12 h-16 shrink-0 chamfer-4 bg-[var(--color-bg-base)]/10 border border-white/10 flex items-center justify-center text-[var(--color-text-primary)]/30">
                    <FaxIcon />
                  </div>
                  {/* Info */}
                  <div className="flex-1 min-w-0">
                    <div className="text-xs font-mono text-[var(--color-text-primary)]/80 truncate">{fax.from_number ?? 'N/A'}</div>
                    <div className="text-micro text-[var(--color-text-primary)]/40 mt-0.5">{relativeTime(fax.received_at)}</div>
                    <div className="text-micro text-[var(--color-text-primary)]/30 mt-0.5">
                      {pageCount == null ? '— pages' : `${pageCount} page${pageCount !== 1 ? 's' : ''}`}
                    </div>
                    <div className="flex flex-wrap gap-1 mt-1.5 items-center">
                      <MatchChip fax={fax} folder={folder} />
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
        <div className="flex-1 overflow-y-auto bg-[var(--color-bg-base)] p-6">
          {!selected ? (
            <div className="flex flex-col items-center justify-center h-full text-[var(--color-text-primary)]/20">
              <FaxIcon />
              <p className="mt-3 text-sm">Select a fax to view details</p>
            </div>
          ) : (
            <div className="max-w-2xl mx-auto space-y-5">
              {/* Header */}
              <div className="flex items-start justify-between gap-4">
                <div>
                  <h2 className="text-base font-bold text-[var(--color-text-primary)]">Fax Detail</h2>
                  <p className="text-xs text-[var(--color-text-primary)]/40 font-mono mt-0.5">{selected.id}</p>
                </div>
                <a
                  href={getFaxDownloadUrl(selected.id)}
                  target="_blank"
                  rel="noreferrer"
                  className="px-4 py-1.5 chamfer-4 bg-[var(--q-orange)]/20 border border-orange/40 text-[var(--q-orange)] text-xs font-semibold hover:bg-[var(--q-orange)]/30 transition-colors"
                >
                  Download
                </a>
              </div>

              {/* Metadata */}
              <div className="bg-[var(--color-bg-base)] border border-border-DEFAULT chamfer-4 p-4 grid grid-cols-2 gap-3">
                {[
                  ['From', selected.from_number ?? 'N/A'],
                  ['To', selected.to_number ?? 'N/A'],
                  ['Received', selected.received_at ? new Date(selected.received_at).toLocaleString() : 'N/A'],
                  ['Pages', String(selected.page_count ?? 'N/A')],
                  ['Delivery Status', selected.status ?? 'N/A'],
                  ['Last Update', selected.status_updated_at ? new Date(selected.status_updated_at).toLocaleString() : 'N/A'],
                  ['Provider Fax ID', selected.telnyx_fax_id ?? selected.data?.telnyx_fax_id ?? 'N/A'],
                  ['Error', selected.error ?? selected.data?.error ?? '—'],
                ].map(([label, value]) => (
                  <div key={label}>
                    <p className="text-micro text-[var(--color-text-primary)]/40 uppercase tracking-wider">{label}</p>
                    <p className="text-sm text-[var(--color-text-primary)]/80 font-mono mt-0.5">{value}</p>
                  </div>
                ))}
              </div>

              {/* Action message */}
              {actionMsg && (
                <div className={`p-3 chamfer-4 text-xs border ${
                  actionMsg.includes('success') || actionMsg.includes('attached') || actionMsg.includes('triggered') || actionMsg.includes('detached')
                    ? 'bg-status-active/10 border-status-active/30 text-[var(--color-status-active)]'
                    : 'bg-red/10 border-red/30 text-red'
                }`}>
                  {actionMsg}
                </div>
              )}

              {/* Match Section */}
              {folder === 'inbox' && (
                <div className="bg-[var(--color-bg-base)] border border-border-DEFAULT chamfer-4 p-4 space-y-4">
                  <h3 className="text-xs font-bold tracking-widest text-[var(--color-text-primary)]/60 uppercase">Match</h3>

                  {(() => {
                  const suggestions = Array.isArray(selected.data?.match_suggestions) ? selected.data.match_suggestions : [];
                  return (
                    <>
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
                                <p className="text-micro text-[var(--color-text-primary)]/40 uppercase tracking-wider">{label}</p>
                                <p className="text-sm text-[var(--color-text-primary)]/80 font-mono mt-0.5">{value}</p>
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
                      {suggestions.length > 0 && (
                        <div className="space-y-2 pt-2 border-t border-white/[0.06]">
                          <p className="text-micro text-[var(--color-text-primary)]/40 uppercase tracking-wider">Suggestions</p>
                          {suggestions.map((s, i) => {
                            const pct = s.score != null ? Math.round(s.score * 100) : null;
                            return (
                              <div key={i} className="flex items-center gap-3 bg-[var(--color-bg-base)]/[0.03] chamfer-4 p-3 border border-white/[0.06]">
                                <div className="flex-1 min-w-0">
                                  <p className="text-xs font-mono text-[var(--color-text-primary)]/80 truncate">{s.claim_id}</p>
                                  <p className="text-micro text-[var(--color-text-primary)]/40 mt-0.5">{s.patient_name ?? 'N/A'}</p>
                                  {pct != null && (
                                    <div className="mt-1.5 flex items-center gap-2">
                                      <div className="flex-1 h-1.5 bg-[var(--color-bg-base)]/10  overflow-hidden">
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
                                  className="px-3 py-1 chamfer-4 bg-status-active/10 border border-status-active/30 text-[var(--color-status-active)] text-body font-semibold hover:bg-status-active/20 transition-colors disabled:opacity-40 shrink-0"
                                >
                                  {actionLoading === 'attach-' + selected.id ? '...' : 'Attach'}
                                </button>
                              </div>
                            );
                          })}
                        </div>
                      )}
                    </>

                  );
                })()}
                </div>
              )}

              {/* Delivery Timeline */}
              <div className="bg-[var(--color-bg-base)] border border-border-DEFAULT chamfer-4 p-4 space-y-3">
                <div className="flex items-center justify-between">
                  <h3 className="text-xs font-bold tracking-widest text-[var(--color-text-primary)]/60 uppercase">Delivery Timeline</h3>
                  {eventsLoading && (
                    <span className="text-micro text-[var(--color-text-primary)]/30">Loading…</span>
                  )}
                </div>
                {!eventsLoading && events.length === 0 && (
                  <div className="text-sm text-[var(--color-text-primary)]/30">No delivery events yet.</div>
                )}
                <div className="space-y-2">
                  {events.map((ev) => {
                    const d = ev.data ?? {};
                    const when = (typeof d.received_at === 'string' && d.received_at)
                      ? d.received_at
                      : ev.created_at;
                    const label = (typeof d.event_type === 'string' && d.event_type)
                      ? d.event_type
                      : 'event';
                    const toStatus = typeof d.to_status === 'string' ? d.to_status : (typeof d.status === 'string' ? d.status : '');
                    const providerType = typeof d.provider_event_type === 'string' ? d.provider_event_type : '';
                    return (
                      <div key={ev.id} className="flex items-start justify-between gap-3 border border-white/[0.06] bg-[var(--color-bg-base)]/[0.03] chamfer-4 p-3">
                        <div className="min-w-0">
                          <div className="text-xs font-mono text-[var(--color-text-primary)]/80 truncate">{label}</div>
                          <div className="text-micro text-[var(--color-text-primary)]/40 mt-0.5">
                            {when ? new Date(when).toLocaleString() : 'N/A'}
                            {providerType ? ` • ${providerType}` : ''}
                          </div>
                        </div>
                        <div className="text-xs font-mono text-[var(--color-text-primary)]/60 shrink-0">
                          {toStatus || '—'}
                        </div>
                      </div>
                    );
                  })}
                </div>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
