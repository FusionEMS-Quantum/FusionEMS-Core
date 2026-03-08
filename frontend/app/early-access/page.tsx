import MarketingShell from '@/components/shells/MarketingShell';
import MarketingPageTemplate from '@/components/marketing/MarketingPageTemplate';

export default function EarlyAccessPage() {
  return (
    <MarketingShell>
      <MarketingPageTemplate
        eyebrow="Deployment Cohorts"
        title="Join Early Access for Billing-First FusionEMS Quantum Rollout"
        description="Enter controlled deployment cohorts designed for agencies that need measurable revenue recovery now, with a planned expansion into full command modules."
        stats={[
          { label: 'Entry Module', value: 'Billing Command', detail: 'Fastest measurable impact path' },
          { label: 'Rollout Strategy', value: 'Phased', detail: 'Revenue first, then operational modules' },
          { label: 'Implementation Support', value: 'Founder-led', detail: 'Briefing and activation sequencing' },
          { label: 'Operational Model', value: 'Multi-tenant', detail: 'Agency-isolated controls by default' },
        ]}
        features={[
          { title: 'Cohort Qualification', description: 'Assess data readiness, communication workflows, and deployment urgency before scheduling activation windows.' },
          { title: 'Revenue-First Onboarding', description: 'Stand up billing intelligence and patient communication controls first to establish immediate ROI signals.' },
          { title: 'Module Expansion Path', description: 'Sequence ePCR, fleet, scheduling, and compliance activation by agency maturity and operational pressure.' },
          { title: 'Executive Coordination', description: 'Align command staff around scope, timeline, and measurable outcomes from day one.', href: '/contact', ctaLabel: 'Talk to Founder' },
        ]}
        actions={[
          { label: 'Start Intake', href: '/signup', primary: true },
          { label: 'Talk to Founder', href: '/contact' },
          { label: 'Review Platform', href: '/platform' },
        ]}
      />
    </MarketingShell>
  );
}
