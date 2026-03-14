import Link from 'next/link';
import AccessShell from '@/components/shells/AccessShell';

export default function ForgotPasswordPage() {
  return (
    <AccessShell title="Password Recovery" subtitle="Reset access credentials using approved account recovery controls.">
      <div className="space-y-4">
        <p className="text-body text-[var(--color-text-secondary)]">For security reasons, password recovery is handled through the unified login workflow.</p>
        <div className="grid sm:grid-cols-2 gap-2">
          {['Identity check required', 'Session token time-boxed', 'Audit event recorded', 'MFA policy enforced'].map((item) => (
            <div key={item} className="border border-border-subtle bg-[rgba(10,10,11,0.45)] chamfer-8 px-3 py-2 text-body text-[var(--color-text-secondary)]">
              {item}
            </div>
          ))}
        </div>
        <Link href="/login" className="quantum-btn-primary">Continue to Login Recovery</Link>
      </div>
    </AccessShell>
  );
}
