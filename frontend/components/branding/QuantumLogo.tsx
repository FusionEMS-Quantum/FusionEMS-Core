import clsx from 'clsx';
import { useId } from 'react';

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
          {/* Carbon/Graphite Outer Hexagon with sharp edges */}
          <path
            d="M32 2L58 17V47L32 62L6 47V17L32 2Z"
            fill="#111417"
            stroke="#2A3036"
            strokeWidth="2"
          />

          {/* Internal Geometric Mark - Sharp, layered F/Q */}
          <path 
            d="M20 20H44V26H28V32H38V38H28V44H20V20Z" 
            fill="#E2E8F0" 
          />
          <path 
            d="M38 42L46 50" 
            stroke="#FF5500" 
            strokeWidth="4" 
            strokeLinecap="square" 
          />
          <circle 
            cx="37" cy="37" r="10" 
            stroke="#FF5500" 
            strokeWidth="3" 
            fill="none" 
            strokeDasharray="40 15" 
          />
          
          {/* Accent slash */}
          <path 
            d="M48 18L18 52" 
            stroke="#FF5500" 
            strokeWidth="1.5" 
            opacity="0.6" 
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
