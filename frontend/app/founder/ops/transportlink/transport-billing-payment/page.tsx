import TransportWorkflowPage from '@/components/transportlink/TransportWorkflowPage';

const BILLING_PAYMENT_WORKFLOWS = [
  'Patient statement payment collection',
  'Transport invoice settlement tracking',
  'Payment link resend and expiration recovery',
  'Balance + payment plan handoff monitoring',
];

export default function TransportBillingPaymentPage() {
  return (
    <TransportWorkflowPage
      backHref="/founder/ops/transportlink"
      backLabel="Back to TransportLink"
      eyebrow="Payment Lane"
      title="Transport Billing Payment"
      subtitle="Payment operations for transport billing accounts and patient-facing settlement workflows."
      workflows={BILLING_PAYMENT_WORKFLOWS}
      actions={[
        { label: 'Open Patient Payment Portal', href: '/portal/patient/pay', tone: 'orange' },
        { label: 'Open Billing Intelligence', href: '/founder/revenue/billing-intelligence', tone: 'blue' },
      ]}
    />
  );
}
