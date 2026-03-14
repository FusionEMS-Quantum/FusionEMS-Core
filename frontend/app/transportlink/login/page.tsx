'use client';

import React, { useState, useCallback, Suspense } from 'react';
import Link from 'next/link';
import { useRouter } from 'next/navigation';
import { Truck, Shield, Eye, EyeOff, AlertCircle, ChevronRight, Lock } from 'lucide-react';
import { loginTransportLink } from '@/services/api';

function TransportLinkLoginInner() {
  const router = useRouter();
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [showPw, setShowPw] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  const handleSubmit = useCallback(
    async (e?: React.FormEvent) => {
      e?.preventDefault();
      if (!email.trim()) { setError('Work email is required.'); return; }
      if (!password.trim()) { setError('Password is required.'); return; }
      setError('');
      setLoading(true);
      try {
        await loginTransportLink({ email: email.trim(), password });
        router.push('/transportlink/dashboard');
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Network error. Please try again.');
        setLoading(false);
      }
    },
    [email, password, router]
  );

  return (
    <div
      className="min-h-screen flex flex-col items-center justify-center px-4 py-12"
      style={{ backgroundColor: '#0A0A0C' }}
    >
      {/* Background grid */}
      <div
        className="absolute inset-0 pointer-events-none opacity-[0.03]"
        style={{
          backgroundImage: 'linear-gradient(rgba(255,115,26,0.8) 1px,transparent 1px),linear-gradient(90deg,rgba(255,115,26,0.8) 1px,transparent 1px)',
          backgroundSize: '40px 40px',
        }}
      />

      <div className="relative w-full max-w-md">
        {/* Logo */}
        <div className="flex flex-col items-center mb-8">
          <div
            className="w-14 h-14 flex items-center justify-center mb-3"
            style={{
              background: 'linear-gradient(135deg, #FF4500 0%, #FF7300 60%, #FFB800 100%)',
              clipPath: 'polygon(0 0, calc(100% - 10px) 0, 100% 10px, 100% 100%, 10px 100%, 0 calc(100% - 10px))',
            }}
          >
            <Truck className="w-6 h-6 text-white" strokeWidth={2.5} />
          </div>
          <div className="text-[13px] font-black tracking-[0.22em] text-white uppercase">TransportLink</div>
          <div className="text-[9px] tracking-[0.35em] text-[var(--q-orange)] uppercase font-medium mt-0.5">FusionEMS · Facility Portal</div>
        </div>

        {/* Panel */}
        <div
          className="border border-white/[0.08] bg-[#0E0E10] p-6 relative overflow-hidden"
          style={{ clipPath: 'polygon(0 0, calc(100% - 14px) 0, 100% 14px, 100% 100%, 14px 100%, 0 calc(100% - 14px))' }}
        >
          <div className="absolute inset-0 bg-gradient-to-br from-orange/[0.04] via-transparent to-transparent pointer-events-none" />
          <div className="relative">
            <div className="flex items-center justify-between mb-5">
              <div>
                <h1 className="text-h2 font-black text-white">Secure Access</h1>
                <p className="text-[10px] text-[var(--color-text-muted)] mt-0.5">Facility portal sign in</p>
              </div>
              <div className="p-2 border border-orange/20 bg-[var(--q-orange)]/5"
                style={{ clipPath: 'polygon(0 0, calc(100% - 5px) 0, 100% 5px, 100% 100%, 0 100%)' }}>
                <Lock className="w-4 h-4 text-[var(--q-orange)]" />
              </div>
            </div>

            {error && (
              <div className="flex items-start gap-2 p-3 mb-4 border border-red/25 bg-red/[0.06]"
                style={{ clipPath: 'polygon(0 0, calc(100% - 5px) 0, 100% 5px, 100% 100%, 0 100%)' }}>
                <AlertCircle className="w-3.5 h-3.5 text-red flex-shrink-0 mt-0.5" />
                <span className="text-[11px] text-red">{error}</span>
              </div>
            )}

            <form onSubmit={handleSubmit} className="space-y-4">
              <div className="space-y-1.5">
                <label className="text-[10px] font-bold uppercase tracking-widest text-[var(--color-text-muted)]">
                  Work Email
                </label>
                <input
                  type="email"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  placeholder="you@yourfacility.org"
                  className="w-full h-10 px-3 bg-[var(--color-bg-base)]/[0.04] border border-white/[0.08] focus:border-orange/40 focus:outline-none text-[12px] text-white placeholder:text-[var(--color-text-muted)] transition-colors"
                  style={{ clipPath: 'polygon(0 0, calc(100% - 5px) 0, 100% 5px, 100% 100%, 0 100%)' }}
                  autoComplete="email"
                />
              </div>

              <div className="space-y-1.5">
                <div className="flex items-center justify-between">
                  <label className="text-[10px] font-bold uppercase tracking-widest text-[var(--color-text-muted)]">Password</label>
                  <Link href="/forgot-password" className="text-[9px] text-[var(--q-orange)]/70 hover:text-[var(--q-orange)] transition-colors">
                    Forgot password?
                  </Link>
                </div>
                <div className="relative">
                  <input
                    type={showPw ? 'text' : 'password'}
                    value={password}
                    onChange={(e) => setPassword(e.target.value)}
                    placeholder="••••••••••••"
                    className="w-full h-10 px-3 pr-10 bg-[var(--color-bg-base)]/[0.04] border border-white/[0.08] focus:border-orange/40 focus:outline-none text-[12px] text-white placeholder:text-[var(--color-text-muted)] transition-colors"
                    style={{ clipPath: 'polygon(0 0, calc(100% - 5px) 0, 100% 5px, 100% 100%, 0 100%)' }}
                    autoComplete="current-password"
                  />
                  <button
                    type="button"
                    onClick={() => setShowPw((v) => !v)}
                    className="absolute right-2.5 top-1/2 -translate-y-1/2 text-[var(--color-text-muted)] hover:text-[var(--color-text-primary)] transition-colors"
                  >
                    {showPw ? <EyeOff className="w-3.5 h-3.5" /> : <Eye className="w-3.5 h-3.5" />}
                  </button>
                </div>
              </div>

              <button
                type="submit"
                disabled={loading}
                className="w-full h-10 bg-[var(--q-orange)] hover:bg-[#FF6A1A] disabled:opacity-50 disabled:cursor-not-allowed text-white text-[11px] font-black uppercase tracking-widest transition-colors flex items-center justify-center gap-2"
                style={{ clipPath: 'polygon(0 0, calc(100% - 6px) 0, 100% 6px, 100% 100%, 0 100%)' }}
              >
                {loading ? (
                  <>
                    <div className="w-3 h-3 border-2 border-white/30 border-t-white  animate-spin" />
                    Authenticating…
                  </>
                ) : (
                  <>
                    Sign In
                    <ChevronRight className="w-3.5 h-3.5" />
                  </>
                )}
              </button>
            </form>

            <div className="mt-5 pt-4 border-t border-white/[0.06] flex items-center justify-between">
              <span className="text-[10px] text-[var(--color-text-muted)]">Don&apos;t have access?</span>
              <Link
                href="/transportlink/request-access"
                className="text-[10px] font-semibold text-[var(--q-orange)] hover:text-[#FF6A1A] transition-colors flex items-center gap-1"
              >
                Request Access <ChevronRight className="w-2.5 h-2.5" />
              </Link>
            </div>
          </div>
        </div>

        {/* Security label */}
        <div className="flex items-center justify-center gap-2 mt-5">
          <Shield className="w-3 h-3 text-[var(--color-text-muted)]" />
          <span className="text-[9px] text-[var(--color-text-muted)] uppercase tracking-widest">
            Secured · CMS-Aware · Wisconsin-First
          </span>
        </div>
      </div>
    </div>
  );
}

export default function TransportLinkLoginPage() {
  return (
    <Suspense fallback={null}>
      <TransportLinkLoginInner />
    </Suspense>
  );
}
