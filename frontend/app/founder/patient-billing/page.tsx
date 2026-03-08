'use client';

import Link from 'next/link';
import { NextBestActionCard, type NextAction } from '@/components/ui/NextBestActionCard';
import { SeverityBadge } from '@/components/ui/SeverityBadge';
import { DomainNavCard, FounderStatusBar } from '@/components/shells/FounderCommand';

const COMMAND_ACTIONS: NextAction[] = [
  {
    id: 'patient-billing-balance-risk',
    title: 'Review patient balance concentration and collections readiness',
    severity: 'HIGH',
    domain: 'Patient Billing',
    href: '/founder/revenue/billing-intelligence',
  },
  {
    id: 'patient-billing-payment-recovery',
    title: 'Recover expired payment-link and callback-required accounts',
    severity: 'MEDIUM',
    domain: 'Payment Recovery',
    href: '/founder/ops/transportlink/transport-billing-payment',
  },
  {
    id: 'patient-billing-comms-sync',
    title: 'Verify communications coverage for unresolved billing conversations',
    severity: 'MEDIUM',
    domain: 'Comms Command',
    href: '/founder/comms/inbox',
  },
  {
    id: 'patient-billing-patient-trust',
    title: 'Audit patient-facing portal clarity and support routing',
    severity: 'LOW',
    domain: 'Patient Portal',
    href: '/patient-billing-login',
  },
];

const ROUTES = [
  {
    href: '/founder/revenue/billing-intelligence',
    title: 'Billing Intelligence',
    desc: 'Denials, payer risk, patient balances, and revenue leakage telemetry.',
    color: 'var(--color-system-billing)',
    tag: 'Revenue',
  },
  {
    href: '/billing-command',
    title: 'Billing Command Center',
    desc: 'Executive billing command with denials, AR concentration, and alerts.',
    color: 'var(--color-status-info)',
    tag: 'Command',
  },
  {
    href: '/founder/ops/transportlink/transport-billing-payment',
    title: 'Transport Billing Payment',
    desc: 'TransportLink payment orchestration and settlement workflows.',
    color: 'var(--q-yellow)',
    tag: 'Operations',
  },
  {
    href: '/founder/comms/inbox',
    title: 'Communications Inbox',
    desc: 'Unified patient/SMS/voice threads linked to billing workflows.',
    color: 'var(--q-green)',
    tag: 'Comms',
  },
  {
    href: '/patient-billing-login',
    title: 'Patient Billing Portal Entry',
    desc: 'Public patient billing experience for statement and payment access.',
    color: '#FF4D00',
    tag: 'Portal',
  },
  {
    href: '/founder/legal-requests',
    title: 'Legal Requests Command',
    desc: 'Legal payment-required requests and secure release chain controls.',
    color: 'var(--color-brand-red)',
    tag: 'Legal',
  },
] as const;

export default function FounderPatientBillingCommandPage() {
  return (
    <div className="p-5 space-y-6">
      <FounderStatusBar isLive activeIncidents={0} />

      <div>
        <div className="text-micro font-bold uppercase tracking-[0.2em] text-orange-dim mb-1">DOMAIN 2C · PATIENT BILLING COMMAND</div>
        <h1 className="text-xl font-black uppercase tracking-wider text-zinc-100">Patient Billing Command</h1>
        <p className="text-xs text-zinc-500 mt-0.5">Balances · payment orchestration · support linkage · trust posture</p>
        <div className="mt-3 flex flex-wrap gap-2">
          <SeverityBadge severity="HIGH" size="sm" />
          <SeverityBadge severity="MEDIUM" size="sm" label="Patient Trust Sensitive" />
        </div>
      </div>

      <NextBestActionCard actions={COMMAND_ACTIONS} title="Patient Billing Next Best Actions" maxVisible={4} />

      <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
        <DomainNavCard
          domain="billing"
          href="/founder/revenue/billing-intelligence"
          description="Anchor patient billing decisions in live billing command telemetry."
        />
        <DomainNavCard
          domain="support"
          href="/founder/comms/inbox"
          description="Escalate unresolved patient interactions from one communications queue."
        />
        <DomainNavCard
          domain="ops"
          href="/founder/ops/transportlink/transport-billing-payment"
          description="Coordinate payment operations with transport workflow execution."
        />
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3">
        {ROUTES.map((route) => (
          <Link
            key={route.href}
            href={route.href}
            className="bg-[#0A0A0B] border border-border-DEFAULT p-4 hover:border-brand-orange/[0.3] transition-colors"
            style={{ clipPath: 'polygon(0 0, calc(100% - 10px) 0, 100% 10px, 100% 100%, 0 100%)' }}
          >
            <div className="text-micro uppercase tracking-wider font-semibold mb-1" style={{ color: route.color }}>{route.tag}</div>
            <div className="text-sm font-bold text-zinc-100 mb-1">{route.title}</div>
            <div className="text-xs text-zinc-500">{route.desc}</div>
          </Link>
        ))}
      </div>
    </div>
  );
}
