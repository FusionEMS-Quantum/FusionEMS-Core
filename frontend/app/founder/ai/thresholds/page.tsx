'use client';

import { useEffect, useState } from 'react';
import Link from 'next/link';
import { motion } from 'framer-motion';
import { getAIUseCases } from '@/services/api';

interface UseCase {
  id: string;
  name: string;
  domain: string;
  risk_tier: string;
  is_enabled: boolean;
  fallback_behavior: string;
  human_override_behavior: string;
  owner: string;
}

function riskColor(r: string): string {
  switch (r) {
    case 'RESTRICTED': return 'var(--color-brand-red)';
    case 'HIGH_RISK': return 'var(--color-brand-orange)';
    case 'MODERATE_RISK': return 'var(--color-status-warning)';
    default: return 'var(--color-status-active)';
  }
}

const CONFIDENCE_THRESHOLDS = [
  { tier: 'RESTRICTED', label: 'Restricted', threshold: 'Always requires human review', color: 'var(--color-brand-red)' },
  { tier: 'HIGH_RISK', label: 'High Risk', threshold: 'HIGH confidence required for auto-approve', color: 'var(--color-brand-orange)' },
  { tier: 'MODERATE_RISK', label: 'Moderate Risk', threshold: 'MEDIUM confidence required for auto-approve', color: 'var(--color-status-warning)' },
  { tier: 'LOW_RISK', label: 'Low Risk', threshold: 'LOW confidence acceptable for auto-approve', color: 'var(--color-status-active)' },
];

export default function AiThresholdsPage() {
  const [useCases, setUseCases] = useState<UseCase[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    getAIUseCases()
      .then((data: UseCase[]) => { if (!cancelled) setUseCases(data); })
      .catch(() => { if (!cancelled) setError('Failed to load use cases.'); })
      .finally(() => { if (!cancelled) setLoading(false); });
    return () => { cancelled = true; };
  }, []);

  return (
    <div className="p-5 min-h-screen space-y-6">
      <div>
        <div className="text-micro font-bold uppercase tracking-[0.2em] text-orange-dim mb-1">AI GOVERNANCE</div>
        <h1 className="text-xl font-black uppercase tracking-wider text-text-primary">Confidence Thresholds</h1>
        <p className="text-xs text-text-muted mt-0.5">Escalation rules per risk tier · auto-approve boundaries</p>
      </div>

      {error && (
        <div className="bg-red-500/[0.08] border border-red-500/[0.35] p-3 chamfer-4 text-xs text-[var(--color-brand-red)]">
          {error}
        </div>
      )}

      {/* Threshold reference table */}
      <div className="bg-bg-panel border border-border-DEFAULT p-5" style={{ clipPath: 'polygon(0 0, calc(100% - 10px) 0, 100% 10px, 100% 100%, 0 100%)' }}>
        <div className="text-micro font-semibold uppercase tracking-widest text-text-muted mb-4">Confidence Policy by Risk Tier</div>
        <div className="space-y-2">
          {CONFIDENCE_THRESHOLDS.map((ct) => (
            <div key={ct.tier} className="flex items-center gap-3 py-2 border-b border-white/5 last:border-0">
              <span className="w-2 h-2 rounded-full shrink-0" style={{ background: ct.color }} />
              <span className="text-xs font-bold w-28 shrink-0" style={{ color: ct.color }}>{ct.label}</span>
              <span className="text-xs text-text-secondary">{ct.threshold}</span>
            </div>
          ))}
        </div>
      </div>

      {/* Use cases by risk tier */}
      <div>
        <div className="text-micro font-semibold uppercase tracking-widest text-text-muted mb-3">Active Use Cases</div>
        {loading ? (
          <div className="space-y-3">
            {[...Array(3)].map((_, i) => (
              <div key={i} className="animate-pulse bg-bg-panel border border-border-DEFAULT h-16 chamfer-8" />
            ))}
          </div>
        ) : useCases.length === 0 ? (
          <div className="bg-bg-panel border border-border-DEFAULT chamfer-8 p-10 text-center text-xs text-text-muted">
            No AI use cases registered
          </div>
        ) : (
          <div className="space-y-2">
            {useCases.map((uc, i) => (
              <motion.div
                key={uc.id}
                initial={{ opacity: 0, y: 6 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: i * 0.03 }}
                className="bg-bg-panel border border-border-DEFAULT p-4 flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3"
                style={{ clipPath: 'polygon(0 0, calc(100% - 10px) 0, 100% 10px, 100% 100%, 0 100%)' }}
              >
                <div className="min-w-0">
                  <div className="flex items-center gap-2 mb-1">
                    <span className="text-sm font-bold text-text-primary">{uc.name}</span>
                    {!uc.is_enabled && (
                      <span className="text-micro uppercase tracking-widest text-text-muted px-1.5 py-0.5 border border-border-DEFAULT chamfer-4">
                        DISABLED
                      </span>
                    )}
                  </div>
                  <div className="text-micro text-text-muted">
                    {uc.domain} · Override: {uc.human_override_behavior} · Fallback: {uc.fallback_behavior}
                  </div>
                </div>
                <span
                  className="text-micro uppercase tracking-widest font-bold px-2 py-0.5 chamfer-4 shrink-0"
                  style={{
                    color: riskColor(uc.risk_tier),
                    background: `color-mix(in srgb, ${riskColor(uc.risk_tier)} 12%, transparent)`,
                    border: `1px solid color-mix(in srgb, ${riskColor(uc.risk_tier)} 30%, transparent)`,
                  }}
                >
                  {uc.risk_tier.replace(/_/g, ' ')}
                </span>
              </motion.div>
            ))}
          </div>
        )}
      </div>

      <Link href="/founder/ai" className="text-xs text-orange-dim hover:text-orange">← Back to AI Governance</Link>
    </div>
  );
}
