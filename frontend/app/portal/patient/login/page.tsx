'use client';

import { useState } from 'react';
import { useRouter } from 'next/navigation';
import Link from 'next/link';
import { loginPatientPortalSession } from '@/services/api';

const S: Record<string, React.CSSProperties> = {
  page: { minHeight: '100vh', background: '#050505', display: 'flex', alignItems: 'center', justifyContent: 'center', padding: '24px 16px', fontFamily: 'var(--font-body)', position: 'relative' },
  glow: { position: 'absolute', top: 0, left: 0, width: '100%', height: '400px', background: 'linear-gradient(to bottom, rgba(255,77,0,0.05), transparent)', pointerEvents: 'none' },
  card: { position: 'relative', zIndex: 1, width: '100%', maxWidth: '440px', background: 'var(--color-bg-surface)', border: '1px solid var(--color-border-default)', padding: '40px 36px', clipPath: 'polygon(0 0,calc(100% - 16px) 0,100% 16px,100% 100%,0 100%)', boxShadow: '0 24px 80px rgba(0,0,0,0.4)' },
  logoRow: { display: 'flex', alignItems: 'center', gap: '10px', marginBottom: '32px' },
  tag: { fontSize: '10px', fontWeight: 700, letterSpacing: '0.2em', textTransform: 'uppercase', color: 'var(--color-text-muted)', marginBottom: '6px' },
  title: { fontSize: '1.5rem', fontWeight: 900, letterSpacing: '-0.01em', color: 'var(--color-text-primary)', marginBottom: '28px' },
  fieldGroup: { marginBottom: '20px' },
  label: { display: 'block', fontSize: '11px', fontWeight: 700, letterSpacing: '0.15em', textTransform: 'uppercase', color: 'var(--color-text-muted)', marginBottom: '8px' },
  field: { width: '100%', background: 'var(--color-bg-input)', border: '1px solid var(--color-border-default)', color: 'var(--color-text-primary)', fontSize: '14px', padding: '11px 14px', outline: 'none', clipPath: 'polygon(0 0,calc(100% - 6px) 0,100% 6px,100% 100%,0 100%)', boxSizing: 'border-box' },
  btn: { width: '100%', padding: '13px', background: '#FF4D00', border: 'none', color: '#000', fontSize: '12px', fontWeight: 700, letterSpacing: '0.15em', textTransform: 'uppercase', cursor: 'pointer', clipPath: 'polygon(0 0,calc(100% - 8px) 0,100% 8px,100% 100%,0 100%)', boxShadow: '0 0 20px rgba(255,77,0,0.2)', marginTop: '8px' },
  btnDisabled: { opacity: 0.6, cursor: 'not-allowed' as const },
  error: { background: 'rgba(229,57,53,0.1)', border: '1px solid rgba(229,57,53,0.3)', color: '#EF5350', padding: '10px 14px', fontSize: '12px', marginBottom: '16px', clipPath: 'polygon(0 0,calc(100% - 6px) 0,100% 6px,100% 100%,0 100%)' },
  links: { display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginTop: '20px', flexWrap: 'wrap', gap: '8px' },
  linkStyle: { color: 'var(--color-text-muted)', fontSize: '12px', textDecoration: 'none' },
};

export default function PatientLoginPage() {
  const router = useRouter();
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!email.trim() || !password) return;
    setLoading(true);
    setError(null);
    try {
      const result = await loginPatientPortalSession({ email: email.trim(), password });
      if (!result.ok) {
        throw new Error(result.detail || 'Invalid email or password. Please try again.');
      }
      router.push('/portal/patient/home');
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Unable to sign in. Please try again.');
    } finally {
      setLoading(false);
    }
  }

  return (
    <div style={S.page}>
      <div style={S.glow} />
      <div style={S.card}>
        <div style={S.logoRow}>
          <svg width="32" height="32" viewBox="0 0 36 36" fill="none">
            <polygon points="18,2 33,10 33,26 18,34 3,26 3,10" fill="#FF4D00" />
            <text x="18" y="23" textAnchor="middle" fill="#050505" fontSize="11" fontWeight="900" fontFamily="sans-serif">FQ</text>
          </svg>
          <div style={{ fontSize: '13px', fontWeight: 900, letterSpacing: '0.15em', textTransform: 'uppercase' }}>
            FUSION<span style={{ color: '#FF4D00' }}>EMS</span>
          </div>
        </div>
        <div style={S.tag}>PATIENT BILLING PORTAL</div>
        <h1 style={S.title}>Account Sign In</h1>

        {error && <div style={S.error}>{error}</div>}

        <form onSubmit={handleSubmit}>
          <div style={S.fieldGroup}>
            <label style={S.label} htmlFor="email">Email Address</label>
            <input
              id="email"
              type="email"
              autoComplete="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              placeholder="your@email.com"
              style={S.field}
              required
            />
          </div>
          <div style={S.fieldGroup}>
            <label style={S.label} htmlFor="password">Password</label>
            <input
              id="password"
              type="password"
              autoComplete="current-password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              placeholder="••••••••"
              style={S.field}
              required
            />
          </div>
          <button
            type="submit"
            disabled={loading}
            style={{ ...S.btn, ...(loading ? S.btnDisabled : {}) }}
          >
            {loading ? 'Signing In…' : 'Sign In to Portal'}
          </button>
        </form>

        <div style={S.links}>
          <Link href="/portal/patient/forgot-password" style={S.linkStyle}>Forgot Password?</Link>
          <Link href="/portal/patient/lookup" style={{ ...S.linkStyle, color: '#FF4D00' }}>Look Up Account →</Link>
        </div>

        <div style={{ marginTop: '28px', paddingTop: '20px', borderTop: '1px solid var(--color-border-default)', textAlign: 'center' }}>
          <Link href="/portal/patient" style={{ fontSize: '11px', color: 'var(--color-text-muted)', textDecoration: 'none', letterSpacing: '0.1em', textTransform: 'uppercase' }}>
            ← Back to Billing Portal
          </Link>
        </div>
      </div>
    </div>
  );
}
