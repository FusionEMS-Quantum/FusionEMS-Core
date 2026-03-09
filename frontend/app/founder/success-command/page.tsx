'use client';
import { useEffect, useState } from 'react';
import Link from 'next/link';
import { motion } from 'framer-motion';
import { getFounderSuccessSummary, getImplementationHealth, getSupportQueueHealth, getTrainingCompletion } from '@/services/api';
import { SeverityBadge } from '@/components/ui';
import { normalizeSeverity } from '@/lib/design-system/severity';

interface SuccessAction {
  domain: string;
  severity: string;
  summary: string;
  recommended_action: string;
  entity_id: string;
}

interface SuccessSummary {
  stalled_implementations: number;
  high_severity_tickets: number;
  at_risk_accounts: number;
  training_gaps: number;
  low_adoption_modules: number;
  expansion_ready_signals: number;
  top_actions: SuccessAction[];
}

interface HealthScore {
  total_projects: number;
  on_track_pct: number;
  at_risk_pct: number;
  avg_milestone_completion_pct: number;
}

interface QueueHealth {
  total_open: number;
  critical_count: number;
  high_count: number;
  avg_age_hours: number;
  sla_breach_count: number;
}

interface TrainingSummary {
  total_assignments: number;
  completed_pct: number;
  overdue_count: number;
  verified_count: number;
}

function severityPanelClass(rawSeverity: string): string {
  switch (normalizeSeverity(rawSeverity)) {
    case 'BLOCKING':
      return 'text-red-400 bg-red-400/10 border-red-400/30';
    case 'HIGH':
      return 'text-[#FF4D00] bg-[rgba(255,77,0,0.1)] border-orange-400/30';
    case 'MEDIUM':
      return 'text-yellow-400 bg-yellow-400/10 border-yellow-400/30';
    case 'LOW':
      return 'text-sky-400 bg-sky-400/10 border-sky-400/30';
    default:
      return 'text-zinc-500 bg-zinc-500/10 border-zinc-500/30';
  }
}

