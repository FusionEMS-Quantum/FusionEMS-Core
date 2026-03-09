'use client';
import { useToast } from '@/components/ui/ProductPolish';
import { ModuleDashboardShell } from '@/components/shells/PageShells';

import { getWSClient, RealtimeEvent } from '@/services/websocket';
import {
  getPortalHemsChecklistTemplate,
  getPortalHemsSafetyTimeline,
  postPortalHemsMissionAction,
  setPortalHemsAircraftReadiness,
  submitPortalHemsMissionAcceptance,
  submitPortalHemsWeatherBrief,
} from '@/services/api';
import { useState, useEffect, useCallback } from 'react';

// ─── Types ────────────────────────────────────────────────────────────────────

type ReadinessState = 'ready' | 'limited' | 'no_go' | 'maintenance_hold';
type TurbulenceLevel = 'none' | 'light' | 'moderate' | 'severe';
type GoNoGo = 'go' | 'no_go';

interface ChecklistTemplate {
  items?: string[];
  risk_factors?: string[];
}

interface SafetyEvent {
  event_type: string;
  timestamp: string;
  details?: Record<string, unknown>;
}

// ─── Constants ────────────────────────────────────────────────────────────────

const READINESS_STATES: ReadinessState[] = ['ready', 'limited', 'no_go', 'maintenance_hold'];

const READINESS_STYLE: Record<ReadinessState, { label: string; color: string; bg: string }> = {
  ready:            { label: 'READY',            color: 'var(--q-green)', bg: 'rgba(76,175,80,0.12)' },
  limited:          { label: 'LIMITED',          color: 'var(--q-yellow)', bg: 'rgba(255,152,0,0.12)' },
  no_go:            { label: 'NO-GO',            color: 'var(--q-red)', bg: 'rgba(229,57,53,0.12)' },
  maintenance_hold: { label: 'MAINTENANCE HOLD', color: 'var(--color-text-muted)', bg: 'rgba(158,158,158,0.12)' },
};

const CHECKLIST_KEYS = [
  'wx_reviewed',
  'minima_met',
  'aircraft_preflight',
  'fuel_sufficient',
  'crew_rest',
  'crew_briefed',
  'comms_check',
  'lz_info_received',
  'medical_crew_ready',
  'no_safety_concerns',
] as const;

const CHECKLIST_LABELS: Record<typeof CHECKLIST_KEYS[number], string> = {
  wx_reviewed:        'Weather reviewed',
  minima_met:         'Minima met',
  aircraft_preflight: 'Aircraft preflight complete',
  fuel_sufficient:    'Fuel sufficient',
  crew_rest:          'Crew rest requirements met',
  crew_briefed:       'Crew briefed',
  comms_check:        'Comms check complete',
  lz_info_received:   'LZ info received',
  medical_crew_ready: 'Medical crew ready',
  no_safety_concerns: 'No safety concerns',
};

const RISK_FACTOR_KEYS = [
  'night_ops',
  'mountainous_terrain',
  'marginal_wx',
  'unfamiliar_lz',
  'single_pilot',
  'critical_patient',
  'long_transport',
  'comms_degraded',
] as const;

const RISK_FACTOR_LABELS: Record<typeof RISK_FACTOR_KEYS[number], string> = {
  night_ops:          'Night operations',
  mountainous_terrain:'Mountainous terrain',
  marginal_wx:        'Marginal weather',
  unfamiliar_lz:      'Unfamiliar LZ',
  single_pilot:       'Single pilot',
  critical_patient:   'Critical patient',
  long_transport:     'Long transport',
  comms_degraded:     'Comms degraded',
};

const RISK_WEIGHTS: Record<typeof RISK_FACTOR_KEYS[number], number> = {
  night_ops:          10,
  mountainous_terrain:8,
  marginal_wx:        12,
  unfamiliar_lz:      8,
  single_pilot:       10,
  critical_patient:   5,
  long_transport:     5,
  comms_degraded:     8,
};

// ─── Helpers ──────────────────────────────────────────────────────────────────

function ReadinessBadge({ state }: { state: ReadinessState }) {
  const s = READINESS_STYLE[state] ?? READINESS_STYLE.no_go;
  return (
    <span
      className="px-2 py-0.5 text-micro font-label uppercase tracking-wider chamfer-4"
      style={{ color: s.color, background: s.bg, border: `1px solid ${s.color}33` }}
    >
      {s.label}
    </span>
  );
}

