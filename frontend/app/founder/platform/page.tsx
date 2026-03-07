'use client';

import { useState, useEffect, useCallback } from 'react';

const API = process.env.NEXT_PUBLIC_API_URL || '';

function getToken(): string {
  if (typeof window === 'undefined') return '';
  return 'Bearer ' + (localStorage.getItem('qs_token') || '');
}

// Color system: RED=BLOCKING, ORANGE=HIGH RISK, YELLOW=WARNING, BLUE=IN REVIEW, GREEN=HEALTHY, GRAY=INFORMATIONAL
const STATUS_COLORS: Record<string, { bg: string; border: string; text: string; dot: string }> = {
  RED:    { bg: 'bg-red-500/10', border: 'border-red-500/40', text: 'text-red-400', dot: 'bg-red-500' },
  ORANGE: { bg: 'bg-orange-500/10', border: 'border-orange-500/40', text: 'text-orange-400', dot: 'bg-orange-500' },
  YELLOW: { bg: 'bg-yellow-500/10', border: 'border-yellow-500/40', text: 'text-yellow-400', dot: 'bg-yellow-500' },
  BLUE:   { bg: 'bg-blue-500/10', border: 'border-blue-500/40', text: 'text-blue-400', dot: 'bg-blue-500' },
  GREEN:  { bg: 'bg-green-500/10', border: 'border-green-500/40', text: 'text-green-400', dot: 'bg-green-500' },
  GRAY:   { bg: 'bg-zinc-500/10', border: 'border-zinc-500/40', text: 'text-zinc-400', dot: 'bg-zinc-500' },
};

const SEVERITY_COLORS: Record<string, string> = {
  CRITICAL: 'text-red-400',
  HIGH: 'text-orange-400',
  MEDIUM: 'text-yellow-400',
  LOW: 'text-blue-400',
  GREEN: 'text-green-400',
};

function getStatusStyle(status: string) {
  return STATUS_COLORS[status] || STATUS_COLORS.GRAY;
}

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
  ci_cd: { last_build: string; branch: string; deployment: string };
  incidents: unknown[];
}

interface AIAnalysis {
  issue: string;
  severity: string;
  source: string;
  what_is_wrong: string;
  why_it_matters: string;
  what_to_do_next: string;
  tech_context: string;
  human_review: string;
  confidence: string;
}

interface Incident {
  id: string;
  title: string;
  severity: string;
  state: string;
  created_at: string;
}

