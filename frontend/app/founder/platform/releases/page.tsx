'use client';

import { useEffect, useState } from 'react';
import { motion } from 'framer-motion';
import { listPlatformEnvironments, listPlatformReleases, listConfigDriftAlerts, createPlatformRelease } from '@/services/api';
import { SeverityBadge } from '@/components/ui';
import { normalizeSeverity } from '@/lib/design-system/severity';

interface Environment {
  id: string;
  name: string;
  display_name: string;
  health_status: string;
  current_version: string | null;
  current_git_sha: string | null;
  is_production: boolean;
}

interface Release {
  id: string;
  version_tag: string;
  git_sha: string;
  release_notes: string;
  released_by: string;
  created_at: string;
}

interface DriftAlert {
  id: string;
  environment_id: string;
  drift_type: string;
  description: string;
  severity: string;
  expected_value: string;
  actual_value: string;
  resolved: boolean;
  created_at: string;
}

const HEALTH_COLORS: Record<string, string> = {
  healthy: 'text-green-400 bg-green-400/10 border-green-400/30',
  degraded: 'text-[#FF4D00]-400 bg-[#FF4D00]-400/10 border-orange-400/30',
  down: 'text-red-400 bg-red-400/10 border-red-400/30',
};

export default function ReleasesPage() {
  const [environments, setEnvironments] = useState<Environment[]>([]);
  const [releases, setReleases] = useState<Release[]>([]);
  const [driftAlerts, setDriftAlerts] = useState<DriftAlert[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Create release form
  const [showCreate, setShowCreate] = useState(false);
  const [newRelease, setNewRelease] = useState({ version_tag: '', git_sha: '', release_notes: '' });

  useEffect(() => {
    async function load() {
      try {
        const [envs, rels, drifts] = await Promise.all([
          listPlatformEnvironments(),
          listPlatformReleases(),
          listConfigDriftAlerts(),
        ]);
        setEnvironments(envs);
        setReleases(rels);
        setDriftAlerts(drifts);
      } catch (err: unknown) {
        setError(err instanceof Error ? err.message : 'Failed to load release data');
      } finally {
        setLoading(false);
      }
    }
    load();
  }, []);

  async function handleCreateRelease() {
    try {
      await createPlatformRelease(newRelease);
      const rels = await listPlatformReleases();
      setReleases(rels);
      setShowCreate(false);
      setNewRelease({ version_tag: '', git_sha: '', release_notes: '' });
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : 'Failed to create release');
    }
  }

  if (loading) return <div className="p-6 text-zinc-500 animate-pulse">Loading releases…</div>;
  if (error) return <div className="p-6 text-red-400 text-sm">{error}</div>;

  return (
    <div className="p-6 space-y-6">
      <div className="flex items-center justify-between hud-rail pb-2">
        <div>
          <h1 className="text-h1 font-bold text-zinc-100">Releases & Environments</h1>
          <p className="text-body text-zinc-500 mt-1">Environment health, release versions, and configuration drift</p>
        </div>
        <button onClick={() => setShowCreate(!showCreate)} className="px-4 py-2 bg-brand-orange text-black text-sm font-semibold">
          {showCreate ? 'Cancel' : '+ New Release'}
        </button>
      </div>

      {/* Create Release */}
      {showCreate && (
        <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} className="bg-[#0A0A0B] border border-border-DEFAULT p-4 space-y-3">
          <div className="grid grid-cols-2 gap-3">
            <input value={newRelease.version_tag} onChange={(e) => setNewRelease({ ...newRelease, version_tag: e.target.value })}
              placeholder="Version tag (e.g., v2.4.0)" className="bg-bg-surface border border-border-DEFAULT p-2 text-sm text-zinc-100" />
            <input value={newRelease.git_sha} onChange={(e) => setNewRelease({ ...newRelease, git_sha: e.target.value })}
              placeholder="Git SHA" className="bg-bg-surface border border-border-DEFAULT p-2 text-sm text-zinc-100" />
          </div>
          <textarea value={newRelease.release_notes} onChange={(e) => setNewRelease({ ...newRelease, release_notes: e.target.value })}
            placeholder="Release notes" className="w-full bg-bg-surface border border-border-DEFAULT p-2 text-sm text-zinc-100 h-20 resize-none" />
          <button onClick={handleCreateRelease} className="px-4 py-2 bg-brand-orange text-black text-sm font-semibold">Create Release</button>
        </motion.div>
      )}

      {/* Environments */}
      <div>
        <h2 className="text-sm font-bold uppercase tracking-widest text-zinc-500 mb-3">Environments</h2>
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-3">
          {environments.map((env) => (
            <motion.div key={env.id} initial={{ opacity: 0, y: 4 }} animate={{ opacity: 1, y: 0 }}
              className={`p-4 border ${HEALTH_COLORS[env.health_status] || 'text-zinc-500 border-border-DEFAULT bg-[#0A0A0B]'}`}>
              <div className="flex items-center justify-between mb-2">
                <span className="text-sm font-bold">{env.display_name}</span>
                {env.is_production && <span className="text-[9px] px-1.5 py-0.5 bg-red-400/10 text-red-400 font-bold">PROD</span>}
              </div>
              <div className="text-[10px] text-zinc-500 space-y-0.5">
                <div>Status: <span className="font-semibold">{env.health_status}</span></div>
                {env.current_version && <div>Version: {env.current_version}</div>}
                {env.current_git_sha && <div>SHA: {env.current_git_sha.slice(0, 8)}</div>}
              </div>
            </motion.div>
          ))}
        </div>
      </div>

      {/* Releases */}
      <div>
        <h2 className="text-sm font-bold uppercase tracking-widest text-zinc-500 mb-3">Releases</h2>
        <div className="space-y-2">
          {releases.length === 0 && <div className="text-xs text-zinc-500">No releases recorded</div>}
          {releases.map((r) => (
            <div key={r.id} className="bg-[#0A0A0B] border border-border-DEFAULT p-3 flex items-center justify-between">
              <div>
                <span className="text-sm font-mono font-bold text-zinc-100">{r.version_tag}</span>
                <span className="text-[10px] text-zinc-500 ml-3">{r.git_sha.slice(0, 8)}</span>
              </div>
              <div className="text-[10px] text-zinc-500">{new Date(r.created_at).toLocaleDateString()} · {r.released_by}</div>
            </div>
          ))}
        </div>
      </div>

      {/* Config Drift Alerts */}
      <div>
        <h2 className="text-sm font-bold uppercase tracking-widest text-zinc-500 mb-3">
          Configuration Drift Alerts
          {driftAlerts.filter((d) => !d.resolved).length > 0 && (
            <span className="ml-2 text-red-400">({driftAlerts.filter((d) => !d.resolved).length} unresolved)</span>
          )}
        </h2>
        <div className="space-y-2">
          {driftAlerts.length === 0 && <div className="text-xs text-zinc-500">No drift alerts</div>}
          {driftAlerts.filter((d) => !d.resolved).map((d) => (
            <div key={d.id} className="bg-[#0A0A0B] border border-orange-400/30 p-3">
              <div className="flex items-center justify-between">
                <span className="text-xs font-semibold text-zinc-100">{d.drift_type}</span>
                <SeverityBadge
                  severity={normalizeSeverity(d.severity)}
                  size="sm"
                  label={normalizeSeverity(d.severity)}
                />
              </div>
              <div className="text-[10px] text-zinc-500 mt-1">{d.description}</div>
              <div className="text-[10px] text-zinc-500 mt-0.5">
                Expected: <span className="text-zinc-400">{d.expected_value}</span> ·
                Actual: <span className="text-[#FF4D00]-400">{d.actual_value}</span>
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
