export default function GlobalLoading() {
  return (
    <div className="flex items-center justify-center min-h-screen bg-[var(--color-bg-base)] px-6">
      <div className="quantum-panel-strong flex flex-col items-center gap-4 px-10 py-10 text-center">
        <div className="h-12 w-12 animate-spin border-[3px] border-[rgba(255,122,47,0.18)] border-t-[var(--color-brand-orange)] chamfer-8" />
        <div>
          <p className="label-caps text-[var(--color-brand-orange-bright)]">Command surface loading</p>
          <p className="mt-2 text-sm text-zinc-400">Synchronizing FusionEMS Quantum modules and access lanes.</p>
        </div>
      </div>
    </div>
  );
}
