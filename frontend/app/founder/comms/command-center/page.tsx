'use client';

import React, { useState, useEffect, useCallback } from 'react';
import {
  Phone, MessageSquare, Mail, Printer, Bell, Volume2, FileText,
  Shield, MapPin, Send, Plus, RefreshCw, CheckCircle2, AlertTriangle,
  Cpu,
} from 'lucide-react';
import { API } from '@/services/api';

// ── Types ─────────────────────────────────────────────────────────────────────

type Channel = 'phone' | 'sms' | 'email' | 'fax' | 'print' | 'alerts' | 'audio' | 'templates' | 'ai' | 'baa' | 'wisconsin';

interface CallRecord { id: string; direction: string; to_number: string; from_number: string | null; status: string; duration_seconds: number | null; has_recording: boolean; created_at: string | null; }
interface SMSThread { id: string; to_number: string; display_name: string | null; message_count: number; last_message_at: string | null; is_archived: boolean; }
interface FaxRecord { id: string; direction: string; to_number: string; status: string; subject: string | null; page_count: number | null; created_at: string | null; }
interface PrintRecord { id: string; lob_letter_id: string | null; status: string; subject_line: string | null; expected_delivery_date: string | null; created_at: string | null; }
interface AlertRecord { id: string; channel: string; severity: string; subject: string; message: string; source_system: string | null; delivery_status: string; acknowledged_at: string | null; created_at: string | null; }
interface AudioConfig { id: string; alert_type: string; display_name: string; audio_url: string | null; is_enabled: boolean; priority: number; }
interface Template { id: string; name: string; channel: string; subject: string | null; is_active: boolean; version: number; }
interface BAATemplate { id: string; template_name: string; version_tag: string; effective_date: string | null; is_current: boolean; }
interface WisconsinTemplate { id: string; doc_type: string; display_name: string; version_tag: string; effective_date: string | null; is_current: boolean; wi_statute_reference: string | null; }

// ── Helpers ───────────────────────────────────────────────────────────────────

function authH() {
  if (typeof window === 'undefined') return {};
  const t = localStorage.getItem('token');
  return t ? { Authorization: `Bearer ${t}` } : {};
}

const CHANNELS: { id: Channel; label: string; icon: React.ReactNode; color: string }[] = [
  { id: 'phone',    label: 'Phone',       icon: <Phone size={14} />,         color: 'var(--color-status-active)' },
  { id: 'sms',      label: 'SMS',         icon: <MessageSquare size={14} />, color: 'var(--color-status-info)' },
  { id: 'email',    label: 'Email',       icon: <Mail size={14} />,          color: '#8B5CF6' },
  { id: 'fax',      label: 'Fax',         icon: <Printer size={14} />,       color: 'var(--q-yellow)' },
  { id: 'print',    label: 'Print/Mail',  icon: <Printer size={14} />,       color: '#6B7280' },
  { id: 'alerts',   label: 'Alerts',      icon: <Bell size={14} />,          color: 'var(--color-brand-red)' },
  { id: 'audio',    label: 'Audio',       icon: <Volume2 size={14} />,       color: '#EC4899' },
  { id: 'templates',label: 'Templates',   icon: <FileText size={14} />,      color: '#14B8A6' },
  { id: 'ai',       label: 'AI Draft',    icon: <Cpu size={14} />,           color: '#A855F7' },
  { id: 'baa',      label: 'BAA',         icon: <Shield size={14} />,        color: 'var(--q-orange)' },
  { id: 'wisconsin',label: 'WI Docs',     icon: <MapPin size={14} />,        color: '#F97316' },
];

function statusColor(s: string): string {
  const m: Record<string, string> = {
    completed: 'var(--color-status-active)', delivered: 'var(--color-status-active)', sent: 'var(--color-status-active)',
    failed: 'var(--color-brand-red)', returned: 'var(--color-brand-red)', no_answer: 'var(--color-brand-red)',
    sending: 'var(--q-yellow)', in_transit: 'var(--q-yellow)', ringing: 'var(--q-yellow)', initiated: 'var(--q-yellow)', queued: 'var(--q-yellow)',
    answered: 'var(--color-status-info)', received: 'var(--color-status-info)',
  };
  return m[s] ?? '#6B7280';
}

// ── Style constants ───────────────────────────────────────────────────────────

