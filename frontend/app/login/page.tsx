'use client';

import React, { Suspense, useState, useCallback, useEffect } from 'react';
import Link from 'next/link';
import { useSearchParams } from 'next/navigation';
import { login } from '@/services/auth';
import AccessShell from '@/components/shells/AccessShell';
import { Input } from '@/components/ui/Input';
import { Button } from '@/components/ui/Button';

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
      founder_role_denied: 'Elevated access requires additional permissions.',
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
      if (!email.trim()) {
        setError('Email is required');
        return;
      }
      if (!password.trim()) {
        setError('Password is required');
        return;
      }

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
    <AccessShell
      title="Platform Login"
      subtitle="Microsoft identity is the primary access path. Credential fallback remains available for controlled operator workflows."
    >
      <div className="space-y-5">
        <div className="quantum-panel-soft px-4 py-4">
          <div className="quantum-kicker mb-3">Operator Access</div>
          <div className="grid gap-3 sm:grid-cols-3">
            {[
              ['Identity', 'Microsoft Entra'],
              ['Session Model', 'OIDC / token-bound'],
              ['Audit Mode', 'Correlated + logged'],
            ].map(([label, value]) => (
              <div key={label} className="border border-[var(--color-border-subtle)] bg-[rgba(255,255,255,0.02)] px-3 py-3 chamfer-8">
                <div className="micro-caps">{label}</div>
                <div className="mt-1 text-label font-semibold uppercase tracking-[0.08em] text-zinc-100">{value}</div>
              </div>
            ))}
          </div>
        </div>

        <a href="/api/v1/auth/microsoft/login" className="quantum-btn-primary w-full min-h-[48px] justify-center text-sm">
          <svg viewBox="0 0 24 24" className="h-5 w-5" aria-hidden="true">
            <path fill="#f25022" d="M1 1h10v10H1z" />
            <path fill="#7fba00" d="M13 1h10v10H13z" />
            <path fill="#00a4ef" d="M1 13h10v10H1z" />
            <path fill="#ffb900" d="M13 13h10v10H13z" />
          </svg>
          Continue with Microsoft
        </a>

        <div className="flex items-center gap-3">
          <div className="h-px flex-1 bg-[var(--color-border-default)]" />
          <span className="micro-caps">Credential fallback</span>
          <div className="h-px flex-1 bg-[var(--color-border-default)]" />
        </div>

        {error && (
          <div className="border border-[rgba(201,59,44,0.35)] bg-[var(--color-brand-red-ghost)] px-4 py-3 chamfer-8">
            <p className="text-sm text-[var(--color-brand-red)] font-medium">{error}</p>
          </div>
        )}

        <form onSubmit={handleSubmit} className="space-y-4" noValidate>
          <Input
            id="email"
            label="Work Email"
            type="email"
            placeholder="name@agency.gov"
            autoComplete="email"
            value={email}
            onChange={(e) => {
              setEmail(e.target.value);
              setError('');
            }}
            disabled={loading}
          />

          <div className="space-y-2">
            <div className="flex items-center justify-between gap-3">
              <label htmlFor="password" className="label-caps">Password</label>
              <Link href="/forgot-password" className="micro-caps text-[var(--color-brand-orange-bright)] hover:text-white">
                Forgot password
              </Link>
            </div>
            <Input
              id="password"
              type="password"
              placeholder="Enter your password"
              autoComplete="current-password"
              value={password}
              onChange={(e) => {
                setPassword(e.target.value);
                setError('');
              }}
              disabled={loading}
            />
          </div>

          <label className="flex items-center gap-3 text-sm text-zinc-400 cursor-pointer">
            <input
              id="remember"
              type="checkbox"
              checked={remember}
              onChange={(e) => setRemember(e.target.checked)}
              className="h-4 w-4 accent-[var(--color-brand-orange)] bg-[var(--color-bg-input)] border-[var(--color-border-default)]"
            />
            Keep this workstation trusted for 30 days
          </label>

          <Button type="submit" variant="secondary" className="w-full" loading={loading}>
            {loading ? 'Authenticating…' : 'Sign in with credentials'}
          </Button>
        </form>

        <div className="border-t border-[var(--color-border-subtle)] pt-4 space-y-2 text-center">
          <p className="text-xs text-zinc-500">
            Need access? <Link href="/early-access" className="text-[var(--color-brand-orange-bright)] font-bold hover:text-white">Request platform access</Link>
          </p>
          <p className="text-[0.7rem] text-zinc-600">
            Protected by enterprise security • <Link href="/privacy" className="hover:text-zinc-400">Privacy Policy</Link>
          </p>
        </div>
      </div>
    </AccessShell>
  );
}

export default function LoginPage() {
  return (
    <Suspense fallback={<div className="min-h-screen bg-[var(--color-bg-base)]" />}>
      <LoginPageInner />
    </Suspense>
  );
}
