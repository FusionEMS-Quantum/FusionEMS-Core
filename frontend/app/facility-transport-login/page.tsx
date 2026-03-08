import Link from 'next/link';
import AccessShell from '@/components/shells/AccessShell';

export default function FacilityTransportLoginPage() {
  return (
    <AccessShell
      title="Facility TransportLink Login"
      subtitle="Dedicated facility entry for hospitals and assisted living teams requesting medical transport."
    >
      <div className="space-y-4">
        <p className="text-body text-zinc-400">
          Choose your facility type to enter the correct TransportLink request portal.
        </p>

        <div className="grid sm:grid-cols-2 gap-3">
           <div className="border border-border-default bg-[rgba(10,10,11,0.45)] chamfer-8 p-3 space-y-2">
            <div className="text-label text-zinc-100 font-semibold uppercase tracking-[0.12em]">Hospital Access</div>
            <p className="text-body text-zinc-400">For emergency departments, discharge teams, and transfer coordinators.</p>
            <Link href="/facility-transport-login/hospital" className="quantum-btn-primary">Hospital Login</Link>
          </div>

            <div className="border border-border-default bg-[rgba(10,10,11,0.45)] chamfer-8 p-3 space-y-2">
            <div className="text-label text-zinc-100 font-semibold uppercase tracking-[0.12em]">Assisted Living Access</div>
            <p className="text-body text-zinc-400">For assisted living and long-term care teams coordinating transport.</p>
            <Link href="/facility-transport-login/assisted-living" className="quantum-btn-primary">Assisted Living Login</Link>
          </div>
        </div>
      </div>
    </AccessShell>
  );
}
