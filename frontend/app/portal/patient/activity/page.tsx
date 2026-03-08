'use client';

import { useEffect, useState } from 'react';
import Link from 'next/link';

interface ActivityEvent {
  id: string;
  event_type: string;
  description: string;
  created_at: string;
  metadata?: Record<string, string | number | boolean | null>;
}

const EVENT_CONFIG: Record<string, { label: string; color: string; icon: string }> = {
  statement_created:     { label: 'Statement Created',          color: '#818CF8', icon: 'doc' },
  statement_sent:        { label: 'Statement Sent',             color: '#60A5FA', icon: 'mail' },
  payment_initiated:     { label: 'Payment Initiated',          color: '#F59E0B', icon: 'pay' },
  payment_posted:        { label: 'Payment Posted',             color: '#10B981', icon: 'check' },
  payment_link_sent:     { label: 'Payment Link Sent',          color: '#60A5FA', icon: 'link' },
  check_expected:        { label: 'Check Expected',             color: '#F59E0B', icon: 'check-mail' },
  check_received:        { label: 'Check Received by Agency',   color: '#10B981', icon: 'check' },
  check_cleared:         { label: 'Check Cleared',              color: '#10B981', icon: 'check' },
  support_opened:        { label: 'Support Request Opened',     color: '#A78BFA', icon: 'support' },
  message_sent:          { label: 'Message Sent',               color: '#A78BFA', icon: 'msg' },
  message_received:      { label: 'Message Received',           color: '#818CF8', icon: 'msg' },
  plan_started:          { label: 'Payment Plan Started',       color: '#F59E0B', icon: 'plan' },
  plan_payment:          { label: 'Plan Payment Made',          color: '#10B981', icon: 'check' },
  receipt_generated:     { label: 'Receipt Generated',          color: '#10B981', icon: 'receipt' },
  document_uploaded:     { label: 'Document Uploaded',          color: '#60A5FA', icon: 'doc' },
  insurance_submitted:   { label: 'Insurance Submitted',        color: '#818CF8', icon: 'ins' },
  portal_login:          { label: 'Portal Access',              color: '#52525B', icon: 'lock' },
  invoice_viewed:        { label: 'Invoice Viewed',             color: '#52525B', icon: 'eye' },
};

const DEFAULT_EVENT = { label: 'Account Event', color: '#52525B', icon: 'dot' };

function EventIcon({ type }: { type: string }) {
  const p = { width: 12, height: 12, viewBox: '0 0 24 24', fill: 'none', stroke: 'currentColor', strokeWidth: 2, strokeLinecap: 'round' as const, strokeLinejoin: 'round' as const };
  switch (type) {
    case 'doc':       return <svg {...p}><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><polyline points="14 2 14 8 20 8"/></svg>;
    case 'mail':      return <svg {...p}><path d="M4 4h16c1.1 0 2 .9 2 2v12c0 1.1-.9 2-2 2H4c-1.1 0-2-.9-2-2V6c0-1.1.9-2 2-2z"/><polyline points="22,6 12,13 2,6"/></svg>;
    case 'pay':       return <svg {...p}><rect x="1" y="4" width="22" height="16" rx="2"/><line x1="1" y1="10" x2="23" y2="10"/></svg>;
    case 'check':     return <svg {...p}><polyline points="20 6 9 17 4 12"/></svg>;
    case 'link':      return <svg {...p}><path d="M10 13a5 5 0 0 0 7.54.54l3-3a5 5 0 0 0-7.07-7.07l-1.72 1.71"/><path d="M14 11a5 5 0 0 0-7.54-.54l-3 3a5 5 0 0 0 7.07 7.07l1.71-1.71"/></svg>;
    case 'check-mail':return <svg {...p}><path d="M4 4h16c1.1 0 2 .9 2 2v12c0 1.1-.9 2-2 2H4c-1.1 0-2-.9-2-2V6c0-1.1.9-2 2-2z"/></svg>;
    case 'support':   return <svg {...p}><circle cx="12" cy="12" r="10"/><circle cx="12" cy="12" r="4"/></svg>;
    case 'msg':       return <svg {...p}><path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"/></svg>;
    case 'plan':      return <svg {...p}><rect x="3" y="4" width="18" height="18" rx="2"/><line x1="3" y1="10" x2="21" y2="10"/></svg>;
    case 'receipt':   return <svg {...p}><polyline points="7 8 3 8 3 21 21 21 21 8 17 8"/><rect x="7" y="2" width="10" height="6" rx="1"/></svg>;
    case 'ins':       return <svg {...p}><path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"/></svg>;
    case 'lock':      return <svg {...p}><rect x="3" y="11" width="18" height="11" rx="2" ry="2"/><path d="M7 11V7a5 5 0 0 1 10 0v4"/></svg>;
    case 'eye':       return <svg {...p}><path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z"/><circle cx="12" cy="12" r="3"/></svg>;
    default:          return <svg {...p}><circle cx="12" cy="12" r="3" fill="currentColor" stroke="none"/></svg>;
  }
}

