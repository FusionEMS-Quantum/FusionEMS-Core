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

const STATUS: Record<string, { label: string; bg: string; border: string; color: string }> = {
  paid:      { label: 'PAID',      bg: 'rgba(16,185,129,0.1)',  border: 'rgba(16,185,129,0.3)',  color: '#10B981' },
  pending:   { label: 'PENDING',   bg: 'rgba(245,158,11,0.1)', border: 'rgba(245,158,11,0.3)', color: '#F59E0B' },
  overdue:   { label: 'OVERDUE',   bg: 'rgba(239,68,68,0.1)',  border: 'rgba(239,68,68,0.3)',  color: '#EF4444' },
  in_review: { label: 'IN REVIEW', bg: 'rgba(99,102,241,0.1)',  border: 'rgba(99,102,241,0.3)',  color: '#818CF8' },
  partial:   { label: 'PARTIAL',   bg: 'rgba(255,77,0,0.1)',    border: 'rgba(255,77,0,0.3)',    color: '#FF4D00' },
};

const S: Record<string, React.CSSProperties> = {
  page: { minHeight: '100vh', background: 'var(--color-bg-base)', color: 'var(--color-text-primary)', fontFamily: 'var(--font-body)' },
  header: { background: 'var(--color-bg-surface)', borderBottom: '1px solid var(--color-border-default)', padding: '20px 24px', display: 'flex', alignItems: 'center', justifyContent: 'space-between', flexWrap: 'wrap', gap: '12px' },
  inner: { maxWidth: '1100px', margin: '0 auto', padding: '32px 24px' },
  filtersRow: { display: 'flex', gap: '10px', marginBottom: '24px', flexWrap: 'wrap' },
  filterBtn: { padding: '7px 16px', fontSize: '11px', fontWeight: 700, letterSpacing: '0.1em', textTransform: 'uppercase', border: '1px solid var(--color-border-default)', background: 'transparent', color: 'var(--color-text-muted)', cursor: 'pointer', clipPath: 'polygon(0 0,calc(100% - 5px) 0,100% 5px,100% 100%,0 100%)', transition: 'all 0.15s' },
  filterBtnActive: { background: 'rgba(255,77,0,0.1)', border: '1px solid rgba(255,77,0,0.3)', color: '#FF4D00' },
  table: { background: 'var(--color-bg-surface)', border: '1px solid var(--color-border-default)', overflow: 'hidden', clipPath: 'polygon(0 0,calc(100% - 12px) 0,100% 12px,100% 100%,0 100%)' },
  thead: { borderBottom: '1px solid var(--color-border-default)', padding: '12px 20px', display: 'grid', gridTemplateColumns: '1fr 140px 120px 120px 100px', gap: '12px', background: 'rgba(255,255,255,0.02)' },
  th: { fontSize: '10px', fontWeight: 700, letterSpacing: '0.15em', textTransform: 'uppercase', color: 'var(--color-text-muted)' },
  row: { padding: '14px 20px', display: 'grid', gridTemplateColumns: '1fr 140px 120px 120px 100px', gap: '12px', borderBottom: '1px solid rgba(255,255,255,0.04)', alignItems: 'center', textDecoration: 'none', color: 'inherit', transition: 'background 0.15s' },
  chip: { fontSize: '10px', fontWeight: 700, letterSpacing: '0.08em', textTransform: 'uppercase', padding: '3px 8px', display: 'inline-block', clipPath: 'polygon(0 0,calc(100% - 4px) 0,100% 4px,100% 100%,0 100%)' },
  empty: { padding: '48px 24px', textAlign: 'center', color: 'var(--color-text-muted)', fontSize: '14px' },
};

