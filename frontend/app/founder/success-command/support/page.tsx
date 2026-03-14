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
  NEW: 'text-[var(--color-status-info)]',
  TRIAGED: 'text-cyan-400',
  ASSIGNED: 'text-purple-400',
  IN_PROGRESS: 'text-yellow-400',
  WAITING_ON_CUSTOMER: 'text-[var(--q-orange)]',
  WAITING_ON_VENDOR: 'text-[var(--q-orange)]',
  ESCALATED: 'text-[var(--color-brand-red)]',
  RESOLVED: 'text-[var(--color-status-active)]',
  CLOSED: 'text-[var(--color-text-muted)]',
  REOPENED: 'text-[var(--color-brand-red)]',
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
        <div className="bg-[var(--color-brand-red)]/10 border border-[var(--color-brand-red)]/30 p-4 text-[var(--color-brand-red)] text-sm">{error}</div>
      </div>
    );
  }

  return (
    <div className="p-5 space-y-6">
      <div>
        <div className="text-micro font-bold uppercase tracking-[0.2em] text-[var(--q-orange)]/70 mb-1">SUCCESS · SUPPORT</div>
        <h1 className="text-xl font-black uppercase tracking-wider text-[var(--color-text-primary)]">Support Operations</h1>
        <p className="text-xs text-[var(--color-text-muted)] mt-0.5">Ticket queue · SLA tracking · escalations · resolution</p>
      </div>

      {/* Filters */}
      <div className="flex items-center gap-4 flex-wrap">
        <div className="flex items-center gap-2">
          <span className="text-xs text-[var(--color-text-muted)]">Status:</span>
          {['', 'NEW', 'TRIAGED', 'ASSIGNED', 'IN_PROGRESS', 'ESCALATED', 'RESOLVED', 'CLOSED'].map((s) => (
            <button key={s} onClick={() => setStatusFilter(s)}
              className={`text-micro px-2 py-1 border ${statusFilter === s ? 'border-orange-dim text-[var(--q-orange)]/70 bg-[rgba(255,106,0,0.1)]' : 'border-border-DEFAULT text-[var(--color-text-muted)] hover:text-[var(--color-text-primary)]'} transition-colors`}>
              {s || 'ALL'}
            </button>
          ))}
        </div>
        <div className="flex items-center gap-2">
          <span className="text-xs text-[var(--color-text-muted)]">Severity:</span>
          {SEVERITY_FILTER_OPTIONS.map((option) => (
            <button key={option.value || 'ALL'} onClick={() => setSeverityFilter(option.value)}
              className={`text-micro px-2 py-1 border ${severityFilter === option.value ? 'border-orange-dim text-[var(--q-orange)]/70 bg-[rgba(255,106,0,0.1)]' : 'border-border-DEFAULT text-[var(--color-text-muted)] hover:text-[var(--color-text-primary)]'} transition-colors`}>
              {option.label}
            </button>
          ))}
        </div>
      </div>

      {loading ? (
        <div className="space-y-2 animate-pulse">
          {Array.from({ length: 4 }).map((_, i) => (
            <div key={i} className="h-14 bg-[var(--color-bg-panel)] " />
          ))}
        </div>
      ) : tickets.length === 0 ? (
        <div className="bg-[var(--color-bg-panel)] border border-border-DEFAULT p-8 text-center text-[var(--color-text-muted)] text-sm">
          No tickets found.
        </div>
      ) : (
        <div className="space-y-1">
          {/* Table Header */}
          <div className="grid grid-cols-12 gap-2 text-micro font-bold text-[var(--color-text-muted)] px-4 py-2 border-b border-border-DEFAULT">
            <div className="col-span-4">Subject</div>
            <div className="col-span-2">State</div>
            <div className="col-span-1">Sev</div>
            <div className="col-span-2">Category</div>
            <div className="col-span-1">SLA Resp</div>
            <div className="col-span-2">Created</div>
          </div>

          {tickets.map((t, i) => (
            <motion.div key={t.id} initial={{ opacity: 0, y: 4 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: i * 0.03 }}
              className="grid grid-cols-12 gap-2 bg-[var(--color-bg-panel)] border border-border-DEFAULT px-4 py-3 hover:border-white/[0.18] transition-colors items-center text-xs">
              <div className="col-span-4">
                <div className="text-[var(--color-text-primary)] font-bold truncate">{t.subject}</div>
                <div className="text-[var(--color-text-muted)] truncate">{t.description.slice(0, 60)}{t.description.length > 60 ? '…' : ''}</div>
              </div>
              <div className={`col-span-2 font-bold ${STATE_BADGE[t.state] || 'text-[var(--color-text-muted)]'}`}>{t.state}</div>
              <div className="col-span-1">
                <SeverityBadge
                  severity={normalizeSeverity(t.severity)}
                  size="sm"
                  label={normalizeSeverity(t.severity)}
                />
              </div>
              <div className="col-span-2 text-[var(--color-text-muted)]">{t.category}</div>
              <div className="col-span-1">
                {t.sla_response_met === null ? (
                  <span className="text-[var(--color-text-muted)]">—</span>
                ) : t.sla_response_met ? (
                  <span className="text-[var(--color-status-active)] font-bold">✓</span>
                ) : (
                  <span className="text-[var(--color-brand-red)] font-bold">✗</span>
                )}
              </div>
              <div className="col-span-2 text-[var(--color-text-muted)]">{new Date(t.created_at).toLocaleString()}</div>
            </motion.div>
          ))}
        </div>
      )}

      <Link href="/founder/success-command" className="text-xs text-[var(--q-orange)]/70 hover:text-[var(--q-orange)]">← Back to Success Command Center</Link>
    </div>
  );
}
