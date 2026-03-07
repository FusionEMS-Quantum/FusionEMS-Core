'use client';

import { useEffect, useState } from 'react';
import Link from 'next/link';
import { motion } from 'framer-motion';
import { getAICommandMetrics, updateAITenantSettings } from '@/services/api';

// ── Types ────────────────────────────────────────────────────────────────────

interface RiskBreakdown {
  RESTRICTED: number;
  HIGH_RISK: number;
  MODERATE_RISK: number;
  LOW_RISK: number;
}

interface ReviewEntry {
  review_id: string;
  workflow_id: string;
  correlation_id: string;
  use_case_name: string;
  domain: string;
  priority: string;
  summary: string | null;
  created_at: string;
}

interface GovernanceAction {
  action_type: string;
  title: string;
  description: string;
  severity: string;
  target_id: string | null;
}

interface HighRiskRecommendation {
  workflow_id: string;
  use_case_name: string;
  domain: string;
  risk_tier: string;
  confidence: string | null;
  explanation_summary: string | null;
  override_state: string;
  created_at: string;
}

interface CommandMetrics {
  health_score: number;
  total_use_cases: number;
  enabled_use_cases: number;
  disabled_workflows: number;
  low_confidence_count: number;
  review_queue_count: number;
  failed_runs_count: number;
  risk_tier_breakdown: RiskBreakdown;
  recent_reviews: ReviewEntry[];
  top_actions: GovernanceAction[];
  high_risk_recommendations: HighRiskRecommendation[];
  tenant_ai_enabled: boolean;
}

// ── Color helpers ────────────────────────────────────────────────────────────

function healthColor(score: number): string {
  if (score >= 90) return 'var(--color-status-active)';
  if (score >= 75) return 'var(--color-status-info)';
  if (score >= 50) return 'var(--color-status-warning)';
  return 'var(--color-brand-red)';
}

function priorityColor(p: string): string {
  switch (p) {
    case 'CRITICAL': return 'var(--color-brand-red)';
    case 'HIGH': return 'var(--color-brand-orange)';
    case 'MEDIUM': return 'var(--color-status-warning)';
    default: return 'var(--color-status-active)';
  }
}