function fmt(cents?: number) { return cents !== undefined ? `$${(cents / 100).toFixed(2)}` : '—'; }

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
    <div style={S.page}>      {fetchError && (
        <div style={{ padding: '12px 20px', background: 'rgba(239,68,68,0.08)', borderBottom: '1px solid rgba(239,68,68,0.2)', color: '#FCA5A5', fontSize: '13px' }}>
          Unable to load invoices. Please refresh the page or contact billing support.
        </div>
      )}      <div style={S.header}>
        <div>
          <div style={{ fontSize: '10px', fontWeight: 700, letterSpacing: '0.2em', textTransform: 'uppercase', color: 'var(--color-text-muted)', marginBottom: '4px' }}>PATIENT BILLING PORTAL</div>
          <h1 style={{ fontSize: '1.4rem', fontWeight: 900, margin: 0 }}>Invoices &amp; Statements</h1>
        </div>
        <div style={{ display: 'flex', gap: '10px' }}>
          <Link href="/portal/patient/home" style={{ padding: '8px 16px', background: 'transparent', border: '1px solid var(--color-border-default)', color: 'var(--color-text-muted)', fontSize: '11px', fontWeight: 700, letterSpacing: '0.1em', textTransform: 'uppercase', textDecoration: 'none', clipPath: 'polygon(0 0,calc(100% - 5px) 0,100% 5px,100% 100%,0 100%)' }}>← Dashboard</Link>
          <Link href="/portal/patient/pay" style={{ padding: '8px 16px', background: '#FF4D00', border: '1px solid #FF4D00', color: '#000', fontSize: '11px', fontWeight: 700, letterSpacing: '0.1em', textTransform: 'uppercase', textDecoration: 'none', clipPath: 'polygon(0 0,calc(100% - 5px) 0,100% 5px,100% 100%,0 100%)' }}>Pay Now</Link>
        </div>
      </div>

      <div style={S.inner}>
        <div style={S.filtersRow}>
          {['all', 'pending', 'overdue', 'paid', 'in_review'].map((f) => (
            <button key={f} onClick={() => setFilter(f)} style={{ ...S.filterBtn, ...(filter === f ? S.filterBtnActive : {}) }}>
              {f === 'all' ? 'All Statements' : f.replace('_', ' ')}
            </button>
          ))}
        </div>

        {loading ? (
          <div style={S.empty}>Loading statements…</div>
        ) : displayed.length === 0 ? (
          <div style={{ ...S.table, ...S.empty }}>No statements found{filter !== 'all' ? ` for filter: ${filter}` : ''}.</div>
        ) : (
          <div style={S.table}>
            <div style={S.thead}>
              <div style={S.th}>Statement</div>
              <div style={S.th}>Date</div>
              <div style={S.th}>Billed</div>
              <div style={S.th}>Balance</div>
              <div style={S.th}>Status</div>
            </div>
            {displayed.map((inv) => {
              const cfg = STATUS[inv.data?.status ?? 'pending'] ?? STATUS.pending;
              return (
                <Link key={inv.id} href={`/portal/patient/invoices/${inv.id}`} style={S.row}>
                  <div>
                    <div style={{ fontSize: '13px', fontWeight: 600 }}>Statement #{inv.id.slice(-8).toUpperCase()}</div>
                    <div style={{ fontSize: '11px', color: 'var(--color-text-muted)', marginTop: '2px' }}>{inv.data?.service_type ?? 'EMS Transport'}</div>
                  </div>
                  <div style={{ fontSize: '13px', color: 'var(--color-text-muted)' }}>{inv.data?.incident_date ?? inv.data?.service_date ?? '—'}</div>
                  <div style={{ fontSize: '13px' }}>{fmt(inv.data?.amount_billed_cents)}</div>
                  <div style={{ fontSize: '14px', fontWeight: 700, color: (inv.data?.amount_due_cents ?? (() => { throw new Error('Unsafe silent fallback. Dependency missing.'); })()) > 0 ? '#FF4D00' : '#10B981' }}>{fmt(inv.data?.amount_due_cents)}</div>
                  <div><span style={{ ...S.chip, background: cfg.bg, border: `1px solid ${cfg.border}`, color: cfg.color }}>{cfg.label}</span></div>
                </Link>
              );
            })}
          </div>
        )}

        <div style={{ marginTop: '24px', display: 'flex', gap: '12px', flexWrap: 'wrap', fontSize: '12px', color: 'var(--color-text-muted)' }}>
          <span>Showing {displayed.length} of {invoices.length} statement{invoices.length !== 1 ? 's' : ''}</span>
          <span>·</span>
          <Link href="/portal/patient/support" style={{ color: '#FF4D00', textDecoration: 'none' }}>Questions about a statement? Get Help</Link>
        </div>
      </div>
    </div>
  );
}

export default function InvoicesPage() {
  return (
    <Suspense fallback={<div style={{ minHeight: '100vh', background: 'var(--color-bg-base)' }} />}>
      <InvoicesContent />
    </Suspense>
  );
}
