'use client';

import { cn } from '@/lib/utils';

export interface ErrorStateProps {
  readonly title?: string;
  readonly message?: string;
  readonly onRetry?: () => void;
  readonly retryLabel?: string;
  readonly className?: string;
}

export function ErrorState({
  title = 'Something went wrong',
  message = 'An error occurred while loading this content. Please try again.',
  onRetry,
  retryLabel = 'Retry',
  className,
}: ErrorStateProps) {
  return (
    <div
      className={cn(
        'flex flex-col items-center justify-center py-12 px-6 text-center',
        className
      )}
      role="alert"
    >
      {/* Error icon */}
      <div className="w-12 h-12 rounded-full bg-red-ghost flex items-center justify-center mb-4">
        <svg
          className="w-6 h-6 text-red"
          fill="none"
          viewBox="0 0 24 24"
          stroke="currentColor"
          strokeWidth={2}
          aria-hidden
        >
          <path strokeLinecap="round" strokeLinejoin="round" d="M12 9v2m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
        </svg>
      </div>

      <h3 className="text-h3 text-text-primary font-medium mb-1">{title}</h3>
      <p className="text-body text-text-muted max-w-sm mb-4">{message}</p>

      {onRetry && (
        <button
          onClick={onRetry}
          className="px-4 py-2 bg-orange text-text-inverse font-label text-label uppercase 
                     tracking-wider chamfer-4 hover:bg-orange-bright transition-colors duration-fast
                     focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-orange focus-visible:ring-offset-2 
                     focus-visible:ring-offset-bg-base"
          type="button"
        >
          {retryLabel}
        </button>
      )}
    </div>
  );
}
