'use client';
import { useState, useEffect, useCallback } from 'react';
import Link from 'next/link';

const API = process.env.NEXT_PUBLIC_API_URL || '';
const getToken = () => typeof window !== 'undefined' ? 'Bearer ' + (localStorage.getItem('qs_token') || '') : '';

// ── Color System ───────────────────────────────────────────────────────────────
// RED = BLOCKING | ORANGE = HIGH RISK | YELLOW = NEEDS ATTENTION
// BLUE = IN REVIEW | GREEN = READY | GRAY = INFORMATIONAL

const HEALTH_COLORS: Record<string, { bg: string; border: string; text: string; label: string }> = {
  RED:    { bg: 'rgba(229,57,53,0.12)',   border: 'rgba(229,57,53,0.5)',   text: '#ef5350', label: 'BLOCKING' },
  ORANGE: { bg: 'rgba(255,107,26,0.12)',  border: 'rgba(255,107,26,0.5)',  text: '#ff6b1a', label: 'HIGH RISK' },
  YELLOW: { bg: 'rgba(255,193,7,0.10)',   border: 'rgba(255,193,7,0.4)',   text: '#ffc107', label: 'ATTENTION' },
  BLUE:   { bg: 'rgba(41,182,246,0.10)',  border: 'rgba(41,182,246,0.4)',  text: '#29b6f6', label: 'IN REVIEW' },
  GREEN:  { bg: 'rgba(76,175,80,0.10)',   border: 'rgba(76,175,80,0.4)',   text: '#4caf50', label: 'READY' },
  GRAY:   { bg: 'rgba(120,130,140,0.10)', border: 'rgba(120,130,140,0.3)', text: '#78909c', label: 'CLOSED' },
};

const SEV_COLOR: Record<string, string> = {
  BLOCKING: '#ef5350', HIGH: '#ff6b1a', MEDIUM: '#ffc107',
  LOW: '#29b6f6', INFORMATIONAL: '#78909c',
};

function Panel({ children, className = '' }: { children: React.ReactNode; className?: string }) {
  return (
    <div className={`bg-[rgba(255,255,255,0.03)] border border-[rgba(255,255,255,0.08)] rounded-lg p-4 ${className}`}>
      {children}
    </div>
  );
}

function StatCard({ label, value, sub, color, link }: { label: string; value: string | number; sub?: string; color?: string; link?: string }) {
  const content = (
    <Panel>
      <div className="text-[10px] uppercase tracking-widest text-[rgba(255,255,255,0.4)] mb-1">{label}</div>
      <div className="text-3xl font-black" style={{ color: color ?? 'white' }}>{value}</div>
      {sub && <div className="text-[11px] text-[rgba(255,255,255,0.4)] mt-0.5">{sub}</div>}
    </Panel>
  );
  if (link) return <Link href={link}>{content}</Link>;
  return content;
}

function HealthBadge({ health }: { health: string }) {
  const c = HEALTH_COLORS[health] ?? HEALTH_COLORS.GRAY;
  return (
    <span className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-[11px] font-bold uppercase tracking-widest"
      style={{ background: c.bg, border: `1px solid ${c.border}`, color: c.text }}>
      <span className="w-2 h-2 rounded-full animate-pulse" style={{ background: c.text }} />
      {c.label}
    </span>
  );
}

function SeverityBadge({ severity }: { severity: string }) {
  const color = SEV_COLOR[severity] ?? '#78909c';
  return (
    <span className="inline-block px-2 py-0.5 rounded text-[10px] font-bold uppercase tracking-wider"
      style={{ background: color + '22', color, border: `1px solid ${color}55` }}>
      {severity}
    </span>
  );
}

interface OpsIssue {
  issue: string;
  severity: string;
  source: string;
  what_is_wrong: string;
  why_it_matters: string;
  what_you_should_do: string;
  operations_context: string;
  human_review: string;
  confidence: string;
}

