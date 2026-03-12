'use client';
import { useEffect, useState } from 'react';
import Link from 'next/link';
import { motion } from 'framer-motion';
import {
  listRenewalRisks,
  listExpansionOpportunities,
  listStakeholderNotes,
  listValueMilestones,
  getExpansionReadiness,
} from '@/services/api';

interface RenewalRisk {
  id: string;
  tenant_id: string;
  signal_type: string;
  description: string;
  severity: string;
  detected_at: string;
  is_resolved: boolean;
}

interface ExpansionOpp {
  id: string;
  module_name: string;
  opportunity_type: string;
  recommended_action: string;
  evidence: Record<string, unknown>;
  estimated_value_cents: number;
  state: string;
  created_at: string;
}

interface StakeholderNote {
  id: string;
  stakeholder_name: string;
  stakeholder_role: string;
  engagement_type: string;
  content: string;
  sentiment: string | null;
  created_at: string;
}

interface ValueMilestone {
  id: string;
  milestone_name: string;
  category: string;
  description: string;
  is_achieved: boolean;
  achieved_at: string | null;
  impact_summary: string | null;
}

interface ReadinessSignal {
  id: string;
  tenant_id: string;
  module_name: string;
  readiness_score: number;
  criteria_met: Record<string, unknown>;
  recommendation: string;
  evaluated_at: string;
}

const SENTIMENT_COLOR: Record<string, string> = {
  positive: 'text-[var(--color-status-active)]',
  neutral: 'text-yellow-400',
  negative: 'text-[var(--color-brand-red)]',
};

