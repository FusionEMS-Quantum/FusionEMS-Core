'use client';

import React, { useEffect, useState, useCallback } from 'react';
import { QuantumTableSkeleton, QuantumEmptyState } from '@/components/ui';
import {
  listTRIPDebts,
  buildTRIPCandidates,
  generateTRIPExport,
  listTRIPExports,
  getTRIPReconciliation,
  getTRIPSettings,
  saveTRIPSettings,
} from '@/services/api';

// ── Types ─────────────────────────────────────────────────────────────────────

interface TRIPDebt {
  id: string;
  debtor_name?: string;
  debtor_ssn_masked?: string;
  debt_id?: string;
  balance?: number;
  debt_age_days?: number;
  status?: string;
  payer_type?: string;
  incident_date?: string;
  enrolled_at?: string;
}

interface TRIPExport {
  id: string;
  generated_at?: string;
  record_count?: number;
  total_balance?: number;
  status?: string;
  filename?: string;
}

interface TRIPReconciliation {
  total_submitted?: number;
  total_intercepted?: number;
  total_rejected?: number;
  total_posted?: number;
  intercept_rate?: number;
  net_recovered?: number;
}

interface TRIPSettings {
  agency_code?: string;
  min_debt_age_days?: number;
  min_balance?: number;
  auto_enroll?: boolean;
  notification_email?: string;
}

// ── Helpers ───────────────────────────────────────────────────────────────────

function fmt$(n: number) {
  return new Intl.NumberFormat('en-US', { style: 'currency', currency: 'USD', maximumFractionDigits: 0 }).format(n);
}

function StatusBadge({ status }: { status: string }) {
  const cls =
    status === 'ENROLLED' ? 'bg-blue-900/30 border-[var(--color-status-info)]/40 text-[var(--color-status-info)]' :
    status === 'INTERCEPTED' ? 'bg-green-900/30 border-[var(--color-status-active)]/40 text-[var(--color-status-active)]' :
    status === 'REJECTED' ? 'bg-red-900/30 border-[var(--color-brand-red)]/40 text-[var(--color-brand-red)]' :
    status === 'PENDING' ? 'bg-yellow-900/30 border-yellow-500/40 text-yellow-300' :
    status === 'POSTED' ? 'bg-purple-900/30 border-purple-500/40 text-purple-300' :
    'bg-[var(--color-bg-panel)]/50 border-gray-600 text-[var(--color-text-muted)]';
  return (
    <span className={`text-xs font-semibold px-2 py-0.5 chamfer-4 border ${cls}`}>{status}</span>
  );
}

// ── Debt Table ────────────────────────────────────────────────────────────────

