import Link from 'next/link';
import AccessShell from '@/components/shells/AccessShell';

export default function RepresentativeAccessPage() {
  return (
    <AccessShell
      title="Authorized Representative Access"
      subtitle="Secure entry for guardians, POA holders, and approved billing representatives."
    >
      <div className="space-y-4">
        <p className="text-body text-[var(--color-text-secondary)]">Use verified representative flows to access patient billing records and payment actions.</p>

        <div className="grid sm:grid-cols-2 gap-2">
          {['Guardian + POA verification', 'Consent and signature workflows', 'Statement and payment access', 'Audit-safe representative trails'].map((item) => (
            <div key={item} className="border border-border-subtle bg-[rgba(10,10,11,0.45)] chamfer-8 px-3 py-2 text-body text-[var(--color-text-secondary)]">
              {item}
            </div>
          ))}
        </div>

        <div className="flex gap-2 flex-wrap">
          <Link href="/portal/rep/login" className="quantum-btn-primary">Representative Login</Link>
          <Link href="/portal/rep/register" className="quantum-btn">Start Registration</Link>
        </div>
      </div>
    </AccessShell>
  );
}
