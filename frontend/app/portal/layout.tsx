'use client';

import React from 'react';
import Link from 'next/link';
import { usePathname } from 'next/navigation';

const NAV_LINKS = [
  { href: '/portal', label: 'Dashboard' },
  { href: '/portal/cad', label: 'CAD Dispatch' },
  { href: '/portal/epcr', label: 'ePCR Charts' },
  { href: '/portal/cases', label: 'Cases' },
  { href: '/portal/incidents', label: 'Incidents' },
  { href: '/portal/fire-rms', label: 'Fire RMS' },
  { href: '/portal/fleet', label: 'Fleet Intelligence' },
  { href: '/portal/billing', label: 'Billing' },
  { href: '/portal/scheduling', label: 'Scheduling' },
  { href: '/portal/staff', label: 'Personnel' },
  { href: '/portal/hems', label: 'HEMS Pilot' },
  { href: '/portal/kitlink', label: 'KitLink AR' },
];

const ADMIN_LINKS = [
  { href: '/portal/facilities', label: 'Facilities' },
  { href: '/portal/documents', label: 'Documents' },
  { href: '/portal/support', label: 'Support' },
]

function TopBar() {
  return (
    <header className="flex-shrink-0 flex items-center justify-between px-6 h-14 border-b border-zinc-900 bg-[#0A0A0B] relative z-10">
      <div className="absolute top-0 left-0 w-full h-[1px] bg-gradient-to-r from-[#FF4D00]/50 to-transparent pointer-events-none" />
      
      <Link href="/portal" className="flex items-center gap-3 group">
        <div
          className="w-8 h-8 bg-[#FF4D00] flex items-center justify-center text-[11px] font-black text-black group-hover:bg-[#E64500] transition-colors shadow-[0_0_15px_rgba(255,77,0,0.15)]"
          style={{ clipPath: 'polygon(0 0, calc(100% - 6px) 0, 100% 6px, 100% 100%, 0 100%)' }}
        >
          FQ
        </div>
        <div className="flex flex-col">
          <span className="text-xs font-black tracking-[0.15em] text-white uppercase leading-none">Fusion<span className="text-[#FF4D00]">EMS</span></span>
          <span className="text-[9px] font-bold text-zinc-500 tracking-[0.3em] uppercase mt-0.5">Quantum Node</span>
        </div>
      </Link>

      <div className="flex items-center gap-4">
        {/* Status indicator */}
        <div className="hidden md:flex items-center gap-2 mr-4 text-[9px] font-bold tracking-widest text-emerald-500 uppercase px-3 py-1 bg-emerald-500/10 border border-emerald-500/20" style={{ clipPath: 'polygon(0 0, calc(100% - 4px) 0, 100% 4px, 100% 100%, 0 100%)' }}>
          <span className="w-1.5 h-1.5  bg-emerald-500 animate-pulse" />
          SYSTEM NOMINAL
        </div>

        <button
          className="relative w-9 h-9 flex items-center justify-center text-zinc-400 hover:text-white bg-zinc-900 hover:bg-zinc-800 transition-colors border border-zinc-800"
          style={{ clipPath: 'polygon(0 0, calc(100% - 6px) 0, 100% 6px, 100% 100%, 0 100%)' }}
          aria-label="Notifications"
        >
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
            <path d="M18 8A6 6 0 0 0 6 8c0 7-3 9-3 9h18s-3-2-3-9" />
            <path d="M13.73 21a2 2 0 0 1-3.46 0" />
          </svg>
          <span className="absolute top-2 right-2 w-2 h-2  bg-[#FF4D00] shadow-[0_0_10px_rgba(255,77,0,0.8)] border border-zinc-900" />
        </button>
        <button 
          className="h-9 px-4 bg-zinc-900 border border-zinc-800 text-[10px] font-bold uppercase tracking-widest text-zinc-300 hover:text-white hover:bg-zinc-800 hover:border-zinc-600 transition-colors"
          style={{ clipPath: 'polygon(0 0, calc(100% - 6px) 0, 100% 6px, 100% 100%, 0 100%)' }}
        >
          Terminate
        </button>
      </div>
    </header>
  );
}

