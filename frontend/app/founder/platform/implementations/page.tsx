'use client';

import { useEffect, useState } from 'react';
import { motion } from 'framer-motion';
import { listPlatformImplementations, listPlatformBlockers } from '@/services/api';
import { SeverityBadge } from '@/components/ui';
import { normalizeSeverity } from '@/lib/design-system/severity';

interface Implementation {
  id: string;
  tenant_id: string;
  project_name: string;
  state: string;
  assigned_pm: string;
  target_go_live_date: string | null;
  created_at: string;
}

interface Blocker {
  id: string;
  project_id: string;
  title: string;
  severity: string;
  status: string;
  created_at: string;
}

const STATE_COLORS: Record<string, string> = {
  NOT_STARTED: 'text-zinc-400 bg-zinc-400/10',
  DISCOVERY: 'text-blue-400 bg-blue-400/10',
  CONFIGURATION: 'text-yellow-400 bg-yellow-400/10',
    INTEGRATION: 'text-[#FF4D00] bg-[rgba(255,77,0,0.10)]',
  TESTING: 'text-purple-400 bg-purple-400/10',
  USER_ACCEPTANCE: 'text-cyan-400 bg-cyan-400/10',
  GO_LIVE_READY: 'text-green-400 bg-green-400/10',
  LIVE: 'text-green-500 bg-green-500/10',
  ON_HOLD: 'text-red-400 bg-red-400/10',
  CANCELLED: 'text-zinc-500 bg-zinc-500/10',
};

export default function ImplementationsPage() {
  const [implementations, setImplementations] = useState<Implementation[]>([]);
  const [blockers, setBlockers] = useState<Blocker[]>([]);
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [filterState, setFilterState] = useState('');
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    async function load() {
      try {
        const data = await listPlatformImplementations(filterState || undefined);
        setImplementations(data);
      } catch (err: unknown) {
        setError(err instanceof Error ? err.message : 'Failed to load implementations');
      } finally {
        setLoading(false);
      }
    }
    load();
  }, [filterState]);

  async function loadBlockers(projectId: string) {
    setSelectedId(projectId);
    try {
      const data = await listPlatformBlockers(projectId);
      setBlockers(data);
    } catch {
      setBlockers([]);
    }
  }

  if (loading) {
    return <div className="p-6 text-zinc-500 animate-pulse">Loading implementations…</div>;
  }
  if (error) {
    return <div className="p-6 text-red-400 text-sm">{error}</div>;
  }

  const stateGroups = implementations.reduce<Record<string, number>>((acc, impl) => {
    acc[impl.state] = (acc[impl.state] || 0) + 1;
    return acc;
  }, {});

  return (
    <div className="p-6 space-y-6">
      <div className="hud-rail pb-2">
        <h1 className="text-h1 font-bold text-zinc-100">Implementation Control</h1>
        <p className="text-body text-zinc-500 mt-1">Track agency implementations from discovery to go-live</p>
      </div>

      {/* State filter strip */}
      <div className="flex flex-wrap gap-2">
        <button
          onClick={() => setFilterState('')}
          className={`px-3 py-1.5 text-xs font-semibold border transition-colors ${!filterState ? 'border-brand-orange/40 bg-brand-orange/10 text-brand-orange' : 'border-border-DEFAULT text-zinc-500 hover:text-zinc-400'}`}
        >
          ALL ({implementations.length})
        </button>
        {Object.entries(stateGroups).map(([state, count]) => (
          <button
            key={state}
            onClick={() => setFilterState(state)}
            className={`px-3 py-1.5 text-xs font-semibold border transition-colors ${filterState === state ? 'border-brand-orange/40 bg-brand-orange/10 text-brand-orange' : 'border-border-DEFAULT text-zinc-500 hover:text-zinc-400'}`}
          >
            {state.replace(/_/g, ' ')} ({count})
          </button>
        ))}
      </div>

      <div className="flex gap-6">
        {/* Implementation list */}
        <div className="flex-1 space-y-2">
          {implementations.length === 0 && <div className="text-xs text-zinc-500">No implementations found</div>}
          {implementations.map((impl) => (
            <motion.button
              key={impl.id}
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              onClick={() => loadBlockers(impl.id)}
              className={`w-full text-left p-4 border transition-colors ${
                selectedId === impl.id
                  ? 'border-brand-orange/40 bg-brand-orange/5'
                  : 'border-border-DEFAULT bg-[#0A0A0B] hover:border-brand-orange/20'
              }`}
            >
              <div className="flex items-center justify-between">
                <span className="text-sm font-semibold text-zinc-100">{impl.project_name}</span>
                <span className={`text-[10px] px-2 py-0.5  font-semibold ${STATE_COLORS[impl.state] || 'text-zinc-500 bg-zinc-500/10'}`}>
                  {impl.state}
                </span>
              </div>
              <div className="text-[10px] text-zinc-500 mt-1 flex gap-3">
                <span>PM: {impl.assigned_pm || 'Unassigned'}</span>
                {impl.target_go_live_date && <span>Go-Live: {new Date(impl.target_go_live_date).toLocaleDateString()}</span>}
              </div>
            </motion.button>
          ))}
        </div>

        {/* Blocker panel */}
        {selectedId && (
          <div className="w-96">
            <div className="bg-[#0A0A0B] border border-border-DEFAULT p-4 max-h-[600px] overflow-y-auto">
              <h3 className="text-sm font-bold uppercase tracking-widest text-zinc-500 mb-3">Blockers</h3>
              {blockers.length === 0 && <div className="text-xs text-zinc-500">No blockers</div>}
              {blockers.map((b) => (
                <div key={b.id} className="py-2 border-b border-white/5 last:border-0">
                  <div className="flex items-center justify-between">
                    <span className="text-xs font-semibold text-zinc-100">{b.title}</span>
                    <SeverityBadge
                      severity={normalizeSeverity(b.severity)}
                      size="sm"
                      label={normalizeSeverity(b.severity)}
                    />
                  </div>
                  <div className="text-[10px] text-zinc-500 mt-0.5">Status: {b.status} · {new Date(b.created_at).toLocaleDateString()}</div>
                </div>
              ))}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
