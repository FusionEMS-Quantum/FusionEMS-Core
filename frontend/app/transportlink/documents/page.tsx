'use client';

import React, { useState, useEffect, useCallback, useRef, Suspense } from 'react';
import { useSearchParams } from 'next/navigation';
import {
  Upload,
  FileText,
  AlertTriangle,
  CheckCircle2,
  Eye,
  Trash2,
  RefreshCw,
  Cpu,
  UserCheck,
  ChevronDown,
  ChevronUp,
  FileWarning,
  Info,
} from 'lucide-react';
import {
  applyTransportLinkOcrToRequest,
  deleteTransportLinkDocument,
  listTransportLinkDocuments,
  requestTransportLinkUploadUrl,
  triggerTransportLinkDocumentOcr,
  uploadTransportLinkDocumentToPresignedUrl,
} from '@/services/api';

// ─────────────────────────────────────────────────────────────
// Types
// ─────────────────────────────────────────────────────────────

type OcrStatus = 'idle' | 'uploading' | 'processing' | 'done' | 'error';

interface OcrField {
  key: string;
  label: string;
  raw_value: string;
  confidence: number; // 0–1
  suggestion: string;
  confirmed: boolean;
  rejected: boolean;
  confirmed_value: string;
}

interface DocumentRecord {
  id: string;
  request_id: string | null;
  filename: string;
  doc_type: 'facesheet' | 'pcs' | 'aob' | 'abn' | 'other';
  ocr_status: OcrStatus;
  s3_key: string;
  uploaded_at: string;
  fields: OcrField[];
  audit: AuditEntry[];
}

interface AuditEntry {
  ts: string;
  actor: string;
  action: string;
  detail?: string;
}

const DOC_TYPE_LABELS: Record<string, string> = {
  facesheet: 'Facesheet',
  pcs: 'Physician Certification Statement (PCS)',
  aob: 'Assignment of Benefits (AOB)',
  abn: 'Advance Beneficiary Notice (ABN)',
  other: 'Other',
};

const CONFIDENCE_COLOR = (c: number) => {
  if (c >= 0.85) return 'text-[var(--color-status-active)]';
  if (c >= 0.60) return 'text-status-warning';
  return 'text-red';
};

const CONFIDENCE_LABEL = (c: number) => {
  if (c >= 0.85) return 'High';
  if (c >= 0.60) return 'Medium';
  return 'Low';
};

// ─────────────────────────────────────────────────────────────
// OCR field row
// ─────────────────────────────────────────────────────────────

