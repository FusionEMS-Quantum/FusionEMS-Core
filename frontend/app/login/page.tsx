'use client';

import React, { Suspense, useState, useCallback, useEffect } from 'react';
import Link from 'next/link';
import { useSearchParams } from 'next/navigation';
import { login } from '@/services/auth';
import QuantumLogo from '@/components/branding/QuantumLogo';

function LoginPageInner() {
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [remember, setRemember] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  const searchParams = useSearchParams();

  useEffect(() => {
    const ssoError = searchParams.get('error');
    if (!ssoError) return;

    const ssoErrorMessages: Record<string, string> = {
      entra_denied: 'Microsoft access was denied. Contact your administrator.',
      no_account: 'No FusionEMS account linked to your Microsoft identity.',
      entra_not_configured: 'Microsoft authentication is temporarily unavailable.',
      founder_role_denied: 'Founder access requires elevated permissions.',
      founder_claim_denied: 'Access denied by group policy.',
      missing_authorization_code: 'Authorization failed. Please try again.',
      invalid_state: 'Session expired. Try signing in again.',
      missing_id_token: 'Identity verification failed. Try again.',
      missing_access_token: 'Authentication incomplete. Try again.',
      no_email_claim: 'Email not provided. Contact your administrator.',
    };

    setError(
      ssoErrorMessages[ssoError] ??
      'Authentication failed. Please try again or contact support.'
    );
  }, [searchParams]);

  const handleSubmit = useCallback(
    async (e?: React.FormEvent) => {
      e?.preventDefault();
      if (!email.trim()) { setError('Email is required'); return; }
      if (!password.trim()) { setError('Password is required'); return; }
      setError('');
      setLoading(true);
      try {
        await login(email.trim(), password);
      } catch {
        setError('Authentication failed. Check your credentials and try again.');
        setLoading(false);
      }
    },
    [email, password]
  );

  return (
    <div className="min-h-screen text-[var(--color-text-primary)] overflow-hidden relative"
      style={{ background: 'var(--color-bg-void)' }}>

      {/* PRECISION GRID — token-driven */}
      <div className="fixed inset-0 pointer-events-none"
        style={{
          backgroundImage: 'linear-gradient(rgba(255,255,255,0.02) 1px, transparent 1px), linear-gradient(90deg, rgba(255,255,255,0.02) 1px, transparent 1px)',
          backgroundSize: '64px 64px',
        }}
      />

      {/* SUBTLE ORANGE ACCENT GLOW — top-right corner */}
      <div className="fixed top-0 right-0 w-[500px] h-[500px] pointer-events-none"
        style={{ background: 'radial-gradient(circle at 80% 10%, rgba(243,106,33,0.08), transparent 60%)' }}
      />
      {/* Corner chamfer accents */}
      <div className="fixed top-0 right-0 w-[300px] h-[1px] pointer-events-none" style={{ background: 'linear-gradient(to left, rgba(243,106,33,0.3), transparent)' }} />
      <div className="fixed top-0 right-0 h-[200px] w-[1px] pointer-events-none" style={{ background: 'linear-gradient(to bottom, rgba(243,106,33,0.3), transparent)' }} />

      {/* MAIN CONTAINER */}
      <div className="relative z-10 min-h-screen flex flex-col items-center justify-center px-4">
        <div className="max-w-[1200px] w-full grid grid-cols-1 lg:grid-cols-[1.1fr_1fr] gap-12 lg:gap-20 items-center">

          {/* LEFT COLUMN — BRAND AUTHORITY */}
          <div className="hidden lg:flex flex-col justify-center">

            {/* LOGO */}
            <div className="mb-10">
              <QuantumLogo size="lg" />
            </div>

            {/* TAGLINE */}
            <div className="mb-10">
              <div className="flex items-center gap-3 mb-6">
                <div className="w-8 h-[2px]" style={{ background: 'var(--color-brand-orange)' }} />
                <span className="text-[0.6rem] font-bold tracking-[0.25em] uppercase" style={{ color: 'var(--color-brand-orange)' }}>Command Platform</span>
              </div>
              <h1 className="text-[3.2rem] font-black tracking-[-0.02em] leading-[1.05] mb-4" style={{ color: 'var(--color-text-primary)' }}>
                The Operating System<br />
                for Modern EMS
              </h1>
              <p className="text-base leading-relaxed max-w-md" style={{ color: 'var(--color-text-muted)' }}>
                Unified billing, ePCR, fleet, compliance, scheduling, and communications — engineered for mission-critical public safety operations.
              </p>
            </div>

            {/* CAPABILITY TILES */}
            <div className="grid grid-cols-3 gap-3 mb-10">
              {[
                { label: 'Billing', sub: 'Revenue capture' },
                { label: 'ePCR', sub: 'Clinical docs' },
                { label: 'Fleet', sub: 'Unit readiness' },
                { label: 'Compliance', sub: 'NEMSIS · HIPAA' },
                { label: 'Comms', sub: 'Voice · SMS' },
                { label: 'Dispatch', sub: 'Real-time CAD' },
              ].map((item) => (
                <div key={item.label}
                  className="chamfer-4 p-3"
                  style={{
                    background: 'var(--color-surface-primary)',
                    border: '1px solid var(--color-border-default)',
                  }}>
                  <div className="text-[0.7rem] font-bold uppercase tracking-[0.12em]" style={{ color: 'var(--color-text-primary)' }}>{item.label}</div>
                  <div className="text-[0.6rem] uppercase tracking-[0.1em] mt-0.5" style={{ color: 'var(--color-text-disabled)' }}>{item.sub}</div>
                </div>
              ))}
            </div>

            {/* TRUST BAR */}
            <div className="flex items-center gap-6 pt-6" style={{ borderTop: '1px solid var(--color-border-default)' }}>
              <span className="text-[0.55rem] font-bold tracking-[0.2em] uppercase" style={{ color: 'var(--color-text-disabled)' }}>HIPAA-Conscious</span>
              <span style={{ color: 'var(--color-border-default)' }}>|</span>
              <span className="text-[0.55rem] font-bold tracking-[0.2em] uppercase" style={{ color: 'var(--color-text-disabled)' }}>Multi-Tenant</span>
              <span style={{ color: 'var(--color-border-default)' }}>|</span>
              <span className="text-[0.55rem] font-bold tracking-[0.2em] uppercase" style={{ color: 'var(--color-text-disabled)' }}>AWS Multi-AZ</span>
            </div>
          </div>

          {/* RIGHT COLUMN — LOGIN PANEL */}
          <div className="w-full max-w-[440px] lg:max-w-none">
            {/* MOBILE HEADER */}
            <div className="mb-8 lg:hidden flex justify-center">
              <QuantumLogo size="md" />
            </div>

            {/* LOGIN CARD — chamfered, token-driven */}
            <div className="chamfer-8 relative"
              style={{
                background: 'var(--color-surface-primary)',
                border: '1px solid var(--color-border-default)',
                boxShadow: '0 16px 40px rgba(0,0,0,0.5), 0 0 0 1px var(--color-border-default)',
              }}>

              {/* TOP ACCENT BAR */}
              <div className="h-[2px]" style={{ background: 'linear-gradient(90deg, var(--color-brand-orange), transparent)' }} />

              <div className="p-8 lg:p-10">
                {/* HEADER */}
                <div className="mb-8">
                  <div className="flex items-center gap-2 mb-4">
                    <div className="w-1.5 h-1.5" style={{ background: 'var(--color-brand-orange)', boxShadow: '0 0 6px var(--color-brand-orange)' }} />
                    <span className="text-[0.6rem] font-bold tracking-[0.2em] uppercase" style={{ color: 'var(--color-brand-orange)' }}>Quantum Platform</span>
                  </div>
                  <h2 className="text-[1.6rem] font-black tracking-[-0.01em] mb-1" style={{ color: 'var(--color-text-primary)' }}>Platform Login</h2>
                  <p className="text-[0.8rem]" style={{ color: 'var(--color-text-muted)' }}>Secure access to the FusionEMS Quantum platform</p>
                </div>

                <form onSubmit={handleSubmit} className="space-y-5" noValidate>
                  {/* EMAIL */}
                  <div>
                    <label htmlFor="email" className="block text-[0.65rem] font-bold uppercase tracking-[0.15em] mb-2" style={{ color: 'var(--color-text-muted)' }}>
                      Work Email
                    </label>
                    <input
                      id="email"
                      type="email"
                      placeholder="name@agency.gov"
                      autoComplete="email"
                      value={email}
                      onChange={(e) => { setEmail(e.target.value); setError(''); }}
                      disabled={loading}
                      className="w-full chamfer-4 px-4 py-3 text-sm outline-none transition-colors duration-150 disabled:opacity-50"
                      style={{
                        background: 'var(--color-surface-secondary)',
                        border: '1px solid var(--color-border-default)',
                        color: 'var(--color-text-primary)',
                      }}
                      onFocus={(e) => { e.currentTarget.style.borderColor = 'var(--color-brand-orange)'; }}
                      onBlur={(e) => { e.currentTarget.style.borderColor = 'var(--color-border-default)'; }}
                    />
                  </div>

                  {/* PASSWORD */}
                  <div>
                    <div className="flex items-center justify-between mb-2">
                      <label htmlFor="password" className="block text-[0.65rem] font-bold uppercase tracking-[0.15em]" style={{ color: 'var(--color-text-muted)' }}>
                        Password
                      </label>
                      <Link href="/forgot-password" className="text-[0.65rem] font-bold transition-colors" style={{ color: 'var(--color-brand-orange)' }}>
                        Forgot?
                      </Link>
                    </div>
                    <input
                      id="password"
                      type="password"
                      placeholder="Enter your password"
                      autoComplete="current-password"
                      value={password}
                      onChange={(e) => { setPassword(e.target.value); setError(''); }}
                      disabled={loading}
                      className="w-full chamfer-4 px-4 py-3 text-sm outline-none transition-colors duration-150 disabled:opacity-50"
                      style={{
                        background: 'var(--color-surface-secondary)',
                        border: '1px solid var(--color-border-default)',
                        color: 'var(--color-text-primary)',
                      }}
                      onFocus={(e) => { e.currentTarget.style.borderColor = 'var(--color-brand-orange)'; }}
                      onBlur={(e) => { e.currentTarget.style.borderColor = 'var(--color-border-default)'; }}
                    />
                  </div>

                  {/* ERROR MESSAGE */}
                  {error && (
                    <div className="chamfer-4 p-3 flex items-start gap-3"
                      style={{ background: 'var(--color-brand-red-ghost)', border: '1px solid rgba(201,59,44,0.3)' }}>
                      <svg className="w-4 h-4 flex-shrink-0 mt-0.5" fill="currentColor" viewBox="0 0 20 20" style={{ color: 'var(--color-brand-red)' }}>
                        <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.707 7.293a1 1 0 00-1.414 1.414L8.586 10l-1.293 1.293a1 1 0 101.414 1.414L10 11.414l1.293 1.293a1 1 0 001.414-1.414L11.414 10l1.293-1.293a1 1 0 00-1.414-1.414L10 8.586 8.707 7.293z" clipRule="evenodd" />
                      </svg>
                      <p className="text-sm font-medium" style={{ color: 'var(--color-brand-red)' }}>{error}</p>
                    </div>
                  )}

                  {/* REMEMBER ME */}
                  <div className="flex items-center gap-2.5">
                    <input
                      id="remember" type="checkbox" checked={remember}
                      onChange={(e) => setRemember(e.target.checked)}
                      className="w-3.5 h-3.5 cursor-pointer accent-[var(--color-brand-orange)]"
                      style={{ background: 'var(--color-surface-secondary)', border: '1px solid var(--color-border-default)' }}
                    />
                    <label htmlFor="remember" className="text-[0.75rem] cursor-pointer" style={{ color: 'var(--color-text-muted)' }}>
                      Keep me signed in for 30 days
                    </label>
                  </div>

                  {/* SUBMIT */}
                  <button type="submit" disabled={loading}
                    className="quantum-btn-primary w-full py-3.5 text-[0.75rem]">
                    {loading ? (
                      <span className="flex items-center justify-center gap-2">
                        <div className="w-4 h-4 border-2 border-black/20 border-t-black rounded-full animate-spin" />
                        Authenticating…
                      </span>
                    ) : 'Sign In'}
                  </button>
                </form>

                {/* SSO DIVIDER */}
                <div className="my-6 flex items-center gap-3">
                  <div className="flex-1 h-px" style={{ background: 'var(--color-border-default)' }} />
                  <span className="text-[0.6rem] font-bold uppercase tracking-[0.15em]" style={{ color: 'var(--color-text-disabled)' }}>Or</span>
                  <div className="flex-1 h-px" style={{ background: 'var(--color-border-default)' }} />
                </div>

                {/* MICROSOFT SSO */}
                <a href="/api/v1/auth/microsoft/login"
                  className="chamfer-8 w-full flex items-center justify-center gap-3 py-3.5 text-[0.75rem] font-bold uppercase tracking-[0.12em] transition-all duration-200 relative overflow-hidden"
                  style={{
                    background: 'var(--color-surface-secondary)',
                    border: '1px solid var(--color-brand-orange)',
                    color: 'var(--color-text-primary)',
                    boxShadow: '0 0 20px rgba(243,106,33,0.15)',
                  }}>
                  <svg viewBox="0 0 24 24" className="h-4 w-4" aria-hidden="true">
                    <path fill="#f25022" d="M1 1h10v10H1z" />
                    <path fill="#7fba00" d="M13 1h10v10H13z" />
                    <path fill="#00a4ef" d="M1 13h10v10H1z" />
                    <path fill="#ffb900" d="M13 13h10v10H13z" />
                  </svg>
                  Microsoft Login
                </a>

                {/* FOOTER */}
                <div className="mt-8 pt-5 space-y-2.5 text-center" style={{ borderTop: '1px solid var(--color-border-default)' }}>
                  <p className="text-[0.7rem]" style={{ color: 'var(--color-text-disabled)' }}>
                    Don&apos;t have access?{' '}
                    <Link href="/early-access" className="font-bold" style={{ color: 'var(--color-brand-orange)' }}>Request access</Link>
                  </p>
                  <p className="text-[0.6rem]" style={{ color: 'var(--color-text-disabled)' }}>
                    Protected by enterprise security · <Link href="/privacy" className="hover:underline">Privacy Policy</Link>
                  </p>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

export default function LoginPage() {
  return (
    <Suspense fallback={<div className="min-h-screen" style={{ background: 'var(--color-bg-void)' }} />}>
      <LoginPageInner />
    </Suspense>
  );
}
