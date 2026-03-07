'use client';

import { cn } from '@/lib/utils';
import { getHealthBand, type HealthBand } from '@/lib/design-system/tokens';
import { healthScoreCopy } from '@/lib/design-system/language';

export interface HealthScoreCardProps {
  readonly score: number;
  readonly title?: string;
  readonly domain?: string;
  readonly showExplanation?: boolean;
  readonly compact?: boolean;
  readonly className?: string;
}

export function HealthScoreCard({
  score,
  title = 'Health Score',
  domain,
  showExplanation = true,
  compact = false,
  className,
}: HealthScoreCardProps) {
  const band: HealthBand = getHealthBand(score);
  const copy = healthScoreCopy(score);
  const radius = compact ? 32 : 44;
  const circumference = 2 * Math.PI * radius;
  const offset = circumference - (score / 100) * circumference;

  return (
    <div
      className={cn(
        'bg-bg-panel border border-[var(--color-border-default)] chamfer-8 p-4',
        className
      )}
    >
      {/* Header */}
      <div className="flex items-center justify-between mb-3">
        <div>
          <h3 className="font-label text-label uppercase tracking-wider text-text-secondary">
            {domain ? `${domain} · ` : ''}{title}
          </h3>
        </div>
        <span
          className="text-micro font-label uppercase tracking-wider px-2 py-0.5 chamfer-4"
          style={{ color: band.colorVar, backgroundColor: `color-mix(in srgb, ${band.colorVar} 15%, transparent)` }}
        >
          {band.label}
        </span>
      </div>

      {/* Gauge */}
      <div className="flex items-center gap-4">
        <div className="relative flex-shrink-0">
          <svg
            width={compact ? 72 : 96}
            height={compact ? 72 : 96}
            viewBox={`0 0 ${(radius + 4) * 2} ${(radius + 4) * 2}`}
            className="transform -rotate-90"
          >
            {/* Background ring */}
            <circle
              cx={radius + 4}
              cy={radius + 4}
              r={radius}
              fill="none"
              stroke="var(--color-border-subtle)"
              strokeWidth={compact ? 4 : 6}
            />
            {/* Score ring */}
            <circle
              cx={radius + 4}
              cy={radius + 4}
              r={radius}
              fill="none"
              stroke={band.colorVar}
              strokeWidth={compact ? 4 : 6}
              strokeDasharray={circumference}
              strokeDashoffset={offset}
              strokeLinecap="round"
              className="transition-all duration-slow ease-out"
            />
          </svg>
          <div className="absolute inset-0 flex items-center justify-center">
            <span
              className={cn('font-sans font-bold', compact ? 'text-h3' : 'text-h2')}
              style={{ color: band.colorVar }}
            >
              {score}
            </span>
          </div>
        </div>

        {/* Explanation */}
        {showExplanation && (
          <div className="flex-1 min-w-0 space-y-1">
            <p className="text-body text-text-primary leading-snug">{copy.what}</p>
            <p className="text-label text-text-muted leading-snug">{copy.why}</p>
            <p className="text-label text-text-secondary font-medium">{copy.next}</p>
          </div>
        )}
      </div>
    </div>
  );
}
