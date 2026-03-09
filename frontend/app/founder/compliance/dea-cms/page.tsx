"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import Link from "next/link";
import { ErrorState } from '@/components/ui/ErrorState';
import { NextBestActionCard, type NextAction } from '@/components/ui/NextBestActionCard';
import { QuantumEmptyState } from '@/components/ui/QuantumEmptyState';
import { SeverityBadge } from '@/components/ui/SeverityBadge';
import {
  CrossModuleHealth,
  FounderStatusBar,
  type DomainHealth,
} from '@/components/shells/FounderCommand';
import {
  createDEAEvidenceBundle,
  getCMSGateAuditHistory,
  getCMSGateAuditSummary,
  getDEAEvidenceBundleDetail,
  getDEAEvidenceBundlesHistory,
  getDEANarcoticsAuditHistory,
  runDEANarcoticsAudit,
  verifyDEAEvidenceBundleHash,
} from '@/services/api';

type Severity = "ok" | "warn" | "critical";

interface DEAGate {
  name: string;
  passed: boolean;
  weight: number;
  detail: string;
}

interface DEAAuditMetrics {
  count_events: number;
  waste_events: number;
  unwitnessed_waste_events: number;
  seal_events: number;
  open_discrepancies: number;
  resolved_discrepancies: number;
}

interface DEAAuditResult {
  report_id: string;
  generated_at: string;
  score: number;
  passed: boolean;
  hard_block: boolean;
  gates: DEAGate[];
  required_actions: string[];
  metrics: DEAAuditMetrics;
}

interface CMSAuditSummary {
  window_days: number;
  total: number;
  pass_count: number;
  fail_count: number;
  hard_block_count: number;
  bs_flag_count: number;
  pass_rate: number;
  avg_score: number;
}

interface CMSAuditHistoryRow {
  id: string;
  data?: {
    evaluated_at?: string;
    score?: number;
    passed?: boolean;
    hard_block?: boolean;
    case_id?: string;
  };
}

interface EvidenceBundleHistoryRow {
  bundle_id: string;
  generated_at: string;
  immutable_hash: string;
  hash_algorithm: string;
  dea_total: number;
  cms_total: number;
}

interface EvidenceBundleArtifact {
  filename?: string;
  content_type?: string;
  content?: string;
}

interface EvidenceBundleDetail {
  bundle_id: string;
  generated_at: string;
  immutable_hash: string;
  hash_algorithm: string;
  bundle_core: {
    window_days?: number;
    source_manifest?: {
      dea_audit_count?: number;
      cms_gate_count?: number;
    };
    dea_summary?: {
      total?: number;
      pass_rate?: number;
      hard_block_count?: number;
    };
    cms_summary?: {
      total?: number;
      pass_rate?: number;
      hard_block_count?: number;
    };
    findings?: {
      critical_findings?: string[];
      required_actions?: string[];
    };
  };
  csv_artifact?: EvidenceBundleArtifact;
  pdf_payload?: {
    template_id?: string;
    document_title?: string;
    sections?: Array<{ type?: string; title?: string }>;
  };
}

interface EvidenceBundleVerifyResult {
  bundle_id: string;
  hash_algorithm: string;
  stored_hash: string;
  recomputed_hash: string;
  hash_valid: boolean;
  verification_status: string;
  verified_at: string;
}

function fmtTs(value: string | undefined): string {
  if (!value) return "—";
  try {
    return new Date(value).toLocaleString();
  } catch {
    return value;
  }
}

function severityFromScore(score: number): Severity {
  if (score >= 85) return "ok";
  if (score >= 70) return "warn";
  return "critical";
}

function severityClasses(severity: Severity): string {
  if (severity === "ok") return "text-emerald-400 border-emerald-900 bg-emerald-950/30";
  if (severity === "warn") return "text-amber-300 border-amber-900 bg-amber-950/30";
  return "text-red-300 border-red-900 bg-red-950/30";
}

