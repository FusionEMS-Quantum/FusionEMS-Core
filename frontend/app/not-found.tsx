import Link from 'next/link';

export default function NotFound() {
  return (
    <div className="min-h-screen flex items-center justify-center bg-[var(--color-bg-base)] px-6 py-12">
      <div className="max-w-md w-full text-center space-y-4 quantum-panel-strong px-8 py-10">
        <div className="quantum-kicker justify-center">Routing exception</div>
        <h1 className="text-6xl font-bold text-[var(--color-brand-orange-bright)]">404</h1>
        <p className="text-[var(--color-text-muted)] text-sm">Route not found in this command namespace.</p>
        <Link
          href="/"
          className="quantum-btn-primary inline-flex px-5 py-2 text-sm"
        >
          Return to Surface
        </Link>
      </div>
    </div>
  );
}
