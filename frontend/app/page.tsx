"use client";

import React, { useState } from "react";
import Link from "next/link";
import type { LucideIcon } from "lucide-react";
import {
  ArrowRight,
  ShieldCheck,
  Database,
  TerminalSquare,
  Users,
  LockKeyhole,
  Server,
  ScanLine,
  Target,
  Box,
  PhoneCall,
  Workflow,
  ClipboardList,
  Calculator,
  Crosshair,
  ArrowUpRight,
  Zap,
} from "lucide-react";
import QuantumLogo from "@/components/branding/QuantumLogo";

function Logo() {
  return (
    <QuantumLogo size="lg" />
  );
}

// Upgraded Icon Wrapper for tactical/tech feel
function TechIcon({ icon: Icon, color = "text-[var(--color-text-muted)]", className = "" }: { icon: LucideIcon, color?: string, className?: string }) {
  return (
    <div className={`quantum-icon-frame relative flex items-center justify-center w-12 h-12 group-hover:border-orange/40 transition-colors ${className}`}>
      {/* Tactical corners */}
      <div className="absolute top-0 left-0 w-1.5 h-1.5 border-t border-l border-white/50"></div>
      <div className="absolute top-0 right-0 w-1.5 h-1.5 border-t border-r border-white/50"></div>
      <div className="absolute bottom-0 left-0 w-1.5 h-1.5 border-b border-l border-white/50"></div>
      <div className="absolute bottom-0 right-0 w-1.5 h-1.5 border-b border-r border-white/50"></div>
      
      <div className="absolute inset-0 bg-[var(--q-orange)]/5 opacity-0 group-hover:opacity-100 transition-opacity"></div>
      <Icon className={`quantum-icon ${color} relative z-10`} />
    </div>
  );
}