interface OpsCommand {
  ops_health: string;
  top_3_actions: Array<{ color: string; title: string; what: string; do_this: string; severity: string }>;
  ai_issues: OpsIssue[];
  dispatch: { active_mission_count: number; unassigned_count: number; en_route_count: number; active_missions: unknown[]; unassigned_missions: unknown[] };
  crewlink: { escalated_page_count: number; late_page_count: number };
  fleet: { fleet_count: number; avg_readiness: number; units_ready: number; units_limited: number; units_no_go: number; active_fleet_alerts: number };
  staffing: { available: number; assigned: number; fatigue_flags: number; active_conflicts: number; overall_readiness: string; gaps: unknown[] };
  facility_requests: { pending_count: number };
  computed_at: string;
}

export default function OpsCommandPage() {
  const [data, setData] = useState<OpsCommand | null>(null);
  const [loading, setLoading] = useState(true);
  const [expandedIssue, setExpandedIssue] = useState<number | null>(null);
  const [lastRefresh, setLastRefresh] = useState<string>('');

  const load = useCallback(async () => {
    try {
      const r = await fetch(`${API}/api/v1/ops/command`, { headers: { Authorization: getToken() } });
      if (r.ok) {
        const j = await r.json();
        setData(j);
        setLastRefresh(new Date().toLocaleTimeString());
      }
    } catch {
      // network error — retain existing data
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    load();
    const iv = setInterval(load, 15000); // auto-refresh every 15s
    return () => clearInterval(iv);
  }, [load]);

  const health = data?.ops_health ?? 'GRAY';
  const hc = HEALTH_COLORS[health] ?? HEALTH_COLORS.GRAY;

  return (
    <div className="p-6 space-y-6 max-w-[1600px] mx-auto">

      {/* ── Header ── */}
      <div className="flex items-center justify-between">
        <div>
          <div className="text-[10px] uppercase tracking-widest text-[rgba(255,255,255,0.4)] mb-1">Founder Operations Command</div>
          <h1 className="text-2xl font-black text-white">Operations Command Center</h1>
          <p className="text-sm text-[rgba(255,255,255,0.45)] mt-1">
            Real-time dispatch · CrewLink · Fleet · Staffing · AI Ops Advisor
          </p>
        </div>
        <div className="flex items-center gap-4">
          {lastRefresh && <span className="text-[10px] text-[rgba(255,255,255,0.3)]">Updated {lastRefresh}</span>}
          <button onClick={load} className="px-4 py-2 bg-[rgba(255,255,255,0.06)] border border-[rgba(255,255,255,0.12)] text-[11px] font-semibold rounded-lg hover:bg-[rgba(255,255,255,0.1)] transition-colors">
            ↻ Refresh
          </button>
          {data && <HealthBadge health={health} />}
        </div>
      </div>

      {loading && (
        <div className="flex items-center gap-3 p-6 rounded-lg border border-[rgba(255,255,255,0.08)]">
          <div className="w-4 h-4 border-2 border-t-transparent border-orange-400 rounded-full animate-spin" />
          <span className="text-sm text-[rgba(255,255,255,0.5)]">Loading operations data…</span>
        </div>
      )}

      {data && (
        <>
          {/* ── Top 3 Next Actions ── */}
          {(data.top_3_actions ?? []).length > 0 && (
            <div>
              <div className="text-[10px] uppercase tracking-widest text-[rgba(255,255,255,0.4)] mb-3">
                ⚡ Top 3 Next Actions — Do These Now
              </div>
              <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
                {data.top_3_actions.map((action, i) => {
                  const ac = HEALTH_COLORS[action.color] ?? HEALTH_COLORS.GRAY;
                  return (
                    <div key={i} className="rounded-xl p-4 border" style={{ background: ac.bg, borderColor: ac.border }}>
                      <div className="flex items-start justify-between mb-2">
                        <span className="text-[10px] font-black uppercase tracking-widest" style={{ color: ac.text }}>
                          #{i + 1} · {action.severity}
                        </span>
                      </div>
                      <div className="text-sm font-bold text-white mb-1">{action.title}</div>
                      <div className="text-[11px] text-[rgba(255,255,255,0.6)] mb-3">{action.what}</div>
                      <div className="text-[11px] font-semibold" style={{ color: ac.text }}>→ {action.do_this}</div>
                    </div>
                  );
                })}
              </div>
            </div>
          )}

          {/* ── Domain Score Cards ── */}
          <div className="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-6 gap-3">
            <StatCard
              label="Active Missions"
              value={data.dispatch.active_mission_count}
              sub={`${data.dispatch.unassigned_count} unassigned`}
              color={data.dispatch.unassigned_count > 0 ? '#ef5350' : '#4caf50'}
              link="/founder/ops/cad"
            />
            <StatCard
              label="En Route"
              value={data.dispatch.en_route_count}
              color="#29b6f6"
              link="/founder/ops/cad"
            />
            <StatCard
              label="Escalated Pages"
              value={data.crewlink.escalated_page_count}
              sub={`${data.crewlink.late_page_count} late`}
              color={data.crewlink.escalated_page_count > 0 ? '#ef5350' : '#4caf50'}
              link="/founder/ops/crewlink"
            />
            <StatCard
              label="Fleet Readiness"
              value={`${data.fleet.avg_readiness}%`}
              sub={`${data.fleet.units_ready} ready / ${data.fleet.units_no_go} no-go`}
              color={data.fleet.avg_readiness >= 70 ? '#4caf50' : data.fleet.avg_readiness >= 40 ? '#ffc107' : '#ef5350'}
              link="/founder/ops/fleet"
            />
            <StatCard
              label="Crew Available"
              value={data.staffing.available}
              sub={data.staffing.overall_readiness}
              color={data.staffing.overall_readiness === 'READY' ? '#4caf50' : data.staffing.overall_readiness === 'WARNING' ? '#ffc107' : '#ef5350'}
              link="/founder/ops/staffing"
            />
            <StatCard
              label="Facility Requests"
              value={data.facility_requests.pending_count}
              sub="pending review"
              color={data.facility_requests.pending_count > 0 ? '#ffc107' : '#78909c'}
              link="/founder/ops/transportlink"
            />
          </div>

          {/* ── Fleet + Staffing Detail ── */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <Panel>
              <div className="flex items-center justify-between mb-4">
                <div className="text-[10px] uppercase tracking-widest text-[rgba(255,255,255,0.4)]">Fleet Status</div>
                <Link href="/founder/ops/fleet" className="text-[11px] text-orange-400 hover:text-orange-300">View Fleet →</Link>
              </div>
              <div className="grid grid-cols-3 gap-3">
                {[
                  { label: 'Ready', val: data.fleet.units_ready, color: '#4caf50' },
                  { label: 'Limited', val: data.fleet.units_limited, color: '#ffc107' },
                  { label: 'No-Go', val: data.fleet.units_no_go, color: '#ef5350' },
                ].map(item => (
                  <div key={item.label} className="text-center p-3 rounded-lg bg-[rgba(255,255,255,0.04)]">
                    <div className="text-2xl font-black" style={{ color: item.color }}>{item.val}</div>
                    <div className="text-[10px] uppercase tracking-wider text-[rgba(255,255,255,0.4)] mt-0.5">{item.label}</div>
                  </div>
                ))}
              </div>
              {data.fleet.active_fleet_alerts > 0 && (
                <div className="mt-3 px-3 py-2 rounded-lg bg-[rgba(229,57,53,0.1)] border border-[rgba(229,57,53,0.3)]">
                  <span className="text-[11px] text-red-400">⚠ {data.fleet.active_fleet_alerts} unresolved fleet alert(s)</span>
                </div>
              )}
            </Panel>

            <Panel>
              <div className="flex items-center justify-between mb-4">
                <div className="text-[10px] uppercase tracking-widest text-[rgba(255,255,255,0.4)]">Staffing Readiness</div>
                <Link href="/founder/ops/staffing" className="text-[11px] text-orange-400 hover:text-orange-300">View Staffing →</Link>
              </div>
              <div className="grid grid-cols-3 gap-3 mb-3">
                {[
                  { label: 'Available', val: data.staffing.available, color: '#4caf50' },
                  { label: 'Assigned', val: data.staffing.assigned, color: '#29b6f6' },
                  { label: 'Unavailable', val: data.staffing.unavailable, color: '#78909c' },
                ].map(item => (
                  <div key={item.label} className="text-center p-3 rounded-lg bg-[rgba(255,255,255,0.04)]">
                    <div className="text-2xl font-black" style={{ color: item.color }}>{(item as Record<string, unknown>).val as number}</div>
                    <div className="text-[10px] uppercase tracking-wider text-[rgba(255,255,255,0.4)] mt-0.5">{item.label}</div>
                  </div>
                ))}
              </div>
              {data.staffing.fatigue_flags > 0 && (
                <div className="px-3 py-2 rounded-lg bg-[rgba(255,107,26,0.1)] border border-[rgba(255,107,26,0.3)] mb-2">
                  <span className="text-[11px] text-orange-400">⚠ {data.staffing.fatigue_flags} fatigue flag(s) active</span>
                </div>
              )}
              {data.staffing.active_conflicts > 0 && (
                <div className="px-3 py-2 rounded-lg bg-[rgba(255,193,7,0.1)] border border-[rgba(255,193,7,0.3)]">
                  <span className="text-[11px] text-yellow-400">⚠ {data.staffing.active_conflicts} assignment conflict(s)</span>
                </div>
              )}
            </Panel>
          </div>

          {/* ── AI Issues ── */}
          {(data.ai_issues ?? []).length > 0 && (
            <div>
              <div className="text-[10px] uppercase tracking-widest text-[rgba(255,255,255,0.4)] mb-3">
                🤖 AI Operations Advisor — {data.ai_issues.length} Issue(s) Detected
              </div>
              <div className="space-y-2">
                {data.ai_issues.map((issue, i) => (
                  <div key={i} className="rounded-xl border overflow-hidden"
                    style={{ borderColor: SEV_COLOR[issue.severity] + '44', background: SEV_COLOR[issue.severity] + '0a' }}>
                    <button
                      onClick={() => setExpandedIssue(expandedIssue === i ? null : i)}
                      className="w-full flex items-center justify-between p-4 text-left hover:bg-[rgba(255,255,255,0.03)] transition-colors"
                    >
                      <div className="flex items-center gap-3">
                        <SeverityBadge severity={issue.severity} />
                        <span className="text-sm font-semibold text-white">{issue.issue}</span>
                        <span className="text-[10px] text-[rgba(255,255,255,0.35)] uppercase tracking-wider">{issue.source}</span>
                      </div>
                      <div className="flex items-center gap-3">
                        <span className={`text-[10px] uppercase tracking-wider ${
                          issue.human_review === 'REQUIRED' ? 'text-red-400' : 'text-[rgba(255,255,255,0.4)]'
                        }`}>
                          {issue.human_review === 'REQUIRED' ? '👤 HUMAN REQUIRED' : ''}
                        </span>
                        <span className="text-[rgba(255,255,255,0.3)] text-sm">{expandedIssue === i ? '▲' : '▼'}</span>
                      </div>
                    </button>

                    {expandedIssue === i && (
                      <div className="px-4 pb-4 space-y-3 border-t border-[rgba(255,255,255,0.06)]">
                        <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mt-4">
                          <div>
                            <div className="text-[10px] uppercase tracking-wider text-[rgba(255,255,255,0.35)] mb-1">WHAT IS WRONG</div>
                            <div className="text-sm text-[rgba(255,255,255,0.8)]">{issue.what_is_wrong}</div>
                          </div>
                          <div>
                            <div className="text-[10px] uppercase tracking-wider text-[rgba(255,255,255,0.35)] mb-1">WHY IT MATTERS</div>
                            <div className="text-sm text-[rgba(255,255,255,0.8)]">{issue.why_it_matters}</div>
                          </div>
                          <div>
                            <div className="text-[10px] uppercase tracking-wider mb-1" style={{ color: SEV_COLOR[issue.severity] + 'cc' }}>DO THIS NEXT</div>
                            <div className="text-sm font-medium text-white whitespace-pre-line">{issue.what_you_should_do}</div>
                          </div>
                        </div>
                        <div className="p-3 rounded-lg bg-[rgba(255,255,255,0.04)] border border-[rgba(255,255,255,0.06)]">
                          <div className="text-[10px] uppercase tracking-wider text-[rgba(255,255,255,0.3)] mb-1">Operations Context</div>
                          <div className="text-[11px] text-[rgba(255,255,255,0.55)]">{issue.operations_context}</div>
                        </div>
                        <div className="flex items-center gap-4 text-[10px] uppercase tracking-wider text-[rgba(255,255,255,0.3)]">
                          <span>Confidence: <span className="text-white">{issue.confidence}</span></span>
                          <span>Human Review: <span className={issue.human_review === 'REQUIRED' ? 'text-red-400' : 'text-white'}>{issue.human_review}</span></span>
                        </div>
                      </div>
                    )}
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* ── No Issues State ── */}
          {(data.ai_issues ?? []).length === 0 && !loading && (
            <div className="text-center py-10 rounded-xl border border-[rgba(76,175,80,0.3)] bg-[rgba(76,175,80,0.05)]">
              <div className="text-4xl mb-3">✅</div>
              <div className="text-lg font-bold text-green-400">All Systems Operational</div>
              <div className="text-sm text-[rgba(255,255,255,0.45)] mt-1">No critical issues detected. Monitor active missions above.</div>
            </div>
          )}

          {/* ── Quick Navigation ── */}
          <div>
            <div className="text-[10px] uppercase tracking-widest text-[rgba(255,255,255,0.4)] mb-3">Operations Domains</div>
            <div className="grid grid-cols-2 md:grid-cols-5 gap-3">
              {[
                { href: '/founder/ops/cad', label: 'CAD / Dispatch', icon: '📡', color: '#ff6b1a', sub: 'Mission state machine' },
                { href: '/founder/ops/crewlink', label: 'CrewLink Paging', icon: '📟', color: '#29b6f6', sub: 'Push paging & escalation' },
                { href: '/founder/ops/fleet', label: 'Fleet & Telemetry', icon: '🚑', color: '#4caf50', sub: 'OBD-II & readiness' },
                { href: '/founder/ops/staffing', label: 'Staffing', icon: '👥', color: '#ffc107', sub: 'Crew qualifications' },
                { href: '/founder/ops/transportlink', label: 'TransportLink', icon: '🏥', color: '#9c27b0', sub: 'Interfacility intake' },
              ].map(item => (
                <Link key={item.href} href={item.href}
                  className="p-4 rounded-xl border border-[rgba(255,255,255,0.08)] bg-[rgba(255,255,255,0.03)] hover:bg-[rgba(255,255,255,0.07)] transition-colors group">
                  <div className="text-2xl mb-2">{item.icon}</div>
                  <div className="text-sm font-bold text-white group-hover:text-orange-400 transition-colors">{item.label}</div>
                  <div className="text-[10px] text-[rgba(255,255,255,0.35)] mt-0.5">{item.sub}</div>
                </Link>
              ))}
            </div>
          </div>
        </>
      )}
    </div>
  );
}
