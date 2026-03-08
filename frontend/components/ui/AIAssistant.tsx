'use client';

import { useState } from 'react';
import { cn } from '@/lib/utils';
import type { SeverityLevel, SystemDomain } from '@/lib/design-system/tokens';
import { DOMAIN_LABEL } from '@/lib/design-system/tokens';
import { SeverityBadge } from './SeverityBadge';

// ══════════════════════════════════════════════════════════════════
// AI ASSISTANT UI COMPONENTS
// Standardized surfaces for AI-generated content that follow
// the Quantum design system. AI never invents its own UI.
// ══════════════════════════════════════════════════════════════════

// ── AI Explanation Card ──────────────────────────────────────────
// Standard "What / Why / Next" explanation following global copy pattern.

export interface AIExplanationCardProps {
  readonly what: string;
  readonly why: string;
  readonly next: string;
  readonly domain?: SystemDomain;
  readonly severity?: SeverityLevel;
  readonly confidence?: number;
  readonly requiresReview?: boolean;
  readonly onDismiss?: () => void;
  readonly className?: string;
}

export function AIExplanationCard({
  what,
  why,
  next,
  domain,
  severity,
  confidence,
  requiresReview = false,
  onDismiss,
  className,
}: AIExplanationCardProps) {
  const [collapsed, setCollapsed] = useState(false);

  return (
    <div
      className={cn(
        'bg-bg-panel border border-[var(--color-border-default)] chamfer-8 overflow-hidden',
        requiresReview && 'border-l-4 border-l-[#818cf8]',
        className
      )}
    >
      {/* Header */}
      <div className="flex items-center justify-between px-4 py-2.5 border-b border-[var(--color-border-subtle)]">
        <div className="flex items-center gap-2">
          <svg
            className="w-4 h-4 text-[#818cf8]"
            fill="none"
            viewBox="0 0 24 24"
            stroke="currentColor"
            strokeWidth={2}
            aria-hidden
          >
            <path strokeLinecap="round" strokeLinejoin="round" d="M9.663 17h4.673M12 3v1m6.364 1.636l-.707.707M21 12h-1M4 12H3m3.343-5.657l-.707-.707m2.828 9.9a5 5 0 117.072 0l-.548.547A3.374 3.374 0 0014 18.469V19a2 2 0 11-4 0v-.531c0-.895-.356-1.754-.988-2.386l-.548-.547z" />
          </svg>
          <span className="text-label font-label uppercase tracking-wider text-[#818cf8]">
            AI Insight
          </span>
          {domain && (
            <span className="text-micro font-label uppercase tracking-wider text-text-muted">
              · {DOMAIN_LABEL[domain]}
            </span>
          )}
          {severity && <SeverityBadge severity={severity} size="sm" />}
        </div>

        <div className="flex items-center gap-2">
          {confidence !== undefined && (
            <span className="text-micro font-label text-text-disabled">
              {Math.round(confidence * 100)}% confidence
            </span>
          )}
          <button
            onClick={() => setCollapsed(!collapsed)}
            className="text-text-muted hover:text-text-primary transition-colors duration-fast p-1"
            type="button"
            aria-label={collapsed ? 'Expand' : 'Collapse'}
          >
            <svg className={cn('w-4 h-4 transition-transform duration-fast', collapsed && '-rotate-90')} fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
              <path strokeLinecap="round" strokeLinejoin="round" d="M19 9l-7 7-7-7" />
            </svg>
          </button>
          {onDismiss && (
            <button
              onClick={onDismiss}
              className="text-text-muted hover:text-text-primary transition-colors duration-fast p-1"
              type="button"
              aria-label="Dismiss"
            >
              <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                <path strokeLinecap="round" strokeLinejoin="round" d="M6 18L18 6M6 6l12 12" />
              </svg>
            </button>
          )}
        </div>
      </div>

      {/* Body */}
      {!collapsed && (
        <div className="p-4 space-y-3">
          <div>
            <span className="text-micro font-label uppercase tracking-wider text-text-disabled block mb-1">
              What happened
            </span>
            <p className="text-body text-text-primary leading-snug">{what}</p>
          </div>
          <div>
            <span className="text-micro font-label uppercase tracking-wider text-text-disabled block mb-1">
              Why it matters
            </span>
            <p className="text-body text-text-muted leading-snug">{why}</p>
          </div>
          <div>
            <span className="text-micro font-label uppercase tracking-wider text-text-disabled block mb-1">
              Do this next
            </span>
            <p className="text-body text-text-secondary font-medium leading-snug">→ {next}</p>
          </div>

          {requiresReview && (
            <div className="flex items-center gap-2 pt-2 border-t border-[var(--color-border-subtle)]">
              <svg className="w-4 h-4 text-[#818cf8]" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2} aria-hidden>
                <path strokeLinecap="round" strokeLinejoin="round" d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
                <path strokeLinecap="round" strokeLinejoin="round" d="M2.458 12C3.732 7.943 7.523 5 12 5c4.478 0 8.268 2.943 9.542 7-1.274 4.057-5.064 7-9.542 7-4.477 0-8.268-2.943-9.542-7z" />
              </svg>
              <span className="text-label text-[#818cf8] font-medium">
                Human review required before acting on this recommendation.
              </span>
            </div>
          )}
        </div>
      )}
    </div>
  );
}

