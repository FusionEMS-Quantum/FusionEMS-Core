import TransportWorkflowPage from '@/components/transportlink/TransportWorkflowPage';

const ASSISTED_LIVING_WORKFLOWS = [
  'Routine appointment transport runs',
  'Non-emergent escalation pickups',
  'After-hours standby scheduling',
  'Recurring care-plan transport windows',
];

export default function AssistedLivingSchedulingPage() {
  return (
    <TransportWorkflowPage
      backHref="/founder/ops/transportlink"
      backLabel="Back to TransportLink"
      eyebrow="Scheduling Lane"
      title="Assisted Living Scheduling"
      subtitle="Manage assisted-living transport scheduling lanes and recurring pickup plans."
      workflows={ASSISTED_LIVING_WORKFLOWS}
      actions={[
        { label: 'Open Scheduling Module', href: '/founder/pwa/scheduling', tone: 'green' },
        { label: 'Open CAD Dispatch', href: '/founder/ops/cad', tone: 'orange' },
      ]}
    />
  );
}
