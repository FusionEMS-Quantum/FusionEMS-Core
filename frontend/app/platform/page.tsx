import Link from 'next/link';
import MarketingShell from '@/components/shells/MarketingShell';
import MarketingPageTemplate from '@/components/marketing/MarketingPageTemplate';

const modules = [
  ['Billing Command', '/billing-command'],
  ['ePCR Command', '/epcr'],
  ['Fleet Command', '/fleet'],
  ['Scheduling Command', '/scheduling'],
  ['Communications Command', '/communications'],
  ['Compliance Command', '/compliance'],
  ['Founder Command', '/founder-command'],
];

export default function PlatformPage() {
  return (
    <MarketingShell>
      <MarketingPageTemplate
        eyebrow="Platform Overview"
        title="A Unified Operating Platform Built for EMS Agency Reality"
        description="FusionEMS Quantum converges billing, clinical, fleet, scheduling, communications, compliance, and command operations into one deterministic platform surface."
        signalLine="Single platform. Explicit controls. Auditable outcomes."
        stats={[
          { label: 'Primary Domains', value: '8 modules', detail: 'Revenue to command oversight' },
          { label: 'Access Model', value: 'Role-based', detail: 'Public, portal, and internal shell separation' },
          { label: 'Deployment Style', value: 'Billing-first', detail: 'Rapid measurable financial impact' },
          { label: 'Infrastructure Bias', value: 'Sovereign-grade', detail: 'Deterministic + observable by default' },
        ]}
        features={modules.map(([label, href]) => ({
          title: label,
          description: `Explore ${label} workflows, entry points, and deployment role in the full agency operating model.`,
          href,
          ctaLabel: 'Open Module Brief',
        }))}
        actions={[
          { label: 'Open ROI Model', href: '/roi', primary: true },
          { label: 'View Architecture', href: '/architecture' },
          { label: 'Request Platform Briefing', href: '/contact' },
        ]}
      >
        <div className="border border-border-default bg-[var(--color-bg-panel)] chamfer-8 p-5 flex flex-wrap items-center justify-between gap-3">
          <div>
            <div className="text-label uppercase tracking-widest text-[var(--color-text-muted)]">Need a deployment sequence?</div>
            <p className="text-body text-[var(--color-text-secondary)] mt-1">Start with Billing Command activation and phase into full command surfaces by operational priority.</p>
          </div>
          <Link href="/early-access" className="quantum-btn-primary">Join Deployment Cohort</Link>
        </div>
      </MarketingPageTemplate>
    </MarketingShell>
  );
}
