import os

filepath = "/workspaces/FusionEMS-Core/frontend/app/founder-command/page.tsx"

with open(filepath, "r") as f:
    content = f.read()

# 1. Add new icons to import
import_old = """  Landmark, FileDigit, DownloadCloud\n} from "lucide-react";"""
import_new = """  Landmark, FileDigit, DownloadCloud, Shield, FileText\n} from "lucide-react";"""
content = content.replace(import_old, import_new)

# 2. Insert the Vault UI right after the "Compile Quarterly Native Tax Returns</button>" div closure.
anchor = """                       <button className="w-full bg-[#FF5500] hover:bg-[#FF5500]/80 text-black text-[10px] font-bold py-3 uppercase tracking-widest transition-colors">Compile Quarterly Native Tax Returns</button>
                     </div>
                   </div>"""

injection = """                       <button className="w-full bg-[#FF5500] hover:bg-[#FF5500]/80 text-black text-[10px] font-bold py-3 uppercase tracking-widest transition-colors">Compile Quarterly Native Tax Returns</button>
                     </div>
                   </div>

                   {/* Family Tax Vault & Credits */}
                   <div className="mt-6 border border-zinc-800 bg-[#050505] p-5 shadow-[inset_0_0_40px_rgba(16,185,129,0.03)]">
                     <h4 className="flex items-center text-emerald-400 font-black uppercase tracking-widest text-xs mb-4">
                       <Shield className="mr-2 h-4 w-4" /> Secure Family Tax Vault & AI Credit Engine
                     </h4>
                     <div className="grid grid-cols-1 lg:grid-cols-5 gap-6">
                       <div className="space-y-4 lg:col-span-2">
                         <div className="text-[10px] uppercase text-zinc-500 font-bold tracking-widest">Encrypted Storage (AES-256)</div>
                         <div className="space-y-2">
                           <div className="flex justify-between items-center text-xs bg-black p-2 border border-emerald-900/30">
                             <span className="text-zinc-300 flex items-center gap-2"><FileText className="h-3 w-3 text-emerald-500"/> Wendorf_Joint_1040_2025.pdf</span>
                             <span className="text-emerald-500 text-[9px] uppercase tracking-widest">Secured</span>
                           </div>
                           <div className="flex justify-between items-center text-xs bg-black p-2 border border-emerald-900/30">
                             <span className="text-zinc-300 flex items-center gap-2"><FileText className="h-3 w-3 text-emerald-500"/> Spouse_W2_2025.pdf</span>
                             <span className="text-emerald-500 text-[9px] uppercase tracking-widest">Secured</span>
                           </div>
                           <div className="flex justify-between items-center text-xs bg-black p-2 border border-emerald-900/30">
                             <span className="text-zinc-300 flex items-center gap-2"><FileText className="h-3 w-3 text-emerald-500"/> Property_Tax_Assessment.pdf</span>
                             <span className="text-emerald-500 text-[9px] uppercase tracking-widest">Secured</span>
                           </div>
                           <button className="w-full border border-dashed border-zinc-700 bg-black text-zinc-500 hover:text-emerald-400 hover:border-emerald-500/50 p-2 text-[10px] uppercase tracking-widest transition-all">
                             + Upload Tax Document
                           </button>
                         </div>
                       </div>
                       <div className="space-y-4 lg:col-span-3">
                         <div className="text-[10px] uppercase text-zinc-500 font-bold tracking-widest flex justify-between">
                           <span>Deduction & Incentive Amplifier</span>
                           <span className="text-emerald-400 font-mono">+$14,250 Found</span>
                         </div>
                         <div className="grid grid-cols-2 gap-3">
                           <div className="p-3 border border-emerald-500/20 bg-emerald-500/5 relative overflow-hidden">
                             <div className="absolute top-0 right-0 w-1 h-full bg-emerald-500" />
                             <div className="text-[10px] text-emerald-500 font-bold uppercase tracking-widest mb-1">Home Office Apportionment</div>
                             <div className="text-lg text-white font-mono">$4,850.00</div>
                             <div className="text-[9px] text-zinc-400 mt-1">SqFt Allocation + Utility %</div>
                           </div>
                           <div className="p-3 border border-emerald-500/20 bg-emerald-500/5 relative overflow-hidden">
                             <div className="absolute top-0 right-0 w-1 h-full bg-emerald-500" />
                             <div className="text-[10px] text-emerald-500 font-bold uppercase tracking-widest mb-1">QBI Deduction (20%)</div>
                             <div className="text-lg text-white font-mono">$9,400.00</div>
                             <div className="text-[9px] text-zinc-400 mt-1">Pass-through maxed</div>
                           </div>
                         </div>
                         <button className="w-full bg-emerald-500 hover:bg-emerald-400 text-black text-[10px] font-bold py-3 uppercase tracking-widest transition-colors shadow-[0_0_15px_rgba(16,185,129,0.2)]">
                           Run Deep AI Credit Sweep (100% Legal Max)
                         </button>
                       </div>
                     </div>"""

content = content.replace(anchor, injection)

with open(filepath, "w") as f:
    f.write(content)
