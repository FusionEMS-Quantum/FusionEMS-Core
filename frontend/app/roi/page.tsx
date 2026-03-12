import Link from 'next/link';
import MarketingShell from '@/components/shells/MarketingShell';
import MarketingPageTemplate from '@/components/marketing/MarketingPageTemplate';

export default function PublicRoiPage() {
  return (
    <MarketingShell>
      <MarketingPageTemplate
        eyebrow="Public ROI Intelligence"
        title="Model Recoverable Revenue Before You Commit to Rollout"
        description="Use FusionEMS Quantum ROI intelligence to baseline private-pay leakage, project cash recovery, and define a deterministic billing-first deployment path."
        signalLine="Revenue lift assumptions are explicit, reviewable, and exportable for executive sign-off."
        stats={[
          { label: 'Modeled Collection Lift', value: '8–28%', detail: 'Based on workflow friction reduction' },
          { label: 'Activation Horizon', value: '30–60 days', detail: 'Billing-first implementation lanes' },
          { label: 'Conversion Visibility', value: 'End-to-end', detail: 'Lead → proposal → payment traceability' },
          { label: 'Security Posture', value: 'HIPAA-aware', detail: 'Tenant and access boundaries enforced' },
        ]}
        features={[
          {
            title: 'Recovery Scenario Builder',
            description: 'Run transport volume, payer-mix, and collection-rate scenarios with explicit assumptions and bounded variance.',
            href: '/roi-funnel',
            ctaLabel: 'Open ROI Calculator',
          },
          {
            title: 'Deployment Fit Scoring',
            description: 'Map agency readiness across communications, billing controls, and staffing before activation windows are committed.',
          },
          {
            title: 'Executive Briefing Outputs',
            description: 'Generate stakeholder-ready summaries for finance, operations, and implementation leadership.',
            href: '/contact',
            ctaLabel: 'Request Briefing',
          },
          {
            title: 'Onboarding Conversion Path',
            description: 'Transition from ROI modeling into controlled intake and phased deployment without route fragmentation.',
            href: '/signup',
            ctaLabel: 'Start Intake',
          },
        ]}
        actions={[
          { label: 'Open ROI Calculator', href: '/roi-funnel', primary: true },
          { label: 'Request Early Access', href: '/early-access' },
          { label: 'Talk to Founder', href: '/contact' },
        ]}
      >
        <div className="border border-border-default bg-[var(--color-bg-panel)] chamfer-8 p-5">
          <div className="text-label uppercase tracking-widest text-[var(--color-text-muted)]">Need implementation guidance first?</div>
          <p className="text-body text-[var(--color-text-secondary)] mt-2 max-w-3xl">
            Start with an executive assessment and we will sequence Billing Command activation, patient communication lanes,
            and command portal onboarding in a single deterministic rollout plan.
          </p>
          <div className="mt-4">
            <Link href="/platform" className="quantum-btn">Review Platform Architecture</Link>
          </div>
        </div>
      </MarketingPageTemplate>
    </MarketingShell>
  );
}
