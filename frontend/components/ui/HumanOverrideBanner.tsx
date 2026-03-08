'use client';

import { cn } from '@/lib/utils';

export interface HumanOverrideBannerProps {
  readonly overriddenBy: string;
  readonly timestamp: string;
  readonly reason?: string;
  readonly originalDecision?: string;
  readonly domain?: string;
  readonly onViewAudit?: () => void;
  readonly className?: string;
}

export function HumanOverrideBanner({
  overriddenBy,
  timestamp,
  reason,
  originalDecision,
  domain,
  onViewAudit,
  className,
}: HumanOverrideBannerProps) {
  return (
    <div
      className={cn(
        'border-l-4 border-orange bg-[#FF4D00]-ghost p-4 chamfer-4',
        className
      )}
      role="status"
    >
      <div className="flex items-start justify-between gap-3">
        <div className="flex items-start gap-3 min-w-0">
          <svg
            className="w-5 h-5 text-[#FF4D00] flex-shrink-0 mt-0.5"
            fill="none"
            viewBox="0 0 24 24"
            stroke="currentColor"
            strokeWidth={2}
            aria-hidden
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              d="M12 9v2m0 4h.01M5.07 19h13.86c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z"
            />
          </svg>
          <div className="min-w-0">
            <div className="flex items-center gap-2 flex-wrap">
              <h4 className="text-body text-[#FF4D00] font-medium">Human Override Applied</h4>
              {domain && (
                <span className="text-micro font-label uppercase tracking-wider text-zinc-500">
                  {domain}
                </span>
              )}
            </div>
            <p className="text-label text-zinc-400 mt-0.5">
              Overridden by <strong className="text-zinc-100">{overriddenBy}</strong> at{' '}
              <time className="text-zinc-500">{timestamp}</time>
            </p>
            {originalDecision && (
              <p className="text-label text-zinc-500 mt-1">
                Original decision: <span className="line-through">{originalDecision}</span>
              </p>
            )}
            {reason && (
              <p className="text-label text-zinc-400 mt-1">
                Reason: {reason}
              </p>
            )}
          </div>
        </div>
        {onViewAudit && (
          <button
            onClick={onViewAudit}
            className="flex-shrink-0 px-3 py-1.5 text-label font-label uppercase tracking-wider
                       text-[#FF4D00] border border-orange/30 chamfer-4
                       hover:bg-[#FF4D00]-ghost transition-colors duration-fast"
            type="button"
          >
            View Audit →
          </button>
        )}
      </div>
    </div>
  );
}
