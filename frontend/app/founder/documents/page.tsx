'use client';

import React, { useState, useEffect, useCallback, useRef } from 'react';
import {
  FolderOpen, Upload, Search, Lock, FileText, Download,
  Cpu, ChevronRight, RotateCcw, Package, ScrollText, Plus, X,
  RefreshCw,
} from 'lucide-react';
import { API } from '@/services/api';

// ── Types ─────────────────────────────────────────────────────────────────────

interface Vault {
  id: string;
  vault_id: string;
  display_name: string;
  description: string;
  retention_class: string;
  retention_years: number | null;
  is_permanent: boolean;
  icon_key: string;
  document_count: number;
}

interface Document {
  id: string;
  vault_id: string;
  title: string;
  original_filename: string;
  content_type: string;
  file_size_bytes: number | null;
  lock_state: string;
  retention_class: string | null;
  retain_until: string | null;
  ocr_status: string | null;
  ai_classification_status: string | null;
  ai_document_type: string | null;
  ai_tags: string[] | null;
  ai_summary: string | null;
  created_at: string | null;
  uploaded_by_display: string | null;
}

interface DocumentDetail extends Document {
  s3_key: string;
  checksum_sha256: string | null;
  ocr_text: string | null;
  ai_confidence: number | null;
  ai_classified_at: string | null;
  doc_metadata: Record<string, unknown> | null;
  addenda: unknown[] | null;
  lock_history: unknown[] | null;
}

interface AuditEntry {
  id: string;
  action: string;
  actor_display: string | null;
  occurred_at: string | null;
  detail: Record<string, unknown> | null;
}

// ── Helpers ───────────────────────────────────────────────────────────────────

function authHeader(): Record<string, string> {
  if (typeof window === 'undefined') return {};
  const t = localStorage.getItem('token');
  return t ? { Authorization: `Bearer ${t}` } : {};
}

function formatBytes(b: number | null): string {
  if (!b) return '—';
  if (b < 1024) return `${b} B`;
  if (b < 1_048_576) return `${(b / 1024).toFixed(1)} KB`;
  return `${(b / 1_048_576).toFixed(1)} MB`;
}

function lockBadgeColor(state: string): string {
  const m: Record<string, string> = {
    active: 'var(--color-status-active)',
    archived: '#6B7280',
    legal_hold: 'var(--color-brand-red)',
    tax_hold: 'var(--q-yellow)',
    compliance_hold: '#8B5CF6',
    pending_review: 'var(--color-status-info)',
    destroy_blocked: '#DC2626',
    destroyed: 'var(--color-border-default)',
  };
  return m[state] ?? '#6B7280';
}

const LOCK_STATES = [
  'active', 'archived', 'legal_hold', 'tax_hold',
  'compliance_hold', 'pending_review', 'destroy_blocked', 'destroyed',
];

// ── Main Component ────────────────────────────────────────────────────────────

