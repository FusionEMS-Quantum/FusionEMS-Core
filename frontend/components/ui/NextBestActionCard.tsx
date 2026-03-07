'use client';

import { type ReactNode } from 'react';
import { cn } from '@/lib/utils';
import type { SeverityLevel } from '@/lib/design-system/tokens';
import { SEVERITY_COLOR_MAP, SEVERITY_BG_MAP } from '@/lib/design-system/tokens';
import { SEVERITY_GUIDANCE, type ActionExplanation } from '@/lib/design-system/language';
import { SeverityBadge } from './SeverityBadge';

export interface NextAction {
  readonly id: string;
  readonly title: string;
  readonly severity: SeverityLevel;
  readonly domain?: string;
  readonly explanation?: ActionExplanation;
  readonly actionLabel?: string;
  readonly onAction?: () => void;
  readonly href?: string;
  readonly icon?: ReactNode;
}

export interface NextBestActionCardProps {
  readonly actions: readonly NextAction[];
  readonly title?: string;
  readonly maxVisible?: number;
  readonly loading?: boolean;
  readonly className?: string;
}

export function NextBestActionCard({
  actions,
  title = 'Next Best Actions',
  maxVisible = 3,
  loading = false,
  className,
}: NextBestActionCardProps) {
  const sorted = [...actions].sort((a, b) => {
    const order: Record<SeverityLevel, number> = {
      BLOCKING: 0, HIGH: 1, MEDIUM: 2, LOW: 3, INFORMATIONAL: 4,
    };
    return order[a.severity] - order[b.severity];
  });
  const visible = sorted.slice(0, maxVisible);

  return (
    <div
      className={cn(
        'bg-bg-panel border border-[var(--color-border-default)] chamfer-8 p-4',
        className
      )}
    >
      <h3 className="font-label text-label uppercase tracking-wider text-text-secondary mb-3">
        {title}
        {actions.length > 0 && (
          <span className="text-text-muted ml-2">({actions.length})</span>
        )}
      </h3>

      {loading ? (
        <div className="space-y-3">
          {[0, 1, 2].map(i => (
            <div key={i} className="animate-pulse p-3 bg-bg-base rounded space-y-2">
              <div className="h-3 w-2/3 bg-bg-overlay rounded" />
              <div className="h-2 w-1/2 bg-bg-overlay rounded" />
            </div>
          ))}
        </div>
      ) : visible.length === 0 ? (
        <div className="text-center py-6">
          <p className="text-body text-text-muted">No actions required right now.</p>
          <p className="text-label text-text-disabled mt-1">You are up to date.</p>
        </div>
      ) : (
        <ul className="space-y-2" role="list">
          {visible.map((action) => (
            <NextActionItem key={action.id} action={action} />
          ))}
        </ul>
      )}
    </div>
  );
}

function NextActionItem({ action }: { readonly action: NextAction }) {
  const bgColor = SEVERITY_BG_MAP[action.severity];
  const borderColor = SEVERITY_COLOR_MAP[action.severity];

  const content = (
    <div
      className="p-3 chamfer-4 transition-all duration-fast hover:brightness-110 cursor-pointer"
      style={{
        backgroundColor: bgColor,
        borderLeft: `3px solid ${borderColor}`,
      }}
    >
      <div className="flex items-start justify-between gap-2">
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 mb-1">
            {action.icon}
            <span className="text-body text-text-primary font-medium truncate">
              {action.title}
            </span>
          </div>
          {action.domain && (
            <span className="text-micro font-label uppercase tracking-wider text-text-muted">
              {action.domain}
            </span>
          )}
          {action.explanation ? (
            <div className="mt-2 space-y-0.5">
              <p className="text-label text-text-secondary">{action.explanation.what}</p>
              <p className="text-label text-text-muted">{action.explanation.why}</p>
              <p className="text-label text-text-primary font-medium mt-1">→ {action.explanation.next}</p>
            </div>
          ) : (
            <p className="text-label text-text-muted mt-1">
              {SEVERITY_GUIDANCE[action.severity]}
            </p>
          )}
        </div>
        <SeverityBadge severity={action.severity} size="sm" />
      </div>

      {action.actionLabel && action.onAction && (
        <button
          onClick={(e) => { e.stopPropagation(); action.onAction?.(); }}
          className="mt-2 text-label font-label font-medium uppercase tracking-wider 
                     hover:underline transition-colors duration-fast"
          style={{ color: borderColor }}
          type="button"
        >
          {action.actionLabel} →
        </button>
      )}
    </div>
  );

  if (action.href) {
    return (
      <li>
        <a href={action.href} className="block no-underline">
          {content}
        </a>
      </li>
    );
  }

  return <li>{content}</li>;
}
