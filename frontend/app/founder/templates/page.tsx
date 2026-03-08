'use client';
import Link from 'next/link';
import { motion } from 'framer-motion';

const LINKS = [
  { href: '/founder/templates/proposals', label: 'Proposal Templates', desc: 'ROI proposals with pricing and value breakdown', color: 'var(--color-status-info)' },
  { href: '/founder/templates/invoices', label: 'Invoice Templates', desc: 'Professional invoice layouts for agencies', color: 'var(--color-status-info)' },
  { href: '/founder/templates/contracts', label: 'Contract Builder', desc: 'Service agreements, BAAs, NDAs, renewals', color: 'var(--color-status-info)' },
  { href: '/founder/templates/reports', label: 'Report Templates', desc: 'Compliance, AR aging, executive briefings', color: 'var(--color-status-info)' },
];

export default function TemplatesPage() {
  return (
    <div className="p-5 space-y-6">
      <div>
        <div className="text-micro font-bold uppercase tracking-[0.2em] text-[#FF4D00]/70 mb-1">DOMAIN 7 · TEMPLATES</div>
        <h1 className="text-xl font-black uppercase tracking-wider text-zinc-100">Templates</h1>
        <p className="text-xs text-zinc-500 mt-0.5">Proposals · invoices · contracts · reports</p>
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
      <Link href="/founder" className="text-xs text-[#FF4D00]/70 hover:text-[#FF4D00]">← Back to Founder Command OS</Link>
    </div>
  );
}
