'use client';

import { type ReactNode } from 'react';
import { cn } from '@/lib/utils';

export interface FilterOption {
  readonly value: string;
  readonly label: string;
  readonly count?: number;
}

export interface FilterBarProps {
  readonly filters: readonly {
    readonly id: string;
    readonly label: string;
    readonly options: readonly FilterOption[];
    readonly value: string;
    readonly onChange: (_value: string) => void;
  }[];
  readonly searchValue?: string;
  readonly onSearchChange?: (_value: string) => void;
  readonly searchPlaceholder?: string;
  readonly actions?: ReactNode;
  readonly className?: string;
}

export function FilterBar({
  filters,
  searchValue,
  onSearchChange,
  searchPlaceholder = 'Search...',
  actions,
  className,
}: FilterBarProps) {
  return (
    <div
      className={cn(
        'flex items-center gap-3 flex-wrap p-3 bg-[#0A0A0B] border border-[var(--color-border-default)] chamfer-4',
        className
      )}
    >
      {/* Search */}
      {onSearchChange && (
        <div className="relative flex-1 min-w-[200px] max-w-sm">
          <svg
            className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-zinc-500"
            fill="none"
            viewBox="0 0 24 24"
            stroke="currentColor"
            strokeWidth={2}
            aria-hidden
          >
            <path strokeLinecap="round" strokeLinejoin="round" d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
          </svg>
          <input
            type="text"
            value={searchValue ?? ''}
            onChange={(e) => onSearchChange(e.target.value)}
            placeholder={searchPlaceholder}
            className="w-full bg-bg-input border border-[var(--color-border-default)] text-zinc-100 
                       text-body pl-10 pr-3 py-2 chamfer-4 placeholder:text-text-disabled
                       focus:outline-none focus:border-orange focus:shadow-[var(--focus-ring)]
                       transition-colors duration-fast"
          />
        </div>
      )}

      {/* Filter dropdowns */}
      {filters.map((filter) => (
        <div key={filter.id} className="flex items-center gap-1.5">
          <label
            htmlFor={`filter-${filter.id}`}
            className="text-micro font-label uppercase tracking-wider text-zinc-500 whitespace-nowrap"
          >
            {filter.label}
          </label>
          <select
            id={`filter-${filter.id}`}
            value={filter.value}
            onChange={(e) => filter.onChange(e.target.value)}
            className="bg-bg-input border border-[var(--color-border-default)] text-zinc-100 
                       text-body px-2 py-1.5 chamfer-4 cursor-pointer
                       focus:outline-none focus:border-orange"
          >
            {filter.options.map((opt) => (
              <option key={opt.value} value={opt.value}>
                {opt.label}{opt.count !== undefined ? ` (${opt.count})` : ''}
              </option>
            ))}
          </select>
        </div>
      ))}

      {/* Actions slot */}
      {actions && (
        <div className="ml-auto flex items-center gap-2">
          {actions}
        </div>
      )}
    </div>
  );
}

// ── Tabs ──────────────────────────────────────────────────────────

export interface TabItem {
  readonly id: string;
  readonly label: string;
  readonly count?: number;
  readonly icon?: ReactNode;
  readonly disabled?: boolean;
}

export interface TabBarProps {
  readonly tabs: readonly TabItem[];
  readonly activeTab: string;
  readonly onTabChange: (_tabId: string) => void;
  readonly size?: 'sm' | 'md';
  readonly className?: string;
}

export function TabBar({
  tabs,
  activeTab,
  onTabChange,
  size = 'md',
  className,
}: TabBarProps) {
  return (
    <div
      className={cn(
        'flex items-center gap-0 border-b border-[var(--color-border-default)] overflow-x-auto',
        className
      )}
      role="tablist"
    >
      {tabs.map((tab) => {
        const isActive = tab.id === activeTab;
        return (
          <button
            key={tab.id}
            role="tab"
            aria-selected={isActive}
            aria-controls={`tabpanel-${tab.id}`}
            disabled={tab.disabled}
            onClick={() => onTabChange(tab.id)}
            className={cn(
              'relative flex items-center gap-1.5 font-label uppercase tracking-wider whitespace-nowrap',
              'transition-colors duration-fast border-b-2 -mb-px',
              size === 'sm' ? 'px-3 py-2 text-micro' : 'px-4 py-2.5 text-label',
              isActive
                ? 'text-[#FF4D00] border-orange'
                : 'text-zinc-500 border-transparent hover:text-zinc-400 hover:border-[var(--color-border-subtle)]',
              tab.disabled && 'opacity-40 cursor-not-allowed'
            )}
            type="button"
          >
            {tab.icon}
            {tab.label}
            {tab.count !== undefined && (
              <span
                className={cn(
                  'text-micro px-1.5 py-0.5 ',
                  isActive ? 'bg-[rgba(255,77,0,0.12)] text-[#FF4D00]' : 'bg-bg-overlay text-zinc-500'
                )}
              >
                {tab.count}
              </span>
            )}
          </button>
        );
      })}
    </div>
  );
}

// ── Tab Panel ─────────────────────────────────────────────────────

export interface TabPanelProps {
  readonly tabId: string;
  readonly activeTab: string;
  readonly children: ReactNode;
  readonly className?: string;
}

export function TabPanel({ tabId, activeTab, children, className }: TabPanelProps) {
  if (tabId !== activeTab) return null;
  return (
    <div
      id={`tabpanel-${tabId}`}
      role="tabpanel"
      aria-labelledby={tabId}
      className={cn('py-4', className)}
    >
      {children}
    </div>
  );
}

// ── Record Summary Header ─────────────────────────────────────────

