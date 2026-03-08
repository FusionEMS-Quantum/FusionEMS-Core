'use client';

import React, { useState } from 'react';
import Link from 'next/link';
import { usePathname } from 'next/navigation';

// Patient portal layout - isolated from internal ops portal
// Uses FusionEMS Quantum visual language: charcoal, orange, red accents

const PUBLIC_PATHS = [
  '/portal/patient',
  '/portal/patient/login',
  '/portal/patient/lookup',
  '/portal/patient/register',
  '/portal/patient/forgot-password',
  '/portal/patient/reset-password',
];

const NAV_ITEMS = [
  { href: '/portal/patient/home',          label: 'Account Home',     icon: 'home' },
  { href: '/portal/patient/invoices',      label: 'Invoices',         icon: 'invoice' },
  { href: '/portal/patient/payments',      label: 'Payments',         icon: 'payment' },
  { href: '/portal/patient/payment-plans', label: 'Payment Plans',    icon: 'plan' },
  { href: '/portal/patient/receipts',      label: 'Receipts',         icon: 'receipt' },
  { href: '/portal/patient/documents',     label: 'Documents',        icon: 'doc' },
  { href: '/portal/patient/activity',      label: 'Account Activity', icon: 'activity' },
  { href: '/portal/patient/messages',      label: 'Messages',         icon: 'message' },
  { href: '/portal/patient/support',       label: 'Billing Help',     icon: 'support' },
  { href: '/portal/patient/notifications', label: 'Notifications',    icon: 'bell' },
  { href: '/portal/patient/profile',       label: 'My Profile',       icon: 'profile' },
];

function NavIcon({ type }: { type: string }) {
  const props = { width: 15, height: 15, viewBox: '0 0 24 24', fill: 'none', stroke: 'currentColor', strokeWidth: 1.8, strokeLinecap: 'round' as const, strokeLinejoin: 'round' as const };
  switch (type) {
    case 'home':     return <svg {...props}><path d="M3 9l9-7 9 7v11a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2z"/><polyline points="9 22 9 12 15 12 15 22"/></svg>;
    case 'invoice':  return <svg {...props}><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><polyline points="14 2 14 8 20 8"/><line x1="9" y1="13" x2="15" y2="13"/><line x1="9" y1="17" x2="13" y2="17"/></svg>;
    case 'payment':  return <svg {...props}><rect x="1" y="4" width="22" height="16" rx="2" ry="2"/><line x1="1" y1="10" x2="23" y2="10"/></svg>;
    case 'plan':     return <svg {...props}><rect x="3" y="4" width="18" height="18" rx="2" ry="2"/><line x1="16" y1="2" x2="16" y2="6"/><line x1="8" y1="2" x2="8" y2="6"/><line x1="3" y1="10" x2="21" y2="10"/><polyline points="8 14 10 16 14 12"/></svg>;
    case 'receipt':  return <svg {...props}><polyline points="7 8 3 8 3 21 21 21 21 8 17 8"/><rect x="7" y="2" width="10" height="6" rx="1"/><line x1="7" y1="13" x2="17" y2="13"/><line x1="7" y1="17" x2="13" y2="17"/></svg>;
    case 'doc':      return <svg {...props}><path d="M13 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V9z"/><polyline points="13 2 13 9 20 9"/></svg>;
    case 'activity': return <svg {...props}><polyline points="22 12 18 12 15 21 9 3 6 12 2 12"/></svg>;
    case 'message':  return <svg {...props}><path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"/></svg>;
    case 'support':  return <svg {...props}><circle cx="12" cy="12" r="10"/><circle cx="12" cy="12" r="4"/><line x1="4.93" y1="4.93" x2="9.17" y2="9.17"/><line x1="14.83" y1="14.83" x2="19.07" y2="19.07"/><line x1="14.83" y1="9.17" x2="19.07" y2="4.93"/><line x1="4.93" y1="19.07" x2="9.17" y2="14.83"/></svg>;
    case 'bell':     return <svg {...props}><path d="M18 8A6 6 0 0 0 6 8c0 7-3 9-3 9h18s-3-2-3-9"/><path d="M13.73 21a2 2 0 0 1-3.46 0"/></svg>;
    case 'profile':  return <svg {...props}><path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2"/><circle cx="12" cy="7" r="4"/></svg>;
    case 'logout':   return <svg {...props}><path d="M9 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4"/><polyline points="16 17 21 12 16 7"/><line x1="21" y1="12" x2="9" y2="12"/></svg>;
    default:         return null;
  }
}