function OcrFieldRow({
  field,
  onChange,
}: {
  field: OcrField;
  onChange: (_updated: OcrField) => void;
}) {
  const [editing, setEditing] = useState(false);
  const [editValue, setEditValue] = useState(field.confirmed_value || field.suggestion);

  const confirm = () => {
    onChange({ ...field, confirmed: true, rejected: false, confirmed_value: editValue });
    setEditing(false);
  };

  const reject = () => {
    onChange({ ...field, confirmed: false, rejected: true });
    setEditing(false);
  };

  const startEdit = () => {
    setEditValue(field.confirmed_value || field.suggestion);
    setEditing(true);
  };

  return (
    <div
      className={`border p-3 transition-colors ${
        field.confirmed
          ? 'border-status-active/20 bg-status-active/[0.03]'
          : field.rejected
          ? 'border-red/15 bg-red/[0.02]'
          : 'border-white/[0.06] bg-[var(--color-bg-base)]/[0.02]'
      }`}
      style={{ clipPath: 'polygon(0 0, calc(100% - 5px) 0, 100% 5px, 100% 100%, 0 100%)' }}
    >
      <div className="flex items-start gap-3">
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 flex-wrap">
            <span className="text-[10px] font-black uppercase tracking-widest text-[var(--color-text-muted)]">{field.label}</span>
            <span className={`text-[9px] font-bold uppercase ${CONFIDENCE_COLOR(field.confidence)}`}>
              {CONFIDENCE_LABEL(field.confidence)} confidence ({Math.round(field.confidence * 100)}%)
            </span>
          </div>

          {editing ? (
            <div className="mt-2 flex items-center gap-2">
              <input
                type="text"
                value={editValue}
                onChange={(e) => setEditValue(e.target.value)}
                className="flex-1 h-8 px-2 bg-[var(--color-bg-base)]/[0.05] border border-white/[0.12] text-[11px] text-white focus:outline-none focus:border-orange/50"
                style={{ clipPath: 'polygon(0 0, calc(100% - 4px) 0, 100% 4px, 100% 100%, 0 100%)' }}
                autoFocus
              />
              <button
                onClick={confirm}
                className="h-8 px-3 text-[9px] font-black uppercase tracking-wider bg-status-active/15 border border-status-active/30 text-[var(--color-status-active)] hover:bg-status-active/25 transition-colors"
                style={{ clipPath: 'polygon(0 0, calc(100% - 4px) 0, 100% 4px, 100% 100%, 0 100%)' }}
              >
                Save
              </button>
              <button
                onClick={() => setEditing(false)}
                className="h-8 px-3 text-[9px] font-bold uppercase tracking-wider border border-white/[0.08] text-[var(--color-text-muted)] hover:text-[var(--color-text-primary)] transition-colors"
                style={{ clipPath: 'polygon(0 0, calc(100% - 4px) 0, 100% 4px, 100% 100%, 0 100%)' }}
              >
                Cancel
              </button>
            </div>
          ) : (
            <div className="mt-1">
              <div className="text-[11px] text-[var(--color-text-primary)] font-mono">
                {field.confirmed ? field.confirmed_value || field.suggestion : field.suggestion || '—'}
              </div>
              {field.raw_value && field.raw_value !== field.suggestion && (
                <div className="text-[9px] text-[var(--color-text-muted)] mt-0.5">OCR raw: <span className="font-mono">{field.raw_value}</span></div>
              )}
            </div>
          )}
        </div>

        {!editing && (
          <div className="flex items-center gap-1.5 flex-shrink-0 mt-0.5">
            {field.confirmed && <CheckCircle2 className="w-3.5 h-3.5 text-[var(--color-status-active)]" />}
            {field.rejected && <span className="text-[9px] font-bold text-red">Rejected</span>}
            {!field.confirmed && !field.rejected && (
              <>
                <button
                  onClick={startEdit}
                  className="h-6 px-2 text-[8px] font-black uppercase tracking-wider border border-orange/20 bg-[var(--q-orange)]/[0.06] text-[var(--q-orange)] hover:bg-[var(--q-orange)]/15 transition-colors"
                  style={{ clipPath: 'polygon(0 0, calc(100% - 3px) 0, 100% 3px, 100% 100%, 0 100%)' }}
                >
                  Confirm
                </button>
                <button
                  onClick={reject}
                  className="h-6 px-2 text-[8px] font-bold uppercase tracking-wider border border-red/15 text-red/60 hover:text-red hover:border-red/25 transition-colors"
                  style={{ clipPath: 'polygon(0 0, calc(100% - 3px) 0, 100% 3px, 100% 100%, 0 100%)' }}
                >
                  Reject
                </button>
              </>
            )}
            {(field.confirmed || field.rejected) && (
              <button
                onClick={() => onChange({ ...field, confirmed: false, rejected: false })}
                className="h-6 px-2 text-[8px] font-bold uppercase tracking-wider border border-white/[0.06] text-[var(--color-text-muted)] hover:text-[var(--color-text-primary)] transition-colors"
                style={{ clipPath: 'polygon(0 0, calc(100% - 3px) 0, 100% 3px, 100% 100%, 0 100%)' }}
              >
                Reset
              </button>
            )}
          </div>
        )}
      </div>
    </div>
  );
}

// ─────────────────────────────────────────────────────────────
// Document card
// ─────────────────────────────────────────────────────────────

