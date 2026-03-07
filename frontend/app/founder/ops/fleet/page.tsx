'use client';
import { useState, useEffect, useCallback } from 'react';
import Link from 'next/link';

const API = process.env.NEXT_PUBLIC_API_URL || '';
const getToken = () => typeof window !== 'undefined' ? 'Bearer ' + (localStorage.getItem('qs_token') || '') : '';

const READINESS_COLOR = (score: number) =>
  score >= 80 ? '#4caf50' : score >= 50 ? '#ffc107' : '#ef5350';

const READINESS_LABEL = (score: number) =>
  score >= 80 ? 'READY' : score >= 50 ? 'LIMITED' : 'NO-GO';

const TELEMETRY_STATE_COLORS: Record<string, { bg: string; text: string }> = {
  UNIT_READY:           { bg: 'rgba(76,175,80,0.15)',   text: '#4caf50' },
  UNIT_WARNING:         { bg: 'rgba(255,193,7,0.15)',   text: '#ffc107' },
  UNIT_DEGRADED:        { bg: 'rgba(255,107,26,0.15)',  text: '#ff6b1a' },
  UNIT_OUT_OF_SERVICE:  { bg: 'rgba(229,57,53,0.2)',    text: '#ef5350' },
  TELEMETRY_DELAYED:    { bg: 'rgba(41,182,246,0.12)',  text: '#29b6f6' },
  TELEMETRY_OFFLINE:    { bg: 'rgba(120,130,140,0.2)',  text: '#78909c' },
  MAINTENANCE_REQUIRED: { bg: 'rgba(255,107,26,0.12)',  text: '#ff8a65' },
  SAFETY_ALERT:         { bg: 'rgba(229,57,53,0.25)',   text: '#f44336' },
};

function Panel({ children, className = '' }: { children: React.ReactNode; className?: string }) {
  return (
    <div className={`bg-[rgba(255,255,255,0.03)] border border-[rgba(255,255,255,0.08)] chamfer-8 p-4 ${className}`}>
      {children}
    </div>
  );
}

function ReadinessBar({ score }: { score: number }) {
  const color = READINESS_COLOR(score);
  return (
    <div className="flex items-center gap-2">
      <div className="flex-1 h-2 rounded-full bg-[rgba(255,255,255,0.08)] overflow-hidden">
        <div className="h-full rounded-full transition-all" style={{ width: `${score}%`, background: color }} />
      </div>
      <span className="text-body font-bold w-8 text-right" style={{ color }}>{score}</span>
    </div>
  );
}

interface FleetSummary {
  fleet_count: number;
  avg_readiness: number;
  units_ready: number;
  units_limited: number;
  units_no_go: number;
  scores: Array<{
    unit_id: string;
    readiness_score: number;
    active_alert_count: number;
    critical_alert_count: number;
    open_maintenance_count: number;
    mdt_online: boolean;
    components: { alert_score: number; maintenance_score: number; mdt_score: number; obd_score: number; credential_score: number };
  }>;
}

interface FleetAlert {
  id: string;
  data: {
    unit_id: string;
    severity: string;
    message: string;
    fault_type?: string;
    resolved: boolean;
    acknowledged: boolean;
    detected_at?: string;
  };
}

interface IngestForm {
  unit_id: string;
  coolant_temp_c: string;
  engine_rpm: string;
  battery_voltage: string;
  fuel_level_pct: string;
  speed_kmh: string;
  oil_pressure_kpa: string;
}

