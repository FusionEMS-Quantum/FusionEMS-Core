'use client';

import { useEffect, useState, useCallback } from 'react';
import { motion } from 'framer-motion';

/* ── Types ───────────────────────────────────────────────────────────── */

interface Facility {
  id: string;
  name: string;
  facility_type: string;
  npi: string | null;
  city: string | null;
  state: string | null;
  phone: string | null;
  relationship_state: string;
}

interface FrictionFlag {
  id: string;
  facility_id: string;
  category: string;
  title: string;
  is_active: boolean;
}

/* ── Helpers ──────────────────────────────────────────────────────────── */

const API = process.env.NEXT_PUBLIC_API_BASE || process.env.NEXT_PUBLIC_API_URL || '';

function getToken(): string {
  if (typeof window === 'undefined') return '';
  return 'Bearer ' + (localStorage.getItem('qs_token') || '');
}

function stateColor(st: string): string {
  switch (st) {
    case 'ACTIVE': return 'var(--color-signal-green, #22c55e)';
    case 'HIGH_FRICTION': return 'var(--color-signal-red, #ef4444)';
    case 'REVIEW_REQUIRED': return 'var(--color-signal-amber, #f59e0b)';
    case 'INACTIVE': return 'var(--color-text-muted, #6b7280)';
    default: return 'var(--color-signal-yellow, #eab308)';
  }
}

/* ── Page ─────────────────────────────────────────────────────────────── */

export default function FacilitiesPage() {
  const [facilities, setFacilities] = useState<Facility[]>([]);
  const [expanded, setExpanded] = useState<string | null>(null);
  const [frictionMap, setFrictionMap] = useState<Record<string, FrictionFlag[]>>({});
  const [loading, setLoading] = useState(true);

  const fetchFacilities = useCallback(async () => {
    try {
      const res = await fetch(`${API}/api/v1/facilities`, {
        headers: { Authorization: getToken() },
      });
      if (res.ok) {
        const d = await res.json();
        setFacilities(d.items || []);
      }
    } catch (_e) {
      /* silent */
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchFacilities();
  }, [fetchFacilities]);

  const toggleExpand = async (id: string) => {
    if (expanded === id) {
      setExpanded(null);
      return;
    }
    setExpanded(id);
    if (!frictionMap[id]) {
      try {
        const res = await fetch(`${API}/api/v1/facilities/${id}/friction`, {
          headers: { Authorization: getToken() },
        });
        if (res.ok) {
          const d = await res.json();
          setFrictionMap((prev) => ({ ...prev, [id]: d.items || [] }));
        }
      } catch (_e) {
        /* silent */
      }
    }
  };

  return (
    <div style={{ minHeight: '100vh', padding: '2rem', maxWidth: 1100, margin: '0 auto' }}>
      <h1 style={{ fontSize: 20, fontWeight: 700, color: 'var(--color-text-primary, #fafafa)', marginBottom: 4 }}>
        Facility Network
      </h1>
      <p style={{ fontSize: 12, color: 'var(--color-text-muted, #a1a1aa)', marginBottom: 20 }}>
        Hospital, SNF, and partner facility relationships
      </p>

      {loading && (
        <div style={{ color: 'var(--color-text-muted)', fontSize: 12 }}>Loading facilities…</div>
      )}

      {!loading && facilities.length === 0 && (
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
          No facilities registered yet
        </div>
      )}

      <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
        {facilities.map((f) => (
          <div key={f.id}>
            <motion.div
              initial={{ opacity: 0, y: 4 }}
              animate={{ opacity: 1, y: 0 }}
              className="chamfer-8"
              style={{
                background: 'var(--color-bg-panel, #18181b)',
                border: '1px solid var(--color-border-default)',
                padding: '0.75rem 1rem',
                cursor: 'pointer',
              }}
              onClick={() => toggleExpand(f.id)}
            >
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                <div>
                  <span style={{ fontSize: 13, fontWeight: 600, color: 'var(--color-text-primary)' }}>
                    {f.name}
                  </span>
                  <span
                    style={{
                      marginLeft: 8,
                      fontSize: 9,
                      fontWeight: 700,
                      textTransform: 'uppercase',
                      padding: '2px 6px',
                      borderRadius: 3,
                      background: `${stateColor(f.relationship_state)}22`,
                      color: stateColor(f.relationship_state),
                    }}
                  >
                    {f.relationship_state}
                  </span>
                </div>
                <span
                  style={{
                    fontSize: 9,
                    fontWeight: 700,
                    textTransform: 'uppercase',
                    color: 'var(--color-text-muted)',
                  }}
                >
                  {f.facility_type}
                </span>
              </div>
              <div style={{ fontSize: 11, color: 'var(--color-text-muted)', marginTop: 4, display: 'flex', gap: 12 }}>
                {f.city && f.state && <span>{f.city}, {f.state}</span>}
                {f.npi && <span>NPI: {f.npi}</span>}
                {f.phone && <span>{f.phone}</span>}
              </div>
            </motion.div>

            {/* ── EXPANDED DETAIL ────────────────────────────────────── */}
            {expanded === f.id && (
              <motion.div
                initial={{ opacity: 0, height: 0 }}
                animate={{ opacity: 1, height: 'auto' }}
                style={{
                  marginTop: 4,
                  marginLeft: 16,
                  padding: '0.75rem 1rem',
                  background: 'var(--color-bg-subtle, #1c1c1e)',
                  border: '1px solid var(--color-border-default)',
                  borderRadius: 6,
                }}
              >
                <div style={{ fontSize: 11, fontWeight: 600, textTransform: 'uppercase', color: 'var(--color-text-muted)', marginBottom: 8 }}>
                  Friction Flags
                </div>
                {!frictionMap[f.id] ? (
                  <div style={{ fontSize: 11, color: 'var(--color-text-muted)' }}>Loading…</div>
                ) : frictionMap[f.id].length === 0 ? (
                  <div style={{ fontSize: 11, color: 'var(--color-signal-green, #22c55e)' }}>No friction flags</div>
                ) : (
                  frictionMap[f.id].map((ff) => (
                    <div
                      key={ff.id}
                      style={{
                        padding: '4px 0',
                        fontSize: 11,
                        color: ff.is_active ? 'var(--color-signal-red, #ef4444)' : 'var(--color-text-muted)',
                        display: 'flex',
                        gap: 6,
                        alignItems: 'center',
                      }}
                    >
                      <span style={{ width: 6, height: 6, borderRadius: 3, background: ff.is_active ? 'var(--color-signal-red, #ef4444)' : 'var(--color-text-muted)', flexShrink: 0 }} />
                      <span style={{ fontWeight: 600 }}>{ff.category}</span>
                      <span>{ff.title}</span>
                    </div>
                  ))
                )}
              </motion.div>
            )}
          </div>
        ))}
      </div>
    </div>
  );
}