const S = {
  container: { display: 'flex', height: 'calc(100vh - 60px)', background: 'var(--color-bg-input)', color: 'var(--color-text-primary)', fontFamily: 'var(--font-geist-mono, monospace)', overflow: 'hidden' } as React.CSSProperties,
  sidebar: { width: 200, background: '#111118', borderRight: '1px solid var(--color-border-subtle)', display: 'flex', flexDirection: 'column' as const, overflow: 'hidden' },
  main: { flex: 1, display: 'flex', flexDirection: 'column' as const, overflow: 'hidden' },
  panelHeader: { padding: '12px 16px', borderBottom: '1px solid var(--color-border-subtle)', background: '#111118', display: 'flex', alignItems: 'center', justifyContent: 'space-between' },
  scroll: { flex: 1, overflowY: 'auto' as const, padding: 16 },
  label: { fontSize: 10, color: 'var(--color-text-muted)', fontWeight: 700, textTransform: 'uppercase' as const, letterSpacing: '0.08em', marginBottom: 6, display: 'block' },
  input: { width: '100%', padding: '7px 8px', background: 'var(--color-bg-input)', border: '1px solid var(--color-border-subtle)', borderRadius: 4, color: 'var(--color-text-primary)', fontSize: 12, outline: 'none', boxSizing: 'border-box' as const },
  textarea: { width: '100%', padding: '7px 8px', background: 'var(--color-bg-input)', border: '1px solid var(--color-border-subtle)', borderRadius: 4, color: 'var(--color-text-primary)', fontSize: 12, outline: 'none', boxSizing: 'border-box' as const, resize: 'vertical' as const },
  primaryBtn: { padding: '7px 14px', background: 'var(--q-orange)', border: 'none', borderRadius: 4, color: '#fff', fontSize: 11, fontWeight: 700, cursor: 'pointer', display: 'inline-flex', alignItems: 'center', gap: 6 } as React.CSSProperties,
  secondaryBtn: { padding: '6px 12px', background: 'transparent', border: '1px solid var(--color-border-default)', borderRadius: 4, color: 'var(--color-text-secondary)', fontSize: 11, cursor: 'pointer', display: 'inline-flex', alignItems: 'center', gap: 5 } as React.CSSProperties,
  card: { padding: '10px 12px', border: '1px solid var(--color-border-subtle)', borderRadius: 6, marginBottom: 8, background: '#0d0d14' } as React.CSSProperties,
  fg: { marginBottom: 12 } as React.CSSProperties,
  badge: (color: string): React.CSSProperties => ({ padding: '2px 8px', borderRadius: 10, fontSize: 10, fontWeight: 700, background: `${color}22`, color, border: `1px solid ${color}44` }),
};

// ── Main Component ────────────────────────────────────────────────────────────

