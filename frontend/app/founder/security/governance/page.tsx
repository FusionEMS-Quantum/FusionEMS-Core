'use client';

import { useEffect, useState } from 'react';
import { motion } from 'framer-motion';
import Link from 'next/link';
import { getGovernanceSummary, getGovernanceInteropReadiness } from '@/services/api';

/* ── color system per directive ── */
const STATUS_COLOR = {
  RED: 'var(--color-brand-red)',
  ORANGE: 'var(--q-orange)',
  YELLOW: 'var(--color-status-warning)',
  BLUE: 'var(--color-status-info)',
  GREEN: 'var(--color-status-active)',
  GRAY: 'rgba(255,255,255,0.35)',
} as const;

function severity(val: string): keyof typeof STATUS_COLOR {
  const v = val.toUpperCase();
  if (v === 'RED' || v === 'BLOCKING') return 'RED';
  if (v === 'ORANGE' || v === 'HIGH') return 'ORANGE';
  if (v === 'YELLOW' || v === 'NEEDS_ATTENTION' || v === 'MEDIUM') return 'YELLOW';
  if (v === 'BLUE' || v === 'IN_REVIEW') return 'BLUE';
  if (v === 'GREEN' || v === 'READY' || v === 'GOOD') return 'GREEN';
  return 'GRAY';
}

/* ── Score Ring ── */
function ScoreRing({ score, label, color }: { score: number | null; label: string; color: string }) {
  const pct = score == null ? null : Math.min(Math.max(score, 0), 100);
  const rad = 36;
  const circ = 2 * Math.PI * rad;
  const offset = pct == null ? circ : circ - (pct / 100) * circ;
  return (
    <div className="flex flex-col items-center">
      <svg width="88" height="88" viewBox="0 0 88 88">
        <circle cx="44" cy="44" r={rad} fill="none" stroke="rgba(255,255,255,0.06)" strokeWidth="6" />
        <motion.circle
          cx="44" cy="44" r={rad} fill="none" stroke={color} strokeWidth="6"
          strokeLinecap="round" strokeDasharray={circ} strokeDashoffset={circ}
          animate={{ strokeDashoffset: offset }}
          transition={{ duration: 1, ease: 'easeOut' }}
          transform="rotate(-90 44 44)"
        />
        <text x="44" y="48" textAnchor="middle" fontSize="18" fontWeight="700" fill="white">{pct == null ? '—' : pct}</text>
      </svg>
      <span className="text-micro uppercase tracking-widest text-[var(--color-text-muted)] mt-1">{label}</span>
    </div>
  );
}

/* ── Badge ── */
function TrustBadge({ label, status, count }: { label: string; status: string; count?: number }) {
  const c = STATUS_COLOR[severity(status)];
  return (
    <div className="flex items-center gap-2 bg-[var(--color-bg-panel)] border border-border-DEFAULT px-3 py-2" style={{ clipPath: 'polygon(0 0, calc(100% - 8px) 0, 100% 8px, 100% 100%, 0 100%)' }}>
      <span className="w-2 h-2  flex-shrink-0" style={{ background: c }} />
      <span className="text-micro font-semibold uppercase tracking-widest text-[var(--color-text-muted)] flex-1">{label}</span>
      {count != null && <span className="text-sm font-bold" style={{ color: c }}>{count}</span>}
    </div>
  );
}

/* ── Timeline Row ── */
function TimelineRow({ time, actor, action, level }: { time: string; actor: string; action: string; level: string }) {
  const c = STATUS_COLOR[severity(level)];
  return (
    <div className="flex items-center gap-3 py-2 border-b border-white/5 last:border-0">
      <span className="w-1.5 h-1.5  flex-shrink-0" style={{ background: c }} />
      <span className="text-micro text-[var(--color-text-muted)] font-mono w-16 flex-shrink-0">{time}</span>
      <span className="text-xs text-[var(--color-text-secondary)] flex-1">{actor} — {action}</span>
    </div>
  );
}

