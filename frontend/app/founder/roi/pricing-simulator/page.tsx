'use client';
import Link from 'next/link';
import { useCallback, useEffect, useMemo, useState, type ReactNode } from 'react';
import { QuantumEmptyState } from '@/components/ui';
import { NextBestActionCard, type NextAction } from '@/components/ui/NextBestActionCard';
import { SeverityBadge } from '@/components/ui/SeverityBadge';
import { DomainNavCard, FounderStatusBar } from '@/components/shells/FounderCommand';
import type { SeverityLevel } from '@/lib/design-system/tokens';
import {
  createROIFunnelPricingSimulation,
  type ROIFunnelPricingSimulationResponse,
} from '@/services/api';

type FetchStatus = 'idle' | 'loading' | 'ready' | 'error';

function SectionHeader({ number, title, sub }: { number: string; title: string; sub?: string }) {
  return (
    <div className="border-b border-border-subtle pb-2 mb-4">
      <div className="flex items-baseline gap-3">
        <span className="text-micro font-bold text-[var(--q-orange)]/70 font-mono">MODULE {number}</span>
        <h2 className="text-sm font-bold uppercase tracking-widest text-[var(--color-text-primary)]">{title}</h2>
        {sub && <span className="text-xs text-[var(--color-text-muted)]">{sub}</span>}
      </div>
    </div>
  );
}

function Badge({ label, status }: { label: string; status: 'ok' | 'warn' | 'error' | 'info' }) {
  const c = { ok: 'var(--color-status-active)', warn: 'var(--color-status-warning)', error: 'var(--color-brand-red)', info: 'var(--color-status-info)' };
  return (
    <span
      className="inline-flex items-center gap-1.5 px-2 py-0.5 chamfer-4 text-micro font-semibold uppercase tracking-wider border"
      style={{ borderColor: `${c[status]}40`, color: c[status], background: `${c[status]}12` }}
    >
      <span className="w-1 h-1 " style={{ background: c[status] }} />
      {label}
    </span>
  );
}

function Panel({ children, className }: { children: ReactNode; className?: string }) {
  return (
    <div
      className={`bg-[var(--color-bg-panel)] border border-border-DEFAULT p-4 ${className ?? ''}`}
      style={{ clipPath: 'polygon(0 0,calc(100% - 10px) 0,100% 10px,100% 100%,0 100%)' }}
    >
      {children}
    </div>
  );
}

function StatCard({ label, value, sub, color }: { label: string; value: string | number; sub?: string; color?: string }) {
  return (
    <div
      className="bg-[var(--color-bg-panel)] border border-border-DEFAULT p-4"
      style={{ clipPath: 'polygon(0 0,calc(100% - 10px) 0,100% 10px,100% 100%,0 100%)' }}
    >
      <div className="text-micro font-semibold uppercase tracking-widest text-[var(--color-text-muted)] mb-1">{label}</div>
      <div className="text-xl font-bold" style={{ color: color ?? 'var(--color-text-primary)' }}>{value}</div>
      {sub && <div className="text-body text-[var(--color-text-muted)] mt-0.5">{sub}</div>}
    </div>
  );
}

const SCENARIOS = [
  { label: 'Small', calls: 100, highlight: false },
  { label: 'Medium', calls: 200, highlight: true },
  { label: 'Large', calls: 400, highlight: false },
  { label: 'Enterprise', calls: 800, highlight: false },
];

function computeModel(
  calls: number,
  medicare: number,
  medicaid: number,
  commercial: number,
  selfPayRate: number,
  medicareP: number,
  medicaidP: number,
  commercialP: number,
  selfPayP: number,
  billingPct: number,
  collectionRate: number,
) {
  const blended =
    (medicare * medicareP + medicaid * medicaidP + commercial * commercialP + selfPayRate * selfPayP) / 100;
  const gross = blended * calls * (collectionRate / 100);
  const currentFee = gross * (billingPct / 100);
  const currentNet = gross - currentFee;

  const platformBase = 1200;
  const perCall = 6;
  const platformCost = platformBase + calls * perCall;
  const fusionNet = gross - platformCost;
  const saving = fusionNet - currentNet;

  const platformPctOfRevenue = gross > 0 ? (platformCost / gross) * 100 : 0;

  return {
    blended,
    gross,
    currentFee,
    currentNet,
    platformCost,
    fusionNet,
    saving,
    platformPctOfRevenue,
  };
}

