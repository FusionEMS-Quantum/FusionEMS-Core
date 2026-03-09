'use client';

import { useEffect, useState } from 'react';
import Link from 'next/link';
import { getPortalPayments } from '@/services/api';

interface Payment {
  id: string;
  data?: {
    amount?: number;
    method?: string;
    posted_at?: string;
    status?: string;
    statement_id?: string;
    reference?: string;
    payment_type?: string;
  };
}

const S: Record<string, React.CSSProperties> = {
  page: { minHeight: '100vh', background: 'var(--color-bg-base)', color: 'var(--color-text-primary)', fontFamily: 'var(--font-body)' },
  header: { background: 'var(--color-bg-surface)', borderBottom: '1px solid var(--color-border-default)', padding: '20px 24px', display: 'flex', alignItems: 'center', justifyContent: 'space-between', flexWrap: 'wrap', gap: '12px' },
  inner: { maxWidth: '1000px', margin: '0 auto', padding: '32px 24px' },
  statsRow: { display: 'grid', gridTemplateColumns: 'repeat(auto-fit,minmax(180px,1fr))', gap: '16px', marginBottom: '28px' },
  stat: { background: 'var(--color-bg-surface)', border: '1px solid var(--color-border-default)', padding: '20px', clipPath: 'polygon(0 0,calc(100% - 10px) 0,100% 10px,100% 100%,0 100%)' },
  statLabel: { fontSize: '10px', fontWeight: 700, letterSpacing: '0.2em', textTransform: 'uppercase', color: 'var(--color-text-muted)', marginBottom: '8px' },
  statVal: { fontSize: '1.6rem', fontWeight: 900 },
  table: { background: 'var(--color-bg-surface)', border: '1px solid var(--color-border-default)', overflow: 'hidden', clipPath: 'polygon(0 0,calc(100% - 12px) 0,100% 12px,100% 100%,0 100%)' },
  thead: { padding: '12px 20px', borderBottom: '1px solid var(--color-border-default)', display: 'grid', gridTemplateColumns: '1fr 130px 100px 120px 90px', gap: '12px', background: 'rgba(255,255,255,0.02)' },
  th: { fontSize: '10px', fontWeight: 700, letterSpacing: '0.15em', textTransform: 'uppercase', color: 'var(--color-text-muted)' },
  row: { padding: '14px 20px', display: 'grid', gridTemplateColumns: '1fr 130px 100px 120px 90px', gap: '12px', borderBottom: '1px solid rgba(255,255,255,0.04)', alignItems: 'center' },
  chip: { fontSize: '10px', fontWeight: 700, letterSpacing: '0.08em', textTransform: 'uppercase', padding: '3px 8px', display: 'inline-block', clipPath: 'polygon(0 0,calc(100% - 4px) 0,100% 4px,100% 100%,0 100%)' },
};

