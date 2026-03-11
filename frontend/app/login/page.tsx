'use client';

import React, { Suspense, useState, useCallback, useEffect } from 'react';
import Link from 'next/link';
import { useSearchParams } from 'next/navigation';
import { Input } from '@/components/ui/Input';
import { Button } from '@/components/ui/Button';
import QuantumLogo from '@/components/branding/QuantumLogo';
import { login } from '@/services/auth';

type TabKey = 'staff' | 'billing';

const TABS: { key: TabKey; label: string }[] = [
  { key: 'staff',   label: 'Staff Login'    },
  { key: 'billing', label: 'Billing Portal' },
];

function LoginPageInner() {
  const [activeTab, setActiveTab] = useState<TabKey>('staff');
  const [email, setEmail]         = useState('');
  const [password, setPassword]   = useState('');
  const [loading, setLoading]     = useState(false);
  const [error, setError]         = useState('');

  const searchParams = useSearchParams();

  useEffect(() => {
    const ssoError = searchParams.get('error');
    if (!ssoError) {
      return;
    }

    const ssoErrorMessages: Record<string, string> = {
      entra_denied: 'Microsoft login was denied. Contact your administrator.',
      no_account: 'No FusionEMS account is linked to that Microsoft identity.',
      entra_not_configured: 'Microsoft login is temporarily unavailable. Your administrator must complete Entra configuration.',
    };

    setError(
      ssoErrorMessages[ssoError]
        ?? 'Microsoft login could not be completed. Please retry or contact your administrator.'
    );
  }, [searchParams]);

  const handleTabChange = useCallback((key: TabKey) => {
    setActiveTab(key);
    setError('');
    setEmail('');
    setPassword('');
  }, []);

  const handleSubmit = useCallback(
    async (e?: React.FormEvent) => {
      e?.preventDefault();
      if (!email.trim()) {
        setError('Email address is required.');
        return;
      }
      if (!password.trim()) {
        setError('Password is required.');
        return;
      }
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

  const handleKeyDown = useCallback(
    (e: React.KeyboardEvent) => {
      if (e.key === 'Enter') handleSubmit();
    },
    [handleSubmit]
  );

  return (
    <div
      className="relative min-h-screen overflow-hidden bg-bg-base text-text-primary texture-powder flex flex-col items-center justify-center px-4 py-12"
    >
      <div
        aria-hidden="true"
        className="absolute inset-0 pointer-events-none opacity-80"
        style={{
          backgroundImage:
            'radial-gradient(circle at 18% 14%, var(--color-brand-orange-glow), transparent 34%), radial-gradient(circle at 86% 18%, var(--color-border-strong), transparent 36%), linear-gradient(to right, var(--color-border-subtle) 1px, transparent 1px), linear-gradient(to bottom, var(--color-border-subtle) 1px, transparent 1px)',
          backgroundSize: 'auto, auto, 46px 46px, 46px 46px',
        }}
      />

      {/* Login panel */}
      <div
        className="relative z-10 w-full max-w-md chamfer-12 border border-border-default bg-bg-panel shadow-elevation-4"
      >
        <div className="h-[2px] bg-gradient-to-r from-orange via-orange-bright to-transparent" />

        {/* Wordmark */}
        <div
          className="hud-rail flex flex-col items-center px-8 pt-8 pb-6 texture-powder"
          style={{ borderBottom: '1px solid var(--color-border-default)' }}
        >
          <div className="relative flex flex-col items-center">
            <div className="absolute -top-10 left-1/2 -translate-x-1/2 opacity-[0.08]">
              <img
                src="/brand/logo-monogram.svg"
                alt=""
                className="h-24 w-24"
                aria-hidden="true"
              />
            </div>

            <QuantumLogo size="lg" />
            <div className="mt-2 micro-caps text-center">
              <span className="text-orange-bright">Secure Access</span>
              <span className="mx-2 text-text-muted">•</span>
              <span className="text-text-muted">Billing-first infrastructure OS</span>
            </div>
          </div>
        </div>

        {/* Tab switcher */}
        <div className="px-6 pt-5">
          <div
            className="chamfer-4 flex p-0.5"
            style={{
              backgroundColor: 'var(--color-bg-input)',
              border:          '1px solid var(--color-border-subtle)',
            }}
          >
            {TABS.map((tab) => {
              const isActive = activeTab === tab.key;
              return (
                <button
                  key={tab.key}
                  type="button"
                  onClick={() => handleTabChange(tab.key)}
                  className="relative flex-1 py-2 transition-all duration-fast ease-out focus-ring"
                  style={{
                    fontFamily:    'var(--font-label)',
                    fontSize:      'var(--text-label)',
                    fontWeight:    600,
                    letterSpacing: 'var(--tracking-label)',
                    textTransform: 'uppercase',
                    color:         isActive
                      ? 'var(--color-text-primary)'
                      : 'var(--color-text-muted)',
                    backgroundColor: isActive
                      ? 'var(--color-bg-panel-raised)'
                      : 'transparent',
                    clipPath: 'var(--chamfer-4)',
                    outline: 'none',
                  }}
                >
                  {tab.label}
                  {/* Orange underline on active */}
                  {isActive && (
                    <span
                      aria-hidden="true"
                      className="absolute bottom-0 left-0 right-0"
                      style={{
                        height:          2,
                        backgroundColor: 'var(--q-orange)',
                      }}
                    />
                  )}
                </button>
              );
            })}
          </div>
        </div>

        {/* Form */}
        <form
          onSubmit={handleSubmit}
          className="flex flex-col gap-4 px-6 pb-6 pt-5"
          noValidate
        >
          <Input
            label={activeTab === 'staff' ? 'Staff Email' : 'Billing Email'}
            type="email"
            placeholder="name@agency.gov"
            autoComplete="email"
            value={email}
            onChange={(e) => { setEmail(e.target.value); setError(''); }}
            onKeyDown={handleKeyDown}
            disabled={loading}
          />

          <Input
            label="Password"
            type="password"
            placeholder="••••••••••••"
            autoComplete={activeTab === 'staff' ? 'current-password' : 'current-password'}
            value={password}
            onChange={(e) => { setPassword(e.target.value); setError(''); }}
            onKeyDown={handleKeyDown}
            disabled={loading}
          />

          {/* Inline error */}
          {error && (
            <p
              role="alert"
              className="micro-caps"
              style={{ color: 'var(--color-brand-red)' }}
            >
              {error}
            </p>
          )}

          <Button
            type="submit"
            variant="primary"
            size="lg"
            loading={loading}
            className="w-full mt-1"
          >
            Sign In
          </Button>

          <div className="flex justify-center">
            <Link
              href="/forgot-password"
              className="chamfer-4 px-2 py-1 transition-colors duration-fast ease-out focus-ring"
              style={{
                fontFamily:    'var(--font-label)',
                fontSize:      'var(--text-label)',
                fontWeight:    500,
                letterSpacing: 'var(--tracking-label)',
                textTransform: 'uppercase',
                color:         'var(--color-text-muted)',
                background:    'transparent',
                textDecoration: 'none',
              }}
              onMouseEnter={(e) =>
                (e.currentTarget.style.color = 'var(--color-text-secondary)')
              }
              onMouseLeave={(e) =>
                (e.currentTarget.style.color = 'var(--color-text-muted)')
              }
              aria-disabled={loading}
              tabIndex={loading ? -1 : 0}
              onClick={(e) => {
                if (loading) e.preventDefault();
              }}
            >
              Forgot password?
            </Link>
          </div>

          <div className="flex items-center gap-3 py-3">
            <span
              className="flex-1"
              style={{ height: 1, backgroundColor: 'var(--color-border-subtle)' }}
            />
            <span
              className="micro-caps"
              style={{ color: 'var(--color-text-muted)' }}
            >
              or
            </span>
            <span
              className="flex-1"
              style={{ height: 1, backgroundColor: 'var(--color-border-subtle)' }}
            />
          </div>

          <a
            href="/api/v1/auth/microsoft/login"
            className="chamfer-8 flex w-full items-center justify-center py-2.5 transition-colors duration-[150ms]"
            style={{
              fontFamily:      'var(--font-label)',
              fontSize:        'var(--text-label)',
              fontWeight:      600,
              letterSpacing:   'var(--tracking-label)',
              textTransform:   'uppercase',
              color:           'var(--color-text-primary)',
              backgroundColor: 'var(--color-bg-input)',
              border:          '1px solid var(--color-border-default)',
              textDecoration:  'none',
            }}
          >
            Sign in with Microsoft
          </a>

        </form>

        {/* Footer */}
        <div
          className="flex items-center justify-center gap-2 px-6 py-4"
          style={{ borderTop: '1px solid var(--color-border-subtle)' }}
        >
          <span
            className="micro-caps"
            style={{ color: 'var(--color-text-muted)' }}
          >
            Protected by end-to-end encryption
          </span>
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
