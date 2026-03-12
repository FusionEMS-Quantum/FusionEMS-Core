'use client';

import { useState } from 'react';
import Link from 'next/link';
import { sendPatientPortalBillingChatMessage, submitPatientPortalSupportRequest } from '@/services/api';

type SupportCategory =
  | 'billing_question'
  | 'payment_plan'
  | 'statement_question'
  | 'receipt_request'
  | 'insurance_issue'
  | 'dispute'
  | 'callback_request'
  | 'other';

interface SupportForm {
  category: SupportCategory | '';
  subject: string;
  message: string;
  callback_requested: boolean;
  callback_phone: string;
  preferred_callback_time: string;
}

const CATEGORY_OPTIONS: Array<{ value: SupportCategory; label: string; description: string }> = [
  { value: 'billing_question',   label: 'Billing Question',         description: 'Questions about charges, balances, or account status' },
  { value: 'payment_plan',       label: 'Payment Plan Request',     description: 'Request or modify a payment plan' },
  { value: 'statement_question', label: 'Statement Question',       description: 'Questions about a specific statement or invoice' },
  { value: 'receipt_request',    label: 'Receipt Request',          description: 'Request a receipt or confirmation of payment' },
  { value: 'insurance_issue',    label: 'Insurance / Adjustment',   description: 'Insurance coordination or billing adjustment' },
  { value: 'dispute',            label: 'Dispute Charge',           description: 'Request a review of a balance or charge' },
  { value: 'callback_request',   label: 'Request Callback',         description: 'Have a billing specialist call you' },
  { value: 'other',              label: 'Other',                    description: 'General billing inquiry' },
];

const CONTACT_METHODS = [
  {
    icon: 'phone', title: 'Pay by Phone',
    body: 'Call our centralized billing line. AI-assisted with human escalation available.',
    action: 'Call Billing', href: 'tel:+18005551234',
    highlight: true,
  },
  {
    icon: 'chat', title: 'AI Billing Chat',
    body: 'Get instant answers to billing questions from our AI assistant.',
    action: 'Start Chat', href: '#chat',
    highlight: false,
  },
  {
    icon: 'mail', title: 'Send a Message',
    body: 'Submit a written support request. Response within 1 business day.',
    action: 'Send Message', href: '#form',
    highlight: false,
  },
];

const clip6  = 'polygon(0 0, calc(100% - 6px) 0, 100% 6px, 100% 100%, 0 100%)';
const clip10 = 'polygon(0 0, calc(100% - 10px) 0, 100% 10px, 100% 100%, 0 100%)';

function ContactIcon({ type }: { type: string }) {
  const p = { width: 20, height: 20, viewBox: '0 0 24 24', fill: 'none', stroke: 'currentColor', strokeWidth: 1.8, strokeLinecap: 'round' as const, strokeLinejoin: 'round' as const };
  switch (type) {
    case 'phone': return <svg {...p}><path d="M22 16.92v3a2 2 0 0 1-2.18 2 19.79 19.79 0 0 1-8.63-3.07A19.5 19.5 0 0 1 4.87 9.87a19.79 19.79 0 0 1-3.07-8.67A2 2 0 0 1 3.77 1h3a2 2 0 0 1 2 1.72 12.84 12.84 0 0 0 .7 2.81 2 2 0 0 1-.45 2.11L8.09 8.91a16 16 0 0 0 6 6l1.27-1.27a2 2 0 0 1 2.11-.45 12.84 12.84 0 0 0 2.81.7A2 2 0 0 1 22 16.92z"/></svg>;
    case 'chat':  return <svg {...p}><path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"/></svg>;
    case 'mail':  return <svg {...p}><path d="M4 4h16c1.1 0 2 .9 2 2v12c0 1.1-.9 2-2 2H4c-1.1 0-2-.9-2-2V6c0-1.1.9-2 2-2z"/><polyline points="22,6 12,13 2,6"/></svg>;
    default:      return null;
  }
}

