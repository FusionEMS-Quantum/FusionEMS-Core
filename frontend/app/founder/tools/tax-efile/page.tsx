'use client';

import Link from 'next/link';
import { useCallback, useEffect, useMemo, useState } from 'react';
import {
  ArrowLeft,
  Landmark,
  RefreshCw,
  Shield,
  Upload,
  Wallet,
  Receipt,
  Database,
  ExternalLink,
} from 'lucide-react';
import {
  connectSimpleFIN,
  getBankConnectionStatus,
  getEfileStatus,
  getSimpleFINAccounts,
  importBankCSV,
  importBankOFX,
  submitFederalEstimatedTax,
  submitWisconsinForm1,
} from '@/services/api';

type LiveCheck = {
  http_status?: number;
  mode?: string;
  message?: string;
  irs_mef_available?: boolean;
  wi_dor_available?: boolean;
};

type EfileProviderStatus = {
  provider: string;
  status: string;
  mode: string;
  endpoint: string;
  registration_url: string;
  forms_supported?: string[];
  live_check?: LiveCheck | null;
};

type EfileDashboard = {
  irs_mef: EfileProviderStatus;
  wi_dor: EfileProviderStatus;
};

type BankProtocolStatus = {
  status: string;
  description: string;
  cost?: string;
  open_source?: boolean;
  library?: string;
  supported_formats?: string[];
  setup_url?: string;
};

type BankStatusPayload = {
  available: string[];
  protocols: Record<string, BankProtocolStatus>;
};

type SubmissionResponse = {
  status: string;
  confirmation_number?: string | null;
  timestamp?: string | null;
  errors?: string[];
};

type ImportResponse = {
  transaction_count?: number;
  protocol?: string;
  institution?: string;
  accounts?: Array<Record<string, unknown>>;
  transactions?: Array<Record<string, unknown>>;
};

const inputCls =
  'w-full rounded-none border border-white/10 bg-black/50 px-3 py-2 text-sm text-white outline-none transition focus:border-[var(--color-brand-orange)]';
const labelCls = 'mb-1 block text-[10px] font-bold uppercase tracking-[0.16em] text-[var(--color-text-muted)]';

function statusTone(status: string): string {
  switch (status) {
    case 'configured':
    case 'connected':
    case 'ready':
    case 'accepted':
      return 'text-emerald-400';
    case 'available':
    case 'sandbox':
    case 'ats_testing':
    case 'pending':
      return 'text-sky-400';
    case 'not_configured':
      return 'text-amber-400';
    case 'rejected':
    case 'error':
      return 'text-red-400';
    default:
      return 'text-zinc-300';
  }
}

function normalizeError(error: unknown): string {
  if (error instanceof Error && error.message) {
    return error.message;
  }
  return 'Unexpected founder tax tool error';
}

function ProviderCard({ provider }: { provider: EfileProviderStatus }) {
  const live = provider.live_check;
  const reachable = typeof live?.irs_mef_available === 'boolean'
    ? live.irs_mef_available
    : typeof live?.wi_dor_available === 'boolean'
      ? live.wi_dor_available
      : null;

  return (
    <div className="border border-white/10 bg-[var(--color-bg-panel)] p-5">
      <div className="flex items-start justify-between gap-4">
        <div>
          <div className="text-[10px] font-bold uppercase tracking-[0.18em] text-[var(--color-text-muted)]">
            {provider.provider}
          </div>
          <div className={`mt-2 text-sm font-black uppercase tracking-[0.12em] ${statusTone(provider.status)}`}>
            {provider.status.replaceAll('_', ' ')}
          </div>
        </div>
        <div className={`text-xs font-mono ${statusTone(provider.mode)}`}>{provider.mode}</div>
      </div>

      <div className="mt-4 space-y-2 text-sm text-zinc-300">
        <div>
          <span className="text-zinc-500">Endpoint:</span> {provider.endpoint}
        </div>
        <div>
          <span className="text-zinc-500">Reachability:</span>{' '}
          {reachable === null ? 'not probed' : reachable ? 'reachable' : 'unreachable'}
        </div>
        {typeof live?.http_status === 'number' && (
          <div>
            <span className="text-zinc-500">HTTP:</span> {live.http_status}
          </div>
        )}
        {live?.message && (
          <div className="text-amber-300">{live.message}</div>
        )}
        {provider.forms_supported && provider.forms_supported.length > 0 && (
          <div>
            <span className="text-zinc-500">Forms:</span> {provider.forms_supported.join(', ')}
          </div>
        )}
      </div>

      <a
        href={provider.registration_url}
        target="_blank"
        rel="noreferrer"
        className="mt-4 inline-flex items-center gap-2 text-xs font-semibold uppercase tracking-[0.14em] text-[var(--color-status-info)] hover:text-white"
      >
        Registration <ExternalLink className="h-3.5 w-3.5" />
      </a>
    </div>
  );
}

