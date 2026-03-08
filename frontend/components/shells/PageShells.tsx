'use client';

import { type ReactNode } from 'react';
import { cn } from '@/lib/utils';

// ══════════════════════════════════════════════════════════════════
// SHARED PAGE SHELLS
// Consistent layout wrappers that make every module feel like
// the same product. Each shell handles responsive behavior,
// widescreen expansion, and content density.
// ══════════════════════════════════════════════════════════════════

// ── Module Dashboard Shell ────────────────────────────────────────
// Used for: billing-ops, fleet, hems, scheduling, compliance, etc.
// Provides: header, KPI strip, tabs, main content area, side panel slot.

export interface ModuleDashboardShellProps {
  /** Page title */
  readonly title: string;
  /** Optional subtitle / domain context */
  readonly subtitle?: string;
  /** KPI cards rendered in top strip */
  readonly kpiStrip?: ReactNode;
  /** Tab bar or filter bar */
  readonly toolbar?: ReactNode;
  /** Primary content area */
  readonly children: ReactNode;
  /** Right side panel (next actions, audit, AI) */
  readonly sidePanel?: ReactNode;
  /** Header actions (buttons, toggles) */
  readonly headerActions?: ReactNode;
  /** Banner (review required, override, etc.) */
  readonly banner?: ReactNode;
  /** Domain accent color */
  readonly accentColor?: string;
  readonly className?: string;
}

export function ModuleDashboardShell({
  title,
  subtitle,
  kpiStrip,
  toolbar,
  children,
  sidePanel,
  headerActions,
  banner,
  accentColor,
  className,
}: ModuleDashboardShellProps) {
  return (
    <div className={cn('flex flex-col h-full min-h-0', className)}>
      {/* Banner slot */}
      {banner && <div className="flex-shrink-0 px-4 pt-3 xl:px-6">{banner}</div>}

      {/* Header */}
      <header className="flex-shrink-0 px-4 pt-4 pb-2 xl:px-6">
        <div className="flex items-start justify-between gap-4">
          <div className="min-w-0">
            <div className="flex items-center gap-3">
              {accentColor && (
                <div
                  className="w-1 h-6 chamfer-4 flex-shrink-0"
                  style={{ backgroundColor: accentColor }}
                  aria-hidden
                />
              )}
              <h1 className="text-h1 font-sans font-bold text-zinc-100 truncate">{title}</h1>
            </div>
            {subtitle && (
              <p className="text-body text-zinc-500 mt-1 ml-4">{subtitle}</p>
            )}
          </div>
          {headerActions && (
            <div className="flex items-center gap-2 flex-shrink-0">
              {headerActions}
            </div>
          )}
        </div>
      </header>

      {/* KPI Strip */}
      {kpiStrip && (
        <div className="flex-shrink-0 px-4 py-3 xl:px-6">
          <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 xl:grid-cols-5 2xl:grid-cols-6 gap-3">
            {kpiStrip}
          </div>
        </div>
      )}

      {/* Toolbar (tabs/filters) */}
      {toolbar && (
        <div className="flex-shrink-0 px-4 xl:px-6">{toolbar}</div>
      )}

      {/* Main content area */}
      <div className="flex-1 min-h-0 flex gap-4 px-4 py-3 xl:px-6 overflow-hidden">
        {/* Primary content */}
        <main className={cn('flex-1 min-w-0 overflow-y-auto', sidePanel ? '3xl:max-w-[calc(100%-380px)]' : '')}>
          {children}
        </main>

        {/* Side panel */}
        {sidePanel && (
          <aside className="hidden xl:block w-[340px] 3xl:w-[380px] flex-shrink-0 overflow-y-auto space-y-3">
            {sidePanel}
          </aside>
        )}
      </div>
    </div>
  );
}

// ── Record Detail Shell ───────────────────────────────────────────
// Used for: individual claim, patient record, incident, trip, etc.
// Provides: summary header, tab-based sections, side audit trail.

export interface RecordDetailShellProps {
  /** Record summary header */
  readonly header: ReactNode;
  /** Main content (tabbed sections) */
  readonly children: ReactNode;
  /** Right panel (audit trail, related items) */
  readonly sidePanel?: ReactNode;
  /** Banner slot */
  readonly banner?: ReactNode;
  readonly className?: string;
}

export function RecordDetailShell({
  header,
  children,
  sidePanel,
  banner,
  className,
}: RecordDetailShellProps) {
  return (
    <div className={cn('flex flex-col h-full min-h-0', className)}>
      {banner && <div className="flex-shrink-0 px-4 pt-3 xl:px-6">{banner}</div>}

      <div className="flex-shrink-0 px-4 pt-4 xl:px-6">
        {header}
      </div>

      <div className="flex-1 min-h-0 flex gap-4 px-4 py-3 xl:px-6 overflow-hidden">
        <main className={cn('flex-1 min-w-0 overflow-y-auto', sidePanel ? '3xl:max-w-[calc(100%-380px)]' : '')}>
          {children}
        </main>

        {sidePanel && (
          <aside className="hidden xl:block w-[340px] 3xl:w-[380px] flex-shrink-0 overflow-y-auto space-y-3">
            {sidePanel}
          </aside>
        )}
      </div>
    </div>
  );
}

