'use client';
import { QuantumTableSkeleton } from '@/components/ui';
import { SeverityBadge } from '@/components/ui';
import { useState, useEffect, useCallback, useRef } from 'react';
import type { SeverityLevel } from '@/lib/design-system/tokens';
import {
  createNEMSISPack,
  generatePatchTasksFromResult,
  getActiveNEMSISPacks,
  getNEMSISCertificationChecklist,
  nemsisStudioAiExplain,
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

  useEffect(() => {
    fetchPackStatus();
    fetchCertChecks();
  }, [fetchPackStatus, fetchCertChecks]);

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

  const blockingCount = validationResult?.issues.filter((i) => validationSeverityToCanonical(i.severity) === 'BLOCKING').length ?? (() => { throw new Error('Unsafe silent fallback. Dependency missing.'); })();
  const mediumCount = validationResult?.issues.filter((i) => validationSeverityToCanonical(i.severity) === 'MEDIUM').length ?? (() => { throw new Error('Unsafe silent fallback. Dependency missing.'); })();

  return (
    <div className="p-5 space-y-6 min-h-screen bg-black">
      <div>
        <div className="text-micro font-bold uppercase tracking-[0.2em] text-system-billing mb-1">
          ePCR · COMPLIANCE STUDIO
        </div>
        <h1 className="text-xl font-black uppercase tracking-wider text-zinc-100">Compliance Studio</h1>
        <p className="text-xs text-zinc-500 mt-0.5">
          Turn-key visual certification — resource packs, validation, AI fix list
        </p>
      </div>

      <div className="bg-[#0A0A0B] border border-border-DEFAULT p-4 space-y-2">
        <div className="text-xs font-bold uppercase tracking-wider text-zinc-400 mb-3">Pack Status</div>
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
                    className={`inline-block w-2 h-2  ${pack?.active ? 'bg-green-400' : 'bg-red-500'}`}
                  />
                  <span className="text-xs text-zinc-100">{pack?.name || label}</span>
                  <span className={`text-micro font-bold ${pack?.active ? 'text-green-400' : 'text-red-400'}`}>
                    {pack?.active ? 'Active' : 'Missing'}
                  </span>
                </div>
              );
            })}
          </div>
        )}
      </div>

      <div
        className={`border-2 border-dashed chamfer-4 transition-colors ${isDragging ? 'border-cyan-400 bg-bg-input' : 'border-border-strong bg-[#0A0A0B]'} p-8 text-center`}
        onDragOver={(e) => { e.preventDefault(); setIsDragging(true); }}
        onDragLeave={() => setIsDragging(false)}
        onDrop={handleDrop}
      >
        <div className="text-zinc-400 text-sm mb-2">
          Drop NEMSIS resource files here (XSD, Schematron, StateDataSet, ZIP)
        </div>
        <div className="text-zinc-500 text-xs mb-4">or click to browse</div>
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
          <div className="mt-3 text-xs text-zinc-400">{uploadStatus}</div>
        )}
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
            className="bg-bg-input border border-border-strong text-zinc-400 text-xs px-3 py-2 hover:border-white/[0.3] transition-colors"
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
                className={`text-xs font-bold px-2 py-1 ${validationResult.valid ? 'bg-green-900 text-green-300' : 'bg-red-900 text-red-300'}`}
              >
                {validationResult.valid ? 'VALID' : 'INVALID'}
              </span>
              <span className="text-xs text-red-400">{blockingCount} blocking issue{blockingCount !== 1 ? 's' : ''}</span>
              <span className="text-xs text-yellow-400">{mediumCount} medium issue{mediumCount !== 1 ? 's' : ''}</span>
            </div>
            <button
              onClick={sendAllToAgent}
              className="text-xs bg-[#0A0A0B] border border-cyan-500/[0.3] text-system-billing px-3 py-1.5 hover:bg-cyan-500/[0.08] transition-colors"
            >
              Send All to Agent
            </button>
          </div>

          <div className="space-y-2">
            {validationResult.issues.map((issue, idx) => (
              <div
                key={idx}
                className="bg-[#0A0A0B] border border-border-DEFAULT p-4 space-y-2"
              >
                <div className="flex flex-wrap items-center gap-2">
                  <SeverityBadge
                    severity={validationSeverityToCanonical(issue.severity)}
                    size="sm"
                    label={validationSeverityToCanonical(issue.severity)}
                  />
                  <span className="text-xs font-mono text-system-billing">{issue.element_id}</span>
                  {issue.ui_section && (
                    <span className="text-micro text-zinc-500">{issue.ui_section}</span>
                  )}
                  {issue.rule_source && (
                    <span
                      className={`text-micro font-bold px-2 py-0.5 ${issue.rule_source.toLowerCase().includes('wisconsin') ? 'bg-blue-900 text-blue-300' : 'bg-bg-raised text-zinc-400'}`}
                    >
                      {issue.rule_source}
                    </span>
                  )}
                </div>
                <p className="text-xs text-zinc-100">{issue.plain_message}</p>
                {issue.fix_hint && (
                  <p className="text-body text-zinc-500 italic">{issue.fix_hint}</p>
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
                    <p className="text-xs text-zinc-100">{aiExplanations[idx]!.plain_explanation}</p>
                    {aiExplanations[idx]!.patch_task?.steps?.length > 0 && (
                      <div>
                        <div className="text-micro text-zinc-500 mb-1 uppercase tracking-wider">Steps</div>
                        <ol className="space-y-1 list-decimal list-inside">
                          {aiExplanations[idx]!.patch_task.steps.map((step, si) => (
                            <li key={si} className="text-body text-zinc-400">{step}</li>
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

      <div className="bg-[#0A0A0B] border border-border-DEFAULT p-4">
        <div className="text-xs font-bold uppercase tracking-wider text-zinc-400 mb-3">
          Certification Checklist
        </div>
        {certLoading ? (
          <div className="p-6"><QuantumTableSkeleton rows={6} cols={4} /></div>
        ) : certChecks.length === 0 ? (
          <div className="text-xs text-zinc-500">No checklist data available</div>
        ) : (
          <div className="space-y-1.5">
            {certChecks.map((check, idx) => (
              <div key={idx} className="flex items-center gap-2">
                <span className={`text-sm ${check.passed ? 'text-green-400' : 'text-red-400'}`}>
                  {check.passed ? '✓' : '✗'}
                </span>
                <span className="text-xs text-zinc-400">{check.label}</span>
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
