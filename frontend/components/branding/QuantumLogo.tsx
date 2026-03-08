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
  const gradientId = useId();
  const edgeId = useId();
  const glowId = useId();
  const spec = SIZE_MAP[size];

  return (
    <div className={clsx('inline-flex items-center gap-2.5', className)}>
      <div className="relative" style={{ width: spec.mark, height: spec.mark }}>
        <svg
          width={spec.mark}
          height={spec.mark}
          viewBox="0 0 64 64"
          fill="none"
          xmlns="http://www.w3.org/2000/svg"
          aria-hidden="true"
          className="drop-shadow-[0_8px_20px_rgba(0,0,0,0.45)]"
        >
          <defs>
            <linearGradient id={gradientId} x1="8" y1="6" x2="56" y2="58" gradientUnits="userSpaceOnUse">
              <stop offset="0" stopColor="#1E293B" />
              <stop offset="0.5" stopColor="#334155" />
              <stop offset="1" stopColor="#0F172A" />
            </linearGradient>
            <linearGradient id={edgeId} x1="10" y1="10" x2="54" y2="54" gradientUnits="userSpaceOnUse">
              <stop offset="0" stopColor="#FF8C33" />
              <stop offset="1" stopColor="#FF6A00" />
            </linearGradient>
            <linearGradient id={glowId} x1="20" y1="16" x2="46" y2="48" gradientUnits="userSpaceOnUse">
              <stop offset="0" stopColor="#FFD7B5" />
              <stop offset="1" stopColor="#FF9A4A" />
            </linearGradient>
          </defs>

          <path
            d="M32 3L56 16.5V47.5L32 61L8 47.5V16.5L32 3Z"
            fill={`url(#${gradientId})`}
            stroke={`url(#${edgeId})`}
            strokeWidth="1.6"
          />

          <path d="M19 18H39L36.5 24.5H26V30H34L31.5 36H26V46H19V18Z" fill="#F8FAFC" />
          <path
            d="M45 35.5C45 41.3 40.4 46 34.7 46C29 46 24.4 41.3 24.4 35.5C24.4 29.7 29 25 34.7 25C40.4 25 45 29.7 45 35.5Z"
            stroke="#F8FAFC"
            strokeWidth="2.6"
          />
          <path d="M39.7 41.2L46.5 48" stroke={`url(#${glowId})`} strokeWidth="2.8" strokeLinecap="round" />
          <path d="M18 46L48 18" stroke={`url(#${glowId})`} strokeWidth="1.6" strokeLinecap="round" opacity="0.9" />
        </svg>
        <div className="absolute inset-0  bg-[radial-gradient(circle,rgba(255,106,0,0.35),transparent_68%)] blur-md pointer-events-none" />
      </div>

      {showWordmark && (
        <div className="leading-none">
          <div
            className="font-black uppercase tracking-[0.22em] text-transparent bg-clip-text bg-gradient-to-b from-slate-100 to-slate-400"
            style={{ fontSize: spec.title }}
          >
            FusionEMS
          </div>
          <div
            className="font-bold uppercase tracking-[0.34em] text-[#FF8C33] mt-1"
            style={{ fontSize: spec.sub }}
          >
            Quantum
          </div>
        </div>
      )}
    </div>
  );
}
