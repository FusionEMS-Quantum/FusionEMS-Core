import TransportWorkflowPage from '@/components/transportlink/TransportWorkflowPage';

const THIRD_PARTY_PAYMENT_WORKFLOWS = [
  'Authorized representative payment intake',
  'Third-party processor reconciliation checks',
  'External billing handoff validation',
  'Payment dispute and override escalation',
];

export default function ThirdPartyPaymentPage() {
  return (
    <TransportWorkflowPage
      backHref="/founder/ops/transportlink"
      backLabel="Back to TransportLink"
      eyebrow="Payment Lane"
      title="Third-Party Payment"
      subtitle="Manage third-party payment pathways, authorization controls, and external settlement oversight."
      workflows={THIRD_PARTY_PAYMENT_WORKFLOWS}
      actions={[
        { label: 'Open Rep Authorization Flow', href: '/portal/rep/sign', tone: 'blue' },
        { label: 'Open Billing Ops Portal', href: '/portal/billing-ops', tone: 'purple' },
      ]}
    />
  );
}
