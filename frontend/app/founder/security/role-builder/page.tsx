'use client';

import { useEffect, useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import Link from 'next/link';

const API = process.env.NEXT_PUBLIC_API_BASE || process.env.NEXT_PUBLIC_API_URL || '';

interface Role {
  id: string;
  name: string;
  description: string | null;
  is_system: boolean;
}

interface RoleAssignment {
  id: string;
  user_id: string;
  role_id: string;
  role_name: string;
  is_active: boolean;
  created_at: string;
}

function authHeaders(): HeadersInit {
  const token = typeof window !== 'undefined' ? localStorage.getItem('token') ?? '' : '';
  return { 'Content-Type': 'application/json', Authorization: `Bearer ${token}` };
}

function Badge({ active }: { active: boolean }) {
  return (
    <span className={`inline-flex items-center px-2 py-0.5 text-micro font-semibold uppercase tracking-widest border ${active ? 'border-green text-green bg-green/10' : 'border-red-500/40 text-red-400 bg-red-500/10'}`}>
      {active ? 'Active' : 'Revoked'}
    </span>
  );
}

function RoleCard({ role, selected, onClick }: { role: Role; selected: boolean; onClick: () => void }) {
  return (
    <motion.button
      whileHover={{ scale: 1.01 }}
      onClick={onClick}
      className={`w-full text-left p-3 border transition-colors ${selected ? 'border-orange bg-[#FF4D00]/10' : 'border-border-DEFAULT hover:border-white/20 bg-[#0A0A0B]'}`}
      style={{ clipPath: 'polygon(0 0, calc(100% - 6px) 0, 100% 6px, 100% 100%, 0 100%)' }}
    >
      <div className="flex items-center gap-2 mb-1">
        <span className="text-xs font-bold text-zinc-100">{role.name}</span>
        {role.is_system && (
          <span className="px-1.5 py-0.5 text-[10px] bg-[#FF4D00]/20 text-[#FF4D00] border border-orange/30 uppercase tracking-widest">System</span>
        )}
      </div>
      {role.description && <p className="text-micro text-zinc-500">{role.description}</p>}
    </motion.button>
  );
}

export default function RoleBuilderPage() {
  const [roles, setRoles] = useState<Role[]>([]);
  const [assignments, setAssignments] = useState<RoleAssignment[]>([]);
  const [selectedRole, setSelectedRole] = useState<Role | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [revoking, setRevoking] = useState<string | null>(null);
  const [toast, setToast] = useState<{ msg: string; ok: boolean } | null>(null);

  // Assign form
  const [assignUserId, setAssignUserId] = useState('');
  const [assigning, setAssigning] = useState(false);

  const showToast = (msg: string, ok: boolean) => {
    setToast({ msg, ok });
    setTimeout(() => setToast(null), 4000);
  };

  useEffect(() => {
    Promise.all([
      fetch(`${API}/api/v1/roles`, { headers: authHeaders() }).then(r => r.ok ? r.json() : []).catch(() => []),
      fetch(`${API}/api/v1/roles/assignments`, { headers: authHeaders() }).then(r => r.ok ? r.json() : []).catch(() => []),
    ]).then(([rolesData, assignData]) => {
      setRoles(rolesData);
      setAssignments(assignData);
      setLoading(false);
    }).catch((err) => {
      console.error('[RoleBuilder] load failed:', err);
      setError('Failed to load roles and assignments. Please refresh.');
      setLoading(false);
    });
  }, []);

  const assignRole = async () => {
    if (!selectedRole || !assignUserId.trim()) return;
    setAssigning(true);
    setError(null);
    try {
      const res = await fetch(`${API}/api/v1/roles/assignments`, {
        method: 'POST',
        headers: authHeaders(),
        body: JSON.stringify({ user_id: assignUserId.trim(), role_id: selectedRole.id }),
      });
      if (!res.ok) {
        const err = await res.json().catch(() => ({}));
        throw new Error(err.detail ?? `HTTP ${res.status}`);
      }
      const newAssign: RoleAssignment = await res.json();
      setAssignments(prev => [newAssign, ...prev]);
      setAssignUserId('');
      showToast(`Role "${selectedRole.name}" assigned.`, true);
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Assignment failed');
      showToast(e instanceof Error ? e.message : 'Assignment failed', false);
    } finally {
      setAssigning(false);
    }
  };

  const revokeAssignment = async (id: string) => {
    setRevoking(id);
    setError(null);
    try {
      const res = await fetch(`${API}/api/v1/roles/assignments/${id}`, {
        method: 'DELETE',
        headers: authHeaders(),
      });
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      setAssignments(prev => prev.filter(a => a.id !== id));
      showToast('Role assignment revoked.', true);
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Revoke failed');
      showToast(e instanceof Error ? e.message : 'Revoke failed', false);
    } finally {
      setRevoking(null);
    }
  };

  const filteredAssignments = selectedRole
    ? assignments.filter(a => a.role_id === selectedRole.id)
    : assignments;

  return (
    <div className="p-5 min-h-screen">
      {/* Toast */}
      <AnimatePresence>
        {toast && (
          <motion.div initial={{ opacity: 0, y: -12 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0 }}
            className={`fixed top-4 right-4 z-50 px-4 py-3 border text-sm font-semibold ${toast.ok ? 'border-green text-green bg-green/10' : 'border-red-500 text-red-400 bg-red-500/10'}`}
            style={{ clipPath: 'polygon(0 0, calc(100% - 8px) 0, 100% 8px, 100% 100%, 0 100%)' }}>
            {toast.msg}
          </motion.div>
        )}
      </AnimatePresence>

      {/* Header */}
      <div className="hud-rail pb-3 mb-6 flex items-end justify-between">
        <div>
          <div className="micro-caps mb-1 text-zinc-500">Security</div>
          <h1 className="text-h2 font-bold text-zinc-100">Role Builder</h1>
          <p className="text-body text-zinc-500 mt-1">Manage role assignments with full audit trail.</p>
        </div>
        <Link href="/founder/security"
          className="px-3 py-1.5 text-micro font-semibold uppercase tracking-widest border border-border-DEFAULT text-zinc-500 hover:text-zinc-100 transition-colors">
          ← Security
        </Link>
      </div>

      {error && <div className="mb-4 px-4 py-3 border border-red-500/40 text-red-400 text-sm">{error}</div>}

      <div className="grid grid-cols-12 gap-4">
        {/* Role list */}
        <div className="col-span-4">
          <div className="text-micro uppercase tracking-widest text-zinc-500 mb-2">Roles ({roles.length})</div>
          {loading ? (
            <div className="text-zinc-500 text-sm py-8 text-center">Loading…</div>
          ) : (
            <div className="flex flex-col gap-1.5">
              <motion.button
                onClick={() => setSelectedRole(null)}
                className={`w-full text-left p-2.5 text-xs font-semibold uppercase tracking-widest border transition-colors ${!selectedRole ? 'border-orange text-[#FF4D00] bg-[#FF4D00]/10' : 'border-border-DEFAULT text-zinc-500 hover:border-white/20'}`}>
                All Roles
              </motion.button>
              {roles.map(r => (
                <RoleCard key={r.id} role={r} selected={selectedRole?.id === r.id} onClick={() => setSelectedRole(r)} />
              ))}
            </div>
          )}
        </div>

        {/* Assignments panel */}
        <div className="col-span-8">
          <div className="text-micro uppercase tracking-widest text-zinc-500 mb-2">
            {selectedRole ? `Assignments — ${selectedRole.name}` : 'All Assignments'}
            <span className="ml-2 text-[#FF4D00]">({filteredAssignments.length})</span>
          </div>

          {/* Assign form */}
          {selectedRole && (
            <div className="flex gap-2 mb-4 bg-[#0A0A0B] border border-border-DEFAULT p-3"
              style={{ clipPath: 'polygon(0 0, calc(100% - 8px) 0, 100% 8px, 100% 100%, 0 100%)' }}>
              <input
                value={assignUserId} onChange={e => setAssignUserId(e.target.value)}
                placeholder="User UUID…"
                className="flex-1 bg-bg-page border border-border-DEFAULT px-3 py-1.5 text-xs text-zinc-100 placeholder:text-zinc-500 focus:outline-none focus:border-orange font-mono" />
              <button onClick={assignRole} disabled={assigning || !assignUserId.trim()}
                className="px-4 py-1.5 text-micro font-semibold uppercase tracking-widest bg-[#FF4D00] text-bg-page hover:bg-[#E64500] transition-colors disabled:opacity-50">
                {assigning ? 'Assigning…' : 'Assign'}
              </button>
            </div>
          )}

          <div className="bg-[#0A0A0B] border border-border-DEFAULT"
            style={{ clipPath: 'polygon(0 0, calc(100% - 10px) 0, 100% 10px, 100% 100%, 0 100%)' }}>
            {/* Headers */}
            <div className="grid grid-cols-12 gap-2 px-4 py-2 border-b border-white/10 bg-zinc-950/[0.02]">
              <span className="col-span-4 text-micro uppercase tracking-widest text-zinc-500">User ID</span>
              <span className="col-span-3 text-micro uppercase tracking-widest text-zinc-500">Role</span>
              <span className="col-span-2 text-micro uppercase tracking-widest text-zinc-500">Status</span>
              <span className="col-span-2 text-micro uppercase tracking-widest text-zinc-500">Created</span>
              <span className="col-span-1" />
            </div>

            {filteredAssignments.length === 0 && !loading && (
              <div className="px-4 py-10 text-center text-zinc-500 text-sm">No role assignments found.</div>
            )}

            {filteredAssignments.map((a, i) => (
              <motion.div key={a.id} initial={{ opacity: 0 }} animate={{ opacity: 1 }} transition={{ delay: i * 0.02 }}
                className="grid grid-cols-12 gap-2 px-4 py-3 border-b border-white/5 last:border-0 items-center hover:bg-zinc-950/[0.02]">
                <span className="col-span-4 text-micro font-mono text-zinc-400 truncate">{a.user_id.slice(0, 8)}…</span>
                <span className="col-span-3 text-xs font-semibold text-zinc-100 truncate">{a.role_name}</span>
                <span className="col-span-2"><Badge active={a.is_active} /></span>
                <span className="col-span-2 text-micro text-zinc-500 font-mono">
                  {new Date(a.created_at).toLocaleDateString()}
                </span>
                <div className="col-span-1 flex justify-end">
                  {a.is_active && (
                    <button onClick={() => revokeAssignment(a.id)} disabled={revoking === a.id}
                      className="text-micro text-red-400 hover:text-red-300 transition-colors disabled:opacity-40 font-semibold">
                      {revoking === a.id ? '…' : 'Revoke'}
                    </button>
                  )}
                </div>
              </motion.div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}
