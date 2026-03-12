'use client';

import Link from 'next/link';
import { BILLING_PHONE_DISPLAY, BILLING_PHONE_TEL } from '@/lib/phone';

const ACTIONS = [
  { href: '/portal/patient/pay', title: 'Pay My Bill', desc: 'Securely pay your balance online', primary: true },
  { href: '/portal/patient/invoices', title: 'View Statement', desc: 'Review your current account and balance', primary: false },
  { href: '/portal/patient/login', title: 'Log In', desc: 'Access your full account portal', primary: false },
  { href: '/portal/patient/lookup', title: 'Look Up Account', desc: 'Find your statement by name & DOB', primary: false },
  { href: '/portal/patient/support', title: 'Get Billing Help', desc: 'Chat, call, or request support', primary: false },
  { href: '/portal/patient/receipts', title: 'Download Receipt', desc: 'Access your payment receipts', primary: false },
];

function HexLogo() {
  return (
    <svg width="40" height="40" viewBox="0 0 36 36" fill="none">
      <polygon points="18,2 33,10 33,26 18,34 3,26 3,10" fill="var(--q-orange)" />
      <text x="18" y="23" textAnchor="middle" fill="var(--color-bg-base)" fontSize="12" fontWeight="900" fontFamily="sans-serif">FQ</text>
    </svg>
  );
}