function DocumentCard({
  doc,
  onFieldChange,
  onApply,
  onDelete,
}: {
  doc: DocumentRecord;
  onFieldChange: (_docId: string, _field: OcrField) => void;
  onApply: (_doc: DocumentRecord) => void;
  onDelete: (_docId: string) => void;
}) {
  const [expanded, setExpanded] = useState(false);
  const [showAudit, setShowAudit] = useState(false);

  const totalFields = doc.fields.length;
  const confirmedFields = doc.fields.filter((f) => f.confirmed).length;
  const pendingFields = doc.fields.filter((f) => !f.confirmed && !f.rejected).length;
  const statusOk = doc.ocr_status === 'done';
  const allConfirmed = totalFields > 0 && pendingFields === 0;

  return (
    <div
      className="border border-white/[0.06] bg-[#0D0D0F] overflow-hidden"
      style={{ clipPath: 'polygon(0 0, calc(100% - 10px) 0, 100% 10px, 100% 100%, 0 100%)' }}
    >
      {/* Card header */}
      <div className="flex items-center gap-3 px-4 py-3 border-b border-white/[0.04]">
        <FileText className="w-4 h-4 text-[var(--q-orange)] flex-shrink-0" />
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 flex-wrap">
            <span className="text-[11px] font-black text-white truncate">{doc.filename}</span>
            <span className="text-[9px] font-bold uppercase tracking-widest text-[var(--q-orange)] border border-orange/20 bg-[var(--q-orange)]/[0.06] px-1.5"
              style={{ clipPath: 'polygon(0 0, calc(100% - 3px) 0, 100% 3px, 100% 100%, 0 100%)' }}>
              {DOC_TYPE_LABELS[doc.doc_type] ?? doc.doc_type}
            </span>
            {doc.ocr_status === 'processing' && (
              <span className="flex items-center gap-1 text-[9px] text-status-info font-bold">
                <RefreshCw className="w-2.5 h-2.5 animate-spin" /> OCR in progress…
              </span>
            )}
            {statusOk && pendingFields > 0 && (
              <span className="flex items-center gap-1 text-[9px] text-status-warning font-bold">
                <AlertTriangle className="w-2.5 h-2.5" /> {pendingFields} field{pendingFields !== 1 ? 's' : ''} need review
              </span>
            )}
            {statusOk && allConfirmed && (
              <span className="flex items-center gap-1 text-[9px] text-[var(--color-status-active)] font-bold">
                <CheckCircle2 className="w-2.5 h-2.5" /> All Confirmed
              </span>
            )}
          </div>
          <div className="text-[9px] text-[var(--color-text-muted)] mt-0.5">
            Uploaded {new Date(doc.uploaded_at).toLocaleString()}
            {doc.request_id && (
              <> · Request <span className="font-mono">{doc.request_id.slice(0, 8)}</span></>
            )}
          </div>
        </div>

        <div className="flex items-center gap-2 flex-shrink-0">
          {totalFields > 0 && (
            <span className="text-[9px] text-[var(--color-text-muted)]">{confirmedFields}/{totalFields}</span>
          )}
          <button
            onClick={() => setExpanded((v) => !v)}
            className="h-7 px-2 text-[9px] font-bold uppercase tracking-wider border border-white/[0.08] text-[var(--color-text-muted)] hover:text-[var(--color-text-primary)] transition-colors flex items-center gap-1"
            style={{ clipPath: 'polygon(0 0, calc(100% - 3px) 0, 100% 3px, 100% 100%, 0 100%)' }}
          >
            {expanded ? <ChevronUp className="w-3 h-3" /> : <ChevronDown className="w-3 h-3" />}
            {expanded ? 'Collapse' : 'Review Fields'}
          </button>
          <button
            onClick={() => onDelete(doc.id)}
            className="h-7 w-7 flex items-center justify-center border border-red/15 text-red/40 hover:text-red hover:border-red/30 transition-colors"
            style={{ clipPath: 'polygon(0 0, calc(100% - 3px) 0, 100% 3px, 100% 100%, 0 100%)' }}
          >
            <Trash2 className="w-3 h-3" />
          </button>
        </div>
      </div>

      {/* OCR fields */}
      {expanded && (
        <div className="p-4 space-y-2">
          {/* Human review notice */}
          <div className="flex items-start gap-2 p-2 border border-status-info/15 bg-status-info/[0.04] mb-3"
            style={{ clipPath: 'polygon(0 0, calc(100% - 4px) 0, 100% 4px, 100% 100%, 0 100%)' }}>
            <Info className="w-3.5 h-3.5 text-status-info flex-shrink-0 mt-0.5" />
            <p className="text-[10px] text-status-info/80">
              OCR suggestions are never applied automatically. Review each field below and confirm or reject. 
              Confirmed data is only applied to the request when you click <strong>Apply to Request</strong>.
            </p>
          </div>

          {doc.fields.length === 0 && doc.ocr_status === 'done' && (
            <p className="text-[10px] text-[var(--color-text-muted)] py-3 text-center">No extractable fields found in this document.</p>
          )}

          {doc.fields.map((field) => (
            <OcrFieldRow
              key={field.key}
              field={field}
              onChange={(updated) => onFieldChange(doc.id, updated)}
            />
          ))}

          {doc.fields.length > 0 && doc.request_id && (
            <div className="pt-3 flex items-center gap-2 flex-wrap">
              <button
                onClick={() => onApply(doc)}
                disabled={pendingFields > 0}
                className={`flex items-center gap-1.5 h-9 px-4 text-[10px] font-black uppercase tracking-wider transition-colors ${
                  pendingFields > 0
                    ? 'opacity-40 cursor-not-allowed bg-[var(--q-orange)]/[0.06] border-orange/15 text-[var(--q-orange)]'
                    : 'bg-[var(--q-orange)] hover:bg-[#FF6A1A] text-white'
                } border border-orange/30`}
                style={{ clipPath: 'polygon(0 0, calc(100% - 5px) 0, 100% 5px, 100% 100%, 0 100%)' }}
              >
                <UserCheck className="w-3.5 h-3.5" />
                Apply to Request
              </button>
              {pendingFields > 0 && (
                <span className="text-[9px] text-[var(--color-text-muted)]">
                  Confirm all fields before applying.
                </span>
              )}
            </div>
          )}

          {/* Audit trail */}
          {doc.audit.length > 0 && (
            <div className="pt-2 mt-2 border-t border-white/[0.04]">
              <button
                onClick={() => setShowAudit((v) => !v)}
                className="text-[9px] font-bold uppercase tracking-widest text-[var(--color-text-muted)] hover:text-[var(--color-text-primary)] flex items-center gap-1"
              >
                {showAudit ? <ChevronUp className="w-2.5 h-2.5" /> : <ChevronDown className="w-2.5 h-2.5" />}
                Audit Trail ({doc.audit.length})
              </button>
              {showAudit && (
                <div className="mt-2 space-y-1">
                  {doc.audit.map((a, i) => (
                    <div key={i} className="flex items-baseline gap-2 text-[9px]">
                      <span className="text-[var(--color-text-muted)] font-mono">{new Date(a.ts).toLocaleString()}</span>
                      <span className="text-[var(--color-text-muted)]/60">·</span>
                      <span className="text-[var(--q-orange)]/70 font-semibold">{a.actor}</span>
                      <span className="text-[var(--color-text-muted)]">{a.action}</span>
                      {a.detail && <span className="text-[var(--color-text-muted)]/60">{a.detail}</span>}
                    </div>
                  ))}
                </div>
              )}
            </div>
          )}
        </div>
      )}
    </div>
  );
}

