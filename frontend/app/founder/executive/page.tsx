'use client';
import Link from 'next/link';
import { motion } from 'framer-motion';

const LINKS = [
  { href: '/founder/executive/daily-brief', label: 'Daily AI Brief', desc: 'AI-generated briefing with top action items updated hourly', color: '#FF4D00' },
  { href: '/founder/executive/risk-monitor', label: 'Risk Monitor', desc: 'Churn risk, compliance gaps, revenue risk, infra alerts', color: '#FF4D00' },
];

export default function ExecutivePage() {
  return (
    <div className="p-5 space-y-6">
      <div>
          <div className="text-micro font-bold uppercase tracking-[0.2em] text-orange-dim mb-1">DOMAIN 1 · EXECUTIVE</div>
        <h1 className="text-xl font-black uppercase tracking-wider text-zinc-100">Executive Command</h1>
        <p className="text-xs text-zinc-500 mt-0.5">Daily AI brief · risk monitor · platform overview</p>
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
        <Link href="/founder" className="text-xs text-orange-dim hover:text-[#FF4D00]">← Back to Founder Command OS</Link>
    </div>
  );
}
