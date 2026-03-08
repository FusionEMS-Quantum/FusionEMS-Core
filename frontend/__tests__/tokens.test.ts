/**
 * Design System Tokens — Unit Tests
 * Verifies all token constants, health band logic, severity levels,
 * and color system compliance per the directive.
 */
import { describe, it, expect } from 'vitest';
import {
  SEVERITY_LEVELS,
  SEVERITY_COLOR_MAP,
  SEVERITY_BG_MAP,
  SEVERITY_LABEL,
  HEALTH_BANDS,
  getHealthBand,
  STATUS_VARIANTS,
  STATUS_COLOR_MAP,
  SYSTEM_DOMAINS,
} from '@/lib/design-system/tokens';

describe('Severity Levels', () => {
  it('defines exactly 5 severity levels', () => {
    expect(SEVERITY_LEVELS).toHaveLength(5);
  });

  it('has correct severity order: BLOCKING → INFORMATIONAL', () => {
    expect(SEVERITY_LEVELS[0]).toBe('BLOCKING');
    expect(SEVERITY_LEVELS[4]).toBe('INFORMATIONAL');
  });

  it('every severity has a color mapping', () => {
    for (const level of SEVERITY_LEVELS) {
      expect(SEVERITY_COLOR_MAP[level]).toBeDefined();
      expect(SEVERITY_COLOR_MAP[level].length).toBeGreaterThan(0);
    }
  });

  it('every severity has a background mapping', () => {
    for (const level of SEVERITY_LEVELS) {
      expect(SEVERITY_BG_MAP[level]).toBeDefined();
    }
  });

  it('every severity has a human-readable label', () => {
    for (const level of SEVERITY_LEVELS) {
      expect(SEVERITY_LABEL[level]).toBeDefined();
      expect(typeof SEVERITY_LABEL[level]).toBe('string');
    }
  });

  it('BLOCKING maps to red', () => {
    expect(SEVERITY_COLOR_MAP.BLOCKING).toContain('red');
  });
});

describe('Health Score Bands', () => {
  it('covers the full 0-100 range without gaps', () => {
    let covered = 0;
    for (const band of HEALTH_BANDS) {
      covered += band.max - band.min + 1;
    }
    expect(covered).toBe(101); // 0 through 100
  });

  it('bands are in ascending order', () => {
    for (let i = 1; i < HEALTH_BANDS.length; i++) {
      expect(HEALTH_BANDS[i].min).toBeGreaterThan(HEALTH_BANDS[i - 1].max);
    }
  });

  it('getHealthBand returns Critical for score 0', () => {
    const band = getHealthBand(0);
    expect(band.label).toBe('Critical');
    expect(band.severity).toBe('BLOCKING');
  });

  it('getHealthBand returns Excellent for score 100', () => {
    const band = getHealthBand(100);
    expect(band.label).toBe('Excellent');
  });

  it('getHealthBand returns At Risk for score 50', () => {
    const band = getHealthBand(50);
    expect(band.label).toBe('At Risk');
  });

  it('getHealthBand returns Needs Attention for score 70', () => {
    const band = getHealthBand(70);
    expect(band.label).toBe('Needs Attention');
  });

  it('getHealthBand returns Good for score 85', () => {
    const band = getHealthBand(85);
    expect(band.label).toBe('Good');
  });

  it('getHealthBand clamps negative scores to 0', () => {
    const band = getHealthBand(-10);
    expect(band.label).toBe('Critical');
  });

  it('getHealthBand clamps scores above 100', () => {
    const band = getHealthBand(150);
    expect(band.label).toBe('Excellent');
  });

  it('every band has a colorVar', () => {
    for (const band of HEALTH_BANDS) {
      expect(band.colorVar).toBeDefined();
      expect(band.colorVar.length).toBeGreaterThan(0);
    }
  });

  it('every band has a severity level', () => {
    for (const band of HEALTH_BANDS) {
      expect(SEVERITY_LEVELS).toContain(band.severity);
    }
  });
});

describe('Directive Color System Compliance', () => {
  // RED = BLOCKING, ORANGE = HIGH RISK, YELLOW = NEEDS ATTENTION,
  // BLUE = IN REVIEW, GREEN = HEALTHY, GRAY = INFORMATIONAL/CLOSED

  it('BLOCKING severity uses red', () => {
    expect(SEVERITY_COLOR_MAP.BLOCKING).toContain('red');
  });

  it('HIGH severity uses orange', () => {
    expect(SEVERITY_COLOR_MAP.HIGH).toContain('orange');
  });

  it('MEDIUM severity uses yellow', () => {
    expect(SEVERITY_COLOR_MAP.MEDIUM).toContain('yellow');
  });
});

describe('Status Variants', () => {
  it('defines expected status types', () => {
    expect(STATUS_VARIANTS).toContain('active');
    expect(STATUS_VARIANTS).toContain('warning');
    expect(STATUS_VARIANTS).toContain('critical');
    expect(STATUS_VARIANTS).toContain('info');
    expect(STATUS_VARIANTS).toContain('neutral');
  });

  it('every status variant has a color', () => {
    for (const variant of STATUS_VARIANTS) {
      expect(STATUS_COLOR_MAP[variant]).toBeDefined();
    }
  });
});

describe('System Domains', () => {
  it('includes all FusionEMS operational domains', () => {
    const expected = ['billing', 'fire', 'hems', 'fleet', 'compliance', 'cad', 'clinical', 'ops'];
    for (const domain of expected) {
      expect(SYSTEM_DOMAINS).toContain(domain);
    }
  });
});
