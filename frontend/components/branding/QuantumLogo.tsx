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
    <div className={clsx('inline-flex items-center gap-2.5', className)}>
      <div className="relative flex items-center justify-center" style={{ width: spec.mark, height: spec.mark }}>
        <svg
          width={spec.mark}
          height={spec.mark}
          viewBox="0 0 64 64"
          fill="none"
          xmlns="http://www.w3.org/2000/svg"
          aria-hidden="true"
          className="drop-shadow-[0_8px_16px_rgba(0,0,0,0.8)]"
        >
          {/* Carbon/Graphite Outer Hexagon — sharp command authority */}
          <path
            d="M32 2L58 17V47L32 62L6 47V17L32 2Z"
            fill="#0D1014"
            stroke="#2A3036"
            strokeWidth="1.5"
          />

          {/* Inner hexagon — layered depth */}
          <path
            d="M32 8L52 20V44L32 56L12 44V20L32 8Z"
            fill="none"
            stroke="#1D2227"
            strokeWidth="1"
          />

          {/* Geometric F — bold structural letterform */}
          <path
            d="M22 20H42V26H30V30H38V36H30V44H22V20Z"
            fill="#E8ECF0"
          />

          {/* Q tail — signature orange diagonal stroke */}
          <path
            d="M38 40L48 52"
            stroke="#FF5500"
            strokeWidth="4"
            strokeLinecap="square"
          />

          {/* Precision ring — partial arc for Q character */}
          <path
            d="M44 32A12 12 0 1 0 36 43"
            stroke="#FF5500"
            strokeWidth="2.5"
            fill="none"
          />
        </svg>
      </div>

      {showWordmark && (
        <div className="leading-none flex flex-col justify-center">
          <div
            className="font-black uppercase tracking-[0.25em] text-white"
            style={{ fontSize: spec.title }}
          >
            FusionEMS
          </div>
          <div
            className="font-semibold uppercase tracking-[0.4em] text-[#FF5500] mt-1"
            style={{ fontSize: spec.sub }}
          >
            Quantum
          </div>
        </div>
      )}
    </div>
  );
}
