'use client';
import { useEffect, useState, useCallback } from 'react';
import Link from 'next/link';
import { motion } from 'framer-motion';
import { listSupportTickets } from '@/services/api';
import { SeverityBadge } from '@/components/ui';
import { normalizeSeverity } from '@/lib/design-system/severity';

interface Ticket {
  id: string;
  subject: string;
  description: string;
  state: string;
  severity: string;
  category: string;
  reporter_user_id: string;
  assigned_user_id: string | null;
  sla_response_target: string | null;
  sla_resolution_target: string | null;
  sla_response_met: boolean | null;
  sla_resolution_met: boolean | null;
  created_at: string;
}

const SEVERITY_FILTER_OPTIONS: Array<{ value: string; label: string }> = [
  { value: '', label: 'ALL' },
  { value: 'CRITICAL', label: 'BLOCKING' },
  { value: 'HIGH', label: 'HIGH' },
  { value: 'MEDIUM', label: 'MEDIUM' },
  { value: 'LOW', label: 'LOW' },
  { value: 'INFO', label: 'INFORMATIONAL' },
];

const STATE_BADGE: Record<string, string> = {
  NEW: 'text-blue-400',
  TRIAGED: 'text-cyan-400',
  ASSIGNED: 'text-purple-400',
  IN_PROGRESS: 'text-yellow-400',
  WAITING_ON_CUSTOMER: 'text-[#FF4D00]',
  WAITING_ON_VENDOR: 'text-[#FF4D00]',
  ESCALATED: 'text-red-400',
  RESOLVED: 'text-green-400',
  CLOSED: 'text-zinc-500',
  REOPENED: 'text-red-300',
};

export default function SupportOpsPage() {
  const [tickets, setTickets] = useState<Ticket[]>([]);
  const [statusFilter, setStatusFilter] = useState<string>('');
  const [severityFilter, setSeverityFilter] = useState<string>('');
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    try {
      setLoading(true);
      const data = await listSupportTickets(statusFilter || undefined, severityFilter || undefined);
      setTickets(data);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : 'Failed to load tickets');
    } finally {
      setLoading(false);
    }
  }, [statusFilter, severityFilter]);

  useEffect(() => { load(); }, [load]);

  if (error) {
    return (
      <div className="p-5">
        <div className="bg-red-500/10 border border-red-500/30 p-4 text-red-400 text-sm">{error}</div>
      </div>
    );
  }

  return (
    <div className="p-5 space-y-6">
      <div>
        <div className="text-micro font-bold uppercase tracking-[0.2em] text-[#FF4D00]/70 mb-1">SUCCESS · SUPPORT</div>
        <h1 className="text-xl font-black uppercase tracking-wider text-zinc-100">Support Operations</h1>
        <p className="text-xs text-zinc-500 mt-0.5">Ticket queue · SLA tracking · escalations · resolution</p>
      </div>

      {/* Filters */}
      <div className="flex items-center gap-4 flex-wrap">
        <div className="flex items-center gap-2">
          <span className="text-xs text-zinc-500">Status:</span>
          {['', 'NEW', 'TRIAGED', 'ASSIGNED', 'IN_PROGRESS', 'ESCALATED', 'RESOLVED', 'CLOSED'].map((s) => (
            <button key={s} onClick={() => setStatusFilter(s)}
              className={`text-micro px-2 py-1 border ${statusFilter === s ? 'border-orange-dim text-[#FF4D00]/70 bg-[rgba(255,77,0,0.1)]' : 'border-border-DEFAULT text-zinc-500 hover:text-zinc-100'} transition-colors`}>
              {s || 'ALL'}
            </button>
          ))}
        </div>
        <div className="flex items-center gap-2">
          <span className="text-xs text-zinc-500">Severity:</span>
          {SEVERITY_FILTER_OPTIONS.map((option) => (
            <button key={option.value || 'ALL'} onClick={() => setSeverityFilter(option.value)}
              className={`text-micro px-2 py-1 border ${severityFilter === option.value ? 'border-orange-dim text-[#FF4D00]/70 bg-[rgba(255,77,0,0.1)]' : 'border-border-DEFAULT text-zinc-500 hover:text-zinc-100'} transition-colors`}>
              {option.label}
            </button>
          ))}
        </div>
      </div>

      {loading ? (
        <div className="space-y-2 animate-pulse">
          {Array.from({ length: 4 }).map((_, i) => (
            <div key={i} className="h-14 bg-[#0A0A0B] " />
          ))}
        </div>
      ) : tickets.length === 0 ? (
        <div className="bg-[#0A0A0B] border border-border-DEFAULT p-8 text-center text-zinc-500 text-sm">
          No tickets found.
        </div>
      ) : (
        <div className="space-y-1">
          {/* Table Header */}
          <div className="grid grid-cols-12 gap-2 text-micro font-bold text-zinc-500 px-4 py-2 border-b border-border-DEFAULT">
            <div className="col-span-4">Subject</div>
            <div className="col-span-2">State</div>
            <div className="col-span-1">Sev</div>
            <div className="col-span-2">Category</div>
            <div className="col-span-1">SLA Resp</div>
            <div className="col-span-2">Created</div>
          </div>

          {tickets.map((t, i) => (
            <motion.div key={t.id} initial={{ opacity: 0, y: 4 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: i * 0.03 }}
              className="grid grid-cols-12 gap-2 bg-[#0A0A0B] border border-border-DEFAULT px-4 py-3 hover:border-white/[0.18] transition-colors items-center text-xs">
              <div className="col-span-4">
                <div className="text-zinc-100 font-bold truncate">{t.subject}</div>
                <div className="text-zinc-500 truncate">{t.description.slice(0, 60)}{t.description.length > 60 ? '…' : ''}</div>
              </div>
              <div className={`col-span-2 font-bold ${STATE_BADGE[t.state] || 'text-zinc-500'}`}>{t.state}</div>
              <div className="col-span-1">
                <SeverityBadge
                  severity={normalizeSeverity(t.severity)}
                  size="sm"
                  label={normalizeSeverity(t.severity)}
                />
              </div>
              <div className="col-span-2 text-zinc-500">{t.category}</div>
              <div className="col-span-1">
                {t.sla_response_met === null ? (
                  <span className="text-zinc-500">—</span>
                ) : t.sla_response_met ? (
                  <span className="text-green-400 font-bold">✓</span>
                ) : (
                  <span className="text-red-400 font-bold">✗</span>
                )}
              </div>
              <div className="col-span-2 text-zinc-500">{new Date(t.created_at).toLocaleString()}</div>
            </motion.div>
          ))}
        </div>
      )}

      <Link href="/founder/success-command" className="text-xs text-[#FF4D00]/70 hover:text-[#FF4D00]">← Back to Success Command Center</Link>
    </div>
  );
}