function PatientTopBar({ onMenuOpen }: { onMenuOpen: () => void }) {
  return (
    <header className="flex-shrink-0 flex items-center justify-between px-4 md:px-6 h-14 border-b border-zinc-900 bg-[#0A0A0B] sticky top-0 z-20">
      <div className="absolute top-0 left-0 w-full h-[1px] bg-gradient-to-r from-[#FF4D00]/40 via-[#FF4D00]/10 to-transparent pointer-events-none" />

      {/* Logo */}
      <Link href="/portal/patient" className="flex items-center gap-3 group">
        <div
          className="w-8 h-8 bg-[#FF4D00] flex items-center justify-center text-[11px] font-black text-black group-hover:bg-[#E64500] transition-colors shadow-[0_0_15px_rgba(255,77,0,0.2)]"
          style={{ clipPath: 'polygon(0 0, calc(100% - 6px) 0, 100% 6px, 100% 100%, 0 100%)' }}
        >
          FQ
        </div>
        <div className="flex flex-col">
          <span className="text-xs font-black tracking-[0.15em] text-white uppercase leading-none">
            Fusion<span className="text-[#FF4D00]">EMS</span>
          </span>
          <span className="text-[9px] font-bold text-zinc-500 tracking-[0.25em] uppercase mt-0.5">
            Patient Billing Portal
          </span>
        </div>
      </Link>

      <div className="flex items-center gap-3">
        {/* Secure badge */}
        <div className="hidden md:flex items-center gap-1.5 text-[9px] font-bold tracking-widest text-emerald-500 uppercase px-3 py-1 bg-emerald-500/10 border border-emerald-500/20"
          style={{ clipPath: 'polygon(0 0, calc(100% - 4px) 0, 100% 4px, 100% 100%, 0 100%)' }}>
          <svg width="10" height="10" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5">
            <rect x="3" y="11" width="18" height="11" rx="2" ry="2"/>
            <path d="M7 11V7a5 5 0 0 1 10 0v4"/>
          </svg>
          SECURE SESSION
        </div>

        {/* Quick pay CTA */}
        <Link
          href="/portal/patient/pay"
          className="hidden md:flex items-center gap-2 h-8 px-4 bg-[#FF4D00] text-black text-[10px] font-black tracking-widest uppercase hover:bg-[#E64500] transition-colors shadow-[0_0_15px_rgba(255,77,0,0.15)]"
          style={{ clipPath: 'polygon(0 0, calc(100% - 6px) 0, 100% 6px, 100% 100%, 0 100%)' }}
        >
          PAY NOW
        </Link>

        {/* Mobile menu */}
        <button
          onClick={onMenuOpen}
          className="md:hidden w-9 h-9 flex items-center justify-center text-zinc-400 hover:text-white bg-zinc-900 border border-zinc-800 transition-colors"
          style={{ clipPath: 'polygon(0 0, calc(100% - 6px) 0, 100% 6px, 100% 100%, 0 100%)' }}
          aria-label="Open menu"
        >
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
            <line x1="3" y1="6" x2="21" y2="6"/>
            <line x1="3" y1="12" x2="21" y2="12"/>
            <line x1="3" y1="18" x2="21" y2="18"/>
          </svg>
        </button>
      </div>
    </header>
  );
}

