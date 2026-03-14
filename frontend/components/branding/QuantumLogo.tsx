import clsx from 'clsx';

type QuantumLogoSize = 'sm' | 'md' | 'lg';

const SIZE_MAP: Record<QuantumLogoSize, { mark: number; title: string; sub: string }> = {
  sm: { mark: 34, title: '0.9rem', sub: '0.42rem' },
  md: { mark: 42, title: '1.05rem', sub: '0.48rem' },
  lg: { mark: 52, title: '1.2rem', sub: '0.54rem' },
};

interface QuantumLogoProps {
  readonly size?: QuantumLogoSize;
  readonly className?: string;
  readonly showWordmark?: boolean;
}

/**
 * FQ Monogram Mark — standalone mark component for icon-only contexts
 * (headers, favicons, inline badges). Uses a chamfered square container
 * with an engineered FQ monogram: geometric F anchors the left, the Q arc
 * wraps the upper-right, and the Q tail exits as a decisive diagonal cut.
 */
export function FQMark({ size = 28, className }: { readonly size?: number; readonly className?: string }) {
  return (
    <svg
      width={size}
      height={size}
      viewBox="0 0 64 64"
      fill="none"
      xmlns="http://www.w3.org/2000/svg"
      aria-hidden="true"
      className={className}
    >
      {/* Chamfered square — obsidian base */}
      <path d="M0 0H52L64 12V64H0V0Z" fill="#0A0C0E" />
      <path d="M1 1H51.5L63 12.5V63H1V1Z" fill="none" stroke="rgba(255,255,255,0.06)" strokeWidth="0.75" />

      {/* Structural F — left anchor */}
      <rect x="14" y="14" width="24" height="3.5" rx="0" fill="#E8ECF0" />
      <rect x="14" y="14" width="3.5" height="28" rx="0" fill="#E8ECF0" />
      <rect x="14" y="27" width="17" height="3.5" rx="0" fill="#E8ECF0" />

      {/* Q arc — upper right containment */}
      <path d="M46 26A13 13 0 1 0 37 40" stroke="#F36A21" strokeWidth="3" fill="none" strokeLinecap="square" />

      {/* Q tail — decisive diagonal exit */}
      <path d="M39 38L54 54" stroke="#F36A21" strokeWidth="3.5" strokeLinecap="square" />
    </svg>
  );
}

/**
 * QuantumLogo — full identity lockup.
 * Pairs the FQ monogram with the FusionEMS Quantum wordmark.
 * The mark uses a chamfered square (no hexagon), clean geometry,
 * and the orange Q arc + tail as the signature accent.
 */
export default function QuantumLogo({ size = 'md', className, showWordmark = true }: QuantumLogoProps) {
  const spec = SIZE_MAP[size];

  return (
    <div className={clsx('inline-flex items-center gap-3', className)}>
      <div className="relative flex items-center justify-center" style={{ width: spec.mark, height: spec.mark }}>
        <FQMark size={spec.mark} />
      </div>

      {showWordmark && (
        <div className="leading-none flex flex-col justify-center">
          <div className="font-black uppercase tracking-[0.3em]" style={{ fontSize: spec.title, color: 'var(--color-text-primary)' }}>
            FusionEMS
          </div>
          <div className="font-bold uppercase tracking-[0.45em] mt-1" style={{ fontSize: spec.sub, color: 'var(--color-brand-orange)' }}>
            Quantum
          </div>
        </div>
      )}
    </div>
  );
}

