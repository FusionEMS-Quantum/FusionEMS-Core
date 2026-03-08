import TransportWorkflowPage from '@/components/transportlink/TransportWorkflowPage';

const HOSPITAL_WORKFLOWS = [
  'ED discharge return transports',
  'Direct-admit interfacility transfers',
  'Dialysis recurring transport blocks',
  'Bed-control overflow transfers',
];

export default function HospitalSchedulingPage() {
  return (
    <TransportWorkflowPage
      backHref="/founder/ops/transportlink"
      backLabel="Back to TransportLink"
      eyebrow="Scheduling Lane"
      title="Hospital Scheduling"
      subtitle="Configure and monitor hospital-origin transport scheduling workflows."
      workflows={HOSPITAL_WORKFLOWS}
      actions={[
        { label: 'Open Scheduling Module', href: '/founder/pwa/scheduling', tone: 'blue' },
        { label: 'Open CAD Dispatch', href: '/founder/ops/cad', tone: 'orange' },
      ]}
    />
  );
}
