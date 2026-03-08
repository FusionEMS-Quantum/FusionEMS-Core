import MarketingShell from '@/components/shells/MarketingShell';
import MarketingPageTemplate from '@/components/marketing/MarketingPageTemplate';

export default function SchedulingMarketingPage() {
  return (
    <MarketingShell>
      <MarketingPageTemplate
        eyebrow="Module · Scheduling Command"
        title="Coverage Planning and Workforce Readiness for Real Incident Tempo"
        description="Coordinate shifts, qualifications, and approvals with deterministic transition states so staffing risk is visible before it impacts response."
        accent="purple"
        stats={[
          { label: 'Coverage Forecasting', value: 'Shift-level', detail: 'Gap and surge visibility' },
          { label: 'Credential Awareness', value: 'Integrated', detail: 'Qualification-aware assignment' },
          { label: 'Approval Chain', value: 'Deterministic', detail: 'No silent schedule changes' },
          { label: 'Command Escalation', value: 'Built-in', detail: 'Ops receives staffing risk signals' },
        ]}
        features={[
          { title: 'Roster Intelligence', description: 'Detect undercoverage, overlap inefficiency, and certification mismatch before shift lock.' },
          { title: 'Policy-Driven Scheduling', description: 'Apply explicit labor and readiness constraints through transparent, auditable rules.' },
          { title: 'Transport and Facility Coordination', description: 'Bridge scheduling with interfacility and assisted-living transport workflows.' },
          { title: 'Scheduling Portal Surface', description: 'Launch role-specific scheduling actions through secure command entry.', href: '/portal/scheduling', ctaLabel: 'Open Scheduling Portal' },
        ]}
        actions={[
          { label: 'Open Scheduling Portal', href: '/portal/scheduling', primary: true },
          { label: 'Back to Platform', href: '/platform' },
        ]}
      />
    </MarketingShell>
  );
}
