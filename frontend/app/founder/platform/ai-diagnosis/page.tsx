'use client';

import { useEffect, useState } from 'react';
import { motion } from 'framer-motion';
import { getPlatformAIDiagnosis, getTenantAIDiagnosis } from '@/services/api';

interface PlatformAdminIssue {
  issue_name: string;
  severity: string;
  source: string;
  what_is_wrong: string;
  why_it_matters: string;
  what_you_should_do: string;
  platform_context: string;
  human_review: string;
  confidence: string;
  basis: string;
  rule_reference: string;
}

const SEVERITY_COLORS: Record<string, string> = {
  BLOCKING: 'text-red-400 bg-red-500/10 border-red-500/30',
  HIGH: 'text-[#FF4D00] bg-[rgba(255,77,0,0.10)] border-orange-500/30',
  MEDIUM: 'text-yellow-400 bg-yellow-500/10 border-yellow-500/30',
  LOW: 'text-blue-400 bg-blue-500/10 border-blue-500/30',
};

const CONFIDENCE_COLORS: Record<string, string> = {
  HIGH: 'text-green-400',
  MEDIUM: 'text-yellow-400',
  LOW: 'text-[#FF4D00]',
};

export default function AIDiagnosisPage() {
  const [issues, setIssues] = useState<PlatformAdminIssue[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [tenantId, setTenantId] = useState('');
  const [tenantIssues, setTenantIssues] = useState<PlatformAdminIssue[]>([]);
  const [tenantLoading, setTenantLoading] = useState(false);

  useEffect(() => {
    async function load() {
      try {
        const data = await getPlatformAIDiagnosis();
        setIssues(data);
      } catch (err: unknown) {
        setError(err instanceof Error ? err.message : 'Failed to load AI diagnosis');
      } finally {
        setLoading(false);
      }
    }
    load();
  }, []);

  async function diagnoseTenant() {
    if (!tenantId) return;
    setTenantLoading(true);
    try {
      const data = await getTenantAIDiagnosis(tenantId);
      setTenantIssues(data);
    } catch {
      setTenantIssues([]);
    } finally {
      setTenantLoading(false);
    }
  }

  function IssueCard({ issue }: { issue: PlatformAdminIssue }) {
    const [expanded, setExpanded] = useState(false);
    return (
      <motion.div
        initial={{ opacity: 0, y: 4 }}
        animate={{ opacity: 1, y: 0 }}
        className={`border p-4 ${SEVERITY_COLORS[issue.severity] || 'text-zinc-500 border-border-DEFAULT bg-[#0A0A0B]'}`}
      >
        <div className="flex items-start justify-between cursor-pointer" onClick={() => setExpanded(!expanded)}>
          <div className="flex-1 min-w-0">
            <div className="flex items-center gap-2 mb-1">
              <span className="text-[9px] px-1.5 py-0.5 font-bold  bg-current/10">{issue.severity}</span>
              <span className="text-[9px] px-1.5 py-0.5 text-zinc-500 bg-zinc-500/10">{issue.source}</span>
              {issue.human_review === 'REQUIRED' && (
                <span className="text-[9px] px-1.5 py-0.5 text-red-400 bg-red-400/10 font-bold">HUMAN REVIEW REQUIRED</span>
              )}
            </div>
            <span className="text-sm font-semibold">{issue.issue_name}</span>
          </div>
          <div className="flex items-center gap-2 flex-shrink-0">
            <span className={`text-[10px] font-semibold ${CONFIDENCE_COLORS[issue.confidence] || 'text-zinc-500'}`}>
              {issue.confidence} confidence
            </span>
            <span className="text-[10px] text-zinc-500">{expanded ? '▼' : '▶'}</span>
          </div>
        </div>

        {expanded && (
          <motion.div initial={{ opacity: 0, height: 0 }} animate={{ opacity: 1, height: 'auto' }} className="mt-3 space-y-2 text-xs">
            <div>
              <span className="text-zinc-500 font-semibold">What is wrong: </span>
              <span className="text-zinc-400">{issue.what_is_wrong}</span>
            </div>
            <div>
              <span className="text-zinc-500 font-semibold">Why it matters: </span>
              <span className="text-zinc-400">{issue.why_it_matters}</span>
            </div>
            <div>
              <span className="text-zinc-500 font-semibold">What you should do: </span>
              <span className="text-zinc-400">{issue.what_you_should_do}</span>
            </div>
            <div className="pt-1 border-t border-white/5 text-[10px] text-zinc-500 space-y-0.5">
              <div>Context: {issue.platform_context}</div>
              <div>Basis: {issue.basis} · Rule: {issue.rule_reference}</div>
            </div>
          </motion.div>
        )}
      </motion.div>
    );
  }

  return (
    <div className="p-6 space-y-6">
      <div className="hud-rail pb-2">
        <h1 className="text-h1 font-bold text-zinc-100">AI Platform Diagnosis</h1>
        <p className="text-body text-zinc-500 mt-1">Automated platform health analysis with structured diagnostic output</p>
      </div>

      {/* Platform-wide diagnosis */}
      <div>
        <h2 className="text-sm font-bold uppercase tracking-widest text-zinc-500 mb-3">
          Platform-Wide Issues
          {!loading && <span className="ml-2 text-zinc-400 font-normal">({issues.length} found)</span>}
        </h2>

        {loading && <div className="text-zinc-500 animate-pulse text-sm">Running diagnostic rules…</div>}
        {error && <div className="text-red-400 text-sm">{error}</div>}

        {!loading && issues.length === 0 && (
          <div className="bg-green-400/10 border border-green-400/30 p-4">
            <span className="text-green-400 text-sm font-semibold">All clear — no platform issues detected</span>
          </div>
        )}

        <div className="space-y-2">
          {issues.map((issue, i) => (
            <IssueCard key={i} issue={issue} />
          ))}
        </div>
      </div>

      {/* Tenant-scoped diagnosis */}
      <div className="bg-[#0A0A0B] border border-border-DEFAULT p-4 space-y-3">
        <h2 className="text-sm font-bold uppercase tracking-widest text-zinc-500">Tenant-Specific Diagnosis</h2>
        <div className="flex gap-2">
          <input
            value={tenantId}
            onChange={(e) => setTenantId(e.target.value)}
            placeholder="Enter tenant ID…"
            className="flex-1 bg-bg-surface border border-border-DEFAULT p-2 text-sm text-zinc-100"
          />
          <button onClick={diagnoseTenant} disabled={tenantLoading || !tenantId}
            className="px-4 py-2 bg-brand-orange text-black text-sm font-semibold disabled:opacity-40">
            {tenantLoading ? 'Diagnosing…' : 'Diagnose Tenant'}
          </button>
        </div>

        {tenantIssues.length > 0 && (
          <div className="space-y-2 mt-2">
            {tenantIssues.map((issue, i) => (
              <IssueCard key={i} issue={issue} />
            ))}
          </div>
        )}

        {!tenantLoading && tenantId && tenantIssues.length === 0 && (
          <div className="text-xs text-zinc-500">No issues found for this tenant (or not yet diagnosed).</div>
        )}
      </div>
    </div>
  );
}
