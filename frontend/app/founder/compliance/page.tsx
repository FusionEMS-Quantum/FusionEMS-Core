'use client';
import Link from 'next/link';
import { motion } from 'framer-motion';

const LINKS = [
  { href: '/founder/compliance/nemsis', label: 'NEMSIS Manager', desc: 'NEMSIS v3.5 validation, element mapping, XML export', color: 'var(--q-yellow)' },
  { href: '/founder/compliance/export-status', label: 'Export Status', desc: '100-module export intelligence and state submission control', color: 'var(--q-yellow)' },
  { href: '/founder/compliance/niers', label: 'NIERS Manager', desc: 'Fire data compliance, crosswalk builder, heatmap', color: 'var(--q-yellow)' },
  { href: '/founder/compliance/certification', label: 'Certification Monitor', desc: 'State certifications, credential tracking, expiry alerts', color: 'var(--q-yellow)' },
];

export default function CompliancePage() {
  return (
    <div className="p-5 space-y-6">
      <div>
        <div className="text-micro font-bold uppercase tracking-[0.2em] text-[#FF4D00]-dim mb-1">DOMAIN 5 · COMPLIANCE</div>
        <h1 className="text-xl font-black uppercase tracking-wider text-zinc-100">Compliance</h1>
        <p className="text-xs text-zinc-500 mt-0.5">NEMSIS · NIERS · export status · certification</p>
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
