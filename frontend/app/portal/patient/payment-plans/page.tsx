'use client';

import { useEffect, useState } from 'react';
import Link from 'next/link';
import { getPortalPaymentPlans, submitPortalSupportRequest } from '@/services/api';

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
  active:    { label: 'ACTIVE',    bg: 'rgba(16,185,129,0.08)',  border: 'rgba(16,185,129,0.25)',  color: 'var(--color-status-active)' },
  completed: { label: 'COMPLETED', bg: 'rgba(129,140,248,0.08)', border: 'rgba(129,140,248,0.25)', color: '#818CF8' },
  paused:    { label: 'PAUSED',    bg: 'rgba(245,158,11,0.08)',  border: 'rgba(245,158,11,0.25)',  color: 'var(--q-yellow)' },
  defaulted: { label: 'PAST DUE',  bg: 'rgba(239,68,68,0.08)',  border: 'rgba(239,68,68,0.25)',  color: 'var(--color-brand-red)' },
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

function asNumberOrZero(v: unknown): number {
  return typeof v === 'number' && Number.isFinite(v) ? v : 0;
}

function PlanProgressBar({ paid, total }: { paid: number; total: number }) {
  const pct = total > 0 ? Math.min(100, Math.round((paid / total) * 100)) : 0;
  return (
    <div>
      <div className="flex items-center justify-between text-[10px] text-[var(--color-text-muted)] mb-1.5">
        <span>{fmt(paid)} paid</span>
        <span>{pct}% complete</span>
      </div>
      <div className="h-1.5 bg-[var(--color-bg-panel)] relative overflow-hidden" style={{ clipPath: clip6 }}>
        <div
          className="absolute left-0 top-0 h-full bg-[var(--q-orange)] transition-all shadow-[0_0_8px_rgba(255,106,0,0.4)]"
          style={{ width: `${pct}%` }}
        />
      </div>
      <div className="flex items-center justify-between text-[10px] text-[var(--color-text-disabled)] mt-1">
        <span>Balance remaining: {fmt(total - paid)}</span>
        <span>of {fmt(total)}</span>
      </div>
    </div>
  );
}

