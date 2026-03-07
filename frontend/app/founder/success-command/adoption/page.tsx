'use client';
import { useEffect, useState } from 'react';
import Link from 'next/link';
import { motion } from 'framer-motion';
import { getLatestHealth, listAdoptionMetrics, listWorkflowAdoption, computeAccountHealth } from '@/services/api';

interface HealthSnapshot {
  id: string;
  overall_score: number;
  state: string;
  login_score: number;
  adoption_score: number;
  support_score: number;
  training_score: number;
  stability_score: number;
  risk_factors: Record<string, unknown>;
  computed_at: string;
  trigger: string;
}

interface AdoptionMetric {
  id: string;
  module_name: string;
  metric_value: number;
  active_user_count: number;
  total_user_count: number;
  category: string;
  measured_at: string;
}

interface WorkflowMetric {
  id: string;
  workflow_name: string;
  domain: string;
  total_invocations: number;
  successful_completions: number;
  abandonment_count: number;
  average_completion_seconds: number | null;
  measured_at: string;
}

const HEALTH_STATE_COLORS: Record<string, string> = {
  HEALTHY: 'text-green-400 border-green-400/30',
  MODERATE: 'text-yellow-400 border-yellow-400/30',
  AT_RISK: 'text-orange-400 border-orange-400/30',
  CRITICAL: 'text-red-400 border-red-400/30',
  CHURNING: 'text-red-500 border-red-500/30',
};

function healthScoreColor(score: number): string {
  if (score >= 80) return 'text-green-400';
  if (score >= 60) return 'text-yellow-400';
  if (score >= 40) return 'text-orange-400';
  return 'text-red-400';
}

function adoptionBarColor(pct: number): string {
  if (pct >= 70) return 'bg-green-400';
  if (pct >= 40) return 'bg-yellow-400';
  return 'bg-red-400';
}

