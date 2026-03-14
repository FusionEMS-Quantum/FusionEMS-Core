import Link from 'next/link';

export default function UnauthorizedPage() {
  return (
    <div className="min-h-screen bg-[var(--color-bg-base)] text-[var(--color-text-primary)] flex items-center justify-center px-6 py-12">
      <div className="w-full max-w-xl chamfer-12 border border-[var(--color-border-default)] bg-[var(--color-bg-panel)] shadow-[var(--elevation-3)] p-8">
        <div className="hud-rail pb-4 border-b border-[var(--color-border-subtle)]">
          <p className="micro-caps" style={{ color: 'var(--color-brand-red-bright)' }}>
            Access Denied
          </p>
          <h1 className="mt-2" style={{ fontSize: 'var(--text-h1)', fontWeight: 700 }}>
            Unauthorized Route Access
          </h1>
          <p className="mt-2 text-[var(--color-text-muted)]">
            Your session is valid, but the requested command surface requires a higher privilege boundary.
          </p>
        </div>

        <div className="mt-6 grid gap-3 sm:grid-cols-2">
          <Link href="/dashboard" className="quantum-btn-primary">
            Return to Dashboard
          </Link>
          <Link href="/login" className="quantum-btn">
            Re-authenticate
          </Link>
        </div>
      </div>
    </div>
  );
}
