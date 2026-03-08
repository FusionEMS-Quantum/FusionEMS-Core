'use client';
import { motion } from 'framer-motion';
import Link from 'next/link';

function SectionHeader({ number, title, sub }: { number: string; title: string; sub?: string }) {
  return (
    <div className="border-b border-border-subtle pb-2 mb-4">
      <div className="flex items-baseline gap-3">
        <span className="text-micro font-bold text-[#FF4D00]-dim font-mono">MODULE {number}</span>
        <h2 className="text-sm font-bold uppercase tracking-widest text-zinc-100">{title}</h2>
        {sub && <span className="text-xs text-zinc-500">{sub}</span>}
      </div>
    </div>
  );
}

function Badge({ label, status }: { label: string; status: 'ok' | 'warn' | 'error' | 'info' }) {
  const c = { ok: 'var(--color-status-active)', warn: 'var(--color-status-warning)', error: 'var(--color-brand-red)', info: 'var(--color-status-info)' };
  return (
    <span
      className="inline-flex items-center gap-1.5 px-2 py-0.5 chamfer-4 text-micro font-semibold uppercase tracking-wider border"
      style={{ borderColor: `${c[status]}40`, color: c[status], background: `${c[status]}12` }}
    >
      <span className="w-1 h-1 " style={{ background: c[status] }} />
      {label}
    </span>
  );
}

function StatCard({ label, value, sub, color }: { label: string; value: string | number; sub?: string; color?: string }) {
  return (
    <div
      className="bg-[#0A0A0B] border border-border-DEFAULT p-4"
      style={{ clipPath: 'polygon(0 0,calc(100% - 10px) 0,100% 10px,100% 100%,0 100%)' }}
    >
      <div className="text-micro font-semibold uppercase tracking-widest text-zinc-500 mb-1">{label}</div>
      <div className="text-xl font-bold" style={{ color: color ?? 'var(--color-text-primary)' }}>{value}</div>
      {sub && <div className="text-body text-zinc-500 mt-0.5">{sub}</div>}
    </div>
  );
}

function Panel({ children, className }: { children: React.ReactNode; className?: string }) {
  return (
    <div
      className={`bg-[#0A0A0B] border border-border-DEFAULT p-4 ${className ?? ''}`}
      style={{ clipPath: 'polygon(0 0,calc(100% - 10px) 0,100% 10px,100% 100%,0 100%)' }}
    >
      {children}
    </div>
  );
}

function ProgressBar({ value, max, color }: { value: number; max: number; color: string }) {
  const pct = max > 0 ? Math.min((value / max) * 100, 100) : 0;
  return (
    <div className="h-1.5 bg-zinc-950/[0.06]  overflow-hidden">
      <motion.div
        className="h-full "
        style={{ background: color }}
        initial={{ width: 0 }}
        animate={{ width: `${pct}%` }}
        transition={{ duration: 0.8 }}
      />
    </div>
  );
}

const SERVICES = [
  { name: 'ECS Fargate', mtd: 380, pct: '30.5%', mom: '+2%', trend: 'up', trendColor: 'var(--color-status-warning)' },
  { name: 'RDS Multi-AZ', mtd: 210, pct: '16.8%', mom: '0%', trend: 'flat', trendColor: 'rgba(255,255,255,0.3)' },
  { name: 'ElastiCache', mtd: 85, pct: '6.8%', mom: '0%', trend: 'flat', trendColor: 'rgba(255,255,255,0.3)' },
  { name: 'ALB', mtd: 42, pct: '3.4%', mom: '+1%', trend: 'up-small', trendColor: 'var(--color-status-warning)' },
  { name: 'S3', mtd: 28, pct: '2.2%', mom: '+5%', trend: 'up', trendColor: 'var(--color-status-warning)' },
  { name: 'CloudFront', mtd: 18, pct: '1.4%', mom: '-2%', trend: 'down', trendColor: 'var(--color-status-active)' },
  { name: 'Route53', mtd: 5, pct: '0.4%', mom: '0%', trend: 'flat', trendColor: 'rgba(255,255,255,0.3)' },
  { name: 'Other', mtd: 479, pct: '38.4%', mom: '+1%', trend: 'up-small', trendColor: 'var(--color-status-warning)' },
];

function TrendIcon({ trend, color }: { trend: string; color: string }) {
  if (trend === 'up' || trend === 'up-small') {
    return <span style={{ color }} className="text-xs font-bold">↑</span>;
  }
  if (trend === 'down') {
    return <span style={{ color }} className="text-xs font-bold">↓</span>;
  }
  return <span style={{ color }} className="text-xs font-bold">—</span>;
}

const MONTHS = [
  { label: 'Aug', cost: 980 },
  { label: 'Sep', cost: 1020 },
  { label: 'Oct', cost: 1100 },
  { label: 'Nov', cost: 1150 },
  { label: 'Dec', cost: 1184 },
  { label: 'Jan', cost: 1247 },
];

