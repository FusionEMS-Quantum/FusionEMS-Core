import AccessShell from '@/components/shells/AccessShell';

export default function FounderLoginPage() {
  return (
    <AccessShell
      title="Platform Login"
      subtitle="Secure access to the FusionEMS Quantum platform with Microsoft Entra identity."
    >
      <div className="space-y-4">
        <p className="text-body text-[var(--color-text-secondary)]">
          Use your authorized Microsoft account to access FusionEMS Quantum with full audit-safe controls.
        </p>

        <div className="grid sm:grid-cols-2 gap-2">
          {['Microsoft Entra SSO', 'Platform command scope', 'Audit trail enabled', 'Tokenized session bootstrap'].map((item) => (
            <div key={item} className="border border-border-subtle bg-[rgba(10,10,11,0.45)] chamfer-8 px-3 py-2 text-body text-[var(--color-text-secondary)]">
              {item}
            </div>
          ))}
        </div>

        <div className="flex gap-2 flex-wrap">
          <a href="/api/v1/auth/microsoft/login?intent=founder" className="quantum-btn-primary">Microsoft Login</a>
          <a href="/login" className="quantum-btn">Open Standard Login</a>
        </div>
      </div>
    </AccessShell>
  );
}
