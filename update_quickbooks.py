import os
filepath = "/workspaces/FusionEMS-Core/frontend/app/founder-command/page.tsx"

with open(filepath, "r") as f:
    content = f.read()

old_subtitle = "Master Control: Stripe, Lob, Telnyx, Office Ally, and Architecture."
new_subtitle = "Master Control: Stripe, Lob, Telnyx, Office Ally, Built-in Ledger, and Architecture."
content = content.replace(old_subtitle, new_subtitle)

old_omni = """                         <h4 className="flex items-center text-[#FF5500] font-black uppercase tracking-widest text-xs mb-3"><DownloadCloud className="mr-2 h-4 w-4" /> Omni-Tax Export</h4>
                         <p className="text-sm text-zinc-400 font-mono mb-4">Stripe + Office Ally reconciliation. CPA-ready export formats.</p>
                         <div className="grid grid-cols-2 gap-2 mb-6 text-center">
                           <div className="border border-zinc-800 bg-white/5 p-3 text-white text-[10px] font-bold tracking-widest hover:border-[#FF5500]/50 hover:bg-[#FF5500]/10 cursor-pointer transition-all">CSV LEDGER</div>
                           <div className="border border-zinc-800 bg-white/5 p-3 text-white text-[10px] font-bold tracking-widest hover:border-[#FF5500]/50 hover:bg-[#FF5500]/10 cursor-pointer transition-all">QBO INTUIT</div>
                           <div className="border border-zinc-800 bg-white/5 p-3 text-white text-[10px] font-bold tracking-widest hover:border-[#FF5500]/50 hover:bg-[#FF5500]/10 cursor-pointer transition-all">XERO SYNC</div>
                           <div className="border border-zinc-800 bg-white/5 p-3 text-white text-[10px] font-bold tracking-widest hover:border-[#FF5500]/50 hover:bg-[#FF5500]/10 cursor-pointer transition-all">ERP AGGREGATE</div>
                         </div>
                       </div>
                       <button className="w-full bg-[#FF5500] hover:bg-[#FF5500]/80 text-black text-[10px] font-bold py-3 uppercase tracking-widest transition-colors">Generate CPA Archive</button>"""

new_omni = """                         <h4 className="flex items-center text-[#FF5500] font-black uppercase tracking-widest text-xs mb-3"><DownloadCloud className="mr-2 h-4 w-4" /> Quantum Ledger (Native)</h4>
                         <p className="text-sm text-zinc-400 font-mono mb-4">You are your own QuickBooks. Full native general ledger, P&L, chart of accounts, and balance sheet built directly into your OS.</p>
                         <div className="grid grid-cols-2 gap-2 mb-6 text-center">
                           <div className="border border-zinc-800 bg-white/5 p-3 text-white text-[10px] font-bold tracking-widest hover:border-[#FF5500]/50 hover:bg-[#FF5500]/10 cursor-pointer transition-all flex items-center justify-center gap-2"><span className="w-1.5 h-1.5 rounded-full bg-emerald-500 animate-pulse" /> PROFIT / LOSS</div>
                           <div className="border border-zinc-800 bg-white/5 p-3 text-white text-[10px] font-bold tracking-widest hover:border-[#FF5500]/50 hover:bg-[#FF5500]/10 cursor-pointer transition-all flex items-center justify-center gap-2"><span className="w-1.5 h-1.5 rounded-full bg-emerald-500 animate-pulse" /> TX EXPENSES</div>
                           <div className="border border-zinc-800 bg-white/5 p-3 text-white text-[10px] font-bold tracking-widest hover:border-[#FF5500]/50 hover:bg-[#FF5500]/10 cursor-pointer transition-all">BALANCE SHEET</div>
                           <div className="border border-zinc-800 bg-white/5 p-3 text-[var(--color-brand-orange)] text-[10px] font-bold tracking-widest hover:border-[#FF5500]/50 hover:bg-[#FF5500]/10 cursor-pointer transition-all">TAX ESTIMATOR</div>
                         </div>
                       </div>
                       <button className="w-full bg-[#FF5500] hover:bg-[#FF5500]/80 text-black text-[10px] font-bold py-3 uppercase tracking-widest transition-colors">Compile Quarterly Native Tax Returns</button>"""

content = content.replace(old_omni, new_omni)

with open(filepath, "w") as f:
    f.write(content)