export default function FounderTaxEfilePage() {
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [efileStatus, setEfileStatus] = useState<EfileDashboard | null>(null);
  const [bankStatus, setBankStatus] = useState<BankStatusPayload | null>(null);
  const [simplefinToken, setSimplefinToken] = useState('');
  const [simplefinResult, setSimplefinResult] = useState<string | null>(null);
  const [simplefinSyncSummary, setSimplefinSyncSummary] = useState<string | null>(null);
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [importInstitution, setImportInstitution] = useState('generic');
  const [importResult, setImportResult] = useState<ImportResponse | null>(null);
  const [importBusy, setImportBusy] = useState(false);
  const [federalBusy, setFederalBusy] = useState(false);
  const [wisconsinBusy, setWisconsinBusy] = useState(false);
  const [federalResult, setFederalResult] = useState<SubmissionResponse | null>(null);
  const [wisconsinResult, setWisconsinResult] = useState<SubmissionResponse | null>(null);
  const [federalForm, setFederalForm] = useState({
    tax_year: new Date().getFullYear(),
    quarter: 1 as 1 | 2 | 3 | 4,
    filer_ssn: '',
    first_name: '',
    last_name: '',
    payment_amount: '0.00',
  });
  const [wisconsinForm, setWisconsinForm] = useState({
    tax_year: new Date().getFullYear(),
    filer_ssn: '',
    first_name: '',
    last_name: '',
    street: '',
    city: '',
    zip_code: '',
    wi_adjusted_gross_income: '0.00',
    wi_exemptions: '700.00',
    wi_credits: '0.00',
    wi_withholding: '0.00',
    net_taxable_income: '0.00',
  });

  const loadDashboard = useCallback(async () => {
    setError(null);
    setRefreshing(true);
    try {
      const [efile, bank] = await Promise.all([getEfileStatus(), getBankConnectionStatus()]);
      setEfileStatus(efile as EfileDashboard);
      setBankStatus(bank as BankStatusPayload);
    } catch (loadError: unknown) {
      setError(normalizeError(loadError));
    } finally {
      setRefreshing(false);
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    loadDashboard().catch(() => undefined);
  }, [loadDashboard]);

  const protocolEntries = useMemo(
    () => Object.entries(bankStatus?.protocols ?? {}),
    [bankStatus],
  );

  async function handleSimplefinConnect(): Promise<void> {
    setError(null);
    setSimplefinResult(null);
    try {
      const response = await connectSimpleFIN(simplefinToken.trim());
      const bridgeDomain = typeof response?.bridge_domain === 'string' ? response.bridge_domain : 'unknown';
      setSimplefinResult(`Connected. Persist the returned access URL in Secrets Manager. Bridge: ${bridgeDomain}`);
      setSimplefinToken('');
      await loadDashboard();
    } catch (connectError: unknown) {
      setError(normalizeError(connectError));
    }
  }

  async function handleSimplefinSync(): Promise<void> {
    setError(null);
    setSimplefinSyncSummary(null);
    try {
      const response = await getSimpleFINAccounts(90);
      const accountCount = Array.isArray(response?.accounts) ? response.accounts.length : 0;
      const transactionCount = typeof response?.transaction_count === 'number' ? response.transaction_count : 0;
      setSimplefinSyncSummary(`Loaded ${accountCount} accounts and ${transactionCount} transactions from SimpleFIN.`);
    } catch (syncError: unknown) {
      setError(normalizeError(syncError));
    }
  }

  async function handleImport(): Promise<void> {
    if (!selectedFile) {
      setError('Select a CSV, OFX, or QFX file first.');
      return;
    }

    setImportBusy(true);
    setError(null);
    setImportResult(null);
    try {
      const lower = selectedFile.name.toLowerCase();
      const response = lower.endsWith('.csv')
        ? await importBankCSV(selectedFile, importInstitution, 'founder-import')
        : await importBankOFX(selectedFile, importInstitution);
      setImportResult(response as ImportResponse);
    } catch (importError: unknown) {
      setError(normalizeError(importError));
    } finally {
      setImportBusy(false);
    }
  }

  async function handleFederalSubmit(): Promise<void> {
    setFederalBusy(true);
    setError(null);
    setFederalResult(null);
    try {
      const response = await submitFederalEstimatedTax({
        tax_year: federalForm.tax_year,
        quarter: federalForm.quarter,
        filer_ssn: federalForm.filer_ssn,
        first_name: federalForm.first_name,
        last_name: federalForm.last_name,
        payment_amount: Number(federalForm.payment_amount),
      });
      setFederalResult(response as SubmissionResponse);
      setFederalForm((prev) => ({ ...prev, filer_ssn: '' }));
      await loadDashboard();
    } catch (submitError: unknown) {
      setError(normalizeError(submitError));
    } finally {
      setFederalBusy(false);
    }
  }

  async function handleWisconsinSubmit(): Promise<void> {
    setWisconsinBusy(true);
    setError(null);
    setWisconsinResult(null);
    try {
      const response = await submitWisconsinForm1({
        tax_year: wisconsinForm.tax_year,
        filer_ssn: wisconsinForm.filer_ssn,
        first_name: wisconsinForm.first_name,
        last_name: wisconsinForm.last_name,
        street: wisconsinForm.street,
        city: wisconsinForm.city,
        zip_code: wisconsinForm.zip_code,
        wi_adjusted_gross_income: Number(wisconsinForm.wi_adjusted_gross_income),
        wi_exemptions: Number(wisconsinForm.wi_exemptions),
        wi_credits: Number(wisconsinForm.wi_credits),
        wi_withholding: Number(wisconsinForm.wi_withholding),
        net_taxable_income: Number(wisconsinForm.net_taxable_income),
      });
      setWisconsinResult(response as SubmissionResponse);
      setWisconsinForm((prev) => ({ ...prev, filer_ssn: '' }));
      await loadDashboard();
    } catch (submitError: unknown) {
      setError(normalizeError(submitError));
    } finally {
      setWisconsinBusy(false);
    }
  }

  return (
    <div className="min-h-screen bg-[var(--color-bg-base)] px-6 py-8 text-white">
      <div className="mx-auto max-w-7xl space-y-8">
        <div className="flex flex-wrap items-start justify-between gap-4">
          <div>
            <Link href="/founder/tools" className="mb-3 inline-flex items-center gap-2 text-sm text-[var(--color-text-secondary)] hover:text-white">
              <ArrowLeft className="h-4 w-4" /> Founder Tools
            </Link>
            <h1 className="flex items-center gap-3 text-3xl font-black uppercase tracking-[0.08em]">
              <Landmark className="h-8 w-8 text-[var(--color-brand-orange)]" />
              Founder Tax & E-File
            </h1>
            <p className="mt-2 max-w-3xl text-sm text-[var(--color-text-secondary)]">
              Real founder tax operations: IRS MeF readiness, Wisconsin DOR filing, open-source-first banking,
              and manual CSV/OFX fallback imports.
            </p>
          </div>
          <button
            type="button"
            onClick={() => loadDashboard().catch(() => undefined)}
            className="inline-flex items-center gap-2 border border-white/10 bg-white/5 px-4 py-2 text-xs font-bold uppercase tracking-[0.16em] text-white hover:border-[var(--color-brand-orange)] hover:text-[var(--color-brand-orange)]"
          >
            <RefreshCw className={`h-4 w-4 ${refreshing ? 'animate-spin' : ''}`} /> Refresh
          </button>
        </div>

        {error && (
          <div className="border border-red-500/30 bg-red-500/10 px-4 py-3 text-sm text-red-200">{error}</div>
        )}

        <section className="space-y-4">
          <div className="flex items-center gap-2 text-xs font-bold uppercase tracking-[0.18em] text-[var(--color-text-muted)]">
            <Shield className="h-4 w-4 text-[var(--color-status-info)]" /> E-file status
          </div>
          {loading && !efileStatus ? (
            <div className="border border-white/10 bg-[var(--color-bg-panel)] px-4 py-5 text-sm text-zinc-400">
              Loading founder filing status…
            </div>
          ) : (
            <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
              {efileStatus?.irs_mef && <ProviderCard provider={efileStatus.irs_mef} />}
              {efileStatus?.wi_dor && <ProviderCard provider={efileStatus.wi_dor} />}
            </div>
          )}
        </section>

        <section className="grid grid-cols-1 gap-6 xl:grid-cols-2">
          <div className="border border-white/10 bg-[var(--color-bg-panel)] p-5">
            <div className="mb-4 flex items-center gap-2 text-xs font-bold uppercase tracking-[0.18em] text-[var(--color-text-muted)]">
              <Wallet className="h-4 w-4 text-[var(--color-brand-orange)]" /> Open-source bank protocols
            </div>
            <div className="grid grid-cols-1 gap-3 md:grid-cols-2">
              {protocolEntries.map(([key, protocol]) => (
                <div key={key} className="border border-white/8 bg-black/30 p-4">
                  <div className="flex items-start justify-between gap-3">
                    <div className="text-sm font-bold uppercase tracking-[0.12em] text-white">{key.replaceAll('_', ' ')}</div>
                    <span className={`text-[10px] font-bold uppercase tracking-[0.16em] ${statusTone(protocol.status)}`}>
                      {protocol.status.replaceAll('_', ' ')}
                    </span>
                  </div>
                  <p className="mt-2 text-sm text-zinc-400">{protocol.description}</p>
                  <div className="mt-3 space-y-1 text-xs text-zinc-500">
                    {protocol.cost && <div>Cost: {protocol.cost}</div>}
                    {'open_source' in protocol && <div>Open source: {protocol.open_source ? 'yes' : 'no'}</div>}
                    {protocol.library && <div>Library: {protocol.library}</div>}
                    {protocol.supported_formats && <div>Formats: {protocol.supported_formats.join(', ')}</div>}
                  </div>
                </div>
              ))}
            </div>
            {bankStatus?.available && (
              <div className="mt-4 text-xs text-zinc-400">
                Available now: {bankStatus.available.join(', ')}
              </div>
            )}
          </div>

          <div className="space-y-6">
            <div className="border border-white/10 bg-[var(--color-bg-panel)] p-5">
              <div className="mb-4 flex items-center gap-2 text-xs font-bold uppercase tracking-[0.18em] text-[var(--color-text-muted)]">
                <Database className="h-4 w-4 text-[var(--color-status-info)]" /> SimpleFIN bridge
              </div>
              <label className={labelCls}>Setup token</label>
              <input
                value={simplefinToken}
                onChange={(event) => setSimplefinToken(event.target.value)}
                className={inputCls}
                placeholder="Paste base64 setup token from bridge.simplefin.org"
              />
              <div className="mt-4 flex flex-wrap gap-3">
                <button
                  type="button"
                  onClick={() => handleSimplefinConnect().catch(() => undefined)}
                  className="bg-[var(--color-brand-orange)] px-4 py-2 text-xs font-bold uppercase tracking-[0.16em] text-black hover:brightness-110"
                >
                  Connect SimpleFIN
                </button>
                <button
                  type="button"
                  onClick={() => handleSimplefinSync().catch(() => undefined)}
                  className="border border-white/10 bg-white/5 px-4 py-2 text-xs font-bold uppercase tracking-[0.16em] text-white hover:border-[var(--color-status-info)] hover:text-[var(--color-status-info)]"
                >
                  Sync Accounts
                </button>
              </div>
              {simplefinResult && <div className="mt-3 text-sm text-emerald-300">{simplefinResult}</div>}
              {simplefinSyncSummary && <div className="mt-2 text-sm text-sky-300">{simplefinSyncSummary}</div>}
            </div>

            <div className="border border-white/10 bg-[var(--color-bg-panel)] p-5">
              <div className="mb-4 flex items-center gap-2 text-xs font-bold uppercase tracking-[0.18em] text-[var(--color-text-muted)]">
                <Upload className="h-4 w-4 text-[var(--color-status-info)]" /> Manual CSV / OFX import
              </div>
              <div className="grid grid-cols-1 gap-4 md:grid-cols-[1fr_180px]">
                <div>
                  <label className={labelCls}>Statement file</label>
                  <input
                    type="file"
                    accept=".csv,.ofx,.qfx"
                    onChange={(event) => setSelectedFile(event.target.files?.[0] ?? null)}
                    className={inputCls}
                  />
                </div>
                <div>
                  <label className={labelCls}>Institution</label>
                  <select
                    value={importInstitution}
                    onChange={(event) => setImportInstitution(event.target.value)}
                    className={inputCls}
                  >
                    <option value="generic">Generic</option>
                    <option value="novo">Novo</option>
                    <option value="amex">AmEx</option>
                    <option value="Imported">Imported OFX</option>
                  </select>
                </div>
              </div>
              <button
                type="button"
                onClick={() => handleImport().catch(() => undefined)}
                disabled={importBusy}
                className="mt-4 bg-[var(--color-status-info)] px-4 py-2 text-xs font-bold uppercase tracking-[0.16em] text-black hover:brightness-110 disabled:cursor-not-allowed disabled:opacity-60"
              >
                {importBusy ? 'Importing…' : 'Import Transactions'}
              </button>
              {importResult && (
                <div className="mt-3 text-sm text-zinc-300">
                  Imported {importResult.transaction_count ?? 0} transactions via {importResult.protocol ?? 'manual import'}.
                </div>
              )}
            </div>
          </div>
        </section>

        <section className="grid grid-cols-1 gap-6 xl:grid-cols-2">
          <div className="border border-white/10 bg-[var(--color-bg-panel)] p-5">
            <div className="mb-4 flex items-center gap-2 text-xs font-bold uppercase tracking-[0.18em] text-[var(--color-text-muted)]">
              <Receipt className="h-4 w-4 text-[var(--color-brand-orange)]" /> IRS estimated payment
            </div>
            <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
              <div>
                <label className={labelCls}>Tax year</label>
                <input type="number" value={federalForm.tax_year} onChange={(event) => setFederalForm((prev) => ({ ...prev, tax_year: Number(event.target.value) }))} className={inputCls} />
              </div>
              <div>
                <label className={labelCls}>Quarter</label>
                <select
                  value={String(federalForm.quarter)}
                  onChange={(event) => setFederalForm((prev) => ({ ...prev, quarter: Number(event.target.value) as 1 | 2 | 3 | 4 }))}
                  className={inputCls}
                >
                  <option value="1">Q1</option>
                  <option value="2">Q2</option>
                  <option value="3">Q3</option>
                  <option value="4">Q4</option>
                </select>
              </div>
              <div>
                <label className={labelCls}>First name</label>
                <input value={federalForm.first_name} onChange={(event) => setFederalForm((prev) => ({ ...prev, first_name: event.target.value }))} className={inputCls} />
              </div>
              <div>
                <label className={labelCls}>Last name</label>
                <input value={federalForm.last_name} onChange={(event) => setFederalForm((prev) => ({ ...prev, last_name: event.target.value }))} className={inputCls} />
              </div>
              <div>
                <label className={labelCls}>SSN</label>
                <input value={federalForm.filer_ssn} onChange={(event) => setFederalForm((prev) => ({ ...prev, filer_ssn: event.target.value }))} className={inputCls} />
              </div>
              <div>
                <label className={labelCls}>Payment amount</label>
                <input value={federalForm.payment_amount} onChange={(event) => setFederalForm((prev) => ({ ...prev, payment_amount: event.target.value }))} className={inputCls} />
              </div>
            </div>
            <button
              type="button"
              onClick={() => handleFederalSubmit().catch(() => undefined)}
              disabled={federalBusy}
              className="mt-4 bg-[var(--color-brand-orange)] px-4 py-2 text-xs font-bold uppercase tracking-[0.16em] text-black hover:brightness-110 disabled:cursor-not-allowed disabled:opacity-60"
            >
              {federalBusy ? 'Submitting…' : 'Transmit to IRS MeF'}
            </button>
            {federalResult && (
              <div className={`mt-4 text-sm ${statusTone(federalResult.status)}`}>
                Status: {federalResult.status} {federalResult.confirmation_number ? `· ${federalResult.confirmation_number}` : ''}
                {federalResult.errors && federalResult.errors.length > 0 ? ` · ${federalResult.errors.join(', ')}` : ''}
              </div>
            )}
          </div>

          <div className="border border-white/10 bg-[var(--color-bg-panel)] p-5">
            <div className="mb-4 flex items-center gap-2 text-xs font-bold uppercase tracking-[0.18em] text-[var(--color-text-muted)]">
              <Landmark className="h-4 w-4 text-[var(--color-status-info)]" /> Wisconsin Form 1
            </div>
            <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
              <div>
                <label className={labelCls}>Tax year</label>
                <input type="number" value={wisconsinForm.tax_year} onChange={(event) => setWisconsinForm((prev) => ({ ...prev, tax_year: Number(event.target.value) }))} className={inputCls} />
              </div>
              <div>
                <label className={labelCls}>ZIP code</label>
                <input value={wisconsinForm.zip_code} onChange={(event) => setWisconsinForm((prev) => ({ ...prev, zip_code: event.target.value }))} className={inputCls} />
              </div>
              <div>
                <label className={labelCls}>First name</label>
                <input value={wisconsinForm.first_name} onChange={(event) => setWisconsinForm((prev) => ({ ...prev, first_name: event.target.value }))} className={inputCls} />
              </div>
              <div>
                <label className={labelCls}>Last name</label>
                <input value={wisconsinForm.last_name} onChange={(event) => setWisconsinForm((prev) => ({ ...prev, last_name: event.target.value }))} className={inputCls} />
              </div>
              <div className="md:col-span-2">
                <label className={labelCls}>Street</label>
                <input value={wisconsinForm.street} onChange={(event) => setWisconsinForm((prev) => ({ ...prev, street: event.target.value }))} className={inputCls} />
              </div>
              <div>
                <label className={labelCls}>City</label>
                <input value={wisconsinForm.city} onChange={(event) => setWisconsinForm((prev) => ({ ...prev, city: event.target.value }))} className={inputCls} />
              </div>
              <div>
                <label className={labelCls}>SSN</label>
                <input value={wisconsinForm.filer_ssn} onChange={(event) => setWisconsinForm((prev) => ({ ...prev, filer_ssn: event.target.value }))} className={inputCls} />
              </div>
              <div>
                <label className={labelCls}>WI AGI</label>
                <input value={wisconsinForm.wi_adjusted_gross_income} onChange={(event) => setWisconsinForm((prev) => ({ ...prev, wi_adjusted_gross_income: event.target.value }))} className={inputCls} />
              </div>
              <div>
                <label className={labelCls}>Net taxable income</label>
                <input value={wisconsinForm.net_taxable_income} onChange={(event) => setWisconsinForm((prev) => ({ ...prev, net_taxable_income: event.target.value }))} className={inputCls} />
              </div>
              <div>
                <label className={labelCls}>Exemptions</label>
                <input value={wisconsinForm.wi_exemptions} onChange={(event) => setWisconsinForm((prev) => ({ ...prev, wi_exemptions: event.target.value }))} className={inputCls} />
              </div>
              <div>
                <label className={labelCls}>Credits</label>
                <input value={wisconsinForm.wi_credits} onChange={(event) => setWisconsinForm((prev) => ({ ...prev, wi_credits: event.target.value }))} className={inputCls} />
              </div>
              <div>
                <label className={labelCls}>Withholding</label>
                <input value={wisconsinForm.wi_withholding} onChange={(event) => setWisconsinForm((prev) => ({ ...prev, wi_withholding: event.target.value }))} className={inputCls} />
              </div>
            </div>
            <button
              type="button"
              onClick={() => handleWisconsinSubmit().catch(() => undefined)}
              disabled={wisconsinBusy}
              className="mt-4 bg-[var(--color-status-info)] px-4 py-2 text-xs font-bold uppercase tracking-[0.16em] text-black hover:brightness-110 disabled:cursor-not-allowed disabled:opacity-60"
            >
              {wisconsinBusy ? 'Submitting…' : 'Transmit to Wisconsin DOR'}
            </button>
            {wisconsinResult && (
              <div className={`mt-4 text-sm ${statusTone(wisconsinResult.status)}`}>
                Status: {wisconsinResult.status} {wisconsinResult.confirmation_number ? `· ${wisconsinResult.confirmation_number}` : ''}
                {wisconsinResult.errors && wisconsinResult.errors.length > 0 ? ` · ${wisconsinResult.errors.join(', ')}` : ''}
              </div>
            )}
          </div>
        </section>
      </div>
    </div>
  );
}
