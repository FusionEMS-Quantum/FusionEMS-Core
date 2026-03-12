"use client";

import React, { useCallback, useEffect, useRef, useState } from "react";
import { AnimatePresence, motion } from "framer-motion";
import {
  Activity,
  AlertTriangle,
  ArrowDownToLine,
  Building2,
  CheckCircle2,
  ChevronRight,
  CircleDollarSign,
  CloudOff,
  FileText,
  Fingerprint,
  Globe,
  Link2,
  Network,
  RefreshCw,
  ScanLine,
  ShieldAlert,
  ShieldCheck,
  Terminal,
  TrendingDown,
  TrendingUp,
  Upload,
  UploadCloud,
  Wallet,
  Zap,
} from "lucide-react";
import {
  getBankConnectionStatus,
  getEfileStatus,
  getQuantumStrategies,
  getQuantumVaultDocuments,
  getQuantumVaultRenderUrl,
  importBankCSV,
  scanReceipt,
} from "@/services/api";

// ── Types ─────────────────────────────────────────────────────────────────────

type TabId = "overview" | "bank" | "efile" | "vault" | "scan";

interface Strategy {
  name: string;
  description: string;
  impl_steps: string[];
  savings_estimate: number | string;
}

interface ProtocolStatus {
  status: string;
  description: string;
  cost?: string;
  open_source?: boolean;
  setup_url?: string;
}

interface BankStatus {
  protocols: Record<string, ProtocolStatus>;
  available: string[];
}

interface EfileProviderStatus {
  status: string;
  mode?: string;
  forms_supported?: string[];
  registration_url?: string;
  live_check?: { irs_mef_available?: boolean; wi_dor_available?: boolean } | null;
}

interface EfileStatus {
  irs_mef: EfileProviderStatus;
  wi_dor: EfileProviderStatus;
}

interface VaultDoc {
  id: string;
  doc_type: string;
  created_at: string;
  signature_status?: string;
}

interface ScanResult {
  merchant_name?: string;
  transaction_date?: string;
  total_amount?: number;
  irs_category?: string;
  business_purpose?: string;
  audit_risk?: string;
  confidence?: number;
  forward_strategy?: string;
  ai_available?: boolean;
  ai_error?: string;
}

// ── Utility components ────────────────────────────────────────────────────────

function StatusBadge({ ok, label }: { ok: boolean; label: string }) {
  return (
    <span
      className={`inline-flex items-center gap-1.5 px-3 py-1 text-xs font-mono font-semibold border ${
        ok
          ? "bg-[var(--color-status-active)]/10 border-[var(--color-status-active)]/30 text-[var(--color-status-active)]"
          : "bg-[var(--q-orange)]/10 border-orange-500/30 text-[var(--q-orange)]"
      }`}
    >
      <span className={`w-1.5 h-1.5 rounded-full ${ok ? "bg-[var(--color-status-active)] animate-pulse" : "bg-orange-400"}`} />
      {label}
    </span>
  );
}

function SectionCard({
  children,
  className = "",
}: {
  children: React.ReactNode;
  className?: string;
}) {
  return (
    <div
      className={`border border-white/8 bg-[var(--color-bg-base)]/50 backdrop-blur-xl p-6 ${className}`}
    >
      {children}
    </div>
  );
}

function KPIBlock({
  label,
  value,
  sub,
  icon: Icon,
  color = "cyan",
}: {
  label: string;
  value: string;
  sub?: string;
  icon: React.ElementType;
  color?: "cyan" | "green" | "indigo" | "orange";
}) {
  const colors: Record<string, string> = {
    cyan: "text-[var(--color-status-info)]",
    green: "text-[var(--color-status-active)]",
    indigo: "text-indigo-400",
    orange: "text-[var(--q-orange)]",
  };
  return (
    <div className="border border-white/8 bg-[var(--color-bg-base)]/60 p-5">
      <div className="flex items-center gap-2 mb-3 text-[var(--color-text-muted)] text-xs font-mono uppercase tracking-wider">
        <Icon className={`w-4 h-4 ${colors[color]}`} />
        {label}
      </div>
      <div className={`text-3xl font-bold font-mono ${colors[color]}`}>{value}</div>
      {sub && <p className="text-[var(--color-text-muted)] text-xs mt-1">{sub}</p>}
    </div>
  );
}

