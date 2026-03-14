import type { Metadata } from 'next';
import Link from 'next/link';

export const metadata: Metadata = {
  title: 'Privacy Policy | FusionEMS Quantum',
  description: 'Privacy policy for FusionEMS Quantum platform services.',
};

export default function PrivacyPage() {
  return (
    <main className="min-h-screen bg-[#000000] text-[var(--color-text-primary)] px-6 py-12">
      <div className="mx-auto w-full max-w-4xl  border border-white/10 bg-[var(--color-bg-base)]/[0.02] p-8 md:p-10">
        <p className="text-xs uppercase tracking-[0.2em] text-white/50">Legal</p>
        <h1 className="mt-2 text-3xl font-bold tracking-tight">Privacy Policy</h1>
        <p className="mt-4 text-sm text-white/70">
          FusionEMS Quantum processes customer and operational data to deliver EMS, fire, dispatch, billing,
          and care-coordination workflows. We apply role-based access controls, audit logging, and encryption
          in transit and at rest to protect sensitive information.
        </p>

        <section className="mt-8 space-y-4 text-sm text-white/75">
          <p>
            We collect only the information required for platform operation, regulatory compliance,
            billing operations, and customer support.
          </p>
          <p>
            Access to protected data is restricted to authorized users with least-privilege permissions,
            and access events are auditable.
          </p>
          <p>
            If your organization has a signed agreement (including HIPAA-related terms), those contract terms
            govern data handling and retention obligations in addition to this policy.
          </p>
        </section>

        <div className="mt-10 flex flex-wrap gap-3">
          <Link href="/terms" className=" border border-white/15 px-4 py-2 text-sm hover:border-white/30">
            View Terms
          </Link>
          <Link href="/signup" className=" bg-[var(--q-orange)] px-4 py-2 text-sm font-semibold text-black">
            Return to Signup
          </Link>
        </div>
      </div>
    </main>
  );
}
