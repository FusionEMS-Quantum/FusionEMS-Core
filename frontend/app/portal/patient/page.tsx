'use client';

import Link from 'next/link';
import { BILLING_PHONE_DISPLAY, BILLING_PHONE_TEL } from '@/lib/phone';

const S: Record<string, React.CSSProperties> = {
  page: { minHeight: '100vh', background: '#050505', color: 'var(--color-text-primary)', fontFamily: 'var(--font-body)', position: 'relative', overflow: 'hidden' },
  glow: { position: 'absolute', top: 0, left: 0, width: '100%', height: '500px', background: 'linear-gradient(to bottom, rgba(255,77,0,0.06), transparent)', pointerEvents: 'none' },
  grid: { position: 'absolute', inset: 0, backgroundImage: 'linear-gradient(rgba(255,255,255,0.015) 1px,transparent 1px),linear-gradient(90deg,rgba(255,255,255,0.015) 1px,transparent 1px)', backgroundSize: '48px 48px', pointerEvents: 'none' },
  inner: { position: 'relative', zIndex: 1, maxWidth: '1100px', margin: '0 auto', padding: '0 20px 80px' },
  header: { display: 'flex', alignItems: 'center', justifyContent: 'space-between', padding: '28px 0 48px', flexWrap: 'wrap', gap: '16px' },
  heroSection: { textAlign: 'center', marginBottom: '56px', paddingTop: '16px' },
  badge: { display: 'inline-flex', alignItems: 'center', gap: '8px', background: 'rgba(16,185,129,0.08)', border: '1px solid rgba(16,185,129,0.2)', color: '#10B981', fontSize: '10px', fontWeight: 700, letterSpacing: '0.2em', textTransform: 'uppercase', padding: '6px 14px', marginBottom: '28px', clipPath: 'polygon(0 0,calc(100% - 6px) 0,100% 6px,100% 100%,0 100%)' },
  heroTitle: { fontSize: 'clamp(2rem,5vw,3.2rem)', fontWeight: 900, lineHeight: 1.1, letterSpacing: '-0.02em', marginBottom: '16px' },
  heroSub: { fontSize: '1rem', color: 'var(--color-text-muted)', maxWidth: '560px', margin: '0 auto 44px', lineHeight: 1.7 },
  grid6: { display: 'grid', gridTemplateColumns: 'repeat(auto-fit,minmax(190px,1fr))', gap: '14px', marginBottom: '56px' },
  card: { background: 'var(--color-bg-surface)', border: '1px solid var(--color-border-default)', padding: '24px 20px', textDecoration: 'none', color: 'inherit', display: 'block', clipPath: 'polygon(0 0,calc(100% - 10px) 0,100% 10px,100% 100%,0 100%)', transition: 'border-color 0.15s' },
  cardPrimary: { background: 'rgba(255,77,0,0.07)', border: '1px solid rgba(255,77,0,0.28)', boxShadow: '0 0 30px rgba(255,77,0,0.06)' },
  iconBox: { width: '38px', height: '38px', display: 'flex', alignItems: 'center', justifyContent: 'center', background: 'rgba(255,77,0,0.1)', border: '1px solid rgba(255,77,0,0.2)', marginBottom: '14px', clipPath: 'polygon(0 0,calc(100% - 4px) 0,100% 4px,100% 100%,0 100%)' },
  cardTitle: { fontSize: '12px', fontWeight: 700, letterSpacing: '0.08em', textTransform: 'uppercase', marginBottom: '6px', color: 'var(--color-text-primary)' },
  cardDesc: { fontSize: '12px', color: 'var(--color-text-muted)', lineHeight: 1.5 },
  divider: { height: '1px', background: 'var(--color-border-default)', margin: '40px 0' },
  infoGrid: { display: 'grid', gridTemplateColumns: 'repeat(auto-fit,minmax(240px,1fr))', gap: '20px', marginBottom: '44px' },
  infoCard: { background: 'var(--color-bg-surface)', border: '1px solid var(--color-border-default)', padding: '24px', clipPath: 'polygon(0 0,calc(100% - 10px) 0,100% 10px,100% 100%,0 100%)' },
  label: { fontSize: '10px', fontWeight: 700, letterSpacing: '0.2em', textTransform: 'uppercase', color: 'var(--color-text-muted)', marginBottom: '8px' },
  trust: { textAlign: 'center', display: 'flex', alignItems: 'center', justifyContent: 'center', gap: '28px', flexWrap: 'wrap', paddingTop: '28px', borderTop: '1px solid var(--color-border-default)' },
  trustItem: { display: 'flex', alignItems: 'center', gap: '6px', fontSize: '11px', fontWeight: 600, letterSpacing: '0.08em', textTransform: 'uppercase', color: 'var(--color-text-muted)' },
};

