import clsx from 'clsx';
import { useId } from 'react';

type QuantumLogoSize = 'sm' | 'md' | 'lg';

const SIZE_MAP: Record<QuantumLogoSize, { mark: number; title: string; sub: string }> = {
  sm: { mark: 34, title: '0.86rem', sub: '0.42rem' },
  md: { mark: 44, title: '1rem', sub: '0.48rem' },
  lg: { mark: 56, title: '1.18rem', sub: '0.56rem' },
};

interface QuantumLogoProps {
  readonly size?: QuantumLogoSize;
  readonly className?: string;
  readonly showWordmark?: boolean;
}

export default function QuantumLogo({ size = 'md', className, showWordmark = true }: QuantumLogoProps) {
  const spec = SIZE_MAP[size];
  const gradientId = useId();
  const glowId = useId();

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
          className="drop-shadow-[0_12px_24px_rgba(0,0,0,0.72)]"
        >
          <defs>
            <linearGradient id={gradientId} x1="12" y1="10" x2="54" y2="54" gradientUnits="userSpaceOnUse">
              <stop stopColor="#FF944D" />
              <stop offset="0.46" stopColor="#FF6A00" />
              <stop offset="1" stopColor="#B63C09" />
            </linearGradient>
            <filter id={glowId} x="-20%" y="-20%" width="140%" height="140%">
              <feGaussianBlur stdDeviation="2.4" result="blur" />
              <feColorMatrix in="blur" type="matrix" values="1 0 0 0 0.95  0 1 0 0 0.4  0 0 1 0 0.08  0 0 0 1 0" />
            </filter>
          </defs>

          <path
            d="M32 3L56 17V47L32 61L8 47V17L32 3Z"
            fill="#090B0D"
            stroke="#313942"
            strokeWidth="1.8"
          />
          <path
            d="M32 6L53 18.5V45.5L32 58L11 45.5V18.5L32 6Z"
            fill="#11161B"
            stroke="rgba(255,255,255,0.08)"
            strokeWidth="1"
          />
          <path d="M18 18H43V23.5H24.5V30.5H36V36H24.5V46H18V18Z" fill="#EEF2F6" />
          <path d="M38 26.5a10.5 10.5 0 1 1-7.42 17.92" stroke={`url(#${gradientId})`} strokeWidth="3.2" fill="none" strokeLinecap="square" />
          <path d="M41.5 41.5L48 48" stroke={`url(#${gradientId})`} strokeWidth="3.2" strokeLinecap="square" />
          <path d="M48.5 14.5L18.5 49.5" stroke={`url(#${gradientId})`} strokeWidth="1.1" opacity="0.7" />
          <path d="M15 48.5L49 15" stroke="#F5A46E" strokeWidth="0.8" opacity="0.2" />
          <circle cx="41" cy="37" r="11.5" stroke={`url(#${gradientId})`} strokeWidth="1.1" opacity="0.28" fill="none" filter={`url(#${glowId})`} />

          <path d="M15 12.5H28" stroke="#FFF3E8" strokeWidth="0.8" opacity="0.24" />
          <path d="M36 52H49" stroke="#FF8A42" strokeWidth="0.8" opacity="0.24" />
        </svg>
      </div>

      {showWordmark && (
        <div className="leading-none flex flex-col justify-center min-w-0">
          <div
            className="font-black uppercase tracking-[0.22em] text-white"
            style={{ fontSize: spec.title }}
          >
            FusionEMS
          </div>
          <div
            className="font-semibold uppercase tracking-[0.38em] text-[#FF7A2F] mt-1"
            style={{ fontSize: spec.sub }}
          >
            Quantum
          </div>
        </div>
      )}
    </div>
  );
}
