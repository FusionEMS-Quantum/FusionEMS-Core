"use client";

import React, { useState } from "react";
import Link from "next/link";
import { 
  Activity, Clock, FileText, Syringe, Zap, User, 
  MapPin, CheckCircle, ChevronLeft, 
  ShieldAlert, Radio, Save, Database, Stethoscope
} from "lucide-react";

export default function EpicrDashboard() {
  const [activeTab, setActiveTab] = useState("narrative");

  return (
    <div className="min-h-screen bg-[#060608] text-gray-200 font-sans selection:bg-[#FF4D00]/20 overflow-hidden flex flex-col">
      
      {/* GLOBAL BACKGROUND SYSTEM */}
      <div className="fixed inset-0 pointer-events-none z-0">
        <div className="absolute inset-0 bg-[#0a0a0c]"></div>
        <div className="absolute inset-0 bg-[linear-gradient(to_right,#ffffff02_1px,transparent_1px),linear-gradient(to_bottom,#ffffff02_1px,transparent_1px)] bg-[size:2rem_2rem]"></div>
      </div>

      {/* TOP COMMAND BAR */}
      <header className="relative z-10 border-b border-white/10 bg-black/80 backdrop-blur-md h-16 flex items-center justify-between px-4 shrink-0">
        <div className="flex items-center gap-4">
          <Link href="/portal" className="text-zinc-500 hover:text-white transition-colors flex items-center gap-1 text-xs font-bold tracking-widest uppercase">
            <ChevronLeft className="w-4 h-4" /> Exit
          </Link>
          <div className="h-6 w-px bg-zinc-950/10"></div>
          <div className="flex items-center gap-2">
            <div className="w-2 h-2  bg-red-500 animate-pulse shadow-[0_0_8px_#ef4444]"></div>
            <span className="text-[0.65rem] font-bold tracking-[0.2em] text-red-500 uppercase">Live Chart</span>
          </div>
          <div className="text-sm font-mono tracking-wider text-white bg-zinc-950/5 border border-white/10 px-3 py-1">
            INC-2026-993847
          </div>
        </div>

        {/* PATIENT BANNER (Fills middle) */}
        <div className="hidden lg:flex flex-1 mx-8 border border-white/10 bg-[#101014] h-10 items-center px-4 justify-between">
          <div className="flex items-center gap-6">
            <div className="flex items-center gap-2">
              <User className="w-4 h-4 text-[#FF4D00]" />
              <span className="font-bold text-white tracking-wide">DOE, JOHN M.</span>
            </div>
            <div className="text-xs font-mono text-zinc-500"><span className="text-gray-600">AGE:</span> 45</div>
            <div className="text-xs font-mono text-zinc-500"><span className="text-gray-600">SEX:</span> M</div>
            <div className="text-xs font-mono text-zinc-500"><span className="text-gray-600">WT:</span> 85kg</div>
          </div>
          <div className="flex items-center gap-4">
            <div className="flex items-center gap-2 text-xs font-mono">
              <span className="text-gray-600">CC:</span>
              <span className="text-red-400 font-bold">CHEST PAIN</span>
            </div>
            <div className="px-2 py-0.5 bg-[#FF4D00]/10 border border-orange/20 text-[#FF4D00] text-[0.6rem] font-bold tracking-widest uppercase">
              Priority 1
            </div>
          </div>
        </div>

        <div className="hidden items-center gap-4 sm:flex">
          <button className="flex items-center gap-2 px-4 py-1.5 border border-white/20 text-xs font-bold tracking-widest uppercase hover:bg-zinc-950/5 transition-colors">
            <Save className="w-3.5 h-3.5" /> Save
          </button>
          <button className="flex items-center gap-2 px-4 py-1.5 bg-[#FF4D00] border border-orange hover:bg-[#FF4D00]/80 text-black text-xs font-black tracking-widest uppercase shadow-[0_0_15px_rgba(255,100,0,0.3)] transition-all">
            <CheckCircle className="w-3.5 h-3.5" /> Finalize
          </button>
        </div>
      </header>

      {/* MAIN WORKSPACE */}
      <main className="relative z-10 flex-1 flex flex-col lg:flex-row overflow-hidden">
        
        {/* LEFT PANEL: DISPATCH & TIMES (Fixed on Desktop, collapse on Mobile) */}
        <aside className="w-full lg:w-72 border-r border-white/10 bg-[#0a0a0c]/90 flex flex-col shrink-0 overflow-y-auto">
          
          {/* Dispatch Info */}
          <div className="p-4 border-b border-white/5">
            <div className="text-[0.6rem] font-bold tracking-[0.2em] text-zinc-500 uppercase mb-3 flex items-center gap-2">
              <Radio className="w-3.5 h-3.5 text-blue-400" /> CAD Data
            </div>
            <div className="space-y-3">
              <div>
                <div className="text-[0.6rem] text-gray-600 font-mono mb-1">LOCATION</div>
                <div className="text-xs font-bold text-gray-300 flex items-start gap-2">
                  <MapPin className="w-3.5 h-3.5 text-zinc-500 shrink-0 mt-0.5" />
                  1234 MISSION CRTL BLVD, APT 4B<br/>SECTOR 7
                </div>
              </div>
              <div>
                <div className="text-[0.6rem] text-gray-600 font-mono mb-1">DISPATCH NOTES</div>
                <div className="text-[0.7rem] text-zinc-500 font-mono leading-relaxed bg-black/50 p-2 border border-white/5">
                  45YOM STATED SEVERE CHEST PAIN. RAD TO L ARM. DIAPHORETIC. HX HYPERTENSION.
                </div>
              </div>
            </div>
          </div>

          {/* Times Grid */}
          <div className="p-4 border-b border-white/5 flex-1">
            <div className="text-[0.6rem] font-bold tracking-[0.2em] text-zinc-500 uppercase mb-3 flex items-center gap-2">
              <Clock className="w-3.5 h-3.5 text-[#FF4D00]" /> Mission Clocks
            </div>
            <div className="grid grid-cols-2 gap-2">
              <TimeBlock label="Received" time="14:02:45" active={false} />
              <TimeBlock label="En Route" time="14:04:12" active={false} />
              <TimeBlock label="At Scene" time="14:11:05" active={false} />
              <TimeBlock label="Pt Contact" time="14:12:30" active={false} />
              <TimeBlock label="Depart" time="14:28:10" active={false} />
              <TimeBlock label="At Dest" time="--:--:--" active={true} />
            </div>
          </div>
          
          {/* Quick Vitals Trend */}
          <div className="p-4 bg-red-950/10">
            <div className="text-[0.6rem] font-bold tracking-[0.2em] text-red-500/80 uppercase mb-3 flex items-center gap-2">
              <Activity className="w-3.5 h-3.5 text-red-500" /> Vitals Monitor
            </div>
            <div className="flex justify-between items-center border border-red-500/20 bg-black/40 p-2 mb-2">
              <div className="text-[0.6rem] text-zinc-500 font-mono">HR</div>
              <div className="text-lg font-black text-red-400 font-mono">112</div>
            </div>
            <div className="flex justify-between items-center border border-white/10 bg-black/40 p-2 mb-2">
              <div className="text-[0.6rem] text-zinc-500 font-mono">BP</div>
              <div className="text-lg font-black text-white font-mono">155/92</div>
            </div>
            <div className="flex justify-between items-center border border-blue-500/20 bg-black/40 p-2">
              <div className="text-[0.6rem] text-zinc-500 font-mono">SpO2</div>
              <div className="text-lg font-black text-blue-400 font-mono">96%</div>
            </div>
          </div>
        </aside>

        {/* CENTER PANEL: CLINICAL INPUT */}
        <section className="flex-1 flex flex-col overflow-hidden bg-[#030304]">
          {/* Tabs */}
          <div className="flex border-b border-white/10 shrink-0 overflow-x-auto no-scrollbar">
            <TabButton active={activeTab === "narrative"} onClick={() => setActiveTab("narrative")} icon={FileText} label="Narrative" />
            <TabButton active={activeTab === "assessment"} onClick={() => setActiveTab("assessment")} icon={Stethoscope} label="Assessment" />
            <TabButton active={activeTab === "interventions"} onClick={() => setActiveTab("interventions")} icon={Zap} label="Interventions" />
            <TabButton active={activeTab === "medications"} onClick={() => setActiveTab("medications")} icon={Syringe} label="Medications" />
            <TabButton active={activeTab === "billing"} onClick={() => setActiveTab("billing")} icon={Database} label="Billing / Sigs" />
          </div>

          {/* Tab Content Area */}
          <div className="flex-1 overflow-y-auto p-4 lg:p-8">
            {activeTab === "narrative" && (
              <div className="h-full flex flex-col max-w-4xl mx-auto">
                <div className="flex justify-between items-end mb-4">
                  <h2 className="text-xl font-black uppercase tracking-wide text-white">Clinical Narrative</h2>
                  <button className="text-[0.6rem] font-bold text-[#FF4D00] uppercase tracking-widest border border-orange/40 bg-[#FF4D00]/10 px-3 py-1 flex items-center gap-2 hover:bg-[#FF4D00]/20 transition-colors">
                    <Zap className="w-3 h-3" /> Auto-Structure via AI
                  </button>
                </div>
                <textarea 
                  className="flex-1 w-full bg-[#0a0a0c] border border-white/10 p-6 text-gray-300 font-mono text-sm leading-relaxed resize-none focus:outline-none focus:border-orange/50 transition-colors shadow-inner"
                  placeholder="Unit 4 responded emergent to..."
                  defaultValue={"Unit 4 responded emergent to a residential address for a 45YOM c/o chest pain. \n\nUpon arrival, crew found Pt seated in living room chair, conscious, alert, oriented x4. Pt states sudden onset substernal chest pressure radiating to left arm that began 30 minutes prior to call. Pt is diaphoretic. \n\n12-Lead EKG obtained showing ST elevation in leads II, III, aVF. Transmitted to receiving facility telemetry. Pt administered 324mg ASA and 0.4mg SL NTG x1. \n\nIV access established 18g Left AC. Initiated transport to..."}
                ></textarea>
                
                {/* AI QA Guardrails Tool */}
                <div className="mt-4 border border-green-500/30 bg-green-500/5 p-4 flex gap-4 items-start">
                  <ShieldAlert className="w-5 h-5 text-green-500 shrink-0" />
                  <div>
                    <div className="text-xs font-bold text-green-400 tracking-wider uppercase mb-1">Billing QA Validation: Passed</div>
                    <div className="text-xs text-zinc-500">Narrative supports Medical Necessity (Chest Pain + STEMI protocols). Mileage and loaded status align with CAD times.</div>
                  </div>
                </div>
              </div>
            )}

            {/* Placeholder for other tabs */}
            {activeTab !== "narrative" && (
              <div className="h-full flex items-center justify-center text-zinc-500 font-mono text-sm uppercase tracking-widest">
                [ Module Content: {activeTab} ]
              </div>
            )}
          </div>
        </section>

        {/* RIGHT PANEL: RAPID ENTRY (High-density actions) */}
        <aside className="w-full lg:w-64 border-l border-white/10 bg-[#0a0a0c] flex flex-col shrink-0">
          <div className="p-4 border-b border-white/10 bg-black">
            <h3 className="text-[0.65rem] font-bold tracking-[0.2em] text-white uppercase flex items-center gap-2">
              <Zap className="w-3.5 h-3.5 text-[#FF4D00]" /> Rapid Entry Actions
            </h3>
          </div>
          <div className="p-4 space-y-2 overflow-y-auto flex-1">
            <RapidButton label="12-Lead EKG" meta="Captured 14:14" status="done" />
            <RapidButton label="Vital Signs" meta="Last 14:20" />
            <RapidButton label="Vascular Access" meta="18g L AC" status="done" />
            <RapidButton label="Aspirin 324mg" meta="PO" status="done" />
            <RapidButton label="Nitro 0.4mg" meta="SL" status="done" />
            <div className="my-4 border-t border-white/5"></div>
            <RapidButton label="Add Medication" type="add" />
            <RapidButton label="Add Procedure" type="add" />
            <RapidButton label="Code Blue / CPR" type="critical" />
          </div>
        </aside>

      </main>
    </div>
  );
}

