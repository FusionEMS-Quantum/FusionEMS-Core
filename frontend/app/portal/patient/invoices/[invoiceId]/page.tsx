'use client';

import { useEffect, useState } from 'react';
import Link from 'next/link';

interface PageProps {
  params: { invoiceId: string };
}

interface Invoice {
  id: string;
  data?: {
    patient_name?: string;
    responsible_party?: string;
    agency_name?: string;
    incident_date?: string;
    transport_date?: string;
    service_type?: string;
    origin?: string;
    destination?: string;
    amount_billed_cents?: number;
    amount_due_cents?: number;
    amount_paid_cents?: number;
    adjustments_cents?: number;
    due_date?: string;
    status?: string;
    account_ref?: string;
  };
}

const S: Record<string, React.CSSProperties> = {
  page: { minHeight: '100vh', background: 'var(--color-bg-base)', color: 'var(--color-text-primary)', fontFamily: 'var(--font-body)' },
  header: { background: 'var(--color-bg-surface)', borderBottom: '1px solid var(--color-border-default)', padding: '20px 24px', display: 'flex', alignItems: 'center', justifyContent: 'space-between', flexWrap: 'wrap', gap: '12px' },
  inner: { maxWidth: '900px', margin: '0 auto', padding: '32px 24px' },
  hero: { background: 'var(--color-bg-surface)', border: '1px solid var(--color-border-default)', padding: '32px', clipPath: 'polygon(0 0,calc(100% - 20px) 0,100% 20px,100% 100%,0 100%)', marginBottom: '24px', position: 'relative' as const },
  section: { background: 'var(--color-bg-surface)', border: '1px solid var(--color-border-default)', clipPath: 'polygon(0 0,calc(100% - 12px) 0,100% 12px,100% 100%,0 100%)', marginBottom: '20px', overflow: 'hidden' },
  sectionHead: { padding: '14px 20px', borderBottom: '1px solid var(--color-border-default)', fontSize: '11px', fontWeight: 700, letterSpacing: '0.15em', textTransform: 'uppercase', color: 'var(--color-text-muted)' },
  grid2: { display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '0', padding: '0' },
  cell: { padding: '16px 20px', borderBottom: '1px solid rgba(255,255,255,0.04)' },
  cellLabel: { fontSize: '10px', fontWeight: 700, letterSpacing: '0.15em', textTransform: 'uppercase', color: 'var(--color-text-muted)', marginBottom: '4px' },
  cellValue: { fontSize: '14px', color: 'var(--color-text-primary)', fontWeight: 500 },
  balanceRow: { display: 'flex', alignItems: 'center', justifyContent: 'space-between', padding: '16px 20px', borderBottom: '1px solid rgba(255,255,255,0.04)' },
  actionBar: { display: 'flex', gap: '12px', flexWrap: 'wrap', marginBottom: '24px' },
  btnPrimary: { padding: '11px 24px', background: '#FF4D00', border: 'none', color: '#000', fontSize: '11px', fontWeight: 700, letterSpacing: '0.12em', textTransform: 'uppercase', textDecoration: 'none', display: 'inline-block', clipPath: 'polygon(0 0,calc(100% - 6px) 0,100% 6px,100% 100%,0 100%)', boxShadow: '0 0 20px rgba(255,77,0,0.2)' },
  btnSecondary: { padding: '11px 20px', background: 'transparent', border: '1px solid var(--color-border-default)', color: 'var(--color-text-primary)', fontSize: '11px', fontWeight: 700, letterSpacing: '0.12em', textTransform: 'uppercase', textDecoration: 'none', display: 'inline-block', clipPath: 'polygon(0 0,calc(100% - 6px) 0,100% 6px,100% 100%,0 100%)' },
  explainBox: { background: 'rgba(255,77,0,0.04)', border: '1px solid rgba(255,77,0,0.15)', padding: '20px 24px', clipPath: 'polygon(0 0,calc(100% - 10px) 0,100% 10px,100% 100%,0 100%)', marginBottom: '20px' },
  chip: { fontSize: '10px', fontWeight: 700, letterSpacing: '0.1em', textTransform: 'uppercase', padding: '4px 10px', display: 'inline-block', clipPath: 'polygon(0 0,calc(100% - 4px) 0,100% 4px,100% 100%,0 100%)' },
};