// ── Review Queue Shell ────────────────────────────────────────────
// Used for: review queues, approval workflows, flagged items.
// Provides: count/severity header, list/detail split layout.

export interface ReviewQueueShellProps {
  readonly title: string;
  readonly count: number;
  readonly headerActions?: ReactNode;
  /** Left: list of items */
  readonly list: ReactNode;
  /** Right: selected item detail */
  readonly detail?: ReactNode;
  /** Banner */
  readonly banner?: ReactNode;
  readonly className?: string;
}

export function ReviewQueueShell({
  title,
  count,
  headerActions,
  list,
  detail,
  banner,
  className,
}: ReviewQueueShellProps) {
  return (
    <div className={cn('flex flex-col h-full min-h-0', className)}>
      {banner && <div className="flex-shrink-0 px-4 pt-3 xl:px-6">{banner}</div>}

      <header className="flex-shrink-0 px-4 pt-4 pb-3 xl:px-6 border-b border-[var(--color-border-default)]">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            <h1 className="text-h2 font-sans font-bold text-zinc-100">{title}</h1>
            <span className="text-label font-label text-zinc-500 bg-bg-overlay px-2 py-0.5 chamfer-4">
              {count} item{count !== 1 ? 's' : ''}
            </span>
          </div>
          {headerActions}
        </div>
      </header>

      <div className="flex-1 min-h-0 flex overflow-hidden">
        {/* List panel */}
        <div className={cn(
          'overflow-y-auto border-r border-[var(--color-border-default)]',
          detail ? 'w-[380px] xl:w-[420px] flex-shrink-0' : 'flex-1'
        )}>
          {list}
        </div>

        {/* Detail panel */}
        {detail && (
          <div className="flex-1 min-w-0 overflow-y-auto">
            {detail}
          </div>
        )}
      </div>
    </div>
  );
}

// ── Settings / Admin Shell ────────────────────────────────────────
// Used for: settings pages, admin configuration, tenant management.

export interface SettingsShellProps {
  readonly title: string;
  readonly sections: readonly {
    readonly id: string;
    readonly label: string;
    readonly icon?: ReactNode;
  }[];
  readonly activeSection: string;
  readonly onSectionChange: (_id: string) => void;
  readonly children: ReactNode;
  readonly className?: string;
}

export function SettingsShell({
  title,
  sections,
  activeSection,
  onSectionChange,
  children,
  className,
}: SettingsShellProps) {
  return (
    <div className={cn('flex flex-col h-full min-h-0', className)}>
      <header className="flex-shrink-0 px-4 pt-4 pb-3 xl:px-6 border-b border-[var(--color-border-default)]">
        <h1 className="text-h1 font-sans font-bold text-zinc-100">{title}</h1>
      </header>

      <div className="flex-1 min-h-0 flex overflow-hidden">
        {/* Section nav */}
        <nav className="w-56 flex-shrink-0 overflow-y-auto border-r border-[var(--color-border-default)] py-2">
          {sections.map((section) => (
            <button
              key={section.id}
              onClick={() => onSectionChange(section.id)}
              className={cn(
                'w-full flex items-center gap-2 px-4 py-2.5 text-left text-body transition-colors duration-fast',
                section.id === activeSection
                  ? 'text-[#FF4D00] bg-[#FF4D00]-ghost border-r-2 border-orange'
                  : 'text-zinc-500 hover:text-zinc-100 hover:bg-bg-overlay'
              )}
              type="button"
            >
              {section.icon}
              {section.label}
            </button>
          ))}
        </nav>

        {/* Content */}
        <main className="flex-1 min-w-0 overflow-y-auto p-4 xl:p-6">
          {children}
        </main>
      </div>
    </div>
  );
}

// ── Dashboard Grid System ─────────────────────────────────────────
// Responsive grid that adapts from mobile to ultra-wide.

export interface DashboardGridProps {
  readonly children: ReactNode;
  /** Minimum column width in pixels */
  readonly minColWidth?: number;
  /** Gap size */
  readonly gap?: 'sm' | 'md' | 'lg';
  readonly className?: string;
}

export function DashboardGrid({
  children,
  minColWidth = 320,
  gap = 'md',
  className,
}: DashboardGridProps) {
  const gapClass = { sm: 'gap-2', md: 'gap-3', lg: 'gap-4' }[gap];

  return (
    <div
      className={cn('grid', gapClass, className)}
      style={{
        gridTemplateColumns: `repeat(auto-fit, minmax(min(${minColWidth}px, 100%), 1fr))`,
      }}
    >
      {children}
    </div>
  );
}

// ── Grid Cell Span ────────────────────────────────────────────────
// For controlling individual cell spans in the dashboard grid.

export interface GridCellProps {
  readonly children: ReactNode;
  readonly span?: 1 | 2 | 3;
  readonly rowSpan?: 1 | 2;
  readonly className?: string;
}

export function GridCell({ children, span = 1, rowSpan = 1, className }: GridCellProps) {
  const spanClass = { 1: '', 2: 'md:col-span-2', 3: 'md:col-span-3' }[span];
  const rowSpanClass = { 1: '', 2: 'md:row-span-2' }[rowSpan];

  return (
    <div className={cn(spanClass, rowSpanClass, className)}>
      {children}
    </div>
  );
}
