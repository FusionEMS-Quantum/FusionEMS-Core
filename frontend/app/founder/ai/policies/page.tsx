'use client';

import { useEffect, useState } from 'react';
import Link from 'next/link';
import { motion } from 'framer-motion';
import { getAIGuardrailRules, getAIProtectedActions } from '@/services/api';

// ── Types ────────────────────────────────────────────────────────────────────

interface GuardrailRule {
  id: string;
  domain: string;
  rule_name: string;
  description: string;
  enforcement: string;
  is_active: boolean;
}

interface ProtectedAction {
  id: string;
  action_name: string;
  domain: string;
  risk_tier: string;
  description: string;
  requires_human: boolean;
}

// ── Helpers ──────────────────────────────────────────────────────────────────

function enforcementColor(e: string): string {
  switch (e) {
    case 'BLOCK': return 'var(--color-brand-red)';
    case 'WARN': return 'var(--color-status-warning)';
    case 'LOG': return 'var(--color-status-info)';
    default: return 'var(--color-text-muted)';
  }
}

function riskColor(r: string): string {
  switch (r) {
    case 'RESTRICTED': return 'var(--color-brand-red)';
    case 'HIGH_RISK': return 'var(--color-brand-orange)';
    case 'MODERATE_RISK': return 'var(--color-status-warning)';
    default: return 'var(--color-status-active)';
  }
}

// ── Page ─────────────────────────────────────────────────────────────────────

export default function AiPoliciesPage() {
  const [rules, setRules] = useState<GuardrailRule[]>([]);
  const [actions, setActions] = useState<ProtectedAction[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    Promise.all([getAIGuardrailRules(), getAIProtectedActions()])
      .then(([r, a]) => {
        if (cancelled) return;
        setRules(r as GuardrailRule[]);
        setActions(a as ProtectedAction[]);
      })
      .catch(() => { if (!cancelled) setError('Failed to load governance data.'); })
      .finally(() => { if (!cancelled) setLoading(false); });
    return () => { cancelled = true; };
  }, []);

  return (
    <div className="p-5 min-h-screen space-y-6">
      {/* Header */}
      <div>
        <div className="text-micro font-bold uppercase tracking-[0.2em] text-orange-dim mb-1">AI GOVERNANCE</div>
        <h1 className="text-xl font-black uppercase tracking-wider text-text-primary">AI Governance & Policies</h1>
        <p className="text-xs text-text-muted mt-0.5">Guardrail rules · protected actions · enforcement levels</p>
      </div>

      {error && (
        <div className="bg-[rgba(255,45,45,0.08)] border border-[rgba(255,45,45,0.35)] p-3 chamfer-4 text-xs text-[var(--color-brand-red)]">
          {error}
        </div>
      )}

      {loading ? (
        <div className="space-y-3">
          {[...Array(4)].map((_, i) => (
            <div key={i} className="animate-pulse bg-bg-panel border border-border-DEFAULT h-16 chamfer-8" />
          ))}
        </div>
      ) : (
        <>
          {/* Guardrail Rules */}
          <section>
            <div className="text-micro font-semibold uppercase tracking-widest text-text-muted mb-3">Guardrail Rules</div>
            {rules.length === 0 ? (
              <div className="bg-bg-panel border border-border-DEFAULT chamfer-8 p-6 text-center text-xs text-text-muted">
                No guardrail rules configured
              </div>
            ) : (
              <div className="space-y-2">
                {rules.map((rule, i) => (
                  <motion.div
                    key={rule.id}
                    initial={{ opacity: 0, y: 6 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ delay: i * 0.03 }}
                    className="bg-bg-panel border border-border-DEFAULT p-4 flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3"
                    style={{ clipPath: 'polygon(0 0, calc(100% - 10px) 0, 100% 10px, 100% 100%, 0 100%)' }}
                  >
                    <div className="min-w-0">
                      <div className="flex items-center gap-2 mb-1">
                        <span className="text-sm font-bold text-text-primary">{rule.rule_name}</span>
                        {!rule.is_active && (
                          <span className="text-micro uppercase tracking-widest text-text-muted px-1.5 py-0.5 border border-border-DEFAULT chamfer-4">
                            DISABLED
                          </span>
                        )}
                      </div>
                      <div className="text-xs text-text-secondary">{rule.description}</div>
                      <div className="text-micro text-text-muted mt-1">Domain: {rule.domain}</div>
                    </div>
                    <span
                      className="text-micro uppercase tracking-widest font-bold px-2 py-0.5 chamfer-4 shrink-0"
                      style={{
                        color: enforcementColor(rule.enforcement),
                        background: `color-mix(in srgb, ${enforcementColor(rule.enforcement)} 12%, transparent)`,
                        border: `1px solid color-mix(in srgb, ${enforcementColor(rule.enforcement)} 30%, transparent)`,
                      }}
                    >
                      {rule.enforcement}
                    </span>
                  </motion.div>
                ))}
              </div>
            )}
          </section>

          {/* Protected Actions */}
          <section>
            <div className="text-micro font-semibold uppercase tracking-widest text-text-muted mb-3">Protected Actions</div>
            {actions.length === 0 ? (
              <div className="bg-bg-panel border border-border-DEFAULT chamfer-8 p-6 text-center text-xs text-text-muted">
                No protected actions configured
              </div>
            ) : (
              <div className="space-y-2">
                {actions.map((action, i) => (
                  <motion.div
                    key={action.id}
                    initial={{ opacity: 0, y: 6 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ delay: i * 0.03 }}
                    className="bg-bg-panel border border-border-DEFAULT p-4 flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3"
                    style={{ clipPath: 'polygon(0 0, calc(100% - 10px) 0, 100% 10px, 100% 100%, 0 100%)' }}
                  >
                    <div className="min-w-0">
                      <div className="text-sm font-bold text-text-primary mb-0.5">{action.action_name}</div>
                      <div className="text-xs text-text-secondary">{action.description}</div>
                      <div className="text-micro text-text-muted mt-1">
                        Domain: {action.domain}
                        {action.requires_human && ' · Human review required'}
                      </div>
                    </div>
                    <span
                      className="text-micro uppercase tracking-widest font-bold px-2 py-0.5 chamfer-4 shrink-0"
                      style={{
                        color: riskColor(action.risk_tier),
                        background: `color-mix(in srgb, ${riskColor(action.risk_tier)} 12%, transparent)`,
                        border: `1px solid color-mix(in srgb, ${riskColor(action.risk_tier)} 30%, transparent)`,
                      }}
                    >
                      {action.risk_tier.replace(/_/g, ' ')}
                    </span>
                  </motion.div>
                ))}
              </div>
            )}
          </section>
        </>
      )}

      <Link href="/founder/ai" className="text-xs text-orange-dim hover:text-orange">← Back to AI Governance</Link>
    </div>
  );
}
