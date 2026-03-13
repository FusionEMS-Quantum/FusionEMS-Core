"use client";

import Link from 'next/link';
import type { ReactNode } from 'react';
import { useState } from 'react';
import { ArrowUpRight, Menu, X } from 'lucide-react';
import QuantumLogo from '@/components/branding/QuantumLogo';

const NAV_LINKS = [
  { href: '/', label: 'Home' },
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

const FOOTER_LINKS = [
  { href: '/architecture', label: 'Architecture' },
  { href: '/roi', label: 'ROI Intelligence' },
  { href: '/early-access', label: 'Early Access' },
  { href: '/contact', label: 'Contact' },
  { href: '/login', label: 'Staff Login' },
  { href: '/signup', label: 'Agency Intake' },
];

function HeaderPortalButtons() {
  return (
    <div className="hidden xl:flex items-center gap-2">
      <Link href="/patient-billing-login" className="quantum-btn-sm">Patient Bill Pay</Link>
      <Link href="/facility-transport-login" className="quantum-btn-sm">Facility Login</Link>
      <Link href="/login" className="quantum-btn-primary">Platform Login</Link>
    </div>
  );
}

export default function MarketingShell({ children }: { children: ReactNode }) {
  const [mobileNavOpen, setMobileNavOpen] = useState(false);

  return (
    <div className="min-h-screen bg-[#050505] text-zinc-100">
      <div className="fixed inset-0 pointer-events-none opacity-60"
        style={{
          backgroundImage:
            'radial-gradient(circle at 20% 20%, rgba(255,106,0,0.06), transparent 40%), radial-gradient(circle at 80% 10%, rgba(255,45,45,0.06), transparent 35%), linear-gradient(to right, rgba(255,255,255,0.02) 1px, transparent 1px), linear-gradient(to bottom, rgba(255,255,255,0.02) 1px, transparent 1px)',
          backgroundSize: 'auto, auto, 48px 48px, 48px 48px',
        }}
      />

      <div className="relative z-50 border-b border-[rgba(255,255,255,0.06)] bg-[rgba(255,77,0,0.08)]">
        <div className="max-w-[1600px] mx-auto px-6 py-2 flex items-center justify-between gap-4 text-[10px] uppercase tracking-[0.18em] text-zinc-400">
          <span>Public Safety Infrastructure</span>
          <div className="hidden md:flex items-center gap-5">
            <span>Billing-first activation</span>
            <span>OIDC-first access</span>
            <span>Deterministic platform operations</span>
          </div>
        </div>
      </div>

      <header className="sticky top-0 z-50 border-b border-border-default bg-[rgba(7,9,13,0.92)] backdrop-blur-sm">
        <div className="max-w-[1600px] mx-auto px-6 h-20 flex items-center justify-between gap-4">
          <Link href="/" className="flex items-center gap-3 min-w-0">
            <QuantumLogo size="sm" />
            <div className="hidden sm:block min-w-0">
              <div className="text-label uppercase tracking-[0.16em] text-zinc-100">FusionEMS Quantum</div>
              <div className="text-micro uppercase tracking-[0.18em] text-zinc-500">Unified Public Safety Operating Platform</div>
            </div>
          </Link>

          <nav className="hidden xl:flex items-center gap-1">
            {NAV_LINKS.map((item) => (
              <Link key={item.href} href={item.href} className="px-3 py-2 text-label uppercase tracking-widest text-zinc-500 hover:text-zinc-100 hover:bg-[#0A0A0B] chamfer-4 transition-colors">
                {item.label}
              </Link>
            ))}
          </nav>

          <div className="flex items-center gap-2">
            <HeaderPortalButtons />
            <Link href="/contact" className="hidden lg:inline-flex items-center gap-2 quantum-btn">
              Request Briefing
              <ArrowUpRight className="w-3.5 h-3.5" />
            </Link>
            <button
              type="button"
              onClick={() => setMobileNavOpen((value) => !value)}
              className="xl:hidden inline-flex items-center justify-center h-11 w-11 border border-border-default bg-[#0A0A0B] chamfer-8 text-zinc-200"
              aria-label={mobileNavOpen ? 'Close navigation' : 'Open navigation'}
            >
              {mobileNavOpen ? <X className="w-5 h-5" /> : <Menu className="w-5 h-5" />}
            </button>
          </div>
        </div>

        {mobileNavOpen && (
          <div className="xl:hidden border-t border-border-default bg-[rgba(7,9,13,0.98)]">
            <div className="px-6 py-5 flex flex-col gap-2">
              {NAV_LINKS.map((item) => (
                <Link
                  key={item.href}
                  href={item.href}
                  className="px-3 py-3 text-label uppercase tracking-widest text-zinc-300 border border-[rgba(255,255,255,0.06)] bg-[#0A0A0B] chamfer-8"
                  onClick={() => setMobileNavOpen(false)}
                >
                  {item.label}
                </Link>
              ))}
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-2 pt-2">
                <Link href="/patient-billing-login" className="quantum-btn-sm" onClick={() => setMobileNavOpen(false)}>Patient Bill Pay</Link>
                <Link href="/facility-transport-login" className="quantum-btn-sm" onClick={() => setMobileNavOpen(false)}>Facility Login</Link>
                <Link href="/login" className="quantum-btn-sm" onClick={() => setMobileNavOpen(false)}>Staff Login</Link>
                <Link href="/login" className="quantum-btn-primary" onClick={() => setMobileNavOpen(false)}>Platform Login</Link>
              </div>
            </div>
          </div>
        )}
      </header>

      <main className="relative z-10">{children}</main>

      <footer className="border-t border-border-default bg-black">
        <div className="max-w-[1600px] mx-auto px-6 py-10 grid lg:grid-cols-[1.2fr_1fr_1fr] gap-8">
          <div>
            <div className="flex items-center gap-3 mb-4">
              <QuantumLogo size="sm" />
              <div>
                <div className="text-label uppercase tracking-[0.16em] text-zinc-100">FusionEMS Quantum</div>
                <div className="text-micro uppercase tracking-[0.18em] text-zinc-500">Mission-critical public safety infrastructure</div>
              </div>
            </div>
            <p className="text-body text-zinc-500 max-w-xl">
              Built to unify billing, clinical, fleet, communications, compliance, and command workflows without fragmented route surfaces or opaque operational failure modes.
            </p>
          </div>

          <div>
            <div className="text-micro uppercase tracking-[0.18em] text-zinc-500 mb-3">Explore</div>
            <div className="grid gap-2">
              {FOOTER_LINKS.map((link) => (
                <Link key={link.href} href={link.href} className="text-body text-zinc-300 hover:text-white transition-colors">
                  {link.label}
                </Link>
              ))}
            </div>
          </div>

          <div>
            <div className="text-micro uppercase tracking-[0.18em] text-zinc-500 mb-3">Access Lanes</div>
            <div className="grid gap-2 text-body text-zinc-400">
              <span>Patient billing support and secure payment access</span>
              <span>Facility transport intake and scheduling coordination</span>
              <span>Staff operations, billing, and founder command surfaces</span>
            </div>
          </div>
        </div>
        <div className="border-t border-border-default">
          <div className="max-w-[1600px] mx-auto px-6 py-4 flex flex-col md:flex-row items-start md:items-center justify-between gap-3 text-micro uppercase tracking-[0.16em] text-zinc-600">
            <span>Deterministic platform posture • billing-first activation • observability-first execution</span>
            <span>FusionEMS Quantum</span>
          </div>
        </div>
      </footer>
    </div>
  );
}
