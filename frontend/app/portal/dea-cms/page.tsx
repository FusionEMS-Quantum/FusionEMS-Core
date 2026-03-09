"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { ModuleDashboardShell } from "@/components/shells/PageShells";
import {
  getCMSGateAuditSummary,
  getDEANarcoticsAuditHistory,
  runDEANarcoticsAudit,
} from "@/services/api";

interface DeaLatest {
  report_id: string;
  generated_at: string;
  result?: {
    score?: number;
    passed?: boolean;
    hard_block?: boolean;
    metrics?: {
      open_discrepancies?: number;
      unwitnessed_waste_events?: number;
    };
  };
  score?: number;
  passed?: boolean;
  hard_block?: boolean;
  metrics?: {
    open_discrepancies?: number;
    unwitnessed_waste_events?: number;
  };
}

interface CmsSummary {
  total: number;
  pass_rate: number;
  hard_block_count: number;
  avg_score: number;
}

function ts(value: string | undefined): string {
  if (!value) return "—";
  try {
    return new Date(value).toLocaleString();
  } catch {
    return value;
  }
}

export default function PortalDeaCmsPage() {
  const [deaLatest, setDeaLatest] = useState<DeaLatest | null>(null);
  const [cmsSummary, setCmsSummary] = useState<CmsSummary | null>(null);
  const [busy, setBusy] = useState(false);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  async function refresh(): Promise<void> {
    setLoading(true);
    setError("");
    try {
      const [deaPayload, cmsPayload] = await Promise.all([
        getDEANarcoticsAuditHistory(1),
        getCMSGateAuditSummary(30),
      ]);

      const deaRows = Array.isArray(deaPayload) ? (deaPayload as DeaLatest[]) : [];
      const cms = cmsPayload as CmsSummary;
      setDeaLatest(deaRows.length > 0 ? deaRows[0] : null);
      setCmsSummary(cms);
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "Failed to load DEA/CMS command data");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    void refresh();
  }, []);

  async function runAudit(): Promise<void> {
    setBusy(true);
    setError("");
    try {
      await runDEANarcoticsAudit({ lookback_days: 30, min_count_events: 1 });
      await refresh();
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "Failed to execute DEA audit");
    } finally {
      setBusy(false);
    }
  }

  const deaScore = deaLatest?.score ?? deaLatest?.result?.score;
  const deaPassed = deaLatest?.passed ?? deaLatest?.result?.passed;
  const deaHardBlock = deaLatest?.hard_block ?? deaLatest?.result?.hard_block;
  const deaOpenDiscrepancies =
    deaLatest?.metrics?.open_discrepancies ?? deaLatest?.result?.metrics?.open_discrepancies;
  const deaUnwitnessed =
    deaLatest?.metrics?.unwitnessed_waste_events ?? deaLatest?.result?.metrics?.unwitnessed_waste_events;

  return (
    <ModuleDashboardShell
      title="DEA & CMS Command"
      subtitle="Agency transparency for narcotics custody and CMS gate quality"
      headerActions={
        <button
          onClick={() => {
            void runAudit();
          }}
          disabled={busy}
          className="px-3 py-1.5 bg-orange-600 hover:bg-orange-500 disabled:opacity-50 text-xs font-semibold"
        >
          {busy ? "Running DEA Audit…" : "Run DEA Audit"}
        </button>
      }
    >
      {error && <div className="mb-4 border border-red-900 bg-red-950/30 text-red-300 text-xs p-3">{error}</div>}

      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        <div className="border border-border-DEFAULT bg-[#0A0A0B] p-4 space-y-2">
          <h2 className="text-sm font-semibold text-zinc-100">DEA Narcotics Audit</h2>
          {loading ? (
            <p className="text-xs text-zinc-500">Loading…</p>
          ) : !deaLatest ? (
            <p className="text-xs text-zinc-500">No audit reports found yet.</p>
          ) : (
            <>
              <p className="text-xs text-zinc-400">Latest run: {ts(deaLatest.generated_at)}</p>
              <p className={deaPassed ? "text-emerald-400 text-sm font-semibold" : "text-red-300 text-sm font-semibold"}>
                Score {deaScore ?? "—"} · {deaPassed ? "PASS" : "FAIL"}
              </p>
              <p className="text-xs text-zinc-500">Hard block: {deaHardBlock ? "YES" : "NO"}</p>
              <p className="text-xs text-zinc-500">Open discrepancies: {deaOpenDiscrepancies ?? 0}</p>
              <p className="text-xs text-zinc-500">Unwitnessed waste events: {deaUnwitnessed ?? 0}</p>
            </>
          )}
        </div>

        <div className="border border-border-DEFAULT bg-[#0A0A0B] p-4 space-y-2">
          <h2 className="text-sm font-semibold text-zinc-100">CMS Gate Summary (30 days)</h2>
          {loading ? (
            <p className="text-xs text-zinc-500">Loading…</p>
          ) : !cmsSummary ? (
            <p className="text-xs text-zinc-500">No CMS summary available.</p>
          ) : (
            <>
              <p className="text-xs text-zinc-500">Total checks: <span className="text-zinc-200">{cmsSummary.total}</span></p>
              <p className="text-xs text-zinc-500">Pass rate: <span className="text-zinc-200">{cmsSummary.pass_rate}%</span></p>
              <p className="text-xs text-zinc-500">Hard blocks: <span className="text-zinc-200">{cmsSummary.hard_block_count}</span></p>
              <p className="text-xs text-zinc-500">Average score: <span className="text-zinc-200">{cmsSummary.avg_score}</span></p>
            </>
          )}
          <Link href="/portal/cases" className="inline-block mt-2 text-xs text-blue-400 hover:text-blue-300">
            Open Cases CMS Gate Workflow →
          </Link>
        </div>
      </div>
    </ModuleDashboardShell>
  );
}
