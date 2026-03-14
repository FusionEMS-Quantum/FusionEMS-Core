'use client';

import { useEffect, useState } from 'react';
import Link from 'next/link';
import { ArrowLeft, Calendar, RefreshCw, AlertTriangle, Clock, Users, Shield } from 'lucide-react';
import { getSchedulingCoverageDashboard, listShiftTemplates, getExpiringCredentials, listSchedulingSwaps } from '@/services/api';

interface CoverageDash { total_shifts?: number; covered_shifts?: number; gap_count?: number; coverage_pct?: number; }
interface ShiftTemplate { id: string; name: string; start_time?: string; end_time?: string; crew_required?: number; recurrence?: string; }
interface ExpiringCred { id: string; user_name?: string; credential_type?: string; expires_at?: string; }
interface Swap { id: string; requester_name?: string; status?: string; shift_date?: string; }

export default function ToolsCalendarPage() {
  const [coverage, setCoverage] = useState<CoverageDash | null>(null);
  const [templates, setTemplates] = useState<ShiftTemplate[]>([]);
  const [expiring, setExpiring] = useState<ExpiringCred[]>([]);
  const [swaps, setSwaps] = useState<Swap[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const loadData = async () => {
    setLoading(true);
    setError(null);
    try {
      const [cRes, tRes, eRes, sRes] = await Promise.allSettled([
        getSchedulingCoverageDashboard(), listShiftTemplates(), getExpiringCredentials(), listSchedulingSwaps(),
      ]);
      if (cRes.status === 'fulfilled') setCoverage(cRes.value);
      if (tRes.status === 'fulfilled') {
        const t = tRes.value;
        setTemplates(Array.isArray(t?.templates) ? t.templates : Array.isArray(t) ? t : []);
      }
      if (eRes.status === 'fulfilled') {
        const e = eRes.value;
        setExpiring(Array.isArray(e?.credentials) ? e.credentials : Array.isArray(e) ? e : []);
      }
      if (sRes.status === 'fulfilled') {
        const s = sRes.value;
        setSwaps(Array.isArray(s?.swaps) ? s.swaps : Array.isArray(s) ? s : []);
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load calendar data');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { loadData(); }, []);

  if (loading) return <div className="min-h-screen bg-[var(--color-bg-base)] text-white flex items-center justify-center"><RefreshCw className="w-8 h-8 animate-spin text-[var(--color-status-active)]" /></div>;

  return (
    <div className="min-h-screen bg-[var(--color-bg-base)] text-white p-6">
      <div className="max-w-7xl mx-auto space-y-8">
        <div className="flex items-center justify-between">
          <div>
            <Link href="/founder/tools" className="text-[var(--color-text-secondary)] hover:text-[var(--color-text-primary)] flex items-center gap-1 text-sm mb-2"><ArrowLeft className="w-4 h-4" /> Tools</Link>
            <h1 className="text-3xl font-bold flex items-center gap-3"><Calendar className="w-8 h-8 text-[var(--color-status-info)]" /> Organization Calendar</h1>
            <p className="text-[var(--color-text-secondary)] mt-1">Shift coverage, training events, compliance deadlines, and swap requests</p>
          </div>
          <button onClick={loadData} className="px-4 py-2 bg-[var(--color-bg-raised)] hover:bg-[var(--color-bg-overlay)] chamfer-8 flex items-center gap-2 text-sm"><RefreshCw className="w-4 h-4" /> Refresh</button>
        </div>

        {error && <div className="bg-red-900/30 border border-[var(--color-brand-red)] chamfer-8 p-4 flex items-center gap-3"><AlertTriangle className="w-5 h-5 text-[var(--color-brand-red)]" /><span className="text-[var(--color-brand-red)]">{error}</span></div>}

        <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
          <div className="bg-[var(--color-bg-panel)] border border-[var(--color-border-default)] chamfer-8 p-5">
            <div className="text-[var(--color-text-secondary)] text-sm mb-1 flex items-center gap-1"><Calendar className="w-4 h-4" /> Total Shifts</div>
            <div className="text-2xl font-bold text-[var(--color-status-info)]">{coverage?.total_shifts ?? 0}</div>
          </div>
          <div className="bg-[var(--color-bg-panel)] border border-[var(--color-border-default)] chamfer-8 p-5">
            <div className="text-[var(--color-text-secondary)] text-sm mb-1 flex items-center gap-1"><Users className="w-4 h-4" /> Coverage</div>
            <div className="text-2xl font-bold text-[var(--color-status-active)]">{coverage?.coverage_pct ?? 0}%</div>
          </div>
          <div className="bg-[var(--color-bg-panel)] border border-[var(--color-border-default)] chamfer-8 p-5">
            <div className="text-[var(--color-text-secondary)] text-sm mb-1 flex items-center gap-1"><Clock className="w-4 h-4" /> Coverage Gaps</div>
            <div className="text-2xl font-bold text-[var(--q-yellow)]">{coverage?.gap_count ?? 0}</div>
          </div>
          <div className="bg-[var(--color-bg-panel)] border border-[var(--color-border-default)] chamfer-8 p-5">
            <div className="text-[var(--color-text-secondary)] text-sm mb-1 flex items-center gap-1"><Shield className="w-4 h-4" /> Expiring Certs</div>
            <div className="text-2xl font-bold text-[var(--color-brand-red)]">{expiring.length}</div>
          </div>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          {/* Shift Templates */}
          <div className="bg-[var(--color-bg-panel)] border border-[var(--color-border-default)] chamfer-8 overflow-hidden">
            <div className="px-6 py-4 border-b border-[var(--color-border-default)]"><h2 className="text-lg font-semibold flex items-center gap-2"><Calendar className="w-5 h-5 text-[var(--color-status-info)]" /> Shift Templates</h2></div>
            {templates.length === 0 ? (
              <div className="p-8 text-center text-[var(--color-text-muted)]">No shift templates configured.</div>
            ) : (
              <div className="divide-y divide-gray-800">
                {templates.map((t) => (
                  <div key={t.id} className="px-6 py-3">
                    <div className="text-white font-medium">{t.name}</div>
                    <div className="text-[var(--color-text-secondary)] text-xs mt-1">{t.start_time} — {t.end_time} · {t.crew_required ?? 0} crew · {t.recurrence ?? 'one-time'}</div>
                  </div>
                ))}
              </div>
            )}
          </div>

          {/* Swap Requests */}
          <div className="bg-[var(--color-bg-panel)] border border-[var(--color-border-default)] chamfer-8 overflow-hidden">
            <div className="px-6 py-4 border-b border-[var(--color-border-default)]"><h2 className="text-lg font-semibold flex items-center gap-2"><Users className="w-5 h-5 text-[var(--color-system-compliance)]" /> Swap Requests</h2></div>
            {swaps.length === 0 ? (
              <div className="p-8 text-center text-[var(--color-text-muted)]">No pending swap requests.</div>
            ) : (
              <div className="divide-y divide-gray-800">
                {swaps.map((s) => (
                  <div key={s.id} className="px-6 py-3 flex justify-between items-center">
                    <div>
                      <div className="text-white text-sm">{s.requester_name ?? 'Unknown'}</div>
                      <div className="text-[var(--color-text-muted)] text-xs">{s.shift_date}</div>
                    </div>
                    <span className={`text-xs font-bold uppercase ${s.status === 'approved' ? 'text-[var(--color-status-active)]' : s.status === 'pending' ? 'text-[var(--q-yellow)]' : 'text-[var(--color-brand-red)]'}`}>{s.status}</span>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>

        {/* Expiring Credentials */}
        {expiring.length > 0 && (
          <div className="bg-[var(--color-bg-panel)] border border-[var(--color-border-default)] chamfer-8 overflow-hidden">
            <div className="px-6 py-4 border-b border-[var(--color-border-default)]"><h2 className="text-lg font-semibold flex items-center gap-2"><Shield className="w-5 h-5 text-[var(--color-brand-red)]" /> Expiring Credentials</h2></div>
            <table className="w-full text-sm">
              <thead className="bg-[var(--color-bg-raised)]/50">
                <tr>
                  <th className="text-left px-6 py-3 text-[var(--color-text-secondary)] font-medium">Crew Member</th>
                  <th className="text-left px-6 py-3 text-[var(--color-text-secondary)] font-medium">Credential</th>
                  <th className="text-left px-6 py-3 text-[var(--color-text-secondary)] font-medium">Expires</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-800">
                {expiring.map((c) => (
                  <tr key={c.id}>
                    <td className="px-6 py-3 text-white">{c.user_name}</td>
                    <td className="px-6 py-3 text-[var(--color-text-secondary)]">{c.credential_type}</td>
                    <td className="px-6 py-3 text-[var(--color-brand-red)]">{c.expires_at ? new Date(c.expires_at).toLocaleDateString() : '—'}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
}
