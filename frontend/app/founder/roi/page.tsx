'use client';

import Link from 'next/link';
import { motion } from 'framer-motion';
import { NextBestActionCard, type NextAction } from '@/components/ui/NextBestActionCard';
import { SeverityBadge } from '@/components/ui/SeverityBadge';
import { DomainNavCard, FounderStatusBar } from '@/components/shells/FounderCommand';

const LINKS = [
  { href: '/founder/roi/analytics', label: 'ROI Analytics', desc: 'MRR, ARR, agency breakdown, payer mix, churn risk', color: 'var(--q-yellow)' },
  { href: '/founder/roi/funnel', label: 'Funnel Dashboard', desc: 'Lead pipeline, conversion rates, deal velocity', color: 'var(--q-yellow)' },
  { href: '/founder/roi/pricing-simulator', label: 'Pricing Simulator', desc: 'Compare FusionEMS vs % billing model ROI', color: 'var(--q-yellow)' },
  { href: '/founder/roi/proposals', label: 'Proposal Tracker', desc: 'Track sent proposals, follow-ups, acceptance rate', color: 'var(--q-yellow)' },
];

export default function ROIPage() {
  const roiActions: NextAction[] = [
    {
      id: 'roi-analytics-review',
      title: 'Review ROI analytics for conversion and margin drift',
      severity: 'MEDIUM',
      domain: 'ROI Analytics',
      href: '/founder/roi/analytics',
    },
    {
      id: 'roi-funnel-followup',
      title: 'Prioritize high-probability funnel opportunities',
      severity: 'HIGH',
      domain: 'Sales Funnel',
      href: '/founder/roi/funnel',
    },
    {
      id: 'roi-pricing-validate',
      title: 'Validate pricing scenarios against current payer mix assumptions',
      severity: 'MEDIUM',
      domain: 'Pricing Simulator',
      href: '/founder/roi/pricing-simulator',
    },
    {
      id: 'roi-proposal-close',
      title: 'Advance proposal follow-ups to closure or explicit deferral',
      severity: 'HIGH',
      domain: 'Proposal Tracker',
      href: '/founder/roi/proposals',
    },
  ];

  return (
    <div className="p-5 space-y-6">
      <FounderStatusBar isLive activeIncidents={0} />

      <div>
        <div className="text-micro font-bold uppercase tracking-[0.2em] text-[var(--q-orange)]/70 mb-1">DOMAIN 8 · ROI & SALES</div>
        <h1 className="text-xl font-black uppercase tracking-wider text-[var(--color-text-primary)]">ROI & Sales</h1>
        <p className="text-xs text-[var(--color-text-muted)] mt-0.5">Pipeline · simulator · proposals · analytics</p>
        <div className="mt-3 flex flex-wrap items-center gap-2">
          <SeverityBadge severity="HIGH" size="sm" />
          <SeverityBadge severity="MEDIUM" size="sm" label="Assumption Sensitive" />
        </div>
      </div>

      <NextBestActionCard actions={roiActions} title="ROI Command Next Best Actions" maxVisible={4} />

      <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
        <DomainNavCard
          domain="billing"
          href="/founder/revenue/billing-intelligence"
          description="Connect ROI assumptions directly to live claims and collections posture."
        />
        <DomainNavCard
          domain="ops"
          href="/founder/ops/command"
          description="Tie conversion and growth plans to operational capacity and risk."
        />
        <DomainNavCard
          domain="ai"
          href="/founder/ai/review-queue"
          description="Use AI review surfaces for faster strategic follow-up decisions."
        />
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
        {LINKS.map((l) => (
          <motion.div key={l.href} initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }}>
            <Link href={l.href} className="block bg-[var(--color-bg-panel)] border border-border-DEFAULT p-5 hover:border-white/[0.18] transition-colors" style={{ clipPath: 'polygon(0 0, calc(100% - 10px) 0, 100% 10px, 100% 100%, 0 100%)' }}>
              <div className="text-sm font-bold mb-1" style={{ color: l.color }}>{l.label}</div>
              <div className="text-xs text-[var(--color-text-muted)]">{l.desc}</div>
            </Link>
          </motion.div>
        ))}
      </div>
      <Link href="/founder" className="text-xs text-[var(--q-orange)]/70 hover:text-[var(--q-orange)]">← Back to Founder Command OS</Link>
    </div>
  );
}
