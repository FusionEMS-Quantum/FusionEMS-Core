'use client';

import { type ReactNode, useState, useCallback, createContext, useContext } from 'react';
import { cn } from '@/lib/utils';

// ══════════════════════════════════════════════════════════════════
// PRODUCT POLISH COMPONENTS
// Standardized empty states, confirmations, toast, loading,
// destructive action guards, and retry flows.
// ══════════════════════════════════════════════════════════════════

// ── Confirmation Dialog ──────────────────────────────────────────

export interface ConfirmDialogProps {
  readonly isOpen: boolean;
  readonly title: string;
  readonly message: string;
  readonly confirmLabel?: string;
  readonly cancelLabel?: string;
  readonly destructive?: boolean;
  readonly onConfirm: () => void;
  readonly onCancel: () => void;
  readonly loading?: boolean;
}

export function ConfirmDialog({
  isOpen,
  title,
  message,
  confirmLabel = 'Confirm',
  cancelLabel = 'Cancel',
  destructive = false,
  onConfirm,
  onCancel,
  loading = false,
}: ConfirmDialogProps) {
  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
      {/* Backdrop */}
      <div className="absolute inset-0 bg-black/70" onClick={onCancel} aria-hidden />

      {/* Dialog */}
      <div
        className="relative bg-[#0A0A0B] border border-[var(--color-border-default)] chamfer-12 
                   w-full max-w-md p-6 shadow-elevation-3 animate-fade-in"
        role="alertdialog"
        aria-modal
        aria-labelledby="confirm-title"
        aria-describedby="confirm-desc"
      >
        {/* Icon */}
        <div className={cn(
          'w-10 h-10  flex items-center justify-center mb-4',
          destructive ? 'bg-red-ghost' : 'bg-[rgba(255,77,0,0.12)]'
        )}>
          {destructive ? (
            <svg className="w-5 h-5 text-red" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2} aria-hidden>
              <path strokeLinecap="round" strokeLinejoin="round" d="M12 9v2m0 4h.01M5.07 19h13.86c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
            </svg>
          ) : (
            <svg className="w-5 h-5 text-[#FF4D00]" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2} aria-hidden>
              <path strokeLinecap="round" strokeLinejoin="round" d="M8.228 9c.549-1.165 2.03-2 3.772-2 2.21 0 4 1.343 4 3 0 1.4-1.278 2.575-3.006 2.907-.542.104-.994.54-.994 1.093m0 3h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
            </svg>
          )}
        </div>

        <h2 id="confirm-title" className="text-h3 font-sans font-bold text-zinc-100 mb-2">
          {title}
        </h2>
        <p id="confirm-desc" className="text-body text-zinc-500 mb-6">
          {message}
        </p>

        <div className="flex items-center justify-end gap-3">
          <button
            onClick={onCancel}
            disabled={loading}
            className="px-4 py-2 text-label font-label uppercase tracking-wider text-zinc-500
                       border border-[var(--color-border-default)] chamfer-4
                       hover:bg-bg-overlay transition-colors duration-fast
                       disabled:opacity-50"
            type="button"
          >
            {cancelLabel}
          </button>
          <button
            onClick={onConfirm}
            disabled={loading}
            className={cn(
              'px-4 py-2 text-label font-label uppercase tracking-wider chamfer-4',
              'transition-colors duration-fast disabled:opacity-50',
              destructive
                ? 'bg-red text-white hover:bg-red-bright'
                : 'bg-[#FF4D00] text-black hover:bg-[#E64500]'
            )}
            type="button"
          >
            {loading && (
              <svg className="animate-spin -ml-1 mr-2 h-4 w-4 inline" fill="none" viewBox="0 0 24 24" aria-hidden>
                <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
              </svg>
            )}
            {confirmLabel}
          </button>
        </div>
      </div>
    </div>
  );
}

// ── Toast System ─────────────────────────────────────────────────

export type ToastVariant = 'success' | 'error' | 'warning' | 'info';

export interface Toast {
  readonly id: string;
  readonly variant: ToastVariant;
  readonly message: string;
  readonly duration?: number;
}

