'use client';
import Link from 'next/link';
import { motion } from 'framer-motion';

const LINKS = [
  { href: '/founder/infra/ecs', label: 'ECS Health', desc: 'Fargate cluster, task health, ALB metrics, auto scaling', color: 'var(--color-text-muted)' },
  { href: '/founder/infra/rds', label: 'RDS Health', desc: 'PostgreSQL status, connection pools, backups, slow queries', color: 'var(--color-text-muted)' },
  { href: '/founder/infra/ai-gpu', label: 'AI GPU Monitor', desc: 'Model inference jobs, memory allocation, throughput', color: 'var(--color-text-muted)' },
  { href: '/founder/infra/cost', label: 'Cost Dashboard', desc: 'AWS spend by service, budget tracking, optimization tips', color: 'var(--color-text-muted)' },
  { href: '/founder/infra/incident', label: 'Incident Control', desc: 'System status, incident history, playbooks, on-call', color: 'var(--color-text-muted)' },
];

export default function InfraPage() {
  return (
    <div className="p-5 space-y-6">
      <div>
        <div className="text-micro font-bold uppercase tracking-[0.2em] text-[#FF4D00]-dim mb-1">DOMAIN 10 · INFRASTRUCTURE</div>
        <h1 className="text-xl font-black uppercase tracking-wider text-zinc-100">Infrastructure</h1>
        <p className="text-xs text-zinc-500 mt-0.5">ECS · RDS · AI GPU · AWS costs · incident control</p>
      </div>
      <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
        {LINKS.map((l) => (
          <motion.div key={l.href} initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }}>
            <Link href={l.href} className="block bg-[#0A0A0B] border border-border-DEFAULT p-5 hover:border-white/[0.18] transition-colors" style={{ clipPath: 'polygon(0 0, calc(100% - 10px) 0, 100% 10px, 100% 100%, 0 100%)' }}>
              <div className="text-sm font-bold mb-1" style={{ color: l.color }}>{l.label}</div>
              <div className="text-xs text-zinc-500">{l.desc}</div>
            </Link>
          </motion.div>
        ))}
      </div>
      <Link href="/founder" className="text-xs text-[#FF4D00]-dim hover:text-[#FF4D00]">← Back to Founder Command OS</Link>
    </div>
  );
}
