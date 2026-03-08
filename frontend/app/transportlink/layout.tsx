'use client';

import React, { useState } from 'react';
import Link from 'next/link';
import { usePathname } from 'next/navigation';
import {
  LayoutDashboard,
  PlusCircle,
  FileText,
  Calendar,
  FolderOpen,
  LogIn,
  UserPlus,
  ChevronRight,
  Activity,
  Shield,
  Truck,
  Menu,
} from 'lucide-react';

const NAV_SECTIONS = [
  {
    label: 'Operations',
    items: [
      { href: '/transportlink/dashboard', label: 'Dashboard', icon: LayoutDashboard },
      { href: '/transportlink/requests/new', label: 'New Request', icon: PlusCircle, accent: true },
      { href: '/transportlink/requests', label: 'All Requests', icon: FileText },
      { href: '/transportlink/calendar', label: 'Transport Calendar', icon: Calendar },
      { href: '/transportlink/documents', label: 'Documents & OCR', icon: FolderOpen },
    ],
  },
  {
    label: 'Access',
    items: [
      { href: '/transportlink/login', label: 'Portal Login', icon: LogIn },
      { href: '/transportlink/request-access', label: 'Request Access', icon: UserPlus },
    ],
  },
];

function TransportLinkLogo() {
  return (
    <div className="flex items-center gap-2.5 px-4 py-3 border-b border-white/[0.06]">
      <div
        className="w-8 h-8 flex items-center justify-center text-[10px] font-black text-white relative overflow-hidden"
        style={{
          background: 'linear-gradient(135deg, #FF4500 0%, #FF7300 60%, #FFB800 100%)',
          clipPath: 'polygon(0 0, calc(100% - 8px) 0, 100% 8px, 100% 100%, 8px 100%, 0 calc(100% - 8px))',
        }}
      >
        <Truck className="w-4 h-4 stroke-white" strokeWidth={2.5} />
        <div className="absolute inset-0 bg-zinc-950/20 opacity-0 hover:opacity-100 transition-opacity" />
      </div>
      <div>
        <div className="text-[11px] font-black tracking-[0.18em] text-white uppercase leading-none">
          TransportLink
        </div>
        <div className="text-[9px] tracking-[0.3em] text-[#FF4D00] uppercase leading-none mt-0.5 font-medium">
          FusionEMS
        </div>
      </div>
    </div>
  );
}

function TransportStatusBar() {
  return (
    <div className="flex items-center justify-between px-3 py-1.5 border-b border-white/[0.04] bg-black/20">
      <div className="flex items-center gap-1.5">
        <div className="w-1.5 h-1.5  bg-status-active animate-pulse" />
        <span className="text-[9px] font-bold tracking-widest text-status-active uppercase">PORTAL LIVE</span>
      </div>
      <div className="flex items-center gap-2">
        <Activity className="w-2.5 h-2.5 text-zinc-500" />
        <span className="text-[8px] tracking-wider text-zinc-500 uppercase">WI-FIRST</span>
      </div>
    </div>
  );
}