export default function LandingPage() {
  const [transports, setTransports] = useState(25000);
  const [privatePayRatio, setPrivatePayRatio] = useState(20);
  const [collectionRate, setCollectionRate] = useState(45);

  // ROI Math
  const privPayTransports = transports * (privatePayRatio / 100);
  const avgBill = 850;
  const totalPrivBilled = privPayTransports * avgBill;
  const currentCollected = totalPrivBilled * (collectionRate / 100);
  const quantumCollected = totalPrivBilled * (Math.min(95, collectionRate + 28) / 100);
  const lift = quantumCollected - currentCollected;

  return (
    <div className="min-h-screen text-gray-200 selection:bg-[var(--q-orange)]/20 selection:text-[var(--q-orange)] overflow-x-hidden font-sans relative">
      
      {/* GLOBAL BACKGROUND SYSTEM — aligned with new FQ Quantum aesthetic */}
      <div className="fixed inset-0 pointer-events-none z-0">
        <div className="absolute inset-0" style={{ background: 'radial-gradient(circle at top, rgba(255,120,40,0.13) 0%, transparent 30%), radial-gradient(circle at bottom right, rgba(255,140,0,0.10) 0%, transparent 28%), linear-gradient(180deg, #070707 0%, #0a0a0b 45%, #050505 100%)' }} />
        <div className="absolute left-[-8%] top-[-5%] h-[450px] w-[450px] rounded-full bg-orange-500/[0.07] blur-3xl" />
        <div className="absolute right-[-6%] top-[20%] h-[400px] w-[400px] rounded-full bg-amber-400/[0.07] blur-3xl" />
        <div className="absolute bottom-[-8%] left-[30%] h-[500px] w-[500px] rounded-full bg-orange-600/[0.07] blur-3xl" />
        {/* Tactical Grid */}
        <div className="absolute inset-0 bg-[linear-gradient(rgba(255,255,255,0.025)_1px,transparent_1px),linear-gradient(90deg,rgba(255,255,255,0.025)_1px,transparent_1px)] bg-[size:72px_72px] [mask-image:radial-gradient(circle_at_center,black,transparent_80%)]" />
      </div>

      {/* NAVIGATION */}
      <nav className="relative z-50 border-b border-white/5 bg-[var(--color-bg-base)]/80 backdrop-blur-md">
        <div className="max-w-[1600px] mx-auto px-6 h-24 flex items-center justify-between">
          <Logo />
          
          <div className="hidden lg:flex items-center gap-8 text-[0.7rem] font-bold tracking-[0.15em] text-[var(--color-text-muted)] uppercase">
            <Link href="/roi" className="hover:text-white transition-colors flex items-center gap-1.5">
              <Calculator className="w-3 h-3 text-[var(--q-orange)]" /> ROI Calc
            </Link>
            <Link href="/platform" className="hover:text-white transition-colors">Platform</Link>
            <Link href="#modules" className="hover:text-white transition-colors">Modules</Link>
            <Link href="/architecture" className="hover:text-white transition-colors">Architecture</Link>
          </div>

          <div className="flex items-center gap-3">
            <Link 
              href="/patient-billing-login" 
              className="group hidden sm:flex items-center gap-3 px-4 py-2.5 bg-[var(--color-bg-base)]/[0.02] border border-white/10 hover:border-orange/40 hover:bg-[var(--q-orange)]/5 transition-all shadow-inner"
            >
              <div className="w-2 h-2  bg-[var(--color-status-active)] animate-pulse shadow-[0_0_8px_#22c55e]"></div>
              <div className="flex flex-col text-left">
                <span className="text-[0.5rem] text-[var(--color-text-muted)] font-bold uppercase tracking-[0.2em] leading-none mb-0.5">Secure Gateway</span>
                <span className="text-[0.7rem] font-bold tracking-[0.1em] text-gray-300 uppercase leading-none group-hover:text-white">Patient Bill Pay Login</span>
              </div>
            </Link>

            <Link
              href="/facility-transport-login"
              className="text-[0.65rem] font-bold tracking-[0.13em] uppercase px-4 py-3 -none border border-white/25 bg-[var(--color-bg-base)]/[0.03] hover:border-orange/60 hover:bg-[var(--q-orange)]/10 transition-all text-gray-200 hover:text-white"
            >
              Facility TransportLink Login
            </Link>

            <Link 
              href="/founder-login" 
              className="text-[0.7rem] font-bold tracking-[0.15em] uppercase px-6 py-3 -none border border-orange bg-[var(--q-orange)]/10 hover:bg-[var(--q-orange)] hover:text-black transition-all text-[var(--q-orange)] shadow-[0_0_15px_rgba(255,100,0,0.15)] flex items-center gap-2"
            >
              Founder Login <TerminalSquare className="w-4 h-4" />
            </Link>
          </div>
        </div>
      </nav>

      <main className="relative z-10">
        
        {/* HERO SECTION */}
        <section className="relative min-h-[85vh] flex items-center justify-center pt-20 pb-32 overflow-hidden border-b border-white/5">
          <div className="max-w-[1400px] mx-auto px-6 relative z-20 text-center">
            
            <div className="inline-flex items-center gap-2 px-4 py-1.5 -none border border-[var(--color-brand-red)]/30 bg-[var(--color-brand-red)]/10 mb-8 shadow-inner">
              <Target className="w-3.5 h-3.5 text-[var(--color-brand-red)]" />
              <span className="text-[0.65rem] font-bold tracking-[0.2em] text-[var(--color-brand-red)] uppercase">Revenue integrity risk detected in legacy stack</span>
            </div>

            <h1 className="text-5xl md:text-8xl font-black tracking-tight mb-8 leading-[1.05] text-white drop-shadow-[0_0_15px_rgba(0,0,0,0.6)]">
              Restore Revenue Performance with <br/>
              <span className="text-transparent bg-clip-text bg-gradient-to-r from-orange via-red-500 to-orange bg-[length:200%_auto] animate-[pulse-glow_4s_ease-in-out_infinite]">Unified Mission-Critical Operations</span>
            </h1>
            
            <p className="max-w-3xl mx-auto text-lg md:text-xl text-[var(--color-text-muted)] leading-relaxed mb-12 font-medium">
              FusionEMS Quantum is the sovereign operating platform built to capture unrecovered cash. Before we deploy operations or fleet, we deploy <strong>Billing Command</strong> — an AI-powered infrastructure layer that stops the bleeding and forces revenue capture.
            </p>

            <div className="flex flex-col sm:flex-row items-center justify-center gap-6">
              <Link 
                href="/roi-funnel" 
                className="group px-10 py-5 bg-[var(--q-orange)] text-black font-black text-xs tracking-[0.15em] uppercase -none hover:bg-[#ff7a00] transition-colors relative shadow-[0_0_30px_rgba(255,100,0,0.3)] hover:shadow-[0_0_40px_rgba(255,100,0,0.5)] flex items-center gap-3"
              >
                <div className="absolute inset-0 border border-white/30 pointer-events-none mix-blend-overlay"></div>
                Calculate Your Unrecovered Yield <ArrowUpRight className="w-5 h-5 group-hover:translate-x-0.5 group-hover:-translate-y-0.5 transition-transform" />
              </Link>
              
              <Link 
                href="/platform" 
                className="group px-8 py-5 bg-transparent border border-white/20 text-white font-bold text-xs tracking-[0.15em] uppercase -none hover:bg-[var(--color-bg-base)]/5 hover:border-white/40 transition-all flex items-center gap-2"
              >
                View Platform Architecture
              </Link>
            </div>
          </div>
        </section>

        {/* SUPPORTING STRIP */}
        <section className="border-b border-white/5 bg-[#030304] relative z-20 shadow-inner">
          <div className="max-w-[1600px] mx-auto px-6 py-5 overflow-x-auto no-scrollbar">
            <div className="flex items-center justify-center gap-6 min-w-[1000px] text-[0.65rem] font-bold tracking-[0.2em] text-gray-600 uppercase">
              <div className="flex items-center gap-2 text-[var(--q-orange)] drop-shadow-[0_0_5px_rgba(255,100,0,0.5)]"><Zap className="w-3 h-3"/> Billing Command</div>
              <span className="text-[var(--color-text-secondary)]">|</span>
              <span>ePCR</span>
              <span className="text-[var(--color-text-secondary)]">|</span>
              <span>Fleet</span>
              <span className="text-[var(--color-text-secondary)]">|</span>
              <span>Scheduling</span>
              <span className="text-[var(--color-text-secondary)]">|</span>
              <span>Compliance</span>
              <span className="text-[var(--color-text-secondary)]">|</span>
              <span>Communications</span>
              <span className="text-[var(--color-text-secondary)]">|</span>
              <span className="text-[var(--color-text-muted)]">Founder Command</span>
            </div>
          </div>
        </section>

        {/* ROI CALCULATOR / WHY SWITCH SECTION */}
        <section id="roi" className="py-32 relative z-20 border-b border-white/5 bg-[radial-gradient(ellipse_at_bottom_right,_rgba(255,100,0,0.05)_0%,_transparent_50%)]">
          <div className="max-w-[1400px] mx-auto px-6">
            <div className="grid lg:grid-cols-[1fr_1.2fr] gap-16 items-center">
              
              {/* Marketing Hard / Why Me */}
              <div className="space-y-8">
                <div className="text-[0.65rem] font-bold tracking-[0.2em] text-[var(--q-orange)] uppercase flex items-center gap-2">
                  <ScanLine className="w-4 h-4" /> System Audit
                </div>
                <h2 className="text-4xl md:text-5xl font-black tracking-tight text-white leading-tight">
                  Why you must switch to FusionEMS Quantum.
                </h2>
                <div className="space-y-6 text-[var(--color-text-muted)] text-lg leading-relaxed">
                  <p>
                    Most EMS agencies have accepted a <strong className="text-white">sub-50% net collection rate</strong> on private-pay statements as &quot;the cost of doing business&quot;. That is a foundational failure of legacy software.
                  </p>
                  <p>
                    You are losing revenue because patient communications are manual, callback workflows are invisible, and fragmented portals cause friction that prevents payments.
                  </p>
                  <ul className="space-y-4 pt-4 border-t border-white/10">
                    <li className="flex gap-4">
                      <Crosshair className="w-6 h-6 text-[var(--color-brand-red)] shrink-0" />
                      <span className="text-base"><strong className="text-white">AI-Driven Capture.</strong> We automate patient billing touches with aggressive, intelligent follow-ups.</span>
                    </li>
                    <li className="flex gap-4">
                      <Workflow className="w-6 h-6 text-[var(--color-brand-red)] shrink-0" />
                      <span className="text-base"><strong className="text-white">Unified Extranet.</strong> TransportLink™ removes payer friction, dramatically increasing payment completion rates.</span>
                    </li>
                    <li className="flex gap-4">
                      <LockKeyhole className="w-6 h-6 text-[var(--color-brand-red)] shrink-0" />
                      <span className="text-base"><strong className="text-white">Complete Authority.</strong> Never wonder where a claim stalled. Every interaction is mapped, transcribed, and actionable.</span>
                    </li>
                  </ul>
                </div>
              </div>

              {/* ROI Calculator Component */}
              <div className="bg-[#0a0a0c] border border-white/10 p-8 md:p-12 shadow-[0_0_50px_rgba(255,100,0,0.05)] relative overflow-hidden group">
                <div className="absolute top-0 right-0 w-32 h-32 bg-[var(--q-orange)]/10 blur-[50px]"></div>
                <div className="absolute top-0 left-0 w-full h-[2px] bg-gradient-to-r from-orange to-transparent"></div>
                
                <h3 className="text-xl font-black uppercase tracking-widest text-white mb-2">Revenue Impact Analysis</h3>
                <p className="text-xs text-[var(--color-text-muted)] font-mono tracking-widest uppercase mb-10">Live Diagnostic / Private-Pay Yield</p>

                <div className="space-y-8 mb-10">
                  {/* Slider 1 */}
                  <div>
                    <div className="flex justify-between text-sm font-bold text-gray-300 mb-4 tracking-wide">
                      <span>Annual Transports</span>
                      <span className="text-[var(--q-orange)]">{transports.toLocaleString()}</span>
                    </div>
                    <input 
                      type="range" min="1000" max="100000" step="1000" value={transports} onChange={(e) => setTransports(Number(e.target.value))}
                      className="w-full h-1 bg-[var(--color-bg-panel)] -none appearance-none cursor-pointer accent-orange" 
                    />
                  </div>
                  {/* Slider 2 */}
                  <div>
                    <div className="flex justify-between text-sm font-bold text-gray-300 mb-4 tracking-wide">
                      <span>Private Pay / Co-Pay Ratio (%)</span>
                      <span className="text-[var(--q-orange)]">{privatePayRatio}%</span>
                    </div>
                    <input 
                      type="range" min="5" max="50" step="1" value={privatePayRatio} onChange={(e) => setPrivatePayRatio(Number(e.target.value))}
                      className="w-full h-1 bg-[var(--color-bg-panel)] -none appearance-none cursor-pointer accent-orange" 
                    />
                  </div>
                  {/* Slider 3 */}
                  <div>
                    <div className="flex justify-between text-sm font-bold text-gray-300 mb-4 tracking-wide">
                      <span>Current Collection Rate (%)</span>
                      <span className="text-[var(--q-orange)]">{collectionRate}%</span>
                    </div>
                    <input 
                      type="range" min="10" max="80" step="1" value={collectionRate} onChange={(e) => setCollectionRate(Number(e.target.value))}
                      className="w-full h-1 bg-[var(--color-bg-panel)] -none appearance-none cursor-pointer accent-orange" 
                    />
                  </div>
                </div>

                <div className="p-6 bg-[var(--color-bg-base)] border border-white/5 flex flex-col items-center justify-center text-center relative pointer-events-none">
                  <div className="absolute top-0 left-1/2 -translate-x-1/2 px-2 py-1 bg-[var(--color-bg-base)]/5 border border-white/10 text-[0.55rem] tracking-[0.2em] uppercase text-[var(--color-status-active)] font-bold -mt-3">
                    Projected Added Lift
                  </div>
                  <div className="text-5xl md:text-6xl font-black tracking-tighter text-white mt-4 drop-shadow-[0_0_15px_rgba(0,0,0,0.6)]">
                    <span className="text-[var(--color-status-active)] mr-2">+</span>
                    ${lift.toLocaleString(undefined, { maximumFractionDigits: 0 })}
                  </div>
                  <p className="text-xs text-[var(--color-text-muted)] uppercase tracking-widest mt-4">Unrecovered revenue captured unconditionally</p>
                </div>
              </div>

            </div>
          </div>
        </section>

        {/* FOUNDER STATEMENT SECTION */}
        <section className="py-24 relative z-20 border-b border-white/5 bg-[#101014]">
          <div className="max-w-[1200px] mx-auto px-6 grid md:grid-cols-[1fr_2fr] gap-12">
            <div>
              <div className="text-[0.65rem] font-bold tracking-[0.2em] text-[var(--q-orange)] uppercase mb-4">Founder’s Statement</div>
              <h2 className="text-3xl font-black tracking-tight text-white mb-6">Built from the field, not from assumptions</h2>
            </div>
            <div className="space-y-6 text-[var(--color-text-muted)] text-lg leading-relaxed border-l border-white/10 pl-8">
              <p>
                As a paramedic, I saw firsthand how often public safety agencies are forced to operate on systems that are slow, fragmented, unreliable, and overly dependent on ideal conditions. In the environments where this work actually happens, connectivity is not always stable, time is limited, and every layer of friction carries operational consequences.
              </p>
              <p>
                That experience led me to build FusionEMS Quantum.
              </p>
              <p>
                I designed, engineered, and built FusionEMS Quantum to deliver a modern platform that is faster, more intuitive, and more resilient than the legacy systems agencies have historically been forced to tolerate. The goal is straightforward: unify billing, operations, compliance, communication, scheduling, fleet, and clinical workflows into a single platform that performs reliably in real-world conditions and scales with the demands of modern public safety organizations.
              </p>
              <p className="font-bold text-gray-300">
                FusionEMS Quantum represents my belief that mission-critical agencies deserve mission-critical infrastructure.
              </p>
              <div className="pt-6">
                <p className="text-white font-black tracking-wide">— Joshua Wendorf</p>
                <p className="text-sm text-[var(--color-text-muted)] uppercase tracking-widest mt-1">Founder, FusionEMS Quantum</p>
              </div>
            </div>
          </div>
        </section>

        {/* PLATFORM MODULES SECTION */}
        <section id="modules" className="py-32 relative z-20 border-b border-white/5 bg-[var(--color-bg-base)]">
          <div className="max-w-[1600px] mx-auto px-6">
            <div className="mb-20">
              <div className="text-[0.65rem] font-bold tracking-[0.2em] text-[var(--color-text-muted)] uppercase mb-4">Platform Modules</div>
              <h2 className="text-4xl md:text-5xl font-black tracking-tight text-white mb-6">A unified command platform across the entire agency</h2>
              <p className="text-xl text-[var(--color-text-muted)] max-w-3xl">
                FusionEMS Quantum is not a single-feature application. It is a modular platform built to bring the operational, financial, administrative, and clinical sides of the agency into one system.
              </p>
            </div>

            <div className="grid md:grid-cols-2 lg:grid-cols-4 gap-4">
              
              <Link href="/billing-command" className="group border border-orange/50 bg-[var(--color-bg-base)]/50 p-8 flex flex-col justify-start relative overflow-hidden hover:border-orange/70 transition-colors">
                <div className="absolute top-0 right-0 w-32 h-32 bg-[var(--q-orange)]/5 blur-[30px]  group-hover:bg-[var(--q-orange)]/10 transition-colors"></div>
                <TechIcon icon={Database} color="text-[var(--q-orange)]" className="mb-6" />
                <h3 className="text-sm font-bold uppercase tracking-wider text-white mb-2">Module 1 — Billing Command</h3>
                <p className="text-sm text-[var(--color-text-muted)] leading-relaxed">
                  <strong className="text-gray-200">Active Module.</strong> Centralized billing communications, patient support, callback workflows, AI-assisted collections infrastructure, and real-time revenue visibility. Designed to reduce friction and replace fragmented patient billing.
                </p>
              </Link>

              <Link href="/epcr" className="group border border-white/10 bg-[#101014] p-8 flex flex-col justify-start hover:border-white/25 transition-colors">
                <TechIcon icon={ClipboardList} className="mb-6" />
                <h3 className="text-sm font-bold uppercase tracking-wider text-white mb-2">Module 2 — ePCR / Clinical Command</h3>
                <p className="text-sm text-[var(--color-text-muted)] leading-relaxed">
                  Field documentation, chart readiness, QA workflows, AI-assisted narrative support, validation, and structured clinical visibility. Built for faster workflows and dependable charging.
                </p>
              </Link>

              <Link href="/fleet" className="group border border-white/10 bg-[#101014] p-8 flex flex-col justify-start hover:border-white/25 transition-colors">
                <TechIcon icon={Box} className="mb-6" />
                <h3 className="text-sm font-bold uppercase tracking-wider text-white mb-2">Module 3 — Fleet Command</h3>
                <p className="text-sm text-[var(--color-text-muted)] leading-relaxed">
                  Fleet readiness, maintenance tracking, inspections, defect visibility, unit state awareness, and long-term serviceability control. Replaces fragmented vehicle readiness processes.
                </p>
              </Link>

              <Link href="/scheduling" className="group border border-white/10 bg-[#101014] p-8 flex flex-col justify-start hover:border-white/25 transition-colors">
                <TechIcon icon={Users} className="mb-6" />
                <h3 className="text-sm font-bold uppercase tracking-wider text-white mb-2">Module 4 — Scheduling Command</h3>
                <p className="text-sm text-[var(--color-text-muted)] leading-relaxed">
                  Shift planning, staffing visibility, coverage gaps, qualification awareness, schedule management, and workforce readiness. Less manual overhead, more structured control.
                </p>
              </Link>

              <Link href="/communications" className="group border border-white/10 bg-[#101014] p-8 flex flex-col justify-start hover:border-white/25 transition-colors">
                <TechIcon icon={PhoneCall} className="mb-6" />
                <h3 className="text-sm font-bold uppercase tracking-wider text-white mb-2">Module 5 — Comms Command</h3>
                <p className="text-sm text-[var(--color-text-muted)] leading-relaxed">
                  Centralized billing communications, secure workflows, AI voice, SMS, voicemail, callback logic. Communications built as infrastructure, not scattered alerts.
                </p>
              </Link>

              <Link href="/compliance" className="group border border-white/10 bg-[#101014] p-8 flex flex-col justify-start hover:border-white/25 transition-colors">
                <TechIcon icon={ShieldCheck} className="mb-6" />
                <h3 className="text-sm font-bold uppercase tracking-wider text-white mb-2">Module 6 — Compliance Command</h3>
                <p className="text-sm text-[var(--color-text-muted)] leading-relaxed">
                  DEA/CMS-ready operational compliance command with controlled-substance custody checks, CMS gate monitoring, NEMSIS validation, HIPAA controls, billing compliance, and accreditation readiness — built for inspection-ready public safety agencies.
                </p>
              </Link>

              <Link href="/platform" className="group border border-white/10 bg-[#101014] p-8 flex flex-col justify-start hover:border-white/25 transition-colors">
                <TechIcon icon={Target} className="mb-6" />
                <h3 className="text-sm font-bold uppercase tracking-wider text-white mb-2">Module 7 — Operations Command</h3>
                <p className="text-sm text-[var(--color-text-muted)] leading-relaxed">
                  Operational visibility, workflow control, role-based command surfaces, and future-ready dispatch and mission coordination infrastructure.
                </p>
              </Link>

              <Link href="/founder-command" className="group border border-white/10 bg-[#101014] p-8 flex flex-col justify-start hover:border-white/25 transition-colors">
                <TechIcon icon={TerminalSquare} className="mb-6 z-10" />
                <h3 className="text-sm font-bold uppercase tracking-wider text-white mb-2 z-10">Module 8 — Founder Command</h3>
                <p className="text-sm text-[var(--color-text-muted)] leading-relaxed z-10">
                  Cross-platform visibility into revenue, communications, workflow risk, implementation, and command-level decision support for executive clarity.
                </p>
              </Link>

            </div>
          </div>
        </section>

        {/* SECURE ACCESS SECTION (TRANSPORTLINK HIGHLIGHT) */}
        <section className="py-32 relative z-20 border-b border-white/5 bg-[#101014]">
          <div className="max-w-[1400px] mx-auto px-6">
            <div className="text-center mb-16">
              <div className="text-[0.65rem] font-bold tracking-[0.2em] text-[var(--color-text-muted)] uppercase mb-4">Portals</div>
              <h2 className="text-4xl font-black tracking-tight text-white mb-4">Role-based access into the platform</h2>
              <p className="text-lg text-[var(--color-text-muted)] max-w-2xl mx-auto">
                FusionEMS Quantum is designed around structured entry points. No more weak links losing patient data. Network perimeters divide patient access, reps, and agency command. Compliance tooling supports agency-level controls and is jurisdiction- and counsel-dependent.
              </p>
            </div>

            <div className="grid md:grid-cols-2 xl:grid-cols-5 gap-6">
              {/* TransportLink Patient Access */}
              <div className="border border-[var(--color-status-active)]/30 bg-[var(--color-bg-base)] p-8 flex flex-col relative overflow-hidden group shadow-[0_0_20px_rgba(34,197,94,0.05)]">
                <div className="absolute inset-0 bg-gradient-to-b from-green-500/5 to-transparent pointer-events-none"></div>
                <h3 className="text-sm font-bold uppercase tracking-widest text-white mb-4 flex items-center justify-between border-b border-white/10 pb-4 relative z-10">
                  <span className="flex items-center gap-2">
                    <div className="w-1.5 h-1.5  bg-[var(--color-status-active)] shadow-[0_0_5px_#22c55e]"></div>
                    TransportLink™ Extranet
                  </span>
                  <LockKeyhole className="w-4 h-4 text-[var(--color-status-active)]" />
                </h3>
                <p className="text-sm text-[var(--color-text-muted)] mb-8 flex-1 relative z-10">
                  Bank-grade secure access for statement review, payment support, and guided billing communication. Built to convert, not to frustrate.
                </p>
                <Link href="/patient-billing-login" className="text-xs font-bold uppercase tracking-widest text-[var(--color-status-active)] hover:text-[var(--color-status-active)] transition-colors flex items-center gap-2 relative z-10">
                  Patient Bill Pay Login <ArrowRight className="w-3 h-3" />
                </Link>
              </div>

              {/* Rep Access */}
              <div className="border border-white/10 bg-[var(--color-bg-base)] p-8 flex flex-col group">
                <h3 className="text-sm font-bold uppercase tracking-widest text-white mb-4 flex items-center justify-between border-b border-white/10 pb-4">
                  Authorized Rep Gateway
                  <ShieldCheck className="w-4 h-4 text-[var(--color-text-muted)] group-hover:text-white transition-colors" />
                </h3>
                <p className="text-sm text-[var(--color-text-muted)] mb-8 flex-1">
                  Controlled access with MFA for approved parties, guardians, and POAs supporting patient billing workflows.
                </p>
                <Link href="/portal/rep/login" className="text-xs font-bold uppercase tracking-widest text-[var(--color-text-muted)] hover:text-white transition-colors flex items-center gap-2">
                  Submit Credentials <ArrowRight className="w-3 h-3" />
                </Link>
              </div>

              {/* Staff Access */}
              <div className="border border-orange/30 bg-[var(--color-bg-base)] p-8 flex flex-col relative group">
                <div className="absolute inset-0 bg-[var(--q-orange)]/5 pointer-events-none opacity-0 group-hover:opacity-100 transition-opacity"></div>
                <h3 className="text-sm font-bold uppercase tracking-widest text-white mb-4 flex items-center justify-between border-b border-white/10 pb-4">
                  Facility TransportLink
                  <Server className="w-4 h-4 text-[var(--q-orange)]" />
                </h3>
                <p className="text-sm text-[var(--color-text-muted)] mb-8 flex-1">
                  Dedicated login for hospital and assisted living teams to request and manage transport operations.
                </p>
                <Link href="/facility-transport-login" className="text-xs font-bold uppercase tracking-widest text-[var(--q-orange)] hover:text-[#ff7a00] transition-colors flex items-center gap-2">
                  Facility Login <ArrowRight className="w-3 h-3" />
                </Link>
              </div>

              {/* DEA/CMS Compliance Command */}
              <div className="border border-[var(--color-status-info)]/30 bg-[var(--color-bg-base)] p-8 flex flex-col relative group">
                <div className="absolute inset-0 bg-[var(--color-status-info)]/5 pointer-events-none opacity-0 group-hover:opacity-100 transition-opacity"></div>
                <h3 className="text-sm font-bold uppercase tracking-widest text-white mb-4 flex items-center justify-between border-b border-white/10 pb-4">
                  DEA / CMS Command
                  <ShieldCheck className="w-4 h-4 text-[var(--color-status-info)]" />
                </h3>
                <p className="text-sm text-[var(--color-text-muted)] mb-8 flex-1">
                  Wisconsin-first DEA/CMS readiness command. Run narcotics chain-of-custody audits, monitor CMS gate pass/fail trends, and generate inspection-ready evidence bundles.
                </p>
                <Link href="/portal/dea-cms" className="text-xs font-bold uppercase tracking-widest text-[var(--color-status-info)] hover:text-[var(--color-status-info)] transition-colors flex items-center gap-2">
                  Open Compliance Command <ArrowRight className="w-3 h-3" />
                </Link>
              </div>

              {/* Legal Requests Command */}
              <div className="border border-sky-500/30 bg-[var(--color-bg-base)] p-8 flex flex-col relative group">
                <div className="absolute inset-0 bg-sky-500/5 pointer-events-none opacity-0 group-hover:opacity-100 transition-opacity"></div>
                <h3 className="text-sm font-bold uppercase tracking-widest text-white mb-4 flex items-center justify-between border-b border-white/10 pb-4">
                  Legal Requests
                  <ShieldCheck className="w-4 h-4 text-sky-400" />
                </h3>
                <p className="text-sm text-[var(--color-text-muted)] mb-8 flex-1">
                  Submit attorney/legal requests with intake triage, checklist validation, default redaction, and secure one-time delivery controls.
                </p>
                <Link href="/portal/legal/requests/new" className="text-xs font-bold uppercase tracking-widest text-sky-400 hover:text-sky-300 transition-colors flex items-center gap-2">
                  Open Legal Intake <ArrowRight className="w-3 h-3" />
                </Link>
              </div>
            </div>
          </div>
        </section>

        {/* VISION SECTION */}
        <section id="vision" className="py-32 relative z-20 border-b border-white/5 bg-[var(--color-bg-base)]">
          <div className="max-w-[1000px] mx-auto px-6 text-center">
            <div className="text-[0.65rem] font-bold tracking-[0.2em] text-[var(--color-text-muted)] uppercase mb-4">The broader vision</div>
            <h2 className="text-4xl md:text-6xl font-black tracking-tight text-white mb-8">
              A full operating system for modern public safety operations
            </h2>
            <div className="text-xl text-[var(--color-text-muted)] leading-relaxed space-y-6 font-medium">
              <p>
                FusionEMS Quantum begins with Billing Command, but the long-term vision is broader: a unified system that connects patient-facing revenue workflows, clinical documentation, operational oversight, fleet readiness, workforce scheduling, communications, compliance, and founder-level command into one modern platform.
              </p>
              <p className="text-white">
                This is not a replacement for one small tool. It is an effort to replace the fragmentation that agencies have had to tolerate for years.
              </p>
            </div>
          </div>
        </section>

      </main>

      {/* FOOTER */}
      <footer className="border-t border-white/10 bg-[#030304] py-12 relative z-20">
        <div className="max-w-[1600px] mx-auto px-6 flex flex-col md:flex-row items-center justify-between gap-6">
          <div className="flex items-center gap-4">
            <div className="text-[1rem] font-black tracking-[0.25em] text-white uppercase leading-none drop-shadow-[0_0_15px_rgba(0,0,0,0.6)]">
              FUSIONEMS
            </div>
          </div>
          <div className="text-xs font-bold tracking-[0.15em] text-gray-600 uppercase">
            © {new Date().getFullYear()} FusionEMS Quantum. All rights reserved.
          </div>
          <div className="text-[9px] text-[var(--color-text-disabled)] text-center max-w-lg leading-relaxed">
            FusionEMS provides compliance workflow tooling to support agency operations. It does not provide legal, regulatory, or medical advice. Compliance determinations are the responsibility of each agency and its counsel.
          </div>
          <div className="flex gap-8 text-[0.65rem] font-bold tracking-[0.15em] text-[var(--color-text-muted)] uppercase">
            <Link href="/login" className="hover:text-white transition-colors">Core</Link>
            <span className="text-white/10">|</span>
            <span className="text-gray-700">Mission Critical Infrastructure</span>
          </div>
        </div>
      </footer>
    </div>
  );
}