export default function SuccessCommandPage() {
  const [summary, setSummary] = useState<SuccessSummary | null>(null);
  const [implHealth, setImplHealth] = useState<HealthScore | null>(null);
  const [queueHealth, setQueueHealth] = useState<QueueHealth | null>(null);
  const [training, setTraining] = useState<TrainingSummary | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    async function load() {
      try {
        const [s, ih, qh, t] = await Promise.all([
          getFounderSuccessSummary(),
          getImplementationHealth(),
          getSupportQueueHealth(),
          getTrainingCompletion(),
        ]);
        setSummary(s);
        setImplHealth(ih);
        setQueueHealth(qh);
        setTraining(t);
      } catch (err: unknown) {
        setError(err instanceof Error ? err.message : 'Failed to load success data');
      } finally {
        setLoading(false);
      }
    }
    load();
  }, []);

  if (loading) {
    return (
      <div className="p-5 space-y-4 animate-pulse">
        <div className="h-6 bg-[#0A0A0B]  w-1/3" />
        <div className="grid grid-cols-3 gap-3">
          {Array.from({ length: 6 }).map((_, i) => (
            <div key={i} className="h-20 bg-[#0A0A0B] " />
          ))}
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="p-5">
        <div className="bg-red-500/10 border border-red-500/30 p-4 text-red-400 text-sm">{error}</div>
      </div>
    );
  }

  const KPI_CARDS = [
    { label: 'Stalled Implementations', value: summary?.stalled_implementations ?? (() => { throw new Error('Unsafe silent fallback. Dependency missing.'); })(), color: summary?.stalled_implementations ? 'text-red-400' : 'text-green-400', link: '/founder/success-command/implementations' },
    { label: 'High-Severity Tickets', value: summary?.high_severity_tickets ?? (() => { throw new Error('Unsafe silent fallback. Dependency missing.'); })(), color: summary?.high_severity_tickets ? 'text-red-400' : 'text-green-400', link: '/founder/success-command/support' },
    { label: 'At-Risk Accounts', value: summary?.at_risk_accounts ?? (() => { throw new Error('Unsafe silent fallback. Dependency missing.'); })(), color: summary?.at_risk_accounts ? 'text-[#FF4D00]' : 'text-green-400', link: '#' },
    { label: 'Training Gaps', value: summary?.training_gaps ?? (() => { throw new Error('Unsafe silent fallback. Dependency missing.'); })(), color: summary?.training_gaps ? 'text-yellow-400' : 'text-green-400', link: '/founder/success-command/training' },
    { label: 'Low Adoption Modules', value: summary?.low_adoption_modules ?? (() => { throw new Error('Unsafe silent fallback. Dependency missing.'); })(), color: summary?.low_adoption_modules ? 'text-yellow-400' : 'text-green-400', link: '/founder/success-command/adoption' },
    { label: 'Expansion Ready', value: summary?.expansion_ready_signals ?? (() => { throw new Error('Unsafe silent fallback. Dependency missing.'); })(), color: 'text-cyan-400', link: '/founder/success-command/renewal' },
  ];

  return (
    <div className="p-5 space-y-6">
      {/* Header */}
      <div>
        <div className="text-micro font-bold uppercase tracking-[0.2em] text-[#FF4D00]/70 mb-1">FOUNDER · SUCCESS</div>
        <h1 className="text-xl font-black uppercase tracking-wider text-zinc-100">Success Command Center</h1>
        <p className="text-xs text-zinc-500 mt-0.5">Implementation · Support · Training · Adoption · Expansion</p>
      </div>

      {/* KPI Cards */}
      <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-3">
        {KPI_CARDS.map((kpi, i) => (
          <motion.div key={kpi.label} initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: i * 0.05 }}>
            <Link href={kpi.link} className="block bg-[#0A0A0B] border border-border-DEFAULT p-4 hover:border-white/[0.18] transition-colors">
              <div className={`text-2xl font-black ${kpi.color}`}>{kpi.value}</div>
              <div className="text-micro text-zinc-500 mt-1">{kpi.label}</div>
            </Link>
          </motion.div>
        ))}
      </div>

      {/* Health Bands */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
        {implHealth && (
          <div className="bg-[#0A0A0B] border border-border-DEFAULT p-4">
            <div className="text-micro font-bold text-[#FF4D00]/70 mb-2">IMPLEMENTATION HEALTH</div>
            <div className="space-y-1 text-xs text-zinc-500">
              <div className="flex justify-between"><span>Total Projects</span><span className="text-zinc-100 font-bold">{implHealth.total_projects}</span></div>
              <div className="flex justify-between"><span>On Track</span><span className="text-green-400 font-bold">{implHealth.on_track_pct.toFixed(0)}%</span></div>
              <div className="flex justify-between"><span>At Risk</span><span className="text-red-400 font-bold">{implHealth.at_risk_pct.toFixed(0)}%</span></div>
              <div className="flex justify-between"><span>Avg Milestone</span><span className="text-zinc-100 font-bold">{implHealth.avg_milestone_completion_pct.toFixed(0)}%</span></div>
            </div>
          </div>
        )}
        {queueHealth && (
          <div className="bg-[#0A0A0B] border border-border-DEFAULT p-4">
            <div className="text-micro font-bold text-[#FF4D00]/70 mb-2">SUPPORT QUEUE HEALTH</div>
            <div className="space-y-1 text-xs text-zinc-500">
              <div className="flex justify-between"><span>Total Open</span><span className="text-zinc-100 font-bold">{queueHealth.total_open}</span></div>
              <div className="flex justify-between"><span>Critical</span><span className="text-red-400 font-bold">{queueHealth.critical_count}</span></div>
              <div className="flex justify-between"><span>High</span><span className="text-[#FF4D00] font-bold">{queueHealth.high_count}</span></div>
              <div className="flex justify-between"><span>SLA Breaches</span><span className={queueHealth.sla_breach_count > 0 ? 'text-red-400 font-bold' : 'text-green-400 font-bold'}>{queueHealth.sla_breach_count}</span></div>
            </div>
          </div>
        )}
        {training && (
          <div className="bg-[#0A0A0B] border border-border-DEFAULT p-4">
            <div className="text-micro font-bold text-[#FF4D00]/70 mb-2">TRAINING COMPLETION</div>
            <div className="space-y-1 text-xs text-zinc-500">
              <div className="flex justify-between"><span>Total Assignments</span><span className="text-zinc-100 font-bold">{training.total_assignments}</span></div>
              <div className="flex justify-between"><span>Completed</span><span className="text-green-400 font-bold">{training.completed_pct.toFixed(0)}%</span></div>
              <div className="flex justify-between"><span>Overdue</span><span className={training.overdue_count > 0 ? 'text-red-400 font-bold' : 'text-green-400 font-bold'}>{training.overdue_count}</span></div>
              <div className="flex justify-between"><span>Verified</span><span className="text-cyan-400 font-bold">{training.verified_count}</span></div>
            </div>
          </div>
        )}
      </div>

      {/* Top Actions */}
      {summary?.top_actions && summary.top_actions.length > 0 && (
        <div>
          <div className="text-micro font-bold text-[#FF4D00]/70 mb-2">TOP ACTIONS</div>
          <div className="space-y-2">
            {summary.top_actions.map((action, i) => (
              <motion.div key={i} initial={{ opacity: 0, x: -8 }} animate={{ opacity: 1, x: 0 }} transition={{ delay: 0.3 + i * 0.1 }}
                className={`border p-3 ${severityPanelClass(action.severity)}`}>
                <div className="flex items-center gap-2 mb-1">
                  <span className="text-micro font-bold uppercase">{action.domain}</span>
                  <SeverityBadge
                    severity={normalizeSeverity(action.severity)}
                    size="sm"
                    label={normalizeSeverity(action.severity)}
                  />
                </div>
                <div className="text-sm text-zinc-100">{action.summary}</div>
                <div className="text-xs text-zinc-500 mt-1">{action.recommended_action}</div>
              </motion.div>
            ))}
          </div>
        </div>
      )}

      {/* Navigation Links */}
      <div className="grid grid-cols-2 md:grid-cols-3 gap-3">
        {[
          { href: '/founder/success-command/implementations', label: 'Implementation Services', desc: 'Project plans · milestones · go-live approvals' },
          { href: '/founder/success-command/support', label: 'Support Operations', desc: 'Ticket queue · SLA tracking · escalations' },
          { href: '/founder/success-command/training', label: 'Training & Enablement', desc: 'Tracks · assignments · completions · verifications' },
          { href: '/founder/success-command/adoption', label: 'Adoption & Health', desc: 'Module adoption · account health · risk factors' },
          { href: '/founder/success-command/renewal', label: 'Renewal & Expansion', desc: 'Renewal risk · expansion opportunities · stakeholders' },
        ].map((l) => (
          <Link key={l.href} href={l.href} className="block bg-[#0A0A0B] border border-border-DEFAULT p-4 hover:border-white/[0.18] transition-colors">
            <div className="text-sm font-bold text-[#FF4D00]/70 mb-1">{l.label}</div>
            <div className="text-xs text-zinc-500">{l.desc}</div>
          </Link>
        ))}
      </div>

      <Link href="/founder" className="text-xs text-[#FF4D00]/70 hover:text-[#FF4D00]">← Back to Founder Command OS</Link>
    </div>
  );
}
