'use client';

import { useState } from 'react';
import { useRouter } from 'next/navigation';
import Link from 'next/link';
import { Suspense } from 'react';
import { useSearchParams } from 'next/navigation';
import { confirmPatientPortalPasswordReset } from '@/services/api';

const S: Record<string, React.CSSProperties> = {
  page: { minHeight: '100vh', background: 'var(--color-bg-base)', display: 'flex', alignItems: 'center', justifyContent: 'center', padding: '24px 16px', fontFamily: 'var(--font-body)', position: 'relative' },
  glow: { position: 'absolute', top: 0, left: 0, width: '100%', height: '300px', background: 'linear-gradient(to bottom, rgba(255,106,0,0.04), transparent)', pointerEvents: 'none' },
  card: { position: 'relative', zIndex: 1, width: '100%', maxWidth: '420px', background: 'var(--color-bg-surface)', border: '1px solid var(--color-border-default)', padding: '40px 36px', clipPath: 'polygon(0 0,calc(100% - 16px) 0,100% 16px,100% 100%,0 100%)', boxShadow: '0 24px 80px rgba(0,0,0,0.4)' },
  label: { display: 'block', fontSize: '11px', fontWeight: 700, letterSpacing: '0.15em', textTransform: 'uppercase', color: 'var(--color-text-muted)', marginBottom: '8px' },
  field: { width: '100%', background: 'var(--color-bg-input)', border: '1px solid var(--color-border-default)', color: 'var(--color-text-primary)', fontSize: '14px', padding: '11px 14px', outline: 'none', clipPath: 'polygon(0 0,calc(100% - 6px) 0,100% 6px,100% 100%,0 100%)', boxSizing: 'border-box', marginBottom: '20px' },
  btn: { width: '100%', padding: '13px', background: 'var(--q-orange)', border: 'none', color: '#000', fontSize: '12px', fontWeight: 700, letterSpacing: '0.15em', textTransform: 'uppercase', cursor: 'pointer', clipPath: 'polygon(0 0,calc(100% - 8px) 0,100% 8px,100% 100%,0 100%)', boxShadow: '0 0 20px rgba(255,106,0,0.2)', marginTop: '8px' },
  error: { background: 'rgba(229,57,53,0.1)', border: '1px solid rgba(229,57,53,0.3)', color: '#EF5350', padding: '10px 14px', fontSize: '12px', marginBottom: '16px', clipPath: 'polygon(0 0,calc(100% - 6px) 0,100% 6px,100% 100%,0 100%)' },
  success: { background: 'rgba(16,185,129,0.08)', border: '1px solid rgba(16,185,129,0.25)', color: 'var(--color-status-active)', padding: '16px', fontSize: '13px', lineHeight: 1.6, clipPath: 'polygon(0 0,calc(100% - 6px) 0,100% 6px,100% 100%,0 100%)' },
};

function ResetPasswordContent() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const token = searchParams.get('token') || '';

  const [password, setPassword] = useState('');
  const [confirm, setConfirm] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [done, setDone] = useState(false);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (password !== confirm) { setError('Passwords do not match.'); return; }
    if (password.length < 8) { setError('Password must be at least 8 characters.'); return; }
    setLoading(true);
    setError(null);
    try {
      const result = await confirmPatientPortalPasswordReset({ token, new_password: password });
      if (!result.ok) throw new Error('Reset failed. The link may have expired.');
      setDone(true);
      setTimeout(() => router.push('/portal/patient/login'), 2000);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Unable to reset password.');
    } finally {
      setLoading(false);
    }
  }

  return (
    <div style={S.page}>
      <div style={S.glow} />
      <div style={S.card}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '10px', marginBottom: '28px' }}>
          <svg width="30" height="30" viewBox="0 0 36 36" fill="none">
            <polygon points="18,2 33,10 33,26 18,34 3,26 3,10" fill="var(--q-orange)" />
            <text x="18" y="23" textAnchor="middle" fill="var(--color-bg-base)" fontSize="11" fontWeight="900" fontFamily="sans-serif">FQ</text>
          </svg>
          <div style={{ fontSize: '12px', fontWeight: 900, letterSpacing: '0.15em', textTransform: 'uppercase' }}>
            FUSION<span style={{ color: 'var(--q-orange)' }}>EMS</span>
          </div>
        </div>

        <h1 style={{ fontSize: '1.5rem', fontWeight: 900, color: 'var(--color-text-primary)', marginBottom: '24px' }}>Set New Password</h1>

        {done ? (
          <div style={S.success}>
            <div style={{ fontWeight: 700, marginBottom: '6px' }}>Password Updated</div>
            Your password has been reset. Redirecting to sign in…
          </div>
        ) : !token ? (
          <div style={S.error}>
            Invalid or missing reset token. Please request a new password reset link.
            <div style={{ marginTop: '12px' }}>
              <Link href="/portal/patient/forgot-password" style={{ color: 'var(--q-orange)', textDecoration: 'none', fontWeight: 700, fontSize: '11px' }}>Request Reset →</Link>
            </div>
          </div>
        ) : (
          <>
            {error && <div style={S.error}>{error}</div>}
            <form onSubmit={handleSubmit}>
              <label style={S.label} htmlFor="password">New Password</label>
              <input id="password" type="password" value={password} onChange={(e) => setPassword(e.target.value)} placeholder="At least 8 characters" style={S.field} required minLength={8} />
              <label style={S.label} htmlFor="confirm">Confirm Password</label>
              <input id="confirm" type="password" value={confirm} onChange={(e) => setConfirm(e.target.value)} placeholder="Repeat password" style={{ ...S.field, marginBottom: '0' }} required />
              <button type="submit" disabled={loading} style={{ ...S.btn, ...(loading ? { opacity: 0.6, cursor: 'not-allowed' } : {}) }}>
                {loading ? 'Updating…' : 'Set New Password'}
              </button>
            </form>
          </>
        )}

        <div style={{ marginTop: '24px', textAlign: 'center' }}>
          <Link href="/portal/patient/login" style={{ fontSize: '12px', color: 'var(--color-text-muted)', textDecoration: 'none' }}>← Back to Sign In</Link>
        </div>
      </div>
    </div>
  );
}

export default function ResetPasswordPage() {
  return (
    <Suspense fallback={<div style={{ minHeight: '100vh', background: 'var(--color-bg-base)' }} />}>
      <ResetPasswordContent />
    </Suspense>
  );
}
