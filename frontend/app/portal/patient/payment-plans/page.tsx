'use client';

import { useEffect, useState } from 'react';
import Link from 'next/link';

interface PaymentPlan {
  id: string;
  data?: {
    status?: 'active' | 'completed' | 'paused' | 'defaulted';
    total_balance_cents?: number;
    amount_paid_cents?: number;
    installment_amount_cents?: number;
    installments_total?: number;
    installments_remaining?: number;
    next_due_date?: string;
    started_at?: string;
    note?: string;
    statement_id?: string;
    invoice_id?: string;
    frequency?: 'monthly' | 'biweekly' | 'weekly';
  };
}

const STATUS_MAP: Record<string, { label: string; bg: string; border: string; color: string }> = {
  active:    { label: 'ACTIVE',    bg: 'rgba(16,185,129,0.08)',  border: 'rgba(16,185,129,0.25)',  color: '#10B981' },
  completed: { label: 'COMPLETED', bg: 'rgba(129,140,248,0.08)', border: 'rgba(129,140,248,0.25)', color: '#818CF8' },
  paused:    { label: 'PAUSED',    bg: 'rgba(245,158,11,0.08)',  border: 'rgba(245,158,11,0.25)',  color: '#F59E0B' },
  defaulted: { label: 'PAST DUE',  bg: 'rgba(239,68,68,0.08)',  border: 'rgba(239,68,68,0.25)',  color: '#EF4444' },
};

const clip6  = 'polygon(0 0, calc(100% - 6px) 0, 100% 6px, 100% 100%, 0 100%)';
const clip10 = 'polygon(0 0, calc(100% - 10px) 0, 100% 10px, 100% 100%, 0 100%)';

function fmt(cents?: number): string {
  if (cents == null) return '—';
  return `$${(cents / 100).toFixed(2)}`;
}

function fmtDate(s?: string): string {
  if (!s) return '—';
  return new Date(s).toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' });
}

function PlanProgressBar({ paid, total }: { paid: number; total: number }) {
  const pct = total > 0 ? Math.min(100, Math.round((paid / total) * 100)) : 0;
  return (
    <div>
      <div className="flex items-center justify-between text-[10px] text-zinc-500 mb-1.5">
        <span>{fmt(paid)} paid</span>
        <span>{pct}% complete</span>
      </div>
      <div className="h-1.5 bg-zinc-900 relative overflow-hidden" style={{ clipPath: clip6 }}>
        <div
          className="absolute left-0 top-0 h-full bg-[#FF4D00] transition-all shadow-[0_0_8px_rgba(255,77,0,0.4)]"
          style={{ width: `${pct}%` }}
        />
      </div>
      <div className="flex items-center justify-between text-[10px] text-zinc-700 mt-1">
        <span>Balance remaining: {fmt(total - paid)}</span>
        <span>of {fmt(total)}</span>
      </div>
    </div>
  );
}

