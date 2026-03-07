'use client';
import { useEffect, useState, useCallback } from 'react';
import Link from 'next/link';
import { motion } from 'framer-motion';
import { listImplementations, listMilestones } from '@/services/api';

interface Implementation {
  id: string;
  name: string;
  state: string;
  owner_user_id: string;
  target_go_live_date: string | null;
  actual_go_live_date: string | null;
  notes: string | null;
  created_at: string;
}

interface Milestone {
  id: string;
  name: string;
  status: string;
  due_date: string;
  owner_user_id: string;
}

const STATE_COLORS: Record<string, string> = {
  DISCOVERY: 'text-blue-400',
  PLANNING: 'text-blue-300',
  CONFIGURATION: 'text-cyan-400',
  DATA_MIGRATION: 'text-purple-400',
  TRAINING: 'text-yellow-400',
  PARALLEL_OPS: 'text-orange-400',
  GO_LIVE_REVIEW: 'text-orange-dim',
  LIVE: 'text-green-400',
  STABILIZATION: 'text-green-300',
};

export default function ImplementationsPage() {
  const [projects, setProjects] = useState<Implementation[]>([]);
  const [stateFilter, setStateFilter] = useState<string>('');
  const [selectedProject, setSelectedProject] = useState<string | null>(null);
  const [milestones, setMilestones] = useState<Milestone[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    try {
      setLoading(true);
      const data = await listImplementations(stateFilter || undefined);
      setProjects(data);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : 'Failed to load implementations');
    } finally {
      setLoading(false);
    }
  }, [stateFilter]);

  useEffect(() => { load(); }, [load]);

  async function loadMilestones(projectId: string) {
    setSelectedProject(projectId);
    try {
      const data = await listMilestones(projectId);
      setMilestones(data);
    } catch {
      setMilestones([]);
    }
  }

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
        <div className="text-micro font-bold uppercase tracking-[0.2em] text-orange-dim mb-1">SUCCESS · IMPLEMENTATION</div>
        <h1 className="text-xl font-black uppercase tracking-wider text-text-primary">Implementation Services</h1>
        <p className="text-xs text-text-muted mt-0.5">Project plans · milestones · go-live approvals · stabilization</p>
      </div>

      {/* State Filter */}
      <div className="flex items-center gap-2 flex-wrap">
        <span className="text-xs text-text-muted">Filter:</span>
        {['', 'DISCOVERY', 'PLANNING', 'CONFIGURATION', 'DATA_MIGRATION', 'TRAINING', 'GO_LIVE_REVIEW', 'LIVE', 'STABILIZATION'].map((s) => (
          <button key={s} onClick={() => setStateFilter(s)}
            className={`text-micro px-2 py-1 border ${stateFilter === s ? 'border-orange-dim text-orange-dim bg-orange-dim/10' : 'border-border-DEFAULT text-text-muted hover:text-text-primary'} transition-colors`}>
            {s || 'ALL'}
          </button>
        ))}
      </div>

      {loading ? (
        <div className="space-y-2 animate-pulse">
          {Array.from({ length: 3 }).map((_, i) => (
            <div key={i} className="h-16 bg-bg-panel rounded" />
          ))}
        </div>
      ) : projects.length === 0 ? (
        <div className="bg-bg-panel border border-border-DEFAULT p-8 text-center text-text-muted text-sm">
          No implementation projects found{stateFilter ? ` in state ${stateFilter}` : ''}.
        </div>
      ) : (
        <div className="space-y-2">
          {projects.map((p, i) => (
            <motion.div key={p.id} initial={{ opacity: 0, y: 6 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: i * 0.04 }}>
              <div className="bg-bg-panel border border-border-DEFAULT p-4 hover:border-white/[0.18] transition-colors cursor-pointer"
                onClick={() => loadMilestones(p.id)}>
                <div className="flex items-center justify-between">
                  <div>
                    <div className="text-sm font-bold text-text-primary">{p.name}</div>
                    <div className="text-xs text-text-muted mt-0.5">
                      Owner: {p.owner_user_id.slice(0, 8)}...
                      {p.target_go_live_date && <> · Target: {new Date(p.target_go_live_date).toLocaleDateString()}</>}
                    </div>
                  </div>
                  <div className={`text-micro font-bold ${STATE_COLORS[p.state] || 'text-text-muted'}`}>{p.state}</div>
                </div>
                {p.notes && <div className="text-xs text-text-muted mt-2 border-t border-border-DEFAULT pt-2">{p.notes}</div>}
              </div>

              {/* Milestones Panel */}
              {selectedProject === p.id && (
                <motion.div initial={{ opacity: 0, height: 0 }} animate={{ opacity: 1, height: 'auto' }}
                  className="bg-bg-panel/50 border-x border-b border-border-DEFAULT p-4 space-y-2">
                  <div className="text-micro font-bold text-orange-dim">MILESTONES</div>
                  {milestones.length === 0 ? (
                    <div className="text-xs text-text-muted">No milestones defined yet.</div>
                  ) : milestones.map((m) => (
                    <div key={m.id} className="flex items-center justify-between text-xs border-b border-border-DEFAULT pb-1">
                      <div>
                        <span className="text-text-primary font-bold">{m.name}</span>
                        <span className="text-text-muted ml-2">Due: {new Date(m.due_date).toLocaleDateString()}</span>
                      </div>
                      <span className={`font-bold ${m.status === 'COMPLETED' ? 'text-green-400' : m.status === 'BLOCKED' ? 'text-red-400' : 'text-yellow-400'}`}>
                        {m.status}
                      </span>
                    </div>
                  ))}
                </motion.div>
              )}
            </motion.div>
          ))}
        </div>
      )}

      <Link href="/founder/success-command" className="text-xs text-orange-dim hover:text-orange">← Back to Success Command Center</Link>
    </div>
  );
}