export default function FleetTelemetryPage() {
  const [summary, setSummary] = useState<FleetSummary | null>(null);
  const [alerts, setAlerts] = useState<FleetAlert[]>([]);
  const [loading, setLoading] = useState(true);
  const [activeTab, setActiveTab] = useState<'readiness' | 'alerts' | 'ingest'>('readiness');
  const [ingestForm, setIngestForm] = useState<IngestForm>({ unit_id: '', coolant_temp_c: '', engine_rpm: '', battery_voltage: '', fuel_level_pct: '', speed_kmh: '', oil_pressure_kpa: '' });
  const [ingestResult, setIngestResult] = useState<Record<string, unknown> | null>(null);
  const [ingesting, setIngesting] = useState(false);
  const [toast, setToast] = useState('');

  const showToast = (msg: string) => { setToast(msg); setTimeout(() => setToast(''), 3000); };

  const load = useCallback(async () => {
    try {
      const [sr, ar] = await Promise.all([
        fetch(`${API}/api/v1/fleet-intelligence/readiness/fleet`, { headers: { Authorization: getToken() } }),
        fetch(`${API}/api/v1/fleet/dashboard`, { headers: { Authorization: getToken() } }),
      ]);
      if (sr.ok) setSummary(await sr.json());
      if (ar.ok) { const j = await ar.json(); setAlerts(j.alerts ?? []); }
    } finally { setLoading(false); }
  }, []);

  useEffect(() => { load(); const iv = setInterval(load, 15000); return () => clearInterval(iv); }, [load]);

  const ackAlert = async (alertId: string, version: number) => {
    await fetch(`${API}/api/v1/fleet/alerts/${alertId}/ack`, {
      method: 'POST', headers: { Authorization: getToken(), 'Content-Type': 'application/json' },
      body: JSON.stringify({ expected_version: version }),
    });
    showToast('Alert acknowledged'); load();
  };

  const ingestTelemetry = async () => {
    if (!ingestForm.unit_id) return;
    setIngesting(true);
    try {
      const payload: Record<string, unknown> = {};
      if (ingestForm.coolant_temp_c) payload.coolant_temp_c = parseFloat(ingestForm.coolant_temp_c);
      if (ingestForm.engine_rpm) payload.engine_rpm = parseFloat(ingestForm.engine_rpm);
      if (ingestForm.battery_voltage) payload.battery_voltage = parseFloat(ingestForm.battery_voltage);
      if (ingestForm.fuel_level_pct) payload.fuel_level_pct = parseFloat(ingestForm.fuel_level_pct);
      if (ingestForm.speed_kmh) payload.speed_kmh = parseFloat(ingestForm.speed_kmh);
      if (ingestForm.oil_pressure_kpa) payload.oil_pressure_kpa = parseFloat(ingestForm.oil_pressure_kpa);

      const r = await fetch(`${API}/api/v1/ops/telemetry/ingest`, {
        method: 'POST', headers: { Authorization: getToken(), 'Content-Type': 'application/json' },
        body: JSON.stringify({ unit_id: ingestForm.unit_id, payload, source: 'OBD2' }),
      });
      const j = await r.json();
      setIngestResult(j);
      if (j.telemetry_event_id) {
        showToast(`Telemetry ingested — ${j.faults_detected ?? 0} fault(s) detected`);
        load();
      }
    } finally { setIngesting(false); }
  };

  const activeAlerts = alerts.filter(a => !(a.data?.resolved));
  const criticalAlerts = activeAlerts.filter(a => a.data?.severity === 'critical');

  return (
    <div className="p-6 space-y-6 max-w-[1600px] mx-auto">
      {toast && (
        <div className="fixed top-4 right-4 z-50 bg-green-600 text-white px-4 py-2 chamfer-8 text-sm font-medium shadow-lg">{toast}</div>
      )}

      {/* ── Header ── */}
      <div className="flex items-center justify-between">
        <div>
          <Link href="/founder/ops" className="text-body text-orange-400 hover:text-orange-300 mb-1 block">← Ops Command</Link>
          <h1 className="text-2xl font-black text-white">Fleet & Telemetry</h1>
          <p className="text-sm text-[rgba(255,255,255,0.45)] mt-1">
            Live unit readiness · OBD-II ingestion · Fault detection · Maintenance alerts
          </p>
        </div>
        <button onClick={load} className="px-3 py-1.5 bg-[rgba(255,255,255,0.06)] border border-[rgba(255,255,255,0.12)] text-body chamfer-8 hover:bg-[rgba(255,255,255,0.1)]">
          ↻ Refresh
        </button>
      </div>

      {/* ── Telemetry State Model ── */}
      <Panel>
        <div className="text-micro uppercase tracking-widest text-[rgba(255,255,255,0.4)] mb-3">Unit Health States</div>
        <div className="flex flex-wrap gap-2">
          {Object.entries(TELEMETRY_STATE_COLORS).map(([state, colors]) => (
            <span key={state} className="px-2 py-1 chamfer-4 text-micro font-bold uppercase tracking-wider"
              style={{ background: colors.bg, color: colors.text }}>
              {state.replace(/_/g, ' ')}
            </span>
          ))}
        </div>
      </Panel>

      {/* ── Summary Cards ── */}
      {summary && (
        <div className="grid grid-cols-2 md:grid-cols-5 gap-3">
          {[
            { label: 'Total Units', value: summary.fleet_count, color: 'white' },
            { label: 'Avg Readiness', value: `${summary.avg_readiness}%`, color: READINESS_COLOR(summary.avg_readiness) },
            { label: 'Ready', value: summary.units_ready, color: '#4caf50' },
            { label: 'Limited', value: summary.units_limited, color: '#ffc107' },
            { label: 'No-Go', value: summary.units_no_go, color: '#ef5350' },
          ].map(item => (
            <div key={item.label} className="chamfer-4-xl p-4 border border-[rgba(255,255,255,0.08)] bg-[rgba(255,255,255,0.03)] text-center">
              <div className="text-3xl font-black" style={{ color: item.color }}>{item.value}</div>
              <div className="text-micro uppercase tracking-widest text-[rgba(255,255,255,0.4)] mt-1">{item.label}</div>
            </div>
          ))}
        </div>
      )}

      {criticalAlerts.length > 0 && (
        <div className="p-4 chamfer-4-xl border border-red-500/40 bg-[rgba(229,57,53,0.08)]">
          <div className="text-red-400 font-bold text-sm mb-1">🚨 {criticalAlerts.length} Critical Fleet Alert(s)</div>
          <div className="text-body text-[rgba(255,255,255,0.6)]">
            Critical alerts require immediate review — affected units should not be dispatched.
          </div>
        </div>
      )}

      {/* ── Tabs ── */}
      <div className="flex gap-2">
        {(['readiness', 'alerts', 'ingest'] as const).map(tab => (
          <button key={tab} onClick={() => setActiveTab(tab)} className={`px-4 py-2 chamfer-8 text-body font-bold uppercase tracking-wider ${activeTab === tab ? 'bg-green-700 text-white' : 'bg-[rgba(255,255,255,0.06)] text-[rgba(255,255,255,0.5)]'}`}>
            {tab === 'readiness' ? 'Fleet Readiness' : tab === 'alerts' ? `Alerts (${activeAlerts.length})` : 'Telemetry Ingest'}
          </button>
        ))}
      </div>

      {/* ── Readiness Tab ── */}
      {activeTab === 'readiness' && (
        <div className="space-y-2">
          {loading && <div className="text-sm text-[rgba(255,255,255,0.4)] p-4">Loading readiness data…</div>}
          {summary?.scores.map(unit => (
            <Panel key={unit.unit_id}>
              <div className="flex items-center gap-4">
                <div className="flex-shrink-0 w-32">
                  <div className="text-micro uppercase tracking-wider text-[rgba(255,255,255,0.4)]">Unit</div>
                  <div className="text-sm font-bold text-white truncate">{unit.unit_id.slice(0, 12)}</div>
                </div>
                <div className="flex-1">
                  <div className="flex items-center justify-between mb-1">
                    <span className="text-micro uppercase tracking-wider" style={{ color: READINESS_COLOR(unit.readiness_score) }}>
                      {READINESS_LABEL(unit.readiness_score)}
                    </span>
                  </div>
                  <ReadinessBar score={unit.readiness_score} />
                </div>
                <div className="grid grid-cols-4 gap-3 flex-shrink-0">
                  {[
                    { label: 'Alerts', value: unit.active_alert_count, color: unit.critical_alert_count > 0 ? '#ef5350' : unit.active_alert_count > 0 ? '#ffc107' : '#4caf50' },
                    { label: 'Maint', value: unit.open_maintenance_count, color: unit.open_maintenance_count > 0 ? '#ff6b1a' : '#4caf50' },
                    { label: 'MDT', value: unit.mdt_online ? 'ONLINE' : 'OFFLINE', color: unit.mdt_online ? '#4caf50' : '#ef5350' },
                    { label: 'OBD', value: `${unit.components.obd_score}%`, color: READINESS_COLOR(unit.components.obd_score) },
                  ].map(item => (
                    <div key={item.label} className="text-center">
                      <div className="text-sm font-bold" style={{ color: item.color }}>{item.value}</div>
                      <div className="text-[9px] uppercase tracking-wider text-[rgba(255,255,255,0.3)]">{item.label}</div>
                    </div>
                  ))}
                </div>
              </div>
            </Panel>
          ))}
          {!loading && (!summary || summary.scores.length === 0) && (
            <div className="text-center py-10 chamfer-4-xl border border-[rgba(255,255,255,0.08)]">
              <div className="text-3xl mb-2">🚑</div>
              <div className="text-sm text-[rgba(255,255,255,0.45)]">No units in fleet. Add units via CAD → Units.</div>
            </div>
          )}
        </div>
      )}

      {/* ── Alerts Tab ── */}
      {activeTab === 'alerts' && (
        <div className="space-y-2">
          {activeAlerts.length === 0 && !loading && (
            <div className="text-center py-10 chamfer-4-xl border border-[rgba(76,175,80,0.3)] bg-[rgba(76,175,80,0.05)]">
              <div className="text-3xl mb-2">✅</div>
              <div className="text-sm text-green-400">No active fleet alerts</div>
            </div>
          )}
          {activeAlerts.map(alert => {
            const d = alert.data ?? {};
            const sevColors: Record<string, string> = { critical: '#ef5350', warning: '#ffc107', info: '#29b6f6' };
            const sevColor = sevColors[d.severity] ?? '#78909c';
            return (
              <div key={alert.id} className="chamfer-4-xl border p-4 flex items-center justify-between"
                style={{ borderColor: sevColor + '40', background: sevColor + '0a' }}>
                <div>
                  <div className="flex items-center gap-2 mb-1">
                    <span className="text-micro font-bold uppercase px-2 py-0.5 chamfer-4"
                      style={{ background: sevColor + '22', color: sevColor, border: `1px solid ${sevColor}44` }}>
                      {d.severity}
                    </span>
                    <span className="text-micro text-[rgba(255,255,255,0.4)]">Unit: {d.unit_id?.slice(0, 12)}</span>
                    {d.fault_type && <span className="text-micro text-[rgba(255,255,255,0.35)]">{d.fault_type}</span>}
                  </div>
                  <div className="text-sm text-white">{d.message}</div>
                </div>
                {!d.acknowledged && (
                  <button onClick={() => ackAlert(alert.id, 1)}
                    className="px-3 py-1.5 bg-[rgba(255,255,255,0.08)] border border-[rgba(255,255,255,0.15)] text-body font-bold text-white chamfer-8 hover:bg-[rgba(255,255,255,0.12)] ml-4">
                    ACK
                  </button>
                )}
              </div>
            );
          })}
        </div>
      )}

      {/* ── Telemetry Ingest Tab ── */}
      {activeTab === 'ingest' && (
        <Panel>
          <div className="text-micro uppercase tracking-widest text-[rgba(255,255,255,0.4)] mb-4">
            Ingest OBD-II / Telemetry Data
          </div>
          <div className="text-body text-[rgba(255,255,255,0.5)] mb-4">
            Submit vehicle telemetry readings. Fault detection runs automatically and creates fleet alerts if thresholds are exceeded.
          </div>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-3 mb-4">
            <input value={ingestForm.unit_id} onChange={e => setIngestForm(p => ({ ...p, unit_id: e.target.value }))}
              placeholder="Unit ID *"
              className="h-9 bg-[rgba(255,255,255,0.06)] border border-[rgba(255,255,255,0.12)] px-3 text-sm text-white chamfer-8 focus:outline-none focus:border-green-400 placeholder-[rgba(255,255,255,0.25)]" />
            {[
              { key: 'coolant_temp_c', label: 'Coolant Temp (°C)', warn: '>110' },
              { key: 'engine_rpm', label: 'Engine RPM', warn: '>6000' },
              { key: 'battery_voltage', label: 'Battery (V)', warn: '<11.5' },
              { key: 'fuel_level_pct', label: 'Fuel Level (%)', warn: '<10' },
              { key: 'speed_kmh', label: 'Speed (km/h)', warn: '>160' },
              { key: 'oil_pressure_kpa', label: 'Oil Pressure (kPa)', warn: '<100' },
            ].map(field => (
              <div key={field.key}>
                <input
                  value={ingestForm[field.key as keyof IngestForm]}
                  onChange={e => setIngestForm(p => ({ ...p, [field.key]: e.target.value }))}
                  placeholder={`${field.label} (${field.warn})`}
                  className="w-full h-9 bg-[rgba(255,255,255,0.06)] border border-[rgba(255,255,255,0.12)] px-3 text-sm text-white chamfer-8 focus:outline-none focus:border-green-400 placeholder-[rgba(255,255,255,0.2)]" />
              </div>
            ))}
          </div>
          <button onClick={ingestTelemetry} disabled={ingesting || !ingestForm.unit_id}
            className="px-6 py-2 bg-green-700 text-white text-sm font-bold chamfer-8 hover:bg-green-600 disabled:opacity-40 transition-colors">
            {ingesting ? 'Processing…' : '📡 Ingest Telemetry'}
          </button>

          {ingestResult && (
            <div className="mt-4 p-4 chamfer-8 bg-[rgba(255,255,255,0.04)] border border-[rgba(255,255,255,0.08)]">
              <div className="text-micro uppercase tracking-wider text-[rgba(255,255,255,0.4)] mb-2">Ingest Result</div>
              <div className="grid grid-cols-3 gap-3">
                <div>
                  <div className="text-micro text-[rgba(255,255,255,0.3)]">Event ID</div>
                  <div className="text-body text-white font-mono">{String(ingestResult.telemetry_event_id ?? '—').slice(0, 16)}</div>
                </div>
                <div>
                  <div className="text-micro text-[rgba(255,255,255,0.3)]">Faults Detected</div>
                  <div className="text-sm font-bold" style={{ color: (ingestResult.faults_detected as number) > 0 ? '#ef5350' : '#4caf50' }}>
                    {String(ingestResult.faults_detected ?? 0)}
                  </div>
                </div>
                <div>
                  <div className="text-micro text-[rgba(255,255,255,0.3)]">Alerts Created</div>
                  <div className="text-sm font-bold text-orange-400">{(ingestResult.alerts_created as string[])?.length ?? 0}</div>
                </div>
              </div>
            </div>
          )}
        </Panel>
      )}
    </div>
  );
}