function fmtDateTime(s: string): { date: string; time: string } {
  const d = new Date(s);
  return {
    date: d.toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' }),
    time: d.toLocaleTimeString('en-US', { hour: '2-digit', minute: '2-digit' }),
  };
}

// Group events by date
function groupByDate(events: ActivityEvent[]): Array<{ date: string; events: ActivityEvent[] }> {
  const map = new Map<string, ActivityEvent[]>();
  for (const ev of events) {
    const d = new Date(ev.created_at).toLocaleDateString('en-US', { weekday: 'long', month: 'long', day: 'numeric', year: 'numeric' });
    if (!map.has(d)) map.set(d, []);
    map.get(d)!.push(ev);
  }
  return Array.from(map.entries()).map(([date, evs]) => ({ date, events: evs }));
}

export default function ActivityPage() {
  const [events, setEvents] = useState<ActivityEvent[]>([]);
  const [loading, setLoading] = useState(true);
  const [fetchError, setFetchError] = useState<string | null>(null);
  const apiBase = process.env.NEXT_PUBLIC_API_BASE ?? process.env.NEXT_PUBLIC_API_URL ?? '';

  useEffect(() => {
    fetch(`${apiBase}/api/v1/portal/activity`, { credentials: 'include' })
      .then(r => r.json())
      .then(d => setEvents(Array.isArray(d) ? d : d.items ?? []))
      .catch((err: unknown) => setFetchError(err instanceof Error ? err.message : 'Failed to load activity'))
      .finally(() => setLoading(false));
  }, [apiBase]);

  const grouped = groupByDate(events);

  return (
    <div className="max-w-3xl mx-auto px-4 py-8">
      {/* Header */}
      <div className="mb-8">
        <div className="flex items-center gap-3 mb-1">
          <div className="w-[3px] h-6 bg-[#FF4D00] shadow-[0_0_8px_rgba(255,77,0,0.6)]" />
          <h1 className="text-xl font-black tracking-[0.12em] text-white uppercase">Account Activity</h1>
        </div>
        <p className="text-sm text-zinc-500 ml-5">Complete timeline of all activity on your billing account.</p>
      </div>

      {fetchError && (
        <div className="mb-6 px-4 py-3 bg-red-500/8 border border-red-500/20 text-sm text-red-400" style={{ clipPath: 'polygon(0 0, calc(100% - 6px) 0, 100% 6px, 100% 100%, 0 100%)' }}>
          Unable to load account activity. Please refresh the page or contact billing support.
        </div>
      )}

      {loading ? (
        <div className="space-y-3">
          {Array.from({ length: 5 }).map((_, i) => (
            <div key={i} className="bg-[#0A0A0B] border border-zinc-900 h-16 animate-pulse" style={{ clipPath: 'polygon(0 0, calc(100% - 8px) 0, 100% 8px, 100% 100%, 0 100%)' }} />
          ))}
        </div>
      ) : events.length === 0 ? (
        <div className="bg-[#0A0A0B] border border-zinc-800 py-16 text-center" style={{ clipPath: 'polygon(0 0, calc(100% - 10px) 0, 100% 10px, 100% 100%, 0 100%)' }}>
          <div className="text-2xl mb-3 opacity-20">📋</div>
          <p className="text-sm text-zinc-500">No account activity yet.</p>
        </div>
      ) : (
        <div className="space-y-8">
          {grouped.map(group => (
            <div key={group.date}>
              {/* Date header */}
              <div className="flex items-center gap-3 mb-4">
                <div className="text-[10px] font-bold tracking-[0.2em] text-zinc-600 uppercase">{group.date}</div>
                <div className="flex-1 h-[1px] bg-zinc-900" />
              </div>

              {/* Events for this date */}
              <div className="relative pl-6">
                {/* Timeline line */}
                <div className="absolute left-[7px] top-0 bottom-0 w-[1px] bg-zinc-900" />

                <div className="space-y-4">
                  {group.events.map((ev, i) => {
                    const cfg = EVENT_CONFIG[ev.event_type] ?? DEFAULT_EVENT;
                    const ts = fmtDateTime(ev.created_at);
                    const isLast = i === group.events.length - 1;
                    return (
                      <div key={ev.id} className="relative flex items-start gap-4">
                        {/* Dot */}
                        <div
                          className="absolute left-[-19px] w-4 h-4 flex items-center justify-center border"
                          style={{ background: cfg.color + '15', borderColor: cfg.color + '40', color: cfg.color, clipPath: 'polygon(0 0, calc(100% - 3px) 0, 100% 3px, 100% 100%, 0 100%)' }}
                        >
                          <EventIcon type={cfg.icon} />
                        </div>

                        {/* Content */}
                        <div className={`flex-1 bg-[#0A0A0B] border border-zinc-900 p-3.5 ${!isLast ? 'mb-1' : ''}`}
                          style={{ clipPath: 'polygon(0 0, calc(100% - 6px) 0, 100% 6px, 100% 100%, 0 100%)' }}
                        >
                          <div className="flex items-start justify-between gap-2">
                            <div>
                              <span
                                className="text-[9px] font-bold tracking-widest uppercase px-1.5 py-0.5 border mr-2"
                                style={{ background: cfg.color + '10', borderColor: cfg.color + '25', color: cfg.color }}
                              >
                                {cfg.label}
                              </span>
                              <p className="inline text-xs text-zinc-300">{ev.description}</p>
                            </div>
                            <div className="flex-shrink-0 text-right">
                              <div className="text-[10px] text-zinc-600">{ts.time}</div>
                            </div>
                          </div>
                          {ev.metadata && Object.keys(ev.metadata).length > 0 && (
                            <div className="mt-2 flex flex-wrap gap-2">
                              {Object.entries(ev.metadata).slice(0, 3).map(([k, v]) => (
                                v !== null && v !== undefined && (
                                  <span key={k} className="text-[9px] text-zinc-600 font-mono">
                                    {k}: <span className="text-zinc-400">{String(v)}</span>
                                  </span>
                                )
                              ))}
                            </div>
                          )}
                        </div>
                      </div>
                    );
                  })}
                </div>
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Footer note */}
      <div className="mt-8 border-t border-zinc-900 pt-6 text-center">
        <p className="text-[10px] text-zinc-700 font-mono">
          Activity log shows all billing events for your account. For questions, contact{' '}
          <Link href="/portal/patient/support" className="text-zinc-500 hover:text-zinc-300 transition-colors underline">billing support</Link>.
        </p>
      </div>
    </div>
  );
}


