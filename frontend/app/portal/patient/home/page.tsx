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

const S: Record<string, React.CSSProperties> = {
  page: { minHeight: '100vh', background: 'var(--color-bg-base)', color: 'var(--color-text-primary)', fontFamily: 'var(--font-body)', position: 'relative' },
  topBar: { background: 'var(--color-bg-surface)', borderBottom: '1px solid var(--color-border-default)', padding: '0 24px', height: '56px', display: 'flex', alignItems: 'center', justifyContent: 'space-between', position: 'sticky' as const, top: 0, zIndex: 10 },
  topBarLeft: { display: 'flex', alignItems: 'center', gap: '12px' },
  inner: { maxWidth: '1200px', margin: '0 auto', padding: '32px 24px' },
  gridRow: { display: 'grid', gridTemplateColumns: 'repeat(auto-fit,minmax(220px,1fr))', gap: '16px', marginBottom: '32px' },
  statCard: { background: 'var(--color-bg-surface)', border: '1px solid var(--color-border-default)', padding: '20px 24px', clipPath: 'polygon(0 0,calc(100% - 10px) 0,100% 10px,100% 100%,0 100%)' },
  statLabel: { fontSize: '10px', fontWeight: 700, letterSpacing: '0.2em', textTransform: 'uppercase', color: 'var(--color-text-muted)', marginBottom: '8px' },
  statValue: { fontSize: '1.8rem', fontWeight: 900, color: 'var(--color-text-primary)', lineHeight: 1 },
  statSub: { fontSize: '11px', color: 'var(--color-text-muted)', marginTop: '6px' },
  twoCol: { display: 'grid', gridTemplateColumns: '1fr 340px', gap: '24px', alignItems: 'start' },
  section: { background: 'var(--color-bg-surface)', border: '1px solid var(--color-border-default)', clipPath: 'polygon(0 0,calc(100% - 12px) 0,100% 12px,100% 100%,0 100%)', overflow: 'hidden' },
  sectionHead: { padding: '16px 20px', borderBottom: '1px solid var(--color-border-default)', display: 'flex', alignItems: 'center', justifyContent: 'space-between' },
  sectionTitle: { fontSize: '11px', fontWeight: 700, letterSpacing: '0.15em', textTransform: 'uppercase', color: 'var(--color-text-primary)' },
  sectionLink: { fontSize: '11px', fontWeight: 600, color: '#FF4D00', textDecoration: 'none', letterSpacing: '0.08em', textTransform: 'uppercase' },
  row: { padding: '14px 20px', borderBottom: '1px solid rgba(255,255,255,0.04)', display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: '12px' },
  rowLabel: { fontSize: '13px', color: 'var(--color-text-primary)', fontWeight: 500 },
  rowSub: { fontSize: '11px', color: 'var(--color-text-muted)', marginTop: '2px' },
  chip: { fontSize: '10px', fontWeight: 700, letterSpacing: '0.1em', textTransform: 'uppercase', padding: '3px 8px', clipPath: 'polygon(0 0,calc(100% - 4px) 0,100% 4px,100% 100%,0 100%)' },
  quickActions: { display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '10px', padding: '16px 20px' },
  qaBtn: { padding: '12px', textAlign: 'center', fontSize: '11px', fontWeight: 700, letterSpacing: '0.1em', textTransform: 'uppercase', textDecoration: 'none', color: 'var(--color-text-primary)', background: 'transparent', border: '1px solid var(--color-border-default)', display: 'block', clipPath: 'polygon(0 0,calc(100% - 6px) 0,100% 6px,100% 100%,0 100%)', lineHeight: 1.4 },
  qaBtnPrimary: { background: 'rgba(255,77,0,0.08)', border: '1px solid rgba(255,77,0,0.25)', color: '#FF4D00' },
  aiPanel: { background: 'rgba(255,77,0,0.04)', border: '1px solid rgba(255,77,0,0.15)', padding: '20px', clipPath: 'polygon(0 0,calc(100% - 10px) 0,100% 10px,100% 100%,0 100%)', marginTop: '24px' },
};

