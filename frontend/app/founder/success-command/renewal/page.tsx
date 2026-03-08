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
  positive: 'text-green-400',
  neutral: 'text-yellow-400',
  negative: 'text-red-400',
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
        <div className="bg-red-500/10 border border-red-500/30 p-4 text-red-400 text-sm">{error}</div>
      </div>
    );
  }

  if (loading) {
    return (
      <div className="p-5 space-y-3 animate-pulse">
        <div className="h-6 bg-[#0A0A0B]  w-1/3" />
        {Array.from({ length: 4 }).map((_, i) => (
          <div key={i} className="h-20 bg-[#0A0A0B] " />
        ))}
      </div>
    );
  }

  return (
    <div className="p-5 space-y-6">
      <div>
        <div className="text-micro font-bold uppercase tracking-[0.2em] text-[#FF4D00]/70 mb-1">SUCCESS · GROWTH</div>
        <h1 className="text-xl font-black uppercase tracking-wider text-zinc-100">Renewal & Expansion</h1>
        <p className="text-xs text-zinc-500 mt-0.5">Renewal risks · expansion opportunities · stakeholders · value milestones</p>
      </div>

      {/* Renewal Risk Signals */}
      <div>
        <div className="text-micro font-bold text-[#FF4D00]/70 mb-2">RENEWAL RISK SIGNALS ({risks.filter((r) => !r.is_resolved).length} active)</div>
        {risks.length === 0 ? (
          <div className="bg-[#0A0A0B] border border-border-DEFAULT p-6 text-center text-zinc-500 text-sm">No renewal risks detected.</div>
        ) : (
          <div className="space-y-1">
            {risks.map((r, i) => (
              <motion.div key={r.id} initial={{ opacity: 0, y: 4 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: i * 0.03 }}
                className={`bg-[#0A0A0B] border p-3 ${r.is_resolved ? 'border-border-DEFAULT opacity-60' : r.severity === 'CRITICAL' ? 'border-red-500/40' : r.severity === 'HIGH' ? 'border-orange-500/40' : 'border-yellow-500/40'}`}>
                <div className="flex items-center justify-between">
                  <div>
                    <span className="text-micro font-bold text-zinc-500">{r.signal_type}</span>
                    <div className="text-sm text-zinc-100">{r.description}</div>
                  </div>
                  <div className="text-right">
                    <div className={`text-micro font-bold ${r.severity === 'CRITICAL' ? 'text-red-400' : r.severity === 'HIGH' ? 'text-[#FF4D00]' : 'text-yellow-400'}`}>{r.severity}</div>
                    {r.is_resolved && <div className="text-micro text-green-400">Resolved</div>}
                  </div>
                </div>
              </motion.div>
            ))}
          </div>
        )}
      </div>

      {/* Expansion Readiness */}
      <div>
        <div className="text-micro font-bold text-[#FF4D00]/70 mb-2">EXPANSION READINESS ({readiness.length} signals)</div>
        {readiness.length === 0 ? (
          <div className="bg-[#0A0A0B] border border-border-DEFAULT p-6 text-center text-zinc-500 text-sm">No expansion readiness signals.</div>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 gap-2">
            {readiness.map((s) => (
              <div key={s.id} className="bg-[#0A0A0B] border border-border-DEFAULT p-3">
                <div className="flex items-center justify-between mb-1">
                  <div className="text-sm font-bold text-zinc-100">{s.module_name}</div>
                  <div className={`text-lg font-black ${s.readiness_score >= 70 ? 'text-green-400' : s.readiness_score >= 40 ? 'text-yellow-400' : 'text-red-400'}`}>{s.readiness_score}</div>
                </div>
                <div className="text-xs text-zinc-500">{s.recommendation}</div>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Expansion Opportunities */}
      <div>
        <div className="text-micro font-bold text-[#FF4D00]/70 mb-2">EXPANSION OPPORTUNITIES ({opportunities.length})</div>
        {opportunities.length === 0 ? (
          <div className="bg-[#0A0A0B] border border-border-DEFAULT p-6 text-center text-zinc-500 text-sm">No expansion opportunities identified yet.</div>
        ) : (
          <div className="space-y-1">
            {opportunities.map((o) => (
              <div key={o.id} className="bg-[#0A0A0B] border border-border-DEFAULT p-3 flex items-center justify-between">
                <div>
                  <div className="text-sm font-bold text-zinc-100">{o.module_name}: {o.opportunity_type}</div>
                  <div className="text-xs text-zinc-500">{o.recommended_action}</div>
                </div>
                <div className="text-right">
                  <div className="text-sm font-bold text-cyan-400">${(o.estimated_value_cents / 100).toLocaleString()}</div>
                  <div className={`text-micro font-bold ${o.state === 'CONVERTED' ? 'text-green-400' : o.state === 'DECLINED' ? 'text-red-400' : 'text-yellow-400'}`}>{o.state}</div>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Value Milestones */}
      <div>
        <div className="text-micro font-bold text-[#FF4D00]/70 mb-2">VALUE MILESTONES</div>
        {milestones.length === 0 ? (
          <div className="bg-[#0A0A0B] border border-border-DEFAULT p-6 text-center text-zinc-500 text-sm">No value milestones recorded yet.</div>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 gap-2">
            {milestones.map((m) => (
              <div key={m.id} className={`bg-[#0A0A0B] border p-3 ${m.is_achieved ? 'border-green-400/30' : 'border-border-DEFAULT'}`}>
                <div className="flex items-center justify-between mb-1">
                  <div className="text-sm font-bold text-zinc-100">{m.milestone_name}</div>
                  {m.is_achieved ? (
                    <span className="text-micro text-green-400 font-bold">ACHIEVED</span>
                  ) : (
                    <span className="text-micro text-yellow-400 font-bold">PENDING</span>
                  )}
                </div>
                <div className="text-xs text-zinc-500">{m.description}</div>
                <div className="text-micro text-zinc-500 opacity-60 mt-1">{m.category}</div>
                {m.impact_summary && <div className="text-xs text-cyan-400 mt-1">{m.impact_summary}</div>}
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Stakeholder Notes */}
      <div>
        <div className="text-micro font-bold text-[#FF4D00]/70 mb-2">STAKEHOLDER ENGAGEMENT ({notes.length})</div>
        {notes.length === 0 ? (
          <div className="bg-[#0A0A0B] border border-border-DEFAULT p-6 text-center text-zinc-500 text-sm">No stakeholder notes recorded yet.</div>
        ) : (
          <div className="space-y-1">
            {notes.slice(0, 10).map((n) => (
              <div key={n.id} className="bg-[#0A0A0B] border border-border-DEFAULT p-3">
                <div className="flex items-center justify-between text-xs mb-1">
                  <div><span className="text-zinc-100 font-bold">{n.stakeholder_name}</span> <span className="text-zinc-500">({n.stakeholder_role})</span></div>
                  <div className="flex items-center gap-2">
                    <span className="text-zinc-500">{n.engagement_type}</span>
                    {n.sentiment && <span className={`font-bold ${SENTIMENT_COLOR[n.sentiment] || 'text-zinc-500'}`}>{n.sentiment}</span>}
                  </div>
                </div>
                <div className="text-xs text-zinc-500">{n.content}</div>
              </div>
            ))}
          </div>
        )}
      </div>

      <Link href="/founder/success-command" className="text-xs text-[#FF4D00]/70 hover:text-[#FF4D00]">← Back to Success Command Center</Link>
    </div>
  );
}
