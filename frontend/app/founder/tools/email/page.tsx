'use client';
import { QuantumTableSkeleton } from '@/components/ui';
import { ModuleDashboardShell } from '@/components/shells/PageShells';

import { useEffect, useRef, useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { getGraphMail, getGraphMailMessage, getGraphMailAttachments, sendGraphMail, replyGraphMail } from '@/services/api';

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
      className={`bg-[var(--color-bg-panel)] border border-[var(--color-border-default)] chamfer-12 ${className ?? ''}`}
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
    getGraphMail(folder, 30)
      .then((d) => setMessages(d.value ?? []))
      .catch(() => setMessages([]))
      .finally(() => setLoading(false));
  };

  useEffect(() => { load(); }, []);

  const openMessage = async (msg: MessageSummary) => {
    try {
      const [detail, atts] = await Promise.all([
        getGraphMailMessage(msg.id),
        getGraphMailAttachments(msg.id),
      ]);
      setSelected(detail as MessageDetail);
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
      await sendGraphMail({
        to: composeForm.to.split(',').map((s) => s.trim()).filter(Boolean),
        cc: composeForm.cc ? composeForm.cc.split(',').map((s) => s.trim()).filter(Boolean) : undefined,
        subject: composeForm.subject,
        body_html: composeForm.body.replace(/\n/g, '<br>'),
      });
      setComposeForm({ to: '', cc: '', subject: '', body: '' });
      setView('inbox');
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : 'Send failed';
      setSendError(msg);
    } finally {
      setSending(false);
    }
  };

  const sendReply = async () => {
    if (!selected || !replyBody) return;
    setSending(true);
    try {
      await replyGraphMail(selected.id, { body_html: replyBody.replace(/\n/g, '<br>') });
      setReplyBody('');
      setView('inbox');
    } finally {
      setSending(false);
    }
  };

  const downloadAttachment = (msgId: string, att: Attachment) => {
    window.open(`/api/v1/founder/graph/mail/${msgId}/attachments/${att.id}/download`, '_blank');
  };

  const inputCls = 'w-full bg-[var(--color-bg-input)] border border-[var(--color-border-default)] text-[var(--color-text-primary)] text-body px-3 py-2 chamfer-4 focus:outline-none focus:border-[var(--q-orange)]';

  return (
    <ModuleDashboardShell
      title="Inbox"
      subtitle="Application permissions · Founder mailbox only · No delegated access"
      headerActions={
        <div className="flex gap-2">
          {view !== 'compose' && (
            <button
              onClick={() => { setView('compose'); setSelected(null); }}
              className="quantum-btn text-micro font-label font-bold uppercase tracking-wider bg-[var(--color-brand-orange-ghost)] border border-[color-mix(in_srgb,var(--q-orange)_30%,transparent)] text-[var(--q-orange)] hover:bg-[color-mix(in_srgb,var(--q-orange)_15%,transparent)] transition-colors chamfer-4 px-4 py-2"
            >
              + Compose
            </button>
          )}
          <button
            onClick={() => load()}
            className="quantum-btn text-micro font-label font-bold uppercase tracking-wider border border-[var(--color-border-default)] text-[var(--color-text-secondary)] hover:text-[var(--color-text-primary)] transition-colors chamfer-4 px-3 py-2"
          >
            Refresh
          </button>
        </div>
      }
    >
      <div className="space-y-5">

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
        <Panel className="lg:col-span-1 overflow-hidden">
          <div className="p-3 border-b border-[var(--color-border-subtle)] text-micro font-label font-bold uppercase tracking-wider text-[var(--color-text-muted)]">
            Inbox {!loading && `· ${messages.length} messages`}
          </div>
          {loading ? (
            <div className="p-6"><QuantumTableSkeleton rows={6} cols={4} /></div>
          ) : messages.length === 0 ? (
            <div className="p-6 text-center text-micro text-[var(--color-text-muted)]">No messages</div>
          ) : (
            <div className="divide-y divide-white/[0.04] max-h-[60vh] overflow-y-auto">
              {messages.map((msg) => (
                <button
                  key={msg.id}
                  onClick={() => openMessage(msg)}
                  className={`w-full text-left px-3 py-3 hover:bg-[var(--color-bg-raised)] transition-colors ${selected?.id === msg.id ? 'bg-[var(--color-brand-orange-ghost)] border-l-2 border-[var(--q-orange)]' : ''}`}
                >
                  <div className="flex items-start justify-between gap-2 mb-0.5">
                    <span className={`text-body truncate ${msg.isRead ? 'text-[var(--color-text-secondary)]' : 'text-[var(--color-text-primary)] font-semibold'}`}>
                      {msg.from?.emailAddress?.name || msg.from?.emailAddress?.address || 'Unknown'}
                    </span>
                    <span className="text-micro text-[var(--color-text-muted)] whitespace-nowrap shrink-0">{formatDate(msg.receivedDateTime)}</span>
                  </div>
                  <div className={`text-body truncate mb-0.5 ${msg.isRead ? 'text-[var(--color-text-muted)]' : 'text-[var(--color-text-primary)]'}`}>{msg.subject || '(no subject)'}</div>
                  <div className="text-micro text-[var(--color-text-muted)] truncate">{msg.bodyPreview}</div>
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
                <div className="text-micro font-label font-bold uppercase tracking-wider text-[var(--color-text-muted)] mb-2">New Message</div>
                <input className={inputCls} placeholder="To (comma-separated)" value={composeForm.to} onChange={(e) => setComposeForm((f) => ({ ...f, to: e.target.value }))} />
                <input className={inputCls} placeholder="CC (optional)" value={composeForm.cc} onChange={(e) => setComposeForm((f) => ({ ...f, cc: e.target.value }))} />
                <input className={inputCls} placeholder="Subject" value={composeForm.subject} onChange={(e) => setComposeForm((f) => ({ ...f, subject: e.target.value }))} />
                <textarea className={`${inputCls} h-40 resize-none`} placeholder="Message body..." value={composeForm.body} onChange={(e) => setComposeForm((f) => ({ ...f, body: e.target.value }))} />
                {sendError && <div className="text-xs text-red">{sendError}</div>}
                <div className="flex gap-2">
                  <button onClick={sendMail} disabled={sending} className="quantum-btn-primary px-4 py-2 text-micro font-label font-bold uppercase chamfer-4 disabled:opacity-40 transition-colors">
                    {sending ? 'Sending...' : 'Send'}
                  </button>
                  <button onClick={() => setView('inbox')} className="quantum-btn px-4 py-2 text-micro font-label font-bold uppercase border border-[var(--color-border-default)] text-[var(--color-text-secondary)] hover:text-[var(--color-text-primary)] transition-colors chamfer-4">
                    Cancel
                  </button>
                </div>
              </motion.div>
            ) : selected ? (
              <motion.div key={selected.id} initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }} className="flex flex-col h-full">
                <div className="p-4 border-b border-border-subtle">
                  <div className="flex items-start justify-between gap-3 mb-2">
                    <h2 className="text-body font-bold text-[var(--color-text-primary)]">{selected.subject || '(no subject)'}</h2>
                    <div className="flex gap-2 shrink-0">
                      {!selected.isRead && <Badge label="Unread" color="var(--color-status-info)" />}
                      {selected.hasAttachments && <Badge label="Attachments" color="var(--color-status-warning)" />}
                    </div>
                  </div>
                  <div className="text-body text-[var(--color-text-muted)] space-y-0.5">
                    <div><span className="text-[var(--color-text-muted)]">From: </span>{selected.from?.emailAddress?.name} &lt;{selected.from?.emailAddress?.address}&gt;</div>
                    <div><span className="text-[var(--color-text-muted)]">Date: </span>{formatDate(selected.receivedDateTime)}</div>
                  </div>
                </div>
                <div className="flex-1 p-4 overflow-auto">
                  {selected.body?.contentType === 'html' ? (
                    <iframe
                      ref={iframeRef}
                      srcDoc={selected.body.content}
                      className="w-full min-h-[300px] border-0 bg-[var(--color-bg-base)] chamfer-4"
                      sandbox=""
                      title="message-body"
                    />
                  ) : (
                    <pre className="text-body text-[var(--color-text-primary)] whitespace-pre-wrap">{selected.body?.content}</pre>
                  )}
                </div>
                {attachments.length > 0 && (
                  <div className="px-4 pb-3 border-t border-border-subtle pt-3">
                    <div className="text-micro font-label font-bold uppercase tracking-wider text-[var(--color-text-muted)] mb-2">Attachments</div>
                    <div className="flex flex-wrap gap-2">
                      {attachments.map((att) => (
                        <button
                          key={att.id}
                          onClick={() => downloadAttachment(selected.id, att)}
                          className="flex items-center gap-1.5 px-3 py-1.5 text-body border border-[var(--color-border-default)] text-[var(--color-text-secondary)] hover:text-[var(--color-text-primary)] hover:border-[var(--color-border-strong)] transition-colors chamfer-4"
                        >
                          <span>↓</span>
                          <span className="truncate max-w-[180px]">{att.name}</span>
                          <span className="text-micro text-[var(--color-text-muted)]">({(att.size / 1024).toFixed(0)}KB)</span>
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
                        <button onClick={sendReply} disabled={sending} className="quantum-btn-primary px-4 py-1.5 text-micro font-label font-bold uppercase chamfer-4 disabled:opacity-40 transition-colors">
                          {sending ? 'Sending...' : 'Reply'}
                        </button>
                        <button onClick={() => setView('inbox')} className="quantum-btn px-4 py-1.5 text-micro font-label font-bold uppercase border border-[var(--color-border-default)] text-[var(--color-text-secondary)] hover:text-[var(--color-text-primary)] transition-colors chamfer-4">
                          Cancel
                        </button>
                      </div>
                    </div>
                  ) : (
                    <button
                      onClick={() => setView('reply')}
                      className="quantum-btn px-4 py-2 text-micro font-label font-bold uppercase tracking-wider border border-[var(--color-border-default)] text-[var(--color-text-secondary)] hover:text-[var(--color-text-primary)] hover:border-[var(--color-border-strong)] transition-colors chamfer-4"
                    >
                      Reply
                    </button>
                  )}
                </div>
              </motion.div>
            ) : (
              <motion.div key="empty" initial={{ opacity: 0 }} animate={{ opacity: 1 }} className="flex items-center justify-center h-full p-12">
                <div className="text-center">
                  <div className="text-[var(--color-text-disabled)] text-4xl mb-3">✉</div>
                  <div className="text-micro text-[var(--color-text-muted)]">Select a message to read</div>
                </div>
              </motion.div>
            )}
          </AnimatePresence>
        </Panel>
      </div>
    </div>
    </ModuleDashboardShell>
  );
}
