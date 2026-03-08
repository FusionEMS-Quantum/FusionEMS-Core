'use client';

import { type ReactNode } from 'react';
import { cn } from '@/lib/utils';
import type { StatusVariant } from '@/lib/design-system/tokens';
import { STATUS_COLOR_MAP } from '@/lib/design-system/tokens';

export interface TimelineEvent {
  readonly id: string;
  readonly timestamp: string;
  readonly title: string;
  readonly description?: string;
  readonly status?: StatusVariant;
  readonly domain?: string;
  readonly actor?: string;
  readonly icon?: ReactNode;
  readonly expandable?: boolean;
  readonly detail?: ReactNode;
}

export interface TimelinePanelProps {
  readonly events: readonly TimelineEvent[];
  readonly title?: string;
  readonly maxVisible?: number;
  readonly onLoadMore?: () => void;
  readonly loading?: boolean;
  readonly emptyMessage?: string;
  readonly className?: string;
}

export function TimelinePanel({
  events,
  title = 'Timeline',
  maxVisible,
  onLoadMore,
  loading = false,
  emptyMessage = 'No events to display.',
  className,
}: TimelinePanelProps) {
  const visible = maxVisible ? events.slice(0, maxVisible) : events;
  const hasMore = maxVisible ? events.length > maxVisible : false;

  return (
    <div
      className={cn(
        'bg-[#0A0A0B] border border-[var(--color-border-default)] chamfer-8 p-4',
        className
      )}
    >
      <h3 className="font-label text-label uppercase tracking-wider text-zinc-400 mb-4">
        {title}
        <span className="text-zinc-500 ml-2">({events.length})</span>
      </h3>

      {loading ? (
        <div className="space-y-3">
          {[0, 1, 2].map(i => (
            <div key={i} className="animate-pulse flex gap-3">
              <div className="w-2 h-2  bg-bg-overlay mt-1.5 flex-shrink-0" />
              <div className="flex-1 space-y-1">
                <div className="h-3 w-3/4 bg-bg-overlay " />
                <div className="h-2 w-1/2 bg-bg-overlay " />
              </div>
            </div>
          ))}
        </div>
      ) : visible.length === 0 ? (
        <p className="text-body text-zinc-500 text-center py-6">{emptyMessage}</p>
      ) : (
        <div className="relative">
          {/* Vertical connector line */}
          <div className="absolute left-[5px] top-2 bottom-2 w-px bg-[var(--color-border-subtle)]" />

          <ul className="space-y-3" role="list">
            {visible.map((event) => (
              <TimelineEventItem key={event.id} event={event} />
            ))}
          </ul>

          {(hasMore || onLoadMore) && (
            <button
              onClick={onLoadMore}
              className="mt-3 w-full text-center text-label font-label text-zinc-500 
                         hover:text-[#FF4D00] transition-colors duration-fast py-1"
              type="button"
            >
              Show more events
            </button>
          )}
        </div>
      )}
    </div>
  );
}

function TimelineEventItem({ event }: { readonly event: TimelineEvent }) {
  const dotColor = event.status
    ? STATUS_COLOR_MAP[event.status]
    : 'var(--color-text-muted)';

  return (
    <li className="relative flex gap-3 pl-0 group">
      {/* Dot */}
      <div
        className="w-[10px] h-[10px]  flex-shrink-0 mt-1 z-10 border-2 border-bg-panel"
        style={{ backgroundColor: dotColor }}
        aria-hidden
      />

      {/* Content */}
      <div className="flex-1 min-w-0">
        <div className="flex items-center gap-2 flex-wrap">
          <span className="text-body text-zinc-100 font-medium truncate">
            {event.title}
          </span>
          {event.domain && (
            <span className="text-micro font-label uppercase tracking-wider text-zinc-500">
              {event.domain}
            </span>
          )}
        </div>
        {event.description && (
          <p className="text-label text-zinc-500 mt-0.5 leading-snug">
            {event.description}
          </p>
        )}
        <div className="flex items-center gap-2 mt-1">
          <time className="text-micro text-text-disabled">
            {event.timestamp}
          </time>
          {event.actor && (
            <span className="text-micro text-text-disabled">
              · {event.actor}
            </span>
          )}
        </div>
        {event.detail && (
          <div className="mt-2 p-2 bg-[#050505] border border-[var(--color-border-subtle)] chamfer-4 text-label text-zinc-400">
            {event.detail}
          </div>
        )}
      </div>
    </li>
  );
}
