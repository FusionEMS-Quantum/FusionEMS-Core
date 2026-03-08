'use client';
import { QuantumTableSkeleton } from '@/components/ui';

import { useEffect, useRef, useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';

const API = process.env.NEXT_PUBLIC_API_BASE ?? '';

type MessageSummary = {
  id: string;
  subject: string;
  from: { emailAddress: { name: string; address: string } };
  receivedDateTime: string;
  isRead: boolean;
  bodyPreview: string;
  hasAttachments: boolean;
};

type MessageDetail = MessageSummary & {
  body: { contentType: string; content: string };
  toRecipients: Array<{ emailAddress: { address: string } }>;
  ccRecipients: Array<{ emailAddress: { address: string } }>;
};

type Attachment = { id: string; name: string; contentType: string; size: number };

function Badge({ label, color }: { label: string; color: string }) {
  return (
    <span
      className="inline-flex items-center gap-1 px-2 py-0.5 chamfer-4 text-micro font-semibold uppercase tracking-wider border"
      style={{ borderColor: `${color}40`, color, background: `${color}12` }}
    >
      {label}
    </span>
  );
}

function Panel({ children, className }: { children: React.ReactNode; className?: string }) {
  return (
    <div
      className={`bg-[#0A0A0B] border border-border-DEFAULT ${className ?? ''}`}
      style={{ clipPath: 'polygon(0 0,calc(100% - 10px) 0,100% 10px,100% 100%,0 100%)' }}
    >
      {children}
    </div>
  );
}

function formatDate(iso: string) {
  const d = new Date(iso);
  return d.toLocaleDateString('en-US', { month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit' });
}

export default function FounderEmailPage() {
  const [messages, setMessages] = useState<MessageSummary[]>([]);
  const [loading, setLoading] = useState(true);
  const [selected, setSelected] = useState<MessageDetail | null>(null);
  const [attachments, setAttachments] = useState<Attachment[]>([]);
  const [view, setView] = useState<'inbox' | 'compose' | 'reply'>('inbox');
  const [sending, setSending] = useState(false);
  const [sendError, setSendError] = useState('');
  const [composeForm, setComposeForm] = useState({ to: '', cc: '', subject: '', body: '' });
  const [replyBody, setReplyBody] = useState('');
  const iframeRef = useRef<HTMLIFrameElement>(null);

  const load = (folder = 'inbox') => {
    setLoading(true);
    fetch(`${API}/api/v1/founder/graph/mail?folder=${folder}&top=30`)
      .then((r) => r.json())
      .then((d) => setMessages(d.value ?? []))
      .catch(() => setMessages([]))
      .finally(() => setLoading(false));
  };

  useEffect(() => { load(); }, []);

  const openMessage = async (msg: MessageSummary) => {
    try {
      const [detail, atts] = await Promise.all([
        fetch(`${API}/api/v1/founder/graph/mail/${msg.id}`).then((r) => r.json()),
        fetch(`${API}/api/v1/founder/graph/mail/${msg.id}/attachments`).then((r) => r.json()),
      ]);
      setSelected(detail);
      setAttachments(atts.value ?? []);
      setView('inbox');
    } catch (err: unknown) {
      console.warn("[email]", err);
    }
  };

  const sendMail = async () => {
    setSendError('');
    if (!composeForm.to || !composeForm.subject) { setSendError('To and Subject are required'); return; }
    setSending(true);
    try {
      const resp = await fetch(`${API}/api/v1/founder/graph/mail/send`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          to: composeForm.to.split(',').map((s) => s.trim()).filter(Boolean),
          cc: composeForm.cc ? composeForm.cc.split(',').map((s) => s.trim()).filter(Boolean) : undefined,
          subject: composeForm.subject,
          body_html: composeForm.body.replace(/\n/g, '<br>'),
        }),
      });
      if (!resp.ok) { const e = await resp.json(); setSendError(e.detail ?? 'Send failed'); return; }
      setComposeForm({ to: '', cc: '', subject: '', body: '' });
      setView('inbox');
    } finally {
      setSending(false);
    }
  };

  const sendReply = async () => {
    if (!selected || !replyBody) return;
    setSending(true);
    try {
      await fetch(`${API}/api/v1/founder/graph/mail/${selected.id}/reply`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ comment_html: replyBody.replace(/\n/g, '<br>') }),
      });
      setReplyBody('');
      setView('inbox');
    } finally {
      setSending(false);
    }
  };

  const downloadAttachment = (msgId: string, att: Attachment) => {
    window.open(`${API}/api/v1/founder/graph/mail/${msgId}/attachments/${att.id}/download`, '_blank');
  };

  const inputCls = 'w-full bg-bg-input border border-border-DEFAULT text-zinc-100 text-xs px-3 py-2 chamfer-4 focus:outline-none focus:border-orange';

  return (
    <div className="p-5 space-y-5 min-h-screen">
      <div className="flex items-center justify-between">
        <div>
          <div className="text-micro font-bold uppercase tracking-[0.2em] text-[#FF4D00]-dim mb-1">FOUNDER TOOLS · MICROSOFT GRAPH</div>
          <h1 className="text-xl font-black uppercase tracking-wider text-zinc-100">Inbox</h1>
          <p className="text-body text-zinc-500 mt-0.5">Application permissions · Founder mailbox only · No delegated access</p>
        </div>
        <div className="flex gap-2">
          {view !== 'compose' && (
            <button
              onClick={() => { setView('compose'); setSelected(null); }}
              className="px-4 py-2 text-xs font-semibold uppercase tracking-wider bg-brand-orange/[0.15] border border-brand-orange/[0.3] text-[#FF4D00] hover:bg-brand-orange/[0.25] transition-colors"
            >
              + Compose
            </button>
          )}
          <button
            onClick={() => load()}
            className="px-3 py-2 text-xs font-semibold uppercase tracking-wider border border-border-DEFAULT text-zinc-400 hover:text-zinc-100 transition-colors"
          >
            Refresh
          </button>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
        <Panel className="lg:col-span-1 overflow-hidden">
          <div className="p-3 border-b border-border-subtle text-micro font-semibold uppercase tracking-widest text-zinc-500">
            Inbox {!loading && `· ${messages.length} messages`}
          </div>
          {loading ? (
            <div className="p-6"><QuantumTableSkeleton rows={6} cols={4} /></div>
          ) : messages.length === 0 ? (
            <div className="p-6 text-center text-xs text-zinc-500">No messages</div>
          ) : (
            <div className="divide-y divide-white/[0.04] max-h-[60vh] overflow-y-auto">
              {messages.map((msg) => (
                <button
                  key={msg.id}
                  onClick={() => openMessage(msg)}
                  className={`w-full text-left px-3 py-3 hover:bg-zinc-950/[0.03] transition-colors ${selected?.id === msg.id ? 'bg-brand-orange/[0.06] border-l-2 border-orange' : ''}`}
                >
                  <div className="flex items-start justify-between gap-2 mb-0.5">
                    <span className={`text-body truncate ${msg.isRead ? 'text-zinc-400' : 'text-zinc-100 font-semibold'}`}>
                      {msg.from?.emailAddress?.name || msg.from?.emailAddress?.address || 'Unknown'}
                    </span>
                    <span className="text-micro text-zinc-500 whitespace-nowrap shrink-0">{formatDate(msg.receivedDateTime)}</span>
                  </div>
                  <div className={`text-body truncate mb-0.5 ${msg.isRead ? 'text-zinc-500' : 'text-zinc-100'}`}>{msg.subject || '(no subject)'}</div>
                  <div className="text-micro text-zinc-500 truncate">{msg.bodyPreview}</div>
                  {msg.hasAttachments && <div className="text-micro text-status-warning mt-0.5">+ attachments</div>}
                </button>
              ))}
            </div>
          )}
        </Panel>

        <Panel className="lg:col-span-2">
          <AnimatePresence mode="wait">
            {view === 'compose' ? (
              <motion.div key="compose" initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }} className="p-4 space-y-3">
                <div className="text-micro font-semibold uppercase tracking-widest text-zinc-500 mb-2">New Message</div>
                <input className={inputCls} placeholder="To (comma-separated)" value={composeForm.to} onChange={(e) => setComposeForm((f) => ({ ...f, to: e.target.value }))} />
                <input className={inputCls} placeholder="CC (optional)" value={composeForm.cc} onChange={(e) => setComposeForm((f) => ({ ...f, cc: e.target.value }))} />
                <input className={inputCls} placeholder="Subject" value={composeForm.subject} onChange={(e) => setComposeForm((f) => ({ ...f, subject: e.target.value }))} />
                <textarea className={`${inputCls} h-40 resize-none`} placeholder="Message body..." value={composeForm.body} onChange={(e) => setComposeForm((f) => ({ ...f, body: e.target.value }))} />
                {sendError && <div className="text-xs text-red">{sendError}</div>}
                <div className="flex gap-2">
                  <button onClick={sendMail} disabled={sending} className="px-4 py-2 text-xs font-semibold uppercase bg-brand-orange/[0.2] border border-brand-orange/[0.4] text-[#FF4D00] hover:bg-brand-orange/[0.3] disabled:opacity-40 transition-colors">
                    {sending ? 'Sending...' : 'Send'}
                  </button>
                  <button onClick={() => setView('inbox')} className="px-4 py-2 text-xs font-semibold uppercase border border-border-DEFAULT text-zinc-400 hover:text-zinc-100 transition-colors">
                    Cancel
                  </button>
                </div>
              </motion.div>
            ) : selected ? (
              <motion.div key={selected.id} initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }} className="flex flex-col h-full">
                <div className="p-4 border-b border-border-subtle">
                  <div className="flex items-start justify-between gap-3 mb-2">
                    <h2 className="text-sm font-bold text-zinc-100">{selected.subject || '(no subject)'}</h2>
                    <div className="flex gap-2 shrink-0">
                      {!selected.isRead && <Badge label="Unread" color="var(--color-status-info)" />}
                      {selected.hasAttachments && <Badge label="Attachments" color="var(--color-status-warning)" />}
                    </div>
                  </div>
                  <div className="text-body text-zinc-500 space-y-0.5">
                    <div><span className="text-zinc-500">From: </span>{selected.from?.emailAddress?.name} &lt;{selected.from?.emailAddress?.address}&gt;</div>
                    <div><span className="text-zinc-500">Date: </span>{formatDate(selected.receivedDateTime)}</div>
                  </div>
                </div>
                <div className="flex-1 p-4 overflow-auto">
                  {selected.body?.contentType === 'html' ? (
                    <iframe
                      ref={iframeRef}
                      srcDoc={selected.body.content}
                      className="w-full min-h-[300px] border-0 bg-zinc-950 chamfer-4"
                      sandbox=""
                      title="message-body"
                    />
                  ) : (
                    <pre className="text-xs text-zinc-100 whitespace-pre-wrap">{selected.body?.content}</pre>
                  )}
                </div>
                {attachments.length > 0 && (
                  <div className="px-4 pb-3 border-t border-border-subtle pt-3">
                    <div className="text-micro font-semibold uppercase tracking-widest text-zinc-500 mb-2">Attachments</div>
                    <div className="flex flex-wrap gap-2">
                      {attachments.map((att) => (
                        <button
                          key={att.id}
                          onClick={() => downloadAttachment(selected.id, att)}
                          className="flex items-center gap-1.5 px-3 py-1.5 text-body border border-border-DEFAULT text-zinc-400 hover:text-zinc-100 hover:border-white/[0.25] transition-colors"
                        >
                          <span>↓</span>
                          <span className="truncate max-w-[180px]">{att.name}</span>
                          <span className="text-[9px] text-zinc-500">({(att.size / 1024).toFixed(0)}KB)</span>
                        </button>
                      ))}
                    </div>
                  </div>
                )}
                <div className="p-4 border-t border-border-subtle">
                  {view === 'reply' ? (
                    <div className="space-y-2">
                      <textarea
                        className={`${inputCls} h-24 resize-none`}
                        placeholder="Reply..."
                        value={replyBody}
                        onChange={(e) => setReplyBody(e.target.value)}
                      />
                      <div className="flex gap-2">
                        <button onClick={sendReply} disabled={sending} className="px-4 py-1.5 text-xs font-semibold uppercase bg-brand-orange/[0.2] border border-brand-orange/[0.4] text-[#FF4D00] hover:bg-brand-orange/[0.3] disabled:opacity-40 transition-colors">
                          {sending ? 'Sending...' : 'Reply'}
                        </button>
                        <button onClick={() => setView('inbox')} className="px-4 py-1.5 text-xs font-semibold uppercase border border-border-DEFAULT text-zinc-400 hover:text-zinc-100 transition-colors">
                          Cancel
                        </button>
                      </div>
                    </div>
                  ) : (
                    <button
                      onClick={() => setView('reply')}
                      className="px-4 py-2 text-xs font-semibold uppercase tracking-wider border border-border-DEFAULT text-zinc-400 hover:text-zinc-100 hover:border-white/[0.25] transition-colors"
                    >
                      Reply
                    </button>
                  )}
                </div>
              </motion.div>
            ) : (
              <motion.div key="empty" initial={{ opacity: 0 }} animate={{ opacity: 1 }} className="flex items-center justify-center h-full p-12">
                <div className="text-center">
                  <div className="text-zinc-500 text-4xl mb-3">✉</div>
                  <div className="text-xs text-zinc-500">Select a message to read</div>
                </div>
              </motion.div>
            )}
          </AnimatePresence>
        </Panel>
      </div>
    </div>
  );
}
