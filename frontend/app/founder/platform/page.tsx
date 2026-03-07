'use client';

import { useState, useEffect } from 'react';
import Link from 'next/link';

const API = process.env.NEXT_PUBLIC_API_URL || '';

function getToken() {
  if (typeof window === 'undefined') return '';
  return 'Bearer ' + (localStorage.getItem('qs_token') || '');
}

export default function PlatformCommandCenter() {
  const [health, setHealth] = useState<any>(null);
  const [aiAnalysis, setAiAnalysis] = useState<any>(null);

  useEffect(() => {
    fetch(`${API}/api/v1/platform/health`, { headers: { Authorization: getToken() } })
      .then(res => res.json())
      .then(data => {
         setHealth(data);
         // Auto-analyze via AI
         fetch(`${API}/api/v1/tech_copilot/analyze`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json', Authorization: getToken() },
            body: JSON.stringify({ type: 'platform_snapshot', data })
         })
         .then(r => r.json())
         .then(ai => setAiAnalysis(ai));
      });
  }, []);

  if (!health) return <div className="p-8 text-orange animate-pulse">Initializing Domination OS...</div>;

  return (
    <div className="p-5 min-h-screen">
      <div className="hud-rail pb-3 mb-6 flex justify-between items-end">
        <div>
          <div className="micro-caps mb-1">Domination OS</div>
          <h1 className="text-h2 font-bold text-text-primary">Tech Command Center</h1>
          <p className="text-body text-text-muted mt-1">Platform Observability & Reliability</p>
        </div>
        <div className="text-right">
          <div className="text-[10px] text-text-muted font-mono mb-1">PLATFORM SCORE</div>
          <div className={`text-4xl font-bold font-mono ${health.score > 90 ? 'text-green-500' : 'text-orange'}`}>
            {health.score}%
          </div>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* LEFT COL: RAW METRICS */}
        <div className="lg:col-span-2 space-y-6">
          
          <div className="grid grid-cols-2 gap-4">
             <div className="bg-bg-panel border border-border-DEFAULT chamfer-8 p-4">
               <h3 className="micro-caps mb-3">Service Health Matrix</h3>
               <div className="space-y-2">
                 {health.services.map((s: any) => (
                   <div key={s.name} className="flex justify-between items-center bg-black/30 p-2 border border-border-DEFAULT rounded-sm">
                     <div className="flex items-center gap-2">
                        <span className={`w-2 h-2 rounded-full ${s.status === 'GREEN' ? 'bg-green-500' : 'bg-red-500'}`}></span>
                        <span className="text-xs text-text-primary">{s.name}</span>
                     </div>
                     <span className="text-[10px] font-mono text-text-muted">{s.latency_ms}ms · {s.uptime}</span>
                   </div>
                 ))}
               </div>
             </div>

             <div className="bg-bg-panel border border-border-DEFAULT chamfer-8 p-4">
               <h3 className="micro-caps mb-3">Integration Health Badges</h3>
               <div className="space-y-2">
                 {health.integrations.map((i: any) => (
                   <div key={i.name} className="flex justify-between items-center bg-black/30 p-2 border border-border-DEFAULT rounded-sm">
                     <span className="text-xs text-text-primary">{i.name}</span>
                     <span className="text-[10px] font-mono text-green-400">SYNCED {i.last_sync}</span>
                   </div>
                 ))}
               </div>
             </div>
          </div>

          <div className="bg-bg-panel border border-border-DEFAULT chamfer-8 p-4">
             <h3 className="micro-caps mb-3">CI/CD & Queue Safety</h3>
             <div className="flex gap-8">
                <div>
                   <div className="text-[10px] text-text-muted mb-1 font-mono">LATEST BUILD</div>
                   <div className="text-xs text-green-400 font-mono border border-green-500/30 px-2 py-1 bg-green-500/10">
                     {health.ci_cd.last_build} [{health.ci_cd.branch}]
                   </div>
                </div>
                <div>
                   <div className="text-[10px] text-text-muted mb-1 font-mono">DEPLOY GATE</div>
                   <div className="text-xs text-orange font-mono border border-orange/30 px-2 py-1 bg-orange/10">
                     {health.ci_cd.deployment}
                   </div>
                </div>
                <div className="flex-1">
                   <div className="text-[10px] text-text-muted mb-1 font-mono">ACTIVE QUEUES</div>
                   <div className="flex gap-2">
                     {health.queues.map((q: any) => (
                        <div key={q.name} className="text-[10px] font-mono bg-black/50 px-2 py-1 text-text-muted border border-border-DEFAULT">
                          {q.name}: <span className="text-white">{q.depth}</span>
                        </div>
                     ))}
                   </div>
                </div>
             </div>
          </div>
        </div>

        {/* RIGHT COL: AI PLATFORM COPILOT */}
        <div>
          <div className="bg-bg-panel border border-orange/40 chamfer-8 p-5 shadow-[0_0_15px_rgba(255,107,26,0.1)] h-full">
            <div className="flex items-center gap-2 mb-4 border-b border-border-DEFAULT pb-3">
              <span className="w-2 h-2 rounded-full bg-orange animate-pulse"></span>
              <h3 className="text-sm font-bold text-orange uppercase tracking-widest">Tech AI Assistant</h3>
            </div>

            {!aiAnalysis ? (
              <div className="text-xs text-text-muted animate-pulse">Scanning incident topology...</div>
            ) : (
              <div className="space-y-4">
                <div>
                  <div className="text-[10px] text-text-muted border-b border-border-DEFAULT mb-1">ISSUE & SEVERITY</div>
                  <div className="text-sm text-text-primary font-bold">{aiAnalysis.issue}</div>
                  <div className="text-[10px] font-mono mt-1 text-green-400">{aiAnalysis.severity} • {aiAnalysis.source}</div>
                </div>

                <div>
                  <div className="text-[10px] text-text-muted border-b border-border-DEFAULT mb-1">WHAT IS WRONG</div>
                  <div className="text-xs text-text-primary">{aiAnalysis.what_is_wrong}</div>
                </div>

                <div>
                  <div className="text-[10px] text-text-muted border-b border-border-DEFAULT mb-1">WHY IT MATTERS</div>
                  <div className="text-xs text-text-primary">{aiAnalysis.why_it_matters}</div>
                </div>

                <div className="bg-orange/10 border border-orange/30 p-3 chamfer-2">
                  <div className="text-[10px] text-orange mb-1 font-bold tracking-wider">WHAT YOU SHOULD DO NEXT</div>
                  <div className="text-xs text-white font-mono">{aiAnalysis.what_to_do_next}</div>
                </div>

                <div className="grid grid-cols-2 gap-2 text-[10px] font-mono pt-4 border-t border-border-DEFAULT">
                  <div>
                    <span className="text-text-muted block">HUMAN REVIEW:</span>
                    <span className="text-text-primary">{aiAnalysis.human_review}</span>
                  </div>
                  <div>
                    <span className="text-text-muted block">CONFIDENCE:</span>
                    <span className="text-text-primary">{aiAnalysis.confidence}</span>
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