/* ── Next Best Action Card ── */
function NextActionCard({ rank, title, why, action, severity: sev }: { rank: number; title: string; why: string; action: string; severity: string }) {
  const c = STATUS_COLOR[severity(sev)];
  return (
    <motion.div initial={{ opacity: 0, x: -8 }} animate={{ opacity: 1, x: 0 }} transition={{ delay: rank * 0.08 }}
      className="bg-[var(--color-bg-panel)] border border-border-DEFAULT p-4" style={{ clipPath: 'polygon(0 0, calc(100% - 10px) 0, 100% 10px, 100% 100%, 0 100%)' }}>
      <div className="flex items-center gap-2 mb-2">
        <span className="text-micro font-bold text-[var(--q-orange)]/70 font-mono">#{rank}</span>
        <span className="w-1.5 h-1.5 " style={{ background: c }} />
        <span className="text-xs font-bold text-[var(--color-text-primary)]">{title}</span>
      </div>
      <p className="text-body text-[var(--color-text-secondary)] mb-2">{why}</p>
      <p className="text-body font-semibold" style={{ color: c }}>→ {action}</p>
    </motion.div>
  );
}

/* ── Meter Bar ── */
function MeterBar({ label, value, max, color }: { label: string; value: number | null; max: number; color: string }) {
  const pct = value != null && max > 0 ? Math.min((value / max) * 100, 100) : 0;
  return (
    <div className="flex items-center gap-3">
      <span className="text-micro text-[var(--color-text-muted)] w-24 flex-shrink-0">{label}</span>
      <div className="flex-1 h-2 bg-[var(--color-bg-base)]/[0.06]  overflow-hidden">
        <motion.div className="h-full " style={{ background: color }} initial={{ width: 0 }} animate={{ width: `${pct}%` }} transition={{ duration: 0.8, ease: 'easeOut' }} />
      </div>
      <span className="text-xs font-semibold text-[var(--color-text-primary)] w-10 text-right">{value != null ? value : '—'}</span>
    </div>
  );
}

/* ──────────── TYPES ──────────── */
interface ComplianceSummary {
  failed_logins_24h: number;
  phi_access_count_24h: number;
  pending_approvals_count: number;
  recent_exports_7d: number;
  health_score: number;
  status: string;
}

interface AuditTimelineEvent {
  time: string;
  actor: string;
  action: string;
  level: string;
}

interface NextAction {
  rank: number;
  title: string;
  why: string;
  action: string;
  severity: string;
}

