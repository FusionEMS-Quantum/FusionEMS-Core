import MarketingShell from '@/components/shells/MarketingShell';
import MarketingPageTemplate from '@/components/marketing/MarketingPageTemplate';

const LAYERS = [
  {
    title: 'Edge and Access Boundary',
    description: 'Amplify Hosting + WAF perimeter with strict ingress policy and route segmentation between public, access, and internal surfaces.',
  },
  {
    title: 'Application Runtime',
    description: 'Amplify-hosted frontend with scalable API, worker, and real-time workloads and deterministic health behavior.',
  },
  {
    title: 'Authoritative Data Plane',
    description: 'PostgreSQL-backed source of truth with transactional integrity, audit trails, and encrypted document/object storage boundaries.',
  },
  {
    title: 'Observability and Security Layer',
    description: 'Structured logs, policy enforcement, traceability, and explicit security controls across all service edges.',
  },
] as const;

const SECURITY_CONTROLS = [
  'Encryption at rest and in transit',
  'OIDC and role-based access enforcement',
  'WAF-protected public endpoints',
  'Tenant isolation with deny-by-default policies',
  'Immutable audit logging for domain mutations',
  'Least-privilege IAM and explicit permissions',
] as const;

export default function ArchitecturePage() {
  return (
    <MarketingShell>
      <MarketingPageTemplate
        eyebrow="Architecture"
        title="Sovereign-Grade Platform Topology for 24/7 Public Safety Operations"
        description="FusionEMS Quantum architecture is designed for deterministic behavior under incident traffic spikes, with strict route boundaries, observability-first operations, and secure multi-tenant isolation."
        accent="purple"
        signalLine="Production assumptions only: fault isolation, explicit controls, and graceful degradation where safe."
        stats={[
          { label: 'Availability Model', value: 'Multi-AZ', detail: 'Failure-tolerant service placement' },
          { label: 'Scaling Approach', value: 'Horizontal', detail: 'Incident spike resilience' },
          { label: 'Auth Pattern', value: 'OIDC-only', detail: 'No static secret login shortcuts' },
          { label: 'Data Authority', value: 'PostgreSQL', detail: 'Transactional source of truth' },
        ]}
        features={LAYERS.map((layer) => ({
          title: layer.title,
          description: layer.description,
        }))}
        actions={[
          { label: 'View Platform Modules', href: '/platform', primary: true },
          { label: 'Model ROI', href: '/roi' },
          { label: 'Request Technical Briefing', href: '/contact' },
        ]}
      >
        <div className="bg-[var(--color-bg-panel)] border border-border-default chamfer-8 p-5">
          <div className="text-label uppercase tracking-widest text-[var(--color-text-muted)]">Security posture controls</div>
          <div className="grid md:grid-cols-2 gap-2 mt-3">
            {SECURITY_CONTROLS.map((control) => (
              <div key={control} className="text-body text-[var(--color-text-secondary)] border border-border-subtle bg-[rgba(10,10,11,0.4)] chamfer-8 px-3 py-2">
                {control}
              </div>
            ))}
          </div>
        </div>
      </MarketingPageTemplate>
    </MarketingShell>
  );
}