export default function RenewalExpansionPage() {
  const [risks, setRisks] = useState<RenewalRisk[]>([]);
  const [opportunities, setOpportunities] = useState<ExpansionOpp[]>([]);
  const [notes, setNotes] = useState<StakeholderNote[]>([]);
  const [milestones, setMilestones] = useState<ValueMilestone[]>([]);
  const [readiness, setReadiness] = useState<ReadinessSignal[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    async function load() {
      try {
        const [r, o, n, m, rs] = await Promise.all([
          listRenewalRisks(),
          listExpansionOpportunities(),
          listStakeholderNotes(),
          listValueMilestones(),
          getExpansionReadiness(),
        ]);
        setRisks(r);
        setOpportunities(o);
        setNotes(n);
        setMilestones(m);
        setReadiness(rs);
      } catch (err: unknown) {
        setError(err instanceof Error ? err.message : 'Failed to load renewal data');
      } finally {
        setLoading(false);
      }
    }
    load();
  }, []);

  if (error) {
    return (
      <div className="p-5">
        <div className="bg-[var(--color-brand-red)]/10 border border-[var(--color-brand-red)]/30 p-4 text-[var(--color-brand-red)] text-sm">{error}</div>
      </div>
    );
  }

  if (loading) {
    return (
      <div className="p-5 space-y-3 animate-pulse">
        <div className="h-6 bg-[var(--color-bg-panel)]  w-1/3" />
        {Array.from({ length: 4 }).map((_, i) => (
          <div key={i} className="h-20 bg-[var(--color-bg-panel)] " />
        ))}
      </div>
    );
  }

  return (
    <div className="p-5 space-y-6">
      <div>
        <div className="text-micro font-bold uppercase tracking-[0.2em] text-[var(--q-orange)]/70 mb-1">SUCCESS · GROWTH</div>
        <h1 className="text-xl font-black uppercase tracking-wider text-[var(--color-text-primary)]">Renewal & Expansion</h1>
        <p className="text-xs text-[var(--color-text-muted)] mt-0.5">Renewal risks · expansion opportunities · stakeholders · value milestones</p>
      </div>

      {/* Renewal Risk Signals */}
      <div>
        <div className="text-micro font-bold text-[var(--q-orange)]/70 mb-2">RENEWAL RISK SIGNALS ({risks.filter((r) => !r.is_resolved).length} active)</div>
        {risks.length === 0 ? (
          <div className="bg-[var(--color-bg-panel)] border border-border-DEFAULT p-6 text-center text-[var(--color-text-muted)] text-sm">No renewal risks detected.</div>
        ) : (
          <div className="space-y-1">
            {risks.map((r, i) => (
              <motion.div key={r.id} initial={{ opacity: 0, y: 4 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: i * 0.03 }}
                className={`bg-[var(--color-bg-panel)] border p-3 ${r.is_resolved ? 'border-border-DEFAULT opacity-60' : r.severity === 'CRITICAL' ? 'border-[var(--color-brand-red)]/40' : r.severity === 'HIGH' ? 'border-orange-500/40' : 'border-yellow-500/40'}`}>
                <div className="flex items-center justify-between">
                  <div>
                    <span className="text-micro font-bold text-[var(--color-text-muted)]">{r.signal_type}</span>
                    <div className="text-sm text-[var(--color-text-primary)]">{r.description}</div>
                  </div>
                  <div className="text-right">
                    <div className={`text-micro font-bold ${r.severity === 'CRITICAL' ? 'text-[var(--color-brand-red)]' : r.severity === 'HIGH' ? 'text-[var(--q-orange)]' : 'text-yellow-400'}`}>{r.severity}</div>
                    {r.is_resolved && <div className="text-micro text-[var(--color-status-active)]">Resolved</div>}
                  </div>
                </div>
              </motion.div>
            ))}
          </div>
        )}
      </div>

      {/* Expansion Readiness */}
      <div>
        <div className="text-micro font-bold text-[var(--q-orange)]/70 mb-2">EXPANSION READINESS ({readiness.length} signals)</div>
        {readiness.length === 0 ? (
          <div className="bg-[var(--color-bg-panel)] border border-border-DEFAULT p-6 text-center text-[var(--color-text-muted)] text-sm">No expansion readiness signals.</div>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 gap-2">
            {readiness.map((s) => (
              <div key={s.id} className="bg-[var(--color-bg-panel)] border border-border-DEFAULT p-3">
                <div className="flex items-center justify-between mb-1">
                  <div className="text-sm font-bold text-[var(--color-text-primary)]">{s.module_name}</div>
                  <div className={`text-lg font-black ${s.readiness_score >= 70 ? 'text-[var(--color-status-active)]' : s.readiness_score >= 40 ? 'text-yellow-400' : 'text-[var(--color-brand-red)]'}`}>{s.readiness_score}</div>
                </div>
                <div className="text-xs text-[var(--color-text-muted)]">{s.recommendation}</div>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Expansion Opportunities */}
      <div>
        <div className="text-micro font-bold text-[var(--q-orange)]/70 mb-2">EXPANSION OPPORTUNITIES ({opportunities.length})</div>
        {opportunities.length === 0 ? (
          <div className="bg-[var(--color-bg-panel)] border border-border-DEFAULT p-6 text-center text-[var(--color-text-muted)] text-sm">No expansion opportunities identified yet.</div>
        ) : (
          <div className="space-y-1">
            {opportunities.map((o) => (
              <div key={o.id} className="bg-[var(--color-bg-panel)] border border-border-DEFAULT p-3 flex items-center justify-between">
                <div>
                  <div className="text-sm font-bold text-[var(--color-text-primary)]">{o.module_name}: {o.opportunity_type}</div>
                  <div className="text-xs text-[var(--color-text-muted)]">{o.recommended_action}</div>
                </div>
                <div className="text-right">
                  <div className="text-sm font-bold text-[var(--color-status-info)]">${(o.estimated_value_cents / 100).toLocaleString()}</div>
                  <div className={`text-micro font-bold ${o.state === 'CONVERTED' ? 'text-[var(--color-status-active)]' : o.state === 'DECLINED' ? 'text-[var(--color-brand-red)]' : 'text-yellow-400'}`}>{o.state}</div>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Value Milestones */}
      <div>
        <div className="text-micro font-bold text-[var(--q-orange)]/70 mb-2">VALUE MILESTONES</div>
        {milestones.length === 0 ? (
          <div className="bg-[var(--color-bg-panel)] border border-border-DEFAULT p-6 text-center text-[var(--color-text-muted)] text-sm">No value milestones recorded yet.</div>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 gap-2">
            {milestones.map((m) => (
              <div key={m.id} className={`bg-[var(--color-bg-panel)] border p-3 ${m.is_achieved ? 'border-green-400/30' : 'border-border-DEFAULT'}`}>
                <div className="flex items-center justify-between mb-1">
                  <div className="text-sm font-bold text-[var(--color-text-primary)]">{m.milestone_name}</div>
                  {m.is_achieved ? (
                    <span className="text-micro text-[var(--color-status-active)] font-bold">ACHIEVED</span>
                  ) : (
                    <span className="text-micro text-[var(--q-yellow)] font-bold">PENDING</span>
                  )}
                </div>
                <div className="text-xs text-[var(--color-text-muted)]">{m.description}</div>
                <div className="text-micro text-[var(--color-text-muted)] opacity-60 mt-1">{m.category}</div>
                {m.impact_summary && <div className="text-xs text-[var(--color-status-info)] mt-1">{m.impact_summary}</div>}
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Stakeholder Notes */}
      <div>
        <div className="text-micro font-bold text-[var(--q-orange)]/70 mb-2">STAKEHOLDER ENGAGEMENT ({notes.length})</div>
        {notes.length === 0 ? (
          <div className="bg-[var(--color-bg-panel)] border border-border-DEFAULT p-6 text-center text-[var(--color-text-muted)] text-sm">No stakeholder notes recorded yet.</div>
        ) : (
          <div className="space-y-1">
            {notes.slice(0, 10).map((n) => (
              <div key={n.id} className="bg-[var(--color-bg-panel)] border border-border-DEFAULT p-3">
                <div className="flex items-center justify-between text-xs mb-1">
                  <div><span className="text-[var(--color-text-primary)] font-bold">{n.stakeholder_name}</span> <span className="text-[var(--color-text-muted)]">({n.stakeholder_role})</span></div>
                  <div className="flex items-center gap-2">
                    <span className="text-[var(--color-text-muted)]">{n.engagement_type}</span>
                    {n.sentiment && <span className={`font-bold ${SENTIMENT_COLOR[n.sentiment] || 'text-[var(--color-text-muted)]'}`}>{n.sentiment}</span>}
                  </div>
                </div>
                <div className="text-xs text-[var(--color-text-muted)]">{n.content}</div>
              </div>
            ))}
          </div>
        )}
      </div>

      <Link href="/founder/success-command" className="text-xs text-[var(--q-orange)]/70 hover:text-[var(--q-orange)]">← Back to Success Command Center</Link>
    </div>
  );
}
