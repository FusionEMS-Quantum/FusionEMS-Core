'use client';

import { ReactNode } from 'react';
import Link from 'next/link';
import { usePathname } from 'next/navigation';

const STEPS = [
  { label: 'AGENCY INFO', path: '/signup' },
  { label: 'LEGAL',       path: '/signup/legal' },
  { label: 'CHECKOUT',    path: '/signup/checkout' },
  { label: 'STATUS',      path: '/signup/success' },
];

function HexLogo() {
  return (
    <svg width="40" height="40" viewBox="0 0 36 36" fill="none" xmlns="http://www.w3.org/2000/svg">
      <polygon
        points="18,2 33,10 33,26 18,34 3,26 3,10"
        fill="#FF4D00"
        stroke="#FF4D00"
        strokeWidth="1"
      />
      <text
        x="18"
        y="23"
        textAnchor="middle"
        fill="#050505"
        fontSize="13"
        fontWeight="900"
        fontFamily="'Barlow Condensed', 'Barlow', sans-serif"
        letterSpacing="0.5"
      >
        FQ
      </text>
    </svg>
  );
}

function StepIndicator({ pathname }: { pathname: string }) {
  const currentIndex = STEPS.reduce((found, step, idx) => {
    if (pathname === step.path || pathname.startsWith(step.path + '/')) return idx;
    return found;
  }, 0);

  return (
    <div className="flex items-center gap-0 mt-8 mb-10 overflow-x-auto w-full max-w-full justify-center pb-2">
      {STEPS.map((step, idx) => {
        const isActive    = idx === currentIndex;
        const isCompleted = idx < currentIndex;
        const isLast      = idx === STEPS.length - 1;

        return (
          <div key={step.path} className="flex items-center shrink-0">
            {/* Step pill */}
            <div className="flex flex-col items-center">
              <div
                className={`flex items-center justify-center text-[10px] font-bold tracking-widest px-4 py-1.5 transition-colors border
                  ${isActive 
                    ? 'bg-[#FF4D00] text-black border-[#FF4D00] shadow-[0_0_15px_rgba(255,77,0,0.2)]'
                    : isCompleted
                      ? 'bg-[#FF4D00]/10 text-[#FF4D00] border-[#FF4D00]/30'
                      : 'bg-zinc-900 border-zinc-800 text-zinc-500'
                  }`}
                style={{
                  minWidth: '110px',
                  textAlign: 'center',
                  clipPath: 'polygon(0 0, calc(100% - 6px) 0, 100% 6px, 100% 100%, 6px 100%, 0 calc(100% - 6px))'
                }}
              >
                {isCompleted && (
                  <svg
                    className="inline mr-1.5"
                    width="10"
                    height="10"
                    viewBox="0 0 10 10"
                    fill="none"
                  >
                    <path
                      d="M1.5 5l2.5 2.5 4.5-4.5"
                      stroke="currentColor"
                      strokeWidth="2"
                      strokeLinecap="square"
                      strokeLinejoin="miter"
                    />
                  </svg>
                )}
                {step.label}
              </div>
            </div>
            {/* Connector */}
            {!isLast && (
              <div
                className={`h-[1px] w-6 md:w-10 transition-colors ${
                  isCompleted ? 'bg-[#FF4D00]/50' : 'bg-zinc-800'
                }`}
              />
            )}
          </div>
        );
      })}
    </div>
  );
}

export default function SignupLayout({ children }: { children: ReactNode }) {
  const pathname = usePathname();

  return (
    <div className="min-h-screen bg-[#050505] text-zinc-200 font-sans flex flex-col items-center px-4 py-12 relative overflow-hidden">
      
      {/* Background elements */}
      <div className="absolute top-0 left-0 w-full h-[500px] bg-gradient-to-b from-[#FF4D00]/5 to-transparent pointer-events-none" />
      <div className="absolute top-[10%] left-0 w-full h-[1px] bg-zinc-900 pointer-events-none" />
      <div className="absolute top-[30%] left-0 w-full h-[1px] bg-zinc-900 pointer-events-none" />
      
      {/* Header */}
      <div className="flex flex-col items-center z-10 w-full">
        <div className="flex items-center gap-4">
          <HexLogo />
          <div>
            <div className="text-xl md:text-2xl font-black tracking-[0.15em] text-white uppercase leading-none">
              FUSION<span className="text-[#FF4D00]">EMS</span> QUANTUM
            </div>
            <div className="text-[10px] font-bold text-zinc-400 tracking-[0.3em] uppercase mt-1">
              AGENCY INITIALIZATION
            </div>
          </div>
        </div>
        <StepIndicator pathname={pathname} />
      </div>

      {/* Page content */}
      <div className="w-full max-w-3xl z-10">
        <div 
          className="bg-[#0A0A0B] border border-zinc-800/80 p-8 shadow-[0_0_15px_rgba(0,0,0,0.6)] relative"
          style={{ clipPath: 'polygon(0 0, calc(100% - 24px) 0, 100% 24px, 100% 100%, 0 100%)' }}
        >
          {/* Decorative Corner Marker */}
          <div className="absolute top-0 right-0 w-[24px] h-[24px] border-l border-b border-zinc-800 pointer-events-none" />
          <div className="absolute top-0 right-[24px] w-8 h-[1px] bg-[#FF4D00]/50 pointer-events-none" />
          <div className="absolute top-[24px] right-0 w-[1px] h-8 bg-[#FF4D00]/50 pointer-events-none" />

          {children}
        </div>
      </div>

      {/* Footer */}
      <div className="mt-16 text-center z-10 flex flex-col items-center gap-3">
        <div className="h-1 w-12 bg-zinc-800" />
        <div className="text-[10px] font-mono tracking-widest text-zinc-600 uppercase">
          &copy; {new Date().getFullYear()} FUSIONEMS QUANTUM · SECURE INFRASTRUCTURE
        </div>
        <div className="flex items-center gap-4 text-[10px] font-bold tracking-widest uppercase">
          <Link
            href="/privacy"
            className="text-zinc-500 hover:text-white transition-colors"
          >
            PRIVACY
          </Link>
          <span className="text-zinc-800">/</span>
          <Link
            href="/terms"
            className="text-zinc-500 hover:text-white transition-colors"
          >
            TERMS
          </Link>
        </div>
      </div>
    </div>
  );
}
