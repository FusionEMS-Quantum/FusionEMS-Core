'use client';

import React, { useEffect, useState, useCallback } from 'react';
import { ModuleDashboardShell } from '@/components/shells/PageShells';
import {
  AIExplanationCard,
  MetricCard,
  QuantumEmptyState,
  QuantumTableSkeleton,
  SeverityBadge,
  SimpleModeSummary,
  StatusChip,
} from '@/components/ui';
import type { SeverityLevel, StatusVariant } from '@/lib/design-system/tokens';
import {
  listEPCRCharts,
  createEPCRChart,
  getEPCRChart,
  updateEPCRChart,
  addEPCRVitals,
  addEPCRMedication,
  addEPCRProcedure,
  getEPCRCompleteness,
  generateEPCRAINarrative,
  submitEPCRChart,
  lockEPCRChart,
} from '@/services/api';

// ── Types ─────────────────────────────────────────────────────────────────────

type ChartStatus = 'DRAFT' | 'IN_PROGRESS' | 'PENDING_QA' | 'APPROVED' | 'LOCKED' | 'EXPORTED';

interface EPCRChart {
  id: string;
  call_id?: string;
  status: ChartStatus;
  patient_first_name?: string;
  patient_last_name?: string;
  patient_dob?: string;
  patient_gender?: string;
  chief_complaint?: string;
  incident_date?: string;
  dispatch_complaint?: string;
  unit_id?: string;
  crew_lead?: string;
  narrative?: string;
  completeness_score?: number;
  created_at: string;
  updated_at?: string;
}

interface CompletenessData {
  score: number;
  missing_fields: string[];
  critical_missing: string[];
  warnings: string[];
}

// ── Constants ─────────────────────────────────────────────────────────────────

const STATUS_CONFIG: Record<ChartStatus, {
  label: string;
  bg: string;
  text: string;
  border: string;
  variant: StatusVariant;
  severity: SeverityLevel;
}> = {
  DRAFT:       { label: 'Draft',       bg: 'bg-gray-800/40',   text: 'text-gray-400',   border: 'border-gray-600',  variant: 'neutral',  severity: 'INFORMATIONAL' },
  IN_PROGRESS: { label: 'In Progress', bg: 'bg-blue-900/40',   text: 'text-blue-300',   border: 'border-blue-500',  variant: 'info',     severity: 'LOW' },
  PENDING_QA:  { label: 'Pending QA',  bg: 'bg-yellow-900/40', text: 'text-yellow-300', border: 'border-yellow-500',variant: 'review',   severity: 'MEDIUM' },
  APPROVED:    { label: 'Approved',    bg: 'bg-green-900/40',  text: 'text-green-300',  border: 'border-green-500', variant: 'active',   severity: 'INFORMATIONAL' },
  LOCKED:      { label: 'Locked',      bg: 'bg-purple-900/40', text: 'text-purple-300', border: 'border-purple-500',variant: 'override', severity: 'LOW' },
  EXPORTED:    { label: 'Exported',    bg: 'bg-cyan-900/40',   text: 'text-cyan-300',   border: 'border-cyan-500',  variant: 'active',   severity: 'INFORMATIONAL' },
};

const VITAL_FIELDS = [
  { key: 'taken_at', label: 'Time', type: 'datetime-local' },
  { key: 'bp_systolic', label: 'SBP', type: 'number', placeholder: '120' },
  { key: 'bp_diastolic', label: 'DBP', type: 'number', placeholder: '80' },
  { key: 'heart_rate', label: 'HR', type: 'number', placeholder: '72' },
  { key: 'respirations', label: 'RR', type: 'number', placeholder: '16' },
  { key: 'spo2', label: 'SpO2 %', type: 'number', placeholder: '98' },
  { key: 'gcs_total', label: 'GCS', type: 'number', placeholder: '15' },
  { key: 'temperature_f', label: 'Temp °F', type: 'number', placeholder: '98.6' },
  { key: 'blood_glucose', label: 'BGL mg/dL', type: 'number', placeholder: '100' },
  { key: 'etco2', label: 'EtCO2', type: 'number', placeholder: '35' },
  { key: 'pain_score', label: 'Pain 0-10', type: 'number', placeholder: '0' },
];

// ── Status Badge ──────────────────────────────────────────────────────────────

function StatusBadge({ status }: { status: ChartStatus }) {
  const cfg = STATUS_CONFIG[status] || STATUS_CONFIG.DRAFT;
  return (
    <StatusChip status={cfg.variant} size="sm">{cfg.label}</StatusChip>
  );
}

// ── Completeness Ring ─────────────────────────────────────────────────────────

