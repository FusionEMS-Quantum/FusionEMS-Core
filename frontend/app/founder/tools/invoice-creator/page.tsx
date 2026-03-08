'use client';
import { motion } from 'framer-motion';
import Link from 'next/link';
import { useState, useEffect } from 'react';

const API = process.env.NEXT_PUBLIC_API_BASE || process.env.NEXT_PUBLIC_API_URL || '';

type InvoiceItem = {
  id: string;
  invoice_number: string;
  client: string;
  total_cents: number;
  invoice_date: string;
  due_date: string;
  status: string;
  reminder_count: number;
};

type InvoiceSummary = {
  invoices_this_month: number;
  total_invoiced_cents: number;
  total_paid_cents: number;
  paid_count: number;
  outstanding_count: number;
};

type InvoiceResponse = {
  summary: InvoiceSummary;
  invoices: InvoiceItem[];
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

export default function InvoiceCreatorPage() {
  const [invoices, setInvoices] = useState<InvoiceItem[]>([]);
  const [summary, setSummary] = useState<InvoiceSummary>({
    invoices_this_month: 0,
    total_invoiced_cents: 0,
    total_paid_cents: 0,
    paid_count: 0,
    outstanding_count: 0,
  });
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [invoiceForm, setInvoiceForm] = useState({
    client: '',
    invoiceDate: new Date().toISOString().split('T')[0],
    dueDate: new Date(Date.now() + 30 * 86400000).toISOString().split('T')[0],
    description: '',
  });
  const [lineItems, setLineItems] = useState([
    { desc: 'Base Platform Fee', amount: 1200 },
    { desc: 'Export Service Fee', amount: 240 },
  ]);
  const [settings, setSettings] = useState({
    company: 'FusionEMS Quantum LLC',
    address: '123 Founder St, Austin, TX 78701',
    terms: 'Net 30',
    lateFee: '1.5% per month after due date',
  });

  const subtotal = lineItems.reduce((s, l) => s + l.amount, 0);

  const authHeaders = () => {
    const token = typeof window !== 'undefined' ? localStorage.getItem('token') : null;
    const headers: Record<string, string> = { 'Content-Type': 'application/json' };
    if (token) {
      headers.Authorization = `Bearer ${token}`;
    }
    return headers;
  };

  const loadInvoices = async () => {
    const res = await fetch(`${API}/api/v1/founder/business/invoices?limit=500`, {
      headers: authHeaders(),
    });
    if (!res.ok) {
      throw new Error(`Failed to load invoices (${res.status})`);
    }
    const payload = (await res.json()) as InvoiceResponse;
    setInvoices(payload.invoices ?? []);
    setSummary(payload.summary ?? summary);
  };

  const loadSettings = async () => {
    const res = await fetch(`${API}/api/v1/founder/business/invoice-settings`, {
      headers: authHeaders(),
    });
    if (!res.ok) {
      return;
    }
    const payload = await res.json();
    setSettings({
      company: payload.company ?? settings.company,
      address: payload.address ?? settings.address,
      terms: payload.terms ?? settings.terms,
      lateFee: payload.lateFee ?? settings.lateFee,
    });
  };

  function addLineItem() {
    setLineItems([...lineItems, { desc: '', amount: 0 }]);
  }

  useEffect(() => {
    Promise.all([loadInvoices(), loadSettings()])
      .catch((e: unknown) => {
        setError(e instanceof Error ? e.message : 'Unable to load invoice data');
      })
      .finally(() => setLoading(false));
  }, []);

  const OUTSTANDING = invoices.filter((inv) => inv.status === 'outstanding' || inv.status === 'overdue');

  const createInvoice = async () => {
    if (!invoiceForm.client.trim()) {
      setError('Client is required before generating an invoice.');
      return;
    }

    const res = await fetch(`${API}/api/v1/founder/business/invoices`, {
      method: 'POST',
      headers: authHeaders(),
      body: JSON.stringify({
        client: invoiceForm.client,
        invoice_date: invoiceForm.invoiceDate,
        due_date: invoiceForm.dueDate,
        description: invoiceForm.description,
        line_items: lineItems.map((item) => ({
          desc: item.desc || 'Line item',
          amount_cents: Math.max(0, Math.round(item.amount * 100)),
        })),
      }),
    });
    if (!res.ok) {
      throw new Error(`Unable to create invoice (${res.status})`);
    }

    setInvoiceForm((prev) => ({ ...prev, client: '', description: '' }));
    await loadInvoices();
  };

  const sendReminder = async (invoiceId: string) => {
    const res = await fetch(`${API}/api/v1/founder/business/invoices/${invoiceId}/send-reminder`, {
      method: 'POST',
      headers: authHeaders(),
      body: JSON.stringify({ channel: 'email' }),
    });
    if (!res.ok) {
      throw new Error(`Reminder failed (${res.status})`);
    }
    await loadInvoices();
  };

  const markPaid = async (invoiceId: string) => {
    const res = await fetch(`${API}/api/v1/founder/business/invoices/${invoiceId}/mark-paid`, {
      method: 'POST',
      headers: authHeaders(),
    });
    if (!res.ok) {
      throw new Error(`Mark-paid failed (${res.status})`);
    }
    await loadInvoices();
  };

  const saveSettings = async () => {
    const res = await fetch(`${API}/api/v1/founder/business/invoice-settings`, {
      method: 'PUT',
      headers: authHeaders(),
      body: JSON.stringify(settings),
    });
    if (!res.ok) {
      throw new Error(`Settings save failed (${res.status})`);
    }
  };

  return (
    <div className="min-h-screen bg-black text-zinc-100 p-6 space-y-6">
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
          Invoice Creator
        </h1>
        <p className="text-xs text-zinc-500 mt-1">Generate professional invoices · track payment status · revenue</p>
      </motion.div>

      <motion.div initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.05 }}>
        <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
          {[
            { label: 'Invoices This Month', value: String(summary.invoices_this_month), status: 'info' as const },
            { label: 'Total Invoiced', value: `$${(summary.total_invoiced_cents / 100).toLocaleString()}`, status: 'info' as const },
            { label: 'Paid', value: String(summary.paid_count), status: 'ok' as const },
            { label: 'Outstanding', value: String(summary.outstanding_count), status: 'warn' as const },
          ].map((s) => (
            <Panel key={s.label} className="flex flex-col gap-1">
              <span className="text-micro text-zinc-500 uppercase tracking-wider">{s.label}</span>
              <span
                className="text-xl font-bold"
                style={{ color: s.status === 'ok' ? 'var(--color-status-active)' : s.status === 'warn' ? 'var(--color-status-warning)' : 'rgba(255,255,255,0.9)' }}
              >
                {s.value}
              </span>
              <Badge label={s.status} status={s.status} />
            </Panel>
          ))}
        </div>
      </motion.div>

      <motion.div initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.1 }}>
        <Panel>
          <SectionHeader number="2" title="Create Invoice" />
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3 mb-4">
            <div className="flex flex-col gap-1">
              <label className="text-micro text-zinc-500 uppercase tracking-wider">Client / Agency</label>
              <input
                type="text"
                value={invoiceForm.client}
                onChange={(e) => setInvoiceForm({ ...invoiceForm, client: e.target.value })}
                placeholder="Agency name"
                className="bg-zinc-950/[0.04] border border-border-DEFAULT text-xs text-zinc-100 px-3 py-2 chamfer-4 outline-none focus:border-orange placeholder:text-zinc-500"
              />
            </div>
            <div className="flex flex-col gap-1">
              <label className="text-micro text-zinc-500 uppercase tracking-wider">Invoice Date</label>
              <input
                type="date"
                value={invoiceForm.invoiceDate}
                onChange={(e) => setInvoiceForm({ ...invoiceForm, invoiceDate: e.target.value })}
                className="bg-zinc-950/[0.04] border border-border-DEFAULT text-xs text-zinc-100 px-3 py-2 chamfer-4 outline-none focus:border-orange"
              />
            </div>
            <div className="flex flex-col gap-1">
              <label className="text-micro text-zinc-500 uppercase tracking-wider">Due Date</label>
              <input
                type="date"
                value={invoiceForm.dueDate}
                onChange={(e) => setInvoiceForm({ ...invoiceForm, dueDate: e.target.value })}
                className="bg-zinc-950/[0.04] border border-border-DEFAULT text-xs text-zinc-100 px-3 py-2 chamfer-4 outline-none focus:border-orange"
              />
            </div>
            <div className="flex flex-col gap-1 md:col-span-2 lg:col-span-3">
              <label className="text-micro text-zinc-500 uppercase tracking-wider">Service Description</label>
              <textarea
                value={invoiceForm.description}
                onChange={(e) => setInvoiceForm({ ...invoiceForm, description: e.target.value })}
                placeholder="Describe services rendered..."
                rows={2}
                className="bg-zinc-950/[0.04] border border-border-DEFAULT text-xs text-zinc-100 px-3 py-2 chamfer-4 outline-none focus:border-orange placeholder:text-zinc-500 resize-none"
              />
            </div>
          </div>

          <div className="mb-3">
            <p className="text-micro text-zinc-500 uppercase tracking-wider mb-2">Line Items</p>
            <div className="space-y-2">
              {lineItems.map((item, i) => (
                <div key={i} className="flex gap-2">
                  <input
                    type="text"
                    value={item.desc}
                    onChange={(e) => {
                      const updated = [...lineItems];
                      updated[i].desc = e.target.value;
                      setLineItems(updated);
                    }}
                    placeholder="Description"
                    className="flex-1 bg-zinc-950/[0.04] border border-border-DEFAULT text-xs text-zinc-100 px-3 py-2 chamfer-4 outline-none focus:border-orange placeholder:text-zinc-500"
                  />
                  <input
                    type="number"
                    value={item.amount}
                    onChange={(e) => {
                      const updated = [...lineItems];
                      updated[i].amount = Number(e.target.value);
                      setLineItems(updated);
                    }}
                    className="w-28 bg-zinc-950/[0.04] border border-border-DEFAULT text-xs text-zinc-100 px-3 py-2 chamfer-4 outline-none focus:border-orange"
                  />
                </div>
              ))}
            </div>
            <button
              onClick={addLineItem}
              className="mt-2 text-micro font-semibold px-3 py-1.5 chamfer-4 transition-all hover:brightness-110"
              style={{ background: 'rgba(41,182,246,0.1)', color: 'var(--color-status-info)', border: '1px solid rgba(41,182,246,0.25)' }}
            >
              + Add Line Item
            </button>
          </div>

          <div className="border-t border-border-subtle pt-3 flex flex-col items-end gap-1 mb-4">
            <div className="flex gap-8 text-xs">
              <span className="text-zinc-500">Subtotal</span>
              <span className="font-mono text-zinc-100">${subtotal.toLocaleString()}</span>
            </div>
            <div className="flex gap-8 text-xs">
              <span className="text-zinc-500">Tax (0%)</span>
              <span className="font-mono text-zinc-100">$0</span>
            </div>
            <div className="flex gap-8 text-sm font-bold border-t border-border-DEFAULT pt-1 mt-1">
              <span className="text-zinc-100">Total</span>
              <span className="font-mono text-[#FF4D00]">${subtotal.toLocaleString()}</span>
            </div>
          </div>

          <button
            className="px-5 py-2 text-xs font-bold uppercase tracking-widest chamfer-4 transition-all hover:brightness-110"
            style={{ background: '#FF4D00', color: '#000' }}
            onClick={() => {
              createInvoice().catch((e: unknown) => {
                setError(e instanceof Error ? e.message : 'Failed to create invoice');
              });
            }}
          >
            Generate Invoice
          </button>
        </Panel>
      </motion.div>

      <motion.div initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.15 }}>
        <Panel>
          <SectionHeader number="3" title="Recent Invoices" />
          <div className="overflow-x-auto">
            <table className="w-full text-xs">
              <thead>
                <tr className="border-b border-border-subtle">
                  {['Invoice #', 'Client', 'Amount', 'Date', 'Due', 'Status'].map((h) => (
                    <th key={h} className="text-left py-1.5 px-2 text-zinc-500 font-semibold uppercase tracking-wider text-micro">
                      {h}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {invoices.length === 0 ? (
                  <tr><td colSpan={6} className="text-center py-4 text-zinc-500">No invoices generated yet.</td></tr>
                ) : (
                  invoices.map((inv) => (
                    <tr key={inv.id} className="border-b border-white/[0.03] hover:bg-zinc-950/[0.02]">
                      <td className="py-2 px-2 font-mono text-brand-orange text-body">{inv.invoice_number || inv.id.slice(0, 8).toUpperCase()}</td>
                      <td className="py-2 px-2 text-zinc-100">{inv.client}</td>
                      <td className="py-2 px-2 font-mono text-zinc-100 font-semibold">${(inv.total_cents / 100).toLocaleString()}</td>
                      <td className="py-2 px-2 text-zinc-500">{inv.invoice_date?.slice(0, 10) || '—'}</td>
                      <td className="py-2 px-2 text-zinc-500">{inv.due_date?.slice(0, 10) || '—'}</td>
                      <td className="py-2 px-2">
                        <Badge
                          label={inv.status}
                          status={inv.status === 'paid' ? 'ok' : inv.status === 'overdue' ? 'error' : 'warn'}
                        />
                      </td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </div>
        </Panel>
      </motion.div>

      <motion.div initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.2 }}>
        <Panel>
          <SectionHeader number="4" title="Payment Tracking" sub="outstanding invoices" />
          <div className="space-y-3">
            {OUTSTANDING.length === 0 && <p className="text-xs text-zinc-500">No outstanding invoices.</p>}
            {OUTSTANDING.map((inv) => (
              <div key={inv.id} className="flex items-center justify-between p-3 chamfer-4" style={{ background: 'rgba(255,152,0,0.06)', border: '1px solid rgba(255,152,0,0.2)' }}>
                <div>
                  <div className="flex items-center gap-2">
                    <span className="text-xs font-semibold text-zinc-100">{inv.invoice_number || inv.id.slice(0, 8).toUpperCase()}</span>
                    <span className="text-micro text-zinc-500">{inv.client}</span>
                  </div>
                  <div className="flex items-center gap-3 mt-0.5">
                    <span className="font-mono text-sm font-bold text-status-warning">${(inv.total_cents / 100).toLocaleString()}</span>
                    <span className="text-micro text-zinc-500">Due {inv.due_date?.slice(0, 10) || '—'}</span>
                    <Badge label="Needs Attention" status="warn" />
                  </div>
                </div>
                <div className="flex items-center gap-2">
                  <button
                    className="text-micro font-bold px-3 py-1.5 chamfer-4 uppercase tracking-wider transition-all hover:brightness-110"
                    style={{ background: 'rgba(255,152,0,0.15)', color: 'var(--q-yellow)', border: '1px solid rgba(255,152,0,0.35)' }}
                    onClick={() => {
                      sendReminder(inv.id).catch((e: unknown) => {
                        setError(e instanceof Error ? e.message : 'Reminder failed');
                      });
                    }}
                  >
                    Send Reminder
                  </button>
                  <button
                    className="text-micro font-bold px-3 py-1.5 chamfer-4 uppercase tracking-wider transition-all hover:brightness-110"
                    style={{ background: 'rgba(76,175,80,0.15)', color: 'var(--q-green)', border: '1px solid rgba(76,175,80,0.35)' }}
                    onClick={() => {
                      markPaid(inv.id).catch((e: unknown) => {
                        setError(e instanceof Error ? e.message : 'Unable to mark paid');
                      });
                    }}
                  >
                    Mark Paid
                  </button>
                </div>
              </div>
            ))}
          </div>
        </Panel>
      </motion.div>

      <motion.div initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.25 }}>
        <Panel>
          <SectionHeader number="5" title="Invoice Settings" />
          <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
            {[
              { label: 'Company Name', key: 'company' as const },
              { label: 'Address', key: 'address' as const },
              { label: 'Payment Terms', key: 'terms' as const },
              { label: 'Late Fee Policy', key: 'lateFee' as const },
            ].map((field) => (
              <div key={field.key} className="flex flex-col gap-1">
                <label className="text-micro text-zinc-500 uppercase tracking-wider">{field.label}</label>
                <input
                  type="text"
                  value={settings[field.key]}
                  onChange={(e) => setSettings({ ...settings, [field.key]: e.target.value })}
                  className="bg-zinc-950/[0.04] border border-border-DEFAULT text-xs text-zinc-100 px-3 py-2 chamfer-4 outline-none focus:border-orange"
                />
              </div>
            ))}
          </div>
          <div className="mt-4">
            <button
              className="px-4 py-2 text-xs font-bold uppercase tracking-widest chamfer-4 transition-all hover:brightness-110"
              style={{ background: '#FF4D00', color: '#000' }}
              onClick={() => {
                saveSettings().catch((e: unknown) => {
                  setError(e instanceof Error ? e.message : 'Failed to save settings');
                });
              }}
            >
              Save Settings
            </button>
          </div>
        </Panel>
      </motion.div>

      {(loading || error) && (
        <Panel>
          <div className="text-xs text-zinc-500">
            {loading ? 'Synchronizing invoices and settings...' : error}
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
