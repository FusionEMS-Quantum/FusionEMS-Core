'use client';

import { useEffect, useState } from 'react';
import Link from 'next/link';
import { getPortalNotifications, markPortalNotificationsRead, markPortalNotificationRead } from '@/services/api';

interface Notification {
  id: string;
  title: string;
  body: string;
  type: 'payment' | 'statement' | 'plan' | 'message' | 'support' | 'system';
  read: boolean;
  created_at: string;
  action_href?: string;
  action_label?: string;
}

const TYPE_CONFIG: Record<string, { color: string; bg: string; border: string; icon: string }> = {
  payment:   { color: 'var(--color-status-active)', bg: 'rgba(16,185,129,0.06)',  border: 'rgba(16,185,129,0.2)',  icon: 'pay' },
  statement: { color: '#818CF8', bg: 'rgba(129,140,248,0.06)', border: 'rgba(129,140,248,0.2)', icon: 'doc' },
  plan:      { color: 'var(--q-yellow)', bg: 'rgba(245,158,11,0.06)',  border: 'rgba(245,158,11,0.2)',  icon: 'plan' },
  message:   { color: '#A78BFA', bg: 'rgba(167,139,250,0.06)', border: 'rgba(167,139,250,0.2)', icon: 'msg' },
  support:   { color: '#60A5FA', bg: 'rgba(96,165,250,0.06)',  border: 'rgba(96,165,250,0.2)',  icon: 'support' },
  system:    { color: 'var(--q-orange)', bg: 'rgba(255,106,0,0.06)',    border: 'rgba(255,106,0,0.2)',    icon: 'system' },
};

function NIcon({ type }: { type: string }) {
  const p = { width: 14, height: 14, viewBox: '0 0 24 24', fill: 'none', stroke: 'currentColor', strokeWidth: 2, strokeLinecap: 'round' as const, strokeLinejoin: 'round' as const };
  switch (type) {
    case 'pay':     return <svg {...p}><rect x="1" y="4" width="22" height="16" rx="2"/><line x1="1" y1="10" x2="23" y2="10"/></svg>;
    case 'doc':     return <svg {...p}><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><polyline points="14 2 14 8 20 8"/></svg>;
    case 'plan':    return <svg {...p}><rect x="3" y="4" width="18" height="18" rx="2"/><line x1="3" y1="10" x2="21" y2="10"/><polyline points="8 14 10 16 14 12"/></svg>;
    case 'msg':     return <svg {...p}><path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"/></svg>;
    case 'support': return <svg {...p}><circle cx="12" cy="12" r="10"/><circle cx="12" cy="12" r="4"/></svg>;
    case 'system':  return <svg {...p}><path d="M18 8A6 6 0 0 0 6 8c0 7-3 9-3 9h18s-3-2-3-9"/><path d="M13.73 21a2 2 0 0 1-3.46 0"/></svg>;
    default:        return <svg {...p}><circle cx="12" cy="12" r="3" fill="currentColor" stroke="none"/></svg>;
  }
}

function fmtRelative(s: string): string {
  const diff = Date.now() - new Date(s).getTime();
  const min = Math.floor(diff / 60000);
  if (min < 1) return 'Just now';
  if (min < 60) return `${min}m ago`;
  const hr = Math.floor(min / 60);
  if (hr < 24) return `${hr}h ago`;
  const days = Math.floor(hr / 24);
  if (days < 7) return `${days}d ago`;
  return new Date(s).toLocaleDateString('en-US', { month: 'short', day: 'numeric' });
}

const clip6  = 'polygon(0 0, calc(100% - 6px) 0, 100% 6px, 100% 100%, 0 100%)';
const clip10 = 'polygon(0 0, calc(100% - 10px) 0, 100% 10px, 100% 100%, 0 100%)';

