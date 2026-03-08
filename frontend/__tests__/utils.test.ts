/**
 * Utility Functions — Unit Tests
 */
import { describe, it, expect } from 'vitest';
import { cn } from '@/lib/utils';

describe('cn (className merger)', () => {
  it('merges simple class names', () => {
    expect(cn('foo', 'bar')).toBe('foo bar');
  });

  it('handles conditional classes', () => {
    const result = cn('base', true && 'active', false && 'hidden');
    expect(result).toContain('base');
    expect(result).toContain('active');
    expect(result).not.toContain('hidden');
  });

  it('resolves Tailwind conflicts (last wins)', () => {
    const result = cn('px-4', 'px-6');
    expect(result).toBe('px-6');
  });

  it('handles undefined and null gracefully', () => {
    const result = cn('base', undefined, null);
    expect(result).toBe('base');
  });

  it('returns empty string for no args', () => {
    expect(cn()).toBe('');
  });
});
