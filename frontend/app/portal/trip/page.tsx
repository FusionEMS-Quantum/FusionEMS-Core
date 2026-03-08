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
    status === 'ENROLLED' ? 'bg-blue-900/30 border-blue-500/40 text-blue-300' :
    status === 'INTERCEPTED' ? 'bg-green-900/30 border-green-500/40 text-green-300' :
    status === 'REJECTED' ? 'bg-red-900/30 border-red-500/40 text-red-300' :
    status === 'PENDING' ? 'bg-yellow-900/30 border-yellow-500/40 text-yellow-300' :
    status === 'POSTED' ? 'bg-purple-900/30 border-purple-500/40 text-purple-300' :
    'bg-zinc-900/50 border-gray-600 text-zinc-500';
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
                'bg-zinc-950/[0.03] border-border-subtle text-zinc-500 hover:text-zinc-400'
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
        <div className="flex items-center gap-4 bg-[#0A0A0B] border border-border-subtle chamfer-8 px-4 py-3">
          <div>
            <div className="text-2xl font-black text-zinc-100">{filtered.length}</div>
            <div className="text-micro text-zinc-500">debts ({statusFilter})</div>
          </div>
          <div className="w-px h-8 bg-border-subtle" />
          <div>
            <div className="text-2xl font-black text-yellow-400">{fmt$(totalBalance)}</div>
            <div className="text-micro text-zinc-500">total balance</div>
          </div>
          <div className="w-px h-8 bg-border-subtle" />
          <div>
            <div className="text-2xl font-black text-blue-400">{filtered.filter(d => d.status === 'ENROLLED').length}</div>
            <div className="text-micro text-zinc-500">enrolled</div>
          </div>
          <div className="w-px h-8 bg-border-subtle" />
          <div>
            <div className="text-2xl font-black text-green-400">{fmt$(filtered.filter(d => d.status === 'INTERCEPTED').reduce((s, d) => s + (d.balance ?? 0), 0))}</div>
            <div className="text-micro text-zinc-500">intercepted</div>
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
        <div className="bg-[#0A0A0B] border border-border-subtle chamfer-8 overflow-hidden">
          <table className="w-full text-left">
            <thead>
              <tr className="border-b border-border-subtle">
                {['Debtor', 'SSN (masked)', 'Agency Debt ID', 'Balance', 'Age', 'Incident Date', 'Status', 'Enrolled'].map(h => (
                  <th key={h} className="px-4 py-3 text-micro uppercase tracking-widest text-zinc-500">{h}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {filtered.map(debt => (
                <tr key={debt.id} className="border-b border-border-subtle hover:bg-zinc-950/[0.02]">
                  <td className="px-4 py-3 text-sm font-semibold text-zinc-100">{debt.debtor_name || '—'}</td>
                  <td className="px-4 py-3 text-xs font-mono text-zinc-500">{debt.debtor_ssn_masked || '***-**-****'}</td>
                  <td className="px-4 py-3 text-xs font-mono text-zinc-400">{debt.debt_id || debt.id.slice(0, 12)}</td>
                  <td className="px-4 py-3 text-sm font-mono font-bold text-yellow-400">{debt.balance != null ? fmt$(debt.balance) : '—'}</td>
                  <td className="px-4 py-3 text-sm text-zinc-400">
                    {debt.debt_age_days != null ? (
                      <span className={debt.debt_age_days >= 90 ? 'text-green-400' : 'text-red-400'}>
                        {debt.debt_age_days}d
                      </span>
                    ) : '—'}
                  </td>
                  <td className="px-4 py-3 text-xs font-mono text-zinc-500">
                    {debt.incident_date ? new Date(debt.incident_date).toLocaleDateString() : '—'}
                  </td>
                  <td className="px-4 py-3"><StatusBadge status={debt.status || 'UNKNOWN'} /></td>
                  <td className="px-4 py-3 text-xs font-mono text-zinc-500">
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
    <div className="bg-[#0A0A0B] border border-border-subtle chamfer-8 overflow-hidden">
      <table className="w-full text-left">
        <thead>
          <tr className="border-b border-border-subtle">
            {['Export ID', 'Generated', 'Records', 'Total Balance', 'Status', 'Filename'].map(h => (
              <th key={h} className="px-4 py-3 text-micro uppercase tracking-widest text-zinc-500">{h}</th>
            ))}
          </tr>
        </thead>
        <tbody>
          {exports.map(exp => (
            <tr key={exp.id} className="border-b border-border-subtle hover:bg-zinc-950/[0.02]">
              <td className="px-4 py-3 text-xs font-mono text-zinc-500">{exp.id.slice(0, 12)}</td>
              <td className="px-4 py-3 text-xs font-mono text-zinc-500">
                {exp.generated_at ? new Date(exp.generated_at).toLocaleString() : '—'}
              </td>
              <td className="px-4 py-3 text-sm text-zinc-400">{exp.record_count ?? '—'}</td>
              <td className="px-4 py-3 text-sm font-mono text-yellow-400">{exp.total_balance != null ? fmt$(exp.total_balance) : '—'}</td>
              <td className="px-4 py-3"><StatusBadge status={exp.status || 'UNKNOWN'} /></td>
              <td className="px-4 py-3 text-xs font-mono text-zinc-500 truncate max-w-xs">{exp.filename || '—'}</td>
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

  const interceptPct = ((data.intercept_rate ?? 0) * 100).toFixed(1);

  return (
    <div className="space-y-5">
      <div className="grid grid-cols-3 gap-4">
        {[
          { label: 'Total Submitted', value: (data.total_submitted ?? 0).toString(), color: 'text-zinc-100' },
          { label: 'Intercepted', value: (data.total_intercepted ?? 0).toString(), color: 'text-green-400' },
          { label: 'Rejected', value: (data.total_rejected ?? 0).toString(), color: 'text-red-400' },
          { label: 'Posted to AR', value: (data.total_posted ?? 0).toString(), color: 'text-blue-400' },
          { label: 'Intercept Rate', value: `${interceptPct}%`, color: parseFloat(interceptPct) >= 50 ? 'text-green-400' : 'text-yellow-400' },
          { label: 'Net Recovered', value: data.net_recovered != null ? fmt$(data.net_recovered) : '—', color: 'text-green-400' },
        ].map(m => (
          <div key={m.label} className="bg-[#0A0A0B] border border-border-subtle chamfer-8 px-4 py-4">
            <div className={`text-3xl font-black ${m.color}`}>{m.value}</div>
            <div className="text-micro text-zinc-500 mt-0.5">{m.label}</div>
          </div>
        ))}
      </div>

      <div className="bg-[#0A0A0B] border border-border-subtle chamfer-8 p-4">
        <div className="text-micro uppercase tracking-widest text-zinc-500 mb-3">Intercept Pipeline</div>
        <div className="space-y-3">
          {[
            { label: 'Submitted to DOR', value: data.total_submitted ?? 0, color: 'bg-blue-500/40' },
            { label: 'Intercepted', value: data.total_intercepted ?? 0, color: 'bg-green-500/40' },
            { label: 'Rejected', value: data.total_rejected ?? 0, color: 'bg-red-500/40' },
            { label: 'Posted to AR', value: data.total_posted ?? 0, color: 'bg-purple-500/40' },
          ].map(stage => {
            const max = data.total_submitted ?? 1;
            return (
              <div key={stage.label} className="flex items-center gap-3">
                <span className="text-micro text-zinc-500 w-28 flex-shrink-0">{stage.label}</span>
                <div className="flex-1 h-5 bg-zinc-950/[0.04] chamfer-4 overflow-hidden">
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
      <div className="bg-blue-900/20 border border-blue-500/30 chamfer-8 p-4 text-sm text-blue-300">
        Wisconsin Tax Refund Intercept Program (TRIP) — Government agencies may submit qualifying delinquent debts to the Wisconsin DOR.
        Minimum debt age: 90 days. Required: Debtor name, SSN/DL/FEIN, balance, Agency Debt ID.
      </div>

      <div className="bg-[#0A0A0B] border border-border-subtle chamfer-8 p-5 space-y-4">
        {[
          { key: 'agency_code' as const, label: 'Agency Code', type: 'text', placeholder: 'WI agency code' },
          { key: 'min_debt_age_days' as const, label: 'Min Debt Age (days)', type: 'number', placeholder: '90' },
          { key: 'min_balance' as const, label: 'Min Balance ($)', type: 'number', placeholder: '50' },
          { key: 'notification_email' as const, label: 'Notification Email', type: 'email', placeholder: 'billing@agency.gov' },
        ].map(field => (
          <div key={field.key}>
            <label className="text-micro uppercase tracking-widest text-zinc-500 block mb-1.5">{field.label}</label>
            <input
              type={field.type}
              value={(form[field.key] as string | number) ?? ''}
              onChange={e => setForm(f => ({ ...f, [field.key]: field.type === 'number' ? parseFloat(e.target.value) : e.target.value }))}
              className="w-full bg-black border border-border-subtle chamfer-4 px-3 py-2 text-sm text-zinc-100 focus:outline-none focus:border-brand-orange/60"
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
          <label htmlFor="auto_enroll" className="text-sm text-zinc-400">Auto-enroll eligible debts (90+ days, qualifying payer)</label>
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

  const loadData = useCallback(async () => {
    setLoading(true);
    try {
      const [debtData, settingsData] = await Promise.all([
        listTRIPDebts().catch(() => []),
        getTRIPSettings().catch(() => ({})),
      ]);
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
    <div className="flex flex-col bg-black min-h-screen">
      {/* Header */}
      <div className="flex-shrink-0 border-b border-border-subtle bg-[#0A0A0B]/50 px-5 py-4">
        <div className="flex items-center justify-between">
          <div>
            <div className="text-xs font-black text-zinc-100 uppercase tracking-widest">Wisconsin TRIP</div>
            <div className="text-micro text-zinc-500">Tax Refund Intercept Program · Debt enrollment · DOR exports · Reconciliation</div>
          </div>
          <div className="flex items-center gap-2">
            {candidateCount > 0 && (
              <div className="flex items-center gap-1.5 bg-yellow-900/30 border border-yellow-500/40 chamfer-4 px-3 py-1.5">
                <span className="text-micro font-bold text-yellow-400">{candidateCount} candidates ready to enroll</span>
              </div>
            )}
          </div>
        </div>

        <div className="grid grid-cols-4 gap-3 mt-4">
          {[
            { label: 'Total TRIP Debts', value: debts.length.toString(), color: 'text-zinc-100' },
            { label: 'Total Balance', value: fmt$(totalBalance), color: 'text-yellow-400' },
            { label: 'Enrolled', value: enrolledCount.toString(), color: 'text-blue-400' },
            { label: 'Intercepted (est.)', value: fmt$(interceptedBalance), color: 'text-green-400' },
          ].map(m => (
            <div key={m.label} className="bg-[#0A0A0B] border border-border-subtle chamfer-8 px-4 py-3">
              <div className={`text-2xl font-black ${m.color}`}>{m.value}</div>
              <div className="text-micro text-zinc-500 mt-0.5">{m.label}</div>
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
                activeView === t.id ? 'border-brand-orange text-brand-orange' : 'border-transparent text-zinc-500 hover:text-zinc-400'
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
