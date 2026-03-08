'use client';

import { type ReactNode, useState, useEffect, useCallback, createContext, useContext } from 'react';
import { cn } from '@/lib/utils';
import { BREAKPOINTS, type DensityMode } from '@/lib/design-system/tokens';

// ══════════════════════════════════════════════════════════════════
// RESPONSIVE + DUAL-MONITOR OPTIMIZATION LAYER
// Handles widescreen detection, density modes, dual-monitor
// founder mode, and mobile-safe critical actions.
// ══════════════════════════════════════════════════════════════════

// ── Viewport Context ─────────────────────────────────────────────

interface ViewportState {
  readonly width: number;
  readonly height: number;
  readonly isMobile: boolean;
  readonly isTablet: boolean;
  readonly isDesktop: boolean;
  readonly isWidescreen: boolean;
  readonly isUltraWide: boolean;
  readonly density: DensityMode;
  readonly setDensity: (_mode: DensityMode) => void;
}

const ViewportContext = createContext<ViewportState>({
  width: 1280,
  height: 800,
  isMobile: false,
  isTablet: false,
  isDesktop: true,
  isWidescreen: false,
  isUltraWide: false,
  density: 'default',
  setDensity: () => {},
});

export function useViewport() {
  return useContext(ViewportContext);
}

export function ViewportProvider({ children }: { readonly children: ReactNode }) {
  const [width, setWidth] = useState(typeof window !== 'undefined' ? window.innerWidth : 1280);
  const [height, setHeight] = useState(typeof window !== 'undefined' ? window.innerHeight : 800);
  const [density, setDensityState] = useState<DensityMode>('default');

  useEffect(() => {
    const onResize = () => {
      setWidth(window.innerWidth);
      setHeight(window.innerHeight);
    };
    window.addEventListener('resize', onResize);
    return () => window.removeEventListener('resize', onResize);
  }, []);

  const setDensity = useCallback((mode: DensityMode) => {
    setDensityState(mode);
    // Apply density attribute to root for CSS token overrides
    document.documentElement.setAttribute(
      'data-density',
      mode === 'dispatch' || mode === 'compact' ? 'dispatch' : ''
    );
  }, []);

  const state: ViewportState = {
    width,
    height,
    isMobile: width < BREAKPOINTS.md,
    isTablet: width >= BREAKPOINTS.md && width < BREAKPOINTS.lg,
    isDesktop: width >= BREAKPOINTS.lg,
    isWidescreen: width >= BREAKPOINTS['3xl'],
    isUltraWide: width >= BREAKPOINTS['4xl'],
    density,
    setDensity,
  };

  return (
    <ViewportContext.Provider value={state}>
      {children}
    </ViewportContext.Provider>
  );
}

// ── Responsive Visibility ────────────────────────────────────────

export interface ResponsiveProps {
  readonly children: ReactNode;
  /** Show only on mobile */
  readonly mobile?: boolean;
  /** Show only on tablet+ */
  readonly tablet?: boolean;
  /** Show only on desktop+ */
  readonly desktop?: boolean;
  /** Show only on widescreen+ */
  readonly widescreen?: boolean;
}

export function Responsive({ children, mobile, tablet, desktop, widescreen }: ResponsiveProps) {
  const { isMobile, isTablet, isDesktop, isWidescreen } = useViewport();

  if (mobile && !isMobile) return null;
  if (tablet && !(isTablet || isDesktop)) return null;
  if (desktop && !isDesktop) return null;
  if (widescreen && !isWidescreen) return null;

  return <>{children}</>;
}

// ── Sticky Action Summary ────────────────────────────────────────
// Sticks to bottom on mobile/tablet for critical actions.

export interface StickyActionSummaryProps {
  readonly children: ReactNode;
  readonly visible?: boolean;
  readonly className?: string;
}

export function StickyActionSummary({
  children,
  visible = true,
  className,
}: StickyActionSummaryProps) {
  if (!visible) return null;

  return (
    <div
      className={cn(
        'fixed bottom-0 left-0 right-0 z-40 bg-[#0A0A0B] border-t border-[var(--color-border-default)]',
        'px-4 py-3 shadow-elevation-3',
        'lg:static lg:border-t-0 lg:shadow-none lg:p-0',
        className
      )}
    >
      {children}
    </div>
  );
}

// ── Density Mode Selector ────────────────────────────────────────

export interface DensitySelectorProps {
  readonly className?: string;
}

