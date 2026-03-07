'use client';

import { useEffect, useState } from 'react';
import Link from 'next/link';
import { motion } from 'framer-motion';
import { getAICommandMetrics } from '@/services/api';

// ── Types ────────────────────────────────────────────────────────────────────

interface RiskBreakdown {
  restricted: number;
  high_risk: number;
  moderate_risk: number;
  low_risk: number;
}

interface ReviewEntry {
  id: string;
  workflow_id: string;
  review_type: string;
  priority: string;
  status: string;
  created_at: string;
}

interface GovernanceAction {
  action: string;
  domain: string;
  urgency: string;
}

interface CommandMetrics {
  health_score: number;
  total_use_cases: number;
  active_use_cases: number;
  total_workflows_24h: number;
  failed_workflows_24h: number;
  pending_reviews: number;
  risk_breakdown: RiskBreakdown;
  review_queue: ReviewEntry[];
  top_governance_actions: GovernanceAction[];
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

function urgencyColor(u: string): string {
  switch (u) {
    case 'high': return 'var(--color-brand-red)';
    case 'medium': return 'var(--color-status-warning)';
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
        <div className="text-[10px] uppercase tracking-widest text-text-muted">AI Health</div>
      </div>
    </div>
  );
}

function KpiCard({ label, value, color }: { label: string; value: string | number; color?: string }) {
  return (
    <div
      className="bg-bg-panel border border-border-DEFAULT p-4 flex flex-col justify-between"
      style={{ clipPath: 'polygon(0 0, calc(100% - 10px) 0, 100% 10px, 100% 100%, 0 100%)' }}
    >
      <div className="text-[10px] font-semibold uppercase tracking-widest text-text-muted mb-2">{label}</div>
      <div className="text-2xl font-bold" style={{ color: color || 'var(--color-text-primary)' }}>{value}</div>
    </div>
  );
}

function RiskBar({ label, count, total, color }: { label: string; count: number; total: number; color: string }) {
  const pct = total > 0 ? (count / total) * 100 : 0;
  return (
    <div className="flex items-center gap-3">
      <div className="text-[10px] uppercase tracking-widest text-text-muted w-24 shrink-0">{label}</div>
      <div className="flex-1 h-2 bg-[rgba(255,255,255,0.04)] rounded-full overflow-hidden">
        <div className="h-full rounded-full transition-all" style={{ width: `${pct}%`, background: color }} />
      </div>
      <div className="text-xs font-bold text-text-secondary w-8 text-right">{count}</div>
    </div>
  );
}

// ── Page ─────────────────────────────────────────────────────────────────────

export default function AICommandCenterPage() {
  const [metrics, setMetrics] = useState<CommandMetrics | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    getAICommandMetrics()
      .then((data) => { if (!cancelled) setMetrics(data); })
      .catch(() => { if (!cancelled) setError('Failed to load AI command metrics.'); })
      .finally(() => { if (!cancelled) setLoading(false); });
    return () => { cancelled = true; };
  }, []);

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
          <Link href="/founder/ai" className="text-xs text-orange-dim hover:text-orange mt-4 inline-block">← Back to AI Governance</Link>
        </div>
      </div>
    );
  }

  const totalUseCases = metrics.total_use_cases || 1;

  return (
    <div className="p-5 space-y-6 min-h-screen">
      {/* Header */}
      <div>
        <div className="text-[10px] font-bold uppercase tracking-[0.2em] text-orange-dim mb-1">FOUNDER · AI PLATFORM</div>
        <h1 className="text-xl font-black uppercase tracking-wider text-text-primary">AI Command Center</h1>
        <p className="text-xs text-text-muted mt-0.5">Real-time health · governance · review queue · risk posture</p>
      </div>

      {/* Top row: Health Gauge + KPIs */}
      <div className="grid grid-cols-1 md:grid-cols-5 gap-4 items-stretch">
        <motion.div
          initial={{ opacity: 0, scale: 0.9 }} animate={{ opacity: 1, scale: 1 }}
          className="md:col-span-1 bg-bg-panel border border-border-DEFAULT p-5 flex items-center justify-center relative"
          style={{ clipPath: 'polygon(0 0, calc(100% - 10px) 0, 100% 10px, 100% 100%, 0 100%)' }}
        >
          <HealthGauge score={metrics.health_score} />
        </motion.div>

        <div className="md:col-span-4 grid grid-cols-2 lg:grid-cols-4 gap-3">
          <KpiCard label="Active Use Cases" value={metrics.active_use_cases} />
          <KpiCard label="Workflows (24h)" value={metrics.total_workflows_24h} />
          <KpiCard
            label="Failed (24h)"
            value={metrics.failed_workflows_24h}
            color={metrics.failed_workflows_24h > 0 ? 'var(--color-brand-red)' : undefined}
          />
          <KpiCard
            label="Pending Reviews"
            value={metrics.pending_reviews}
            color={metrics.pending_reviews > 0 ? 'var(--color-brand-orange)' : undefined}
          />
        </div>
      </div>

      {/* Risk Breakdown */}
      <div className="bg-bg-panel border border-border-DEFAULT p-5" style={{ clipPath: 'polygon(0 0, calc(100% - 10px) 0, 100% 10px, 100% 100%, 0 100%)' }}>
        <div className="text-[10px] font-semibold uppercase tracking-widest text-text-muted mb-4">Risk Tier Distribution</div>
        <div className="space-y-2.5">
          <RiskBar label="Restricted" count={metrics.risk_breakdown.restricted} total={totalUseCases} color="var(--color-brand-red)" />
          <RiskBar label="High Risk" count={metrics.risk_breakdown.high_risk} total={totalUseCases} color="var(--color-brand-orange)" />
          <RiskBar label="Moderate" count={metrics.risk_breakdown.moderate_risk} total={totalUseCases} color="var(--color-status-warning)" />
          <RiskBar label="Low Risk" count={metrics.risk_breakdown.low_risk} total={totalUseCases} color="var(--color-status-active)" />
        </div>
      </div>

      {/* Two-column: Review Queue + Governance Actions */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        {/* Review Queue */}
        <div className="bg-bg-panel border border-border-DEFAULT p-5" style={{ clipPath: 'polygon(0 0, calc(100% - 10px) 0, 100% 10px, 100% 100%, 0 100%)' }}>
          <div className="flex items-center justify-between mb-4">
            <div className="text-[10px] font-semibold uppercase tracking-widest text-text-muted">Review Queue</div>
            <Link href="/founder/ai/review-queue" className="text-[10px] text-orange-dim hover:text-orange uppercase tracking-widest">
              View All →
            </Link>
          </div>
          {metrics.review_queue.length === 0 ? (
            <div className="text-xs text-[rgba(255,255,255,0.4)] py-6 text-center">No pending reviews</div>
          ) : (
            <div className="space-y-2">
              {metrics.review_queue.map((item) => (
                <div key={item.id} className="flex items-center justify-between gap-3 py-2 border-b border-[rgba(255,255,255,0.05)] last:border-0">
                  <div className="flex items-center gap-2 min-w-0">
                    <span className="w-1.5 h-1.5 rounded-full shrink-0" style={{ background: priorityColor(item.priority) }} />
                    <span className="text-xs text-text-secondary truncate">{item.review_type}</span>
                  </div>
                  <span className="text-[10px] uppercase tracking-wider shrink-0" style={{ color: priorityColor(item.priority) }}>
                    {item.priority}
                  </span>
                </div>
              ))}
            </div>
          )}
        </div>

        {/* Governance Actions */}
        <div className="bg-bg-panel border border-border-DEFAULT p-5" style={{ clipPath: 'polygon(0 0, calc(100% - 10px) 0, 100% 10px, 100% 100%, 0 100%)' }}>
          <div className="text-[10px] font-semibold uppercase tracking-widest text-text-muted mb-4">Top Governance Actions</div>
          {metrics.top_governance_actions.length === 0 ? (
            <div className="text-xs text-[rgba(255,255,255,0.4)] py-6 text-center">No governance actions</div>
          ) : (
            <div className="space-y-2">
              {metrics.top_governance_actions.map((ga, i) => (
                <div key={i} className="flex items-center justify-between gap-3 py-2 border-b border-[rgba(255,255,255,0.05)] last:border-0">
                  <div className="flex items-center gap-2 min-w-0">
                    <span className="text-xs text-text-secondary truncate">{ga.action}</span>
                  </div>
                  <div className="flex items-center gap-2 shrink-0">
                    <span className="text-[10px] text-text-muted uppercase tracking-wider">{ga.domain}</span>
                    <span className="w-1.5 h-1.5 rounded-full" style={{ background: urgencyColor(ga.urgency) }} />
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>

      <Link href="/founder/ai" className="text-xs text-orange-dim hover:text-orange">← Back to AI Governance</Link>
    </div>
  );
}
