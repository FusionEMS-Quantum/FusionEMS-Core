'use client';

import { useEffect, useState } from 'react';
import { motion } from 'framer-motion';
import { listTenantConfigurations, setTenantConfiguration, listSystemConfigurations, getConfigCompleteness } from '@/services/api';

interface TenantConfig {
  id: string;
  tenant_id: string;
  config_key: string;
  config_value: string;
  description: string;
  updated_at: string;
}

interface SystemConfig {
  id: string;
  config_key: string;
  config_value: string;
  description: string;
  is_sensitive: boolean;
  updated_at: string;
}

interface ConfigCompleteness {
  total_required: number;
  total_present: number;
  completeness_pct: number;
  missing_keys: string[];
}

export default function ConfigurationPage() {
  const [tenantId, setTenantId] = useState('');
  const [tenantConfigs, setTenantConfigs] = useState<TenantConfig[]>([]);
  const [systemConfigs, setSystemConfigs] = useState<SystemConfig[]>([]);
  const [completeness, setCompleteness] = useState<ConfigCompleteness | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // New config form
  const [newKey, setNewKey] = useState('');
  const [newValue, setNewValue] = useState('');
  const [newDesc, setNewDesc] = useState('');

  useEffect(() => {
    async function loadSystem() {
      try {
        const data = await listSystemConfigurations();
        setSystemConfigs(data);
      } catch {
        // OK if no system configs
      }
    }
    loadSystem();
  }, []);

  async function loadTenantData() {
    if (!tenantId) return;
    setLoading(true);
    setError(null);
    try {
      const [configs, report] = await Promise.all([
        listTenantConfigurations(tenantId),
        getConfigCompleteness(tenantId),
      ]);
      setTenantConfigs(configs);
      setCompleteness(report);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : 'Failed to load tenant config');
    } finally {
      setLoading(false);
    }
  }

  async function handleSetConfig() {
    if (!tenantId || !newKey || !newValue) return;
    try {
      await setTenantConfiguration({ tenant_id: tenantId, config_key: newKey, config_value: newValue, description: newDesc });
      setNewKey('');
      setNewValue('');
      setNewDesc('');
      await loadTenantData();
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : 'Failed to set config');
    }
  }

  return (
    <div className="p-6 space-y-6">
      <div className="hud-rail pb-2">
        <h1 className="text-h1 font-bold text-text-primary">System Configuration</h1>
        <p className="text-body text-text-muted mt-1">Manage tenant and system-level configuration keys</p>
      </div>

      {/* Tenant Config Loader */}
      <div className="bg-bg-panel border border-border-DEFAULT p-4 space-y-3">
        <h2 className="text-sm font-bold uppercase tracking-widest text-text-muted">Tenant Configuration</h2>
        <div className="flex gap-2">
          <input
            value={tenantId}
            onChange={(e) => setTenantId(e.target.value)}
            placeholder="Enter tenant ID…"
            className="flex-1 bg-bg-surface border border-border-DEFAULT p-2 text-sm text-text-primary"
          />
          <button onClick={loadTenantData} disabled={loading || !tenantId}
            className="px-4 py-2 bg-brand-orange text-text-inverse text-sm font-semibold disabled:opacity-40">
            {loading ? 'Loading…' : 'Load Config'}
          </button>
        </div>
      </div>

      {error && <div className="text-red-400 text-sm">{error}</div>}

      {/* Completeness Report */}
      {completeness && (
        <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} className="bg-bg-panel border border-border-DEFAULT p-4">
          <h3 className="text-sm font-bold uppercase tracking-widest text-text-muted mb-3">Configuration Completeness</h3>
          <div className="flex items-center gap-4 mb-2">
            <div className="flex-1 bg-bg-surface h-3 rounded-sm overflow-hidden">
              <div
                className="h-full transition-all"
                style={{
                  width: `${completeness.completeness_pct}%`,
                  backgroundColor: completeness.completeness_pct === 100 ? 'var(--color-status-active)' :
                    completeness.completeness_pct >= 70 ? 'var(--color-status-warning)' : 'var(--color-brand-red)',
                }}
              />
            </div>
            <span className="text-sm font-bold text-text-primary">{completeness.completeness_pct}%</span>
          </div>
          <div className="text-[10px] text-text-muted">
            {completeness.total_present} / {completeness.total_required} keys set
          </div>
          {completeness.missing_keys.length > 0 && (
            <div className="mt-2">
              <span className="text-[10px] text-orange-400 font-semibold">Missing: </span>
              <span className="text-[10px] text-text-muted">{completeness.missing_keys.join(', ')}</span>
            </div>
          )}
        </motion.div>
      )}

      {/* Tenant Config Keys */}
      {tenantConfigs.length > 0 && (
        <div className="space-y-1">
          <h3 className="text-sm font-bold uppercase tracking-widest text-text-muted mb-2">Tenant Keys</h3>
          {tenantConfigs.map((c) => (
            <div key={c.id} className="bg-bg-panel border border-border-DEFAULT p-3 flex items-center justify-between">
              <div>
                <span className="text-xs font-mono font-semibold text-text-primary">{c.config_key}</span>
                <span className="text-xs text-text-muted ml-2">= {c.config_value}</span>
              </div>
              <span className="text-[10px] text-text-muted">{new Date(c.updated_at).toLocaleDateString()}</span>
            </div>
          ))}
        </div>
      )}

      {/* Add Tenant Config */}
      {tenantId && (
        <div className="bg-bg-panel border border-border-DEFAULT p-4 space-y-3">
          <h3 className="text-sm font-bold uppercase tracking-widest text-text-muted">Set Tenant Configuration</h3>
          <div className="grid grid-cols-3 gap-2">
            <input value={newKey} onChange={(e) => setNewKey(e.target.value)} placeholder="Config key"
              className="bg-bg-surface border border-border-DEFAULT p-2 text-sm text-text-primary" />
            <input value={newValue} onChange={(e) => setNewValue(e.target.value)} placeholder="Config value"
              className="bg-bg-surface border border-border-DEFAULT p-2 text-sm text-text-primary" />
            <input value={newDesc} onChange={(e) => setNewDesc(e.target.value)} placeholder="Description (optional)"
              className="bg-bg-surface border border-border-DEFAULT p-2 text-sm text-text-primary" />
          </div>
          <button onClick={handleSetConfig} disabled={!newKey || !newValue}
            className="px-4 py-2 bg-brand-orange text-text-inverse text-sm font-semibold disabled:opacity-40">
            Set Config
          </button>
        </div>
      )}

      {/* System Configurations */}
      <div className="space-y-1">
        <h3 className="text-sm font-bold uppercase tracking-widest text-text-muted mb-2">System Configurations</h3>
        {systemConfigs.length === 0 && <div className="text-xs text-text-muted">No system configurations</div>}
        {systemConfigs.map((c) => (
          <div key={c.id} className="bg-bg-panel border border-border-DEFAULT p-3 flex items-center justify-between">
            <div>
              <span className="text-xs font-mono font-semibold text-text-primary">{c.config_key}</span>
              <span className="text-xs text-text-muted ml-2">= {c.is_sensitive ? '••••••••' : c.config_value}</span>
            </div>
            <div className="flex items-center gap-2">
              {c.is_sensitive && <span className="text-[9px] px-1.5 py-0.5 bg-red-400/10 text-red-400 font-bold">SENSITIVE</span>}
              <span className="text-[10px] text-text-muted">{new Date(c.updated_at).toLocaleDateString()}</span>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