interface ToastContextValue {
  readonly toasts: readonly Toast[];
  readonly addToast: (_variant: ToastVariant, _message: string, _duration?: number) => void;
  readonly removeToast: (_id: string) => void;
}

const ToastContext = createContext<ToastContextValue | null>(null);

export function useToast() {
  const ctx = useContext(ToastContext);
  if (!ctx) {
    // Graceful fallback for components outside provider
    return {
      toasts: [] as readonly Toast[],
      addToast: (_v: ToastVariant, _m: string) => {},
      removeToast: (_id: string) => {},
      success: (_msg: string) => {},
      error: (_msg: string) => {},
      warning: (_msg: string) => {},
      info: (_msg: string) => {},
    };
  }
  return {
    ...ctx,
    success: (msg: string) => ctx.addToast('success', msg),
    error: (msg: string) => ctx.addToast('error', msg),
    warning: (msg: string) => ctx.addToast('warning', msg),
    info: (msg: string) => ctx.addToast('info', msg),
  };
}

export function ToastProvider({ children }: { readonly children: ReactNode }) {
  const [toasts, setToasts] = useState<Toast[]>([]);

  const addToast = useCallback((variant: ToastVariant, message: string, duration = 4000) => {
    const id = `toast-${Date.now()}-${Math.random().toString(36).slice(2, 6)}`;
    setToasts(prev => [...prev, { id, variant, message, duration }]);
    if (duration > 0) {
      setTimeout(() => {
        setToasts(prev => prev.filter(t => t.id !== id));
      }, duration);
    }
  }, []);

  const removeToast = useCallback((id: string) => {
    setToasts(prev => prev.filter(t => t.id !== id));
  }, []);

  return (
    <ToastContext.Provider value={{ toasts, addToast, removeToast }}>
      {children}
      <ToastContainer toasts={toasts} onDismiss={removeToast} />
    </ToastContext.Provider>
  );
}

function ToastContainer({
  toasts,
  onDismiss,
}: {
  readonly toasts: readonly Toast[];
  readonly onDismiss: (_id: string) => void;
}) {
  if (toasts.length === 0) return null;

  return (
    <div
      className="fixed bottom-4 right-4 z-[60] flex flex-col gap-2 max-w-sm w-full pointer-events-none"
      aria-live="polite"
    >
      {toasts.map((toast) => (
        <ToastItem key={toast.id} toast={toast} onDismiss={onDismiss} />
      ))}
    </div>
  );
}

const TOAST_STYLES: Record<ToastVariant, string> = {
  success: 'border-l-4 border-[var(--color-status-active)] bg-[rgba(34,197,94,0.08)]',
  error:   'border-l-4 border-red bg-red-ghost',
  warning: 'border-l-4 border-[var(--color-status-warning)] bg-[rgba(245,158,11,0.08)]',
  info:    'border-l-4 border-[var(--color-status-info)] bg-[rgba(56,189,248,0.08)]',
};

const TOAST_ICONS: Record<ToastVariant, string> = {
  success: '✓',
  error:   '✕',
  warning: '⚠',
  info:    'ℹ',
};

function ToastItem({
  toast,
  onDismiss,
}: {
  readonly toast: Toast;
  readonly onDismiss: (_id: string) => void;
}) {
  return (
    <div
      className={cn(
        'pointer-events-auto chamfer-4 p-3 flex items-start gap-3 shadow-elevation-3 animate-fade-in',
        TOAST_STYLES[toast.variant]
      )}
      role="alert"
    >
      <span className="text-body flex-shrink-0 mt-0.5" aria-hidden>
        {TOAST_ICONS[toast.variant]}
      </span>
      <p className="text-body text-zinc-100 flex-1">{toast.message}</p>
      <button
        onClick={() => onDismiss(toast.id)}
        className="text-zinc-500 hover:text-zinc-100 transition-colors duration-fast flex-shrink-0"
        type="button"
        aria-label="Dismiss"
      >
        <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
          <path strokeLinecap="round" strokeLinejoin="round" d="M6 18L18 6M6 6l12 12" />
        </svg>
      </button>
    </div>
  );
}

// ── Partial Data Warning ─────────────────────────────────────────

export interface PartialDataWarningProps {
  readonly message?: string;
  readonly className?: string;
}

