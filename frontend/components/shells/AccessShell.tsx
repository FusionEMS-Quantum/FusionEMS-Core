import Link from 'next/link';
import type { ReactNode } from 'react';
import QuantumLogo from '@/components/branding/QuantumLogo';

export default function AccessShell({ title, subtitle, children }: { title: string; subtitle: string; children: ReactNode }) {
  return (
    <div className="min-h-screen bg-[var(--color-bg-base)] text-zinc-100 flex flex-col relative overflow-hidden">
      <header className="h-16 border-b border-border-default bg-[rgba(7,9,13,0.92)] backdrop-blur-sm flex items-center justify-between px-6 relative z-10">
        <Link href="/" className="flex items-center gap-3 min-w-0">
          <QuantumLogo size="sm" />
          <span className="text-label uppercase tracking-[0.16em] text-zinc-400 hidden sm:inline">Secure Access</span>
        </Link>
        <Link href="/" className="text-label uppercase tracking-[0.16em] text-zinc-500 hover:text-zinc-100">Back to Site</Link>
      </header>

      <main className="flex-1 flex items-center justify-center px-4 py-10 relative z-10">
        <div className="w-full max-w-2xl quantum-page-frame p-6 md:p-8 space-y-5 shadow-elevation-2">
          <div className="quantum-command-band px-3 py-2">
            <span className="relative z-10 h-1.5 w-1.5 bg-[var(--color-status-active)] shadow-[0_0_6px_#22c55e]" />
            <span className="relative z-10 text-[var(--color-status-active)]">Encrypted Session Boundary</span>
            <span className="relative z-10 text-[var(--color-text-disabled)]">•</span>
            <span className="relative z-10">OIDC Ready</span>
          </div>
          <div>
            <div className="flex flex-wrap items-center gap-2">
              <div className="text-micro uppercase tracking-[0.16em] text-[var(--color-brand-orange-bright)]">FusionEMS Quantum</div>
              <span className="quantum-badge text-[var(--color-status-active)]">Encrypted Session</span>
            </div>
            <h1 className="text-h2 font-bold mt-1">{title}</h1>
            <p className="text-body text-zinc-500 mt-1">{subtitle}</p>
          </div>

          <div className="grid grid-cols-3 gap-2">
            {[
              ['Access Model', 'Role-based'],
              ['Audit Trail', 'Enabled'],
              ['Session Guard', 'Active'],
            ].map(([label, value]) => (
              <div key={label} className="quantum-panel p-3">
                <div className="text-micro uppercase tracking-[0.14em] text-zinc-500">{label}</div>
                <div className="text-label font-semibold text-zinc-100 mt-1">{value}</div>
              </div>
            ))}
          </div>

          {children}
        </div>
      </main>
    </div>
  );
}
