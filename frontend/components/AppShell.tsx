"use client";

import React from "react";
import Link from "next/link";
import { ArrowUpRight, Shield, Wallet } from "lucide-react";

export type SystemStatus =
  | "ACTIVE"
  | "CERTIFICATION_ACTIVATION_REQUIRED"
  | "ARCHITECTURE_COMPLETE"
  | "ACTIVE_CORE_LAYER"
  | "IN_DEVELOPMENT"
  | "INFRASTRUCTURE_LAYER";

export function StatusBadge({ status, accent }: { status: SystemStatus; accent: string }) {
  return (
    <span className="inline-flex items-center gap-2  border px-3 py-1 text-xs"
      style={{ borderColor: "rgba(255,255,255,0.12)" }}>
      <span className="h-2 w-2 " style={{ background: accent }} />
      <span className="text-[rgba(255,255,255,0.78)]">{status.replaceAll("_", " ")}</span>
    </span>
  );
}

export function ModalContainer({
  open, title, body, onClose, ctaLabel
}: {
  open: boolean; title: string; body: string; onClose: () => void; ctaLabel?: string;
}) {
  if (!open) return null;
  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-[rgba(0,0,0,0.65)] p-4">
      <div className="w-full max-w-xl  border border-border bg-panel shadow-[0_0_15px_rgba(0,0,0,0.6)]">
        <div className="border-b border-border p-5">
          <div className="text-lg font-semibold">{title}</div>
        </div>
        <div className="p-5 text-sm text-muted whitespace-pre-wrap">{body}</div>
        <div className="flex justify-end gap-3 border-t border-border p-4">
          <button onClick={onClose} className=" border border-border px-4 py-2 text-sm">
            {ctaLabel ?? "Return"}
          </button>
        </div>
      </div>
    </div>
  );
}

function NavLink({ href, label }: { href: string; label: string }) {
  return (
    <Link href={href} className=" px-3 py-2 text-sm text-muted hover:text-text hover:bg-[rgba(255,255,255,0.06)]">
      {label}
    </Link>
  );
}

export default function AppShell({ children }: { children: React.ReactNode }) {
  return (
    <div className="min-h-screen bg-[#050505] text-text-primary">
      <div className="fixed inset-0 pointer-events-none opacity-60"
        style={{
          backgroundImage:
            "radial-gradient(circle at 12% 10%, rgba(255,77,0,0.14), transparent 30%), radial-gradient(circle at 88% 0%, rgba(229,57,53,0.12), transparent 28%), linear-gradient(to right, rgba(255,255,255,0.02) 1px, transparent 1px), linear-gradient(to bottom, rgba(255,255,255,0.02) 1px, transparent 1px)",
          backgroundSize: "auto, auto, 40px 40px, 40px 40px",
        }}
      />

      <div className="relative z-40 border-b border-[rgba(255,255,255,0.08)] bg-[rgba(255,77,0,0.12)]">
        <div className="mx-auto flex max-w-7xl items-center justify-between gap-4 px-5 py-2 text-[10px] uppercase tracking-[0.18em] text-[rgba(255,255,255,0.45)]">
          <span>Sovereign Operations Surface</span>
          <div className="hidden md:flex items-center gap-5">
            <span>Billing-first execution</span>
            <span>Role-based access</span>
            <span>Deny-by-default access</span>
          </div>
        </div>
      </div>

      <header className="sticky top-0 z-40 border-b border-border bg-[rgba(11,15,20,0.94)] backdrop-blur">
        <div className="mx-auto flex max-w-7xl items-center justify-between gap-4 px-5 py-4">
          <div className="flex items-center gap-3">
            <div className="h-10 w-10 border border-border bg-panel2 flex items-center justify-center font-bold chamfer-8 shadow-[0_0_24px_rgba(255,77,0,0.24)]">
              FQ
            </div>
            <div>
              <div className="text-sm font-semibold leading-4 uppercase tracking-[0.12em]">FusionEMS Quantum</div>
              <div className="text-xs text-muted uppercase tracking-[0.16em]">Public Safety Command Platform</div>
            </div>
          </div>

          <nav className="hidden lg:flex items-center gap-1">
            <NavLink href="/" label="Platform" />
            <NavLink href="/billing" label="Billing" />
            <NavLink href="/systems" label="Systems" />
            <NavLink href="/compliance" label="Compliance" />
            <NavLink href="/visibility" label="Visibility" />
            <NavLink href="/nemsis-manager" label="NEMSIS" />
            <NavLink href="/architecture" label="Architecture" />
            <NavLink href="/founder" label="Founder Command" />
            <NavLink href="/templates" label="Templates" />
            <NavLink href="/billing-command" label="Billing Command" />
            <NavLink href="/roi-funnel" label="ROI Funnel" />
            <NavLink href="/mobile-ops" label="Mobile Ops" />
            <NavLink href="/system-health" label="System Health" />
          </nav>

          <div className="flex items-center gap-2">
            <Link href="/portal/patient" className="hidden md:inline-flex items-center gap-2 border border-border px-3 py-2 text-sm text-muted hover:text-text chamfer-8 bg-panel">
              <Wallet className="w-4 h-4" />
              Pay My Bill
            </Link>
            <Link href="/billing/login" className="hidden md:inline-flex items-center gap-2 border border-border px-3 py-2 text-sm text-muted hover:text-text chamfer-8 bg-panel">
              <Shield className="w-4 h-4" />
              Billing Login
            </Link>
            <Link
              href="/founder-command"
              className="inline-flex items-center gap-2 bg-billing px-4 py-2 text-sm font-semibold text-black hover:opacity-90 chamfer-8"
            >
              Founder Command
            </Link>
          </div>
        </div>
      </header>

      <main className="relative z-10 mx-auto max-w-7xl px-5 py-8 md:py-10">
        {children}
      </main>

      <footer className="relative z-10 border-t border-border bg-[rgba(11,15,20,0.88)]">
        <div className="mx-auto max-w-7xl px-5 py-6 flex flex-col md:flex-row items-start md:items-center justify-between gap-4 text-xs text-muted">
          <div className="space-y-1">
            <div className="uppercase tracking-[0.16em] text-[rgba(255,255,255,0.38)]">FusionEMS Quantum Platform</div>
            <div>Deterministic workflows • auditable actions • integrated agency operations</div>
          </div>
          <Link href="/founder-command" className="inline-flex items-center gap-2 text-[rgba(255,255,255,0.75)] hover:text-white transition-colors uppercase tracking-[0.14em]">
            Founder Command
            <ArrowUpRight className="w-3.5 h-3.5" />
          </Link>
        </div>
      </footer>
    </div>
  );
}
