'use client';

import { type ReactNode } from 'react';
import { cva, type VariantProps } from 'class-variance-authority';
import { cn } from '@/lib/utils';
import type { SeverityLevel } from '@/lib/design-system/tokens';
import { SEVERITY_LABEL } from '@/lib/design-system/tokens';

const badgeVariants = cva(
  'inline-flex items-center gap-1.5 font-label uppercase tracking-wider whitespace-nowrap',
  {
    variants: {
      severity: {
        BLOCKING: 'bg-red-ghost text-red border border-red/30',
        HIGH: 'bg-orange-ghost text-orange border border-orange/30',
        MEDIUM: 'bg-yellow-500/10 text-yellow-400 border border-yellow-500/20',
        LOW: 'bg-sky-500/10 text-sky-400 border border-sky-500/20',
        INFORMATIONAL: 'bg-gray-500/10 text-text-muted border border-gray-500/20',
      },
      size: {
        sm: 'px-2 py-0.5 text-micro',
        md: 'px-3 py-1 text-label',
        lg: 'px-4 py-1.5 text-body',
      },
    },
    defaultVariants: {
      severity: 'INFORMATIONAL',
      size: 'md',
    },
  }
);

export interface SeverityBadgeProps extends VariantProps<typeof badgeVariants> {
  readonly severity: SeverityLevel;
  readonly label?: string;
  readonly icon?: ReactNode;
  readonly pulse?: boolean;
  readonly className?: string;
}

export function SeverityBadge({
  severity,
  label,
  icon,
  pulse = false,
  size,
  className,
}: SeverityBadgeProps) {
  const displayLabel = label ?? SEVERITY_LABEL[severity];
  const isBlocking = severity === 'BLOCKING';

  return (
    <span
      className={cn(
        badgeVariants({ severity, size }),
        'chamfer-4',
        className
      )}
      role="status"
      aria-label={`Severity: ${displayLabel}`}
    >
      {(pulse || isBlocking) && (
        <span
          className={cn(
            'inline-block h-2 w-2 rounded-full',
            isBlocking ? 'bg-red animate-pulse' : 'bg-current'
          )}
          aria-hidden
        />
      )}
      {icon}
      {displayLabel}
    </span>
  );
}
