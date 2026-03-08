'use client';

import Link from 'next/link';
import { ModuleDashboardShell } from '@/components/shells/PageShells';

const DOCUMENT_WORKFLOWS = [
  {
    href: '/portal/rep/upload',
    title: 'Authorization Uploads',
    description: 'Collect and validate POA, guardianship, and other representative documents.',
  },
  {
    href: '/portal/fax-inbox',
    title: 'Fax Intake',
    description: 'Process inbound clinical and billing documents from connected fax channels.',
  },
  {
    href: '/portal/edi',
    title: 'EDI Attachments',
    description: 'Track clearinghouse attachment readiness and transmission states.',
  },
  {
    href: '/portal/patient/lookup',
    title: 'Patient Document Context',
    description: 'Locate patient account records before uploading or linking supporting documents.',
  },
];

export default function PortalDocumentsPage() {
  return (
    <ModuleDashboardShell
      title="Document Operations"
      subtitle="Secure intake and routing for patient and billing documentation"
    >
      <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
        {DOCUMENT_WORKFLOWS.map((item) => (
          <Link
            key={item.href}
            href={item.href}
            className="block  border border-border-subtle bg-[#0A0A0B] px-5 py-4 transition-colors hover:border-brand-orange/50"
          >
            <h2 className="text-sm font-semibold text-zinc-100">{item.title}</h2>
            <p className="mt-2 text-sm text-zinc-500">{item.description}</p>
          </Link>
        ))}
      </div>
    </ModuleDashboardShell>
  );
}
