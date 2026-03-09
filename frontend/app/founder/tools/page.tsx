'use client';

import { useEffect, useState } from 'react';
import Link from 'next/link';
import { ArrowLeft, Wrench, RefreshCw, Calendar, FileText, ListTodo, MessageSquare, Shield, Radio } from 'lucide-react';
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
    { name: 'Calendar', description: 'Organization calendar, shift coverage, and compliance deadlines', href: '/founder/tools/calendar', icon: <Calendar className="w-6 h-6 text-blue-400" />, status: 'active' },
    { name: 'Documents', description: 'Document management, SOP library, and policy distribution', href: '/founder/tools/documents', icon: <FileText className="w-6 h-6 text-emerald-400" />, status: 'active' },
    { name: 'Task Center', description: 'Compliance actions, training requirements, and operational follow-ups', href: '/founder/tools/task-center', icon: <ListTodo className="w-6 h-6 text-violet-400" />, status: 'active' },
    { name: 'Script Builder', description: 'AI-powered communication script generation', href: '/founder/comms/script-builder', icon: <MessageSquare className="w-6 h-6 text-cyan-400" />, status: 'active' },
    { name: 'Broadcast Center', description: 'Mass notification and broadcast messaging', href: '/founder/comms/broadcast', icon: <Radio className="w-6 h-6 text-amber-400" />, status: 'active' },
    { name: 'Field Masking', description: 'PHI field masking and data governance policies', href: '/founder/security/field-masking', icon: <Shield className="w-6 h-6 text-red-400" />, status: 'active' },
  ];

  if (loading) {
    return <div className="min-h-screen bg-gray-950 text-white flex items-center justify-center"><RefreshCw className="w-8 h-8 animate-spin text-emerald-400" /></div>;
  }

  return (
    <div className="min-h-screen bg-gray-950 text-white p-6">
      <div className="max-w-7xl mx-auto space-y-8">
        <div>
          <Link href="/founder" className="text-gray-400 hover:text-white flex items-center gap-1 text-sm mb-2"><ArrowLeft className="w-4 h-4" /> Founder Command</Link>
          <h1 className="text-3xl font-bold flex items-center gap-3">
            <Wrench className="w-8 h-8 text-violet-400" />
            Founder Tools
          </h1>
          <p className="text-gray-400 mt-1">Operational tools and management utilities — Platform: <span className={health?.overall_status === 'healthy' ? 'text-emerald-400' : 'text-amber-400'}>{health?.overall_status ?? 'connecting...'}</span></p>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {tools.map((tool) => (
            <Link key={tool.href} href={tool.href} className="bg-gray-900 border border-gray-800 hover:border-gray-600 rounded-lg p-6 transition-colors group">
              <div className="flex items-center gap-3 mb-3">
                {tool.icon}
                <h3 className="text-lg font-semibold text-white group-hover:text-blue-400 transition-colors">{tool.name}</h3>
              </div>
              <p className="text-gray-400 text-sm">{tool.description}</p>
              <div className="mt-3 flex items-center gap-2">
                <span className="w-2 h-2 rounded-full bg-emerald-400"></span>
                <span className="text-xs text-emerald-400 uppercase font-bold">Active</span>
              </div>
            </Link>
          ))}
        </div>
      </div>
    </div>
  );
}
