'use client';

import { useEffect, useMemo, useState } from 'react';

import { AIExplanationCard, SimpleModeSummary } from '@/components/ui/AIAssistant';
import {
  getPlatformHealth,
  getTechAssistantIssues,
  listPlatformIncidents,
} from '@/services/api';
import type { SeverityLevel } from '@/lib/design-system/tokens';

type StatusColor = {
  bg: string;
  border: string;
  text: string;
  dot: string;
};

const STATUS_COLORS: Record<string, StatusColor> = {
  RED: {
    bg: 'bg-red-500/10',
    border: 'border-red-500/40',
    text: 'text-red-400',
    dot: 'bg-red-500',
  },
  ORANGE: {
    bg: 'bg-[#FF4D00]-500/10',
    border: 'border-orange-500/40',
    text: 'text-[#FF4D00]-400',
    dot: 'bg-[#FF4D00]-500',
  },
  YELLOW: {
    bg: 'bg-yellow-500/10',
    border: 'border-yellow-500/40',
    text: 'text-yellow-400',
    dot: 'bg-yellow-500',
  },
  BLUE: {
    bg: 'bg-blue-500/10',
    border: 'border-blue-500/40',
    text: 'text-blue-400',
    dot: 'bg-blue-500',
  },
  GREEN: {
    bg: 'bg-green-500/10',
    border: 'border-green-500/40',
    text: 'text-green-400',
    dot: 'bg-green-500',
  },
  GRAY: {
    bg: 'bg-zinc-500/10',
    border: 'border-zinc-500/40',
    text: 'text-zinc-400',
    dot: 'bg-zinc-500',
  },
};

interface ServiceHealth {
  name: string;
  status: string;
  latency_ms: number;
  uptime: string;
}

interface Integration {
  name: string;
  status: string;
  last_sync: string;
}

interface QueueInfo {
  name: string;
  depth: number;
  status: string;
}

interface PlatformHealth {
  score: number;
  status: string;
  timestamp: string;
  services: ServiceHealth[];
  integrations: Integration[];
  queues: QueueInfo[];
  ci_cd: {
    last_build: string;
    branch: string;
    deployment: string;
  };
}

interface Incident {
  id: string;
  title: string;
  severity: string;
  state: string;
  created_at: string;
}

interface AssistantIssue {
  issue: string;
  severity: string;
  source: string;
  what_changed: string;
  why_it_matters: string;
  what_you_should_do: string;
  executive_context: string;
  human_review: string;
  confidence: string;
}

function statusStyle(status: string): StatusColor {
  return STATUS_COLORS[status] || STATUS_COLORS.GRAY;
}

function normalizeSeverity(severity: string): SeverityLevel {
  if (severity === 'BLOCKING' || severity === 'CRITICAL') return 'BLOCKING';
  if (severity === 'HIGH') return 'HIGH';
  if (severity === 'MEDIUM') return 'MEDIUM';
  if (severity === 'LOW') return 'LOW';
  return 'INFORMATIONAL';
}

function severityTextColor(severity: string): string {
  const normalized = normalizeSeverity(severity);
  if (normalized === 'BLOCKING') return 'text-red-400';
  if (normalized === 'HIGH') return 'text-[#FF4D00]-400';
  if (normalized === 'MEDIUM') return 'text-yellow-400';
  if (normalized === 'LOW') return 'text-blue-400';
  return 'text-zinc-400';
}

