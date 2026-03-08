import Link from 'next/link';
import AccessShell from '@/components/shells/AccessShell';

export default function AgencyAccessPage() {
  return (
    <AccessShell
      title="Agency and Staff Access"
      subtitle="Secure command entry for agency operators, billing staff, dispatch, and administrative teams."
    >
      <div className="space-y-4">
        <p className="text-body text-zinc-400">Authenticate to access command modules, operational dashboards, and module controls.</p>

        <div className="grid sm:grid-cols-2 gap-2">
          {['Command dashboards', 'Billing workflows', 'Dispatch-aligned operations', 'Compliance controls'].map((item) => (
            <div key={item} className="border border-border-subtle bg-[rgba(10,10,11,0.45)] chamfer-8 px-3 py-2 text-body text-zinc-400">
              {item}
            </div>
          ))}
        </div>

        <div className="flex gap-2 flex-wrap">
          <Link href="/login" className="quantum-btn-primary">Unified Login</Link>
          <Link href="/portal" className="quantum-btn">Agency Portal</Link>
        </div>
      </div>
    </AccessShell>
  );
}
