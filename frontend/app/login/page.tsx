'use client';

import React, { Suspense, useState, useCallback, useEffect } from 'react';
import Link from 'next/link';
import { useSearchParams } from 'next/navigation';
import { login } from '@/services/auth';

function LoginPageInner() {
  const [email, setEmail]       = useState('');
  const [password, setPassword] = useState('');
  const [remember, setRemember] = useState(false);
  const [loading, setLoading]   = useState(false);
  const [error, setError]       = useState('');

  const searchParams = useSearchParams();

  useEffect(() => {
    const ssoError = searchParams.get('error');
    if (!ssoError) return;

    const ssoErrorMessages: Record<string, string> = {
      entra_denied: 'Microsoft login was denied. Contact your administrator.',
      no_account: 'No FusionEMS account is linked to that Microsoft identity.',
      entra_not_configured:
        'Microsoft login is temporarily unavailable. Your administrator must complete Entra configuration.',
    };

    setError(
      ssoErrorMessages[ssoError] ??
        'Microsoft login could not be completed. Please retry or contact your administrator.'
    );
  }, [searchParams]);

  const handleSubmit = useCallback(
    async (e?: React.FormEvent) => {
      e?.preventDefault();
      if (!email.trim()) { setError('Email address is required.'); return; }
      if (!password.trim()) { setError('Password is required.'); return; }
      setError('');
      setLoading(true);
      try {
        await login(email.trim(), password);
      } catch {
        setError('Authentication failed. Verify your credentials and try again.');
        setLoading(false);
      }
    },
    [email, password]
  );

  return (
    <div className="min-h-screen bg-[#0A0C0E] text-white overflow-hidden relative">

      {/* PRECISION GRID */}
      <div
        className="fixed inset-0 pointer-events-none"
        aria-hidden="true"
        style={{
          backgroundImage: 'linear-gradient(rgba(255,255,255,0.025) 1px, transparent 1px), linear-gradient(90deg, rgba(255,255,255,0.025) 1px, transparent 1px)',
          backgroundSize: '80px 80px',
        }}
      />

      {/* CHAMFER CORNER GEOMETRY */}
      <div className="fixed inset-0 pointer-events-none" aria-hidden="true">
        <div className="absolute top-0 left-0 w-24 h-24" style={{
          background: 'linear-gradient(135deg, rgba(243,106,33,0.18) 0%, transparent 60%)',
          clipPath: 'polygon(0 0, 100% 0, 0 100%)',
        }} />
        <div className="absolute top-0 right-0 w-24 h-24" style={{
          background: 'linear-gradient(225deg, rgba(243,106,33,0.10) 0%, transparent 60%)',
          clipPath: 'polygon(0 0, 100% 0, 100% 100%)',
        }} />
        <div className="absolute bottom-0 left-0 w-32 h-32" style={{
          background: 'linear-gradient(45deg, rgba(243,106,33,0.08) 0%, transparent 60%)',
          clipPath: 'polygon(0 0, 0 100%, 100% 100%)',
        }} />
      </div>

      <div className="relative z-10 mx-auto grid min-h-screen max-w-7xl lg:grid-cols-[1.1fr_0.9fr]">

        {/* ── BRAND COMMAND COLUMN (desktop) ── */}
        <div className="hidden lg:flex flex-col justify-between px-12 py-14 xl:px-20 xl:py-16 border-r border-white/[0.04]">
          <div className="flex items-center gap-3">
            <div className="w-1.5 h-1.5 bg-[#4E9F6E] shadow-[0_0_6px_#4E9F6E]" />
            <div className="text-[0.55rem] font-bold tracking-[0.2em] text-[#4E9F6E] uppercase">
              Authentication Required
            </div>
            <div className="ml-4 text-[0.55rem] font-bold tracking-[0.15em] text-[#66707A] uppercase">
              FusionEMS Quantum Platform
            </div>
          </div>

          <div className="max-w-2xl">
            <div className="mb-6">
              <div className="text-[6rem] xl:text-[8rem] font-black leading-none tracking-[-0.04em] text-white">
                FQ
              </div>
              <div className="mt-1 w-40 h-px bg-[#F36A21]" />
            </div>

            <h1 className="text-5xl xl:text-6xl font-black tracking-[0.08em] text-white leading-tight">
              FUSIONEMS
            </h1>
            <div className="mt-3 flex items-center gap-4">
              <div className="h-px flex-1 bg-[#F36A21]/40" />
              <span className="text-[0.7rem] font-black tracking-[0.4em] text-[#F36A21] uppercase">QUANTUM</span>
              <div className="h-px flex-1 bg-[#F36A21]/40" />
            </div>

            <p className="mt-10 max-w-xl text-base leading-7 text-[#8D98A3]">
              Unified EMS scheduling, workforce coordination, and response intelligence
              built for secure operational control.
            </p>

            <div className="mt-10 grid grid-cols-3 gap-3">
              {([
                ['24/7', 'System Uptime'],
                ['SSO',  'Microsoft Identity'],
                ['AES',  'Encrypted Access'],
              ] as const).map(([value, label]) => (
                <div
                  key={label}
                  className="border border-white/[0.06] bg-[#111417] px-5 py-4"
                  style={{ clipPath: 'polygon(0 0, calc(100% - 8px) 0, 100% 8px, 100% 100%, 8px 100%, 0 calc(100% - 8px))' }}
                >
                  <div className="text-xl font-black tracking-[0.05em] text-white">{value}</div>
                  <div className="mt-1 text-[0.6rem] font-bold tracking-[0.15em] text-[#66707A] uppercase">{label}</div>
                </div>
              ))}
            </div>
          </div>

          <div className="flex items-center gap-6 text-[0.6rem] font-bold tracking-[0.15em] text-[#66707A] uppercase">
            <span>Enterprise Access</span>
            <span className="w-1 h-1 bg-[#66707A]" />
            <span>Role-Based Permissions</span>
            <span className="w-1 h-1 bg-[#66707A]" />
            <span>Audit Ready</span>
          </div>
        </div>

        {/* ── LOGIN FORM COLUMN ── */}
        <div className="flex flex-col items-center justify-center px-5 py-8 sm:px-8 lg:px-10 xl:px-14">
          <div className="w-full max-w-lg">
            <div
              className="border border-white/[0.08] bg-[#111417] p-7 sm:p-9"
              style={{ clipPath: 'polygon(0 0, calc(100% - 16px) 0, 100% 16px, 100% 100%, 16px 100%, 0 calc(100% - 16px))' }}
            >
              {/* Mobile brand mark */}
              <div className="mb-8 lg:hidden text-center">
                <div className="text-6xl font-black leading-none tracking-[-0.04em] text-white">FQ</div>
                <div className="mt-2 w-20 h-px bg-[#F36A21] mx-auto" />
                <div className="mt-4 text-2xl font-black tracking-[0.15em] text-white">FUSIONEMS</div>
                <div className="mt-1 text-xs font-black tracking-[0.4em] text-[#F36A21]">QUANTUM</div>
              </div>

              {/* Status badge */}
              <div className="mb-6 flex items-center gap-2">
                <div className="w-1 h-1 bg-[#4E9F6E] shadow-[0_0_4px_#4E9F6E]" />
                <span className="text-[0.55rem] font-bold tracking-[0.2em] text-[#4E9F6E] uppercase">Protected Session Entry</span>
              </div>

              <h2 className="mb-2 text-2xl font-black tracking-[0.02em] text-white">
                Welcome Back
              </h2>
              <p className="mb-7 text-sm text-[#8D98A3]">
                Sign in to access scheduling, operations, and workforce tools.
              </p>

              <form onSubmit={handleSubmit} className="space-y-5" noValidate>
                <div>
                  <label htmlFor="email" className="mb-2 block text-[0.65rem] font-bold tracking-[0.15em] text-[#8D98A3] uppercase">
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
                    className="w-full border border-white/[0.08] bg-[#0A0C0E] px-4 py-3 text-white placeholder:text-[#66707A] text-sm outline-none transition duration-200 focus:border-[#F36A21]/50 focus:ring-1 focus:ring-[#F36A21]/20 disabled:opacity-50"
                    style={{ clipPath: 'polygon(0 0, calc(100% - 6px) 0, 100% 6px, 100% 100%, 6px 100%, 0 calc(100% - 6px))' }}
                  />
                </div>

                <div>
                  <div className="mb-2 flex items-center justify-between">
                    <label htmlFor="password" className="block text-[0.65rem] font-bold tracking-[0.15em] text-[#8D98A3] uppercase">
                      Password
                    </label>
                    <Link
                      href="/forgot-password"
                      tabIndex={loading ? -1 : 0}
                      onClick={(e) => { if (loading) e.preventDefault(); }}
                      className="text-[0.6rem] font-bold tracking-[0.12em] text-[#F36A21] uppercase transition hover:text-[#FF7A2F]"
                    >
                      Forgot Password?
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
                    className="w-full border border-white/[0.08] bg-[#0A0C0E] px-4 py-3 text-white placeholder:text-[#66707A] text-sm outline-none transition duration-200 focus:border-[#F36A21]/50 focus:ring-1 focus:ring-[#F36A21]/20 disabled:opacity-50"
                    style={{ clipPath: 'polygon(0 0, calc(100% - 6px) 0, 100% 6px, 100% 100%, 6px 100%, 0 calc(100% - 6px))' }}
                  />
                </div>

                {error && (
                  <div role="alert" className="flex items-center gap-2 border border-[#C93B2C]/30 bg-[#2B1414] px-4 py-2.5">
                    <div className="w-1 h-1 bg-[#C93B2C] flex-shrink-0" />
                    <p className="text-[0.65rem] font-bold text-[#E14B3B]">{error}</p>
                  </div>
                )}

                <div className="flex items-center justify-between">
                  <label className="flex items-center gap-2.5 text-[#8D98A3] cursor-pointer text-xs">
                    <input
                      type="checkbox"
                      checked={remember}
                      onChange={(e) => setRemember(e.target.checked)}
                      className="h-3.5 w-3.5 border border-white/20 bg-[#0A0C0E] accent-[#F36A21]"
                    />
                    Keep me signed in
                  </label>
                  <div className="flex items-center gap-1.5">
                    <div className="w-1 h-1 bg-[#4E9F6E] shadow-[0_0_4px_#4E9F6E]" />
                    <span className="text-[0.55rem] font-bold tracking-[0.15em] text-[#4E9F6E] uppercase">AES Encrypted</span>
                  </div>
                </div>

                <button
                  type="submit"
                  disabled={loading}
                  className="w-full bg-[#F36A21] px-4 py-3.5 text-[0.7rem] font-black tracking-[0.2em] text-white uppercase transition duration-200 hover:bg-[#FF7A2F] disabled:opacity-50 disabled:cursor-not-allowed"
                  style={{ clipPath: 'polygon(0 0, calc(100% - 10px) 0, 100% 10px, 100% 100%, 10px 100%, 0 calc(100% - 10px))' }}
                >
                  {loading ? 'Authenticating…' : 'Authenticate'}
                </button>
              </form>

              <div className="my-6 flex items-center gap-4">
                <div className="h-px flex-1 bg-white/[0.06]" />
                <span className="text-[0.5rem] font-bold tracking-[0.3em] text-[#66707A] uppercase">Or Continue With</span>
                <div className="h-px flex-1 bg-white/[0.06]" />
              </div>

              {/* Microsoft SSO — must be a full-page navigation, not a button */}
              <a
                href="/api/v1/auth/microsoft/login"
                className="flex w-full items-center justify-center gap-3 border border-white/[0.08] bg-[#0A0C0E] px-4 py-3 text-[0.65rem] font-bold tracking-[0.1em] text-[#C7CDD3] uppercase transition duration-200 hover:border-white/[0.15] hover:text-white"
                style={{ clipPath: 'polygon(0 0, calc(100% - 8px) 0, 100% 8px, 100% 100%, 8px 100%, 0 calc(100% - 8px))' }}
              >
                <svg viewBox="0 0 24 24" className="h-4 w-4 flex-shrink-0" aria-hidden="true">
                  <path fill="#f25022" d="M1 1h10v10H1z" />
                  <path fill="#7fba00" d="M13 1h10v10H13z" />
                  <path fill="#00a4ef" d="M1 13h10v10H1z" />
                  <path fill="#ffb900" d="M13 13h10v10H13z" />
                </svg>
                Sign in with Microsoft
              </a>

              <div className="mt-5 grid grid-cols-2 gap-3">
                <button
                  type="button"
                  className="border border-white/[0.08] bg-[#111417] px-4 py-3 text-[0.6rem] font-bold tracking-[0.15em] text-[#8D98A3] uppercase transition hover:border-white/[0.15] hover:text-white"
                  style={{ clipPath: 'polygon(0 0, calc(100% - 6px) 0, 100% 6px, 100% 100%, 0 100%)' }}
                >
                  Request Access
                </button>
                <button
                  type="button"
                  className="border border-[#F36A21]/20 bg-[#F36A21]/[0.06] px-4 py-3 text-[0.6rem] font-bold tracking-[0.15em] text-[#F36A21] uppercase transition hover:bg-[#F36A21]/[0.12]"
                  style={{ clipPath: 'polygon(6px 0, 100% 0, 100% calc(100% - 6px), calc(100% - 6px) 100%, 0 100%, 0 6px)' }}
                >
                  System Status
                </button>
              </div>

              <div className="mt-6 border-t border-white/[0.04] pt-5">
                <p className="text-center text-[0.5rem] font-bold tracking-[0.15em] text-[#66707A] uppercase">
                  Secure Gateway &mdash; FusionEMS Quantum Platform
                </p>
                <p className="mt-2 text-center text-[0.5rem] text-[#66707A] leading-relaxed">
                  Access is monitored and protected by enterprise security controls.
                </p>
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
    <Suspense>
      <LoginPageInner />
    </Suspense>
  );
}