export default function PatientPortalEntryPage() {
  return (
    <div className="min-h-screen bg-[var(--color-bg-base)] text-[var(--color-text-primary)] font-sans relative overflow-hidden">
      {/* Background glow and grid */}
      <div className="absolute top-0 left-0 w-full h-[500px] pointer-events-none" style={{ background: 'linear-gradient(to bottom, rgba(255,106,0,0.06), transparent)' }} />
      <div className="absolute inset-0 pointer-events-none" style={{ backgroundImage: 'linear-gradient(rgba(255,255,255,0.015) 1px,transparent 1px),linear-gradient(90deg,rgba(255,255,255,0.015) 1px,transparent 1px)', backgroundSize: '48px 48px' }} />

      <div className="relative z-10 max-w-[1100px] mx-auto px-5 pb-20">
        <header className="flex flex-wrap items-center justify-between py-7 pb-12 gap-4">
          <div className="flex items-center gap-3.5">
            <HexLogo />
            <div>
              <div className="text-base font-black uppercase tracking-[0.15em] leading-none">
                FUSION<span className="text-[var(--q-orange)]">EMS</span>
              </div>
              <div className="text-[9px] font-bold text-[var(--color-text-muted)] uppercase tracking-[0.3em] mt-1">
                PATIENT BILLING PORTAL
              </div>
            </div>
          </div>
          <div className="flex gap-3">
            <Link href="/portal/patient/login" className="px-4 py-2 border border-[var(--color-border-default)] text-[var(--color-text-primary)] text-[11px] font-bold uppercase tracking-[0.12em] chamfer-4 bg-transparent hover:border-[var(--color-text-muted)] transition-colors">
              Patient Login
            </Link>
            <Link href="/portal/patient/pay" className="px-4 py-2 border border-[var(--q-orange)] text-black text-[11px] font-bold uppercase tracking-[0.12em] chamfer-4 bg-[var(--q-orange)] transition-colors" style={{ boxShadow: '0 0 20px rgba(255,106,0,0.2)' }}>
              Pay Now
            </Link>
          </div>
        </header>

        <section className="text-center mb-14 pt-4">
          <div className="inline-flex items-center gap-2 bg-[rgba(16,185,129,0.08)] border border-[rgba(16,185,129,0.2)] text-[var(--color-status-active)] text-[10px] font-bold uppercase tracking-[0.2em] px-3.5 py-1.5 mb-7 chamfer-4">
            <span className="w-1.5 h-1.5 rounded-full bg-[var(--color-status-active)] animate-pulse" />
            SECURE PORTAL ONLINE
          </div>
          <h1 className="text-[clamp(2rem,5vw,3.2rem)] font-black leading-[1.1] tracking-[-0.02em] mb-4">
            Manage your account.
          </h1>
          <p className="text-base text-[var(--color-text-muted)] max-w-[560px] mx-auto leading-[1.7] mb-11">
            Access your statements, pay securely online, or setup a flexible payment plan. Please have your Statement ID and Date of Birth ready.
          </p>
        </section>

        <section>
          <div className="grid grid-cols-2 md:grid-cols-3 gap-3 mb-14">
            {ACTIONS.map((a, i) => (
              <Link key={i} href={a.href} className={`block p-6 chamfer-4 border transition-colors ${a.primary ? 'bg-[rgba(255,106,0,0.07)] border-[rgba(255,106,0,0.28)] hover:border-[rgba(255,106,0,0.5)]' : 'bg-[var(--color-bg-surface)] border-[var(--color-border-default)] hover:border-[var(--color-text-muted)]'}`} style={a.primary ? { boxShadow: '0 0 30px rgba(255,106,0,0.06)' } : {}}>
                <div className="w-[38px] h-[38px] flex items-center justify-center bg-[rgba(255,106,0,0.1)] border border-[rgba(255,106,0,0.2)] mb-3.5 chamfer">
                  <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="var(--q-orange)" strokeWidth="2"><rect x="3" y="3" width="18" height="18" rx="2" /></svg>
                </div>
                <div className="text-[12px] font-bold uppercase tracking-[0.08em] mb-1.5 text-[var(--color-text-primary)]">{a.title}</div>
                <div className="text-[12px] text-[var(--color-text-muted)] leading-[1.5]">{a.desc}</div>
              </Link>
            ))}
          </div>
        </section>

        <div className="h-[1px] bg-[var(--color-border-default)] my-10" />

        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-5 mb-11">
          <div className="bg-[var(--color-bg-surface)] border border-[var(--color-border-default)] p-6 chamfer-4">
            <div className="text-[10px] font-bold uppercase tracking-[0.2em] text-[var(--color-text-muted)] mb-2">Pay Online</div>
            <div className="font-bold mb-2">Secure Hosted Payment</div>
            <div className="text-[12px] text-[var(--color-text-muted)] leading-[1.6] mb-3.5">
              Pay securely using our hosted payment portal. FusionEMS never stores your card data.
            </div>
            <Link href="/portal/patient/pay" className="text-[var(--q-orange)] text-[11px] font-bold uppercase tracking-[0.1em]">Pay Online →</Link>
          </div>
          <div className="bg-[var(--color-bg-surface)] border border-[var(--color-border-default)] p-6 chamfer-4">
            <div className="text-[10px] font-bold uppercase tracking-[0.2em] text-[var(--color-text-muted)] mb-2">Pay by Phone</div>
            <div className="font-bold mb-2">Billing Support Line</div>
            <div className="text-[12px] text-[var(--color-text-muted)] leading-[1.6] mb-3.5">
              AI-assisted support 24/7. Human billing specialists available Mon–Fri 8am–6pm.
            </div>
            <a href={BILLING_PHONE_TEL} className="text-[var(--q-orange)] text-[15px] font-black">{BILLING_PHONE_DISPLAY}</a>
          </div>
          <div className="bg-[var(--color-bg-surface)] border border-[var(--color-border-default)] p-6 chamfer-4">
            <div className="text-[10px] font-bold uppercase tracking-[0.2em] text-[var(--color-text-muted)] mb-2">Pay by Mail</div>
            <div className="font-bold mb-2">Check Payment Instructions</div>
            <div className="text-[12px] text-[var(--color-text-muted)] leading-[1.6] mb-3.5">
              Mail your check directly to the agency remittance address. Include your Statement ID in the memo line.
            </div>
            <Link href="/portal/patient/support?type=check-instructions" className="text-[var(--q-orange)] text-[11px] font-bold uppercase tracking-[0.1em]">Get Mailing Address →</Link>
          </div>
          <div className="bg-[var(--color-bg-surface)] border border-[var(--color-border-default)] p-6 chamfer-4">
            <div className="text-[10px] font-bold uppercase tracking-[0.2em] text-[var(--color-text-muted)] mb-2">Payment Plans</div>
            <div className="font-bold mb-2">Flexible Installments</div>
            <div className="text-[12px] text-[var(--color-text-muted)] leading-[1.6] mb-3.5">
              Set up a payment plan that works for your budget. View schedule, simulate options, and enroll online.
            </div>
            <Link href="/portal/patient/payment-plans" className="text-[var(--q-orange)] text-[11px] font-bold uppercase tracking-[0.1em]">View Plans →</Link>
          </div>
        </div>

        <div className="flex flex-wrap items-center justify-center gap-7 pt-7 border-t border-[var(--color-border-default)] text-center">
          {[
            ['🔒', 'Secure & Encrypted'],
            ['✓', 'No Card Data Stored'],
            ['🏥', 'HIPAA-Conscious'],
            ['📞', 'Live Support Available']
          ].map(([icon, label]) => (
            <div key={label} className="flex items-center gap-1.5 text-[11px] font-semibold uppercase tracking-[0.08em] text-[var(--color-text-muted)]">
              <span>{icon}</span><span>{label}</span>
            </div>
          ))}
          <div className="w-full text-center mt-4">
            <span className="text-[10px] uppercase tracking-[0.15em] text-[var(--color-text-muted)]">
              © {new Date().getFullYear()} FusionEMS Quantum · Secure Billing Infrastructure
            </span>
          </div>
        </div>
      </div>
    </div>
  );
}
