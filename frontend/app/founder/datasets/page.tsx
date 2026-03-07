"use client";

import React, { useEffect, useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import {
  Database,
  Activity,
  Bot,
  TerminalSquare,
  ShieldCheck,
  Stethoscope,
  Building2,
  Ghost,
  Workflow,
  Send,
  Loader2,
  Server,
  X,
  FileJson,
  Layers,
  CheckCircle2,
  AlertTriangle
} from "lucide-react";

export default function GodModeDatasets() {
  const [activeTab, setActiveTab] = useState<'status' | 'nemsis_ai' | 'exports' | 'templates'>('status');
  const [systemStatus, setSystemStatus] = useState<any>(null);
  const [naturalQuery, setNaturalQuery] = useState("");
  const [aiResult, setAiResult] = useState<any>(null);
  const [thinking, setThinking] = useState(false);
  
  // New States
  const [showGhostMode, setShowGhostMode] = useState(false);
  const [activeDevices, setActiveDevices] = useState<any[]>([]);
  const [exportData, setExportData] = useState<any>(null);

  const [infiltratedDevice, setInfiltratedDevice] = useState<any>(null);
  const [infiltrationLogs, setInfiltrationLog] = useState<string[]>([]);

  const startInfiltration = (dev: any) => {
    setInfiltratedDevice(dev);
    setInfiltrationLog([]);
    const logs = [
      `[GHOST] Initializing secure socket to Android device (${dev.ip})...`,
      `[AUTH] Bypassing tenant firewall via Founder sovereign key...`,
      `[RTC] Establishing WebRTC data channel...`,
      `[STREAM] Capturing raw frame buffer from Android Mobile display...`,
      `[SUCCESS] Remote access granted. You are now controlling ${dev.user}'s screen.`
    ];
    logs.forEach((log, index) => {
      setTimeout(() => {
        setInfiltrationLog(prev => [...prev, log]);
      }, (index + 1) * 800);
    });
  };

  useEffect(() => {
    async function load() {
      try {
        const res = await fetch(`${process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000"}/api/datasets/status`);
        const data = await res.json();
        setSystemStatus(data);
      } catch (e) {
        console.error("Failed to fetch system datasets status", e);
      }
    }
    load();
  }, []);

  const loadExports = async () => {
    try {
      const res = await fetch(`${process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000"}/api/datasets/exports`);
      setExportData(await res.json());
    } catch (e) { console.error(e); }
  };

  const loadDevices = async () => {
    try {
      const res = await fetch(`${process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000"}/api/datasets/active-devices`);
      setActiveDevices(await res.json());
    } catch (e) { console.error(e); }
  };

  useEffect(() => {
    if (activeTab === 'exports' && !exportData) loadExports();
  }, [activeTab]);

  useEffect(() => {
    if (showGhostMode) loadDevices();
  }, [showGhostMode]);

  const handleAIExpression = async () => {
    if (!naturalQuery) return;
    setThinking(true);
    setAiResult(null);
    try {
      const res = await fetch(`${process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000"}/api/datasets/ai-expression-builder`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ natural_language: naturalQuery })
      });
      const data = await res.json();
      setAiResult(data);
    } catch (e) {
      console.error(e);
    } finally {
      setTimeout(() => setThinking(false), 800);
    }
  };

  return (
    <div className="min-h-screen bg-[#07090D] text-white selection:bg-orange-500 selection:text-black font-sans relative overflow-hidden">
      {/* Background Effect */}
      <div className="fixed inset-0 z-0 bg-[radial-gradient(ellipse_at_top_right,_var(--tw-gradient-stops))] from-yellow-900/20 via-black to-black opacity-90 pointer-events-none" />

      {/* Ghost Mode Overlay */}
      <AnimatePresence>
        {showGhostMode && (
          <motion.div 
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            className="fixed inset-0 z-50 bg-black/80 backdrop-blur-sm flex items-center justify-center p-6"
          >
            <motion.div 
              initial={{ scale: 0.95, y: 20 }}
              animate={{ scale: 1, y: 0 }}
              exit={{ scale: 0.95, y: 20 }}
              className="bg-[#0f1115] border border-orange-500/30 rounded-2xl w-full max-w-4xl shadow-2xl overflow-hidden shadow-orange-900/20"
            >
              <div className="bg-orange-500/10 border-b border-orange-500/20 p-4 flex justify-between items-center">
                <div className="flex items-center gap-3">
                  <Ghost className="w-6 h-6 text-orange-400 animate-pulse" />
                  <div>
                    <h3 className="text-orange-400 font-bold tracking-widest uppercase">GHOST MODE : ACTIVE SESSIONS</h3>
                    <p className="text-orange-500/60 text-xs font-mono">Intercepting live tenant websockets for remote assist...</p>
                  </div>
                </div>
                <button onClick={() => setShowGhostMode(false)} className="text-gray-400 hover:text-white transition-colors">
                  <X className="w-6 h-6" />
                </button>
              </div>
              <div className="p-6">
                <table className="w-full text-left border-collapse">
                  <thead>
                    <tr className="border-b border-gray-800 text-xs text-gray-500 uppercase tracking-wider font-mono">
                      <th className="pb-3">Device ID / IP</th>
                      <th className="pb-3">Agency</th>
                      <th className="pb-3">User (Active)</th>
                      <th className="pb-3">Status</th>
                      <th className="pb-3 text-right">Action</th>
                    </tr>
                  </thead>
                  <tbody className="text-sm">
                    {activeDevices.map(dev => (
                      <tr key={dev.id} className="border-b border-gray-800/50 hover:bg-white/5 transition-colors">
                        <td className="py-4 font-mono text-gray-400">
                          <span className="text-orange-300">{dev.device_type}</span><br/>
                          <span className="text-xs">{dev.ip}</span>
                        </td>
                        <td className="py-4 text-gray-300">{dev.agency}</td>
                        <td className="py-4 text-gray-300">{dev.user}</td>
                        <td className="py-4">
                          <span className="px-2 py-1 bg-green-500/10 text-green-400 text-xs rounded-full border border-green-500/20">
                            {dev.status}
                          </span>
                        </td>
                        <td className="py-4 text-right">
                          <button className="bg-orange-600 hover:bg-orange-500 text-black font-bold text-xs px-4 py-2 rounded shadow shrink-0">
                            INFILTRATE
                          </button>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </motion.div>
          </motion.div>
        )}
      </AnimatePresence>

      <div className="relative z-10 p-6 md:p-10 max-w-[90rem] mx-auto space-y-8">
        
        {/* Header */}
        <motion.div
          initial={{ opacity: 0, y: -20 }}
          animate={{ opacity: 1, y: 0 }}
          className="flex items-center justify-between border-b border-white/10 pb-6"
        >
          <div>
            <h1 className="text-4xl font-extrabold tracking-tighter text-transparent bg-clip-text bg-gradient-to-r from-yellow-400 to-orange-600 drop-shadow-sm flex items-center gap-4">
              <Database className="w-9 h-9 text-yellow-400" />
              Sovereign Operations Command
            </h1>
            <p className="text-gray-400 mt-2 text-sm max-w-2xl">
              God Mode Dataset Manager. Track Schematron expressions, manage lexicons, build templates, monitor export queues, and access Remote Assist.
            </p>
          </div>
          <div className="flex gap-4">
            <div 
              onClick={() => setShowGhostMode(true)}
              className="px-4 py-2 rounded-lg bg-orange-500/10 border border-orange-500/30 flex items-center gap-2 cursor-pointer hover:bg-orange-500/20 transition-colors shadow-[0_0_15px_rgba(249,115,22,0.2)]"
            >
              <Ghost className="w-4 h-4 text-orange-400" />
              <span className="text-orange-400 font-mono text-sm tracking-wide">GHOST MODE</span>
            </div>
          </div>
        </motion.div>

        {/* Tab Navigation */}
        <div className="flex gap-6 border-b border-gray-800">
          <button onClick={() => setActiveTab('status')} className={`pb-3 font-semibold text-sm transition-colors border-b-2 flex items-center gap-2 ${activeTab === 'status' ? 'border-yellow-400 text-yellow-400' : 'border-transparent text-gray-500 hover:text-gray-300'}`}>
            <Database className="w-4 h-4" /> Lexicons & Facilities
          </button>
          <button onClick={() => setActiveTab('templates')} className={`pb-3 font-semibold text-sm transition-colors border-b-2 flex items-center gap-2 ${activeTab === 'templates' ? 'border-yellow-400 text-yellow-400' : 'border-transparent text-gray-500 hover:text-gray-300'}`}>
            <Layers className="w-4 h-4" /> Template Builder
          </button>
          <button onClick={() => setActiveTab('nemsis_ai')} className={`pb-3 font-semibold text-sm transition-colors border-b-2 flex items-center gap-2 ${activeTab === 'nemsis_ai' ? 'border-yellow-400 text-yellow-400' : 'border-transparent text-gray-500 hover:text-gray-300'}`}>
            <Bot className="w-4 h-4" /> AI NEMSIS Engine
          </button>
          <button onClick={() => setActiveTab('exports')} className={`pb-3 font-semibold text-sm transition-colors border-b-2 flex items-center gap-2 ${activeTab === 'exports' ? 'border-yellow-400 text-yellow-400' : 'border-transparent text-gray-500 hover:text-gray-300'}`}>
            <Server className="w-4 h-4" /> Global Export Status
          </button>
        </div>

        {/* VIEW: STATUS / LEXICONS */}
        {activeTab === 'status' && (
          <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
            <div className="bg-black/40 border border-white/10 rounded-xl p-6 backdrop-blur-md">
              <div className="flex items-center gap-3 mb-4">
                <ShieldCheck className="w-6 h-6 text-blue-400" />
                <h3 className="text-lg font-bold text-gray-100">NEMSIS Core</h3>
              </div>
              {systemStatus ? (
                <div className="space-y-3 font-mono text-xs">
                  <div className="flex justify-between border-b border-white/5 pb-2"><span className="text-gray-500">Version</span><span className="text-blue-300">v{systemStatus.nemsis.version}</span></div>
                  <div className="flex justify-between border-b border-white/5 pb-2"><span className="text-gray-500">Last Database Sync</span><span className="text-gray-300">{systemStatus.nemsis.last_update}</span></div>
                  <div className="flex justify-between pb-2"><span className="text-gray-500">Schematron Target</span><span className="text-green-400">ACTIVE</span></div>
                </div>
              ) : <Loader2 className="w-5 h-5 animate-spin text-blue-400" />}
            </div>

            <div className="bg-black/40 border border-white/10 rounded-xl p-6 backdrop-blur-md">
              <div className="flex items-center gap-3 mb-4">
                <Activity className="w-6 h-6 text-red-500" />
                <h3 className="text-lg font-bold text-gray-100">NERIS Fire Sync</h3>
              </div>
              {systemStatus ? (
                <div className="space-y-3 font-mono text-xs">
                  <div className="flex justify-between border-b border-white/5 pb-2"><span className="text-gray-500">Standard</span><span className="text-red-300">v{systemStatus.neris.version}</span></div>
                  <div className="flex justify-between border-b border-white/5 pb-2"><span className="text-gray-500">Last Block Push</span><span className="text-gray-300">{systemStatus.neris.last_update}</span></div>
                  <div className="flex justify-between pb-2"><span className="text-gray-500">Validation DB</span><span className="text-green-400">SYNCED</span></div>
                </div>
              ) : <Loader2 className="w-5 h-5 animate-spin text-red-500" />}
            </div>

            <div className="bg-black/40 border border-white/10 rounded-xl p-6 backdrop-blur-md">
              <div className="flex items-center gap-3 mb-4">
                <Stethoscope className="w-6 h-6 text-purple-400" />
                <h3 className="text-lg font-bold text-gray-100">Clinical Lexicons</h3>
              </div>
              {systemStatus ? (
                <div className="space-y-3 font-mono text-xs">
                  <div className="flex justify-between border-b border-white/5 pb-2"><span className="text-gray-500">RxNorm Set</span><span className="text-purple-300">{systemStatus.rxnorm.term_count.toLocaleString()} Terms</span></div>
                  <div className="flex justify-between border-b border-white/5 pb-2"><span className="text-gray-500">SNOMED CT</span><span className="text-purple-300">{systemStatus.snomed.term_count.toLocaleString()} Terms</span></div>
                  <div className="flex justify-between pb-2"><span className="text-gray-500">ICD-10-CM</span><span className="text-purple-300">v{systemStatus.icd10.version}</span></div>
                </div>
              ) : <Loader2 className="w-5 h-5 animate-spin text-purple-400" />}
            </div>

            <div className="bg-black/40 border border-white/10 rounded-xl p-6 backdrop-blur-md lg:col-span-3">
              <div className="flex items-center gap-3 mb-4 border-b border-white/5 pb-3">
                <Building2 className="w-6 h-6 text-emerald-400" />
                <h3 className="text-lg font-bold text-gray-100 flex-1">Global Facility & Receiving Center Tracker</h3>
                <span className="text-xs text-gray-500 font-mono">Last State Sweep: {systemStatus?.facilities.last_state_sync || '...'}</span>
              </div>
              <div className="flex items-center justify-between text-sm">
                <p className="text-gray-400">Total Validated Hospitals/Destinations mapped for Tenant Agencies.</p>
                <div className="text-2xl font-mono text-emerald-400 font-bold">{systemStatus ? systemStatus.facilities.active_count.toLocaleString() : '...'}</div>
              </div>
            </div>
          </motion.div>
        )}

        {/* VIEW: TEMPLATE BUILDER */}
        {activeTab === 'templates' && (
          <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} className="grid grid-cols-3 gap-6 h-[600px]">
            <div className="col-span-1 bg-black/40 border border-white/10 rounded-xl flex flex-col overflow-hidden">
              <div className="p-4 border-b border-white/10 bg-white/5"><h3 className="font-bold text-yellow-500">Available NEMSIS Blocks</h3></div>
              <div className="p-4 space-y-3 overflow-y-auto flex-1">
                {['eArrest Panel', 'eVitals Grid', 'eMeds Matrix', 'eProtocol Flow', 'eNarrative Advanced'].map(block => (
                  <div key={block} className="p-3 border border-white/10 rounded bg-[#0d1017] flex justify-between items-center cursor-grab hover:border-yellow-500/50">
                    <span className="text-sm font-mono text-gray-300">{block}</span>
                    <Layers className="w-4 h-4 text-gray-600" />
                  </div>
                ))}
              </div>
            </div>
            <div className="col-span-2 border-2 border-dashed border-yellow-500/20 rounded-xl bg-black/20 flex items-center justify-center relative overflow-hidden">
              <div className="absolute inset-0 bg-[url('/img/grid.svg')] bg-center opacity-10 pointer-events-none" />
              <div className="text-center w-full max-w-sm">
                <FileJson className="w-16 h-16 text-yellow-500/20 mx-auto mb-4" />
                <h3 className="text-xl font-bold text-gray-400 mb-2">Drag NEMSIS Blocks Here</h3>
                <p className="text-sm text-gray-500">Build standard clinical forms for tenant Android Tablets visually based on the national v3.5.0 dataset layout.</p>
              </div>
            </div>
          </motion.div>
        )}

        {/* VIEW: EXPORT STATUS */}
        {activeTab === 'exports' && exportData && (
          <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} className="space-y-6">
            <div className="grid grid-cols-4 gap-4">
              <div className="bg-black/40 border border-t-yellow-500/50 rounded-xl p-6">
                <p className="text-gray-500 text-xs font-mono mb-1">Total Charts Attempted</p>
                <p className="text-3xl font-bold text-white">{exportData.total_today.toLocaleString()}</p>
              </div>
              <div className="bg-green-900/10 border border-t-green-500/50 rounded-xl p-6">
                <p className="text-gray-500 text-xs font-mono mb-1 text-green-500/70">Successful Exports</p>
                <p className="text-3xl font-bold text-green-400">{exportData.successful.toLocaleString()}</p>
              </div>
              <div className="bg-red-900/10 border border-t-red-500/50 rounded-xl p-6">
                <p className="text-gray-500 text-xs font-mono mb-1 text-red-500/70">Failed Validation</p>
                <p className="text-3xl font-bold text-red-400">{exportData.failed}</p>
              </div>
              <div className="bg-blue-900/10 border border-t-blue-500/50 rounded-xl p-6">
                <p className="text-gray-500 text-xs font-mono mb-1 text-blue-500/70">In State Queue</p>
                <p className="text-3xl font-bold text-blue-400">{exportData.in_queue}</p>
              </div>
            </div>
            
            <div className="bg-black/40 border border-white/10 rounded-xl overflow-hidden">
              <table className="w-full text-left text-sm">
                <thead className="bg-white/5 border-b border-white/10 font-mono text-xs text-gray-400">
                  <tr>
                    <th className="p-4">Tenant Agency</th>
                    <th className="p-4">Receiving Hub</th>
                    <th className="p-4">Status</th>
                    <th className="p-4">Success Rate</th>
                    <th className="p-4 text-right">Failed Charts</th>
                  </tr>
                </thead>
                <tbody>
                  {exportData.agencies.map((agency: any, i: number) => (
                    <tr key={i} className="border-b border-white/5">
                      <td className="p-4 font-bold text-gray-200">{agency.name}</td>
                      <td className="p-4 text-gray-400">State HUB: {agency.state}</td>
                      <td className="p-4">
                        {agency.status === 'Warning' 
                          ? <span className="flex items-center gap-2 text-red-400"><AlertTriangle className="w-4 h-4"/> Validation Failures</span>
                          : <span className="flex items-center gap-2 text-green-400"><CheckCircle2 className="w-4 h-4"/> Nominal</span>
                        }
                      </td>
                      <td className="p-4 font-mono">{agency.success_rate}%</td>
                      <td className="p-4 text-right text-red-400 font-mono">{agency.failed_charts > 0 ? agency.failed_charts : '-'}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </motion.div>
        )}

        {/* VIEW: AI NEMSIS ENGINE */}
        {activeTab === 'nemsis_ai' && (
          <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} className="grid grid-cols-1 lg:grid-cols-2 gap-8">
            <div className="flex flex-col gap-4">
              <h2 className="text-xl font-bold flex items-center gap-2 text-yellow-500">
                <Workflow className="w-5 h-5" /> Express Rule Generator
              </h2>
              <p className="text-sm text-gray-400">Type what NEMSIS or NERIS rule you want to enforce in natural language. The AI will translate it into a verified XPath Schema validation block.</p>
              
              <div className="relative">
                <textarea 
                  value={naturalQuery}
                  onChange={(e) => setNaturalQuery(e.target.value)}
                  placeholder="e.g., If the patient is undergoing cardiac arrest, the narrative must be at least 50 words..." 
                  className="w-full h-32 bg-[#0d1017] border border-gray-700 rounded-xl p-4 text-sm text-gray-200 focus:outline-none focus:border-yellow-500/50 resize-none font-mono"
                />
                <button 
                  onClick={handleAIExpression}
                  disabled={thinking}
                  className="absolute bottom-4 right-4 bg-yellow-600 hover:bg-yellow-500 text-black px-4 py-2 rounded-md font-bold text-xs flex items-center gap-2 transition-colors disabled:opacity-50"
                >
                  {thinking ? <><Loader2 className="w-4 h-4 animate-spin" /> compiling...</> : <><Send className="w-4 h-4"/> Generate XPath</>}
                </button>
              </div>
            </div>

            <div className="bg-[#09090b] rounded-xl border border-gray-800 shadow-2xl overflow-hidden flex flex-col">
              <div className="bg-[#18181b] border-b border-gray-800 px-4 py-3 flex items-center gap-2">
                <TerminalSquare className="w-4 h-4 text-gray-400" />
                <span className="text-xs font-mono text-gray-400">nemsis_schematron_compiler.out</span>
              </div>
              <div className="p-6 flex-1 font-mono text-sm">
                {!aiResult && !thinking && <p className="text-gray-600 italic">// Waiting for natural language input...</p>}
                {thinking && <p className="text-yellow-500 animate-pulse">// Abstracting syntax tree and matching to NEMSIS v3.5.0 dictionary...</p>}
                {aiResult && !thinking && (
                  <div className="space-y-6">
                    <div>
                      <p className="text-gray-500 text-xs mb-1">Generated XPath Target:</p>
                      <div className="bg-black/50 p-3 rounded text-blue-400 break-all">{aiResult.generated_xpath}</div>
                    </div>
                    <div>
                      <p className="text-gray-500 text-xs mb-1">Schematron Block:</p>
                      <div className="bg-black/50 p-3 rounded text-emerald-400 break-all whitespace-pre-wrap">{aiResult.schematron_rule}</div>
                    </div>
                    <div>
                      <p className="text-gray-500 text-xs mb-1">AI Explanation:</p>
                      <p className="text-gray-300 text-xs">{aiResult.human_readable}</p>
                    </div>
                  </div>
                )}
              </div>
            </div>
          </motion.div>
        )}

      </div>
    </div>
  );
}
