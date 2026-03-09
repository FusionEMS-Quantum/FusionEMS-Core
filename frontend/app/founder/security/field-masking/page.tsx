'use client';

import { useEffect, useState } from 'react';
import Link from 'next/link';
import { ArrowLeft, Shield, RefreshCw, AlertTriangle, Lock, Eye, EyeOff, Plus } from 'lucide-react';
import { listPolicies, createPolicy } from '@/services/api';

interface PolicyRecord {
  id: string;
  name: string;
  description?: string;
  policy_type?: string;
  status?: string;
  version?: number;
  created_at?: string;
  updated_at?: string;
  rules_count?: number;
}

export default function FieldMaskingPage() {
  const [policies, setPolicies] = useState<PolicyRecord[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [showCreate, setShowCreate] = useState(false);
  const [newPolicy, setNewPolicy] = useState({ name: '', description: '', policy_type: 'field_masking' });

  const loadData = async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await listPolicies();
      const p = Array.isArray(res?.policies) ? res.policies : Array.isArray(res) ? res : [];
      setPolicies(p);
    } catch {
      setPolicies([]);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { loadData(); }, []);

  const handleCreate = async () => {
    try {
      await createPolicy(newPolicy);
      setShowCreate(false);
      setNewPolicy({ name: '', description: '', policy_type: 'field_masking' });
      await loadData();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to create policy');
    }
  };

  if (loading) return <div className="min-h-screen bg-gray-950 text-white flex items-center justify-center"><RefreshCw className="w-8 h-8 animate-spin text-emerald-400" /></div>;

  return (
    <div className="min-h-screen bg-gray-950 text-white p-6">
      <div className="max-w-7xl mx-auto space-y-8">
        <div className="flex items-center justify-between">
          <div>
            <Link href="/founder/security" className="text-gray-400 hover:text-white flex items-center gap-1 text-sm mb-2"><ArrowLeft className="w-4 h-4" /> Security</Link>
            <h1 className="text-3xl font-bold flex items-center gap-3"><Shield className="w-8 h-8 text-red-400" /> Field Masking & Data Governance</h1>
            <p className="text-gray-400 mt-1">PHI field masking, role-based access policies, and Cedar policy engine configuration</p>
          </div>
          <div className="flex gap-2">
            <button onClick={() => setShowCreate(true)} className="px-4 py-2 bg-red-600 hover:bg-red-500 rounded-lg flex items-center gap-2 text-sm"><Plus className="w-4 h-4" /> New Policy</button>
            <button onClick={loadData} className="px-4 py-2 bg-gray-800 hover:bg-gray-700 rounded-lg flex items-center gap-2 text-sm"><RefreshCw className="w-4 h-4" /> Refresh</button>
          </div>
        </div>

        {error && <div className="bg-red-900/30 border border-red-700 rounded-lg p-4 flex items-center gap-3"><AlertTriangle className="w-5 h-5 text-red-400" /><span className="text-red-300">{error}</span></div>}

        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          <div className="bg-gray-900 border border-gray-800 rounded-lg p-5">
            <div className="text-gray-400 text-sm mb-1 flex items-center gap-1"><Lock className="w-4 h-4" /> Active Policies</div>
            <div className="text-2xl font-bold text-emerald-400">{policies.filter(p => p.status === 'active').length}</div>
          </div>
          <div className="bg-gray-900 border border-gray-800 rounded-lg p-5">
            <div className="text-gray-400 text-sm mb-1 flex items-center gap-1"><EyeOff className="w-4 h-4" /> Masking Rules</div>
            <div className="text-2xl font-bold text-red-400">{policies.filter(p => p.policy_type === 'field_masking').length}</div>
          </div>
          <div className="bg-gray-900 border border-gray-800 rounded-lg p-5">
            <div className="text-gray-400 text-sm mb-1 flex items-center gap-1"><Eye className="w-4 h-4" /> Total Policies</div>
            <div className="text-2xl font-bold text-blue-400">{policies.length}</div>
          </div>
        </div>

        {showCreate && (
          <div className="bg-gray-900 border border-red-700 rounded-lg p-6">
            <h3 className="text-lg font-semibold mb-4">Create Masking Policy</h3>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <input placeholder="Policy name" value={newPolicy.name} onChange={(e) => setNewPolicy({ ...newPolicy, name: e.target.value })}
                className="bg-gray-800 border border-gray-700 rounded px-3 py-2 text-sm text-white" />
              <input placeholder="Description" value={newPolicy.description} onChange={(e) => setNewPolicy({ ...newPolicy, description: e.target.value })}
                className="bg-gray-800 border border-gray-700 rounded px-3 py-2 text-sm text-white" />
            </div>
            <div className="mt-4 flex gap-2">
              <button onClick={handleCreate} className="px-4 py-2 bg-red-600 hover:bg-red-500 rounded text-sm">Create</button>
              <button onClick={() => setShowCreate(false)} className="px-4 py-2 bg-gray-700 hover:bg-gray-600 rounded text-sm">Cancel</button>
            </div>
          </div>
        )}

        <div className="bg-gray-900 border border-gray-800 rounded-lg overflow-hidden">
          <div className="px-6 py-4 border-b border-gray-800"><h2 className="text-lg font-semibold flex items-center gap-2"><Shield className="w-5 h-5 text-red-400" /> Policy Registry</h2></div>
          {policies.length === 0 ? (
            <div className="p-12 text-center text-gray-500"><Shield className="w-12 h-12 mx-auto mb-3 opacity-30" /><p>No policies configured. Create your first field masking policy.</p></div>
          ) : (
            <table className="w-full text-sm">
              <thead className="bg-gray-800/50">
                <tr>
                  <th className="text-left px-6 py-3 text-gray-400 font-medium">Policy Name</th>
                  <th className="text-left px-6 py-3 text-gray-400 font-medium">Type</th>
                  <th className="text-left px-6 py-3 text-gray-400 font-medium">Status</th>
                  <th className="text-left px-6 py-3 text-gray-400 font-medium">Version</th>
                  <th className="text-left px-6 py-3 text-gray-400 font-medium">Updated</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-800">
                {policies.map((p) => (
                  <tr key={p.id} className="hover:bg-gray-800/30">
                    <td className="px-6 py-3 text-white font-medium">{p.name}</td>
                    <td className="px-6 py-3 text-gray-400">{p.policy_type ?? 'general'}</td>
                    <td className={`px-6 py-3 font-bold ${p.status === 'active' ? 'text-emerald-400' : 'text-amber-400'}`}>{p.status ?? 'draft'}</td>
                    <td className="px-6 py-3 text-gray-400">v{p.version ?? 1}</td>
                    <td className="px-6 py-3 text-gray-400">{p.updated_at ? new Date(p.updated_at).toLocaleDateString() : '—'}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </div>
      </div>
    </div>
  );
}