function CompletenessRing({ score }: { score: number }) {
  const deg = Math.round(score * 360);
  const color = score >= 0.9 ? '#22c55e' : score >= 0.7 ? '#f59e0b' : '#ef4444';
  const pct = Math.round(score * 100);

  return (
    <div className="relative w-10 h-10 flex-shrink-0">
      <svg viewBox="0 0 36 36" className="w-full h-full -rotate-90">
        <circle cx="18" cy="18" r="15" fill="none" stroke="rgba(255,255,255,0.08)" strokeWidth="3" />
        <circle
          cx="18" cy="18" r="15" fill="none" stroke={color} strokeWidth="3"
          strokeDasharray={`${(deg / 360) * 94.2} 94.2`}
          strokeLinecap="round"
        />
      </svg>
      <span className="absolute inset-0 flex items-center justify-center text-micro font-black" style={{ color }}>
        {pct}
      </span>
    </div>
  );
}

// ── New Chart Form ────────────────────────────────────────────────────────────

interface NewChartFormProps {
  onClose: () => void;
  onCreated: (_chart: EPCRChart) => void;
}

function NewChartForm({ onClose, onCreated }: NewChartFormProps) {
  const [form, setForm] = useState({
    patient_first_name: '', patient_last_name: '', patient_dob: '', patient_gender: 'Unknown',
    chief_complaint: '', dispatch_complaint: '', incident_date: new Date().toISOString().slice(0, 16),
    unit_id: '', crew_lead: '',
  });
  const [submitting, setSubmitting] = useState(false);

  const f = (k: string, v: string) => setForm(prev => ({ ...prev, [k]: v }));

  const handleSubmit = async () => {
    setSubmitting(true);
    try {
      const chart = await createEPCRChart({ ...form, status: 'DRAFT' });
      onCreated(chart);
      onClose();
    } catch (err) {
      console.error('Failed to create chart', err);
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/80" onClick={onClose}>
      <div className="bg-bg-void border border-brand-orange/40 chamfer-16 p-6 w-full max-w-2xl max-h-[90vh] overflow-y-auto" onClick={e => e.stopPropagation()}>
        <div className="flex items-center justify-between mb-5">
          <div>
            <h2 className="text-base font-black text-text-primary uppercase tracking-wider">New ePCR Chart</h2>
            <div className="text-micro text-text-muted">NEMSIS 3.5 compliant · All data encrypted at rest</div>
          </div>
          <button onClick={onClose} className="text-text-muted hover:text-text-primary">✕</button>
        </div>
        <div className="space-y-4">
          {/* Patient Demographics */}
          <div>
            <div className="text-micro font-bold text-text-muted uppercase tracking-widest mb-2">Patient Demographics</div>
            <div className="grid grid-cols-2 gap-3">
              <div>
                <label className="block text-micro text-text-muted mb-1">FIRST NAME</label>
                <input value={form.patient_first_name} onChange={e => f('patient_first_name', e.target.value)}
                  className="w-full bg-bg-panel border border-border-subtle chamfer-4 px-3 py-2 text-sm text-text-primary focus:outline-none focus:border-brand-orange/60"
                  placeholder="John" />
              </div>
              <div>
                <label className="block text-micro text-text-muted mb-1">LAST NAME</label>
                <input value={form.patient_last_name} onChange={e => f('patient_last_name', e.target.value)}
                  className="w-full bg-bg-panel border border-border-subtle chamfer-4 px-3 py-2 text-sm text-text-primary focus:outline-none focus:border-brand-orange/60"
                  placeholder="Smith" />
              </div>
              <div>
                <label className="block text-micro text-text-muted mb-1">DATE OF BIRTH</label>
                <input type="date" value={form.patient_dob} onChange={e => f('patient_dob', e.target.value)}
                  className="w-full bg-bg-panel border border-border-subtle chamfer-4 px-3 py-2 text-sm text-text-primary focus:outline-none focus:border-brand-orange/60" />
              </div>
              <div>
                <label className="block text-micro text-text-muted mb-1">SEX</label>
                <select value={form.patient_gender} onChange={e => f('patient_gender', e.target.value)}
                  className="w-full bg-bg-panel border border-border-subtle chamfer-4 px-3 py-2 text-sm text-text-primary focus:outline-none focus:border-brand-orange/60">
                  <option value="Unknown">Unknown</option>
                  <option value="Male">Male</option>
                  <option value="Female">Female</option>
                  <option value="Other">Other / Non-binary</option>
                </select>
              </div>
            </div>
          </div>
          {/* Incident Info */}
          <div>
            <div className="text-micro font-bold text-text-muted uppercase tracking-widest mb-2">Incident Info</div>
            <div className="grid grid-cols-2 gap-3">
              <div>
                <label className="block text-micro text-text-muted mb-1">DISPATCH COMPLAINT</label>
                <input value={form.dispatch_complaint} onChange={e => f('dispatch_complaint', e.target.value)}
                  className="w-full bg-bg-panel border border-border-subtle chamfer-4 px-3 py-2 text-sm text-text-primary focus:outline-none focus:border-brand-orange/60"
                  placeholder="Chest pain" />
              </div>
              <div>
                <label className="block text-micro text-text-muted mb-1">INCIDENT DATE/TIME</label>
                <input type="datetime-local" value={form.incident_date} onChange={e => f('incident_date', e.target.value)}
                  className="w-full bg-bg-panel border border-border-subtle chamfer-4 px-3 py-2 text-sm text-text-primary focus:outline-none focus:border-brand-orange/60" />
              </div>
              <div>
                <label className="block text-micro text-text-muted mb-1">UNIT ID</label>
                <input value={form.unit_id} onChange={e => f('unit_id', e.target.value)}
                  className="w-full bg-bg-panel border border-border-subtle chamfer-4 px-3 py-2 text-sm text-text-primary focus:outline-none focus:border-brand-orange/60"
                  placeholder="Medic 1" />
              </div>
              <div>
                <label className="block text-micro text-text-muted mb-1">CREW LEAD / SIGNATURE</label>
                <input value={form.crew_lead} onChange={e => f('crew_lead', e.target.value)}
                  className="w-full bg-bg-panel border border-border-subtle chamfer-4 px-3 py-2 text-sm text-text-primary focus:outline-none focus:border-brand-orange/60"
                  placeholder="J. Martinez, NRP" />
              </div>
            </div>
            <div className="mt-3">
              <label className="block text-micro text-text-muted mb-1">CHIEF COMPLAINT (PATIENT/CREW OBSERVED)</label>
              <input value={form.chief_complaint} onChange={e => f('chief_complaint', e.target.value)}
                className="w-full bg-bg-panel border border-border-subtle chamfer-4 px-3 py-2 text-sm text-text-primary focus:outline-none focus:border-brand-orange/60"
                placeholder="Substernal chest pressure, radiating to left arm, onset 30 minutes prior to call…" />
            </div>
          </div>
          <div className="flex gap-3 pt-2">
            <button onClick={onClose} className="flex-1 quantum-btn-sm py-2">Cancel</button>
            <button
              onClick={handleSubmit}
              disabled={submitting}
              className="flex-1 quantum-btn-primary py-2 text-sm font-bold disabled:opacity-50"
            >
              {submitting ? 'Creating…' : '📋 Create Chart'}
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}

// ── Vitals Panel ─────────────────────────────────────────────────────────────

interface VitalsPanelProps {
  chartId: string;
  onAdded: () => void;
}

function VitalsPanel({ chartId, onAdded }: VitalsPanelProps) {
  const [form, setForm] = useState<Record<string, string>>({
    taken_at: new Date().toISOString().slice(0, 16),
  });
  const [saving, setSaving] = useState(false);
  const [done, setDone] = useState(false);

  const handleSave = async () => {
    setSaving(true);
    try {
      const payload: Record<string, unknown> = {};
      for (const [k, v] of Object.entries(form)) {
        if (v !== '') payload[k] = k === 'taken_at' ? v : Number(v);
      }
      await addEPCRVitals(chartId, payload);
      setDone(true);
      onAdded();
    } catch (err) {
      console.error('Vitals save failed', err);
    } finally {
      setSaving(false);
    }
  };

  if (done) {
    return (
      <div className="bg-green-900/20 border border-green-500/30 chamfer-8 p-4 text-center">
        <div className="text-green-400 font-bold text-sm">✓ Vitals recorded</div>
        <button onClick={() => { setDone(false); setForm({ taken_at: new Date().toISOString().slice(0, 16) }); }}
          className="mt-2 text-micro text-text-muted hover:text-brand-orange transition-colors">
          Add another set
        </button>
      </div>
    );
  }

  return (
    <div className="bg-bg-panel border border-border-subtle chamfer-8 p-4">
      <div className="grid grid-cols-4 md:grid-cols-6 gap-2 mb-3">
        {VITAL_FIELDS.map(field => (
          <div key={field.key}>
            <label className="block text-micro text-text-muted mb-1 uppercase tracking-wider">{field.label}</label>
            <input
              type={field.type}
              value={form[field.key] ?? ''}
              onChange={e => setForm(f => ({ ...f, [field.key]: e.target.value }))}
              className="w-full bg-bg-void border border-border-subtle chamfer-4 px-2 py-1.5 text-sm text-text-primary focus:outline-none focus:border-brand-orange/60"
              placeholder={field.placeholder}
            />
          </div>
        ))}
      </div>
      <button
        onClick={handleSave}
        disabled={saving}
        className="quantum-btn-primary px-4 py-1.5 text-sm font-bold disabled:opacity-50"
      >
        {saving ? 'Saving…' : 'Record Vitals'}
      </button>
    </div>
  );
}

// ── Chart Detail Panel ────────────────────────────────────────────────────────

interface ChartDetailProps {
  chartId: string;
  onClose: () => void;
  onUpdated: () => void;
}

type DetailTab = 'overview' | 'vitals' | 'medications' | 'procedures' | 'narrative' | 'completeness';

function ChartDetail({ chartId, onClose, onUpdated }: ChartDetailProps) {
  const [chart, setChart] = useState<EPCRChart | null>(null);
  const [completeness, setCompleteness] = useState<CompletenessData | null>(null);
  const [narrative, setNarrative] = useState<string>('');
  const [generatingNarrative, setGeneratingNarrative] = useState(false);
  const [activeTab, setActiveTab] = useState<DetailTab>('overview');
  const [loading, setLoading] = useState(true);
  const [medForm, setMedForm] = useState({ medication_name: '', dose: '', route: '', time_given: '' });
  const [procForm, setProcForm] = useState({ procedure_name: '', successful: 'true', attempts: '1', time_performed: '' });
  const [saving, setSaving] = useState<string | null>(null);

  const load = useCallback(async () => {
    try {
      const [chartData, complData] = await Promise.all([
        getEPCRChart(chartId),
        getEPCRCompleteness(chartId).catch(() => null),
      ]);
      setChart(chartData);
      setNarrative(chartData.narrative || '');
      if (complData) setCompleteness(complData);
    } finally {
      setLoading(false);
    }
  }, [chartId]);

  useEffect(() => { load(); }, [load]);

  const handleGenerateNarrative = async () => {
    setGeneratingNarrative(true);
    try {
      const result = await generateEPCRAINarrative(chartId);
      setNarrative(result.narrative || result.text || '');
    } catch (err) {
      console.error('AI narrative generation failed', err);
    } finally {
      setGeneratingNarrative(false);
    }
  };

  const handleSaveNarrative = async () => {
    setSaving('narrative');
    try {
      await updateEPCRChart(chartId, { narrative });
      onUpdated();
    } catch (err) {
      console.error('Narrative save failed', err);
    } finally {
      setSaving(null);
    }
  };

  const handleAddMed = async () => {
    setSaving('med');
    try {
      await addEPCRMedication(chartId, {
        ...medForm,
        dose: medForm.dose,
      });
      setMedForm({ medication_name: '', dose: '', route: '', time_given: '' });
      await load();
    } finally {
      setSaving(null);
    }
  };

  const handleAddProc = async () => {
    setSaving('proc');
    try {
      await addEPCRProcedure(chartId, {
        ...procForm,
        successful: procForm.successful === 'true',
        attempts: parseInt(procForm.attempts),
      });
      setProcForm({ procedure_name: '', successful: 'true', attempts: '1', time_performed: '' });
      await load();
    } finally {
      setSaving(null);
    }
  };

  const handleSubmit = async () => {
    setSaving('submit');
    try {
      await submitEPCRChart(chartId);
      await load();
      onUpdated();
    } finally {
      setSaving(null);
    }
  };

  const handleLock = async () => {
    setSaving('lock');
    try {
      await lockEPCRChart(chartId);
      await load();
      onUpdated();
    } finally {
      setSaving(null);
    }
  };

  const TABS: { id: DetailTab; label: string }[] = [
    { id: 'overview', label: 'Overview' },
    { id: 'vitals', label: 'Vitals' },
    { id: 'medications', label: 'Medications' },
    { id: 'procedures', label: 'Procedures' },
    { id: 'narrative', label: 'Narrative' },
    { id: 'completeness', label: 'Completeness' },
  ];

  return (
    <div className="fixed inset-0 z-50 flex items-end sm:items-center justify-center bg-black/80" onClick={onClose}>
      <div
        className="bg-bg-void border border-border-subtle chamfer-16 w-full max-w-3xl max-h-[90vh] flex flex-col"
        onClick={e => e.stopPropagation()}
      >
        {/* Header */}
        <div className="flex-shrink-0 p-5 border-b border-border-subtle flex items-center justify-between">
          {chart && (
            <div className="flex items-center gap-3">
              {completeness && <CompletenessRing score={completeness.score} />}
              <div>
                <div className="text-base font-black text-text-primary">
                  {chart.patient_first_name || '—'} {chart.patient_last_name || '—'}
                </div>
                <div className="flex items-center gap-2 mt-0.5">
                  <StatusBadge status={chart.status} />
                  {chart.chief_complaint && (
                    <span className="text-micro text-text-muted">{chart.chief_complaint}</span>
                  )}
                </div>
              </div>
            </div>
          )}
          <div className="flex items-center gap-2">
            {chart && chart.status === 'IN_PROGRESS' && (
              <button
                onClick={handleSubmit}
                disabled={saving === 'submit'}
                className="quantum-btn-primary px-4 py-1.5 text-sm font-bold disabled:opacity-50"
              >
                {saving === 'submit' ? 'Submitting…' : 'Submit for QA →'}
              </button>
            )}
            {chart && chart.status === 'APPROVED' && (
              <button
                onClick={handleLock}
                disabled={saving === 'lock'}
                className="px-4 py-1.5 text-sm font-bold border border-purple-500/60 text-purple-300 bg-purple-900/20 hover:bg-purple-900/40 transition-colors chamfer-4 disabled:opacity-50"
              >
                {saving === 'lock' ? 'Locking…' : '🔒 Lock & Export'}
              </button>
            )}
            <button onClick={onClose} className="text-text-muted hover:text-text-primary text-lg">✕</button>
          </div>
        </div>

        {/* Tabs */}
        <div className="flex-shrink-0 flex border-b border-border-subtle overflow-x-auto">
          {TABS.map(t => (
            <button
              key={t.id}
              onClick={() => setActiveTab(t.id)}
              className={`px-4 py-2.5 text-micro font-semibold whitespace-nowrap transition-colors border-b-2 ${
                activeTab === t.id
                  ? 'border-brand-orange text-brand-orange'
                  : 'border-transparent text-text-muted hover:text-text-secondary'
              }`}
            >
              {t.label}
            </button>
          ))}
        </div>

        {/* Content */}
        <div className="flex-1 overflow-y-auto p-5">
          {loading ? (
            <QuantumTableSkeleton rows={3} />
          ) : !chart ? (
            <div className="text-center py-8 text-text-muted text-sm">Chart not found</div>
          ) : activeTab === 'overview' ? (
            <div className="space-y-4">
              <div className="grid grid-cols-2 gap-4">
                {[
                  ['DOB', chart.patient_dob ? new Date(chart.patient_dob).toLocaleDateString() : '—'],
                  ['Sex', chart.patient_gender || '—'],
                  ['Dispatch Complaint', chart.dispatch_complaint || '—'],
                  ['Incident Date', chart.incident_date ? new Date(chart.incident_date).toLocaleString() : '—'],
                  ['Unit', chart.unit_id || '—'],
                  ['Crew Lead', chart.crew_lead || '—'],
                ].map(([label, value]) => (
                  <div key={label} className="bg-bg-panel border border-border-subtle chamfer-8 px-4 py-3">
                    <div className="text-micro text-text-muted uppercase tracking-wider mb-0.5">{label}</div>
                    <div className="text-sm font-semibold text-text-primary">{value}</div>
                  </div>
                ))}
              </div>
              {chart.chief_complaint && (
                <div className="bg-bg-panel border border-border-subtle chamfer-8 px-4 py-3">
                  <div className="text-micro text-text-muted uppercase tracking-wider mb-1">Chief Complaint</div>
                  <div className="text-sm text-text-primary">{chart.chief_complaint}</div>
                </div>
              )}
            </div>
          ) : activeTab === 'vitals' ? (
            <div className="space-y-4">
              <div className="text-sm text-text-secondary mb-3">
                Record vital sign sets in chronological order. All vitals are timestamped and immutable once saved.
              </div>
              <VitalsPanel chartId={chartId} onAdded={load} />
            </div>
          ) : activeTab === 'medications' ? (
            <div className="space-y-4">
              <div className="bg-bg-panel border border-border-subtle chamfer-8 p-4 space-y-3">
                <div className="text-micro font-bold text-text-muted uppercase tracking-widest">Add Medication Administration</div>
                <div className="grid grid-cols-2 gap-3">
                  {([
                    ['medication_name', 'Medication', 'text', 'Aspirin 81mg', medForm.medication_name, (v: string) => setMedForm(f => ({ ...f, medication_name: v }))],
                    ['dose', 'Dose', 'text', '324 mg PO', medForm.dose, (v: string) => setMedForm(f => ({ ...f, dose: v }))],
                    ['route', 'Route', 'text', 'PO / IV / IM / IN', medForm.route, (v: string) => setMedForm(f => ({ ...f, route: v }))],
                    ['time_given', 'Time Given', 'datetime-local', '', medForm.time_given, (v: string) => setMedForm(f => ({ ...f, time_given: v }))],
                  ] as [string, string, string, string, string, (_v: string) => void][]).map(([_key, label, type, placeholder, value, onChange]) => (
                    <div key={label}>
                      <label className="block text-micro text-text-muted mb-1 uppercase">{label}</label>
                      <input type={type} value={value} onChange={e => onChange(e.target.value)} placeholder={placeholder}
                        className="w-full bg-bg-void border border-border-subtle chamfer-4 px-3 py-2 text-sm text-text-primary focus:outline-none focus:border-brand-orange/60" />
                    </div>
                  ))}
                </div>
                <button
                  onClick={handleAddMed}
                  disabled={saving === 'med' || !medForm.medication_name}
                  className="quantum-btn-primary px-4 py-1.5 text-sm font-bold disabled:opacity-50"
                >
                  {saving === 'med' ? 'Saving…' : '+ Add Medication'}
                </button>
              </div>
              <div className="text-micro text-text-muted text-center">Medication log populates after each entry is saved.</div>
            </div>
          ) : activeTab === 'procedures' ? (
            <div className="space-y-4">
              <div className="bg-bg-panel border border-border-subtle chamfer-8 p-4 space-y-3">
                <div className="text-micro font-bold text-text-muted uppercase tracking-widest">Add Procedure / Intervention</div>
                <div className="grid grid-cols-2 gap-3">
                  <div>
                    <label className="block text-micro text-text-muted mb-1 uppercase">PROCEDURE</label>
                    <input value={procForm.procedure_name} onChange={e => setProcForm(f => ({ ...f, procedure_name: e.target.value }))}
                      className="w-full bg-bg-void border border-border-subtle chamfer-4 px-3 py-2 text-sm text-text-primary focus:outline-none focus:border-brand-orange/60"
                      placeholder="IV Access — 18g AC" />
                  </div>
                  <div>
                    <label className="block text-micro text-text-muted mb-1 uppercase">TIME PERFORMED</label>
                    <input type="datetime-local" value={procForm.time_performed} onChange={e => setProcForm(f => ({ ...f, time_performed: e.target.value }))}
                      className="w-full bg-bg-void border border-border-subtle chamfer-4 px-3 py-2 text-sm text-text-primary focus:outline-none focus:border-brand-orange/60" />
                  </div>
                  <div>
                    <label className="block text-micro text-text-muted mb-1 uppercase">ATTEMPTS</label>
                    <input type="number" value={procForm.attempts} onChange={e => setProcForm(f => ({ ...f, attempts: e.target.value }))}
                      min={1} max={10}
                      className="w-full bg-bg-void border border-border-subtle chamfer-4 px-3 py-2 text-sm text-text-primary focus:outline-none focus:border-brand-orange/60" />
                  </div>
                  <div>
                    <label className="block text-micro text-text-muted mb-1 uppercase">SUCCESSFUL?</label>
                    <select value={procForm.successful} onChange={e => setProcForm(f => ({ ...f, successful: e.target.value }))}
                      className="w-full bg-bg-void border border-border-subtle chamfer-4 px-3 py-2 text-sm text-text-primary focus:outline-none focus:border-brand-orange/60">
                      <option value="true">Yes</option>
                      <option value="false">No</option>
                    </select>
                  </div>
                </div>
                <button
                  onClick={handleAddProc}
                  disabled={saving === 'proc' || !procForm.procedure_name}
                  className="quantum-btn-primary px-4 py-1.5 text-sm font-bold disabled:opacity-50"
                >
                  {saving === 'proc' ? 'Saving…' : '+ Add Procedure'}
                </button>
              </div>
            </div>
          ) : activeTab === 'narrative' ? (
            <div className="space-y-4">
              {/* AI Narrative Panel */}
              <div className="bg-gradient-to-br from-brand-orange/10 to-transparent border border-brand-orange/30 chamfer-8 p-4">
                <div className="flex items-center justify-between mb-2">
                  <div>
                    <div className="text-sm font-bold text-brand-orange">AI Narrative Generator</div>
                    <div className="text-micro text-text-muted">Analyzes vitals, medications, procedures, and chief complaint</div>
                  </div>
                  <button
                    onClick={handleGenerateNarrative}
                    disabled={generatingNarrative}
                    className="px-4 py-1.5 text-sm font-bold border border-brand-orange/60 text-brand-orange bg-brand-orange/10 hover:bg-brand-orange/20 chamfer-4 transition-colors disabled:opacity-50"
                  >
                    {generatingNarrative ? '⚡ Generating…' : '⚡ Generate Narrative'}
                  </button>
                </div>
                <div className="text-micro text-text-muted">
                  AI assists narrative composition only. All content must be verified and finalized by the attending clinician before submission.
                </div>
              </div>
              <div>
                <label className="block text-micro text-text-muted mb-2 uppercase tracking-wider">CALL NARRATIVE (EDITABLE)</label>
                <textarea
                  value={narrative}
                  onChange={e => setNarrative(e.target.value)}
                  rows={12}
                  className="w-full bg-bg-panel border border-border-subtle chamfer-8 px-4 py-3 text-sm text-text-primary focus:outline-none focus:border-brand-orange/60 resize-none font-mono leading-relaxed"
                  placeholder="Dispatched to 123 Main St at 14:32 for a 65-year-old male complaining of chest pain. Upon arrival, patient was found…"
                />
                <div className="flex items-center justify-between mt-2">
                  <div className="text-micro text-text-muted">{narrative.length} characters</div>
                  <button
                    onClick={handleSaveNarrative}
                    disabled={saving === 'narrative'}
                    className="quantum-btn-primary px-4 py-1.5 text-sm font-bold disabled:opacity-50"
                  >
                    {saving === 'narrative' ? 'Saving…' : 'Save Narrative'}
                  </button>
                </div>
              </div>
            </div>
          ) : activeTab === 'completeness' ? (
            <div className="space-y-4">
              {completeness ? (
                <>
                  <div className="flex items-center gap-4 bg-bg-panel border border-border-subtle chamfer-8 p-4">
                    <CompletenessRing score={completeness.score} />
                    <div>
                      <div className="text-lg font-black text-text-primary">{Math.round(completeness.score * 100)}% Complete</div>
                      <div className="text-micro text-text-muted">
                        {completeness.critical_missing.length > 0
                          ? `${completeness.critical_missing.length} critical fields missing`
                          : 'All critical fields present'}
                      </div>
                    </div>
                  </div>
                  {completeness.critical_missing.length > 0 && (
                    <div className="bg-red-900/20 border border-red-500/30 chamfer-8 p-4">
                      <div className="text-sm font-bold text-red-400 mb-2">⚠ Critical Missing Fields</div>
                      <ul className="space-y-1">
                        {completeness.critical_missing.map(f => (
                          <li key={f} className="text-sm text-red-300 flex items-center gap-2">
                            <span className="w-1.5 h-1.5 rounded-full bg-red-400 flex-shrink-0" />
                            {f.replace(/_/g, ' ')}
                          </li>
                        ))}
                      </ul>
                    </div>
                  )}
                  {completeness.missing_fields.length > 0 && (
                    <div className="bg-yellow-900/20 border border-yellow-500/30 chamfer-8 p-4">
                      <div className="text-sm font-bold text-yellow-400 mb-2">Recommended Fields</div>
                      <div className="flex flex-wrap gap-2">
                        {completeness.missing_fields.map(f => (
                          <span key={f} className="px-2 py-0.5 text-micro bg-yellow-900/40 border border-yellow-500/30 text-yellow-300 chamfer-4">
                            {f.replace(/_/g, ' ')}
                          </span>
                        ))}
                      </div>
                    </div>
                  )}
                  {completeness.warnings.length > 0 && (
                    <div className="bg-blue-900/20 border border-blue-500/30 chamfer-8 p-4">
                      <div className="text-sm font-bold text-blue-400 mb-2">Quality Warnings</div>
                      <ul className="space-y-1">
                        {completeness.warnings.map((w, i) => (
                          <li key={i} className="text-sm text-blue-300">{w}</li>
                        ))}
                      </ul>
                    </div>
                  )}
                </>
              ) : (
                <div className="text-center py-8 text-sm text-text-muted">
                  Completeness data not yet available for this chart.
                </div>
              )}
            </div>
          ) : null}
        </div>
      </div>
    </div>
  );
}

// ── Page ──────────────────────────────────────────────────────────────────────

export default function EPCRPage() {
  const [charts, setCharts] = useState<EPCRChart[]>([]);
  const [loading, setLoading] = useState(true);
  const [showNew, setShowNew] = useState(false);
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [statusFilter, setStatusFilter] = useState<string>('ALL');

  const refresh = useCallback(async () => {
    try {
      const data = await listEPCRCharts();
      setCharts(data as EPCRChart[]);
    } catch {
      setCharts([]);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { refresh(); }, [refresh]);

  const filtered = statusFilter === 'ALL'
    ? charts
    : charts.filter(c => c.status === statusFilter);

  const statusCounts = (Object.keys(STATUS_CONFIG) as ChartStatus[]).reduce<Record<string, number>>(
    (acc, s) => ({ ...acc, [s]: charts.filter(c => c.status === s).length }),
    {}
  );

  const pendingQA = statusCounts['PENDING_QA'] || 0;
  const inProgress = statusCounts['IN_PROGRESS'] || 0;
  const lockedCount = statusCounts['LOCKED'] || 0;
  const completeScores = charts
    .map((c) => c.completeness_score)
    .filter((score): score is number => typeof score === 'number');
  const avgCompleteness = completeScores.length > 0
    ? Math.round((completeScores.reduce((a, b) => a + b, 0) / completeScores.length) * 100)
    : 0;
  const riskSeverity: SeverityLevel = pendingQA > 0 ? 'MEDIUM' : 'INFORMATIONAL';

  return (
    <>
      <ModuleDashboardShell
        title="ePCR Command Center"
        subtitle="NEMSIS 3.5 lifecycle orchestration · AI narrative assist · QA readiness control"
        accentColor="#ec4899"
        headerActions={
          <div className="flex items-center gap-2">
            {pendingQA > 0 && (
              <button
                onClick={() => setStatusFilter('PENDING_QA')}
                className="flex items-center gap-1.5 bg-yellow-900/30 border border-yellow-500/40 chamfer-4 px-3 py-1.5"
              >
                <div className="w-2 h-2 rounded-full bg-yellow-400 animate-pulse" />
                <span className="text-micro font-bold text-yellow-400">{pendingQA} pending QA</span>
              </button>
            )}
            <button onClick={() => setShowNew(true)} className="quantum-btn-primary px-4 py-1.5 text-sm font-bold">
              📋 New Chart
            </button>
          </div>
        }
        kpiStrip={
          <>
            <MetricCard label="Total Charts" value={charts.length} domain="clinical" compact />
            <MetricCard label="In Progress" value={inProgress} domain="clinical" compact />
            <MetricCard label="Pending QA" value={pendingQA} domain="clinical" compact />
            <MetricCard label="Locked" value={lockedCount} domain="clinical" compact />
            <MetricCard label="Avg Completeness" value={`${avgCompleteness}%`} domain="clinical" compact />
          </>
        }
        toolbar={
          <div className="flex items-center gap-2 mt-1 mb-1 flex-wrap">
            <button
              onClick={() => setStatusFilter('ALL')}
              className={`px-3 py-1 text-micro font-bold chamfer-4 border transition-all ${
                statusFilter === 'ALL'
                  ? 'bg-brand-orange border-brand-orange text-white'
                  : 'border-border-subtle text-text-muted hover:border-brand-orange/40'
              }`}
            >
              All ({charts.length})
            </button>
            {(Object.entries(STATUS_CONFIG) as [ChartStatus, typeof STATUS_CONFIG[ChartStatus]][]).map(([status, cfg]) => {
              const count = statusCounts[status] || 0;
              if (count === 0 && statusFilter !== status) return null;
              return (
                <button
                  key={status}
                  onClick={() => setStatusFilter(statusFilter === status ? 'ALL' : status)}
                  className={`px-3 py-1 text-micro font-bold chamfer-4 border transition-all ${
                    statusFilter === status
                      ? `${cfg.bg} ${cfg.border} ${cfg.text}`
                      : `${cfg.border} ${cfg.text} opacity-50 hover:opacity-80`
                  }`}
                >
                  {cfg.label} ({count})
                </button>
              );
            })}
          </div>
        }
        sidePanel={
          <div className="space-y-3">
            <SimpleModeSummary
              screenName="ePCR Command"
              domain="clinical"
              whatThisDoes="This screen manages patient care charts from draft through QA, lock, and export."
              whatIsWrong={pendingQA > 0 ? `${pendingQA} charts are blocked waiting for QA review.` : undefined}
              whatMatters="Incomplete or delayed charts create billing lag, compliance risk, and care documentation gaps."
              whatToClickNext={pendingQA > 0 ? 'Filter to Pending QA, open each chart, and resolve critical fields.' : 'Open In Progress charts and push them to QA with complete vitals/narrative.'}
              requiresReview={pendingQA > 0}
            />
            <AIExplanationCard
              domain="clinical"
              severity={riskSeverity}
              what={pendingQA > 0
                ? `QA backlog is elevated: ${pendingQA} charts currently require review.`
                : 'QA backlog is stable and no immediate review bottleneck is detected.'}
              why="Delayed ePCR finalization slows claim readiness and increases denial risk downstream."
              next={pendingQA > 0
                ? 'Prioritize oldest pending QA charts, validate critical fields, then submit lock/export.'
                : 'Continue moving in-progress charts to QA and maintain same-day completion cadence.'}
              requiresReview={pendingQA > 0}
            />
          </div>
        }
      >
        {loading ? (
          <QuantumTableSkeleton rows={5} />
        ) : filtered.length === 0 ? (
          <QuantumEmptyState
            title="No charts found"
            description={statusFilter !== 'ALL' ? `No ${STATUS_CONFIG[statusFilter as ChartStatus]?.label ?? statusFilter} charts.` : 'Create a new ePCR chart to get started.'}
            icon="document"
          />
        ) : (
          <div className="bg-bg-panel border border-border-subtle chamfer-8 overflow-hidden">
            <table className="w-full text-left">
              <thead>
                <tr className="border-b border-border-subtle">
                  {['Patient','Complaint','Unit','Date','Status','Risk','Completeness',''].map(h => (
                    <th key={h} className="px-4 py-3 text-micro uppercase tracking-widest text-text-muted">{h}</th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {filtered.map(chart => {
                  const statusOrDraft = (chart.status as ChartStatus) || 'DRAFT';
                  const cfg = STATUS_CONFIG[statusOrDraft] || STATUS_CONFIG.DRAFT;
                  return (
                    <tr
                      key={chart.id}
                      className="border-b border-border-subtle hover:bg-white/[0.02] cursor-pointer"
                      onClick={() => setSelectedId(chart.id)}
                    >
                      <td className="px-4 py-3">
                        <div className="text-sm font-semibold text-text-primary">
                          {chart.patient_first_name || chart.patient_last_name
                            ? `${chart.patient_first_name || ''} ${chart.patient_last_name || ''}`.trim()
                            : <span className="text-text-muted italic">Anonymous</span>}
                        </div>
                        {chart.patient_dob && (
                          <div className="text-micro text-text-muted">
                            DOB: {new Date(chart.patient_dob).toLocaleDateString()}
                          </div>
                        )}
                      </td>
                      <td className="px-4 py-3 text-sm text-text-secondary max-w-xs truncate">
                        {chart.chief_complaint || chart.dispatch_complaint || '—'}
                      </td>
                      <td className="px-4 py-3 text-sm text-text-secondary font-mono">{chart.unit_id || '—'}</td>
                      <td className="px-4 py-3 text-sm text-text-muted font-mono">
                        {chart.incident_date ? new Date(chart.incident_date).toLocaleDateString() : '—'}
                      </td>
                      <td className="px-4 py-3">
                        <StatusBadge status={statusOrDraft} />
                      </td>
                      <td className="px-4 py-3">
                        <SeverityBadge severity={cfg.severity} size="sm" />
                      </td>
                      <td className="px-4 py-3">
                        {chart.completeness_score != null
                          ? <CompletenessRing score={chart.completeness_score} />
                          : <span className="text-micro text-text-muted">—</span>}
                      </td>
                      <td className="px-4 py-3">
                        <button
                          onClick={e => { e.stopPropagation(); setSelectedId(chart.id); }}
                          className="text-micro font-semibold text-brand-orange hover:underline"
                        >
                          Open →
                        </button>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        )}
      </ModuleDashboardShell>

      {showNew && <NewChartForm onClose={() => setShowNew(false)} onCreated={() => refresh()} />}
      {selectedId && (
        <ChartDetail
          chartId={selectedId}
          onClose={() => setSelectedId(null)}
          onUpdated={() => { refresh(); }}
        />
      )}
    </>
  );
}
