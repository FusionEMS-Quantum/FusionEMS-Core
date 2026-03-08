'use client';

import { cn } from '@/lib/utils';

// ── Types ────────────────────────────────────────────────────────────────────

export interface AIExplanation {
  title: string;
  severity: 'BLOCKING' | 'HIGH' | 'MEDIUM' | 'LOW' | 'INFORMATIONAL' | 'CRITICAL' | 'INFO';
  source: 'AI_ENGINE' | 'GOVERNANCE' | 'HUMAN_OVERRIDE';
  what_is_wrong: string;
  why_it_matters: string;
  what_you_should_do: string;
  domain_context: string;
  human_review: 'REQUIRED' | 'RECOMMENDED' | 'OPTIONAL';
  confidence: 'HIGH' | 'MEDIUM' | 'LOW';
  simple_mode_summary?: string;
}

export interface AIExplanationCardProps {
  readonly explanation: AIExplanation;
  readonly compact?: boolean;
  readonly className?: string;
  readonly onAction?: () => void;
  readonly actionLabel?: string;
}

// ── Helpers ──────────────────────────────────────────────────────────────────

function normalizeSeverity(s: string): 'BLOCKING' | 'HIGH' | 'MEDIUM' | 'LOW' | 'INFORMATIONAL' {
  switch (s) {
    case 'CRITICAL':
      return 'BLOCKING';
    case 'INFO':
      return 'INFORMATIONAL';
    case 'BLOCKING':
    case 'HIGH':
    case 'MEDIUM':
    case 'LOW':
    case 'INFORMATIONAL':
      return s;
    default:
      return 'INFORMATIONAL';
  }
}

function severityStyle(s: string): { bg: string; border: string; text: string; label: string } {
  switch (normalizeSeverity(s)) {
    case 'BLOCKING':
      return { bg: 'rgba(255,45,45,0.08)', border: 'rgba(255,45,45,0.35)', text: 'var(--color-brand-red)', label: 'BLOCKING' };
    case 'HIGH':
      return { bg: 'rgba(255,107,26,0.08)', border: 'rgba(255,107,26,0.35)', text: '#FF4D00', label: 'HIGH' };
    case 'MEDIUM':
      return { bg: 'rgba(245,158,11,0.08)', border: 'rgba(245,158,11,0.25)', text: 'var(--color-status-warning)', label: 'MEDIUM' };
    case 'LOW':
      return { bg: 'rgba(34,197,94,0.08)', border: 'rgba(34,197,94,0.25)', text: 'var(--color-status-active)', label: 'LOW' };
    default:
      return { bg: 'rgba(156,163,175,0.10)', border: 'rgba(156,163,175,0.25)', text: 'var(--color-text-muted)', label: 'INFORMATIONAL' };
  }
}

function confidenceDot(c: string): string {
  switch (c) {
    case 'HIGH': return 'var(--color-status-active)';
    case 'MEDIUM': return 'var(--color-status-warning)';
    default: return 'var(--color-brand-red)';
  }
}

function reviewBadge(h: string): { color: string; label: string } {
  switch (h) {
    case 'REQUIRED':
      return { color: 'var(--color-brand-red)', label: 'REVIEW REQUIRED' };
    case 'RECOMMENDED':
      return { color: 'var(--color-status-warning)', label: 'REVIEW RECOMMENDED' };
    default:
      return { color: 'var(--color-status-active)', label: 'REVIEW OPTIONAL' };
  }
}

// ── Component ────────────────────────────────────────────────────────────────

export function AIExplanationCard({ explanation, compact, className, onAction, actionLabel }: AIExplanationCardProps) {
  const sev = severityStyle(explanation.severity);
  const rev = reviewBadge(explanation.human_review);

  return (
    <div
      className={cn('border p-4 space-y-3', className)}
      style={{
        backgroundColor: sev.bg,
        borderColor: sev.border,
        clipPath: 'polygon(0 0, calc(100% - 10px) 0, 100% 10px, 100% 100%, 0 100%)',
      }}
    >
      {/* Header row */}
      <div className="flex items-start justify-between gap-3">
        <div className="flex items-center gap-2 min-w-0">
          <span
            className="text-[10px] font-bold uppercase tracking-widest px-2 py-0.5 chamfer-4 shrink-0"
            style={{ color: sev.text, background: `color-mix(in srgb, ${sev.text} 15%, transparent)` }}
          >
            {sev.label}
          </span>
          <h3 className="text-sm font-bold text-zinc-100 truncate">{explanation.title}</h3>
        </div>
        <div className="flex items-center gap-2 shrink-0">
          <span className="w-1.5 h-1.5 " style={{ background: confidenceDot(explanation.confidence) }} />
          <span className="text-[10px] uppercase tracking-wider text-zinc-500">{explanation.confidence}</span>
        </div>
      </div>

      {/* Source + Review badges */}
      <div className="flex items-center gap-2 flex-wrap">
        <span className="text-[10px] uppercase tracking-widest text-zinc-500 px-2 py-0.5 border border-border-DEFAULT chamfer-4">
          {explanation.source.replace(/_/g, ' ')}
        </span>
        <span
          className="text-[10px] uppercase tracking-widest px-2 py-0.5 chamfer-4"
          style={{ color: rev.color, background: `color-mix(in srgb, ${rev.color} 12%, transparent)`, border: `1px solid color-mix(in srgb, ${rev.color} 30%, transparent)` }}
        >
          {rev.label}
        </span>
      </div>

      {/* Body: the 3-part explanation */}
      {!compact && (
        <div className="space-y-2.5">
          <ExplanationSection icon="⚠" title="What Happened" body={explanation.what_is_wrong} />
          <ExplanationSection icon="→" title="Why It Matters" body={explanation.why_it_matters} />
          <ExplanationSection icon="✓" title="Do This Next" body={explanation.what_you_should_do} />
        </div>
      )}

      {compact && explanation.simple_mode_summary && (
        <p className="text-xs text-zinc-400 leading-relaxed">{explanation.simple_mode_summary}</p>
      )}

      {/* Domain context */}
      {!compact && (
        <div className="text-[10px] text-zinc-500 border-t border-[rgba(255,255,255,0.05)] pt-2 mt-2">
          <span className="uppercase tracking-widest font-semibold">Context:</span> {explanation.domain_context}
        </div>
      )}

      {/* Optional action button */}
      {onAction && (
        <button
          onClick={onAction}
          className="text-[10px] uppercase tracking-widest font-bold px-3 py-1.5 border chamfer-4 transition-colors hover:bg-[rgba(255,107,26,0.12)]"
          style={{ color: '#FF4D00', borderColor: 'rgba(255,107,26,0.35)' }}
        >
          {actionLabel || 'Take Action'}
        </button>
      )}
    </div>
  );
}

function ExplanationSection({ icon, title, body }: { icon: string; title: string; body: string }) {
  return (
    <div className="flex gap-2">
      <span className="text-xs shrink-0 mt-0.5" aria-hidden>{icon}</span>
      <div>
        <div className="text-[10px] font-bold uppercase tracking-widest text-zinc-500 mb-0.5">{title}</div>
        <p className="text-xs text-zinc-400 leading-relaxed">{body}</p>
      </div>
    </div>
  );
}
