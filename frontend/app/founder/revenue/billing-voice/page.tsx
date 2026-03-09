'use client';

import React, { useCallback, useEffect, useMemo, useState } from 'react';
import {
  getFounderBillingVoiceConfig,
  getFounderBillingVoiceSummary,
  listFounderBillingVoiceCallbacks,
  listFounderBillingVoiceEscalations,
  listFounderBillingVoiceVoicemails,
  renderFounderBillingVoicePrompts,
  takeoverFounderBillingVoiceEscalation,
  updateFounderBillingVoiceConfig,
  type FounderBillingVoiceConfigApi,
} from '@/services/api';

type SummaryPayload = {
  active_billing_calls: number;
  awaiting_human_followup: number;
  unresolved_voice_sessions: number;
  top_billing_phone_actions: Array<{ action: string; count: number }>;
};

type EscalationItem = {
  id: string;
  session_id: string | null;
  tenant_id: string | null;
  caller_phone_number: string | null;
  statement_id: string | null;
  account_id: string | null;
  verification_state: string | null;
  ai_intent: string | null;
  ai_summary: string | null;
  escalation_reason: string;
  recommended_next_action: string | null;
  status: string;
  created_at: string | null;
};

type EscalationsPayload = { items: EscalationItem[] };

type VoiceConfig = FounderBillingVoiceConfigApi;

type VoicemailItem = {
  id: string;
  caller_phone_number: string | null;
  received_at: string | null;
  tenant_id: string | null;
  statement_id: string | null;
  account_id: string | null;
  state: string;
  urgency: string;
  risk_level: string;
  risk_score: number;
  transcript_preview: string;
  intent_code: string | null;
};

type CallbackItem = {
  id: string;
  voicemail_id: string | null;
  tenant_id: string | null;
  callback_phone: string | null;
  callback_state: string;
  sla_due_at: string | null;
  priority: string;
  reason: string | null;
  created_at: string | null;
  updated_at: string | null;
};

function cardTone(reason: string): { border: string; bg: string; text: string } {
  const r = (reason || '').toLowerCase();
  if (r.includes('legal') || r.includes('fraud') || r.includes('identity')) {
    return { border: 'rgba(229,57,53,0.45)', bg: 'rgba(229,57,53,0.10)', text: 'var(--color-brand-red)' };
  }
  if (r.includes('dispute') || r.includes('policy') || r.includes('lookup')) {
    return { border: 'rgba(255,152,0,0.45)', bg: 'rgba(255,152,0,0.10)', text: '#FF4D00' };
  }
  return { border: 'rgba(76,175,80,0.35)', bg: 'rgba(76,175,80,0.08)', text: 'var(--color-status-active)' };
}

