'use client';

import React, { Suspense, useState, useCallback, useEffect } from 'react';
import Link from 'next/link';
import { useSearchParams } from 'next/navigation';
import { Input } from '@/components/ui/Input';
import { Button } from '@/components/ui/Button';
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
      className="relative min-h-screen overflow-hidden bg-bg-base text-text-primary flex items-center justify-center px-4 py-12"
    >
      <div
        aria-hidden="true"
        className="absolute inset-0 pointer-events-none opacity-85 quantum-field"
      />

      <div
        aria-hidden="true"
        className="absolute inset-0 pointer-events-none"
        style={{
          backgroundImage:
            'radial-gradient(circle at 55% 65%, transparent 0%, var(--color-bg-base) 62%, var(--color-bg-void) 100%)',
        }}
      />

      {/* Login surface */}
      <div className="relative z-10 w-full max-w-xl">
        <div className="chamfer-16 border border-border-strong bg-bg-panel shadow-elevation-4 overflow-hidden">
          <div className="flex">
            <div
              aria-hidden="true"
              className="w-[5px] bg-gradient-to-b from-orange-bright via-orange to-red"
            />

            <div className="flex-1 min-w-0">
              {/* Masthead */}
              <div className="px-6 pt-6 pb-5 border-b border-border-subtle">
                <div className="flex items-start justify-between gap-4">
                  <div className="min-w-0">
                    <img
                      src="/brand/logo-primary.svg"
                      alt="FusionEMS Quantum"
                      className="h-10 w-auto max-w-full"
                      style={{ filter: 'drop-shadow(0 10px 22px var(--color-brand-orange-glow))' }}
                    />
                    <div className="micro-caps mt-3">
                      <span className="text-text-muted">Command Access Gate</span>
                      <span className="mx-2 text-text-muted">•</span>
                      <span className="text-orange-bright">Zero-trust</span>
                      <span className="mx-2 text-text-muted">•</span>
                      <span className="text-text-muted">Audited</span>
                    </div>
                  </div>

                  <div className="flex flex-col items-end gap-2 shrink-0">
                    <span
                      className="micro-caps chamfer-4 px-2 py-1 border"
                      style={{
                        borderColor: 'var(--color-border-default)',
                        backgroundColor: 'var(--color-bg-input)',
                        color: 'var(--color-text-muted)',
                      }}
                    >
                      Encrypted Session
                    </span>
                    <span
                      className="micro-caps chamfer-4 px-2 py-1 border"
                      style={{
                        borderColor: 'var(--color-brand-red-dim)',
                        backgroundColor: 'var(--color-brand-red-ghost)',
                        color: 'var(--color-brand-red-bright)',
                      }}
                    >
                      Monitoring Active
                    </span>
                  </div>
                </div>
              </div>

              {/* Tabs */}
              <div className="px-6 pt-5">
                <div
                  className="grid grid-cols-2 gap-2"
                  role="tablist"
                  aria-label="Login mode"
                >
                  {TABS.map((tab) => {
                    const isActive = activeTab === tab.key;
                    return (
                      <button
                        key={tab.key}
                        type="button"
                        role="tab"
                        aria-selected={isActive}
                        onClick={() => handleTabChange(tab.key)}
                        className="relative chamfer-8 px-3 py-2.5 text-left focus-ring transition-all duration-fast ease-out border"
                        style={{
                          borderColor: isActive
                            ? 'var(--color-border-strong)'
                            : 'var(--color-border-subtle)',
                          background: isActive
                            ? 'linear-gradient(135deg, var(--color-brand-orange-ghost), transparent)'
                            : 'linear-gradient(180deg, var(--color-border-default), var(--color-border-subtle))',
                        }}
                      >
                        <div className="label-caps" style={{ color: isActive ? 'var(--color-text-primary)' : 'var(--color-text-muted)' }}>
                          {tab.label}
                        </div>
                        <div className="micro-caps mt-1" style={{ color: 'var(--color-text-muted)' }}>
                          {tab.key === 'staff' ? 'Agency & operations access' : 'Revenue command access'}
                        </div>

                        {isActive && (
                          <span
                            aria-hidden="true"
                            className="absolute left-2 right-2 -bottom-[1px] h-[2px]"
                            style={{
                              background: 'linear-gradient(90deg, var(--color-brand-red), var(--color-brand-orange))',
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
                  autoComplete="current-password"
                  value={password}
                  onChange={(e) => { setPassword(e.target.value); setError(''); }}
                  onKeyDown={handleKeyDown}
                  disabled={loading}
                />

                {error && (
                  <p role="alert" className="micro-caps" style={{ color: 'var(--color-brand-red-bright)' }}>
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

                <div className="flex items-center justify-center">
                  <Link
                    href="/forgot-password"
                    className="micro-caps focus-ring chamfer-4 px-2 py-1 transition-colors duration-fast ease-out"
                    style={{
                      color: 'var(--color-text-muted)',
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
                  <span className="flex-1" style={{ height: 1, backgroundColor: 'var(--color-border-subtle)' }} />
                  <span className="micro-caps" style={{ color: 'var(--color-text-muted)' }}>or</span>
                  <span className="flex-1" style={{ height: 1, backgroundColor: 'var(--color-border-subtle)' }} />
                </div>

                <a
                  href="/api/v1/auth/microsoft/login"
                  className="chamfer-8 focus-ring flex w-full items-center justify-center py-2.5 transition-all duration-fast ease-out border"
                  style={{
                    fontFamily: 'var(--font-label)',
                    fontSize: 'var(--text-label)',
                    fontWeight: 700,
                    letterSpacing: 'var(--tracking-label)',
                    textTransform: 'uppercase',
                    color: 'var(--color-text-primary)',
                    backgroundColor: 'var(--color-bg-input)',
                    borderColor: 'var(--color-border-default)',
                    textDecoration: 'none',
                    boxShadow: 'var(--elevation-1)',
                  }}
                  onMouseEnter={(e) => {
                    e.currentTarget.style.borderColor = 'var(--color-border-strong)';
                    e.currentTarget.style.boxShadow = 'var(--elevation-2)';
                  }}
                  onMouseLeave={(e) => {
                    e.currentTarget.style.borderColor = 'var(--color-border-default)';
                    e.currentTarget.style.boxShadow = 'var(--elevation-1)';
                  }}
                >
                  Sign in with Microsoft
                </a>
              </form>

              {/* Footer */}
              <div className="px-6 py-4 border-t border-border-subtle">
                <div className="micro-caps" style={{ color: 'var(--color-text-muted)' }}>
                  Protected by end-to-end encryption • Tenant-isolated • Audited
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