export default function PlatformCommandCenter() {
  const [health, setHealth] = useState<PlatformHealth | null>(null);
  const [aiAnalysis, setAiAnalysis] = useState<AIAnalysis | null>(null);
  const [incidents, setIncidents] = useState<Incident[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [lastRefresh, setLastRefresh] = useState<string>('');

  const fetchHealth = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const headers = { Authorization: getToken() };
      const res = await fetch(`${API}/api/v1/platform/health`, { headers });
      if (!res.ok) throw new Error(`Health API returned ${res.status}`);
      const data: PlatformHealth = await res.json();
      setHealth(data);
      setLastRefresh(new Date().toLocaleTimeString());

      // Fetch AI analysis
      try {
        const aiRes = await fetch(`${API}/api/v1/tech_copilot/analyze`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json', ...headers },
          body: JSON.stringify({ type: 'platform_snapshot', data }),
        });
        if (aiRes.ok) {
          setAiAnalysis(await aiRes.json());
        }
      } catch {
        // AI is non-critical
      }

      // Fetch active incidents
      try {
        const incRes = await fetch(`${API}/api/v1/platform/incidents?active_only=true`, { headers });
        if (incRes.ok) {
          setIncidents(await incRes.json());
        }
      } catch {
        // Incidents non-critical
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to fetch platform health');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchHealth();
    const interval = setInterval(fetchHealth, 30000);
    return () => clearInterval(interval);
  }, [fetchHealth]);

  // Score color
  const scoreColor = (score: number) => {
    if (score >= 90) return 'text-green-400';
    if (score >= 70) return 'text-yellow-400';
    if (score >= 50) return 'text-orange-400';
    return 'text-red-400';
  };

  if (error && !health) {
    return (
      <div className="p-8">
        <div className="bg-red-500/10 border border-red-500/40 p-6 rounded-lg">
          <h2 className="text-lg font-bold text-red-400 mb-2">Platform Health Unavailable</h2>
          <p className="text-sm text-zinc-300 mb-4">{error}</p>
          <button onClick={fetchHealth} className="px-4 py-2 bg-red-500/20 border border-red-500/40 text-red-300 text-sm hover:bg-red-500/30 transition-colors rounded">
            Retry
          </button>
        </div>
      </div>
    );
  }

  if (loading && !health) {
    return (
      <div className="p-8 flex items-center gap-3">
        <div className="w-3 h-3 rounded-full bg-orange-500 animate-pulse" />
        <span className="text-sm text-zinc-400">Probing infrastructure...</span>
      </div>
    );
  }

  if (!health) return null;

  const overallStyle = getStatusStyle(health.status);

  return (
    <div className="p-5 min-h-screen">
      {/* HEADER */}
      <div className="pb-3 mb-6 flex justify-between items-end border-b border-zinc-800">
        <div>
          <div className="text-[10px] uppercase tracking-[0.2em] text-zinc-500 mb-1">Domination OS</div>
          <h1 className="text-2xl font-bold text-white">Tech Command Center</h1>
          <p className="text-sm text-zinc-400 mt-1">Platform Observability &amp; Reliability</p>
        </div>
        <div className="text-right flex items-end gap-4">
          <div>
            <div className="text-[10px] text-zinc-500 font-mono mb-1">REFRESHED</div>
            <div className="text-xs text-zinc-400 font-mono">{lastRefresh}</div>
          </div>
          <div>
            <div className="text-[10px] text-zinc-500 font-mono mb-1">PLATFORM SCORE</div>
            <div className={`text-4xl font-bold font-mono ${scoreColor(health.score)}`}>
              {health.score}%
            </div>
          </div>
          <button
            onClick={fetchHealth}
            disabled={loading}
            className="px-3 py-1.5 bg-zinc-800 border border-zinc-700 text-zinc-300 text-xs hover:bg-zinc-700 transition-colors rounded disabled:opacity-50"
          >
            {loading ? 'Scanning...' : 'Refresh'}
          </button>
        </div>
      </div>

      {/* ERROR BANNER */}
      {error && (
        <div className="mb-4 p-3 bg-yellow-500/10 border border-yellow-500/30 rounded text-xs text-yellow-300">
          Last refresh error: {error} — showing cached data
        </div>
      )}

      {/* TOP 3 PRIORITIES (always visible) */}
      {(incidents.length > 0 || (aiAnalysis && aiAnalysis.severity !== 'GREEN')) && (
        <div className="mb-6 grid grid-cols-1 md:grid-cols-3 gap-3">
          {incidents.slice(0, 3).map((inc) => {
            const sev = SEVERITY_COLORS[inc.severity] || 'text-zinc-400';
            return (
              <div key={inc.id} className="bg-zinc-900 border border-zinc-700 p-3 rounded">
                <div className="flex items-center gap-2 mb-1">
                  <span className={`text-[10px] font-mono font-bold ${sev}`}>{inc.severity}</span>
                  <span className="text-[10px] text-zinc-500">{inc.state}</span>
                </div>
                <div className="text-xs text-white">{inc.title}</div>
              </div>
            );
          })}
          {aiAnalysis && aiAnalysis.severity !== 'GREEN' && incidents.length < 3 && (
            <div className="bg-zinc-900 border border-orange-500/30 p-3 rounded">
              <div className="flex items-center gap-2 mb-1">
                <span className={`text-[10px] font-mono font-bold ${SEVERITY_COLORS[aiAnalysis.severity] || 'text-zinc-400'}`}>
                  {aiAnalysis.severity}
                </span>
                <span className="text-[10px] text-zinc-500">AI DETECTED</span>
              </div>
              <div className="text-xs text-white">{aiAnalysis.issue}</div>
            </div>
          )}
        </div>
      )}

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* LEFT COL: RAW METRICS */}
        <div className="lg:col-span-2 space-y-6">
          {/* Service Health Matrix */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div className="bg-zinc-900/60 border border-zinc-800 rounded-lg p-4">
              <h3 className="text-[10px] uppercase tracking-[0.15em] text-zinc-500 mb-3">Service Health Matrix</h3>
              <div className="space-y-2">
                {health.services.map((s) => {
                  const st = getStatusStyle(s.status);
                  return (
                    <div key={s.name} className={`flex justify-between items-center ${st.bg} p-2.5 border ${st.border} rounded`}>
                      <div className="flex items-center gap-2">
                        <span className={`w-2 h-2 rounded-full ${st.dot}`} />
                        <span className="text-xs text-white">{s.name}</span>
                      </div>
                      <span className="text-[10px] font-mono text-zinc-400">{s.latency_ms}ms &middot; {s.uptime}</span>
                    </div>
                  );
                })}
              </div>
            </div>

            {/* Integration Health Badges */}
            <div className="bg-zinc-900/60 border border-zinc-800 rounded-lg p-4">
              <h3 className="text-[10px] uppercase tracking-[0.15em] text-zinc-500 mb-3">Integration Health</h3>
              <div className="space-y-2">
                {health.integrations.map((i) => {
                  const st = getStatusStyle(i.status);
                  return (
                    <div key={i.name} className={`flex justify-between items-center ${st.bg} p-2.5 border ${st.border} rounded`}>
                      <span className="text-xs text-white">{i.name}</span>
                      <span className={`text-[10px] font-mono ${st.text}`}>{i.last_sync.toUpperCase()}</span>
                    </div>
                  );
                })}
              </div>
            </div>
          </div>

          {/* CI/CD & Queue Safety */}
          <div className="bg-zinc-900/60 border border-zinc-800 rounded-lg p-4">
            <h3 className="text-[10px] uppercase tracking-[0.15em] text-zinc-500 mb-3">CI/CD &amp; Queue Safety</h3>
            <div className="flex flex-wrap gap-6">
              <div>
                <div className="text-[10px] text-zinc-500 mb-1 font-mono">LATEST BUILD</div>
                <div className="text-xs text-green-400 font-mono border border-green-500/30 px-2 py-1 bg-green-500/10 rounded">
                  {health.ci_cd.last_build} [{health.ci_cd.branch}]
                </div>
              </div>
              <div>
                <div className="text-[10px] text-zinc-500 mb-1 font-mono">DEPLOY GATE</div>
                <div className="text-xs text-blue-400 font-mono border border-blue-500/30 px-2 py-1 bg-blue-500/10 rounded">
                  {health.ci_cd.deployment}
                </div>
              </div>
              {health.queues.length > 0 && (
                <div className="flex-1">
                  <div className="text-[10px] text-zinc-500 mb-1 font-mono">ACTIVE QUEUES</div>
                  <div className="flex flex-wrap gap-2">
                    {health.queues.map((q) => {
                      const st = getStatusStyle(q.status);
                      return (
                        <div key={q.name} className={`text-[10px] font-mono ${st.bg} px-2 py-1 ${st.text} border ${st.border} rounded`}>
                          {q.name}: <span className="text-white">{q.depth}</span>
                        </div>
                      );
                    })}
                  </div>
                </div>
              )}
            </div>
          </div>

          {/* Active Incidents Panel */}
          <div className="bg-zinc-900/60 border border-zinc-800 rounded-lg p-4">
            <h3 className="text-[10px] uppercase tracking-[0.15em] text-zinc-500 mb-3">Active Incidents</h3>
            {incidents.length === 0 ? (
              <div className="text-xs text-zinc-500 py-2">No active incidents — all clear</div>
            ) : (
              <div className="space-y-2">
                {incidents.map((inc) => {
                  const sev = SEVERITY_COLORS[inc.severity] || 'text-zinc-400';
                  return (
                    <div key={inc.id} className="flex justify-between items-center bg-zinc-800/50 p-2.5 border border-zinc-700 rounded">
                      <div className="flex items-center gap-3">
                        <span className={`text-[10px] font-mono font-bold ${sev}`}>{inc.severity}</span>
                        <span className="text-xs text-white">{inc.title}</span>
                      </div>
                      <div className="flex items-center gap-3">
                        <span className="text-[10px] text-zinc-500 font-mono">{inc.state}</span>
                        <span className="text-[10px] text-zinc-600 font-mono">{new Date(inc.created_at).toLocaleTimeString()}</span>
                      </div>
                    </div>
                  );
                })}
              </div>
            )}
          </div>
        </div>

        {/* RIGHT COL: AI TECH ASSISTANT */}
        <div>
          <div className="bg-zinc-900/60 border border-orange-500/30 rounded-lg p-5 shadow-[0_0_20px_rgba(255,107,26,0.08)] sticky top-5">
            <div className="flex items-center gap-2 mb-4 border-b border-zinc-800 pb-3">
              <span className="w-2 h-2 rounded-full bg-orange-500 animate-pulse" />
              <h3 className="text-xs font-bold text-orange-400 uppercase tracking-[0.15em]">Tech AI Assistant</h3>
            </div>

            {!aiAnalysis ? (
              <div className="text-xs text-zinc-500 animate-pulse py-8 text-center">Analyzing system topology...</div>
            ) : (
              <div className="space-y-4">
                <div>
                  <div className="text-[10px] text-zinc-500 border-b border-zinc-800 mb-1 pb-1">ISSUE &amp; SEVERITY</div>
                  <div className="text-sm text-white font-bold">{aiAnalysis.issue}</div>
                  <div className={`text-[10px] font-mono mt-1 ${SEVERITY_COLORS[aiAnalysis.severity] || 'text-zinc-400'}`}>
                    {aiAnalysis.severity} &bull; {aiAnalysis.source}
                  </div>
                </div>

                <div>
                  <div className="text-[10px] text-zinc-500 border-b border-zinc-800 mb-1 pb-1">WHAT IS WRONG</div>
                  <div className="text-xs text-zinc-200">{aiAnalysis.what_is_wrong}</div>
                </div>

                <div>
                  <div className="text-[10px] text-zinc-500 border-b border-zinc-800 mb-1 pb-1">WHY IT MATTERS</div>
                  <div className="text-xs text-zinc-200">{aiAnalysis.why_it_matters}</div>
                </div>

                <div className="bg-orange-500/10 border border-orange-500/30 p-3 rounded">
                  <div className="text-[10px] text-orange-400 mb-1 font-bold tracking-wider">WHAT YOU SHOULD DO NEXT</div>
                  <div className="text-xs text-white font-mono">{aiAnalysis.what_to_do_next}</div>
                </div>

                <div>
                  <div className="text-[10px] text-zinc-500 border-b border-zinc-800 mb-1 pb-1">TECHNICAL CONTEXT</div>
                  <div className="text-xs text-zinc-300 font-mono">{aiAnalysis.tech_context}</div>
                </div>

                <div className="grid grid-cols-2 gap-2 text-[10px] font-mono pt-3 border-t border-zinc-800">
                  <div>
                    <span className="text-zinc-500 block">HUMAN REVIEW</span>
                    <span className="text-zinc-200">{aiAnalysis.human_review}</span>
                  </div>
                  <div>
                    <span className="text-zinc-500 block">CONFIDENCE</span>
                    <span className="text-zinc-200">{aiAnalysis.confidence}</span>
                  </div>
                </div>
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
