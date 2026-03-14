'use client';
import { QuantumTableSkeleton } from '@/components/ui';
import { SeverityBadge } from '@/components/ui';
import { useState, useEffect, useCallback, useRef } from 'react';
import type { SeverityLevel } from '@/lib/design-system/tokens';
import {
  checkNEMSISCtaRunStatus,
  createNEMSISPack,
  generatePatchTasksFromResult,
  getActiveNEMSISPacks,
  getNEMSISCertificationChecklist,
  getNEMSISCtaCases,
  getNEMSISCtaRuns,
  nemsisStudioAiExplain,
  runNEMSISCtaCase,
  uploadNEMSISPackFile,
  validateNEMSISStudioFile,
} from '@/services/api';

interface PackStatus {
  national_xsd: { active: boolean; name: string } | null;
  wi_schematron: { active: boolean; name: string } | null;
  wi_state_dataset: { active: boolean; name: string } | null;
}

interface ValidationIssue {
  severity: string;
  element_id: string;
  ui_section: string;
  rule_source: string;
  plain_message: string;
  fix_hint: string;
}

interface ValidationResult {
  valid: boolean;
  issues: ValidationIssue[];
  record_id?: string;
}

interface AiExplanation {
  plain_explanation: string;
  fix_type: string;
  patch_task: { steps: string[] };
}

interface CertCheck {
  label: string;
  passed: boolean;
}

interface CTACase {
  case_id: string;
  short_name: string;
  description: string;
  dataset_type: 'DEM' | 'EMS';
  expected_result: string;
  schema_version: string;
  request_data_schema: number;
  test_key_element: string;
}

interface CTARun {
  id: string;
  status: string;
  case_id: string;
  case_label: string;
  dataset_type: 'DEM' | 'EMS';
  schema_version: string;
  request_data_schema: number;
  request_handle: string | null;
  submit_status_code: number | null;
  retrieve_status_code: number | null;
  plain_summary: string;
  current_state_label: string;
  validation_blocking_count: number;
  resolved_test_key: string | null;
  organization: string | null;
  last_checked_at: string | null;
  created_at: string;
  updated_at: string;
  history: Array<{ status: string; at: string; summary?: string }>;
  details: Record<string, unknown>;
}

interface CtaCredentialForm {
  username: string;
  password: string;
  organization: string;
  endpoint_url: string;
  additional_info: string;
}

function validationSeverityToCanonical(severity: string): SeverityLevel {
  switch (severity.toLowerCase()) {
    case 'error':
      return 'BLOCKING';
    case 'warning':
      return 'MEDIUM';
    case 'info':
      return 'INFORMATIONAL';
    default:
      return 'INFORMATIONAL';
  }
}

function formatTimestamp(value?: string | null): string {
  if (!value) return 'Not checked yet';
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return value;
  return date.toLocaleString();
}

function decodeXmlDetail(value: unknown): string {
  if (typeof value !== 'string' || value.length === 0) return 'No XML available';
  try {
    return atob(value);
  } catch {
    return 'Unable to decode XML payload';
  }
}