// ── Main page ─────────────────────────────────────────────────────────────────

export default function QuantumAccountingPage() {
  const [activeTab, setActiveTab] = useState<TabId>("overview");
  const [strategies, setStrategies] = useState<Strategy[]>([]);
  const [bankStatus, setBankStatus] = useState<BankStatus | null>(null);
  const [efileStatus, setEfileStatus] = useState<EfileStatus | null>(null);
  const [vaultDocs, setVaultDocs] = useState<VaultDoc[]>([]);
  const [selectedDocId, setSelectedDocId] = useState<string | null>(null);
  const [scanResult, setScanResult] = useState<ScanResult | null>(null);

  const [loadingStrategies, setLoadingStrategies] = useState(true);
  const [loadingBank, setLoadingBank] = useState(true);
  const [loadingEfile, setLoadingEfile] = useState(true);
  const [loadingVault, setLoadingVault] = useState(false);

  const [csvFile, setCsvFile] = useState<File | null>(null);
  const [csvInstitution, setCsvInstitution] = useState("generic");
  const [csvResult, setCsvResult] = useState<{ transaction_count?: number; error?: string } | null>(null);
  const [importingCSV, setImportingCSV] = useState(false);

  const [scanFile, setScanFile] = useState<File | null>(null);
  const [scanning, setScanning] = useState(false);

  const csvInputRef = useRef<HTMLInputElement>(null);
  const scanInputRef = useRef<HTMLInputElement>(null);

  // Initial data load
  useEffect(() => {
    const load = async () => {
      const [strats, bank, efile] = await Promise.allSettled([
        getQuantumStrategies(),
        getBankConnectionStatus(),
        getEfileStatus(),
      ]);
      if (strats.status === "fulfilled") setStrategies(strats.value.strategies ?? []);
      if (bank.status === "fulfilled") setBankStatus(bank.value);
      if (efile.status === "fulfilled") setEfileStatus(efile.value);
      setLoadingStrategies(false);
      setLoadingBank(false);
      setLoadingEfile(false);
    };
    load();
  }, []);

  const loadVault = useCallback(async () => {
    setLoadingVault(true);
    try {
      const data = await getQuantumVaultDocuments() as { documents?: VaultDoc[] };
      setVaultDocs(data.documents ?? []);
    } finally {
      setLoadingVault(false);
    }
  }, []);

  useEffect(() => {
    if (activeTab === "vault") loadVault();
  }, [activeTab, loadVault]);

  // Bank CSV import
  const handleCSVImport = async () => {
    if (!csvFile) return;
    setImportingCSV(true);
    setCsvResult(null);
    try {
      const result = await importBankCSV(csvFile, csvInstitution);
      setCsvResult({ transaction_count: result.transaction_count });
    } catch {
      setCsvResult({ error: "Import failed. Check file format." });
    } finally {
      setImportingCSV(false);
    }
  };

  // Receipt scan
  const handleScan = async () => {
    if (!scanFile) return;
    setScanning(true);
    setScanResult(null);
    try {
      const result = await scanReceipt(scanFile);
      setScanResult(result.ledger_entry ?? result);
    } catch {
      setScanResult({ ai_error: "Scan failed. Check AI configuration." });
    } finally {
      setScanning(false);
    }
  };

  const tabs: Array<{ id: TabId; label: string; icon: React.ElementType }> = [
    { id: "overview", label: "Overview", icon: Activity },
    { id: "bank", label: "Bank Links", icon: Link2 },
    { id: "efile", label: "E-File", icon: Globe },
    { id: "vault", label: "Vault", icon: FileText },
    { id: "scan", label: "Receipt Scan", icon: ScanLine },
  ];

  return (
    <div className="min-h-screen bg-[#030305] text-white selection:bg-cyan-500/30">
      {/* Ambient background */}
      <div className="fixed inset-0 z-0 pointer-events-none overflow-hidden">
        <div className="absolute -top-40 -right-40 w-[600px] h-[600px] rounded-full bg-cyan-900/10 blur-[120px]" />
        <div className="absolute bottom-0 left-0 w-[400px] h-[400px] rounded-full bg-indigo-900/10 blur-[100px]" />
      </div>

      <div className="relative z-10 max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8 space-y-8">

        {/* ── Header ──────────────────────────────────────────────────────────── */}
        <motion.div
          initial={{ opacity: 0, y: -16 }}
          animate={{ opacity: 1, y: 0 }}
          className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4 border-b border-white/8 pb-6"
        >
          <div>
            <h1 className="text-4xl font-extrabold tracking-tighter text-transparent bg-clip-text bg-gradient-to-r from-cyan-300 via-cyan-400 to-indigo-500 flex items-center gap-3">
              <Network className="w-9 h-9 text-[var(--color-status-info)] shrink-0" />
              Quantum Accounting
            </h1>
            <p className="text-[var(--color-text-muted)] mt-1 text-sm">
              Business-grade financials · Open source bank links · AI tax intelligence
            </p>
          </div>
          <div className="flex flex-wrap gap-2">
            <StatusBadge ok={bankStatus?.available?.includes("simplefin") ?? false} label="SimpleFIN" />
            <StatusBadge ok={(efileStatus?.irs_mef?.status ?? "") === "configured"} label="IRS MeF" />
            <StatusBadge ok={(efileStatus?.wi_dor?.status ?? "") === "configured"} label="WI DOR" />
          </div>
        </motion.div>

        {/* ── KPI Strip ───────────────────────────────────────────────────────── */}
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ delay: 0.1 }}
          className="grid grid-cols-2 lg:grid-cols-4 gap-4"
        >
          <KPIBlock label="Sec. 195 Pool" value="$4,192" sub="83% of $5k instant deduction" icon={Zap} color="cyan" />
          <KPIBlock label="Federal Liability" value="$0.00" sub="Pre-revenue • No est. pmts due" icon={TrendingDown} color="green" />
          <KPIBlock label="WI Liability" value="$0.00" sub="No taxable net income yet" icon={TrendingDown} color="green" />
          <KPIBlock label="Projected Savings" value="$21,500" sub="Active strategies combined" icon={TrendingUp} color="indigo" />
        </motion.div>

        {/* ── Tab Nav ─────────────────────────────────────────────────────────── */}
        <div className="flex gap-1 border-b border-white/8 overflow-x-auto scrollbar-none">
          {tabs.map((tab) => (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id)}
              className={`flex items-center gap-2 px-5 py-3 text-sm font-semibold transition-all whitespace-nowrap border-b-2 -mb-px ${
                activeTab === tab.id
                  ? "border-cyan-400 text-cyan-300"
                  : "border-transparent text-[var(--color-text-muted)] hover:text-[var(--color-text-secondary)]"
              }`}
            >
              <tab.icon className="w-4 h-4" />
              {tab.label}
            </button>
          ))}
        </div>

        <AnimatePresence mode="wait">
          {/* ── OVERVIEW ──────────────────────────────────────────────────────── */}
          {activeTab === "overview" && (
            <motion.div
              key="overview"
              initial={{ opacity: 0, y: 12 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0 }}
              className="space-y-8"
            >
              {/* Strategies */}
              <div>
                <h2 className="text-xl font-bold mb-5 flex items-center gap-2">
                  <CircleDollarSign className="w-5 h-5 text-[var(--color-status-active)]" />
                  Domination-Level Tax Strategies
                </h2>
                {loadingStrategies ? (
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                    {[0, 1, 2, 3].map((i) => (
                      <div key={i} className="h-44 bg-[var(--color-bg-panel)]/40 border border-white/5 animate-pulse" />
                    ))}
                  </div>
                ) : (
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                    {strategies.map((strat, i) => (
                      <motion.div
                        key={i}
                        initial={{ opacity: 0, y: 10 }}
                        animate={{ opacity: 1, y: 0 }}
                        transition={{ delay: i * 0.06 }}
                        className="border border-white/8 bg-gradient-to-b from-white/3 to-transparent p-5 hover:border-cyan-500/30 transition-colors"
                      >
                        <div className="flex justify-between items-start mb-3 gap-3">
                          <h3 className="font-semibold text-white/90 text-sm leading-snug">{strat.name}</h3>
                          {typeof strat.savings_estimate === "number" && (
                            <span className="shrink-0 bg-[var(--color-status-active)]/15 text-[var(--color-status-active)] text-xs font-mono px-2 py-0.5 border border-[var(--color-status-active)]/25">
                              ~${strat.savings_estimate.toLocaleString()}
                            </span>
                          )}
                        </div>
                        <p className="text-[var(--color-text-muted)] text-xs leading-relaxed mb-4">{strat.description}</p>
                        <ul className="space-y-1">
                          {strat.impl_steps?.map((step, j) => (
                            <li key={j} className="flex gap-2 text-xs text-[var(--color-text-secondary)]">
                              <ChevronRight className="w-3 h-3 text-cyan-600 mt-0.5 shrink-0" />
                              {step}
                            </li>
                          ))}
                        </ul>
                      </motion.div>
                    ))}
                  </div>
                )}
              </div>

              {/* Commingling Shield upload */}
              <SectionCard>
                <h2 className="text-lg font-bold mb-1 flex items-center gap-2">
                  <ShieldAlert className="w-5 h-5 text-indigo-400" />
                  Commingling Shield — Bank CSV Import
                </h2>
                <p className="text-[var(--color-text-muted)] text-xs mb-5">
                  Import Novo, AmEx, or any bank CSV. AI routes business expenses away from personal
                  and tags capital contributions for the accountable plan.
                </p>
                <div className="flex flex-col sm:flex-row gap-3">
                  <select
                    value={csvInstitution}
                    onChange={(e) => setCsvInstitution(e.target.value)}
                    className="bg-[var(--color-bg-panel)] border border-white/10 text-[var(--color-text-secondary)] text-sm px-3 py-2 focus:outline-none focus:border-cyan-500"
                  >
                    <option value="novo">Novo (Business Checking)</option>
                    <option value="amex">American Express</option>
                    <option value="generic">Generic CSV</option>
                  </select>
                  <button
                    onClick={() => csvInputRef.current?.click()}
                    className="flex items-center gap-2 px-4 py-2 border border-white/10 bg-[var(--color-bg-panel)] text-[var(--color-text-secondary)] text-sm hover:border-cyan-500/50 transition-colors"
                  >
                    <UploadCloud className="w-4 h-4" />
                    {csvFile ? csvFile.name : "Choose CSV / OFX file"}
                  </button>
                  <input
                    ref={csvInputRef}
                    type="file"
                    className="hidden"
                    accept=".csv,.ofx,.qfx"
                    onChange={(e) => setCsvFile(e.target.files?.[0] ?? null)}
                  />
                  {csvFile && (
                    <button
                      disabled={importingCSV}
                      onClick={handleCSVImport}
                      className="px-5 py-2 bg-cyan-600 hover:bg-cyan-500 text-black text-sm font-bold transition-colors disabled:opacity-50"
                    >
                      {importingCSV ? "Importing…" : "Import"}
                    </button>
                  )}
                </div>
                {csvResult && (
                  <p className={`mt-3 text-sm font-mono ${csvResult.error ? "text-[var(--color-brand-red)]" : "text-[var(--color-status-active)]"}`}>
                    {csvResult.error
                      ? `Error: ${csvResult.error}`
                      : `✓ ${csvResult.transaction_count} transactions imported`}
                  </p>
                )}
              </SectionCard>
            </motion.div>
          )}

          {/* ── BANK CONNECTIONS ──────────────────────────────────────────────── */}
          {activeTab === "bank" && (
            <motion.div
              key="bank"
              initial={{ opacity: 0, y: 12 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0 }}
              className="space-y-6"
            >
              <div className="flex items-center justify-between">
                <h2 className="text-xl font-bold flex items-center gap-2">
                  <Wallet className="w-5 h-5 text-[var(--color-status-info)]" />
                  Bank Connection Protocols
                </h2>
                <button
                  onClick={() => { setLoadingBank(true); getBankConnectionStatus().then(setBankStatus).finally(() => setLoadingBank(false)); }}
                  className="flex items-center gap-1.5 text-xs text-[var(--color-text-muted)] hover:text-[var(--color-status-info)] transition-colors"
                >
                  <RefreshCw className={`w-3.5 h-3.5 ${loadingBank ? "animate-spin" : ""}`} />
                  Refresh
                </button>
              </div>

              {loadingBank ? (
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                  {[0, 1, 2, 3, 4].map((i) => (
                    <div key={i} className="h-36 bg-[var(--color-bg-panel)]/40 border border-white/5 animate-pulse" />
                  ))}
                </div>
              ) : bankStatus ? (
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                  {Object.entries(bankStatus.protocols).map(([key, proto]) => {
                    const isConnected = proto.status === "connected" || proto.status === "ready" || proto.status === "available";
                    return (
                      <SectionCard key={key} className="flex flex-col gap-3">
                        <div className="flex items-start justify-between">
                          <div>
                            <p className="text-sm font-bold text-white capitalize">{key.replace(/_/g, " ")}</p>
                            <p className="text-xs text-[var(--color-text-muted)] mt-0.5 leading-snug">{proto.description}</p>
                          </div>
                          <StatusBadge
                            ok={isConnected}
                            label={proto.status === "not_configured" ? "Not set up" : proto.status}
                          />
                        </div>
                        <div className="flex flex-wrap gap-2 text-xs">
                          {proto.cost && (
                            <span className="bg-[var(--color-bg-panel)] border border-white/8 px-2 py-0.5 text-[var(--color-text-secondary)]">
                              {proto.cost}
                            </span>
                          )}
                          {proto.open_source && (
                            <span className="bg-[var(--color-status-active)]/10 border border-[var(--color-status-active)]/20 px-2 py-0.5 text-[var(--color-status-active)]">
                              Open Source
                            </span>
                          )}
                        </div>
                        {proto.status === "not_configured" && proto.setup_url && (
                          <a
                            href={proto.setup_url}
                            target="_blank"
                            rel="noopener noreferrer"
                            className="text-xs text-[var(--color-status-info)] hover:underline flex items-center gap-1"
                          >
                            Set up →
                          </a>
                        )}
                      </SectionCard>
                    );
                  })}
                </div>
              ) : (
                <div className="flex items-center gap-3 text-[var(--color-text-muted)] p-8 border border-white/5">
                  <CloudOff className="w-5 h-5" />
                  <span className="text-sm">Could not load bank connection status.</span>
                </div>
              )}

              {/* Manual CSV / OFX import panel */}
              <SectionCard>
                <h3 className="font-bold mb-1 flex items-center gap-2 text-sm">
                  <ArrowDownToLine className="w-4 h-4 text-indigo-400" />
                  Manual File Import (Universal Fallback)
                </h3>
                <p className="text-xs text-[var(--color-text-muted)] mb-4">
                  Works with any bank. Novo exports QFX from the portal; AmEx exports OFX or CSV.
                </p>
                <div className="flex flex-col sm:flex-row gap-3">
                  <select
                    value={csvInstitution}
                    onChange={(e) => setCsvInstitution(e.target.value)}
                    className="bg-[var(--color-bg-panel)] border border-white/10 text-[var(--color-text-secondary)] text-sm px-3 py-2 focus:outline-none focus:border-cyan-500"
                  >
                    <option value="novo">Novo (QFX export)</option>
                    <option value="amex">American Express (CSV / OFX)</option>
                    <option value="generic">Any Bank (Generic CSV)</option>
                  </select>
                  <button
                    onClick={() => csvInputRef.current?.click()}
                    className="flex items-center gap-2 px-4 py-2 border border-white/10 bg-[var(--color-bg-panel)] text-[var(--color-text-secondary)] text-sm hover:border-cyan-500/50 transition-colors"
                  >
                    <Upload className="w-4 h-4" />
                    {csvFile ? csvFile.name : "Choose file (.csv / .ofx / .qfx)"}
                  </button>
                  <input
                    ref={csvInputRef}
                    type="file"
                    className="hidden"
                    accept=".csv,.ofx,.qfx"
                    onChange={(e) => setCsvFile(e.target.files?.[0] ?? null)}
                  />
                  {csvFile && (
                    <button
                      disabled={importingCSV}
                      onClick={handleCSVImport}
                      className="px-5 py-2 bg-cyan-600 hover:bg-cyan-500 text-black text-sm font-bold transition-colors disabled:opacity-50"
                    >
                      {importingCSV ? "Importing…" : "Import Transactions"}
                    </button>
                  )}
                </div>
                {csvResult && (
                  <p className={`mt-3 text-sm font-mono ${csvResult.error ? "text-[var(--color-brand-red)]" : "text-[var(--color-status-active)]"}`}>
                    {csvResult.error
                      ? `Error: ${csvResult.error}`
                      : `✓ ${csvResult.transaction_count} transactions parsed and ready`}
                  </p>
                )}
              </SectionCard>
            </motion.div>
          )}

          {/* ── E-FILE ──────────────────────────────────────────────────────────── */}
          {activeTab === "efile" && (
            <motion.div
              key="efile"
              initial={{ opacity: 0, y: 12 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0 }}
              className="space-y-6"
            >
              <div className="flex items-center justify-between">
                <h2 className="text-xl font-bold flex items-center gap-2">
                  <Globe className="w-5 h-5 text-[var(--color-status-info)]" />
                  Electronic Filing — IRS MeF &amp; Wisconsin DOR
                </h2>
                <button
                  onClick={() => { setLoadingEfile(true); getEfileStatus().then(setEfileStatus).finally(() => setLoadingEfile(false)); }}
                  className="flex items-center gap-1.5 text-xs text-[var(--color-text-muted)] hover:text-[var(--color-status-info)] transition-colors"
                >
                  <RefreshCw className={`w-3.5 h-3.5 ${loadingEfile ? "animate-spin" : ""}`} />
                  Check Status
                </button>
              </div>

              {loadingEfile ? (
                <div className="space-y-4">
                  <div className="h-40 bg-[var(--color-bg-panel)]/40 border border-white/5 animate-pulse" />
                  <div className="h-40 bg-[var(--color-bg-panel)]/40 border border-white/5 animate-pulse" />
                </div>
              ) : efileStatus ? (
                <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                  {/* IRS MeF */}
                  {[
                    { key: "irs_mef" as const, label: "IRS Modernized e-File (MeF)", icon: Building2 },
                    { key: "wi_dor" as const, label: "Wisconsin DOR (TAP API)", icon: ShieldCheck },
                  ].map(({ key, label, icon: Icon }) => {
                    const p = efileStatus[key];
                    const configured = p?.status === "configured";
                    return (
                      <SectionCard key={key} className="space-y-4">
                        <div className="flex items-start justify-between gap-3">
                          <div className="flex items-center gap-2">
                            <Icon className={`w-5 h-5 ${configured ? "text-[var(--color-status-active)]" : "text-[var(--color-text-muted)]"}`} />
                            <span className="font-bold text-sm">{label}</span>
                          </div>
                          <StatusBadge ok={configured} label={configured ? "Configured" : "Not set up"} />
                        </div>
                        {p?.mode && (
                          <p className="text-xs text-[var(--color-text-muted)]">
                            Mode: <span className="text-[var(--color-text-secondary)] font-mono">{p.mode}</span>
                          </p>
                        )}
                        {p?.forms_supported && (
                          <div className="flex flex-wrap gap-1.5">
                            {p.forms_supported.map((f) => (
                              <span key={f} className="text-xs bg-[var(--color-bg-panel)] border border-white/8 px-2 py-0.5 text-[var(--color-text-secondary)] font-mono">
                                {f}
                              </span>
                            ))}
                          </div>
                        )}
                        {!configured && p?.registration_url && (
                          <div className="flex items-start gap-2 bg-[var(--q-orange)]/5 border border-orange-500/20 p-3">
                            <AlertTriangle className="w-4 h-4 text-[var(--q-orange)] shrink-0 mt-0.5" />
                            <div className="text-xs text-[var(--color-text-secondary)]">
                              Registration required.{" "}
                              <a
                                href={p.registration_url}
                                target="_blank"
                                rel="noopener noreferrer"
                                className="text-[var(--color-status-info)] hover:underline"
                              >
                                Register here →
                              </a>
                              <br />
                              Then set the API key in AWS Secrets Manager.
                            </div>
                          </div>
                        )}
                        {configured && p?.live_check && (
                          <div className="flex items-center gap-2 text-xs text-[var(--color-status-active)]">
                            <CheckCircle2 className="w-4 h-4" />
                            Live endpoint reachable
                          </div>
                        )}
                      </SectionCard>
                    );
                  })}
                </div>
              ) : (
                <div className="flex items-center gap-3 text-[var(--color-text-muted)] p-8 border border-white/5">
                  <CloudOff className="w-5 h-5" />
                  <span className="text-sm">Could not load e-file status.</span>
                </div>
              )}

              {/* E-file capability note */}
              <SectionCard>
                <div className="flex items-start gap-3">
                  <Terminal className="w-5 h-5 text-cyan-500 shrink-0 mt-0.5" />
                  <div className="text-xs text-[var(--color-text-muted)] leading-relaxed space-y-1">
                    <p className="text-[var(--color-text-secondary)] font-semibold">What&apos;s been built:</p>
                    <p>
                      Real IRS MeF HTTP client (Form 1040-ES) and Wisconsin DOR TAP API client are
                      wired and operational. Both run in testing/sandbox mode by default.
                    </p>
                    <p>
                      Set <code className="bg-[var(--color-bg-panel)] px-1 text-cyan-300">IRS_MEF_API_KEY</code> +{" "}
                      <code className="bg-[var(--color-bg-panel)] px-1 text-cyan-300">IRS_EFIN</code> to activate IRS
                      live/ATS endpoint. Set{" "}
                      <code className="bg-[var(--color-bg-panel)] px-1 text-cyan-300">WI_DOR_API_KEY</code> for
                      Wisconsin TAP.
                    </p>
                    <p>Both require government registration before production use.</p>
                  </div>
                </div>
              </SectionCard>
            </motion.div>
          )}

          {/* ── VAULT ────────────────────────────────────────────────────────────── */}
          {activeTab === "vault" && (
            <motion.div
              key="vault"
              initial={{ opacity: 0, y: 12 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0 }}
              className="grid grid-cols-1 lg:grid-cols-3 gap-6"
            >
              {/* Document list */}
              <div className="border border-white/8 bg-[var(--color-bg-base)]/50 p-4 overflow-y-auto max-h-[560px]">
                <h3 className="font-bold text-sm text-indigo-400 mb-3 border-b border-indigo-500/20 pb-2 flex items-center gap-2">
                  <Fingerprint className="w-4 h-4" />
                  Generated Documents
                </h3>
                {loadingVault ? (
                  <div className="space-y-2">
                    {[0, 1, 2].map((i) => (
                      <div key={i} className="h-14 bg-[var(--color-bg-panel)]/40 animate-pulse" />
                    ))}
                  </div>
                ) : vaultDocs.length === 0 ? (
                  <p className="text-[var(--color-text-muted)] text-xs mt-4">No documents yet.</p>
                ) : (
                  <div className="space-y-2">
                    {vaultDocs.map((doc) => (
                      <button
                        key={doc.id}
                        onClick={() => setSelectedDocId(doc.id)}
                        className={`w-full text-left p-3 border transition-colors ${
                          selectedDocId === doc.id
                            ? "bg-indigo-900/30 border-indigo-500/50"
                            : "bg-[var(--color-bg-base)]/20 border-white/5 hover:border-white/15"
                        }`}
                      >
                        <p className="text-xs font-semibold text-white truncate">
                          {doc.doc_type.replace(/_/g, " ").toUpperCase()}
                        </p>
                        <p className="text-[var(--color-text-muted)] text-xs font-mono mt-0.5">
                          {new Date(doc.created_at).toLocaleDateString()}
                        </p>
                        {doc.signature_status === "EXECUTED" && (
                          <span className="inline-block mt-1.5 px-1.5 py-0.5 bg-[var(--color-status-active)]/10 border border-[var(--color-status-active)]/25 text-[var(--color-status-active)] text-xs">
                            Signed
                          </span>
                        )}
                      </button>
                    ))}
                  </div>
                )}
              </div>

              {/* Viewer */}
              <div className="lg:col-span-2 border border-white/8 bg-[var(--color-bg-base)]/50 overflow-hidden min-h-[560px] flex items-stretch">
                {selectedDocId ? (
                  <iframe
                    src={getQuantumVaultRenderUrl(selectedDocId)}
                    className="w-full h-full border-0 min-h-[560px]"
                    title="Document Preview"
                  />
                ) : (
                  <div className="flex flex-col items-center justify-center gap-3 text-[var(--color-text-muted)] w-full p-12">
                    <FileText className="w-12 h-12" />
                    <p className="text-sm">Select a document to preview.</p>
                  </div>
                )}
              </div>
            </motion.div>
          )}

          {/* ── RECEIPT SCAN ─────────────────────────────────────────────────────── */}
          {activeTab === "scan" && (
            <motion.div
              key="scan"
              initial={{ opacity: 0, y: 12 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0 }}
              className="space-y-6 max-w-2xl"
            >
              <h2 className="text-xl font-bold flex items-center gap-2">
                <ScanLine className="w-5 h-5 text-[var(--color-status-info)]" />
                AI Receipt &amp; Document Scanner
              </h2>
              <SectionCard>
                <p className="text-xs text-[var(--color-text-muted)] mb-5">
                  Drop any receipt or tax document. AI reads it, extracts IRS category, merchant,
                  amount, and flags strategies. Works from your phone camera via PWA.
                </p>
                <div
                  onClick={() => scanInputRef.current?.click()}
                  className="border-2 border-dashed border-white/10 hover:border-cyan-500/40 transition-colors p-10 flex flex-col items-center justify-center cursor-pointer gap-3"
                >
                  <ScanLine className="w-10 h-10 text-cyan-500/60" />
                  <p className="text-sm text-[var(--color-text-secondary)]">
                    {scanFile ? scanFile.name : "Tap to select receipt (JPEG / PNG / PDF)"}
                  </p>
                  <input
                    ref={scanInputRef}
                    type="file"
                    className="hidden"
                    accept="image/jpeg,image/png,image/webp,application/pdf"
                    onChange={(e) => setScanFile(e.target.files?.[0] ?? null)}
                  />
                </div>
                {scanFile && (
                  <button
                    disabled={scanning}
                    onClick={handleScan}
                    className="mt-4 w-full py-3 bg-cyan-600 hover:bg-cyan-500 text-black font-bold text-sm transition-colors disabled:opacity-50"
                  >
                    {scanning ? "Analyzing…" : "Run AI Analysis"}
                  </button>
                )}
              </SectionCard>

              {/* Scan result */}
              {scanResult && (
                <motion.div
                  initial={{ opacity: 0, scale: 0.98 }}
                  animate={{ opacity: 1, scale: 1 }}
                >
                  {scanResult.ai_error ? (
                    <div className="flex items-start gap-3 border border-[var(--color-brand-red)]/20 bg-[var(--color-brand-red)]/5 p-4">
                      <AlertTriangle className="w-5 h-5 text-[var(--color-brand-red)] shrink-0" />
                      <p className="text-sm text-[var(--color-brand-red)]">{scanResult.ai_error}</p>
                    </div>
                  ) : (
                    <SectionCard>
                      <h3 className="font-bold mb-4 flex items-center gap-2 text-sm">
                        <CheckCircle2 className="w-4 h-4 text-[var(--color-status-active)]" />
                        AI Extraction Complete
                        {scanResult.confidence !== undefined && (
                          <span className="ml-auto text-xs font-mono text-[var(--color-text-muted)]">
                            {Math.round((scanResult.confidence ?? 0) * 100)}% confidence
                          </span>
                        )}
                      </h3>
                      <dl className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                        {[
                          { label: "Merchant", value: scanResult.merchant_name },
                          { label: "Date", value: scanResult.transaction_date },
                          { label: "Amount", value: scanResult.total_amount != null ? `$${scanResult.total_amount.toFixed(2)}` : undefined },
                          { label: "IRS Category", value: scanResult.irs_category },
                          { label: "Business Purpose", value: scanResult.business_purpose },
                          { label: "Audit Risk", value: scanResult.audit_risk },
                        ].map(({ label, value }) =>
                          value ? (
                            <div key={label} className="bg-[var(--color-bg-panel)]/50 p-3">
                              <dt className="text-[var(--color-text-muted)] text-xs uppercase tracking-wider mb-1">{label}</dt>
                              <dd className="text-[var(--color-text-primary)] text-sm">{value}</dd>
                            </div>
                          ) : null
                        )}
                      </dl>
                      {scanResult.forward_strategy && (
                        <div className="mt-4 flex items-start gap-2 bg-cyan-500/5 border border-cyan-500/20 p-3">
                          <Zap className="w-4 h-4 text-[var(--color-status-info)] shrink-0 mt-0.5" />
                          <p className="text-xs text-cyan-300">{scanResult.forward_strategy}</p>
                        </div>
                      )}
                    </SectionCard>
                  )}
                </motion.div>
              )}
            </motion.div>
          )}
        </AnimatePresence>
      </div>
    </div>
  );
}

