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
    <span
      className="inline-flex items-center gap-2 border px-3 py-1 text-xs"
      style={{ borderColor: "rgba(255,255,255,0.12)", backgroundColor: "rgba(255,255,255,0.02)" }}
    >
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
    <Link
      href={href}
      className="px-3 py-2 text-xs font-bold tracking-[0.12em] uppercase text-[var(--color-text-muted)] hover:text-[var(--color-text-primary)] hover:bg-white/[0.04] transition-colors"
    >
      {label}
    </Link>
  );
}

export default function AppShell({ children }: { children: React.ReactNode }) {
  const primaryNav = [
    { href: "/dashboard", label: "Command" },
    { href: "/billing", label: "Billing" },
    { href: "/compliance", label: "Compliance" },
    { href: "/systems", label: "Systems" },
    { href: "/founder-command", label: "Founder" },
    { href: "/nemsis-manager", label: "NEMSIS" },
  ];

  const railNav = [
    { href: "/dashboard", label: "Operations Dashboard" },
    { href: "/billing-command", label: "Billing Command" },
    { href: "/compliance", label: "Compliance Command" },
    { href: "/system-health", label: "System Health" },
    { href: "/transportlink/dashboard", label: "TransportLink" },
    { href: "/founder", label: "Founder Workspace" },
  ];

  return (
    <div className="min-h-screen bg-[var(--color-bg-base)] text-[var(--color-text-primary)]">
      <div
        className="fixed inset-0 pointer-events-none opacity-50"
        style={{
          backgroundImage:
            "linear-gradient(rgba(255,255,255,0.018) 1px, transparent 1px), linear-gradient(90deg, rgba(255,255,255,0.018) 1px, transparent 1px)",
          backgroundSize: "72px 72px",
        }}
      />

      <div className="relative z-40 border-b border-white/[0.06] bg-[var(--color-bg-base)]">
        <div className="mx-auto flex max-w-[1600px] items-center justify-between gap-4 px-5 py-2 text-[10px] font-bold uppercase tracking-[0.2em] text-[var(--color-text-muted)]">
          <span>FusionEMS Quantum</span>
          <div className="hidden md:flex items-center gap-5">
            <span>Production Command Surface</span>
          </div>
        </div>
      </div>

      <header className="sticky top-0 z-40 border-b border-white/[0.06] bg-[var(--color-surface-primary)]/95 backdrop-blur">
        <div className="mx-auto flex max-w-[1600px] items-center justify-between gap-4 px-5 py-4">
          <div className="flex items-center gap-3">
            <div className="h-10 w-10 border border-white/[0.10] bg-[var(--color-surface-secondary)] flex items-center justify-center font-black tracking-wide shadow-[0_0_16px_rgba(243,106,33,0.22)]">
              FQ
            </div>
            <div>
              <div className="text-sm font-black leading-4 uppercase tracking-[0.16em]">FusionEMS Quantum</div>
              <div className="text-[10px] text-[var(--color-text-muted)] uppercase tracking-[0.18em]">Production Command Surface</div>
            </div>
            <span className="hidden lg:inline-flex items-center border border-white/[0.10] px-2 py-1 text-[10px] font-bold tracking-[0.14em] uppercase text-[var(--color-brand-orange)]">
              PRODUCTION
            </span>
          </div>

          <nav className="hidden lg:flex items-center gap-1">
            {primaryNav.map((item) => (
              <NavLink key={item.href} href={item.href} label={item.label} />
            ))}
          </nav>

          <div className="flex items-center gap-2">
            <Link href="/portal/patient" className="hidden md:inline-flex items-center gap-2 border border-white/[0.10] px-3 py-2 text-xs font-bold tracking-[0.1em] uppercase text-[var(--color-text-muted)] hover:text-[var(--color-text-primary)] bg-[var(--color-surface-secondary)]">
              <Wallet className="w-4 h-4" />
              Pay My Bill
            </Link>
            <Link href="/billing/login" className="hidden md:inline-flex items-center gap-2 border border-white/[0.10] px-3 py-2 text-xs font-bold tracking-[0.1em] uppercase text-[var(--color-text-muted)] hover:text-[var(--color-text-primary)] bg-[var(--color-surface-secondary)]">
              <Shield className="w-4 h-4" />
              Billing Login
            </Link>
            <Link
              href="/founder-command"
              className="inline-flex items-center gap-2 bg-[var(--color-brand-orange)] px-4 py-2 text-xs font-black tracking-[0.14em] uppercase text-black hover:bg-[var(--color-orange-hover)] transition-colors"
            >
              Founder Command
            </Link>
          </div>
        </div>
      </header>

      <main className="relative z-10 mx-auto max-w-[1600px] px-5 py-8 md:py-10 lg:grid lg:grid-cols-[260px_1fr] lg:gap-6">
        <aside className="hidden lg:block">
          <div className="sticky top-[96px] border border-white/[0.06] bg-[var(--color-surface-primary)] p-3">
            <div className="mb-3 px-2 text-[10px] font-bold uppercase tracking-[0.2em] text-[var(--color-text-muted)]">Command Rail</div>
            <div className="flex flex-col gap-1">
              {railNav.map((item) => (
                <Link
                  key={item.href}
                  href={item.href}
                  className="px-3 py-2 text-[11px] font-bold uppercase tracking-[0.14em] text-[var(--color-text-secondary)] border border-transparent hover:border-white/[0.08] hover:bg-[var(--color-surface-secondary)] transition-colors"
                >
                  {item.label}
                </Link>
              ))}
            </div>
          </div>
        </aside>

        <section className="min-w-0">{children}</section>
      </main>

      <footer className="relative z-10 border-t border-white/[0.06] bg-[var(--color-surface-primary)]">
        <div className="mx-auto max-w-[1600px] px-5 py-6 flex flex-col md:flex-row items-start md:items-center justify-between gap-4 text-xs text-[var(--color-text-muted)]">
          <div className="space-y-1">
            <div className="uppercase tracking-[0.16em] text-[rgba(255,255,255,0.45)]">FusionEMS Quantum Platform</div>
            <div>Deterministic workflows • auditable actions • integrated agency operations</div>
          </div>
          <Link href="/founder-command" className="inline-flex items-center gap-2 text-[rgba(255,255,255,0.78)] hover:text-white transition-colors uppercase tracking-[0.14em]">
            Founder Command
            <ArrowUpRight className="w-3.5 h-3.5" />
          </Link>
        </div>
      </footer>
    </div>
  );
}