const ALERTS: { text: string; status: 'ok' | 'warn' | 'error' | 'info' }[] = [
  { text: 'S3 costs increased 5% MoM — review storage lifecycle rules', status: 'info' },
  { text: 'Fargate CPU over-provisioned — potential $45/mo saving by right-sizing', status: 'warn' },
  { text: 'All services within monthly budget', status: 'ok' },
];

const TENANTS = [
  { name: 'Agency-A1', exports: 412, compute: '48hrs', cost: '$124' },
  { name: 'Agency-B2', exports: 280, compute: '32hrs', cost: '$86' },
  { name: 'Agency-C3', exports: 190, compute: '22hrs', cost: '$62' },
  { name: 'Agency-D4', exports: 88, compute: '10hrs', cost: '$31' },
];

const OPTIMIZATIONS = [
  {
    title: 'Enable S3 Intelligent-Tiering',
    desc: 'Automatically moves objects between tiers based on access frequency to reduce storage costs.',
    saving: '~$8/mo',
  },
  {
    title: 'Use Fargate Savings Plan',
    desc: 'Commit to consistent compute usage in exchange for a discounted rate on Fargate workloads.',
    saving: '~$100/mo',
  },
  {
    title: 'Right-size worker ECS tasks',
    desc: 'Worker tasks are currently provisioned at 2 vCPU but analysis shows 1 vCPU is sufficient.',
    saving: '~$45/mo',
  },
  {
    title: 'Enable RDS read replica for reporting',
    desc: 'Offload heavy reporting queries to a read replica to reduce primary DB load and latency.',
    saving: '$0 (performance gain)',
  },
];