export interface RecordSummaryProps {
  readonly title: string;
  readonly subtitle?: string;
  readonly status?: ReactNode;
  readonly breadcrumbs?: readonly { label: string; href?: string }[];
  readonly actions?: ReactNode;
  readonly metadata?: readonly { label: string; value: string }[];
  readonly className?: string;
}

export function RecordSummary({
  title,
  subtitle,
  status,
  breadcrumbs,
  actions,
  metadata,
  className,
}: RecordSummaryProps) {
  return (
    <div className={cn('border-b border-[var(--color-border-default)] pb-4 mb-4', className)}>
      {/* Breadcrumbs */}
      {breadcrumbs && breadcrumbs.length > 0 && (
        <nav className="flex items-center gap-1 mb-2" aria-label="Breadcrumb">
          {breadcrumbs.map((crumb, i) => (
            <span key={i} className="flex items-center gap-1">
              {i > 0 && <span className="text-text-disabled mx-1">/</span>}
              {crumb.href ? (
                <a
                  href={crumb.href}
                  className="text-label text-zinc-500 hover:text-[#FF4D00] transition-colors duration-fast"
                >
                  {crumb.label}
                </a>
              ) : (
                <span className="text-label text-zinc-400">{crumb.label}</span>
              )}
            </span>
          ))}
        </nav>
      )}

      {/* Title row */}
      <div className="flex items-start justify-between gap-4">
        <div className="min-w-0">
          <div className="flex items-center gap-3">
            <h1 className="text-h2 font-sans font-bold text-zinc-100 truncate">{title}</h1>
            {status}
          </div>
          {subtitle && (
            <p className="text-body text-zinc-500 mt-1">{subtitle}</p>
          )}
        </div>
        {actions && (
          <div className="flex items-center gap-2 flex-shrink-0">
            {actions}
          </div>
        )}
      </div>

      {/* Metadata strip */}
      {metadata && metadata.length > 0 && (
        <div className="flex items-center gap-4 mt-3 flex-wrap">
          {metadata.map((item, i) => (
            <div key={i} className="flex items-center gap-1.5">
              <span className="text-micro font-label uppercase tracking-wider text-text-disabled">
                {item.label}
              </span>
              <span className="text-label text-zinc-400">{item.value}</span>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

// ── Simple Mode Toggle ────────────────────────────────────────────

export interface SimpleModeToggleProps {
  readonly isSimple: boolean;
  readonly onToggle: (_value: boolean) => void;
  readonly className?: string;
}

export function SimpleModeToggle({ isSimple, onToggle, className }: SimpleModeToggleProps) {
  return (
    <button
      onClick={() => onToggle(!isSimple)}
      className={cn(
        'flex items-center gap-2 px-3 py-1.5 text-label font-label uppercase tracking-wider',
        'border chamfer-4 transition-all duration-fast',
        isSimple
          ? 'bg-[rgba(255,77,0,0.12)] text-[#FF4D00] border-orange/30'
          : 'bg-[#0A0A0B] text-zinc-500 border-[var(--color-border-default)] hover:text-zinc-400',
        className
      )}
      type="button"
      aria-pressed={isSimple}
    >
      <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2} aria-hidden>
        {isSimple ? (
          <path strokeLinecap="round" strokeLinejoin="round" d="M4 6h16M4 12h8m-8 6h16" />
        ) : (
          <path strokeLinecap="round" strokeLinejoin="round" d="M4 6h16M4 10h16M4 14h16M4 18h16" />
        )}
      </svg>
      {isSimple ? 'Simple View' : 'Detailed View'}
    </button>
  );
}

// ── Drilldown Drawer ──────────────────────────────────────────────

export interface DrilldownDrawerProps {
  readonly isOpen: boolean;
  readonly onClose: () => void;
  readonly title: string;
  readonly subtitle?: string;
  readonly children: ReactNode;
  readonly width?: 'sm' | 'md' | 'lg' | 'xl';
  readonly actions?: ReactNode;
  readonly className?: string;
}

export function DrilldownDrawer({
  isOpen,
  onClose,
  title,
  subtitle,
  children,
  width = 'md',
  actions,
  className,
}: DrilldownDrawerProps) {
  const widthClasses = {
    sm: 'max-w-sm',
    md: 'max-w-lg',
    lg: 'max-w-2xl',
    xl: 'max-w-4xl',
  };

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 flex justify-end">
      {/* Backdrop */}
      <div
        className="absolute inset-0 bg-black/60 transition-opacity duration-base"
        onClick={onClose}
        aria-hidden
      />

      {/* Drawer panel */}
      <div
        className={cn(
          'relative w-full h-full bg-[#0A0A0B] border-l border-[var(--color-border-default)]',
          'flex flex-col overflow-hidden animate-slide-in-right',
          widthClasses[width],
          'chamfer-drawer',
          className
        )}
        role="dialog"
        aria-modal
        aria-label={title}
      >
        {/* Header */}
        <div className="flex items-center justify-between p-4 border-b border-[var(--color-border-default)]">
          <div className="min-w-0">
            <h2 className="text-h3 font-sans font-bold text-zinc-100 truncate">{title}</h2>
            {subtitle && (
              <p className="text-label text-zinc-500 mt-0.5">{subtitle}</p>
            )}
          </div>
          <div className="flex items-center gap-2">
            {actions}
            <button
              onClick={onClose}
              className="p-2 text-zinc-500 hover:text-zinc-100 transition-colors duration-fast"
              type="button"
              aria-label="Close drawer"
            >
              <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                <path strokeLinecap="round" strokeLinejoin="round" d="M6 18L18 6M6 6l12 12" />
              </svg>
            </button>
          </div>
        </div>

        {/* Content */}
        <div className="flex-1 overflow-y-auto p-4">
          {children}
        </div>
      </div>
    </div>
  );
}
