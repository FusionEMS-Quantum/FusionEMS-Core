import type { ReactNode } from 'react';
import Link from 'next/link';

const MODULE_LINKS = [
  { href: '/_legacy_app/home', label: 'Home' },
  { href: '/_legacy_app/founder', label: 'Founder' },
  { href: '/_legacy_app/billing', label: 'Billing' },
  { href: '/_legacy_app/epcr', label: 'ePCR' },
  { href: '/_legacy_app/ops', label: 'Ops' },
  { href: '/_legacy_app/scheduling', label: 'Scheduling' },
  { href: '/_legacy_app/fleet', label: 'Fleet' },
  { href: '/_legacy_app/compliance', label: 'Compliance' },
  { href: '/_legacy_app/communications', label: 'Communications' },
  { href: '/_legacy_app/analytics', label: 'Analytics' },
  { href: '/_legacy_app/admin', label: 'Admin' },
];

export default function InternalAppLayout({ children }: { children: ReactNode }) {
  return (
    <div className="min-h-screen bg-[#050505] text-zinc-100 flex flex-col">
      <header className="h-14 border-b border-border-default bg-[rgba(7,9,13,0.92)] backdrop-blur-sm flex items-center justify-between px-5">
        <Link href="/_legacy_app/home" className="flex items-center gap-2">
          <div className="w-8 h-8 bg-brand-orange text-black flex items-center justify-center font-black chamfer-8">FQ</div>
          <span className="text-label uppercase tracking-[0.16em] text-zinc-400">Command Application</span>
        </Link>
        <Link href="/portal/agency" className="quantum-btn-sm">Secure Access</Link>
      </header>

      <div className="flex flex-1 min-h-0">
        <aside className="w-56 border-r border-border-subtle bg-black p-2 overflow-y-auto">
          {MODULE_LINKS.map((item) => (
            <Link key={item.href} href={item.href} className="block px-3 py-2 text-label uppercase tracking-widest text-zinc-500 hover:text-zinc-100 hover:bg-[#0A0A0B] chamfer-4 transition-colors">
              {item.label}
            </Link>
          ))}
        </aside>
        <main className="flex-1 min-h-0 overflow-y-auto p-5">{children}</main>
      </div>
    </div>
  );
}