// ── AI Context Panel ─────────────────────────────────────────────
// Standardized right-side panel for AI suggestions/explanations.

export interface AIContextPanelProps {
  readonly suggestions?: readonly AIExplanationCardProps[];
  readonly title?: string;
  readonly loading?: boolean;
  readonly onAskAI?: (_question: string) => void;
  readonly className?: string;
}

export function AIContextPanel({
  suggestions = [],
  title = 'AI Assistant',
  loading = false,
  onAskAI,
  className,
}: AIContextPanelProps) {
  const [question, setQuestion] = useState('');

  const handleAsk = () => {
    if (question.trim() && onAskAI) {
      onAskAI(question.trim());
      setQuestion('');
    }
  };

  return (
    <div className={cn('flex flex-col gap-3', className)}>
      <div className="flex items-center gap-2">
        <svg className="w-4 h-4 text-[#818cf8]" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2} aria-hidden>
          <path strokeLinecap="round" strokeLinejoin="round" d="M9.663 17h4.673M12 3v1m6.364 1.636l-.707.707M21 12h-1M4 12H3m3.343-5.657l-.707-.707m2.828 9.9a5 5 0 117.072 0l-.548.547A3.374 3.374 0 0014 18.469V19a2 2 0 11-4 0v-.531c0-.895-.356-1.754-.988-2.386l-.548-.547z" />
        </svg>
        <h3 className="font-label text-label uppercase tracking-wider text-[#818cf8]">
          {title}
        </h3>
      </div>

      {/* Ask AI input */}
      {onAskAI && (
        <div className="flex gap-2">
          <input
            type="text"
            value={question}
            onChange={(e) => setQuestion(e.target.value)}
            onKeyDown={(e) => e.key === 'Enter' && handleAsk()}
            placeholder="Ask AI about this screen..."
            className="flex-1 bg-bg-input border border-[var(--color-border-default)] text-text-primary 
                       text-label px-3 py-2 chamfer-4 placeholder:text-text-disabled
                       focus:outline-none focus:border-[#818cf8]"
          />
          <button
            onClick={handleAsk}
            disabled={!question.trim()}
            className="px-3 py-2 bg-[rgba(129,140,248,0.15)] text-[#818cf8] chamfer-4 text-label
                       hover:bg-[rgba(129,140,248,0.25)] transition-colors duration-fast
                       disabled:opacity-40"
            type="button"
          >
            Ask
          </button>
        </div>
      )}

      {/* Suggestions */}
      {loading ? (
        <div className="space-y-3">
          {[0, 1].map(i => (
            <div key={i} className="animate-pulse bg-bg-panel border border-[var(--color-border-default)] chamfer-8 p-4 space-y-2">
              <div className="h-3 w-24 bg-bg-overlay rounded" />
              <div className="h-3 w-full bg-bg-overlay rounded" />
              <div className="h-3 w-3/4 bg-bg-overlay rounded" />
            </div>
          ))}
        </div>
      ) : suggestions.length === 0 ? (
        <div className="text-center py-6 text-label text-text-muted">
          No AI insights for this screen right now.
        </div>
      ) : (
        suggestions.map((suggestion, i) => (
          <AIExplanationCard key={i} {...suggestion} />
        ))
      )}
    </div>
  );
}

