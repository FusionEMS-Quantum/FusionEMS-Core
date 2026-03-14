'use client';

import { useState } from 'react';
import Link from 'next/link';
import { requestPatientPortalPasswordReset } from '@/services/api';
import { FQMark } from '@/components/branding/QuantumLogo';

const S: Record<string, React.CSSProperties> = {
  page: { minHeight: '100vh', background: 'var(--color-bg-base)', display: 'flex', alignItems: 'center', justifyContent: 'center', padding: '24px 16px', fontFamily: 'var(--font-body)', position: 'relative' },
  glow: { position: 'absolute', top: 0, left: 0, width: '100%', height: '300px', background: 'linear-gradient(to bottom, rgba(255,106,0,0.04), transparent)', pointerEvents: 'none' },
  card: { position: 'relative', zIndex: 1, width: '100%', maxWidth: '420px', background: 'var(--color-bg-surface)', border: '1px solid var(--color-border-default)', padding: '40px 36px', clipPath: 'polygon(0 0,calc(100% - 16px) 0,100% 16px,100% 100%,0 100%)', boxShadow: '0 24px 80px rgba(0,0,0,0.4)' },
  tag: { fontSize: '10px', fontWeight: 700, letterSpacing: '0.2em', textTransform: 'uppercase', color: 'var(--color-text-muted)', marginBottom: '6px' },
  title: { fontSize: '1.5rem', fontWeight: 900, letterSpacing: '-0.01em', color: 'var(--color-text-primary)', marginBottom: '12px' },
  sub: { fontSize: '13px', color: 'var(--color-text-muted)', lineHeight: 1.6, marginBottom: '28px' },
  label: { display: 'block', fontSize: '11px', fontWeight: 700, letterSpacing: '0.15em', textTransform: 'uppercase', color: 'var(--color-text-muted)', marginBottom: '8px' },
  field: { width: '100%', background: 'var(--color-bg-input)', border: '1px solid var(--color-border-default)', color: 'var(--color-text-primary)', fontSize: '14px', padding: '11px 14px', outline: 'none', clipPath: 'polygon(0 0,calc(100% - 6px) 0,100% 6px,100% 100%,0 100%)', boxSizing: 'border-box', marginBottom: '20px' },
  btn: { width: '100%', padding: '13px', background: 'var(--q-orange)', border: 'none', color: '#000', fontSize: '12px', fontWeight: 700, letterSpacing: '0.15em', textTransform: 'uppercase', cursor: 'pointer', clipPath: 'polygon(0 0,calc(100% - 8px) 0,100% 8px,100% 100%,0 100%)', boxShadow: '0 0 20px rgba(255,106,0,0.2)', marginTop: '8px' },
  success: { background: 'rgba(16,185,129,0.08)', border: '1px solid rgba(16,185,129,0.25)', color: 'var(--color-status-active)', padding: '16px', fontSize: '13px', lineHeight: 1.6, clipPath: 'polygon(0 0,calc(100% - 6px) 0,100% 6px,100% 100%,0 100%)' },
  error: { background: 'rgba(229,57,53,0.1)', border: '1px solid rgba(229,57,53,0.3)', color: '#EF5350', padding: '10px 14px', fontSize: '12px', marginBottom: '16px', clipPath: 'polygon(0 0,calc(100% - 6px) 0,100% 6px,100% 100%,0 100%)' },
};

export default function ForgotPasswordPage() {
  const [email, setEmail] = useState('');
  const [sent, setSent] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!email.trim()) return;
    setLoading(true);
    setError(null);
    try {
      const result = await requestPatientPortalPasswordReset({ email: email.trim() });
      if (!result.ok && result.status !== 404) {
        throw new Error('Unable to process request. Please try again.');
      }
      setSent(true);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Unable to process request.');
    } finally {
      setLoading(false);
    }
  }

  return (
    <div style={S.page}>
      <div style={S.glow} />
      <div style={S.card}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '10px', marginBottom: '28px' }}>
          <FQMark size={30} />
          <div style={{ fontSize: '12px', fontWeight: 900, letterSpacing: '0.15em', textTransform: 'uppercase' }}>
            FUSION<span style={{ color: 'var(--q-orange)' }}>EMS</span>
          </div>
        </div>

        <div style={S.tag}>PATIENT BILLING PORTAL</div>
        <h1 style={S.title}>Reset Password</h1>
        <p style={S.sub}>
          Enter your account email address and we&apos;ll send a password reset link if an account exists.
        </p>

        {sent ? (
          <div style={S.success}>
            <div style={{ fontWeight: 700, marginBottom: '6px' }}>Reset Link Sent</div>
            If an account with that email exists, a password reset link has been sent. Check your inbox and spam folder.
          </div>
        ) : (
          <>
            {error && <div style={S.error}>{error}</div>}
            <form onSubmit={handleSubmit}>
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
              <button
                type="submit"
                disabled={loading}
                style={{ ...S.btn, ...(loading ? { opacity: 0.6, cursor: 'not-allowed' } : {}) }}
              >
                {loading ? 'Sending…' : 'Send Reset Link'}
              </button>
            </form>
          </>
        )}

        <div style={{ marginTop: '24px', textAlign: 'center' }}>
          <Link href="/portal/patient/login" style={{ fontSize: '12px', color: 'var(--color-text-muted)', textDecoration: 'none' }}>
            ← Back to Sign In
          </Link>
        </div>
      </div>
    </div>
  );
}
