import clsx from 'clsx';

export type QuantumLogoSize = 'sm' | 'md' | 'lg';

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

export function FQMark({ size = 'md', className }: Pick<QuantumLogoProps, 'size' | 'className'>) {
  const spec = SIZE_MAP[size];

  return (
    <div className={clsx('relative flex items-center justify-center', className)} style={{ width: spec.mark, height: spec.mark }}>
      <div className="absolute inset-[2px] clip-path-[var(--chamfer-8)] bg-[linear-gradient(180deg,rgba(255,255,255,0.12),rgba(255,255,255,0.01))] opacity-70" />
      <svg
        width={spec.mark}
        height={spec.mark}
        viewBox="0 0 64 64"
        fill="none"
        xmlns="http://www.w3.org/2000/svg"
        aria-hidden="true"
        className="relative drop-shadow-[0_10px_22px_rgba(0,0,0,0.78)]"
      >
        <path
          d="M8 8H50L56 14V56H8V8Z"
          fill="#0F1317"
          stroke="#313943"
          strokeWidth="2"
        />
        <path d="M8 8H50L56 14H14L8 8Z" fill="rgba(255,255,255,0.06)" />
        <path d="M20 18H43V24H27V31H38V37H27V46H20V18Z" fill="#F3F5F7" />
        <path d="M37 31C37 24.3726 42.3726 19 49 19V25C45.6863 25 43 27.6863 43 31V37C43 40.3137 45.6863 43 49 43H52V49H49C42.3726 49 37 43.6274 37 37V31Z" fill="#F36A21" />
        <path d="M45 42L53 50" stroke="#F36A21" strokeWidth="3" strokeLinecap="square" />
        <path d="M14 52L52 14" stroke="rgba(243,106,33,0.35)" strokeWidth="1.5" />
      </svg>
    </div>
  );
}

export default function QuantumLogo({ size = 'md', className, showWordmark = true }: QuantumLogoProps) {
  const spec = SIZE_MAP[size];

  return (
    <div className={clsx('inline-flex items-center gap-2.5', className)}>
      <FQMark size={size} />

      {showWordmark && (
        <div className="leading-none flex flex-col justify-center">
          <div
            className="font-black uppercase tracking-[0.24em] text-white"
            style={{ fontSize: spec.title }}
          >
            FusionEMS
          </div>
          <div
            className="font-semibold uppercase tracking-[0.34em] text-[#FF5500] mt-1"
            style={{ fontSize: spec.sub }}
          >
            Quantum Command
          </div>
        </div>
      )}
    </div>
  );
}
