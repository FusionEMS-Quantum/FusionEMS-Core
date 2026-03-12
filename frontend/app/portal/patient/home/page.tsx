'use client';

import { useEffect, useState } from 'react';
import Link from 'next/link';
import { getPortalStatements, getPortalPayments } from '@/services/api';

interface SummaryData {
  total_balance: number;
  payment_count: number;
  statement_count: number;
  total_paid: number;
}

interface Statement {
  id: string;
  data?: { amount_due_cents?: number; status?: string; incident_date?: string; service_type?: string };
}

interface Payment {
  id: string;
  data?: { amount?: number; posted_at?: string; method?: string; status?: string };
}

function fmt(cents: number) {
  return `$${(cents / 100).toFixed(2)}`;
}

function asNumberOrUndefined(v: unknown): number | undefined {
  return typeof v === 'number' && Number.isFinite(v) ? v : undefined;
}

function asNumberOrZero(v: unknown): number {
  return asNumberOrUndefined(v) ?? 0;
}

function fmtOrDash(cents?: number): string {
  return typeof cents === 'number' && Number.isFinite(cents) ? fmt(cents) : '—';
}

function StatusChip({ status }: { status?: string }) {
  const s = status ?? 'pending';
  const color = s === 'paid' ? 'var(--color-status-active)' : s === 'overdue' ? 'var(--color-brand-red)' : 'var(--q-yellow)';
  return (
    <span
      className="text-micro font-label uppercase tracking-wider px-2 py-0.5 chamfer-4"
      style={{ color, backgroundColor: `color-mix(in srgb, ${color} 12%, transparent)` }}
    >
      {s.toUpperCase()}
    </span>
  );
}