function Sidebar({ currentPath }: { currentPath: string }) {
  return (
    <aside className="w-56 flex-shrink-0 border-r border-zinc-900 bg-[#0A0A0B] flex flex-col overflow-y-auto">
      <div className="px-4 py-3 border-b border-zinc-900/50">
        <span className="text-[10px] font-bold tracking-[0.2em] text-zinc-600 uppercase">Operations</span>
      </div>
      <nav className="px-2 py-3 space-y-0.5 flex-1">
        {NAV_LINKS.map((link) => {
          const active = currentPath === link.href || currentPath.startsWith(link.href + '/');
          // For EXACT match if needed: const active = currentPath === link.href;
          return (
            <Link
              key={link.href}
              href={link.href}
              className={`block px-3 py-2 text-[11px] font-bold uppercase tracking-wider transition-all
                  ${active
                  ? 'text-[#FF4D00] bg-[#FF4D00]/5 border-l-2 border-[#FF4D00]'
                  : 'text-zinc-500 hover:text-zinc-200 hover:bg-zinc-900/50 hover:pl-4 border-l-2 border-transparent'
                }`}
            >
              {link.label}
            </Link>
          );
        })}
      </nav>

      <div className="px-4 py-3 border-t border-zinc-900/50 border-b">
        <span className="text-[10px] font-bold tracking-[0.2em] text-zinc-600 uppercase">Admin</span>
      </div>
      <nav className="px-2 py-3 space-y-0.5 mb-4">
        {ADMIN_LINKS.map((link) => {
          const active = currentPath === link.href || currentPath.startsWith(link.href + '/');
          return (
            <Link
              key={link.href}
              href={link.href}
              className={`block px-3 py-2 text-[11px] font-bold uppercase tracking-wider transition-all
                  ${active
                  ? 'text-[#FF4D00] bg-[#FF4D00]/5 border-l-2 border-[#FF4D00]'
                  : 'text-zinc-500 hover:text-zinc-200 hover:bg-zinc-900/50 hover:pl-4 border-l-2 border-transparent'
                }`}
            >
              {link.label}
            </Link>
          );
        })}
      </nav>
    </aside>
  );
}

function PatientTopBar() {
  return (
    <header className="flex-shrink-0 flex items-center justify-between px-6 h-14 border-b border-zinc-900 bg-[#0A0A0B]">
      <Link href="/portal/patient/lookup" className="flex items-center gap-3">
        <div
          className="w-8 h-8 bg-blue-500 flex items-center justify-center text-[11px] font-black text-white"
          style={{ clipPath: 'polygon(0 0, calc(100% - 6px) 0, 100% 6px, 100% 100%, 0 100%)' }}
        >
          FQ
        </div>
        <span className="text-xs font-black tracking-widest text-zinc-200 uppercase">Patient Portal</span>
      </Link>
    </header>
  );
}

function RepTopBar() {
  return (
    <header className="flex-shrink-0 flex items-center justify-between px-6 h-14 border-b border-zinc-900 bg-[#0A0A0B]">
      <div className="absolute top-0 right-0 w-1/4 h-[1px] bg-gradient-to-l from-purple-500/50 to-transparent pointer-events-none" />
      <Link href="/portal/rep/login" className="flex items-center gap-3">
        <div
          className="w-8 h-8 bg-purple-500 flex items-center justify-center text-[11px] font-black text-white"
          style={{ clipPath: 'polygon(0 0, calc(100% - 6px) 0, 100% 6px, 100% 100%, 0 100%)' }}
        >
          FQ
        </div>
        <span className="text-xs font-black tracking-widest text-zinc-200 uppercase">Authorized Representative</span>
      </Link>
    </header>
  );
}

export default function PortalLayout({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();
  const isPatientRoute = pathname.startsWith('/portal/patient/');
  const isRepRoute = pathname.startsWith('/portal/rep/');

  if (isPatientRoute) {
    return (
      <div className="flex flex-col min-h-screen bg-[#050505] text-zinc-200 font-sans">
        <PatientTopBar />
        <main className="flex-1 overflow-y-auto">{children}</main>
      </div>
    );
  }

  if (isRepRoute) {
    return (
      <div className="flex flex-col min-h-screen bg-[#050505] text-zinc-200 font-sans">
        <RepTopBar />
        <main className="flex-1 overflow-y-auto">{children}</main>
      </div>
    );
  }

  return (
    <div className="flex flex-col h-screen bg-[#050505] text-zinc-200 font-sans overflow-hidden">
      <TopBar />
      <div className="flex flex-1 overflow-hidden">
        <Sidebar currentPath={pathname} />
        <main className="flex-1 overflow-y-auto bg-[#050505]">
          {children}
        </main>
      </div>
    </div>
  );
}
