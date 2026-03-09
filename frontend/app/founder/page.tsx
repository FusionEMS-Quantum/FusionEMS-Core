'use client';

import { useCallback, useEffect, useMemo, useState } from 'react';
import { motion } from 'framer-motion';
import Link from 'next/link';
import { QuantumEmptyState } from '@/components/ui';
import { NextBestActionCard, type NextAction } from '@/components/ui/NextBestActionCard';
import { SeverityBadge } from '@/components/ui/SeverityBadge';
import {
  CrossModuleActions,
  CrossModuleHealth,
  FounderStatusBar,
  type CrossModuleAction,
  type DomainHealth,
} from '@/components/shells/FounderCommand';
import type { SeverityLevel, SystemDomain } from '@/lib/design-system/tokens';
import {
  getARConcentrationRisk,
  getBillingAlerts,
  getBillingARAgingReport,
  getBillingExecutiveSummary,
  getBillingHealth,
  getBillingKPIs,
  getComplianceCommandSummary,
  getDenialHeatmap,
  getFounderComplianceStatus,
  getFounderDashboardMetrics,
  getFounderGrowthSetupWizard,
  getFounderGrowthSummary,
  getFounderOpsSummary,
  getMarginRiskByTenant,
  getReleaseReadiness,
  getRevenueLeakage,
  getRevenueTrend,
  startFounderLaunchOrchestrator,
} from '@/services/api';

type FetchStatus = 'idle' | 'loading' | 'ready' | 'error';
type TelemetryModuleKey =
  | 'dashboard'
  | 'arAging'
  | 'compliance'
  | 'ops'
  | 'growthSummary'
  | 'growthWizard'
  | 'billingHealth'
  | 'billingKpis'
  | 'billingExecutive'
  | 'billingLeakage'
  | 'billingConcentration'
  | 'billingDenials'
  | 'billingAlerts'
  | 'revenueTrend'
  | 'releaseReadiness'
  | 'marginRisk';

type FounderDashboardMetrics = {
  mrr_cents: number;
  tenant_count: number;
  error_count_1h: number;
  as_of: string;
};

type ArAgingSummary = {
  buckets: Array<{ label: string; total_cents: number; count: number }>;
};

type OpsSeverity = 'critical' | 'high' | 'medium' | 'low';

type FounderOpsSummary = {
  deployment_issues: {
    failed_deployments: number;
    retrying_deployments: number;
  };
  payment_failures: {
    past_due_subscriptions: number;
  };
  claims_pipeline: {
    ready_to_submit: number;
    blocked_for_review: number;
    denied: number;
    appeals_drafted: number;
    blocking_issues: number;
  };
  patient_balance_review: {
    open_balances: number;
    autopay_pending: number;
    collections_ready: number;
    total_outstanding_cents: number;
  };
  profile_gaps: {
    missing_tax_profile: number;
    missing_billing_policy: number;
    missing_public_sector_profile: number;
  };
  comms_health: {
    degraded_channels: number;
    total_channels: number;
    open_threads?: number;
    failed_messages?: number;
  };
  crewlink_health: {
    active_alerts: number;
    escalations_last_24h: number;
    pending_no_response?: number;
    completed_last_24h?: number;
  };
  top_actions: Array<{
    domain: string;
    severity: OpsSeverity;
    action: string;
    reason: string;
    category: string;
  }>;
  generated_at: string;
};

type BillingHealthSummary = {
  status?: string;
  health_score?: number;
};

type BillingExecutiveSummary = {
  total_revenue_cents?: number;
  mrr_cents?: number;
  arr_cents?: number;
  as_of?: string;
};

type BillingLeakageSummary = {
  total_leakage_cents?: number;
  item_count?: number;
};

type BillingArConcentration = {
  total_ar_cents?: number;
  concentration?: Array<{ payer: string; pct: number; risk: string }>;
};

type BillingKpisSummary = {
  clean_claim_rate?: number;
  denial_rate?: number;
  total_claims?: number;
  total_revenue_cents?: number;
};

type FounderComplianceStatus = {
  nemsis?: { certified?: boolean; status?: string };
  neris?: { onboarded?: boolean; status?: string };
  compliance_packs?: { active_count?: number };
  overall?: string;
};

type ComplianceCommandSummaryBrief = {
  overall_score: number;
  total_items: number;
  passing_items: number;
  warning_items: number;
  critical_items: number;
  priority_alerts: Array<{ title: string; severity: string; domain: string }>;
  generated_at: string;
};

type BillingDenialHeatmap = {
  heatmap?: Array<{ reason_code: string; count: number }>;
  total_denials?: number;
  top_reason?: string | null;
};

type BillingAlertsSummary = {
  alerts?: Array<{ type: string; count: number; severity: string }>;
  total?: number;
};

type RevenueTrendSummary = {
  historical_monthly?: Record<string, number>;
  avg_monthly_cents?: number;
  months_of_data?: number;
  forecast?: Array<{ month: string; projected_cents: number; confidence: string }>;
};

type ReleaseReadinessGate = {
  name: string;
  passed: boolean;
  detail: string;
};

type ReleaseReadinessSummary = {
  ready: boolean;
  score: string;
  passed_count: number;
  total_count: number;
  verdict: string;
  gates: ReleaseReadinessGate[];
};

type MarginRiskTenant = {
  tenant_id: string;
  name: string;
  billing_tier: string | null;
  total_claims: number;
  revenue_cents: number;
  denied_count: number;
  denial_rate_pct: number;
  net_margin_cents: number;
  margin_pct: number;
  risk_level: string;
};

type MarginRiskSummary = {
  tenants: MarginRiskTenant[];
  total_tenants: number;
  high_risk_count: number;
  as_of: string;
};

type GrowthSummaryMetric = {
  key: string;
  value: number;
};

type FounderGrowthSummary = {
  generated_at: string;
  conversion_events_total: number;
  proposals_total: number;
  proposals_pending: number;
  active_subscriptions: number;
  proposal_to_paid_conversion_pct: number;
  pending_pipeline_cents: number;
  active_mrr_cents: number;
  pipeline_to_mrr_ratio: number;
  graph_mailbox_configured: boolean;
  funnel_stage_counts: GrowthSummaryMetric[];
  lead_tier_distribution: GrowthSummaryMetric[];
  lead_score_buckets: GrowthSummaryMetric[];
};

type GrowthConnectionStatus = {
  service_key: string;
  label: string;
  required: boolean;
  connected: boolean;
  install_state: string;
  permissions_state: string;
  permission_errors: string[];
  token_state: string;
  health_state: string;
  retry_count: number;
  blocking_reason?: string | null;
};

type FounderGrowthSetupWizard = {
  generated_at: string;
  autopilot_ready: boolean;
  blocked_items: string[];
  services: GrowthConnectionStatus[];
};

type LaunchMode = 'autopilot' | 'approval-first' | 'draft-only';

type LaunchOrchestratorRun = {
  run_id: string;
  mode: LaunchMode;
  queued_sync_jobs: number;
  blocked_items: string[];
  status: 'started' | 'blocked';
  generated_at: string;
};

const TELEMETRY_MODULES: TelemetryModuleKey[] = [
  'dashboard',
  'arAging',
  'compliance',
  'ops',
  'growthSummary',
  'growthWizard',
  'billingHealth',
  'billingKpis',
  'billingExecutive',
  'billingLeakage',
  'billingConcentration',
  'billingDenials',
  'billingAlerts',
  'revenueTrend',
  'releaseReadiness',
  'marginRisk',
];

const MODULE_LABELS: Record<TelemetryModuleKey, string> = {
  dashboard: 'Founder dashboard',
  arAging: 'A/R aging',
  compliance: 'Compliance status',
  ops: 'Operations summary',
  growthSummary: 'Growth runtime summary',
  growthWizard: 'Growth setup wizard',
  billingHealth: 'Billing health',
  billingKpis: 'Billing KPIs',
  billingExecutive: 'Billing executive summary',
  billingLeakage: 'Revenue leakage',
  billingConcentration: 'A/R concentration',
  billingDenials: 'Denial heatmap',
  billingAlerts: 'Billing alerts',
  revenueTrend: 'Revenue trend',
  releaseReadiness: 'Release readiness',
  marginRisk: 'Margin risk',
};

const INITIAL_MODULE_STATUS: Record<TelemetryModuleKey, FetchStatus> = {
  dashboard: 'idle',
  arAging: 'idle',
  compliance: 'idle',
  ops: 'idle',
  growthSummary: 'idle',
  growthWizard: 'idle',
  billingHealth: 'idle',
  billingKpis: 'idle',
  billingExecutive: 'idle',
  billingLeakage: 'idle',
  billingConcentration: 'idle',
  billingDenials: 'idle',
  billingAlerts: 'idle',
  revenueTrend: 'idle',
  releaseReadiness: 'idle',
  marginRisk: 'idle',
};

function clampScore(value: number): number {
  if (Number.isNaN(value)) return 0;
  return Math.max(0, Math.min(100, Math.round(value)));
}

function mapOpsDomainToSystemDomain(domain: string): SystemDomain {
  if (['billing', 'payments', 'collections'].includes(domain)) return 'billing';
  if (['crewlink', 'deployment'].includes(domain)) return 'ops';
  if (['compliance', 'profile_gaps'].includes(domain)) return 'compliance';
  if (['communications', 'comms'].includes(domain)) return 'support';
  return 'ops';
}

function mapOpsSeverityToActionSeverity(severity: OpsSeverity): CrossModuleAction['severity'] {
  if (severity === 'critical') return 'BLOCKING';
  if (severity === 'high') return 'HIGH';
  return 'MEDIUM';
}

function mapCrossActionSeverityToSeverityLevel(severity: CrossModuleAction['severity']): SeverityLevel {
  if (severity === 'BLOCKING') return 'BLOCKING';
  if (severity === 'HIGH') return 'HIGH';
  return 'MEDIUM';
}

