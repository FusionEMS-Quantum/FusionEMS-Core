'use client';

import * as React from 'react';
import { cva, type VariantProps } from 'class-variance-authority';
import { clsx } from 'clsx';

const buttonVariants = cva(
  [
    'relative inline-flex items-center justify-center gap-2',
    'font-label text-label uppercase tracking-[var(--tracking-label)]',
    'transition-all duration-fast ease-out',
    'select-none cursor-pointer',
    'focus-visible:outline-none focus-visible:shadow-focus',
    'disabled:opacity-40 disabled:cursor-not-allowed',
    'active:scale-[0.97]',
  ],
  {
    variants: {
      variant: {
        primary: [
          'quantum-btn-primary',
        ],
        secondary: [
          'quantum-btn',
        ],
        danger: [
          'bg-red text-zinc-100',
          'chamfer-8',
          'hover:bg-red-bright',
          'shadow-elevation-1',
          'hover:shadow-[0_0_12px_2px_var(--color-brand-red-ghost)]',
        ],
        ghost: [
          'bg-transparent text-zinc-400',
          'chamfer-4',
          'hover:bg-[#0A0A0B] hover:text-zinc-100',
        ],
        icon: [
          'bg-transparent text-zinc-400',
          'chamfer-4',
          'hover:bg-[#0A0A0B] hover:text-zinc-100',
          '!px-0',
        ],
      },
      size: {
        sm: [
          'h-[var(--density-button-height)] px-3',
          'text-[var(--text-micro)]',
        ],
        md: [
          'h-[var(--density-button-height)] px-4',
          'text-[var(--text-label)]',
        ],
        lg: [
          'h-10 px-6',
          'text-body',
        ],
        icon: [
          'h-[var(--density-button-height)] w-[var(--density-button-height)]',
        ],
      },
    },
    defaultVariants: {
      variant: 'primary',
      size: 'md',
    },
  }
);

export interface ButtonProps
  extends React.ButtonHTMLAttributes<HTMLButtonElement>,
    VariantProps<typeof buttonVariants> {
  loading?: boolean;
  leftIcon?: React.ReactNode;
  rightIcon?: React.ReactNode;
  asChild?: boolean;
}

export const Button = React.forwardRef<HTMLButtonElement, ButtonProps>(
  (
    {
      className,
      variant,
      size,
      loading = false,
      leftIcon,
      rightIcon,
      disabled,
      children,
      ...props
    },
    ref
  ) => {
    return (
      <button
        ref={ref}
        className={clsx(buttonVariants({ variant, size }), className)}
        disabled={disabled || loading}
        {...props}
      >
        {loading ? (
          <LoadingSpinner />
        ) : leftIcon ? (
          <span className="shrink-0 quantum-btn-icon">{leftIcon}</span>
        ) : null}

        {children && (
          <span className={clsx(variant === 'icon' && 'sr-only')}>
            {children}
          </span>
        )}

        {!loading && rightIcon ? (
          <span className="shrink-0 quantum-btn-icon">{rightIcon}</span>
        ) : null}
      </button>
    );
  }
);

Button.displayName = 'Button';

function LoadingSpinner() {
  return (
    <svg
      className="animate-spin"
      style={{
        width: 'var(--density-icon-size)',
        height: 'var(--density-icon-size)',
      }}
      viewBox="0 0 24 24"
      fill="none"
      aria-hidden="true"
    >
      <circle
        cx="12"
        cy="12"
        r="10"
        stroke="currentColor"
        strokeWidth="3"
        strokeLinecap="round"
        strokeDasharray="40"
        strokeDashoffset="10"
        opacity="0.3"
      />
      <path
        d="M12 2a10 10 0 0 1 10 10"
        stroke="currentColor"
        strokeWidth="3"
        strokeLinecap="round"
      />
    </svg>
  );
}

export { buttonVariants };
