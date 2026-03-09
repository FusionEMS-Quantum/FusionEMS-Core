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

  if (loading) return <div className="min-h-screen bg-gray-950 text-white flex items-center justify-center"><RefreshCw className="w-8 h-8 animate-spin text-emerald-400" /></div>;

  return (
    <div className="min-h-screen bg-gray-950 text-white p-6">
      <div className="max-w-7xl mx-auto space-y-8">
        <div className="flex items-center justify-between">
          <div>
            <Link href="/founder/tools" className="text-gray-400 hover:text-white flex items-center gap-1 text-sm mb-2"><ArrowLeft className="w-4 h-4" /> Tools</Link>
            <h1 className="text-3xl font-bold flex items-center gap-3"><Calendar className="w-8 h-8 text-blue-400" /> Organization Calendar</h1>
            <p className="text-gray-400 mt-1">Shift coverage, training events, compliance deadlines, and swap requests</p>
          </div>
          <button onClick={loadData} className="px-4 py-2 bg-gray-800 hover:bg-gray-700 rounded-lg flex items-center gap-2 text-sm"><RefreshCw className="w-4 h-4" /> Refresh</button>
        </div>

        {error && <div className="bg-red-900/30 border border-red-700 rounded-lg p-4 flex items-center gap-3"><AlertTriangle className="w-5 h-5 text-red-400" /><span className="text-red-300">{error}</span></div>}

        <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
          <div className="bg-gray-900 border border-gray-800 rounded-lg p-5">
            <div className="text-gray-400 text-sm mb-1 flex items-center gap-1"><Calendar className="w-4 h-4" /> Total Shifts</div>
            <div className="text-2xl font-bold text-blue-400">{coverage?.total_shifts ?? (() => { throw new Error('Unsafe silent fallback. Dependency missing.'); })()}</div>
          </div>
          <div className="bg-gray-900 border border-gray-800 rounded-lg p-5">
            <div className="text-gray-400 text-sm mb-1 flex items-center gap-1"><Users className="w-4 h-4" /> Coverage</div>
            <div className="text-2xl font-bold text-emerald-400">{coverage?.coverage_pct ?? (() => { throw new Error('Unsafe silent fallback. Dependency missing.'); })()}%</div>
          </div>
          <div className="bg-gray-900 border border-gray-800 rounded-lg p-5">
            <div className="text-gray-400 text-sm mb-1 flex items-center gap-1"><Clock className="w-4 h-4" /> Coverage Gaps</div>
            <div className="text-2xl font-bold text-amber-400">{coverage?.gap_count ?? (() => { throw new Error('Unsafe silent fallback. Dependency missing.'); })()}</div>
          </div>
          <div className="bg-gray-900 border border-gray-800 rounded-lg p-5">
            <div className="text-gray-400 text-sm mb-1 flex items-center gap-1"><Shield className="w-4 h-4" /> Expiring Certs</div>
            <div className="text-2xl font-bold text-red-400">{expiring.length}</div>
          </div>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          {/* Shift Templates */}
          <div className="bg-gray-900 border border-gray-800 rounded-lg overflow-hidden">
            <div className="px-6 py-4 border-b border-gray-800"><h2 className="text-lg font-semibold flex items-center gap-2"><Calendar className="w-5 h-5 text-blue-400" /> Shift Templates</h2></div>
            {templates.length === 0 ? (
              <div className="p-8 text-center text-gray-500">No shift templates configured.</div>
            ) : (
              <div className="divide-y divide-gray-800">
                {templates.map((t) => (
                  <div key={t.id} className="px-6 py-3">
                    <div className="text-white font-medium">{t.name}</div>
                    <div className="text-gray-400 text-xs mt-1">{t.start_time} — {t.end_time} · {t.crew_required ?? (() => { throw new Error('Unsafe silent fallback. Dependency missing.'); })()} crew · {t.recurrence ?? 'one-time'}</div>
                  </div>
                ))}
              </div>
            )}
          </div>

          {/* Swap Requests */}
          <div className="bg-gray-900 border border-gray-800 rounded-lg overflow-hidden">
            <div className="px-6 py-4 border-b border-gray-800"><h2 className="text-lg font-semibold flex items-center gap-2"><Users className="w-5 h-5 text-violet-400" /> Swap Requests</h2></div>
            {swaps.length === 0 ? (
              <div className="p-8 text-center text-gray-500">No pending swap requests.</div>
            ) : (
              <div className="divide-y divide-gray-800">
                {swaps.map((s) => (
                  <div key={s.id} className="px-6 py-3 flex justify-between items-center">
                    <div>
                      <div className="text-white text-sm">{s.requester_name ?? 'Unknown'}</div>
                      <div className="text-gray-500 text-xs">{s.shift_date}</div>
                    </div>
                    <span className={`text-xs font-bold uppercase ${s.status === 'approved' ? 'text-emerald-400' : s.status === 'pending' ? 'text-amber-400' : 'text-red-400'}`}>{s.status}</span>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>

        {/* Expiring Credentials */}
        {expiring.length > 0 && (
          <div className="bg-gray-900 border border-gray-800 rounded-lg overflow-hidden">
            <div className="px-6 py-4 border-b border-gray-800"><h2 className="text-lg font-semibold flex items-center gap-2"><Shield className="w-5 h-5 text-red-400" /> Expiring Credentials</h2></div>
            <table className="w-full text-sm">
              <thead className="bg-gray-800/50">
                <tr>
                  <th className="text-left px-6 py-3 text-gray-400 font-medium">Crew Member</th>
                  <th className="text-left px-6 py-3 text-gray-400 font-medium">Credential</th>
                  <th className="text-left px-6 py-3 text-gray-400 font-medium">Expires</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-800">
                {expiring.map((c) => (
                  <tr key={c.id}>
                    <td className="px-6 py-3 text-white">{c.user_name}</td>
                    <td className="px-6 py-3 text-gray-400">{c.credential_type}</td>
                    <td className="px-6 py-3 text-red-400">{c.expires_at ? new Date(c.expires_at).toLocaleDateString() : '—'}</td>
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