const ACTIONS = [
  { href: '/portal/patient/pay', title: 'Pay My Bill', desc: 'Securely pay your balance online', primary: true },
  { href: '/portal/patient/invoices', title: 'View Statement', desc: 'Review your current account and balance', primary: false },
  { href: '/portal/patient/login', title: 'Log In', desc: 'Access your full account portal', primary: false },
  { href: '/portal/patient/lookup', title: 'Look Up Account', desc: 'Find your statement by name & DOB', primary: false },
  { href: '/portal/patient/support', title: 'Get Billing Help', desc: 'Chat, call, or request support', primary: false },
  { href: '/portal/patient/receipts', title: 'Download Receipt', desc: 'Access your payment receipts', primary: false },
];

function HexLogo() {
  return (
    <svg width="40" height="40" viewBox="0 0 36 36" fill="none">
      <polygon points="18,2 33,10 33,26 18,34 3,26 3,10" fill="#FF4D00" />
      <text x="18" y="23" textAnchor="middle" fill="#050505" fontSize="12" fontWeight="900" fontFamily="sans-serif">FQ</text>
    </svg>
  );
}

const BTN_LOGIN: React.CSSProperties = { padding: '8px 18px', background: 'transparent', border: '1px solid var(--color-border-default)', color: 'var(--color-text-primary)', fontSize: '11px', fontWeight: 700, letterSpacing: '0.12em', textTransform: 'uppercase', textDecoration: 'none', clipPath: 'polygon(0 0,calc(100% - 6px) 0,100% 6px,100% 100%,0 100%)' };
const BTN_PAY: React.CSSProperties = { padding: '8px 18px', background: '#FF4D00', border: '1px solid #FF4D00', color: '#000', fontSize: '11px', fontWeight: 700, letterSpacing: '0.12em', textTransform: 'uppercase', textDecoration: 'none', clipPath: 'polygon(0 0,calc(100% - 6px) 0,100% 6px,100% 100%,0 100%)', boxShadow: '0 0 20px rgba(255,77,0,0.2)' };