// Sub-components
function TimeBlock({ label, time, active }: { label: string, time: string, active: boolean }) {
  return (
    <div className={`p-2 border border-white/10 flex flex-col justify-center ${active ? 'bg-[#FF4D00]/10 border-orange/30' : 'bg-black/50'}`}>
      <div className={`text-[0.55rem] font-bold tracking-widest uppercase mb-1 ${active ? 'text-[#FF4D00]' : 'text-zinc-500'}`}>{label}</div>
      <div className={`font-mono text-xs ${active ? 'text-white' : 'text-zinc-500'}`}>{time}</div>
    </div>
  );
}

function TabButton({ active, onClick, icon: Icon, label }: { active: boolean, onClick: () => void, icon: any, label: string }) {
  return (
    <button 
      onClick={onClick}
      className={`flex items-center gap-2 px-6 py-4 text-xs font-bold tracking-widest uppercase whitespace-nowrap transition-all border-r border-white/5
        ${active 
          ? 'bg-zinc-950/5 text-white border-b-2 border-b-orange' 
          : 'bg-transparent text-zinc-500 hover:bg-zinc-950/[0.02] hover:text-gray-300 border-b-2 border-b-transparent'}`}
    >
      <Icon className="w-4 h-4" />
      {label}
    </button>
  );
}

function RapidButton({ label, meta, status, type = "normal" }: { label: string, meta?: string, status?: "done", type?: "normal"|"add"|"critical" }) {
  let style = "bg-zinc-950/5 border-white/10 text-gray-300 hover:bg-zinc-950/10 hover:border-white/20";
  if (status === "done") style = "bg-[#060608] border-green-500/30 text-zinc-500 opacity-60";
  if (type === "add") style = "bg-transparent border-dashed border-white/20 text-zinc-500 hover:text-white hover:border-white/40";
  if (type === "critical") style = "bg-red-500/10 border-red-500/30 text-red-500 hover:bg-red-500 hover:text-white";

  return (
    <button className={`w-full text-left p-3 border transition-all flex flex-col group ${style}`}>
      <div className="flex items-center justify-between w-full">
        <span className="text-xs font-bold uppercase tracking-wider">{label}</span>
        {status === "done" && <CheckCircle className="w-3.5 h-3.5 text-green-500" />}
      </div>
      {meta && <span className="text-[0.6rem] font-mono mt-1 opacity-70">{meta}</span>}
    </button>
  );
}
