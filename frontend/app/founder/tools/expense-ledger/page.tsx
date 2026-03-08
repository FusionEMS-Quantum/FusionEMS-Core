'use client';
import { motion } from 'framer-motion';
import Link from 'next/link';
import { useEffect, useMemo, useState } from 'react';

const API = process.env.NEXT_PUBLIC_API_BASE || process.env.NEXT_PUBLIC_API_URL || '';

type ExpenseEntry = {
  id: string;
  expense_date: string;
  vendor: string;
  category: string;
  amount_cents: number;
  description: string;
  receipt_attached: boolean;
};

type CategoryBreakdown = {
  label: string;
  amount_cents: number;
  pct: number;
};

type ExpenseSummary = {
  month_total_cents: number;
  total_cents: number;
  entry_count: number;
  receipt_missing_count: number;
  quickbooks_sync_status: string;
};

type ExpenseLedgerResponse = {
  summary: ExpenseSummary;
  category_breakdown: CategoryBreakdown[];
  entries: ExpenseEntry[];
};

function SectionHeader({ number, title, sub }: { number: string; title: string; sub?: string }) {
  return (
    <div className="border-b border-border-subtle pb-2 mb-4">
      <div className="flex items-baseline gap-3">
        <span className="text-micro font-bold text-[#FF4D00]/70 font-mono">MODULE {number}</span>
        <h2 className="text-sm font-bold uppercase tracking-widest text-zinc-100">{title}</h2>
        {sub && <span className="text-xs text-zinc-500">{sub}</span>}
      </div>
    </div>
  );
}

function Badge({ label, status }: { label: string; status: 'ok' | 'warn' | 'error' | 'info' }) {
  const c = { ok: 'var(--color-status-active)', warn: 'var(--color-status-warning)', error: 'var(--color-brand-red)', info: 'var(--color-status-info)' };
  return (
    <span
      className="inline-flex items-center gap-1.5 px-2 py-0.5 chamfer-4 text-micro font-semibold uppercase tracking-wider border"
      style={{ borderColor: `${c[status]}40`, color: c[status], background: `${c[status]}12` }}
    >
      <span className="w-1 h-1 " style={{ background: c[status] }} />
      {label}
    </span>
  );
}

function Panel({ children, className }: { children: React.ReactNode; className?: string }) {
  return (
    <div
      className={`bg-[#0A0A0B] border border-border-DEFAULT p-4 ${className ?? ''}`}
      style={{ clipPath: 'polygon(0 0,calc(100% - 10px) 0,100% 10px,100% 100%,0 100%)' }}
    >
      {children}
    </div>
  );
}