function riskColor(score: number): string {
  if (score < 20) return 'var(--color-status-active)';
  if (score < 45) return 'var(--color-status-warning)';
  return 'var(--color-brand-red)';
}

function fmtTs(ts: string): string {
  try { return new Date(ts).toLocaleString(); } catch { return ts; }
}

// ─── Page ─────────────────────────────────────────────────────────────────────

export default function HemsPage() {
  const toast = useToast();

  // Shared IDs
  const [missionId, setMissionId] = useState('');
  const [aircraftId, setAircraftId] = useState('');

  // ── Aircraft Readiness ───
  const [readinessState, setReadinessState] = useState<ReadinessState | null>(null);
  const [newReadiness, setNewReadiness] = useState<ReadinessState>('ready');
  const [readinessReason, setReadinessReason] = useState('');
  const [readinessBusy, setReadinessBusy] = useState(false);

  // ── Mission Acceptance Checklist ───
  const [checklistItems, setChecklistItems] = useState<Record<typeof CHECKLIST_KEYS[number], boolean>>(
    Object.fromEntries(CHECKLIST_KEYS.map((k) => [k, false])) as Record<typeof CHECKLIST_KEYS[number], boolean>
  );
  const [riskFactors, setRiskFactors] = useState<Record<typeof RISK_FACTOR_KEYS[number], boolean>>(
    Object.fromEntries(RISK_FACTOR_KEYS.map((k) => [k, false])) as Record<typeof RISK_FACTOR_KEYS[number], boolean>
  );
  const [acceptanceBusy, setAcceptanceBusy] = useState(false);

  // ── Weather Brief ───
  const [wx, setWx] = useState({
    ceiling_ft: '',
    visibility_sm: '',
    wind_direction: '',
    wind_speed_kt: '',
    gusts_kt: '',
    precip: false,
    icing: false,
    turbulence: 'none' as TurbulenceLevel,
    go_no_go: 'go' as GoNoGo,
    source: '',
  });
  const [wxBusy, setWxBusy] = useState(false);

  // ── Safety Timeline ───
  const [timeline, setTimeline] = useState<SafetyEvent[]>([]);
  const [timelineBusy, setTimelineBusy] = useState(false);

  // ── Fetch Safety Timeline ───
  const fetchTimeline = useCallback(async () => {
    if (!missionId.trim()) { toast.error('Enter mission ID'); return; }
    setTimelineBusy(true);
    try {
      setTimeline(await getPortalHemsSafetyTimeline(missionId.trim()));
    } catch (e: unknown) {
      toast.error(e instanceof Error ? e.message : 'Failed to fetch timeline');
    } finally {
      setTimelineBusy(false);
    }
  }, [missionId, toast]);

  // ── Fetch checklist template on mount ───
  useEffect(() => {
    getPortalHemsChecklistTemplate()
      .then((data: ChecklistTemplate | null) => {
        if (!data) return;
      })
      .catch((e: unknown) => { console.warn('checklist-template fetch failed', e); });
  }, []);

  // ── SSE: realtime mission events ───────────────────────────────────────────
  useEffect(() => {
    if (typeof window === 'undefined') return;

    // Use global WebSocket client (100% realtime)
    const client = getWSClient();
    let removeHandler: (() => void) | undefined;

    if (client) {
      removeHandler = client.addHandler((event: RealtimeEvent) => {
        // HEMS mission events
        if (event.event_type === 'hems_mission_events.created') {
          const record = (event.payload as Record<string, unknown>)?.record as Record<string, unknown> | undefined;
          const payload = record?.data as Record<string, unknown> | undefined;
          if (payload?.mission_id === missionId) {
            toast.success(`Mission update: ${String(payload.event_type)}`);
            fetchTimeline();
          } else if (!missionId && payload?.mission_id) {
             setMissionId(String(payload.mission_id));
             toast.success(`New Mission Received: ${String(payload.mission_id)}`);
          }
        }
        
        // HEMS acceptance events
        if (event.event_type === 'hems_acceptance_records.created') {
             const acceptRecord = (event.payload as Record<string, unknown>)?.record as Record<string, unknown> | undefined;
             const acceptData = acceptRecord?.data as Record<string, unknown> | undefined;
             if (acceptData?.mission_id === missionId) {
                 toast.success('Checklist accepted by another crew member.');
             }
        }
      });
    }

    // Fallback poll if WS not connected or for safety
    const pollInterval = setInterval(() => {
      if (missionId) fetchTimeline();
    }, 15000);

    return () => {
      if (removeHandler) removeHandler();
      clearInterval(pollInterval);
    };
  }, [missionId, toast, fetchTimeline]);

  // ── Action Handlers ───

  async function performAction(endpoint: string, body: Record<string, unknown>, successMsg: string) {
      if (!missionId.trim()) { toast.error('Enter mission ID'); return; }
      try {
        await postPortalHemsMissionAction(missionId.trim(), endpoint, body);
        toast.success(successMsg);
        fetchTimeline();
      } catch (e: unknown) {
        toast.error(e instanceof Error ? e.message : 'Action failed');
      }
  }

  // ── Set Readiness ───
  async function submitReadiness() {
    if (!aircraftId.trim()) { toast.error('Enter aircraft ID'); return; }
    setReadinessBusy(true);
    try {
      await setPortalHemsAircraftReadiness(aircraftId.trim(), {
        state: newReadiness,
        reason: readinessReason,
      });
      setReadinessState(newReadiness);
      setReadinessReason('');
      toast.success('Readiness updated');
    } catch (e: unknown) {
      toast.error(e instanceof Error ? e.message : 'Failed to update readiness');
    } finally {
      setReadinessBusy(false);
    }
  }

  // ── Submit Acceptance ───
  function riskScore(): number {
    return RISK_FACTOR_KEYS.reduce((sum, k) => sum + (riskFactors[k] ? RISK_WEIGHTS[k] : 0), 0);
  }

  async function submitAcceptance() {
    if (!missionId.trim()) { toast.error('Enter mission ID'); return; }
    setAcceptanceBusy(true);
    try {
      await submitPortalHemsMissionAcceptance(missionId.trim(), {
        aircraft_id: aircraftId.trim() || undefined,
        checklist: checklistItems,
        risk_factors: riskFactors,
        risk_score: riskScore(),
      });
      toast.success('Acceptance submitted');
    } catch (e: unknown) {
      toast.error(e instanceof Error ? e.message : 'Failed to submit acceptance');
    } finally {
      setAcceptanceBusy(false);
    }
  }

  // ── Submit Weather Brief ───
  async function submitWeather() {
    if (!missionId.trim()) { toast.error('Enter mission ID'); return; }
    setWxBusy(true);
    try {
      await submitPortalHemsWeatherBrief(missionId.trim(), {
        ceiling_ft: wx.ceiling_ft ? Number(wx.ceiling_ft) : undefined,
        visibility_sm: wx.visibility_sm ? Number(wx.visibility_sm) : undefined,
        wind_direction: wx.wind_direction ? Number(wx.wind_direction) : undefined,
        wind_speed_kt: wx.wind_speed_kt ? Number(wx.wind_speed_kt) : undefined,
        gusts_kt: wx.gusts_kt ? Number(wx.gusts_kt) : undefined,
        precip: wx.precip,
        icing: wx.icing,
        turbulence: wx.turbulence,
        go_no_go: wx.go_no_go,
        source: wx.source || undefined,
      });
      toast.success('Weather brief submitted');
    } catch (e: unknown) {
      toast.error(e instanceof Error ? e.message : 'Failed to submit weather brief');
    } finally {
      setWxBusy(false);
    }
  }

  const score = riskScore();

  return (
    <ModuleDashboardShell
      title="HEMS Pilot Portal"
      subtitle="Helicopter Emergency Medical Services — Mission Acceptance &amp; Safety"
      accentColor="var(--color-system-hems)"
    >

      <div className="space-y-5">

        {/* ── Shared ID inputs ── */}
        <div className="p-4 bg-[#0A0A0B] border border-[var(--color-border-default)] chamfer-8">
          <p className="text-body font-label mb-3 text-zinc-400">Session IDs</p>
          <div className="flex flex-wrap gap-3">
            <div className="flex flex-col gap-1 flex-1 min-w-[160px]">
              <label className="text-body text-zinc-500">Aircraft ID</label>
              <input
                className="bg-black chamfer-4 border border-[var(--color-border-default)] px-2.5 py-1.5 text-body text-zinc-100 outline-none"
                placeholder="e.g. N123HM"
                value={aircraftId}
                onChange={(e) => setAircraftId(e.target.value)}
              />
            </div>
            <div className="flex flex-col gap-1 flex-1 min-w-[160px]">
              <label className="text-body text-zinc-500">Mission ID</label>
              <input
                className="bg-black chamfer-4 border border-[var(--color-border-default)] px-2.5 py-1.5 text-body text-zinc-100 outline-none"
                placeholder="e.g. MSN-0001"
                value={missionId}
                onChange={(e) => setMissionId(e.target.value)}
              />
            </div>
          </div>
        </div>

        {/* ── 1. Aircraft Readiness Panel ── */}
        <div className="p-4 bg-[#0A0A0B] border border-[var(--color-border-default)] chamfer-8">
          <div className="flex items-center justify-between mb-3">
            <p className="text-body font-label text-zinc-400">Aircraft Readiness</p>
            {readinessState && <ReadinessBadge state={readinessState} />}
          </div>
          {!readinessState && (
            <p className="text-body mb-3 text-zinc-500">
              No readiness state recorded this session.
            </p>
          )}
          <div className="flex flex-wrap gap-3 items-end">
            <div className="flex flex-col gap-1">
              <label className="text-body text-zinc-500">New State</label>
              <select
                className="bg-black chamfer-4 border border-[var(--color-border-default)] px-2.5 py-1.5 text-body text-zinc-100 outline-none"
                value={newReadiness}
                onChange={(e) => setNewReadiness(e.target.value as ReadinessState)}
              >
                {READINESS_STATES.map((s) => (
                  <option key={s} value={s}>{READINESS_STYLE[s].label}</option>
                ))}
              </select>
            </div>
            <div className="flex flex-col gap-1 flex-1 min-w-[180px]">
              <label className="text-body text-zinc-500">Reason</label>
              <input
                className="bg-black chamfer-4 border border-[var(--color-border-default)] px-2.5 py-1.5 text-body text-zinc-100 outline-none"
                placeholder="Optional reason"
                value={readinessReason}
                onChange={(e) => setReadinessReason(e.target.value)}
              />
            </div>
            <button
              onClick={submitReadiness}
              disabled={readinessBusy}
              className="px-3 py-1.5 text-body font-label chamfer-4 bg-brand-orange text-zinc-100 disabled:opacity-40 transition-opacity"
            >
              {readinessBusy ? 'Saving...' : 'Set Readiness'}
            </button>
          </div>
        </div>

        {/* ── Mission Actions ── */}
        <div className="p-4 bg-[#0A0A0B] border border-[var(--color-border-default)] chamfer-8">
            <p className="text-body font-label mb-3 text-zinc-400">Mission Controls</p>
            <div className="flex flex-wrap gap-2">
                <button
                    onClick={() => performAction('acknowledge', { decision: 'accept' }, 'Mission Accepted')}
                    className="px-4 py-2 text-body font-label chamfer-4 bg-green-600/20 text-green-400 border border-green-600/30 hover:bg-green-600/30"
                >
                    Accept Mission
                </button>
                <button
                    onClick={() => {
                        const reason = prompt('Reason for decline?');
                        if (reason) performAction('acknowledge', { decision: 'decline', decline_reason: reason }, 'Mission Declined');
                    }}
                    className="px-4 py-2 text-body font-label chamfer-4 bg-red-600/20 text-red-400 border border-red-600/30 hover:bg-red-600/30"
                >
                    Decline
                </button>
                <div className="w-4" />
                <button
                    onClick={() => performAction('wheels-up', { aircraft_id: aircraftId, crew: [] }, 'Wheels Up Recorded')}
                    className="px-4 py-2 text-body font-label chamfer-4 bg-blue-600/20 text-blue-400 border border-blue-600/30 hover:bg-blue-600/30"
                >
                    Wheels Up
                </button>
                <button
                    onClick={() => performAction('wheels-down', { destination: 'Hospital' }, 'Wheels Down Recorded')}
                    className="px-4 py-2 text-body font-label chamfer-4 bg-blue-600/20 text-blue-400 border border-blue-600/30 hover:bg-blue-600/30"
                >
                    Wheels Down
                </button>
                <div className="w-4" />
                <button
                    onClick={() => performAction('complete', { outcome: 'completed' }, 'Mission Completed')}
                    className="px-4 py-2 text-body font-label chamfer-4 bg-gray-600/20 text-gray-300 border border-gray-600/30 hover:bg-gray-600/30"
                >
                    Complete Mission
                </button>
            </div>
        </div>

        {/* ── Mission Acceptance Checklist ── */}
        <div className="p-4 bg-[#0A0A0B] border border-[var(--color-border-default)] chamfer-8">
          <p className="text-body font-label mb-3 text-zinc-400">Mission Acceptance Checklist</p>

          <div className="grid grid-cols-1 sm:grid-cols-2 gap-y-2 gap-x-6 mb-4">
            {CHECKLIST_KEYS.map((key) => (
              <label key={key} className="flex items-center gap-2 cursor-pointer">
                <input
                  type="checkbox"
                  checked={checklistItems[key]}
                  onChange={(e) =>
                    setChecklistItems((prev) => ({ ...prev, [key]: e.target.checked }))
                  }
                  className="w-3.5 h-3.5 accent-[#FF4D00] cursor-pointer"
                />
                <span className="text-body text-zinc-400">{CHECKLIST_LABELS[key]}</span>
              </label>
            ))}
          </div>

          <p className="text-body font-label mb-2 text-zinc-500">Risk Factors</p>
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-y-2 gap-x-6 mb-4">
            {RISK_FACTOR_KEYS.map((key) => (
              <label key={key} className="flex items-center gap-2 cursor-pointer">
                <input
                  type="checkbox"
                  checked={riskFactors[key]}
                  onChange={(e) =>
                    setRiskFactors((prev) => ({ ...prev, [key]: e.target.checked }))
                  }
                  className="w-3.5 h-3.5 accent-[#FF4D00] cursor-pointer"
                />
                <span className="text-body text-zinc-400">
                  {RISK_FACTOR_LABELS[key]}
                  <span className="ml-1 text-zinc-500">(+{RISK_WEIGHTS[key]})</span>
                </span>
              </label>
            ))}
          </div>

          {/* Risk Score */}
          <div className="flex items-center gap-3 mb-4">
            <span className="text-body text-zinc-500">Risk Score:</span>
            <span
              className="text-sm font-bold tabular-nums"
              style={{ color: riskColor(score) }}
            >
              {score}
            </span>
            <span
              className="text-micro px-1.5 py-0.5 chamfer-4 font-label uppercase"
              style={{
                color: riskColor(score),
                background: `${riskColor(score)}1a`,
                border: `1px solid ${riskColor(score)}33`,
              }}
            >
              {score < 20 ? 'Low' : score < 45 ? 'Moderate' : 'High'}
            </span>
          </div>

          <button
            onClick={submitAcceptance}
            disabled={acceptanceBusy}
            className="px-3 py-1.5 text-body font-label chamfer-4 bg-brand-orange text-zinc-100 disabled:opacity-40 transition-opacity"
          >
            {acceptanceBusy ? 'Submitting...' : 'Submit Acceptance'}
          </button>
        </div>

        {/* ── Weather Brief ── */}
        <div className="p-4 bg-[#0A0A0B] border border-[var(--color-border-default)] chamfer-8">
          <p className="text-body font-label mb-3 text-zinc-400">Weather Brief</p>
          <div className="grid grid-cols-2 sm:grid-cols-3 gap-3 mb-3">
            {(
              [
                { key: 'ceiling_ft',     label: 'Ceiling (ft)',        type: 'number' },
                { key: 'visibility_sm',  label: 'Visibility (sm)',     type: 'number' },
                { key: 'wind_direction', label: 'Wind Direction (deg)',type: 'number' },
                { key: 'wind_speed_kt',  label: 'Wind Speed (kt)',     type: 'number' },
                { key: 'gusts_kt',       label: 'Gusts (kt)',          type: 'number' },
                { key: 'source',         label: 'Source',              type: 'text'   },
              ] as { key: keyof typeof wx; label: string; type: string }[]
            ).map(({ key, label, type }) => (
              <div key={key} className="flex flex-col gap-1">
                <label className="text-body text-zinc-500">{label}</label>
                <input
                  type={type}
                  className="bg-black chamfer-4 border border-[var(--color-border-default)] px-2.5 py-1.5 text-body text-zinc-100 outline-none"
                  value={wx[key] as string}
                  onChange={(e) => setWx((prev) => ({ ...prev, [key]: e.target.value }))}
                />
              </div>
            ))}

            <div className="flex flex-col gap-1">
              <label className="text-body text-zinc-500">Turbulence</label>
              <select
                className="bg-black chamfer-4 border border-[var(--color-border-default)] px-2.5 py-1.5 text-body text-zinc-100 outline-none"
                value={wx.turbulence}
                onChange={(e) => setWx((prev) => ({ ...prev, turbulence: e.target.value as TurbulenceLevel }))}
              >
                <option value="none">None</option>
                <option value="light">Light</option>
                <option value="moderate">Moderate</option>
                <option value="severe">Severe</option>
              </select>
            </div>

            <div className="flex flex-col gap-1">
              <label className="text-body text-zinc-500">Go / No-Go</label>
              <select
                className="bg-black chamfer-4 border border-[var(--color-border-default)] px-2.5 py-1.5 text-body text-zinc-100 outline-none"
                value={wx.go_no_go}
                onChange={(e) => setWx((prev) => ({ ...prev, go_no_go: e.target.value as GoNoGo }))}
              >
                <option value="go">Go</option>
                <option value="no_go">No-Go</option>
              </select>
            </div>
          </div>

          <div className="flex gap-4 mb-4">
            <label className="flex items-center gap-2 cursor-pointer">
              <input
                type="checkbox"
                checked={wx.precip}
                onChange={(e) => setWx((prev) => ({ ...prev, precip: e.target.checked }))}
                className="w-3.5 h-3.5 accent-[#FF4D00] cursor-pointer"
              />
              <span className="text-body text-zinc-400">Precipitation</span>
            </label>
            <label className="flex items-center gap-2 cursor-pointer">
              <input
                type="checkbox"
                checked={wx.icing}
                onChange={(e) => setWx((prev) => ({ ...prev, icing: e.target.checked }))}
                className="w-3.5 h-3.5 accent-[#FF4D00] cursor-pointer"
              />
              <span className="text-body text-zinc-400">Icing</span>
            </label>
          </div>

          <button
            onClick={submitWeather}
            disabled={wxBusy}
            className="px-3 py-1.5 text-body font-label chamfer-4 bg-brand-orange text-zinc-100 disabled:opacity-40 transition-opacity"
          >
            {wxBusy ? 'Submitting...' : 'Submit Weather Brief'}
          </button>
        </div>

        {/* ── Safety Timeline ── */}
        <div className="p-4 bg-[#0A0A0B] border border-[var(--color-border-default)] chamfer-8">
          <div className="flex items-center justify-between mb-3">
            <p className="text-body font-label text-zinc-400">Safety Timeline</p>
            <button
              onClick={fetchTimeline}
              disabled={timelineBusy}
              className="px-3 py-1 text-body font-label chamfer-4 bg-brand-orange/15 text-brand-orange border border-brand-orange/30 disabled:opacity-40 transition-opacity"
            >
              {timelineBusy ? 'Loading...' : 'Fetch Timeline'}
            </button>
          </div>

          {timeline.length === 0 ? (
            <p className="text-body text-zinc-500">
              No events loaded. Enter a mission ID and click Fetch Timeline.
            </p>
          ) : (
            <div className="relative pl-4">
              <div className="absolute left-1 top-0 bottom-0 w-px bg-[var(--color-border-default)]" />
              <div className="space-y-3">
                {timeline.map((ev, i) => (
                  <div key={i} className="relative">
                    <div className="absolute -left-[13px] top-1 w-2 h-2  bg-brand-orange" />
                    <p className="text-micro mb-0.5 text-zinc-500">{fmtTs(ev.timestamp)}</p>
                    <p className="text-body font-label text-zinc-100">{ev.event_type}</p>
                    {ev.details && Object.keys(ev.details).length > 0 && (
                      <p className="text-micro mt-0.5 text-zinc-500">{JSON.stringify(ev.details)}</p>
                    )}
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>

      </div>
    </ModuleDashboardShell>
  );
}
