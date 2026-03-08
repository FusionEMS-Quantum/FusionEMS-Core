import type { Metadata } from 'next';
import Link from 'next/link';

export const metadata: Metadata = {
  title: 'Terms of Service | FusionEMS Quantum',
  description: 'Terms of service for FusionEMS Quantum platform services.',
};

export default function TermsPage() {
  return (
    <main className="min-h-screen bg-[#000000] text-[var(--color-text-primary)] px-6 py-12">
      <div className="mx-auto w-full max-w-4xl  border border-white/10 bg-zinc-950/[0.02] p-8 md:p-10">
        <p className="text-xs uppercase tracking-[0.2em] text-white/50">Legal</p>
        <h1 className="mt-2 text-3xl font-bold tracking-tight">Terms of Service</h1>
        <p className="mt-4 text-sm text-white/70">
          These terms govern access to and use of FusionEMS Quantum software services, including
          dispatch, ePCR, billing, compliance, and analytics modules.
        </p>

        <section className="mt-8 space-y-4 text-sm text-white/75">
          <p>
            Organizations are responsible for user account governance, lawful data use, and compliance with
            applicable federal and state regulations.
          </p>
          <p>
            Service availability targets, support channels, and response commitments are defined by your
            executed agreement and applicable service schedules.
          </p>
          <p>
            In the event of a conflict between these public terms and a signed master agreement,
            the signed agreement controls.
          </p>
        </section>

        <div className="mt-10 flex flex-wrap gap-3">
          <Link href="/privacy" className=" border border-white/15 px-4 py-2 text-sm hover:border-white/30">
            View Privacy Policy
          </Link>
          <Link href="/signup" className=" bg-[#FF4D00] px-4 py-2 text-sm font-semibold text-black">
            Return to Signup
          </Link>
        </div>
      </div>
    </main>
  );
}
