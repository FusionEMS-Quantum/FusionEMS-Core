'use client';
import { motion } from 'framer-motion';
import Link from 'next/link';

function SectionHeader({ number, title, sub }: { number: string; title: string; sub?: string }) {
  return (
    <div className="border-b border-border-subtle pb-2 mb-4">
      <div className="flex items-baseline gap-3">
          <span className="text-micro font-bold text-orange-dim font-mono">MODULE {number}</span>
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

const JOBS = [
  { id: 'job-a1b2', type: 'narrative_gen', model: 'STATFLOW-v2', duration: '2m 14s', status: 'Running' as const, badge: 'info' as const },
  { id: 'job-c3d4', type: 'denial_risk', model: 'DenialRisk-v2', duration: '42s', status: 'Running' as const, badge: 'info' as const },
  { id: 'job-e5f6', type: 'appeal_draft', model: 'AppealDraft-v1', duration: '5m 02s', status: 'Running' as const, badge: 'info' as const },
  { id: 'job-g7h8', type: 'classification', model: 'Classifier-fast', duration: '8s', status: 'Completed' as const, badge: 'ok' as const },
];

const MODELS = [
  { name: 'STATFLOW-Narrative', latency: 420, max: 500, color: 'var(--color-system-compliance)' },
  { name: 'DenialRisk-v2', latency: 85, max: 500, color: 'var(--q-green)' },
  { name: 'AppealDraft-v1', latency: 1200, max: 1500, color: 'var(--q-yellow)' },
  { name: 'Classifier-fast', latency: 22, max: 500, color: 'var(--q-green)' },
];

const MEMORY_SEGMENTS = [
  { label: 'Model Weights', gb: 8.2, color: 'var(--color-system-compliance)' },
  { label: 'KV Cache', gb: 4.1, color: 'var(--color-status-info)' },
  { label: 'Batch Buffer', gb: 2.8, color: 'var(--q-yellow)' },
  { label: 'Available', gb: 9.3, color: 'rgba(255,255,255,0.12)' },
];
const TOTAL_GB = MEMORY_SEGMENTS.reduce((a, s) => a + s.gb, 0);

const TEMP_HISTORY = [65, 66, 67, 68, 68, 69, 68, 67, 68, 69, 68, 68];

function tempColor(t: number) {
  if (t <= 65) return 'var(--color-status-active)';
  if (t <= 68) return 'var(--color-status-warning)';
  return 'var(--color-brand-red)';
}

const MODEL_REGISTRY = [
  { name: 'STATFLOW-Narrative', version: 'v2.3', size: '7.1 GB', status: 'active' as const, updated: '14 days ago' },
  { name: 'DenialRisk', version: 'v2.1', size: '0.8 GB', status: 'active' as const, updated: '7 days ago' },
  { name: 'AppealDraft', version: 'v1.4', size: '3.2 GB', status: 'active' as const, updated: '21 days ago' },
  { name: 'Classifier-fast', version: 'v3.0', size: '0.2 GB', status: 'active' as const, updated: '3 days ago' },
];

export default function AIGPUMonitorPage() {
  return (
    <div className="min-h-screen bg-black text-zinc-100 p-6 space-y-8">
      {/* Header */}
      <div className="flex items-start justify-between flex-wrap gap-4">
        <div>
            <div className="text-micro font-bold font-mono text-orange-dim uppercase tracking-widest mb-1">
            MODULE 10 · INFRASTRUCTURE
          </div>
          <h1 className="text-2xl font-bold tracking-tight text-zinc-100">AI GPU Monitor</h1>
          <p className="text-xs text-zinc-500 mt-1">
            Model inference · throughput · memory · temperature · job queue
          </p>
        </div>
        <Badge label="GPU Healthy" status="ok" />
      </div>

      {/* MODULE 1 — GPU Overview */}
      <section>
        <SectionHeader number="1" title="GPU Overview" />
        <div className="grid grid-cols-2 sm:grid-cols-3 gap-3">
          <StatCard label="GPU Utilization" value="61%" color="var(--color-status-warning)" />
          <StatCard label="GPU Memory" value="18.4 / 24 GB" color="var(--color-status-warning)" />
          <StatCard label="Temperature" value="68°C" color="var(--color-status-warning)" />
          <StatCard label="Power Draw" value="210 / 250W" color="var(--color-status-active)" />
          <StatCard label="Active Jobs" value={3} color="var(--color-status-info)" />
          <StatCard label="Queue Depth" value={2} color="var(--color-text-primary)" />
        </div>
      </section>

      {/* MODULE 2 — Active AI Jobs */}
      <section>
        <SectionHeader number="2" title="Active AI Jobs" />
        <Panel>
          <div className="overflow-x-auto">
            <table className="w-full text-xs">
              <thead>
                <tr className="text-zinc-500 uppercase tracking-widest text-micro">
                  <th className="text-left pb-2 pr-4 font-semibold">Job ID</th>
                  <th className="text-left pb-2 pr-4 font-semibold">Type</th>
                  <th className="text-left pb-2 pr-4 font-semibold">Model</th>
                  <th className="text-left pb-2 pr-4 font-semibold">Duration</th>
                  <th className="text-left pb-2 font-semibold">Status</th>
                </tr>
              </thead>
              <tbody>
                {JOBS.map((job) => (
                  <tr key={job.id} className="border-t border-border-subtle">
                    <td className="py-2 pr-4 font-mono text-zinc-100">{job.id}</td>
                    <td className="py-2 pr-4 text-zinc-400">{job.type}</td>
                    <td className="py-2 pr-4 text-zinc-100">{job.model}</td>
                    <td className="py-2 pr-4 font-mono text-zinc-400">{job.duration}</td>
                    <td className="py-2"><Badge label={job.status} status={job.badge} /></td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </Panel>
      </section>

      {/* MODULE 3 — Model Performance */}
      <section>
        <SectionHeader number="3" title="Model Performance" />
        <Panel>
          <div className="space-y-4">
            {MODELS.map((m) => (
              <div key={m.name}>
                <div className="flex justify-between items-center mb-1">
                  <span className="text-xs text-zinc-100">{m.name}</span>
                  <span className="text-body font-mono" style={{ color: m.color }}>{m.latency}ms avg latency</span>
                </div>
                <ProgressBar value={m.latency} max={m.max} color={m.color} />
              </div>
            ))}
          </div>
        </Panel>
      </section>

      {/* MODULE 4 — GPU Memory Allocation */}
      <section>
        <SectionHeader number="4" title="GPU Memory Allocation" />
        <Panel>
          <div className="flex chamfer-4 overflow-hidden h-7 mb-3">
            {MEMORY_SEGMENTS.map((seg) => (
              <div
                key={seg.label}
                style={{ width: `${(seg.gb / TOTAL_GB) * 100}%`, background: seg.color }}
                title={`${seg.label}: ${seg.gb} GB`}
              />
            ))}
          </div>
          <div className="flex flex-wrap gap-4">
            {MEMORY_SEGMENTS.map((seg) => (
              <div key={seg.label} className="flex items-center gap-1.5">
                <span className="w-2.5 h-2.5 chamfer-4 flex-shrink-0" style={{ background: seg.color, border: '1px solid rgba(255,255,255,0.1)' }} />
                <span className="text-body text-zinc-400">{seg.label}</span>
                <span className="text-body font-mono text-zinc-100">{seg.gb} GB</span>
              </div>
            ))}
          </div>
          <div className="mt-2 text-micro text-zinc-500 font-mono">Total: {TOTAL_GB.toFixed(1)} GB</div>
        </Panel>
      </section>

      {/* MODULE 5 — Throughput Metrics */}
      <section>
        <SectionHeader number="5" title="Throughput Metrics" />
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
          <StatCard label="Tokens/sec" value="4,200" color="var(--color-status-info)" />
          <StatCard label="Requests/min" value={142} color="var(--color-text-primary)" />
          <StatCard label="Avg Queue Wait" value="1.4s" color="var(--color-status-warning)" />
          <StatCard label="Batch Efficiency" value="87%" color="var(--color-status-active)" />
        </div>
      </section>

      {/* MODULE 6 — Temperature History */}
      <section>
        <SectionHeader number="6" title="Temperature History" sub="Last 12 hours" />
        <Panel>
          <div className="text-micro text-zinc-500 uppercase tracking-widest mb-3">
            Last 12 hours — GPU temperature
          </div>
          <div className="flex gap-2 flex-wrap">
            {TEMP_HISTORY.map((t, i) => (
              <div key={i} className="flex flex-col items-center gap-1">
                <div
                  className="chamfer-4"
                  style={{ width: 32, height: 24, background: tempColor(t) + '33', border: `1px solid ${tempColor(t)}66` }}
                />
                <span className="text-micro font-mono" style={{ color: tempColor(t) }}>{t}°</span>
              </div>
            ))}
          </div>
        </Panel>
      </section>

      {/* MODULE 7 — Model Registry */}
      <section>
        <SectionHeader number="7" title="Model Registry" />
        <Panel>
          <div className="overflow-x-auto">
            <table className="w-full text-xs">
              <thead>
                <tr className="text-zinc-500 uppercase tracking-widest text-micro">
                  <th className="text-left pb-2 pr-4 font-semibold">Model</th>
                  <th className="text-left pb-2 pr-4 font-semibold">Version</th>
                  <th className="text-left pb-2 pr-4 font-semibold">Size</th>
                  <th className="text-left pb-2 pr-4 font-semibold">Status</th>
                  <th className="text-left pb-2 font-semibold">Last Updated</th>
                </tr>
              </thead>
              <tbody>
                {MODEL_REGISTRY.map((m) => (
                  <tr key={m.name} className="border-t border-border-subtle">
                    <td className="py-2 pr-4 text-zinc-100">{m.name}</td>
                    <td className="py-2 pr-4 font-mono text-zinc-400">{m.version}</td>
                    <td className="py-2 pr-4 font-mono text-zinc-400">{m.size}</td>
                    <td className="py-2 pr-4"><Badge label={m.status} status="ok" /></td>
                    <td className="py-2 text-zinc-500">{m.updated}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </Panel>
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