export default function FounderDEACMSPage() {
  const [lookbackDays, setLookbackDays] = useState(30);
  const [deaLatest, setDeaLatest] = useState<DEAAuditResult | null>(null);
  const [deaHistory, setDeaHistory] = useState<DEAAuditResult[]>([]);
  const [cmsSummary, setCmsSummary] = useState<CMSAuditSummary | null>(null);
  const [cmsHistory, setCmsHistory] = useState<CMSAuditHistoryRow[]>([]);
  const [bundleHistory, setBundleHistory] = useState<EvidenceBundleHistoryRow[]>([]);
  const [bundleDetail, setBundleDetail] = useState<EvidenceBundleDetail | null>(null);
  const [bundleVerify, setBundleVerify] = useState<EvidenceBundleVerifyResult | null>(null);
  const [busy, setBusy] = useState(false);
  const [bundleBusy, setBundleBusy] = useState(false);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const commandActions = useMemo<NextAction[]>(() => {
    const actions: NextAction[] = [];

    if (deaLatest && (!deaLatest.passed || deaLatest.hard_block)) {
      actions.push({
        id: 'dea-hard-block',
        title: 'Resolve DEA narcotics hard-block findings',
        severity: deaLatest.hard_block ? 'BLOCKING' : 'HIGH',
        domain: 'DEA Compliance',
      });
    }

    if ((cmsSummary?.hard_block_count ?? 0) > 0) {
      actions.push({
        id: 'cms-hard-block',
        title: `Resolve ${cmsSummary?.hard_block_count ?? 0} CMS hard-block case(s)`,
        severity: 'BLOCKING',
        domain: 'CMS Gate',
      });
    }

    if ((cmsSummary?.pass_rate ?? 100) < 85) {
      actions.push({
        id: 'cms-pass-rate',
        title: `Improve CMS pass rate from ${cmsSummary?.pass_rate ?? 0}%`,
        severity: 'HIGH',
        domain: 'CMS Gate',
      });
    }

    if (bundleHistory.length === 0) {
      actions.push({
        id: 'bundle-generate',
        title: 'Generate first DEA/CMS inspection evidence bundle',
        severity: 'MEDIUM',
        domain: 'Regulatory Evidence',
      });
    }

    if (actions.length === 0) {
      actions.push({
        id: 'command-stable',
        title: 'DEA/CMS command stable; continue periodic audit cadence',
        severity: 'INFORMATIONAL',
        domain: 'Compliance Command',
      });
    }

    return actions;
  }, [bundleHistory.length, cmsSummary?.hard_block_count, cmsSummary?.pass_rate, deaLatest]);

  const complianceDomainHealth = useMemo<DomainHealth[]>(() => {
    const deaScore = Math.max(0, Math.min(100, Math.round(deaLatest?.score ?? 0)));
    const cmsScore = Math.max(0, Math.min(100, Math.round(cmsSummary?.pass_rate ?? 0)));
    const evidenceScore = bundleHistory.length > 0 ? 92 : 58;

    return [
      {
        domain: 'compliance',
        score: deaLatest ? deaScore : 55,
        trend: deaLatest?.passed ? 'up' : 'down',
        alertCount: (deaLatest?.metrics?.open_discrepancies ?? 0) + (deaLatest?.hard_block ? 1 : 0),
        topIssue: deaLatest?.hard_block
          ? 'DEA hard-block findings require intervention'
          : 'DEA custody posture stable',
      },
      {
        domain: 'billing',
        score: cmsSummary ? cmsScore : 60,
        trend: (cmsSummary?.pass_rate ?? 0) >= 85 ? 'up' : 'down',
        alertCount: cmsSummary?.hard_block_count ?? 0,
        topIssue: (cmsSummary?.hard_block_count ?? 0) > 0
          ? `${cmsSummary?.hard_block_count ?? 0} CMS hard block(s)`
          : 'CMS gate checks healthy',
      },
      {
        domain: 'ops',
        score: evidenceScore,
        trend: evidenceScore >= 80 ? 'up' : 'stable',
        alertCount: bundleHistory.length === 0 ? 1 : 0,
        topIssue: bundleHistory.length === 0
          ? 'No inspection evidence bundle generated'
          : 'Inspection evidence pipeline active',
      },
    ];
  }, [bundleHistory.length, cmsSummary, deaLatest]);

  const refresh = useCallback(async () => {
    setLoading(true);
    setError("");
    try {
      const [deaRows, summary, history, bundleRows] = await Promise.all([
        getDEANarcoticsAuditHistory(10),
        getCMSGateAuditSummary(30),
        getCMSGateAuditHistory(10),
        getDEAEvidenceBundlesHistory(10),
      ]);

      setDeaHistory(deaRows);
      setDeaLatest(deaRows.length > 0 ? deaRows[0] : null);
      setCmsSummary(summary);
      setCmsHistory(history);
      setBundleHistory(bundleRows);
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "Failed to load compliance command data");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void refresh();
  }, [refresh]);

  async function runDeaAudit(): Promise<void> {
    setBusy(true);
    setError("");
    try {
      const audit = (await runDEANarcoticsAudit({
        lookback_days: lookbackDays,
        min_count_events: 1,
      })) as DEAAuditResult;
      setDeaLatest(audit);
      await refresh();
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "Failed to run DEA audit");
    } finally {
      setBusy(false);
    }
  }

  async function createEvidenceBundle(): Promise<void> {
    setBundleBusy(true);
    setError("");
    setBundleVerify(null);
    try {
      const bundle = (await createDEAEvidenceBundle({
        lookback_days: lookbackDays,
        include_raw_rows: false,
      })) as EvidenceBundleDetail;
      setBundleDetail(bundle);
      await refresh();
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "Failed to generate evidence bundle");
    } finally {
      setBundleBusy(false);
    }
  }

  async function loadEvidenceBundle(bundleId: string): Promise<void> {
    setBundleBusy(true);
    setBundleVerify(null);
    setError("");
    try {
      const detail = (await getDEAEvidenceBundleDetail(bundleId)) as EvidenceBundleDetail;
      setBundleDetail(detail);
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "Failed to load evidence bundle");
    } finally {
      setBundleBusy(false);
    }
  }

  async function verifyEvidenceBundle(bundleId: string): Promise<void> {
    setBundleBusy(true);
    setError("");
    try {
      const result = (await verifyDEAEvidenceBundleHash(bundleId)) as EvidenceBundleVerifyResult;
      setBundleVerify(result);
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "Failed to verify bundle hash");
    } finally {
      setBundleBusy(false);
    }
  }

  function downloadCsv(artifact: EvidenceBundleArtifact | undefined): void {
    if (!artifact?.content) return;
    const blob = new Blob([artifact.content], { type: artifact.content_type || "text/csv" });
    const url = URL.createObjectURL(blob);
    const anchor = document.createElement("a");
    anchor.href = url;
    anchor.download = artifact.filename || "dea_cms_evidence.csv";
    document.body.appendChild(anchor);
    anchor.click();
    anchor.remove();
    URL.revokeObjectURL(url);
  }

  return (
    <div className="p-5 space-y-6">
      <FounderStatusBar
        isLive={!Boolean(error)}
        activeIncidents={(deaLatest?.hard_block ? 1 : 0) + (cmsSummary?.hard_block_count ?? 0)}
      />

      <div className="flex items-start justify-between gap-4">
        <div>
          <div className="text-micro font-bold uppercase tracking-[0.2em] text-orange-dim mb-1">
            DOMAIN 5 · DEA / CMS COMMAND
          </div>
          <h1 className="text-xl font-black uppercase tracking-wider text-zinc-100">DEA & CMS Compliance Command</h1>
          <p className="text-xs text-zinc-500 mt-0.5">
            Controlled-substance audit evidence + CMS medical necessity gate transparency
          </p>
          <div className="mt-3 flex flex-wrap items-center gap-2">
            <SeverityBadge
              severity={
                deaLatest?.hard_block || (cmsSummary?.hard_block_count ?? 0) > 0
                  ? 'BLOCKING'
                  : (cmsSummary?.pass_rate ?? 100) < 85
                    ? 'HIGH'
                    : 'LOW'
              }
              size="sm"
            />
          </div>
        </div>
        <Link
          href="/portal/dea-cms"
          className="text-xs text-blue-400 hover:text-blue-300 transition-colors"
        >
          Open Agency Portal View →
        </Link>
      </div>

      <NextBestActionCard actions={commandActions} title="DEA/CMS Next Best Actions" maxVisible={4} />

      <CrossModuleHealth domains={complianceDomainHealth} compact />

      {error && <ErrorState title="Compliance command error" message={error} />}

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
        <div className="border border-border-DEFAULT bg-[#0A0A0B] p-4 space-y-3">
          <h2 className="text-sm font-semibold text-zinc-100">Run DEA Narcotics Audit</h2>
          <label className="block text-xs text-zinc-500">Lookback window (days)</label>
          <input
            type="number"
            min={1}
            max={365}
            value={lookbackDays}
            onChange={(e) => setLookbackDays(Number(e.target.value || 30))}
            className="w-full bg-black border border-border-DEFAULT px-2 py-1.5 text-xs text-zinc-100"
          />
          <button
            onClick={() => {
              void runDeaAudit();
            }}
            disabled={busy}
            className="w-full px-3 py-2 bg-orange-600 hover:bg-orange-500 disabled:opacity-50 text-xs font-semibold"
          >
            {busy ? "Running…" : "Run DEA Audit"}
          </button>
          <button
            onClick={() => {
              void refresh();
            }}
            disabled={loading}
            className="w-full px-3 py-2 border border-border-DEFAULT text-xs text-zinc-300 hover:bg-zinc-900 disabled:opacity-50"
          >
            Refresh Metrics
          </button>
        </div>

        <div className="border border-border-DEFAULT bg-[#0A0A0B] p-4">
          <h2 className="text-sm font-semibold text-zinc-100 mb-3">Latest DEA Audit</h2>
          {loading ? (
            <p className="text-xs text-zinc-500">Loading DEA audit telemetry...</p>
          ) : !deaLatest ? (
            <QuantumEmptyState
              title="No DEA audit reports yet"
              description="Run the DEA audit command to establish baseline custody posture."
              className="py-8"
            />
          ) : (
            <div className="space-y-2">
              <div className={`inline-flex px-2 py-1 text-xs border ${severityClasses(severityFromScore(deaLatest.score))}`}>
                Score {deaLatest.score} · {deaLatest.passed ? "PASS" : "FAIL"}
              </div>
              <p className="text-xs text-zinc-500">Generated: {fmtTs(deaLatest.generated_at)}</p>
              <p className="text-xs text-zinc-400">Open discrepancies: {deaLatest.metrics.open_discrepancies}</p>
              <p className="text-xs text-zinc-400">Unwitnessed waste events: {deaLatest.metrics.unwitnessed_waste_events}</p>
              {deaLatest.required_actions.length > 0 && (
                <ul className="mt-2 space-y-1">
                  {deaLatest.required_actions.map((action) => (
                    <li key={action} className="text-xs text-amber-300">• {action}</li>
                  ))}
                </ul>
              )}
            </div>
          )}
        </div>

        <div className="border border-border-DEFAULT bg-[#0A0A0B] p-4">
          <h2 className="text-sm font-semibold text-zinc-100 mb-3">CMS Gate Summary (30d)</h2>
          {loading ? (
            <p className="text-xs text-zinc-500">Loading CMS summary telemetry...</p>
          ) : !cmsSummary ? (
            <QuantumEmptyState
              title="No CMS summary available"
              description="CMS gate history has not produced a summary payload yet."
              className="py-8"
            />
          ) : (
            <div className="grid grid-cols-2 gap-2 text-xs">
              <div className="bg-black border border-border-subtle p-2">
                <p className="text-zinc-500">Total checks</p>
                <p className="text-zinc-100 text-sm font-semibold">{cmsSummary.total}</p>
              </div>
              <div className="bg-black border border-border-subtle p-2">
                <p className="text-zinc-500">Pass rate</p>
                <p className="text-zinc-100 text-sm font-semibold">{cmsSummary.pass_rate}%</p>
              </div>
              <div className="bg-black border border-border-subtle p-2">
                <p className="text-zinc-500">Hard blocks</p>
                <p className="text-zinc-100 text-sm font-semibold">{cmsSummary.hard_block_count}</p>
              </div>
              <div className="bg-black border border-border-subtle p-2">
                <p className="text-zinc-500">Avg score</p>
                <p className="text-zinc-100 text-sm font-semibold">{cmsSummary.avg_score}</p>
              </div>
            </div>
          )}
        </div>

        <div className="border border-border-DEFAULT bg-[#0A0A0B] p-4 space-y-3">
          <h2 className="text-sm font-semibold text-zinc-100">Inspection Evidence Bundle</h2>
          <p className="text-xs text-zinc-500">
            Generates CSV + PDF payload + immutable hash (sha256-jcs) for inspection handoff.
          </p>
          <button
            onClick={() => {
              void createEvidenceBundle();
            }}
            disabled={bundleBusy}
            className="w-full px-3 py-2 bg-blue-600 hover:bg-blue-500 disabled:opacity-50 text-xs font-semibold"
          >
            {bundleBusy ? "Generating…" : "Generate Evidence Bundle"}
          </button>
          {bundleDetail && (
            <div className="space-y-1 border border-border-subtle bg-black p-2">
              <p className="text-xs text-zinc-500">Selected bundle</p>
              <p className="text-xs text-zinc-300 font-mono">{bundleDetail.bundle_id}</p>
              <p className="text-xs text-zinc-500">Hash: {bundleDetail.immutable_hash.slice(0, 18)}…</p>
              <div className="flex gap-2 pt-1">
                <button
                  onClick={() => {
                    downloadCsv(bundleDetail.csv_artifact);
                  }}
                  className="px-2 py-1 text-xs border border-border-DEFAULT text-zinc-300 hover:bg-zinc-900"
                >
                  Download CSV
                </button>
                <button
                  onClick={() => {
                    void verifyEvidenceBundle(bundleDetail.bundle_id);
                  }}
                  disabled={bundleBusy}
                  className="px-2 py-1 text-xs border border-border-DEFAULT text-zinc-300 hover:bg-zinc-900 disabled:opacity-50"
                >
                  Verify Hash
                </button>
              </div>
            </div>
          )}
          {bundleVerify && (
            <div className={`border p-2 text-xs ${bundleVerify.hash_valid ? "border-emerald-900 bg-emerald-950/30 text-emerald-300" : "border-red-900 bg-red-950/30 text-red-300"}`}>
              Verification: {bundleVerify.verification_status} · {fmtTs(bundleVerify.verified_at)}
            </div>
          )}
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        <div className="border border-border-DEFAULT bg-[#0A0A0B] p-4">
          <h3 className="text-sm font-semibold text-zinc-100 mb-3">DEA Audit History</h3>
          <div className="space-y-2">
            {deaHistory.length === 0 && !loading && (
              <QuantumEmptyState title="No DEA history" description="No DEA audit records were returned for this tenant." className="py-6" />
            )}
            {deaHistory.map((row) => (
              <div key={row.report_id} className="border border-border-subtle bg-black p-2">
                <div className="flex items-center justify-between text-xs">
                  <span className="text-zinc-400">{fmtTs(row.generated_at)}</span>
                  <span className={row.passed ? "text-emerald-400" : "text-red-300"}>{row.score}</span>
                </div>
              </div>
            ))}
          </div>
        </div>

        <div className="border border-border-DEFAULT bg-[#0A0A0B] p-4">
          <h3 className="text-sm font-semibold text-zinc-100 mb-3">CMS Gate History</h3>
          <div className="space-y-2">
            {cmsHistory.length === 0 && !loading && (
              <QuantumEmptyState title="No CMS history" description="No CMS gate history rows were returned for this tenant." className="py-6" />
            )}
            {cmsHistory.map((row) => (
              <div key={row.id} className="border border-border-subtle bg-black p-2 text-xs">
                <div className="flex items-center justify-between">
                  <span className="text-zinc-400">{fmtTs(row.data?.evaluated_at)}</span>
                  <span className={row.data?.passed ? "text-emerald-400" : "text-red-300"}>
                    {row.data?.score ?? "—"}
                  </span>
                </div>
                <p className="text-zinc-500 mt-1">Case: {row.data?.case_id ?? "standalone"}</p>
              </div>
            ))}
          </div>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        <div className="border border-border-DEFAULT bg-[#0A0A0B] p-4">
          <h3 className="text-sm font-semibold text-zinc-100 mb-3">Evidence Bundle History</h3>
          <div className="space-y-2">
            {bundleHistory.length === 0 && !loading && (
              <QuantumEmptyState title="No evidence bundles generated" description="Generate an inspection-ready bundle to establish immutable evidence output." className="py-6" />
            )}
            {bundleHistory.map((row) => (
              <div key={row.bundle_id} className="border border-border-subtle bg-black p-2 text-xs space-y-1">
                <div className="flex items-center justify-between">
                  <span className="text-zinc-400">{fmtTs(row.generated_at)}</span>
                  <span className="text-blue-300">DEA {row.dea_total} · CMS {row.cms_total}</span>
                </div>
                <p className="text-zinc-500 font-mono">{row.immutable_hash.slice(0, 24)}…</p>
                <div className="flex gap-2">
                  <button
                    onClick={() => {
                      void loadEvidenceBundle(row.bundle_id);
                    }}
                    disabled={bundleBusy}
                    className="px-2 py-1 border border-border-DEFAULT text-zinc-300 hover:bg-zinc-900 disabled:opacity-50"
                  >
                    Inspect
                  </button>
                  <button
                    onClick={() => {
                      void verifyEvidenceBundle(row.bundle_id);
                    }}
                    disabled={bundleBusy}
                    className="px-2 py-1 border border-border-DEFAULT text-zinc-300 hover:bg-zinc-900 disabled:opacity-50"
                  >
                    Verify
                  </button>
                </div>
              </div>
            ))}
          </div>
        </div>

        <div className="border border-border-DEFAULT bg-[#0A0A0B] p-4">
          <h3 className="text-sm font-semibold text-zinc-100 mb-3">Bundle Detail</h3>
          {!bundleDetail ? (
            <p className="text-xs text-zinc-500">Select a bundle from history to inspect payload details.</p>
          ) : (
            <div className="space-y-2 text-xs">
              <p className="text-zinc-500">Bundle ID: <span className="text-zinc-300 font-mono">{bundleDetail.bundle_id}</span></p>
              <p className="text-zinc-500">Hash algorithm: <span className="text-zinc-300">{bundleDetail.hash_algorithm}</span></p>
              <p className="text-zinc-500">Immutable hash:</p>
              <p className="text-zinc-300 font-mono break-all">{bundleDetail.immutable_hash}</p>
              <p className="text-zinc-500">
                PDF Template: <span className="text-zinc-300">{bundleDetail.pdf_payload?.template_id || "—"}</span>
              </p>
              <p className="text-zinc-500">
                PDF Sections: <span className="text-zinc-300">{bundleDetail.pdf_payload?.sections?.length ?? 0}</span>
              </p>
              <div className="pt-2 border-t border-border-subtle">
                <p className="text-zinc-500 mb-1">Critical Findings</p>
                <ul className="space-y-1">
                  {(bundleDetail.bundle_core.findings?.critical_findings || []).map((finding) => (
                    <li key={finding} className="text-zinc-300">• {finding}</li>
                  ))}
                </ul>
              </div>
            </div>
          )}
        </div>
      </div>

      <Link href="/founder/compliance" className="text-xs text-orange-dim hover:text-[#FF4D00]">
        ← Back to Compliance
      </Link>
    </div>
  );
}
