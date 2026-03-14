'use client';

import { useEffect, useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import Link from 'next/link';
import { listPolicies, createPolicy, updatePolicy, deletePolicy, getPolicyVersions, requestPolicyApproval, rollbackPolicy } from '@/services/api';

interface TenantPolicy {
  id: string;
  tenant_id: string;
  key: string;
  value: Record<string, unknown>;
  is_active: boolean;
  version: number;
  created_at: string;
  updated_at: string;
}

interface PolicyVersion {
  id: string;
  version_number: number;
  changed_by_user_id: string;
  change_reason: string | null;
  value_snapshot: Record<string, unknown>;
  created_at: string;
}

function StatusBadge({ active }: { active: boolean }) {
  return (
    <span className={`px-1.5 py-0.5 text-[10px] uppercase tracking-widest font-semibold border ${active ? 'border-green/40 text-green bg-green/10' : 'border-[var(--color-brand-red)]/40 text-[var(--color-brand-red)] bg-[var(--color-brand-red)]/10'}`}>
      {active ? 'Active' : 'Inactive'}
    </span>
  );
}

export default function PolicySandboxPage() {
  const [policies, setPolicies] = useState<TenantPolicy[]>([]);
  const [selected, setSelected] = useState<TenantPolicy | null>(null);
  const [versions, setVersions] = useState<PolicyVersion[]>([]);
  const [loading, setLoading] = useState(true);
  const [versionsLoading, setVersionsLoading] = useState(false);
  const [toast, setToast] = useState<{ msg: string; ok: boolean } | null>(null);

  // Create / edit form
  const [mode, setMode] = useState<'list' | 'create' | 'edit'>('list');
  const [formKey, setFormKey] = useState('');
  const [formValue, setFormValue] = useState('{}');
  const [formReason, setFormReason] = useState('');
  const [formValueError, setFormValueError] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);

  // Approval form
  const [showApprovalPanel, setShowApprovalPanel] = useState(false);
  const [approvalProposed, setApprovalProposed] = useState('{}');
  const [requestingApproval, setRequestingApproval] = useState(false);
  const [rollbackVersion, setRollbackVersion] = useState<number | null>(null);
  const [rollingBack, setRollingBack] = useState(false);

  const showToast = (msg: string, ok: boolean) => {
    setToast({ msg, ok });
    setTimeout(() => setToast(null), 5000);
  };

  const loadPolicies = async () => {
    setLoading(true);
    try {
      const data = await listPolicies();
      setPolicies(data);
    } catch { /* swallow */ } finally {
      setLoading(false);
    }
  };

  const loadVersions = async (policyId: string) => {
    setVersionsLoading(true);
    try {
      const data = await getPolicyVersions(policyId);
      setVersions(data);
    } catch { /* swallow */ } finally {
      setVersionsLoading(false);
    }
  };

  useEffect(() => { loadPolicies(); }, []);

  const selectPolicy = (p: TenantPolicy) => {
    setSelected(p);
    setMode('list');
    loadVersions(p.id);
  };

  const validateJson = (raw: string): Record<string, unknown> | null => {
    try {
      return JSON.parse(raw);
    } catch {
      return null;
    }
  };

  const openCreate = () => {
    setSelected(null);
    setFormKey('');
    setFormValue('{}');
    setFormReason('');
    setFormValueError(null);
    setMode('create');
  };

  const openEdit = () => {
    if (!selected) return;
    setFormKey(selected.key);
    setFormValue(JSON.stringify(selected.value, null, 2));
    setFormReason('');
    setFormValueError(null);
    setMode('edit');
  };

  const savePolicy = async () => {
    const parsed = validateJson(formValue);
    if (!parsed) { setFormValueError('Invalid JSON'); return; }
    setFormValueError(null);
    setSaving(true);
    try {
      let saved: TenantPolicy;
      if (mode === 'create') {
        saved = await createPolicy({ key: formKey, value: parsed, change_reason: formReason || null });
      } else {
        saved = await updatePolicy(selected!.id, { value: parsed, change_reason: formReason || null });
      }
      if (mode === 'create') {
        setPolicies(prev => [saved, ...prev]);
      } else {
        setPolicies(prev => prev.map(p => p.id === saved.id ? saved : p));
      }
      setSelected(saved);
      setMode('list');
      await loadVersions(saved.id);
      showToast(`Policy "${saved.key}" saved (v${saved.version}).`, true);
    } catch (e) {
      showToast(e instanceof Error ? e.message : 'Save failed', false);
    } finally {
      setSaving(false);
    }
  };

  const deactivatePolicy = async () => {
    if (!selected) return;
    try {
      await deletePolicy(selected.id);
      await loadPolicies();
      setSelected(null);
      setVersions([]);
      showToast('Policy deactivated.', true);
    } catch (e) {
      showToast(e instanceof Error ? e.message : 'Deactivate failed', false);
    }
  };

  const rollback = async () => {
    if (!selected || rollbackVersion === null) return;
    setRollingBack(true);
    try {
      const updated: TenantPolicy = await rollbackPolicy(selected.id, rollbackVersion);
      setPolicies(prev => prev.map(p => p.id === updated.id ? updated : p));
      setSelected(updated);
      await loadVersions(updated.id);
      setRollbackVersion(null);
      showToast(`Rolled back to version ${rollbackVersion}.`, true);
    } catch (e) {
      showToast(e instanceof Error ? e.message : 'Rollback failed', false);
    } finally {
      setRollingBack(false);
    }
  };

  const requestApproval = async () => {
    if (!selected) return;
    const parsed = validateJson(approvalProposed);
    if (!parsed) { showToast('Invalid JSON in proposed value', false); return; }
    setRequestingApproval(true);
    try {
      await requestPolicyApproval(selected.id, { proposed_value: parsed });
      setShowApprovalPanel(false);
      showToast('Approval request submitted.', true);
    } catch (e) {
      showToast(e instanceof Error ? e.message : 'Request failed', false);
    } finally {
      setRequestingApproval(false);
    }
  };

  return (
    <div className="p-5 min-h-screen">
      {/* Toast */}
      <AnimatePresence>
        {toast && (
          <motion.div initial={{ opacity: 0, y: -12 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0 }}
            className={`fixed top-4 right-4 z-50 px-4 py-3 border text-sm font-semibold max-w-sm ${toast.ok ? 'border-green text-green bg-green/10' : 'border-[var(--color-brand-red)] text-[var(--color-brand-red)] bg-[var(--color-brand-red)]/10'}`}
            style={{ clipPath: 'polygon(0 0, calc(100% - 8px) 0, 100% 8px, 100% 100%, 0 100%)' }}>
            {toast.msg}
          </motion.div>
        )}
      </AnimatePresence>

      {/* Header */}
      <div className="hud-rail pb-3 mb-6 flex items-end justify-between">
        <div>
          <div className="micro-caps mb-1 text-[var(--color-text-muted)]">Security</div>
          <h1 className="text-h2 font-bold text-[var(--color-text-primary)]">Policy Sandbox</h1>
          <p className="text-body text-[var(--color-text-muted)] mt-1">
            Manage tenant policies with versioning and two-person approval workflow.
          </p>
        </div>
        <div className="flex gap-2">
          <button onClick={openCreate}
            className="px-3 py-1.5 text-micro font-semibold uppercase tracking-widest bg-[var(--q-orange)] text-bg-page hover:bg-[#E64500] transition-colors">
            + New Policy
          </button>
          <Link href="/founder/security"
            className="px-3 py-1.5 text-micro font-semibold uppercase tracking-widest border border-border-DEFAULT text-[var(--color-text-muted)] hover:text-[var(--color-text-primary)] transition-colors">
            ← Security
          </Link>
        </div>
      </div>

      <div className="grid grid-cols-12 gap-4">
        {/* Policy list */}
        <div className="col-span-4">
          <div className="text-micro uppercase tracking-widest text-[var(--color-text-muted)] mb-2">Policies ({policies.length})</div>
          {loading ? (
            <div className="text-[var(--color-text-muted)] text-sm py-8 text-center">Loading…</div>
          ) : policies.length === 0 ? (
            <div className="text-[var(--color-text-muted)] text-sm py-8 text-center border border-border-DEFAULT p-4">No policies yet.</div>
          ) : (
            <div className="flex flex-col gap-1.5">
              {policies.map(p => (
                <motion.button key={p.id} whileHover={{ scale: 1.01 }}
                  onClick={() => selectPolicy(p)}
                  className={`w-full text-left p-3 border transition-colors ${selected?.id === p.id ? 'border-orange bg-[var(--q-orange)]/10' : 'border-border-DEFAULT hover:border-white/20 bg-[var(--color-bg-panel)]'}`}
                  style={{ clipPath: 'polygon(0 0, calc(100% - 6px) 0, 100% 6px, 100% 100%, 0 100%)' }}>
                  <div className="flex items-center gap-2 mb-1">
                    <span className="text-xs font-bold text-[var(--color-text-primary)] font-mono">{p.key}</span>
                    <StatusBadge active={p.is_active} />
                  </div>
                  <div className="text-micro text-[var(--color-text-muted)]">v{p.version} · {new Date(p.updated_at).toLocaleDateString()}</div>
                </motion.button>
              ))}
            </div>
          )}
        </div>

        {/* Detail / Editor panel */}
        <div className="col-span-8">
          {mode === 'list' && !selected && (
            <div className="bg-[var(--color-bg-panel)] border border-border-DEFAULT p-8 text-center text-[var(--color-text-muted)] text-sm"
              style={{ clipPath: 'polygon(0 0, calc(100% - 10px) 0, 100% 10px, 100% 100%, 0 100%)' }}>
              Select a policy or create a new one.
            </div>
          )}

          {/* Create / Edit form */}
          {(mode === 'create' || mode === 'edit') && (
            <div className="bg-[var(--color-bg-panel)] border border-border-DEFAULT p-4"
              style={{ clipPath: 'polygon(0 0, calc(100% - 10px) 0, 100% 10px, 100% 100%, 0 100%)' }}>
              <div className="text-micro uppercase tracking-widest text-[var(--q-orange)] mb-4">
                {mode === 'create' ? 'New Policy' : `Edit — ${selected?.key}`}
              </div>
              {mode === 'create' && (
                <div className="mb-3">
                  <label className="text-micro text-[var(--color-text-muted)] block mb-1">Policy Key</label>
                  <input value={formKey} onChange={e => setFormKey(e.target.value)} placeholder="e.g. mfa.required"
                    className="w-full bg-bg-page border border-border-DEFAULT px-3 py-2 text-xs font-mono text-[var(--color-text-primary)] focus:outline-none focus:border-orange" />
                </div>
              )}
              <div className="mb-3">
                <label className="text-micro text-[var(--color-text-muted)] block mb-1">Value (JSON)</label>
                <textarea rows={8} value={formValue} onChange={e => setFormValue(e.target.value)}
                  className={`w-full bg-bg-page border px-3 py-2 text-xs font-mono text-[var(--color-text-primary)] focus:outline-none resize-none ${formValueError ? 'border-[var(--color-brand-red)]' : 'border-border-DEFAULT focus:border-orange'}`} />
                {formValueError && <p className="text-micro text-[var(--color-brand-red)] mt-1">{formValueError}</p>}
              </div>
              <div className="mb-4">
                <label className="text-micro text-[var(--color-text-muted)] block mb-1">Change Reason (optional)</label>
                <input value={formReason} onChange={e => setFormReason(e.target.value)} placeholder="Summarize the change…"
                  className="w-full bg-bg-page border border-border-DEFAULT px-3 py-2 text-xs text-[var(--color-text-primary)] focus:outline-none focus:border-orange" />
              </div>
              <div className="flex gap-2">
                <button onClick={savePolicy} disabled={saving || !formKey.trim()}
                  className="px-4 py-2 text-micro font-semibold uppercase tracking-widest bg-[var(--q-orange)] text-bg-page hover:bg-[#E64500] transition-colors disabled:opacity-50">
                  {saving ? 'Saving…' : 'Save'}
                </button>
                <button onClick={() => setMode('list')}
                  className="px-4 py-2 text-micro font-semibold uppercase tracking-widest border border-border-DEFAULT text-[var(--color-text-muted)] hover:text-[var(--color-text-primary)] transition-colors">
                  Cancel
                </button>
              </div>
            </div>
          )}

          {/* Policy detail */}
          {mode === 'list' && selected && (
            <div className="space-y-4">
              {/* Current value */}
              <div className="bg-[var(--color-bg-panel)] border border-border-DEFAULT p-4"
                style={{ clipPath: 'polygon(0 0, calc(100% - 10px) 0, 100% 10px, 100% 100%, 0 100%)' }}>
                <div className="flex items-center justify-between mb-3">
                  <div>
                    <span className="text-xs font-bold text-[var(--color-text-primary)] font-mono">{selected.key}</span>
                    <span className="ml-2"><StatusBadge active={selected.is_active} /></span>
                    <span className="ml-2 text-micro text-[var(--color-text-muted)]">v{selected.version}</span>
                  </div>
                  <div className="flex gap-2">
                    <button onClick={openEdit}
                      className="px-2 py-1 text-micro font-semibold uppercase tracking-widest border border-border-DEFAULT text-[var(--color-text-secondary)] hover:text-[var(--color-text-primary)] hover:border-orange transition-colors">
                      Edit
                    </button>
                    <button onClick={() => setShowApprovalPanel(p => !p)}
                      className="px-2 py-1 text-micro font-semibold uppercase tracking-widest border border-orange/40 text-[var(--q-orange)] hover:bg-[var(--q-orange)]/10 transition-colors">
                      Request Approval
                    </button>
                    {selected.is_active && (
                      <button onClick={deactivatePolicy}
                        className="px-2 py-1 text-micro font-semibold uppercase tracking-widest border border-[var(--color-brand-red)]/40 text-[var(--color-brand-red)] hover:bg-[var(--color-brand-red)]/10 transition-colors">
                        Deactivate
                      </button>
                    )}
                  </div>
                </div>
                <pre className="bg-bg-page text-xs font-mono text-[var(--color-text-secondary)] p-3  overflow-auto max-h-48">
                  {JSON.stringify(selected.value, null, 2)}
                </pre>
              </div>

              {/* Approval request */}
              <AnimatePresence>
                {showApprovalPanel && (
                  <motion.div initial={{ opacity: 0, height: 0 }} animate={{ opacity: 1, height: 'auto' }} exit={{ opacity: 0, height: 0 }}
                    className="bg-[var(--color-bg-panel)] border border-orange/30 p-4 overflow-hidden"
                    style={{ clipPath: 'polygon(0 0, calc(100% - 10px) 0, 100% 10px, 100% 100%, 0 100%)' }}>
                    <div className="text-micro uppercase tracking-widest text-[var(--q-orange)] mb-3">
                      Request Approval (2-person rule enforced)
                    </div>
                    <label className="text-micro text-[var(--color-text-muted)] block mb-1">Proposed Value (JSON)</label>
                    <textarea rows={6} value={approvalProposed} onChange={e => setApprovalProposed(e.target.value)}
                      className="w-full bg-bg-page border border-border-DEFAULT px-3 py-2 text-xs font-mono text-[var(--color-text-primary)] focus:outline-none focus:border-orange resize-none mb-3" />
                    <div className="flex gap-2">
                      <button onClick={requestApproval} disabled={requestingApproval}
                        className="px-4 py-2 text-micro font-semibold uppercase tracking-widest bg-[var(--q-orange)] text-bg-page hover:bg-[#E64500] transition-colors disabled:opacity-50">
                        {requestingApproval ? 'Requesting…' : 'Submit for Approval'}
                      </button>
                      <button onClick={() => setShowApprovalPanel(false)}
                        className="px-4 py-2 text-micro font-semibold uppercase tracking-widest border border-border-DEFAULT text-[var(--color-text-muted)] hover:text-[var(--color-text-primary)] transition-colors">
                        Cancel
                      </button>
                    </div>
                  </motion.div>
                )}
              </AnimatePresence>

              {/* Version history */}
              <div className="bg-[var(--color-bg-panel)] border border-border-DEFAULT"
                style={{ clipPath: 'polygon(0 0, calc(100% - 10px) 0, 100% 10px, 100% 100%, 0 100%)' }}>
                <div className="flex items-center justify-between px-4 py-3 border-b border-white/10">
                  <span className="text-micro uppercase tracking-widest text-[var(--color-text-muted)]">Version History</span>
                  {rollbackVersion !== null && (
                    <button onClick={rollback} disabled={rollingBack}
                      className="px-3 py-1 text-micro font-semibold uppercase tracking-widest bg-[var(--q-orange)]/20 text-[var(--q-orange)] border border-orange/40 hover:bg-[var(--q-orange)]/30 transition-colors disabled:opacity-50">
                      {rollingBack ? 'Rolling back…' : `Rollback to v${rollbackVersion}`}
                    </button>
                  )}
                </div>
                {versionsLoading ? (
                  <div className="px-4 py-6 text-center text-[var(--color-text-muted)] text-sm">Loading versions…</div>
                ) : versions.length === 0 ? (
                  <div className="px-4 py-6 text-center text-[var(--color-text-muted)] text-sm">No version history yet.</div>
                ) : (
                  versions.map((v, i) => (
                    <motion.div key={v.id} initial={{ opacity: 0 }} animate={{ opacity: 1 }} transition={{ delay: i * 0.03 }}
                      className="flex items-center gap-3 px-4 py-3 border-b border-white/5 last:border-0 hover:bg-[var(--color-bg-base)]/[0.02]">
                      <span className="text-xs font-bold font-mono text-[var(--q-orange)] w-8">v{v.version_number}</span>
                      <div className="flex-1">
                        <div className="text-xs text-[var(--color-text-primary)]">{v.change_reason ?? 'No reason provided'}</div>
                        <div className="text-micro text-[var(--color-text-muted)] font-mono">
                          {v.changed_by_user_id.slice(0, 8)}… · {new Date(v.created_at).toLocaleString()}
                        </div>
                      </div>
                      <button onClick={() => setRollbackVersion(v.version_number === rollbackVersion ? null : v.version_number)}
                        className={`text-micro font-semibold uppercase tracking-widest transition-colors px-2 py-1 border ${rollbackVersion === v.version_number ? 'border-orange text-[var(--q-orange)] bg-[var(--q-orange)]/10' : 'border-border-DEFAULT text-[var(--color-text-muted)] hover:text-[var(--color-text-primary)]'}`}>
                        {rollbackVersion === v.version_number ? 'Selected' : 'Select'}
                      </button>
                    </motion.div>
                  ))
                )}
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
