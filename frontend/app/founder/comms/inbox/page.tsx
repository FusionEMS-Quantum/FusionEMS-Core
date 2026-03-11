'use client';

import { useState, useEffect, useRef, useCallback } from 'react';
import {
  listSupportInboxThreads,
  listSupportThreadMessages,
  resolveSupportInboxThread,
  sendSupportInboxReply,
  summarizeSupportInboxThread,
  listFaxInbox,
  getFaxPreviewUrl,
  getFaxDownloadUrl,
  type SupportThreadApi,
  type SupportThreadMessageApi,
  type FaxItemApi,
} from '@/services/api';

function relativeTime(iso: string): string {
  const diff = Date.now() - new Date(iso).getTime();
  const s = Math.floor(diff / 1000);
  if (s < 60) return `${s}s ago`;
  const m = Math.floor(s / 60);
  if (m < 60) return `${m}m ago`;
  const h = Math.floor(m / 60);
  if (h < 24) return `${h}h ago`;
  return `${Math.floor(h / 24)}d ago`;
}

type ThreadStatus = 'open' | 'escalated' | 'resolved';
type FilterTab = 'all' | 'escalated' | 'open' | 'resolved';
type CommsChannel = 'support' | 'fax';
type FaxFolder = 'inbox' | 'outbox';

// ─── Toast ────────────────────────────────────────────────────────────────────
interface ToastItem {
  id: number;
  msg: string;
  type: 'success' | 'error';
}

function Toast({ items }: { items: ToastItem[] }) {
  if (!items.length) return null;
  return (
    <div className="fixed bottom-5 right-5 z-50 flex flex-col gap-2 pointer-events-none">
      {items.map((t) => (
        <div
          key={t.id}
          className="px-4 py-2.5 chamfer-4 text-xs font-semibold shadow-[0_0_15px_rgba(0,0,0,0.6)]"
          style={{
            background: t.type === 'success' ? 'rgba(76,175,80,0.18)' : 'rgba(229,57,53,0.18)',
            border: `1px solid ${t.type === 'success' ? 'rgba(76,175,80,0.4)' : 'rgba(229,57,53,0.4)'}`,
            color: t.type === 'success' ? 'var(--color-status-active)' : 'var(--color-brand-red)',
          }}
        >
          {t.msg}
        </div>
      ))}
    </div>
  );
}

function useToast() {
  const [toasts, setToasts] = useState<ToastItem[]>([]);
  const counter = useRef(0);

  const push = useCallback((msg: string, type: 'success' | 'error' = 'success') => {
    const id = ++counter.current;
    setToasts((prev) => [...prev, { id, msg, type }]);
    setTimeout(() => setToasts((prev) => prev.filter((t) => t.id !== id)), 3000);
  }, []);

  return { toasts, push };
}

// ─── Status badge ─────────────────────────────────────────────────────────────
function StatusBadge({ status }: { status: ThreadStatus }) {
  const map: Record<ThreadStatus, { label: string; color: string; bg: string }> = {
    open: { label: 'OPEN', color: 'var(--color-system-billing)', bg: 'rgba(34,211,238,0.12)' },
    escalated: { label: 'ESCALATED', color: 'var(--q-red)', bg: 'rgba(229,57,53,0.12)' },
    resolved: { label: 'RESOLVED', color: 'rgba(255,255,255,0.4)', bg: 'rgba(255,255,255,0.06)' },
  };
  const s = map[status];
  return (
    <span
      className="px-1.5 py-0.5 text-micro font-semibold uppercase tracking-wider chamfer-4"
      style={{ color: s.color, background: s.bg }}
    >
      {s.label}
    </span>
  );
}

