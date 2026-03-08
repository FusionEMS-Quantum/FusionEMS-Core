import Link from 'next/link';
import AccessShell from '@/components/shells/AccessShell';

export default function ResetPasswordPage() {
  return (
    <AccessShell title="Reset Password" subtitle="Complete credential reset under secure access controls.">
      <div className="space-y-4">
        <p className="text-body text-zinc-400">Password reset tokens and validation are processed via the unified login endpoint.</p>
        <div className="grid sm:grid-cols-2 gap-2">
          {['One-time token required', 'Credential policy validated', 'Role scope preserved', 'Security event logged'].map((item) => (
            <div key={item} className="border border-border-subtle bg-[rgba(10,10,11,0.45)] chamfer-8 px-3 py-2 text-body text-zinc-400">
              {item}
            </div>
          ))}
        </div>
        <Link href="/login" className="quantum-btn-primary">Return to Login</Link>
      </div>
    </AccessShell>
  );
}