function PatientSidebar({ currentPath, onClose }: { currentPath: string; onClose?: () => void }) {
  return (
    <aside className="w-56 flex-shrink-0 border-r border-zinc-900 bg-[#0A0A0B] flex flex-col overflow-y-auto">
      <div className="px-4 py-3 border-b border-zinc-900/50">
        <span className="text-[9px] font-bold tracking-[0.2em] text-zinc-600 uppercase">Your Account</span>
      </div>

      <nav className="flex-1 py-2">
        {NAV_ITEMS.map((item) => {
          const isActive = currentPath === item.href || currentPath.startsWith(item.href + '/');
          return (
            <Link
              key={item.href}
              href={item.href}
              onClick={onClose}
              className={`flex items-center gap-3 px-4 py-2.5 text-[11px] font-bold tracking-[0.08em] uppercase transition-all group relative ${
                isActive
                  ? 'text-[#FF4D00] bg-[#FF4D00]/5 border-l-2 border-[#FF4D00]'
                  : 'text-zinc-500 hover:text-zinc-200 hover:bg-zinc-900/50 border-l-2 border-transparent'
              }`}
            >
              {isActive && (
                <div className="absolute left-0 top-0 bottom-0 w-[2px] bg-[#FF4D00] shadow-[0_0_8px_rgba(255,77,0,0.6)]" />
              )}
              <span className={isActive ? 'text-[#FF4D00]' : 'text-zinc-600 group-hover:text-zinc-400'}>
                <NavIcon type={item.icon} />
              </span>
              {item.label}
            </Link>
          );
        })}
      </nav>

      <div className="border-t border-zinc-900 p-4 space-y-2">
        <Link
          href="/portal/patient/pay"
          className="flex items-center justify-center gap-2 w-full py-2.5 bg-[#FF4D00] text-black text-[10px] font-black tracking-widest uppercase hover:bg-[#E64500] transition-colors shadow-[0_0_15px_rgba(255,77,0,0.15)]"
          style={{ clipPath: 'polygon(0 0, calc(100% - 6px) 0, 100% 6px, 100% 100%, 0 100%)' }}
        >
          PAY MY BILL
        </Link>
        <Link
          href="/portal/patient/support"
          className="flex items-center justify-center gap-2 w-full py-2 border border-zinc-800 text-zinc-400 text-[10px] font-bold tracking-widest uppercase hover:border-zinc-600 hover:text-zinc-200 transition-colors"
          style={{ clipPath: 'polygon(0 0, calc(100% - 6px) 0, 100% 6px, 100% 100%, 0 100%)' }}
        >
          GET HELP
        </Link>
        <Link
          href="/portal/patient/login"
          className="flex items-center gap-2 w-full text-[10px] font-bold tracking-widest uppercase text-zinc-600 hover:text-zinc-400 transition-colors py-1.5 pl-1"
        >
          <NavIcon type="logout" />
          SIGN OUT
        </Link>
      </div>
    </aside>
  );
}

function MobileDrawer({ open, currentPath, onClose }: { open: boolean; currentPath: string; onClose: () => void }) {
  if (!open) return null;
  return (
    <div className="fixed inset-0 z-50 md:hidden">
      <div className="absolute inset-0 bg-black/70 backdrop-blur-sm" onClick={onClose} />
      <div className="absolute left-0 top-0 bottom-0 w-64 bg-[#0A0A0B] border-r border-zinc-800 flex flex-col overflow-y-auto">
        <div className="flex items-center justify-between px-4 h-14 border-b border-zinc-900">
          <span className="text-xs font-black tracking-widest text-white uppercase">Your Account</span>
          <button onClick={onClose} className="text-zinc-500 hover:text-white transition-colors">
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/>
            </svg>
          </button>
        </div>
        <PatientSidebar currentPath={currentPath} onClose={onClose} />
      </div>
    </div>
  );
}

