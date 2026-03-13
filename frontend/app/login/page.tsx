'use client';

import React, { Suspense, useState, useCallback, useEffect } from 'react';
import Link from 'next/link';
import { useSearchParams } from 'next/navigation';
import { login } from '@/services/auth';

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
    <div className="min-h-screen bg-gradient-to-br from-slate-950 via-slate-900 to-slate-950 text-white overflow-hidden relative">
      
      {/* QUANTUM GRID BACKGROUND */}
      <div
        className="fixed inset-0 pointer-events-none opacity-40"
        style={{
          backgroundImage: 'radial-gradient(circle at 1px 1px, rgba(15, 207, 255, 0.3) 1px, transparent 1px)',
          backgroundSize: '50px 50px',
        }}
      />

      {/* ANIMATED QUANTUM ORBS */}
      <div className="fixed inset-0 overflow-hidden pointer-events-none">
        <div
          className="absolute -top-40 -left-40 w-96 h-96 rounded-full blur-3xl opacity-30"
          style={{
            background: 'radial-gradient(circle, rgba(255, 107, 53, 0.8) 0%, transparent 70%)',
            animation: 'pulse 8s ease-in-out infinite',
          }}
        />
        
        <div
          className="absolute -bottom-40 -right-40 w-96 h-96 rounded-full blur-3xl opacity-30"
          style={{
            background: 'radial-gradient(circle, rgba(16, 185, 129, 0.8) 0%, transparent 70%)',
            animation: 'pulse 10s ease-in-out infinite 1s',
          }}
        />
        
        <div
          className="absolute -top-40 -right-40 w-80 h-80 rounded-full blur-3xl opacity-20"
          style={{
            background: 'radial-gradient(circle, rgba(220, 38, 38, 0.8) 0%, transparent 70%)',
            animation: 'pulse 12s ease-in-out infinite 2s',
          }}
        />

        <style>{`
          @keyframes pulse {
            0%, 100% { transform: scale(1); }
            50% { transform: scale(1.1); }
          }
        `}</style>
      </div>

      {/* MAIN CONTAINER */}
      <div className="relative z-10 min-h-screen flex flex-col items-center justify-center px-4">
        <div className="max-w-6xl w-full grid grid-cols-1 lg:grid-cols-2 gap-8 lg:gap-12 items-center">

          {/* LEFT COLUMN - BRAND */}
          <div className="hidden lg:flex flex-col justify-center space-y-12">
            {/* LOGO & BRANDING */}
            <div className="space-y-6">
              <div className="inline-flex items-center gap-3 px-4 py-2 bg-quantum-orange/10 border border-quantum-orange/30 rounded-full">
                <div className="w-2 h-2 rounded-full bg-quantum-orange animate-pulse" />
                <span className="text-sm font-bold tracking-widest text-quantum-orange uppercase">Quantum Command</span>
              </div>

              <div className="space-y-3">
                <h1 className="text-7xl font-black tracking-tighter leading-none">
                  <span className="text-quantum-orange">Fusion</span>
                  <span className="text-white">EMS</span>
                </h1>
                <p className="text-4xl font-bold text-slate-400">Operational Control Redefined</p>
              </div>

              <div className="h-1 w-32 bg-gradient-to-r from-quantum-orange via-quantum-red to-transparent" />
            </div>

            {/* CAPABILITIES */}
            <div className="space-y-6">
              <div className="space-y-4">
                <div className="flex items-start gap-4">
                  <div className="w-12 h-12 rounded-lg bg-quantum-orange/10 border border-quantum-orange/30 flex items-center justify-center flex-shrink-0">
                    <svg className="w-6 h-6 text-quantum-orange" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 10V3L4 14h7v7l9-11h-7z" />
                    </svg>
                  </div>
                  <div>
                    <p className="font-bold text-white">Real-Time Dispatch</p>
                    <p className="text-sm text-slate-400">Live incident coordination and response</p>
                  </div>
                </div>

                <div className="flex items-start gap-4">
                  <div className="w-12 h-12 rounded-lg bg-quantum-green/10 border border-quantum-green/30 flex items-center justify-center flex-shrink-0">
                    <svg className="w-6 h-6 text-quantum-green" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
                    </svg>
                  </div>
                  <div>
                    <p className="font-bold text-white">Unified Operations</p>
                    <p className="text-sm text-slate-400">EMS, HEMS, Fire coordination in one platform</p>
                  </div>
                </div>

                <div className="flex items-start gap-4">
                  <div className="w-12 h-12 rounded-lg bg-quantum-red/10 border border-quantum-red/30 flex items-center justify-center flex-shrink-0">
                    <svg className="w-6 h-6 text-quantum-red" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 15v2m-6 4h12a2 2 0 002-2v-6a2 2 0 00-2-2H6a2 2 0 00-2 2v6a2 2 0 002 2zm10-10V7a4 4 0 00-8 0v4h8z" />
                    </svg>
                  </div>
                  <div>
                    <p className="font-bold text-white">Enterprise Security</p>
                    <p className="text-sm text-slate-400">HIPAA-compliant encryption and audit trails</p>
                  </div>
                </div>
              </div>
            </div>

            {/* STATS */}
            <div className="grid grid-cols-3 gap-4 pt-6 border-t border-slate-800">
              <div>
                <p className="text-3xl font-black text-quantum-orange">99.9%</p>
                <p className="text-xs text-slate-400 uppercase tracking-wide">Uptime SLA</p>
              </div>
              <div>
                <p className="text-3xl font-black text-quantum-green">50M+</p>
                <p className="text-xs text-slate-400 uppercase tracking-wide">Incidents Managed</p>
              </div>
              <div>
                <p className="text-3xl font-black text-quantum-blue">240+</p>
                <p className="text-xs text-slate-400 uppercase tracking-wide">Agencies</p>
              </div>
            </div>
          </div>

          {/* RIGHT COLUMN - LOGIN FORM */}
          <div className="w-full max-w-md">
            {/* MOBILE HEADER */}
            <div className="mb-8 lg:hidden text-center">
              <h1 className="text-5xl font-black tracking-tighter mb-2">
                <span className="text-quantum-orange">Fusion</span>
                <span className="text-white">EMS</span>
              </h1>
              <p className="text-slate-400 font-semibold">Operational Control Redefined</p>
            </div>

            {/* LOGIN CARD */}
            <div className="bg-gradient-to-br from-slate-900/80 to-slate-950/80 backdrop-blur-sm border border-quantum-orange/20 rounded-2xl p-8 shadow-2xl">
              
              {/* STATUS INDICATOR */}
              <div className="mb-8 flex items-center gap-3 p-3 bg-quantum-green/10 border border-quantum-green/30 rounded-lg">
                <div className="w-2.5 h-2.5 rounded-full bg-quantum-green animate-pulse" />
                <span className="text-sm font-bold text-quantum-green uppercase tracking-wide">System Operational</span>
              </div>

              <div className="mb-6">
                <h2 className="text-3xl font-black mb-2">Welcome</h2>
                <p className="text-slate-400">Access your operational dashboard</p>
              </div>

              <form onSubmit={handleSubmit} className="space-y-5" noValidate>
                {/* EMAIL */}
                <div>
                  <label htmlFor="email" className="block text-xs font-bold text-slate-400 uppercase tracking-wide mb-2">
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
                    className="w-full bg-slate-800/50 border border-slate-700 rounded-xl px-4 py-3.5 text-white placeholder:text-slate-500 text-sm outline-none transition duration-200 focus:border-quantum-orange focus:ring-2 focus:ring-quantum-orange/30 disabled:opacity-50"
                  />
                </div>

                {/* PASSWORD */}
                <div>
                  <div className="flex items-center justify-between mb-2">
                    <label htmlFor="password" className="block text-xs font-bold text-slate-400 uppercase tracking-wide">
                      Password
                    </label>
                    <Link
                      href="/forgot-password"
                      className="text-xs font-bold text-quantum-orange hover:text-quantum-orange_light transition"
                    >
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
                    className="w-full bg-slate-800/50 border border-slate-700 rounded-xl px-4 py-3.5 text-white placeholder:text-slate-500 text-sm outline-none transition duration-200 focus:border-quantum-orange focus:ring-2 focus:ring-quantum-orange/30 disabled:opacity-50"
                  />
                </div>

                {/* ERROR MESSAGE */}
                {error && (
                  <div className="p-4 bg-quantum-red/10 border border-quantum-red/30 rounded-lg flex items-start gap-3">
                    <svg className="w-5 h-5 text-quantum-red flex-shrink-0 mt-0.5" fill="currentColor" viewBox="0 0 20 20">
                      <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.707 7.293a1 1 0 00-1.414 1.414L8.586 10l-1.293 1.293a1 1 0 101.414 1.414L10 11.414l1.293 1.293a1 1 0 001.414-1.414L11.414 10l1.293-1.293a1 1 0 00-1.414-1.414L10 8.586 8.707 7.293z" clipRule="evenodd" />
                    </svg>
                    <p className="text-sm text-quantum-red font-medium">{error}</p>
                  </div>
                )}

                {/* REMEMBER ME */}
                <div className="flex items-center gap-3">
                  <input
                    id="remember"
                    type="checkbox"
                    checked={remember}
                    onChange={(e) => setRemember(e.target.checked)}
                    className="w-4 h-4 rounded bg-slate-800 border-slate-700 accent-quantum-orange cursor-pointer"
                  />
                  <label htmlFor="remember" className="text-sm text-slate-400 cursor-pointer">
                    Keep me signed in for 30 days
                  </label>
                </div>

                {/* SUBMIT BUTTON */}
                <button
                  type="submit"
                  disabled={loading}
                  className="w-full bg-gradient-to-r from-quantum-orange to-quantum-orange_light hover:from-quantum-orange_dark hover:to-quantum-orange text-white font-black uppercase tracking-wider py-4 rounded-xl transition duration-300 disabled:opacity-50 disabled:cursor-not-allowed text-sm"
                >
                  {loading ? (
                    <span className="flex items-center justify-center gap-2">
                      <div className="w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin" />
                      Authenticating...
                    </span>
                  ) : (
                    'Sign In'
                  )}
                </button>
              </form>

              {/* SSO DIVIDER */}
              <div className="my-6 flex items-center gap-3">
                <div className="flex-1 h-px bg-slate-700" />
                <span className="text-xs text-slate-500 font-bold uppercase">Or</span>
                <div className="flex-1 h-px bg-slate-700" />
              </div>

              {/* MICROSOFT SSO */}
              <a
                href="/api/v1/auth/microsoft/login"
                className="w-full flex items-center justify-center gap-3 bg-slate-800/50 border border-slate-700 hover:border-quantum-blue hover:bg-slate-800 text-white font-bold uppercase tracking-wide py-3.5 rounded-xl transition duration-200"
              >
                <svg viewBox="0 0 24 24" className="h-5 w-5" aria-hidden="true">
                  <path fill="#f25022" d="M1 1h10v10H1z" />
                  <path fill="#7fba00" d="M13 1h10v10H13z" />
                  <path fill="#00a4ef" d="M1 13h10v10H1z" />
                  <path fill="#ffb900" d="M13 13h10v10H13z" />
                </svg>
                <span className="text-sm">Microsoft Account</span>
              </a>

              {/* FOOTER */}
              <div className="mt-8 pt-6 border-t border-slate-800 space-y-3 text-center">
                <p className="text-xs text-slate-500">
                  Don't have access? <Link href="/early-access" className="text-quantum-orange font-bold hover:text-quantum-orange_light">Request access</Link>
                </p>
                <p className="text-[0.7rem] text-slate-600">
                  Protected by enterprise security • <Link href="/privacy" className="hover:text-slate-400">Privacy Policy</Link>
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
    <Suspense fallback={<div className="min-h-screen bg-slate-950" />}>
      <LoginPageInner />
    </Suspense>
  );
}