function DebtTable({
  debts,
  onBuildCandidates,
  onExport,
}: {
  debts: TRIPDebt[];
  onBuildCandidates: () => Promise<void>;
  onExport: () => Promise<void>;
}) {
  const [building, setBuilding] = useState(false);
  const [exporting, setExporting] = useState(false);
  const [statusFilter, setStatusFilter] = useState<string>('ALL');

  const statuses = ['ALL', 'CANDIDATE', 'ENROLLED', 'INTERCEPTED', 'REJECTED', 'POSTED'];
  const filtered = debts.filter(d => statusFilter === 'ALL' || d.status === statusFilter);

  const totalBalance = filtered.reduce((sum, d) => sum + (d.balance ?? 0), 0);

  async function handleBuild() {
    setBuilding(true);
    try { await onBuildCandidates(); } finally { setBuilding(false); }
  }

  async function handleExport() {
    setExporting(true);
    try { await onExport(); } finally { setExporting(false); }
  }

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          {statuses.map(s => (
            <button
              key={s}
              onClick={() => setStatusFilter(s)}
              className={`px-3 py-1.5 text-micro font-semibold chamfer-4 border transition-colors ${
                statusFilter === s ? 'bg-brand-orange/15 border-brand-orange/35 text-brand-orange' :
                'bg-[var(--color-bg-base)]/[0.03] border-border-subtle text-[var(--color-text-muted)] hover:text-[var(--color-text-secondary)]'
              }`}
            >
              {s}
            </button>
          ))}
        </div>
        <div className="flex items-center gap-2">
          <button
            onClick={handleBuild}
            disabled={building}
            className="quantum-btn-sm disabled:opacity-50"
          >
            {building ? 'Building…' : '⚡ Build Candidates'}
          </button>
          <button
            onClick={handleExport}
            disabled={exporting || filtered.filter(d => d.status === 'ENROLLED').length === 0}
            className="quantum-btn-primary disabled:opacity-50"
          >
            {exporting ? 'Generating…' : '↑ Generate DOR Export'}
          </button>
        </div>
      </div>

      {filtered.length > 0 && (
        <div className="flex items-center gap-4 bg-[var(--color-bg-panel)] border border-border-subtle chamfer-8 px-4 py-3">
          <div>
            <div className="text-2xl font-black text-[var(--color-text-primary)]">{filtered.length}</div>
            <div className="text-micro text-[var(--color-text-muted)]">debts ({statusFilter})</div>
          </div>
          <div className="w-px h-8 bg-border-subtle" />
          <div>
            <div className="text-2xl font-black text-[var(--q-yellow)]">{fmt$(totalBalance)}</div>
            <div className="text-micro text-[var(--color-text-muted)]">total balance</div>
          </div>
          <div className="w-px h-8 bg-border-subtle" />
          <div>
            <div className="text-2xl font-black text-[var(--color-status-info)]">{filtered.filter(d => d.status === 'ENROLLED').length}</div>
            <div className="text-micro text-[var(--color-text-muted)]">enrolled</div>
          </div>
          <div className="w-px h-8 bg-border-subtle" />
          <div>
            <div className="text-2xl font-black text-[var(--color-status-active)]">{fmt$(filtered.filter(d => d.status === 'INTERCEPTED').reduce((s, d) => s + (d.balance ?? 0), 0))}</div>
            <div className="text-micro text-[var(--color-text-muted)]">intercepted</div>
          </div>
        </div>
      )}

      {filtered.length === 0 ? (
        <QuantumEmptyState
          title="No TRIP debts"
          description={statusFilter === 'ALL'
            ? "Click 'Build Candidates' to identify eligible debts (90+ days, qualifying payer types)."
            : `No debts with status: ${statusFilter}`}
          icon="document"
        />
      ) : (
        <div className="bg-[var(--color-bg-panel)] border border-border-subtle chamfer-8 overflow-hidden">
          <table className="w-full text-left">
            <thead>
              <tr className="border-b border-border-subtle">
                {['Debtor', 'SSN (masked)', 'Agency Debt ID', 'Balance', 'Age', 'Incident Date', 'Status', 'Enrolled'].map(h => (
                  <th key={h} className="px-4 py-3 text-micro uppercase tracking-widest text-[var(--color-text-muted)]">{h}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {filtered.map(debt => (
                <tr key={debt.id} className="border-b border-border-subtle hover:bg-[var(--color-bg-base)]/[0.02]">
                  <td className="px-4 py-3 text-sm font-semibold text-[var(--color-text-primary)]">{debt.debtor_name || '—'}</td>
                  <td className="px-4 py-3 text-xs font-mono text-[var(--color-text-muted)]">{debt.debtor_ssn_masked || '***-**-****'}</td>
                  <td className="px-4 py-3 text-xs font-mono text-[var(--color-text-secondary)]">{debt.debt_id || debt.id.slice(0, 12)}</td>
                  <td className="px-4 py-3 text-sm font-mono font-bold text-[var(--q-yellow)]">{debt.balance != null ? fmt$(debt.balance) : '—'}</td>
                  <td className="px-4 py-3 text-sm text-[var(--color-text-secondary)]">
                    {debt.debt_age_days != null ? (
                      <span className={debt.debt_age_days >= 90 ? 'text-[var(--color-status-active)]' : 'text-[var(--color-brand-red)]'}>
                        {debt.debt_age_days}d
                      </span>
                    ) : '—'}
                  </td>
                  <td className="px-4 py-3 text-xs font-mono text-[var(--color-text-muted)]">
                    {debt.incident_date ? new Date(debt.incident_date).toLocaleDateString() : '—'}
                  </td>
                  <td className="px-4 py-3"><StatusBadge status={debt.status || 'UNKNOWN'} /></td>
                  <td className="px-4 py-3 text-xs font-mono text-[var(--color-text-muted)]">
                    {debt.enrolled_at ? new Date(debt.enrolled_at).toLocaleDateString() : '—'}
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

// ── Export History ────────────────────────────────────────────────────────────

function ExportHistory({ exports }: { exports: TRIPExport[] }) {
  if (exports.length === 0) {
    return (
      <QuantumEmptyState
        title="No DOR exports generated"
        description="Generate a TRIP export from the Debts tab to submit to the Wisconsin Department of Revenue."
        icon="document"
      />
    );
  }

  return (
    <div className="bg-[var(--color-bg-panel)] border border-border-subtle chamfer-8 overflow-hidden">
      <table className="w-full text-left">
        <thead>
          <tr className="border-b border-border-subtle">
            {['Export ID', 'Generated', 'Records', 'Total Balance', 'Status', 'Filename'].map(h => (
              <th key={h} className="px-4 py-3 text-micro uppercase tracking-widest text-[var(--color-text-muted)]">{h}</th>
            ))}
          </tr>
        </thead>
        <tbody>
          {exports.map(exp => (
            <tr key={exp.id} className="border-b border-border-subtle hover:bg-[var(--color-bg-base)]/[0.02]">
              <td className="px-4 py-3 text-xs font-mono text-[var(--color-text-muted)]">{exp.id.slice(0, 12)}</td>
              <td className="px-4 py-3 text-xs font-mono text-[var(--color-text-muted)]">
                {exp.generated_at ? new Date(exp.generated_at).toLocaleString() : '—'}
              </td>
              <td className="px-4 py-3 text-sm text-[var(--color-text-secondary)]">{exp.record_count ?? '—'}</td>
              <td className="px-4 py-3 text-sm font-mono text-[var(--q-yellow)]">{exp.total_balance != null ? fmt$(exp.total_balance) : '—'}</td>
              <td className="px-4 py-3"><StatusBadge status={exp.status || 'UNKNOWN'} /></td>
              <td className="px-4 py-3 text-xs font-mono text-[var(--color-text-muted)] truncate max-w-xs">{exp.filename || '—'}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

// ── Reconciliation View ───────────────────────────────────────────────────────

function ReconciliationView({ data }: { data: TRIPReconciliation | null }) {
  if (!data) {
    return (
      <QuantumEmptyState
        title="No reconciliation data"
        description="Reconciliation data will appear after TRIP postings are imported."
        icon="check-circle"
      />
    );
  }

  const interceptRate = data.intercept_rate ?? 0;
  const interceptPct = (interceptRate * 100).toFixed(1);

  return (
    <div className="space-y-5">
      <div className="grid grid-cols-3 gap-4">
        {[
          { label: 'Total Submitted', value: String(data.total_submitted ?? 0), color: 'text-[var(--color-text-primary)]' },
          { label: 'Intercepted', value: String(data.total_intercepted ?? 0), color: 'text-[var(--color-status-active)]' },
          { label: 'Rejected', value: String(data.total_rejected ?? 0), color: 'text-[var(--color-brand-red)]' },
          { label: 'Posted to AR', value: String(data.total_posted ?? 0), color: 'text-[var(--color-status-info)]' },
          { label: 'Intercept Rate', value: `${interceptPct}%`, color: parseFloat(interceptPct) >= 50 ? 'text-[var(--color-status-active)]' : 'text-yellow-400' },
          { label: 'Net Recovered', value: data.net_recovered != null ? fmt$(data.net_recovered) : '—', color: 'text-[var(--color-status-active)]' },
        ].map(m => (
          <div key={m.label} className="bg-[var(--color-bg-panel)] border border-border-subtle chamfer-8 px-4 py-4">
            <div className={`text-3xl font-black ${m.color}`}>{m.value}</div>
            <div className="text-micro text-[var(--color-text-muted)] mt-0.5">{m.label}</div>
          </div>
        ))}
      </div>

      <div className="bg-[var(--color-bg-panel)] border border-border-subtle chamfer-8 p-4">
        <div className="text-micro uppercase tracking-widest text-[var(--color-text-muted)] mb-3">Intercept Pipeline</div>
        <div className="space-y-3">
          {[
            { label: 'Submitted to DOR', value: data.total_submitted ?? 0, color: 'bg-[var(--color-status-info)]/40' },
            { label: 'Intercepted', value: data.total_intercepted ?? 0, color: 'bg-[var(--color-status-active)]/40' },
            { label: 'Rejected', value: data.total_rejected ?? 0, color: 'bg-[var(--color-brand-red)]/40' },
            { label: 'Posted to AR', value: data.total_posted ?? 0, color: 'bg-purple-500/40' },
          ].map(stage => {
            const max = Math.max(data.total_submitted ?? 0, 1);
            return (
              <div key={stage.label} className="flex items-center gap-3">
                <span className="text-micro text-[var(--color-text-muted)] w-28 flex-shrink-0">{stage.label}</span>
                <div className="flex-1 h-5 bg-[var(--color-bg-base)]/[0.04] chamfer-4 overflow-hidden">
                  <div className={`h-full ${stage.color} chamfer-4 flex items-center px-2 transition-all`} style={{ width: `${(stage.value / max) * 100}%` }}>
                    <span className="text-micro text-white/80 whitespace-nowrap">{stage.value}</span>
                  </div>
                </div>
              </div>
            );
          })}
        </div>
      </div>
    </div>
  );
}

// ── Settings View ─────────────────────────────────────────────────────────────

function SettingsView({ settings, onSave }: { settings: TRIPSettings; onSave: (_s: TRIPSettings) => Promise<void> }) {
  const [form, setForm] = useState<TRIPSettings>(settings);
  const [saving, setSaving] = useState(false);
  const [saved, setSaved] = useState(false);

  async function handleSave() {
    setSaving(true);
    try {
      await onSave(form);
      setSaved(true);
      setTimeout(() => setSaved(false), 3000);
    } finally {
      setSaving(false);
    }
  }

  return (
    <div className="max-w-lg space-y-4">
      <div className="bg-blue-900/20 border border-[var(--color-status-info)]/30 chamfer-8 p-4 text-sm text-[var(--color-status-info)]">
        Wisconsin Tax Refund Intercept Program (TRIP) — Government agencies may submit qualifying delinquent debts to the Wisconsin DOR.
        Minimum debt age: 90 days. Required: Debtor name, SSN/DL/FEIN, balance, Agency Debt ID.
      </div>

      <div className="bg-[var(--color-bg-panel)] border border-border-subtle chamfer-8 p-5 space-y-4">
        {[
          { key: 'agency_code' as const, label: 'Agency Code', type: 'text', placeholder: 'WI agency code' },
          { key: 'min_debt_age_days' as const, label: 'Min Debt Age (days)', type: 'number', placeholder: '90' },
          { key: 'min_balance' as const, label: 'Min Balance ($)', type: 'number', placeholder: '50' },
          { key: 'notification_email' as const, label: 'Notification Email', type: 'email', placeholder: 'billing@agency.gov' },
        ].map(field => (
          <div key={field.key}>
            <label className="text-micro uppercase tracking-widest text-[var(--color-text-muted)] block mb-1.5">{field.label}</label>
            <input
              type={field.type}
              value={(form[field.key] as string | number) ?? ''}
              onChange={e => setForm(f => ({ ...f, [field.key]: field.type === 'number' ? parseFloat(e.target.value) : e.target.value }))}
              className="w-full bg-[var(--color-bg-base)] border border-border-subtle chamfer-4 px-3 py-2 text-sm text-[var(--color-text-primary)] focus:outline-none focus:border-brand-orange/60"
              placeholder={field.placeholder}
            />
          </div>
        ))}

        <div className="flex items-center gap-3">
          <input
            id="auto_enroll"
            type="checkbox"
            checked={form.auto_enroll ?? false}
            onChange={e => setForm(f => ({ ...f, auto_enroll: e.target.checked }))}
            className="accent-brand-orange"
          />
          <label htmlFor="auto_enroll" className="text-sm text-[var(--color-text-secondary)]">Auto-enroll eligible debts (90+ days, qualifying payer)</label>
        </div>

        <button
          onClick={handleSave}
          disabled={saving}
          className="quantum-btn-primary disabled:opacity-50 w-full"
        >
          {saved ? '✓ Saved' : saving ? 'Saving…' : 'Save Settings'}
        </button>
      </div>
    </div>
  );
}

// ── Page ──────────────────────────────────────────────────────────────────────

type ActiveView = 'debts' | 'exports' | 'reconciliation' | 'settings';

export default function TRIPPage() {
  const [activeView, setActiveView] = useState<ActiveView>('debts');
  const [debts, setDebts] = useState<TRIPDebt[]>([]);
  const [exports, setExports] = useState<TRIPExport[]>([]);
  const [reconciliation, setReconciliation] = useState<TRIPReconciliation | null>(null);
  const [settings, setSettings] = useState<TRIPSettings>({});
  const [loading, setLoading] = useState(true);
  const [loadError, setLoadError] = useState<string | null>(null);

  const loadData = useCallback(async () => {
    setLoading(true);
    setLoadError(null);
    let anyFailed = false;
    try {
      const [debtData, settingsData] = await Promise.all([
        listTRIPDebts().catch((err) => { anyFailed = true; console.error('[TRIP] debts failed:', err); return []; }),
        getTRIPSettings().catch((err) => { anyFailed = true; console.error('[TRIP] settings failed:', err); return {}; }),
      ]);
      if (anyFailed) setLoadError('Some TRIP data failed to load. Displayed data may be incomplete.');
      setDebts(Array.isArray(debtData) ? debtData : debtData?.debts || []);
      setSettings(settingsData || {});
    } finally {
      setLoading(false);
    }
  }, []);

  const loadViewData = useCallback(async (view: ActiveView) => {
    if (view === 'exports') {
      const data = await listTRIPExports().catch(() => []);
      setExports(Array.isArray(data) ? data : data?.exports || []);
    }
    if (view === 'reconciliation') {
      const data = await getTRIPReconciliation().catch(() => null);
      setReconciliation(data);
    }
  }, []);

  useEffect(() => { loadData(); }, [loadData]);
  useEffect(() => { loadViewData(activeView); }, [activeView, loadViewData]);

  async function handleBuildCandidates() {
    await buildTRIPCandidates();
    await loadData();
  }

  async function handleExport() {
    await generateTRIPExport();
    const data = await listTRIPExports().catch(() => []);
    setExports(Array.isArray(data) ? data : data?.exports || []);
    setActiveView('exports');
  }

  async function handleSaveSettings(newSettings: TRIPSettings) {
    await saveTRIPSettings(newSettings as Record<string, unknown>);
    setSettings(newSettings);
  }

  const enrolledCount = debts.filter(d => d.status === 'ENROLLED').length;
  const interceptedBalance = debts.filter(d => d.status === 'INTERCEPTED').reduce((s, d) => s + (d.balance ?? 0), 0);
  const candidateCount = debts.filter(d => d.status === 'CANDIDATE').length;
  const totalBalance = debts.reduce((s, d) => s + (d.balance ?? 0), 0);

  return (
    <div className="flex flex-col bg-[var(--color-bg-base)] min-h-screen">
      {loadError && (
        <div className="mx-5 mt-4 px-4 py-3 bg-red-900/20 border border-[var(--color-brand-red)]/30 text-[var(--color-brand-red)] text-sm font-medium chamfer-4">
          ⚠ {loadError}
        </div>
      )}
      {/* Header */}
      <div className="flex-shrink-0 border-b border-border-subtle bg-[var(--color-bg-panel)]/50 px-5 py-4">
        <div className="flex items-center justify-between">
          <div>
            <div className="text-xs font-black text-[var(--color-text-primary)] uppercase tracking-widest">Wisconsin TRIP</div>
            <div className="text-micro text-[var(--color-text-muted)]">Tax Refund Intercept Program · Debt enrollment · DOR exports · Reconciliation</div>
          </div>
          <div className="flex items-center gap-2">
            {candidateCount > 0 && (
              <div className="flex items-center gap-1.5 bg-yellow-900/30 border border-yellow-500/40 chamfer-4 px-3 py-1.5">
                <span className="text-micro font-bold text-[var(--q-yellow)]">{candidateCount} candidates ready to enroll</span>
              </div>
            )}
          </div>
        </div>

        <div className="grid grid-cols-4 gap-3 mt-4">
          {[
            { label: 'Total TRIP Debts', value: debts.length.toString(), color: 'text-[var(--color-text-primary)]' },
            { label: 'Total Balance', value: fmt$(totalBalance), color: 'text-yellow-400' },
            { label: 'Enrolled', value: enrolledCount.toString(), color: 'text-[var(--color-status-info)]' },
            { label: 'Intercepted (est.)', value: fmt$(interceptedBalance), color: 'text-[var(--color-status-active)]' },
          ].map(m => (
            <div key={m.label} className="bg-[var(--color-bg-panel)] border border-border-subtle chamfer-8 px-4 py-3">
              <div className={`text-2xl font-black ${m.color}`}>{m.value}</div>
              <div className="text-micro text-[var(--color-text-muted)] mt-0.5">{m.label}</div>
            </div>
          ))}
        </div>

        <div className="flex items-center gap-1 mt-4">
          {([
            { id: 'debts', label: 'Debt Register' },
            { id: 'exports', label: 'DOR Exports' },
            { id: 'reconciliation', label: 'Reconciliation' },
            { id: 'settings', label: 'Settings' },
          ] as const).map(t => (
            <button
              key={t.id}
              onClick={() => setActiveView(t.id)}
              className={`px-4 py-2 text-micro font-semibold border-b-2 transition-colors ${
                activeView === t.id ? 'border-brand-orange text-brand-orange' : 'border-transparent text-[var(--color-text-muted)] hover:text-[var(--color-text-secondary)]'
              }`}
            >
              {t.label}
            </button>
          ))}
        </div>
      </div>

      {/* Content */}
      <div className="flex-1 p-5">
        {loading && (activeView === 'debts' || activeView === 'settings') ? (
          <QuantumTableSkeleton rows={5} />
        ) : activeView === 'debts' ? (
          <DebtTable debts={debts} onBuildCandidates={handleBuildCandidates} onExport={handleExport} />
        ) : activeView === 'exports' ? (
          <ExportHistory exports={exports} />
        ) : activeView === 'reconciliation' ? (
          <ReconciliationView data={reconciliation} />
        ) : (
          <SettingsView settings={settings} onSave={handleSaveSettings} />
        )}
      </div>
    </div>
  );
}
