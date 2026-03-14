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

      {/* GLOBAL BACKGROUND SYSTEM — FQ Quantum Command Surface */}
      <div className="fixed inset-0 pointer-events-none z-0">
        {/* Canvas Black base */}
        <div className="absolute inset-0 bg-[#0A0C0E]" />
        {/* Horizontal scanlines — ultra-subtle tension texture */}
        <div className="absolute inset-0" style={{ background: 'repeating-linear-gradient(0deg, transparent, transparent 3px, rgba(255,255,255,0.007) 3px, rgba(255,255,255,0.007) 4px)' }} />
        {/* Precision tactical grid */}
        <div className="absolute inset-0 bg-[linear-gradient(rgba(255,255,255,0.016)_1px,transparent_1px),linear-gradient(90deg,rgba(255,255,255,0.016)_1px,transparent_1px)] bg-[size:80px_80px]" />
        {/* Hard orange chamfer accent — top right */}
        <div className="absolute top-0 right-0 w-[400px] h-[1px] bg-gradient-to-l from-[#F36A21]/25 to-transparent" />
        <div className="absolute top-0 right-0 w-[1px] h-[260px] bg-gradient-to-b from-[#F36A21]/25 to-transparent" />
        {/* Bottom left accent line */}
        <div className="absolute bottom-0 left-0 w-[300px] h-[1px] bg-gradient-to-r from-[#F36A21]/15 to-transparent" />
        <div className="absolute bottom-0 left-0 w-[1px] h-[120px] bg-gradient-to-t from-[#F36A21]/15 to-transparent" />
      </div>

      {/* SYSTEM IDENTITY BAND */}
      <div className="relative z-50 bg-[#0A0C0E] border-b border-white/[0.04]">
        <div className="max-w-[1600px] mx-auto px-6 py-1.5 flex items-center justify-between">
          <div className="flex items-center gap-4 text-[0.55rem] font-bold tracking-[0.2em] uppercase">
            <div className="flex items-center gap-1.5">
              <div className="w-1 h-1 bg-[#F36A21] shadow-[0_0_4px_#F36A21]"></div>
              <span className="text-[#F36A21]">Quantum Platform</span>
            </div>
            <span className="text-[#66707A]">|</span>
            <span className="text-[#66707A]">Billing</span>
            <span className="text-[#66707A]">·</span>
            <span className="text-[#66707A]">ePCR</span>
            <span className="text-[#66707A]">·</span>
            <span className="text-[#66707A]">Fleet</span>
            <span className="text-[#66707A]">·</span>
            <span className="text-[#66707A]">Comms</span>
            <span className="text-[#66707A]">·</span>
            <span className="text-[#66707A]">Compliance</span>
          </div>
          <div className="hidden md:flex items-center gap-2 text-[0.55rem] font-bold tracking-[0.2em] text-[#66707A] uppercase">
            <span>FusionEMS Quantum</span>
            <span className="text-white/10">|</span>
            <span>Mission-Critical Public Safety SaaS</span>
          </div>
        </div>
      </div>

      {/* NAVIGATION */}
      <nav className="relative z-50 border-b border-white/5 bg-[#0A0C0E]/90 backdrop-blur-md" style={{ boxShadow: '0 1px 0 rgba(243,106,33,0.12)' }}>
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
              className="text-[0.65rem] font-bold tracking-[0.13em] uppercase px-4 py-3 rounded-none border border-white/25 bg-[var(--color-bg-base)]/[0.03] hover:border-orange/60 hover:bg-[var(--q-orange)]/10 transition-all text-gray-200 hover:text-white"
            >
              Facility TransportLink Login
            </Link>

            <Link
              href="/login"
              className="text-[0.7rem] font-bold tracking-[0.15em] uppercase px-6 py-3 rounded-none border border-orange bg-[var(--q-orange)]/10 hover:bg-[var(--q-orange)] hover:text-black transition-all text-[var(--q-orange)] shadow-[0_0_15px_rgba(255,100,0,0.15)] flex items-center gap-2"
            >
              Platform Login <TerminalSquare className="w-4 h-4" />
            </Link>
          </div>
        </div>
      </nav>

      <main className="relative z-10">

        {/* HERO SECTION */}
        <section className="relative min-h-[88vh] flex items-center justify-center pt-20 pb-32 overflow-hidden border-b border-white/[0.04]">

          {/* Hero accent geometry */}
          <div className="absolute inset-0 pointer-events-none">
            <div className="absolute top-[46%] left-0 right-0 flex items-center justify-center opacity-[0.05]">
              <div className="flex-1 h-[1px] bg-gradient-to-r from-transparent to-[#F36A21]" />
              <div className="w-3 h-3 border border-[#F36A21] mx-4 rotate-45" />
              <div className="flex-1 h-[1px] bg-gradient-to-l from-transparent to-[#F36A21]" />
            </div>
          </div>

          <div className="max-w-[1400px] mx-auto px-6 relative z-20 text-center">

            {/* Status badge */}
            <div className="inline-flex items-center gap-3 px-5 py-2 border border-white/10 bg-white/[0.02] mb-10">
              <div className="w-1.5 h-1.5 bg-[#F36A21] shadow-[0_0_6px_#F36A21]"></div>
              <span className="text-[0.6rem] font-bold tracking-[0.25em] text-[#8D98A3] uppercase">MISSION-CRITICAL PUBLIC SAFETY SAAS — EMS / HEMS / FIRE / BILLING</span>
              <div className="w-1.5 h-1.5 bg-[#F36A21] shadow-[0_0_6px_#F36A21]"></div>
            </div>

            {/* Headline — hard command authority, no animation */}
            <h1 className="text-5xl md:text-[5.5rem] font-black tracking-[-0.02em] mb-8 leading-[1.02] text-white">
              Capture Every Dollar.<br />
              <span className="text-[#F36A21]">Command Every Operation.</span>
            </h1>

            {/* Tactical divider */}
            <div className="flex items-center justify-center gap-4 mb-8 opacity-25">
              <div className="w-16 h-[1px] bg-[#F36A21]"></div>
              <div className="w-1 h-1 bg-[#F36A21] rotate-45"></div>
              <div className="w-16 h-[1px] bg-[#F36A21]"></div>
            </div>

            <p className="max-w-2xl mx-auto text-base md:text-lg text-[#8D98A3] leading-relaxed mb-12 font-medium">
              The sovereign operating platform for EMS, HEMS, and Fire agencies. Unified billing, ePCR, fleet, compliance, scheduling, and communications — engineered for mission-critical real-world operations.
            </p>

            <div className="flex flex-col sm:flex-row items-center justify-center gap-4">
              <Link
                href="/roi-funnel"
                className="group px-10 py-5 bg-[#F36A21] text-black font-black text-xs tracking-[0.18em] uppercase hover:bg-[#FF7A2F] transition-colors flex items-center gap-3"
                style={{ clipPath: 'polygon(0 0, calc(100% - 8px) 0, 100% 8px, 100% 100%, 0 100%)', boxShadow: '0 0 28px rgba(243,106,33,0.22)' }}
              >
                Calculate Unrecovered Yield <ArrowUpRight className="w-4 h-4 group-hover:translate-x-0.5 group-hover:-translate-y-0.5 transition-transform" />
              </Link>

              <Link
                href="/platform"
                className="px-8 py-5 bg-transparent border border-white/15 text-[#C7CDD3] font-bold text-xs tracking-[0.18em] uppercase hover:border-[#F36A21]/40 hover:text-white transition-all flex items-center gap-2"
              >
                View Platform Architecture
              </Link>
            </div>

            {/* Credential micro-label row */}
            <div className="mt-14 flex flex-wrap items-center justify-center gap-x-8 gap-y-1 text-[0.55rem] font-bold tracking-[0.2em] text-[#66707A] uppercase">
              <span>HIPAA-Conscious</span>
              <span className="text-white/10">|</span>
              <span>Multi-Tenant Architecture</span>
              <span className="text-white/10">|</span>
              <span>Real-Time Dispatch Ready</span>
              <span className="text-white/10">|</span>
              <span>NEMSIS 3.5 Compliant</span>
              <span className="text-white/10">|</span>
              <span>AWS Multi-AZ</span>
            </div>

          </div>
        </section>

        {/* CAPABILITY COMMAND RAIL */}
        <section className="border-b border-white/[0.04] bg-[#111417] relative z-20">
          <div className="max-w-[1600px] mx-auto px-6 py-4 overflow-x-auto no-scrollbar">
            <div className="flex items-center justify-center gap-0 min-w-[900px]">
              {[
                { label: 'Billing Command', active: true },
                { label: 'ePCR', active: false },
                { label: 'Fleet', active: false },
                { label: 'Scheduling', active: false },
                { label: 'Compliance', active: false },
                { label: 'Comms', active: false },
                { label: 'NEMSIS', active: false },
                { label: 'System Command', active: false },
              ].map((item, i) => (
                <div key={item.label} className="flex items-center">
                  {i > 0 && <div className="w-px h-4 bg-white/[0.08] mx-6" />}
                  <div className="flex items-center gap-2">
                    <div className={`w-1 h-1 ${item.active ? 'bg-[#F36A21] shadow-[0_0_4px_#F36A21]' : 'bg-[#1D2227]'}`}></div>
                    <span className={`text-[0.6rem] font-bold tracking-[0.18em] uppercase ${item.active ? 'text-[#F36A21]' : 'text-[#66707A]'}`}>{item.label}</span>
                  </div>
                </div>
              ))}
            </div>
          </div>
        </section>

        {/* ROI CALCULATOR / WHY SWITCH SECTION */}
        <section id="roi" className="py-32 relative z-20 border-b border-white/[0.04] bg-[#0A0C0E]">
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
              <div className="bg-[#111417] border border-white/[0.07] p-8 md:p-12 relative overflow-hidden group" style={{ boxShadow: '0 0 40px rgba(243,106,33,0.04)' }}>
                <div className="absolute top-0 left-0 w-full h-[1px] bg-gradient-to-r from-[#F36A21]/60 to-transparent"></div>
                <div className="absolute top-0 right-0 w-[80px] h-[80px] opacity-[0.06]" style={{ background: 'radial-gradient(circle at top right, #F36A21, transparent 70%)' }}></div>

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
                      className="w-full h-1 bg-[var(--color-bg-panel)] rounded-none appearance-none cursor-pointer accent-orange"
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
                      className="w-full h-1 bg-[var(--color-bg-panel)] rounded-none appearance-none cursor-pointer accent-orange"
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
                      className="w-full h-1 bg-[var(--color-bg-panel)] rounded-none appearance-none cursor-pointer accent-orange"
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

        {/* PLATFORM ORIGIN SECTION */}
        <section className="py-24 relative z-20 border-b border-white/[0.04] bg-[#111417]">
          <div className="max-w-[1200px] mx-auto px-6 grid md:grid-cols-[1fr_2fr] gap-12">
            <div>
              <div className="text-[0.65rem] font-bold tracking-[0.2em] text-[var(--q-orange)] uppercase mb-4">Platform Vision</div>
              <h2 className="text-3xl font-black tracking-tight text-white mb-6">Built from the field, not from assumptions</h2>
            </div>
            <div className="space-y-6 text-[var(--color-text-muted)] text-lg leading-relaxed border-l border-white/10 pl-8">
              <p>
                Public safety agencies have long been forced to operate on systems that are slow, fragmented, unreliable, and overly dependent on ideal conditions. In the environments where this work actually happens, connectivity is not always stable, time is limited, and every layer of friction carries operational consequences.
              </p>
              <p>
                That reality led to FusionEMS Quantum.
              </p>
              <p>
                FusionEMS Quantum was engineered to deliver a modern platform that is faster, more intuitive, and more resilient than the legacy systems agencies have historically been forced to tolerate. The goal is straightforward: unify billing, operations, compliance, communication, scheduling, fleet, and clinical workflows into a single platform that performs reliably in real-world conditions and scales with the demands of modern public safety organizations.
              </p>
              <p className="font-bold text-gray-300">
                Mission-critical agencies deserve mission-critical infrastructure.
              </p>
              <div className="pt-6">
                <p className="text-white font-black tracking-wide">— FusionEMS Engineering</p>
                <p className="text-sm text-[var(--color-text-muted)] uppercase tracking-widest mt-1">Platform Architecture Team</p>
              </div>
            </div>
          </div>
        </section>

        {/* PLATFORM MODULES SECTION */}
        <section id="modules" className="py-32 relative z-20 border-b border-white/[0.04] bg-[#0A0C0E]">
          <div className="max-w-[1600px] mx-auto px-6">
            <div className="mb-20">
              <div className="flex items-center justify-between mb-6">
                <div className="text-[0.6rem] font-bold tracking-[0.2em] text-[#8D98A3] uppercase flex items-center gap-2">
                  <div className="w-3 h-[1px] bg-[#F36A21]"></div>
                  Platform Modules
                </div>
                <div className="hidden md:flex items-center gap-3 text-[0.55rem] font-bold tracking-[0.2em] text-[#66707A] uppercase">
                  <div className="w-1 h-1 bg-[#4E9F6E] shadow-[0_0_4px_#4E9F6E]"></div>
                  <span>8 Modules Active</span>
                  <span className="text-white/10">|</span>
                  <span>Quantum Build 2.0</span>
                </div>
              </div>
              <h2 className="text-4xl md:text-5xl font-black tracking-tight text-white mb-6 leading-tight">A unified command platform<br />across the entire agency.</h2>
              <p className="text-lg text-[#8D98A3] max-w-2xl">
                FusionEMS Quantum is a modular platform connecting operational, financial, administrative, and clinical workflows into a single sovereign system.
              </p>
            </div>

            <div className="grid md:grid-cols-2 lg:grid-cols-4 gap-px bg-white/[0.04]">

              <Link href="/billing-command" className="group bg-[#111417] p-8 flex flex-col justify-start relative overflow-hidden hover:bg-[#171B1F] transition-colors">
                <div className="absolute top-0 left-0 w-full h-[2px] bg-[#F36A21]/60"></div>
                <div className="absolute top-3 right-3 flex items-center gap-1.5">
                  <div className="w-1 h-1 bg-[#F36A21] shadow-[0_0_4px_#F36A21]"></div>
                  <span className="text-[0.5rem] font-bold tracking-[0.2em] text-[#F36A21] uppercase">Active</span>
                </div>
                <TechIcon icon={Database} color="text-[#F36A21]" className="mb-6" />
                <h3 className="text-xs font-bold uppercase tracking-[0.12em] text-white mb-3">Module 01 — Billing Command</h3>
                <p className="text-sm text-[#8D98A3] leading-relaxed">
                  <strong className="text-[#C7CDD3]">Active Module.</strong> Centralized billing communications, patient support, callback workflows, AI-assisted collections, and real-time revenue visibility.
                </p>
              </Link>

              <Link href="/epcr" className="group bg-[#111417] p-8 flex flex-col justify-start hover:bg-[#171B1F] transition-colors relative overflow-hidden">
                <div className="absolute top-0 left-0 w-full h-[1px] bg-white/[0.06]"></div>
                <div className="absolute top-3 right-3">
                  <span className="text-[0.5rem] font-bold tracking-[0.2em] text-[#66707A] uppercase">Releasing</span>
                </div>
                <TechIcon icon={ClipboardList} className="mb-6" />
                <h3 className="text-xs font-bold uppercase tracking-[0.12em] text-white mb-3">Module 02 — ePCR / Clinical</h3>
                <p className="text-sm text-[#8D98A3] leading-relaxed">Field documentation, chart readiness, QA workflows, AI-assisted narrative, validation, and structured clinical visibility.</p>
              </Link>

              <Link href="/fleet" className="group bg-[#111417] p-8 flex flex-col justify-start hover:bg-[#171B1F] transition-colors relative overflow-hidden">
                <div className="absolute top-0 left-0 w-full h-[1px] bg-white/[0.06]"></div>
                <div className="absolute top-3 right-3">
                  <span className="text-[0.5rem] font-bold tracking-[0.2em] text-[#66707A] uppercase">Releasing</span>
                </div>
                <TechIcon icon={Box} className="mb-6" />
                <h3 className="text-xs font-bold uppercase tracking-[0.12em] text-white mb-3">Module 03 — Fleet Command</h3>
                <p className="text-sm text-[#8D98A3] leading-relaxed">Fleet readiness, maintenance tracking, inspections, defect visibility, unit state awareness, and serviceability control.</p>
              </Link>

              <Link href="/scheduling" className="group bg-[#111417] p-8 flex flex-col justify-start hover:bg-[#171B1F] transition-colors relative overflow-hidden">
                <div className="absolute top-0 left-0 w-full h-[1px] bg-white/[0.06]"></div>
                <div className="absolute top-3 right-3">
                  <span className="text-[0.5rem] font-bold tracking-[0.2em] text-[#66707A] uppercase">Releasing</span>
                </div>
                <TechIcon icon={Users} className="mb-6" />
                <h3 className="text-xs font-bold uppercase tracking-[0.12em] text-white mb-3">Module 04 — Scheduling</h3>
                <p className="text-sm text-[#8D98A3] leading-relaxed">Shift planning, staffing visibility, coverage gaps, qualification awareness, and workforce readiness.</p>
              </Link>

              <Link href="/communications" className="group bg-[#111417] p-8 flex flex-col justify-start hover:bg-[#171B1F] transition-colors relative overflow-hidden">
                <div className="absolute top-0 left-0 w-full h-[1px] bg-white/[0.06]"></div>
                <TechIcon icon={PhoneCall} className="mb-6" />
                <h3 className="text-xs font-bold uppercase tracking-[0.12em] text-white mb-3">Module 05 — Comms Command</h3>
                <p className="text-sm text-[#8D98A3] leading-relaxed">AI voice, SMS, voicemail, callback workflows, and secure billing communications built as infrastructure, not scattered alerts.</p>
              </Link>

              <Link href="/compliance" className="group bg-[#111417] p-8 flex flex-col justify-start hover:bg-[#171B1F] transition-colors relative overflow-hidden">
                <div className="absolute top-0 left-0 w-full h-[1px] bg-white/[0.06]"></div>
                <TechIcon icon={ShieldCheck} className="mb-6" />
                <h3 className="text-xs font-bold uppercase tracking-[0.12em] text-white mb-3">Module 06 — Compliance</h3>
                <p className="text-sm text-[#8D98A3] leading-relaxed">DEA/CMS-ready compliance, narcotics chain-of-custody, NEMSIS validation, HIPAA controls, and accreditation readiness.</p>
              </Link>

              <Link href="/platform" className="group bg-[#111417] p-8 flex flex-col justify-start hover:bg-[#171B1F] transition-colors relative overflow-hidden">
                <div className="absolute top-0 left-0 w-full h-[1px] bg-white/[0.06]"></div>
                <TechIcon icon={Target} className="mb-6" />
                <h3 className="text-xs font-bold uppercase tracking-[0.12em] text-white mb-3">Module 07 — Operations</h3>
                <p className="text-sm text-[#8D98A3] leading-relaxed">Operational visibility, workflow control, role-based command surfaces, and future-ready dispatch and mission coordination.</p>
              </Link>

              <Link href="/platform" className="group bg-[#111417] p-8 flex flex-col justify-start hover:bg-[#171B1F] transition-colors relative overflow-hidden">
                <div className="absolute top-0 left-0 w-full h-[1px] bg-white/[0.06]"></div>
                <TechIcon icon={TerminalSquare} className="mb-6 z-10" />
                <h3 className="text-xs font-bold uppercase tracking-[0.12em] text-white mb-3 z-10">Module 08 — System Command</h3>
                <p className="text-sm text-[#8D98A3] leading-relaxed z-10">Cross-platform visibility into revenue, communications, workflow risk, and command-level decision support.</p>
              </Link>

            </div>
          </div>
        </section>

        {/* SECURE ACCESS SECTION (TRANSPORTLINK HIGHLIGHT) */}
        <section className="py-32 relative z-20 border-b border-white/[0.04] bg-[#111417]">
          <div className="max-w-[1400px] mx-auto px-6">
            <div className="text-center mb-16">
              <div className="text-[0.6rem] font-bold tracking-[0.2em] text-[#8D98A3] uppercase mb-4 flex items-center justify-center gap-2">
                <div className="w-3 h-[1px] bg-[#F36A21]"></div>
                Portals
                <div className="w-3 h-[1px] bg-[#F36A21]"></div>
              </div>
              <h2 className="text-4xl font-black tracking-tight text-white mb-4">Role-based access into the platform</h2>
              <p className="text-lg text-[#8D98A3] max-w-2xl mx-auto">
                Structured entry points with network perimeters dividing patient access, authorized reps, and agency command. Compliance tooling is jurisdiction- and counsel-dependent.
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
        <section id="vision" className="py-32 relative z-20 border-b border-white/[0.04] bg-[#0A0C0E]">
          <div className="max-w-[1000px] mx-auto px-6 text-center">
            <div className="text-[0.65rem] font-bold tracking-[0.2em] text-[var(--color-text-muted)] uppercase mb-4">The broader vision</div>
            <h2 className="text-4xl md:text-6xl font-black tracking-tight text-white mb-8">
              A full operating system for modern public safety operations
            </h2>
            <div className="text-xl text-[var(--color-text-muted)] leading-relaxed space-y-6 font-medium">
              <p>
                FusionEMS Quantum begins with Billing Command, but the long-term vision is broader: a unified system that connects patient-facing revenue workflows, clinical documentation, operational oversight, fleet readiness, workforce scheduling, communications, compliance, and executive-level command into one modern platform.
              </p>
              <p className="text-white">
                This is not a replacement for one small tool. It is an effort to replace the fragmentation that agencies have had to tolerate for years.
              </p>
            </div>
          </div>
        </section>

      </main>

      {/* FOOTER */}
      <footer className="relative z-20">
        {/* Brand stripe */}
        <div className="h-px bg-gradient-to-r from-transparent via-[#F36A21]/40 to-transparent" />
        <div className="bg-[#0A0C0E] border-t border-white/[0.04]">
          <div className="max-w-[1600px] mx-auto px-6 py-10">
            <div className="flex flex-col md:flex-row items-start md:items-center justify-between gap-6">

              {/* Brand mark */}
              <div>
                <div className="text-[1.1rem] font-black tracking-[0.3em] text-white uppercase leading-none mb-1">
                  FQ FUSIONEMS QUANTUM
                </div>
                <div className="text-[0.55rem] font-bold tracking-[0.2em] text-[#66707A] uppercase">
                  Mission-Critical Public Safety SaaS
                </div>
              </div>

              {/* Operational status */}
              <div className="flex items-center gap-2">
                <div className="w-1.5 h-1.5 rounded-full bg-[#4E9F6E] shadow-[0_0_6px_#4E9F6E]" />
                <span className="text-[0.55rem] font-bold tracking-[0.2em] text-[#4E9F6E] uppercase">
                  Enterprise Ready
                </span>
              </div>

              {/* Nav links */}
              <div className="flex gap-8 text-[0.6rem] font-bold tracking-[0.15em] text-[#8D98A3] uppercase">
                <Link href="/login" className="hover:text-white transition-colors">Portal</Link>
                <span className="text-white/10">|</span>
                <Link href="/terms" className="hover:text-white transition-colors">Terms</Link>
                <span className="text-white/10">|</span>
                <Link href="/privacy" className="hover:text-white transition-colors">Privacy</Link>
              </div>

            </div>

            {/* Bottom bar */}
            <div className="mt-8 pt-6 border-t border-white/[0.04] flex flex-col md:flex-row items-start md:items-center justify-between gap-3">
              <div className="text-[0.55rem] font-bold tracking-[0.15em] text-[#66707A] uppercase">
                © {new Date().getFullYear()} FusionEMS Quantum. All rights reserved.
              </div>
              <div className="text-[0.5rem] text-[#66707A] max-w-lg leading-relaxed">
                FusionEMS provides compliance workflow tooling to support agency operations.
                Not legal, regulatory, or medical advice. Compliance determinations remain
                the responsibility of each agency and its authorized counsel.
              </div>
            </div>

          </div>
        </div>
      </footer>
    </div>
  );
}