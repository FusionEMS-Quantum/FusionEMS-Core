import AccessShell from '@/components/shells/AccessShell';

export default function FounderLoginPage() {
  return (
    <AccessShell
      title="Founder Login"
      subtitle="Executive command access using Microsoft Entra identity and secure token exchange."
    >
      <div className="space-y-4">
        <p className="text-body text-zinc-400">
          Use your Founder Microsoft account to enter Founder Command with full audit-safe access controls.
        </p>

        <div className="grid sm:grid-cols-2 gap-2">
          {['Microsoft Entra SSO', 'Founder command scope', 'Audit trail enabled', 'Tokenized session bootstrap'].map((item) => (
            <div key={item} className="border border-border-subtle bg-[rgba(10,10,11,0.45)] chamfer-8 px-3 py-2 text-body text-zinc-400">
              {item}
            </div>
          ))}
        </div>

        <div className="flex gap-2 flex-wrap">
          <a href="/api/v1/auth/microsoft/login?intent=founder" className="quantum-btn-primary">Continue with Microsoft</a>
          <a href="/login" className="quantum-btn">Open Standard Login</a>
        </div>
      </div>
    </AccessShell>
  );
}
