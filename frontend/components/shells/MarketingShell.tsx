import Link from 'next/link';
import type { ReactNode } from 'react';
import QuantumLogo from '@/components/branding/QuantumLogo';

const NAV_LINKS = [
  { href: '/platform', label: 'Platform' },
  { href: '/billing-command', label: 'Billing Command' },
  { href: '/epcr', label: 'ePCR' },
  { href: '/fleet', label: 'Fleet' },
  { href: '/scheduling', label: 'Scheduling' },
  { href: '/communications', label: 'Communications' },
  { href: '/compliance', label: 'Compliance' },
  { href: '/roi', label: 'ROI' },
  { href: '/founder-command', label: 'Founder' },
];

function HeaderPortalButtons() {
  return (
    <div className="flex items-center gap-2">
      <Link href="/patient-billing-login" className="quantum-btn-sm">Patient Bill Pay Login</Link>
      <Link href="/facility-transport-login" className="quantum-btn-sm">Facility TransportLink Login</Link>
      <Link href="/founder-login" className="quantum-btn-primary">Founder Login</Link>
    </div>
  );
}

export default function MarketingShell({ children }: { children: ReactNode }) {
  return (
    <div className="min-h-screen bg-[#050505] text-zinc-100">
      <div className="fixed inset-0 pointer-events-none opacity-60"
        style={{
          backgroundImage:
            'radial-gradient(circle at 20% 20%, rgba(255,106,0,0.06), transparent 40%), radial-gradient(circle at 80% 10%, rgba(255,45,45,0.06), transparent 35%), linear-gradient(to right, rgba(255,255,255,0.02) 1px, transparent 1px), linear-gradient(to bottom, rgba(255,255,255,0.02) 1px, transparent 1px)',
          backgroundSize: 'auto, auto, 48px 48px, 48px 48px',
        }}
      />

      <header className="sticky top-0 z-50 border-b border-border-default bg-[rgba(7,9,13,0.92)] backdrop-blur-sm">
        <div className="max-w-[1600px] mx-auto px-6 h-16 flex items-center justify-between gap-4">
          <Link href="/" className="flex items-center gap-3">
            <QuantumLogo size="sm" />
          </Link>

          <nav className="hidden xl:flex items-center gap-1">
            {NAV_LINKS.map((item) => (
              <Link key={item.href} href={item.href} className="px-3 py-2 text-label uppercase tracking-widest text-zinc-500 hover:text-zinc-100 hover:bg-[#0A0A0B]-raised chamfer-4 transition-colors">
                {item.label}
              </Link>
            ))}
          </nav>

          <HeaderPortalButtons />
        </div>
      </header>

      <main className="relative z-10">{children}</main>

      <footer className="border-t border-border-default bg-black">
        <div className="max-w-[1600px] mx-auto px-6 py-6 flex items-center justify-between text-micro uppercase tracking-[0.16em] text-zinc-500">
          <span>Mission-critical public safety infrastructure</span>
          <span>FusionEMS Quantum</span>
        </div>
      </footer>
    </div>
  );
}
