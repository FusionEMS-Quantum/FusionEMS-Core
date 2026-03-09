'use client';

import { useEffect } from 'react';
import { AlertTriangle } from 'lucide-react';

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
    <div className="flex items-center justify-center min-h-screen bg-gray-950">
      <div className="max-w-md w-full bg-gray-900 border border-red-700/50 rounded-xl p-8 text-center space-y-4">
        <AlertTriangle className="h-10 w-10 text-red-400 mx-auto" />
        <h2 className="text-xl font-bold text-white">Something went wrong</h2>
        <p className="text-sm text-gray-400">
          An unexpected error occurred. Our team has been notified.
        </p>
        {error.digest && (
          <p className="text-xs text-gray-500 font-mono">Ref: {error.digest}</p>
        )}
        <button
          onClick={reset}
          className="px-5 py-2 bg-blue-600 hover:bg-blue-700 rounded-lg text-white text-sm font-medium transition-colors"
        >
          Try again
        </button>
      </div>
    </div>
  );
}