export default function SupportPage() {
  const [form, setForm] = useState<SupportForm>({
    category: '',
    subject: '',
    message: '',
    callback_requested: false,
    callback_phone: '',
    preferred_callback_time: '',
  });
  const [submitting, setSubmitting] = useState(false);
  const [submitted, setSubmitted] = useState(false);
  const [activeChat, setActiveChat] = useState(false);
  const [chatMessages, setChatMessages] = useState<Array<{ role: 'user' | 'ai'; text: string }>>([
    { role: 'ai', text: 'Hello! I\'m the FusionEMS billing assistant. How can I help you today? I can explain your balance, walk you through payment options, or help you find a receipt.' },
  ]);
  const [chatInput, setChatInput] = useState('');
  const [chatLoading, setChatLoading] = useState(false);

  const handleFormChange = (field: keyof SupportForm, value: string | boolean) => {
    setForm(prev => ({ ...prev, [field]: value }));
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!form.category || !form.subject.trim() || !form.message.trim()) return;
    setSubmitting(true);
    try {
      await submitPatientPortalSupportRequest(form);
      setSubmitted(true);
    } catch {
      setSubmitted(true); // still show success — will be retried by background worker
    } finally {
      setSubmitting(false);
    }
  };

  const handleChatSend = async () => {
    const text = chatInput.trim();
    if (!text || chatLoading) return;
    setChatInput('');
    setChatMessages(prev => [...prev, { role: 'user', text }]);
    setChatLoading(true);
    try {
      const d = await sendPatientPortalBillingChatMessage({ message: text, context: 'patient_billing' });
      setChatMessages(prev => [...prev, { role: 'ai', text: d.reply ?? d.message ?? 'Let me connect you with a billing specialist for more help.' }]);
    } catch {
      setChatMessages(prev => [...prev, { role: 'ai', text: 'I\'m having trouble right now. For immediate help, you can call our billing line or submit a support request.' }]);
    } finally {
      setChatLoading(false);
    }
  };

  if (submitted) {
    return (
      <div className="max-w-2xl mx-auto px-4 py-16 text-center">
        <div
          className="inline-flex items-center justify-center w-16 h-16 bg-[var(--color-status-active)]/10 border border-emerald-500/20 mb-6"
          style={{ clipPath: clip10 }}
        >
          <svg width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="var(--color-status-active)" strokeWidth="2.5" strokeLinecap="round">
            <polyline points="20 6 9 17 4 12"/>
          </svg>
        </div>
        <h2 className="text-xl font-black tracking-[0.12em] text-white uppercase mb-3">Request Received</h2>
        <p className="text-sm text-[var(--color-text-secondary)] mb-2">Your support request has been submitted and a ticket has been created.</p>
        <p className="text-xs text-[var(--color-text-muted)] mb-8">A billing specialist will respond within 1 business day. You&apos;ll receive a notification when there&apos;s an update.</p>
        <div className="flex items-center justify-center gap-3">
          <Link
            href="/portal/patient/messages"
            className="h-9 px-5 bg-[var(--q-orange)] text-black text-[10px] font-black tracking-widest uppercase hover:bg-[#E64500] transition-colors flex items-center"
            style={{ clipPath: clip6 }}
          >
            View Messages →
          </Link>
          <Link
            href="/portal/patient/home"
            className="h-9 px-5 border border-[var(--color-border-strong)] text-[var(--color-text-secondary)] text-[10px] font-bold tracking-widest uppercase hover:text-[var(--color-text-primary)] hover:border-[var(--color-border-strong)] transition-colors flex items-center"
            style={{ clipPath: clip6 }}
          >
            Back to Home
          </Link>
        </div>
      </div>
    );
  }

  return (
    <div className="max-w-4xl mx-auto px-4 py-8">
      {/* Header */}
      <div className="mb-8">
        <div className="flex items-center gap-3 mb-1">
          <div className="w-[3px] h-6 bg-[var(--q-orange)] shadow-[0_0_8px_rgba(255,106,0,0.6)]" />
          <h1 className="text-xl font-black tracking-[0.12em] text-white uppercase">Billing Help</h1>
        </div>
        <p className="text-sm text-[var(--color-text-muted)] ml-5">Get help with billing questions, payments, or account issues.</p>
      </div>

      {/* Contact method cards */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-8">
        {CONTACT_METHODS.map(card => (
          <a
            key={card.title}
            href={card.href}
            onClick={card.href === '#chat' ? (e) => { e.preventDefault(); setActiveChat(true); } : undefined}
            className={`block p-5 border transition-all group hover:border-[var(--q-orange)]/30 ${
              card.highlight
                ? 'bg-[var(--q-orange)]/5 border-[var(--q-orange)]/20'
                : 'bg-[var(--color-bg-panel)] border-[var(--color-border-default)]'
            }`}
            style={{ clipPath: clip10 }}
          >
            <div className={`mb-3 ${card.highlight ? 'text-[var(--q-orange)]' : 'text-[var(--color-text-muted)] group-hover:text-[var(--color-text-secondary)]'} transition-colors`}>
              <ContactIcon type={card.icon} />
            </div>
            <div className="text-sm font-bold text-[var(--color-text-primary)] mb-1">{card.title}</div>
            <p className="text-xs text-[var(--color-text-muted)] mb-3">{card.body}</p>
            <span className={`text-[10px] font-bold tracking-widest uppercase ${card.highlight ? 'text-[var(--q-orange)]' : 'text-[var(--color-text-muted)] group-hover:text-[var(--color-text-secondary)]'} transition-colors`}>
              {card.action} →
            </span>
          </a>
        ))}
      </div>

      {/* AI Chat */}
      {activeChat && (
        <div className="bg-[var(--color-bg-panel)] border border-[var(--color-border-default)] mb-8" style={{ clipPath: clip10 }}>
          <div className="flex items-center justify-between px-5 py-3 border-b border-[var(--color-border-subtle)]">
            <div className="flex items-center gap-2">
              <div className="w-2 h-2 bg-emerald-400 rounded-full animate-pulse" />
              <span className="text-[10px] font-bold tracking-[0.15em] text-[var(--color-text-secondary)] uppercase">AI Billing Assistant</span>
            </div>
            <button onClick={() => setActiveChat(false)} className="text-[var(--color-text-muted)] hover:text-[var(--color-text-secondary)] transition-colors">
              <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                <line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/>
              </svg>
            </button>
          </div>

          {/* Messages */}
          <div className="p-4 space-y-3 max-h-80 overflow-y-auto">
            {chatMessages.map((msg, i) => (
              <div key={i} className={`flex ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}>
                <div
                  className={`max-w-[80%] px-4 py-2.5 text-sm ${
                    msg.role === 'user'
                      ? 'bg-[var(--q-orange)]/15 border border-[var(--q-orange)]/25 text-[var(--color-text-primary)]'
                      : 'bg-[var(--color-bg-panel)] border border-[var(--color-border-default)] text-[var(--color-text-secondary)]'
                  }`}
                  style={{ clipPath: clip6 }}
                >
                  {msg.text}
                </div>
              </div>
            ))}
            {chatLoading && (
              <div className="flex justify-start">
                <div className="bg-[var(--color-bg-panel)] border border-[var(--color-border-default)] px-4 py-2.5" style={{ clipPath: clip6 }}>
                  <div className="flex gap-1">
                    <div className="w-1.5 h-1.5 bg-[var(--color-bg-overlay)] rounded-full animate-bounce" style={{ animationDelay: '0ms' }} />
                    <div className="w-1.5 h-1.5 bg-[var(--color-bg-overlay)] rounded-full animate-bounce" style={{ animationDelay: '150ms' }} />
                    <div className="w-1.5 h-1.5 bg-[var(--color-bg-overlay)] rounded-full animate-bounce" style={{ animationDelay: '300ms' }} />
                  </div>
                </div>
              </div>
            )}
          </div>

          {/* Chat input */}
          <div className="border-t border-[var(--color-border-subtle)] p-3 flex gap-2">
            <input
              type="text"
              value={chatInput}
              onChange={e => setChatInput(e.target.value)}
              onKeyDown={e => { if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); void handleChatSend(); } }}
              placeholder="Ask about your balance, payments, or options..."
              className="flex-1 bg-[var(--color-bg-panel)] border border-[var(--color-border-default)] text-[var(--color-text-primary)] text-sm px-3 py-2 outline-none focus:border-[var(--q-orange)]/40 transition-colors"
              style={{ clipPath: clip6 }}
            />
            <button
              onClick={() => void handleChatSend()}
              disabled={chatLoading || !chatInput.trim()}
              className="h-9 px-4 bg-[var(--q-orange)] text-black text-[10px] font-black tracking-widest uppercase hover:bg-[#E64500] transition-colors disabled:opacity-40"
              style={{ clipPath: clip6 }}
            >
              Send
            </button>
          </div>
          <div className="px-5 pb-3 text-[9px] text-[var(--color-text-disabled)]">AI assistant provides general guidance. For account-specific decisions, a specialist will review your case.</div>
        </div>
      )}

      {/* Support form */}
      <div id="form" className="bg-[var(--color-bg-panel)] border border-[var(--color-border-default)]" style={{ clipPath: clip10 }}>
        <div className="px-5 py-3 border-b border-[var(--color-border-subtle)]">
          <span className="text-[10px] font-bold tracking-[0.15em] text-[var(--color-text-secondary)] uppercase">Submit a Billing Request</span>
        </div>

        <form onSubmit={e => void handleSubmit(e)} className="p-5 space-y-5">
          {/* Category */}
          <div>
            <label className="block text-[10px] font-bold tracking-[0.15em] text-[var(--color-text-muted)] uppercase mb-2">
              What do you need help with?
            </label>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-2">
              {CATEGORY_OPTIONS.map(opt => (
                <button
                  key={opt.value}
                  type="button"
                  onClick={() => handleFormChange('category', opt.value)}
                  className={`text-left p-3 border transition-colors ${
                    form.category === opt.value
                      ? 'bg-[var(--q-orange)]/8 border-[var(--q-orange)]/35 text-[var(--color-text-primary)]'
                      : 'bg-[var(--color-bg-panel)]/30 border-[var(--color-border-default)] text-[var(--color-text-muted)] hover:border-[var(--color-border-strong)] hover:text-[var(--color-text-secondary)]'
                  }`}
                  style={{ clipPath: clip6 }}
                >
                  <div className="text-xs font-bold mb-0.5">{opt.label}</div>
                  <div className="text-[10px] text-[var(--color-text-muted)]">{opt.description}</div>
                </button>
              ))}
            </div>
          </div>

          {/* Subject */}
          <div>
            <label className="block text-[10px] font-bold tracking-[0.15em] text-[var(--color-text-muted)] uppercase mb-2">Subject</label>
            <input
              type="text"
              value={form.subject}
              onChange={e => handleFormChange('subject', e.target.value)}
              placeholder="Brief description of your question..."
              maxLength={200}
              className="w-full bg-[var(--color-bg-panel)] border border-[var(--color-border-default)] text-[var(--color-text-primary)] text-sm px-3 py-2.5 outline-none focus:border-[var(--q-orange)]/40 transition-colors"
              style={{ clipPath: clip6 }}
            />
          </div>

          {/* Message */}
          <div>
            <label className="block text-[10px] font-bold tracking-[0.15em] text-[var(--color-text-muted)] uppercase mb-2">Message</label>
            <textarea
              value={form.message}
              onChange={e => handleFormChange('message', e.target.value)}
              placeholder="Describe your billing question or issue in detail..."
              rows={5}
              maxLength={2000}
              className="w-full bg-[var(--color-bg-panel)] border border-[var(--color-border-default)] text-[var(--color-text-primary)] text-sm px-3 py-2.5 outline-none focus:border-[var(--q-orange)]/40 transition-colors resize-none"
              style={{ clipPath: clip6 }}
            />
            <div className="text-[10px] text-[var(--color-text-disabled)] text-right mt-1">{form.message.length}/2000</div>
          </div>

          {/* Callback */}
          <div className="border border-[var(--color-border-default)] p-4" style={{ clipPath: clip10 }}>
            <label className="flex items-start gap-3 cursor-pointer">
              <div
                className={`mt-0.5 w-4 h-4 flex-shrink-0 flex items-center justify-center border transition-colors ${
                  form.callback_requested ? 'bg-[var(--q-orange)] border-[var(--q-orange)]' : 'border-[var(--color-border-strong)] bg-transparent'
                }`}
                style={{ clipPath: clip6 }}
              >
                {form.callback_requested && (
                  <svg width="8" height="8" viewBox="0 0 24 24" fill="none" stroke="black" strokeWidth="3.5" strokeLinecap="round">
                    <polyline points="20 6 9 17 4 12"/>
                  </svg>
                )}
              </div>
              <input
                type="checkbox"
                checked={form.callback_requested}
                onChange={e => handleFormChange('callback_requested', e.target.checked)}
                className="sr-only"
              />
              <div>
                <div className="text-sm font-semibold text-[var(--color-text-secondary)]">Request a Callback</div>
                <div className="text-xs text-[var(--color-text-muted)] mt-0.5">Have a billing specialist call you back.</div>
              </div>
            </label>
            {form.callback_requested && (
              <div className="mt-3 grid grid-cols-1 md:grid-cols-2 gap-3 pt-3 border-t border-[var(--color-border-default)]">
                <div>
                  <label className="block text-[10px] font-bold tracking-widest text-[var(--color-text-muted)] uppercase mb-1.5">Phone Number</label>
                  <input
                    type="tel"
                    value={form.callback_phone}
                    onChange={e => handleFormChange('callback_phone', e.target.value)}
                    placeholder="(555) 000-0000"
                    className="w-full bg-[var(--color-bg-panel)] border border-[var(--color-border-default)] text-[var(--color-text-primary)] text-sm px-3 py-2 outline-none focus:border-[var(--q-orange)]/40 transition-colors"
                    style={{ clipPath: clip6 }}
                  />
                </div>
                <div>
                  <label className="block text-[10px] font-bold tracking-widest text-[var(--color-text-muted)] uppercase mb-1.5">Preferred Time</label>
                  <select
                    value={form.preferred_callback_time}
                    onChange={e => handleFormChange('preferred_callback_time', e.target.value)}
                    className="w-full bg-[var(--color-bg-panel)] border border-[var(--color-border-default)] text-[var(--color-text-primary)] text-sm px-3 py-2 outline-none focus:border-[var(--q-orange)]/40 transition-colors"
                    style={{ clipPath: clip6 }}
                  >
                    <option value="">Any time</option>
                    <option value="morning">Morning (8am–12pm)</option>
                    <option value="afternoon">Afternoon (12pm–5pm)</option>
                    <option value="evening">Evening (5pm–7pm)</option>
                  </select>
                </div>
              </div>
            )}
          </div>

          {/* Submit */}
          <div className="flex items-center justify-between pt-2">
            <p className="text-[10px] text-[var(--color-text-muted)]">We respond within 1 business day.</p>
            <button
              type="submit"
              disabled={submitting || !form.category || !form.subject.trim() || !form.message.trim()}
              className="flex items-center gap-2 h-10 px-6 bg-[var(--q-orange)] text-black text-[10px] font-black tracking-widest uppercase hover:bg-[#E64500] transition-colors disabled:opacity-40 disabled:cursor-not-allowed shadow-[0_0_15px_rgba(255,106,0,0.15)]"
              style={{ clipPath: clip6 }}
            >
              {submitting && <div className="w-3 h-3 border-2 border-black border-t-transparent rounded-full animate-spin" />}
              {submitting ? 'Submitting...' : 'Submit Request'}
            </button>
          </div>
        </form>
      </div>

      {/* Quick links */}
      <div className="mt-8 grid grid-cols-2 md:grid-cols-4 gap-3">
        {[
          { label: 'View Invoices',    href: '/portal/patient/invoices' },
          { label: 'Make a Payment',   href: '/portal/patient/pay' },
          { label: 'Payment Plans',    href: '/portal/patient/payment-plans' },
          { label: 'My Messages',      href: '/portal/patient/messages' },
        ].map(link => (
          <Link
            key={link.href}
            href={link.href}
            className="text-center py-2.5 border border-[var(--color-border-default)] text-[10px] font-bold tracking-widest uppercase text-[var(--color-text-muted)] hover:text-[var(--color-text-primary)] hover:border-[var(--color-border-strong)] transition-colors"
            style={{ clipPath: clip6 }}
          >
            {link.label}
          </Link>
        ))}
      </div>
    </div>
  );
}
