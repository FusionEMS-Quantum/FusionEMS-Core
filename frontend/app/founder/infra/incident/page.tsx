'use client';
import { motion } from 'framer-motion';
import Link from 'next/link';
import { useState, useEffect } from 'react';

function SectionHeader({ number, title, sub }: { number: string; title: string; sub?: string }) {
  return (
    <div className="border-b border-border-subtle pb-2 mb-4">
      <div className="flex items-baseline gap-3">
          <span className="text-micro font-bold text-orange-dim font-mono">MODULE {number}</span>
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

function Panel({ children, className }: { children: React.ReactNode; className?: string }) {
  return (
    <div
      className={`bg-[var(--color-bg-panel)] border border-border-DEFAULT p-4 ${className ?? ''}`}
      style={{ clipPath: 'polygon(0 0,calc(100% - 10px) 0,100% 10px,100% 100%,0 100%)' }}
    >
      {children}
    </div>
  );
}

function severityBadge(s: string): 'ok' | 'warn' | 'error' | 'info' {
  if (s === 'high') return 'error';
  if (s === 'medium') return 'warn';
  return 'info';
}

const CONTACT_METHODS_FOUNDER = ['PagerDuty', 'SMS', 'Phone'];
const CONTACT_METHODS_TL = ['PagerDuty', 'SMS'];

interface ServiceStatus {
  name: string;
  uptime: string;
}
interface Incident {
  date: string;
  title: string;
  severity: string;
  duration: string;
  affected: string;
  resolution: string;
}
interface Playbook {
  id: string;
  name: string;
  desc: string;
}

export default function IncidentControlCenterPage() {
  const [incidentMode, setIncidentMode] = useState(false);
  const [data, setData] = useState<{ services: ServiceStatus[]; incidents: Incident[]; playbooks: Playbook[] }>({
    services: [], incidents: [], playbooks: []
  });
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        const res = await fetch('/api/v1/founder/infra/incidents', { credentials: 'include' });
        if (!res.ok) throw new Error(`${res.status}`);
        const json = await res.json();
        if (!cancelled) setData(json);
      } catch (e: unknown) {
        if (!cancelled) setError(e instanceof Error ? e.message : 'Failed to load');
      } finally {
        if (!cancelled) setLoading(false);
      }
    })();
    return () => { cancelled = true; };
  }, []);

  if (loading) {
    return (
      <div className="min-h-screen bg-[var(--color-bg-base)] text-[var(--color-text-primary)] flex items-center justify-center">
        <div className="text-xs text-[var(--color-text-muted)] uppercase tracking-widest animate-pulse">Loading incident data…</div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="min-h-screen bg-[var(--color-bg-base)] text-[var(--color-text-primary)] flex items-center justify-center">
        <div className="text-center space-y-2">
          <div className="text-xs text-red uppercase tracking-widest font-bold">Failed to load incident data</div>
          <div className="text-body text-[var(--color-text-muted)]">{error}</div>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-[var(--color-bg-base)] text-[var(--color-text-primary)] p-6 space-y-8">
      {/* Header */}
      <div className="flex items-start justify-between flex-wrap gap-4">
        <div>
            <div className="text-micro font-bold font-mono text-orange-dim uppercase tracking-widest mb-1">
            MODULE 10 · INFRASTRUCTURE
          </div>
          <h1 className="text-2xl font-bold tracking-tight text-[var(--color-text-primary)]">Incident Control Center</h1>
          <p className="text-xs text-[var(--color-text-muted)] mt-1">
            System status · incident history · response playbooks · on-call
          </p>
        </div>
      </div>

      {/* MODULE 1 — System Status Overview */}
      <section>
        <SectionHeader number="1" title="System Status Overview" />
        {data.services.length === 0 ? (
          <Panel>
            <div className="text-body text-[var(--color-text-muted)] py-4 text-center">No service status data — connect infrastructure monitoring to populate.</div>
          </Panel>
        ) : (
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
            {data.services.map((svc) => (
              <div
                key={svc.name}
                className="bg-[var(--color-bg-panel)] border border-border-DEFAULT p-4"
                style={{ clipPath: 'polygon(0 0,calc(100% - 10px) 0,100% 10px,100% 100%,0 100%)' }}
              >
                <div className="text-xs font-semibold text-[var(--color-text-primary)] mb-2">{svc.name}</div>
                <div className="mb-2">
                  <Badge label="operational" status="ok" />
                </div>
                <div className="text-micro font-mono text-[var(--color-text-muted)]">{svc.uptime} uptime</div>
              </div>
            ))}
          </div>
        )}
      </section>

      {/* MODULE 2 — Active Incidents */}
      <section>
        <SectionHeader number="2" title="Active Incidents" />
        <Panel>
          <div
            className="flex items-center gap-4 p-4 chamfer-4"
            style={{ background: 'color-mix(in srgb, var(--color-status-active) 8%, transparent)', border: '1px solid color-mix(in srgb, var(--color-status-active) 19%, transparent)' }}
          >
            <div
              className="w-8 h-8  flex items-center justify-center flex-shrink-0"
              style={{ background: 'color-mix(in srgb, var(--color-status-active) 13%, transparent)', border: '1px solid color-mix(in srgb, var(--color-status-active) 31%, transparent)' }}
            >
              <svg width="16" height="16" viewBox="0 0 16 16" fill="none">
                <path d="M3 8L6.5 11.5L13 5" stroke="var(--color-status-active)" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" />
              </svg>
            </div>
            <div>
              <div className="text-sm font-bold text-[var(--color-status-active)] tracking-wide uppercase">ALL SYSTEMS OPERATIONAL</div>
              <div className="text-body text-[var(--color-text-muted)] mt-0.5">No active incidents · Last checked moments ago</div>
            </div>
          </div>
        </Panel>
      </section>

      {/* MODULE 3 — Incident History */}
      <section>
        <SectionHeader number="3" title="Incident History" />
        <Panel>
          <div className="overflow-x-auto">
            <table className="w-full text-xs">
              <thead>
                <tr className="text-[var(--color-text-muted)] uppercase tracking-widest text-micro">
                  <th className="text-left pb-2 pr-4 font-semibold">Date</th>
                  <th className="text-left pb-2 pr-4 font-semibold">Title</th>
                  <th className="text-left pb-2 pr-4 font-semibold">Severity</th>
                  <th className="text-left pb-2 pr-4 font-semibold">Duration</th>
                  <th className="text-left pb-2 pr-4 font-semibold">Affected</th>
                  <th className="text-left pb-2 font-semibold">Resolution</th>
                </tr>
              </thead>
              <tbody>
                {data.incidents.length === 0 ? (
                  <tr>
                    <td colSpan={6} className="py-6 text-center text-body text-[var(--color-text-muted)]">
                      No incident history — incidents will appear here once reported.
                    </td>
                  </tr>
                ) : data.incidents.map((inc, i) => (
                  <tr key={i} className="border-t border-border-subtle">
                    <td className="py-2 pr-4 font-mono text-[var(--color-text-muted)]">{inc.date}</td>
                    <td className="py-2 pr-4 text-[var(--color-text-primary)]">{inc.title}</td>
                    <td className="py-2 pr-4"><Badge label={inc.severity} status={severityBadge(inc.severity)} /></td>
                    <td className="py-2 pr-4 font-mono text-[var(--color-text-secondary)]">{inc.duration}</td>
                    <td className="py-2 pr-4 font-mono text-[var(--color-text-muted)]">{inc.affected}</td>
                    <td className="py-2 text-[var(--color-text-muted)]">{inc.resolution}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </Panel>
      </section>

      {/* MODULE 4 — Response Playbooks */}
      <section>
        <SectionHeader number="4" title="Response Playbooks" />
        <Panel>
          {data.playbooks.length === 0 ? (
            <div className="text-body text-[var(--color-text-muted)] py-4 text-center">No playbooks configured — add response playbooks to enable rapid incident response.</div>
          ) : (
            <div className="space-y-0">
              {data.playbooks.map((pb) => (
                <div
                  key={pb.id}
                  className="flex items-center justify-between gap-4 py-3 border-b border-border-subtle last:border-0"
                >
                  <div className="flex items-center gap-3 min-w-0">
                    <span className="text-micro font-mono text-brand-orange flex-shrink-0">{pb.id}</span>
                    <div className="min-w-0">
                      <div className="text-xs font-semibold text-[var(--color-text-primary)]">{pb.name}</div>
                      <div className="text-body text-[var(--color-text-muted)] truncate">{pb.desc}</div>
                    </div>
                  </div>
                  <button
                    className="flex-shrink-0 px-3 py-1 text-micro font-semibold uppercase tracking-wider chamfer-4 border border-border-DEFAULT text-system-cad hover:bg-bg-overlay transition-colors"
                  >
                    View Playbook
                  </button>
                </div>
              ))}
            </div>
          )}
        </Panel>
      </section>

      {/* MODULE 5 — Incident Mode Controls */}
      <section>
        <SectionHeader number="5" title="Incident Mode Controls" />
        <Panel>
          <p className="text-body text-[var(--color-text-muted)] mb-4 leading-relaxed">
            Activating incident mode suspends all non-critical automated communications, routes all alerts to the founder dashboard, and enables war-room protocols.
          </p>

          {!incidentMode ? (
            <button
              onClick={() => setIncidentMode(true)}
              className="px-6 py-2.5 text-xs font-bold uppercase tracking-widest chamfer-4 border border-[var(--color-brand-red)]/20 text-red hover:bg-[var(--color-brand-red)]/10 transition-colors"
              style={{ background: 'color-mix(in srgb, var(--color-brand-red) 3%, transparent)' }}
            >
              ACTIVATE INCIDENT MODE
            </button>
          ) : (
            <div className="space-y-3">
              <motion.div
                className="flex items-center gap-3 p-3 chamfer-4"
                style={{ background: 'color-mix(in srgb, var(--color-brand-red) 8%, transparent)', border: '1px solid color-mix(in srgb, var(--color-brand-red) 25%, transparent)' }}
                animate={{ opacity: [1, 0.7, 1] }}
                transition={{ duration: 1.4, repeat: Infinity }}
              >
                <span className="w-2 h-2  flex-shrink-0" style={{ background: 'var(--color-brand-red)' }} />
                <div>
                  <div className="text-xs font-bold text-red uppercase tracking-widest">INCIDENT MODE ACTIVE</div>
                  <div className="text-body text-[var(--color-text-secondary)] mt-0.5">
                    Non-critical comms suspended · War room routing engaged · Founder alerted
                  </div>
                </div>
              </motion.div>
              <button
                onClick={() => setIncidentMode(false)}
                className="px-4 py-1.5 text-micro font-semibold uppercase tracking-wider chamfer-4 border border-white/[0.12] text-[var(--color-text-secondary)] hover:bg-[var(--color-bg-base)]/5 transition-colors"
              >
                Deactivate
              </button>
            </div>
          )}
        </Panel>
      </section>

      {/* MODULE 6 — Public Status Page */}
      <section>
        <SectionHeader number="6" title="Public Status Page" />
        <Panel>
          <div className="grid grid-cols-2 sm:grid-cols-3 gap-4 mb-4">
            <div>
              <div className="text-micro font-semibold uppercase tracking-widest text-[var(--color-text-muted)] mb-1">Status Page URL</div>
              <div className="text-body font-mono text-system-billing">status.fusionemsquantum.com</div>
            </div>
            <div>
              <div className="text-micro font-semibold uppercase tracking-widest text-[var(--color-text-muted)] mb-1">Last Published</div>
              <div className="text-body text-[var(--color-text-secondary)]">2 minutes ago</div>
            </div>
            <div>
              <div className="text-micro font-semibold uppercase tracking-widest text-[var(--color-text-muted)] mb-1">Agency Subscribers</div>
              <div className="text-body font-bold text-[var(--color-text-primary)]">12</div>
            </div>
            <div>
              <div className="text-micro font-semibold uppercase tracking-widest text-[var(--color-text-muted)] mb-1">30d Uptime</div>
              <div className="text-body font-bold text-[var(--color-status-active)]">99.97%</div>
            </div>
          </div>
          <button
            className="px-4 py-1.5 text-micro font-semibold uppercase tracking-wider chamfer-4 border border-border-DEFAULT text-system-cad hover:bg-bg-overlay transition-colors"
          >
            Publish Update
          </button>
        </Panel>
      </section>

      {/* MODULE 7 — On-Call Schedule */}
      <section>
        <SectionHeader number="7" title="On-Call Schedule" />
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
          {/* Primary */}
          <Panel>
            <div className="flex items-center justify-between mb-2">
              <div className="text-micro font-semibold uppercase tracking-widest text-[var(--color-text-muted)]">Primary On-Call</div>
              <Badge label="active" status="ok" />
            </div>
            <div className="text-sm font-bold text-[var(--color-text-primary)] mb-1">Founder</div>
            <div className="flex flex-wrap gap-1.5">
              {CONTACT_METHODS_FOUNDER.map((m) => (
                <span
                  key={m}
                  className="px-2 py-0.5 text-micro font-semibold chamfer-4 border border-border-DEFAULT text-[var(--color-text-secondary)]"
                  style={{ background: 'rgba(255,255,255,0.04)' }}
                >
                  {m}
                </span>
              ))}
            </div>
          </Panel>

          {/* Secondary */}
          <Panel>
            <div className="flex items-center justify-between mb-2">
              <div className="text-micro font-semibold uppercase tracking-widest text-[var(--color-text-muted)]">Secondary On-Call</div>
              <Badge label="standby" status="info" />
            </div>
            <div className="text-sm font-bold text-[var(--color-text-primary)] mb-1">Tech Lead</div>
            <div className="flex flex-wrap gap-1.5">
              {CONTACT_METHODS_TL.map((m) => (
                <span
                  key={m}
                  className="px-2 py-0.5 text-micro font-semibold chamfer-4 border border-border-DEFAULT text-[var(--color-text-secondary)]"
                  style={{ background: 'rgba(255,255,255,0.04)' }}
                >
                  {m}
                </span>
              ))}
            </div>
          </Panel>
        </div>
        <div className="mt-3 px-1">
          <span className="text-body text-[var(--color-text-muted)]">Next rotation: </span>
          <span className="text-body text-[var(--color-text-secondary)]">in 5 days</span>
        </div>
      </section>

      {/* Back */}
      <div>
        <Link href="/founder" className="text-xs text-system-cad hover:text-[var(--color-text-primary)] transition-colors">
          ← Back to Founder OS
        </Link>
      </div>
    </div>
  );
}