export default function CommsCommandCenter() {
  const [channel, setChannel] = useState<Channel>('phone');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);

  // Data states
  const [calls, setCalls] = useState<CallRecord[]>([]);
  const [threads, setThreads] = useState<SMSThread[]>([]);
  const [faxes, setFaxes] = useState<FaxRecord[]>([]);
  const [printMail, setPrintMail] = useState<PrintRecord[]>([]);
  const [alerts, setAlerts] = useState<AlertRecord[]>([]);
  const [audioConfigs, setAudioConfigs] = useState<AudioConfig[]>([]);
  const [templates, setTemplates] = useState<Template[]>([]);
  const [baaTemplates, setBAATemplates] = useState<BAATemplate[]>([]);
  const [wiTemplates, setWITemplates] = useState<WisconsinTemplate[]>([]);
  const [aiDraft, setAIDraft] = useState<{ subject: string; body: string } | null>(null);

  // Form states
  const [toNumber, setToNumber] = useState('');
  const [smsBody, setSMSBody] = useState('');
  const [emailTo, setEmailTo] = useState('');
  const [emailSubject, setEmailSubject] = useState('');
  const [emailBody, setEmailBody] = useState('');
  const [faxTo, setFaxTo] = useState('');
  const [faxMedia, setFaxMedia] = useState('');
  const [faxSubject, setFaxSubject] = useState('');
  const [mailName, setMailName] = useState('');
  const [mailAddr1, setMailAddr1] = useState('');
  const [mailCity, setMailCity] = useState('');
  const [mailState, setMailState] = useState('');
  const [mailZip, setMailZip] = useState('');
  const [mailBody, setMailBody] = useState('');
  const [mailSubject, setMailSubject] = useState('');
  const [alertChannel, setAlertChannel] = useState('email');
  const [alertSeverity, setAlertSeverity] = useState('info');
  const [alertSubject, setAlertSubject] = useState('');
  const [alertMessage, setAlertMessage] = useState('');
  const [tmplName, setTmplName] = useState('');
  const [tmplChannel, setTmplChannel] = useState('email');
  const [tmplBody, setTmplBody] = useState('');
  const [tmplSubject, setTmplSubject] = useState('');
  const [aiContext, setAIContext] = useState('');
  const [aiChannel, setAIChannel] = useState('email');
  const [aiTone, setAITone] = useState('professional');
  const [baaName, setBAAName] = useState('');
  const [baaBody, setBAABody] = useState('');
  const [wiDocType, setWIDocType] = useState('');
  const [wiDisplayName, setWIDisplayName] = useState('');
  const [wiBody, setWIBody] = useState('');
  const [wiStatute, setWIStatute] = useState('');

  const showSuccess = (msg: string) => { setSuccess(msg); setTimeout(() => setSuccess(null), 4000); };
  const showError = (msg: string) => { setError(msg); setTimeout(() => setError(null), 6000); };

  // ── Data loaders ──────────────────────────────────────────────────────────

  const load = useCallback(async (ch: Channel) => {
    setLoading(true);
    try {
      switch (ch) {
        case 'phone': { const r = await API.get('/api/v1/founder/comms/calls', { headers: authH() }); setCalls(r.data); break; }
        case 'sms': { const r = await API.get('/api/v1/founder/comms/sms/threads', { headers: authH() }); setThreads(r.data); break; }
        case 'fax': { const r = await API.get('/api/v1/founder/comms/fax', { headers: authH() }); setFaxes(r.data); break; }
        case 'print': { const r = await API.get('/api/v1/founder/comms/print-mail', { headers: authH() }); setPrintMail(r.data); break; }
        case 'alerts': { const r = await API.get('/api/v1/founder/comms/alerts', { headers: authH() }); setAlerts(r.data); break; }
        case 'audio': { const r = await API.get('/api/v1/founder/comms/audio-config', { headers: authH() }); setAudioConfigs(r.data); break; }
        case 'templates': { const r = await API.get('/api/v1/founder/comms/templates', { headers: authH() }); setTemplates(r.data); break; }
        case 'baa': { const r = await API.get('/api/v1/founder/comms/baa-templates', { headers: authH() }); setBAATemplates(r.data); break; }
        case 'wisconsin': { const r = await API.get('/api/v1/founder/comms/wisconsin-docs', { headers: authH() }); setWITemplates(r.data); break; }
        default: break;
      }
    } catch (e: unknown) {
      showError(e instanceof Error ? e.message : 'Load failed');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { load(channel); }, [channel, load]);

  // ── Action handlers ───────────────────────────────────────────────────────

  const callHandle = async () => {
    if (!toNumber) return;
    try {
      await API.post('/api/v1/founder/comms/calls', { to_number: toNumber }, { headers: authH() });
      showSuccess(`Call initiated to ${toNumber}`);
      setToNumber('');
      load('phone');
    } catch (e: unknown) { showError(e instanceof Error ? e.message : 'Call failed'); }
  };

  const smsHandle = async () => {
    if (!toNumber || !smsBody) return;
    try {
      await API.post('/api/v1/founder/comms/sms', { to_number: toNumber, body: smsBody }, { headers: authH() });
      showSuccess('SMS sent');
      setSMSBody('');
      load('sms');
    } catch (e: unknown) { showError(e instanceof Error ? e.message : 'SMS failed'); }
  };

  const emailHandle = async () => {
    if (!emailTo || !emailSubject || !emailBody) return;
    try {
      await API.post('/api/v1/founder/comms/email', { to_email: emailTo, subject: emailSubject, body_html: `<p>${emailBody}</p>` }, { headers: authH() });
      showSuccess('Email sent');
      setEmailTo(''); setEmailSubject(''); setEmailBody('');
    } catch (e: unknown) { showError(e instanceof Error ? e.message : 'Email failed'); }
  };

  const faxHandle = async () => {
    if (!faxTo || !faxMedia) return;
    try {
      await API.post('/api/v1/founder/comms/fax', { to_number: faxTo, media_url: faxMedia, subject: faxSubject || undefined }, { headers: authH() });
      showSuccess('Fax queued');
      setFaxTo(''); setFaxMedia(''); setFaxSubject('');
      load('fax');
    } catch (e: unknown) { showError(e instanceof Error ? e.message : 'Fax failed'); }
  };

  const mailHandle = async () => {
    if (!mailName || !mailAddr1 || !mailCity || !mailState || !mailZip || !mailBody) return;
    try {
      await API.post('/api/v1/founder/comms/print-mail', {
        recipient_address: { name: mailName, address_line1: mailAddr1, city: mailCity, state: mailState, zip: mailZip },
        body_html: `<p>${mailBody}</p>`,
        subject_line: mailSubject || undefined,
      }, { headers: authH() });
      showSuccess('Letter queued with LOB');
      setMailName(''); setMailAddr1(''); setMailCity(''); setMailState(''); setMailZip(''); setMailBody(''); setMailSubject('');
      load('print');
    } catch (e: unknown) { showError(e instanceof Error ? e.message : 'Mail failed'); }
  };

  const alertHandle = async () => {
    if (!alertSubject || !alertMessage) return;
    try {
      await API.post('/api/v1/founder/comms/alerts', {
        channel: alertChannel, severity: alertSeverity,
        subject: alertSubject, message: alertMessage,
      }, { headers: authH() });
      showSuccess('Alert dispatched');
      setAlertSubject(''); setAlertMessage('');
      load('alerts');
    } catch (e: unknown) { showError(e instanceof Error ? e.message : 'Alert failed'); }
  };

  const ackAlert = async (id: string) => {
    try {
      await API.post(`/api/v1/founder/comms/alerts/${id}/acknowledge`, {}, { headers: authH() });
      load('alerts');
    } catch { /* noop */ }
  };

  const tmplHandle = async () => {
    if (!tmplName || !tmplBody) return;
    try {
      await API.post('/api/v1/founder/comms/templates', {
        name: tmplName, channel: tmplChannel, body_template: tmplBody, subject: tmplSubject || undefined,
      }, { headers: authH() });
      showSuccess('Template created');
      setTmplName(''); setTmplBody(''); setTmplSubject('');
      load('templates');
    } catch (e: unknown) { showError(e instanceof Error ? e.message : 'Template create failed'); }
  };

  const aiDraftHandle = async () => {
    if (!aiContext) return;
    setLoading(true);
    try {
      const r = await API.post('/api/v1/founder/comms/ai/draft', { channel: aiChannel, context: aiContext, tone: aiTone }, { headers: authH() });
      setAIDraft(r.data);
    } catch (e: unknown) { showError(e instanceof Error ? e.message : 'AI draft failed'); }
    finally { setLoading(false); }
  };

  const baaHandle = async () => {
    if (!baaName || !baaBody) return;
    try {
      await API.post('/api/v1/founder/comms/baa-templates', { template_name: baaName, body_html: baaBody }, { headers: authH() });
      showSuccess('BAA template created');
      setBAAName(''); setBAABody('');
      load('baa');
    } catch (e: unknown) { showError(e instanceof Error ? e.message : 'BAA create failed'); }
  };

  const wiHandle = async () => {
    if (!wiDocType || !wiDisplayName || !wiBody) return;
    try {
      await API.post('/api/v1/founder/comms/wisconsin-docs', {
        doc_type: wiDocType, display_name: wiDisplayName, body_html: wiBody,
        wi_statute_reference: wiStatute || undefined,
      }, { headers: authH() });
      showSuccess('Wisconsin doc template created');
      setWIDocType(''); setWIDisplayName(''); setWIBody(''); setWIStatute('');
      load('wisconsin');
    } catch (e: unknown) { showError(e instanceof Error ? e.message : 'WI doc create failed'); }
  };

  // ── Render ────────────────────────────────────────────────────────────────

  return (
    <div style={S.container}>
      {/* Sidebar */}
      <aside style={S.sidebar}>
        <div style={{ padding: '14px 16px 8px', borderBottom: '1px solid var(--color-border-subtle)' }}>
          <div style={{ fontSize: 10, fontWeight: 700, color: 'var(--q-orange)', letterSpacing: '0.1em', textTransform: 'uppercase' }}>Comms Command</div>
        </div>
        <div style={{ overflowY: 'auto', flex: 1 }}>
          {CHANNELS.map(ch => (
            <button
              key={ch.id}
              onClick={() => setChannel(ch.id)}
              style={{
                width: '100%', padding: '9px 16px', background: channel === ch.id ? 'var(--color-border-subtle)' : 'transparent',
                border: 'none', color: channel === ch.id ? 'var(--color-text-primary)' : 'var(--color-text-muted)', fontSize: 12,
                textAlign: 'left', cursor: 'pointer', display: 'flex', alignItems: 'center', gap: 10,
                borderLeft: channel === ch.id ? `3px solid ${ch.color}` : '3px solid transparent',
              }}
            >
              <span style={{ color: ch.color }}>{ch.icon}</span>
              {ch.label}
            </button>
          ))}
        </div>
      </aside>

      {/* Main panel */}
      <main style={S.main}>
        {/* Header */}
        <div style={S.panelHeader}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
            <span style={{ color: CHANNELS.find(c => c.id === channel)?.color }}>{CHANNELS.find(c => c.id === channel)?.icon}</span>
            <span style={{ fontSize: 13, fontWeight: 700, color: 'var(--color-text-primary)', textTransform: 'uppercase', letterSpacing: '0.05em' }}>
              {CHANNELS.find(c => c.id === channel)?.label}
            </span>
          </div>
          <button onClick={() => load(channel)} style={S.secondaryBtn}><RefreshCw size={12} /></button>
        </div>

        {/* Toast messages */}
        {success && (
          <div style={{ margin: '8px 16px 0', padding: '8px 12px', background: 'var(--color-status-active)22', border: '1px solid var(--color-status-active)44', borderRadius: 4, color: 'var(--color-status-active)', fontSize: 12, display: 'flex', alignItems: 'center', gap: 8 }}>
            <CheckCircle2 size={13} /> {success}
          </div>
        )}
        {error && (
          <div style={{ margin: '8px 16px 0', padding: '8px 12px', background: 'var(--color-brand-red)22', border: '1px solid var(--color-brand-red)44', borderRadius: 4, color: 'var(--color-brand-red)', fontSize: 12, display: 'flex', alignItems: 'center', gap: 8 }}>
            <AlertTriangle size={13} /> {error}
          </div>
        )}

        <div style={S.scroll}>

          {/* ── PHONE ── */}
          {channel === 'phone' && (
            <>
              <div style={S.card}>
                <div style={S.label}>Initiate Outbound Call</div>
                <div style={{ display: 'flex', gap: 8 }}>
                  <input value={toNumber} onChange={e => setToNumber(e.target.value)} placeholder="+1 (608) 555-0100" style={{ ...S.input, flex: 1 }} />
                  <button onClick={callHandle} style={S.primaryBtn}><Phone size={12} /> Call</button>
                </div>
              </div>
              <div style={S.label}>Call History</div>
              {loading && <div style={{ color: 'var(--color-text-muted)', fontSize: 12 }}>Loading…</div>}
              {calls.map(c => (
                <div key={c.id} style={S.card}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                    <span style={{ fontSize: 12, color: 'var(--color-text-primary)', fontWeight: 600 }}>{c.to_number}</span>
                    <span style={S.badge(statusColor(c.status))}>{c.status}</span>
                  </div>
                  <div style={{ fontSize: 11, color: 'var(--color-text-muted)', marginTop: 4, display: 'flex', gap: 12 }}>
                    <span>{c.direction}</span>
                    {c.duration_seconds != null && <span>{c.duration_seconds}s</span>}
                    {c.has_recording && <span style={{ color: 'var(--color-status-active)' }}>● Recording</span>}
                    <span>{c.created_at ? new Date(c.created_at).toLocaleString() : '—'}</span>
                  </div>
                </div>
              ))}
              {!loading && calls.length === 0 && <p style={{ color: 'var(--color-text-muted)', fontSize: 12 }}>No call records yet.</p>}
            </>
          )}

          {/* ── SMS ── */}
          {channel === 'sms' && (
            <>
              <div style={S.card}>
                <div style={S.label}>Send SMS</div>
                <div style={S.fg}>
                  <input value={toNumber} onChange={e => setToNumber(e.target.value)} placeholder="To number (+1…)" style={S.input} />
                </div>
                <div style={S.fg}>
                  <textarea value={smsBody} onChange={e => setSMSBody(e.target.value)} rows={3} placeholder="Message body (max 1600 chars)" style={S.textarea} />
                </div>
                <button onClick={smsHandle} style={S.primaryBtn}><Send size={12} /> Send SMS</button>
              </div>
              <div style={S.label}>Threads</div>
              {threads.map(t => (
                <div key={t.id} style={S.card}>
                  <div style={{ fontSize: 12, fontWeight: 600, color: 'var(--color-text-primary)' }}>{t.display_name ?? t.to_number}</div>
                  <div style={{ fontSize: 11, color: 'var(--color-text-muted)', display: 'flex', gap: 12, marginTop: 4 }}>
                    <span>{t.message_count} messages</span>
                    <span>{t.last_message_at ? new Date(t.last_message_at).toLocaleString() : '—'}</span>
                  </div>
                </div>
              ))}
              {!loading && threads.length === 0 && <p style={{ color: 'var(--color-text-muted)', fontSize: 12 }}>No SMS threads.</p>}
            </>
          )}

          {/* ── EMAIL ── */}
          {channel === 'email' && (
            <div style={S.card}>
              <div style={S.label}>Send Email via SES</div>
              <div style={S.fg}><input value={emailTo} onChange={e => setEmailTo(e.target.value)} placeholder="To email address" style={S.input} /></div>
              <div style={S.fg}><input value={emailSubject} onChange={e => setEmailSubject(e.target.value)} placeholder="Subject" style={S.input} /></div>
              <div style={S.fg}><textarea value={emailBody} onChange={e => setEmailBody(e.target.value)} rows={6} placeholder="Message body (plain text — will be wrapped in HTML)" style={S.textarea} /></div>
              <button onClick={emailHandle} style={S.primaryBtn}><Mail size={12} /> Send Email</button>
            </div>
          )}

          {/* ── FAX ── */}
          {channel === 'fax' && (
            <>
              <div style={S.card}>
                <div style={S.label}>Send Fax via Telnyx</div>
                <div style={S.fg}><input value={faxTo} onChange={e => setFaxTo(e.target.value)} placeholder="Fax number (+1…)" style={S.input} /></div>
                <div style={S.fg}><input value={faxMedia} onChange={e => setFaxMedia(e.target.value)} placeholder="PDF media URL (publicly accessible)" style={S.input} /></div>
                <div style={S.fg}><input value={faxSubject} onChange={e => setFaxSubject(e.target.value)} placeholder="Subject (optional)" style={S.input} /></div>
                <button onClick={faxHandle} style={S.primaryBtn}><Printer size={12} /> Send Fax</button>
              </div>
              <div style={S.label}>Fax History</div>
              {faxes.map(f => (
                <div key={f.id} style={S.card}>
                  <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                    <span style={{ fontSize: 12, color: 'var(--color-text-primary)' }}>{f.to_number}{f.subject ? ` — ${f.subject}` : ''}</span>
                    <span style={S.badge(statusColor(f.status))}>{f.status}</span>
                  </div>
                  <div style={{ fontSize: 11, color: 'var(--color-text-muted)', marginTop: 4 }}>
                    {f.direction} · {f.page_count != null ? `${f.page_count} pages` : 'unknown pages'} · {f.created_at ? new Date(f.created_at).toLocaleString() : '—'}
                  </div>
                </div>
              ))}
              {!loading && faxes.length === 0 && <p style={{ color: 'var(--color-text-muted)', fontSize: 12 }}>No fax records.</p>}
            </>
          )}

          {/* ── PRINT / MAIL ── */}
          {channel === 'print' && (
            <>
              <div style={S.card}>
                <div style={S.label}>Send Physical Letter (LOB)</div>
                <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 8, marginBottom: 8 }}>
                  <div><span style={S.label}>Name</span><input value={mailName} onChange={e => setMailName(e.target.value)} style={S.input} /></div>
                  <div><span style={S.label}>Subject</span><input value={mailSubject} onChange={e => setMailSubject(e.target.value)} style={S.input} /></div>
                  <div style={{ gridColumn: '1/-1' }}><span style={S.label}>Address Line 1</span><input value={mailAddr1} onChange={e => setMailAddr1(e.target.value)} style={S.input} /></div>
                  <div><span style={S.label}>City</span><input value={mailCity} onChange={e => setMailCity(e.target.value)} style={S.input} /></div>
                  <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 8 }}>
                    <div><span style={S.label}>State</span><input value={mailState} onChange={e => setMailState(e.target.value)} maxLength={2} style={S.input} /></div>
                    <div><span style={S.label}>ZIP</span><input value={mailZip} onChange={e => setMailZip(e.target.value)} style={S.input} /></div>
                  </div>
                </div>
                <div style={S.fg}><span style={S.label}>Letter Body</span><textarea value={mailBody} onChange={e => setMailBody(e.target.value)} rows={5} style={S.textarea} /></div>
                <button onClick={mailHandle} style={S.primaryBtn}><Printer size={12} /> Queue Letter</button>
              </div>
              <div style={S.label}>Mail History</div>
              {printMail.map(m => (
                <div key={m.id} style={S.card}>
                  <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                    <span style={{ fontSize: 12, color: 'var(--color-text-primary)' }}>{m.subject_line ?? '(no subject)'}</span>
                    <span style={S.badge(statusColor(m.status))}>{m.status}</span>
                  </div>
                  <div style={{ fontSize: 11, color: 'var(--color-text-muted)', marginTop: 4 }}>
                    LOB: {m.lob_letter_id ?? '—'} · EDD: {m.expected_delivery_date ?? 'unknown'}
                  </div>
                </div>
              ))}
              {!loading && printMail.length === 0 && <p style={{ color: 'var(--color-text-muted)', fontSize: 12 }}>No mail records.</p>}
            </>
          )}

          {/* ── ALERTS ── */}
          {channel === 'alerts' && (
            <>
              <div style={S.card}>
                <div style={S.label}>Dispatch Alert</div>
                <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 8, marginBottom: 8 }}>
                  <div>
                    <span style={S.label}>Channel</span>
                    <select value={alertChannel} onChange={e => setAlertChannel(e.target.value)} style={{ ...S.input, cursor: 'pointer' }}>
                      {['email', 'sms', 'voice', 'audit_log'].map(c => <option key={c} value={c}>{c}</option>)}
                    </select>
                  </div>
                  <div>
                    <span style={S.label}>Severity</span>
                    <select value={alertSeverity} onChange={e => setAlertSeverity(e.target.value)} style={{ ...S.input, cursor: 'pointer' }}>
                      {['info', 'warning', 'critical'].map(s => <option key={s} value={s}>{s}</option>)}
                    </select>
                  </div>
                </div>
                <div style={S.fg}><input value={alertSubject} onChange={e => setAlertSubject(e.target.value)} placeholder="Subject" style={S.input} /></div>
                <div style={S.fg}><textarea value={alertMessage} onChange={e => setAlertMessage(e.target.value)} rows={3} placeholder="Alert message" style={S.textarea} /></div>
                <button onClick={alertHandle} style={S.primaryBtn}><Bell size={12} /> Dispatch Alert</button>
              </div>
              <div style={S.label}>Alert Log</div>
              {alerts.map(a => (
                <div key={a.id} style={{ ...S.card, borderLeft: `3px solid ${a.severity === 'critical' ? 'var(--color-brand-red)' : a.severity === 'warning' ? 'var(--q-yellow)' : 'var(--color-status-active)'}` }}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                    <span style={{ fontSize: 12, color: 'var(--color-text-primary)', fontWeight: 600 }}>{a.subject}</span>
                    <div style={{ display: 'flex', gap: 6, alignItems: 'center' }}>
                      <span style={S.badge(statusColor(a.delivery_status))}>{a.delivery_status}</span>
                      {!a.acknowledged_at && (
                        <button onClick={() => ackAlert(a.id)} style={{ ...S.secondaryBtn, padding: '2px 8px', fontSize: 10 }}><CheckCircle2 size={10} /> Ack</button>
                      )}
                    </div>
                  </div>
                  <div style={{ fontSize: 11, color: 'var(--color-text-secondary)', marginTop: 4 }}>{a.message}</div>
                  <div style={{ fontSize: 10, color: 'var(--color-text-muted)', marginTop: 4 }}>{a.channel} · {a.source_system ?? 'manual'} · {a.created_at ? new Date(a.created_at).toLocaleString() : '—'}</div>
                </div>
              ))}
              {!loading && alerts.length === 0 && <p style={{ color: 'var(--color-text-muted)', fontSize: 12 }}>No alerts.</p>}
            </>
          )}

          {/* ── AUDIO CONFIG ── */}
          {channel === 'audio' && (
            <>
              <div style={S.label}>Audio Alert Configurations</div>
              {audioConfigs.map(a => (
                <div key={a.id} style={{ ...S.card, display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                  <div>
                    <div style={{ fontSize: 12, color: 'var(--color-text-primary)', fontWeight: 600 }}>{a.display_name}</div>
                    <div style={{ fontSize: 10, color: 'var(--color-text-muted)', marginTop: 2 }}>{a.alert_type} · priority {a.priority}</div>
                    {a.audio_url && <div style={{ fontSize: 10, color: 'var(--color-status-info)', marginTop: 2 }}>{a.audio_url}</div>}
                  </div>
                  <span style={S.badge(a.is_enabled ? 'var(--color-status-active)' : 'var(--color-text-muted)')}>{a.is_enabled ? 'ENABLED' : 'DISABLED'}</span>
                </div>
              ))}
              {!loading && audioConfigs.length === 0 && <p style={{ color: 'var(--color-text-muted)', fontSize: 12 }}>No audio configs. Use the API to configure alert types.</p>}
            </>
          )}

          {/* ── TEMPLATES ── */}
          {channel === 'templates' && (
            <>
              <div style={S.card}>
                <div style={S.label}>Create Template</div>
                <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 8, marginBottom: 8 }}>
                  <div><span style={S.label}>Name</span><input value={tmplName} onChange={e => setTmplName(e.target.value)} style={S.input} /></div>
                  <div>
                    <span style={S.label}>Channel</span>
                    <select value={tmplChannel} onChange={e => setTmplChannel(e.target.value)} style={{ ...S.input, cursor: 'pointer' }}>
                      {['email', 'sms', 'fax', 'voice', 'print_mail'].map(c => <option key={c} value={c}>{c}</option>)}
                    </select>
                  </div>
                  <div style={{ gridColumn: '1/-1' }}><span style={S.label}>Subject (email/fax)</span><input value={tmplSubject} onChange={e => setTmplSubject(e.target.value)} style={S.input} /></div>
                </div>
                <div style={S.fg}><span style={S.label}>Body Template (use {'{{variable}}'})</span><textarea value={tmplBody} onChange={e => setTmplBody(e.target.value)} rows={4} style={S.textarea} /></div>
                <button onClick={tmplHandle} style={S.primaryBtn}><Plus size={12} /> Create Template</button>
              </div>
              <div style={S.label}>Templates</div>
              {templates.map(t => (
                <div key={t.id} style={S.card}>
                  <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                    <span style={{ fontSize: 12, color: 'var(--color-text-primary)', fontWeight: 600 }}>{t.name}</span>
                    <span style={S.badge('#14B8A6')}>{t.channel}</span>
                  </div>
                  <div style={{ fontSize: 11, color: 'var(--color-text-muted)', marginTop: 4 }}>{t.subject ?? '(no subject)'} · v{t.version}</div>
                </div>
              ))}
              {!loading && templates.length === 0 && <p style={{ color: 'var(--color-text-muted)', fontSize: 12 }}>No templates.</p>}
            </>
          )}

          {/* ── AI DRAFT ── */}
          {channel === 'ai' && (
            <>
              <div style={S.card}>
                <div style={S.label}>AI-Drafted Message (Bedrock)</div>
                <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 8, marginBottom: 8 }}>
                  <div>
                    <span style={S.label}>Channel</span>
                    <select value={aiChannel} onChange={e => setAIChannel(e.target.value)} style={{ ...S.input, cursor: 'pointer' }}>
                      {['email', 'sms', 'fax', 'voice', 'print_mail'].map(c => <option key={c} value={c}>{c}</option>)}
                    </select>
                  </div>
                  <div>
                    <span style={S.label}>Tone</span>
                    <select value={aiTone} onChange={e => setAITone(e.target.value)} style={{ ...S.input, cursor: 'pointer' }}>
                      {['professional', 'formal', 'concise', 'urgent'].map(t => <option key={t} value={t}>{t}</option>)}
                    </select>
                  </div>
                </div>
                <div style={S.fg}><span style={S.label}>Context / Instructions</span><textarea value={aiContext} onChange={e => setAIContext(e.target.value)} rows={4} placeholder="Describe what you need — include recipient, purpose, and any key details" style={S.textarea} /></div>
                <button onClick={aiDraftHandle} disabled={loading || !aiContext} style={{ ...S.primaryBtn, opacity: loading ? 0.6 : 1 }}>
                  <Cpu size={12} /> {loading ? 'Drafting…' : 'Generate Draft'}
                </button>
              </div>
              {aiDraft && (
                <div style={{ ...S.card, borderLeft: '3px solid #A855F7' }}>
                  <div style={S.label}>Generated Draft</div>
                  {aiDraft.subject && <div style={{ marginBottom: 8 }}><span style={S.label}>Subject</span><p style={{ color: '#c4b5fd', fontSize: 12, margin: 0 }}>{aiDraft.subject}</p></div>}
                  <span style={S.label}>Body</span>
                  <pre style={{ fontSize: 12, color: 'var(--color-text-primary)', whiteSpace: 'pre-wrap', background: 'var(--color-bg-input)', padding: 10, borderRadius: 4, marginTop: 4 }}>{aiDraft.body}</pre>
                </div>
              )}
            </>
          )}

          {/* ── BAA ── */}
          {channel === 'baa' && (
            <>
              <div style={S.card}>
                <div style={S.label}>Create BAA Template</div>
                <div style={S.fg}><input value={baaName} onChange={e => setBAAName(e.target.value)} placeholder="Template name" style={S.input} /></div>
                <div style={S.fg}><textarea value={baaBody} onChange={e => setBAABody(e.target.value)} rows={6} placeholder="BAA HTML body (use {{variable}} for substitution)" style={S.textarea} /></div>
                <button onClick={baaHandle} style={S.primaryBtn}><Shield size={12} /> Create BAA Template</button>
              </div>
              <div style={S.label}>BAA Templates</div>
              {baaTemplates.map(t => (
                <div key={t.id} style={S.card}>
                  <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                    <span style={{ fontSize: 12, color: 'var(--color-text-primary)', fontWeight: 600 }}>{t.template_name}</span>
                    <div style={{ display: 'flex', gap: 6 }}>
                      <span style={S.badge('var(--color-text-muted)')}>{t.version_tag}</span>
                      {t.is_current && <span style={S.badge('var(--color-status-active)')}>CURRENT</span>}
                    </div>
                  </div>
                  <div style={{ fontSize: 11, color: 'var(--color-text-muted)', marginTop: 4 }}>Effective: {t.effective_date ?? '—'}</div>
                </div>
              ))}
              {!loading && baaTemplates.length === 0 && <p style={{ color: 'var(--color-text-muted)', fontSize: 12 }}>No BAA templates.</p>}
            </>
          )}

          {/* ── WISCONSIN ── */}
          {channel === 'wisconsin' && (
            <>
              <div style={S.card}>
                <div style={S.label}>Create Wisconsin Statutory Document</div>
                <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 8, marginBottom: 8 }}>
                  <div><span style={S.label}>Doc Type</span><input value={wiDocType} onChange={e => setWIDocType(e.target.value)} placeholder="e.g. retention_notice" style={S.input} /></div>
                  <div><span style={S.label}>Display Name</span><input value={wiDisplayName} onChange={e => setWIDisplayName(e.target.value)} style={S.input} /></div>
                  <div style={{ gridColumn: '1/-1' }}><span style={S.label}>WI Statute Reference</span><input value={wiStatute} onChange={e => setWIStatute(e.target.value)} placeholder="e.g. Wis. Stat. § 146.82" style={S.input} /></div>
                </div>
                <div style={S.fg}><span style={S.label}>Document HTML Body</span><textarea value={wiBody} onChange={e => setWIBody(e.target.value)} rows={6} style={S.textarea} /></div>
                <button onClick={wiHandle} style={S.primaryBtn}><MapPin size={12} /> Create WI Document</button>
              </div>
              <div style={S.label}>Wisconsin Document Templates</div>
              {wiTemplates.map(t => (
                <div key={t.id} style={S.card}>
                  <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                    <span style={{ fontSize: 12, color: 'var(--color-text-primary)', fontWeight: 600 }}>{t.display_name}</span>
                    <div style={{ display: 'flex', gap: 6 }}>
                      <span style={S.badge('#F97316')}>{t.doc_type}</span>
                      {t.is_current && <span style={S.badge('var(--color-status-active)')}>CURRENT</span>}
                    </div>
                  </div>
                  {t.wi_statute_reference && <div style={{ fontSize: 11, color: '#F97316', marginTop: 4 }}>{t.wi_statute_reference}</div>}
                  <div style={{ fontSize: 11, color: 'var(--color-text-muted)', marginTop: 2 }}>{t.version_tag} · Effective: {t.effective_date ?? '—'}</div>
                </div>
              ))}
              {!loading && wiTemplates.length === 0 && <p style={{ color: 'var(--color-text-muted)', fontSize: 12 }}>No Wisconsin document templates.</p>}
            </>
          )}

        </div>
      </main>
    </div>
  );
}
