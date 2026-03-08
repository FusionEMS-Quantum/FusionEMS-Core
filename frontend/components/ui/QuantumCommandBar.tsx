'use client';

import * as React from 'react';
import { clsx } from 'clsx';

export interface CommandBarAction {
  label: string;
  icon?: React.ReactNode;
  onClick: () => void;
  variant?: 'primary' | 'danger' | 'ghost';
}

export interface QuantumCommandBarProps {
  selectedCount?: number;
  actions: CommandBarAction[];
  onClear?: () => void;
  className?: string;
}

export function QuantumCommandBar({
  selectedCount = 0,
  actions,
  onClear,
  className,
}: QuantumCommandBarProps) {
  if (selectedCount === 0 && actions.length === 0) return null;

  return (
    <div
      className={clsx(
        'flex items-center justify-between gap-4',
        'px-4 py-3 bg-[#0A0A0B] border border-border-DEFAULT chamfer-8',
        'animate-fade-in',
        className,
      )}
    >
      <div className="flex items-center gap-3">
        {selectedCount > 0 && (
          <span className="label-caps text-[#FF4D00]">
            {selectedCount} selected
          </span>
        )}
        {onClear && selectedCount > 0 && (
          <button
            onClick={onClear}
            className="text-zinc-500 hover:text-zinc-100 text-label transition-colors duration-fast"
          >
            Clear
          </button>
        )}
      </div>
      <div className="flex items-center gap-2">
        {actions.map((action, i) => {
          const variantClass = {
            primary: 'bg-[#FF4D00] text-black hover:bg-[#E64500]',
            danger: 'bg-red-ghost text-red hover:bg-red-dim hover:text-zinc-100',
            ghost: 'text-zinc-400 hover:text-zinc-100 hover:bg-bg-overlay',
          }[action.variant ?? 'ghost'];

          return (
            <button
              key={i}
              onClick={action.onClick}
              className={clsx(
                'inline-flex items-center gap-2 px-3 h-8',
                'text-label font-label uppercase tracking-[var(--tracking-label)]',
                'chamfer-4 transition-colors duration-fast',
                variantClass,
              )}
            >
              {action.icon}
              {action.label}
            </button>
          );
        })}
      </div>
    </div>
  );
}
