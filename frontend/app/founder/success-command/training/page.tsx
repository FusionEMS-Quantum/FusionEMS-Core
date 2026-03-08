'use client';
import { useEffect, useState, useCallback } from 'react';
import Link from 'next/link';
import { motion } from 'framer-motion';
import { listTrainingTracks, listTrainingAssignments } from '@/services/api';

interface Track {
  id: string;
  name: string;
  description: string;
  target_role: string;
  module_type: string;
  estimated_duration_minutes: number;
  is_active: boolean;
  created_at: string;
}

interface Assignment {
  id: string;
  track_id: string;
  user_id: string;
  status: string;
  progress_pct: number;
  due_date: string | null;
  completed_at: string | null;
  created_at: string;
}

const STATUS_COLOR: Record<string, string> = {
  ASSIGNED: 'text-blue-400',
  IN_PROGRESS: 'text-yellow-400',
  COMPLETED: 'text-green-400',
  VERIFIED: 'text-cyan-400',
  OVERDUE: 'text-red-400',
  WAIVED: 'text-zinc-500',
};

export default function TrainingPage() {
  const [tracks, setTracks] = useState<Track[]>([]);
  const [assignments, setAssignments] = useState<Assignment[]>([]);
  const [roleFilter, setRoleFilter] = useState<string>('');
  const [statusFilter, setStatusFilter] = useState<string>('');
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    try {
      setLoading(true);
      const [t, a] = await Promise.all([
        listTrainingTracks(roleFilter || undefined),
        listTrainingAssignments(undefined, statusFilter || undefined),
      ]);
      setTracks(t);
      setAssignments(a);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : 'Failed to load training data');
    } finally {
      setLoading(false);
    }
  }, [roleFilter, statusFilter]);

  useEffect(() => { load(); }, [load]);

  if (error) {
    return (
      <div className="p-5">
        <div className="bg-red-500/10 border border-red-500/30 p-4 text-red-400 text-sm">{error}</div>
      </div>
    );
  }

  const assignmentsByTrack = assignments.reduce<Record<string, Assignment[]>>((acc, a) => {
    if (!acc[a.track_id]) acc[a.track_id] = [];
    acc[a.track_id].push(a);
    return acc;
  }, {});

  return (
    <div className="p-5 space-y-6">
      <div>
        <div className="text-micro font-bold uppercase tracking-[0.2em] text-[#FF4D00]-dim mb-1">SUCCESS · TRAINING</div>
        <h1 className="text-xl font-black uppercase tracking-wider text-zinc-100">Training & Enablement</h1>
        <p className="text-xs text-zinc-500 mt-0.5">Tracks · assignments · completions · verifications</p>
      </div>

      {/* Filters */}
      <div className="flex items-center gap-4 flex-wrap">
        <div className="flex items-center gap-2">
          <span className="text-xs text-zinc-500">Role:</span>
          {['', 'MEDIC', 'DISPATCHER', 'SUPERVISOR', 'ADMIN', 'BILLING_SPECIALIST', 'PILOT'].map((r) => (
            <button key={r} onClick={() => setRoleFilter(r)}
              className={`text-micro px-2 py-1 border ${roleFilter === r ? 'border-orange-dim text-[#FF4D00]-dim bg-[#FF4D00]-dim/10' : 'border-border-DEFAULT text-zinc-500 hover:text-zinc-100'} transition-colors`}>
              {r || 'ALL'}
            </button>
          ))}
        </div>
        <div className="flex items-center gap-2">
          <span className="text-xs text-zinc-500">Status:</span>
          {['', 'ASSIGNED', 'IN_PROGRESS', 'COMPLETED', 'VERIFIED', 'OVERDUE'].map((s) => (
            <button key={s} onClick={() => setStatusFilter(s)}
              className={`text-micro px-2 py-1 border ${statusFilter === s ? 'border-orange-dim text-[#FF4D00]-dim bg-[#FF4D00]-dim/10' : 'border-border-DEFAULT text-zinc-500 hover:text-zinc-100'} transition-colors`}>
              {s || 'ALL'}
            </button>
          ))}
        </div>
      </div>

      {loading ? (
        <div className="space-y-3 animate-pulse">
          {Array.from({ length: 3 }).map((_, i) => (
            <div key={i} className="h-24 bg-[#0A0A0B] " />
          ))}
        </div>
      ) : tracks.length === 0 ? (
        <div className="bg-[#0A0A0B] border border-border-DEFAULT p-8 text-center text-zinc-500 text-sm">
          No training tracks found.
        </div>
      ) : (
        <div className="space-y-3">
          {tracks.map((track, i) => {
            const trackAssignments = assignmentsByTrack[track.id] || [];
            const completedCount = trackAssignments.filter((a) => a.status === 'COMPLETED' || a.status === 'VERIFIED').length;
            const completionRate = trackAssignments.length > 0 ? (completedCount / trackAssignments.length) * 100 : 0;

            return (
              <motion.div key={track.id} initial={{ opacity: 0, y: 6 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: i * 0.05 }}
                className="bg-[#0A0A0B] border border-border-DEFAULT p-4">
                <div className="flex items-center justify-between mb-2">
                  <div>
                    <div className="text-sm font-bold text-zinc-100">{track.name}</div>
                    <div className="text-xs text-zinc-500 mt-0.5">{track.description}</div>
                  </div>
                  <div className="text-right">
                    <div className="text-micro text-zinc-500">{track.target_role} · {track.module_type}</div>
                    <div className="text-micro text-zinc-500">{track.estimated_duration_minutes} min</div>
                  </div>
                </div>

                {/* Progress Bar */}
                <div className="flex items-center gap-2 mb-2">
                  <div className="flex-1 h-1.5 bg-[#0A0A0B]-muted  overflow-hidden">
                    <div className="h-full bg-green-400 transition-all" style={{ width: `${completionRate}%` }} />
                  </div>
                  <span className="text-micro text-zinc-500">{completionRate.toFixed(0)}% ({completedCount}/{trackAssignments.length})</span>
                </div>

                {/* Assignments Table */}
                {trackAssignments.length > 0 && (
                  <div className="space-y-1 mt-2">
                    {trackAssignments.map((a) => (
                      <div key={a.id} className="flex items-center justify-between text-xs border-t border-border-DEFAULT pt-1">
                        <div className="text-zinc-500">User: {a.user_id.slice(0, 8)}...</div>
                        <div className="flex items-center gap-3">
                          <span className="text-zinc-500">Progress: {a.progress_pct}%</span>
                          {a.due_date && <span className="text-zinc-500">Due: {new Date(a.due_date).toLocaleDateString()}</span>}
                          <span className={`font-bold ${STATUS_COLOR[a.status] || 'text-zinc-500'}`}>{a.status}</span>
                        </div>
                      </div>
                    ))}
                  </div>
                )}
              </motion.div>
            );
          })}
        </div>
      )}

      <Link href="/founder/success-command" className="text-xs text-[#FF4D00]-dim hover:text-[#FF4D00]">← Back to Success Command Center</Link>
    </div>
  );
}
