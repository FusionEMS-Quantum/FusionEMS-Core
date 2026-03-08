import Link from 'next/link';
import MarketingShell from '@/components/shells/MarketingShell';
import MarketingPageTemplate from '@/components/marketing/MarketingPageTemplate';

export default function CommunicationsMarketingPage() {
  return (
    <MarketingShell>
      <MarketingPageTemplate
        eyebrow="Module · Communications Command"
        title="Voice, SMS, Voicemail, and Callback Workflows Under One Policy Layer"
        description="Treat patient and billing communication channels as command infrastructure with explicit sequencing, escalation controls, and measurable outcomes."
        accent="orange"
        stats={[
          { label: 'Channel Orchestration', value: 'Unified', detail: 'Voice + SMS + voicemail + callbacks' },
          { label: 'Escalation Logic', value: 'Policy-bound', detail: 'No silent workflow divergence' },
          { label: 'Interaction Audit', value: 'Complete', detail: 'Traceable communication state' },
          { label: 'Revenue Impact', value: 'Measurable', detail: 'Collection and response KPIs' },
        ]}
        features={[
          { title: 'Centralized Billing Voice', description: 'Operate high-volume patient communication lanes without fragmented toolchain overhead.', href: '/founder/revenue/billing-voice', ctaLabel: 'Open Billing Voice Command' },
          { title: 'Callback Reliability Layer', description: 'Manage callback lifecycle deterministically with retry policy, state progression, and escalation hooks.' },
          { title: 'SMS and Voicemail Cadence', description: 'Enforce tone, timing, and compliance boundaries while preserving conversion outcomes.' },
          { title: 'Executive Communication Visibility', description: 'Track communication effectiveness as a command-level signal in Founder and revenue modules.' },
        ]}
        actions={[
          { label: 'Open Billing Voice Command', href: '/founder/revenue/billing-voice', primary: true },
          { label: 'Back to Platform', href: '/platform' },
          { label: 'Request Briefing', href: '/contact' },
        ]}
      >
        <div className="mt-2">
          <Link href="/roi" className="quantum-btn">Model Communication ROI</Link>
        </div>
      </MarketingPageTemplate>
    </MarketingShell>
  );
}