export function PartialDataWarning({
  message = 'Some data may be incomplete or still loading. Results shown are partial.',
  className,
}: PartialDataWarningProps) {
  return (
    <div
      className={cn(
        'flex items-center gap-2 px-3 py-2 bg-[rgba(245,158,11,0.08)] border border-[rgba(245,158,11,0.2)] chamfer-4 text-label text-yellow-400',
        className
      )}
      role="status"
    >
      <svg className="w-4 h-4 flex-shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2} aria-hidden>
        <path strokeLinecap="round" strokeLinejoin="round" d="M12 9v2m0 4h.01M5.07 19h13.86c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
      </svg>
      {message}
    </div>
  );
}

// ── Degraded Mode Warning ────────────────────────────────────────

export interface DegradedModeWarningProps {
  readonly service?: string;
  readonly message?: string;
  readonly className?: string;
}

export function DegradedModeWarning({
  service,
  message,
  className,
}: DegradedModeWarningProps) {
  const displayMessage = message ?? `${service ?? 'A service'} is operating in degraded mode. Some features may be unavailable.`;

  return (
    <div
      className={cn(
        'flex items-center gap-2 px-3 py-2 bg-[rgba(255,77,0,0.12)] border border-orange/20 chamfer-4 text-label text-[#FF4D00]',
        className
      )}
      role="alert"
    >
      <svg className="w-4 h-4 flex-shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2} aria-hidden>
        <path strokeLinecap="round" strokeLinejoin="round" d="M13 10V3L4 14h7v7l9-11h-7z" />
      </svg>
      {displayMessage}
    </div>
  );
}

// ── Retry Affordance ─────────────────────────────────────────────

export interface RetryAffordanceProps {
  readonly message?: string;
  readonly onRetry: () => void;
  readonly retrying?: boolean;
  readonly className?: string;
}

export function RetryAffordance({
  message = 'This action failed. Would you like to try again?',
  onRetry,
  retrying = false,
  className,
}: RetryAffordanceProps) {
  return (
    <div
      className={cn(
        'flex items-center justify-between gap-3 px-3 py-2 bg-red-ghost border border-red/20 chamfer-4',
        className
      )}
      role="alert"
    >
      <span className="text-body text-zinc-100">{message}</span>
      <button
        onClick={onRetry}
        disabled={retrying}
        className="flex-shrink-0 px-3 py-1.5 text-label font-label uppercase tracking-wider
                   bg-red text-white chamfer-4 hover:bg-red-bright transition-colors duration-fast
                   disabled:opacity-50"
        type="button"
      >
        {retrying ? (
          <svg className="animate-spin h-4 w-4" fill="none" viewBox="0 0 24 24" aria-hidden>
            <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
            <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
          </svg>
        ) : (
          'Retry'
        )}
      </button>
    </div>
  );
}

// ── Success Confirmation ─────────────────────────────────────────

export interface SuccessConfirmationProps {
  readonly message: string;
  readonly className?: string;
}

export function SuccessConfirmation({ message, className }: SuccessConfirmationProps) {
  return (
    <div
      className={cn(
        'flex items-center gap-2 px-3 py-2 bg-[rgba(34,197,94,0.08)] border border-[rgba(34,197,94,0.2)] chamfer-4 text-label text-status-active',
        className
      )}
      role="status"
    >
      <svg className="w-4 h-4 flex-shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2} aria-hidden>
        <path strokeLinecap="round" strokeLinejoin="round" d="M5 13l4 4L19 7" />
      </svg>
      {message}
    </div>
  );
}

// ── Loading Overlay ──────────────────────────────────────────────

export interface LoadingOverlayProps {
  readonly message?: string;
  readonly className?: string;
}

export function LoadingOverlay({ message = 'Loading...', className }: LoadingOverlayProps) {
  return (
    <div className={cn('flex flex-col items-center justify-center py-16', className)}>
      <div className="relative w-10 h-10 mb-4">
        <div className="absolute inset-0 border-2 border-[var(--color-border-subtle)] " />
        <div className="absolute inset-0 border-2 border-transparent border-t-orange  animate-spin" />
      </div>
      <p className="text-body text-zinc-500">{message}</p>
    </div>
  );
}
