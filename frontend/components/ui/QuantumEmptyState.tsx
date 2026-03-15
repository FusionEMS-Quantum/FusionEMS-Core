'use client';

import * as React from 'react';
import { clsx } from 'clsx';

export interface QuantumEmptyStateProps {
  icon?: React.ReactNode;
  title: string;
  description?: string;
  action?: React.ReactNode;
  actionLabel?: string;
  onAction?: () => void;
  className?: string;
}

export function QuantumEmptyState({
  icon,
  title,
  description,
  action,
  actionLabel,
  onAction,
  className,
}: QuantumEmptyStateProps) {
  return (
    <div
      className={clsx(
        'quantum-panel-soft flex flex-col items-center justify-center px-6 py-14 text-center quantum-noise',
        className,
      )}
    >
      {icon && (
        <div className="mb-4 flex h-14 w-14 items-center justify-center border border-[var(--color-border-default)] bg-[rgba(255,255,255,0.03)] text-[var(--color-brand-orange-bright)] chamfer-8" aria-hidden="true">
          {icon}
        </div>
      )}
      <h3
        className="font-label text-h3 font-semibold uppercase tracking-[0.08em] text-zinc-100 mb-2"
      >
        {title}
      </h3>
      {description && (
        <p className="text-body text-zinc-500 max-w-md mb-6">
          {description}
        </p>
      )}
      {action && <div>{action}</div>}
      {!action && actionLabel && onAction && (
        <button
          onClick={onAction}
          className="quantum-btn-primary px-4"
        >
          {actionLabel}
        </button>
      )}
    </div>
  );
}