export default function InfraCostPage() {
  return (
    <div className="min-h-screen bg-black text-zinc-100 p-6 space-y-8">
      {/* Header */}
      <div className="flex items-start justify-between flex-wrap gap-4">
        <div>
          <div className="text-micro font-bold font-mono text-[#FF4D00]-dim uppercase tracking-widest mb-1">
            MODULE 10 · INFRASTRUCTURE
          </div>
          <h1 className="text-2xl font-bold tracking-tight text-zinc-100">Infrastructure Cost Dashboard</h1>
          <p className="text-xs text-zinc-500 mt-1">
            AWS spend · service breakdown · budget tracking · optimization
          </p>
        </div>
        <Badge label="Within Budget" status="ok" />
      </div>

      {/* MODULE 1 — Cost Overview */}
      <section>
        <SectionHeader number="1" title="Cost Overview" />
        <div className="grid grid-cols-2 sm:grid-cols-3 gap-3">
          <StatCard label="MTD Total" value="$1,247" color="var(--color-text-primary)" />
          <StatCard label="Last Month" value="$1,184" color="var(--color-text-primary)" />
          <StatCard label="Projected" value="$1,310" color="var(--color-status-warning)" />
          <StatCard label="Budget" value="$1,500" color="var(--color-text-primary)" />
          <StatCard label="Budget Remaining" value="$253" color="var(--color-status-active)" />
          <StatCard label="YTD Total" value="$8,420" color="var(--color-text-primary)" />
        </div>
      </section>

      {/* MODULE 2 — Cost by Service */}
      <section>
        <SectionHeader number="2" title="Cost by Service" />
        <Panel>
          <div className="overflow-x-auto">
            <table className="w-full text-xs">
              <thead>
                <tr className="text-zinc-500 uppercase tracking-widest text-micro">
                  <th className="text-left pb-2 pr-4 font-semibold">Service</th>
                  <th className="text-left pb-2 pr-4 font-semibold">MTD Cost</th>
                  <th className="text-left pb-2 pr-4 font-semibold">% of Total</th>
                  <th className="text-left pb-2 pr-4 font-semibold">MoM Change</th>
                  <th className="text-left pb-2 font-semibold">Trend</th>
                </tr>
              </thead>
              <tbody>
                {SERVICES.map((svc) => (
                  <tr key={svc.name} className="border-t border-border-subtle">
                    <td className="py-2 pr-4 text-zinc-100">{svc.name}</td>
                    <td className="py-2 pr-4 font-mono text-zinc-100">${svc.mtd}</td>
                    <td className="py-2 pr-4 text-zinc-400">{svc.pct}</td>
                    <td className="py-2 pr-4" style={{ color: svc.trendColor }}>{svc.mom}</td>
                    <td className="py-2"><TrendIcon trend={svc.trend} color={svc.trendColor} /></td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </Panel>
      </section>

      {/* MODULE 3 — 6-Month Cost Trend */}
      <section>
        <SectionHeader number="3" title="6-Month Cost Trend" />
        <Panel>
          <div className="space-y-3">
            {MONTHS.map((m) => (
              <div key={m.label} className="flex items-center gap-3">
                <span className="text-body font-mono text-zinc-500 w-8 flex-shrink-0">{m.label}</span>
                <div className="flex-1">
                  <ProgressBar value={m.cost} max={1500} color="var(--color-text-muted)" />
                </div>
                <span className="text-body font-mono text-zinc-400 w-14 text-right flex-shrink-0">${m.cost.toLocaleString()}</span>
              </div>
            ))}
          </div>
        </Panel>
      </section>

      {/* MODULE 4 — Reserved vs On-Demand */}
      <section>
        <SectionHeader number="4" title="Reserved vs On-Demand" />
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
          <Panel>
            <div className="text-micro font-semibold uppercase tracking-widest text-zinc-500 mb-3">Current Savings</div>
            <div className="space-y-3">
              <div className="flex justify-between items-start">
                <div>
                  <div className="text-xs text-zinc-100">RDS Reserved</div>
                  <div className="text-body text-zinc-500 mt-0.5">1-year reserved instance active</div>
                </div>
                <span className="text-sm font-bold text-status-active">-$85/mo</span>
              </div>
              <div className="border-t border-white/5 pt-3 flex justify-between items-start">
                <div>
                  <div className="text-xs text-zinc-100">Fargate Spot</div>
                  <div className="text-body text-zinc-500 mt-0.5">18% of tasks on Spot pricing</div>
                </div>
                <span className="text-body font-mono text-zinc-400">18%</span>
              </div>
            </div>
          </Panel>
          <Panel>
            <div className="text-micro font-semibold uppercase tracking-widest text-zinc-500 mb-3">Optimization Potential</div>
            <div className="space-y-3">
              <div className="flex justify-between items-start">
                <div>
                  <div className="text-xs text-zinc-100">Full RDS Reservation</div>
                  <div className="text-body text-zinc-500 mt-0.5">Reserve remaining on-demand instances</div>
                </div>
                <span className="text-sm font-bold text-status-warning">+$42/mo</span>
              </div>
              <div className="border-t border-white/5 pt-3 flex justify-between items-start">
                <div>
                  <div className="text-xs text-zinc-100">Fargate Savings Plan</div>
                  <div className="text-body text-zinc-500 mt-0.5">Commit to hourly compute spend</div>
                </div>
                <span className="text-sm font-bold text-status-warning">+$100/mo</span>
              </div>
            </div>
          </Panel>
        </div>
      </section>

      {/* MODULE 5 — Cost Alerts */}
      <section>
        <SectionHeader number="5" title="Cost Alerts" />
        <Panel>
          <div className="space-y-3">
            {ALERTS.map((alert, i) => (
              <div key={i} className="flex items-center gap-3 py-2 border-b border-border-subtle last:border-0">
                <Badge label={alert.status} status={alert.status} />
                <span className="text-xs text-zinc-400">{alert.text}</span>
              </div>
            ))}
          </div>
        </Panel>
      </section>

      {/* MODULE 6 — Cost Per Tenant */}
      <section>
        <SectionHeader number="6" title="Cost Per Tenant" />
        <Panel>
          <div className="overflow-x-auto">
            <table className="w-full text-xs">
              <thead>
                <tr className="text-zinc-500 uppercase tracking-widest text-micro">
                  <th className="text-left pb-2 pr-4 font-semibold">Tenant</th>
                  <th className="text-left pb-2 pr-4 font-semibold">Exports/mo</th>
                  <th className="text-left pb-2 pr-4 font-semibold">Compute hrs</th>
                  <th className="text-left pb-2 font-semibold">Est. Cost</th>
                </tr>
              </thead>
              <tbody>
                {TENANTS.map((t) => (
                  <tr key={t.name} className="border-t border-border-subtle">
                    <td className="py-2 pr-4 font-mono text-zinc-100">{t.name}</td>
                    <td className="py-2 pr-4 font-mono text-zinc-400">{t.exports}</td>
                    <td className="py-2 pr-4 font-mono text-zinc-400">{t.compute}</td>
                    <td className="py-2 font-mono font-semibold text-zinc-100">{t.cost}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </Panel>
      </section>

      {/* MODULE 7 — Optimization Recommendations */}
      <section>
        <SectionHeader number="7" title="Optimization Recommendations" />
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
          {OPTIMIZATIONS.map((opt, i) => (
            <Panel key={i}>
              <div className="text-xs font-bold text-zinc-100 mb-1">{opt.title}</div>
              <div className="text-body text-zinc-500 mb-3 leading-relaxed">{opt.desc}</div>
              <div className="flex items-center gap-2">
                <span className="text-micro font-semibold uppercase tracking-widest text-zinc-500">Est. Saving</span>
                <span className="text-xs font-bold text-status-active">{opt.saving}</span>
              </div>
            </Panel>
          ))}
        </div>
      </section>

      {/* Back */}
      <div>
        <Link href="/founder" className="text-xs text-system-cad hover:text-zinc-100 transition-colors">
          ← Back to Founder OS
        </Link>
      </div>
    </div>
  );
}
