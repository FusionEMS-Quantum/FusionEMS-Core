import Link from 'next/link';
import MarketingShell from '@/components/shells/MarketingShell';
import MarketingPageTemplate from '@/components/marketing/MarketingPageTemplate';

export default function FleetMarketingPage() {
  return (
    <MarketingShell>
      <MarketingPageTemplate
        eyebrow="Module · Fleet Command"
        title="Fleet Readiness, Inspection, and Maintenance in One Command Plane"
        description="Track unit readiness, enforce preventive maintenance programs, and push issues to operations before they become service disruptions."
        accent="green"
        stats={[
          { label: 'Readiness Visibility', value: 'Live', detail: 'Unit status and defect state' },
          { label: 'Inspection Cadence', value: 'Policy-driven', detail: 'Scheduled + ad-hoc checks' },
          { label: 'Maintenance Workflow', value: 'Tracked', detail: 'Queue, assign, resolve' },
          { label: 'Command Reporting', value: 'Audit-ready', detail: 'Historical serviceability trails' },
        ]}
        features={[
          { title: 'Inspection and Defect Pipelines', description: 'Capture frontline findings and route defects into structured remediation workflows.' },
          { title: 'Maintenance Prioritization', description: 'Segment safety-critical, uptime-critical, and routine service items with explicit SLA cues.' },
          { title: 'Operational Readiness Overlay', description: 'Show fleet status in operational context so dispatch and command can adapt proactively.' },
          { title: 'Fleet Portal Surface', description: 'Launch fleet tools with role-based controls and module-level observability.', href: '/portal/fleet', ctaLabel: 'Open Fleet Portal' },
        ]}
        actions={[
          { label: 'Open Fleet Portal', href: '/portal/fleet', primary: true },
          { label: 'Back to Platform', href: '/platform' },
        ]}
      >
        <div className="mt-2">
          <Link href="/scheduling" className="quantum-btn">Explore Scheduling Module</Link>
        </div>
      </MarketingPageTemplate>
    </MarketingShell>
  );
}
