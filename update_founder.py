import os

filepath = "/workspaces/FusionEMS-Core/frontend/app/founder-command/page.tsx"
with open(filepath, "r") as f:
    text = f.read()

# 1. Update imports
import_old = """  Bot, GitPullRequest, SearchCheck, Cpu, Code\n} from "lucide-react";"""
import_new = """  Bot, GitPullRequest, SearchCheck, Cpu, Code,\n  Landmark, FileDigit, DownloadCloud\n} from "lucide-react";"""
text = text.replace(import_old, import_new)

# 2. Update TabState
tab_old = 'type TabState = "overview" | "finance" | "comms" | "ai_agent";'
tab_new = 'type TabState = "overview" | "finance" | "comms" | "tax" | "ai_agent";'
text = text.replace(tab_old, tab_new)

# 3. Update nav options
nav_old = """          <button onClick={() => setActiveTab("overview")} className={navClasses("overview")}>Warp-Drive</button>
          <button onClick={() => setActiveTab("finance")} className={navClasses("finance")}>Treasury / Auth</button>
          <button onClick={() => setActiveTab("comms")} className={navClasses("comms")}>Dispatch Vectors</button>"""
nav_new = """          <button onClick={() => setActiveTab("overview")} className={navClasses("overview")}>Warp-Drive</button>
          <button onClick={() => setActiveTab("finance")} className={navClasses("finance")}>Treasury / Auth</button>
          <button onClick={() => setActiveTab("tax")} className={navClasses("tax")}>Tax & E-File</button>
          <button onClick={() => setActiveTab("comms")} className={navClasses("comms")}>Dispatch Vectors</button>"""
text = text.replace(nav_old, nav_new)

# 4. Insert section
tax_section = """
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
                             <span className="text-amber-500 font-mono flex items-center gap-2"><span className="w-1.5 h-1.5 rounded-full bg-amber-500 animate-pulse" /> DRAFT</span>
                           </div>
                         </div>
                       </div>
                       <button className="w-full border border-[#00D1FF]/30 bg-[#00D1FF]/10 hover:bg-[#00D1FF]/20 text-[#00D1FF] text-[10px] font-bold py-3 uppercase tracking-widest transition-colors">Sign & Transmit E-File payload</button>
                     </div>
                     <div className="p-4 border border-zinc-800 bg-black/50 flex flex-col justify-between">
                       <div>
                         <h4 className="flex items-center text-[#FF5500] font-black uppercase tracking-widest text-xs mb-3"><DownloadCloud className="mr-2 h-4 w-4" /> Omni-Tax Export</h4>
                         <p className="text-sm text-zinc-400 font-mono mb-4">Stripe + Office Ally reconciliation. CPA-ready export formats.</p>
                         <div className="grid grid-cols-2 gap-2 mb-6 text-center">
                           <div className="border border-zinc-800 bg-white/5 p-3 text-white text-[10px] font-bold tracking-widest hover:border-[#FF5500]/50 hover:bg-[#FF5500]/10 cursor-pointer transition-all">CSV LEDGER</div>
                           <div className="border border-zinc-800 bg-white/5 p-3 text-white text-[10px] font-bold tracking-widest hover:border-[#FF5500]/50 hover:bg-[#FF5500]/10 cursor-pointer transition-all">QBO INTUIT</div>
                           <div className="border border-zinc-800 bg-white/5 p-3 text-white text-[10px] font-bold tracking-widest hover:border-[#FF5500]/50 hover:bg-[#FF5500]/10 cursor-pointer transition-all">XERO SYNC</div>
                           <div className="border border-zinc-800 bg-white/5 p-3 text-white text-[10px] font-bold tracking-widest hover:border-[#FF5500]/50 hover:bg-[#FF5500]/10 cursor-pointer transition-all">ERP AGGREGATE</div>
                         </div>
                       </div>
                       <button className="w-full bg-[#FF5500] hover:bg-[#FF5500]/80 text-black text-[10px] font-bold py-3 uppercase tracking-widest transition-colors">Generate CPA Archive</button>
                     </div>
                   </div>
                </div>
              </motion.div>
            )}
"""

target = '{activeTab === "comms" && ('
text = text.replace(target, tax_section + "\n            " + target)

with open(filepath, "w") as f:
    f.write(text)