/* ──────────── PAGE ──────────── */
export default function GovernanceCommandPage() {
  const [summary, setSummary] = useState<ComplianceSummary | null>(null);
  const [timeline, setTimeline] = useState<AuditTimelineEvent[]>([]);
  const [actions, setActions] = useState<NextAction[]>([]);
  const [interopScore, setInteropScore] = useState(0);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    Promise.all([
      getGovernanceSummary().catch(() => null),
      getGovernanceInteropReadiness().catch(() => null),
    ]).then(([summaryData, interopData]) => {
      if (summaryData) {
        setSummary(summaryData);

        // Derive next actions from summary data
        const derivedActions: NextAction[] = [];
        if (summaryData.failed_logins_24h > 3) {
          derivedActions.push({ rank: 1, title: 'Failed Login Spike', why: `${summaryData.failed_logins_24h} failed logins in the last 24h may indicate credential attack.`, action: 'Review auth logs and consider account lockout.', severity: 'RED' });
        }
        if (summaryData.pending_approvals_count > 0) {
          derivedActions.push({ rank: derivedActions.length + 1, title: 'Pending Approvals', why: `${summaryData.pending_approvals_count} protected actions awaiting your review.`, action: 'Review and approve or deny pending actions.', severity: 'ORANGE' });
        }
        if (summaryData.recent_exports_7d > 10) {
          derivedActions.push({ rank: derivedActions.length + 1, title: 'High Export Activity', why: `${summaryData.recent_exports_7d} exports in the last 7 days — verify legitimate use.`, action: 'Audit recent export requests for compliance.', severity: 'YELLOW' });
        }
        if (derivedActions.length === 0) {
          derivedActions.push({ rank: 1, title: 'All Clear', why: 'No urgent security or compliance actions detected.', action: 'Continue monitoring. System is healthy.', severity: 'GREEN' });
        }
        setActions(derivedActions);

        // Placeholder timeline from derived data
        const t: AuditTimelineEvent[] = [];
        if (summaryData.failed_logins_24h > 0) t.push({ time: 'recent', actor: 'System', action: `${summaryData.failed_logins_24h} failed login attempts`, level: 'RED' });
        if (summaryData.phi_access_count_24h > 0) t.push({ time: 'recent', actor: 'System', action: `${summaryData.phi_access_count_24h} PHI access events`, level: 'YELLOW' });
        if (summaryData.recent_exports_7d > 0) t.push({ time: '7d', actor: 'System', action: `${summaryData.recent_exports_7d} data exports`, level: 'BLUE' });
        setTimeline(t);
      }
      if (interopData) {
        setInteropScore(interopData.score as number);
      }
      setLoading(false);
    });
  }, []);

  const healthScoreCandidate = summary?.health_score;
  const healthScore = typeof healthScoreCandidate === 'number' && Number.isFinite(healthScoreCandidate) ? healthScoreCandidate : null;

  const healthColor = healthScore == null ? STATUS_COLOR.GRAY
    : healthScore >= 80 ? STATUS_COLOR.GREEN
    : healthScore >= 50 ? STATUS_COLOR.YELLOW
    : STATUS_COLOR.RED;

  const policyCompleteness = healthScore != null ? Math.min(healthScore + 10, 100) : 0;

  const hasSummary = summary != null;
  const failedLogins24h = hasSummary ? summary.failed_logins_24h : null;
  const phiAccess24h = hasSummary ? summary.phi_access_count_24h : null;
  const pendingApprovals = hasSummary ? summary.pending_approvals_count : null;
  const exports7d = hasSummary ? summary.recent_exports_7d : null;

  return (
    <div className="p-5 space-y-8 min-h-screen">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <div className="text-micro font-bold uppercase tracking-[0.2em] text-[var(--q-orange)]/70 mb-1">TRUST & GOVERNANCE</div>
          <h1 className="text-xl font-black uppercase tracking-wider text-[var(--color-text-primary)]">Compliance Command Center</h1>
          <p className="text-xs text-[var(--color-text-muted)] mt-0.5">Security · Audit · PHI · Interoperability · Policy — Real-Time</p>
        </div>
        <div className="flex items-center gap-3">
          <Link href="/founder/security/access-logs" className="h-8 px-3 bg-red-600/[0.12] border border-[var(--color-brand-red)]/20 text-red text-xs font-semibold chamfer-4 hover:bg-red-600/[0.2] transition-colors flex items-center gap-1.5">
            <span className="w-1.5 h-1.5  bg-red animate-pulse" />
            Access Logs
          </Link>
          <Link href="/founder/security/role-builder" className="h-8 px-3 bg-purple-500/[0.1] border border-purple-500/[0.25] text-system-compliance text-xs font-semibold chamfer-4 hover:bg-purple-500/[0.15] transition-colors flex items-center">
            Role Builder
          </Link>
        </div>
      </div>

      {loading ? (
        <div className="grid grid-cols-3 gap-4">
          {[1, 2, 3].map(i => <div key={i} className="h-28 bg-[var(--color-bg-panel)] border border-border-DEFAULT animate-pulse" />)}
        </div>
      ) : (
        <>
          {/* ── MODULE 1 : Score Rings ── */}
          <section>
            <div className="hud-rail pb-2 mb-4">
              <div className="flex items-baseline gap-3">
                <span className="text-micro font-bold text-[var(--q-orange)]/70 font-mono">MODULE 01</span>
                <h2 className="text-sm font-bold uppercase tracking-widest text-[var(--color-text-primary)]">Trust Scores</h2>
              </div>
            </div>
            <div className="grid grid-cols-2 md:grid-cols-4 gap-6 justify-items-center">
              <ScoreRing score={healthScore} label="Security Health" color={healthColor} />
              <ScoreRing score={policyCompleteness} label="Policy Complete" color={policyCompleteness >= 80 ? STATUS_COLOR.GREEN : STATUS_COLOR.YELLOW} />
              <ScoreRing score={interopScore} label="Interop Ready" color={STATUS_COLOR.BLUE} />
              <ScoreRing score={summary ? Math.max(100 - summary.failed_logins_24h * 10, 0) : 100} label="Auth Health" color={summary && summary.failed_logins_24h > 3 ? STATUS_COLOR.RED : STATUS_COLOR.GREEN} />
            </div>
          </section>

          {/* ── MODULE 2 : Risk Badges ── */}
          <section>
            <div className="hud-rail pb-2 mb-4">
              <div className="flex items-baseline gap-3">
                <span className="text-micro font-bold text-[var(--q-orange)]/70 font-mono">MODULE 02</span>
                <h2 className="text-sm font-bold uppercase tracking-widest text-[var(--color-text-primary)]">Status Badges</h2>
              </div>
            </div>
            <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
              <TrustBadge label="Failed Logins (24h)" status={hasSummary ? (summary.failed_logins_24h > 3 ? 'RED' : 'GREEN') : 'GRAY'} count={failedLogins24h ?? undefined} />
              <TrustBadge label="PHI Access (24h)" status={hasSummary ? (summary.phi_access_count_24h > 50 ? 'ORANGE' : 'GREEN') : 'GRAY'} count={phiAccess24h ?? undefined} />
              <TrustBadge label="Pending Approvals" status={hasSummary ? (summary.pending_approvals_count > 0 ? 'YELLOW' : 'GREEN') : 'GRAY'} count={pendingApprovals ?? undefined} />
              <TrustBadge label="Exports (7d)" status={hasSummary ? (summary.recent_exports_7d > 10 ? 'YELLOW' : 'GREEN') : 'GRAY'} count={exports7d ?? undefined} />
            </div>
          </section>

          {/* ── MODULE 3 : Activity Meters ── */}
          <section>
            <div className="hud-rail pb-2 mb-4">
              <div className="flex items-baseline gap-3">
                <span className="text-micro font-bold text-[var(--q-orange)]/70 font-mono">MODULE 03</span>
                <h2 className="text-sm font-bold uppercase tracking-widest text-[var(--color-text-primary)]">Activity Meters</h2>
              </div>
            </div>
            <div className="bg-[var(--color-bg-panel)] border border-border-DEFAULT p-4 space-y-3" style={{ clipPath: 'polygon(0 0, calc(100% - 10px) 0, 100% 10px, 100% 100%, 0 100%)' }}>
              <MeterBar label="Failed Logins" value={failedLogins24h} max={20} color={STATUS_COLOR.RED} />
              <MeterBar label="PHI Access" value={phiAccess24h} max={200} color={STATUS_COLOR.ORANGE} />
              <MeterBar label="Pending Actions" value={pendingApprovals} max={20} color={STATUS_COLOR.YELLOW} />
              <MeterBar label="Data Exports" value={exports7d} max={50} color={STATUS_COLOR.BLUE} />
            </div>
          </section>

          {/* ── MODULE 4 : Sensitive Access Timeline ── */}
          <section>
            <div className="hud-rail pb-2 mb-4">
              <div className="flex items-baseline gap-3">
                <span className="text-micro font-bold text-[var(--q-orange)]/70 font-mono">MODULE 04</span>
                <h2 className="text-sm font-bold uppercase tracking-widest text-[var(--color-text-primary)]">Sensitive Access Timeline</h2>
              </div>
            </div>
            <div className="bg-[var(--color-bg-panel)] border border-border-DEFAULT p-4" style={{ clipPath: 'polygon(0 0, calc(100% - 10px) 0, 100% 10px, 100% 100%, 0 100%)' }}>
              {timeline.length === 0 ? (
                <div className="text-xs text-[var(--color-text-muted)]">No recent sensitive access events.</div>
              ) : (
                timeline.map((e, i) => <TimelineRow key={i} {...e} />)
              )}
            </div>
          </section>

          {/* ── MODULE 5 : Next Best Actions (Top 3) ── */}
          <section>
            <div className="hud-rail pb-2 mb-4">
              <div className="flex items-baseline gap-3">
                <span className="text-micro font-bold text-[var(--q-orange)]/70 font-mono">MODULE 05</span>
                <h2 className="text-sm font-bold uppercase tracking-widest text-[var(--color-text-primary)]">Next Best Actions</h2>
                <span className="text-xs text-[var(--color-text-muted)]">Top 3 priorities</span>
              </div>
            </div>
            <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
              {actions.slice(0, 3).map(a => <NextActionCard key={a.rank} {...a} />)}
            </div>
          </section>

          {/* ── MODULE 6 : Simple Mode Summary ── */}
          <section>
            <div className="hud-rail pb-2 mb-4">
              <div className="flex items-baseline gap-3">
                <span className="text-micro font-bold text-[var(--q-orange)]/70 font-mono">MODULE 06</span>
                <h2 className="text-sm font-bold uppercase tracking-widest text-[var(--color-text-primary)]">Simple Mode</h2>
              </div>
            </div>
            <div className="bg-[var(--color-bg-panel)] border border-border-DEFAULT p-5 space-y-4" style={{ clipPath: 'polygon(0 0, calc(100% - 10px) 0, 100% 10px, 100% 100%, 0 100%)' }}>
              <div>
                <div className="text-micro font-bold uppercase tracking-widest text-[var(--q-orange)]/70 mb-1">WHAT HAPPENED</div>
                <div className="text-sm text-[var(--color-text-primary)]">
                  {summary?.failed_logins_24h ? `${summary.failed_logins_24h} failed login attempts detected.` : 'No anomalies detected.'}
                  {summary?.phi_access_count_24h ? ` ${summary.phi_access_count_24h} PHI access events logged.` : ''}
                  {summary?.pending_approvals_count ? ` ${summary.pending_approvals_count} actions awaiting approval.` : ''}
                </div>
              </div>
              <div>
                <div className="text-micro font-bold uppercase tracking-widest text-[var(--q-orange)]/70 mb-1">WHY IT MATTERS</div>
                <div className="text-sm text-[var(--color-text-primary)]">
                  {summary && summary.health_score < 80
                    ? 'Your trust score is below optimal. This means there are open security or compliance gaps that could put your agency at risk during audits or incidents.'
                    : 'Your agency is operating within healthy security and compliance boundaries. Good posture.'}
                </div>
              </div>
              <div>
                <div className="text-micro font-bold uppercase tracking-widest text-[var(--q-orange)]/70 mb-1">DO THIS NEXT</div>
                <div className="text-sm font-semibold text-[var(--color-text-primary)]">
                  {actions[0]?.action ?? 'Continue monitoring. All clear.'}
                </div>
              </div>
            </div>
          </section>

          {/* ── Quick Links ── */}
          <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
            {[
              { href: '/founder/security/access-logs', label: 'Access Logs', color: 'var(--q-red)' },
              { href: '/founder/security/role-builder', label: 'Role Builder', color: 'var(--q-red)' },
              { href: '/founder/security/field-masking', label: 'Field Masking', color: 'var(--q-red)' },
              { href: '/founder/security/policy-sandbox', label: 'Policy Sandbox', color: 'var(--q-red)' },
            ].map((l) => (
              <Link key={l.href} href={l.href} className="block bg-[var(--color-bg-panel)] border border-border-DEFAULT p-4 hover:border-white/[0.18] transition-colors text-center" style={{ clipPath: 'polygon(0 0, calc(100% - 8px) 0, 100% 8px, 100% 100%, 0 100%)' }}>
                <div className="text-xs font-bold" style={{ color: l.color }}>{l.label}</div>
              </Link>
            ))}
          </div>
        </>
      )}

      <Link href="/founder" className="text-xs text-[var(--q-orange)]/70 hover:text-[var(--q-orange)]">← Back to Founder Command OS</Link>
    </div>
  );
}
