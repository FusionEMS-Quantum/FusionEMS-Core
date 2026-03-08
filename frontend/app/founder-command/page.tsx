import Link from 'next/link';
import MarketingShell from '@/components/shells/MarketingShell';
import MarketingPageTemplate from '@/components/marketing/MarketingPageTemplate';

export default function FounderCommandPublicPage() {
  return (
    <MarketingShell>
      <MarketingPageTemplate
        eyebrow="Founder Command"
        title="Executive Control Plane Across Revenue, Operations, and Risk"
        description="Founder Command provides strategic oversight for platform health, escalation handling, deployment governance, and cross-module performance signals."
        accent="purple"
        stats={[
          { label: 'Signal Coverage', value: 'Cross-module', detail: 'Revenue, ops, compliance, and comms' },
          { label: 'Escalation Model', value: 'Deterministic', detail: 'Explicit response lanes and ownership' },
          { label: 'Decision Support', value: 'Command-grade', detail: 'Priority and risk context preserved' },
          { label: 'Governance', value: 'Audit-first', detail: 'Policy and action traceability' },
        ]}
        features={[
          { title: 'Revenue Signal Intelligence', description: 'Track collection velocity, communication outcomes, and leakage risk from one executive surface.' },
          { title: 'Operational Escalation Console', description: 'Prioritize and route incident-grade workflow exceptions with clear ownership and response clocks.' },
          { title: 'Compliance and Security Posture', description: 'View compliance drift and security posture indicators before they become operational incidents.' },
          { title: 'Command Application Entry', description: 'Launch founder-level command workflows through secure role-based access controls.', href: '/app/founder', ctaLabel: 'Open Founder Command' },
        ]}
        actions={[
          { label: 'Open Founder Command', href: '/app/founder', primary: true },
          { label: 'Back to Platform', href: '/platform' },
          { label: 'Request Executive Briefing', href: '/contact' },
        ]}
      >
        <div className="mt-2">
          <Link href="/roi" className="quantum-btn">Review Revenue Modeling</Link>
        </div>
      </MarketingPageTemplate>
    </MarketingShell>
  );
}
