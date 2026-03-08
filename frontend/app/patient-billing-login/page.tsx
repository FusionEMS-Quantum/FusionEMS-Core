import Link from 'next/link';
import AccessShell from '@/components/shells/AccessShell';

export default function PatientBillingLoginPage() {
  return (
    <AccessShell
      title="Patient Bill Pay Login"
      subtitle="Secure patient entry portal for medical transport statement lookup and payment actions."
    >
      <div className="space-y-4">
        <p className="text-body text-zinc-400">
          Log in to access medical transport billing statements, payment plans, receipts, and support workflows.
        </p>

        <div className="grid sm:grid-cols-2 gap-2">
          {[
            'Medical transport statement lookup',
            'Secure payment workflows',
            'Payment plan enrollment',
            'Receipt and communication history',
          ].map((item) => (
            <div key={item} className="border border-border-subtle bg-[#0A0A0B]-raised/45 chamfer-8 px-3 py-2 text-body text-zinc-400">
              {item}
            </div>
          ))}
        </div>

        <div className="flex gap-2 flex-wrap">
          <Link href="/portal/patient/lookup" className="quantum-btn-primary">Patient Login</Link>
          <Link href="/portal/patient/pay" className="quantum-btn">Go to Bill Pay</Link>
        </div>
      </div>
    </AccessShell>
  );
}
