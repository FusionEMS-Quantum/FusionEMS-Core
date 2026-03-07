'use client';

import { useEffect, useState, useCallback } from 'react';
import Link from 'next/link';
import { motion } from 'framer-motion';
import { getAIReviewQueue, approveAIReview, rejectAIReview } from '@/services/api';

// ── Types ────────────────────────────────────────────────────────────────────

interface ReviewItem {
  id: string;
  workflow_id: string;
  review_type: string;
  priority: string;
  status: string;
  assigned_to: string | null;
  created_at: string;
}

// ── Helpers ──────────────────────────────────────────────────────────────────

function priorityColor(p: string): string {
  switch (p) {
    case 'CRITICAL': return 'var(--color-brand-red)';
    case 'HIGH': return 'var(--color-brand-orange)';
    case 'MEDIUM': return 'var(--color-status-warning)';
    default: return 'var(--color-status-active)';
  }
}

function statusColor(s: string): string {
  switch (s) {
    case 'REVIEW_PENDING': return 'var(--color-status-warning)';
    case 'APPROVED': return 'var(--color-status-active)';
    case 'REJECTED': return 'var(--color-brand-red)';
    default: return 'var(--color-text-muted)';
  }
}

// ── Page ─────────────────────────────────────────────────────────────────────

export default function AiReviewQueuePage() {
  const [items, setItems] = useState<ReviewItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [actionLoading, setActionLoading] = useState<string | null>(null);

  const fetchQueue = useCallback(() => {
    setLoading(true);
    setError('');
    getAIReviewQueue()
      .then((data: ReviewItem[]) => setItems(data))
      .catch(() => setError('Failed to load review queue.'))
      .finally(() => setLoading(false));
  }, []);

  useEffect(() => { fetchQueue(); }, [fetchQueue]);

  async function handleApprove(id: string) {
    setActionLoading(id);
    try {
      await approveAIReview(id);
      fetchQueue();
    } catch {
      setError('Failed to approve item.');
    } finally {
      setActionLoading(null);
    }
  }

  async function handleReject(id: string) {
    const reason = prompt('Rejection reason:');
    if (!reason) return;
    setActionLoading(id);
    try {
      await rejectAIReview(id, reason);
      fetchQueue();
    } catch {
      setError('Failed to reject item.');
    } finally {
      setActionLoading(null);
    }
  }

  return (
    <div className="p-5 min-h-screen space-y-6">
      {/* Header */}
      <div>
        <div className="text-micro font-bold uppercase tracking-[0.2em] text-orange-dim mb-1">AI GOVERNANCE</div>
        <h1 className="text-xl font-black uppercase tracking-wider text-text-primary">AI Review Queue</h1>
        <p className="text-xs text-text-muted mt-0.5">Approve, reject, or take over AI decisions requiring human review</p>
      </div>

      {/* Error banner */}
      {error && (
        <div className="bg-[rgba(255,45,45,0.08)] border border-[rgba(255,45,45,0.35)] p-3 chamfer-4 text-xs text-[var(--color-brand-red)]">
          {error}
        </div>
      )}

      {/* Loading state */}
      {loading ? (
        <div className="space-y-3">
          {[...Array(3)].map((_, i) => (
            <div key={i} className="animate-pulse bg-bg-panel border border-border-DEFAULT h-16 chamfer-8" />
          ))}
        </div>
      ) : items.length === 0 ? (
        <div className="bg-bg-panel border border-border-DEFAULT chamfer-8 p-10 text-center">
          <div className="text-sm text-text-muted">No pending review items</div>
          <p className="text-xs text-[rgba(255,255,255,0.3)] mt-1">All AI decisions have been reviewed.</p>
        </div>
      ) : (
        <div className="space-y-2">
          {items.map((item, i) => (
            <motion.div
              key={item.id}
              initial={{ opacity: 0, y: 6 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: i * 0.03 }}
              className="bg-bg-panel border border-border-DEFAULT p-4 flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3"
              style={{ clipPath: 'polygon(0 0, calc(100% - 10px) 0, 100% 10px, 100% 100%, 0 100%)' }}
            >
              {/* Left: metadata */}
              <div className="flex items-center gap-3 min-w-0">
                <span className="w-2 h-2 rounded-full shrink-0" style={{ background: priorityColor(item.priority) }} />
                <div className="min-w-0">
                  <div className="text-sm font-bold text-text-primary truncate">{item.review_type}</div>
                  <div className="text-micro text-text-muted">
                    Workflow: <span className="font-mono">{item.workflow_id.slice(0, 8)}</span>
                    {' · '}
                    {new Date(item.created_at).toLocaleString()}
                  </div>
                </div>
              </div>

              {/* Right: status + actions */}
              <div className="flex items-center gap-2 shrink-0">
                <span
                  className="text-micro uppercase tracking-widest font-bold px-2 py-0.5 chamfer-4"
                  style={{
                    color: statusColor(item.status),
                    background: `color-mix(in srgb, ${statusColor(item.status)} 12%, transparent)`,
                    border: `1px solid color-mix(in srgb, ${statusColor(item.status)} 30%, transparent)`,
                  }}
                >
                  {item.status.replace(/_/g, ' ')}
                </span>

                {item.status === 'REVIEW_PENDING' && (
                  <>
                    <button
                      onClick={() => handleApprove(item.id)}
                      disabled={actionLoading === item.id}
                      className="text-micro uppercase tracking-widest font-bold px-3 py-1 chamfer-4 border transition-colors hover:bg-[rgba(34,197,94,0.12)] disabled:opacity-50"
                      style={{ color: 'var(--color-status-active)', borderColor: 'rgba(34,197,94,0.35)' }}
                    >
                      Approve
                    </button>
                    <button
                      onClick={() => handleReject(item.id)}
                      disabled={actionLoading === item.id}
                      className="text-micro uppercase tracking-widest font-bold px-3 py-1 chamfer-4 border transition-colors hover:bg-[rgba(255,45,45,0.12)] disabled:opacity-50"
                      style={{ color: 'var(--color-brand-red)', borderColor: 'rgba(255,45,45,0.35)' }}
                    >
                      Reject
                    </button>
                  </>
                )}
              </div>
            </motion.div>
          ))}
        </div>
      )}

      <Link href="/founder/ai" className="text-xs text-orange-dim hover:text-orange">← Back to AI Governance</Link>
    </div>
  );
}
