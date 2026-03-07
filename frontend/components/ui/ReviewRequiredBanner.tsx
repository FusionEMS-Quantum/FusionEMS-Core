'use client';

import { cn } from '@/lib/utils';

export interface ReviewRequiredBannerProps {
  readonly title?: string;
  readonly reason: string;
  readonly domain?: string;
  readonly onReview?: () => void;
  readonly reviewLabel?: string;
  readonly className?: string;
}

export function ReviewRequiredBanner({
  title = 'Human Review Required',
  reason,
  domain,
  onReview,
  reviewLabel = 'Review Now',
  className,
}: ReviewRequiredBannerProps) {
  return (
    <div
      className={cn(
        'border-l-4 border-[#818cf8] bg-[rgba(129,140,248,0.08)] p-4 chamfer-4',
        className
      )}
      role="alert"
    >
      <div className="flex items-start justify-between gap-3">
        <div className="flex items-start gap-3 min-w-0">
          <svg
            className="w-5 h-5 text-[#818cf8] flex-shrink-0 mt-0.5"
            fill="none"
            viewBox="0 0 24 24"
            stroke="currentColor"
            strokeWidth={2}
            aria-hidden
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              d="M15 12a3 3 0 11-6 0 3 3 0 016 0z"
            />
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              d="M2.458 12C3.732 7.943 7.523 5 12 5c4.478 0 8.268 2.943 9.542 7-1.274 4.057-5.064 7-9.542 7-4.477 0-8.268-2.943-9.542-7z"
            />
          </svg>
          <div className="min-w-0">
            <div className="flex items-center gap-2">
              <h4 className="text-body text-[#818cf8] font-medium">{title}</h4>
              {domain && (
                <span className="text-micro font-label uppercase tracking-wider text-text-muted">
                  {domain}
                </span>
              )}
            </div>
            <p className="text-label text-text-secondary mt-0.5">{reason}</p>
          </div>
        </div>
        {onReview && (
          <button
            onClick={onReview}
            className="flex-shrink-0 px-3 py-1.5 text-label font-label uppercase tracking-wider
                       text-[#818cf8] border border-[#818cf8]/30 chamfer-4
                       hover:bg-[rgba(129,140,248,0.12)] transition-colors duration-fast"
            type="button"
          >
            {reviewLabel}
          </button>
        )}
      </div>
    </div>
  );
}