export default function FounderBillingVoicePage() {
  const [summary, setSummary] = useState<SummaryPayload | null>(null);
  const [escalations, setEscalations] = useState<EscalationItem[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string>('');
  const [takeoverId, setTakeoverId] = useState<string>('');
  const [voiceConfig, setVoiceConfig] = useState<VoiceConfig | null>(null);
  const [savingConfig, setSavingConfig] = useState(false);
  const [renderingPrompts, setRenderingPrompts] = useState(false);
  const [voicemails, setVoicemails] = useState<VoicemailItem[]>([]);
  const [callbacks, setCallbacks] = useState<CallbackItem[]>([]);

  const promptKeys = [
    ['menu_text', 'Main greeting/menu'],
    ['statement_text', 'Statement ID prompt'],
    ['phone_text', 'Phone capture prompt'],
    ['invalid_text', 'Invalid input prompt'],
    ['sent_sms_text', 'SMS sent prompt'],
    ['transfer_text', 'Transfer prompt'],
    ['goodbye_text', 'Goodbye prompt'],
  ] as const;

  const audioKeys = [
    ['menu', 'Menu audio URL'],
    ['statement', 'Statement prompt audio URL'],
    ['phone', 'Phone prompt audio URL'],
    ['invalid', 'Invalid prompt audio URL'],
    ['sent_sms', 'Sent SMS prompt audio URL'],
    ['transfer', 'Transfer prompt audio URL'],
    ['goodbye', 'Goodbye prompt audio URL'],
  ] as const;

  const load = useCallback(async () => {
    setLoading(true);
    setError('');
    try {
      const [summaryJson, escalationsJson, configJson, voicemailJson, callbackJson] = await Promise.all([
        getFounderBillingVoiceSummary() as Promise<SummaryPayload>,
        listFounderBillingVoiceEscalations('awaiting_human', 50) as Promise<EscalationsPayload>,
        getFounderBillingVoiceConfig(),
        listFounderBillingVoiceVoicemails(50),
        listFounderBillingVoiceCallbacks(50),
      ]);

      setSummary(summaryJson);
      setEscalations(escalationsJson.items || []);
      setVoiceConfig((configJson?.config || null) as VoiceConfig | null);
      setVoicemails((voicemailJson?.items || []) as VoicemailItem[]);
      setCallbacks((callbackJson?.items || []) as CallbackItem[]);
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : 'Failed to load billing voice command data');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    load();
    const id = window.setInterval(load, 10000);
    return () => window.clearInterval(id);
  }, [load]);

  const highPriorityCount = useMemo(
    () => escalations.filter((i) => /legal|fraud|identity/i.test(i.escalation_reason || '')).length,
    [escalations],
  );

  async function takeover(escalationId: string) {
    setTakeoverId(escalationId);
    setError('');
    try {
      await takeoverFounderBillingVoiceEscalation(escalationId, { channel: 'softphone' });
      await load();
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : 'Takeover failed');
    } finally {
      setTakeoverId('');
    }
  }

  async function saveVoiceConfig() {
    if (!voiceConfig) return;
    setSavingConfig(true);
    setError('');
    try {
      const payload = await updateFounderBillingVoiceConfig(voiceConfig);
      setVoiceConfig(payload?.config || voiceConfig);
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : 'Failed to save voice config');
    } finally {
      setSavingConfig(false);
    }
  }

  async function renderPromptAudio() {
    if (!voiceConfig) return;
    setRenderingPrompts(true);
    setError('');
    try {
      const payload = await renderFounderBillingVoicePrompts({ preferred_engine: voiceConfig.tts_primary_engine || 'xtts' });
      setVoiceConfig(payload?.config || voiceConfig);
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : 'Failed to render prompt audio');
    } finally {
      setRenderingPrompts(false);
    }
  }

  function setPrompt(key: string, value: string) {
    setVoiceConfig((prev) => {
      if (!prev) return prev;
      return { ...prev, prompts: { ...(prev.prompts || {}), [key]: value } };
    });
  }

  function setAudioUrl(key: string, value: string) {
    setVoiceConfig((prev) => {
      if (!prev) return prev;
      return { ...prev, audio_urls: { ...(prev.audio_urls || {}), [key]: value } };
    });
  }

  return (
    <div className="min-h-screen bg-black text-zinc-100 px-4 md:px-8 py-6 space-y-6">
      <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-2">
        <div>
          <h1 className="text-2xl font-bold">Central Billing Voice Command</h1>
          <p className="text-xs text-zinc-500">WHAT HAPPENED · WHY IT MATTERS · DO THIS NEXT</p>
        </div>
        <button
          onClick={load}
          className="px-3 py-2 text-xs font-semibold border border-border-strong chamfer-4 hover:bg-[rgba(255,255,255,0.06)]"
          disabled={loading}
        >
          {loading ? 'Refreshing…' : 'Refresh'}
        </button>
      </div>

      {error && (
        <div className="p-3 text-sm border chamfer-4" style={{ borderColor: 'rgba(229,57,53,0.45)', backgroundColor: 'rgba(229,57,53,0.10)', color: 'var(--color-brand-red)' }}>
          {error}
        </div>
      )}

      <div className="grid grid-cols-1 md:grid-cols-4 gap-3">
        <div className="p-4 border border-border-subtle bg-[rgba(255,255,255,0.02)] chamfer-4">
          <div className="text-xs text-zinc-500">Active Calls</div>
          <div className="text-2xl font-bold">{summary?.active_billing_calls ?? '—'}</div>
        </div>
        <div className="p-4 border border-border-subtle bg-[rgba(255,255,255,0.02)] chamfer-4">
          <div className="text-xs text-zinc-500">Awaiting Human</div>
          <div className="text-2xl font-bold text-[#FF4D00]">{summary?.awaiting_human_followup ?? '—'}</div>
        </div>
        <div className="p-4 border border-border-subtle bg-[rgba(255,255,255,0.02)] chamfer-4">
          <div className="text-xs text-zinc-500">Unresolved Sessions</div>
          <div className="text-2xl font-bold">{summary?.unresolved_voice_sessions ?? '—'}</div>
        </div>
        <div className="p-4 border border-border-subtle bg-[rgba(255,255,255,0.02)] chamfer-4">
          <div className="text-xs text-zinc-500">High-Risk Escalations</div>
          <div className="text-2xl font-bold text-red-400">{highPriorityCount}</div>
        </div>
      </div>

      <div className="p-4 border border-border-subtle bg-[rgba(255,255,255,0.02)] chamfer-4">
        <div className="text-xs uppercase tracking-wider text-zinc-500 mb-3">Top 3 Billing Phone Actions</div>
        <div className="flex flex-wrap gap-2">
          {(summary?.top_billing_phone_actions || []).map((a) => (
            <span key={a.action} className="text-xs px-2 py-1  border border-border-subtle bg-[rgba(255,255,255,0.03)]">
              {a.action} · {a.count}
            </span>
          ))}
          {(!summary?.top_billing_phone_actions || summary.top_billing_phone_actions.length === 0) && (
            <span className="text-xs text-zinc-500">No action data yet.</span>
          )}
        </div>
      </div>

      <div className="p-4 border border-border-subtle bg-[rgba(255,255,255,0.02)] chamfer-4 space-y-4">
        <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-2">
          <div>
            <div className="text-xs uppercase tracking-wider text-zinc-500">AI Phone Script + Voice Control</div>
            <div className="text-xs text-zinc-400">Type exactly what the phone says, and choose human voice audio or TTS.</div>
          </div>
          <button
            onClick={saveVoiceConfig}
            disabled={!voiceConfig || savingConfig}
            className="px-3 py-2 text-xs font-bold bg-[#FF4D00] text-black chamfer-4 disabled:opacity-50"
          >
            {savingConfig ? 'Saving…' : 'Save Voice Config'}
          </button>
        </div>

        {voiceConfig && (
          <>
            <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
              <label className="text-xs text-zinc-400">
                Voice Mode
                <select
                  className="mt-1 w-full bg-[rgba(255,255,255,0.04)] border border-border-subtle  px-2 py-2 text-sm"
                  value={voiceConfig.voice_mode || 'human_audio'}
                  onChange={(e) => setVoiceConfig({ ...voiceConfig, voice_mode: e.target.value as VoiceConfig['voice_mode'] })}
                >
                  <option value="human_audio">Human Audio (recommended)</option>
                  <option value="tts">Text-to-Speech</option>
                </select>
              </label>
              <label className="text-xs text-zinc-400">
                TTS Voice
                <input
                  className="mt-1 w-full bg-[rgba(255,255,255,0.04)] border border-border-subtle  px-2 py-2 text-sm"
                  value={voiceConfig.tts_voice || 'female'}
                  onChange={(e) => setVoiceConfig({ ...voiceConfig, tts_voice: e.target.value })}
                />
              </label>
              <label className="text-xs text-zinc-400">
                TTS Language
                <input
                  className="mt-1 w-full bg-[rgba(255,255,255,0.04)] border border-border-subtle  px-2 py-2 text-sm"
                  value={voiceConfig.tts_language || 'en-US'}
                  onChange={(e) => setVoiceConfig({ ...voiceConfig, tts_language: e.target.value })}
                />
              </label>
              <label className="text-xs text-zinc-400">
                Primary TTS Engine
                <select
                  className="mt-1 w-full bg-[rgba(255,255,255,0.04)] border border-border-subtle  px-2 py-2 text-sm"
                  value={voiceConfig.tts_primary_engine || 'xtts'}
                  onChange={(e) => setVoiceConfig({ ...voiceConfig, tts_primary_engine: e.target.value })}
                >
                  <option value="xtts">XTTS (human-sounding)</option>
                  <option value="piper">Piper</option>
                </select>
              </label>
              <label className="text-xs text-zinc-400">
                Fallback TTS Engine
                <select
                  className="mt-1 w-full bg-[rgba(255,255,255,0.04)] border border-border-subtle  px-2 py-2 text-sm"
                  value={voiceConfig.tts_fallback_engine || 'piper'}
                  onChange={(e) => setVoiceConfig({ ...voiceConfig, tts_fallback_engine: e.target.value })}
                >
                  <option value="piper">Piper</option>
                  <option value="xtts">XTTS</option>
                </select>
              </label>
              <label className="text-xs text-zinc-400">
                STT Engine
                <input
                  className="mt-1 w-full bg-[rgba(255,255,255,0.04)] border border-border-subtle  px-2 py-2 text-sm"
                  value={voiceConfig.stt_engine || 'faster_whisper'}
                  onChange={(e) => setVoiceConfig({ ...voiceConfig, stt_engine: e.target.value })}
                />
              </label>
              <label className="text-xs text-zinc-400">
                STT Model
                <input
                  className="mt-1 w-full bg-[rgba(255,255,255,0.04)] border border-border-subtle  px-2 py-2 text-sm"
                  value={voiceConfig.stt_model_size || 'small'}
                  onChange={(e) => setVoiceConfig({ ...voiceConfig, stt_model_size: e.target.value })}
                />
              </label>
              <label className="text-xs text-zinc-400">
                Telephony Engine
                <select
                  className="mt-1 w-full bg-[rgba(255,255,255,0.04)] border border-border-subtle  px-2 py-2 text-sm"
                  value={voiceConfig.telephony_engine || 'telnyx'}
                  onChange={(e) => setVoiceConfig({ ...voiceConfig, telephony_engine: e.target.value })}
                >
                  <option value="telnyx">Telnyx</option>
                  <option value="asterisk">Asterisk bridge</option>
                  <option value="freeswitch">FreeSWITCH bridge</option>
                </select>
              </label>
              <label className="text-xs text-zinc-400 flex items-center gap-2 mt-5">
                <input
                  type="checkbox"
                  checked={Boolean(voiceConfig.emergency_forwarding_enabled)}
                  onChange={(e) => setVoiceConfig({ ...voiceConfig, emergency_forwarding_enabled: e.target.checked })}
                />
                Emergency forward to work cell on policy trigger
              </label>
            </div>

            <div className="flex items-center justify-end">
              <button
                onClick={renderPromptAudio}
                disabled={!voiceConfig || renderingPrompts}
                className="px-3 py-2 text-xs font-bold border border-border-strong chamfer-4 disabled:opacity-50"
              >
                {renderingPrompts ? 'Rendering voice pack…' : 'Render Prompt Audio (XTTS/Piper)'}
              </button>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
              {promptKeys.map(([key, label]) => (
                <label key={key} className="text-xs text-zinc-400">
                  {label}
                  <textarea
                    className="mt-1 w-full min-h-[74px] bg-[rgba(255,255,255,0.04)] border border-border-subtle  px-2 py-2 text-sm"
                    value={voiceConfig.prompts?.[key] || ''}
                    onChange={(e) => setPrompt(key, e.target.value)}
                  />
                </label>
              ))}
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
              {audioKeys.map(([key, label]) => (
                <label key={key} className="text-xs text-zinc-400">
                  {label}
                  <input
                    className="mt-1 w-full bg-[rgba(255,255,255,0.04)] border border-border-subtle  px-2 py-2 text-sm"
                    placeholder="https://.../prompt.wav"
                    value={voiceConfig.audio_urls?.[key] || ''}
                    onChange={(e) => setAudioUrl(key, e.target.value)}
                  />
                </label>
              ))}
            </div>
          </>
        )}
      </div>

      <div className="space-y-3">
        <div className="text-xs uppercase tracking-wider text-zinc-500">Calls Awaiting Founder Takeover</div>
        {escalations.length === 0 && (
          <div className="p-4 border border-border-subtle bg-[rgba(255,255,255,0.02)] chamfer-4 text-sm text-zinc-500">
            No pending escalations. AI is holding the line. ☕
          </div>
        )}

        {escalations.map((e) => {
          const tone = cardTone(e.escalation_reason || '');
          return (
            <div key={e.id} className="p-4 border chamfer-4" style={{ borderColor: tone.border, backgroundColor: tone.bg }}>
              <div className="flex flex-col md:flex-row md:items-start md:justify-between gap-3">
                <div className="space-y-1">
                  <div className="text-sm font-semibold" style={{ color: tone.text }}>
                    {e.escalation_reason || 'escalation'}
                  </div>
                  <div className="text-xs text-zinc-400">
                    Caller: {e.caller_phone_number || 'unknown'} · Statement: {e.statement_id || 'unknown'} · Account: {e.account_id || 'unknown'}
                  </div>
                  <div className="text-xs text-zinc-400">
                    Verification: {e.verification_state || 'unknown'} · Intent: {e.ai_intent || 'unknown'}
                  </div>
                  {e.ai_summary && <div className="text-sm text-zinc-100">{e.ai_summary}</div>}
                  {e.recommended_next_action && (
                    <div className="text-xs text-zinc-500">Do this next: {e.recommended_next_action}</div>
                  )}
                </div>
                <button
                  onClick={() => takeover(e.id)}
                  disabled={takeoverId === e.id}
                  className="px-3 py-2 text-xs font-bold bg-[#FF4D00] text-black chamfer-4 disabled:opacity-50"
                >
                  {takeoverId === e.id ? 'Connecting…' : 'Accept Call'}
                </button>
              </div>
            </div>
          );
        })}
      </div>

      <div className="space-y-3">
        <div className="text-xs uppercase tracking-wider text-zinc-500">Visual Voicemail Board</div>
        {voicemails.length === 0 && (
          <div className="p-4 border border-border-subtle bg-[rgba(255,255,255,0.02)] chamfer-4 text-sm text-zinc-500">
            No voicemail cards yet.
          </div>
        )}
        {voicemails.map((v) => {
          const high = /high/i.test(v.risk_level || '');
          return (
            <div
              key={v.id}
              className="p-4 border chamfer-4"
              style={{
                borderColor: high ? 'rgba(229,57,53,0.45)' : 'rgba(255,152,0,0.40)',
                backgroundColor: high ? 'rgba(229,57,53,0.08)' : 'rgba(255,152,0,0.07)',
              }}
            >
              <div className="text-xs text-zinc-400 mb-1">
                {v.state} · Risk {v.risk_level} ({v.risk_score}) · {v.urgency}
              </div>
              <div className="text-sm font-semibold">{v.caller_phone_number || 'Unknown caller'}</div>
              <div className="text-xs text-zinc-400">Statement: {v.statement_id || '—'} · Account: {v.account_id || '—'}</div>
              <div className="text-xs text-zinc-400">Intent: {v.intent_code || 'unknown'} · Received: {v.received_at || '—'}</div>
              {v.transcript_preview && <div className="text-sm mt-2">{v.transcript_preview}</div>}
            </div>
          );
        })}
      </div>

      <div className="space-y-3">
        <div className="text-xs uppercase tracking-wider text-zinc-500">Callback Task Lane</div>
        {callbacks.length === 0 && (
          <div className="p-4 border border-border-subtle bg-[rgba(255,255,255,0.02)] chamfer-4 text-sm text-zinc-500">
            No callback tasks yet.
          </div>
        )}
        {callbacks.map((c) => (
          <div key={c.id} className="p-4 border border-border-subtle bg-[rgba(255,255,255,0.02)] chamfer-4">
            <div className="text-xs text-zinc-400">{c.callback_state} · {c.priority}</div>
            <div className="text-sm font-semibold">{c.callback_phone || 'No callback phone'}</div>
            <div className="text-xs text-zinc-400">Due: {c.sla_due_at || '—'} · Reason: {c.reason || '—'}</div>
          </div>
        ))}
      </div>
    </div>
  );
}