function FaxCommandPane() {
  const [folder, setFolder] = useState<FaxFolder>('inbox');
  const [items, setItems] = useState<FaxItemApi[]>([]);
  const [active, setActive] = useState<FaxItemApi | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [previewUrl, setPreviewUrl] = useState<string>('');

  const fetchItems = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await listFaxInbox({ folder, status: 'all', limit: 50 });
      setItems(data);
      setActive((prev) => {
        if (prev && data.some((i) => i.id === prev.id)) return prev;
        return data.length ? data[0] : null;
      });
    } catch {
      setError('Failed to load faxes');
    } finally {
      setLoading(false);
    }
  }, [folder]);

  useEffect(() => {
    fetchItems();
    const interval = setInterval(fetchItems, 30000);
    return () => clearInterval(interval);
  }, [fetchItems]);

  useEffect(() => {
    let cancelled = false;
    async function loadPreview() {
      if (!active) {
        setPreviewUrl('');
        return;
      }
      try {
        const { url } = await getFaxPreviewUrl(active.id);
        if (!cancelled) setPreviewUrl(url);
      } catch {
        if (!cancelled) setPreviewUrl('');
      }
    }
    loadPreview();
    return () => {
      cancelled = true;
    };
  }, [active]);

  const FOLDER_TABS: { key: FaxFolder; label: string }[] = [
    { key: 'inbox', label: 'Inbox' },
    { key: 'outbox', label: 'Outbox' },
  ];

  function primaryLabel(item: FaxItemApi): string {
    if (folder === 'inbox') return item.from_number || 'Unknown sender';
    return item.to_number || 'Unknown recipient';
  }

  return (
    <div className="flex flex-1 overflow-hidden" style={{ height: 'calc(100vh - 90px)' }}>
      {/* ── LEFT: Fax list ─────────────────────────────────────────────── */}
      <div
        className="flex flex-col border-r border-border-DEFAULT"
        style={{ width: 340, minWidth: 340, flexShrink: 0 }}
      >
        <div className="flex border-b border-border-subtle px-2 pt-2 pb-0 gap-0.5">
          {FOLDER_TABS.map((tab) => (
            <button
              key={tab.key}
              onClick={() => setFolder(tab.key)}
              className="px-2.5 py-1.5 text-micro font-semibold uppercase tracking-wider transition-colors"
              style={{
                color: folder === tab.key ? 'var(--q-orange)' : 'rgba(255,255,255,0.38)',
                borderBottom:
                  folder === tab.key ? '2px solid var(--q-orange)' : '2px solid transparent',
              }}
            >
              {tab.label}
            </button>
          ))}
        </div>

        <div className="flex-1 overflow-y-auto">
          {loading && (
            <div className="p-4 text-body text-[var(--color-text-muted)] text-center mt-6">Loading faxes…</div>
          )}
          {!loading && error && (
            <div className="p-4 text-body text-[var(--color-brand-red)] text-center mt-6">{error}</div>
          )}
          {!loading && !error && items.length === 0 && (
            <div className="p-4 text-body text-[var(--color-text-muted)] text-center mt-6">No faxes</div>
          )}
          {!loading &&
            !error &&
            items.map((fax) => {
              const isActive = active?.id === fax.id;
              return (
                <button
                  key={fax.id}
                  onClick={() => setActive(fax)}
                  className="w-full text-left px-3 py-3 border-b border-white/5 transition-colors hover:bg-[var(--color-bg-base)]/[0.03]"
                  style={{
                    background: isActive ? 'rgba(255,106,0,0.06)' : 'transparent',
                    borderLeft: isActive ? '3px solid var(--q-orange)' : '3px solid transparent',
                  }}
                >
                  <div className="flex items-center gap-2 mb-1">
                    <span className="text-xs font-semibold text-[var(--color-text-primary)] truncate flex-1">
                      {primaryLabel(fax)}
                    </span>
                    {fax.status && (
                      <span
                        className="px-1.5 py-0.5 text-[9px] font-semibold uppercase tracking-wider chamfer-4 flex-shrink-0"
                        style={{ background: 'rgba(255,255,255,0.06)', color: 'rgba(255,255,255,0.55)' }}
                      >
                        {fax.status}
                      </span>
                    )}
                  </div>
                  <div className="flex items-end justify-between gap-2">
                    <p className="text-body text-[var(--color-text-muted)] leading-snug flex-1 min-w-0 truncate">
                      {folder === 'inbox'
                        ? `To: ${fax.to_number || '—'}`
                        : `From: ${fax.from_number || '—'}`}
                    </p>
                    {fax.received_at && (
                      <span className="text-micro text-[var(--color-text-muted)] whitespace-nowrap flex-shrink-0">
                        {relativeTime(fax.received_at)}
                      </span>
                    )}
                  </div>
                </button>
              );
            })}
        </div>
      </div>

      {/* ── RIGHT: Preview ─────────────────────────────────────────────── */}
      <div className="flex-1 flex flex-col min-w-0 overflow-hidden">
        {!active ? (
          <div className="flex-1 flex items-center justify-center">
            <div className="text-center space-y-2">
              <div className="text-3xl text-white/[0.06]">{'▸'}</div>
              <p className="text-body text-[var(--color-text-muted)] uppercase tracking-wider">Select a fax</p>
            </div>
          </div>
        ) : (
          <>
            <div className="px-4 py-3 border-b border-border-DEFAULT flex items-center gap-3 flex-wrap">
              <div className="flex items-center gap-2 flex-1 min-w-0">
                <span className="text-sm font-bold text-[var(--color-text-primary)] truncate">
                  {folder === 'inbox'
                    ? `${active.from_number || 'Unknown sender'} → ${active.to_number || '—'}`
                    : `${active.from_number || '—'} → ${active.to_number || 'Unknown recipient'}`}
                </span>
                {active.status && (
                  <span
                    className="px-1.5 py-0.5 text-micro font-semibold uppercase tracking-wider chamfer-4"
                    style={{ color: 'rgba(255,255,255,0.55)', background: 'rgba(255,255,255,0.06)' }}
                  >
                    {active.status}
                  </span>
                )}
              </div>
              <div className="flex items-center gap-2 flex-shrink-0">
                <a
                  href={previewUrl || getFaxDownloadUrl(active.id)}
                  target="_blank"
                  rel="noreferrer"
                  className="h-7 px-3 text-micro font-semibold uppercase tracking-wider chamfer-4 transition-colors inline-flex items-center"
                  style={{
                    background: 'rgba(255,106,0,0.10)',
                    border: '1px solid rgba(255,106,0,0.25)',
                    color: 'var(--q-orange)',
                  }}
                >
                  Open
                </a>
              </div>
            </div>

            <div className="flex-1 bg-[var(--color-bg-base)]">
              {previewUrl ? (
                <iframe
                  title="Fax Preview"
                  src={previewUrl}
                  className="w-full h-full"
                  style={{ border: 'none' }}
                />
              ) : (
                <div className="h-full flex items-center justify-center">
                  <div className="text-body text-[var(--color-text-muted)]">Preview unavailable</div>
                </div>
              )}
            </div>
          </>
        )}
      </div>
    </div>
  );
}

