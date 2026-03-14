'use client';

import { useEffect, useState, useCallback } from 'react';
import { motion } from 'framer-motion';
import Link from 'next/link';
import { getRelationshipCommandSummaryPortal } from '@/services/api';

/* ── Types ───────────────────────────────────────────────────────────── */

interface IdentityConfidence {
  total_patients: number;
  verified_count: number;
  incomplete_count: number;
  duplicate_candidate_count: number;
  merge_pending_count: number;
  confidence_pct: number;
}

interface ResponsiblePartyCompletion {
  total_patients: number;
  with_responsible_party: number;
  unknown_responsibility: number;
  disputed_count: number;
  completion_pct: number;
}

interface FacilityHealth {
  total_facilities: number;
  active_count: number;
  high_friction_count: number;
  review_required_count: number;
  inactive_count: number;
  health_pct: number;
}

interface CommunicationCompleteness {
  total_patients: number;
  with_preferences: number;
  completeness_pct: number;
}

interface RelationshipAction {
  priority: number;
  category: string;
  title: string;
  description: string;
  severity: string;
  action_url?: string;
}

interface CommandSummary {
  identity_confidence: IdentityConfidence;
  responsible_party_completion: ResponsiblePartyCompletion;
  facility_health: FacilityHealth;
  communication_completeness: CommunicationCompleteness;
  duplicate_review_count: number;
  facility_contact_gaps: number;
  frequent_utilizer_count: number;
  top_actions: RelationshipAction[];
}

/* ── Helpers ──────────────────────────────────────────────────────────── */

function severityColor(sev: string): string {
  switch (sev) {
    case 'BLOCKING': return 'var(--color-signal-red, #ef4444)';
    case 'HIGH': return 'var(--color-signal-amber, #f59e0b)';
    case 'MEDIUM': return 'var(--color-signal-yellow, #eab308)';
    case 'GREEN': return 'var(--color-signal-green, #22c55e)';
    default: return 'var(--color-text-muted, var(--color-text-muted))';
  }
}

function pctColor(value: number): string {
  if (value >= 90) return 'var(--color-signal-green, #22c55e)';
  if (value >= 70) return 'var(--color-signal-yellow, #eab308)';
  if (value >= 50) return 'var(--color-signal-amber, #f59e0b)';
  return 'var(--color-signal-red, #ef4444)';
}

function asFiniteNumberOrNull(value: unknown): number | null {
  return typeof value === 'number' && Number.isFinite(value) ? value : null;
}

function fmtPct(value: number | null): string {
  return value == null ? '—' : `${value}%`;
}

function fmtCount(value: number | null): string {
  return value == null ? '—' : String(value);
}

function pctColorOrNeutral(value: number | null): string {
  return value == null ? 'var(--color-text-muted, var(--color-text-muted))' : pctColor(value);
}

/* ── Components ───────────────────────────────────────────────────────── */

function KPICard({
  label, value, sub, color,
}: {
  label: string; value: string; sub?: string; color: string;
}) {
  return (
    <motion.div
      initial={{ opacity: 0, y: 6 }}
      animate={{ opacity: 1, y: 0 }}
      className="chamfer-8"
      style={{
        background: 'var(--color-bg-panel, #18181b)',
        border: '1px solid var(--color-border-default, #27272a)',
        padding: '1rem',
      }}
    >
      <div style={{ fontSize: 11, color: 'var(--color-text-muted, #a1a1aa)', textTransform: 'uppercase', letterSpacing: '0.05em' }}>
        {label}
      </div>
      <div style={{ fontSize: 28, fontWeight: 700, color, marginTop: 4 }}>
        {value}
      </div>
      {sub && (
        <div style={{ fontSize: 11, color: 'var(--color-text-muted, #71717a)', marginTop: 2 }}>
          {sub}
        </div>
      )}
    </motion.div>
  );
}

function ProgressBar({ pct, color }: { pct: number | null; color: string }) {
  return (
    <div style={{ height: 6, borderRadius: 3, background: 'var(--color-bg-subtle, #27272a)', overflow: 'hidden' }}>
      <motion.div
        style={{ height: '100%', borderRadius: 3, background: color }}
        initial={{ width: 0 }}
        animate={{ width: `${Math.min(pct ?? 0, 100)}%` }}
        transition={{ duration: 0.8, ease: 'easeOut' }}
      />
    </div>
  );
}

