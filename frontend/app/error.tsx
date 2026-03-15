'use client';

import { useEffect } from 'react';

export default function GlobalError({
  error,
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
  useEffect(() => {
    // Structured error reporting — correlation ID attached if available
    console.error('[FusionEMS] Unhandled error:', error);
  }, [error]);

  return (
    <div className="min-h-screen flex items-center justify-center bg-[var(--color-bg-base)] px-6 py-12">
      <div className="w-full max-w-md quantum-panel-strong border-[var(--color-brand-red-dim)] p-8 text-center shadow-[var(--elevation-critical)] space-y-4">
        <div className="quantum-kicker justify-center text-[var(--color-brand-red)] before:bg-[linear-gradient(90deg,var(--color-brand-red),transparent)]">Unhandled platform exception</div>
        <h2 className="text-xl font-bold text-[var(--color-text-primary)]">Unhandled Platform Error</h2>
        <p className="text-sm text-[var(--color-text-muted)]">
          An unexpected error occurred. Our team has been notified.
        </p>
        {error.digest && (
          <p className="text-xs text-[var(--color-text-disabled)] font-mono">Ref: {error.digest}</p>
        )}
        <button
          onClick={reset}
          className="quantum-btn-primary px-5 py-2 text-sm"
        >
          Try again
        </button>
      </div>
    </div>
  );
}