export default function PatientHomeDashboard() {
  const [summary, setSummary] = useState<SummaryData | null>(null);
  const [statements, setStatements] = useState<Statement[]>([]);
  const [payments, setPayments] = useState<Payment[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    async function load() {
      try {
        const [stmts, pays] = await Promise.all([
          getPortalStatements(),
          getPortalPayments(),
        ]) as [Statement[], Payment[]];
        setStatements(stmts);
        setPayments(pays);
        const totalBalance = stmts.reduce((acc, s) => acc + asNumberOrZero(s.data?.amount_due_cents), 0);
        const totalPaid = pays.reduce((acc, p) => acc + (asNumberOrZero(p.data?.amount) * 100), 0);
        setSummary({ total_balance: totalBalance, payment_count: pays.length, statement_count: stmts.length, total_paid: totalPaid });
      } catch {
        // Non-fatal — render with empty state
      } finally {
        setLoading(false);
      }
    }
    void load();
  }, []);

  const hasBalance = (summary?.total_balance ?? 0) > 0;

  return (
    <div className="min-h-screen bg-[var(--color-bg-base)] text-[var(--color-text-primary)] font-sans relative">
      {/* Top bar */}
      <div className="bg-[var(--color-bg-surface)] border-b border-[var(--color-border-default)] px-6 h-14 flex items-center justify-between sticky top-0 z-10">
        <div className="flex items-center gap-3">
          <svg width="28" height="28" viewBox="0 0 36 36" fill="none">
            <polygon points="18,2 33,10 33,26 18,34 3,26 3,10" fill="var(--q-orange)" />
            <text x="18" y="23" textAnchor="middle" fill="var(--color-bg-base)" fontSize="10" fontWeight="900" fontFamily="sans-serif">FQ</text>
          </svg>
          <div className="flex items-center gap-2.5">
            <span className="text-micro font-label font-black tracking-wider uppercase">FUSION<span className="text-[var(--q-orange)]">EMS</span></span>
            <span className="text-micro text-[var(--color-text-muted)] tracking-wider uppercase ml-2">MY ACCOUNT</span>
          </div>
        </div>
        <div className="flex gap-3 items-center">
          <Link href="/portal/patient/notifications" className="text-micro text-[var(--color-text-muted)] no-underline tracking-wider uppercase hover:text-[var(--color-text-primary)] transition-colors">Notifications</Link>
          <Link href="/portal/patient" className="text-micro text-[var(--color-text-muted)] no-underline tracking-wider uppercase hover:text-[var(--color-text-primary)] transition-colors">&larr; Portal Home</Link>
        </div>
      </div>

      <div className="max-w-[1200px] mx-auto px-6 py-8">
        {/* Page heading */}
        <div className="mb-7">
          <div className="text-micro font-label font-bold tracking-wider uppercase text-[var(--color-text-muted)] mb-1.5">ACCOUNT OVERVIEW</div>
          <h1 className="text-h1 font-black text-[var(--color-text-primary)] m-0">My Billing Account</h1>
        </div>

        {/* Alert if balance due */}
        {!loading && hasBalance && (
          <div className="bg-[var(--color-brand-orange-ghost)] border border-[color-mix(in_srgb,var(--q-orange)_20%,transparent)] chamfer-8 p-5 mb-6 flex items-center justify-between gap-4 flex-wrap">
            <div>
              <div className="text-micro font-label font-bold text-[var(--q-orange)] tracking-wider uppercase mb-1">Balance Due</div>
              <div className="text-h2 font-black text-[var(--color-text-primary)]">{fmtOrDash(summary?.total_balance)}</div>
            </div>
            <Link href="/portal/patient/pay" className="quantum-btn-primary px-6 py-2.5 no-underline whitespace-nowrap">
              Pay Now &rarr;
            </Link>
          </div>
        )}

        {/* Stats row */}
        <div className="grid grid-cols-[repeat(auto-fit,minmax(220px,1fr))] gap-4 mb-8">
          <div className="bg-[var(--color-bg-surface)] border border-[var(--color-border-default)] chamfer-8 p-5">
            <div className="text-micro font-label font-bold tracking-wider uppercase text-[var(--color-text-muted)] mb-2">Current Balance</div>
            <div className={`text-h1 font-black leading-none ${hasBalance ? 'text-[var(--q-orange)]' : 'text-[var(--color-status-active)]'}`}>
              {loading ? '—' : fmtOrDash(summary?.total_balance)}
            </div>
            <div className="text-micro text-[var(--color-text-muted)] mt-1.5">{hasBalance ? 'Amount due now' : 'Account is current'}</div>
          </div>
          <div className="bg-[var(--color-bg-surface)] border border-[var(--color-border-default)] chamfer-8 p-5">
            <div className="text-micro font-label font-bold tracking-wider uppercase text-[var(--color-text-muted)] mb-2">Total Paid</div>
            <div className="text-h1 font-black text-[var(--color-text-primary)] leading-none">{loading ? '—' : fmtOrDash(summary?.total_paid)}</div>
            <div className="text-micro text-[var(--color-text-muted)] mt-1.5">{typeof summary?.payment_count === 'number' ? summary.payment_count : '—'} payment{(summary?.payment_count ?? 0) !== 1 ? 's' : ''} on record</div>
          </div>
          <div className="bg-[var(--color-bg-surface)] border border-[var(--color-border-default)] chamfer-8 p-5">
            <div className="text-micro font-label font-bold tracking-wider uppercase text-[var(--color-text-muted)] mb-2">Statements</div>
            <div className="text-h1 font-black text-[var(--color-text-primary)] leading-none">{loading ? '—' : (typeof summary?.statement_count === 'number' ? summary.statement_count : '—')}</div>
            <div className="text-micro text-[var(--color-text-muted)] mt-1.5">Total statements on file</div>
          </div>
          <div className="bg-[var(--color-brand-orange-ghost)] border border-[color-mix(in_srgb,var(--q-orange)_15%,transparent)] chamfer-8 p-5">
            <div className="text-micro font-label font-bold tracking-wider uppercase text-[var(--color-text-muted)] mb-2">Quick Actions</div>
            <div className="flex flex-col gap-2 mt-2">
              <Link href="/portal/patient/pay" className="text-[var(--q-orange)] text-body font-bold no-underline hover:underline">&rarr; Pay My Bill</Link>
              <Link href="/portal/patient/support" className="text-[var(--color-text-muted)] text-body no-underline hover:text-[var(--color-text-primary)]">&rarr; Get Billing Help</Link>
              <Link href="/portal/patient/payment-plans" className="text-[var(--color-text-muted)] text-body no-underline hover:text-[var(--color-text-primary)]">&rarr; Set Up Payment Plan</Link>
            </div>
          </div>
        </div>

        {/* Main 2-col layout */}
        <div className="grid grid-cols-1 lg:grid-cols-[1fr_340px] gap-6 items-start">
          <div>
            {/* Recent statements */}
            <div className="bg-[var(--color-bg-surface)] border border-[var(--color-border-default)] chamfer-12 overflow-hidden mb-5">
              <div className="px-5 py-4 border-b border-[var(--color-border-default)] flex items-center justify-between">
                <span className="label-caps">Recent Statements</span>
                <Link href="/portal/patient/invoices" className="text-micro font-label font-semibold text-[var(--q-orange)] no-underline tracking-wider uppercase hover:underline">View All &rarr;</Link>
              </div>
              {loading ? (
                <div className="p-6 text-body text-[var(--color-text-muted)]">Loading&hellip;</div>
              ) : statements.length === 0 ? (
                <div className="p-6 text-body text-[var(--color-text-muted)]">No statements found.</div>
              ) : statements.slice(0, 4).map((s) => {
                const dueCents = asNumberOrUndefined(s.data?.amount_due_cents);
                const dueForCompare = dueCents ?? 0;
                return (
                  <Link key={s.id} href={`/portal/patient/invoices?id=${s.id}`} className="flex items-center justify-between gap-3 px-5 py-3.5 border-b border-[var(--color-border-subtle)] no-underline text-inherit hover:bg-[var(--color-bg-overlay)] transition-colors">
                    <div>
                      <div className="text-body font-medium text-[var(--color-text-primary)]">Statement #{s.id.slice(-8).toUpperCase()}</div>
                      <div className="text-micro text-[var(--color-text-muted)] mt-0.5">{s.data?.incident_date ?? 'N/A'} &middot; {s.data?.service_type ?? 'EMS Transport'}</div>
                    </div>
                    <div className="flex items-center gap-3">
                      <span className={`text-body font-bold ${dueForCompare > 0 ? 'text-[var(--q-orange)]' : 'text-[var(--color-status-active)]'}`}>
                        {fmtOrDash(dueCents)}
                      </span>
                      <StatusChip status={s.data?.status} />
                    </div>
                  </Link>
                );
              })}
            </div>

            {/* Recent payments */}
            <div className="bg-[var(--color-bg-surface)] border border-[var(--color-border-default)] chamfer-12 overflow-hidden">
              <div className="px-5 py-4 border-b border-[var(--color-border-default)] flex items-center justify-between">
                <span className="label-caps">Recent Payments</span>
                <Link href="/portal/patient/payments" className="text-micro font-label font-semibold text-[var(--q-orange)] no-underline tracking-wider uppercase hover:underline">View All &rarr;</Link>
              </div>
              {loading ? (
                <div className="p-6 text-body text-[var(--color-text-muted)]">Loading&hellip;</div>
              ) : payments.length === 0 ? (
                <div className="p-6 text-body text-[var(--color-text-muted)]">No payments on record.</div>
              ) : payments.slice(0, 4).map((p) => (
                <div key={p.id} className="flex items-center justify-between gap-3 px-5 py-3.5 border-b border-[var(--color-border-subtle)]">
                  <div>
                    <div className="text-body font-medium text-[var(--color-text-primary)]">Payment &middot; {p.data?.method ?? 'Online'}</div>
                    <div className="text-micro text-[var(--color-text-muted)] mt-0.5">{p.data?.posted_at ? new Date(p.data.posted_at).toLocaleDateString() : 'On file'}</div>
                  </div>
                  <span className="text-body font-bold text-[var(--color-status-active)]">
                    ${asNumberOrZero(p.data?.amount).toFixed(2)}
                  </span>
                </div>
              ))}
            </div>
          </div>

          {/* Right panel */}
          <div className="space-y-5">
            <div className="bg-[var(--color-bg-surface)] border border-[var(--color-border-default)] chamfer-12 overflow-hidden">
              <div className="px-5 py-4 border-b border-[var(--color-border-default)]">
                <span className="label-caps">Quick Actions</span>
              </div>
              <div className="grid grid-cols-2 gap-2.5 p-4">
                {[
                  { href: '/portal/patient/pay', label: 'Pay Online', primary: true },
                  { href: '/portal/patient/payment-plans', label: 'Payment Plan', primary: false },
                  { href: '/portal/patient/receipts', label: 'Receipts', primary: false },
                  { href: '/portal/patient/documents', label: 'Documents', primary: false },
                  { href: '/portal/patient/messages', label: 'Messages', primary: false },
                  { href: '/portal/patient/support', label: 'Get Help', primary: false },
                  { href: '/portal/patient/activity', label: 'Activity', primary: false },
                  { href: '/portal/patient/profile', label: 'Profile', primary: false },
                ].map((a) => (
                  <Link
                    key={a.href} href={a.href}
                    className={`p-3 text-center text-micro font-label font-bold tracking-wider uppercase no-underline chamfer-4 block leading-snug transition-colors ${
                      a.primary
                        ? 'bg-[var(--color-brand-orange-ghost)] border border-[color-mix(in_srgb,var(--q-orange)_25%,transparent)] text-[var(--q-orange)] hover:bg-[color-mix(in_srgb,var(--q-orange)_12%,transparent)]'
                        : 'bg-transparent border border-[var(--color-border-default)] text-[var(--color-text-primary)] hover:bg-[var(--color-bg-overlay)]'
                    }`}
                  >
                    {a.label}
                  </Link>
                ))}
              </div>
            </div>

            {/* AI Helper panel */}
            <div className="bg-[var(--color-brand-orange-ghost)] border border-[color-mix(in_srgb,var(--q-orange)_15%,transparent)] chamfer-8 p-5">
              <div className="text-micro font-label font-bold tracking-wider uppercase text-[var(--q-orange)] mb-2.5">AI BILLING ASSISTANT</div>
              <div className="text-body text-[var(--color-text-muted)] leading-relaxed mb-3.5">
                Have questions about your bill? Our AI assistant can explain your balance, guide you to receipts, or connect you with billing support.
              </div>
              <Link
                href="/portal/patient/support?mode=ai"
                className="block p-2.5 bg-[color-mix(in_srgb,var(--q-orange)_12%,transparent)] border border-[color-mix(in_srgb,var(--q-orange)_25%,transparent)] text-[var(--q-orange)] text-micro font-label font-bold tracking-wider uppercase no-underline text-center chamfer-4 hover:bg-[color-mix(in_srgb,var(--q-orange)_18%,transparent)] transition-colors"
              >
                Ask AI Assistant &rarr;
              </Link>
            </div>

            {/* Navigation */}
            <div className="bg-[var(--color-bg-surface)] border border-[var(--color-border-default)] chamfer-12 overflow-hidden">
              <div className="px-5 py-4 border-b border-[var(--color-border-default)]">
                <span className="label-caps">Account Navigation</span>
              </div>
              {[
                { href: '/portal/patient/invoices', label: 'Invoices & Statements' },
                { href: '/portal/patient/payments', label: 'Payment History' },
                { href: '/portal/patient/payment-plans', label: 'Payment Plans' },
                { href: '/portal/patient/receipts', label: 'Receipts Center' },
                { href: '/portal/patient/documents', label: 'Documents' },
                { href: '/portal/patient/activity', label: 'Account Activity' },
                { href: '/portal/patient/notifications', label: 'Notifications' },
                { href: '/portal/patient/profile', label: 'Profile & Preferences' },
              ].map((link) => (
                <Link key={link.href} href={link.href} className="flex items-center justify-between gap-3 px-5 py-3.5 border-b border-[var(--color-border-subtle)] no-underline text-body text-[var(--color-text-muted)] hover:bg-[var(--color-bg-overlay)] hover:text-[var(--color-text-primary)] transition-colors">
                  {link.label}
                  <span className="text-[var(--color-text-muted)]">&rsaquo;</span>
                </Link>
              ))}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
