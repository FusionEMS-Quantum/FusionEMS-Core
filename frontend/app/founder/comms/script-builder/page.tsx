'use client';
import Link from 'next/link';
import { QuantumEmptyState } from '@/components/ui';

export default function ScriptBuilderPage() {
  return (
    <div className="p-5 min-h-screen">
      <div className="hud-rail pb-3 mb-6">
        <div className="micro-caps mb-1">Communications</div>
        <h1 className="text-h2 font-bold text-zinc-100">Script Builder</h1>
        <p className="text-body text-zinc-500 mt-1">Create and manage IVR call scripts and automated response templates.</p>
      </div>
      <div className="bg-[#0A0A0B] border border-border-DEFAULT chamfer-8 shadow-elevation-1">
        <QuantumEmptyState
          title="Not Yet Configured"
          description="This module is scheduled for an upcoming release. Contact your account manager for early access."
          icon={
            <svg width="48" height="48" viewBox="0 0 48 48" fill="none" stroke="currentColor" strokeWidth="1.5">
              <rect x="6" y="10" width="36" height="28" rx="2" />
              <path d="M6 18h36M16 10V6M32 10V6" />
              <circle cx="24" cy="30" r="4" />
            </svg>
          }
          action={
            <Link
              href="/founder"
                className="inline-flex items-center gap-2 px-4 py-2 text-label font-label uppercase tracking-[var(--tracking-label)] text-[#FF4D00] hover:text-[#FF4D00] transition-colors duration-fast"
            >
              &larr; Back to Command Center
            </Link>
          }
        />
      </div>
    </div>
  );
}