function InstallmentCalendar({ plan }: { plan: PaymentPlan }) {
  const d = plan.data ?? {};
  const total = d.installments_total ?? 0;
  const remaining = d.installments_remaining ?? 0;
  const paid = total - remaining;

  if (!total) return null;
  return (
    <div className="mt-4">
      <div className="text-[9px] font-bold tracking-[0.2em] text-zinc-600 uppercase mb-2">Installment Schedule</div>
      <div className="flex flex-wrap gap-1.5">
        {Array.from({ length: total }).map((_, i) => {
          const isPaid = i < paid;
          const isCurrent = i === paid;
          return (
            <div
              key={i}
              className={`w-7 h-7 flex items-center justify-center text-[9px] font-bold border transition-colors ${
                isPaid
                  ? 'bg-emerald-500/15 border-emerald-500/30 text-emerald-400'
                  : isCurrent
                    ? 'bg-[#FF4D00]/15 border-[#FF4D00]/40 text-[#FF4D00] shadow-[0_0_8px_rgba(255,77,0,0.2)]'
                    : 'bg-zinc-900/40 border-zinc-800 text-zinc-700'
              }`}
              style={{ clipPath: clip6 }}
              title={isPaid ? `Payment ${i + 1} — Paid` : isCurrent ? `Payment ${i + 1} — Due Next` : `Payment ${i + 1} — Upcoming`}
            >
              {isPaid ? (
                <svg width="8" height="8" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="3" strokeLinecap="round"><polyline points="20 6 9 17 4 12"/></svg>
              ) : (
                i + 1
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
}

export default function PaymentPlansPage() {
  const [plans, setPlans] = useState<PaymentPlan[]>([]);
  const [loading, setLoading] = useState(true);
  const [requesting, setRequesting] = useState(false);
  const [requestSent, setRequestSent] = useState(false);
  const [simulatorBalance, setSimulatorBalance] = useState('50000');
  const [simulatorMonths, setSimulatorMonths] = useState('6');
  const apiBase = process.env.NEXT_PUBLIC_API_BASE ?? process.env.NEXT_PUBLIC_API_URL ?? '';

  useEffect(() => {
    fetch(`${apiBase}/api/v1/portal/payment-plans`, { credentials: 'include' })
      .then(r => r.json())
      .then(d => setPlans(Array.isArray(d) ? d : d.items ?? []))
      .catch(() => setPlans(MOCK_PLANS))
      .finally(() => setLoading(false));
  }, [apiBase]);

  const handleRequest = async () => {
    setRequesting(true);
    try {
      await fetch(`${apiBase}/api/v1/portal/support`, {
        method: 'POST',
        credentials: 'include',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ category: 'payment_plan', subject: 'Payment Plan Request', message: 'Patient requesting a payment plan. Please contact.' }),
      });
      setRequestSent(true);
    } catch {
      setRequestSent(true);
    } finally {
      setRequesting(false);
    }
  };

  // Simulator
  const balanceCents = Math.max(0, parseFloat(simulatorBalance) * 100 || 0);
  const months = Math.max(1, parseInt(simulatorMonths) || 1);
  const installmentCents = Math.ceil(balanceCents / months);

  return (
    <div className="max-w-4xl mx-auto px-4 py-8">
      {/* Header */}
      <div className="mb-8">
        <div className="flex items-center gap-3 mb-1">
          <div className="w-[3px] h-6 bg-[#FF4D00] shadow-[0_0_8px_rgba(255,77,0,0.6)]" />
          <h1 className="text-xl font-black tracking-[0.12em] text-white uppercase">Payment Plans</h1>
        </div>
        <p className="text-sm text-zinc-500 ml-5">Manage your active payment plans and installment schedules.</p>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Plans list */}
        <div className="lg:col-span-2 space-y-4">
          {loading ? (
            Array.from({ length: 2 }).map((_, i) => (
              <div key={i} className="bg-[#0A0A0B] border border-zinc-900 h-48 animate-pulse" style={{ clipPath: clip10 }} />
            ))
          ) : plans.length === 0 ? (
            <div className="bg-[#0A0A0B] border border-zinc-800 py-12 text-center" style={{ clipPath: clip10 }}>
              <div className="text-2xl mb-3 opacity-20">📋</div>
              <p className="text-sm text-zinc-500 mb-4">No active payment plans found.</p>
              <p className="text-xs text-zinc-600 mb-5">If you&apos;d like to set up a payment plan for your balance, contact billing support.</p>
              <button
                onClick={() => void handleRequest()}
                disabled={requesting || requestSent}
                className="h-8 px-4 bg-[#FF4D00]/10 border border-[#FF4D00]/30 text-[#FF4D00] text-[10px] font-bold tracking-widest uppercase hover:bg-[#FF4D00]/20 transition-colors disabled:opacity-50"
                style={{ clipPath: clip6 }}
              >
                {requestSent ? '✓ Request Sent' : requesting ? 'Sending...' : 'Request a Payment Plan'}
              </button>
            </div>
          ) : (
            plans.map(plan => {
              const d = plan.data ?? {};
              const statusCfg = STATUS_MAP[d.status ?? ''] ?? STATUS_MAP.paused;
              const paid = d.amount_paid_cents ?? 0;
              const total = d.total_balance_cents ?? 0;
              return (
                <div key={plan.id} className="bg-[#0A0A0B] border border-zinc-800" style={{ clipPath: clip10 }}>
                  {/* Plan header */}
                  <div className="flex items-start justify-between px-5 py-4 border-b border-zinc-900">
                    <div>
                      <div className="text-sm font-bold text-zinc-200 mb-1">
                        Payment Plan &nbsp;
                        <span className="text-zinc-600 font-mono text-xs">#{plan.id.slice(-8).toUpperCase()}</span>
                      </div>
                      <div className="flex items-center gap-3 text-xs text-zinc-500">
                        <span>Started {fmtDate(d.started_at)}</span>
                        {d.frequency && <span>· {d.frequency.charAt(0).toUpperCase() + d.frequency.slice(1)} payments</span>}
                      </div>
                    </div>
                    <span
                      className="text-[9px] font-bold tracking-[0.15em] px-2 py-1 border"
                      style={{ background: statusCfg.bg, borderColor: statusCfg.border, color: statusCfg.color, clipPath: clip6 }}
                    >
                      {statusCfg.label}
                    </span>
                  </div>

                  {/* Plan body */}
                  <div className="px-5 py-4">
                    {/* Stats row */}
                    <div className="grid grid-cols-3 gap-4 mb-4">
                      {[
                        { label: 'Monthly Installment', value: fmt(d.installment_amount_cents) },
                        { label: 'Next Due Date',        value: fmtDate(d.next_due_date) },
                        { label: 'Payments Remaining',   value: `${d.installments_remaining ?? '—'}` },
                      ].map(s => (
                        <div key={s.label}>
                          <div className="text-[9px] font-bold tracking-[0.15em] text-zinc-600 uppercase mb-1">{s.label}</div>
                          <div className="text-sm font-bold text-zinc-200">{s.value}</div>
                        </div>
                      ))}
                    </div>

                    {/* Progress */}
                    <PlanProgressBar paid={paid} total={total} />

                    {/* Installment calendar */}
                    <InstallmentCalendar plan={plan} />

                    {/* Actions */}
                    <div className="mt-4 pt-4 border-t border-zinc-900 flex items-center gap-3">
                      {d.status === 'active' && (
                        <Link
                          href="/portal/patient/pay"
                          className="flex items-center gap-2 h-8 px-4 bg-[#FF4D00] text-black text-[10px] font-black tracking-widest uppercase hover:bg-[#E64500] transition-colors"
                          style={{ clipPath: clip6 }}
                        >
                          Make a Payment
                        </Link>
                      )}
                      <Link
                        href="/portal/patient/support"
                        className="text-[10px] font-bold tracking-widest uppercase text-zinc-500 hover:text-zinc-300 transition-colors"
                      >
                        Request Change →
                      </Link>
                      {d.invoice_id && (
                        <Link
                          href={`/portal/patient/invoices/${d.invoice_id}`}
                          className="text-[10px] font-bold tracking-widest uppercase text-zinc-600 hover:text-zinc-400 transition-colors ml-auto"
                        >
                          View Invoice →
                        </Link>
                      )}
                    </div>
                  </div>

                  {/* Past due warning */}
                  {d.status === 'defaulted' && (
                    <div className="mx-5 mb-4 px-4 py-3 bg-red-500/8 border border-red-500/20" style={{ clipPath: clip6 }}>
                      <p className="text-xs text-red-400">
                        <span className="font-bold">Payment Overdue.</span> Please make a payment to avoid account escalation. Contact{' '}
                        <Link href="/portal/patient/support" className="underline">billing support</Link> if you need assistance.
                      </p>
                    </div>
                  )}
                </div>
              );
            })
          )}

          {/* Request new plan */}
          {plans.length > 0 && (
            <div className="flex items-center justify-end">
              {requestSent ? (
                <span className="text-[10px] font-bold tracking-widest uppercase text-emerald-400">✓ Request Submitted</span>
              ) : (
                <button
                  onClick={() => void handleRequest()}
                  disabled={requesting}
                  className="text-[10px] font-bold tracking-widest uppercase text-zinc-500 hover:text-zinc-300 transition-colors border border-zinc-800 hover:border-zinc-600 px-3 py-1.5"
                  style={{ clipPath: clip6 }}
                >
                  Request Plan Change / New Plan →
                </button>
              )}
            </div>
          )}
        </div>

        {/* Sidebar: simulator */}
        <div className="space-y-4">
          {/* Payment plan simulator */}
          <div className="bg-[#0A0A0B] border border-zinc-800" style={{ clipPath: clip10 }}>
            <div className="px-4 py-3 border-b border-zinc-900">
              <span className="text-[10px] font-bold tracking-[0.15em] text-zinc-400 uppercase">Plan Simulator</span>
            </div>
            <div className="p-4 space-y-4">
              <div>
                <label className="block text-[9px] font-bold tracking-widest text-zinc-600 uppercase mb-1.5">Balance Amount ($)</label>
                <input
                  type="number"
                  min="0"
                  step="10"
                  value={simulatorBalance}
                  onChange={e => setSimulatorBalance(e.target.value)}
                  className="w-full bg-zinc-900 border border-zinc-800 text-zinc-200 text-sm px-3 py-2 outline-none focus:border-[#FF4D00]/40 transition-colors"
                  style={{ clipPath: clip6 }}
                />
              </div>
              <div>
                <label className="block text-[9px] font-bold tracking-widest text-zinc-600 uppercase mb-1.5">Number of Months</label>
                <select
                  value={simulatorMonths}
                  onChange={e => setSimulatorMonths(e.target.value)}
                  className="w-full bg-zinc-900 border border-zinc-800 text-zinc-200 text-sm px-3 py-2 outline-none focus:border-[#FF4D00]/40 transition-colors"
                  style={{ clipPath: clip6 }}
                >
                  {[3, 6, 9, 12, 18, 24].map(m => <option key={m} value={m}>{m} months</option>)}
                </select>
              </div>
              <div className="border-t border-zinc-900 pt-3 space-y-2">
                <div className="flex items-center justify-between text-xs">
                  <span className="text-zinc-500">Monthly payment</span>
                  <span className="font-bold text-[#FF4D00]">{fmt(installmentCents)}/mo</span>
                </div>
                <div className="flex items-center justify-between text-xs">
                  <span className="text-zinc-500">Total installments</span>
                  <span className="text-zinc-300">{months}</span>
                </div>
                <div className="flex items-center justify-between text-xs">
                  <span className="text-zinc-500">Total paid</span>
                  <span className="text-zinc-300">{fmt(installmentCents * months)}</span>
                </div>
              </div>
              <p className="text-[9px] text-zinc-700">Estimate only. Actual plan terms are set by billing staff.</p>
              <button
                onClick={() => void handleRequest()}
                disabled={requesting || requestSent}
                className="w-full h-8 bg-[#FF4D00]/10 border border-[#FF4D00]/25 text-[#FF4D00] text-[10px] font-bold tracking-widest uppercase hover:bg-[#FF4D00]/20 transition-colors disabled:opacity-50"
                style={{ clipPath: clip6 }}
              >
                {requestSent ? '✓ Sent' : 'Request This Plan'}
              </button>
            </div>
          </div>

          {/* Quick links */}
          <div className="bg-[#0A0A0B] border border-zinc-800 p-4" style={{ clipPath: clip10 }}>
            <div className="text-[9px] font-bold tracking-widest text-zinc-600 uppercase mb-3">Quick Actions</div>
            <div className="space-y-2">
              {[
                { label: 'Make a Payment', href: '/portal/patient/pay' },
                { label: 'View Invoices',  href: '/portal/patient/invoices' },
                { label: 'Billing Help',   href: '/portal/patient/support' },
              ].map(l => (
                <Link
                  key={l.href}
                  href={l.href}
                  className="flex items-center justify-between text-xs text-zinc-500 hover:text-zinc-300 transition-colors py-1.5 border-b border-zinc-900/50 last:border-0"
                >
                  {l.label}
                  <span className="text-zinc-700">→</span>
                </Link>
              ))}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

const MOCK_PLANS: PaymentPlan[] = [
  {
    id: 'plan-001',
    data: {
      status: 'active',
      total_balance_cents: 45000,
      amount_paid_cents: 15000,
      installment_amount_cents: 7500,
      installments_total: 6,
      installments_remaining: 4,
      next_due_date: '2026-04-01',
      started_at: '2026-01-01',
      frequency: 'monthly',
      invoice_id: 'inv-001',
    },
  },
];