// ── Simple Mode AI Summary ───────────────────────────────────────
// "Tell me simply" card that works identically across all domains.

export interface SimpleModeSummaryProps {
  readonly screenName: string;
  readonly whatThisDoes: string;
  readonly whatIsWrong?: string;
  readonly whatMatters: string;
  readonly whatToClickNext: string;
  readonly requiresReview?: boolean;
  readonly domain?: SystemDomain;
  readonly className?: string;
}

export function SimpleModeSummary({
  screenName,
  whatThisDoes,
  whatIsWrong,
  whatMatters,
  whatToClickNext,
  requiresReview = false,
  domain,
  className,
}: SimpleModeSummaryProps) {
  return (
    <div
      className={cn(
        'bg-bg-panel border border-[var(--color-border-default)] chamfer-8 p-5',
        className
      )}
    >
      <div className="flex items-center gap-2 mb-4">
        <svg className="w-5 h-5 text-orange" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2} aria-hidden>
          <path strokeLinecap="round" strokeLinejoin="round" d="M4 6h16M4 12h8m-8 6h16" />
        </svg>
        <h3 className="text-h3 font-sans font-bold text-text-primary">
          {screenName}
        </h3>
        {domain && (
          <span className="text-micro font-label uppercase tracking-wider text-text-muted ml-auto">
            {DOMAIN_LABEL[domain]}
          </span>
        )}
      </div>

      <div className="space-y-4">
        <div>
          <p className="text-micro font-label uppercase tracking-wider text-text-disabled mb-1">
            What this area does
          </p>
          <p className="text-body text-text-primary leading-relaxed">{whatThisDoes}</p>
        </div>

        {whatIsWrong && (
          <div className="p-3 bg-red-ghost border border-red/20 chamfer-4">
            <p className="text-micro font-label uppercase tracking-wider text-red mb-1">
              What is wrong here
            </p>
            <p className="text-body text-text-primary leading-relaxed">{whatIsWrong}</p>
          </div>
        )}

        <div>
          <p className="text-micro font-label uppercase tracking-wider text-text-disabled mb-1">
            What matters most
          </p>
          <p className="text-body text-text-secondary leading-relaxed">{whatMatters}</p>
        </div>

        <div className="p-3 bg-orange-ghost border border-orange/20 chamfer-4">
          <p className="text-micro font-label uppercase tracking-wider text-orange mb-1">
            What to click next
          </p>
          <p className="text-body text-text-primary font-medium leading-relaxed">→ {whatToClickNext}</p>
        </div>

        {requiresReview && (
          <div className="flex items-center gap-2 p-3 bg-[rgba(129,140,248,0.08)] border border-[rgba(129,140,248,0.2)] chamfer-4">
            <svg className="w-4 h-4 text-[#818cf8] flex-shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2} aria-hidden>
              <path strokeLinecap="round" strokeLinejoin="round" d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
              <path strokeLinecap="round" strokeLinejoin="round" d="M2.458 12C3.732 7.943 7.523 5 12 5c4.478 0 8.268 2.943 9.542 7-1.274 4.057-5.064 7-9.542 7-4.477 0-8.268-2.943-9.542-7z" />
            </svg>
            <p className="text-label text-[#818cf8]">
              A human must review this before you proceed.
            </p>
          </div>
        )}
      </div>
    </div>
  );
}