function fmt(cents?: number) { return cents !== undefined ? `$${(cents / 100).toFixed(2)}` : '—'; }

const STATUS_MAP: Record<string, { bg: string; border: string; color: string }> = {
  paid:      { bg: 'rgba(16,185,129,0.1)',  border: 'rgba(16,185,129,0.3)',  color: '#10B981' },
  pending:   { bg: 'rgba(245,158,11,0.1)', border: 'rgba(245,158,11,0.3)', color: '#F59E0B' },
  overdue:   { bg: 'rgba(239,68,68,0.1)',  border: 'rgba(239,68,68,0.3)',  color: '#EF4444' },
  in_review: { bg: 'rgba(99,102,241,0.1)',  border: 'rgba(99,102,241,0.3)',  color: '#818CF8' },
};

export default function InvoiceDetailPage({ params }: PageProps) {
  const [invoice, setInvoice] = useState<Invoice | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const apiBase = process.env.NEXT_PUBLIC_API_BASE || process.env.NEXT_PUBLIC_API_URL || '';
    fetch(`${apiBase}/api/v1/portal/statements?limit=200`, { credentials: 'include' })
      .then((r) => (r.ok ? r.json() : Promise.resolve({ statements: [] })))
      .then((d) => {
        const stmts: Invoice[] = Array.isArray(d?.statements) ? d.statements : [];
        const found = stmts.find((s) => s.id === params.invoiceId);
        if (!found) throw new Error('Invoice not found.');
        setInvoice(found);
      })
      .catch((err) => setError(err instanceof Error ? err.message : 'Unable to load invoice.'))
      .finally(() => setLoading(false));
  }, [params.invoiceId]);

  const status = invoice?.data?.status ?? 'pending';
  const cfg = STATUS_MAP[status] ?? STATUS_MAP.pending;
  const balance = invoice?.data?.amount_due_cents ?? 0;
  const billed = invoice?.data?.amount_billed_cents ?? 0;
  const paid = invoice?.data?.amount_paid_cents ?? 0;
  const adj = invoice?.data?.adjustments_cents ?? 0;

  return (
    <div style={S.page}>
      <div style={S.header}>
        <div>
          <div style={{ fontSize: '10px', fontWeight: 700, letterSpacing: '0.2em', textTransform: 'uppercase', color: 'var(--color-text-muted)', marginBottom: '4px' }}>INVOICE DETAIL</div>
          <h1 style={{ fontSize: '1.3rem', fontWeight: 900, margin: 0 }}>Statement #{params.invoiceId.slice(-8).toUpperCase()}</h1>
        </div>
        <Link href="/portal/patient/invoices" style={S.btnSecondary}>← All Statements</Link>
      </div>

      <div style={S.inner}>
        {loading && <div style={{ color: 'var(--color-text-muted)', padding: '48px 0', textAlign: 'center' }}>Loading invoice…</div>}
        {error && <div style={{ background: 'rgba(239,68,68,0.1)', border: '1px solid rgba(239,68,68,0.3)', color: '#EF4444', padding: '16px', marginBottom: '24px' }}>{error}</div>}

        {invoice && (
          <>
            {/* Action bar */}
            <div style={S.actionBar}>
              {balance > 0 && (
                <Link href={`/portal/patient/pay?statement_id=${invoice.id}`} style={S.btnPrimary}>
                  Pay ${(balance / 100).toFixed(2)} Now
                </Link>
              )}
              <Link href={`/portal/patient/payment-plans?statement_id=${invoice.id}`} style={S.btnSecondary}>Set Up Payment Plan</Link>
              <Link href="/portal/patient/support" style={S.btnSecondary}>Get Help</Link>
              <button onClick={() => window.print()} style={{ ...S.btnSecondary, cursor: 'pointer', fontFamily: 'inherit' }}>Print</button>
            </div>

            {/* Hero balance card */}
            <div style={S.hero}>
              <div style={{ position: 'absolute', top: '20px', right: '20px' }}>
                <span style={{ ...S.chip, background: cfg.bg, border: `1px solid ${cfg.border}`, color: cfg.color }}>
                  {status.replace('_', ' ').toUpperCase()}
                </span>
              </div>
              <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit,minmax(160px,1fr))', gap: '24px' }}>
                <div>
                  <div style={{ fontSize: '10px', fontWeight: 700, letterSpacing: '0.2em', textTransform: 'uppercase', color: 'var(--color-text-muted)', marginBottom: '6px' }}>Current Balance</div>
                  <div style={{ fontSize: '2.2rem', fontWeight: 900, color: balance > 0 ? '#FF4D00' : '#10B981', lineHeight: 1 }}>{fmt(balance)}</div>
                  {invoice.data?.due_date && <div style={{ fontSize: '11px', color: 'var(--color-text-muted)', marginTop: '6px' }}>Due {invoice.data.due_date}</div>}
                </div>
                <div>
                  <div style={{ fontSize: '10px', fontWeight: 700, letterSpacing: '0.2em', textTransform: 'uppercase', color: 'var(--color-text-muted)', marginBottom: '6px' }}>Billed Amount</div>
                  <div style={{ fontSize: '1.5rem', fontWeight: 700, color: 'var(--color-text-primary)' }}>{fmt(billed)}</div>
                </div>
                <div>
                  <div style={{ fontSize: '10px', fontWeight: 700, letterSpacing: '0.2em', textTransform: 'uppercase', color: 'var(--color-text-muted)', marginBottom: '6px' }}>Payments Applied</div>
                  <div style={{ fontSize: '1.5rem', fontWeight: 700, color: '#10B981' }}>{fmt(paid)}</div>
                </div>
                {adj !== 0 && (
                  <div>
                    <div style={{ fontSize: '10px', fontWeight: 700, letterSpacing: '0.2em', textTransform: 'uppercase', color: 'var(--color-text-muted)', marginBottom: '6px' }}>Adjustments</div>
                    <div style={{ fontSize: '1.5rem', fontWeight: 700, color: 'var(--color-text-primary)' }}>{fmt(Math.abs(adj))}</div>
                  </div>
                )}
              </div>
            </div>

            {/* Plain English explanation */}
            <div style={S.explainBox}>
              <div style={{ fontSize: '10px', fontWeight: 700, letterSpacing: '0.2em', textTransform: 'uppercase', color: '#FF4D00', marginBottom: '10px' }}>WHAT THIS BILL MEANS</div>
              <p style={{ fontSize: '13px', color: 'var(--color-text-muted)', lineHeight: 1.7, margin: 0 }}>
                You received emergency medical service on <strong style={{ color: 'var(--color-text-primary)' }}>{invoice.data?.incident_date ?? 'the date shown above'}</strong>.
                The total billed amount was <strong style={{ color: 'var(--color-text-primary)' }}>{fmt(billed)}</strong>.
                {paid > 0 && <> Payments of <strong style={{ color: '#10B981' }}>{fmt(paid)}</strong> have been applied.</>}
                {adj !== 0 && <> Adjustments of <strong style={{ color: 'var(--color-text-primary)' }}>{fmt(Math.abs(adj))}</strong> were applied.</>}
                {balance > 0
                  ? <> Your <strong style={{ color: '#FF4D00' }}>remaining balance is {fmt(balance)}</strong>. This amount is currently due.</>
                  : <> Your account <strong style={{ color: '#10B981' }}>is paid in full</strong>. Thank you.</>
                }
              </p>
              {balance > 0 && (
                <Link href="/portal/patient/support?mode=ai" style={{ display: 'inline-block', marginTop: '14px', color: '#FF4D00', fontSize: '11px', fontWeight: 700, textDecoration: 'none', letterSpacing: '0.1em', textTransform: 'uppercase' }}>
                  Ask AI to Explain This Bill →
                </Link>
              )}
            </div>

            {/* Patient & Service details */}
            <div style={S.section}>
              <div style={S.sectionHead}>Account &amp; Service Details</div>
              <div style={S.grid2}>
                {[
                  ['Patient Name', invoice.data?.patient_name ?? '—'],
                  ['Agency', invoice.data?.agency_name ?? '—'],
                  ['Date of Service', invoice.data?.incident_date ?? '—'],
                  ['Transport Date', invoice.data?.transport_date ?? '—'],
                  ['Service Type', invoice.data?.service_type ?? 'EMS Transport'],
                  ['Account Reference', invoice.data?.account_ref ?? invoice.id.slice(-10).toUpperCase()],
                  ['Origin', invoice.data?.origin ?? '—'],
                  ['Destination', invoice.data?.destination ?? '—'],
                ].map(([label, value]) => (
                  <div key={label} style={{ ...S.cell, borderRight: '1px solid rgba(255,255,255,0.03)' }}>
                    <div style={S.cellLabel}>{label}</div>
                    <div style={S.cellValue}>{value}</div>
                  </div>
                ))}
              </div>
            </div>

            {/* Payment breakdown */}
            <div style={S.section}>
              <div style={S.sectionHead}>Billing Summary</div>
              {[
                { label: 'Total Billed', value: fmt(billed), bold: false },
                { label: 'Adjustments', value: adj !== 0 ? `-${fmt(Math.abs(adj))}` : '$0.00', bold: false },
                { label: 'Insurance / Payments Applied', value: fmt(paid), bold: false },
                { label: 'Current Balance Due', value: fmt(balance), bold: true },
              ].map((r) => (
                <div key={r.label} style={S.balanceRow}>
                  <span style={{ fontSize: '13px', color: r.bold ? 'var(--color-text-primary)' : 'var(--color-text-muted)', fontWeight: r.bold ? 700 : 400 }}>{r.label}</span>
                  <span style={{ fontSize: r.bold ? '18px' : '14px', fontWeight: r.bold ? 900 : 500, color: r.bold && balance > 0 ? '#FF4D00' : 'var(--color-text-primary)' }}>{r.value}</span>
                </div>
              ))}
            </div>

            {/* Payment options */}
            <div style={S.section}>
              <div style={S.sectionHead}>Payment Options</div>
              <div style={{ padding: '20px', display: 'grid', gridTemplateColumns: 'repeat(auto-fit,minmax(200px,1fr))', gap: '14px' }}>
                {balance > 0 && (
                  <Link href={`/portal/patient/pay?statement_id=${invoice.id}`} style={{ padding: '18px', background: 'rgba(255,77,0,0.08)', border: '1px solid rgba(255,77,0,0.25)', textDecoration: 'none', clipPath: 'polygon(0 0,calc(100% - 8px) 0,100% 8px,100% 100%,0 100%)' }}>
                    <div style={{ fontSize: '10px', fontWeight: 700, letterSpacing: '0.15em', textTransform: 'uppercase', color: '#FF4D00', marginBottom: '6px' }}>Pay Online</div>
                    <div style={{ fontSize: '12px', color: 'var(--color-text-muted)' }}>Secure hosted payment. Card data never stored.</div>
                  </Link>
                )}
                <div style={{ padding: '18px', background: 'var(--color-bg-base)', border: '1px solid var(--color-border-default)', clipPath: 'polygon(0 0,calc(100% - 8px) 0,100% 8px,100% 100%,0 100%)' }}>
                  <div style={{ fontSize: '10px', fontWeight: 700, letterSpacing: '0.15em', textTransform: 'uppercase', color: 'var(--color-text-muted)', marginBottom: '6px' }}>Pay by Phone</div>
                  <div style={{ fontSize: '13px', fontWeight: 700, color: '#FF4D00' }}>(800) 555-0100</div>
                  <div style={{ fontSize: '11px', color: 'var(--color-text-muted)', marginTop: '4px' }}>Mention your statement ID when you call.</div>
                </div>
                <div style={{ padding: '18px', background: 'var(--color-bg-base)', border: '1px solid var(--color-border-default)', clipPath: 'polygon(0 0,calc(100% - 8px) 0,100% 8px,100% 100%,0 100%)' }}>
                  <div style={{ fontSize: '10px', fontWeight: 700, letterSpacing: '0.15em', textTransform: 'uppercase', color: 'var(--color-text-muted)', marginBottom: '6px' }}>Pay by Mail</div>
                  <div style={{ fontSize: '12px', color: 'var(--color-text-muted)', lineHeight: 1.6 }}>Mail check to agency remittance address. Memo: {invoice.id.slice(-10).toUpperCase()}</div>
                  <Link href={`/portal/patient/support?type=check-instructions&statement_id=${invoice.id}`} style={{ display: 'block', marginTop: '8px', fontSize: '11px', fontWeight: 700, color: '#FF4D00', textDecoration: 'none' }}>View Mailing Instructions →</Link>
                </div>
              </div>
            </div>
          </>
        )}
      </div>
    </div>
  );
}
