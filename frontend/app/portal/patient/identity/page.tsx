'use client';

import { useEffect, useState, useCallback } from 'react';
import { motion } from 'framer-motion';
import {
  listPatientPortalIdentityDuplicates,
  listPatientPortalIdentityMerges,
  type PatientPortalIdentityDuplicateCandidateApi,
  type PatientPortalIdentityMergeRequestApi,
} from '@/services/api';

/* ── Types ───────────────────────────────────────────────────────────── */

type DuplicateCandidate = PatientPortalIdentityDuplicateCandidateApi;
type MergeRequest = PatientPortalIdentityMergeRequestApi;

/* ── Page ─────────────────────────────────────────────────────────────── */

export default function PatientIdentityPage() {
  const [tab, setTab] = useState<'duplicates' | 'merges'>('duplicates');
  const [duplicates, setDuplicates] = useState<DuplicateCandidate[]>([]);
  const [merges, setMerges] = useState<MergeRequest[]>([]);
  const [loading, setLoading] = useState(true);

  const fetchData = useCallback(async () => {
    try {
      const [duplicateItems, mergeItems] = await Promise.all([
        listPatientPortalIdentityDuplicates(),
        listPatientPortalIdentityMerges(),
      ]);
      setDuplicates(duplicateItems);
      setMerges(mergeItems);
    } catch (_e) {
      /* silent */
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchData();
  }, [fetchData]);

  const tabStyle = (active: boolean) => ({
    fontSize: 12,
    fontWeight: 600 as const,
    padding: '6px 16px',
    cursor: 'pointer' as const,
    background: active ? 'var(--color-brand-orange, #f97316)' : 'transparent',
    color: active ? '#000' : 'var(--color-text-muted, #a1a1aa)',
    border: active ? 'none' : '1px solid var(--color-border-default, #27272a)',
    borderRadius: 4,
  });

  return (
    <div style={{ minHeight: '100vh', padding: '2rem', maxWidth: 1100, margin: '0 auto' }}>
      <h1 style={{ fontSize: 20, fontWeight: 700, color: 'var(--color-text-primary, #fafafa)', marginBottom: 4 }}>
        Patient Identity Manager
      </h1>
      <p style={{ fontSize: 12, color: 'var(--color-text-muted, #a1a1aa)', marginBottom: 20 }}>
        Duplicate detection queue and merge request workflow
      </p>

      {/* ── TABS ──────────────────────────────────────────────────── */}
      <div style={{ display: 'flex', gap: 8, marginBottom: 20 }}>
        <button onClick={() => setTab('duplicates')} style={tabStyle(tab === 'duplicates')}>
          Duplicates ({duplicates.length})
        </button>
        <button onClick={() => setTab('merges')} style={tabStyle(tab === 'merges')}>
          Merge Requests ({merges.length})
        </button>
      </div>

      {loading && (
        <div style={{ color: 'var(--color-text-muted)', fontSize: 12 }}>Loading…</div>
      )}

      {/* ── DUPLICATES TAB ────────────────────────────────────────── */}
      {tab === 'duplicates' && !loading && (
        <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
          {duplicates.length === 0 ? (
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
              No unresolved duplicate candidates
            </div>
          ) : (
            duplicates.map((d) => (
              <motion.div
                key={d.id}
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
                  <div>
                    <span style={{ fontSize: 12, fontWeight: 600, color: 'var(--color-text-primary)' }}>
                      Patients: {d.patient_a_id.slice(0, 8)}… ↔ {d.patient_b_id.slice(0, 8)}…
                    </span>
                    <span
                      style={{
                        marginLeft: 8,
                        fontSize: 10,
                        fontWeight: 700,
                        color: d.confidence_score >= 0.8
                          ? 'var(--color-signal-red, #ef4444)'
                          : 'var(--color-signal-amber, #f59e0b)',
                      }}
                    >
                      {(d.confidence_score * 100).toFixed(0)}% match
                    </span>
                  </div>
                  <span
                    style={{
                      fontSize: 9,
                      fontWeight: 700,
                      textTransform: 'uppercase',
                      padding: '2px 6px',
                      borderRadius: 3,
                      background: 'var(--color-signal-amber, #f59e0b)22',
                      color: 'var(--color-signal-amber, #f59e0b)',
                    }}
                  >
                    {d.resolution}
                  </span>
                </div>
                {d.detection_method && (
                  <div style={{ fontSize: 10, color: 'var(--color-text-muted)', marginTop: 4 }}>
                    Method: {d.detection_method}
                  </div>
                )}
              </motion.div>
            ))
          )}
        </div>
      )}

      {/* ── MERGES TAB ────────────────────────────────────────────── */}
      {tab === 'merges' && !loading && (
        <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
          {merges.length === 0 ? (
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
              No merge requests
            </div>
          ) : (
            merges.map((m) => (
              <motion.div
                key={m.id}
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
                  <div>
                    <span style={{ fontSize: 12, fontWeight: 600, color: 'var(--color-text-primary)' }}>
                      Merge: {m.source_patient_id.slice(0, 8)}… → {m.target_patient_id.slice(0, 8)}…
                    </span>
                  </div>
                  <span
                    style={{
                      fontSize: 9,
                      fontWeight: 700,
                      textTransform: 'uppercase',
                      padding: '2px 6px',
                      borderRadius: 3,
                      background: m.status === 'PENDING_REVIEW'
                        ? 'var(--color-signal-amber, #f59e0b)22'
                        : m.status === 'APPROVED'
                        ? 'var(--color-signal-green, #22c55e)22'
                        : 'var(--color-signal-red, #ef4444)22',
                      color: m.status === 'PENDING_REVIEW'
                        ? 'var(--color-signal-amber, #f59e0b)'
                        : m.status === 'APPROVED'
                        ? 'var(--color-signal-green, #22c55e)'
                        : 'var(--color-signal-red, #ef4444)',
                    }}
                  >
                    {m.status}
                  </span>
                </div>
                {m.merge_reason && (
                  <div style={{ fontSize: 11, color: 'var(--color-text-muted)', marginTop: 4 }}>
                    {m.merge_reason}
                  </div>
                )}
                <div style={{ fontSize: 10, color: 'var(--color-text-muted)', marginTop: 2 }}>
                  Created {new Date(m.created_at).toLocaleDateString()}
                </div>
              </motion.div>
            ))
          )}
        </div>
      )}
    </div>
  );
}