function InstallmentCalendar({ plan }: { plan: PaymentPlan }) {
  const d = plan.data ?? {};
  const total = asNumberOrZero(d.installments_total);
  const remaining = asNumberOrZero(d.installments_remaining);
  const paid = total - remaining;

  if (!total) return null;
  return (
    <div className="mt-4">
      <div className="text-[9px] font-bold tracking-[0.2em] text-[var(--color-text-muted)] uppercase mb-2">Installment Schedule</div>
      <div className="flex flex-wrap gap-1.5">
        {Array.from({ length: total }).map((_, i) => {
          const isPaid = i < paid;
          const isCurrent = i === paid;
          return (
            <div
              key={i}
              className={`w-7 h-7 flex items-center justify-center text-[9px] font-bold border transition-colors ${
                isPaid
                  ? 'bg-[var(--color-status-active)]/15 border-emerald-500/30 text-[var(--color-status-active)]'
                  : isCurrent
                    ? 'bg-[var(--q-orange)]/15 border-[var(--q-orange)]/40 text-[var(--q-orange)] shadow-[0_0_8px_rgba(255,106,0,0.2)]'
                    : 'bg-[var(--color-bg-panel)]/40 border-[var(--color-border-default)] text-[var(--color-text-disabled)]'
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
  const [fetchError, setFetchError] = useState<string | null>(null);

  useEffect(() => {
    getPortalPaymentPlans()
      .then(d => setPlans(Array.isArray(d) ? d : d.items ?? []))
      .catch((err: unknown) => setFetchError(err instanceof Error ? err.message : 'Failed to load payment plans'))
      .finally(() => setLoading(false));
  }, []);

  const handleRequest = async () => {
    setRequesting(true);
    try {
      await submitPortalSupportRequest({ category: 'payment_plan', subject: 'Payment Plan Request', body: 'Patient requesting a payment plan. Please contact.' });
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
          <div className="w-[3px] h-6 bg-[var(--q-orange)] shadow-[0_0_8px_rgba(255,106,0,0.6)]" />
          <h1 className="text-xl font-black tracking-[0.12em] text-white uppercase">Payment Plans</h1>
        </div>
        <p className="text-sm text-[var(--color-text-muted)] ml-5">Manage your active payment plans and installment schedules.</p>
      </div>

      {fetchError && (
        <div className="mb-6 px-4 py-3 bg-[var(--color-brand-red)]/8 border border-[var(--color-brand-red)]/20 text-sm text-[var(--color-brand-red)]" style={{ clipPath: clip6 }}>
          Unable to load payment plans. Please refresh the page or contact billing support.
        </div>
      )}

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Plans list */}
        <div className="lg:col-span-2 space-y-4">
          {loading ? (
            Array.from({ length: 2 }).map((_, i) => (
              <div key={i} className="bg-[var(--color-bg-panel)] border border-[var(--color-border-subtle)] h-48 animate-pulse" style={{ clipPath: clip10 }} />
            ))
          ) : plans.length === 0 ? (
            <div className="bg-[var(--color-bg-panel)] border border-[var(--color-border-default)] py-12 text-center" style={{ clipPath: clip10 }}>
              <div className="text-2xl mb-3 opacity-20">📋</div>
              <p className="text-sm text-[var(--color-text-muted)] mb-4">No active payment plans found.</p>
              <p className="text-xs text-[var(--color-text-muted)] mb-5">If you&apos;d like to set up a payment plan for your balance, contact billing support.</p>
              <button
                onClick={() => void handleRequest()}
                disabled={requesting || requestSent}
                className="h-8 px-4 bg-[var(--q-orange)]/10 border border-[var(--q-orange)]/30 text-[var(--q-orange)] text-[10px] font-bold tracking-widest uppercase hover:bg-[var(--q-orange)]/20 transition-colors disabled:opacity-50"
                style={{ clipPath: clip6 }}
              >
                {requestSent ? '✓ Request Sent' : requesting ? 'Sending...' : 'Request a Payment Plan'}
              </button>
            </div>
          ) : (
            plans.map(plan => {
              const d = plan.data ?? {};
              const statusCfg = STATUS_MAP[d.status ?? ''] ?? STATUS_MAP.paused;
              const paid = asNumberOrZero(d.amount_paid_cents);
              const total = asNumberOrZero(d.total_balance_cents);
              return (
                <div key={plan.id} className="bg-[var(--color-bg-panel)] border border-[var(--color-border-default)]" style={{ clipPath: clip10 }}>
                  {/* Plan header */}
                  <div className="flex items-start justify-between px-5 py-4 border-b border-[var(--color-border-subtle)]">
                    <div>
                      <div className="text-sm font-bold text-[var(--color-text-primary)] mb-1">
                        Payment Plan &nbsp;
                        <span className="text-[var(--color-text-muted)] font-mono text-xs">#{plan.id.slice(-8).toUpperCase()}</span>
                      </div>
                      <div className="flex items-center gap-3 text-xs text-[var(--color-text-muted)]">
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
                          <div className="text-[9px] font-bold tracking-[0.15em] text-[var(--color-text-muted)] uppercase mb-1">{s.label}</div>
                          <div className="text-sm font-bold text-[var(--color-text-primary)]">{s.value}</div>
                        </div>
                      ))}
                    </div>

                    {/* Progress */}
                    <PlanProgressBar paid={paid} total={total} />

                    {/* Installment calendar */}
                    <InstallmentCalendar plan={plan} />

                    {/* Actions */}
                    <div className="mt-4 pt-4 border-t border-[var(--color-border-subtle)] flex items-center gap-3">
                      {d.status === 'active' && (
                        <Link
                          href="/portal/patient/pay"
                          className="flex items-center gap-2 h-8 px-4 bg-[var(--q-orange)] text-black text-[10px] font-black tracking-widest uppercase hover:bg-[#E64500] transition-colors"
                          style={{ clipPath: clip6 }}
                        >
                          Make a Payment
                        </Link>
                      )}
                      <Link
                        href="/portal/patient/support"
                        className="text-[10px] font-bold tracking-widest uppercase text-[var(--color-text-muted)] hover:text-[var(--color-text-secondary)] transition-colors"
                      >
                        Request Change →
                      </Link>
                      {d.invoice_id && (
                        <Link
                          href={`/portal/patient/invoices/${d.invoice_id}`}
                          className="text-[10px] font-bold tracking-widest uppercase text-[var(--color-text-muted)] hover:text-[var(--color-text-secondary)] transition-colors ml-auto"
                        >
                          View Invoice →
                        </Link>
                      )}
                    </div>
                  </div>

                  {/* Past due warning */}
                  {d.status === 'defaulted' && (
                    <div className="mx-5 mb-4 px-4 py-3 bg-[var(--color-brand-red)]/8 border border-[var(--color-brand-red)]/20" style={{ clipPath: clip6 }}>
                      <p className="text-xs text-[var(--color-brand-red)]">
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
                <span className="text-[10px] font-bold tracking-widest uppercase text-[var(--color-status-active)]">✓ Request Submitted</span>
              ) : (
                <button
                  onClick={() => void handleRequest()}
                  disabled={requesting}
                  className="text-[10px] font-bold tracking-widest uppercase text-[var(--color-text-muted)] hover:text-[var(--color-text-secondary)] transition-colors border border-[var(--color-border-default)] hover:border-[var(--color-border-strong)] px-3 py-1.5"
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
          <div className="bg-[var(--color-bg-panel)] border border-[var(--color-border-default)]" style={{ clipPath: clip10 }}>
            <div className="px-4 py-3 border-b border-[var(--color-border-subtle)]">
              <span className="text-[10px] font-bold tracking-[0.15em] text-[var(--color-text-secondary)] uppercase">Plan Simulator</span>
            </div>
            <div className="p-4 space-y-4">
              <div>
                <label className="block text-[9px] font-bold tracking-widest text-[var(--color-text-muted)] uppercase mb-1.5">Balance Amount ($)</label>
                <input
                  type="number"
                  min="0"
                  step="10"
                  value={simulatorBalance}
                  onChange={e => setSimulatorBalance(e.target.value)}
                  className="w-full bg-[var(--color-bg-panel)] border border-[var(--color-border-default)] text-[var(--color-text-primary)] text-sm px-3 py-2 outline-none focus:border-[var(--q-orange)]/40 transition-colors"
                  style={{ clipPath: clip6 }}
                />
              </div>
              <div>
                <label className="block text-[9px] font-bold tracking-widest text-[var(--color-text-muted)] uppercase mb-1.5">Number of Months</label>
                <select
                  value={simulatorMonths}
                  onChange={e => setSimulatorMonths(e.target.value)}
                  className="w-full bg-[var(--color-bg-panel)] border border-[var(--color-border-default)] text-[var(--color-text-primary)] text-sm px-3 py-2 outline-none focus:border-[var(--q-orange)]/40 transition-colors"
                  style={{ clipPath: clip6 }}
                >
                  {[3, 6, 9, 12, 18, 24].map(m => <option key={m} value={m}>{m} months</option>)}
                </select>
              </div>
              <div className="border-t border-[var(--color-border-subtle)] pt-3 space-y-2">
                <div className="flex items-center justify-between text-xs">
                  <span className="text-[var(--color-text-muted)]">Monthly payment</span>
                  <span className="font-bold text-[var(--q-orange)]">{fmt(installmentCents)}/mo</span>
                </div>
                <div className="flex items-center justify-between text-xs">
                  <span className="text-[var(--color-text-muted)]">Total installments</span>
                  <span className="text-[var(--color-text-secondary)]">{months}</span>
                </div>
                <div className="flex items-center justify-between text-xs">
                  <span className="text-[var(--color-text-muted)]">Total paid</span>
                  <span className="text-[var(--color-text-secondary)]">{fmt(installmentCents * months)}</span>
                </div>
              </div>
              <p className="text-[9px] text-[var(--color-text-disabled)]">Estimate only. Actual plan terms are set by billing staff.</p>
              <button
                onClick={() => void handleRequest()}
                disabled={requesting || requestSent}
                className="w-full h-8 bg-[var(--q-orange)]/10 border border-[var(--q-orange)]/25 text-[var(--q-orange)] text-[10px] font-bold tracking-widest uppercase hover:bg-[var(--q-orange)]/20 transition-colors disabled:opacity-50"
                style={{ clipPath: clip6 }}
              >
                {requestSent ? '✓ Sent' : 'Request This Plan'}
              </button>
            </div>
          </div>

          {/* Quick links */}
          <div className="bg-[var(--color-bg-panel)] border border-[var(--color-border-default)] p-4" style={{ clipPath: clip10 }}>
            <div className="text-[9px] font-bold tracking-widest text-[var(--color-text-muted)] uppercase mb-3">Quick Actions</div>
            <div className="space-y-2">
              {[
                { label: 'Make a Payment', href: '/portal/patient/pay' },
                { label: 'View Invoices',  href: '/portal/patient/invoices' },
                { label: 'Billing Help',   href: '/portal/patient/support' },
              ].map(l => (
                <Link
                  key={l.href}
                  href={l.href}
                  className="flex items-center justify-between text-xs text-[var(--color-text-muted)] hover:text-[var(--color-text-secondary)] transition-colors py-1.5 border-b border-[var(--color-border-subtle)]/50 last:border-0"
                >
                  {l.label}
                  <span className="text-[var(--color-text-disabled)]">→</span>
                </Link>
              ))}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}


