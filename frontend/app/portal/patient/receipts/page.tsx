'use client';

import { useEffect, useState } from 'react';
import Link from 'next/link';
import { getPortalPayments } from '@/services/api';

interface Receipt {
  id: string;
  data?: {
    amount?: number;
    payment_date?: string;
    posted_at?: string;
    method?: string;
    status?: string;
    invoice_id?: string;
    statement_id?: string;
    reference?: string;
    patient_name?: string;
    agency_name?: string;
    confirmation?: string;
  };
}

const METHOD_LABELS: Record<string, string> = {
  card: 'CREDIT / DEBIT CARD',
  ach: 'BANK TRANSFER (ACH)',
  check: 'PAPER CHECK',
  cash: 'CASH',
  payment_plan: 'PAYMENT PLAN',
  insurance: 'INSURANCE',
};

const clip6 = 'polygon(0 0, calc(100% - 6px) 0, 100% 6px, 100% 100%, 0 100%)';
const clip10 = 'polygon(0 0, calc(100% - 10px) 0, 100% 10px, 100% 100%, 0 100%)';

function fmt(cents?: number): string {
  if (cents === undefined || cents === null) return '—';
  return `$${(cents / 100).toFixed(2)}`;
}

function fmtDate(s?: string): string {
  if (!s) return '—';
  return new Date(s).toLocaleDateString('en-US', { year: 'numeric', month: 'short', day: 'numeric' });
}

function StatusChip({ status }: { status?: string }) {
  const map: Record<string, { label: string; bg: string; border: string; color: string }> = {
    posted:   { label: 'POSTED',   bg: 'rgba(16,185,129,0.08)',  border: 'rgba(16,185,129,0.25)',  color: '#10B981' },
    cleared:  { label: 'CLEARED',  bg: 'rgba(16,185,129,0.08)',  border: 'rgba(16,185,129,0.25)',  color: '#10B981' },
    pending:  { label: 'PENDING',  bg: 'rgba(245,158,11,0.08)', border: 'rgba(245,158,11,0.25)', color: '#F59E0B' },
    voided:   { label: 'VOIDED',   bg: 'rgba(239,68,68,0.08)',  border: 'rgba(239,68,68,0.25)',  color: '#EF4444' },
    reversed: { label: 'REVERSED', bg: 'rgba(99,102,241,0.08)', border: 'rgba(99,102,241,0.25)', color: '#818CF8' },
  };
  const s = map[status ?? ''] ?? { label: (status ?? 'UNKNOWN').toUpperCase(), bg: 'rgba(255,255,255,0.04)', border: 'rgba(255,255,255,0.1)', color: '#A1A1AA' };
  return (
    <span className="text-[9px] font-bold tracking-[0.12em] px-2 py-1 border" style={{ background: s.bg, borderColor: s.border, color: s.color, clipPath: clip6 }}>
      {s.label}
    </span>
  );
}