export default function SupportInboxPage() {
  const [channel, setChannel] = useState<CommsChannel>('support');
  const [threads, setThreads] = useState<SupportThreadApi[]>([]);
  const [filter, setFilter] = useState<FilterTab>('all');
  const [activeThread, setActiveThread] = useState<SupportThreadApi | null>(null);
  const [messages, setMessages] = useState<SupportThreadMessageApi[]>([]);
  const [replyText, setReplyText] = useState('');
  const [summary, setSummary] = useState<string | null>(null);
  const [summaryOpen, setSummaryOpen] = useState(false);
  const [loadingMessages, setLoadingMessages] = useState(false);
  const [sendingReply, setSendingReply] = useState(false);
  const [resolvingId, setResolvingId] = useState<string | null>(null);
  const [summarizing, setSummarizing] = useState(false);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const { toasts, push: pushToast } = useToast();

  // ── Fetch threads ──────────────────────────────────────────────────────────
  const fetchThreads = useCallback(async () => {
    try {
      const data = await listSupportInboxThreads({ status: 'open', limit: 50 });
      setThreads(data);
    } catch (err: unknown) {
      console.warn("[inbox] refresh", err);
    }
  }, []);

  useEffect(() => {
    fetchThreads();
    const interval = setInterval(fetchThreads, 30000);
    return () => clearInterval(interval);
  }, [fetchThreads]);

  // ── Fetch messages for selected thread ────────────────────────────────────
  const fetchMessages = useCallback(async (threadId: string) => {
    setLoadingMessages(true);
    setSummary(null);
    setSummaryOpen(false);
    try {
      const data = await listSupportThreadMessages(threadId);
      setMessages(data);
    } catch {
      pushToast('Failed to load messages', 'error');
    } finally {
      setLoadingMessages(false);
    }
  }, [pushToast]);

  useEffect(() => {
    if (activeThread) fetchMessages(activeThread.id);
  }, [activeThread, fetchMessages]);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  // ── Send reply ─────────────────────────────────────────────────────────────
  async function sendReply() {
    if (!activeThread || !replyText.trim()) return;
    setSendingReply(true);
    try {
      await sendSupportInboxReply(activeThread.id, { content: replyText.trim() });
      setReplyText('');
      await fetchMessages(activeThread.id);
      pushToast('Reply sent', 'success');
    } catch {
      pushToast('Failed to send reply', 'error');
    } finally {
      setSendingReply(false);
    }
  }

  // ── Resolve thread ─────────────────────────────────────────────────────────
  async function resolveThread(thread: SupportThreadApi) {
    setResolvingId(thread.id);
    try {
      await resolveSupportInboxThread(thread.id);
      pushToast('Thread resolved', 'success');
      await fetchThreads();
      if (activeThread?.id === thread.id) {
        setActiveThread((prev) => prev ? { ...prev, status: 'resolved' } : null);
      }
    } catch {
      pushToast('Failed to resolve thread', 'error');
    } finally {
      setResolvingId(null);
    }
  }

  // ── AI Summarize ───────────────────────────────────────────────────────────
  async function summarizeThread() {
    if (!activeThread) return;
    setSummarizing(true);
    try {
      const summaryText = await summarizeSupportInboxThread(activeThread.id);
      setSummary(summaryText);
      setSummaryOpen(true);
    } catch {
      pushToast('Summarize failed', 'error');
    } finally {
      setSummarizing(false);
    }
  }

  // ── Derived data ───────────────────────────────────────────────────────────
  const filteredThreads = threads.filter((t) => {
    if (filter === 'all') return true;
    if (filter === 'escalated') return t.escalated || t.status === 'escalated';
    return t.status === filter;
  });

  const unreadCount = threads.filter((t) => t.unread).length;

  function agencyName(t: SupportThreadApi): string {
    return t.data?.context?.agency_name || t.data?.title || 'Unknown Agency';
  }

  function lastPreview(t: SupportThreadApi): string {
    const raw = t.data?.last_message ?? '';
    return raw.length > 60 ? raw.slice(0, 60) + '…' : raw;
  }

  const FILTER_TABS: { key: FilterTab; label: string }[] = [
    { key: 'all', label: 'All' },
    { key: 'escalated', label: 'Escalated' },
    { key: 'open', label: 'Open' },
    { key: 'resolved', label: 'Resolved' },
  ];

  return (
    <div className="min-h-screen bg-[var(--color-bg-base)] text-[var(--color-text-primary)] flex flex-col">
      <Toast items={toasts} />

      {/* Page header */}
      <div className="px-5 pt-5 pb-4 border-b border-border-subtle">
        <div className="flex items-center gap-3">
          <h1 className="text-sm font-black uppercase tracking-[0.18em] text-[var(--color-text-primary)]">
            COMMUNICATIONS COMMAND
          </h1>
          <div className="flex items-center gap-0.5">
            <button
              onClick={() => setChannel('support')}
              className="px-2.5 py-1.5 text-micro font-semibold uppercase tracking-wider transition-colors"
              style={{
                color: channel === 'support' ? 'var(--q-orange)' : 'rgba(255,255,255,0.38)',
                borderBottom: channel === 'support' ? '2px solid var(--q-orange)' : '2px solid transparent',
              }}
            >
              Support
            </button>
            <button
              onClick={() => setChannel('fax')}
              className="px-2.5 py-1.5 text-micro font-semibold uppercase tracking-wider transition-colors"
              style={{
                color: channel === 'fax' ? 'var(--q-orange)' : 'rgba(255,255,255,0.38)',
                borderBottom: channel === 'fax' ? '2px solid var(--q-orange)' : '2px solid transparent',
              }}
            >
              Fax
            </button>
          </div>
          {channel === 'support' && unreadCount > 0 && (
            <span
              className="px-1.5 py-0.5 text-micro font-semibold uppercase tracking-wider chamfer-4"
              style={{ background: 'rgba(255,106,0,0.18)', color: 'var(--q-orange)' }}
            >
              {unreadCount} unread
            </span>
          )}
          <div className="ml-auto flex items-center gap-1.5">
            <span className="w-1.5 h-1.5  bg-status-active animate-pulse" />
            <span className="text-micro font-semibold uppercase tracking-wider text-[var(--color-status-active)]">LIVE</span>
          </div>
        </div>
        <p className="text-body text-[var(--color-text-muted)] mt-0.5">
          {channel === 'support'
            ? 'Agency support threads · real-time · AI assist'
            : 'Fax inbox/outbox · inline preview'}
        </p>
      </div>

      {channel === 'support' ? (
        <div className="flex flex-1 overflow-hidden" style={{ height: 'calc(100vh - 90px)' }}>

          {/* ── LEFT: Thread list (300px) ───────────────────────────────────── */}
          <div
            className="flex flex-col border-r border-border-DEFAULT"
            style={{ width: 300, minWidth: 300, flexShrink: 0 }}
          >
            {/* Filter tabs */}
            <div className="flex border-b border-border-subtle px-2 pt-2 pb-0 gap-0.5">
              {FILTER_TABS.map((tab) => (
                <button
                  key={tab.key}
                  onClick={() => setFilter(tab.key)}
                  className="px-2.5 py-1.5 text-micro font-semibold uppercase tracking-wider transition-colors"
                  style={{
                    color: filter === tab.key ? 'var(--q-orange)' : 'rgba(255,255,255,0.38)',
                    borderBottom: filter === tab.key ? '2px solid var(--q-orange)' : '2px solid transparent',
                  }}
                >
                  {tab.label}
                </button>
              ))}
            </div>

            {/* Thread list */}
            <div className="flex-1 overflow-y-auto">
              {filteredThreads.length === 0 && (
                <div className="p-4 text-body text-[var(--color-text-muted)] text-center mt-8">
                  No threads in this view
                </div>
              )}
              {filteredThreads.map((thread) => {
                const isActive = activeThread?.id === thread.id;
                return (
                  <button
                    key={thread.id}
                    onClick={() => setActiveThread(thread)}
                    className="w-full text-left px-3 py-3 border-b border-white/5 transition-colors hover:bg-[var(--color-bg-base)]/[0.03]"
                    style={{
                      background: isActive ? 'rgba(255,106,0,0.06)' : 'transparent',
                      borderLeft: isActive ? '3px solid var(--q-orange)' : '3px solid transparent',
                    }}
                  >
                    <div className="flex items-center gap-2 mb-1">
                      <span className="text-xs font-semibold text-[var(--color-text-primary)] truncate flex-1">
                        {agencyName(thread)}
                      </span>
                      {thread.unread && (
                        <span className="w-2 h-2  flex-shrink-0" style={{ background: 'var(--q-orange)' }} />
                      )}
                      {(thread.escalated || thread.status === 'escalated') && (
                        <span
                          className="px-1.5 py-0.5 text-[9px] font-semibold uppercase tracking-wider chamfer-4 flex-shrink-0"
                          style={{ background: 'rgba(229,57,53,0.15)', color: 'var(--q-red)' }}
                        >
                          ESC
                        </span>
                      )}
                    </div>
                    <div className="flex items-end justify-between gap-2">
                      <p className="text-body text-[var(--color-text-muted)] leading-snug flex-1 min-w-0 truncate">
                        {lastPreview(thread)}
                      </p>
                      <span className="text-micro text-[var(--color-text-muted)] whitespace-nowrap flex-shrink-0">
                        {relativeTime(thread.updated_at)}
                      </span>
                    </div>
                  </button>
                );
              })}
            </div>
          </div>

          {/* ── RIGHT: Messages panel ───────────────────────────────────────── */}
          <div className="flex-1 flex flex-col min-w-0 overflow-hidden">
            {!activeThread ? (
              <div className="flex-1 flex items-center justify-center">
                <div className="text-center space-y-2">
                  <div className="text-3xl text-white/[0.06]">{'\u25B8'}</div>
                  <p className="text-body text-[var(--color-text-muted)] uppercase tracking-wider">
                    Select a thread
                  </p>
                </div>
              </div>
            ) : (
              <>
                {/* Thread header */}
                <div className="px-4 py-3 border-b border-border-DEFAULT flex items-center gap-3 flex-wrap">
                  <div className="flex items-center gap-2 flex-1 min-w-0">
                    <span className="text-sm font-bold text-[var(--color-text-primary)] truncate">
                      {agencyName(activeThread)}
                    </span>
                    <StatusBadge status={activeThread.status} />
                  </div>
                  <div className="flex items-center gap-2 flex-shrink-0">
                    <button
                      onClick={summarizeThread}
                      disabled={summarizing}
                      className="h-7 px-3 text-micro font-semibold uppercase tracking-wider chamfer-4 transition-colors"
                      style={{
                        background: 'rgba(34,211,238,0.10)',
                        border: '1px solid rgba(34,211,238,0.25)',
                        color: 'var(--color-system-billing)',
                        opacity: summarizing ? 0.6 : 1,
                      }}
                    >
                      {summarizing ? 'Summarizing…' : 'Summarize AI'}
                    </button>
                    {activeThread.status !== 'resolved' && (
                      <button
                        onClick={() => resolveThread(activeThread)}
                        disabled={resolvingId === activeThread.id}
                        className="h-7 px-3 text-micro font-semibold uppercase tracking-wider chamfer-4 transition-colors"
                        style={{
                          background: 'rgba(76,175,80,0.10)',
                          border: '1px solid rgba(76,175,80,0.25)',
                          color: 'var(--q-green)',
                          opacity: resolvingId === activeThread.id ? 0.6 : 1,
                        }}
                      >
                        {resolvingId === activeThread.id ? 'Resolving…' : 'Resolve'}
                      </button>
                    )}
                  </div>
                </div>

                {/* AI Summary collapsible panel */}
                {summary && (
                  <div
                    className="border-b border-cyan-500/[0.15]"
                    style={{ background: 'rgba(34,211,238,0.04)' }}
                  >
                    <button
                      className="w-full flex items-center justify-between px-4 py-2 text-left"
                      onClick={() => setSummaryOpen((v) => !v)}
                    >
                      <span className="text-micro font-semibold uppercase tracking-wider text-system-billing">
                        AI Summary
                      </span>
                      <span className="text-micro text-[var(--color-text-muted)]">
                        {summaryOpen ? '▲ Collapse' : '▼ Expand'}
                      </span>
                    </button>
                    {summaryOpen && (
                      <div className="px-4 pb-3 text-body text-[var(--color-text-primary)] leading-relaxed">
                        {summary}
                      </div>
                    )}
                  </div>
                )}

                {/* Messages list */}
                <div className="flex-1 overflow-y-auto px-4 py-3 space-y-3">
                  {loadingMessages && (
                    <div className="text-center text-body text-[var(--color-text-muted)] py-8">
                      Loading messages…
                    </div>
                  )}
                  {!loadingMessages && messages.length === 0 && (
                    <div className="text-center text-body text-[var(--color-text-muted)] py-8">
                      No messages yet
                    </div>
                  )}
                  {messages.map((msg) => {
                    const isAgency = msg.sender_role === 'agency';
                    return (
                      <div
                        key={msg.id}
                        className={`flex flex-col ${isAgency ? 'items-end' : 'items-start'}`}
                      >
                        <div
                          className="max-w-[72%] px-3 py-2 chamfer-4 text-xs leading-relaxed"
                          style={{
                            background: isAgency
                              ? 'rgba(255,106,0,0.12)'
                              : 'rgba(255,255,255,0.05)',
                            border: `1px solid ${isAgency ? 'rgba(255,106,0,0.18)' : 'rgba(255,255,255,0.07)'}`,
                            color: 'rgba(255,255,255,0.85)',
                          }}
                        >
                          {msg.content}
                        </div>
                        <div className="flex items-center gap-1.5 mt-0.5 px-0.5">
                          <span className="text-micro text-[var(--color-text-muted)] uppercase tracking-wider">
                            {msg.sender_role}
                          </span>
                          <span className="text-micro text-text-disabled">
                            {relativeTime(msg.created_at)}
                          </span>
                        </div>
                      </div>
                    );
                  })}
                  <div ref={messagesEndRef} />
                </div>

                {/* Reply box */}
                <div className="border-t border-border-DEFAULT px-4 py-3">
                  <div className="flex gap-2 items-end">
                    <textarea
                      value={replyText}
                      onChange={(e) => setReplyText(e.target.value)}
                      onKeyDown={(e) => {
                        if (e.key === 'Enter' && (e.ctrlKey || e.metaKey)) sendReply();
                      }}
                      placeholder="Type a reply… (Ctrl+Enter to send)"
                      rows={3}
                      className="flex-1 bg-[var(--color-bg-base)]/[0.04] border border-border-DEFAULT text-xs text-[var(--color-text-primary)] px-3 py-2 chamfer-4 outline-none resize-none placeholder:text-text-disabled focus:border-brand-orange/40"
                    />
                    <button
                      onClick={sendReply}
                      disabled={sendingReply || !replyText.trim()}
                      className="h-9 px-4 text-micro font-bold uppercase tracking-widest chamfer-4 transition-all"
                      style={{
                        background: replyText.trim() && !sendingReply ? 'var(--q-orange)' : 'rgba(255,106,0,0.2)',
                        color: replyText.trim() && !sendingReply ? 'black' : 'rgba(255,106,0,0.5)',
                      }}
                    >
                      {sendingReply ? '…' : 'Send'}
                    </button>
                  </div>
                </div>
              </>
            )}
          </div>
        </div>
      ) : (
        <FaxCommandPane />
      )}
    </div>
  );
}
