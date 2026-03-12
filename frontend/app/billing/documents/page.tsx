'use client';

import { useEffect, useState } from 'react';
import Link from 'next/link';
import { ArrowLeft, FileText, RefreshCw, Upload, AlertTriangle, Search, Eye } from 'lucide-react';
import { getDocumentUploadUrl, getDocument, processDocument } from '@/services/api';

interface DocRecord {
  id: string;
  filename: string;
  content_type: string;
  status: string;
  created_at: string;
  s3_key?: string;
  ocr_status?: string;
  extracted_text?: string;
}

export default function BillingDocumentsPage() {
  const [documents, setDocuments] = useState<DocRecord[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [uploading, setUploading] = useState(false);
  const [searchQuery, setSearchQuery] = useState('');

  const loadDocuments = async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await getDocument('list') as { documents?: DocRecord[] } | DocRecord[];
      const docs = Array.isArray((res as { documents?: DocRecord[] })?.documents) ? (res as { documents?: DocRecord[] }).documents! : Array.isArray(res) ? (res as DocRecord[]) : [];
      setDocuments(docs);
    } catch {
      setDocuments([]);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { loadDocuments(); }, []);

  const handleUpload = async (file: File) => {
    setUploading(true);
    try {
      const urlRes = await getDocumentUploadUrl({ filename: file.name, content_type: file.type });
      if (urlRes?.upload_url) {
        await fetch(urlRes.upload_url, { method: 'PUT', body: file, headers: { 'Content-Type': file.type } });
        if (urlRes.document_id) {
          await processDocument({ document_id: urlRes.document_id, s3_key: urlRes.s3_key ?? '' });
        }
      }
      await loadDocuments();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Upload failed');
    } finally {
      setUploading(false);
    }
  };

  const filteredDocs = documents.filter(d =>
    d.filename?.toLowerCase().includes(searchQuery.toLowerCase())
  );

  const statusColor = (s: string) => {
    if (s === 'processed' || s === 'complete') return 'text-[var(--color-status-active)]';
    if (s === 'processing' || s === 'pending') return 'text-[var(--q-yellow)]';
    return 'text-[var(--color-brand-red)]';
  };

  if (loading) {
    return (
      <div className="min-h-screen bg-[var(--color-bg-base)] text-white flex items-center justify-center">
        <RefreshCw className="w-8 h-8 animate-spin text-[var(--color-status-active)]" />
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-[var(--color-bg-base)] text-white p-6">
      <div className="max-w-7xl mx-auto space-y-8">
        <div className="flex items-center justify-between">
          <div>
            <Link href="/billing" className="text-[var(--color-text-secondary)] hover:text-[var(--color-text-primary)] flex items-center gap-1 text-sm mb-2">
              <ArrowLeft className="w-4 h-4" /> Billing Hub
            </Link>
            <h1 className="text-3xl font-bold flex items-center gap-3">
              <FileText className="w-8 h-8 text-[var(--color-status-info)]" />
              Billing Document Management
            </h1>
            <p className="text-[var(--color-text-secondary)] mt-1">Upload, process, and manage billing documents with OCR verification</p>
          </div>
          <button onClick={loadDocuments} className="px-4 py-2 bg-[var(--color-bg-raised)] hover:bg-[var(--color-bg-overlay)] chamfer-8 flex items-center gap-2 text-sm">
            <RefreshCw className="w-4 h-4" /> Refresh
          </button>
        </div>

        {error && (
          <div className="bg-red-900/30 border border-[var(--color-brand-red)] chamfer-8 p-4 flex items-center gap-3">
            <AlertTriangle className="w-5 h-5 text-[var(--color-brand-red)]" />
            <span className="text-[var(--color-brand-red)]">{error}</span>
          </div>
        )}

        {/* Upload & Search */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <label className="bg-[var(--color-bg-panel)] border border-dashed border-gray-600 hover:border-[var(--color-status-info)] chamfer-8 p-8 text-center cursor-pointer transition-colors">
            <Upload className="w-8 h-8 text-[var(--color-text-secondary)] mx-auto mb-2" />
            <span className="text-[var(--color-text-secondary)]">{uploading ? 'Uploading...' : 'Drop or click to upload document'}</span>
            <input
              type="file"
              className="hidden"
              accept=".pdf,.png,.jpg,.jpeg,.tiff"
              disabled={uploading}
              onChange={(e) => { if (e.target.files?.[0]) handleUpload(e.target.files[0]); }}
            />
          </label>
          <div className="bg-[var(--color-bg-panel)] border border-[var(--color-border-default)] chamfer-8 p-5">
            <div className="flex items-center gap-2 mb-3">
              <Search className="w-4 h-4 text-[var(--color-text-secondary)]" />
              <span className="text-sm text-[var(--color-text-secondary)]">Search Documents</span>
            </div>
            <input
              type="text"
              placeholder="Search by filename..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="w-full bg-[var(--color-bg-raised)] border border-[var(--color-border-strong)] chamfer-4 px-3 py-2 text-sm text-white placeholder-[var(--color-text-muted)]"
            />
            <div className="mt-2 text-xs text-[var(--color-text-muted)]">{filteredDocs.length} document{filteredDocs.length !== 1 ? 's' : ''} found</div>
          </div>
        </div>

        {/* KPI Cards */}
        <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
          <div className="bg-[var(--color-bg-panel)] border border-[var(--color-border-default)] chamfer-8 p-5">
            <div className="text-[var(--color-text-secondary)] text-sm mb-1">Total Documents</div>
            <div className="text-2xl font-bold text-[var(--color-status-info)]">{documents.length}</div>
          </div>
          <div className="bg-[var(--color-bg-panel)] border border-[var(--color-border-default)] chamfer-8 p-5">
            <div className="text-[var(--color-text-secondary)] text-sm mb-1">Processed</div>
            <div className="text-2xl font-bold text-[var(--color-status-active)]">{documents.filter(d => d.status === 'processed' || d.status === 'complete').length}</div>
          </div>
          <div className="bg-[var(--color-bg-panel)] border border-[var(--color-border-default)] chamfer-8 p-5">
            <div className="text-[var(--color-text-secondary)] text-sm mb-1">Pending OCR</div>
            <div className="text-2xl font-bold text-[var(--q-yellow)]">{documents.filter(d => d.ocr_status === 'pending' || d.ocr_status === 'processing').length}</div>
          </div>
          <div className="bg-[var(--color-bg-panel)] border border-[var(--color-border-default)] chamfer-8 p-5">
            <div className="text-[var(--color-text-secondary)] text-sm mb-1">Failed</div>
            <div className="text-2xl font-bold text-[var(--color-brand-red)]">{documents.filter(d => d.status === 'error' || d.status === 'failed').length}</div>
          </div>
        </div>

        {/* Documents Table */}
        <div className="bg-[var(--color-bg-panel)] border border-[var(--color-border-default)] chamfer-8 overflow-hidden">
          <div className="px-6 py-4 border-b border-[var(--color-border-default)]">
            <h2 className="text-lg font-semibold flex items-center gap-2">
              <FileText className="w-5 h-5 text-[var(--color-status-info)]" /> Document Registry
            </h2>
          </div>
          {filteredDocs.length === 0 ? (
            <div className="p-12 text-center text-[var(--color-text-muted)]">
              <FileText className="w-12 h-12 mx-auto mb-3 opacity-30" />
              <p>No documents found. Upload a billing document to get started.</p>
            </div>
          ) : (
            <table className="w-full text-sm">
              <thead className="bg-[var(--color-bg-raised)]">
                <tr>
                  <th className="text-left px-6 py-3 text-[var(--color-text-secondary)] font-medium">Filename</th>
                  <th className="text-left px-6 py-3 text-[var(--color-text-secondary)] font-medium">Type</th>
                  <th className="text-left px-6 py-3 text-[var(--color-text-secondary)] font-medium">Status</th>
                  <th className="text-left px-6 py-3 text-[var(--color-text-secondary)] font-medium">OCR</th>
                  <th className="text-left px-6 py-3 text-[var(--color-text-secondary)] font-medium">Created</th>
                  <th className="text-left px-6 py-3 text-[var(--color-text-secondary)] font-medium">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-800">
                {filteredDocs.map((doc) => (
                  <tr key={doc.id} className="hover:bg-[var(--color-bg-raised)]/30">
                    <td className="px-6 py-3 text-white font-medium">{doc.filename}</td>
                    <td className="px-6 py-3 text-[var(--color-text-secondary)]">{doc.content_type}</td>
                    <td className={`px-6 py-3 font-medium ${statusColor(doc.status)}`}>{doc.status}</td>
                    <td className={`px-6 py-3 font-medium ${statusColor(doc.ocr_status ?? 'unknown')}`}>{doc.ocr_status ?? '—'}</td>
                    <td className="px-6 py-3 text-[var(--color-text-secondary)]">{doc.created_at ? new Date(doc.created_at).toLocaleDateString() : '—'}</td>
                    <td className="px-6 py-3">
                      <button className="text-[var(--color-status-info)] hover:text-[var(--color-status-info)] text-xs flex items-center gap-1">
                        <Eye className="w-3 h-3" /> View
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </div>
      </div>
    </div>
  );
}