// ─────────────────────────────────────────────────────────────
// Upload zone
// ─────────────────────────────────────────────────────────────

function UploadZone({
  requestId,
  onUploaded,
}: {
  requestId: string | null;
  onUploaded: (_doc: DocumentRecord) => void;
}) {
  const inputRef = useRef<HTMLInputElement>(null);
  const [dragging, setDragging] = useState(false);
  const [docType, setDocType] = useState<DocumentRecord['doc_type']>('facesheet');
  const [uploading, setUploading] = useState(false);
  const [error, setError] = useState('');

  const upload = useCallback(async (file: File) => {
    if (!requestId) {
      setError('Select a request before uploading a document.');
      return;
    }

    setUploading(true);
    setError('');

    try {
      // Step 1: Get presigned URL
      const presignedPayload = await requestTransportLinkUploadUrl(requestId, {
        filename: file.name,
        content_type: file.type,
        doc_type: docType,
      });

      const { upload: presigned, document_id } = presignedPayload;

      // Step 2: PUT to presigned URL
      await uploadTransportLinkDocumentToPresignedUrl(presigned.url, file);

      // Step 3: Notify backend to kick off OCR
      await triggerTransportLinkDocumentOcr(document_id);

      // Return optimistic record while OCR processes
      const newDoc: DocumentRecord = {
        id: document_id ?? crypto.randomUUID(),
        request_id: requestId,
        filename: file.name,
        doc_type: docType,
        ocr_status: 'processing',
        s3_key: '',
        uploaded_at: new Date().toISOString(),
        fields: [],
        audit: [
          {
            ts: new Date().toISOString(),
            actor: 'Current User',
            action: 'Uploaded document',
            detail: file.name,
          },
        ],
      };
      onUploaded(newDoc);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Upload error');
    } finally {
      setUploading(false);
    }
  }, [requestId, docType, onUploaded]);

  const handleDrop = (e: React.DragEvent<HTMLDivElement>) => {
    e.preventDefault();
    setDragging(false);
    const file = e.dataTransfer.files[0];
    if (file) upload(file);
  };

  const handleInput = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (file) upload(file);
  };

  return (
    <div className="space-y-3">
      <div className="flex items-center gap-3 flex-wrap">
        <div>
          <label className="text-[9px] font-black uppercase tracking-widest text-[var(--color-text-muted)] block mb-1">Document Type</label>
          <select
            value={docType}
            onChange={(e) => setDocType(e.target.value as DocumentRecord['doc_type'])}
            className="h-9 px-3 bg-[var(--color-bg-base)]/[0.05] border border-white/[0.10] text-[10px] text-[var(--color-text-primary)] focus:outline-none focus:border-orange/40"
            style={{ clipPath: 'polygon(0 0, calc(100% - 5px) 0, 100% 5px, 100% 100%, 0 100%)' }}
          >
            {Object.entries(DOC_TYPE_LABELS).map(([value, label]) => (
              <option key={value} value={value}>{label}</option>
            ))}
          </select>
        </div>
      </div>

      <div
        onDragOver={(e) => { e.preventDefault(); setDragging(true); }}
        onDragLeave={() => setDragging(false)}
        onDrop={handleDrop}
        onClick={() => inputRef.current?.click()}
        className={`relative flex flex-col items-center justify-center gap-2 p-8 cursor-pointer border-2 border-dashed transition-colors ${
          dragging
            ? 'border-orange/60 bg-[var(--q-orange)]/[0.06]'
            : 'border-white/[0.10] bg-[var(--color-bg-base)]/[0.02] hover:border-white/[0.20] hover:bg-[var(--color-bg-base)]/[0.03]'
        }`}
        style={{ clipPath: 'polygon(0 0, calc(100% - 8px) 0, 100% 8px, 100% 100%, 0 100%)' }}
      >
        <input
          ref={inputRef}
          type="file"
          accept=".pdf,.png,.jpg,.jpeg,.tiff,.bmp"
          className="hidden"
          onChange={handleInput}
        />
        {uploading ? (
          <>
            <RefreshCw className="w-8 h-8 text-[var(--q-orange)] animate-spin" />
            <span className="text-[11px] text-[var(--color-text-muted)]">Uploading…</span>
          </>
        ) : (
          <>
            <Upload className="w-8 h-8 text-[var(--color-text-muted)]/30" />
            <div className="text-center">
              <p className="text-[11px] text-[var(--color-text-primary)] font-semibold">Drop PDF, PNG, JPEG, or TIFF here</p>
              <p className="text-[10px] text-[var(--color-text-muted)] mt-0.5">or click to browse · Max 25 MB</p>
            </div>
          </>
        )}
      </div>

      {error && (
        <div className="flex items-center gap-2 p-2 border border-red/20 bg-red/[0.05]"
          style={{ clipPath: 'polygon(0 0, calc(100% - 4px) 0, 100% 4px, 100% 100%, 0 100%)' }}>
          <FileWarning className="w-3.5 h-3.5 text-red flex-shrink-0" />
          <span className="text-[10px] text-red">{error}</span>
        </div>
      )}
    </div>
  );
}

