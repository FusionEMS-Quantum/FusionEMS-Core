import * as React from 'react';
import { cva, type VariantProps } from 'class-variance-authority';
import { cn } from '@/lib/utils';

const badgeVariants = cva(
    'quantum-badge transition-colors focus:outline-none focus:ring-2 focus:ring-ring focus:ring-offset-2',
    {
        variants: {
            variant: {
                default: 'border-[var(--color-brand-orange)]/30 bg-[var(--color-brand-orange-ghost)] text-[var(--color-brand-orange-bright)]',
                secondary: 'border-[var(--color-border-default)] bg-[rgba(255,255,255,0.04)] text-[var(--color-text-secondary)]',
                destructive: 'border-[rgba(201,59,44,0.35)] bg-[var(--color-brand-red-ghost)] text-[var(--color-brand-red)]',
                outline: 'border-[var(--color-border-strong)] bg-transparent text-[var(--color-text-primary)]',
                success: 'border-[rgba(34,197,94,0.3)] bg-[rgba(34,197,94,0.12)] text-[var(--color-status-active)]',
                warning: 'border-[rgba(245,158,11,0.3)] bg-[rgba(245,158,11,0.12)] text-[var(--color-status-warning)]',
            },
        },
        defaultVariants: {
            variant: 'default',
        },
    }
);

export interface BadgeProps
    extends React.HTMLAttributes<HTMLDivElement>,
    VariantProps<typeof badgeVariants> { }

function Badge({ className, variant, ...props }: BadgeProps) {
    return <div className={cn(badgeVariants({ variant }), className)} {...props} />;
}

export { Badge, badgeVariants };
