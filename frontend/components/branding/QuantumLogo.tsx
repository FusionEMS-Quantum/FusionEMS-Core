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

export default function QuantumLogo({ size = 'md', className, showWordmark = true }: QuantumLogoProps) {
  const spec = SIZE_MAP[size];

  return (
    <div className={clsx('inline-flex items-center gap-3', className)}>
      <div className="relative flex items-center justify-center" style={{ width: spec.mark, height: spec.mark }}>
        <svg
          width={spec.mark}
          height={spec.mark}
          viewBox="0 0 64 64"
          fill="none"
          xmlns="http://www.w3.org/2000/svg"
          aria-hidden="true"
        >
          <defs>
            <linearGradient id="q-orange-grad" x1="0" y1="0" x2="64" y2="64" gradientUnits="userSpaceOnUse">
              <stop stopColor="#FF7A2F" />
              <stop offset="1" stopColor="#F36A21" />
            </linearGradient>
            <filter id="q-glow">
              <feGaussianBlur in="SourceGraphic" stdDeviation="1.5" />
            </filter>
          </defs>

          {/* Outer Hexagon — obsidian */}
          <path d="M32 2L58 17V47L32 62L6 47V17L32 2Z" fill="#0A0C0E" stroke="#1D2227" strokeWidth="1" />

          {/* Inner hexagon — layered depth */}
          <path d="M32 8L52 20V44L32 56L12 44V20L32 8Z" fill="none" stroke="rgba(255,255,255,0.04)" strokeWidth="0.75" />

          {/* Orange glow behind mark */}
          <path d="M44 32A12 12 0 1 0 36 43" stroke="url(#q-orange-grad)" strokeWidth="3" fill="none" filter="url(#q-glow)" opacity="0.5" />

          {/* Geometric F — precision letterform */}
          <path d="M23 19H41V24.5H29.5V29.5H37V35H29.5V45H23V19Z" fill="#E8ECF0" />

          {/* Q arc — signature stroke */}
          <path d="M44 32A12 12 0 1 0 36 43" stroke="url(#q-orange-grad)" strokeWidth="2.5" fill="none" strokeLinecap="square" />

          {/* Q tail — diagonal brand mark */}
          <path d="M38 40L49 53" stroke="url(#q-orange-grad)" strokeWidth="3.5" strokeLinecap="square" />
        </svg>
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