function Sidebar({ mobilOpen, onClose }: { mobilOpen: boolean; onClose: () => void }) {
  const pathname = usePathname();

  return (
    <>
      {/* Mobile overlay */}
      {mobilOpen && (
        <div
          className="fixed inset-0 bg-black/60 z-30 lg:hidden"
          onClick={onClose}
        />
      )}

      <aside
        className={`
          fixed lg:relative top-0 left-0 h-full z-40 lg:z-auto
          w-56 flex-shrink-0 flex flex-col
          bg-[#0D0D0F] border-r border-white/[0.06]
          transition-transform duration-300
          ${mobilOpen ? 'translate-x-0' : '-translate-x-full lg:translate-x-0'}
        `}
      >
        <TransportLinkLogo />
        <TransportStatusBar />

        <nav className="flex-1 overflow-y-auto py-3 space-y-0.5">
          {NAV_SECTIONS.map((section) => (
            <div key={section.label} className="mb-4">
              <div className="px-4 pb-1.5">
                <span className="text-[8px] font-bold tracking-[0.25em] text-zinc-500 uppercase">
                  {section.label}
                </span>
              </div>
              {section.items.map(({ href, label, icon: Icon, accent }) => {
                const active = pathname === href || (href !== '/transportlink' && pathname.startsWith(href));
                return (
                  <Link
                    key={href}
                    href={href}
                    onClick={onClose}
                    className={`
                      flex items-center gap-2.5 px-3 mx-2 py-2 text-[11px] font-semibold
                      transition-all duration-150 group relative
                      ${active
                        ? 'text-white bg-[#FF4D00]/15 border border-orange/25'
                        : accent
                          ? 'text-[#FF4D00] bg-[#FF4D00]/[0.06] border border-orange/15 hover:bg-[#FF4D00]/15'
                          : 'text-zinc-500 hover:text-zinc-100 hover:bg-zinc-950/[0.04] border border-transparent'
                      }
                    `}
                    style={{ clipPath: 'polygon(0 0, calc(100% - 5px) 0, 100% 5px, 100% 100%, 0 100%)' }}
                  >
                    {active && (
                      <div className="absolute left-0 top-0 bottom-0 w-0.5 bg-[#FF4D00]" />
                    )}
                    <Icon className={`w-3.5 h-3.5 flex-shrink-0 ${active ? 'text-[#FF4D00]' : ''}`} />
                    <span className="truncate">{label}</span>
                    {active && <ChevronRight className="w-2.5 h-2.5 ml-auto text-[#FF4D00]/60" />}
                  </Link>
                );
              })}
            </div>
          ))}
        </nav>

        {/* Compliance badge */}
        <div className="p-3 border-t border-white/[0.06]">
          <div className="flex items-center gap-2 px-3 py-2 bg-status-active/[0.06] border border-status-active/15" style={{ clipPath: 'polygon(0 0, calc(100% - 5px) 0, 100% 5px, 100% 100%, 0 100%)' }}>
            <Shield className="w-3 h-3 text-status-active flex-shrink-0" />
            <div>
              <div className="text-[8px] font-bold tracking-widest text-status-active uppercase leading-none">CMS / WI Medicaid</div>
              <div className="text-[8px] text-zinc-500 leading-none mt-0.5">Rules engine active</div>
            </div>
          </div>
        </div>
      </aside>
    </>
  );
}

function TopBar({ onMenuClick }: { onMenuClick: () => void }) {
  const pathname = usePathname();
  const parts = pathname.replace('/transportlink', '').split('/').filter(Boolean);

  return (
    <header className="flex-shrink-0 flex items-center justify-between h-11 px-4 border-b border-white/[0.06] bg-[#0D0D0F]/80 backdrop-blur-sm">
      <div className="flex items-center gap-3">
        <button
          className="lg:hidden text-zinc-500 hover:text-zinc-100"
          onClick={onMenuClick}
        >
          <Menu className="w-4 h-4" />
        </button>

        <nav className="flex items-center gap-1 text-[10px]">
          <Link href="/transportlink/dashboard" className="text-zinc-500 hover:text-[#FF4D00] transition-colors uppercase tracking-widest font-bold">
            TransportLink
          </Link>
          {parts.map((part, i) => (
            <React.Fragment key={i}>
              <ChevronRight className="w-2.5 h-2.5 text-zinc-500/40" />
              <span className="text-zinc-100 uppercase tracking-widest font-bold">
                {part.replace(/-/g, ' ')}
              </span>
            </React.Fragment>
          ))}
        </nav>
      </div>

      <div className="flex items-center gap-3">
        <Link
          href="/transportlink/requests/new"
          className="flex items-center gap-1.5 h-7 px-3 text-[10px] font-bold tracking-wider uppercase text-white border border-orange/40 bg-[#FF4D00]/10 hover:bg-[#FF4D00]/20 transition-colors"
          style={{ clipPath: 'polygon(0 0, calc(100% - 5px) 0, 100% 5px, 100% 100%, 0 100%)' }}
        >
          <PlusCircle className="w-3 h-3" />
          New Request
        </Link>
        <Link
          href="/portal"
          className="h-7 px-2 flex items-center text-[10px] font-semibold text-zinc-500 hover:text-zinc-100 border border-white/[0.06] hover:border-white/[0.12] transition-colors"
          style={{ clipPath: 'polygon(0 0, calc(100% - 4px) 0, 100% 4px, 100% 100%, 0 100%)' }}
        >
          Agency Portal
        </Link>
      </div>
    </header>
  );
}

export default function TransportLinkLayout({ children }: { children: React.ReactNode }) {
  const [mobileOpen, setMobileOpen] = useState(false);

  return (
    <div className="min-h-screen flex bg-[#0A0A0C]" style={{ fontFamily: 'var(--font-sans)' }}>
      <Sidebar mobilOpen={mobileOpen} onClose={() => setMobileOpen(false)} />

      <div className="flex-1 flex flex-col min-w-0 overflow-hidden">
        <TopBar onMenuClick={() => setMobileOpen(true)} />
        <main className="flex-1 overflow-y-auto">
          {children}
        </main>
      </div>
    </div>
  );
}
