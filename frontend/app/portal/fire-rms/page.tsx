'use client';

import React, { useEffect, useState, useCallback } from 'react';
import { ModuleDashboardShell } from '@/components/shells/PageShells';
import {
  AIExplanationCard,
  MetricCard,
  QuantumTableSkeleton,
  QuantumEmptyState,
  SimpleModeSummary,
  StatusChip,
} from '@/components/ui';
import { TabBar, TabPanel } from '@/components/ui/InteractionPatterns';
import type { StatusVariant } from '@/lib/design-system/tokens';
import {
  listFirePreplans,
  createFirePreplan,
  listFireHydrants,
  createFireHydrant,
} from '@/services/api';

// ── Types ────────────────────────────────────────────────────────────────────

interface FirePreplan {
  id: string;
  name: string;
  address: string;
  occupancy_type: string | null;
  stories: number | null;
  sprinkler_system: boolean;
  standpipe: boolean;
  fire_alarm_system: boolean;
  construction_type: string | null;
  last_reviewed_at: string | null;
  notes: string | null;
  hazards: Record<string, unknown> | null;
}

interface FireHydrant {
  id: string;
  hydrant_number: string;
  latitude: number;
  longitude: number;
  in_service: boolean;
  flow_rate_gpm: number | null;
  static_pressure_psi: number | null;
  hydrant_type: string | null;
  color_code: string | null;
  last_tested_at: string | null;
  notes: string | null;
}

interface Inspection {
  id: string;
  preplan_id: string | null;
  status: string;
  scheduled_date: string | null;
  completed_date: string | null;
  notes: string | null;
  deficiencies: unknown[] | null;
}

const TABS = [
  { id: 'preplans', label: 'Pre-Incident Plans' },
  { id: 'hydrants', label: 'Hydrant Management' },
  { id: 'inspections', label: 'Inspections' },
  { id: 'arson', label: 'Investigation Files' },
] as const;

const CONSTRUCTION_TYPES = ['Type I', 'Type II', 'Type III', 'Type IV', 'Type V'];
const OCCUPANCY_TYPES = [
  'Assembly', 'Business', 'Educational', 'Factory/Industrial', 'Hazardous',
  'Institutional', 'Mercantile', 'Residential', 'Storage', 'Utility/Miscellaneous',
];
const HYDRANT_COLORS: Record<string, { label: string; bg: string; border: string; text: string }> = {
  RED:    { label: 'Class AA  (<500 GPM)',    bg: 'bg-red-900/30',    border: 'border-red-500/50',    text: 'text-red-400'    },
  ORANGE: { label: 'Class A   (500-999 GPM)', bg: 'bg-[rgba(255,77,0,0.3)]', border: 'border-orange-500/50', text: 'text-[#FF7A33]' },
  GREEN:  { label: 'Class B   (1000-1499 GPM)',bg: 'bg-green-900/30', border: 'border-green-500/50',  text: 'text-green-400'  },
  BLUE:   { label: 'Class C   (≥1500 GPM)',   bg: 'bg-blue-900/30',   border: 'border-blue-500/50',   text: 'text-blue-400'   },
};
const INSPECTION_STATUS_VARIANT_MAP: Record<string, StatusVariant> = {
  SCHEDULED: 'warning',
  IN_PROGRESS: 'info',
  PASSED: 'active',
  FAILED: 'critical',
  CORRECTIVE_ACTION: 'review',
  CLOSED: 'neutral',
};

// ── Pre-Plans Tab ─────────────────────────────────────────────────────────────