function fmt(cents: number) {
  return `$${(cents / 100).toFixed(2)}`;
}

function statusChip(status?: string) {
  const map: Record<string, { bg: string; border: string; color: string }> = {
    paid: { bg: 'rgba(16,185,129,0.1)', border: 'rgba(16,185,129,0.3)', color: '#10B981' },
    pending: { bg: 'rgba(245,158,11,0.1)', border: 'rgba(245,158,11,0.3)', color: '#F59E0B' },
    overdue: { bg: 'rgba(239,68,68,0.1)', border: 'rgba(239,68,68,0.3)', color: '#EF4444' },
  };
  const cfg = map[status ?? 'pending'] ?? map.pending;
  return (
    <span style={{ ...S.chip, background: cfg.bg, border: `1px solid ${cfg.border}`, color: cfg.color }}>
      {status?.toUpperCase() ?? 'PENDING'}
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
        const totalBalance = stmts.reduce((acc, s) => acc + (s.data?.amount_due_cents ?? 0), 0);
        const totalPaid = pays.reduce((acc, p) => acc + ((p.data?.amount ?? 0) * 100), 0);
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
    <div style={S.page}>
      {/* Top bar */}
      <div style={S.topBar}>
        <div style={S.topBarLeft}>
          <svg width="28" height="28" viewBox="0 0 36 36" fill="none">
            <polygon points="18,2 33,10 33,26 18,34 3,26 3,10" fill="#FF4D00" />
            <text x="18" y="23" textAnchor="middle" fill="#050505" fontSize="10" fontWeight="900" fontFamily="sans-serif">FQ</text>
          </svg>
          <div>
            <span style={{ fontSize: '11px', fontWeight: 900, letterSpacing: '0.15em', textTransform: 'uppercase' }}>FUSION<span style={{ color: '#FF4D00' }}>EMS</span></span>
            <span style={{ fontSize: '10px', color: 'var(--color-text-muted)', letterSpacing: '0.2em', textTransform: 'uppercase', marginLeft: '10px' }}>MY ACCOUNT</span>
          </div>
        </div>
        <div style={{ display: 'flex', gap: '10px', alignItems: 'center' }}>
          <Link href="/portal/patient/notifications" style={{ fontSize: '11px', color: 'var(--color-text-muted)', textDecoration: 'none', letterSpacing: '0.1em', textTransform: 'uppercase' }}>Notifications</Link>
          <Link href="/portal/patient" style={{ fontSize: '11px', color: 'var(--color-text-muted)', textDecoration: 'none', letterSpacing: '0.1em', textTransform: 'uppercase' }}>← Portal Home</Link>
        </div>
      </div>

      <div style={S.inner}>
        {/* Page heading */}
        <div style={{ marginBottom: '28px' }}>
          <div style={{ fontSize: '11px', fontWeight: 700, letterSpacing: '0.2em', textTransform: 'uppercase', color: 'var(--color-text-muted)', marginBottom: '6px' }}>ACCOUNT OVERVIEW</div>
          <h1 style={{ fontSize: '1.6rem', fontWeight: 900, color: 'var(--color-text-primary)', margin: 0 }}>My Billing Account</h1>
        </div>

        {/* Alert if balance due */}
        {!loading && hasBalance && (
          <div style={{ background: 'rgba(255,77,0,0.06)', border: '1px solid rgba(255,77,0,0.2)', padding: '14px 20px', clipPath: 'polygon(0 0,calc(100% - 10px) 0,100% 10px,100% 100%,0 100%)', marginBottom: '24px', display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: '16px', flexWrap: 'wrap' }}>
            <div>
              <div style={{ fontSize: '12px', fontWeight: 700, color: '#FF4D00', letterSpacing: '0.1em', textTransform: 'uppercase', marginBottom: '4px' }}>Balance Due</div>
              <div style={{ fontSize: '1.4rem', fontWeight: 900, color: 'var(--color-text-primary)' }}>{fmt(summary?.total_balance ?? 0)}</div>
            </div>
            <Link href="/portal/patient/pay" style={{ padding: '10px 24px', background: '#FF4D00', color: '#000', fontWeight: 700, fontSize: '11px', letterSpacing: '0.12em', textTransform: 'uppercase', textDecoration: 'none', clipPath: 'polygon(0 0,calc(100% - 6px) 0,100% 6px,100% 100%,0 100%)', boxShadow: '0 0 20px rgba(255,77,0,0.2)', whiteSpace: 'nowrap' }}>
              Pay Now →
            </Link>
          </div>
        )}

        {/* Stats row */}
        <div style={S.gridRow}>
          <div style={S.statCard}>
            <div style={S.statLabel}>Current Balance</div>
            <div style={{ ...S.statValue, color: hasBalance ? '#FF4D00' : '#10B981' }}>{loading ? '—' : fmt(summary?.total_balance ?? 0)}</div>
            <div style={S.statSub}>{hasBalance ? 'Amount due now' : 'Account is current'}</div>
          </div>
          <div style={S.statCard}>
            <div style={S.statLabel}>Total Paid</div>
            <div style={S.statValue}>{loading ? '—' : fmt(summary?.total_paid ?? 0)}</div>
            <div style={S.statSub}>{summary?.payment_count ?? 0} payment{(summary?.payment_count ?? 0) !== 1 ? 's' : ''} on record</div>
          </div>
          <div style={S.statCard}>
            <div style={S.statLabel}>Statements</div>
            <div style={S.statValue}>{loading ? '—' : (summary?.statement_count ?? 0)}</div>
            <div style={S.statSub}>Total statements on file</div>
          </div>
          <div style={{ ...S.statCard, background: 'rgba(255,77,0,0.04)', border: '1px solid rgba(255,77,0,0.15)' }}>
            <div style={S.statLabel}>Quick Actions</div>
            <div style={{ display: 'flex', flexDirection: 'column', gap: '8px', marginTop: '8px' }}>
              <Link href="/portal/patient/pay" style={{ color: '#FF4D00', fontSize: '12px', fontWeight: 700, textDecoration: 'none' }}>→ Pay My Bill</Link>
              <Link href="/portal/patient/support" style={{ color: 'var(--color-text-muted)', fontSize: '12px', textDecoration: 'none' }}>→ Get Billing Help</Link>
              <Link href="/portal/patient/payment-plans" style={{ color: 'var(--color-text-muted)', fontSize: '12px', textDecoration: 'none' }}>→ Set Up Payment Plan</Link>
            </div>
          </div>
        </div>

        {/* Main 2-col layout */}
        <div style={{ ...S.twoCol, '@media (max-width:900px)': { gridTemplateColumns: '1fr' } } as React.CSSProperties}>
          <div>
            {/* Recent statements */}
            <div style={{ ...S.section, marginBottom: '20px' }}>
              <div style={S.sectionHead}>
                <span style={S.sectionTitle}>Recent Statements</span>
                <Link href="/portal/patient/invoices" style={S.sectionLink}>View All →</Link>
              </div>
              {loading ? (
                <div style={{ padding: '24px', color: 'var(--color-text-muted)', fontSize: '13px' }}>Loading…</div>
              ) : statements.length === 0 ? (
                <div style={{ padding: '24px', color: 'var(--color-text-muted)', fontSize: '13px' }}>No statements found.</div>
              ) : statements.slice(0, 4).map((s) => (
                <Link key={s.id} href={`/portal/patient/invoices?id=${s.id}`} style={{ ...S.row, textDecoration: 'none', color: 'inherit' }}>
                  <div>
                    <div style={S.rowLabel}>Statement #{s.id.slice(-8).toUpperCase()}</div>
                    <div style={S.rowSub}>{s.data?.incident_date ?? 'N/A'} · {s.data?.service_type ?? 'EMS Transport'}</div>
                  </div>
                  <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
                    <span style={{ fontSize: '14px', fontWeight: 700, color: (s.data?.amount_due_cents ?? 0) > 0 ? '#FF4D00' : '#10B981' }}>
                      {fmt(s.data?.amount_due_cents ?? 0)}
                    </span>
                    {statusChip(s.data?.status)}
                  </div>
                </Link>
              ))}
            </div>

            {/* Recent payments */}
            <div style={S.section}>
              <div style={S.sectionHead}>
                <span style={S.sectionTitle}>Recent Payments</span>
                <Link href="/portal/patient/payments" style={S.sectionLink}>View All →</Link>
              </div>
              {loading ? (
                <div style={{ padding: '24px', color: 'var(--color-text-muted)', fontSize: '13px' }}>Loading…</div>
              ) : payments.length === 0 ? (
                <div style={{ padding: '24px', color: 'var(--color-text-muted)', fontSize: '13px' }}>No payments on record.</div>
              ) : payments.slice(0, 4).map((p) => (
                <div key={p.id} style={S.row}>
                  <div>
                    <div style={S.rowLabel}>Payment · {p.data?.method ?? 'Online'}</div>
                    <div style={S.rowSub}>{p.data?.posted_at ? new Date(p.data.posted_at).toLocaleDateString() : 'On file'}</div>
                  </div>
                  <span style={{ fontSize: '14px', fontWeight: 700, color: '#10B981' }}>
                    ${((p.data?.amount ?? 0)).toFixed(2)}
                  </span>
                </div>
              ))}
            </div>
          </div>

          {/* Right panel */}
          <div>
            <div style={{ ...S.section, marginBottom: '20px' }}>
              <div style={S.sectionHead}><span style={S.sectionTitle}>Quick Actions</span></div>
              <div style={S.quickActions}>
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
                  <Link key={a.href} href={a.href} style={{ ...S.qaBtn, ...(a.primary ? S.qaBtnPrimary : {}) }}>
                    {a.label}
                  </Link>
                ))}
              </div>
            </div>

            {/* AI Helper panel */}
            <div style={S.aiPanel}>
              <div style={{ fontSize: '10px', fontWeight: 700, letterSpacing: '0.2em', textTransform: 'uppercase', color: '#FF4D00', marginBottom: '10px' }}>AI BILLING ASSISTANT</div>
              <div style={{ fontSize: '13px', color: 'var(--color-text-muted)', lineHeight: 1.6, marginBottom: '14px' }}>
                Have questions about your bill? Our AI assistant can explain your balance, guide you to receipts, or connect you with billing support.
              </div>
              <Link href="/portal/patient/support?mode=ai" style={{ display: 'block', padding: '10px', background: 'rgba(255,77,0,0.12)', border: '1px solid rgba(255,77,0,0.25)', color: '#FF4D00', fontSize: '11px', fontWeight: 700, letterSpacing: '0.1em', textTransform: 'uppercase', textDecoration: 'none', textAlign: 'center', clipPath: 'polygon(0 0,calc(100% - 6px) 0,100% 6px,100% 100%,0 100%)' }}>
                Ask AI Assistant →
              </Link>
            </div>

            {/* Navigation */}
            <div style={{ ...S.section, marginTop: '20px' }}>
              <div style={S.sectionHead}><span style={S.sectionTitle}>Account Navigation</span></div>
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
                <Link key={link.href} href={link.href} style={{ ...S.row, textDecoration: 'none', color: 'var(--color-text-muted)', fontSize: '13px' }}>
                  {link.label}
                  <span style={{ color: 'var(--color-text-muted)', fontSize: '16px' }}>›</span>
                </Link>
              ))}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
