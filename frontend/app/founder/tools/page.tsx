'use client';

import { useEffect, useState } from 'react';
import Link from 'next/link';
import { ArrowLeft, Wrench, RefreshCw, Calendar, FileText, ListTodo, MessageSquare, Shield, Radio, FolderOpen, Mail, Receipt, Landmark } from 'lucide-react';
import { getSystemHealthDashboard } from '@/services/api';

interface ToolModule {
  name: string;
  description: string;
  href: string;
  icon: React.ReactNode;
  status: string;
}

export default function FounderToolsPage() {
  const [health, setHealth] = useState<{ overall_status?: string } | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    (async () => {
      try {
        const res = await getSystemHealthDashboard();
        setHealth(res);
      } catch { /* graceful fallback */ }
      setLoading(false);
    })();
  }, []);

  const tools: ToolModule[] = [
    { name: 'Calendar', description: 'Organization calendar, shift coverage, and compliance deadlines', href: '/founder/tools/calendar', icon: <Calendar className="w-6 h-6 text-[var(--color-status-info)]" />, status: 'active' },
    { name: 'Documents', description: 'Document management, SOP library, and policy distribution', href: '/founder/tools/documents', icon: <FileText className="w-6 h-6 text-[var(--color-status-active)]" />, status: 'active' },
    { name: 'Files', description: 'Founder file browser, document access, and linked workspace files', href: '/founder/tools/files', icon: <FolderOpen className="w-6 h-6 text-[var(--color-status-info)]" />, status: 'active' },
    { name: 'Email', description: 'Founder email operations and outbound communications', href: '/founder/tools/email', icon: <Mail className="w-6 h-6 text-[var(--q-yellow)]" />, status: 'active' },
    { name: 'Onboarding Control', description: 'Provisioning queue, legal resend, and self-serve launch controls', href: '/founder/tools/onboarding-control', icon: <Shield className="w-6 h-6 text-[var(--color-system-compliance)]" />, status: 'active' },
    { name: 'Invoice Creator', description: 'Founder invoice drafting and export workflows', href: '/founder/tools/invoice-creator', icon: <Receipt className="w-6 h-6 text-[var(--color-brand-orange)]" />, status: 'active' },
    { name: 'Expense Ledger', description: 'Founder-native expense tracking and export for accounting', href: '/founder/tools/expense-ledger', icon: <Receipt className="w-6 h-6 text-[var(--color-status-warning)]" />, status: 'active' },
    { name: 'Task Center', description: 'Compliance actions, training requirements, and operational follow-ups', href: '/founder/tools/task-center', icon: <ListTodo className="w-6 h-6 text-[var(--color-system-compliance)]" />, status: 'active' },
    { name: 'Tax & E-File', description: 'IRS MeF status, Wisconsin filing, and open-source bank connection workflows', href: '/founder/tools/tax-efile', icon: <Landmark className="w-6 h-6 text-[var(--color-brand-orange)]" />, status: 'active' },
    { name: 'Script Builder', description: 'AI-powered communication script generation', href: '/founder/comms/script-builder', icon: <MessageSquare className="w-6 h-6 text-[var(--color-status-info)]" />, status: 'active' },
    { name: 'Broadcast Center', description: 'Mass notification and broadcast messaging', href: '/founder/comms/broadcast', icon: <Radio className="w-6 h-6 text-[var(--q-yellow)]" />, status: 'active' },
    { name: 'Field Masking', description: 'PHI field masking and data governance policies', href: '/founder/security/field-masking', icon: <Shield className="w-6 h-6 text-[var(--color-brand-red)]" />, status: 'active' },
  ];

  if (loading) {
    return <div className="min-h-screen bg-[var(--color-bg-base)] text-white flex items-center justify-center"><RefreshCw className="w-8 h-8 animate-spin text-[var(--color-status-active)]" /></div>;
  }

  return (
    <div className="min-h-screen bg-[var(--color-bg-base)] text-white p-6">
      <div className="max-w-7xl mx-auto space-y-8">
        <div>
          <Link href="/founder" className="text-[var(--color-text-secondary)] hover:text-[var(--color-text-primary)] flex items-center gap-1 text-sm mb-2"><ArrowLeft className="w-4 h-4" /> Founder Command</Link>
          <h1 className="text-3xl font-bold flex items-center gap-3">
            <Wrench className="w-8 h-8 text-[var(--color-system-compliance)]" />
            Founder Tools
          </h1>
          <p className="text-[var(--color-text-secondary)] mt-1">Operational tools and management utilities — Platform: <span className={health?.overall_status === 'healthy' ? 'text-[var(--color-status-active)]' : 'text-[var(--q-yellow)]'}>{health?.overall_status ?? 'connecting...'}</span></p>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {tools.map((tool) => (
            <Link key={tool.href} href={tool.href} className="bg-[var(--color-bg-panel)] border border-[var(--color-border-default)] hover:border-gray-600 chamfer-8 p-6 transition-colors group">
              <div className="flex items-center gap-3 mb-3">
                {tool.icon}
                <h3 className="text-lg font-semibold text-white group-hover:text-[var(--color-status-info)] transition-colors">{tool.name}</h3>
              </div>
              <p className="text-[var(--color-text-secondary)] text-sm">{tool.description}</p>
              <div className="mt-3 flex items-center gap-2">
                <span className="w-2 h-2 rounded-full bg-emerald-400"></span>
                <span className="text-xs text-[var(--color-status-active)] uppercase font-bold">Active</span>
              </div>
            </Link>
          ))}
        </div>
      </div>
    </div>
  );
}