function PreplansTab() {
  const [plans, setPlans] = useState<FirePreplan[]>([]);
  const [loading, setLoading] = useState(true);
  const [selected, setSelected] = useState<FirePreplan | null>(null);
  const [showForm, setShowForm] = useState(false);
  const [filter, setFilter] = useState('');
  const [form, setForm] = useState({
    name: '', address: '', occupancy_type: '', stories: '',
    construction_type: '', sprinkler_system: false, standpipe: false,
    fire_alarm_system: false, notes: '',
  });
  const [submitting, setSubmitting] = useState(false);

  const load = useCallback(async () => {
    try {
      const data = await listFirePreplans();
      setPlans(data as FirePreplan[]);
    } catch {
      setPlans([]);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { load(); }, [load]);

  const handleCreate = async () => {
    setSubmitting(true);
    try {
      await createFirePreplan({
        ...form,
        stories: form.stories ? parseInt(form.stories) : null,
      });
      setShowForm(false);
      setForm({ name:'',address:'',occupancy_type:'',stories:'',construction_type:'',sprinkler_system:false,standpipe:false,fire_alarm_system:false,notes:'' });
      await load();
    } catch (err) {
      console.error('Create preplan failed', err);
    } finally {
      setSubmitting(false);
    }
  };

  const filtered = plans.filter(p =>
    !filter ||
    p.name.toLowerCase().includes(filter.toLowerCase()) ||
    p.address.toLowerCase().includes(filter.toLowerCase())
  );

  if (loading) return <QuantumTableSkeleton rows={6} />;

  return (
    <div className="space-y-4">
      {/* Controls */}
      <div className="flex items-center justify-between gap-3">
        <input
          value={filter}
          onChange={e => setFilter(e.target.value)}
          placeholder="Search by name or address…"
          className="flex-1 max-w-xs bg-[#0A0A0B] border border-border-subtle chamfer-4 px-3 py-2 text-sm text-zinc-100 placeholder:text-zinc-500 focus:outline-none focus:border-brand-orange/60"
        />
        <button
          onClick={() => setShowForm(true)}
          className="quantum-btn-primary text-sm px-4 py-2"
        >
          + New Pre-Plan
        </button>
      </div>

      {/* AI Insight Banner */}
      <div className="bg-brand-orange/5 border border-brand-orange/20 chamfer-8 p-3 flex items-start gap-3">
        <div className="w-6 h-6  bg-brand-orange/20 flex items-center justify-center flex-shrink-0 mt-0.5">
          <svg width="12" height="12" viewBox="0 0 24 24" fill="currentColor" className="text-brand-orange">
            <path d="M12 2L2 7l10 5 10-5-10-5zM2 17l10 5 10-5M2 12l10 5 10-5"/>
          </svg>
        </div>
        <div className="text-xs text-zinc-400">
          <span className="text-brand-orange font-semibold">AI Analysis:</span> {plans.length} pre-plans on file.{' '}
          {plans.filter(p => !p.last_reviewed_at).length > 0 && (
            <span className="text-[#FF7A33]">
              {plans.filter(p => !p.last_reviewed_at).length} plans have never been reviewed — recommend scheduling inspections.
            </span>
          )}
          {plans.filter(p => p.sprinkler_system).length} / {plans.length} structures have active sprinkler systems.
        </div>
      </div>

      {/* Grid */}
      {filtered.length === 0 ? (
        <QuantumEmptyState
          title="No pre-incident plans"
          description="Create structure pre-plans to give crews critical tactical information before arrival."
          icon="building"
        />
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-3">
          {filtered.map(plan => (
            <div
              key={plan.id}
              onClick={() => setSelected(plan)}
              className="bg-[#0A0A0B] border border-border-subtle chamfer-8 p-4 cursor-pointer hover:border-brand-orange/40 hover:bg-brand-orange/[0.02] transition-all group"
            >
              <div className="flex items-start justify-between mb-2">
                <div>
                  <div className="text-sm font-semibold text-zinc-100 group-hover:text-brand-orange transition-colors">
                    {plan.name}
                  </div>
                  <div className="text-micro text-zinc-500 mt-0.5">{plan.address}</div>
                </div>
                <div className="flex flex-col items-end gap-1">
                  {plan.sprinkler_system && (
                    <span className="text-micro px-1.5 py-0.5 bg-blue-900/20 border border-blue-500/30 text-blue-400">SPKLR</span>
                  )}
                  {plan.fire_alarm_system && (
                    <span className="text-micro px-1.5 py-0.5 bg-green-900/20 border border-green-500/30 text-green-400">ALARM</span>
                  )}
                </div>
              </div>
              <div className="grid grid-cols-2 gap-1 mt-3">
                <div className="text-micro text-zinc-500">
                  Type: <span className="text-zinc-400">{plan.occupancy_type || '—'}</span>
                </div>
                <div className="text-micro text-zinc-500">
                  Stories: <span className="text-zinc-400">{plan.stories ?? '—'}</span>
                </div>
                <div className="text-micro text-zinc-500">
                  Construction: <span className="text-zinc-400">{plan.construction_type || '—'}</span>
                </div>
                <div className="text-micro text-zinc-500">
                  Reviewed:{' '}
                  <span className={plan.last_reviewed_at ? 'text-green-400' : 'text-[#FF7A33]'}>
                    {plan.last_reviewed_at
                      ? new Date(plan.last_reviewed_at).toLocaleDateString()
                      : 'Never'}
                  </span>
                </div>
              </div>
              {plan.notes && (
                <div className="mt-2 text-micro text-zinc-500 line-clamp-2">{plan.notes}</div>
              )}
            </div>
          ))}
        </div>
      )}

      {/* Create Form Modal */}
      {showForm && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 p-4">
          <div className="bg-black border border-brand-orange/30 chamfer-16 p-6 w-full max-w-xl max-h-[90vh] overflow-y-auto">
            <div className="flex items-center justify-between mb-5">
              <h2 className="text-base font-bold text-zinc-100">New Pre-Incident Plan</h2>
              <button onClick={() => setShowForm(false)} className="text-zinc-500 hover:text-zinc-100 transition-colors">✕</button>
            </div>
            <div className="space-y-3">
              <div>
                <label className="block text-micro text-zinc-500 mb-1">STRUCTURE NAME *</label>
                <input
                  value={form.name} onChange={e => setForm(f => ({ ...f, name: e.target.value }))}
                  className="w-full bg-[#0A0A0B] border border-border-subtle chamfer-4 px-3 py-2 text-sm text-zinc-100 focus:outline-none focus:border-brand-orange/60"
                  placeholder="e.g., Riverside Industrial Complex"
                />
              </div>
              <div>
                <label className="block text-micro text-zinc-500 mb-1">ADDRESS *</label>
                <input
                  value={form.address} onChange={e => setForm(f => ({ ...f, address: e.target.value }))}
                  className="w-full bg-[#0A0A0B] border border-border-subtle chamfer-4 px-3 py-2 text-sm text-zinc-100 focus:outline-none focus:border-brand-orange/60"
                  placeholder="Street address"
                />
              </div>
              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block text-micro text-zinc-500 mb-1">OCCUPANCY TYPE</label>
                  <select
                    value={form.occupancy_type} onChange={e => setForm(f => ({ ...f, occupancy_type: e.target.value }))}
                    className="w-full bg-[#0A0A0B] border border-border-subtle chamfer-4 px-3 py-2 text-sm text-zinc-100 focus:outline-none focus:border-brand-orange/60"
                  >
                    <option value="">Select…</option>
                    {OCCUPANCY_TYPES.map(t => <option key={t} value={t}>{t}</option>)}
                  </select>
                </div>
                <div>
                  <label className="block text-micro text-zinc-500 mb-1">CONSTRUCTION TYPE</label>
                  <select
                    value={form.construction_type} onChange={e => setForm(f => ({ ...f, construction_type: e.target.value }))}
                    className="w-full bg-[#0A0A0B] border border-border-subtle chamfer-4 px-3 py-2 text-sm text-zinc-100 focus:outline-none focus:border-brand-orange/60"
                  >
                    <option value="">Select…</option>
                    {CONSTRUCTION_TYPES.map(t => <option key={t} value={t}>{t}</option>)}
                  </select>
                </div>
              </div>
              <div>
                <label className="block text-micro text-zinc-500 mb-1">STORIES</label>
                <input
                  type="number" min="1" value={form.stories}
                  onChange={e => setForm(f => ({ ...f, stories: e.target.value }))}
                  className="w-full bg-[#0A0A0B] border border-border-subtle chamfer-4 px-3 py-2 text-sm text-zinc-100 focus:outline-none focus:border-brand-orange/60"
                />
              </div>
              <div className="border border-border-subtle chamfer-4 p-3 space-y-2">
                <div className="text-micro text-zinc-500 uppercase tracking-wider mb-2">Fire Protection Systems</div>
                {[
                  ['sprinkler_system', 'Sprinkler System Installed'],
                  ['standpipe', 'Standpipe System Present'],
                  ['fire_alarm_system', 'Fire Alarm System Active'],
                ].map(([key, label]) => (
                  <label key={key} className="flex items-center gap-3 cursor-pointer">
                    <div
                      onClick={() => setForm(f => ({ ...f, [key]: !f[key as keyof typeof f] }))}
                      className={`w-4 h-4 border-2 flex items-center justify-center transition-colors ${form[key as keyof typeof form] ? 'bg-brand-orange border-brand-orange' : 'border-border-subtle hover:border-brand-orange/50'}`}
                    >
                      {form[key as keyof typeof form] && (
                        <svg width="10" height="10" viewBox="0 0 12 12" fill="none">
                          <path d="M2 6l3 3 5-5" stroke="white" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/>
                        </svg>
                      )}
                    </div>
                    <span className="text-sm text-zinc-400">{label}</span>
                  </label>
                ))}
              </div>
              <div>
                <label className="block text-micro text-zinc-500 mb-1">TACTICAL NOTES</label>
                <textarea
                  value={form.notes} onChange={e => setForm(f => ({ ...f, notes: e.target.value }))}
                  rows={3}
                  className="w-full bg-[#0A0A0B] border border-border-subtle chamfer-4 px-3 py-2 text-sm text-zinc-100 focus:outline-none focus:border-brand-orange/60 resize-none"
                  placeholder="Access notes, hazards, key box locations, staging areas…"
                />
              </div>
              <div className="flex gap-3 pt-2">
                <button onClick={() => setShowForm(false)} className="flex-1 quantum-btn-sm py-2">Cancel</button>
                <button
                  onClick={handleCreate}
                  disabled={submitting || !form.name || !form.address}
                  className="flex-1 quantum-btn-primary py-2 text-sm disabled:opacity-50"
                >
                  {submitting ? 'Creating…' : 'Create Pre-Plan'}
                </button>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Detail Modal */}
      {selected && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 p-4">
          <div className="bg-black border border-border-subtle chamfer-16 p-6 w-full max-w-2xl max-h-[90vh] overflow-y-auto">
            <div className="flex items-start justify-between mb-4">
              <div>
                <h2 className="text-base font-bold text-zinc-100">{selected.name}</h2>
                <div className="text-sm text-zinc-500">{selected.address}</div>
              </div>
              <button onClick={() => setSelected(null)} className="text-zinc-500 hover:text-zinc-100 transition-colors ml-4 flex-shrink-0">✕</button>
            </div>
            <div className="grid grid-cols-2 gap-4 mb-4">
              {[
                ['Occupancy Type', selected.occupancy_type || '—'],
                ['Construction', selected.construction_type || '—'],
                ['Stories', selected.stories?.toString() || '—'],
                ['Last Reviewed', selected.last_reviewed_at ? new Date(selected.last_reviewed_at).toLocaleDateString() : 'Never'],
              ].map(([k, v]) => (
                <div key={k} className="bg-[#0A0A0B] border border-border-subtle chamfer-4 p-3">
                  <div className="text-micro text-zinc-500 uppercase tracking-wider">{k}</div>
                  <div className="text-sm font-semibold text-zinc-100 mt-1">{v}</div>
                </div>
              ))}
            </div>
            <div className="grid grid-cols-3 gap-3 mb-4">
              {[
                ['Sprinkler', selected.sprinkler_system],
                ['Standpipe', selected.standpipe],
                ['Fire Alarm', selected.fire_alarm_system],
              ].map(([label, active]) => (
                <div key={String(label)} className={`border chamfer-4 p-3 text-center ${active ? 'bg-green-900/20 border-green-500/30' : 'bg-[#0A0A0B] border-border-subtle'}`}>
                  <div className={`text-sm font-semibold ${active ? 'text-green-400' : 'text-zinc-500'}`}>
                    {active ? '✓' : '✗'} {label}
                  </div>
                </div>
              ))}
            </div>
            {selected.notes && (
              <div className="bg-[#0A0A0B] border border-border-subtle chamfer-4 p-3">
                <div className="text-micro text-zinc-500 uppercase tracking-wider mb-1">Tactical Notes</div>
                <div className="text-sm text-zinc-400 whitespace-pre-wrap">{selected.notes}</div>
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
}

// ── Hydrant Management Tab ───────────────────────────────────────────────────

function HydrantsTab() {
  const [hydrants, setHydrants] = useState<FireHydrant[]>([]);
  const [loading, setLoading] = useState(true);
  const [showForm, setShowForm] = useState(false);
  const [filter, setFilter] = useState<string>('ALL');
  const [form, setForm] = useState({
    hydrant_number: '', latitude: '', longitude: '',
    flow_rate_gpm: '', static_pressure_psi: '',
    hydrant_type: 'DRY_BARREL', color_code: 'GREEN',
    in_service: true, notes: '',
  });
  const [submitting, setSubmitting] = useState(false);

  const load = useCallback(async () => {
    try {
      const data = await listFireHydrants();
      setHydrants(data as FireHydrant[]);
    } catch {
      setHydrants([]);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { load(); }, [load]);

  const handleCreate = async () => {
    setSubmitting(true);
    try {
      await createFireHydrant({
        ...form,
        latitude: parseFloat(form.latitude),
        longitude: parseFloat(form.longitude),
        flow_rate_gpm: form.flow_rate_gpm ? parseInt(form.flow_rate_gpm) : null,
        static_pressure_psi: form.static_pressure_psi ? parseInt(form.static_pressure_psi) : null,
      });
      setShowForm(false);
      setForm({ hydrant_number:'', latitude:'', longitude:'', flow_rate_gpm:'', static_pressure_psi:'', hydrant_type:'DRY_BARREL', color_code:'GREEN', in_service:true, notes:'' });
      await load();
    } catch (err) {
      console.error('Create hydrant failed', err);
    } finally {
      setSubmitting(false);
    }
  };

  const filtered = filter === 'ALL' ? hydrants :
    filter === 'OOS' ? hydrants.filter(h => !h.in_service) :
    hydrants.filter(h => h.color_code === filter && h.in_service);

  const outOfService = hydrants.filter(h => !h.in_service).length;
  const needingTest = hydrants.filter(h => {
    if (!h.last_tested_at) return true;
    const d = new Date(h.last_tested_at);
    const ageMonths = (Date.now() - d.getTime()) / (30 * 24 * 3600 * 1000);
    return ageMonths > 12;
  }).length;

  if (loading) return <QuantumTableSkeleton rows={6} />;

  return (
    <div className="space-y-4">
      {/* Stats Row */}
      <div className="grid grid-cols-4 gap-3">
        <div className="bg-[#0A0A0B] border border-border-subtle chamfer-8 p-3 text-center">
          <div className="text-2xl font-black text-zinc-100">{hydrants.length}</div>
          <div className="text-micro text-zinc-500 uppercase tracking-wider">Total Hydrants</div>
        </div>
        <div className={`bg-[#0A0A0B] border chamfer-8 p-3 text-center ${outOfService > 0 ? 'border-red-500/30' : 'border-border-subtle'}`}>
          <div className={`text-2xl font-black ${outOfService > 0 ? 'text-red-400' : 'text-green-400'}`}>{outOfService}</div>
          <div className="text-micro text-zinc-500 uppercase tracking-wider">Out of Service</div>
        </div>
        <div className={`bg-[#0A0A0B] border chamfer-8 p-3 text-center ${needingTest > 0 ? 'border-orange-500/30' : 'border-border-subtle'}`}>
          <div className={`text-2xl font-black ${needingTest > 0 ? 'text-[#FF7A33]' : 'text-green-400'}`}>{needingTest}</div>
          <div className="text-micro text-zinc-500 uppercase tracking-wider">Test Overdue</div>
        </div>
        <div className="bg-[#0A0A0B] border border-border-subtle chamfer-8 p-3 text-center">
          <div className="text-2xl font-black text-green-400">{hydrants.length - outOfService}</div>
          <div className="text-micro text-zinc-500 uppercase tracking-wider">Operational</div>
        </div>
      </div>

      {/* Filter + Add */}
      <div className="flex items-center justify-between gap-3 flex-wrap">
        <div className="flex items-center gap-2">
          {['ALL', 'RED', 'ORANGE', 'GREEN', 'BLUE', 'OOS'].map(f => (
            <button
              key={f}
              onClick={() => setFilter(f)}
              className={`px-3 py-1 text-micro font-semibold uppercase transition-all chamfer-4 border ${
                filter === f
                  ? 'bg-brand-orange border-brand-orange text-white'
                  : f === 'OOS'
                    ? 'border-red-500/30 text-red-400 hover:border-red-500/60'
                    : HYDRANT_COLORS[f]
                      ? `${HYDRANT_COLORS[f].border} ${HYDRANT_COLORS[f].text} ${HYDRANT_COLORS[f].bg}`
                      : 'border-border-subtle text-zinc-500 hover:border-brand-orange/30'
              }`}
            >
              {f === 'OOS' ? 'Out of Service' : f}
            </button>
          ))}
        </div>
        <button onClick={() => setShowForm(true)} className="quantum-btn-primary text-sm px-4 py-2">
          + Register Hydrant
        </button>
      </div>

      {/* ISO Color Code Legend */}
      <div className="bg-[#0A0A0B] border border-border-subtle chamfer-8 p-3">
        <div className="text-micro text-zinc-500 uppercase tracking-wider mb-2">ISO Color Classification</div>
        <div className="grid grid-cols-2 md:grid-cols-4 gap-2">
          {Object.entries(HYDRANT_COLORS).map(([color, { label, bg, border, text }]) => (
            <div key={color} className={`${bg} border ${border} chamfer-4 p-2 flex items-center gap-2`}>
              <div className={`w-3 h-3  ${
                color === 'RED' ? 'bg-red-500' : color === 'ORANGE' ? 'bg-[#FF4D00]' : color === 'GREEN' ? 'bg-green-500' : 'bg-blue-500'
              }`} />
              <span className={`text-micro ${text}`}>{label}</span>
            </div>
          ))}
        </div>
      </div>

      {/* Table */}
      {filtered.length === 0 ? (
        <QuantumEmptyState
          title="No hydrants found"
          description="Register hydrants to manage flow data, testing schedules, and operational status."
          icon="droplet"
        />
      ) : (
        <div className="bg-[#0A0A0B] border border-border-subtle chamfer-8 overflow-hidden">
          <table className="w-full text-left">
            <thead>
              <tr className="border-b border-border-subtle">
                {['Hydrant #', 'GPS', 'Status', 'Class', 'Flow (GPM)', 'Pressure (PSI)', 'Last Test', 'Type'].map(h => (
                  <th key={h} className="px-4 py-3 text-micro uppercase tracking-widest text-zinc-500">{h}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {filtered.map(h => {
                const color = HYDRANT_COLORS[h.color_code || ''];
                return (
                  <tr key={h.id} className="border-b border-border-subtle hover:bg-zinc-950/[0.02]">
                    <td className="px-4 py-3 text-sm font-bold text-zinc-100">{h.hydrant_number}</td>
                    <td className="px-4 py-3 text-micro text-zinc-500 font-mono">
                      {h.latitude.toFixed(4)}, {h.longitude.toFixed(4)}
                    </td>
                    <td className="px-4 py-3">
                      <span className={`text-micro font-semibold ${h.in_service ? 'text-green-400' : 'text-red-400'}`}>
                        {h.in_service ? '● IN SERVICE' : '● OUT OF SERVICE'}
                      </span>
                    </td>
                    <td className="px-4 py-3">
                      {color ? (
                        <span className={`text-micro px-2 py-0.5 border ${color.bg} ${color.border} ${color.text}`}>
                          {h.color_code}
                        </span>
                      ) : <span className="text-zinc-500">—</span>}
                    </td>
                    <td className="px-4 py-3 text-sm text-zinc-400">{h.flow_rate_gpm ?? '—'}</td>
                    <td className="px-4 py-3 text-sm text-zinc-400">{h.static_pressure_psi ?? '—'}</td>
                    <td className="px-4 py-3 text-sm text-zinc-400">
                      {h.last_tested_at ? new Date(h.last_tested_at).toLocaleDateString() : (
                        <span className="text-[#FF7A33]">Never</span>
                      )}
                    </td>
                    <td className="px-4 py-3 text-sm text-zinc-400">{h.hydrant_type || '—'}</td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      )}

      {/* Create Form Modal */}
      {showForm && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 p-4">
          <div className="bg-black border border-brand-orange/30 chamfer-16 p-6 w-full max-w-md max-h-[90vh] overflow-y-auto">
            <div className="flex items-center justify-between mb-5">
              <h2 className="text-base font-bold text-zinc-100">Register Hydrant</h2>
              <button onClick={() => setShowForm(false)} className="text-zinc-500 hover:text-zinc-100">✕</button>
            </div>
            <div className="space-y-3">
              <div>
                <label className="block text-micro text-zinc-500 mb-1">HYDRANT NUMBER *</label>
                <input value={form.hydrant_number} onChange={e => setForm(f => ({ ...f, hydrant_number: e.target.value }))}
                  className="w-full bg-[#0A0A0B] border border-border-subtle chamfer-4 px-3 py-2 text-sm text-zinc-100 focus:outline-none focus:border-brand-orange/60"
                  placeholder="e.g., H-1042" />
              </div>
              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block text-micro text-zinc-500 mb-1">LATITUDE *</label>
                  <input type="number" step="0.0001" value={form.latitude} onChange={e => setForm(f => ({ ...f, latitude: e.target.value }))}
                    className="w-full bg-[#0A0A0B] border border-border-subtle chamfer-4 px-3 py-2 text-sm text-zinc-100 focus:outline-none focus:border-brand-orange/60" />
                </div>
                <div>
                  <label className="block text-micro text-zinc-500 mb-1">LONGITUDE *</label>
                  <input type="number" step="0.0001" value={form.longitude} onChange={e => setForm(f => ({ ...f, longitude: e.target.value }))}
                    className="w-full bg-[#0A0A0B] border border-border-subtle chamfer-4 px-3 py-2 text-sm text-zinc-100 focus:outline-none focus:border-brand-orange/60" />
                </div>
              </div>
              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block text-micro text-zinc-500 mb-1">FLOW RATE (GPM)</label>
                  <input type="number" value={form.flow_rate_gpm} onChange={e => setForm(f => ({ ...f, flow_rate_gpm: e.target.value }))}
                    className="w-full bg-[#0A0A0B] border border-border-subtle chamfer-4 px-3 py-2 text-sm text-zinc-100 focus:outline-none focus:border-brand-orange/60" />
                </div>
                <div>
                  <label className="block text-micro text-zinc-500 mb-1">SUPPLY PRESSURE (PSI)</label>
                  <input type="number" value={form.static_pressure_psi} onChange={e => setForm(f => ({ ...f, static_pressure_psi: e.target.value }))}
                    className="w-full bg-[#0A0A0B] border border-border-subtle chamfer-4 px-3 py-2 text-sm text-zinc-100 focus:outline-none focus:border-brand-orange/60" />
                </div>
              </div>
              <div>
                <label className="block text-micro text-zinc-500 mb-1">ISO COLOR CLASS</label>
                <select value={form.color_code} onChange={e => setForm(f => ({ ...f, color_code: e.target.value }))}
                  className="w-full bg-[#0A0A0B] border border-border-subtle chamfer-4 px-3 py-2 text-sm text-zinc-100 focus:outline-none focus:border-brand-orange/60">
                  {Object.entries(HYDRANT_COLORS).map(([c, { label }]) => <option key={c} value={c}>{c} — {label}</option>)}
                </select>
              </div>
              <label className="flex items-center gap-3 cursor-pointer">
                <div onClick={() => setForm(f => ({ ...f, in_service: !f.in_service }))}
                  className={`w-4 h-4 border-2 flex items-center justify-center transition-colors ${form.in_service ? 'bg-green-500 border-green-500' : 'border-border-subtle'}`}>
                  {form.in_service && <svg width="10" height="10" viewBox="0 0 12 12" fill="none"><path d="M2 6l3 3 5-5" stroke="white" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/></svg>}
                </div>
                <span className="text-sm text-zinc-400">Currently In Service</span>
              </label>
              <div className="flex gap-3 pt-2">
                <button onClick={() => setShowForm(false)} className="flex-1 quantum-btn-sm py-2">Cancel</button>
                <button onClick={handleCreate} disabled={submitting || !form.hydrant_number || !form.latitude || !form.longitude}
                  className="flex-1 quantum-btn-primary py-2 text-sm disabled:opacity-50">
                  {submitting ? 'Saving…' : 'Register'}
                </button>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

// ── Inspections Tab ───────────────────────────────────────────────────────────

function InspectionsTab() {
  const [inspections] = useState<Inspection[]>([]);
  const [loading] = useState(false);

  const statusCounts = {
    scheduled: inspections.filter(i => i.status === 'SCHEDULED').length,
    in_progress: inspections.filter(i => i.status === 'IN_PROGRESS').length,
    failed: inspections.filter(i => i.status === 'FAILED').length,
    corrective: inspections.filter(i => i.status === 'CORRECTIVE_ACTION').length,
  };

  if (loading) return <QuantumTableSkeleton rows={5} />;

  return (
    <div className="space-y-4">
      <div className="grid grid-cols-4 gap-3">
        {[
          { label: 'Scheduled', value: statusCounts.scheduled, color: 'text-yellow-400', border: 'border-yellow-500/20' },
          { label: 'In Progress', value: statusCounts.in_progress, color: 'text-blue-400', border: 'border-blue-500/20' },
          { label: 'Corrective Action', value: statusCounts.corrective, color: 'text-[#FF7A33]', border: 'border-orange-500/20' },
          { label: 'Failed', value: statusCounts.failed, color: 'text-red-400', border: 'border-red-500/20' },
        ].map(({ label, value, color, border }) => (
          <div key={label} className={`bg-[#0A0A0B] border ${border || 'border-border-subtle'} chamfer-8 p-3 text-center`}>
            <div className={`text-2xl font-black ${color}`}>{value}</div>
            <div className="text-micro text-zinc-500 uppercase tracking-wider">{label}</div>
          </div>
        ))}
      </div>

      {inspections.length === 0 ? (
        <QuantumEmptyState
          title="No inspections on record"
          description="Schedule building inspections by linking them to pre-incident plans. The system will auto-track violations and corrective deadlines."
          icon="clipboard-check"
        />
      ) : (
        <div className="bg-[#0A0A0B] border border-border-subtle chamfer-8 overflow-hidden">
          <table className="w-full text-left">
            <thead>
              <tr className="border-b border-border-subtle">
                {['Structure', 'Scheduled', 'Completed', 'Status', 'Deficiencies'].map(h => (
                  <th key={h} className="px-4 py-3 text-micro uppercase tracking-widest text-zinc-500">{h}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {inspections.map(i => (
                <tr key={i.id} className="border-b border-border-subtle hover:bg-zinc-950/[0.02]">
                  <td className="px-4 py-3 text-sm font-semibold text-zinc-100">{i.preplan_id || '—'}</td>
                  <td className="px-4 py-3 text-sm text-zinc-400">
                    {i.scheduled_date ? new Date(i.scheduled_date).toLocaleDateString() : '—'}
                  </td>
                  <td className="px-4 py-3 text-sm text-zinc-400">
                    {i.completed_date ? new Date(i.completed_date).toLocaleDateString() : '—'}
                  </td>
                  <td className="px-4 py-3 text-sm font-semibold">
                    <StatusChip status={INSPECTION_STATUS_VARIANT_MAP[i.status] ?? 'neutral'} size="sm">
                      {i.status.replace(/_/g, ' ')}
                    </StatusChip>
                  </td>
                  <td className="px-4 py-3 text-sm text-zinc-400">
                    {i.deficiencies ? (i.deficiencies as unknown[]).length : 0}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}

// ── Arson Investigation Tab ───────────────────────────────────────────────────

function ArsonTab() {
  return (
    <div className="space-y-4">
      <div className="bg-[rgba(255,77,0,0.1)] border border-orange-500/20 chamfer-8 p-4">
        <div className="text-sm font-semibold text-[#FF7A33] mb-1">Restricted Module</div>
        <div className="text-sm text-zinc-400">
          Arson investigation case files are restricted to designated investigators.
          Access is fully audited. All case data is end-to-end encrypted at rest and in transit.
        </div>
      </div>
      <QuantumEmptyState
        title="No active investigations"
        description="Arson investigation files will appear here once the Investigations module is provisioned for your agency. Contact your administrator to enable access."
        icon="shield"
      />
    </div>
  );
}

// ── Page ─────────────────────────────────────────────────────────────────────

export default function FireRMSPage() {
  const [activeTab, setActiveTab] = useState<string>('preplans');

  return (
    <ModuleDashboardShell
      title="Fire RMS"
      subtitle="Pre-incident planning, hydrant network, inspection tracking, and investigations"
      accentColor="var(--color-system-fire)"
      sidePanel={
        <div className="space-y-3">
          <SimpleModeSummary
            screenName="Fire RMS"
            domain="fire"
            whatThisDoes="This screen manages pre-plans, hydrants, and inspections so crews have building intelligence before arrival."
            whatIsWrong={activeTab === 'inspections' ? 'Inspection module is not yet populated with live inspection records.' : undefined}
            whatMatters="Missing pre-plan and hydrant quality data slows tactical decisions and increases on-scene risk."
            whatToClickNext={activeTab === 'preplans' ? 'Create or review high-risk structure pre-plans, then schedule inspections.' : activeTab === 'hydrants' ? 'Filter hydrants for OOS and overdue tests, then register corrections.' : 'Complete inspection data population and enforce corrective action closure.'}
            requiresReview={activeTab === 'inspections'}
          />
          <AIExplanationCard
            domain="fire"
            severity={activeTab === 'inspections' ? 'MEDIUM' : 'LOW'}
            what={activeTab === 'hydrants'
              ? 'Hydrant operations are central to suppression readiness and route planning.'
              : activeTab === 'preplans'
                ? 'Pre-plan coverage determines tactical awareness before first unit arrival.'
                : 'Inspection completeness directly impacts prevention and compliance posture.'}
            why="Operational fire data quality affects speed-to-decision, responder safety, and compliance confidence."
            next={activeTab === 'hydrants'
              ? 'Prioritize out-of-service and overdue hydrants, then update status/testing records.'
              : activeTab === 'preplans'
                ? 'Fill missing occupancy/construction metadata and schedule first review dates.'
                : 'Populate inspections with status, deficiencies, and corrective due dates.'}
            requiresReview={activeTab === 'inspections'}
          />
        </div>
      }
    >
      <div className="grid grid-cols-4 gap-3 mb-5">
        <MetricCard label="Pre-Plans" value="—" domain="fire" compact />
        <MetricCard label="Hydrants Tracked" value="—" domain="fire" compact />
        <MetricCard label="Inspections Due" value="—" domain="fire" compact />
        <MetricCard label="Compliance Rate" value="—%" domain="fire" compact />
      </div>
      <TabBar tabs={TABS} activeTab={activeTab} onTabChange={setActiveTab} />
      <TabPanel tabId="preplans" activeTab={activeTab}><PreplansTab /></TabPanel>
      <TabPanel tabId="hydrants" activeTab={activeTab}><HydrantsTab /></TabPanel>
      <TabPanel tabId="inspections" activeTab={activeTab}><InspectionsTab /></TabPanel>
      <TabPanel tabId="arson" activeTab={activeTab}><ArsonTab /></TabPanel>
    </ModuleDashboardShell>
  );
}
