import type { SeverityLevel } from './tokens';

const SEVERITY_ALIAS_MAP: Record<string, SeverityLevel> = {
  BLOCKING: 'BLOCKING',
  CRITICAL: 'BLOCKING',
  HIGH: 'HIGH',
  ERROR: 'HIGH',
  MEDIUM: 'MEDIUM',
  WARNING: 'MEDIUM',
  LOW: 'LOW',
  INFORMATIONAL: 'INFORMATIONAL',
  INFO: 'INFORMATIONAL',
};

/**
 * Normalizes backend and legacy severity labels to canonical design-system severity.
 */
export function normalizeSeverity(raw: string | null | undefined): SeverityLevel {
  if (!raw) {
    return 'INFORMATIONAL';
  }

  const key = raw.trim().toUpperCase();
  return SEVERITY_ALIAS_MAP[key] ?? 'INFORMATIONAL';
}