function KpiCard({
  label,
  value,
  sub,
  trend,
  color,
  href,
}: {
  label: string;
  value: string;
  sub?: string;
  trend?: 'up' | 'down' | 'flat';
  color?: string;
  href?: string;
}) {
  const trendColor = trend === 'up' ? 'var(--color-status-active)' : trend === 'down' ? 'var(--color-brand-red)' : 'rgba(255,255,255,0.38)';
  const trendIcon = trend === 'up' ? '▲' : trend === 'down' ? '▼' : '—';
  
  const inner = (
    <div
      className="bg-[#0A0A0B] border border-border-DEFAULT p-4 h-full flex flex-col justify-between hover:border-brand-orange/[0.3] transition-colors cursor-pointer group"
      style={{ clipPath: 'polygon(0 0, calc(100% - 10px) 0, 100% 10px, 100% 100%, 0 100%)' }}
    >
      <div className="text-micro font-semibold uppercase tracking-widest text-zinc-500 mb-2">{label}</div>
      <div className="text-2xl font-bold text-zinc-100" style={color ? { color } : {}}>{value}</div>
      {sub && (
        <div className="flex items-center gap-1 mt-1">
          {trend && <span className="text-micro" style={{ color: trendColor }}>{trendIcon}</span>}
          <span className="text-body" style={{ color: trendColor }}>{sub}</span>
        </div>
      )}
    </div>
  );
  return (
    <motion.div initial={{ opacity: 0, y: 6 }} animate={{ opacity: 1, y: 0 }} className="h-full">
      {href ? <Link href={href}>{inner}</Link> : inner}
    </motion.div>
  );
}

function SectionHeader({ title, sub, number }: { title: string; sub?: string; number: string }) {
  return (
    <div className="hud-rail pb-2 mb-4">
      <div className="flex items-baseline gap-3">
          <span className="text-micro font-bold text-orange-dim font-mono">MODULE {number}</span>
        <h2 className="text-sm font-bold uppercase tracking-widest text-zinc-100">{title}</h2>
        {sub && <span className="text-xs text-zinc-500">{sub}</span>}
      </div>
    </div>
  );
}

