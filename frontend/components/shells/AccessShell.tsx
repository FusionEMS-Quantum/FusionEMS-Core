import Link from 'next/link';
import type { ReactNode } from 'react';
import QuantumLogo from '@/components/branding/QuantumLogo';

export default function AccessShell({ title, subtitle, children }: { title: string; subtitle: string; children: ReactNode }) {
  return (
    <div className="min-h-screen bg-[#050505] text-zinc-100 flex flex-col relative overflow-hidden">
      <div className="absolute inset-0 pointer-events-none opacity-60"
        style={{
          backgroundImage:
            'radial-gradient(circle at 12% 10%, rgba(255,106,0,0.2), transparent 28%), radial-gradient(circle at 88% 12%, rgba(255,106,0,0.09), transparent 26%), linear-gradient(to right, rgba(255,255,255,0.02) 1px, transparent 1px), linear-gradient(to bottom, rgba(255,255,255,0.02) 1px, transparent 1px)',
          backgroundSize: 'auto, auto, 48px 48px, 48px 48px',
        }}
      />

      <header className="h-14 border-b border-border-default bg-[rgba(7,9,13,0.92)] backdrop-blur-sm flex items-center justify-between px-6 relative z-10">
        <Link href="/" className="flex items-center gap-2">
          <QuantumLogo size="sm" showWordmark={false} />
          <span className="text-label uppercase tracking-[0.16em] text-zinc-400">Platform Access</span>
        </Link>
        <Link href="/" className="text-label uppercase tracking-[0.16em] text-zinc-500 hover:text-zinc-100">Back to Site</Link>
      </header>

      <main className="flex-1 flex items-center justify-center px-4 py-10 relative z-10">
        <div className="w-full max-w-xl quantum-panel-strong p-6 space-y-4">
          <div className="h-[2px] bg-gradient-to-r from-brand-orange via-brand-orange-bright to-transparent" />
          <div>
            <div className="flex flex-wrap items-center gap-2">
              <div className="text-micro uppercase tracking-[0.16em] text-brand-orange-bright">FusionEMS Quantum</div>
              <span className="text-micro uppercase tracking-[0.14em] text-brand-orange-bright border border-brand-orange/30 bg-brand-orange/10 px-2 py-0.5 chamfer-4">OIDC Access Path</span>
            </div>
            <h1 className="text-h2 font-bold mt-1">{title}</h1>
            <p className="text-body text-zinc-500 mt-1">{subtitle}</p>
          </div>

          <div className="grid grid-cols-3 gap-2">
            {[
              ['Access Model', 'Role-based'],
              ['Audit Trail', 'Enabled'],
              ['Primary Sign-In', 'Microsoft'],
            ].map(([label, value]) => (
              <div key={label} className="border border-border-subtle bg-[rgba(10,10,11,0.52)] chamfer-8 p-2">
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
