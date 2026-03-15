import Link from 'next/link';
import MarketingShell from '@/components/shells/MarketingShell';
import MarketingPageTemplate from '@/components/marketing/MarketingPageTemplate';

export default function ContactPage() {
  return (
    <MarketingShell>
      <MarketingPageTemplate
        eyebrow="Executive Platform Briefing"
        title="Request an Executive Platform Session"
        description="For agencies, regional systems, and implementation partners evaluating FusionEMS Quantum with strict reliability, security, and deployment requirements."
        stats={[
          { label: 'Audience', value: 'Executive + Ops', detail: 'Finance, clinical, and command stakeholders' },
          { label: 'Focus', value: 'Deployment-grade', detail: 'No demo-grade assumptions' },
          { label: 'Primary Outcome', value: 'Action plan', detail: 'Route architecture + rollout sequence' },
          { label: 'Coordination', value: 'Architecture team', detail: 'Technical and strategic alignment' },
        ]}
        features={[
          { title: 'Architecture and Risk Review', description: 'Walk through current-state tool fragmentation, risk points, and proposed target platform state.' },
          { title: 'Billing and Revenue Strategy', description: 'Define billing-first execution with communication orchestration and deterministic KPI baselines.' },
          { title: 'Operational Module Sequencing', description: 'Prioritize ePCR, scheduling, fleet, and compliance activations by agency readiness and incident profile.' },
          { title: 'Secure Engagement Workflow', description: 'Use structured support workflows for follow-ups, documentation exchange, and next-step approvals.', href: '/portal/support', ctaLabel: 'Open Contact Workflow' },
        ]}
        actions={[
          { label: 'Open Contact Workflow', href: '/portal/support', primary: true },
          { label: 'View Platform', href: '/platform' },
          { label: 'Model ROI First', href: '/roi' },
        ]}
      >
        <div className="mt-2">
          <Link href="/early-access" className="quantum-btn">Join Early Access Cohort</Link>
        </div>
      </MarketingPageTemplate>
    </MarketingShell>
  );
}
