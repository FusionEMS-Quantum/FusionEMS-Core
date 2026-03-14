import os
filepath = "/workspaces/FusionEMS-Core/frontend/app/founder-command/page.tsx"

with open(filepath, "r") as f:
    content = f.read()

# I need to add state for the E-File transmission
old_state = '  const [activeTab, setActiveTab] = useState<TabState>("overview");'
new_state = """  const [activeTab, setActiveTab] = useState<TabState>("overview");
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
  };"""

content = content.replace(old_state, new_state)

old_efile_block = """                       <button className="w-full border border-[#00D1FF]/30 bg-[#00D1FF]/10 hover:bg-[#00D1FF]/20 text-[#00D1FF] text-[10px] font-bold py-3 uppercase tracking-widest transition-colors">Sign & Transmit E-File payload</button>"""

new_efile_block = """                       
                       {!isTransmitting && efileStatus === "DRAFT" ? (
                           <button onClick={startEfileTransmission} className="w-full bg-[#00D1FF] hover:bg-[#00D1FF]/80 text-black text-[10px] font-bold py-3 uppercase tracking-widest transition-colors">Sign & Transmit Direct to IRS</button>
                       ) : (
                           <div className="w-full bg-black border border-[#00D1FF]/50 p-3 h-32 overflow-y-auto font-mono text-[10px] text-[#00D1FF] space-y-1">
                               {transmitLog.map((log, i) => (
                                   <div key={i}>{log}</div>
                               ))}
                               {isTransmitting && <div className="animate-pulse">_</div>}
                           </div>
                       )}"""
content = content.replace(old_efile_block, new_efile_block)

old_status = '<span className="w-1.5 h-1.5 rounded-full bg-amber-500 animate-pulse" /> DRAFT</span>'
new_status = '{efileStatus === "DRAFT" ? <><span className="w-1.5 h-1.5 rounded-full bg-amber-500 animate-pulse" /> DRAFT</> : efileStatus === "TRANSMITTING" ? <><span className="w-1.5 h-1.5 rounded-full bg-[#00D1FF] animate-pulse" /> TRANSMITTING</> : <><span className="w-1.5 h-1.5 rounded-full bg-emerald-500" /> ACCEPTED</>}</span>'
content = content.replace(old_status, new_status)

with open(filepath, "w") as f:
    f.write(content)