export default function PaymentsPage() {
  const [payments, setPayments] = useState<Payment[]>([]);
  const [loading, setLoading] = useState(true);
  const [fetchError, setFetchError] = useState<string | null>(null);

  useEffect(() => {
    getPortalPayments()
      .then((data) => setPayments(data as Payment[]))
      .catch((err: unknown) => setFetchError(err instanceof Error ? err.message : 'Failed to load payment history'))
      .finally(() => setLoading(false));
  }, []);

  const totalPaid = payments.reduce((acc, p) => acc + (p.data?.amount ?? 0), 0);
  const pending = payments.filter((p) => p.data?.status === 'pending').length;

  return (
    <div style={S.page}>
      <div style={S.header}>
        <div>
          <div style={{ fontSize: '10px', fontWeight: 700, letterSpacing: '0.2em', textTransform: 'uppercase', color: 'var(--color-text-muted)', marginBottom: '4px' }}>BILLING PORTAL</div>
          <h1 style={{ fontSize: '1.4rem', fontWeight: 900, margin: 0 }}>Payment History</h1>
        </div>
        <div style={{ display: 'flex', gap: '10px' }}>
          <Link href="/portal/patient/home" style={{ padding: '8px 16px', background: 'transparent', border: '1px solid var(--color-border-default)', color: 'var(--color-text-muted)', fontSize: '11px', fontWeight: 700, letterSpacing: '0.1em', textTransform: 'uppercase', textDecoration: 'none', clipPath: 'polygon(0 0,calc(100% - 5px) 0,100% 5px,100% 100%,0 100%)' }}>← Dashboard</Link>
          <Link href="/portal/patient/receipts" style={{ padding: '8px 16px', background: 'transparent', border: '1px solid rgba(255,77,0,0.3)', color: '#FF4D00', fontSize: '11px', fontWeight: 700, letterSpacing: '0.1em', textTransform: 'uppercase', textDecoration: 'none', clipPath: 'polygon(0 0,calc(100% - 5px) 0,100% 5px,100% 100%,0 100%)' }}>Receipts Center</Link>
        </div>
      </div>
      <div style={S.inner}>
        {fetchError && (
          <div style={{ marginBottom: '20px', padding: '12px 16px', background: 'rgba(239,68,68,0.08)', border: '1px solid rgba(239,68,68,0.2)', color: '#FCA5A5', fontSize: '13px' }}>
            Unable to load payment history. Please refresh the page or contact billing support.
          </div>
        )}
        <div style={S.statsRow}>
          <div style={S.stat}>
            <div style={S.statLabel}>Total Paid</div>
            <div style={{ ...S.statVal, color: '#10B981' }}>${totalPaid.toFixed(2)}</div>
          </div>
          <div style={S.stat}>
            <div style={S.statLabel}>Transactions</div>
            <div style={S.statVal}>{payments.length}</div>
          </div>
          {pending > 0 && (
            <div style={{ ...S.stat, background: 'rgba(245,158,11,0.06)', border: '1px solid rgba(245,158,11,0.2)' }}>
              <div style={S.statLabel}>Pending</div>
              <div style={{ ...S.statVal, color: '#F59E0B' }}>{pending}</div>
            </div>
          )}
        </div>

        {loading ? (
          <div style={{ padding: '48px', textAlign: 'center', color: 'var(--color-text-muted)' }}>Loading payment history…</div>
        ) : payments.length === 0 ? (
          <div style={{ ...S.table, padding: '48px', textAlign: 'center', color: 'var(--color-text-muted)' }}>No payments on record.</div>
        ) : (
          <div style={S.table}>
            <div style={S.thead}>
              <div style={S.th}>Reference</div>
              <div style={S.th}>Date Posted</div>
              <div style={S.th}>Method</div>
              <div style={S.th}>Amount</div>
              <div style={S.th}>Status</div>
            </div>
            {payments.map((p) => {
              const statusCfg = p.data?.status === 'posted'
                ? { bg: 'rgba(16,185,129,0.1)', border: 'rgba(16,185,129,0.3)', color: '#10B981' }
                : p.data?.status === 'pending'
                  ? { bg: 'rgba(245,158,11,0.1)', border: 'rgba(245,158,11,0.3)', color: '#F59E0B' }
                  : { bg: 'rgba(99,102,241,0.1)', border: 'rgba(99,102,241,0.3)', color: '#818CF8' };
              return (
                <div key={p.id} style={S.row}>
                  <div>
                    <div style={{ fontSize: '13px', fontWeight: 600 }}>
                      {p.data?.reference ?? p.id.slice(-8).toUpperCase()}
                    </div>
                    {p.data?.statement_id && (
                      <Link href={`/portal/patient/invoices/${p.data.statement_id}`} style={{ fontSize: '11px', color: '#FF4D00', textDecoration: 'none' }}>
                        View Statement →
                      </Link>
                    )}
                  </div>
                  <div style={{ fontSize: '13px', color: 'var(--color-text-muted)' }}>
                    {p.data?.posted_at ? new Date(p.data.posted_at).toLocaleDateString() : '—'}
                  </div>
                  <div style={{ fontSize: '13px', color: 'var(--color-text-muted)', textTransform: 'capitalize' as const }}>
                    {p.data?.method ?? 'Online'}
                  </div>
                  <div style={{ fontSize: '14px', fontWeight: 700, color: '#10B981' }}>
                    ${(p.data?.amount ?? 0).toFixed(2)}
                  </div>
                  <div>
                    <span style={{ ...S.chip, background: statusCfg.bg, border: `1px solid ${statusCfg.border}`, color: statusCfg.color }}>
                      {(p.data?.status ?? 'posted').toUpperCase()}
                    </span>
                  </div>
                </div>
              );
            })}
          </div>
        )}

        <div style={{ marginTop: '20px', fontSize: '12px', color: 'var(--color-text-muted)' }}>
          <span>Questions about a payment? </span>
          <Link href="/portal/patient/support" style={{ color: '#FF4D00', textDecoration: 'none' }}>Contact Billing Support</Link>
        </div>
      </div>
    </div>
  );
}
