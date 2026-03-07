/**
 * FusionEMS Quantum — Design System Tokens (TypeScript)
 * 
 * Canonical constants for the Quantum design system.
 * Maps CSS custom properties to typed TS values for runtime use.
 * CSS tokens in styles/tokens.css remain the visual source of truth;
 * these constants drive logic, mapping, and component prop validation.
 */

// ── Severity ──────────────────────────────────────────────────────
export const SEVERITY_LEVELS = ['BLOCKING', 'HIGH', 'MEDIUM', 'LOW', 'INFORMATIONAL'] as const;
export type SeverityLevel = (typeof SEVERITY_LEVELS)[number];

export const SEVERITY_COLOR_MAP: Record<SeverityLevel, string> = {
  BLOCKING:      'var(--color-brand-red)',
  HIGH:          'var(--q-orange)',
  MEDIUM:        'var(--q-yellow)',
  LOW:           'var(--color-status-info)',
  INFORMATIONAL: 'var(--color-text-muted)',
} as const;

export const SEVERITY_BG_MAP: Record<SeverityLevel, string> = {
  BLOCKING:      'var(--color-brand-red-ghost)',
  HIGH:          'var(--color-brand-orange-ghost)',
  MEDIUM:        'rgba(245, 158, 11, 0.12)',
  LOW:           'rgba(56, 189, 248, 0.10)',
  INFORMATIONAL: 'rgba(156, 163, 175, 0.10)',
} as const;

export const SEVERITY_LABEL: Record<SeverityLevel, string> = {
  BLOCKING:      'Blocking',
  HIGH:          'High Risk',
  MEDIUM:        'Needs Attention',
  LOW:           'Low Priority',
  INFORMATIONAL: 'Informational',
} as const;

// ── Status ────────────────────────────────────────────────────────
export const STATUS_VARIANTS = ['active', 'warning', 'critical', 'info', 'neutral', 'review', 'override'] as const;
export type StatusVariant = (typeof STATUS_VARIANTS)[number];

export const STATUS_COLOR_MAP: Record<StatusVariant, string> = {
  active:   'var(--color-status-active)',
  warning:  'var(--color-status-warning)',
  critical: 'var(--color-status-critical)',
  info:     'var(--color-status-info)',
  neutral:  'var(--color-status-neutral)',
  review:   '#818cf8',
  override: 'var(--q-orange)',
} as const;

// ── Health Score Bands ────────────────────────────────────────────
export interface HealthBand {
  readonly min: number;
  readonly max: number;
  readonly label: string;
  readonly colorVar: string;
  readonly severity: SeverityLevel;
}

export const HEALTH_BANDS: readonly HealthBand[] = [
  { min: 0,  max: 39,  label: 'Critical',       colorVar: 'var(--color-brand-red)',       severity: 'BLOCKING' },
  { min: 40, max: 59,  label: 'At Risk',         colorVar: 'var(--q-orange)',              severity: 'HIGH' },
  { min: 60, max: 74,  label: 'Needs Attention',  colorVar: 'var(--q-yellow)',              severity: 'MEDIUM' },
  { min: 75, max: 89,  label: 'Good',            colorVar: 'var(--color-status-info)',     severity: 'LOW' },
  { min: 90, max: 100, label: 'Excellent',        colorVar: 'var(--color-status-active)',   severity: 'INFORMATIONAL' },
] as const;

export function getHealthBand(score: number): HealthBand {
  const clamped = Math.max(0, Math.min(100, score));
  return HEALTH_BANDS.find(b => clamped >= b.min && clamped <= b.max) ?? HEALTH_BANDS[0];
}

// ── Domain System Colors ──────────────────────────────────────────
export const SYSTEM_DOMAINS = [
  'billing', 'fire', 'hems', 'fleet', 'compliance', 'cad',
  'clinical', 'ops', 'support', 'scheduling', 'ai',
] as const;
export type SystemDomain = (typeof SYSTEM_DOMAINS)[number];

export const DOMAIN_COLOR_MAP: Record<SystemDomain, string> = {
  billing:    'var(--color-system-billing)',
  fire:       'var(--color-system-fire)',
  hems:       'var(--color-system-hems)',
  fleet:      'var(--color-system-fleet)',
  compliance: 'var(--color-system-compliance)',
  cad:        'var(--color-system-cad)',
  clinical:   '#ec4899',
  ops:        'var(--q-orange)',
  support:    '#a78bfa',
  scheduling: '#2dd4bf',
  ai:         '#818cf8',
} as const;

export const DOMAIN_LABEL: Record<SystemDomain, string> = {
  billing:    'Billing',
  fire:       'Fire',
  hems:       'HEMS',
  fleet:      'Fleet',
  compliance: 'Compliance',
  cad:        'CAD',
  clinical:   'Clinical',
  ops:        'Operations',
  support:    'Support',
  scheduling: 'Scheduling',
  ai:         'AI / Analytics',
} as const;

// ── Spacing Helpers ───────────────────────────────────────────────
export const SPACING = {
  0: '0px',  1: '4px',  2: '8px',  3: '12px',
  4: '16px', 5: '20px', 6: '24px', 7: '32px',
  8: '40px', 9: '48px', 10: '64px', 11: '80px', 12: '96px',
} as const;

// ── Breakpoints ───────────────────────────────────────────────────
export const BREAKPOINTS = {
  sm:  640,
  md:  768,
  lg:  1024,
  xl:  1280,
  '2xl': 1536,
  '3xl': 1920,   // widescreen
  '4xl': 2560,   // ultra-wide / dual-monitor
} as const;

// ── Density Modes ─────────────────────────────────────────────────
export const DENSITY_MODES = ['default', 'dispatch', 'compact', 'comfortable'] as const;
export type DensityMode = (typeof DENSITY_MODES)[number];

// ── Animation Durations ───────────────────────────────────────────
export const MOTION = {
  instant: 80,
  fast:    150,
  base:    220,
  slow:    350,
} as const;