function RiskCard({ label, items }: { label: string; items: { text: string; level: 'ok' | 'warn' | 'crit' }[] }) {
  const levelColor = { ok: 'var(--color-status-active)', warn: 'var(--color-status-warning)', crit: 'var(--color-brand-red)' };
  return (
    <div className="bg-[#0A0A0B] border border-border-DEFAULT p-4" style={{ clipPath: 'polygon(0 0, calc(100% - 10px) 0, 100% 10px, 100% 100%, 0 100%)' }}>
      <div className="text-micro font-semibold uppercase tracking-widest text-zinc-500 mb-3">{label}</div>
      {items.length === 0 ? (
          <div className="text-xs text-zinc-500">No active risk signals detected for this module.</div>
      ) : (
        <div className="space-y-1.5">
          {items.map((item, i) => (
            <div key={i} className="flex items-center gap-2">
              <span className="w-1.5 h-1.5  flex-shrink-0" style={{ background: levelColor[item.level] }} />
              <span className="text-xs text-zinc-400">{item.text}</span>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

function DenialHeatCell({ value, max }: { value: number; max: number }) {
  const intensity = max > 0 ? value / max : 0;
  const bg = intensity > 0.8 ? 'var(--color-brand-red)' : intensity > 0.5 ? '#FF4D00' : intensity > 0.25 ? 'var(--color-status-warning)' : '#0A0A0B';
  const text = intensity > 0.5 ? 'var(--color-text-primary)' : 'rgba(255,255,255,0.65)';
  return (
    <div
      className="flex items-center justify-center h-10 text-xs font-semibold transition-colors"
      style={{ background: bg, color: text }}
    >
      {value}%
    </div>
  );
}

function ActionItemRow({ rank, text, category, urgency }: { rank: number; text: string; category: string; urgency: 'high' | 'medium' | 'low' }) {
  const urgencyColor = { high: 'var(--color-brand-red)', medium: 'var(--color-status-warning)', low: 'var(--color-status-active)' };
  return (
    <div className="flex items-center gap-3 py-2.5 border-b border-white/5 last:border-0">
        <span className="text-micro font-bold text-orange-dim font-mono w-5">{rank}</span>
      <span className="w-1.5 h-1.5  flex-shrink-0" style={{ background: urgencyColor[urgency] }} />
      <span className="flex-1 text-xs text-zinc-100">{text}</span>
      <span className="text-micro uppercase tracking-wider text-zinc-500 bg-zinc-950/5 px-2 py-0.5 chamfer-4">
        {category}
      </span>
    </div>
  );
}

function GrowthVelocityBar({ label, value, max }: { label: string; value: number; max: number }) {
  const pct = max > 0 ? (value / max) * 100 : 0;
  return (
    <div className="flex items-center gap-3">
      <span className="text-micro text-zinc-500 w-10 flex-shrink-0">{label}</span>
      <div className="flex-1 h-1.5 bg-zinc-950/[0.06]  overflow-hidden">
        <motion.div
          className="h-full "
          style={{ background: '#FF4D00' }}
          initial={{ width: 0 }}
          animate={{ width: `${pct}%` }}
          transition={{ duration: 0.8, ease: 'easeOut' }}
        />
      </div>
      <span className="text-xs font-semibold text-zinc-100 w-12 text-right">{value.toLocaleString()}</span>
    </div>
  );
}

export default function FounderExecutivePage() {
  const [metrics, setMetrics] = useState<FounderDashboardMetrics | null>(null);
  const [aging, setAging] = useState<ArAgingSummary | null>(null);
  const [incidentMode, setIncidentMode] = useState(false);
  const [complianceStatus, setComplianceStatus] = useState<FounderComplianceStatus | null>(null);
  const [complianceCommandSummary, setComplianceCommandSummary] = useState<ComplianceCommandSummaryBrief | null>(null);
  const [opsData, setOpsData] = useState<FounderOpsSummary | null>(null);
  const [growthSummary, setGrowthSummary] = useState<FounderGrowthSummary | null>(null);
  const [growthWizard, setGrowthWizard] = useState<FounderGrowthSetupWizard | null>(null);
  const [launchMode, setLaunchMode] = useState<LaunchMode>('approval-first');
  const [launchBusy, setLaunchBusy] = useState(false);
  const [launchRun, setLaunchRun] = useState<LaunchOrchestratorRun | null>(null);
  const [launchError, setLaunchError] = useState<string | null>(null);
  const [billingHealth, setBillingHealth] = useState<BillingHealthSummary | null>(null);
  const [billingKpis, setBillingKpis] = useState<BillingKpisSummary | null>(null);
  const [billingExec, setBillingExec] = useState<BillingExecutiveSummary | null>(null);
  const [billingLeakage, setBillingLeakage] = useState<BillingLeakageSummary | null>(null);
  const [billingArConcentration, setBillingArConcentration] = useState<BillingArConcentration | null>(null);
  const [billingDenials, setBillingDenials] = useState<BillingDenialHeatmap | null>(null);
  const [billingAlerts, setBillingAlerts] = useState<BillingAlertsSummary | null>(null);
  const [revenueTrend, setRevenueTrend] = useState<RevenueTrendSummary | null>(null);
  const [releaseReadiness, setReleaseReadiness] = useState<ReleaseReadinessSummary | null>(null);
  const [marginRisk, setMarginRisk] = useState<MarginRiskSummary | null>(null);
  const [moduleStatus, setModuleStatus] = useState<Record<TelemetryModuleKey, FetchStatus>>(INITIAL_MODULE_STATUS);
  const [moduleErrors, setModuleErrors] = useState<Partial<Record<TelemetryModuleKey, string>>>({});

  const fetchAllTelemetry = useCallback((): void => {
    const runFetch = async <T,>(
      key: TelemetryModuleKey,
      loader: () => Promise<T>,
      setter: (_payload: T) => void,
    ): Promise<void> => {
      setModuleStatus((prev) => ({ ...prev, [key]: 'loading' }));
      try {
        const payload = await loader();
        setter(payload);
        setModuleStatus((prev) => ({ ...prev, [key]: 'ready' }));
        setModuleErrors((prev) => {
          const next = { ...prev };
          delete next[key];
          return next;
        });
      } catch (e: unknown) {
        const message = e instanceof Error ? e.message : 'Unknown telemetry fetch error';
        setModuleStatus((prev) => ({ ...prev, [key]: 'error' }));
        setModuleErrors((prev) => ({ ...prev, [key]: message }));
        console.warn('[fetch error]', key, message);
      }
    };

    void runFetch<FounderDashboardMetrics>('dashboard', getFounderDashboardMetrics, setMetrics);
    void runFetch<ArAgingSummary>('arAging', getBillingARAgingReport, setAging);
    void runFetch<FounderComplianceStatus>('compliance', getFounderComplianceStatus, setComplianceStatus);
    // Also fetch the 7-domain compliance command summary for enriched domain health
    getComplianceCommandSummary(30)
      .then(setComplianceCommandSummary)
      .catch(() => { /* graceful degradation: fall back to basic compliance status */ });
    void runFetch<FounderOpsSummary>('ops', getFounderOpsSummary, setOpsData);
    void runFetch<FounderGrowthSummary>('growthSummary', getFounderGrowthSummary, setGrowthSummary);
    void runFetch<FounderGrowthSetupWizard>('growthWizard', getFounderGrowthSetupWizard, setGrowthWizard);
    void runFetch<BillingHealthSummary>('billingHealth', getBillingHealth, setBillingHealth);
    void runFetch<BillingKpisSummary>('billingKpis', getBillingKPIs, setBillingKpis);
    void runFetch<BillingExecutiveSummary>('billingExecutive', getBillingExecutiveSummary, setBillingExec);
    void runFetch<BillingLeakageSummary>('billingLeakage', getRevenueLeakage, setBillingLeakage);
    void runFetch<BillingArConcentration>('billingConcentration', getARConcentrationRisk, setBillingArConcentration);
    void runFetch<BillingDenialHeatmap>('billingDenials', getDenialHeatmap, setBillingDenials);
    void runFetch<BillingAlertsSummary>('billingAlerts', getBillingAlerts, setBillingAlerts);
    void runFetch<RevenueTrendSummary>('revenueTrend', getRevenueTrend, setRevenueTrend);
    void runFetch<ReleaseReadinessSummary>('releaseReadiness', getReleaseReadiness, setReleaseReadiness);
    void runFetch<MarginRiskSummary>('marginRisk', getMarginRiskByTenant, setMarginRisk);
  }, []);

  useEffect(() => {
    fetchAllTelemetry();
  }, [fetchAllTelemetry]);

  useEffect(() => {
    const intervalId = window.setInterval(() => {
      fetchAllTelemetry();
    }, 15000);
    return () => window.clearInterval(intervalId);
  }, [fetchAllTelemetry]);

  const startLaunchOrchestrator = useCallback(async (): Promise<void> => {
    setLaunchBusy(true);
    setLaunchError(null);
    try {
      const payload = await startFounderLaunchOrchestrator({ mode: launchMode, auto_queue_sync_jobs: true }) as LaunchOrchestratorRun;
      setLaunchRun(payload);
      if (payload.status === 'blocked') {
        setLaunchError(`Launch blocked: ${payload.blocked_items.join(' · ') || 'setup prerequisites not satisfied'}`);
      }
      fetchAllTelemetry();
    } catch (e: unknown) {
      setLaunchError(e instanceof Error ? e.message : 'Unable to start launch orchestrator');
    } finally {
      setLaunchBusy(false);
    }
  }, [fetchAllTelemetry, launchMode]);

  const mrr = metrics?.mrr_cents;
  const arr = mrr != null ? mrr * 12 : null;
  const mrrDisplay = mrr != null ? `$${(mrr / 100).toLocaleString()}` : '—';
  const arrDisplay = arr != null ? `$${(arr / 100).toLocaleString()}` : '—';
  const tenantCount = metrics?.tenant_count ?? '—';
  const errorCount = metrics?.error_count_1h ?? 0;
  const totalAR = aging ? aging.buckets.reduce((a, b) => a + b.total_cents, 0) / 100 : null;

  const degradedModules = TELEMETRY_MODULES.filter((key) => moduleStatus[key] === 'error');
  const hasTelemetryDegradation = degradedModules.length > 0;

  const denialHeatmap = billingDenials?.heatmap ?? [];
  const complianceScoreValue = ((complianceStatus?.compliance_packs?.active_count ?? 0) * 20)
    + (complianceStatus?.nemsis?.certified ? 30 : 0)
    + (complianceStatus?.neris?.onboarded ? 30 : 0);
  const complianceScore = `${Math.min(100, complianceScoreValue)}%`;
  const cleanClaimRate = billingKpis?.clean_claim_rate != null ? `${billingKpis.clean_claim_rate.toFixed(1)}%` : '—';
  const denialRate = billingKpis?.denial_rate != null ? `${billingKpis.denial_rate.toFixed(1)}%` : '—';
  const exportSuccessRateValue = (
    Number(Boolean(complianceStatus?.nemsis?.certified))
    + Number(Boolean(complianceStatus?.neris?.onboarded))
  ) / 2;
  const exportSuccessRate = `${Math.round(exportSuccessRateValue * 100)}%`;

  const billingHealthScoreNum = Number(billingHealth?.health_score ?? 0);
  const complianceScoreNum = Math.min(100, complianceScoreValue);
  const failedDeployments = opsData?.deployment_issues?.failed_deployments ?? 0;
  const pastDueSubscriptions = opsData?.payment_failures?.past_due_subscriptions ?? 0;
  const degradedChannels = opsData?.comms_health?.degraded_channels ?? 0;
  const crewEscalations = opsData?.crewlink_health?.escalations_last_24h ?? 0;

  const apiHealthScore = clampScore(100 - Math.min(80, errorCount * 3) - degradedModules.length * 8);
  const operationsScore = clampScore(100 - failedDeployments * 20 - crewEscalations * 4 - degradedModules.length * 10);
  const supportScore = clampScore(100 - degradedChannels * 30 - (opsData?.comms_health?.failed_messages ?? 0));
  const schedulingScore = clampScore(100 - crewEscalations * 12 - (opsData?.crewlink_health?.pending_no_response ?? 0) * 2);

  const commandDomainHealth: DomainHealth[] = [
    {
      domain: 'billing',
      score: clampScore(billingHealthScoreNum),
      trend: (billingKpis?.denial_rate ?? 0) > 10 ? 'down' : 'stable',
      alertCount: (billingAlerts?.total ?? 0) + (billingLeakage?.item_count ?? 0),
      topIssue: billingAlerts?.alerts?.[0]?.type?.replaceAll('_', ' ') || 'Billing telemetry nominal',
    },
    {
      domain: 'ops',
      score: operationsScore,
      trend: failedDeployments > 0 ? 'down' : 'stable',
      alertCount: failedDeployments + crewEscalations,
      topIssue: failedDeployments > 0 ? `${failedDeployments} failed deployments` : 'Deployment and crew operations stable',
    },
    {
      domain: 'compliance',
      score: clampScore(complianceCommandSummary?.overall_score ?? complianceScoreNum),
      trend: (complianceCommandSummary?.overall_score ?? complianceScoreNum) < 70 ? 'down' : 'stable',
      alertCount: complianceCommandSummary
        ? complianceCommandSummary.critical_items + complianceCommandSummary.warning_items
        : (complianceStatus?.nemsis?.certified ? 0 : 1) + (complianceStatus?.neris?.onboarded ? 0 : 1),
      topIssue: complianceCommandSummary?.priority_alerts?.[0]?.title
        ?? (complianceStatus?.overall === 'none' ? 'Compliance artifacts missing' : 'Compliance controls active'),
    },
    {
      domain: 'support',
      score: supportScore,
      trend: degradedChannels > 0 ? 'down' : 'stable',
      alertCount: degradedChannels + (opsData?.comms_health?.failed_messages ?? 0),
      topIssue: degradedChannels > 0 ? `${degradedChannels} communication channels degraded` : 'Communication channels healthy',
    },
    {
      domain: 'ai',
      score: clampScore(apiHealthScore),
      trend: hasTelemetryDegradation ? 'down' : 'up',
      alertCount: degradedModules.length,
      topIssue: hasTelemetryDegradation ? 'Telemetry degradation affecting AI summaries' : 'AI command telemetry online',
    },
    {
      domain: 'scheduling',
      score: schedulingScore,
      trend: crewEscalations > 0 ? 'down' : 'stable',
      alertCount: crewEscalations,
      topIssue: crewEscalations > 0 ? `${crewEscalations} crew escalation(s) in last 24h` : 'Crew response posture stable',
    },
  ];

  const commandTopActions = useMemo<CrossModuleAction[]>(() => [
    ...(opsData?.top_actions ?? []).map((action, index) => ({
      id: `ops-${index}-${action.domain}`,
      label: action.action,
      domain: mapOpsDomainToSystemDomain(action.domain),
      severity: mapOpsSeverityToActionSeverity(action.severity),
      href: action.domain === 'billing' ? '/billing-command' : '/founder/ops/command',
    })),
    ...((growthWizard?.blocked_items ?? []).slice(0, 4).map((item, index) => ({
      id: `growth-wizard-blocked-${index}`,
      label: item,
      domain: 'ops' as const,
      severity: 'BLOCKING' as const,
      href: '/founder/integration-command',
    }))),
    ...(growthSummary && !growthSummary.graph_mailbox_configured
      ? [{
          id: 'growth-graph-missing',
          label: 'Microsoft 365 Graph mailbox credentials missing for founder outbound automation',
          domain: 'support' as const,
          severity: 'HIGH' as const,
          href: '/founder/tools/email',
        }]
      : []),
    ...(billingAlerts?.alerts ?? []).map((alert, index) => ({
      id: `billing-alert-${index}-${alert.type}`,
      label: `${alert.type.replaceAll('_', ' ')} (${alert.count})`,
      domain: 'billing' as const,
      severity: (alert.severity === 'high' ? 'HIGH' : 'MEDIUM') as CrossModuleAction['severity'],
      href: '/billing-command',
    })),
    ...degradedModules.map((module) => ({
      id: `module-${module}-degraded`,
      label: `${MODULE_LABELS[module]} telemetry unavailable`,
      domain: 'ops' as const,
      severity: 'BLOCKING' as const,
      href: '/founder',
    })),
  ], [billingAlerts?.alerts, degradedModules, growthSummary, growthWizard?.blocked_items, opsData?.top_actions]);

  const founderNextActions = useMemo<NextAction[]>(() => {
    const actions: NextAction[] = commandTopActions.slice(0, 8).map((action) => ({
      id: action.id,
      title: action.label,
      severity: mapCrossActionSeverityToSeverityLevel(action.severity),
      domain: action.domain,
      href: action.href,
    }));

    if (actions.length === 0) {
      actions.push({
        id: 'founder-command-stable',
        title: 'Founder command posture stable; no immediate intervention required.',
        severity: 'INFORMATIONAL',
        domain: 'ops',
        href: '/founder',
      });
    }

    return actions;
  }, [commandTopActions]);

  const actionBriefs = useMemo<Array<{ text: string; category: string; urgency: 'high' | 'medium' | 'low' }>>(() => commandTopActions
    .slice(0, 6)
    .map((action) => ({
      text: action.label,
      category: action.domain,
      urgency: action.severity === 'BLOCKING' || action.severity === 'HIGH'
        ? 'high'
        : action.severity === 'MEDIUM'
          ? 'medium'
          : 'low',
    })), [commandTopActions]);

  const activeIncidentCount = failedDeployments + degradedChannels + pastDueSubscriptions + degradedModules.length;
  const founderOverallSeverity: SeverityLevel = hasTelemetryDegradation || activeIncidentCount > 0
    ? 'BLOCKING'
    : (billingAlerts?.total ?? 0) > 0 || (opsData?.claims_pipeline?.denied ?? 0) > 0
      ? 'HIGH'
      : 'LOW';

  const historicalRevenue = Object.entries(revenueTrend?.historical_monthly ?? {}).map(([month, cents]) => ({
    label: month.slice(5),
    value: Math.round((cents as number) / 100),
  }));
  const revenueMax = Math.max(...historicalRevenue.map((r) => r.value), 1);
  const growthMetrics = {
    tenants: typeof tenantCount === 'number' ? [{ label: 'now', value: tenantCount, max: Math.max(tenantCount, 1) }] : [],
    revenue: historicalRevenue.map((r) => ({ label: r.label, value: r.value, max: revenueMax })),
  };

  const riskInfrastructure: Array<{ text: string; level: 'ok' | 'warn' | 'crit' }> = [
    { text: `${opsData?.deployment_issues?.failed_deployments ?? 0} failed deployments`, level: (opsData?.deployment_issues?.failed_deployments ?? 0) > 0 ? 'crit' : 'ok' },
    { text: `${opsData?.comms_health?.degraded_channels ?? 0} degraded comms channels`, level: (opsData?.comms_health?.degraded_channels ?? 0) > 0 ? 'warn' : 'ok' },
    { text: `${opsData?.crewlink_health?.escalations_last_24h ?? 0} crew escalations (24h)`, level: (opsData?.crewlink_health?.escalations_last_24h ?? 0) > 0 ? 'warn' : 'ok' },
  ];

  const riskBusiness: Array<{ text: string; level: 'ok' | 'warn' | 'crit' }> = [
    { text: `${opsData?.payment_failures?.past_due_subscriptions ?? 0} past-due subscriptions`, level: (opsData?.payment_failures?.past_due_subscriptions ?? 0) > 0 ? 'crit' : 'ok' },
    { text: `${opsData?.claims_pipeline?.denied ?? 0} denied claims`, level: (opsData?.claims_pipeline?.denied ?? 0) > 0 ? 'crit' : 'ok' },
    { text: `${billingLeakage?.item_count ?? 0} leakage candidates`, level: (billingLeakage?.item_count ?? 0) > 0 ? 'warn' : 'ok' },
  ];

  const complianceGauges: Array<{ label: string; value: number; color: string }> = [
    {
      label: 'NEMSIS Readiness',
      value: complianceStatus?.nemsis?.certified ? 100 : 0,
      color: complianceStatus?.nemsis?.certified ? 'var(--color-status-active)' : 'var(--color-status-warning)',
    },
    {
      label: 'NERIS Readiness',
      value: complianceStatus?.neris?.onboarded ? 100 : 0,
      color: complianceStatus?.neris?.onboarded ? 'var(--color-status-active)' : 'var(--color-status-warning)',
    },
    {
      label: 'Compliance Packs',
      value: Math.min(100, (complianceStatus?.compliance_packs?.active_count ?? 0) * 20),
      color: 'var(--color-status-info)',
    },
  ];

  const systemIncidents = [
    ...(typeof opsData?.deployment_issues?.failed_deployments === 'number' && opsData.deployment_issues.failed_deployments > 0
      ? [{ text: `${opsData.deployment_issues.failed_deployments} failed deployments` }]
      : []),
    ...(typeof opsData?.comms_health?.degraded_channels === 'number' && opsData.comms_health.degraded_channels > 0
      ? [{ text: `${opsData.comms_health.degraded_channels} degraded communication channels` }]
      : []),
    ...(typeof opsData?.payment_failures?.past_due_subscriptions === 'number' && opsData.payment_failures.past_due_subscriptions > 0
      ? [{ text: `${opsData.payment_failures.past_due_subscriptions} past-due subscriptions` }]
      : []),
  ];
  const billingHealthDisplay = billingHealth?.status ? String(billingHealth.status).toUpperCase() : '—';
  const billingHealthScore = billingHealth?.health_score != null ? String(billingHealth.health_score) : '—';
  const leakageDisplay = billingLeakage?.total_leakage_cents != null ? `$${(billingLeakage.total_leakage_cents / 100).toLocaleString()}` : '—';
  const claimRevenueDisplay = billingExec?.total_revenue_cents != null ? `$${(billingExec.total_revenue_cents / 100).toLocaleString()}` : '—';
  const concentrationTop = billingArConcentration?.concentration?.[0];
  const arConcentrationDisplay = concentrationTop ? `${concentrationTop.payer} ${concentrationTop.pct}%` : '—';
  const arAtRiskDisplay = billingArConcentration?.total_ar_cents != null ? `$${(billingArConcentration.total_ar_cents / 100).toLocaleString()}` : '—';
  const requiredGrowthServices = growthWizard?.services.filter((service) => service.required) ?? [];
  const requiredGrowthConnected = requiredGrowthServices.filter((service) => service.connected).length;
  const growthMrrDisplay = growthSummary ? `$${(growthSummary.active_mrr_cents / 100).toLocaleString()}` : '—';
  const growthPipelineDisplay = growthSummary ? `$${(growthSummary.pending_pipeline_cents / 100).toLocaleString()}` : '—';

  return (
    <div className="p-5 space-y-8 min-h-screen">
      <FounderStatusBar
        isLive={!hasTelemetryDegradation}
        activeIncidents={activeIncidentCount}
        apiHealth={apiHealthScore}
        tenantCount={typeof tenantCount === 'number' ? tenantCount : undefined}
      />

      {incidentMode && (
        <motion.div
          initial={{ opacity: 0, y: -8 }}
          animate={{ opacity: 1, y: 0 }}
          className="flex items-center gap-3 px-4 py-2 bg-red-ghost border border-red text-red-bright text-sm font-semibold chamfer-4"
        >
          <span className="animate-pulse">⬤</span>
          INCIDENT MODE ACTIVE — All non-critical communications suspended. War room routing engaged.
          <button onClick={() => setIncidentMode(false)} className="ml-auto text-xs underline">Deactivate</button>
        </motion.div>
      )}

      <div className="flex items-center justify-between">
        <div>
          <div className="text-micro font-bold uppercase tracking-[0.2em] text-orange-dim mb-1">FUSIONEMS QUANTUM</div>
          <h1 className="text-xl font-black uppercase tracking-wider text-zinc-100">Founder Command OS</h1>
          <p className="text-xs text-zinc-500 mt-0.5">Executive Command Overview · Real-Time Backend Hooked System</p>
          <div className="mt-2">
            <SeverityBadge severity={founderOverallSeverity} size="sm" />
          </div>
        </div>
        <div className="flex items-center gap-3">
          <Link href="/founder/comms/inbox" className="h-8 px-3 bg-cyan-500/[0.1] border border-cyan-500/[0.25] text-system-billing text-xs font-semibold chamfer-4 hover:bg-cyan-500/[0.15] transition-colors flex items-center gap-1.5">
            <span className="w-1.5 h-1.5  bg-system-billing animate-pulse" />
            Communications
          </Link>
          <Link href="/founder/ai/review-queue" className="h-8 px-3 bg-purple-500/[0.1] border border-purple-500/[0.25] text-system-compliance text-xs font-semibold chamfer-4 hover:bg-purple-500/[0.15] transition-colors flex items-center">
            AI Queue
          </Link>
          <button
            onClick={() => setIncidentMode(true)}
            className="h-8 px-3 bg-red-600/[0.12] border border-red-ghost text-red text-xs font-semibold chamfer-4 hover:bg-red-600/[0.2] transition-colors"
          >
            Incident Mode
          </button>
        </div>
      </div>

      {hasTelemetryDegradation && (
        <motion.div
          initial={{ opacity: 0, y: -6 }}
          animate={{ opacity: 1, y: 0 }}
          className="px-4 py-3 border border-amber-500/30 bg-amber-500/[0.08] text-xs text-amber-300"
          style={{ clipPath: 'polygon(0 0, calc(100% - 10px) 0, 100% 10px, 100% 100%, 0 100%)' }}
        >
          <div className="flex items-center justify-between gap-3 mb-1">
            <div className="font-semibold uppercase tracking-wider text-micro text-amber-200">Telemetry Degraded</div>
            <button
              onClick={fetchAllTelemetry}
              className="px-2 py-1 border border-amber-400/30 text-amber-200 hover:bg-amber-400/10 transition-colors uppercase tracking-wider text-[10px]"
            >
              Retry Telemetry
            </button>
          </div>
          <div className="text-amber-100/80">
            {degradedModules.map((key) => MODULE_LABELS[key]).join(' · ')} unavailable. Founder command is running in partial visibility mode until these signals recover.
          </div>
        </motion.div>
      )}

      <div className="grid grid-cols-1 xl:grid-cols-[2fr_1fr] gap-4">
        <CrossModuleHealth domains={commandDomainHealth} className="xl:col-span-1" />
        <CrossModuleActions actions={commandTopActions} className="xl:col-span-1" />
      </div>

      <NextBestActionCard actions={founderNextActions} title="Founder Command Next Best Actions" maxVisible={5} />

      <div>
        <SectionHeader
          number="X"
          title="Growth Engine Warp Core"
          sub="Live autopilot readiness, connected-service health, and launch execution"
        />
        {moduleStatus.growthSummary === 'loading' || moduleStatus.growthWizard === 'loading' ? (
          <QuantumEmptyState
            title="Loading growth command telemetry..."
            description="Pulling live growth summary and setup wizard status from founder integration APIs."
            icon="activity"
          />
        ) : moduleStatus.growthSummary === 'error' || moduleStatus.growthWizard === 'error' ? (
          <QuantumEmptyState
            title="Growth engine telemetry unavailable"
            description={moduleErrors.growthSummary || moduleErrors.growthWizard || 'Growth command endpoints are not responding.'}
            icon="activity"
          />
        ) : (
          <div className="grid grid-cols-1 xl:grid-cols-[1.5fr_1fr] gap-4">
            <div
              className="relative overflow-hidden border p-5"
              style={{
                borderColor: growthWizard?.autopilot_ready ? 'rgba(34,197,94,0.35)' : 'rgba(255,77,0,0.4)',
                background: 'radial-gradient(circle at 20% 0%, rgba(255,77,0,0.16), transparent 55%), #0A0A0B',
                clipPath: 'polygon(0 0, calc(100% - 14px) 0, 100% 14px, 100% 100%, 0 100%)',
              }}
            >
              <div className="flex flex-wrap items-center justify-between gap-3 mb-4">
                <div>
                  <div className="text-micro uppercase tracking-wider text-zinc-400">Autopilot Readiness</div>
                  <div className={`text-lg font-black ${growthWizard?.autopilot_ready ? 'text-green-300' : 'text-orange-300'}`}>
                    {growthWizard?.autopilot_ready ? 'READY FOR AUTOPILOT' : 'BLOCKED — HUMAN SETUP REQUIRED'}
                  </div>
                </div>
                <div className="flex items-center gap-2">
                  <select
                    value={launchMode}
                    onChange={(event) => setLaunchMode(event.target.value as LaunchMode)}
                    className="h-8 bg-black/40 border border-white/20 px-2 text-xs text-zinc-100"
                  >
                    <option value="autopilot">autopilot</option>
                    <option value="approval-first">approval-first</option>
                    <option value="draft-only">draft-only</option>
                  </select>
                  <button
                    onClick={() => { void startLaunchOrchestrator(); }}
                    disabled={launchBusy}
                    className="h-8 px-3 bg-orange-600/25 border border-orange-400/50 text-orange-200 text-xs font-semibold hover:bg-orange-600/35 disabled:opacity-50"
                  >
                    {launchBusy ? 'Launching…' : 'Start Launch Orchestrator'}
                  </button>
                </div>
              </div>

              {launchError && (
                <div className="mb-3 px-3 py-2 border border-red-500/40 bg-red-500/10 text-xs text-red-200">
                  {launchError}
                </div>
              )}

              {launchRun && (
                <div className="mb-3 px-3 py-2 border border-white/20 bg-black/30 text-xs text-zinc-300">
                  Run {launchRun.run_id.slice(0, 8)} · {launchRun.status.toUpperCase()} · mode {launchRun.mode} · queued sync jobs {launchRun.queued_sync_jobs}
                </div>
              )}

              <div className="grid grid-cols-2 md:grid-cols-4 gap-3 mb-4">
                <KpiCard label="Active MRR" value={growthMrrDisplay} sub="live subscription base" trend="up" color="var(--color-status-info)" />
                <KpiCard label="Pipeline" value={growthPipelineDisplay} sub="pending proposal value" trend="up" color="var(--color-status-warning)" />
                <KpiCard label="Conversion" value={`${growthSummary?.proposal_to_paid_conversion_pct ?? 0}%`} sub="proposal → paid" trend="flat" color="var(--color-status-active)" />
                <KpiCard label="Graph Mailbox" value={growthSummary?.graph_mailbox_configured ? 'ONLINE' : 'MISSING'} sub="outbound founder email" trend={growthSummary?.graph_mailbox_configured ? 'up' : 'down'} color={growthSummary?.graph_mailbox_configured ? 'var(--color-status-active)' : 'var(--color-brand-red)'} />
              </div>

              <div className="flex flex-wrap items-center gap-3 text-xs">
                <span className="text-zinc-400">Required services connected</span>
                <span className="font-bold text-zinc-100">{requiredGrowthConnected}/{requiredGrowthServices.length}</span>
                <span className="text-zinc-500">•</span>
                <span className="text-zinc-400">Blocked items</span>
                <span className={`font-bold ${(growthWizard?.blocked_items.length ?? 0) > 0 ? 'text-red-300' : 'text-green-300'}`}>{growthWizard?.blocked_items.length ?? 0}</span>
              </div>

              {(growthWizard?.blocked_items.length ?? 0) > 0 && (
                <div className="mt-3 grid grid-cols-1 gap-2">
                  {growthWizard?.blocked_items.slice(0, 4).map((item) => (
                    <div key={item} className="px-3 py-2 border border-red-500/25 bg-red-500/[0.08] text-xs text-red-200">
                      {item}
                    </div>
                  ))}
                </div>
              )}
            </div>

            <div className="bg-[#0A0A0B] border border-border-DEFAULT p-4" style={{ clipPath: 'polygon(0 0, calc(100% - 10px) 0, 100% 10px, 100% 100%, 0 100%)' }}>
              <div className="text-micro uppercase tracking-wider text-zinc-500 mb-3">Connected Services Matrix</div>
              <div className="space-y-2 max-h-[420px] overflow-y-auto pr-1">
                {(growthWizard?.services ?? []).map((service) => (
                  <div key={service.service_key} className="border border-white/10 bg-black/20 p-2">
                    <div className="flex items-center justify-between gap-2">
                      <div className="text-xs font-semibold text-zinc-100">{service.label}</div>
                      <div className={`text-[10px] uppercase tracking-wider ${service.connected ? 'text-green-300' : 'text-red-300'}`}>
                        {service.connected ? 'connected' : 'disconnected'}
                      </div>
                    </div>
                    <div className="mt-1 text-[11px] text-zinc-400">
                      {service.install_state} · perms {service.permissions_state} · token {service.token_state} · health {service.health_state} · retry {service.retry_count}
                    </div>
                    {service.required && !service.connected && (
                      <div className="mt-1 text-[11px] text-red-200">required service is not ready</div>
                    )}
                  </div>
                ))}
              </div>
            </div>
          </div>
        )}
      </div>

      {/* MODULE 1–4 · Revenue & Tenant Metrics */}
      <div>
        <SectionHeader number="1–4" title="Global Revenue Snapshot" sub="MRR · ARR · Tenants · AR Overview" />
        <div className="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-5 gap-3">
          <KpiCard label="MRR" value={mrrDisplay} sub="Monthly Recurring" trend="up" color="var(--color-status-info)" href="/founder/revenue/stripe" />
          <KpiCard label="ARR" value={arrDisplay} sub="Annual Run Rate" trend="up" color="var(--color-status-info)" href="/founder/revenue/forecast" />
          <KpiCard label="Active Tenants" value={String(tenantCount)} sub="Billing accounts" href="/founder/revenue/billing-intelligence" />
          <KpiCard
            label="Total AR"
            value={totalAR != null ? `$${totalAR.toLocaleString()}` : '—'}
            sub="Outstanding claims"
            trend="flat"
            href="/founder/revenue/ar-aging"
          />
          <KpiCard
            label="API Errors (1h)"
            value={String(errorCount)}
            sub="System health"
            trend={errorCount > 10 ? 'down' : 'flat'}
            href="/founder/infra/ecs"
          />
        </div>
      </div>

      {/* MODULE 4B · Business Control */}
      <div>
        <SectionHeader number="4B" title="Business Control" sub="Billing · Accounting · Invoicing · Reconciliation" />
        <div className="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-5 gap-3 mb-4">
          <KpiCard
            label="Billing Health"
            value={billingHealthDisplay}
            sub={`Score ${billingHealthScore}`}
            trend={billingHealthDisplay === 'FAIR' || billingHealthDisplay === 'POOR' ? 'down' : 'flat'}
            color={billingHealthDisplay === 'POOR' ? 'var(--color-brand-red)' : 'var(--color-status-info)'}
            href="/billing-command"
          />
          <KpiCard
            label="Claim Revenue"
            value={claimRevenueDisplay}
            sub="Executive summary"
            trend="up"
            color="var(--color-status-info)"
            href="/billing-command"
          />
          <KpiCard
            label="Revenue Leakage"
            value={leakageDisplay}
            sub={billingLeakage?.item_count != null ? `${billingLeakage.item_count} leakage items` : 'Leakage monitor'}
            trend={billingLeakage?.total_leakage_cents ? 'down' : 'flat'}
            color={billingLeakage?.total_leakage_cents ? 'var(--color-brand-red)' : 'var(--color-status-active)'}
            href="/billing-command"
          />
          <KpiCard
            label="AR Concentration"
            value={arConcentrationDisplay}
            sub="Top payer exposure"
            trend={concentrationTop && concentrationTop.pct > 40 ? 'down' : 'flat'}
            color={concentrationTop && concentrationTop.pct > 40 ? 'var(--color-brand-red)' : 'var(--color-status-warning)'}
            href="/billing-command"
          />
          <KpiCard
            label="Total AR at Risk"
            value={arAtRiskDisplay}
            sub="Concentration model"
            trend="flat"
            href="/billing-command"
          />
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3">
          {[
            {
              href: '/billing-command',
              title: 'Billing Command Center',
              sub: 'Denials · payer performance · leakage · AR concentration',
              tag: 'Command',
              color: 'var(--color-system-billing)',
            },
            {
              href: '/founder/revenue/billing-intelligence',
              title: 'Billing Intelligence',
              sub: 'Revenue velocity · denial intelligence · coding accuracy',
              tag: 'Analytics',
              color: 'var(--color-status-info)',
            },
            {
              href: '/founder/revenue/stripe',
              title: 'Stripe Revenue Ops',
              sub: 'MRR/ARR operations · subscription and payment health',
              tag: 'Payments',
              color: 'var(--color-status-active)',
            },
            {
              href: '/founder/tools/invoice-creator',
              title: 'Invoice Creator',
              sub: 'Generate invoices · track outstanding balances · reminders',
              tag: 'Invoicing',
              color: '#FF4D00',
            },
            {
              href: '/founder/tools/expense-ledger',
              title: 'Expense Ledger',
              sub: 'Capture operating spend · categorize · export accounting bundle',
              tag: 'Accounting',
              color: 'var(--q-yellow)',
            },
            {
              href: '/founder/patient-billing',
              title: 'Patient Billing Command',
              sub: 'Statement/payment orchestration · support linkage · trust risk',
              tag: 'Patient Billing',
              color: 'var(--color-status-info)',
            },
            {
              href: '/founder/legal-requests',
              title: 'Legal Revenue Desk',
              sub: 'Legal request pricing, payment status, and fulfillment holds',
              tag: 'Legal',
              color: 'var(--color-brand-red)',
            },
          ].map((item) => (
            <Link
              key={item.href}
              href={item.href}
              className="bg-[#0A0A0B] border border-border-DEFAULT p-4 hover:border-brand-orange/[0.3] transition-colors"
              style={{ clipPath: 'polygon(0 0, calc(100% - 10px) 0, 100% 10px, 100% 100%, 0 100%)' }}
            >
              <div className="text-micro uppercase tracking-wider font-semibold mb-1" style={{ color: item.color }}>{item.tag}</div>
              <div className="text-sm font-bold text-zinc-100 mb-1">{item.title}</div>
              <div className="text-xs text-zinc-500">{item.sub}</div>
            </Link>
          ))}
        </div>
      </div>

      {/* MODULE 6 · Operations Intelligence (Live Ops Data) */}
      <div>
        <SectionHeader number="6" title="Operations Intelligence" sub="Deployment · Claims · Payments · CrewLink · Comms" />
        {moduleStatus.ops === 'loading' || moduleStatus.ops === 'idle' ? (
          <QuantumEmptyState title="Loading ops data..." description="Connecting to founder operations API." icon="activity" />
        ) : moduleStatus.ops === 'error' ? (
          <QuantumEmptyState
            title="Operations telemetry unavailable"
            description={moduleErrors.ops ?? 'Founder operations summary endpoint is not responding.'}
            icon="activity"
          />
        ) : opsData ? (
          <div className="space-y-4">
            {/* Top 3 Actions */}
            {opsData.top_actions?.length > 0 && (
              <div className="bg-[#0A0A0B] border border-brand-orange/[0.15] p-4" style={{ clipPath: 'polygon(0 0, calc(100% - 14px) 0, 100% 14px, 100% 100%, 0 100%)' }}>
                <div className="flex items-center gap-2 mb-3">
                  <span className="w-1.5 h-1.5  bg-[#FF4D00] animate-pulse" />
                  <span className="text-micro font-bold uppercase tracking-widest text-brand-orange">Top Actions — Right Now</span>
                </div>
                {opsData.top_actions.map((a, i: number) => (
                  <ActionItemRow key={i} rank={i + 1} text={a.action} category={a.domain} urgency={a.severity === 'critical' ? 'high' : a.severity === 'high' ? 'high' : a.severity === 'medium' ? 'medium' : 'low'} />
                ))}
              </div>
            )}

            {/* Ops KPI Grid */}
            <div className="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-6 gap-3">
              <KpiCard
                label="Failed Deployments"
                value={String(opsData.deployment_issues?.failed_deployments ?? 0)}
                sub="Blocking agencies"
                trend={(opsData.deployment_issues?.failed_deployments ?? 0) > 0 ? 'down' : 'flat'}
                color={(opsData.deployment_issues?.failed_deployments ?? 0) > 0 ? 'var(--color-brand-red)' : 'var(--color-status-active)'}
              />
              <KpiCard
                label="Past-Due Subs"
                value={String(opsData.payment_failures?.past_due_subscriptions ?? 0)}
                sub="Revenue at risk"
                trend={(opsData.payment_failures?.past_due_subscriptions ?? 0) > 0 ? 'down' : 'flat'}
                color={(opsData.payment_failures?.past_due_subscriptions ?? 0) > 0 ? 'var(--color-brand-red)' : 'var(--color-status-active)'}
              />
              <KpiCard
                label="Ready to Submit"
                value={String(opsData.claims_pipeline?.ready_to_submit ?? 0)}
                sub="Claims waiting"
                trend={(opsData.claims_pipeline?.ready_to_submit ?? 0) > 0 ? 'up' : 'flat'}
                color="var(--color-status-warning)"
                href="/founder/revenue/billing-intelligence"
              />
              <KpiCard
                label="Denied Claims"
                value={String(opsData.claims_pipeline?.denied ?? 0)}
                sub="Need appeal review"
                trend={(opsData.claims_pipeline?.denied ?? 0) > 0 ? 'down' : 'flat'}
                color={(opsData.claims_pipeline?.denied ?? 0) > 0 ? 'var(--color-brand-red)' : 'var(--color-status-active)'}
                href="/founder/revenue/billing-intelligence"
              />
              <KpiCard
                label="Active Paging"
                value={String(opsData.crewlink_health?.active_alerts ?? 0)}
                sub="CrewLink alerts"
                color="var(--color-status-info)"
              />
              <KpiCard
                label="Comms Degraded"
                value={String(opsData.comms_health?.degraded_channels ?? 0)}
                sub={`of ${opsData.comms_health?.total_channels ?? 0} channels`}
                trend={(opsData.comms_health?.degraded_channels ?? 0) > 0 ? 'down' : 'flat'}
                color={(opsData.comms_health?.degraded_channels ?? 0) > 0 ? 'var(--color-brand-red)' : 'var(--color-status-active)'}
              />
            </div>

            {/* Detailed Panels */}
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
              {/* Claims Pipeline */}
              <RiskCard label="Claims Pipeline" items={[
                { text: `${opsData.claims_pipeline?.ready_to_submit ?? 0} ready to submit`, level: (opsData.claims_pipeline?.ready_to_submit ?? 0) > 0 ? 'warn' : 'ok' },
                { text: `${opsData.claims_pipeline?.blocked_for_review ?? 0} blocked for review`, level: (opsData.claims_pipeline?.blocked_for_review ?? 0) > 0 ? 'crit' : 'ok' },
                { text: `${opsData.claims_pipeline?.denied ?? 0} denied`, level: (opsData.claims_pipeline?.denied ?? 0) > 0 ? 'crit' : 'ok' },
                { text: `${opsData.claims_pipeline?.appeals_drafted ?? 0} appeals drafted`, level: 'warn' },
                { text: `${opsData.claims_pipeline?.blocking_issues ?? 0} blocking issues`, level: (opsData.claims_pipeline?.blocking_issues ?? 0) > 0 ? 'crit' : 'ok' },
              ]} />
              {/* Patient Balances */}
              <RiskCard label="Patient Balances" items={[
                { text: `${opsData.patient_balance_review?.open_balances ?? 0} open balances`, level: 'warn' },
                { text: `${opsData.patient_balance_review?.autopay_pending ?? 0} autopay pending`, level: 'ok' },
                { text: `${opsData.patient_balance_review?.collections_ready ?? 0} collections ready`, level: (opsData.patient_balance_review?.collections_ready ?? 0) > 0 ? 'crit' : 'ok' },
                { text: `$${((opsData.patient_balance_review?.total_outstanding_cents ?? 0) / 100).toLocaleString()} outstanding`, level: (opsData.patient_balance_review?.total_outstanding_cents ?? 0) > 100000 ? 'crit' : 'warn' },
              ]} />
              {/* Profile Gaps */}
              <RiskCard label="Agency Profile Gaps" items={[
                { text: `${opsData.profile_gaps?.missing_tax_profile ?? 0} missing tax profile`, level: (opsData.profile_gaps?.missing_tax_profile ?? 0) > 0 ? 'crit' : 'ok' },
                { text: `${opsData.profile_gaps?.missing_billing_policy ?? 0} missing billing policy`, level: (opsData.profile_gaps?.missing_billing_policy ?? 0) > 0 ? 'warn' : 'ok' },
                { text: `${opsData.profile_gaps?.missing_public_sector_profile ?? 0} missing public sector`, level: (opsData.profile_gaps?.missing_public_sector_profile ?? 0) > 0 ? 'warn' : 'ok' },
              ]} />
            </div>
          </div>
        ) : (
          <QuantumEmptyState
            title="Operations summary unavailable"
            description="No operations summary payload was returned for this tenant."
            icon="activity"
          />
        )}
      </div>

      {/* MODULE 3 · Clean Claim Rate + MODULE 6 · Export Success Rate */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
        <KpiCard label="Clean Claim Rate" value={cleanClaimRate} sub="From API" trend="flat" color="var(--color-status-active)" />
        <KpiCard label="Denial Rate" value={denialRate} sub="From API" trend="flat" color="var(--color-brand-red)" />
        <KpiCard label="Export Success Rate" value={exportSuccessRate} sub="NEMSIS · NERIS" trend="flat" color="var(--color-status-active)" />
        <KpiCard label="Compliance Score" value={complianceScore} sub="Pack coverage" trend="flat" color="var(--color-status-info)" />
      </div>

      {/* MODULE 5 · Denial Rate Heatmap */}
      <div>
        <SectionHeader number="5" title="Denial Intelligence" sub="Live denial reason concentration" />
        {moduleStatus.billingDenials === 'error' ? (
          <QuantumEmptyState
            title="Denial telemetry unavailable"
            description={moduleErrors.billingDenials ?? 'Denial heatmap endpoint is currently unavailable.'}
            icon="activity"
          />
        ) : denialHeatmap.length === 0 ? (
          <QuantumEmptyState title="No denial data" description="No denied-claim reason signals were returned for this tenant." icon="activity" />
        ) : (
          <div className="bg-[#0A0A0B] border border-border-DEFAULT p-4 overflow-x-auto" style={{ clipPath: 'polygon(0 0, calc(100% - 12px) 0, 100% 12px, 100% 100%, 0 100%)' }}>
            <table className="w-full min-w-[600px] text-xs">
              <thead>
                <tr>
                  <th className="text-left text-micro uppercase tracking-wider text-zinc-500 pb-2 pr-4 font-semibold">Reason Code</th>
                  <th className="text-right text-micro uppercase tracking-wider text-zinc-500 pb-2 px-1 font-semibold">Count</th>
                  <th className="text-right text-micro uppercase tracking-wider text-zinc-500 pb-2 px-1 font-semibold">Share</th>
                </tr>
              </thead>
              <tbody>
                {denialHeatmap.map((row) => {
                  const total = billingDenials?.total_denials ?? 0;
                  const pct = total > 0 ? (row.count / total) * 100 : 0;
                  return (
                  <tr key={row.reason_code}>
                    <td className="text-zinc-400 pr-4 py-0.5 whitespace-nowrap">{row.reason_code}</td>
                    <td className="text-zinc-100 text-right px-0.5 py-0.5">{row.count}</td>
                    <td className="px-0.5 py-0.5">
                      <DenialHeatCell value={Math.round(pct)} max={100} />
                    </td>
                  </tr>
                );})}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {/* MODULE 8–9 · AI + Infrastructure */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        {riskInfrastructure.length === 0 ? (
            <RiskCard label="Infrastructure Health" items={[]} />
        ) : (
            <RiskCard label="Infrastructure Health · Module 9" items={riskInfrastructure} />
        )}
        {riskBusiness.length === 0 ? (
            <RiskCard label="Churn Risk" items={[]} />
        ) : (
            <RiskCard label="Churn · Revenue · Compliance Risks · Modules 11–13" items={riskBusiness} />
        )}
        <div className="bg-[#0A0A0B] border border-purple-500/20 p-4" style={{ clipPath: 'polygon(0 0, calc(100% - 10px) 0, 100% 10px, 100% 100%, 0 100%)' }}>
          <div className="flex items-center justify-between mb-3">
            <div className="text-micro font-semibold uppercase tracking-widest text-zinc-500">Module 7 · Compliance Command</div>
            <Link href="/compliance" className="text-[9px] font-bold uppercase tracking-widest text-purple-400 hover:text-purple-300 transition-colors flex items-center gap-1">
              Open 7-Domain Command Center →
            </Link>
          </div>

          {/* Compliance Score + Domain Health */}
          <div className="flex items-center gap-4 mb-3">
            <div className="flex items-center gap-2">
              <div className="text-lg font-black" style={{ color: complianceScoreNum >= 80 ? 'var(--color-status-active)' : complianceScoreNum >= 60 ? 'var(--color-status-warning)' : 'var(--color-brand-red)' }}>{complianceScore}</div>
              <div className="text-[9px] font-bold tracking-widest text-zinc-500 uppercase">Overall</div>
            </div>
            <div className="h-5 w-px bg-white/10" />
            <div className="flex gap-2 text-[9px] font-bold tracking-wider">
              <span className="text-green-400">NEMSIS</span>
              <span className="text-zinc-600">|</span>
              <span className="text-blue-400">HIPAA</span>
              <span className="text-zinc-600">|</span>
              <span className="text-yellow-400">PCR</span>
              <span className="text-zinc-600">|</span>
              <span className="text-cyan-400">Billing</span>
              <span className="text-zinc-600">|</span>
              <span className="text-purple-400">Accred</span>
              <span className="text-zinc-600">|</span>
              <span className="text-red-400">DEA</span>
              <span className="text-zinc-600">|</span>
              <span className="text-orange-400">CMS</span>
            </div>
          </div>

          {/* Compliance Gauges */}
          {!complianceGauges || complianceGauges.length === 0 ? (
             <div className="text-xs text-zinc-500">Compliance telemetry stream has not published values yet.</div>
          ) : complianceGauges.map((item) => (
            <div key={item.label} className="mb-2">
              <div className="flex justify-between text-body mb-0.5">
                <span className="text-zinc-400">{item.label}</span>
                <span className="font-semibold" style={{ color: item.color }}>{item.value}%</span>
              </div>
              <div className="h-1 bg-zinc-950/[0.06]  overflow-hidden">
                <div className="h-full " style={{ width: `${item.value}%`, background: item.color }} />
              </div>
            </div>
          ))}

          {/* Quick Linked Surfaces */}
          <div className="mt-3 pt-3 border-t border-white/5 grid grid-cols-3 gap-2">
            <Link href="/portal/dea-cms" className="text-[10px] text-zinc-500 hover:text-red-400 transition-colors flex items-center gap-1">
              <span className="w-1 h-1 inline-block bg-red-500" />DEA/CMS →
            </Link>
            <Link href="/compliance" className="text-[10px] text-zinc-500 hover:text-purple-400 transition-colors flex items-center gap-1">
              <span className="w-1 h-1 inline-block bg-purple-500" />All Domains →
            </Link>
            <Link href="/founder/compliance/dea-cms" className="text-[10px] text-zinc-500 hover:text-orange-400 transition-colors flex items-center gap-1">
              <span className="w-1 h-1 inline-block bg-orange-500" />Evidence Bundles →
            </Link>
          </div>
        </div>
      </div>

      {/* MODULE 10 · Daily AI Brief */}
      <div>
        <SectionHeader number="10" title="Daily AI Brief" sub="Top Action Items · AI-generated · updated hourly" />
        {actionBriefs.length === 0 ? (
          <QuantumEmptyState title="No active AI briefs" description="All monitored alert classes are currently below action thresholds." icon="activity" />
        ) : (
            <div className="bg-[#0A0A0B] border border-brand-orange/[0.15] p-4" style={{ clipPath: 'polygon(0 0, calc(100% - 14px) 0, 100% 14px, 100% 100%, 0 100%)' }}>
              <div className="flex items-center gap-2 mb-3">
                <span className="w-1.5 h-1.5  bg-[#FF4D00] animate-pulse" />
                <span className="text-micro font-bold uppercase tracking-widest text-brand-orange">Quantum Intelligence Brief — Today</span>
              </div>
              {actionBriefs.map((b, rank: number) => (
                 <ActionItemRow key={rank} rank={rank+1} text={b.text} category={b.category} urgency={b.urgency} />
              ))}
            </div>
        )}
      </div>

      {/* MODULE 14 · System Incident Banner */}
      <div>
        <SectionHeader number="14" title="System Incident Status" />
        <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
          <div
            className={`${systemIncidents.length === 0 ? 'bg-green-500/[0.08] border-green-500/[0.2]' : 'bg-red-500/[0.08] border-red-500/[0.2]'} border p-3 flex items-center gap-3`}
            style={{ clipPath: 'polygon(0 0, calc(100% - 8px) 0, 100% 8px, 100% 100%, 0 100%)' }}
          >
            <span className={`text-xl font-black ${systemIncidents.length === 0 ? 'text-status-active' : 'text-red-bright'}`}>
              {systemIncidents.length === 0 ? '✓' : '!'}
            </span>
            <div>
              <div className={`text-xs font-semibold ${systemIncidents.length === 0 ? 'text-status-active' : 'text-red-bright'}`}>
                {systemIncidents.length === 0 ? 'All Systems Operational' : 'Active Operational Incidents'}
              </div>
              <div className="text-body text-zinc-500">
                {systemIncidents.length === 0 ? 'No active incidents in current founder telemetry.' : `${systemIncidents.length} incident signal(s) require attention.`}
              </div>
            </div>
          </div>
          <div className="bg-[#0A0A0B] border border-border-DEFAULT p-3" style={{ clipPath: 'polygon(0 0, calc(100% - 8px) 0, 100% 8px, 100% 100%, 0 100%)' }}>
            <div className="text-micro uppercase tracking-wider text-zinc-500 mb-2">Recent Incidents</div>
            {systemIncidents.length === 0 ? (
                <div className="text-xs text-zinc-500">No incident signals are currently active in operations telemetry.</div>
            ) : (
              systemIncidents.map((inc, idx: number) => <div key={idx} className="text-xs text-zinc-100">{inc.text}</div>)
            )}
          </div>
        </div>
      </div>

      {/* MODULE 15 · Growth Velocity Graph */}
      <div>
        <SectionHeader number="15" title="Growth Velocity" sub="30 / 90 / 365 day view" />
        <div className="bg-[#0A0A0B] border border-border-DEFAULT p-5 grid grid-cols-1 md:grid-cols-2 gap-6" style={{ clipPath: 'polygon(0 0, calc(100% - 14px) 0, 100% 14px, 100% 100%, 0 100%)' }}>
          <div>
            <div className="text-micro uppercase tracking-wider text-zinc-500 mb-3">Tenant Growth</div>
            {growthMetrics.tenants.length === 0 ? (
                <div className="text-xs text-zinc-500">Tenant growth telemetry has not emitted a datapoint yet.</div>
            ) : (
                <div className="space-y-2">
              {growthMetrics.tenants.map((t) => (
                    <GrowthVelocityBar key={t.label} label={t.label} value={t.value} max={t.max} />
                ))}
                </div>
            )}
          </div>
          <div>
            <div className="text-micro uppercase tracking-wider text-zinc-500 mb-3">Revenue Growth ($)</div>
            {growthMetrics.revenue.length === 0 ? (
                <div className="text-xs text-zinc-500">Revenue trend telemetry has not emitted a datapoint yet.</div>
            ) : (
                <div className="space-y-2">
              {growthMetrics.revenue.map((r) => (
                    <GrowthVelocityBar key={r.label} label={r.label} value={r.value} max={r.max} />
                ))}
                </div>
            )}
          </div>
        </div>
      </div>

      {/* MODULE 16 · Release Readiness Gate */}
      <div>
        <SectionHeader number="16" title="Release Readiness Gate" sub="Infrastructure · integrations · deployment prerequisites" />
        {moduleStatus.releaseReadiness === 'loading' || moduleStatus.releaseReadiness === 'idle' ? (
          <QuantumEmptyState title="Checking release gates..." description="Querying platform release readiness endpoint." icon="activity" />
        ) : moduleStatus.releaseReadiness === 'error' ? (
          <QuantumEmptyState
            title="Release readiness unavailable"
            description={moduleErrors.releaseReadiness ?? 'Release gate endpoint is not responding.'}
            icon="activity"
          />
        ) : releaseReadiness ? (
          <div className="bg-[#0A0A0B] border p-4" style={{
            borderColor: releaseReadiness.ready ? 'rgba(34,197,94,0.25)' : 'rgba(239,68,68,0.25)',
            clipPath: 'polygon(0 0, calc(100% - 12px) 0, 100% 12px, 100% 100%, 0 100%)',
          }}>
            <div className="flex items-center justify-between mb-4">
              <div className="flex items-center gap-3">
                <span className={`text-xl font-black ${releaseReadiness.ready ? 'text-status-active' : 'text-red-bright'}`}>
                  {releaseReadiness.ready ? '✓' : '✗'}
                </span>
                <div>
                  <div className={`text-sm font-bold ${releaseReadiness.ready ? 'text-status-active' : 'text-red-bright'}`}>
                    {releaseReadiness.verdict}
                  </div>
                  <div className="text-body text-zinc-500">Gates passed: {releaseReadiness.score}</div>
                </div>
              </div>
            </div>
            <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-5 gap-2">
              {releaseReadiness.gates.map((gate) => (
                <div
                  key={gate.name}
                  className="flex items-center gap-2 px-3 py-2 border"
                  style={{
                    borderColor: gate.passed ? 'rgba(34,197,94,0.2)' : 'rgba(239,68,68,0.2)',
                    background: gate.passed ? 'rgba(34,197,94,0.05)' : 'rgba(239,68,68,0.05)',
                  }}
                >
                  <span className={`w-2 h-2 flex-shrink-0 ${gate.passed ? 'bg-green-500' : 'bg-red-500'}`} />
                  <div>
                    <div className="text-[10px] font-semibold uppercase tracking-wider text-zinc-300">
                      {gate.name.replaceAll('_', ' ')}
                    </div>
                    <div className="text-[9px] text-zinc-500">{gate.detail}</div>
                  </div>
                </div>
              ))}
            </div>
          </div>
        ) : (
          <QuantumEmptyState title="No readiness data" description="Release gate response was empty." icon="activity" />
        )}
      </div>

      {/* MODULE 17 · Margin Risk by Tenant */}
      <div>
        <SectionHeader number="17" title="Margin Risk by Tenant" sub="Revenue vs cost exposure · per-tenant profitability" />
        {moduleStatus.marginRisk === 'loading' || moduleStatus.marginRisk === 'idle' ? (
          <QuantumEmptyState title="Loading margin analysis..." description="Computing per-tenant margin risk." icon="activity" />
        ) : moduleStatus.marginRisk === 'error' ? (
          <QuantumEmptyState
            title="Margin risk unavailable"
            description={moduleErrors.marginRisk ?? 'Margin risk analytics endpoint is not responding.'}
            icon="activity"
          />
        ) : marginRisk && marginRisk.tenants.length > 0 ? (
          <div className="bg-[#0A0A0B] border border-border-DEFAULT p-4 overflow-x-auto" style={{ clipPath: 'polygon(0 0, calc(100% - 12px) 0, 100% 12px, 100% 100%, 0 100%)' }}>
            <div className="flex items-center justify-between mb-3">
              <div className="text-micro font-bold uppercase tracking-widest text-zinc-500">
                {marginRisk.total_tenants} tenants · {marginRisk.high_risk_count} at risk
              </div>
              <span className="text-body text-zinc-500">as of {marginRisk.as_of?.slice(0, 10)}</span>
            </div>
            <table className="w-full min-w-[700px] text-xs">
              <thead>
                <tr>
                  <th className="text-left text-micro uppercase tracking-wider text-zinc-500 pb-2 pr-2 font-semibold">Tenant</th>
                  <th className="text-right text-micro uppercase tracking-wider text-zinc-500 pb-2 px-1 font-semibold">Claims</th>
                  <th className="text-right text-micro uppercase tracking-wider text-zinc-500 pb-2 px-1 font-semibold">Revenue</th>
                  <th className="text-right text-micro uppercase tracking-wider text-zinc-500 pb-2 px-1 font-semibold">Denial %</th>
                  <th className="text-right text-micro uppercase tracking-wider text-zinc-500 pb-2 px-1 font-semibold">Net Margin</th>
                  <th className="text-right text-micro uppercase tracking-wider text-zinc-500 pb-2 px-1 font-semibold">Margin %</th>
                  <th className="text-center text-micro uppercase tracking-wider text-zinc-500 pb-2 px-1 font-semibold">Risk</th>
                </tr>
              </thead>
              <tbody>
                {marginRisk.tenants.map((t) => {
                  const riskColor = t.risk_level === 'critical' ? 'var(--color-brand-red)' : t.risk_level === 'high' ? '#FF4D00' : t.risk_level === 'medium' ? 'var(--color-status-warning)' : 'var(--color-status-active)';
                  return (
                    <tr key={t.tenant_id} className="border-b border-white/5 last:border-0">
                      <td className="text-zinc-300 pr-2 py-1.5 whitespace-nowrap">{t.name}</td>
                      <td className="text-zinc-100 text-right px-1 py-1.5">{t.total_claims}</td>
                      <td className="text-zinc-100 text-right px-1 py-1.5">${(t.revenue_cents / 100).toLocaleString()}</td>
                      <td className="text-zinc-100 text-right px-1 py-1.5">{t.denial_rate_pct}%</td>
                      <td className="text-right px-1 py-1.5" style={{ color: t.net_margin_cents >= 0 ? 'var(--color-status-active)' : 'var(--color-brand-red)' }}>
                        ${(t.net_margin_cents / 100).toLocaleString()}
                      </td>
                      <td className="text-right px-1 py-1.5" style={{ color: riskColor }}>{t.margin_pct}%</td>
                      <td className="text-center px-1 py-1.5">
                        <span
                          className="inline-block px-2 py-0.5 text-[9px] font-bold uppercase tracking-wider"
                          style={{ color: riskColor, background: `color-mix(in srgb, ${riskColor} 12%, transparent)` }}
                        >
                          {t.risk_level}
                        </span>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        ) : (
          <QuantumEmptyState title="No margin data" description="No tenant margin risk data available." icon="activity" />
        )}
      </div>

      {/* Quick Nav to all 12 Domains */}
      <div>
        <SectionHeader number="—" title="Domain Control Grid" sub="Navigate all 12 command domains" />
        <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-6 gap-2">
          {[
            { href: '/founder', label: 'Executive', color: '#FF4D00', mod: '1' },
            { href: '/founder/revenue/billing-intelligence', label: 'Revenue & Billing', color: 'var(--color-system-billing)', mod: '2' },
            { href: '/billing-command', label: 'Billing Command', color: 'var(--color-system-billing)', mod: '2B' },
            { href: '/founder/patient-billing', label: 'Patient Billing', color: 'var(--color-status-info)', mod: '2C' },
            { href: '/founder/ai/policies', label: 'AI Governance', color: 'var(--color-system-compliance)', mod: '3' },
            { href: '/founder/comms/inbox', label: 'Communications', color: 'var(--q-green)', mod: '4' },
            { href: '/founder/comms/phone-system', label: 'AI Voice & Alerts', color: 'var(--q-green)', mod: '4B' },
            { href: '/compliance', label: 'Compliance Command', color: 'var(--color-system-compliance)', mod: '5' },
            { href: '/portal/dea-cms', label: 'DEA/CMS Readiness', color: 'var(--color-status-info)', mod: '5B' },
            { href: '/founder/security/role-builder', label: 'Visibility & Sec.', color: 'var(--q-red)', mod: '6' },
            { href: '/founder/templates/proposals', label: 'Templates', color: 'var(--color-status-info)', mod: '7' },
            { href: '/founder/roi', label: 'ROI & Sales', color: 'var(--q-yellow)', mod: '8' },
            { href: '/founder/pwa/crewlink', label: 'PWA & Mobile', color: 'var(--color-system-fleet)', mod: '9' },
            { href: '/founder/infra/ecs', label: 'Infrastructure', color: 'var(--color-text-muted)', mod: '10' },
            { href: '/founder/tools/calendar', label: 'Founder Tools', color: '#FF4D00', mod: '11' },
            { href: '/founder/tools/invoice-creator', label: 'Invoice Creator', color: '#FF4D00', mod: '11A' },
            { href: '/founder/tools/expense-ledger', label: 'Expense Ledger', color: 'var(--q-yellow)', mod: '11B' },
            { href: '/founder/success-command', label: 'Customer Success', color: 'var(--q-green)', mod: '12' },
            { href: '/founder/ops/command', label: 'Ops Intelligence', color: 'var(--color-brand-red)', mod: '6B' },
          ].map((d) => (
            <Link
              key={d.href}
              href={d.href}
              className="flex flex-col gap-1 p-3 bg-[#0A0A0B] border border-border-subtle hover:border-border-strong transition-colors group"
              style={{ clipPath: 'polygon(0 0, calc(100% - 8px) 0, 100% 8px, 100% 100%, 0 100%)' }}
            >
              <span className="text-[9px] font-bold font-mono" style={{ color: d.color }}>DOMAIN {d.mod}</span>
              <span className="text-xs font-semibold text-zinc-100 group-hover:text-zinc-100 transition-colors">{d.label}</span>
            </Link>
          ))}
        </div>
      </div>
    </div>
  );
}
