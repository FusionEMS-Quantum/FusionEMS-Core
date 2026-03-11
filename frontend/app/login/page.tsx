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
    <div className="min-h-screen text-white" style={{ background: 'radial-gradient(circle at top, rgba(255,120,40,0.16) 0%, transparent 30%), radial-gradient(circle at bottom right, rgba(255,140,0,0.12) 0%, transparent 28%), linear-gradient(180deg, #070707 0%, #0a0a0b 45%, #050505 100%)' }}>
      <div className="relative isolate overflow-hidden min-h-screen">
        {/* Page-level ambient layer — supplements the global fixed layer */}
        <div className="absolute inset-0" aria-hidden="true">
          <div className="absolute left-[-10%] top-[-8%] h-72 w-72 rounded-full bg-orange-500/10 blur-3xl" />
          <div className="absolute right-[-8%] top-[12%] h-80 w-80 rounded-full bg-amber-400/10 blur-3xl" />
          <div className="absolute bottom-[-10%] left-[35%] h-96 w-96 rounded-full bg-orange-600/10 blur-3xl" />
          <div className="absolute inset-0 bg-[linear-gradient(rgba(255,255,255,0.03)_1px,transparent_1px),linear-gradient(90deg,rgba(255,255,255,0.03)_1px,transparent_1px)] bg-[size:72px_72px] [mask-image:radial-gradient(circle_at_center,black,transparent_82%)]" />
        </div>

        <div className="relative z-10 mx-auto grid min-h-screen max-w-7xl lg:grid-cols-[1.1fr_0.9fr]">

          {/* ── Brand column (desktop only) ── */}
          <div className="hidden lg:flex flex-col justify-between px-12 py-14 xl:px-20 xl:py-16">
            <div>
              <div className="inline-flex items-center gap-3 rounded-full border border-orange-500/20 bg-white/5 px-4 py-2 text-sm text-orange-200 backdrop-blur-xl shadow-[0_0_40px_rgba(255,120,40,0.10)]">
                <span className="h-2.5 w-2.5 rounded-full bg-orange-400 shadow-[0_0_12px_rgba(255,140,50,0.9)]" />
                Secure workforce command portal
              </div>
            </div>

            <div className="max-w-2xl">
              <div className="mb-8 flex items-end gap-5">
                <div className="relative">
                  <div className="bg-gradient-to-b from-white via-zinc-100 to-zinc-500 bg-clip-text text-8xl font-black leading-none tracking-[-0.06em] text-transparent xl:text-9xl">
                    FQ
                  </div>
                  <div className="absolute left-4 top-[62%] h-3 w-40 -rotate-[18deg] rounded-full bg-gradient-to-r from-transparent via-orange-500 to-amber-300 shadow-[0_0_24px_rgba(255,120,40,0.85)]" />
                </div>
                <div className="mb-3 h-px flex-1 bg-gradient-to-r from-orange-500/70 via-orange-300/20 to-transparent" />
              </div>

              <h1 className="text-5xl font-black tracking-[0.12em] text-white xl:text-7xl">
                FUSIONEMS
              </h1>
              <div className="mt-4 flex items-center gap-4 text-lg font-semibold tracking-[0.65em] text-orange-400 xl:text-2xl">
                <span className="h-px flex-1 bg-orange-500/60" />
                <span>QUANTUM</span>
                <span className="h-px flex-1 bg-orange-500/60" />
              </div>

              <p className="mt-10 max-w-xl text-lg leading-8 text-zinc-300 xl:text-xl">
                Unified EMS scheduling, workforce coordination, and response intelligence built for
                secure operational control.
              </p>

              <div className="mt-12 grid max-w-2xl grid-cols-3 gap-4">
                {([
                  ['24/7', 'System availability'],
                  ['SSO',  'Microsoft identity'],
                  ['AES',  'Encrypted access'],
                ] as const).map(([value, label]) => (
                  <div
                    key={label}
                    className="rounded-3xl border border-white/10 bg-white/[0.04] px-5 py-5 backdrop-blur-xl shadow-[0_10px_35px_rgba(0,0,0,0.25)]"
                  >
                    <div className="text-2xl font-bold text-white">{value}</div>
                    <div className="mt-1 text-sm text-zinc-400">{label}</div>
                  </div>
                ))}
              </div>
            </div>

            <div className="flex items-center gap-6 text-sm text-zinc-500">
              <span>Enterprise access</span>
              <span className="h-1 w-1 rounded-full bg-zinc-600" />
              <span>Role-based permissions</span>
              <span className="h-1 w-1 rounded-full bg-zinc-600" />
              <span>Audit ready</span>
            </div>
          </div>

          {/* ── Login card column ── */}
          <div className="flex items-center justify-center px-5 py-8 sm:px-8 lg:px-10 xl:px-14">
            <div className="w-full max-w-lg">
              <div className="rounded-[2rem] border border-white/10 bg-white/[0.055] p-3 shadow-[0_25px_100px_rgba(0,0,0,0.55)] backdrop-blur-2xl">
                <div className="rounded-[1.6rem] border border-white/10 bg-[linear-gradient(180deg,rgba(255,255,255,0.08),rgba(255,255,255,0.03))] p-7 sm:p-9">

                  {/* Mobile brand mark */}
                  <div className="mb-8 lg:hidden text-center">
                    <div className="relative inline-block">
                      <div className="bg-gradient-to-b from-white via-zinc-200 to-zinc-500 bg-clip-text text-6xl font-black leading-none tracking-[-0.06em] text-transparent">
                        FQ
                      </div>
                      <div className="absolute left-3 top-9 h-2 w-28 -rotate-[18deg] rounded-full bg-gradient-to-r from-transparent via-orange-500 to-amber-300 shadow-[0_0_20px_rgba(255,120,40,0.8)]" />
                    </div>
                    <div className="mt-5 text-2xl font-black tracking-[0.18em] text-zinc-100">FUSIONEMS</div>
                    <div className="mt-1 text-sm font-bold tracking-[0.5em] text-orange-400">QUANTUM</div>
                  </div>

                  <div className="mb-8">
                    <div className="inline-flex items-center rounded-full border border-emerald-400/20 bg-emerald-400/10 px-3 py-1 text-xs font-medium text-emerald-300">
                      Protected session entry
                    </div>
                    <h2 className="mt-4 text-3xl font-bold tracking-tight text-white sm:text-4xl">
                      Welcome back
                    </h2>
                    <p className="mt-2 text-base leading-7 text-zinc-400">
                      Sign in to access scheduling, operations, and workforce tools.
                    </p>
                  </div>

                  <form onSubmit={handleSubmit} className="space-y-5" noValidate>
                    <div>
                      <label htmlFor="email" className="mb-2 block text-sm font-medium text-zinc-300">
                        Work email
                      </label>
                      <input
                        id="email"
                        type="email"
                        placeholder="name@fusionems.com"
                        autoComplete="email"
                        value={email}
                        onChange={(e) => { setEmail(e.target.value); setError(''); }}
                        disabled={loading}
                        className="w-full rounded-2xl border border-white/10 bg-black/35 px-4 py-3.5 text-white placeholder:text-zinc-500 outline-none transition duration-200 focus:border-orange-500/70 focus:bg-black/45 focus:ring-4 focus:ring-orange-500/15 disabled:opacity-50"
                      />
                    </div>

                    <div>
                      <div className="mb-2 flex items-center justify-between">
                        <label htmlFor="password" className="block text-sm font-medium text-zinc-300">
                          Password
                        </label>
                        <Link
                          href="/forgot-password"
                          tabIndex={loading ? -1 : 0}
                          onClick={(e) => { if (loading) e.preventDefault(); }}
                          className="text-xs font-medium text-orange-400 transition hover:text-orange-300"
                        >
                          Forgot password?
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
                        className="w-full rounded-2xl border border-white/10 bg-black/35 px-4 py-3.5 text-white placeholder:text-zinc-500 outline-none transition duration-200 focus:border-orange-500/70 focus:bg-black/45 focus:ring-4 focus:ring-orange-500/15 disabled:opacity-50"
                      />
                    </div>

                    {error && (
                      <p role="alert" className="text-sm font-medium text-red-400">
                        {error}
                      </p>
                    )}

                    <div className="flex items-center justify-between text-sm">
                      <label className="flex items-center gap-3 text-zinc-400 cursor-pointer">
                        <input
                          type="checkbox"
                          checked={remember}
                          onChange={(e) => setRemember(e.target.checked)}
                          className="h-4 w-4 rounded border-white/20 bg-black/40 text-orange-500"
                        />
                        Keep me signed in
                      </label>
                      <div className="rounded-full border border-orange-500/20 bg-orange-500/10 px-3 py-1 text-xs font-medium text-orange-300">
                        Encrypted
                      </div>
                    </div>

                    <button
                      type="submit"
                      disabled={loading}
                      className="group relative w-full overflow-hidden rounded-2xl bg-gradient-to-r from-orange-600 via-orange-500 to-amber-300 px-4 py-3.5 font-bold text-black shadow-[0_14px_34px_rgba(255,110,40,0.35)] transition duration-200 hover:-translate-y-0.5 hover:shadow-[0_18px_44px_rgba(255,110,40,0.45)] disabled:opacity-60 disabled:cursor-not-allowed disabled:hover:translate-y-0"
                    >
                      <span className="relative z-10">{loading ? 'Signing in…' : 'Sign In'}</span>
                      <span className="absolute inset-0 -translate-x-[120%] bg-gradient-to-r from-transparent via-white/40 to-transparent transition duration-700 group-hover:translate-x-[120%]" />
                    </button>
                  </form>

                  <div className="my-7 flex items-center gap-4">
                    <div className="h-px flex-1 bg-white/10" />
                    <span className="text-[11px] font-semibold uppercase tracking-[0.35em] text-zinc-500">
                      Or continue with
                    </span>
                    <div className="h-px flex-1 bg-white/10" />
                  </div>

                  {/* Microsoft SSO — must be a full-page navigation, not a button */}
                  <a
                    href="/api/v1/auth/microsoft/login"
                    className="group flex w-full items-center justify-center gap-3 rounded-2xl border border-white/10 bg-white/5 px-4 py-3.5 text-sm font-semibold text-zinc-100 transition duration-200 hover:border-white/20 hover:bg-white/10 hover:shadow-[0_10px_30px_rgba(255,255,255,0.05)]"
                  >
                    <svg viewBox="0 0 24 24" className="h-5 w-5" aria-hidden="true">
                      <path fill="#f25022" d="M1 1h10v10H1z" />
                      <path fill="#7fba00" d="M13 1h10v10H13z" />
                      <path fill="#00a4ef" d="M1 13h10v10H1z" />
                      <path fill="#ffb900" d="M13 13h10v10H13z" />
                    </svg>
                    Sign in with Microsoft
                  </a>

                  <div className="mt-7 grid grid-cols-2 gap-3">
                    <button
                      type="button"
                      className="rounded-2xl border border-white/10 bg-white/5 px-4 py-3 text-sm font-medium text-zinc-300 transition hover:bg-white/10"
                    >
                      Request Access
                    </button>
                    <button
                      type="button"
                      className="rounded-2xl border border-orange-500/20 bg-orange-500/10 px-4 py-3 text-sm font-medium text-orange-300 transition hover:bg-orange-500/15"
                    >
                      System Status
                    </button>
                  </div>

                  <p className="mt-6 text-center text-xs leading-6 text-zinc-500">
                    Access is monitored and protected by enterprise security controls.
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
    <Suspense>
      <LoginPageInner />
    </Suspense>
  );
}