export default function AdoptionHealthPage() {
  const [health, setHealth] = useState<HealthSnapshot | null>(null);
  const [adoption, setAdoption] = useState<AdoptionMetric[]>([]);
  const [workflows, setWorkflows] = useState<WorkflowMetric[]>([]);
  const [loading, setLoading] = useState(true);
  const [computing, setComputing] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function load() {
    try {
      setLoading(true);
      const [h, a, w] = await Promise.all([
        getLatestHealth(),
        listAdoptionMetrics(),
        listWorkflowAdoption(),
      ]);
      setHealth(h);
      setAdoption(a);
      setWorkflows(w);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : 'Failed to load health data');
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => { load(); }, []);

  async function handleRecompute() {
    setComputing(true);
    try {
      const newHealth = await computeAccountHealth();
      setHealth(newHealth);
    } catch {
      // Keep existing data
    } finally {
      setComputing(false);
    }
  }

  if (error) {
    return (
      <div className="p-5">
        <div className="bg-red-500/10 border border-red-500/30 p-4 text-red-400 text-sm">{error}</div>
      </div>
    );
  }

  return (
    <div className="p-5 space-y-6">
      <div className="flex items-start justify-between">
        <div>
          <div className="text-micro font-bold uppercase tracking-[0.2em] text-orange-dim mb-1">SUCCESS · HEALTH</div>
          <h1 className="text-xl font-black uppercase tracking-wider text-text-primary">Adoption & Health</h1>
          <p className="text-xs text-text-muted mt-0.5">Account health · module adoption · workflow completion</p>
        </div>
        <button onClick={handleRecompute} disabled={computing}
          className="text-micro px-3 py-1.5 border border-orange-dim text-orange-dim hover:bg-orange-dim/10 disabled:opacity-50 transition-colors">
          {computing ? 'Computing...' : 'Recompute Health'}
        </button>
      </div>

      {loading ? (
        <div className="space-y-3 animate-pulse">
          <div className="h-32 bg-bg-panel rounded" />
          <div className="h-40 bg-bg-panel rounded" />
        </div>
      ) : (
        <>
          {/* Account Health Score */}
          {health && (
            <div className={`bg-bg-panel border p-5 ${HEALTH_STATE_COLORS[health.state] || 'border-border-DEFAULT'}`}>
              <div className="flex items-center justify-between mb-4">
                <div>
                  <div className="text-micro font-bold text-orange-dim">ACCOUNT HEALTH</div>
                  <div className="text-xs text-text-muted mt-0.5">Last computed: {new Date(health.computed_at).toLocaleString()} ({health.trigger})</div>
                </div>
                <div className="text-right">
                  <div className={`text-3xl font-black ${healthScoreColor(health.overall_score)}`}>{health.overall_score.toFixed(0)}</div>
                  <div className={`text-micro font-bold ${HEALTH_STATE_COLORS[health.state]?.split(' ')[0] || ''}`}>{health.state}</div>
                </div>
              </div>

              <div className="grid grid-cols-5 gap-3">
                {[
                  { label: 'Login', score: health.login_score, weight: '15%' },
                  { label: 'Adoption', score: health.adoption_score, weight: '25%' },
                  { label: 'Support', score: health.support_score, weight: '20%' },
                  { label: 'Training', score: health.training_score, weight: '20%' },
                  { label: 'Stability', score: health.stability_score, weight: '20%' },
                ].map((f) => (
                  <div key={f.label} className="text-center">
                    <div className={`text-lg font-bold ${healthScoreColor(f.score)}`}>{f.score.toFixed(0)}</div>
                    <div className="text-micro text-text-muted">{f.label}</div>
                    <div className="text-micro text-text-muted opacity-60">({f.weight})</div>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Module Adoption */}
          <div>
            <div className="text-micro font-bold text-orange-dim mb-2">MODULE ADOPTION</div>
            {adoption.length === 0 ? (
              <div className="bg-bg-panel border border-border-DEFAULT p-6 text-center text-text-muted text-sm">No adoption metrics recorded yet.</div>
            ) : (
              <div className="space-y-2">
                {adoption.map((m, i) => (
                  <motion.div key={m.id} initial={{ opacity: 0, x: -6 }} animate={{ opacity: 1, x: 0 }} transition={{ delay: i * 0.04 }}
                    className="bg-bg-panel border border-border-DEFAULT p-3">
                    <div className="flex items-center justify-between mb-1">
                      <div className="text-sm font-bold text-text-primary">{m.module_name}</div>
                      <div className="text-xs text-text-muted">{m.active_user_count}/{m.total_user_count} users · {m.category}</div>
                    </div>
                    <div className="flex items-center gap-2">
                      <div className="flex-1 h-2 bg-bg-panel-muted rounded-full overflow-hidden">
                        <div className={`h-full ${adoptionBarColor(m.metric_value)} transition-all`} style={{ width: `${m.metric_value}%` }} />
                      </div>
                      <span className={`text-sm font-bold ${healthScoreColor(m.metric_value)}`}>{m.metric_value.toFixed(0)}%</span>
                    </div>
                  </motion.div>
                ))}
              </div>
            )}
          </div>

          {/* Workflow Adoption */}
          <div>
            <div className="text-micro font-bold text-orange-dim mb-2">WORKFLOW COMPLETION RATES</div>
            {workflows.length === 0 ? (
              <div className="bg-bg-panel border border-border-DEFAULT p-6 text-center text-text-muted text-sm">No workflow metrics recorded yet.</div>
            ) : (
              <div className="grid grid-cols-1 md:grid-cols-2 gap-2">
                {workflows.map((w) => {
                  const completionRate = w.total_invocations > 0 ? (w.successful_completions / w.total_invocations) * 100 : 0;
                  return (
                  <div key={w.id} className="bg-bg-panel border border-border-DEFAULT p-3">
                    <div className="text-sm font-bold text-text-primary">{w.workflow_name}</div>
                    <div className="text-xs text-text-muted">{w.domain}</div>
                    <div className="flex items-center justify-between mt-1 text-xs">
                      <span className={`font-bold ${healthScoreColor(completionRate)}`}>{completionRate.toFixed(0)}% completion</span>
                      {w.average_completion_seconds != null && <span className="text-text-muted">Avg: {(w.average_completion_seconds / 60).toFixed(1)} min</span>}
                    </div>
                    {w.abandonment_count > 0 && <div className="text-micro text-red-400 mt-1">Abandonments: {w.abandonment_count}</div>}
                  </div>
                  );
                })}
              </div>
            )}
          </div>
        </>
      )}

      <Link href="/founder/success-command" className="text-xs text-orange-dim hover:text-orange">← Back to Success Command Center</Link>
    </div>
  );
}