export default function NotificationsPage() {
  const [notifications, setNotifications] = useState<Notification[]>([]);
  const [loading, setLoading] = useState(true);
  const [filter, setFilter] = useState<'all' | 'unread'>('all');
  const [fetchError, setFetchError] = useState<string | null>(null);

  useEffect(() => {
    getPortalNotifications()
      .then(d => setNotifications(Array.isArray(d) ? d : d.items ?? []))
      .catch((err: unknown) => setFetchError(err instanceof Error ? err.message : 'Failed to load notifications'))
      .finally(() => setLoading(false));
  }, []);

  const markAllRead = () => {
    setNotifications(prev => prev.map(n => ({ ...n, read: true })));
    markPortalNotificationsRead().catch(() => null);
  };

  const markRead = (id: string) => {
    setNotifications(prev => prev.map(n => n.id === id ? { ...n, read: true } : n));
    markPortalNotificationRead(id).catch(() => null);
  };

  const filtered = filter === 'unread' ? notifications.filter(n => !n.read) : notifications;
  const unreadCount = notifications.filter(n => !n.read).length;

  return (
    <div className="max-w-3xl mx-auto px-4 py-8">
      {/* Header */}
      <div className="flex items-start justify-between mb-8">
        <div>
          <div className="flex items-center gap-3 mb-1">
            <div className="w-[3px] h-6 bg-[var(--q-orange)] shadow-[0_0_8px_rgba(255,106,0,0.6)]" />
            <h1 className="text-xl font-black tracking-[0.12em] text-white uppercase">Notifications</h1>
            {unreadCount > 0 && (
              <span className="text-[9px] font-black px-1.5 py-0.5 bg-[var(--q-orange)] text-black">
                {unreadCount}
              </span>
            )}
          </div>
          <p className="text-sm text-[var(--color-text-muted)] ml-5">Billing alerts, payment confirmations, and account updates.</p>
        </div>
        {unreadCount > 0 && (
          <button
            onClick={markAllRead}
            className="text-[10px] font-bold tracking-widest uppercase text-[var(--color-text-muted)] hover:text-[var(--color-text-secondary)] transition-colors border border-[var(--color-border-default)] hover:border-[var(--color-border-strong)] px-3 py-1.5"
            style={{ clipPath: clip6 }}
          >
            Mark All Read
          </button>
        )}
      </div>

      {/* Filter bar */}
      <div className="flex items-center gap-2 mb-6">
        {(['all', 'unread'] as const).map(f => (
          <button
            key={f}
            onClick={() => setFilter(f)}
            className={`px-3 py-1.5 text-[10px] font-bold tracking-widest uppercase border transition-colors ${
              filter === f
                ? 'bg-[var(--q-orange)]/10 border-[var(--q-orange)]/40 text-[var(--q-orange)]'
                : 'border-[var(--color-border-default)] text-[var(--color-text-muted)] hover:border-[var(--color-border-strong)] hover:text-[var(--color-text-secondary)]'
            }`}
            style={{ clipPath: clip6 }}
          >
            {f === 'all' ? `All (${notifications.length})` : `Unread (${unreadCount})`}
          </button>
        ))}
      </div>

      {/* Notifications */}
      {fetchError && (
        <div className="mb-4 px-4 py-3 bg-[var(--color-brand-red)]/8 border border-[var(--color-brand-red)]/20 text-sm text-[var(--color-brand-red)]" style={{ clipPath: clip6 }}>
          Unable to load notifications. Please refresh the page or contact billing support.
        </div>
      )}

      {loading ? (
        <div className="space-y-3">
          {Array.from({ length: 4 }).map((_, i) => (
            <div key={i} className="bg-[var(--color-bg-panel)] border border-[var(--color-border-subtle)] h-20 animate-pulse" style={{ clipPath: clip10 }} />
          ))}
        </div>
      ) : filtered.length === 0 ? (
        <div className="bg-[var(--color-bg-panel)] border border-[var(--color-border-default)] py-16 text-center" style={{ clipPath: clip10 }}>
          <div className="text-2xl mb-3 opacity-20">🔔</div>
          <p className="text-sm text-[var(--color-text-muted)]">
            {filter === 'unread' ? 'No unread notifications.' : 'No notifications yet.'}
          </p>
        </div>
      ) : (
        <div className="space-y-2">
          {filtered.map(n => {
            const cfg = TYPE_CONFIG[n.type] ?? TYPE_CONFIG.system;
            return (
              <div
                key={n.id}
                className={`border p-4 transition-all cursor-default ${
                  n.read
                    ? 'bg-[var(--color-bg-panel)] border-[var(--color-border-subtle)]'
                    : 'bg-[var(--color-bg-panel)] border-[var(--color-border-default)]'
                }`}
                style={{ clipPath: clip10, borderLeftColor: n.read ? undefined : cfg.color }}
                onClick={() => markRead(n.id)}
              >
                <div className="flex items-start gap-3">
                  {/* Icon */}
                  <div
                    className="flex-shrink-0 w-8 h-8 flex items-center justify-center border mt-0.5"
                    style={{ background: cfg.bg, borderColor: cfg.border, color: cfg.color, clipPath: clip6 }}
                  >
                    <NIcon type={cfg.icon} />
                  </div>

                  {/* Content */}
                  <div className="flex-1 min-w-0">
                    <div className="flex items-start justify-between gap-2">
                      <p className={`text-sm font-semibold ${n.read ? 'text-[var(--color-text-secondary)]' : 'text-[var(--color-text-primary)]'}`}>
                        {n.title}
                        {!n.read && (
                          <span className="inline-block ml-2 w-1.5 h-1.5 bg-[var(--q-orange)] rounded-full align-middle" />
                        )}
                      </p>
                      <span className="flex-shrink-0 text-[10px] text-[var(--color-text-muted)]">{fmtRelative(n.created_at)}</span>
                    </div>
                    <p className={`text-xs mt-1 ${n.read ? 'text-[var(--color-text-muted)]' : 'text-[var(--color-text-secondary)]'}`}>{n.body}</p>
                    {n.action_href && (
                      <Link
                        href={n.action_href}
                        className="inline-block mt-2 text-[10px] font-bold tracking-widest uppercase text-[var(--q-orange)] hover:underline"
                        onClick={e => { e.stopPropagation(); markRead(n.id); }}
                      >
                        {n.action_label ?? 'View'} →
                      </Link>
                    )}
                  </div>
                </div>
              </div>
            );
          })}
        </div>
      )}

      {/* Notification preferences link */}
      <div className="mt-8 text-center">
        <Link href="/portal/patient/preferences" className="text-[10px] font-bold tracking-widest uppercase text-[var(--color-text-muted)] hover:text-[var(--color-text-secondary)] transition-colors">
          Manage Notification Preferences →
        </Link>
      </div>
    </div>
  );
}