export default function PlatformCommandCenterPage() {
  const [health, setHealth] = useState<PlatformHealth | null>(null);
  const [incidents, setIncidents] = useState<Incident[]>([]);
  const [assistantIssues, setAssistantIssues] = useState<AssistantIssue[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [lastRefresh, setLastRefresh] = useState<string>('');

  async function refreshAll() {
    setError(null);
    try {
      const [healthData, incidentData] = await Promise.all([
        getPlatformHealth(),
        listPlatformIncidents(true),
      ]);

      const normalizedHealth: PlatformHealth = {
        score: Number(healthData?.score ?? 0),
        status: String(healthData?.status ?? 'GRAY'),
        timestamp: String(healthData?.timestamp ?? ''),
        services: Array.isArray(healthData?.services) ? healthData.services : [],
        integrations: Array.isArray(healthData?.integrations) ? healthData.integrations : [],
        queues: Array.isArray(healthData?.queues) ? healthData.queues : [],
        ci_cd: {
          last_build: String(healthData?.ci_cd?.last_build ?? 'N/A'),
          branch: String(healthData?.ci_cd?.branch ?? 'main'),
          deployment: String(healthData?.ci_cd?.deployment ?? 'UNKNOWN'),
        },
      };

      const normalizedIncidents: Incident[] = Array.isArray(incidentData) ? incidentData : [];

      setHealth(normalizedHealth);
      setIncidents(normalizedIncidents);

      const issueData = await getTechAssistantIssues({
        snapshot: normalizedHealth as unknown as Record<string, unknown>,
        incidents: normalizedIncidents as unknown as Array<Record<string, unknown>>,
        top_n: 5,
      });
      setAssistantIssues(Array.isArray(issueData) ? issueData : []);
      setLastRefresh(new Date().toLocaleTimeString());
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : 'Failed to fetch platform command data');
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    void refreshAll();
    const interval = setInterval(() => {
      void refreshAll();
    }, 30000);
    return () => clearInterval(interval);
  }, []);

  const topPriorityIncidents = useMemo(() => incidents.slice(0, 3), [incidents]);

  const scoreClass = useMemo(() => {
    if (!health) return 'text-zinc-400';
    if (health.score >= 90) return 'text-green-400';
    if (health.score >= 70) return 'text-yellow-400';
    if (health.score >= 50) return 'text-[#FF4D00]-400';
    return 'text-red-400';
  }, [health]);

  if (loading && !health) {
    return (
      <div className="p-8 flex items-center gap-3">
        <div className="w-3 h-3  bg-[#FF4D00]-500 animate-pulse" />
        <span className="text-sm text-zinc-400">Loading platform command telemetry…</span>
      </div>
    );
  }

  if (!health) {
    return (
      <div className="p-8">
        <div className="bg-red-500/10 border border-red-500/40 p-6 chamfer-8">
          <h2 className="text-lg font-bold text-red-400 mb-2">Platform command unavailable</h2>
          <p className="text-sm text-zinc-300 mb-4">{error || 'No platform data available.'}</p>
          <button
            onClick={() => void refreshAll()}
            className="px-4 py-2 bg-red-500/20 border border-red-500/40 text-red-300 text-sm hover:bg-red-500/30 transition-colors chamfer-4"
          >
            Retry
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="p-5 min-h-screen">
      <div className="pb-3 mb-6 flex justify-between items-end border-b border-zinc-800">
        <div>
          <div className="text-micro uppercase tracking-[0.2em] text-zinc-500 mb-1">Domination OS</div>
          <h1 className="text-2xl font-bold text-white">Platform Command Center</h1>
          <p className="text-sm text-zinc-400 mt-1">Reliability telemetry, incident control, and AI executive guidance</p>
        </div>
        <div className="text-right flex items-end gap-4">
          <div>
            <div className="text-micro text-zinc-500 font-mono mb-1">REFRESHED</div>
            <div className="text-xs text-zinc-400 font-mono">{lastRefresh || '—'}</div>
          </div>
          <div>
            <div className="text-micro text-zinc-500 font-mono mb-1">PLATFORM SCORE</div>
            <div className={`text-4xl font-bold font-mono ${scoreClass}`}>{health.score}%</div>
          </div>
          <button
            onClick={() => void refreshAll()}
            disabled={loading}
            className="px-3 py-1.5 bg-zinc-800 border border-zinc-700 text-zinc-300 text-xs hover:bg-zinc-700 transition-colors chamfer-4 disabled:opacity-50"
          >
            {loading ? 'Refreshing…' : 'Refresh'}
          </button>
        </div>
      </div>

      {error && (
        <div className="mb-4 p-3 bg-yellow-500/10 border border-yellow-500/30 chamfer-4 text-xs text-yellow-300">
          Last refresh warning: {error}
        </div>
      )}

      {(topPriorityIncidents.length > 0 || assistantIssues.length > 0) && (
        <div className="mb-6 grid grid-cols-1 md:grid-cols-3 gap-3">
          {topPriorityIncidents.map((incident) => (
            <div key={incident.id} className="bg-zinc-900 border border-zinc-700 p-3 chamfer-4">
              <div className="flex items-center gap-2 mb-1">
                <span className={`text-micro font-mono font-bold ${severityTextColor(incident.severity)}`}>
                  {incident.severity}
                </span>
                <span className="text-micro text-zinc-500">{incident.state}</span>
              </div>
              <div className="text-xs text-white">{incident.title}</div>
            </div>
          ))}

          {topPriorityIncidents.length < 3 && assistantIssues[0] && (
            <div className="bg-zinc-900 border border-orange-500/30 p-3 chamfer-4">
              <div className="flex items-center gap-2 mb-1">
                <span className={`text-micro font-mono font-bold ${severityTextColor(assistantIssues[0].severity)}`}>
                  {assistantIssues[0].severity}
                </span>
                <span className="text-micro text-zinc-500">AI ANALYST</span>
              </div>
              <div className="text-xs text-white">{assistantIssues[0].issue}</div>
            </div>
          )}
        </div>
      )}

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <div className="lg:col-span-2 space-y-6">
          <SimpleModeSummary
            domain="ops"
            screenName="Platform Command"
            whatThisDoes="Shows real health probes, incidents, integration status, and queue pressure for founder-level operational control."
            whatIsWrong={assistantIssues[0]?.what_changed}
            whatMatters={assistantIssues[0]?.why_it_matters || 'Platform reliability directly affects dispatch, billing, and customer trust.'}
            whatToClickNext={assistantIssues[0]?.what_you_should_do || 'Review active incidents and refresh platform health telemetry.'}
            requiresReview={assistantIssues[0]?.human_review === 'REQUIRED'}
          />

          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div className="bg-zinc-900/60 border border-zinc-800 chamfer-8 p-4">
              <h3 className="text-micro uppercase tracking-[0.15em] text-zinc-500 mb-3">Service Health Matrix</h3>
              <div className="space-y-2">
                {health.services.map((service) => {
                  const style = statusStyle(service.status);
                  return (
                    <div key={service.name} className={`flex justify-between items-center ${style.bg} p-2.5 border ${style.border} chamfer-4`}>
                      <div className="flex items-center gap-2">
                        <span className={`w-2 h-2  ${style.dot}`} />
                        <span className="text-xs text-white">{service.name}</span>
                      </div>
                      <span className="text-micro font-mono text-zinc-400">
                        {service.latency_ms}ms · {service.uptime}
                      </span>
                    </div>
                  );
                })}
              </div>
            </div>

            <div className="bg-zinc-900/60 border border-zinc-800 chamfer-8 p-4">
              <h3 className="text-micro uppercase tracking-[0.15em] text-zinc-500 mb-3">Integration Status</h3>
              <div className="space-y-2">
                {health.integrations.map((integration) => {
                  const style = statusStyle(integration.status);
                  return (
                    <div key={integration.name} className={`flex justify-between items-center ${style.bg} p-2.5 border ${style.border} chamfer-4`}>
                      <span className="text-xs text-white">{integration.name}</span>
                      <span className={`text-micro font-mono ${style.text}`}>{integration.last_sync.toUpperCase()}</span>
                    </div>
                  );
                })}
              </div>
            </div>
          </div>

          <div className="bg-zinc-900/60 border border-zinc-800 chamfer-8 p-4">
            <h3 className="text-micro uppercase tracking-[0.15em] text-zinc-500 mb-3">Active Incidents</h3>
            {incidents.length === 0 ? (
              <div className="text-xs text-zinc-500 py-2">No active incidents — all clear.</div>
            ) : (
              <div className="space-y-2">
                {incidents.map((incident) => (
                  <div key={incident.id} className="flex justify-between items-center bg-zinc-800/50 p-2.5 border border-zinc-700 chamfer-4">
                    <div className="flex items-center gap-3">
                      <span className={`text-micro font-mono font-bold ${severityTextColor(incident.severity)}`}>
                        {incident.severity}
                      </span>
                      <span className="text-xs text-white">{incident.title}</span>
                    </div>
                    <div className="flex items-center gap-3">
                      <span className="text-micro text-zinc-500 font-mono">{incident.state}</span>
                      <span className="text-micro text-zinc-600 font-mono">{new Date(incident.created_at).toLocaleTimeString()}</span>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>

        <div className="space-y-3">
          <div className="bg-zinc-900/60 border border-orange-500/30 chamfer-8 p-4 sticky top-5 space-y-3">
            <div className="flex items-center gap-2 border-b border-zinc-800 pb-3">
              <span className="w-2 h-2  bg-[#FF4D00]-500 animate-pulse" />
              <h3 className="text-xs font-bold text-[#FF4D00]-400 uppercase tracking-[0.15em]">Executive AI Analyst</h3>
            </div>

            {assistantIssues.length === 0 ? (
              <div className="text-xs text-zinc-500 py-6 text-center">No AI issues currently detected.</div>
            ) : (
              assistantIssues.map((issue, idx) => (
                <AIExplanationCard
                  key={`${issue.issue}-${idx}`}
                  what={issue.what_changed}
                  why={issue.why_it_matters}
                  next={issue.what_you_should_do}
                  domain="ops"
                  severity={normalizeSeverity(issue.severity)}
                  confidence={issue.confidence === 'HIGH' ? 0.9 : issue.confidence === 'MEDIUM' ? 0.7 : 0.5}
                  requiresReview={issue.human_review === 'REQUIRED'}
                />
              ))
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
