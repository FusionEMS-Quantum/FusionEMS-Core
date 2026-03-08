"use client";

import React, { useEffect, useState, useRef } from "react";
import { motion, AnimatePresence } from "framer-motion";
import {
  UploadCloud,
  ShieldAlert,
  Zap,
  DollarSign,
  Fingerprint,
  FileText,
  TerminalSquare,
  Network,
} from "lucide-react";
import { getQuantumStrategies, uploadQuantumCSV, getQuantumVaultDocuments } from "@/services/api";

type TrackingEvent = {
  step: string;
  status: string;
  refund_est?: number | string;
};

export default function QuantumTaxShieldPage() {
  const [strategies, setStrategies] = useState<any[]>([]);
  const [vaultDocs, setVaultDocs] = useState<any[]>([]);
  const [activeTab, setActiveTab] = useState<'dashboard' | 'vault'>('dashboard');
  const [selectedDocId, setSelectedDocId] = useState<string | null>(null);

  const [loading, setLoading] = useState(true);
  const [uploading, setUploading] = useState(false);
  const [csvStatus, setCsvStatus] = useState<string | null>(null);
  
  // Realtime tracker state
  const [efileLog, setEfileLog] = useState<TrackingEvent[]>([]);
  const [isTracking, setIsTracking] = useState(false);
  
  // Drag drop ref
  const fileInputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    async function load() {
      try {
        const [stratData, vaultData] = await Promise.all([
          getQuantumStrategies(),
          getQuantumVaultDocuments()
        ]);
        setStrategies(stratData.strategies || []);
        setVaultDocs(vaultData.documents || []);
      } catch (e) {
        console.error("Failed to load quantum strategies", e);
      } finally {
        setLoading(false);
      }
    }
    load();
  }, []);

  const startRealtimeTracking = () => {
    setIsTracking(true);
    setEfileLog([]);
    // Setup SSE connection
    const eventSource = new EventSource(
      `${process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000"}/api/quantum-founder/efile/realtime-status`
    );

    eventSource.onmessage = (event) => {
      const parsedData = JSON.parse(event.data);
      setEfileLog(prev => [...prev, parsedData]);
      
      // Auto-close when finished
      if (parsedData.status === "Success" && parsedData.step.includes("Wisconsin")) {
        setTimeout(() => eventSource.close(), 1000);
      }
    };

    eventSource.onerror = () => {
      eventSource.close();
      setIsTracking(false);
    };
  };

  const handleCsvUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;
    
    setUploading(true);
    try {
      const result = await uploadQuantumCSV(file);
      setCsvStatus(result.message);
    } catch (err) {
      setCsvStatus("Error analyzing CSV against Sec 195.");
    } finally {
      setTimeout(() => setUploading(false), 2000);
    }
  };

  return (
    <div className="min-h-screen bg-black text-white selection:bg-cyan-500 selection:text-black">
      {/* Background Quantum Grid */}
      <div className="fixed inset-0 z-0 bg-[radial-gradient(ellipse_at_center,_var(--tw-gradient-stops))] from-cyan-900/20 via-black to-black opacity-80 pointer-events-none" />
      <div className="fixed inset-0 z-0 bg-[url('/img/grid.svg')] bg-center [mask-image:linear-gradient(180deg,white,rgba(255,255,255,0))]" />

      <div className="relative z-10 p-6 md:p-10 max-w-7xl mx-auto space-y-10">
        
        {/* Header Section */}
        <motion.div
          initial={{ opacity: 0, y: -20 }}
          animate={{ opacity: 1, y: 0 }}
          className="flex items-center justify-between border-b border-white/10 pb-6"
        >
          <div>
            <h1 className="text-4xl lg:text-5xl font-extrabold tracking-tighter text-transparent bg-clip-text bg-gradient-to-r from-cyan-400 to-indigo-600 drop-shadow-[0_0_15px_rgba(0,0,0,0.6)] flex items-center gap-4">
              <Network className="w-10 h-10 text-cyan-400" />
              Quantum Founder Shield
            </h1>
            <p className="text-zinc-500 mt-2 text-lg">
              Pre-Revenue State • Sec 195 Startup Capitalizer Active
            </p>
          </div>
          <div className="flex gap-4">
            <div className="px-4 py-2  bg-green-500/10 border border-green-500/30 flex items-center gap-2">
              <div className="w-2 h-2  bg-green-500 animate-pulse" />
              <span className="text-green-400 font-mono text-sm">IRS Connection Secure</span>
            </div>
            <div className="px-4 py-2  bg-indigo-500/10 border border-indigo-500/30 flex items-center gap-2">
              <Fingerprint className="w-4 h-4 text-indigo-400" />
              <span className="text-indigo-400 font-mono text-sm">Commingling Shield Active</span>
            </div>
          </div>
        </motion.div>

          {/* Tab Navigation */}
          <div className="flex border-b border-gray-800">
            <button
              onClick={() => setActiveTab('dashboard')}
              className={`px-6 py-3 font-semibold text-lg transition-colors border-b-2 ${
                activeTab === 'dashboard' ? 'border-cyan-400 text-cyan-400' : 'border-transparent text-zinc-500 hover:text-gray-300'
              }`}
            >
              Command Center
            </button>
            <button
              onClick={() => setActiveTab('vault')}
              className={`px-6 py-3 font-semibold text-lg transition-colors border-b-2 ${
                activeTab === 'vault' ? 'border-indigo-400 text-indigo-400' : 'border-transparent text-zinc-500 hover:text-gray-300'
              }`}
            >
              Document Vault
            </button>
          </div>

          {activeTab === 'dashboard' ? (
            <>
              {/* Top Grid: Capitalizer & Vault */}
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
          
          {/* Section 195 Startup Pool (Interactive) */}
          <motion.div
            initial={{ opacity: 0, x: -20 }}
            animate={{ opacity: 1, x: 0 }}
            transition={{ delay: 0.1 }}
            className=" border border-white/10 bg-black/40 backdrop-blur-xl p-8 relative overflow-hidden group"
          >
            <div className="absolute top-0 right-0 p-4 opacity-10 group-hover:opacity-20 transition-opacity">
              <Zap className="w-40 h-40 text-cyan-500" />
            </div>
            <h2 className="text-2xl font-bold text-white mb-2 flex items-center gap-2">
              Sec. 195 Capitalization Pool
            </h2>
            <p className="text-zinc-500 text-sm mb-8">Amortized pre-revenue startup deductions waiting for Stripe activation trigger.</p>
            
            <div className="flex items-end gap-2 text-6xl font-mono text-cyan-400 font-bold tracking-tight">
              $<span className="counter-tick">4,192</span><span className="text-3xl text-cyan-700">.45</span>
            </div>
            <div className="w-full bg-zinc-900  h-3 mt-6 border border-gray-800">
              <div className="bg-gradient-to-r from-cyan-600 to-cyan-400 h-3 " style={{ width: '83%' }}></div>
            </div>
            <p className="text-xs text-zinc-500 mt-2 text-right">83% of $5,000 Instant Deduction Threshold</p>
          </motion.div>

          {/* S3 Vault Upload & Commingling Shield */}
          <motion.div
            initial={{ opacity: 0, x: 20 }}
            animate={{ opacity: 1, x: 0 }}
            transition={{ delay: 0.2 }}
            className=" border border-indigo-500/20 bg-indigo-900/10 backdrop-blur-xl p-8 flex flex-col justify-between"
          >
            <div>
              <h2 className="text-2xl font-bold text-white mb-2 flex items-center gap-2">
                <ShieldAlert className="w-6 h-6 text-indigo-400" />
                The Commingling Shield
              </h2>
              <p className="text-indigo-200/70 text-sm mb-4">
                Drag and drop personal Chase/Amex CSVs here. The Quantum Engine filters personal groceries and securely routes business expenses to Owner Capital Eq.
              </p>
            </div>
            
            <div 
              onClick={() => fileInputRef.current?.click()}
              className="border-2 border-dashed border-indigo-500/40 hover:border-cyan-400/60 transition-colors  p-8 flex flex-col items-center justify-center cursor-pointer bg-black/50 group"
            >
              <input type="file" className="hidden" ref={fileInputRef} accept=".csv" onChange={handleCsvUpload} />
              {uploading ? (
                <div className="animate-spin  h-10 w-10 border-b-2 border-cyan-400" />
              ) : (
                <>
                  <UploadCloud className="w-12 h-12 text-indigo-400 group-hover:text-cyan-400 transition-colors mb-3" />
                  <p className="font-mono text-sm text-gray-300">Drop Bank CSV / Receipts</p>
                </>
              )}
            </div>
            {csvStatus && (
              <p className="mt-4 text-sm text-cyan-400 font-mono text-center animate-pulse">{csvStatus}</p>
            )}
          </motion.div>

        </div>

        {/* Domination Strategies */}
        <motion.div
           initial={{ opacity: 0, y: 20 }}
           animate={{ opacity: 1, y: 0 }}
           transition={{ delay: 0.3 }}
           className="mt-12"
        >
          <h3 className="text-3xl font-bold mb-6 flex items-center gap-3">
             <DollarSign className="w-8 h-8 text-green-400" /> 
             Domination Level Tax Loopholes
          </h3>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            {loading ? (
              <div className="col-span-2 h-40 border border-white/5  animate-pulse bg-zinc-900/50" />
            ) : (
              strategies.map((strat, i) => (
                <div key={i} className="relative group p-1  bg-gradient-to-b from-white/10 to-transparent hover:from-cyan-500/30 transition-all duration-500">
                  <div className="h-full bg-black/80 backdrop-blur-md  p-6 border border-white/5 flex flex-col justify-between">
                    <div>
                      <div className="flex justify-between items-start mb-4">
                        <h4 className="text-xl font-semibold text-white/90">{strat.name}</h4>
                        {strat.savings_estimate && typeof strat.savings_estimate === 'number' && (
                          <span className="bg-green-500/20 text-green-400 px-3 py-1  text-sm font-mono border border-green-500/30">
                            Est. ${strat.savings_estimate.toLocaleString()}
                          </span>
                        )}
                      </div>
                      <p className="text-zinc-500 text-sm leading-relaxed mb-6">{strat.description}</p>
                    </div>
                    <div>
                      <div className="border-t border-white/10 pt-4">
                        <p className="text-xs uppercase tracking-wider text-cyan-500 mb-2 font-semibold">Implementation Protocol</p>
                        <ul className="space-y-2">
                          {strat.impl_steps?.map((step: string, j: number) => (
                            <li key={j} className="flex gap-2 text-sm text-gray-300 items-start">
                              <span className="text-cyan-600 font-bold mt-0.5">›</span> {step}
                            </li>
                          ))}
                        </ul>
                      </div>
                    </div>
                  </div>
                </div>
              ))
            )}
          </div>
        </motion.div>

        {/* Real-time E-File Tracker Terminal */}
        <motion.div
           initial={{ opacity: 0, y: 20 }}
           animate={{ opacity: 1, y: 0 }}
           transition={{ delay: 0.4 }}
           className="mt-12 bg-[#09090b]  border border-gray-800 shadow-[0_0_15px_rgba(0,0,0,0.6)] overflow-hidden"
        >
          <div className="bg-[#18181b] border-b border-gray-800 px-4 py-3 flex justify-between items-center">
            <div className="flex items-center gap-2">
              <TerminalSquare className="w-5 h-5 text-zinc-500" />
              <h3 className="font-mono text-sm text-gray-300">quantum_efile_socket.exe</h3>
            </div>
            <button 
              onClick={startRealtimeTracking}
              disabled={isTracking}
              className="bg-cyan-600 hover:bg-cyan-500 text-black px-4 py-1.5  text-xs font-bold font-mono transition-colors disabled:opacity-50"
            >
              {isTracking ? "TRANSMITTING..." : "INITIATE WISCONSIN E-FILE"}
            </button>
          </div>
          <div className="p-6 h-64 overflow-y-auto font-mono text-sm space-y-2 relative">
            <AnimatePresence>
              {!isTracking && efileLog.length === 0 && (
                <motion.div 
                  initial={{ opacity: 0 }}
                  animate={{ opacity: 1 }}
                  className="text-gray-600 absolute inset-0 flex items-center justify-center pointer-events-none"
                >
                  [ STANDBY: AWAITING E-FILE TRANSMISSION ]
                </motion.div>
              )}
              {efileLog.map((log, idx) => (
                <motion.div
                  key={idx}
                  initial={{ opacity: 0, x: -10 }}
                  animate={{ opacity: 1, x: 0 }}
                  className="flex items-start gap-4"
                >
                  <span className="text-zinc-500">[{new Date().toLocaleTimeString()}]</span>
                  <span className={log.status === "In Progress" ? "text-yellow-400" : log.status.includes("Success") ? "text-green-400" : "text-cyan-300"}>
                    {log.step.padEnd(30, ' ')} 
                    {log.status === "In Progress" && <span className="animate-pulse">...</span>}
                    {log.status !== "In Progress" && `[${log.status}]`}
                  </span>
                  {log.refund_est !== undefined && (
                     <span className="text-green-300 ml-auto bg-green-900/30 px-2 ">
                       WI Liability / Refund: {log.refund_est === 0 ? "$0.00" : log.refund_est}
                     </span>
                  )}
                </motion.div>
              ))}
            </AnimatePresence>
            {isTracking && (
              <div className="w-2 h-4 bg-cyan-500 animate-pulse mt-2 inline-block"></div>
            )}
          </div>
        </motion.div>
        
        </>
        ) : (
          /* Document Vault View */
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            className="mt-8 grid grid-cols-1 lg:grid-cols-3 gap-8"
          >
            {/* Sidebar list of documents */}
            <div className="col-span-1 border border-indigo-500/20 bg-black/40  p-4 overflow-y-auto max-h-[600px]">
              <h3 className="text-xl font-bold text-indigo-400 mb-4 border-b border-indigo-500/20 pb-2">Generated Resolutions</h3>
              {vaultDocs.length === 0 ? (
                <p className="text-zinc-500 text-sm">No documents generated yet.</p>
              ) : (
                <div className="space-y-2">
                  {vaultDocs.map((doc) => (
                    <div 
                      key={doc.id}
                      onClick={() => setSelectedDocId(doc.id)}
                      className={`p-3  cursor-pointer transition-colors border ${
                        selectedDocId === doc.id 
                          ? 'bg-indigo-900/40 border-indigo-500' 
                          : 'bg-black/20 border-white/5 hover:border-white/20'
                      }`}
                    >
                      <p className="font-semibold text-white text-sm">{doc.doc_type.replace(/_/g, ' ').toUpperCase()}</p>
                      <p className="text-xs text-zinc-500 font-mono mt-1">{new Date(doc.created_at).toLocaleDateString()}</p>
                      {doc.signature_status === "EXECUTED" && (
                        <span className="inline-block mt-2 px-2 py-0.5 bg-green-500/10 border border-green-500/30 text-green-400 text-xs ">Signed</span>
                      )}
                    </div>
                  ))}
                </div>
              )}
            </div>

            {/* Document Viewer Frame */}
            <div className="col-span-1 lg:col-span-2 bg-zinc-950  shadow-[0_0_15px_rgba(0,0,0,0.6)] overflow-hidden min-h-[600px]">
              {selectedDocId ? (
                <iframe 
                  src={`${process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000"}/api/quantum-founder/vault/render/${selectedDocId}`} 
                  className="w-full h-full border-0"
                  title="Document Viewer"
                />
              ) : (
                <div className="w-full h-full flex flex-col items-center justify-center text-zinc-500 bg-[#050505]">
                  <FileText className="w-16 h-16 text-gray-300 mb-4" />
                  <p>Select a document to view.</p>
                </div>
              )}
            </div>
          </motion.div>
        )}

      </div>
    </div>
  );
}