export default function PatientPortalEntryPage() {
  return (
    <div style={S.page}>
      <div style={S.glow} />
      <div style={S.grid} />
      <div style={S.inner}>
        <header style={S.header}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '14px' }}>
            <HexLogo />
            <div>
              <div style={{ fontSize: '1rem', fontWeight: 900, letterSpacing: '0.15em', textTransform: 'uppercase', lineHeight: 1 }}>
                FUSION<span style={{ color: '#FF4D00' }}>EMS</span>
              </div>
              <div style={{ fontSize: '9px', fontWeight: 700, color: 'var(--color-text-muted)', letterSpacing: '0.3em', textTransform: 'uppercase', marginTop: '4px' }}>
                PATIENT BILLING PORTAL
              </div>
            </div>
          </div>
          <div style={{ display: 'flex', gap: '10px' }}>
            <Link href="/portal/patient/login" style={BTN_LOGIN}>Log In</Link>
            <Link href="/portal/patient/pay" style={BTN_PAY}>Pay Now</Link>
          </div>
        </header>

        <section style={S.heroSection}>
          <div style={S.badge}>
            <span style={{ width: '6px', height: '6px', borderRadius: '50%', background: '#10B981', display: 'inline-block' }} />
            SECURE BILLING ACCESS
          </div>
          <h1 style={S.heroTitle}>
            Your Billing,<br />
            <span style={{ color: '#FF4D00' }}>Clear and Simple.</span>
          </h1>
          <p style={S.heroSub}>
            View your balance, pay your bill, set up a payment plan, or get billing help — all in one secure, private portal.
          </p>
          <div style={S.grid6}>
            {ACTIONS.map((a) => (
              <Link key={a.href} href={a.href} style={{ ...S.card, ...(a.primary ? S.cardPrimary : {}) }}>
                <div style={S.iconBox}>
                  <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="#FF4D00" strokeWidth="2"><rect x="3" y="3" width="18" height="18" rx="2" /></svg>
                </div>
                <div style={S.cardTitle}>{a.title}</div>
                <div style={S.cardDesc}>{a.desc}</div>
              </Link>
            ))}
          </div>
        </section>

        <div style={S.divider} />

        <div style={S.infoGrid}>
          <div style={S.infoCard}>
            <div style={S.label}>Pay Online</div>
            <div style={{ fontWeight: 700, marginBottom: '8px' }}>Secure Hosted Payment</div>
            <div style={{ fontSize: '12px', color: 'var(--color-text-muted)', lineHeight: 1.6, marginBottom: '14px' }}>
              Pay securely using our hosted payment portal. FusionEMS never stores your card data.
            </div>
            <Link href="/portal/patient/pay" style={{ color: '#FF4D00', fontSize: '11px', fontWeight: 700, textDecoration: 'none', letterSpacing: '0.1em', textTransform: 'uppercase' }}>Pay Online →</Link>
          </div>
          <div style={S.infoCard}>
            <div style={S.label}>Pay by Phone</div>
            <div style={{ fontWeight: 700, marginBottom: '8px' }}>Billing Support Line</div>
            <div style={{ fontSize: '12px', color: 'var(--color-text-muted)', lineHeight: 1.6, marginBottom: '14px' }}>
              AI-assisted support 24/7. Human billing specialists available Mon–Fri 8am–6pm.
            </div>
            <a href={BILLING_PHONE_TEL} style={{ color: '#FF4D00', fontWeight: 900, fontSize: '15px', textDecoration: 'none' }}>{BILLING_PHONE_DISPLAY}</a>
          </div>
          <div style={S.infoCard}>
            <div style={S.label}>Pay by Mail</div>
            <div style={{ fontWeight: 700, marginBottom: '8px' }}>Check Payment Instructions</div>
            <div style={{ fontSize: '12px', color: 'var(--color-text-muted)', lineHeight: 1.6, marginBottom: '14px' }}>
              Mail your check directly to the agency remittance address. Include your Statement ID in the memo line.
            </div>
            <Link href="/portal/patient/support?type=check-instructions" style={{ color: '#FF4D00', fontSize: '11px', fontWeight: 700, textDecoration: 'none', letterSpacing: '0.1em', textTransform: 'uppercase' }}>Get Mailing Address →</Link>
          </div>
          <div style={S.infoCard}>
            <div style={S.label}>Payment Plans</div>
            <div style={{ fontWeight: 700, marginBottom: '8px' }}>Flexible Installments</div>
            <div style={{ fontSize: '12px', color: 'var(--color-text-muted)', lineHeight: 1.6, marginBottom: '14px' }}>
              Set up a payment plan that works for your budget. View schedule, simulate options, and enroll online.
            </div>
            <Link href="/portal/patient/payment-plans" style={{ color: '#FF4D00', fontSize: '11px', fontWeight: 700, textDecoration: 'none', letterSpacing: '0.1em', textTransform: 'uppercase' }}>View Plans →</Link>
          </div>
        </div>

        <div style={S.trust}>
          {[['🔒','Secure & Encrypted'],['✓','No Card Data Stored'],['🏥','HIPAA-Conscious'],['📞','Live Support Available']].map(([icon, label]) => (
            <div key={label} style={S.trustItem}><span>{icon}</span><span>{label}</span></div>
          ))}
          <div style={{ width: '100%', textAlign: 'center', marginTop: '16px' }}>
            <span style={{ fontSize: '10px', letterSpacing: '0.15em', color: 'var(--color-text-muted)', textTransform: 'uppercase' }}>
              © {new Date().getFullYear()} FusionEMS Quantum · Secure Billing Infrastructure
            </span>
          </div>
        </div>
      </div>
    </div>
  );
}