export default function PricingSimulatorPage() {
  const [calls, setCalls] = useState(200);
  const [medicare, setMedicare] = useState(650);
  const [medicaid, setMedicaid] = useState(280);
  const [commercial, setCommercial] = useState(820);
  const [selfPayRate] = useState(120);
  const [medicareP, setMedicareP] = useState(40);
  const [medicaidP, setMedicaidP] = useState(30);
  const [commercialP, setCommercialP] = useState(20);
  const [selfPayP, setSelfPayP] = useState(10);
  const [billingPct, setBillingPct] = useState(8);
  const [collectionRate, setCollectionRate] = useState(72);
  const [proposalEmail, setProposalEmail] = useState('');
  const [pricingStatus, setPricingStatus] = useState<FetchStatus>('idle');
  const [pricingError, setPricingError] = useState<string | null>(null);
  const [pricingSimulation, setPricingSimulation] = useState<ROIFunnelPricingSimulationResponse | null>(null);

  const fetchPricingSimulation = useCallback((): void => {
    setPricingStatus('loading');
    setPricingError(null);

    void createROIFunnelPricingSimulation({
        base_plan: 'professional',
        modules: ['billing', 'analytics', 'compliance'],
        call_volume: calls,
        contract_length_months: 12,
    })
      .then((payload) => {
        setPricingSimulation(payload);
        setPricingStatus('ready');
      })
      .catch((fetchError: unknown) => {
        const message = fetchError instanceof Error ? fetchError.message : 'Unknown pricing simulation failure';
        setPricingError(message);
        setPricingStatus('error');
      });
  }, [calls]);

  useEffect(() => {
    fetchPricingSimulation();
  }, [fetchPricingSimulation]);

  const model = computeModel(
    calls, medicare, medicaid, commercial, selfPayRate,
    medicareP, medicaidP, commercialP, selfPayP,
    billingPct, collectionRate,
  );

  const platformBase = 1200;
  const perCall = 6;
  const platformCost = platformBase + calls * perCall;
  const pricingMonthlyCents = typeof pricingSimulation?.monthly_cents === 'number' && Number.isFinite(pricingSimulation.monthly_cents)
    ? pricingSimulation.monthly_cents
    : null;
  const pricingAnnualCents = typeof pricingSimulation?.annual_cents === 'number' && Number.isFinite(pricingSimulation.annual_cents)
    ? pricingSimulation.annual_cents
    : null;
  const pricingAnnualSavingsPct = typeof pricingSimulation?.annual_savings_pct === 'number' && Number.isFinite(pricingSimulation.annual_savings_pct)
    ? pricingSimulation.annual_savings_pct
    : null;

  const fmt = (n: number) =>
    n < 0
      ? `-$${Math.abs(n).toLocaleString('en-US', { maximumFractionDigits: 0 })}`
      : `$${n.toLocaleString('en-US', { maximumFractionDigits: 0 })}`;

  const pricingSeverity: SeverityLevel = pricingStatus === 'error'
    ? 'BLOCKING'
    : model.saving < 0
      ? 'HIGH'
      : model.saving < 1000
        ? 'MEDIUM'
        : 'LOW';

  const pricingActions = useMemo<NextAction[]>(() => {
    const actions: NextAction[] = [
      {
        id: 'roi-pricing-validate-assumptions',
        title: 'Validate payer-mix assumptions against conversion and reimbursement telemetry.',
        severity: 'MEDIUM',
        domain: 'ROI Analytics',
        href: '/founder/roi/analytics',
      },
    ];

    if (pricingStatus === 'error') {
      actions.unshift({
        id: 'roi-pricing-telemetry-recover',
        title: 'Recover pricing simulation telemetry before publishing proposal pricing.',
        severity: 'BLOCKING',
        domain: 'Pricing Telemetry',
        href: '/founder/roi/pricing-simulator',
      });
    }

    if (model.saving < 0) {
      actions.unshift({
        id: 'roi-pricing-negative-margin',
        title: 'Current assumptions produce negative monthly savings; recalibrate pricing model.',
        severity: 'HIGH',
        domain: 'Margin Posture',
        href: '/founder/roi/proposals',
      });
    }

    return actions;
  }, [model.saving, pricingStatus]);

  function scenarioModel(c: number) {
    return computeModel(c, medicare, medicaid, commercial, selfPayRate, medicareP, medicaidP, commercialP, selfPayP, billingPct, collectionRate);
  }

  return (
    <div className="min-h-screen bg-[var(--color-bg-base)] text-[var(--color-text-primary)] p-6 space-y-6">
      <FounderStatusBar isLive={pricingStatus !== 'error'} activeIncidents={pricingStatus === 'error' ? 1 : 0} />

      {/* Page Header */}
      <div className="border-b border-border-subtle pb-4">
        <div className="flex items-center justify-between">
          <div>
            <p className="text-micro font-bold tracking-widest font-mono mb-1" style={{ color: 'rgba(255,152,0,0.6)' }}>
              MODULE 8 · ROI &amp; SALES
            </p>
            <h1 className="text-2xl font-bold tracking-tight" style={{ color: 'var(--q-yellow)' }}>Pricing Simulator</h1>
            <p className="text-xs text-[var(--color-text-muted)] mt-1">Model different pricing scenarios · compare vs competitor billing models</p>
            <div className="mt-2">
              <SeverityBadge severity={pricingSeverity} size="sm" />
            </div>
          </div>
          <div className="flex items-center gap-3">
            <button
              onClick={fetchPricingSimulation}
              className="h-8 px-3 text-xs font-semibold border border-status-warning/35 text-status-warning hover:bg-status-warning/10 transition-colors"
            >
              Refresh Pricing Telemetry
            </button>
            <Link href="/founder/roi" className="text-body text-[var(--color-text-muted)] hover:text-status-warning transition-colors font-mono">
              ← Back to ROI Command
            </Link>
          </div>
        </div>
      </div>

      <NextBestActionCard actions={pricingActions} title="Pricing Command Next Best Actions" maxVisible={4} />

      <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
        <DomainNavCard
          domain="billing"
          href="/founder/revenue/billing-intelligence"
          description="Cross-check modeled pricing against live collections and denial rates."
        />
        <DomainNavCard
          domain="ops"
          href="/founder/ops/command"
          description="Ensure pricing assumptions match operational capacity and response readiness."
        />
        <DomainNavCard
          domain="support"
          href="/founder/roi/proposals"
          description="Push validated pricing into proposal execution and follow-up workflows."
        />
      </div>

      {/* MODULE 1 — Agency Input Parameters */}
      <Panel>
        <SectionHeader number="1" title="Agency Input Parameters" sub="Adjust to model any agency" />
        <div className="grid grid-cols-2 gap-6">
          <div className="space-y-4">
            <div>
              <label className="text-micro text-[var(--color-text-muted)] block mb-1">Monthly Call Volume: <span className="text-status-warning font-bold">{calls}</span></label>
              <input
                type="range" min={50} max={1000} step={10} value={calls}
                onChange={(e) => setCalls(Number(e.target.value))}
                className="w-full accent-[var(--color-status-warning)]"
              />
              <div className="flex justify-between text-[9px] text-[var(--color-text-muted)] mt-0.5">
                <span>50</span><span>1,000</span>
              </div>
            </div>
            <div className="grid grid-cols-2 gap-3">
              {[
                { label: 'Avg Medicare Rate ($)', val: medicare, set: setMedicare },
                { label: 'Avg Medicaid Rate ($)', val: medicaid, set: setMedicaid },
                { label: 'Avg Commercial Rate ($)', val: commercial, set: setCommercial },
                { label: 'Billing % Fee', val: billingPct, set: setBillingPct },
              ].map(({ label, val, set }) => (
                <div key={label}>
                  <label className="text-micro text-[var(--color-text-muted)] block mb-1">{label}</label>
                  <input
                    type="number" value={val}
                    onChange={(e) => set(Number(e.target.value))}
                    className="w-full bg-bg-input border border-border-DEFAULT text-body text-[var(--color-text-primary)] px-3 py-2 chamfer-4 outline-none focus:border-status-warning"
                  />
                </div>
              ))}
            </div>
            <div>
              <label className="text-micro text-[var(--color-text-muted)] block mb-1">Current Collection Rate (%): <span className="text-status-warning font-bold">{collectionRate}%</span></label>
              <input
                type="range" min={40} max={100} step={1} value={collectionRate}
                onChange={(e) => setCollectionRate(Number(e.target.value))}
                className="w-full accent-[var(--color-status-warning)]"
              />
            </div>
          </div>
          <div>
            <p className="text-micro font-semibold uppercase tracking-widest text-[var(--color-text-muted)] mb-3">Payer Mix (%)</p>
            <div className="space-y-3">
              {[
                { label: 'Medicare %', val: medicareP, set: setMedicareP, color: 'var(--color-status-info)' },
                { label: 'Medicaid %', val: medicaidP, set: setMedicaidP, color: 'var(--color-system-compliance)' },
                { label: 'Commercial %', val: commercialP, set: setCommercialP, color: 'var(--q-green)' },
                { label: 'Self-Pay %', val: selfPayP, set: setSelfPayP, color: 'var(--q-yellow)' },
              ].map(({ label, val, set, color }) => (
                <div key={label}>
                  <div className="flex justify-between mb-1">
                    <span className="text-micro text-[var(--color-text-muted)]">{label}</span>
                    <span className="text-micro font-bold" style={{ color }}>{val}%</span>
                  </div>
                  <input
                    type="range" min={0} max={100} step={5} value={val}
                    onChange={(e) => set(Number(e.target.value))}
                    className="w-full"
                    style={{ accentColor: color }}
                  />
                </div>
              ))}
              <div className="flex justify-between text-micro pt-1 border-t border-border-subtle">
                <span className="text-[var(--color-text-muted)]">Total</span>
                <span className={`font-bold ${medicareP + medicaidP + commercialP + selfPayP === 100 ? 'text-[var(--color-status-active)]' : 'text-red'}`}>
                  {medicareP + medicaidP + commercialP + selfPayP}%
                </span>
              </div>
            </div>
          </div>
        </div>
      </Panel>

      {/* MODULE 2 — FusionEMS Quantum Pricing */}
      <Panel>
        <SectionHeader number="2" title="FusionEMS Quantum Pricing" sub="Calculated from inputs" />
        <div className="grid grid-cols-4 gap-3">
          <StatCard label="Base Platform" value="$1,200/mo" color="var(--color-status-warning)" />
          <StatCard label="Per-Transport" value="$6/call" color="var(--color-status-warning)" />
          <StatCard label={`Total Platform Cost (${calls} calls)`} value={fmt(platformCost) + '/mo'} color="var(--color-text-primary)" />
          <StatCard
            label="Platform as % of Revenue"
            value={model.gross > 0 ? `${model.platformPctOfRevenue.toFixed(1)}%` : '—'}
            color={model.platformPctOfRevenue < 8 ? 'var(--color-status-active)' : 'var(--color-brand-red)'}
            sub={model.platformPctOfRevenue < 8 ? 'Better than 8% billing' : 'Higher than 8% billing'}
          />
        </div>
        <div className="mt-3 text-body text-[var(--color-text-muted)] font-mono">
          $1,200 + ({calls} × $6) = {fmt(platformCost)}/mo
        </div>
        <div className="mt-3">
          {pricingStatus === 'loading' || pricingStatus === 'idle' ? (
            <div className="text-xs text-[var(--color-text-muted)]">Loading live pricing simulation telemetry...</div>
          ) : pricingStatus === 'error' ? (
            <QuantumEmptyState
              title="Pricing telemetry unavailable"
              description={pricingError ?? 'Unable to load pricing simulation telemetry.'}
              icon="activity"
            />
          ) : (
            <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
              <StatCard
                label="Live Monthly Cost"
                value={pricingMonthlyCents != null ? `$${(pricingMonthlyCents / 100).toLocaleString()}` : '—'}
                color="var(--color-status-warning)"
                sub="ROI pricing simulation API"
              />
              <StatCard
                label="Live Annual Cost"
                value={pricingAnnualCents != null ? `$${(pricingAnnualCents / 100).toLocaleString()}` : '—'}
                color="var(--color-status-info)"
                sub={`Annual discount: ${pricingAnnualSavingsPct != null ? `${pricingAnnualSavingsPct}%` : '—'}`}
              />
              <StatCard
                label="Cost / Transport"
                value={pricingSimulation?.cost_per_transport != null ? `$${pricingSimulation.cost_per_transport.toFixed(2)}` : '—'}
                color="var(--color-status-active)"
                sub="Command telemetry"
              />
            </div>
          )}
        </div>
      </Panel>

      {/* MODULE 3 — Revenue Comparison */}
      <Panel>
        <SectionHeader number="3" title="Revenue Comparison" sub="Current vs FusionEMS Quantum" />
        <div className="grid grid-cols-2 gap-4">
          <div className="p-4 bg-bg-input border border-[var(--color-brand-red)]/20 chamfer-4">
            <p className="text-micro font-bold uppercase tracking-widest text-[var(--color-brand-red)]/70 mb-3">Current Model ({billingPct}% billing)</p>
            <div className="space-y-2">
              {[
                { label: 'Gross Revenue', val: fmt(model.gross), color: 'rgba(255,255,255,0.7)' },
                { label: `Billing Co. Fee (${billingPct}%)`, val: `-${fmt(model.currentFee)}`, color: 'var(--q-red)' },
                { label: 'Net to Agency', val: fmt(model.currentNet), color: 'var(--color-text-primary)' },
              ].map(({ label, val, color }) => (
                <div key={label} className="flex justify-between py-1.5 border-b border-border-subtle last:border-b-2 last:border-white/[0.12]">
                  <span className="text-body text-[var(--color-text-muted)]">{label}</span>
                  <span className="text-body font-bold font-mono" style={{ color }}>{val}</span>
                </div>
              ))}
            </div>
          </div>
          <div className="p-4 bg-bg-input border border-[var(--color-status-active)]/[0.2] chamfer-4">
            <p className="text-micro font-bold uppercase tracking-widest text-[var(--color-status-active)]/[0.7] mb-3">FusionEMS Quantum</p>
            <div className="space-y-2">
              {[
                { label: 'Gross Revenue', val: fmt(model.gross), color: 'rgba(255,255,255,0.7)' },
                { label: `Platform Cost`, val: `-${fmt(platformCost)}`, color: 'var(--q-yellow)' },
                { label: 'Net to Agency', val: fmt(model.fusionNet), color: 'var(--q-green)' },
              ].map(({ label, val, color }) => (
                <div key={label} className="flex justify-between py-1.5 border-b border-border-subtle last:border-b-2 last:border-[var(--color-status-active)]/[0.2]">
                  <span className="text-body text-[var(--color-text-muted)]">{label}</span>
                  <span className="text-body font-bold font-mono" style={{ color }}>{val}</span>
                </div>
              ))}
            </div>
            <div className="mt-3 pt-2 border-t border-[var(--color-status-active)]/[0.2]">
              <div className="flex justify-between items-center">
                <span className="text-body font-semibold text-[var(--color-text-secondary)]">Monthly Saving</span>
                <span className="text-[15px] font-bold" style={{ color: model.saving >= 0 ? 'var(--color-status-active)' : 'var(--color-brand-red)' }}>
                  {model.saving >= 0 ? '+' : ''}{fmt(model.saving)}/mo
                </span>
              </div>
            </div>
          </div>
        </div>
      </Panel>

      {/* MODULE 4 — ROI over Time */}
      <Panel>
        <SectionHeader number="4" title="ROI over Time" sub="Cumulative savings" />
        <div className="grid grid-cols-3 gap-3">
          <StatCard
            label="1-Year Savings"
            value={fmt(model.saving * 12)}
            sub="Annual cumulative"
            color="var(--color-status-active)"
          />
          <StatCard
            label="5-Year Savings"
            value={fmt(model.saving * 60)}
            sub="5-year cumulative"
            color="var(--color-status-active)"
          />
          <StatCard
            label="10-Year Savings"
            value={fmt(model.saving * 120)}
            sub="10-year cumulative"
            color="var(--color-status-active)"
          />
        </div>
      </Panel>

      {/* MODULE 5 — Scenario Comparison */}
      <Panel>
        <SectionHeader number="5" title="Scenario Comparison" sub="Pre-built agency sizes" />
        <div className="overflow-x-auto">
          <table className="w-full text-body">
            <thead>
              <tr className="border-b border-border-subtle">
                {['Size', 'Calls/mo', 'Platform Cost', 'Gross Rev', 'Net (Current)', 'Net (Fusion)', 'Monthly Saving'].map((h) => (
                  <th key={h} className="text-left py-2 pr-4 text-[var(--color-text-muted)] font-semibold uppercase tracking-wider text-micro">{h}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {SCENARIOS.map((s) => {
                const m = scenarioModel(s.calls);
                const pc = platformBase + s.calls * perCall;
                return (
                  <tr
                    key={s.label}
                    className="border-b border-border-subtle hover:bg-[var(--color-bg-base)]/[0.02]"
                    style={{ background: s.highlight ? 'rgba(255,152,0,0.04)' : undefined }}
                  >
                    <td className="py-2 pr-4">
                      <div className="flex items-center gap-2">
                        <span className="font-semibold text-[var(--color-text-primary)]">{s.label}</span>
                        {s.highlight && <Badge label="Most Common" status="warn" />}
                      </div>
                    </td>
                    <td className="py-2 pr-4 text-[var(--color-text-secondary)]">{s.calls}</td>
                    <td className="py-2 pr-4 font-mono text-status-warning">{fmt(pc)}/mo</td>
                    <td className="py-2 pr-4 font-mono text-[var(--color-text-secondary)]">{fmt(m.gross)}/mo</td>
                    <td className="py-2 pr-4 font-mono text-[var(--color-text-secondary)]">{fmt(m.currentNet)}/mo</td>
                    <td className="py-2 pr-4 font-mono text-[var(--color-text-primary)]">{fmt(m.fusionNet)}/mo</td>
                    <td className="py-2 pr-4 font-mono font-bold" style={{ color: m.saving >= 0 ? 'var(--color-status-active)' : 'var(--color-brand-red)' }}>
                      {m.saving >= 0 ? '+' : ''}{fmt(m.saving)}/mo
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      </Panel>

      {/* MODULE 6 — Export Proposal */}
      <Panel>
        <SectionHeader number="6" title="Export Proposal" sub="Generate and send ROI proposal" />
        <div className="flex items-end gap-3">
          <div className="flex-1">
            <label className="text-micro text-[var(--color-text-muted)] block mb-1">Agency Email Address</label>
            <input
              type="email"
              value={proposalEmail}
              onChange={(e) => setProposalEmail(e.target.value)}
              placeholder="agency@example.com"
              className="w-full bg-bg-input border border-border-DEFAULT text-body text-[var(--color-text-primary)] px-3 py-2 chamfer-4 outline-none focus:border-status-warning"
            />
          </div>
          <button
            className="text-body font-bold px-5 py-2 chamfer-4 transition-all hover:opacity-90"
            style={{ background: 'var(--color-status-warning)', color: '#000' }}
          >
            Generate PDF Proposal
          </button>
          <button
            disabled={!proposalEmail}
            className="text-body font-bold px-5 py-2 chamfer-4 transition-all disabled:opacity-30"
            style={{ background: 'color-mix(in srgb, var(--color-status-info) 9%, transparent)', color: 'var(--color-status-info)', border: '1px solid color-mix(in srgb, var(--color-status-info) 19%, transparent)' }}
          >
            Send to Agency
          </button>
        </div>
      </Panel>
    </div>
  );
}