export default function ComplianceStudioPage() {
  const [packStatus, setPackStatus] = useState<PackStatus | null>(null);
  const [packLoading, setPackLoading] = useState(false);
  const [uploadStatus, setUploadStatus] = useState<string>('');
  const [isDragging, setIsDragging] = useState(false);
  const [validationFile, setValidationFile] = useState<File | null>(null);
  const [validationLoading, setValidationLoading] = useState(false);
  const [validationResult, setValidationResult] = useState<ValidationResult | null>(null);
  const [aiExplanations, setAiExplanations] = useState<Record<number, AiExplanation | null>>({});
  const [aiLoadingIdx, setAiLoadingIdx] = useState<number | null>(null);
  const [certChecks, setCertChecks] = useState<CertCheck[]>([]);
  const [certLoading, setCertLoading] = useState(false);
  const [ctaCases, setCtaCases] = useState<CTACase[]>([]);
  const [ctaRuns, setCtaRuns] = useState<CTARun[]>([]);
  const [ctaLoading, setCtaLoading] = useState(false);
  const [ctaRunning, setCtaRunning] = useState(false);
  const [ctaChecking, setCtaChecking] = useState(false);
  const [ctaMessage, setCtaMessage] = useState<string>('');
  const [ctaDetailsOpen, setCtaDetailsOpen] = useState(false);
  const [selectedCaseId, setSelectedCaseId] = useState<string>('2025-DEM-1-FullSet_v351');
  const [selectedRunId, setSelectedRunId] = useState<string | null>(null);
  const [ctaCredentials, setCtaCredentials] = useState<CtaCredentialForm>({
    username: '',
    password: '',
    organization: '',
    endpoint_url: 'https://compliance.nemsis.org/',
    additional_info: '',
  });
  const fileInputRef = useRef<HTMLInputElement>(null);
  const dropFileInputRef = useRef<HTMLInputElement>(null);

  const fetchPackStatus = useCallback(async () => {
    setPackLoading(true);
    try {
      const data = await getActiveNEMSISPacks();
      const packs: { data: { pack_type?: string; pack_name?: string; active?: boolean } }[] = Array.isArray(data) ? data : [];
      const national = packs.find((p) => p.data?.pack_type === 'national_xsd');
      const wi_sch = packs.find((p) => p.data?.pack_type === 'wi_schematron');
      const wi_ds = packs.find((p) => p.data?.pack_type === 'wi_state_dataset');
      setPackStatus({
        national_xsd: national ? { active: !!national.data?.active, name: national.data?.pack_name || 'National XSD' } : null,
        wi_schematron: wi_sch ? { active: !!wi_sch.data?.active, name: wi_sch.data?.pack_name || 'WI Schematron' } : null,
        wi_state_dataset: wi_ds ? { active: !!wi_ds.data?.active, name: wi_ds.data?.pack_name || 'WI State Dataset' } : null,
      });
    } catch {
      setPackStatus({ national_xsd: null, wi_schematron: null, wi_state_dataset: null });
    } finally {
      setPackLoading(false);
    }
  }, []);

  const fetchCertChecks = useCallback(async () => {
    setCertLoading(true);
    try {
      const data = await getNEMSISCertificationChecklist();
      setCertChecks(Array.isArray((data as { checks?: unknown[] }).checks) ? ((data as { checks: CertCheck[] }).checks) : []);
    } catch {
      setCertChecks([]);
    } finally {
      setCertLoading(false);
    }
  }, []);

  const fetchCtaCases = useCallback(async () => {
    setCtaLoading(true);
    try {
      const data = await getNEMSISCtaCases();
      setCtaCases(Array.isArray(data.cases) ? data.cases : []);
    } catch {
      setCtaCases([]);
    } finally {
      setCtaLoading(false);
    }
  }, []);

  const fetchCtaRuns = useCallback(async () => {
    setCtaLoading(true);
    try {
      const data = await getNEMSISCtaRuns();
      setCtaRuns(Array.isArray(data.runs) ? data.runs : []);
    } catch {
      setCtaRuns([]);
    } finally {
      setCtaLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchPackStatus();
    fetchCertChecks();
    fetchCtaCases();
    fetchCtaRuns();
  }, [fetchPackStatus, fetchCertChecks, fetchCtaCases, fetchCtaRuns]);

  useEffect(() => {
    if (!selectedCaseId && ctaCases.length > 0) {
      setSelectedCaseId(ctaCases[0].case_id);
    }
  }, [ctaCases, selectedCaseId]);

  useEffect(() => {
    if (!selectedRunId && ctaRuns.length > 0) {
      setSelectedRunId(ctaRuns[0].id);
    }
  }, [ctaRuns, selectedRunId]);

  const handleDropFiles = useCallback(async (files: FileList | null) => {
    if (!files || files.length === 0) return;
    setUploadStatus('Creating pack...');
    const file = files[0];
    const form = new FormData();
    form.append('file', file);
    form.append('pack_name', file.name);
    try {
      const rec = await createNEMSISPack({ pack_name: file.name, pack_type: 'upload' });
      const record = rec as { id?: string; data?: { pack_id?: string } };
      const packId = record.id || record.data?.pack_id || 'new';
      const uploadForm = new FormData();
      uploadForm.append('file', file);

      if (packId === 'new') {
        setUploadStatus('Pack created response missing pack_id');
      } else {
        await uploadNEMSISPackFile(packId, uploadForm);
        setUploadStatus(`Uploaded: ${file.name}`);
        fetchPackStatus();
      }
    } catch (e: unknown) {
      setUploadStatus(`Error: ${e instanceof Error ? e.message : String(e)}`);
    }
  }, [fetchPackStatus]);

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(false);
    handleDropFiles(e.dataTransfer.files);
  };

  const runValidation = async () => {
    if (!validationFile) return;
    setValidationLoading(true);
    setValidationResult(null);
    setAiExplanations({});
    const form = new FormData();
    form.append('file', validationFile);
    try {
      const data = await validateNEMSISStudioFile(form);
      setValidationResult(data as ValidationResult);
    } catch (e: unknown) {
      setValidationResult({ valid: false, issues: [{ severity: 'error', element_id: 'network', ui_section: '', rule_source: '', plain_message: e instanceof Error ? e.message : String(e), fix_hint: '' }] });
    } finally {
      setValidationLoading(false);
    }
  };

  const fetchAiExplain = async (idx: number) => {
    if (!validationResult?.record_id) return;
    setAiLoadingIdx(idx);
    try {
      const data = await nemsisStudioAiExplain({ validation_result_id: validationResult.record_id, issue_index: idx });
      setAiExplanations((prev) => ({ ...prev, [idx]: data as AiExplanation }));
    } finally {
      setAiLoadingIdx(null);
    }
  };

  const sendAllToAgent = async () => {
    if (!validationResult?.record_id) return;
    try {
      await generatePatchTasksFromResult({ validation_result_id: validationResult.record_id });
    } catch (err: unknown) {
      console.warn("[compliance-studio]", err);
    }
  };

  const selectedRun = ctaRuns.find((run) => run.id === selectedRunId) ?? (ctaRuns.length > 0 ? ctaRuns[0] : null);

  const runSelectedCtaCase = async () => {
    if (!selectedCaseId) return;
    setCtaRunning(true);
    setCtaMessage('');
    try {
      const run = await runNEMSISCtaCase({
        case_id: selectedCaseId,
        endpoint_url: ctaCredentials.endpoint_url,
        additional_info: ctaCredentials.additional_info || undefined,
        credentials: {
          username: ctaCredentials.username,
          password: ctaCredentials.password,
          organization: ctaCredentials.organization,
        },
      });
      setSelectedRunId(run.id);
      setCtaMessage(run.plain_summary || 'CTA test started.');
      await fetchCtaRuns();
    } catch (error: unknown) {
      const message = error instanceof Error ? error.message : 'Unable to run CTA test.';
      setCtaMessage(message);
    } finally {
      setCtaRunning(false);
    }
  };

  const checkSelectedRunStatus = async () => {
    if (!selectedRun) return;
    setCtaChecking(true);
    setCtaMessage('');
    try {
      const run = await checkNEMSISCtaRunStatus(selectedRun.id, {
        endpoint_url: ctaCredentials.endpoint_url,
        additional_info: ctaCredentials.additional_info || undefined,
        credentials: {
          username: ctaCredentials.username,
          password: ctaCredentials.password,
          organization: ctaCredentials.organization,
        },
      });
      setSelectedRunId(run.id);
      setCtaMessage(run.plain_summary || 'CTA status updated.');
      await fetchCtaRuns();
    } catch (error: unknown) {
      const message = error instanceof Error ? error.message : 'Unable to check CTA status.';
      setCtaMessage(message);
    } finally {
      setCtaChecking(false);
    }
  };

  const blockingCount = validationResult?.issues.filter((i) => validationSeverityToCanonical(i.severity) === 'BLOCKING').length ?? 0;
  const mediumCount = validationResult?.issues.filter((i) => validationSeverityToCanonical(i.severity) === 'MEDIUM').length ?? 0;

  return (
    <div className="p-5 space-y-6 min-h-screen bg-[var(--color-bg-base)]">
      <div>
        <div className="text-micro font-bold uppercase tracking-[0.2em] text-system-billing mb-1">
          ePCR · COMPLIANCE STUDIO
        </div>
        <h1 className="text-xl font-black uppercase tracking-wider text-[var(--color-text-primary)]">Compliance Studio</h1>
        <p className="text-xs text-[var(--color-text-muted)] mt-0.5">
          Turn-key visual certification — resource packs, validation, AI fix list
        </p>
      </div>

      <div className="bg-[var(--color-bg-panel)] border border-border-DEFAULT p-4 space-y-2">
        <div className="text-xs font-bold uppercase tracking-wider text-[var(--color-text-secondary)] mb-3">Pack Status</div>
        {packLoading ? (
          <div className="p-6"><QuantumTableSkeleton rows={6} cols={4} /></div>
        ) : (
          <div className="flex flex-wrap gap-3">
            {[
              { key: 'national_xsd', label: 'National XSD' },
              { key: 'wi_schematron', label: 'WI Schematron' },
              { key: 'wi_state_dataset', label: 'WI State Dataset' },
            ].map(({ key, label }) => {
              const pack = packStatus?.[key as keyof PackStatus];
              return (
                <div key={key} className="flex items-center gap-2 bg-bg-input border border-border-DEFAULT px-3 py-2">
                  <span
                    className={`inline-block w-2 h-2  ${pack?.active ? 'bg-[var(--color-status-active)]' : 'bg-[var(--color-brand-red)]'}`}
                  />
                  <span className="text-xs text-[var(--color-text-primary)]">{pack?.name || label}</span>
                  <span className={`text-micro font-bold ${pack?.active ? 'text-[var(--color-status-active)]' : 'text-[var(--color-brand-red)]'}`}>
                    {pack?.active ? 'Active' : 'Missing'}
                  </span>
                </div>
              );
            })}
          </div>
        )}
      </div>

      <div
        className={`border-2 border-dashed chamfer-4 transition-colors ${isDragging ? 'border-cyan-400 bg-bg-input' : 'border-border-strong bg-[var(--color-bg-panel)]'} p-8 text-center`}
        onDragOver={(e) => { e.preventDefault(); setIsDragging(true); }}
        onDragLeave={() => setIsDragging(false)}
        onDrop={handleDrop}
      >
        <div className="text-[var(--color-text-secondary)] text-sm mb-2">
          Drop NEMSIS resource files here (XSD, Schematron, StateDataSet, ZIP)
        </div>
        <div className="text-[var(--color-text-muted)] text-xs mb-4">or click to browse</div>
        <input
          ref={dropFileInputRef}
          type="file"
          accept=".xsd,.sch,.xml,.zip"
          className="hidden"
          onChange={(e) => handleDropFiles(e.target.files)}
        />
        <button
          onClick={() => dropFileInputRef.current?.click()}
          className="bg-bg-input border border-cyan-500/[0.3] text-system-billing text-xs px-4 py-2 hover:bg-cyan-500/[0.08] transition-colors"
        >
          Browse Files
        </button>
        {uploadStatus && (
          <div className="mt-3 text-xs text-[var(--color-text-secondary)]">{uploadStatus}</div>
        )}
      </div>

      <div className="bg-[#0A0A0B] border border-border-DEFAULT p-4 space-y-4">
        <div className="flex items-center justify-between gap-3 flex-wrap">
          <div>
            <div className="text-xs font-bold uppercase tracking-wider text-zinc-400">CTA Collect &amp; Send</div>
            <div className="text-xs text-zinc-500 mt-1">Start with DEM 1, submit over SOAP, persist the request handle, and poll status without exposing SOAP details.</div>
          </div>
          <div className="text-xs text-zinc-500">First-pass focus: DEM 1 end to end</div>
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-[1.1fr_1.4fr] gap-4">
          <div className="space-y-3">
            <div className="text-micro uppercase tracking-wider text-zinc-500">Case List</div>
            {ctaLoading && ctaCases.length === 0 ? (
              <div className="p-4"><QuantumTableSkeleton rows={4} cols={2} /></div>
            ) : (
              <div className="space-y-2">
                {ctaCases.map((ctaCase) => (
                  <button
                    key={ctaCase.case_id}
                    onClick={() => setSelectedCaseId(ctaCase.case_id)}
                    className={`w-full text-left border px-3 py-3 transition-colors ${selectedCaseId === ctaCase.case_id ? 'border-cyan-500/50 bg-cyan-500/[0.08]' : 'border-border-DEFAULT bg-bg-input hover:border-white/[0.2]'}`}
                  >
                    <div className="flex items-center justify-between gap-3">
                      <div className="text-xs font-bold text-zinc-100">{ctaCase.short_name}</div>
                      <span className={`text-micro font-bold px-2 py-0.5 ${ctaCase.dataset_type === 'DEM' ? 'bg-cyan-950 text-cyan-300' : 'bg-amber-950 text-amber-300'}`}>
                        {ctaCase.dataset_type}
                      </span>
                    </div>
                    <div className="text-xs text-zinc-500 mt-1">{ctaCase.description}</div>
                    <div className="text-micro text-zinc-600 mt-2">
                      Schema {ctaCase.schema_version} · requestDataSchema {ctaCase.request_data_schema} · key {ctaCase.test_key_element}
                    </div>
                  </button>
                ))}
              </div>
            )}
          </div>

          <div className="space-y-3">
            <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
              <input
                value={ctaCredentials.username}
                onChange={(event) => setCtaCredentials((prev) => ({ ...prev, username: event.target.value }))}
                placeholder="CTA username"
                className="bg-bg-input border border-border-DEFAULT text-xs text-zinc-100 px-3 py-2 outline-none focus:border-cyan-500/40"
              />
              <input
                value={ctaCredentials.organization}
                onChange={(event) => setCtaCredentials((prev) => ({ ...prev, organization: event.target.value }))}
                placeholder="CTA organization"
                className="bg-bg-input border border-border-DEFAULT text-xs text-zinc-100 px-3 py-2 outline-none focus:border-cyan-500/40"
              />
              <input
                type="password"
                value={ctaCredentials.password}
                onChange={(event) => setCtaCredentials((prev) => ({ ...prev, password: event.target.value }))}
                placeholder="CTA password"
                className="bg-bg-input border border-border-DEFAULT text-xs text-zinc-100 px-3 py-2 outline-none focus:border-cyan-500/40"
              />
              <input
                value={ctaCredentials.endpoint_url}
                onChange={(event) => setCtaCredentials((prev) => ({ ...prev, endpoint_url: event.target.value }))}
                placeholder="CTA endpoint"
                className="bg-bg-input border border-border-DEFAULT text-xs text-zinc-100 px-3 py-2 outline-none focus:border-cyan-500/40"
              />
            </div>

            <input
              value={ctaCredentials.additional_info}
              onChange={(event) => setCtaCredentials((prev) => ({ ...prev, additional_info: event.target.value }))}
              placeholder="Optional additional info override"
              className="w-full bg-bg-input border border-border-DEFAULT text-xs text-zinc-100 px-3 py-2 outline-none focus:border-cyan-500/40"
            />

            <div className="flex flex-wrap items-center gap-3">
              <button
                onClick={runSelectedCtaCase}
                disabled={!selectedCaseId || ctaRunning}
                className="bg-system-billing text-black text-xs font-bold px-5 py-2 disabled:opacity-40 disabled:cursor-not-allowed"
              >
                {ctaRunning ? 'Running Test...' : 'Run Test'}
              </button>
              <button
                onClick={checkSelectedRunStatus}
                disabled={!selectedRun || ctaChecking}
                className="bg-bg-input border border-cyan-500/[0.3] text-system-billing text-xs px-4 py-2 disabled:opacity-40 disabled:cursor-not-allowed"
              >
                {ctaChecking ? 'Checking...' : 'Check Status'}
              </button>
              <button
                onClick={() => { void fetchCtaRuns(); }}
                className="bg-bg-input border border-border-DEFAULT text-zinc-300 text-xs px-4 py-2"
              >
                Refresh Runs
              </button>
              {ctaMessage && <span className="text-xs text-zinc-400">{ctaMessage}</span>}
            </div>

            <div className="border border-border-DEFAULT bg-bg-input p-4 space-y-3">
              <div className="flex items-center justify-between gap-3 flex-wrap">
                <div>
                  <div className="text-micro uppercase tracking-wider text-zinc-500">Latest Run</div>
                  <div className="text-sm font-bold text-zinc-100">{selectedRun?.case_label || 'No CTA run yet'}</div>
                </div>
                <div className="text-right">
                  <div className="text-xs text-system-billing font-bold">{selectedRun?.current_state_label || 'Ready'}</div>
                  <div className="text-micro text-zinc-500">{selectedRun ? formatTimestamp(selectedRun.updated_at) : 'Select DEM 1 and run the test.'}</div>
                </div>
              </div>

              {selectedRun ? (
                <>
                  <div className="grid grid-cols-1 md:grid-cols-3 gap-3 text-xs">
                    <div>
                      <div className="text-zinc-500">Current State</div>
                      <div className="text-zinc-100 font-bold">{selectedRun.current_state_label}</div>
                    </div>
                    <div>
                      <div className="text-zinc-500">Request Handle</div>
                      <div className="text-zinc-100 font-mono break-all">{selectedRun.request_handle || 'Not assigned yet'}</div>
                    </div>
                    <div>
                      <div className="text-zinc-500">Timestamp</div>
                      <div className="text-zinc-100">{formatTimestamp(selectedRun.last_checked_at || selectedRun.updated_at)}</div>
                    </div>
                  </div>

                  <div className="text-xs text-zinc-300">{selectedRun.plain_summary}</div>
                  <div className="text-micro text-zinc-500">
                    Submit code: {selectedRun.submit_status_code ?? 'n/a'} · Retrieve code: {selectedRun.retrieve_status_code ?? 'n/a'} · Blocking validation issues: {selectedRun.validation_blocking_count}
                  </div>

                  <div className="flex items-center justify-between gap-3 flex-wrap">
                    <div className="text-xs text-zinc-500">Retry by selecting the case and pressing Run Test again. Use Check Status for pending handles.</div>
                    <button
                      onClick={() => setCtaDetailsOpen((prev) => !prev)}
                      className="text-xs bg-[#0A0A0B] border border-border-DEFAULT text-zinc-300 px-3 py-1.5"
                    >
                      {ctaDetailsOpen ? 'Hide Advanced Detail' : 'Show Advanced Detail'}
                    </button>
                  </div>

                  {ctaDetailsOpen && (
                    <div className="space-y-3 border-t border-border-DEFAULT pt-3">
                      <div>
                        <div className="text-micro uppercase tracking-wider text-zinc-500 mb-1">Status History</div>
                        <div className="space-y-1">
                          {selectedRun.history.map((entry, index) => (
                            <div key={`${entry.at}-${index}`} className="text-xs text-zinc-400">
                              {formatTimestamp(entry.at)} · {entry.status} · {entry.summary || 'No summary'}
                            </div>
                          ))}
                        </div>
                      </div>

                      <div className="grid grid-cols-1 xl:grid-cols-2 gap-3">
                        <div>
                          <div className="text-micro uppercase tracking-wider text-zinc-500 mb-1">Generated XML</div>
                          <pre className="bg-black/40 border border-border-DEFAULT p-3 text-[10px] text-zinc-300 overflow-auto max-h-64 whitespace-pre-wrap">
                            {decodeXmlDetail(selectedRun.details.xml_b64)}
                          </pre>
                        </div>
                        <div className="space-y-3">
                          <div>
                            <div className="text-micro uppercase tracking-wider text-zinc-500 mb-1">Submit Response</div>
                            <pre className="bg-black/40 border border-border-DEFAULT p-3 text-[10px] text-zinc-300 overflow-auto max-h-28 whitespace-pre-wrap">
                              {typeof selectedRun.details.submit_response_xml === 'string' ? selectedRun.details.submit_response_xml : 'No submit response yet'}
                            </pre>
                          </div>
                          <div>
                            <div className="text-micro uppercase tracking-wider text-zinc-500 mb-1">Retrieve Response</div>
                            <pre className="bg-black/40 border border-border-DEFAULT p-3 text-[10px] text-zinc-300 overflow-auto max-h-28 whitespace-pre-wrap">
                              {typeof selectedRun.details.retrieve_response_xml === 'string' ? selectedRun.details.retrieve_response_xml : 'No retrieve response yet'}
                            </pre>
                          </div>
                          <div>
                            <div className="text-micro uppercase tracking-wider text-zinc-500 mb-1">Validation Snapshot</div>
                            <pre className="bg-black/40 border border-border-DEFAULT p-3 text-[10px] text-zinc-300 overflow-auto max-h-32 whitespace-pre-wrap">
                              {JSON.stringify(selectedRun.details.validation ?? {}, null, 2)}
                            </pre>
                          </div>
                        </div>
                      </div>
                    </div>
                  )}
                </>
              ) : (
                <div className="text-xs text-zinc-500">No CTA runs recorded yet. Select DEM 1 and press Run Test.</div>
              )}
            </div>
          </div>
        </div>
      </div>

      <div className="bg-[#0A0A0B] border border-border-DEFAULT p-4 space-y-3">
        <div className="text-xs font-bold uppercase tracking-wider text-zinc-400">Validate XML File</div>
        <div className="flex items-center gap-3">
          <input
            ref={fileInputRef}
            type="file"
            accept=".xml"
            className="hidden"
            onChange={(e) => setValidationFile(e.target.files?.[0] ?? null)}
          />
          <button
            onClick={() => fileInputRef.current?.click()}
            className="bg-bg-input border border-border-strong text-[var(--color-text-secondary)] text-xs px-3 py-2 hover:border-white/[0.3] transition-colors"
          >
            {validationFile ? validationFile.name : 'Choose XML file'}
          </button>
          <button
            onClick={runValidation}
            disabled={!validationFile || validationLoading}
            className="bg-system-billing text-black text-xs font-bold px-5 py-2 hover:bg-system-billing disabled:opacity-40 disabled:cursor-not-allowed transition-colors"
          >
            {validationLoading ? (
              <span className="flex items-center gap-2">
                <span className="inline-block w-3 h-3 border-2 border-bg-void border-t-transparent  animate-spin" />
                Running...
              </span>
            ) : (
              'Run Validation'
            )}
          </button>
        </div>
      </div>

      {validationResult && (
        <div className="space-y-3">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-3">
              <span
                className={`text-xs font-bold px-2 py-1 ${validationResult.valid ? 'bg-green-900 text-[var(--color-status-active)]' : 'bg-red-900 text-[var(--color-brand-red)]'}`}
              >
                {validationResult.valid ? 'VALID' : 'INVALID'}
              </span>
              <span className="text-xs text-[var(--color-brand-red)]">{blockingCount} blocking issue{blockingCount !== 1 ? 's' : ''}</span>
              <span className="text-xs text-[var(--q-yellow)]">{mediumCount} medium issue{mediumCount !== 1 ? 's' : ''}</span>
            </div>
            <button
              onClick={sendAllToAgent}
              className="text-xs bg-[var(--color-bg-panel)] border border-cyan-500/[0.3] text-system-billing px-3 py-1.5 hover:bg-cyan-500/[0.08] transition-colors"
            >
              Send All to Agent
            </button>
          </div>

          <div className="space-y-2">
            {validationResult.issues.map((issue, idx) => (
              <div
                key={idx}
                className="bg-[var(--color-bg-panel)] border border-border-DEFAULT p-4 space-y-2"
              >
                <div className="flex flex-wrap items-center gap-2">
                  <SeverityBadge
                    severity={validationSeverityToCanonical(issue.severity)}
                    size="sm"
                    label={validationSeverityToCanonical(issue.severity)}
                  />
                  <span className="text-xs font-mono text-system-billing">{issue.element_id}</span>
                  {issue.ui_section && (
                    <span className="text-micro text-[var(--color-text-muted)]">{issue.ui_section}</span>
                  )}
                  {issue.rule_source && (
                    <span
                      className={`text-micro font-bold px-2 py-0.5 ${issue.rule_source.toLowerCase().includes('wisconsin') ? 'bg-blue-900 text-[var(--color-status-info)]' : 'bg-bg-raised text-[var(--color-text-secondary)]'}`}
                    >
                      {issue.rule_source}
                    </span>
                  )}
                </div>
                <p className="text-xs text-[var(--color-text-primary)]">{issue.plain_message}</p>
                {issue.fix_hint && (
                  <p className="text-body text-[var(--color-text-muted)] italic">{issue.fix_hint}</p>
                )}
                <div>
                  <button
                    onClick={() => fetchAiExplain(idx)}
                    disabled={aiLoadingIdx === idx}
                    className="text-body text-system-billing hover:underline disabled:opacity-40"
                  >
                    {aiLoadingIdx === idx ? 'Loading...' : 'AI Explain'}
                  </button>
                </div>
                {aiExplanations[idx] && (
                  <div className="mt-2 bg-bg-input border border-cyan-500/[0.15] p-3 space-y-2">
                    <div className="flex items-center gap-2">
                      <span className="text-micro font-bold text-system-billing">AI EXPLANATION</span>
                      <span className="text-micro bg-purple-900 text-purple-300 px-2 py-0.5 font-bold">
                        {aiExplanations[idx]!.fix_type}
                      </span>
                    </div>
                    <p className="text-xs text-[var(--color-text-primary)]">{aiExplanations[idx]!.plain_explanation}</p>
                    {aiExplanations[idx]!.patch_task?.steps?.length > 0 && (
                      <div>
                        <div className="text-micro text-[var(--color-text-muted)] mb-1 uppercase tracking-wider">Steps</div>
                        <ol className="space-y-1 list-decimal list-inside">
                          {aiExplanations[idx]!.patch_task.steps.map((step, si) => (
                            <li key={si} className="text-body text-[var(--color-text-secondary)]">{step}</li>
                          ))}
                        </ol>
                      </div>
                    )}
                  </div>
                )}
              </div>
            ))}
          </div>
        </div>
      )}

      <div className="bg-[var(--color-bg-panel)] border border-border-DEFAULT p-4">
        <div className="text-xs font-bold uppercase tracking-wider text-[var(--color-text-secondary)] mb-3">
          Certification Checklist
        </div>
        {certLoading ? (
          <div className="p-6"><QuantumTableSkeleton rows={6} cols={4} /></div>
        ) : certChecks.length === 0 ? (
          <div className="text-xs text-[var(--color-text-muted)]">No checklist data available</div>
        ) : (
          <div className="space-y-1.5">
            {certChecks.map((check, idx) => (
              <div key={idx} className="flex items-center gap-2">
                <span className={`text-sm ${check.passed ? 'text-[var(--color-status-active)]' : 'text-[var(--color-brand-red)]'}`}>
                  {check.passed ? '✓' : '✗'}
                </span>
                <span className="text-xs text-[var(--color-text-secondary)]">{check.label}</span>
              </div>
            ))}
          </div>
        )}
      </div>

      <div className="pt-2">
        <a href="/founder/epcr" className="text-xs text-system-billing hover:text-system-billing">
          ← Back to ePCR
        </a>
      </div>
    </div>
  );
}
