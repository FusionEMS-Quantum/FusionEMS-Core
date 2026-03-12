'use client';

import { useEffect, useState } from 'react';
import { AlertTriangle, ArrowLeft, Phone, Plus, RefreshCw, Trash2 } from 'lucide-react';
import Link from 'next/link';
import { getTelnyxCNAMList, registerTelnyxCNAM, deleteTelnyxCNAM } from '@/services/api';

interface CNAMEntry {
  phone_number?: string;
  display_name?: string;
  status?: string;
  created_at?: string;
}

export default function CNAMManagementPage() {
  const [entries, setEntries] = useState<CNAMEntry[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [showAdd, setShowAdd] = useState(false);
  const [newPhone, setNewPhone] = useState('');
  const [newName, setNewName] = useState('');
  const [submitting, setSubmitting] = useState(false);
  const [deleting, setDeleting] = useState<string | null>(null);

  const loadData = async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await getTelnyxCNAMList();
      const data = Array.isArray(res?.entries) ? res.entries : Array.isArray(res) ? res : [];
      setEntries(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load CNAM data');
    } finally {
      setLoading(false);
    }
  };

  const handleRegister = async () => {
    if (!newPhone.trim() || !newName.trim()) return;
    setSubmitting(true);
    setError(null);
    try {
      await registerTelnyxCNAM({ phone_number: newPhone.trim(), display_name: newName.trim() });
      setNewPhone('');
      setNewName('');
      setShowAdd(false);
      await loadData();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to register CNAM');
    } finally {
      setSubmitting(false);
    }
  };

  const handleDelete = async (phone: string) => {
    setDeleting(phone);
    setError(null);
    try {
      await deleteTelnyxCNAM(phone);
      await loadData();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to delete CNAM entry');
    } finally {
      setDeleting(null);
    }
  };

  useEffect(() => { loadData(); }, []);

  if (loading) {
    return (
      <div className="min-h-screen bg-[var(--color-bg-base)] text-white flex items-center justify-center">
        <RefreshCw className="w-8 h-8 animate-spin text-[var(--color-status-active)]" />
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-[var(--color-bg-base)] text-white p-6">
      <div className="max-w-5xl mx-auto space-y-8">
        <div className="flex items-center justify-between">
          <div>
            <Link href="/founder/comms" className="text-[var(--color-text-secondary)] hover:text-[var(--color-text-primary)] flex items-center gap-1 text-sm mb-2">
              <ArrowLeft className="w-4 h-4" /> Back to Comms
            </Link>
            <h1 className="text-3xl font-bold flex items-center gap-3">
              <Phone className="w-8 h-8 text-[var(--color-status-info)]" />
              CNAM Management
            </h1>
            <p className="text-[var(--color-text-secondary)] mt-1">Manage Caller ID (CNAM) registrations for Telnyx voice lines</p>
          </div>
          <div className="flex gap-2">
            <button onClick={() => setShowAdd(!showAdd)} className="px-4 py-2 bg-teal-600 hover:bg-teal-500 chamfer-8 flex items-center gap-2 text-sm">
              <Plus className="w-4 h-4" /> Register
            </button>
            <button onClick={loadData} className="px-4 py-2 bg-[var(--color-bg-raised)] hover:bg-[var(--color-bg-overlay)] chamfer-8 flex items-center gap-2 text-sm">
              <RefreshCw className="w-4 h-4" /> Refresh
            </button>
          </div>
        </div>

        {error && (
          <div className="bg-red-900/30 border border-[var(--color-brand-red)] chamfer-8 p-4 flex items-center gap-3">
            <AlertTriangle className="w-5 h-5 text-[var(--color-brand-red)]" />
            <span className="text-[var(--color-brand-red)]">{error}</span>
          </div>
        )}

        {/* Add Form */}
        {showAdd && (
          <div className="bg-[var(--color-bg-panel)] border border-teal-800 chamfer-8 p-6">
            <h2 className="text-lg font-semibold mb-4">Register New CNAM</h2>
            <div className="flex flex-col md:flex-row gap-3">
              <input
                type="text"
                value={newPhone}
                onChange={(e) => setNewPhone(e.target.value)}
                placeholder="Phone number (e.g., +15551234567)"
                className="flex-1 bg-[var(--color-bg-raised)] border border-[var(--color-border-strong)] chamfer-8 px-4 py-2 text-sm"
              />
              <input
                type="text"
                value={newName}
                onChange={(e) => setNewName(e.target.value)}
                placeholder="Display name (e.g., Metro EMS)"
                className="flex-1 bg-[var(--color-bg-raised)] border border-[var(--color-border-strong)] chamfer-8 px-4 py-2 text-sm"
                maxLength={15}
              />
              <button
                onClick={handleRegister}
                disabled={submitting || !newPhone.trim() || !newName.trim()}
                className="px-6 py-2 bg-teal-600 hover:bg-teal-500 disabled:opacity-50 chamfer-8 text-sm font-medium"
              >
                {submitting ? 'Registering...' : 'Register'}
              </button>
            </div>
            <p className="text-[var(--color-text-muted)] text-xs mt-2">CNAM display name max 15 characters. Changes may take 24-48 hours to propagate across carriers.</p>
          </div>
        )}

        {/* CNAM Entries Table */}
        <div className="bg-[var(--color-bg-panel)] border border-[var(--color-border-default)] chamfer-8 p-6">
          <h2 className="text-lg font-semibold mb-4">Registered CNAM Entries ({entries.length})</h2>
          {entries.length > 0 ? (
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead><tr className="text-[var(--color-text-secondary)] border-b border-[var(--color-border-default)]">
                  <th className="text-left py-2">Phone Number</th>
                  <th className="text-left py-2">Display Name</th>
                  <th className="text-left py-2">Status</th>
                  <th className="text-left py-2">Created</th>
                  <th className="text-right py-2">Actions</th>
                </tr></thead>
                <tbody>
                  {entries.map((e, i) => (
                    <tr key={i} className="border-b border-[var(--color-border-subtle)] hover:bg-[var(--color-bg-raised)]/30">
                      <td className="py-2 font-mono">{e.phone_number ?? '—'}</td>
                      <td className="py-2 font-medium">{e.display_name ?? '—'}</td>
                      <td className={`py-2 ${e.status === 'active' ? 'text-[var(--color-status-active)]' : e.status === 'pending' ? 'text-[var(--q-yellow)]' : 'text-[var(--color-text-secondary)]'}`}>
                        {e.status ?? '—'}
                      </td>
                      <td className="py-2 text-[var(--color-text-secondary)]">{e.created_at ?? '—'}</td>
                      <td className="py-2 text-right">
                        {e.phone_number && (
                          <button
                            onClick={() => handleDelete(e.phone_number!)}
                            disabled={deleting === e.phone_number}
                            className="text-[var(--color-brand-red)] hover:text-[var(--color-brand-red)] p-1"
                            title="Delete CNAM"
                          >
                            <Trash2 className={`w-4 h-4 ${deleting === e.phone_number ? 'animate-pulse' : ''}`} />
                          </button>
                        )}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          ) : (
            <div className="text-[var(--color-text-muted)] text-center py-8">
              <Phone className="w-12 h-12 text-gray-700 mx-auto mb-3" />
              <p>No CNAM registrations yet. Click &ldquo;Register&rdquo; to add a Caller ID entry.</p>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