function ActionCard({ action }: { action: RelationshipAction }) {
  const inner = (
    <motion.div
      initial={{ opacity: 0, x: -4 }}
      animate={{ opacity: 1, x: 0 }}
      className="chamfer-8"
      style={{
        background: 'var(--color-bg-panel, #18181b)',
        border: '1px solid var(--color-border-default, #27272a)',
        padding: '0.75rem 1rem',
        display: 'flex',
        alignItems: 'flex-start',
        gap: '0.75rem',
      }}
    >
      <div style={{
        width: 8, height: 8, borderRadius: 4, marginTop: 6, flexShrink: 0,
        background: severityColor(action.severity),
      }} />
      <div>
        <div style={{ fontSize: 13, fontWeight: 600, color: 'var(--color-text-primary, #fafafa)' }}>
          {action.title}
        </div>
        <div style={{ fontSize: 11, color: 'var(--color-text-muted, #a1a1aa)', marginTop: 2 }}>
          {action.description}
        </div>
        <span
          style={{
            display: 'inline-block',
            marginTop: 4,
            fontSize: 9,
            fontWeight: 700,
            textTransform: 'uppercase',
            letterSpacing: '0.05em',
            padding: '2px 6px',
            borderRadius: 3,
            background: severityColor(action.severity) + '22',
            color: severityColor(action.severity),
          }}
        >
          {action.severity}
        </span>
      </div>
    </motion.div>
  );

  if (action.action_url) {
    return <Link href={action.action_url}>{inner}</Link>;
  }
  return inner;
}

/* ── Page ─────────────────────────────────────────────────────────────── */

