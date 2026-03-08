'use client';

import { cn } from '@/lib/utils';
import type { StatusVariant } from '@/lib/design-system/tokens';
import { STATUS_COLOR_MAP } from '@/lib/design-system/tokens';
import { STATUS_DISPLAY } from '@/lib/design-system/language';

export interface AuditEvent {
  readonly id: string;
  readonly timestamp: string;
  readonly action: string;
  readonly actor: string;
  readonly detail?: string;
  readonly status?: StatusVariant;
  readonly domain?: string;
  readonly metadata?: Record<string, string>;
}

export interface AuditEventListProps {
  readonly events: readonly AuditEvent[];
  readonly title?: string;
  readonly maxVisible?: number;
  readonly onViewAll?: () => void;
  readonly loading?: boolean;
  readonly className?: string;
}

export function AuditEventList({
  events,
  title = 'Audit Trail',
  maxVisible = 10,
  onViewAll,
  loading = false,
  className,
}: AuditEventListProps) {
  const visible = events.slice(0, maxVisible);
  const hasMore = events.length > maxVisible;

  return (
    <div
      className={cn(
        'bg-[#0A0A0B] border border-[var(--color-border-default)] chamfer-8 p-4',
        className
      )}
    >
      <div className="flex items-center justify-between mb-3">
        <h3 className="font-label text-label uppercase tracking-wider text-zinc-400">
          {title}
          <span className="text-zinc-500 ml-2">({events.length})</span>
        </h3>
        {(hasMore || onViewAll) && (
          <button
            onClick={onViewAll}
            className="text-label font-label text-[#FF4D00] hover:text-[#FF4D00] transition-colors duration-fast"
            type="button"
          >
            View All →
          </button>
        )}
      </div>

      {loading ? (
        <div className="space-y-2">
          {[0, 1, 2, 3].map(i => (
            <div key={i} className="animate-pulse flex items-center gap-3 py-2">
              <div className="h-2 w-2  bg-bg-overlay flex-shrink-0" />
              <div className="h-3 flex-1 bg-bg-overlay " />
              <div className="h-3 w-20 bg-bg-overlay " />
            </div>
          ))}
        </div>
      ) : visible.length === 0 ? (
        <p className="text-body text-zinc-500 text-center py-6">No audit events recorded.</p>
      ) : (
        <div className="divide-y divide-[var(--color-border-subtle)]">
          {visible.map((event) => (
            <div key={event.id} className="py-2 first:pt-0 last:pb-0">
              <div className="flex items-start justify-between gap-2">
                <div className="flex items-start gap-2 min-w-0 flex-1">
                  {event.status && (
                    <span
                      className="w-2 h-2  flex-shrink-0 mt-1.5"
                      style={{ backgroundColor: STATUS_COLOR_MAP[event.status] }}
                      title={STATUS_DISPLAY[event.status]}
                      aria-hidden
                    />
                  )}
                  <div className="min-w-0">
                    <p className="text-body text-zinc-100 truncate">
                      <span className="font-medium">{event.action}</span>
                      {event.domain && (
                        <span className="text-zinc-500 ml-1">· {event.domain}</span>
                      )}
                    </p>
                    {event.detail && (
                      <p className="text-label text-zinc-500 mt-0.5 truncate">
                        {event.detail}
                      </p>
                    )}
                  </div>
                </div>
                <div className="text-right flex-shrink-0">
                  <time className="text-micro text-text-disabled block">{event.timestamp}</time>
                  <span className="text-micro text-text-disabled">{event.actor}</span>
                </div>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
