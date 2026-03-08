'use client';

import { useEffect, useState, useCallback } from 'react';
import Link from 'next/link';
import { motion } from 'framer-motion';
import { getAIReviewQueue, approveAIReview, rejectAIReview } from '@/services/api';
import { ReviewQueueShell } from '@/components/shells/PageShells';
import {
  ErrorState,
  QuantumCardSkeleton,
  QuantumEmptyState,
  ReviewRequiredBanner,
  SeverityBadge,
  StatusChip,
} from '@/components/ui';
import type { SeverityLevel, StatusVariant } from '@/lib/design-system/tokens';

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

const PRIORITY_SEVERITY_MAP: Record<string, SeverityLevel> = {
  CRITICAL: 'BLOCKING',
  HIGH: 'HIGH',
  MEDIUM: 'MEDIUM',
  LOW: 'LOW',
  INFO: 'INFORMATIONAL',
};

const REVIEW_STATUS_MAP: Record<string, StatusVariant> = {
  REVIEW_PENDING: 'review',
  APPROVED: 'active',
  REJECTED: 'critical',
  ESCALATED: 'override',
  OVERRIDDEN: 'override',
};

function prioritySeverity(priority: string): SeverityLevel {
  return PRIORITY_SEVERITY_MAP[priority.toUpperCase()] ?? 'MEDIUM';
}

function reviewStatus(status: string): StatusVariant {
  return REVIEW_STATUS_MAP[status.toUpperCase()] ?? 'neutral';
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

  const listContent = error ? (
    <div className="p-4">
      <ErrorState
        title="Failed to load AI review queue"
        message={error}
        onRetry={fetchQueue}
      />
    </div>
  ) : loading ? (
    <div className="p-4 space-y-2">
      {[0, 1, 2, 3].map((i) => (
        <QuantumCardSkeleton key={i} />
      ))}
    </div>
  ) : items.length === 0 ? (
    <div className="p-4">
      <QuantumEmptyState
        title="No pending review items"
        description="All AI decisions have been reviewed. New items will appear here when human validation is required."
      />
    </div>
  ) : (
    <div className="p-4 space-y-2">
      {items.map((item, i) => (
        <motion.div
          key={item.id}
          initial={{ opacity: 0, y: 6 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: i * 0.03 }}
          className="bg-bg-panel border border-[var(--color-border-default)] p-4 chamfer-8 flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3"
        >
          <div className="flex items-center gap-3 min-w-0">
            <SeverityBadge severity={prioritySeverity(item.priority)} size="sm" label={item.priority} />
            <div className="min-w-0">
              <div className="text-sm font-bold text-text-primary truncate">{item.review_type}</div>
              <div className="text-micro text-text-muted">
                Workflow: <span className="font-mono">{item.workflow_id.slice(0, 8)}</span>
                {' · '}
                {new Date(item.created_at).toLocaleString()}
              </div>
            </div>
          </div>

          <div className="flex items-center gap-2 shrink-0">
            <StatusChip status={reviewStatus(item.status)} size="sm">
              {item.status.replace(/_/g, ' ')}
            </StatusChip>

            {item.status === 'REVIEW_PENDING' && (
              <>
                <button
                  onClick={() => handleApprove(item.id)}
                  disabled={actionLoading === item.id}
                  className="text-micro uppercase tracking-widest font-bold px-3 py-1 chamfer-4 border transition-colors hover:bg-green-500/10 disabled:opacity-50"
                  style={{ color: 'var(--color-status-active)', borderColor: 'rgba(34,197,94,0.35)' }}
                >
                  Approve
                </button>
                <button
                  onClick={() => handleReject(item.id)}
                  disabled={actionLoading === item.id}
                  className="text-micro uppercase tracking-widest font-bold px-3 py-1 chamfer-4 border transition-colors hover:bg-red-500/10 disabled:opacity-50"
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
  );

  return (
    <div className="h-[calc(100vh-80px)] min-h-[680px]">
      <ReviewQueueShell
        title="AI Review Queue"
        count={items.length}
        banner={(
          <ReviewRequiredBanner
            reason="AI-generated decisions in this queue require explicit human review before approval or rejection."
            domain="AI Governance"
          />
        )}
        headerActions={(
          <div className="flex items-center gap-2">
            <button
              onClick={fetchQueue}
              className="text-micro uppercase tracking-widest font-bold px-3 py-1.5 border chamfer-4 text-orange border-orange/30 hover:bg-orange-ghost transition-colors"
            >
              Refresh
            </button>
            <Link href="/founder/ai" className="text-micro uppercase tracking-widest text-text-muted hover:text-orange">
              Back to AI Governance
            </Link>
          </div>
        )}
        list={listContent}
      />
      </div>
  );
}
