'use client';

import { useEffect } from 'react';
import { AlertTriangle } from 'lucide-react';
import Link from 'next/link';

export default function PatientPortalError({
  error,
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
  useEffect(() => {
    console.error('[FusionEMS:PatientPortal] Error:', error);
  }, [error]);

  return (
    <div className="flex items-center justify-center min-h-[60vh]">
      <div className="max-w-md w-full bg-gray-900 border border-red-700/50 rounded-xl p-8 text-center space-y-4">
        <AlertTriangle className="h-8 w-8 text-red-400 mx-auto" />
        <h2 className="text-lg font-bold text-white">Portal Error</h2>
        <p className="text-sm text-gray-400">We encountered an error loading your information. Please try again.</p>
        {error.digest && (
          <p className="text-xs text-gray-500 font-mono">Ref: {error.digest}</p>
        )}
        <div className="flex items-center justify-center gap-3">
          <button onClick={reset} className="px-4 py-2 bg-rose-600 hover:bg-rose-700 rounded-lg text-white text-sm font-medium">Retry</button>
          <Link href="/portal/patient/home" className="px-4 py-2 bg-gray-700 hover:bg-gray-600 rounded-lg text-white text-sm font-medium">Home</Link>
        </div>
      </div>
    </div>
  );
}