export default function ExpenseLedgerPage() {
  const [showForm, setShowForm] = useState(false);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [entries, setEntries] = useState<ExpenseEntry[]>([]);
  const [categoryBreakdown, setCategoryBreakdown] = useState<CategoryBreakdown[]>([]);
  const [summary, setSummary] = useState<ExpenseSummary>({
    month_total_cents: 0,
    total_cents: 0,
    entry_count: 0,
    receipt_missing_count: 0,
    quickbooks_sync_status: 'unknown',
  });
  const [expenseForm, setExpenseForm] = useState({
    date: '',
    amount: '',
    category: 'AWS',
    description: '',
    vendor: '',
  });

  const fetchLedger = async () => {
    const token = typeof window !== 'undefined' ? localStorage.getItem('token') : null;
    const headers = token ? { Authorization: `Bearer ${token}` } : undefined;
    const res = await fetch(`${API}/api/v1/founder/business/expense-ledger?limit=500`, { headers });
    if (!res.ok) {
      throw new Error(`Expense ledger request failed (${res.status})`);
    }
    const payload = (await res.json()) as ExpenseLedgerResponse;
    setEntries(payload.entries ?? []);
    setCategoryBreakdown(payload.category_breakdown ?? []);
    setSummary(payload.summary ?? summary);
  };

  useEffect(() => {
    fetchLedger()
      .catch((e: unknown) => {
        setError(e instanceof Error ? e.message : 'Unable to load expense ledger');
      })
      .finally(() => setLoading(false));
  }, []);

  const monthTotalDollars = summary.month_total_cents / 100;
  const largestCategory = categoryBreakdown[0];
  const softwareSpend = categoryBreakdown
    .filter((c) => c.label.toLowerCase().includes('software'))
    .reduce((acc, c) => acc + c.amount_cents, 0);

  const exportCsv = useMemo(() => {
    if (entries.length === 0) return '';
    const header = ['expense_date', 'vendor', 'category', 'amount_cents', 'description', 'receipt_attached'];
    const lines = entries.map((entry) => [
      entry.expense_date,
      entry.vendor,
      entry.category,
      String(entry.amount_cents),
      entry.description.replaceAll(',', ' '),
      String(entry.receipt_attached),
    ].join(','));
    return [header.join(','), ...lines].join('\n');
  }, [entries]);

  const downloadContent = (filename: string, content: string, contentType: string) => {
    const blob = new Blob([content], { type: contentType });
    const url = URL.createObjectURL(blob);
    const anchor = document.createElement('a');
    anchor.href = url;
    anchor.download = filename;
    anchor.click();
    URL.revokeObjectURL(url);
  };

  const saveExpense = async () => {
    const amount = Number(expenseForm.amount);
    if (!expenseForm.vendor || !expenseForm.category || !Number.isFinite(amount) || amount <= 0) {
      setError('Provide vendor, category, and a valid amount before saving.');
      return;
    }

    const token = typeof window !== 'undefined' ? localStorage.getItem('token') : null;
    const headers: Record<string, string> = {
      'Content-Type': 'application/json',
    };
    if (token) {
      headers.Authorization = `Bearer ${token}`;
    }

    const res = await fetch(`${API}/api/v1/founder/business/expense-ledger/entries`, {
      method: 'POST',
      headers,
      body: JSON.stringify({
        vendor: expenseForm.vendor,
        category: expenseForm.category,
        amount_cents: Math.round(amount * 100),
        description: expenseForm.description,
        expense_date: expenseForm.date || new Date().toISOString().slice(0, 10),
        receipt_attached: false,
      }),
    });

    if (!res.ok) {
      throw new Error(`Failed to save expense (${res.status})`);
    }

    setExpenseForm({ date: '', amount: '', category: 'AWS', description: '', vendor: '' });
    setShowForm(false);
    await fetchLedger();
  };

  return (
    <div className="min-h-screen bg-black text-zinc-100 p-6 space-y-6">
      {/* Header */}
      <motion.div initial={{ opacity: 0, y: -12 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.4 }}>
        <div className="flex items-center justify-between mb-1">
          <span className="text-micro font-bold text-[#FF4D00]/70 font-mono tracking-widest uppercase">
            MODULE 11 · FOUNDER TOOLS
          </span>
          <Link href="/founder" className="text-body text-zinc-500 hover:text-[#FF4D00] transition-colors">
            ← Back to Founder OS
          </Link>
        </div>
        <h1 className="text-2xl font-bold tracking-tight text-zinc-100" style={{ textShadow: '0 0 24px rgba(255,107,26,0.3)' }}>
          Expense Ledger
        </h1>
        <p className="text-xs text-zinc-500 mt-1">Track business expenses · categorize · export for accounting</p>
      </motion.div>

      {/* MODULE 1 — Monthly Summary */}
      <motion.div initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.05 }}>
        <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
          {[
            { label: 'Total MTD', value: `$${monthTotalDollars.toLocaleString()}`, status: 'info' as const },
            {
              label: largestCategory ? `${largestCategory.label}` : 'Largest Category',
              value: largestCategory ? `$${(largestCategory.amount_cents / 100).toLocaleString()}` : '$0',
              status: 'error' as const,
            },
            { label: 'Software & Tools', value: `$${(softwareSpend / 100).toLocaleString()}`, status: 'warn' as const },
            { label: 'Receipt Gaps', value: String(summary.receipt_missing_count), status: summary.receipt_missing_count > 0 ? 'warn' as const : 'ok' as const },
          ].map((s) => (
            <Panel key={s.label} className="flex flex-col gap-1">
              <span className="text-micro text-zinc-500 uppercase tracking-wider">{s.label}</span>
              <span
                className="text-xl font-bold"
                style={{ color: s.status === 'error' ? 'var(--color-brand-red)' : s.status === 'warn' ? 'var(--color-status-warning)' : 'rgba(255,255,255,0.9)' }}
              >
                {s.value}
              </span>
              <Badge label={s.status === 'error' ? 'largest' : s.status} status={s.status} />
            </Panel>
          ))}
        </div>
      </motion.div>

      {/* MODULE 2 — Add Expense */}
      <motion.div initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.1 }}>
        <Panel>
          <SectionHeader number="2" title="Add Expense" />
          <button
            onClick={() => setShowForm((v) => !v)}
            className="px-4 py-2 text-xs font-bold uppercase tracking-widest chamfer-4 transition-all hover:brightness-110"
            style={{ background: '#FF4D00', color: '#000' }}
          >
            {showForm ? 'Hide Form' : 'Add Expense'}
          </button>
          {showForm && (
            <div className="mt-4 grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3">
              <div className="flex flex-col gap-1">
                <label className="text-micro text-zinc-500 uppercase tracking-wider">Date</label>
                <input
                  type="date"
                  value={expenseForm.date}
                  onChange={(e) => setExpenseForm({ ...expenseForm, date: e.target.value })}
                  className="bg-zinc-950/[0.04] border border-border-DEFAULT text-xs text-zinc-100 px-3 py-2 chamfer-4 outline-none focus:border-orange"
                />
              </div>
              <div className="flex flex-col gap-1">
                <label className="text-micro text-zinc-500 uppercase tracking-wider">Amount</label>
                <input
                  type="number"
                  value={expenseForm.amount}
                  onChange={(e) => setExpenseForm({ ...expenseForm, amount: e.target.value })}
                  placeholder="0.00"
                  className="bg-zinc-950/[0.04] border border-border-DEFAULT text-xs text-zinc-100 px-3 py-2 chamfer-4 outline-none focus:border-orange placeholder:text-zinc-500"
                />
              </div>
              <div className="flex flex-col gap-1">
                <label className="text-micro text-zinc-500 uppercase tracking-wider">Category</label>
                <select
                  value={expenseForm.category}
                  onChange={(e) => setExpenseForm({ ...expenseForm, category: e.target.value })}
                  className="bg-zinc-950/[0.04] border border-border-DEFAULT text-xs text-zinc-100 px-3 py-2 chamfer-4 outline-none focus:border-orange"
                >
                  {['AWS', 'Software', 'Marketing', 'Legal', 'Travel', 'Other'].map((c) => (
                    <option key={c} value={c} className="bg-[#0A0A0B]">{c}</option>
                  ))}
                </select>
              </div>
              <div className="flex flex-col gap-1">
                <label className="text-micro text-zinc-500 uppercase tracking-wider">Vendor</label>
                <input
                  type="text"
                  value={expenseForm.vendor}
                  onChange={(e) => setExpenseForm({ ...expenseForm, vendor: e.target.value })}
                  placeholder="Vendor name"
                  className="bg-zinc-950/[0.04] border border-border-DEFAULT text-xs text-zinc-100 px-3 py-2 chamfer-4 outline-none focus:border-orange placeholder:text-zinc-500"
                />
              </div>
              <div className="flex flex-col gap-1">
                <label className="text-micro text-zinc-500 uppercase tracking-wider">Description</label>
                <input
                  type="text"
                  value={expenseForm.description}
                  onChange={(e) => setExpenseForm({ ...expenseForm, description: e.target.value })}
                  placeholder="Description"
                  className="bg-zinc-950/[0.04] border border-border-DEFAULT text-xs text-zinc-100 px-3 py-2 chamfer-4 outline-none focus:border-orange placeholder:text-zinc-500"
                />
              </div>
              <div className="flex items-end">
                <button
                  className="px-4 py-2 text-xs font-bold uppercase tracking-widest chamfer-4 transition-all hover:brightness-110"
                  style={{ background: '#FF4D00', color: '#000' }}
                  onClick={() => {
                    saveExpense().catch((e: unknown) => {
                      setError(e instanceof Error ? e.message : 'Unable to save expense');
                    });
                  }}
                >
                  Save
                </button>
              </div>
            </div>
          )}
        </Panel>
      </motion.div>

      {/* MODULE 3 — Expense Log */}
      <motion.div initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.15 }}>
        <Panel>
          <SectionHeader number="3" title="Expense Log" sub="January 2026" />
          <div className="overflow-x-auto">
            <table className="w-full text-xs">
              <thead>
                <tr className="border-b border-border-subtle">
                  {['Date', 'Vendor', 'Category', 'Amount', 'Description', 'Receipt'].map((h) => (
                    <th key={h} className="text-left py-1.5 px-2 text-zinc-500 font-semibold uppercase tracking-wider text-micro">
                      {h}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {entries.map((exp) => (
                  <tr key={exp.id} className="border-b border-white/[0.03] hover:bg-zinc-950/[0.02]">
                    <td className="py-1.5 px-2 font-mono text-brand-orange text-body">{exp.expense_date.slice(0, 10)}</td>
                    <td className="py-1.5 px-2 text-zinc-100 font-medium">{exp.vendor}</td>
                    <td className="py-1.5 px-2 text-zinc-500">{exp.category}</td>
                    <td className="py-1.5 px-2 font-mono text-zinc-100 font-semibold">
                      ${(exp.amount_cents / 100).toLocaleString()}
                    </td>
                    <td className="py-1.5 px-2 text-zinc-500">{exp.description || '—'}</td>
                    <td className="py-1.5 px-2 text-center">
                      {exp.receipt_attached ? (
                        <span className="text-status-active font-bold">&#10003;</span>
                      ) : (
                        <span className="text-zinc-500">—</span>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </Panel>
      </motion.div>

      {/* MODULE 4 — Category Breakdown */}
      <motion.div initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.2 }}>
        <Panel>
          <SectionHeader number="4" title="Category Breakdown" sub="% of total spend" />
          <div className="space-y-3">
            {categoryBreakdown.map((cat) => (
              <div key={cat.label} className="flex items-center gap-3">
                <span className="text-xs text-zinc-400 w-32 shrink-0">{cat.label}</span>
                <div className="flex-1 h-2 bg-zinc-950/5  overflow-hidden">
                  <div
                    className="h-full  transition-all"
                    style={{
                      width: `${cat.pct}%`,
                      background: cat.pct >= 30
                        ? 'var(--color-brand-red)'
                        : cat.pct >= 15
                          ? 'var(--color-status-warning)'
                          : 'var(--color-status-info)',
                    }}
                  />
                </div>
                <span className="text-micro font-mono text-zinc-400 w-8 text-right">{cat.pct}%</span>
                <span className="text-body font-mono font-semibold text-zinc-100 w-16 text-right">${(cat.amount_cents / 100).toLocaleString()}</span>
              </div>
            ))}
          </div>
        </Panel>
      </motion.div>

      {/* MODULE 5 — Export Options */}
      <motion.div initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.25 }}>
        <Panel>
          <SectionHeader number="5" title="Export Options" />
          <div className="flex flex-wrap gap-3">
            {[
              { label: 'Export CSV', style: { background: 'rgba(76,175,80,0.12)', color: 'var(--q-green)', border: '1px solid rgba(76,175,80,0.3)' } },
              { label: 'Export PDF', style: { background: 'rgba(255,107,26,0.12)', color: '#FF4D00', border: '1px solid rgba(255,107,26,0.3)' } },
              { label: 'Download Receipts ZIP', style: { background: 'rgba(41,182,246,0.1)', color: 'var(--color-status-info)', border: '1px solid rgba(41,182,246,0.25)' } },
            ].map((btn) => (
              <button
                key={btn.label}
                className="px-4 py-2 text-xs font-bold uppercase tracking-widest chamfer-4 transition-all hover:brightness-110"
                style={btn.style}
                onClick={() => {
                  if (btn.label === 'Export CSV') {
                    downloadContent(`expense-ledger-${new Date().toISOString().slice(0, 10)}.csv`, exportCsv, 'text/csv;charset=utf-8;');
                    return;
                  }
                  if (btn.label === 'Export PDF') {
                    const printable = JSON.stringify({ summary, entries, categoryBreakdown }, null, 2);
                    downloadContent(`expense-ledger-${new Date().toISOString().slice(0, 10)}.json`, printable, 'application/json;charset=utf-8;');
                    return;
                  }
                  const receiptsOnly = entries.filter((entry) => entry.receipt_attached);
                  downloadContent(`expense-receipts-${new Date().toISOString().slice(0, 10)}.json`, JSON.stringify(receiptsOnly, null, 2), 'application/json;charset=utf-8;');
                }}
              >
                {btn.label}
              </button>
            ))}
            <div className="flex items-center gap-2">
              <span className="px-4 py-2 text-xs font-bold uppercase tracking-widest chamfer-4" style={{ background: 'rgba(255,255,255,0.05)', color: 'rgba(255,255,255,0.65)', border: '1px solid rgba(255,255,255,0.1)' }}>
                QuickBooks: {summary.quickbooks_sync_status}
              </span>
              <Badge label="Accounting" status="info" />
            </div>
          </div>
        </Panel>
      </motion.div>

      {(loading || error) && (
        <Panel>
          <div className="text-xs text-zinc-500">
            {loading ? 'Synchronizing ledger data...' : error}
          </div>
        </Panel>
      )}

      <div className="pt-2">
        <Link href="/founder" className="text-body text-zinc-500 hover:text-[#FF4D00] transition-colors">
          ← Back to Founder OS
        </Link>
      </div>
    </div>
  );
}