export default function FounderRelationshipsPage() {
  const [data, setData] = useState<CommandSummary | null>(null);
  const [loading, setLoading] = useState(true);

  const fetchData = useCallback(async () => {
    try {
      const summary = await getRelationshipCommandSummaryPortal();
      setData(summary as unknown as CommandSummary);
    } catch (_e) {
      /* silent — retain last good data */
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchData();
    const iv = setInterval(fetchData, 30_000);
    return () => clearInterval(iv);
  }, [fetchData]);

  if (loading && !data) {
    return (
      <div style={{ minHeight: '100vh', padding: '2rem', color: 'var(--color-text-muted)' }}>
        Loading relationship intelligence…
      </div>
    );
  }

  const ic = data?.identity_confidence;
  const rp = data?.responsible_party_completion;
  const fh = data?.facility_health;
  const cc = data?.communication_completeness;

  const icConfidencePct = asFiniteNumberOrNull(ic?.confidence_pct);
  const rpCompletionPct = asFiniteNumberOrNull(rp?.completion_pct);
  const fhHealthPct = asFiniteNumberOrNull(fh?.health_pct);
  const ccCompletenessPct = asFiniteNumberOrNull(cc?.completeness_pct);

  const icVerifiedCount = asFiniteNumberOrNull(ic?.verified_count);
  const icTotalPatients = asFiniteNumberOrNull(ic?.total_patients);
  const rpDisputedCount = asFiniteNumberOrNull(rp?.disputed_count);
  const fhHighFrictionCount = asFiniteNumberOrNull(fh?.high_friction_count);
  const ccWithPrefs = asFiniteNumberOrNull(cc?.with_preferences);
  const ccTotalPatients = asFiniteNumberOrNull(cc?.total_patients);

  return (
    <div style={{ minHeight: '100vh', padding: '2rem 2rem 4rem', maxWidth: 1200, margin: '0 auto' }}>
      {/* ── HEADER ──────────────────────────────────────────────────── */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1.5rem' }}>
        <div>
          <h1 style={{ fontSize: 22, fontWeight: 700, color: 'var(--color-text-primary, #fafafa)' }}>
            Relationship Command Center
          </h1>
          <p style={{ fontSize: 12, color: 'var(--color-text-muted, #a1a1aa)', marginTop: 2 }}>
            Patient identity, responsible parties, facilities, and communication intelligence
          </p>
        </div>
        <div style={{ display: 'flex', gap: 8 }}>
          <Link href="/portal/facilities"
            className="chamfer-4"
            style={{
              fontSize: 11, fontWeight: 600, padding: '6px 12px',
              background: 'var(--color-bg-panel)', border: '1px solid var(--color-border-default)',
              color: 'var(--color-text-primary)',
            }}
          >
            Facilities
          </Link>
          <Link href="/portal/patient/identity"
            className="chamfer-4"
            style={{
              fontSize: 11, fontWeight: 600, padding: '6px 12px',
              background: 'var(--color-brand-orange, #f97316)', color: '#000',
            }}
          >
            Identity Manager
          </Link>
        </div>
      </div>

      {/* ── KPI GRID ────────────────────────────────────────────────── */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', gap: 12, marginBottom: 24 }}>
        <KPICard
          label="Identity Confidence"
          value={fmtPct(icConfidencePct)}
          sub={`${fmtCount(icVerifiedCount)} / ${fmtCount(icTotalPatients)} verified`}
          color={pctColorOrNeutral(icConfidencePct)}
        />
        <KPICard
          label="Responsible Party"
          value={fmtPct(rpCompletionPct)}
          sub={rpDisputedCount == null ? '—' : `${rpDisputedCount} disputed`}
          color={pctColorOrNeutral(rpCompletionPct)}
        />
        <KPICard
          label="Facility Health"
          value={fmtPct(fhHealthPct)}
          sub={fhHighFrictionCount == null ? '—' : `${fhHighFrictionCount} high friction`}
          color={pctColorOrNeutral(fhHealthPct)}
        />
        <KPICard
          label="Comm Preferences"
          value={fmtPct(ccCompletenessPct)}
          sub={`${fmtCount(ccWithPrefs)} / ${fmtCount(ccTotalPatients)}`}
          color={pctColorOrNeutral(ccCompletenessPct)}
        />
      </div>

      {/* ── PROGRESS BARS ───────────────────────────────────────────── */}
      <div
        className="chamfer-8"
        style={{
          background: 'var(--color-bg-panel, #18181b)',
          border: '1px solid var(--color-border-default, #27272a)',
          padding: '1rem',
          marginBottom: 24,
        }}
      >
        <div style={{ fontSize: 11, fontWeight: 600, textTransform: 'uppercase', color: 'var(--color-text-muted)', marginBottom: 12 }}>
          Domain Health
        </div>
        <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
          <div>
            <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: 11, marginBottom: 4 }}>
              <span>Identity Confidence</span><span>{fmtPct(icConfidencePct)}</span>
            </div>
            <ProgressBar pct={icConfidencePct} color={pctColorOrNeutral(icConfidencePct)} />
          </div>
          <div>
            <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: 11, marginBottom: 4 }}>
              <span>Responsible Party</span><span>{fmtPct(rpCompletionPct)}</span>
            </div>
            <ProgressBar pct={rpCompletionPct} color={pctColorOrNeutral(rpCompletionPct)} />
          </div>
          <div>
            <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: 11, marginBottom: 4 }}>
              <span>Facility Health</span><span>{fmtPct(fhHealthPct)}</span>
            </div>
            <ProgressBar pct={fhHealthPct} color={pctColorOrNeutral(fhHealthPct)} />
          </div>
          <div>
            <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: 11, marginBottom: 4 }}>
              <span>Communication Prefs</span><span>{fmtPct(ccCompletenessPct)}</span>
            </div>
            <ProgressBar pct={ccCompletenessPct} color={pctColorOrNeutral(ccCompletenessPct)} />
          </div>
        </div>
      </div>

      {/* ── SIGNAL METRICS ──────────────────────────────────────────── */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(150px, 1fr))', gap: 12, marginBottom: 24 }}>
        <KPICard label="Duplicate Queue" value={data?.duplicate_review_count != null ? String(data.duplicate_review_count) : '—'} color="var(--color-signal-amber, #f59e0b)" />
        <KPICard label="Facility Contact Gaps" value={data?.facility_contact_gaps != null ? String(data.facility_contact_gaps) : '—'} color="var(--color-signal-yellow, #eab308)" />
        <KPICard label="Frequent Utilizers" value={data?.frequent_utilizer_count != null ? String(data.frequent_utilizer_count) : '—'} color="var(--color-signal-red, #ef4444)" />
      </div>

      {/* ── TOP ACTIONS ─────────────────────────────────────────────── */}
      <div style={{ marginBottom: 24 }}>
        <div style={{ fontSize: 14, fontWeight: 700, color: 'var(--color-text-primary)', marginBottom: 8 }}>
          Priority Actions
        </div>
        <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
          {data?.top_actions?.map((a, i) => (
            <ActionCard key={i} action={a} />
          ))}
        </div>
      </div>

      {/* ── QUICK NAV ───────────────────────────────────────────────── */}
      <div
        className="chamfer-8"
        style={{
          background: 'var(--color-bg-panel, #18181b)',
          border: '1px solid var(--color-border-default, #27272a)',
          padding: '1rem',
        }}
      >
        <div style={{ fontSize: 11, fontWeight: 600, textTransform: 'uppercase', color: 'var(--color-text-muted)', marginBottom: 12 }}>
          Relationship Domains
        </div>
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(180px, 1fr))', gap: 8 }}>
          {[
            { label: 'Patient Identity', href: '/portal/patient/identity' },
            { label: 'Responsible Parties', href: '/portal/patient/relationships' },
            { label: 'Facility Network', href: '/portal/facilities' },
          ].map((link) => (
            <Link
              key={link.href}
              href={link.href}
              className="chamfer-4"
              style={{
                display: 'block',
                padding: '10px 14px',
                fontSize: 12,
                fontWeight: 600,
                color: 'var(--color-text-primary)',
                background: 'var(--color-bg-subtle, #27272a)',
                textAlign: 'center',
              }}
            >
              {link.label}
            </Link>
          ))}
        </div>
      </div>
    </div>
  );
}
