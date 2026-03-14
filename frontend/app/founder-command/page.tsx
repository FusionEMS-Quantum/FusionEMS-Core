import Link from 'next/link';
import AppShell from '@/components/AppShell';

const metrics = [
  { label: 'Monthly Recurring Revenue', value: '$2.84M', delta: '+6.1% MoM', tone: 'var(--color-success)' },
  { label: 'Tenant Activations', value: '34', delta: '+4 this week', tone: 'var(--color-info)' },
  { label: 'Critical Issues', value: '2', delta: 'requires response', tone: 'var(--color-critical)' },
  { label: 'Queue Health', value: '99.2%', delta: 'within SLA', tone: 'var(--color-success)' },
  { label: 'Stripe Success', value: '98.7%', delta: 'checkout completion', tone: 'var(--color-brand-orange)' },
  { label: 'NEMSIS Readiness', value: 'Ready', delta: 'DEM + EMS checks green', tone: 'var(--color-success)' },
];

const watchlist = [
  { area: 'Deployment', state: 'Stable', detail: 'frontend 2/2, backend 1/1', tone: 'var(--color-success)' },
  { area: 'Billing', state: 'Attention', detail: '2 denied claim clusters', tone: 'var(--color-warning)' },
  { area: 'Communications', state: 'Stable', detail: 'mail + SMS dispatch healthy', tone: 'var(--color-success)' },
  { area: 'NEMSIS', state: 'Ready', detail: 'submission queue passing', tone: 'var(--color-success)' },
  { area: 'NERIS', state: 'Blocked', detail: 'external credential dependency', tone: 'var(--color-critical)' },
];

export default function FounderCommandPublicPage() {
  return (
    <AppShell>
      <div className="space-y-6">
        <section className="border border-white/[0.06] bg-[var(--color-surface-primary)] p-6 md:p-8">
          <div className="flex flex-col gap-5 lg:flex-row lg:items-end lg:justify-between">
            <div>
              <div className="mb-2 text-[11px] font-bold uppercase tracking-[0.2em] text-[var(--color-brand-orange)]">Founder Command Center</div>
              <h1 className="text-3xl font-black tracking-[0.01em] text-[var(--color-text-primary)] md:text-4xl">
                Executive War Room for Revenue, Risk, and Readiness
              </h1>
              <p className="mt-3 max-w-3xl text-sm leading-relaxed text-[var(--color-text-secondary)]">
                Unified command visibility across deployment state, tenant growth, billing outcomes, communications health,
                and compliance posture. Built for rapid executive decisions under operational load.
              </p>
            </div>
            <div className="flex flex-wrap gap-2">
              <Link
                href="/founder"
                className="bg-[var(--color-brand-orange)] px-4 py-2 text-xs font-black uppercase tracking-[0.15em] text-black hover:bg-[var(--color-orange-hover)]"
              >
                Enter Command
              </Link>
              <Link
                href="/system-health"
                className="border border-white/[0.12] bg-[var(--color-surface-secondary)] px-4 py-2 text-xs font-bold uppercase tracking-[0.15em] text-[var(--color-text-secondary)] hover:text-white"
              >
                View System Health
              </Link>
            </div>
          </div>
        </section>

        <section className="grid grid-cols-1 gap-3 sm:grid-cols-2 xl:grid-cols-3">
          {metrics.map((metric) => (
            <div key={metric.label} className="border border-white/[0.06] bg-[var(--color-surface-secondary)] p-4">
              <div className="text-[10px] font-bold uppercase tracking-[0.18em] text-[var(--color-text-muted)]">{metric.label}</div>
              <div className="mt-2 text-2xl font-black" style={{ color: metric.tone }}>{metric.value}</div>
              <div className="mt-1 text-[11px] font-bold uppercase tracking-[0.14em] text-[var(--color-text-secondary)]">{metric.delta}</div>
            </div>
          ))}
        </section>

        <section className="grid grid-cols-1 gap-4 xl:grid-cols-[1.4fr_1fr]">
          <div className="border border-white/[0.06] bg-[var(--color-surface-primary)]">
            <div className="border-b border-white/[0.06] px-4 py-3 text-[11px] font-bold uppercase tracking-[0.2em] text-[var(--color-text-muted)]">
              Critical Issues and Escalations
            </div>
            <div className="divide-y divide-white/[0.06]">
              <div className="flex items-start justify-between gap-3 px-4 py-3">
                <div>
                  <div className="text-sm font-bold text-[var(--color-text-primary)]">Stripe retries elevated in two agencies</div>
                  <div className="mt-1 text-xs text-[var(--color-text-secondary)]">Impact: checkout conversion risk in self-service signup funnel</div>
                </div>
                <span className="border border-[var(--color-warning)]/40 bg-[var(--color-warning)]/10 px-2 py-1 text-[10px] font-bold uppercase tracking-[0.14em] text-[var(--color-warning)]">warning</span>
              </div>
              <div className="flex items-start justify-between gap-3 px-4 py-3">
                <div>
                  <div className="text-sm font-bold text-[var(--color-text-primary)]">NERIS external credentials pending</div>
                  <div className="mt-1 text-xs text-[var(--color-text-secondary)]">Impact: live submission remains blocked, test-ready path only</div>
                </div>
                <span className="border border-[var(--color-critical)]/45 bg-[var(--color-dark-red-surface)] px-2 py-1 text-[10px] font-bold uppercase tracking-[0.14em] text-[var(--color-critical)]">critical</span>
              </div>
              <div className="flex items-start justify-between gap-3 px-4 py-3">
                <div>
                  <div className="text-sm font-bold text-[var(--color-text-primary)]">Billing denial cluster from one payer</div>
                  <div className="mt-1 text-xs text-[var(--color-text-secondary)]">Impact: AR aging drift if unresolved beyond 72h</div>
                </div>
                <span className="border border-[var(--color-warning)]/40 bg-[var(--color-warning)]/10 px-2 py-1 text-[10px] font-bold uppercase tracking-[0.14em] text-[var(--color-warning)]">warning</span>
              </div>
            </div>
          </div>

          <div className="border border-white/[0.06] bg-[var(--color-surface-primary)]">
            <div className="border-b border-white/[0.06] px-4 py-3 text-[11px] font-bold uppercase tracking-[0.2em] text-[var(--color-text-muted)]">
              Live Watchlist
            </div>
            <div className="divide-y divide-white/[0.06]">
              {watchlist.map((item) => (
                <div key={item.area} className="px-4 py-3">
                  <div className="flex items-center justify-between">
                    <span className="text-xs font-bold uppercase tracking-[0.12em] text-[var(--color-text-primary)]">{item.area}</span>
                    <span className="text-[11px] font-black uppercase tracking-[0.14em]" style={{ color: item.tone }}>{item.state}</span>
                  </div>
                  <div className="mt-1 text-xs text-[var(--color-text-secondary)]">{item.detail}</div>
                </div>
              ))}
            </div>
          </div>
        </section>
      </div>
    </AppShell>
  );
}