export default function DocumentManagerPage() {
  const [vaults, setVaults] = useState<Vault[]>([]);
  const [selectedVault, setSelectedVault] = useState<string | null>(null);
  const [documents, setDocuments] = useState<Document[]>([]);
  const [selectedDoc, setSelectedDoc] = useState<DocumentDetail | null>(null);
  const [auditTrail, setAuditTrail] = useState<AuditEntry[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Search / filter
  const [searchQuery, setSearchQuery] = useState('');
  const [filterLockState, setFilterLockState] = useState('');

  // Panels
  const [activePanel, setActivePanel] = useState<'detail' | 'audit' | 'upload' | 'lock' | 'addendum' | 'export' | null>(null);

  // Upload state
  const [uploadVault, setUploadVault] = useState('');
  const [uploadTitle, setUploadTitle] = useState('');
  const [uploadFile, setUploadFile] = useState<File | null>(null);
  const [uploading, setUploading] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);

  // Lock state change
  const [lockTargetState, setLockTargetState] = useState('');
  const [lockReason, setLockReason] = useState('');

  // Addendum
  const [addendumNote, setAddendumNote] = useState('');
  const [addendumReason, setAddendumReason] = useState('');

  // Export package
  const [exportName, setExportName] = useState('');
  const [exportReason, setExportReason] = useState('');
  const [exportDocIds, setExportDocIds] = useState<string[]>([]);

  const [classifyingId, setClassifyingId] = useState<string | null>(null);
  const [pollingOCR, setPollingOCR] = useState<string | null>(null);
  const [buildingPkg, setBuildingPkg] = useState<string | null>(null);

  // ── API ─────────────────────────────────────────────────────────────────────

  const fetchVaults = useCallback(async () => {
    try {
      const res = await API.get('/api/v1/founder/vault/vaults', { headers: authHeader() });
      setVaults(res.data || []);
    } catch { /* handled by error state */ }
  }, []);

  const fetchDocuments = useCallback(async (vaultId: string | null) => {
    if (!vaultId) { setDocuments([]); return; }
    setLoading(true);
    setError(null);
    try {
      const params: Record<string, string> = {};
      if (searchQuery) params.q = searchQuery;
      if (filterLockState) params.lock_state = filterLockState;
      const res = await API.get(`/api/v1/founder/vault/vaults/${vaultId}/documents`, {
        headers: authHeader(),
        params,
      });
      setDocuments(res.data?.documents ?? []);
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : 'Failed to load documents');
    } finally {
      setLoading(false);
    }
  }, [searchQuery, filterLockState]);

  const fetchDocumentDetail = useCallback(async (docId: string) => {
    try {
      const [detailRes, auditRes] = await Promise.all([
        API.get(`/api/v1/founder/vault/documents/${docId}`, { headers: authHeader() }),
        API.get(`/api/v1/founder/vault/documents/${docId}/audit`, { headers: authHeader() }),
      ]);
      setSelectedDoc(detailRes.data);
      setAuditTrail(auditRes.data?.entries ?? []);
      setActivePanel('detail');
    } catch { /* noop */ }
  }, []);

  useEffect(() => { fetchVaults(); }, [fetchVaults]);
  useEffect(() => { fetchDocuments(selectedVault); }, [selectedVault, fetchDocuments]);

  // ── Upload flow ─────────────────────────────────────────────────────────────

  const handleUpload = async () => {
    if (!uploadFile || !uploadVault || !uploadTitle) return;
    setUploading(true);
    try {
      // Step 1: initiate upload
      const initRes = await API.post(
        `/api/v1/founder/vault/vaults/${uploadVault}/upload/initiate`,
        {
          title: uploadTitle,
          original_filename: uploadFile.name,
          content_type: uploadFile.type || 'application/octet-stream',
          file_size_bytes: uploadFile.size,
          doc_metadata: {},
        },
        { headers: authHeader() },
      );
      const { document_id, presigned_url, presigned_fields } = initRes.data;

      // Step 2: PUT directly to S3 presigned URL (CORS must allow)
      const fd = new FormData();
      Object.entries(presigned_fields as Record<string, string>).forEach(([k, v]) => fd.append(k, v));
      fd.append('file', uploadFile);
      await fetch(presigned_url, { method: 'POST', body: fd });

      // Step 3: confirm
      await API.post(
        `/api/v1/founder/vault/documents/${document_id}/upload/confirm`,
        { file_size_bytes: uploadFile.size },
        { headers: authHeader() },
      );

      setActivePanel(null);
      setUploadFile(null);
      setUploadTitle('');
      await fetchVaults();
      if (uploadVault === selectedVault) await fetchDocuments(selectedVault);
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : 'Upload failed');
    } finally {
      setUploading(false);
    }
  };

  // ── Download ────────────────────────────────────────────────────────────────

  const handleDownload = async (docId: string) => {
    try {
      const res = await API.post(`/api/v1/founder/vault/documents/${docId}/download`, {}, { headers: authHeader() });
      window.open(res.data.presigned_url, '_blank');
    } catch { /* noop */ }
  };

  // ── Lock state ──────────────────────────────────────────────────────────────

  const handleLockChange = async () => {
    if (!selectedDoc || !lockTargetState || !lockReason) return;
    try {
      await API.post(
        `/api/v1/founder/vault/documents/${selectedDoc.id}/lock`,
        { lock_state: lockTargetState, reason: lockReason },
        { headers: authHeader() },
      );
      setLockTargetState('');
      setLockReason('');
      setActivePanel('detail');
      await fetchDocumentDetail(selectedDoc.id);
      await fetchDocuments(selectedVault);
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : 'Lock change failed');
    }
  };

  // ── Addendum ────────────────────────────────────────────────────────────────

  const handleAddendum = async () => {
    if (!selectedDoc || !addendumNote || !addendumReason) return;
    try {
      await API.post(
        `/api/v1/founder/vault/documents/${selectedDoc.id}/addendum`,
        { note: addendumNote, reason: addendumReason },
        { headers: authHeader() },
      );
      setAddendumNote('');
      setAddendumReason('');
      setActivePanel('detail');
      await fetchDocumentDetail(selectedDoc.id);
    } catch { /* noop */ }
  };

  // ── OCR / classify ──────────────────────────────────────────────────────────

  const handlePollOCR = async (docId: string) => {
    setPollingOCR(docId);
    try {
      const res = await API.post(`/api/v1/founder/vault/documents/${docId}/ocr/poll`, {}, { headers: authHeader() });
      if (res.data?.ocr_status === 'classified') {
        await fetchDocumentDetail(docId);
        await fetchDocuments(selectedVault);
      }
    } finally {
      setPollingOCR(null);
    }
  };

  const handleClassify = async (docId: string) => {
    setClassifyingId(docId);
    try {
      await API.post(`/api/v1/founder/vault/documents/${docId}/classify`, {}, { headers: authHeader() });
      await fetchDocumentDetail(docId);
      await fetchDocuments(selectedVault);
    } finally {
      setClassifyingId(null);
    }
  };

  // ── Export package ──────────────────────────────────────────────────────────

  const handleCreateExportPackage = async () => {
    if (!exportName || exportDocIds.length === 0) return;
    try {
      const pkgRes = await API.post(
        '/api/v1/founder/vault/packages',
        { package_name: exportName, export_reason: exportReason, document_ids: exportDocIds },
        { headers: authHeader() },
      );
      const pkgId = pkgRes.data.id;
      setBuildingPkg(pkgId);
      const buildRes = await API.post(`/api/v1/founder/vault/packages/${pkgId}/build`, {}, { headers: authHeader() });
      window.open(buildRes.data.presigned_url, '_blank');
      setBuildingPkg(null);
      setActivePanel(null);
    } catch { setBuildingPkg(null); }
  };

  // ── Render ───────────────────────────────────────────────────────────────────

  return (
    <div className="flex h-[calc(100vh-60px)] bg-[var(--color-bg-input)] text-[var(--color-text-primary)] font-mono overflow-hidden">

      {/* ── Vault sidebar ──────────────────────────────────────────────────── */}
      <aside className="w-[260px] bg-[var(--color-bg-base)] border-r border-[var(--color-border-subtle)] flex flex-col overflow-hidden">
        <div className="p-4 pb-2 border-b border-[var(--color-border-subtle)]">
          <div className="flex items-center gap-2 mb-3">
            <FolderOpen size={16} color="var(--q-orange)" />
            <span className="text-xs font-bold tracking-[0.1em] text-[var(--q-orange)] uppercase">Document Vault</span>
          </div>
          <button
            onClick={() => { setUploadVault(selectedVault ?? ''); setActivePanel('upload'); }}
            className="w-full py-2 px-3 bg-[var(--q-orange)] text-black text-[11px] font-bold cursor-pointer flex items-center gap-1.5 justify-center chamfer-4"
          >
            <Upload size={12} /> Upload Document
          </button>
        </div>

        <div style={{ overflowY: 'auto', flex: 1 }}>
          <div style={{ padding: '8px 0' }}>
            <button
              onClick={() => setSelectedVault(null)}
              style={{ width: '100%', padding: '8px 16px', background: selectedVault === null ? 'var(--color-border-subtle)' : 'transparent', border: 'none', color: selectedVault === null ? 'var(--color-text-primary)' : 'var(--color-text-secondary)', fontSize: 12, textAlign: 'left', cursor: 'pointer', display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}
            >
              <span style={{ display: 'flex', alignItems: 'center', gap: 8 }}><FolderOpen size={14} /> All Vaults</span>
            </button>
            {vaults.map(v => (
              <button
                key={v.vault_id}
                onClick={() => setSelectedVault(v.vault_id)}
                style={{ width: '100%', padding: '8px 16px', background: selectedVault === v.vault_id ? 'var(--color-border-subtle)' : 'transparent', border: 'none', color: selectedVault === v.vault_id ? 'var(--color-text-primary)' : 'var(--color-text-secondary)', fontSize: 12, textAlign: 'left', cursor: 'pointer', display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}
              >
                <span style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                  <ChevronRight size={12} style={{ opacity: selectedVault === v.vault_id ? 1 : 0 }} />
                  {v.display_name}
                </span>
                <span style={{ fontSize: 10, background: 'var(--color-border-subtle)', clipPath: "polygon(0 0, calc(100% - 4px) 0, 100% 4px, 100% 100%, 0 100%)", padding: '1px 6px', color: 'var(--color-text-muted)' }}>{v.document_count}</span>
              </button>
            ))}
          </div>
        </div>

        {/* Export action */}
        <div style={{ borderTop: '1px solid var(--color-border-subtle)', padding: 12 }}>
          <button
            onClick={() => { setExportDocIds(documents.map(d => d.id)); setActivePanel('export'); }}
            style={{ width: '100%', padding: '7px 12px', background: 'transparent', border: '1px solid var(--color-border-default)', clipPath: "polygon(0 0, calc(100% - 4px) 0, 100% 4px, 100% 100%, 0 100%)", color: 'var(--color-text-secondary)', fontSize: 11, cursor: 'pointer', display: 'flex', alignItems: 'center', gap: 6, justifyContent: 'center' }}
          >
            <Package size={12} /> Export Package
          </button>
        </div>
      </aside>

      {/* ── Document list ───────────────────────────────────────────────────── */}
      <main style={{ flex: 1, display: 'flex', flexDirection: 'column', overflow: 'hidden' }}>
        {/* Toolbar */}
        <div style={{ padding: '12px 16px', borderBottom: '1px solid var(--color-border-subtle)', display: 'flex', gap: 8, alignItems: 'center', background: 'var(--color-bg-base)' }}>
          <div style={{ flex: 1, position: 'relative' }}>
            <Search size={13} style={{ position: 'absolute', left: 8, top: '50%', transform: 'translateY(-50%)', color: 'var(--color-text-muted)' }} />
            <input
              value={searchQuery}
              onChange={e => setSearchQuery(e.target.value)}
              onKeyDown={e => e.key === 'Enter' && fetchDocuments(selectedVault)}
              placeholder="Search documents..."
              style={{ width: '100%', padding: '6px 8px 6px 28px', background: 'var(--color-bg-input)', border: '1px solid var(--color-border-subtle)', clipPath: "polygon(0 0, calc(100% - 4px) 0, 100% 4px, 100% 100%, 0 100%)", color: 'var(--color-text-primary)', fontSize: 12, outline: 'none', boxSizing: 'border-box' }}
            />
          </div>
          <select
            value={filterLockState}
            onChange={e => { setFilterLockState(e.target.value); }}
            style={{ padding: '6px 8px', background: 'var(--color-bg-input)', border: '1px solid var(--color-border-subtle)', clipPath: "polygon(0 0, calc(100% - 4px) 0, 100% 4px, 100% 100%, 0 100%)", color: 'var(--color-text-secondary)', fontSize: 12, cursor: 'pointer' }}
          >
            <option value="">All states</option>
            {LOCK_STATES.map(s => <option key={s} value={s}>{s.replace('_', ' ')}</option>)}
          </select>
          <button onClick={() => fetchDocuments(selectedVault)} style={{ padding: '6px 10px', background: 'transparent', border: '1px solid var(--color-border-subtle)', clipPath: "polygon(0 0, calc(100% - 4px) 0, 100% 4px, 100% 100%, 0 100%)", color: 'var(--color-text-secondary)', fontSize: 12, cursor: 'pointer' }}>
            <RefreshCw size={12} />
          </button>
        </div>

        {/* Document table */}
        <div style={{ flex: 1, overflowY: 'auto' }}>
          {loading && <div style={{ padding: 32, textAlign: 'center', color: 'var(--color-text-muted)', fontSize: 12 }}>Loading…</div>}
          {error && <div style={{ padding: 16, color: 'var(--color-brand-red)', fontSize: 12 }}>{error}</div>}
          {!loading && !selectedVault && (
            <div style={{ padding: 32, textAlign: 'center', color: 'var(--color-text-muted)', fontSize: 12 }}>
              <FolderOpen size={32} style={{ margin: '0 auto 12px', display: 'block', opacity: 0.3 }} />
              Select a vault from the sidebar
            </div>
          )}
          {!loading && selectedVault && documents.length === 0 && (
            <div style={{ padding: 32, textAlign: 'center', color: 'var(--color-text-muted)', fontSize: 12 }}>
              <FileText size={32} style={{ margin: '0 auto 12px', display: 'block', opacity: 0.3 }} />
              No documents in this vault
            </div>
          )}
          {documents.length > 0 && (
            <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 12 }}>
              <thead>
                <tr style={{ borderBottom: '1px solid var(--color-border-subtle)', background: 'var(--color-bg-base)', position: 'sticky', top: 0 }}>
                  {['Title', 'Type', 'Lock State', 'OCR', 'AI', 'Size', 'Retain Until', 'Actions'].map(h => (
                    <th key={h} style={{ padding: '8px 12px', textAlign: 'left', color: 'var(--color-text-muted)', fontWeight: 600, fontSize: 10, letterSpacing: '0.05em', textTransform: 'uppercase', whiteSpace: 'nowrap' }}>{h}</th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {documents.map(doc => (
                  <tr
                    key={doc.id}
                    onClick={() => fetchDocumentDetail(doc.id)}
                    style={{ borderBottom: '1px solid #1a1a24', cursor: 'pointer', background: selectedDoc?.id === doc.id ? '#1a1a2e' : 'transparent' }}
                  >
                    <td style={{ padding: '8px 12px', maxWidth: 220, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                      <span title={doc.title}>{doc.title}</span>
                    </td>
                    <td style={{ padding: '8px 12px', color: 'var(--color-text-secondary)', fontSize: 11 }}>{doc.ai_document_type ?? '—'}</td>
                    <td style={{ padding: '8px 12px' }}>
                      <span style={{ padding: '2px 8px', clipPath: "polygon(0 0, calc(100% - 4px) 0, 100% 4px, 100% 100%, 0 100%)", fontSize: 10, fontWeight: 700, background: `${lockBadgeColor(doc.lock_state)}22`, color: lockBadgeColor(doc.lock_state), border: `1px solid ${lockBadgeColor(doc.lock_state)}44` }}>
                        {doc.lock_state}
                      </span>
                    </td>
                    <td style={{ padding: '8px 12px' }}>
                      <span style={{ fontSize: 10, color: doc.ocr_status === 'classified' ? 'var(--color-status-active)' : doc.ocr_status === 'failed' ? 'var(--color-brand-red)' : 'var(--q-yellow)' }}>
                        ● {doc.ocr_status ?? 'pending'}
                      </span>
                    </td>
                    <td style={{ padding: '8px 12px' }}>
                      {doc.ai_classification_status === 'classified' ? (
                        <span style={{ fontSize: 10, color: 'var(--color-status-active)' }}>● classified</span>
                      ) : doc.ai_classification_status === 'failed' ? (
                        <span style={{ fontSize: 10, color: 'var(--color-brand-red)' }}>● failed</span>
                      ) : (
                        <span style={{ fontSize: 10, color: 'var(--color-text-muted)' }}>● {doc.ai_classification_status ?? 'pending'}</span>
                      )}
                    </td>
                    <td style={{ padding: '8px 12px', color: 'var(--color-text-muted)', whiteSpace: 'nowrap' }}>{formatBytes(doc.file_size_bytes)}</td>
                    <td style={{ padding: '8px 12px', color: 'var(--color-text-muted)', whiteSpace: 'nowrap', fontSize: 11 }}>
                      {doc.retain_until ? new Date(doc.retain_until).toLocaleDateString() : doc.retention_class === 'legal_founder' || doc.retention_class === 'intellectual_prop' ? '∞ Permanent' : '—'}
                    </td>
                    <td style={{ padding: '8px 12px' }}>
                      <div style={{ display: 'flex', gap: 6 }} onClick={e => e.stopPropagation()}>
                        <button title="Download" onClick={() => handleDownload(doc.id)} style={iconBtn}><Download size={12} /></button>
                        <button title="Lock State" onClick={() => { fetchDocumentDetail(doc.id); setActivePanel('lock'); }} style={iconBtn}><Lock size={12} /></button>
                        {doc.ocr_status === 'processing' && (
                          <button title="Poll OCR" onClick={() => handlePollOCR(doc.id)} disabled={pollingOCR === doc.id} style={iconBtn}>
                            <RotateCcw size={12} style={{ animation: pollingOCR === doc.id ? 'spin 1s linear infinite' : 'none' }} />
                          </button>
                        )}
                        {doc.ocr_status === 'classified' && doc.ai_classification_status !== 'classified' && (
                          <button title="Run AI Classification" onClick={() => handleClassify(doc.id)} disabled={classifyingId === doc.id} style={iconBtn}>
                            <Cpu size={12} />
                          </button>
                        )}
                        <button title="Export" onClick={() => { setExportDocIds([doc.id]); setExportName(`Export - ${doc.title}`); setActivePanel('export'); }} style={iconBtn}><Package size={12} /></button>
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </div>
      </main>

      {/* ── Right panel ─────────────────────────────────────────────────────── */}
      {activePanel && (
        <aside style={{ width: activePanel === 'upload' ? 360 : 420, background: 'var(--color-bg-base)', borderLeft: '1px solid var(--color-border-subtle)', display: 'flex', flexDirection: 'column', overflow: 'hidden' }}>
          <div style={{ padding: '12px 16px', borderBottom: '1px solid var(--color-border-subtle)', display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
            <span style={{ fontSize: 12, fontWeight: 700, color: 'var(--color-text-primary)', textTransform: 'uppercase', letterSpacing: '0.05em' }}>
              {activePanel === 'detail' && 'Document Detail'}
              {activePanel === 'audit' && 'Audit Trail'}
              {activePanel === 'upload' && 'Upload Document'}
              {activePanel === 'lock' && 'Change Lock State'}
              {activePanel === 'addendum' && 'Append Addendum'}
              {activePanel === 'export' && 'Export Package'}
            </span>
            <button onClick={() => setActivePanel(null)} style={{ background: 'none', border: 'none', color: 'var(--color-text-muted)', cursor: 'pointer', padding: 2 }}><X size={14} /></button>
          </div>

          <div style={{ flex: 1, overflowY: 'auto', padding: 16 }}>

            {/* ── Detail panel ── */}
            {activePanel === 'detail' && selectedDoc && (
              <div style={{ fontSize: 12 }}>
                <section style={section}>
                  <h4 style={sectionLabel}>Title</h4>
                  <p style={fieldValue}>{selectedDoc.title}</p>
                </section>
                <section style={section}>
                  <h4 style={sectionLabel}>Filename</h4>
                  <p style={fieldValue}>{selectedDoc.original_filename}</p>
                </section>
                <section style={section}>
                  <h4 style={sectionLabel}>Lock State</h4>
                  <span style={{ padding: '2px 8px', clipPath: "polygon(0 0, calc(100% - 4px) 0, 100% 4px, 100% 100%, 0 100%)", fontSize: 11, fontWeight: 700, background: `${lockBadgeColor(selectedDoc.lock_state)}22`, color: lockBadgeColor(selectedDoc.lock_state) }}>
                    {selectedDoc.lock_state}
                  </span>
                </section>
                {selectedDoc.ai_summary && (
                  <section style={section}>
                    <h4 style={sectionLabel}>AI Summary</h4>
                    <p style={{ ...fieldValue, color: 'var(--color-status-info)' }}>{selectedDoc.ai_summary}</p>
                  </section>
                )}
                {selectedDoc.ai_tags && selectedDoc.ai_tags.length > 0 && (
                  <section style={section}>
                    <h4 style={sectionLabel}>AI Tags</h4>
                    <div style={{ display: 'flex', flexWrap: 'wrap', gap: 4 }}>
                      {selectedDoc.ai_tags.map((t, i) => (
                        <span key={i} style={{ padding: '2px 8px', clipPath: "polygon(0 0, calc(100% - 4px) 0, 100% 4px, 100% 100%, 0 100%)", fontSize: 10, background: 'var(--color-bg-base)', color: 'var(--color-status-info)', border: '1px solid var(--color-border-default)' }}>{t}</span>
                      ))}
                    </div>
                  </section>
                )}
                {selectedDoc.ocr_text && (
                  <section style={section}>
                    <h4 style={sectionLabel}>OCR Text Preview</h4>
                    <pre style={{ fontSize: 10, color: 'var(--color-text-muted)', whiteSpace: 'pre-wrap', maxHeight: 200, overflowY: 'auto', background: 'var(--color-bg-input)', padding: 8, clipPath: "polygon(0 0, calc(100% - 4px) 0, 100% 4px, 100% 100%, 0 100%)" }}>
                      {selectedDoc.ocr_text.slice(0, 1000)}{selectedDoc.ocr_text.length > 1000 ? '…' : ''}
                    </pre>
                  </section>
                )}
                {selectedDoc.addenda && selectedDoc.addenda.length > 0 && (
                  <section style={section}>
                    <h4 style={sectionLabel}>Addenda ({selectedDoc.addenda.length})</h4>
                    {(selectedDoc.addenda as Record<string, unknown>[]).map((a, i) => (
                      <div key={i} style={{ padding: 8, border: '1px solid var(--color-border-subtle)', clipPath: "polygon(0 0, calc(100% - 4px) 0, 100% 4px, 100% 100%, 0 100%)", marginBottom: 6 }}>
                        <div style={{ color: 'var(--color-text-muted)', fontSize: 10, marginBottom: 4 }}>{String(a.timestamp ?? '').replace('T', ' ').slice(0, 19)} — {String(a.actor ?? 'unknown')}</div>
                        <div style={{ color: 'var(--color-text-secondary)', fontSize: 11 }}>{String(a.reason ?? '')}</div>
                      </div>
                    ))}
                  </section>
                )}
                <div style={{ display: 'flex', gap: 6, marginTop: 12 }}>
                  <button onClick={() => handleDownload(selectedDoc.id)} style={primaryBtn}><Download size={12} /> Download</button>
                  <button onClick={() => setActivePanel('audit')} style={secondaryBtn}><ScrollText size={12} /> Audit</button>
                  <button onClick={() => setActivePanel('lock')} style={secondaryBtn}><Lock size={12} /> Lock</button>
                  <button onClick={() => setActivePanel('addendum')} style={secondaryBtn}><Plus size={12} /> Addendum</button>
                </div>
              </div>
            )}

            {/* ── Audit trail ── */}
            {activePanel === 'audit' && (
              <div>
                <button onClick={() => setActivePanel('detail')} style={{ ...secondaryBtn, marginBottom: 12 }}><ChevronRight size={12} style={{ transform: 'rotate(180deg)' }} /> Back</button>
                {auditTrail.length === 0 && <p style={{ color: 'var(--color-text-muted)', fontSize: 12 }}>No audit entries.</p>}
                {auditTrail.map(e => (
                  <div key={e.id} style={{ padding: '8px 0', borderBottom: '1px solid var(--color-border-subtle)', fontSize: 11 }}>
                    <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 2 }}>
                      <span style={{ color: 'var(--color-text-primary)', fontWeight: 600 }}>{e.action.replace('_', ' ')}</span>
                      <span style={{ color: 'var(--color-text-muted)', fontSize: 10 }}>{e.occurred_at ? new Date(e.occurred_at).toLocaleString() : '—'}</span>
                    </div>
                    <div style={{ color: 'var(--color-text-secondary)' }}>{e.actor_display ?? 'System'}</div>
                    {e.detail && <pre style={{ fontSize: 10, color: 'var(--color-text-muted)', marginTop: 4, whiteSpace: 'pre-wrap' }}>{JSON.stringify(e.detail, null, 2)}</pre>}
                  </div>
                ))}
              </div>
            )}

            {/* ── Upload form ── */}
            {activePanel === 'upload' && (
              <div style={{ fontSize: 12 }}>
                <div style={formGroup}>
                  <label style={formLabel}>Vault</label>
                  <select value={uploadVault} onChange={e => setUploadVault(e.target.value)} style={formSelect}>
                    <option value="">— Select vault —</option>
                    {vaults.map(v => <option key={v.vault_id} value={v.vault_id}>{v.display_name}</option>)}
                  </select>
                </div>
                <div style={formGroup}>
                  <label style={formLabel}>Title</label>
                  <input value={uploadTitle} onChange={e => setUploadTitle(e.target.value)} placeholder="Document title" style={formInput} />
                </div>
                <div style={formGroup}>
                  <label style={formLabel}>File</label>
                  <div
                    onClick={() => fileInputRef.current?.click()}
                    style={{ padding: 20, border: '2px dashed var(--color-border-default)', clipPath: "polygon(0 0, calc(100% - 4px) 0, 100% 4px, 100% 100%, 0 100%)", textAlign: 'center', cursor: 'pointer', color: 'var(--color-text-muted)' }}
                  >
                    {uploadFile ? (
                      <span style={{ color: 'var(--color-text-primary)' }}>{uploadFile.name} ({formatBytes(uploadFile.size)})</span>
                    ) : (
                      <span>Click to select file</span>
                    )}
                  </div>
                  <input ref={fileInputRef} type="file" style={{ display: 'none' }} onChange={e => setUploadFile(e.target.files?.[0] ?? null)} />
                </div>
                {error && <div style={{ color: 'var(--color-brand-red)', fontSize: 11, marginBottom: 8 }}>{error}</div>}
                <button
                  onClick={handleUpload}
                  disabled={uploading || !uploadFile || !uploadVault || !uploadTitle}
                  style={{ ...primaryBtn, width: '100%', justifyContent: 'center', opacity: uploading ? 0.6 : 1 }}
                >
                  <Upload size={12} /> {uploading ? 'Uploading…' : 'Upload to Vault'}
                </button>
              </div>
            )}

            {/* ── Lock state form ── */}
            {activePanel === 'lock' && selectedDoc && (
              <div style={{ fontSize: 12 }}>
                <div style={{ marginBottom: 12, padding: 10, background: 'var(--color-bg-input)', clipPath: "polygon(0 0, calc(100% - 4px) 0, 100% 4px, 100% 100%, 0 100%)" }}>
                  <div style={{ color: 'var(--color-text-muted)', marginBottom: 4 }}>Current state</div>
                  <span style={{ padding: '2px 10px', clipPath: "polygon(0 0, calc(100% - 4px) 0, 100% 4px, 100% 100%, 0 100%)", fontSize: 11, fontWeight: 700, background: `${lockBadgeColor(selectedDoc.lock_state)}22`, color: lockBadgeColor(selectedDoc.lock_state) }}>
                    {selectedDoc.lock_state}
                  </span>
                </div>
                <div style={formGroup}>
                  <label style={formLabel}>New State</label>
                  <select value={lockTargetState} onChange={e => setLockTargetState(e.target.value)} style={formSelect}>
                    <option value="">— Select state —</option>
                    {LOCK_STATES.filter(s => s !== selectedDoc.lock_state).map(s => (
                      <option key={s} value={s}>{s.replace(/_/g, ' ')}</option>
                    ))}
                  </select>
                </div>
                <div style={formGroup}>
                  <label style={formLabel}>Reason (required)</label>
                  <textarea value={lockReason} onChange={e => setLockReason(e.target.value)} rows={3} placeholder="Required justification for lock state change" style={{ ...formInput, resize: 'vertical' as const }} />
                </div>
                <button onClick={handleLockChange} disabled={!lockTargetState || !lockReason} style={{ ...primaryBtn, width: '100%', justifyContent: 'center' }}>
                  <Lock size={12} /> Apply Lock Change
                </button>
              </div>
            )}

            {/* ── Addendum form ── */}
            {activePanel === 'addendum' && selectedDoc && (
              <div style={{ fontSize: 12 }}>
                <div style={formGroup}>
                  <label style={formLabel}>Addendum Note</label>
                  <textarea value={addendumNote} onChange={e => setAddendumNote(e.target.value)} rows={4} placeholder="Correction or additional note (append-only)" style={{ ...formInput, resize: 'vertical' as const }} />
                </div>
                <div style={formGroup}>
                  <label style={formLabel}>Reason</label>
                  <input value={addendumReason} onChange={e => setAddendumReason(e.target.value)} placeholder="Why is this addendum being added?" style={formInput} />
                </div>
                <button onClick={handleAddendum} disabled={!addendumNote || !addendumReason} style={{ ...primaryBtn, width: '100%', justifyContent: 'center' }}>
                  <Plus size={12} /> Append Addendum
                </button>
              </div>
            )}

            {/* ── Export package form ── */}
            {activePanel === 'export' && (
              <div style={{ fontSize: 12 }}>
                <div style={formGroup}>
                  <label style={formLabel}>Package Name</label>
                  <input value={exportName} onChange={e => setExportName(e.target.value)} placeholder="e.g. Q1 2025 Legal Records" style={formInput} />
                </div>
                <div style={formGroup}>
                  <label style={formLabel}>Export Reason</label>
                  <textarea value={exportReason} onChange={e => setExportReason(e.target.value)} rows={2} placeholder="Audit, legal request, etc." style={{ ...formInput, resize: 'vertical' as const }} />
                </div>
                <div style={formGroup}>
                  <label style={formLabel}>Documents ({exportDocIds.length} selected)</label>
                  <div style={{ maxHeight: 200, overflowY: 'auto', border: '1px solid var(--color-border-subtle)', clipPath: "polygon(0 0, calc(100% - 4px) 0, 100% 4px, 100% 100%, 0 100%)", padding: 8 }}>
                    {documents.map(d => (
                      <label key={d.id} style={{ display: 'flex', alignItems: 'center', gap: 8, padding: '4px 0', cursor: 'pointer' }}>
                        <input
                          type="checkbox"
                          checked={exportDocIds.includes(d.id)}
                          onChange={e => setExportDocIds(prev => e.target.checked ? [...prev, d.id] : prev.filter(id => id !== d.id))}
                          style={{ accentColor: 'var(--q-orange)' }}
                        />
                        <span style={{ color: 'var(--color-text-primary)', fontSize: 11 }}>{d.title}</span>
                      </label>
                    ))}
                  </div>
                </div>
                <button
                  onClick={handleCreateExportPackage}
                  disabled={!exportName || exportDocIds.length === 0 || !!buildingPkg}
                  style={{ ...primaryBtn, width: '100%', justifyContent: 'center', opacity: buildingPkg ? 0.6 : 1 }}
                >
                  <Package size={12} /> {buildingPkg ? 'Building ZIP…' : 'Build & Download ZIP'}
                </button>
              </div>
            )}
          </div>
        </aside>
      )}
    </div>
  );
}

// ── Style constants ────────────────────────────────────────────────────────────

const iconBtn: React.CSSProperties = {
  background: 'transparent', border: '1px solid var(--color-border-subtle)', clipPath: "polygon(0 0, calc(100% - 4px) 0, 100% 4px, 100% 100%, 0 100%)",
  padding: '3px 5px', color: 'var(--color-text-secondary)', cursor: 'pointer', display: 'inline-flex', alignItems: 'center',
};

const primaryBtn: React.CSSProperties = {
  padding: '7px 12px', background: 'var(--q-orange)', border: 'none', clipPath: "polygon(0 0, calc(100% - 4px) 0, 100% 4px, 100% 100%, 0 100%)",
  color: 'var(--color-bg-base)', fontSize: 11, fontWeight: 700, cursor: 'pointer',
  display: 'inline-flex', alignItems: 'center', gap: 6,
};

const secondaryBtn: React.CSSProperties = {
  padding: '6px 10px', background: 'transparent', border: '1px solid var(--color-border-default)',
  clipPath: "polygon(0 0, calc(100% - 4px) 0, 100% 4px, 100% 100%, 0 100%)", color: 'var(--color-text-secondary)', fontSize: 11, cursor: 'pointer',
  display: 'inline-flex', alignItems: 'center', gap: 5,
};

const section: React.CSSProperties = { marginBottom: 16 };
const sectionLabel: React.CSSProperties = { fontSize: 10, color: 'var(--color-text-muted)', fontWeight: 700, textTransform: 'uppercase', letterSpacing: '0.08em', marginBottom: 6, margin: '0 0 6px' };
const fieldValue: React.CSSProperties = { fontSize: 12, color: 'var(--color-text-primary)', margin: 0 };

const formGroup: React.CSSProperties = { marginBottom: 14 };
const formLabel: React.CSSProperties = { display: 'block', fontSize: 10, color: 'var(--color-text-muted)', fontWeight: 700, textTransform: 'uppercase', letterSpacing: '0.08em', marginBottom: 6 };
const formInput: React.CSSProperties = { width: '100%', padding: '7px 8px', background: 'var(--color-bg-input)', border: '1px solid var(--color-border-subtle)', clipPath: "polygon(0 0, calc(100% - 4px) 0, 100% 4px, 100% 100%, 0 100%)", color: 'var(--color-text-primary)', fontSize: 12, outline: 'none', boxSizing: 'border-box' };
const formSelect: React.CSSProperties = { ...formInput, cursor: 'pointer' };
