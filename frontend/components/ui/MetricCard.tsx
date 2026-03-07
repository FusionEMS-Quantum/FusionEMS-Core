'use client';

import { type ReactNode } from 'react';
import { cn } from '@/lib/utils';
import type { SystemDomain } from '@/lib/design-system/tokens';
import { DOMAIN_COLOR_MAP } from '@/lib/design-system/tokens';

export interface MetricCardProps {
  readonly label: string;
  readonly value: string | number;
  readonly change?: string;
  readonly changeDirection?: 'up' | 'down' | 'neutral';
  readonly icon?: ReactNode;
  readonly domain?: SystemDomain;
  readonly loading?: boolean;
  readonly compact?: boolean;
  readonly className?: string;
}

export function MetricCard({
  label,
  value,
  change,
  changeDirection = 'neutral',
  icon,
  domain,
  loading = false,
  compact = false,
  className,
}: MetricCardProps) {
  const accentColor = domain ? DOMAIN_COLOR_MAP[domain] : 'var(--color-brand-orange)';

  if (loading) {
    return (
      <div
        className={cn(
          'bg-bg-panel border border-[var(--color-border-default)] chamfer-8',
          compact ? 'p-3' : 'p-4',
          className
        )}
      >
        <div className="animate-pulse space-y-2">
          <div className="h-3 w-20 bg-bg-overlay rounded" />
          <div className="h-6 w-16 bg-bg-overlay rounded" />
        </div>
      </div>
    );
  }

  return (
    <div
      className={cn(
        'bg-bg-panel border border-[var(--color-border-default)] chamfer-8 relative overflow-hidden',
        compact ? 'p-3' : 'p-4',
        className
      )}
    >
      {/* Domain accent line */}
      <div
        className="absolute top-0 left-0 right-0 h-0.5"
        style={{ backgroundColor: accentColor }}
      />

      {/* Label */}
      <div className="flex items-center gap-2 mb-2">
        {icon && (
          <span className="flex-shrink-0 text-text-muted" style={{ color: accentColor }}>
            {icon}
          </span>
        )}
        <span className="font-label text-label uppercase tracking-wider text-text-muted truncate">
          {label}
        </span>
      </div>

      {/* Value */}
      <div className="flex items-end gap-2">
        <span className={cn('font-sans font-bold text-text-primary', compact ? 'text-h3' : 'text-h2')}>
          {value}
        </span>
        {change && (
          <span
            className={cn(
              'text-label font-label mb-0.5',
              changeDirection === 'up' && 'text-status-active',
              changeDirection === 'down' && 'text-red',
              changeDirection === 'neutral' && 'text-text-muted'
            )}
          >
            {changeDirection === 'up' && '▲ '}
            {changeDirection === 'down' && '▼ '}
            {change}
          </span>
        )}
      </div>
    </div>
  );
}