export function DensitySelector({ className }: DensitySelectorProps) {
  const { density, setDensity } = useViewport();

  const modes: { id: DensityMode; label: string; icon: string }[] = [
    { id: 'comfortable', label: 'Comfortable', icon: '▬' },
    { id: 'default', label: 'Default', icon: '≡' },
    { id: 'compact', label: 'Compact', icon: '☰' },
    { id: 'dispatch', label: 'Dispatch', icon: '▤' },
  ];

  return (
    <div className={cn('flex items-center gap-1 bg-[#050505] border border-[var(--color-border-default)] chamfer-4 p-0.5', className)}>
      {modes.map((mode) => (
        <button
          key={mode.id}
          onClick={() => setDensity(mode.id)}
          className={cn(
            'px-2 py-1 text-micro font-label uppercase tracking-wider chamfer-4 transition-colors duration-fast',
            density === mode.id
              ? 'bg-[#FF4D00]-ghost text-[#FF4D00]'
              : 'text-zinc-500 hover:text-zinc-400'
          )}
          title={mode.label}
          type="button"
        >
          <span aria-hidden>{mode.icon}</span>
          <span className="sr-only">{mode.label}</span>
        </button>
      ))}
    </div>
  );
}

// ── Widescreen Split Panel ───────────────────────────────────────
// On widescreen, shows two panels side by side.
// On smaller screens, collapses to single panel with toggle.

export interface WidescreenSplitProps {
  readonly primary: ReactNode;
  readonly secondary: ReactNode;
  readonly primaryLabel?: string;
  readonly secondaryLabel?: string;
  readonly className?: string;
}

export function WidescreenSplit({
  primary,
  secondary,
  primaryLabel = 'Main',
  secondaryLabel = 'Detail',
  className,
}: WidescreenSplitProps) {
  const { isWidescreen } = useViewport();
  const [showSecondary, setShowSecondary] = useState(false);

  if (isWidescreen) {
    return (
      <div className={cn('flex gap-4 h-full', className)}>
        <div className="flex-1 min-w-0 overflow-y-auto">{primary}</div>
        <div className="w-[45%] max-w-2xl flex-shrink-0 overflow-y-auto border-l border-[var(--color-border-default)] pl-4">
          {secondary}
        </div>
      </div>
    );
  }

  return (
    <div className={cn('h-full flex flex-col', className)}>
      {/* Panel toggle */}
      <div className="flex items-center gap-2 mb-3">
        <button
          onClick={() => setShowSecondary(false)}
          className={cn(
            'px-3 py-1.5 text-label font-label uppercase tracking-wider chamfer-4 transition-colors duration-fast',
            !showSecondary ? 'bg-[#FF4D00]-ghost text-[#FF4D00]' : 'text-zinc-500 hover:text-zinc-400'
          )}
          type="button"
        >
          {primaryLabel}
        </button>
        <button
          onClick={() => setShowSecondary(true)}
          className={cn(
            'px-3 py-1.5 text-label font-label uppercase tracking-wider chamfer-4 transition-colors duration-fast',
            showSecondary ? 'bg-[#FF4D00]-ghost text-[#FF4D00]' : 'text-zinc-500 hover:text-zinc-400'
          )}
          type="button"
        >
          {secondaryLabel}
        </button>
      </div>

      <div className="flex-1 min-h-0 overflow-y-auto">
        {showSecondary ? secondary : primary}
      </div>
    </div>
  );
}

// ── Touch Safe Button ────────────────────────────────────────────
// Ensures minimum touch target (48px) on mobile/tablet.

export interface TouchSafeButtonProps {
  readonly children: ReactNode;
  readonly onClick?: () => void;
  readonly variant?: 'primary' | 'secondary' | 'danger' | 'ghost';
  readonly disabled?: boolean;
  readonly className?: string;
  readonly type?: 'button' | 'submit' | 'reset';
}

export function TouchSafeButton({
  children,
  onClick,
  variant = 'primary',
  disabled = false,
  className,
  type = 'button',
}: TouchSafeButtonProps) {
  const variantStyles = {
    primary: 'bg-[#FF4D00] text-black hover:bg-[#FF4D00]-bright',
    secondary: 'bg-[#0A0A0B] text-zinc-100 border border-[var(--color-border-default)] hover:bg-bg-overlay',
    danger: 'bg-red text-white hover:bg-red-bright',
    ghost: 'text-zinc-500 hover:text-zinc-100 hover:bg-bg-overlay',
  };

  return (
    <button
      onClick={onClick}
      disabled={disabled}
      type={type}
      className={cn(
        'min-h-[48px] min-w-[48px] px-4 py-3 md:min-h-[36px] md:min-w-0 md:py-2',
        'text-label font-label uppercase tracking-wider chamfer-4',
        'transition-colors duration-fast disabled:opacity-50 disabled:cursor-not-allowed',
        'focus-visible:outline-none focus-visible:shadow-[var(--focus-ring)]',
        variantStyles[variant],
        className
      )}
    >
      {children}
    </button>
  );
}
