'use client';

import { useEffect, useState } from 'react';
import { motion } from 'framer-motion';
import { FileText, Plus, Copy, CheckCircle, Clock, ArrowLeft } from 'lucide-react';
import Link from 'next/link';
import {
  listTemplates,
  createTemplate,
  cloneTemplate,
  approveTemplate,
  getTemplateVersions,
  bulkGenerateTemplates,
} from '@/services/api';

interface TemplateRecord {
  id: string;
  name: string;
  type: string;
  status: string;
  version: number;
  updated_at: string;
  created_by: string;
}

interface VersionRecord {
  version: number;
  created_at: string;
  author: string;
}

export default function ProposalTemplatesPage() {
  const [templates, setTemplates] = useState<TemplateRecord[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [showCreate, setShowCreate] = useState(false);
  const [newName, setNewName] = useState('');
  const [versions, setVersions] = useState<Record<string, VersionRecord[]>>({});

  async function loadData() {
    try {
      setLoading(true);
      const res = await listTemplates({ type: 'proposal' });
      const list: TemplateRecord[] = Array.isArray(res?.data) ? res.data : Array.isArray(res) ? res : [];
      setTemplates(list);
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : 'Failed to load proposal templates';
      setError(msg);
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => { loadData(); }, []);

  async function handleCreate() {
    if (!newName.trim()) return;
    try {
      await createTemplate({ name: newName.trim(), type: 'proposal' });
      setNewName('');
      setShowCreate(false);
      await loadData();
    } catch { /* toast */ }
  }

  async function handleClone(id: string) {
    try {
      await cloneTemplate({ source_template_id: id });
      await loadData();
    } catch { /* toast */ }
  }

  async function handleApprove(id: string) {
    try {
      await approveTemplate(id);
      await loadData();
    } catch { /* toast */ }
  }

  async function handleViewVersions(id: string) {
    try {
      const res = await getTemplateVersions(id);
      const list: VersionRecord[] = Array.isArray(res?.data) ? res.data : Array.isArray(res) ? res : [];
      setVersions((prev) => ({ ...prev, [id]: list }));
    } catch { /* toast */ }
  }

  async function handleBulkGenerate(id: string) {
    try {
      await bulkGenerateTemplates({ template_id: id, variable_sets: [{}] });
    } catch { /* toast */ }
  }

  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-[60vh]">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-500" />
      </div>
    );
  }

  if (error) {
    return (
      <div className="p-6 max-w-7xl mx-auto">
        <div className="bg-red-900/30 border border-red-700 rounded-lg p-4 text-red-300">{error}</div>
      </div>
    );
  }

  const approved = templates.filter((t) => t.status === 'approved').length;
  const draft = templates.filter((t) => t.status === 'draft').length;

  return (
    <div className="p-6 max-w-7xl mx-auto space-y-6">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <Link href="/founder/templates" className="text-gray-400 hover:text-white"><ArrowLeft className="h-5 w-5" /></Link>
          <FileText className="h-6 w-6 text-blue-400" />
          <h1 className="text-2xl font-bold text-white">Proposal Templates</h1>
        </div>
        <button onClick={() => setShowCreate(!showCreate)} className="flex items-center gap-2 px-4 py-2 bg-blue-600 hover:bg-blue-700 rounded-lg text-white text-sm font-medium">
          <Plus className="h-4 w-4" /> New Template
        </button>
      </div>

      {showCreate && (
        <motion.div initial={{ opacity: 0, y: -10 }} animate={{ opacity: 1, y: 0 }} className="bg-gray-800 border border-gray-700 rounded-lg p-4 flex gap-3 items-end">
          <div className="flex-1">
            <label className="block text-xs text-gray-400 mb-1">Template Name</label>
            <input value={newName} onChange={(e) => setNewName(e.target.value)} className="w-full px-3 py-2 bg-gray-900 border border-gray-600 rounded text-white text-sm" placeholder="e.g. Municipal Ambulance Proposal" />
          </div>
          <button onClick={handleCreate} className="px-4 py-2 bg-green-600 hover:bg-green-700 rounded text-white text-sm font-medium">Create</button>
        </motion.div>
      )}

      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        {[
          { label: 'Total Templates', value: templates.length, icon: FileText, color: 'blue' },
          { label: 'Approved', value: approved, icon: CheckCircle, color: 'green' },
          { label: 'Drafts', value: draft, icon: Clock, color: 'yellow' },
        ].map((kpi) => (
          <motion.div key={kpi.label} initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} className={`bg-gray-800 border border-${kpi.color}-500/30 rounded-lg p-4`}>
            <div className="flex items-center gap-2 text-gray-400 text-xs mb-1"><kpi.icon className="h-4 w-4" />{kpi.label}</div>
            <div className="text-2xl font-bold text-white">{kpi.value}</div>
          </motion.div>
        ))}
      </div>

      <div className="bg-gray-800 border border-gray-700 rounded-lg overflow-hidden">
        <table className="w-full text-sm">
          <thead className="bg-gray-900 text-gray-400 text-xs uppercase">
            <tr>
              <th className="px-4 py-3 text-left">Name</th>
              <th className="px-4 py-3 text-left">Status</th>
              <th className="px-4 py-3 text-left">Version</th>
              <th className="px-4 py-3 text-left">Updated</th>
              <th className="px-4 py-3 text-right">Actions</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-700">
            {templates.length === 0 ? (
              <tr><td colSpan={5} className="px-4 py-8 text-center text-gray-500">No proposal templates yet. Create your first template.</td></tr>
            ) : templates.map((t) => (
              <tr key={t.id} className="hover:bg-gray-700/50">
                <td className="px-4 py-3 text-white font-medium">{t.name}</td>
                <td className="px-4 py-3">
                  <span className={`px-2 py-0.5 rounded text-xs font-medium ${t.status === 'approved' ? 'bg-green-900/50 text-green-300' : 'bg-yellow-900/50 text-yellow-300'}`}>{t.status}</span>
                </td>
                <td className="px-4 py-3 text-gray-300">v{t.version ?? 1}</td>
                <td className="px-4 py-3 text-gray-400">{t.updated_at ? new Date(t.updated_at).toLocaleDateString() : '—'}</td>
                <td className="px-4 py-3 text-right space-x-2">
                  <button onClick={() => handleClone(t.id)} className="text-blue-400 hover:text-blue-300 text-xs" title="Clone"><Copy className="h-3.5 w-3.5 inline" /></button>
                  {t.status !== 'approved' && <button onClick={() => handleApprove(t.id)} className="text-green-400 hover:text-green-300 text-xs" title="Approve"><CheckCircle className="h-3.5 w-3.5 inline" /></button>}
                  <button onClick={() => handleViewVersions(t.id)} className="text-gray-400 hover:text-gray-300 text-xs" title="Versions"><Clock className="h-3.5 w-3.5 inline" /></button>
                  <button onClick={() => handleBulkGenerate(t.id)} className="text-purple-400 hover:text-purple-300 text-xs" title="Generate">Gen</button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {Object.entries(versions).map(([id, vList]) => (
        <div key={id} className="bg-gray-800 border border-gray-700 rounded-lg p-4">
          <h3 className="text-sm font-semibold text-white mb-2">Version History — {templates.find((t) => t.id === id)?.name}</h3>
          <div className="space-y-1">
            {vList.map((v) => (
              <div key={v.version} className="flex justify-between text-xs text-gray-400">
                <span>v{v.version}</span>
                <span>{v.author ?? '—'}</span>
                <span>{v.created_at ? new Date(v.created_at).toLocaleDateString() : '—'}</span>
              </div>
            ))}
            {vList.length === 0 && <p className="text-xs text-gray-500">No version history available.</p>}
          </div>
        </div>
      ))}
    </div>
  );
}