// ─────────────────────────────────────────────────────────────
// Page inner (can call useSearchParams)
// ─────────────────────────────────────────────────────────────

function DocumentsPageInner() {
  const params = useSearchParams();
  const requestId = params.get('requestId');

  const [docs, setDocs] = useState<DocumentRecord[]>([]);
  const [loading, setLoading] = useState(true);
  const [loadError, setLoadError] = useState('');
  const [actionError, setActionError] = useState('');

  const loadDocs = useCallback(async () => {
    setLoading(true);
    setLoadError('');
    try {
      const records = await listTransportLinkDocuments(requestId ?? undefined);
      setDocs(records as DocumentRecord[]);
    } catch (err) {
      setLoadError(err instanceof Error ? err.message : 'Unable to load documents.');
      setDocs([]);
    } finally {
      setLoading(false);
    }
  }, [requestId]);

  useEffect(() => { loadDocs(); }, [loadDocs]);

  const handleFieldChange = (docId: string, updated: OcrField) => {
    setDocs((prev) =>
      prev.map((d) =>
        d.id !== docId
          ? d
          : {
              ...d,
              fields: d.fields.map((f) => (f.key === updated.key ? updated : f)),
              audit: [
                ...d.audit,
                {
                  ts: new Date().toISOString(),
                  actor: 'Current User',
                  action: updated.confirmed ? `Confirmed field: ${updated.label}` : `Rejected field: ${updated.label}`,
                  detail: updated.confirmed ? `Value: ${updated.confirmed_value}` : undefined,
                },
              ],
            }
      )
    );
  };

  const handleApply = async (doc: DocumentRecord) => {
    setActionError('');
    const confirmedMap: Record<string, string> = {};
    doc.fields.forEach((f) => {
      if (f.confirmed) confirmedMap[f.key] = f.confirmed_value;
    });

    try {
      const result = await applyTransportLinkOcrToRequest(doc.id, {
        request_id: doc.request_id,
        confirmed_fields: confirmedMap,
      });
      setDocs((prev) =>
        prev.map((d) =>
          d.id !== doc.id
            ? d
            : {
                ...d,
                audit: [
                  ...d.audit,
                  {
                    ts: new Date().toISOString(),
                    actor: 'Current User',
                    action: 'Applied confirmed OCR fields to request',
                    detail: `${result.applied} fields applied (${result.skipped} skipped)`,
                  },
                ],
              }
        )
      );
    } catch (err) {
      setActionError(err instanceof Error ? err.message : 'Failed to apply OCR fields.');
    }
  };

  const handleDelete = async (docId: string) => {
    if (!confirm('Remove this document? This cannot be undone.')) return;
    setActionError('');
    try {
      const deleted = await deleteTransportLinkDocument(docId);
      if (!deleted) {
        setActionError('Delete was not acknowledged by the server.');
        return;
      }
      setDocs((prev) => prev.filter((d) => d.id !== docId));
    } catch (err) {
      setActionError(err instanceof Error ? err.message : 'Failed to delete document.');
    }
  };

  const handleUploaded = (doc: DocumentRecord) => {
    setDocs((prev) => [doc, ...prev]);
  };

  const pendingTotal = docs.filter((d) => d.fields.some((f) => !f.confirmed && !f.rejected)).length;

  return (
    <div className="p-5 max-w-4xl mx-auto">
      {/* Header */}
      <div className="mb-5">
        <div className="text-[9px] font-bold tracking-[0.3em] text-[var(--q-orange)] uppercase mb-1">TransportLink · Documents</div>
        <h1 className="text-h1 font-black text-white">Documents &amp; OCR Review</h1>
        {requestId && (
          <p className="text-[11px] text-[var(--color-text-muted)] mt-1">
            Showing documents for request <span className="font-mono text-[var(--color-text-primary)]">{requestId.slice(0, 8)}…</span>
          </p>
        )}
      </div>

      {/* OCR notice */}
      <div className="flex items-start gap-3 p-3 border border-orange/20 bg-[var(--q-orange)]/[0.04] mb-5"
        style={{ clipPath: 'polygon(0 0, calc(100% - 8px) 0, 100% 8px, 100% 100%, 0 100%)' }}>
        <Cpu className="w-4 h-4 text-[var(--q-orange)] flex-shrink-0 mt-0.5" />
        <div>
          <p className="text-[10px] text-[var(--color-text-primary)] font-bold">OCR Extraction — Human Review Required</p>
          <p className="text-[10px] text-[var(--color-text-muted)] mt-0.5">
            All OCR suggestions must be individually confirmed or rejected by a human before they can be applied to a
            transport request. Data is never silently overwritten.
          </p>
        </div>
      </div>

      {pendingTotal > 0 && (
        <div className="flex items-center gap-2 p-2 border border-status-warning/20 bg-status-warning/[0.04] mb-4"
          style={{ clipPath: 'polygon(0 0, calc(100% - 5px) 0, 100% 5px, 100% 100%, 0 100%)' }}>
          <AlertTriangle className="w-3.5 h-3.5 text-status-warning flex-shrink-0" />
          <span className="text-[10px] text-status-warning font-semibold">
            {pendingTotal} document{pendingTotal !== 1 ? 's' : ''} have fields awaiting review.
          </span>
        </div>
      )}

      {loadError && (
        <div className="mb-4 flex items-center gap-2 border border-red/25 bg-red/[0.06] p-2.5"
          style={{ clipPath: 'polygon(0 0, calc(100% - 4px) 0, 100% 4px, 100% 100%, 0 100%)' }}>
          <AlertTriangle className="h-3.5 w-3.5 flex-shrink-0 text-red" />
          <span className="text-[10px] text-red">{loadError}</span>
        </div>
      )}

      {actionError && (
        <div className="mb-4 flex items-center gap-2 border border-red/25 bg-red/[0.06] p-2.5"
          style={{ clipPath: 'polygon(0 0, calc(100% - 4px) 0, 100% 4px, 100% 100%, 0 100%)' }}>
          <AlertTriangle className="h-3.5 w-3.5 flex-shrink-0 text-red" />
          <span className="text-[10px] text-red">{actionError}</span>
        </div>
      )}

      {/* Upload zone */}
      <div
        className="p-4 border border-white/[0.06] bg-[#0D0D0F] mb-6"
        style={{ clipPath: 'polygon(0 0, calc(100% - 10px) 0, 100% 10px, 100% 100%, 0 100%)' }}
      >
        <div className="text-[10px] font-black uppercase tracking-widest text-[var(--color-text-muted)] mb-3 flex items-center gap-2">
          <Upload className="w-3 h-3" />
          Upload New Document
        </div>
        <UploadZone requestId={requestId} onUploaded={handleUploaded} />
      </div>

      {/* Document list */}
      <div>
        <div className="flex items-center justify-between mb-3">
          <div className="text-[10px] font-black uppercase tracking-widest text-[var(--color-text-muted)] flex items-center gap-2">
            <FileText className="w-3 h-3" />
            Documents ({docs.length})
          </div>
          <button
            onClick={loadDocs}
            disabled={loading}
            className="flex items-center gap-1.5 h-7 px-2 text-[9px] font-bold uppercase tracking-wider border border-white/[0.06] text-[var(--color-text-muted)] hover:text-[var(--color-text-primary)] transition-colors"
            style={{ clipPath: 'polygon(0 0, calc(100% - 3px) 0, 100% 3px, 100% 100%, 0 100%)' }}
          >
            <RefreshCw className={`w-2.5 h-2.5 ${loading ? 'animate-spin' : ''}`} />
            Refresh
          </button>
        </div>

        {loading ? (
          <div className="flex items-center justify-center h-32">
            <div className="flex items-center gap-2 text-[var(--color-text-muted)] text-[11px]">
              <RefreshCw className="w-3.5 h-3.5 animate-spin" /> Loading documents…
            </div>
          </div>
        ) : docs.length === 0 ? (
          <div className="flex flex-col items-center justify-center py-16 gap-3 border border-dashed border-white/[0.06]"
            style={{ clipPath: 'polygon(0 0, calc(100% - 8px) 0, 100% 8px, 100% 100%, 0 100%)' }}>
            <Eye className="w-10 h-10 text-[var(--color-text-muted)]/20" />
            <p className="text-[11px] text-[var(--color-text-muted)]">
              {loadError ? 'Documents unavailable. Resolve the error and retry.' : 'No documents uploaded yet.'}
            </p>
          </div>
        ) : (
          <div className="space-y-3">
            {docs.map((doc) => (
              <DocumentCard
                key={doc.id}
                doc={doc}
                onFieldChange={handleFieldChange}
                onApply={handleApply}
                onDelete={handleDelete}
              />
            ))}
          </div>
        )}
      </div>
    </div>
  );
}

// ─────────────────────────────────────────────────────────────
// Export with Suspense boundary
// ─────────────────────────────────────────────────────────────

export default function DocumentsPage() {
  return (
    <Suspense
      fallback={
        <div className="flex items-center justify-center h-64 text-[var(--color-text-muted)] text-[11px] gap-2">
          <RefreshCw className="w-3.5 h-3.5 animate-spin" /> Loading…
        </div>
      }
    >
      <DocumentsPageInner />
    </Suspense>
  );
}
