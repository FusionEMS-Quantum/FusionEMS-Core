'use client';

import { useEffect, useState, useCallback } from 'react';
import { motion } from 'framer-motion';
import { listResponsibleParties } from '@/services/api';

/* ── Types ───────────────────────────────────────────────────────────── */

interface ResponsibleParty {
  id: string;
  first_name: string;
  last_name: string;
  phone: string | null;
  email: string | null;
}

/* ── Page ─────────────────────────────────────────────────────────────── */

export default function PatientRelationshipsPage() {
  const [parties, setParties] = useState<ResponsibleParty[]>([]);
  const [loading, setLoading] = useState(true);

  const fetchData = useCallback(async () => {
    try {
      const d = await listResponsibleParties();
      setParties(d.items || []);
    } catch (_e) {
      /* silent */
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchData();
  }, [fetchData]);

  return (
    <div style={{ minHeight: '100vh', padding: '2rem', maxWidth: 1100, margin: '0 auto' }}>
      <h1 style={{ fontSize: 20, fontWeight: 700, color: 'var(--color-text-primary, #fafafa)', marginBottom: 4 }}>
        Responsible Parties &amp; Guarantors
      </h1>
      <p style={{ fontSize: 12, color: 'var(--color-text-muted, #a1a1aa)', marginBottom: 20 }}>
        View and manage financially responsible parties linked to patients
      </p>

      {loading && (
        <div style={{ color: 'var(--color-text-muted)', fontSize: 12 }}>Loading…</div>
      )}

      {!loading && parties.length === 0 && (
        <div
          className="chamfer-8"
          style={{
            padding: '2rem',
            textAlign: 'center',
            background: 'var(--color-bg-panel, #18181b)',
            border: '1px solid var(--color-border-default)',
            color: 'var(--color-text-muted)',
            fontSize: 13,
          }}
        >
          No responsible parties registered yet
        </div>
      )}

      <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
        {parties.map((p) => (
          <motion.div
            key={p.id}
            initial={{ opacity: 0, y: 4 }}
            animate={{ opacity: 1, y: 0 }}
            className="chamfer-8"
            style={{
              background: 'var(--color-bg-panel, #18181b)',
              border: '1px solid var(--color-border-default)',
              padding: '0.75rem 1rem',
            }}
          >
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
              <span style={{ fontSize: 13, fontWeight: 600, color: 'var(--color-text-primary)' }}>
                {p.first_name} {p.last_name}
              </span>
              <span style={{ fontSize: 10, color: 'var(--color-text-muted)' }}>
                {p.id.slice(0, 8)}…
              </span>
            </div>
            <div style={{ fontSize: 11, color: 'var(--color-text-muted)', marginTop: 4, display: 'flex', gap: 12 }}>
              {p.phone && <span>{p.phone}</span>}
              {p.email && <span>{p.email}</span>}
            </div>
          </motion.div>
        ))}
      </div>
    </div>
  );
}
