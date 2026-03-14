'use client';

import { useEffect, useState } from 'react';
import Link from 'next/link';
import { Suspense } from 'react';
import { useSearchParams } from 'next/navigation';
import { getPortalStatements } from '@/services/api';

type InvoiceStatus = 'paid' | 'pending' | 'overdue' | 'in_review' | 'partial';

interface Invoice {
  id: string;
  data?: {
    incident_date?: string;
    service_date?: string;
    service_type?: string;
    amount_billed_cents?: number;
    amount_due_cents?: number;
    amount_paid_cents?: number;
    status?: InvoiceStatus;
    patient_name?: string;
    agency_name?: string;
  };
}

const STATUS_COLORS: Record<string, { color: string; label: string }> = {
  paid:      { color: 'var(--color-status-active)', label: 'PAID' },
  pending:   { color: 'var(--q-yellow)', label: 'PENDING' },
  overdue:   { color: 'var(--color-brand-red)', label: 'OVERDUE' },
  in_review: { color: 'var(--color-status-info)', label: 'IN REVIEW' },
  partial:   { color: 'var(--q-orange)', label: 'PARTIAL' },
};

function fmt(cents?: number) { return cents !== undefined ? `$${(cents / 100).toFixed(2)}` : '—'; }

function asNumberOrUndefined(v: unknown): number | undefined {
  return typeof v === 'number' && Number.isFinite(v) ? v : undefined;
}

function StatusChip({ status }: { status?: string }) {
  const cfg = STATUS_COLORS[status ?? 'pending'] ?? STATUS_COLORS.pending;
  return (
    <span
      className="text-micro font-label font-bold tracking-wider uppercase px-2 py-0.5 chamfer-4 inline-block"
      style={{ color: cfg.color, backgroundColor: `color-mix(in srgb, ${cfg.color} 12%, transparent)`, border: `1px solid color-mix(in srgb, ${cfg.color} 30%, transparent)` }}
    >
      {cfg.label}
    </span>
  );
}

