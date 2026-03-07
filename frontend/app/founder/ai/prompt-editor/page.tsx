'use client';

import { useEffect, useState, useCallback } from 'react';
import Link from 'next/link';
import { motion } from 'framer-motion';
import { getAIPromptTemplates, updateAIPromptTemplate } from '@/services/api';

interface PromptTemplate {
  id: string;
  template_key: string;
  domain: string;
  system_prompt: string;
  user_prompt_template: string;
  version: number;
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

export default function PromptEditorPage() {
  const [templates, setTemplates] = useState<PromptTemplate[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [selected, setSelected] = useState<PromptTemplate | null>(null);
  const [editSystem, setEditSystem] = useState('');
  const [editUser, setEditUser] = useState('');
  const [saving, setSaving] = useState(false);

  const fetchTemplates = useCallback(() => {
    setLoading(true);
    setError('');
    getAIPromptTemplates()
      .then((data: PromptTemplate[]) => setTemplates(data))
      .catch(() => setError('Failed to load prompt templates.'))
      .finally(() => setLoading(false));
  }, []);

  useEffect(() => { fetchTemplates(); }, [fetchTemplates]);

  function selectTemplate(tpl: PromptTemplate) {
    setSelected(tpl);
    setEditSystem(tpl.system_prompt);
    setEditUser(tpl.user_prompt_template);
  }

  async function handleSave() {
    if (!selected) return;
    setSaving(true);
    try {
      await updateAIPromptTemplate(selected.id, {
        system_prompt: editSystem,
        user_prompt_template: editUser,
      });
      fetchTemplates();
      setSelected(null);
    } catch {
      setError('Failed to save prompt template.');
    } finally {
      setSaving(false);
    }
  }

  return (
    <div className="p-5 min-h-screen space-y-6">
      <div>
        <div className="text-micro font-bold uppercase tracking-[0.2em] text-orange-dim mb-1">AI GOVERNANCE</div>
        <h1 className="text-xl font-black uppercase tracking-wider text-text-primary">Prompt Editor</h1>
        <p className="text-xs text-text-muted mt-0.5">Build, version, and test system prompts with guardrails</p>
      </div>

      {error && (
        <div className="bg-red-500/[0.08] border border-red-500/[0.35] p-3 chamfer-4 text-xs text-[var(--color-brand-red)]">
          {error}
        </div>
      )}

      {loading ? (
        <div className="space-y-3">
          {[...Array(3)].map((_, i) => (
            <div key={i} className="animate-pulse bg-bg-panel border border-border-DEFAULT h-16 chamfer-8" />
          ))}
        </div>
      ) : selected ? (
        /* Edit panel */
        <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} className="space-y-4">
          <div className="flex items-center justify-between">
            <div>
              <div className="text-sm font-bold text-text-primary">{selected.template_key}</div>
              <div className="text-micro text-text-muted">Domain: {selected.domain} · Version: {selected.version}</div>
            </div>
            <button onClick={() => setSelected(null)} className="text-micro uppercase tracking-widest text-text-muted hover:text-text-primary transition-colors">
              Cancel
            </button>
          </div>

          <div>
            <label className="text-micro uppercase tracking-widest text-text-muted block mb-1">System Prompt</label>
            <textarea
              value={editSystem}
              onChange={(e) => setEditSystem(e.target.value)}
              rows={8}
              className="w-full bg-bg-void border border-border-DEFAULT p-3 text-xs text-text-primary font-mono resize-y chamfer-4 focus:border-brand-orange/40 focus:outline-none"
            />
          </div>

          <div>
            <label className="text-micro uppercase tracking-widest text-text-muted block mb-1">User Prompt Template</label>
            <textarea
              value={editUser}
              onChange={(e) => setEditUser(e.target.value)}
              rows={6}
              className="w-full bg-bg-void border border-border-DEFAULT p-3 text-xs text-text-primary font-mono resize-y chamfer-4 focus:border-brand-orange/40 focus:outline-none"
            />
          </div>

          <button
            onClick={handleSave}
            disabled={saving}
            className="text-micro uppercase tracking-widest font-bold px-4 py-2 chamfer-4 border transition-colors hover:bg-brand-orange/[0.12] disabled:opacity-50"
            style={{ color: 'var(--color-brand-orange)', borderColor: 'rgba(255,107,26,0.35)' }}
          >
            {saving ? 'Saving...' : 'Save & Version'}
          </button>
        </motion.div>
      ) : templates.length === 0 ? (
        <div className="bg-bg-panel border border-border-DEFAULT chamfer-8 p-10 text-center">
          <div className="text-sm text-text-muted">No prompt templates configured</div>
          <p className="text-xs text-text-muted mt-1">Create prompt templates via the API to manage them here.</p>
        </div>
      ) : (
        <div className="space-y-2">
          {templates.map((tpl, i) => (
            <motion.button
              key={tpl.id}
              initial={{ opacity: 0, y: 6 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: i * 0.03 }}
              onClick={() => selectTemplate(tpl)}
              className="w-full text-left bg-bg-panel border border-border-DEFAULT p-4 flex items-center justify-between gap-3 hover:border-white/[0.18] transition-colors"
              style={{ clipPath: 'polygon(0 0, calc(100% - 10px) 0, 100% 10px, 100% 100%, 0 100%)' }}
            >
              <div className="min-w-0">
                <div className="text-sm font-bold text-text-primary">{tpl.template_key}</div>
                <div className="text-micro text-text-muted">Domain: {tpl.domain} · v{tpl.version}</div>
              </div>
              <div className="flex items-center gap-2 shrink-0">
                <span
                  className="text-micro uppercase tracking-widest font-bold px-2 py-0.5 chamfer-4"
                  style={{
                    color: tpl.is_active ? 'var(--color-status-active)' : 'var(--color-text-muted)',
                    background: tpl.is_active ? 'rgba(34,197,94,0.12)' : 'rgba(255,255,255,0.04)',
                    border: `1px solid ${tpl.is_active ? 'rgba(34,197,94,0.25)' : 'var(--color-border-default)'}`,
                  }}
                >
                  {tpl.is_active ? 'ACTIVE' : 'INACTIVE'}
                </span>
              </div>
            </motion.button>
          ))}
        </div>
      )}

      <Link href="/founder/ai" className="text-xs text-orange-dim hover:text-orange">← Back to AI Governance</Link>
    </div>
  );
}