export default function ReceiptsPage() {
  const [receipts, setReceipts] = useState<Receipt[]>([]);
  const [loading, setLoading] = useState(true);
  const [filter, setFilter] = useState<'all' | 'posted' | 'pending'>('all');
  const [fetchError, setFetchError] = useState<string | null>(null);

  useEffect(() => {
    getPortalPayments()
      .then(d => setReceipts(Array.isArray(d) ? d : []))
      .catch((err: unknown) => setFetchError(err instanceof Error ? err.message : 'Failed to load receipts'))
      .finally(() => setLoading(false));
  }, []);

  const filtered = receipts.filter(r => {
    if (filter === 'all') return true;
    return (r.data?.status ?? '') === filter;
  });

  const totalPaid = filtered.reduce((sum, r) => sum + (r.data?.amount ?? 0), 0);

  return (
    <div className="max-w-5xl mx-auto px-4 py-8">
      {/* Header */}
      <div className="mb-8">
        <div className="flex items-center gap-3 mb-1">
          <div className="w-[3px] h-6 bg-[#FF4D00] shadow-[0_0_8px_rgba(255,77,0,0.6)]" />
          <h1 className="text-xl font-black tracking-[0.12em] text-white uppercase">Receipts Center</h1>
        </div>
        <p className="text-sm text-zinc-500 ml-5">Complete record of all payments processed on your account.</p>
      </div>

      {fetchError && (
        <div className="mb-6 px-4 py-3 bg-red-500/8 border border-red-500/20 text-sm text-red-400" style={{ clipPath: clip6 }}>
          Unable to load receipts. Please refresh the page or contact billing support.
        </div>
      )}

      {/* Summary bar */}
      <div className="grid grid-cols-3 gap-4 mb-6">
        {[
          { label: 'Total Receipts', value: filtered.length.toString(), color: 'text-white' },
          { label: 'Total Paid', value: fmt(totalPaid), color: 'text-emerald-400' },
          { label: 'This Year', value: filtered.filter(r => (r.data?.posted_at ?? r.data?.payment_date ?? '').startsWith('2026')).length.toString() + ' payments', color: 'text-zinc-300' },
        ].map(card => (
          <div key={card.label} className="bg-[#0A0A0B] border border-zinc-800 p-4" style={{ clipPath: clip10 }}>
            <div className="text-[9px] font-bold tracking-[0.2em] text-zinc-600 uppercase mb-2">{card.label}</div>
            <div className={`text-lg font-black ${card.color}`}>{card.value}</div>
          </div>
        ))}
      </div>

      {/* Filter + actions bar */}
      <div className="flex items-center justify-between gap-4 mb-4">
        <div className="flex items-center gap-2">
          {(['all', 'posted', 'pending'] as const).map(f => (
            <button
              key={f}
              onClick={() => setFilter(f)}
              className={`px-3 py-1.5 text-[10px] font-bold tracking-widest uppercase border transition-colors ${
                filter === f
                  ? 'bg-[#FF4D00]/10 border-[#FF4D00]/40 text-[#FF4D00]'
                  : 'border-zinc-800 text-zinc-500 hover:border-zinc-600 hover:text-zinc-300 bg-transparent'
              }`}
              style={{ clipPath: clip6 }}
            >
              {f === 'all' ? 'All' : f.charAt(0).toUpperCase() + f.slice(1)}
            </button>
          ))}
        </div>
        <button
          className="flex items-center gap-2 h-8 px-4 border border-zinc-800 text-[10px] font-bold tracking-widest uppercase text-zinc-400 hover:text-zinc-200 hover:border-zinc-600 transition-colors"
          style={{ clipPath: clip6 }}
        >
          <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/><polyline points="7 10 12 15 17 10"/><line x1="12" y1="15" x2="12" y2="3"/></svg>
          Annual Summary
        </button>
      </div>

      {/* Receipts table */}
      <div className="bg-[#0A0A0B] border border-zinc-800 overflow-hidden" style={{ clipPath: clip10 }}>
        <div className="border-b border-zinc-900 px-5 py-3 flex items-center justify-between">
          <span className="text-[10px] font-bold tracking-[0.15em] text-zinc-400 uppercase">Payment Receipts</span>
          <span className="text-[10px] text-zinc-600">{filtered.length} records</span>
        </div>

        {loading ? (
          <div className="py-16 text-center">
            <div className="inline-block w-5 h-5 border-2 border-[#FF4D00] border-t-transparent rounded-full animate-spin mb-3" />
            <p className="text-xs text-zinc-600">Loading receipts...</p>
          </div>
        ) : filtered.length === 0 ? (
          <div className="py-16 text-center">
            <div className="text-2xl mb-3 opacity-20">🧾</div>
            <p className="text-sm text-zinc-500">No receipts found.</p>
            <Link href="/portal/patient/pay" className="mt-4 inline-block text-[10px] font-bold tracking-widest uppercase text-[#FF4D00] hover:underline">
              Make a Payment →
            </Link>
          </div>
        ) : (
          <div>
            {/* Header row */}
            <div className="hidden md:grid grid-cols-6 gap-4 px-5 py-2.5 border-b border-zinc-900 text-[9px] font-bold tracking-[0.2em] text-zinc-600 uppercase">
              <div className="col-span-2">Payment Date</div>
              <div>Method</div>
              <div>Amount</div>
              <div>Status</div>
              <div className="text-right">Actions</div>
            </div>

            {filtered.map((r, i) => {
              const d = r.data ?? {};
              const date = fmtDate(d.posted_at ?? d.payment_date);
              const method = METHOD_LABELS[d.method ?? ''] ?? (d.method ?? 'UNKNOWN').toUpperCase();
              return (
                <div
                  key={r.id}
                  className={`grid grid-cols-1 md:grid-cols-6 gap-4 px-5 py-4 items-center transition-colors hover:bg-zinc-900/30 ${i < filtered.length - 1 ? 'border-b border-zinc-900/50' : ''}`}
                >
                  <div className="col-span-2">
                    <div className="text-sm font-semibold text-zinc-200">{date}</div>
                    <div className="text-[10px] text-zinc-600 mt-0.5 font-mono">
                      REF: {d.confirmation ?? d.reference ?? r.id.slice(-8).toUpperCase()}
                    </div>
                  </div>
                  <div className="text-xs text-zinc-400">{method}</div>
                  <div className="text-sm font-bold text-emerald-400">{fmt(d.amount)}</div>
                  <div><StatusChip status={d.status} /></div>
                  <div className="flex items-center gap-2 md:justify-end">
                    <button
                      className="text-[10px] font-bold tracking-widest uppercase text-zinc-500 hover:text-zinc-200 transition-colors px-2 py-1 border border-zinc-800 hover:border-zinc-600"
                      style={{ clipPath: clip6 }}
                      title="Download receipt"
                    >
                      <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/><polyline points="7 10 12 15 17 10"/><line x1="12" y1="15" x2="12" y2="3"/></svg>
                    </button>
                    <button
                      className="text-[10px] font-bold tracking-widest uppercase text-zinc-500 hover:text-zinc-200 transition-colors px-2 py-1 border border-zinc-800 hover:border-zinc-600"
                      style={{ clipPath: clip6 }}
                      title="Resend receipt by email"
                    >
                      <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><path d="M4 4h16c1.1 0 2 .9 2 2v12c0 1.1-.9 2-2 2H4c-1.1 0-2-.9-2-2V6c0-1.1.9-2 2-2z"/><polyline points="22,6 12,13 2,6"/></svg>
                    </button>
                    {d.invoice_id && (
                      <Link
                        href={`/portal/patient/invoices/${d.invoice_id}`}
                        className="text-[10px] font-bold tracking-widest uppercase text-[#FF4D00]/70 hover:text-[#FF4D00] transition-colors"
                      >
                        VIEW INV
                      </Link>
                    )}
                  </div>
                </div>
              );
            })}
          </div>
        )}
      </div>

      {/* Annual summary CTA */}
      <div className="mt-6 bg-[#FF4D00]/5 border border-[#FF4D00]/15 p-4 flex items-center justify-between" style={{ clipPath: clip10 }}>
        <div>
          <div className="text-[10px] font-bold tracking-widest text-[#FF4D00] uppercase mb-1">Annual Payment Summary</div>
          <p className="text-xs text-zinc-500">Download a complete summary of all payments for tax or insurance purposes.</p>
        </div>
        <button
          className="flex-shrink-0 flex items-center gap-2 h-8 px-4 bg-[#FF4D00]/10 border border-[#FF4D00]/30 text-[#FF4D00] text-[10px] font-bold tracking-widest uppercase hover:bg-[#FF4D00]/20 transition-colors"
          style={{ clipPath: clip6 }}
        >
          Download (2026)
        </button>
      </div>
    </div>
  );
}