function InvoicesContent() {
  const searchParams = useSearchParams();
  const filterParam = searchParams.get('status') || 'all';
  const [invoices, setInvoices] = useState<Invoice[]>([]);
  const [loading, setLoading] = useState(true);
  const [fetchError, setFetchError] = useState<string | null>(null);
  const [filter, setFilter] = useState(filterParam);

  useEffect(() => {
    getPortalStatements()
      .then((data) => setInvoices(data as Invoice[]))
      .catch((err: unknown) => setFetchError(err instanceof Error ? err.message : 'Failed to load invoices'))
      .finally(() => setLoading(false));
  }, []);

  const displayed = filter === 'all' ? invoices : invoices.filter((i) => i.data?.status === filter);

  return (
    <div className="min-h-screen bg-[var(--color-bg-base)] text-[var(--color-text-primary)] font-sans">
      {fetchError && (
        <div className="px-5 py-3 bg-[var(--color-brand-red-ghost)] border-b border-[var(--color-brand-red)] text-body text-[var(--color-brand-red)]">
          Unable to load invoices. Please refresh the page or contact billing support.
        </div>
      )}

      <header className="bg-[var(--color-bg-surface)] border-b border-[var(--color-border-default)] px-6 py-5 flex items-center justify-between flex-wrap gap-3">
        <div>
          <div className="text-micro font-label font-bold tracking-wider uppercase text-[var(--color-text-muted)] mb-1">PATIENT BILLING PORTAL</div>
          <h1 className="text-h2 font-black m-0">Invoices &amp; Statements</h1>
        </div>
        <div className="flex gap-2.5">
          <Link href="/portal/patient/home" className="quantum-btn no-underline">&larr; Dashboard</Link>
          <Link href="/portal/patient/pay" className="quantum-btn-primary no-underline">Pay Now</Link>
        </div>
      </header>

      <div className="max-w-[1100px] mx-auto px-6 py-8">
        {/* Filters */}
        <div className="flex gap-2.5 mb-6 flex-wrap">
          {['all', 'pending', 'overdue', 'paid', 'in_review'].map((f) => (
            <button
              key={f} onClick={() => setFilter(f)}
              className={`px-4 py-1.5 text-micro font-label font-bold tracking-wider uppercase chamfer-4 border transition-colors cursor-pointer ${
                filter === f
                  ? 'bg-[var(--color-brand-orange-ghost)] border-[color-mix(in_srgb,var(--q-orange)_30%,transparent)] text-[var(--q-orange)]'
                  : 'bg-transparent border-[var(--color-border-default)] text-[var(--color-text-muted)] hover:text-[var(--color-text-primary)] hover:border-[var(--color-border-strong)]'
              }`}
            >
              {f === 'all' ? 'All Statements' : f.replace('_', ' ')}
            </button>
          ))}
        </div>

        {loading ? (
          <div className="p-12 text-center text-body text-[var(--color-text-muted)]">Loading statements&hellip;</div>
        ) : displayed.length === 0 ? (
          <div className="bg-[var(--color-bg-surface)] border border-[var(--color-border-default)] chamfer-12 p-12 text-center text-body text-[var(--color-text-muted)]">
            No statements found{filter !== 'all' ? ` for filter: ${filter}` : ''}.
          </div>
        ) : (
          <div className="bg-[var(--color-bg-surface)] border border-[var(--color-border-default)] chamfer-12 overflow-hidden">
            {/* Table header */}
            <div className="grid grid-cols-[1fr_140px_120px_120px_100px] gap-3 px-5 py-3 border-b border-[var(--color-border-default)] bg-[var(--color-bg-overlay)]">
              <span className="label-caps">Statement</span>
              <span className="label-caps">Date</span>
              <span className="label-caps">Billed</span>
              <span className="label-caps">Balance</span>
              <span className="label-caps">Status</span>
            </div>
            {/* Rows */}
            {displayed.map((inv) => {
              const dueCents = asNumberOrUndefined(inv.data?.amount_due_cents);
              const dueForCompare = dueCents ?? 0;
              return (
                <Link
                  key={inv.id} href={`/portal/patient/invoices/${inv.id}`}
                  className="grid grid-cols-[1fr_140px_120px_120px_100px] gap-3 px-5 py-3.5 border-b border-[var(--color-border-subtle)] no-underline text-inherit items-center hover:bg-[var(--color-bg-overlay)] transition-colors"
                >
                  <div>
                    <div className="text-body font-semibold text-[var(--color-text-primary)]">Statement #{inv.id.slice(-8).toUpperCase()}</div>
                    <div className="text-micro text-[var(--color-text-muted)] mt-0.5">{inv.data?.service_type ?? 'EMS Transport'}</div>
                  </div>
                  <div className="text-body text-[var(--color-text-muted)]">{inv.data?.incident_date ?? inv.data?.service_date ?? '—'}</div>
                  <div className="text-body text-[var(--color-text-primary)]">{fmt(inv.data?.amount_billed_cents)}</div>
                  <div className={`text-body font-bold ${dueForCompare > 0 ? 'text-[var(--q-orange)]' : 'text-[var(--color-status-active)]'}`}>{fmt(dueCents)}</div>
                  <div><StatusChip status={inv.data?.status} /></div>
                </Link>
              );
            })}
          </div>
        )}

        <div className="mt-6 flex gap-3 flex-wrap text-body text-[var(--color-text-muted)]">
          <span>Showing {displayed.length} of {invoices.length} statement{invoices.length !== 1 ? 's' : ''}</span>
          <span>&middot;</span>
          <Link href="/portal/patient/support" className="text-[var(--q-orange)] no-underline hover:underline">Questions about a statement? Get Help</Link>
        </div>
      </div>
    </div>
  );
}

export default function InvoicesPage() {
  return (
    <Suspense fallback={<div className="min-h-screen bg-[var(--color-bg-base)]" />}>
      <InvoicesContent />
    </Suspense>
  );
}
