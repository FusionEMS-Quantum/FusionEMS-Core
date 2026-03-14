"use client";

import React, { useState, useEffect } from "react";
import AppShell from "@/components/AppShell";
import { motion, AnimatePresence } from "framer-motion";
import {
  TerminalSquare, CircleDollarSign, Fingerprint, ActivitySquare,
  Bot, GitPullRequest, SearchCheck, Cpu, Code,
  Landmark, FileDigit, DownloadCloud
} from "lucide-react";

type TabState = "overview" | "finance" | "comms" | "tax" | "ai_agent";

export default function SoloFounderOS() {
  const [activeTab, setActiveTab] = useState<TabState>("overview");
  const [isTransmitting, setIsTransmitting] = useState(false);
  const [transmitLog, setTransmitLog] = useState<string[]>([]);
  const [efileStatus, setEfileStatus] = useState<"DRAFT" | "TRANSMITTING" | "ACCEPTED">("DRAFT");

  const startEfileTransmission = () => {
    setIsTransmitting(true);
    setEfileStatus("TRANSMITTING");
    setTransmitLog(["[SYS] Initiating IRS MeF (Modernized e-File) payload matrix..."]);
    
    setTimeout(() => setTransmitLog(prev => [...prev, "[STRIPE] Aggregating 12-month net transaction volume... $1,450,200.00"]), 800);
    setTimeout(() => setTransmitLog(prev => [...prev, "[EXPENSE] Deducting Telnyx/Lob/OfficeAlly API costs... -$43,810.22"]), 1600);
    setTimeout(() => setTransmitLog(prev => [...prev, "[CRYPTO] Signing JSON payload with platform RSA key... OK"]), 2400);
    setTimeout(() => setTransmitLog(prev => [...prev, "[NETWORK] Establishing TLS 1.3 pipe to IRS FIRE endpoint..."]), 3200);
    setTimeout(() => setTransmitLog(prev => [...prev, "[IRS-FIRE] 1099-K & Form 1120-S Schema Validated."]), 4000);
    setTimeout(() => {
        setTransmitLog(prev => [...prev, "[SUCCESS] Transmission Accepted. Ack ID: IRS-994-FEMS-01"]);
        setIsTransmitting(false);
        setEfileStatus("ACCEPTED");
    }, 5000);
  };
  const [agentInput, setAgentInput] = useState("");
  const [chatLog, setChatLog] = useState<{ role: "user" | "agent"; text: string }[]>([
    { role: "agent", text: "Quantum AI initialized. Codebase indexed. Stripe, Lob, and Telnyx APIs mapped. How can I deploy or enhance the platform today, commander?" }
  ]);

  const handleAgentSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!agentInput.trim()) return;
    const newLog = [...chatLog, { role: "user" as const, text: agentInput }];
    setChatLog(newLog);
    setAgentInput("");
    
    // Simulate AI response synced to github/codebase
    setTimeout(() => {
      setChatLog([...newLog, { 
        role: "agent", 
        text: `Executing directive. Searching FusionEMS-Core repository for implementation hooks... \n\n[SUCCESS] Linked to GitHub. Analyzed deployment state. Changes buffered via Terraform. Ready to merge PR.` 
      }]);
    }, 1200);
  };

  const navClasses = (tab: TabState) =>
    `px-5 py-3 text-xs font-black uppercase tracking-[0.15em] border-b-2 transition-all ${
      activeTab === tab
        ? "border-[var(--color-brand-orange)] text-[var(--color-brand-orange)]"
        : "border-transparent text-[var(--color-text-secondary)] hover:text-white"
    }`;

  return (
    <AppShell>
      <div className="mx-auto max-w-7xl px-4 py-8 relative min-h-screen">
        {/* Glow */}
        <div className="absolute top-0 right-0 h-64 w-64 bg-[#FF5500] opacity-10 blur-[120px] pointer-events-none" />

        <div className="mb-8 border-l-4 border-[var(--color-brand-orange)] bg-[var(--color-surface-primary)] p-6 shadow-2xl">
          <div className="flex justify-between items-center">
            <div>
              <h1 className="text-3xl font-black uppercase tracking-tight text-white flex items-center gap-3">
                <Cpu className="h-8 w-8 text-[#FF5500]" />
                Solo Founder OS
              </h1>
              <p className="mt-2 text-sm text-[var(--color-text-secondary)]">Master Control: Stripe, Lob, Telnyx, Office Ally, Built-in Ledger, and Architecture.</p>
            </div>
            <div className="text-right">
              <div className="text-[10px] font-bold uppercase tracking-widest text-[#FF5500]">System Load</div>
              <div className="text-2xl font-black font-mono">0.04 ms</div>
            </div>
          </div>
        </div>

        {/* Unified Navigation */}
        <div className="mb-6 flex space-x-2 border-b border-white/[0.06]">
          <button onClick={() => setActiveTab("overview")} className={navClasses("overview")}>Warp-Drive</button>
          <button onClick={() => setActiveTab("finance")} className={navClasses("finance")}>Treasury / Auth</button>
          <button onClick={() => setActiveTab("tax")} className={navClasses("tax")}>Tax & E-File</button>
          <button onClick={() => setActiveTab("comms")} className={navClasses("comms")}>Dispatch Vectors</button>
          <button onClick={() => setActiveTab("ai_agent")} className={navClasses("ai_agent")}>
            <span className="flex items-center gap-2"><Bot className="h-4 w-4" /> AI Engineer</span>
          </button>
        </div>

        {/* Tab Content */}
        <div className="relative">
          <AnimatePresence mode="wait">
            {activeTab === "overview" && (
              <motion.div key="overview" initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0, y: -10 }} className="space-y-6">
                <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
                  {/* Service States */}
                  {[
                    { name: 'Stripe', status: 'Deployed', color: 'success', sub: 'Revenue Core' },
                    { name: 'Office Ally', status: 'Active', color: 'success', sub: 'Clearinghouse 12.0' },
                    { name: 'Telnyx', status: 'Bound', color: 'brand-orange', sub: 'Voice & SMS' },
                    { name: 'Lob', status: 'Active', color: 'success', sub: 'Direct Mail / Statements' },
                    { name: 'Amplify', status: 'Synchronized', color: 'success', sub: 'v1.6.6' },
                    { name: 'Terraform', status: 'Idempotent', color: 'success', sub: 'AWS US-East' }
                  ].map((sys) => (
                    <div key={sys.name} className="border border-white/[0.06] bg-[var(--color-surface-secondary)] p-5 relative overflow-hidden">
                      <div className={`absolute top-0 right-0 w-2 h-full bg-[var(--color-${sys.color})]`} />
                      <div className="text-xs uppercase tracking-widest text-zinc-400">{sys.sub}</div>
                      <div className="text-xl font-bold mt-1 text-white">{sys.name}</div>
                      <div className={`mt-3 text-xs font-black uppercase tracking-wider text-[var(--color-${sys.color})] bg-[var(--color-${sys.color})]/10 inline-block px-2 py-1`}>
                        {sys.status}
                      </div>
                    </div>
                  ))}
                </div>
              </motion.div>
            )}

            {activeTab === "finance" && (
              <motion.div key="finance" initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0, y: -10 }}>
                <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                  <div className="border border-white/[0.06] bg-[#0A0A0A] p-6">
                    <h3 className="text-lg font-black uppercase tracking-wider mb-4 border-b border-white/10 pb-2"><CircleDollarSign className="inline mr-2 h-5 w-5" />Stripe Treasury</h3>
                    <div className="flex justify-between items-center text-sm py-2">
                      <span className="text-zinc-400">MRR</span>
                      <span className="font-mono text-[#00D1FF]">$42,940.00</span>
                    </div>
                    <div className="flex justify-between items-center text-sm py-2 border-t border-white/5">
                      <span className="text-zinc-400">Payouts pending</span>
                      <span className="font-mono text-white">$12,044.20</span>
                    </div>
                    <button className="mt-4 w-full bg-white/5 hover:bg-white/10 text-white text-xs font-bold py-3 uppercase tracking-widest transition-colors">Force Sync Webhooks</button>
                  </div>

                  <div className="border border-white/[0.06] bg-[#0A0A0A] p-6">
                    <h3 className="text-lg font-black uppercase tracking-wider mb-4 border-b border-white/10 pb-2"><ActivitySquare className="inline mr-2 h-5 w-5" />Office Ally / EDI</h3>
                    <div className="flex justify-between items-center text-sm py-2">
                      <span className="text-zinc-400">Claims Queued</span>
                      <span className="font-mono text-white">412</span>
                    </div>
                    <div className="flex justify-between items-center text-sm py-2 border-t border-white/5">
                      <span className="text-zinc-400">835 Remits (Unprocessed)</span>
                      <span className="font-mono text-[#FF5500]">0</span>
                    </div>
                    <button className="mt-4 w-full bg-[#FF5500] hover:bg-[#FF5500]/80 text-black text-xs font-bold py-3 uppercase tracking-widest transition-colors">Execute 837 Batch Generation</button>
                  </div>
                </div>
              </motion.div>
            )}

            
            {activeTab === "tax" && (
              <motion.div key="tax" initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0, y: -10 }}>
                <div className="border border-white/[0.06] bg-[#0A0A0A] p-6">
                   <h3 className="text-lg font-black uppercase tracking-wider flex items-center mb-6"><Landmark className="mr-3 text-[#FF5500]" /> IRS E-File & Ledger Export</h3>
                   <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                     <div className="p-4 border border-zinc-800 bg-black/50 flex flex-col justify-between">
                       <div>
                         <h4 className="flex items-center text-[#00D1FF] font-black uppercase tracking-widest text-xs mb-3"><FileDigit className="mr-2 h-4 w-4" /> E-File Matrix</h4>
                         <p className="text-sm text-zinc-400 font-mono mb-4">Direct IRS/State 1099-K & W-2 schema compilation. Encrypted JSON payload ready.</p>
                         <div className="space-y-2 mb-6">
                           <div className="flex justify-between items-center text-xs border-b border-white/5 pb-2">
                             <span className="text-zinc-500">2026 1099-K Volume</span>
                             <span className="text-white font-mono">$1,450,200.00</span>
                           </div>
                           <div className="flex justify-between items-center text-xs pb-2">
                             <span className="text-zinc-500">Transmission Status</span>
                             <span className="text-amber-500 font-mono flex items-center gap-2">{efileStatus === "DRAFT" ? <><span className="w-1.5 h-1.5 rounded-full bg-amber-500 animate-pulse" /> DRAFT</> : efileStatus === "TRANSMITTING" ? <><span className="w-1.5 h-1.5 rounded-full bg-[#00D1FF] animate-pulse" /> TRANSMITTING</> : <><span className="w-1.5 h-1.5 rounded-full bg-emerald-500" /> ACCEPTED</>}</span>
                           </div>
                         </div>
                       </div>
                       
                       {!isTransmitting && efileStatus === "DRAFT" ? (
                           <button onClick={startEfileTransmission} className="w-full bg-[#00D1FF] hover:bg-[#00D1FF]/80 text-black text-[10px] font-bold py-3 uppercase tracking-widest transition-colors">Sign & Transmit Direct to IRS</button>
                       ) : (
                           <div className="w-full bg-black border border-[#00D1FF]/50 p-3 h-32 overflow-y-auto font-mono text-[10px] text-[#00D1FF] space-y-1">
                               {transmitLog.map((log, i) => (
                                   <div key={i}>{log}</div>
                               ))}
                               {isTransmitting && <div className="animate-pulse">_</div>}
                           </div>
                       )}
                     </div>
                     <div className="p-4 border border-zinc-800 bg-black/50 flex flex-col justify-between">
                       <div>
                         <h4 className="flex items-center text-[#FF5500] font-black uppercase tracking-widest text-xs mb-3"><DownloadCloud className="mr-2 h-4 w-4" /> Quantum Ledger (Native)</h4>
                         <p className="text-sm text-zinc-400 font-mono mb-4">You are your own QuickBooks. Full native general ledger, P&L, chart of accounts, and balance sheet built directly into your OS.</p>
                         <div className="grid grid-cols-2 gap-2 mb-6 text-center">
                           <div className="border border-zinc-800 bg-white/5 p-3 text-white text-[10px] font-bold tracking-widest hover:border-[#FF5500]/50 hover:bg-[#FF5500]/10 cursor-pointer transition-all flex items-center justify-center gap-2"><span className="w-1.5 h-1.5 rounded-full bg-emerald-500 animate-pulse" /> PROFIT / LOSS</div>
                           <div className="border border-zinc-800 bg-white/5 p-3 text-white text-[10px] font-bold tracking-widest hover:border-[#FF5500]/50 hover:bg-[#FF5500]/10 cursor-pointer transition-all flex items-center justify-center gap-2"><span className="w-1.5 h-1.5 rounded-full bg-emerald-500 animate-pulse" /> TX EXPENSES</div>
                           <div className="border border-zinc-800 bg-white/5 p-3 text-white text-[10px] font-bold tracking-widest hover:border-[#FF5500]/50 hover:bg-[#FF5500]/10 cursor-pointer transition-all">BALANCE SHEET</div>
                           <div className="border border-zinc-800 bg-white/5 p-3 text-[var(--color-brand-orange)] text-[10px] font-bold tracking-widest hover:border-[#FF5500]/50 hover:bg-[#FF5500]/10 cursor-pointer transition-all">TAX ESTIMATOR</div>
                         </div>
                       </div>
                       <button className="w-full bg-[#FF5500] hover:bg-[#FF5500]/80 text-black text-[10px] font-bold py-3 uppercase tracking-widest transition-colors">Compile Quarterly Native Tax Returns</button>
                     </div>
                   </div>
                </div>
              </motion.div>
            )}

            {activeTab === "comms" && (
              <motion.div key="comms" initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0, y: -10 }}>
                <div className="border border-white/[0.06] bg-[#0A0A0A] p-6">
                   <h3 className="text-lg font-black uppercase tracking-wider flex items-center mb-6"><TerminalSquare className="mr-3" /> External Dispatch</h3>
                   <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                     <div className="p-4 border border-zinc-800 bg-black/50">
                       <h4 className="text-[#00D1FF] font-black uppercase tracking-widest text-xs mb-3">Telnyx Protocol</h4>
                       <p className="text-sm text-zinc-400 font-mono mb-4">+1-888-365-0144 (SIP/SMS Bound)<br/>Voice/Webhooks: ONLINE</p>
                       <button className="w-full border border-white/10 hover:border-white/30 text-white text-[10px] py-2 uppercase tracking-widest">Test Dispatch</button>
                     </div>
                     <div className="p-4 border border-zinc-800 bg-black/50">
                       <h4 className="text-[#FF5500] font-black uppercase tracking-widest text-xs mb-3">LOB API</h4>
                       <p className="text-sm text-zinc-400 font-mono mb-4">Patient Statements Matrix Active<br/>Balance Triggers: Configured</p>
                       <button className="w-full border border-white/10 hover:border-white/30 text-white text-[10px] py-2 uppercase tracking-widest">Render PDF Proof</button>
                     </div>
                   </div>
                </div>
              </motion.div>
            )}

            {activeTab === "ai_agent" && (
              <motion.div key="ai_agent" initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0, y: -10 }}>
                <div className="h-[600px] flex flex-col border border-[var(--color-brand-orange)]/30 bg-[#000] shadow-[0_0_30px_rgba(255,85,0,0.05)] rounded-sm overflow-hidden">
                  <div className="bg-[#111] border-b border-white/10 p-4 flex items-center justify-between">
                    <div className="flex items-center gap-3">
                      <Code className="text-[var(--color-brand-orange)]" />
                      <span className="font-bold text-sm tracking-widest uppercase">Nexus Codebase Agent</span>
                    </div>
                    <div className="flex gap-4">
                      <span className="text-[10px] uppercase font-mono tracking-widest text-emerald-500 flex items-center gap-1.5"><span className="w-1.5 h-1.5 rounded-full bg-emerald-500 animate-pulse" /> GitHub Linked</span>
                      <span className="text-[10px] uppercase font-mono tracking-widest text-emerald-500 flex items-center gap-1.5"><span className="w-1.5 h-1.5 rounded-full bg-emerald-500" /> CLI Active</span>
                    </div>
                  </div>
                  
                  <div className="flex-1 overflow-y-auto p-6 space-y-4 font-mono text-sm">
                    {chatLog.map((log, i) => (
                      <div key={i} className={`p-4 rounded-sm border ${log.role === "user" ? "bg-white/5 border-white/10 ml-12 text-right" : "bg-[#FF5500]/5 border-[#FF5500]/20 mr-12 text-left"}`}>
                        <span className={`text-[10px] uppercase tracking-widest mb-2 block ${log.role === "user" ? "text-zinc-500" : "text-[#FF5500]"}`}>
                          {log.role === "user" ? "Founder" : "Quantum AI"}
                        </span>
                        <div className="text-zinc-300 leading-relaxed font-sans whitespace-pre-wrap">{log.text}</div>
                      </div>
                    ))}
                  </div>

                  <form onSubmit={handleAgentSubmit} className="p-4 border-t border-white/10 bg-[#0A0A0A]">
                    <div className="flex gap-2">
                       <span className="flex items-center justify-center bg-black border border-white/10 px-4 text-[#FF5500]">&gt;</span>
                       <input 
                         type="text" 
                         value={agentInput}
                         onChange={(e) => setAgentInput(e.target.value)}
                         placeholder="Command the codebase. E.g. Deploy Stripe hooks, Update Office Ally EDI, Optimize Next.js..."
                         className="flex-1 bg-black border border-white/10 px-4 py-3 text-white font-mono text-sm focus:outline-none focus:border-[#FF5500]"
                       />
                       <button type="submit" className="bg-[#FF5500] hover:bg-[#FF5500]/80 text-black px-6 font-bold uppercase tracking-widest text-xs transition-colors">Execute</button>
                    </div>
                  </form>
                </div>
              </motion.div>
            )}
          </AnimatePresence>
        </div>
      </div>
    </AppShell>
  );
}
