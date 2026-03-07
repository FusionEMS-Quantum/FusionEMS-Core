'use client';

import { useEffect, useState } from 'react';
import { motion } from 'framer-motion';
import { listPlatformFeatureFlags, createPlatformFeatureFlag, listTenantFeatureStates, setTenantFeatureState } from '@/services/api';

interface FeatureFlag {
  id: string;
  flag_key: string;
  display_name: string;
  description: string;
  module: string;
  is_critical: boolean;
  default_state: string;
  created_at: string;
}

interface TenantFeatureState {
  id: string;
  tenant_id: string;
  feature_flag_id: string;
  current_state: string;
  changed_by: string;
  reason: string;
  updated_at: string;
}

const FLAG_STATES = ['DISABLED', 'ENABLED', 'LIMITED_ROLLOUT', 'BETA_ENABLED', 'KILL_SWITCH'];

export default function FeatureFlagsPage() {
  const [flags, setFlags] = useState<FeatureFlag[]>([]);
  const [tenantStates, setTenantStates] = useState<TenantFeatureState[]>([]);
  const [selectedFlag, setSelectedFlag] = useState<FeatureFlag | null>(null);
  const [tenantId, setTenantId] = useState('');
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Create flag form
  const [showCreate, setShowCreate] = useState(false);
  const [newFlag, setNewFlag] = useState({ flag_key: '', display_name: '', description: '', module: '', is_critical: false, default_state: 'DISABLED' });

  useEffect(() => {
    async function load() {
      try {
        const data = await listPlatformFeatureFlags();
        setFlags(data);
      } catch (err: unknown) {
        setError(err instanceof Error ? err.message : 'Failed to load feature flags');
      } finally {
        setLoading(false);
      }
    }
    load();
  }, []);

  async function handleCreateFlag() {
    try {
      await createPlatformFeatureFlag(newFlag);
      const data = await listPlatformFeatureFlags();
      setFlags(data);
      setShowCreate(false);
      setNewFlag({ flag_key: '', display_name: '', description: '', module: '', is_critical: false, default_state: 'DISABLED' });
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : 'Failed to create flag');
    }
  }

  async function loadTenantStates() {
    if (!tenantId) return;
    try {
      const data = await listTenantFeatureStates(tenantId);
      setTenantStates(data);
    } catch {
      setTenantStates([]);
    }
  }

  async function toggleState(featureFlagId: string, newState: string) {
    if (!tenantId) return;
    try {
      await setTenantFeatureState({ tenant_id: tenantId, feature_flag_id: featureFlagId, new_state: newState, reason: 'Toggled via admin UI' });
      await loadTenantStates();
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : 'Failed to update state');
    }
  }

  if (loading) {
    return <div className="p-6 text-text-muted animate-pulse">Loading feature flags…</div>;
  }
  if (error) {
    return <div className="p-6 text-red-400 text-sm">{error}</div>;
  }

  return (
    <div className="p-6 space-y-6">
      <div className="flex items-center justify-between hud-rail pb-2">
        <div>
          <h1 className="text-h1 font-bold text-text-primary">Feature Flags</h1>
          <p className="text-body text-text-muted mt-1">Control feature rollout across tenants</p>
        </div>
        <button
          onClick={() => setShowCreate(!showCreate)}
          className="px-4 py-2 bg-brand-orange text-text-inverse text-sm font-semibold"
        >
          {showCreate ? 'Cancel' : '+ New Flag'}
        </button>
      </div>

      {/* Create Flag Form */}
      {showCreate && (
        <motion.div initial={{ opacity: 0, height: 0 }} animate={{ opacity: 1, height: 'auto' }}
          className="bg-bg-panel border border-border-DEFAULT p-4 space-y-3">
          <div className="grid grid-cols-2 gap-3">
            <input value={newFlag.flag_key} onChange={(e) => setNewFlag({ ...newFlag, flag_key: e.target.value })}
              placeholder="Flag key (e.g., billing_v2)" className="bg-bg-surface border border-border-DEFAULT p-2 text-sm text-text-primary" />
            <input value={newFlag.display_name} onChange={(e) => setNewFlag({ ...newFlag, display_name: e.target.value })}
              placeholder="Display name" className="bg-bg-surface border border-border-DEFAULT p-2 text-sm text-text-primary" />
            <input value={newFlag.module} onChange={(e) => setNewFlag({ ...newFlag, module: e.target.value })}
              placeholder="Module" className="bg-bg-surface border border-border-DEFAULT p-2 text-sm text-text-primary" />
            <select value={newFlag.default_state} onChange={(e) => setNewFlag({ ...newFlag, default_state: e.target.value })}
              className="bg-bg-surface border border-border-DEFAULT p-2 text-sm text-text-primary">
              {FLAG_STATES.map((s) => <option key={s} value={s}>{s}</option>)}
            </select>
          </div>
          <textarea value={newFlag.description} onChange={(e) => setNewFlag({ ...newFlag, description: e.target.value })}
            placeholder="Description" className="w-full bg-bg-surface border border-border-DEFAULT p-2 text-sm text-text-primary h-16 resize-none" />
          <div className="flex items-center gap-4">
            <label className="flex items-center gap-2 text-xs text-text-secondary">
              <input type="checkbox" checked={newFlag.is_critical} onChange={(e) => setNewFlag({ ...newFlag, is_critical: e.target.checked })} />
              Critical flag
            </label>
            <button onClick={handleCreateFlag} className="px-4 py-2 bg-brand-orange text-text-inverse text-sm font-semibold">Create Flag</button>
          </div>
        </motion.div>
      )}

      {/* Flag List */}
      <div className="space-y-2">
        {flags.map((f) => (
          <button
            key={f.id}
            onClick={() => setSelectedFlag(f)}
            className={`w-full text-left p-3 border transition-colors ${
              selectedFlag?.id === f.id ? 'border-brand-orange/40 bg-brand-orange/5' : 'border-border-DEFAULT bg-bg-panel hover:border-brand-orange/20'
            }`}
          >
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2">
                <span className="text-sm font-mono font-semibold text-text-primary">{f.flag_key}</span>
                {f.is_critical && <span className="text-[9px] px-1.5 py-0.5 bg-red-400/10 text-red-400 font-bold">CRITICAL</span>}
              </div>
              <span className={`text-[10px] px-2 py-0.5 font-semibold ${
                f.default_state === 'ENABLED' ? 'text-green-400 bg-green-400/10' :
                f.default_state === 'KILL_SWITCH' ? 'text-red-400 bg-red-400/10' :
                'text-yellow-400 bg-yellow-400/10'
              }`}>{f.default_state}</span>
            </div>
            <div className="text-[10px] text-text-muted mt-1">{f.display_name} · {f.module}</div>
          </button>
        ))}
      </div>

      {/* Tenant-scoped feature states */}
      <div className="bg-bg-panel border border-border-DEFAULT p-4 space-y-3">
        <h2 className="text-sm font-bold uppercase tracking-widest text-text-muted">Tenant Feature States</h2>
        <div className="flex gap-2">
          <input
            value={tenantId}
            onChange={(e) => setTenantId(e.target.value)}
            placeholder="Enter tenant ID…"
            className="flex-1 bg-bg-surface border border-border-DEFAULT p-2 text-sm text-text-primary"
          />
          <button onClick={loadTenantStates} className="px-4 py-2 bg-brand-orange text-text-inverse text-sm font-semibold">Load</button>
        </div>
        {tenantStates.length > 0 && (
          <div className="space-y-1">
            {tenantStates.map((ts) => (
              <div key={ts.id} className="flex items-center justify-between p-2 border-b border-white/5">
                <span className="text-xs text-text-secondary">{ts.feature_flag_id}</span>
                <div className="flex items-center gap-2">
                  <span className={`text-[10px] font-semibold ${
                    ts.current_state === 'ENABLED' ? 'text-green-400' :
                    ts.current_state === 'KILL_SWITCH' ? 'text-red-400' :
                    'text-yellow-400'
                  }`}>{ts.current_state}</span>
                  <select
                    onChange={(e) => toggleState(ts.feature_flag_id, e.target.value)}
                    defaultValue=""
                    className="bg-bg-surface border border-border-DEFAULT p-1 text-[10px] text-text-primary"
                  >
                    <option value="" disabled>Change…</option>
                    {FLAG_STATES.filter((s) => s !== ts.current_state).map((s) => (
                      <option key={s} value={s}>{s}</option>
                    ))}
                  </select>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