export default function PatientPortalLayout({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();
  const [mobileOpen, setMobileOpen] = useState(false);

  const isPublicPath = PUBLIC_PATHS.some(p => pathname === p || pathname === p + '/');

  // Public pages: no sidebar, just the premium shell
  if (isPublicPath) {
    return (
      <div className="min-h-screen bg-[#050505] text-zinc-200">
        <div className="absolute top-0 left-0 w-full h-[600px] bg-gradient-to-b from-[#FF4D00]/4 via-[#FF4D00]/1 to-transparent pointer-events-none" />
        {/* Minimal public header */}
        <header className="flex items-center justify-between px-6 h-14 border-b border-zinc-900 bg-[#0A0A0B] sticky top-0 z-20">
          <div className="absolute top-0 left-0 w-full h-[1px] bg-gradient-to-r from-[#FF4D00]/40 via-[#FF4D00]/10 to-transparent pointer-events-none" />
          <Link href="/portal/patient" className="flex items-center gap-3 group">
            <div
              className="w-8 h-8 bg-[#FF4D00] flex items-center justify-center text-[11px] font-black text-black group-hover:bg-[#E64500] transition-colors"
              style={{ clipPath: 'polygon(0 0, calc(100% - 6px) 0, 100% 6px, 100% 100%, 0 100%)' }}
            >
              FQ
            </div>
            <div className="flex flex-col">
              <span className="text-xs font-black tracking-[0.15em] text-white uppercase leading-none">
                Fusion<span className="text-[#FF4D00]">EMS</span>
              </span>
              <span className="text-[9px] font-bold text-zinc-500 tracking-[0.25em] uppercase mt-0.5">
                Patient Billing Portal
              </span>
            </div>
          </Link>
          <div className="flex items-center gap-3">
            <div className="hidden md:flex items-center gap-1.5 text-[9px] font-bold tracking-widest text-emerald-500 uppercase px-3 py-1 bg-emerald-500/10 border border-emerald-500/20"
              style={{ clipPath: 'polygon(0 0, calc(100% - 4px) 0, 100% 4px, 100% 100%, 0 100%)' }}>
              <svg width="10" height="10" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5">
                <rect x="3" y="11" width="18" height="11" rx="2" ry="2"/>
                <path d="M7 11V7a5 5 0 0 1 10 0v4"/>
              </svg>
              256-BIT ENCRYPTED
            </div>
            <Link
              href="/portal/patient/login"
              className="h-8 px-4 border border-zinc-700 text-[10px] font-bold tracking-widest uppercase text-zinc-300 hover:text-white hover:border-zinc-500 transition-colors flex items-center"
              style={{ clipPath: 'polygon(0 0, calc(100% - 5px) 0, 100% 5px, 100% 100%, 0 100%)' }}
            >
              LOG IN
            </Link>
          </div>
        </header>
        <main className="relative z-10">
          {children}
        </main>
        <footer className="border-t border-zinc-900 py-8 text-center mt-16">
          <p className="text-[10px] font-mono tracking-widest text-zinc-700 uppercase">
            © {new Date().getFullYear()} FusionEMS Quantum · HIPAA-Conscious Secure Billing Infrastructure
          </p>
          <div className="flex items-center justify-center gap-6 mt-3 text-[10px] font-bold tracking-widest uppercase">
            <Link href="/privacy" className="text-zinc-600 hover:text-zinc-400 transition-colors">Privacy</Link>
            <span className="text-zinc-800">/</span>
            <Link href="/terms" className="text-zinc-600 hover:text-zinc-400 transition-colors">Terms</Link>
            <span className="text-zinc-800">/</span>
            <Link href="/portal/patient/support" className="text-zinc-600 hover:text-zinc-400 transition-colors">Billing Help</Link>
          </div>
        </footer>
      </div>
    );
  }

  // Authenticated portal: full layout with sidebar
  return (
    <div className="min-h-screen bg-[#050505] text-zinc-200 flex flex-col">
      <PatientTopBar onMenuOpen={() => setMobileOpen(true)} />
      <MobileDrawer open={mobileOpen} currentPath={pathname} onClose={() => setMobileOpen(false)} />
      <div className="flex flex-1 overflow-hidden">
        <div className="hidden md:flex">
          <PatientSidebar currentPath={pathname} />
        </div>
        <main className="flex-1 overflow-y-auto bg-[#050505] relative">
          {/* Subtle grid overlay */}
          <div
            className="pointer-events-none absolute inset-0 opacity-[0.015]"
            style={{
              backgroundImage: 'linear-gradient(rgba(255,77,0,0.5) 1px, transparent 1px), linear-gradient(90deg, rgba(255,77,0,0.5) 1px, transparent 1px)',
              backgroundSize: '60px 60px',
            }}
          />
          <div className="relative z-10">
            {children}
          </div>
        </main>
      </div>
    </div>
  );
}