function severityColor(s: string): string {
  switch (s) {
    case 'RED': return 'var(--color-brand-red)';
    case 'ORANGE': return 'var(--color-brand-orange)';
    case 'YELLOW': return 'var(--color-status-warning)';
    case 'BLUE': return 'var(--color-status-info)';
    case 'GREEN': return 'var(--color-status-active)';
    case 'GRAY': return 'var(--color-text-muted)';
    default: return 'var(--color-status-active)';
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

// ── Sub-components ───────────────────────────────────────────────────────────

function HealthGauge({ score }: { score: number }) {
  const radius = 44;
  const circumference = 2 * Math.PI * radius;
  const offset = circumference - (score / 100) * circumference;
  const color = healthColor(score);

  return (
    <div className="flex flex-col items-center justify-center gap-2">
      <svg width={120} height={120} className="-rotate-90">
        <circle cx={60} cy={60} r={radius} fill="none" stroke="rgba(255,255,255,0.06)" strokeWidth={8} />
        <circle
          cx={60} cy={60} r={radius} fill="none" stroke={color} strokeWidth={8}
          strokeDasharray={circumference} strokeDashoffset={offset}
          strokeLinecap="round" className="transition-all duration-700"
        />
      </svg>
      <div className="absolute text-center">
        <div className="text-3xl font-black" style={{ color }}>{score}</div>
        <div className="text-micro uppercase tracking-widest text-text-muted">AI Health</div>
      </div>
    </div>
  );
}

function KpiCard({ label, value, color, badge }: { label: string; value: string | number; color?: string; badge?: string }) {
  return (
    <div
      className="bg-bg-panel border border-border-DEFAULT p-4 flex flex-col justify-between relative"
      style={{ clipPath: 'polygon(0 0, calc(100% - 10px) 0, 100% 10px, 100% 100%, 0 100%)' }}
    >
      <div className="text-micro font-semibold uppercase tracking-widest text-text-muted mb-2">{label}</div>
      <div className="text-2xl font-bold" style={{ color: color || 'var(--color-text-primary)' }}>{value}</div>
      {badge && (
        <span className="absolute top-2 right-3 text-micro uppercase tracking-widest font-bold px-1.5 py-0.5 rounded"
          style={{ background: 'rgba(255,107,26,0.15)', color: 'var(--color-brand-orange)', border: '1px solid rgba(255,107,26,0.3)' }}>
          {badge}
        </span>
      )}
    </div>
  );
}

function RiskBar({ label, count, total, color }: { label: string; count: number; total: number; color: string }) {
  const pct = total > 0 ? (count / total) * 100 : 0;
  return (
    <div className="flex items-center gap-3">
      <div className="text-micro uppercase tracking-widest text-text-muted w-24 shrink-0">{label}</div>
      <div className="flex-1 h-2 bg-white/[0.04] rounded-full overflow-hidden">
        <div className="h-full rounded-full transition-all" style={{ width: `${pct}%`, background: color }} />
      </div>
      <div className="text-xs font-bold text-text-secondary w-8 text-right">{count}</div>
    </div>
  );
}

function SimpleModeCard({ title, items }: { title: string; items: { what: string; why: string; next: string }[] }) {
  if (items.length === 0) return null;
  return (
    <div className="bg-bg-panel border border-border-DEFAULT p-5" style={{ clipPath: 'polygon(0 0, calc(100% - 10px) 0, 100% 10px, 100% 100%, 0 100%)' }}>
      <div className="text-micro font-semibold uppercase tracking-widest text-text-muted mb-4">{title}</div>
      <div className="space-y-3">
        {items.map((item, i) => (
          <div key={i} className="border-b border-white/5 last:border-0 pb-3 last:pb-0 space-y-1">
            <div className="text-xs"><span className="font-bold text-text-primary">WHAT HAPPENED:</span> <span className="text-text-secondary">{item.what}</span></div>
            <div className="text-xs"><span className="font-bold text-text-primary">WHY IT MATTERS:</span> <span className="text-text-secondary">{item.why}</span></div>
            <div className="text-xs"><span className="font-bold" style={{ color: 'var(--color-brand-orange)' }}>DO THIS NEXT:</span> <span className="text-text-secondary">{item.next}</span></div>
          </div>
        ))}
      </div>
    </div>
  );
}

// ── Page ─────────────────────────────────────────────────────────────────────

export default function AICommandCenterPage() {
  const [metrics, setMetrics] = useState<CommandMetrics | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [simpleMode, setSimpleMode] = useState(false);
  const [toggling, setToggling] = useState(false);

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    getAICommandMetrics()
      .then((data) => { if (!cancelled) setMetrics(data); })
      .catch(() => { if (!cancelled) setError('Failed to load AI command metrics.'); })
      .finally(() => { if (!cancelled) setLoading(false); });
    return () => { cancelled = true; };
  }, []);

  async function handleToggleAI() {
    if (!metrics) return;
    setToggling(true);
    try {
      await updateAITenantSettings({ ai_enabled: !metrics.tenant_ai_enabled });
      setMetrics({ ...metrics, tenant_ai_enabled: !metrics.tenant_ai_enabled });
    } catch {
      setError('Failed to toggle AI.');
    } finally {
      setToggling(false);
    }
  }

  if (loading) {
    return (
      <div className="p-5 space-y-4">
        <div className="animate-pulse bg-bg-panel border border-border-DEFAULT chamfer-8 h-10 w-64" />
        <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
          {[...Array(4)].map((_, i) => (
            <div key={i} className="animate-pulse bg-bg-panel border border-border-DEFAULT h-24" />
          ))}
        </div>
      </div>
    );
  }

  if (error || !metrics) {
    return (
      <div className="p-5">
        <div className="bg-bg-panel border border-border-DEFAULT chamfer-8 p-8 text-center">
          <div className="text-sm text-text-muted">{error || 'No data available'}</div>
          <Link href="/founder/ai" className="text-xs text-orange-dim hover:text-orange mt-4 inline-block">&larr; Back to AI Governance</Link>
        </div>
      </div>
    );
  }

  const totalUseCases = metrics.total_use_cases || 1;

  // Simple Mode summaries derived from top_actions
  const simpleModeItems = metrics.top_actions.map((ga) => ({
    what: ga.title,
    why: ga.description,
    next: ga.action_type === 'investigate_failures' ? 'Open failed run logs and resolve root errors'
      : ga.action_type === 'clear_review_queue' ? 'Review and approve or reject pending AI outputs'
      : ga.action_type === 'review_low_confidence' ? 'Tune prompts or adjust model bindings for low-confidence use cases'
      : 'Review disabled workflows and re-enable or archive them',
  }));

  return (
    <div className="p-5 space-y-6 min-h-screen">
      {/* Header + Controls */}
      <div className="flex flex-col sm:flex-row sm:items-start sm:justify-between gap-3">
        <div>
          <div className="text-micro font-bold uppercase tracking-[0.2em] text-orange-dim mb-1">FOUNDER &middot; AI PLATFORM</div>
          <h1 className="text-xl font-black uppercase tracking-wider text-text-primary">AI Command Center</h1>
          <p className="text-xs text-text-muted mt-0.5">Real-time health &middot; governance &middot; review queue &middot; risk posture</p>
        </div>
        <div className="flex items-center gap-3 shrink-0">
          {/* Simple Mode Toggle */}
          <button
            onClick={() => setSimpleMode(!simpleMode)}
            className="text-micro uppercase tracking-widest font-bold px-3 py-1.5 border transition-colors"
            style={{
              color: simpleMode ? 'var(--color-brand-orange)' : 'var(--color-text-muted)',
              borderColor: simpleMode ? 'rgba(255,107,26,0.5)' : 'var(--color-border-default)',
              background: simpleMode ? 'rgba(255,107,26,0.08)' : 'transparent',
            }}
          >
            {simpleMode ? 'SIMPLE MODE ON' : 'SIMPLE MODE'}
          </button>
          {/* AI Master Toggle */}
          <button
            onClick={handleToggleAI}
            disabled={toggling}
            className="text-micro uppercase tracking-widest font-bold px-3 py-1.5 border transition-colors disabled:opacity-50"
            style={{
              color: metrics.tenant_ai_enabled ? 'var(--color-status-active)' : 'var(--color-brand-red)',
              borderColor: metrics.tenant_ai_enabled ? 'rgba(34,197,94,0.4)' : 'rgba(239,68,68,0.4)',
              background: metrics.tenant_ai_enabled ? 'rgba(34,197,94,0.08)' : 'rgba(239,68,68,0.08)',
            }}
          >
            {metrics.tenant_ai_enabled ? 'AI ENABLED' : 'AI DISABLED'}
          </button>
        </div>
      </div>

      {/* Simple Mode View */}
      {simpleMode ? (
        <SimpleModeCard title="Top Priorities — Simple Mode" items={simpleModeItems} />
      ) : (
        <>
          {/* Top row: Health Gauge + KPIs */}
          <div className="grid grid-cols-1 md:grid-cols-5 gap-4 items-stretch">
            <motion.div
              initial={{ opacity: 0, scale: 0.9 }} animate={{ opacity: 1, scale: 1 }}
              className="md:col-span-1 bg-bg-panel border border-border-DEFAULT p-5 flex items-center justify-center relative"
              style={{ clipPath: 'polygon(0 0, calc(100% - 10px) 0, 100% 10px, 100% 100%, 0 100%)' }}
            >
              <HealthGauge score={metrics.health_score} />
            </motion.div>

            <div className="md:col-span-4 grid grid-cols-2 lg:grid-cols-5 gap-3">
              <KpiCard label="Active Use Cases" value={metrics.enabled_use_cases} />
              <KpiCard label="Disabled" value={metrics.disabled_workflows} badge={metrics.disabled_workflows > 0 ? `${metrics.disabled_workflows}` : undefined} />
              <KpiCard
                label="Failed Runs"
                value={metrics.failed_runs_count}
                color={metrics.failed_runs_count > 0 ? 'var(--color-brand-red)' : undefined}
              />
              <KpiCard
                label="Low Confidence"
                value={metrics.low_confidence_count}
                color={metrics.low_confidence_count > 0 ? 'var(--color-status-warning)' : undefined}
                badge={metrics.low_confidence_count > 0 ? `${metrics.low_confidence_count}` : undefined}
              />
              <KpiCard
                label="Pending Reviews"
                value={metrics.review_queue_count}
                color={metrics.review_queue_count > 0 ? 'var(--color-brand-orange)' : undefined}
                badge={metrics.review_queue_count > 0 ? `${metrics.review_queue_count}` : undefined}
              />
            </div>
          </div>

          {/* Risk Breakdown */}
          <div className="bg-bg-panel border border-border-DEFAULT p-5" style={{ clipPath: 'polygon(0 0, calc(100% - 10px) 0, 100% 10px, 100% 100%, 0 100%)' }}>
            <div className="text-micro font-semibold uppercase tracking-widest text-text-muted mb-4">Risk Tier Distribution</div>
            <div className="space-y-2.5">
              <RiskBar label="Restricted" count={metrics.risk_tier_breakdown.RESTRICTED ?? 0} total={totalUseCases} color="var(--color-brand-red)" />
              <RiskBar label="High Risk" count={metrics.risk_tier_breakdown.HIGH_RISK ?? 0} total={totalUseCases} color="var(--color-brand-orange)" />
              <RiskBar label="Moderate" count={metrics.risk_tier_breakdown.MODERATE_RISK ?? 0} total={totalUseCases} color="var(--color-status-warning)" />
              <RiskBar label="Low Risk" count={metrics.risk_tier_breakdown.LOW_RISK ?? 0} total={totalUseCases} color="var(--color-status-active)" />
            </div>
          </div>

          {/* High-Risk Recommendations Awaiting Approval */}
          {metrics.high_risk_recommendations.length > 0 && (
            <div className="bg-bg-panel border border-border-DEFAULT p-5" style={{ clipPath: 'polygon(0 0, calc(100% - 10px) 0, 100% 10px, 100% 100%, 0 100%)', borderColor: 'rgba(255,107,26,0.3)' }}>
              <div className="text-micro font-semibold uppercase tracking-widest mb-4" style={{ color: 'var(--color-brand-orange)' }}>
                High-Risk Recommendations Awaiting Approval
              </div>
              <div className="space-y-2">
                {metrics.high_risk_recommendations.map((rec: HighRiskRecommendation) => (
                  <div key={rec.workflow_id} className="flex items-center justify-between gap-3 py-2 border-b border-white/5 last:border-0">
                    <div className="min-w-0">
                      <div className="flex items-center gap-2 mb-0.5">
                        <span className="w-1.5 h-1.5 rounded-full shrink-0" style={{ background: riskColor(rec.risk_tier) }} />
                        <span className="text-xs font-bold text-text-primary truncate">{rec.use_case_name}</span>
                        <span className="text-micro text-text-muted">{rec.domain}</span>
                      </div>
                      {rec.explanation_summary && (
                        <div className="text-micro text-text-muted truncate ml-3.5">{rec.explanation_summary}</div>
                      )}
                    </div>
                    <div className="flex items-center gap-2 shrink-0">
                      {rec.confidence && (
                        <span className="text-micro uppercase tracking-widest" style={{ color: rec.confidence === 'LOW' ? 'var(--color-brand-red)' : rec.confidence === 'MEDIUM' ? 'var(--color-status-warning)' : 'var(--color-status-active)' }}>
                          {rec.confidence}
                        </span>
                      )}
                      <span className="text-micro uppercase tracking-widest font-bold px-1.5 py-0.5 rounded"
                        style={{ color: riskColor(rec.risk_tier), background: `color-mix(in srgb, ${riskColor(rec.risk_tier)} 12%, transparent)` }}>
                        {rec.risk_tier.replace(/_/g, ' ')}
                      </span>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Three-column: Review Queue + Governance Actions + Next Best Actions */}
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
            {/* Review Queue */}
            <div className="bg-bg-panel border border-border-DEFAULT p-5" style={{ clipPath: 'polygon(0 0, calc(100% - 10px) 0, 100% 10px, 100% 100%, 0 100%)' }}>
              <div className="flex items-center justify-between mb-4">
                <div className="text-micro font-semibold uppercase tracking-widest text-text-muted">Review Queue</div>
                <Link href="/founder/ai/review-queue" className="text-micro text-orange-dim hover:text-orange uppercase tracking-widest">
                  View All &rarr;
                </Link>
              </div>
              {metrics.recent_reviews.length === 0 ? (
                <div className="text-xs text-text-muted py-6 text-center">No pending reviews</div>
              ) : (
                <div className="space-y-2">
                  {metrics.recent_reviews.map((item: ReviewEntry) => (
                    <div key={item.review_id} className="flex items-center justify-between gap-3 py-2 border-b border-white/5 last:border-0">
                      <div className="flex items-center gap-2 min-w-0">
                        <span className="w-1.5 h-1.5 rounded-full shrink-0" style={{ background: priorityColor(item.priority) }} />
                        <span className="text-xs text-text-secondary truncate">{item.use_case_name} &mdash; {item.domain}</span>
                      </div>
                      <span className="text-micro uppercase tracking-wider shrink-0" style={{ color: priorityColor(item.priority) }}>
                        {item.priority}
                      </span>
                    </div>
                  ))}
                </div>
              )}
            </div>

            {/* Governance Actions + Next Best Action */}
            <div className="bg-bg-panel border border-border-DEFAULT p-5" style={{ clipPath: 'polygon(0 0, calc(100% - 10px) 0, 100% 10px, 100% 100%, 0 100%)' }}>
              <div className="text-micro font-semibold uppercase tracking-widest text-text-muted mb-4">Top Governance Actions</div>
              {metrics.top_actions.length === 0 ? (
                <div className="text-xs text-text-muted py-6 text-center">No governance actions</div>
              ) : (
                <div className="space-y-2">
                  {metrics.top_actions.map((ga: GovernanceAction, i: number) => (
                    <div key={i} className="flex items-center justify-between gap-3 py-2 border-b border-white/5 last:border-0">
                      <div className="min-w-0">
                        <div className="text-xs font-bold text-text-primary truncate">{ga.title}</div>
                        <div className="text-micro text-text-muted truncate">{ga.description}</div>
                      </div>
                      <span className="w-2 h-2 rounded-full shrink-0" style={{ background: severityColor(ga.severity) }} />
                    </div>
                  ))}
                </div>
              )}
            </div>
          </div>
        </>
      )}

      <Link href="/founder/ai" className="text-xs text-orange-dim hover:text-orange">&larr; Back to AI Governance</Link>
    </div>
  );
}
