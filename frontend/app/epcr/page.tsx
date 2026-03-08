import Link from 'next/link';
import MarketingShell from '@/components/shells/MarketingShell';
import MarketingPageTemplate from '@/components/marketing/MarketingPageTemplate';

export default function EpcrMarketingPage() {
  return (
    <MarketingShell>
      <MarketingPageTemplate
        eyebrow="Module · ePCR Command"
        title="Clinical Documentation That Produces Clean, Billable Records Faster"
        description="Drive chart completion quality with narrative support, QA review controls, and deterministic export readiness for NEMSIS-aligned reporting flows."
        accent="blue"
        stats={[
          { label: 'Chart Throughput', value: 'Accelerated', detail: 'Lower time-to-finalization' },
          { label: 'Data Quality', value: 'Schema-aware', detail: 'Required-field validation lanes' },
          { label: 'Billing Alignment', value: 'Integrated', detail: 'Clinical-to-claim continuity' },
          { label: 'Auditability', value: 'End-to-end', detail: 'Review trail preserved' },
        ]}
        features={[
          { title: 'Narrative and QA Workbench', description: 'Structure narratives, identify quality gaps early, and route records through explicit review queues.' },
          { title: 'Export and Compliance Guardrails', description: 'Maintain conformance on data payloads before external submission and reporting handoff.' },
          { title: 'Role-Based Clinical Views', description: 'Separate crew, supervisor, and command workflows without fragmenting chart state.', href: '/portal/epcr', ctaLabel: 'Open ePCR Portal' },
          { title: 'Revenue Continuity Inputs', description: 'Capture billing-critical documentation fields directly in clinical workflows to reduce downstream denial risk.' },
        ]}
        actions={[
          { label: 'Open ePCR Portal', href: '/portal/epcr', primary: true },
          { label: 'Back to Platform', href: '/platform' },
        ]}
      >
        <div className="mt-2">
          <Link href="/compliance" className="quantum-btn">View Compliance Command</Link>
        </div>
      </MarketingPageTemplate>
    </MarketingShell>
  );
}
