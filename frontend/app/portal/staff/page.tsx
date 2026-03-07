'use client';

import React from 'react';
import { MetricCard } from '@/components/ui/MetricCard';
import { ModuleDashboardShell } from '@/components/shells/PageShells';

const PANEL_STYLE = 'bg-bg-panel border border-[var(--color-border-default)] chamfer-8';
const LABEL_STYLE = 'text-micro uppercase tracking-widest text-text-muted';

type Priority = 'HIGH' | 'MED' | 'LOW';

interface Claim {
  id: string;
  patientId: string;
  dos: string;
  payer: string;
  amount: string;
  priority: Priority;
}

interface Activity {
  time: string;
  text: string;
}

const SAMPLE_CLAIMS: Claim[] = [
  { id: 'CLM-88412', patientId: 'PT-***4821', dos: '02/14/2026', payer: 'BlueCross BS', amount: '$1,842.00', priority: 'HIGH' },
  { id: 'CLM-88398', patientId: 'PT-***1193', dos: '02/13/2026', payer: 'Aetna', amount: '$3,210.50', priority: 'HIGH' },
  { id: 'CLM-88375', patientId: 'PT-***7742', dos: '02/12/2026', payer: 'United Health', amount: '$970.00', priority: 'MED' },
  { id: 'CLM-88361', patientId: 'PT-***3309', dos: '02/11/2026', payer: 'Cigna', amount: '$2,150.75', priority: 'MED' },
  { id: 'CLM-88349', patientId: 'PT-***9954', dos: '02/10/2026', payer: 'Medicare', amount: '$680.00', priority: 'LOW' },
  { id: 'CLM-88337', patientId: 'PT-***6618', dos: '02/09/2026', payer: 'Medicaid', amount: '$455.25', priority: 'LOW' },
  { id: 'CLM-88321', patientId: 'PT-***2287', dos: '02/08/2026', payer: 'BlueCross BS', amount: '$5,320.00', priority: 'HIGH' },
  { id: 'CLM-88308', patientId: 'PT-***8801', dos: '02/07/2026', payer: 'Humana', amount: '$1,090.00', priority: 'MED' },
];

const RECENT_ACTIVITY: Activity[] = [
  { time: '09:42 AM', text: 'CLM-88412 submitted to BlueCross BS' },
  { time: '09:28 AM', text: 'Denial worked on CLM-88276 — resubmitted' },
  { time: '09:11 AM', text: 'Payment posted: CLM-88194 · $2,340.00' },
  { time: '08:55 AM', text: 'Auth rep document approved — PT-***4821' },
  { time: '08:39 AM', text: 'CLM-88398 flagged for additional documentation' },
  { time: '08:22 AM', text: 'Batch upload completed: 14 claims processed' },
];

const PRIORITY_STYLE: Record<Priority, React.CSSProperties> = {
  HIGH: {
    background: 'rgba(220,38,38,0.15)',
    border: '1px solid rgba(220,38,38,0.35)',
    color: 'var(--color-brand-red)',
  },
  MED: {
    background: 'rgba(234,179,8,0.12)',
    border: '1px solid rgba(234,179,8,0.3)',
    color: 'var(--color-status-warning)',
  },
  LOW: {
    background: 'rgba(255,255,255,0.06)',
    border: '1px solid rgba(255,255,255,0.1)',
    color: 'rgba(255,255,255,0.45)',
  },
};

function PriorityChip({ priority }: { priority: Priority }) {
  return (
    <span
      className="chamfer-4 text-body tracking-widest uppercase px-2 py-0.5 font-semibold inline-block"
      style={{
        ...PRIORITY_STYLE[priority],
      }}
    >
      {priority}
    </span>
  );
}

export default function StaffDashboardPage() {
  return (
    <ModuleDashboardShell
      title="Staff Dashboard"
      subtitle="Billing Specialist"
    >
      {/* Top stats */}
      <div className="flex gap-3 mb-6 flex-wrap">
        <MetricCard label="My Open Claims" value="34" domain="billing" compact />
        <MetricCard label="Claims Due Today" value="7" domain="billing" compact />
        <MetricCard label="Pending Authorizations" value="5" domain="billing" compact />
        <MetricCard label="Flagged for Review" value="3" domain="billing" compact />
      </div>

      {/* Main content: queue + activity */}
      <div className="grid gap-4 items-start" style={{ gridTemplateColumns: '1fr 300px' }}>
        {/* Claims queue */}
        <div className={`${PANEL_STYLE} overflow-hidden`}>
          <div className="px-5 py-4 border-b border-[var(--color-border-default)]">
            <p className={LABEL_STYLE}>My Claims Queue</p>
          </div>
          <div className="overflow-x-auto">
            <table className="w-full border-collapse">
              <thead>
                <tr className="border-b border-[var(--color-border-default)]">
                  {['Claim ID', 'Patient ID', 'DOS', 'Payer', 'Amount', 'Priority', 'Action'].map((h) => (
                    <th key={h} className="px-4 py-2.5 text-left text-micro tracking-widest uppercase text-text-muted font-semibold whitespace-nowrap">
                      {h}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {SAMPLE_CLAIMS.map((claim, i) => (
                  <tr key={claim.id} className={`border-b border-[var(--color-border-default)] last:border-0 ${i % 2 === 1 ? 'bg-white/[0.015]' : ''}`}>
                    <td className="px-4 py-3 text-text-primary text-sm font-medium whitespace-nowrap">{claim.id}</td>
                    <td className="px-4 py-3 text-text-muted text-sm font-mono whitespace-nowrap">{claim.patientId}</td>
                    <td className="px-4 py-3 text-text-secondary text-sm whitespace-nowrap">{claim.dos}</td>
                    <td className="px-4 py-3 text-text-secondary text-sm whitespace-nowrap">{claim.payer}</td>
                    <td className="px-4 py-3 text-text-primary text-sm font-semibold whitespace-nowrap">{claim.amount}</td>
                    <td className="px-4 py-3 whitespace-nowrap"><PriorityChip priority={claim.priority} /></td>
                    <td className="px-4 py-3 whitespace-nowrap">
                      <button type="button" className="chamfer-4 bg-brand-orange/10 border border-brand-orange/25 text-brand-orange text-body tracking-wider uppercase px-3 py-1 cursor-pointer font-semibold">
                        Work
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>

        {/* Recent activity */}
        <div className={`${PANEL_STYLE} overflow-hidden`}>
          <div className="px-5 py-4 border-b border-[var(--color-border-default)]">
            <p className={LABEL_STYLE}>Recent Activity</p>
          </div>
          <div className="py-2">
            {RECENT_ACTIVITY.map((a, i) => (
              <div key={i} className={`flex gap-3 px-[18px] py-3 items-start ${i < RECENT_ACTIVITY.length - 1 ? 'border-b border-[var(--color-border-default)]' : ''}`}>
                <div className="w-1.5 h-1.5 rounded-full bg-brand-orange/60 mt-1.5 flex-shrink-0" />
                <div className="min-w-0">
                  <p className="text-body text-text-secondary mb-0.5 leading-snug">{a.text}</p>
                  <p className="text-micro text-text-muted">{a.time}</p>
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* Bottom stats */}
      <div className="flex gap-3 mt-4 flex-wrap">
        <MetricCard label="Claims Processed Today" value="18" domain="billing" compact />
        <MetricCard label="Clean Claim Rate" value="91.2%" domain="billing" compact />
        <MetricCard label="Avg Processing Time" value="2.4d" domain="billing" compact />
        <MetricCard label="Denials Worked" value="6" domain="billing" compact />
      </div>
    </ModuleDashboardShell>
  );
}
