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
      const res = await getDocument('list');
      const docs = Array.isArray(res?.documents) ? res.documents : Array.isArray(res) ? res : [];
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
    if (s === 'processed' || s === 'complete') return 'text-emerald-400';
    if (s === 'processing' || s === 'pending') return 'text-amber-400';
    return 'text-red-400';
  };

  if (loading) {
    return (
      <div className="min-h-screen bg-gray-950 text-white flex items-center justify-center">
        <RefreshCw className="w-8 h-8 animate-spin text-emerald-400" />
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gray-950 text-white p-6">
      <div className="max-w-7xl mx-auto space-y-8">
        <div className="flex items-center justify-between">
          <div>
            <Link href="/billing" className="text-gray-400 hover:text-white flex items-center gap-1 text-sm mb-2">
              <ArrowLeft className="w-4 h-4" /> Billing Hub
            </Link>
            <h1 className="text-3xl font-bold flex items-center gap-3">
              <FileText className="w-8 h-8 text-blue-400" />
              Billing Document Management
            </h1>
            <p className="text-gray-400 mt-1">Upload, process, and manage billing documents with OCR verification</p>
          </div>
          <button onClick={loadDocuments} className="px-4 py-2 bg-gray-800 hover:bg-gray-700 rounded-lg flex items-center gap-2 text-sm">
            <RefreshCw className="w-4 h-4" /> Refresh
          </button>
        </div>

        {error && (
          <div className="bg-red-900/30 border border-red-700 rounded-lg p-4 flex items-center gap-3">
            <AlertTriangle className="w-5 h-5 text-red-400" />
            <span className="text-red-300">{error}</span>
          </div>
        )}

        {/* Upload & Search */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <label className="bg-gray-900 border border-dashed border-gray-600 hover:border-blue-500 rounded-lg p-8 text-center cursor-pointer transition-colors">
            <Upload className="w-8 h-8 text-gray-400 mx-auto mb-2" />
            <span className="text-gray-400">{uploading ? 'Uploading...' : 'Drop or click to upload document'}</span>
            <input
              type="file"
              className="hidden"
              accept=".pdf,.png,.jpg,.jpeg,.tiff"
              disabled={uploading}
              onChange={(e) => { if (e.target.files?.[0]) handleUpload(e.target.files[0]); }}
            />
          </label>
          <div className="bg-gray-900 border border-gray-800 rounded-lg p-5">
            <div className="flex items-center gap-2 mb-3">
              <Search className="w-4 h-4 text-gray-400" />
              <span className="text-sm text-gray-400">Search Documents</span>
            </div>
            <input
              type="text"
              placeholder="Search by filename..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="w-full bg-gray-800 border border-gray-700 rounded px-3 py-2 text-sm text-white placeholder-gray-500"
            />
            <div className="mt-2 text-xs text-gray-500">{filteredDocs.length} document{filteredDocs.length !== 1 ? 's' : ''} found</div>
          </div>
        </div>

        {/* KPI Cards */}
        <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
          <div className="bg-gray-900 border border-gray-800 rounded-lg p-5">
            <div className="text-gray-400 text-sm mb-1">Total Documents</div>
            <div className="text-2xl font-bold text-blue-400">{documents.length}</div>
          </div>
          <div className="bg-gray-900 border border-gray-800 rounded-lg p-5">
            <div className="text-gray-400 text-sm mb-1">Processed</div>
            <div className="text-2xl font-bold text-emerald-400">{documents.filter(d => d.status === 'processed' || d.status === 'complete').length}</div>
          </div>
          <div className="bg-gray-900 border border-gray-800 rounded-lg p-5">
            <div className="text-gray-400 text-sm mb-1">Pending OCR</div>
            <div className="text-2xl font-bold text-amber-400">{documents.filter(d => d.ocr_status === 'pending' || d.ocr_status === 'processing').length}</div>
          </div>
          <div className="bg-gray-900 border border-gray-800 rounded-lg p-5">
            <div className="text-gray-400 text-sm mb-1">Failed</div>
            <div className="text-2xl font-bold text-red-400">{documents.filter(d => d.status === 'error' || d.status === 'failed').length}</div>
          </div>
        </div>

        {/* Documents Table */}
        <div className="bg-gray-900 border border-gray-800 rounded-lg overflow-hidden">
          <div className="px-6 py-4 border-b border-gray-800">
            <h2 className="text-lg font-semibold flex items-center gap-2">
              <FileText className="w-5 h-5 text-blue-400" /> Document Registry
            </h2>
          </div>
          {filteredDocs.length === 0 ? (
            <div className="p-12 text-center text-gray-500">
              <FileText className="w-12 h-12 mx-auto mb-3 opacity-30" />
              <p>No documents found. Upload a billing document to get started.</p>
            </div>
          ) : (
            <table className="w-full text-sm">
              <thead className="bg-gray-800/50">
                <tr>
                  <th className="text-left px-6 py-3 text-gray-400 font-medium">Filename</th>
                  <th className="text-left px-6 py-3 text-gray-400 font-medium">Type</th>
                  <th className="text-left px-6 py-3 text-gray-400 font-medium">Status</th>
                  <th className="text-left px-6 py-3 text-gray-400 font-medium">OCR</th>
                  <th className="text-left px-6 py-3 text-gray-400 font-medium">Created</th>
                  <th className="text-left px-6 py-3 text-gray-400 font-medium">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-800">
                {filteredDocs.map((doc) => (
                  <tr key={doc.id} className="hover:bg-gray-800/30">
                    <td className="px-6 py-3 text-white font-medium">{doc.filename}</td>
                    <td className="px-6 py-3 text-gray-400">{doc.content_type}</td>
                    <td className={`px-6 py-3 font-medium ${statusColor(doc.status)}`}>{doc.status}</td>
                    <td className={`px-6 py-3 font-medium ${statusColor(doc.ocr_status ?? 'unknown')}`}>{doc.ocr_status ?? '—'}</td>
                    <td className="px-6 py-3 text-gray-400">{doc.created_at ? new Date(doc.created_at).toLocaleDateString() : '—'}</td>
                    <td className="px-6 py-3">
                      <button className="text-blue-400 hover:text-blue-300 text-xs flex items-center gap-1">
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
