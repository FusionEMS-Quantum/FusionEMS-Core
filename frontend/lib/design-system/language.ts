/**
 * FusionEMS Quantum — Global Status Language
 * 
 * Canonical copy patterns, action grammar, and status terminology.
 * Every user-facing status term, severity label, and action prompt
 * must come from this file to ensure consistent product language.
 */

import type { SeverityLevel, StatusVariant, SystemDomain } from './tokens';

// ── Copy Pattern ──────────────────────────────────────────────────
/** Standard explanation structure for any critical surface */
export interface ActionExplanation {
  /** What happened (past tense, factual) */
  readonly what: string;
  /** Why it matters (risk/impact framing) */
  readonly why: string;
  /** What to do next (imperative, clear) */
  readonly next: string;
}

// ── Status Labels ─────────────────────────────────────────────────
export const STATUS_DISPLAY: Record<StatusVariant, string> = {
  active:   'Active',
  warning:  'Warning',
  critical: 'Critical',
  info:     'Info',
  neutral:  'Inactive',
  review:   'In Review',
  override: 'Override',
} as const;

// ── Action Verbs ──────────────────────────────────────────────────
export const ACTION_VERBS = {
  review:   'Review',
  approve:  'Approve',
  deny:     'Deny',
  override: 'Override',
  retry:    'Retry',
  dismiss:  'Dismiss',
  escalate: 'Escalate',
  resolve:  'Resolve',
  cancel:   'Cancel',
  submit:   'Submit',
  assign:   'Assign',
  archive:  'Archive',
} as const;

// ── Readiness Language ────────────────────────────────────────────
export const READINESS_STATES = {
  READY:            { label: 'Ready',            color: 'active'   as StatusVariant },
  LIMITED:          { label: 'Limited',           color: 'warning'  as StatusVariant },
  NOT_READY:        { label: 'Not Ready',         color: 'critical' as StatusVariant },
  MAINTENANCE_HOLD: { label: 'Maintenance Hold',  color: 'info'     as StatusVariant },
  UNKNOWN:          { label: 'Unknown',           color: 'neutral'  as StatusVariant },
} as const;

// ── Health Score Copy ─────────────────────────────────────────────
export function healthScoreCopy(score: number): ActionExplanation {
  if (score >= 90) {
    return {
      what: `Health score is ${score}% — all systems operational.`,
      why: 'No action required right now.',
      next: 'Continue monitoring.',
    };
  }
  if (score >= 75) {
    return {
      what: `Health score is ${score}% — minor issues detected.`,
      why: 'Some items need attention before they escalate.',
      next: 'Review flagged items in the next 24 hours.',
    };
  }
  if (score >= 60) {
    return {
      what: `Health score is ${score}% — attention required.`,
      why: 'Multiple issues may affect operations or compliance.',
      next: 'Prioritize the highest-severity items now.',
    };
  }
  if (score >= 40) {
    return {
      what: `Health score is ${score}% — at risk.`,
      why: 'Critical gaps exist that could impact operations.',
      next: 'Address blocking issues immediately.',
    };
  }
  return {
    what: `Health score is ${score}% — critical condition.`,
    why: 'Significant operational or compliance failures detected.',
    next: 'Escalate and take corrective action now.',
  };
}

// ── Domain Context Prefixes ───────────────────────────────────────
export const DOMAIN_CONTEXT: Record<SystemDomain, string> = {
  billing:    'Revenue',
  fire:       'Fire Operations',
  hems:       'HEMS Mission',
  fleet:      'Fleet',
  compliance: 'Compliance',
  cad:        'Dispatch',
  clinical:   'Clinical',
  ops:        'Operations',
  support:    'Support',
  scheduling: 'Scheduling',
  ai:         'AI Analytics',
} as const;

// ── Severity Action Guidance ──────────────────────────────────────
export const SEVERITY_GUIDANCE: Record<SeverityLevel, string> = {
  BLOCKING:      'Requires immediate action. Do not proceed until resolved.',
  HIGH:          'Address within the current shift. May impact operations.',
  MEDIUM:        'Review and address within 24 hours.',
  LOW:           'Schedule for review at next opportunity.',
  INFORMATIONAL: 'For awareness only. No action required.',
} as const;

// ── Empty State Messages ──────────────────────────────────────────
export const EMPTY_STATE = {
  NO_DATA:      { title: 'No Data Yet',          description: 'This area will populate as data becomes available.' },
  NO_RESULTS:   { title: 'No Results Found',      description: 'Try adjusting your filters or search terms.' },
  NO_INCIDENTS: { title: 'No Active Incidents',    description: 'All clear. No incidents require attention.' },
  NO_ALERTS:    { title: 'No Alerts',             description: 'Everything is operating within normal parameters.' },
  NO_ACTIONS:   { title: 'No Actions Required',    description: 'You are up to date. Check back later.' },
  LOADING_FAIL: { title: 'Unable to Load',         description: 'Something went wrong. Try refreshing or check your connection.' },
} as const;

// ── Confirmation Copy ─────────────────────────────────────────────
export const CONFIRMATION = {
  DELETE:        'This action cannot be undone. Are you sure you want to delete this item?',
  OVERRIDE:      'You are overriding an automated decision. This will be logged for audit.',
  SUBMIT_FINAL:  'Once submitted, this record cannot be edited. Please review before confirming.',
  DESTRUCTIVE:   'This is a destructive action. Confirm to proceed.',
} as const;

// ── Success Copy ──────────────────────────────────────────────────
export const SUCCESS = {
  SAVED:        'Changes saved successfully.',
  SUBMITTED:    'Submitted successfully.',
  APPROVED:     'Approved successfully.',
  DELETED:      'Deleted successfully.',
  OVERRIDDEN:   'Override applied. Logged for audit.',
  RETRY_OK:     'Retry succeeded.',
} as const;
