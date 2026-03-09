'use client';

import { useEffect, useState } from 'react';
import { getPortalDocuments, uploadPortalDocument } from '@/services/api';

interface PatientDoc {
  id: string;
  data?: {
    type?: string;
    name?: string;
    created_at?: string;
    file_url?: string;
    description?: string;
    size_bytes?: number;
    status?: string;
  };
}

const DOC_TYPES: Record<string, { label: string; icon: string; color: string }> = {
  statement:     { label: 'Statement',        icon: 'file-text', color: '#818CF8' },
  invoice:       { label: 'Invoice',          icon: 'file-text', color: '#FF4D00' },
  receipt:       { label: 'Receipt',          icon: 'receipt',   color: '#10B981' },
  payment_plan:  { label: 'Payment Plan',     icon: 'plan',      color: '#F59E0B' },
  signed_form:   { label: 'Signed Form',      icon: 'pen',       color: '#A78BFA' },
  upload:        { label: 'Your Upload',      icon: 'upload',    color: '#60A5FA' },
  correspondence:{ label: 'Correspondence',   icon: 'mail',      color: '#94A3B8' },
};

const CATEGORIES = ['All', 'Statements', 'Invoices', 'Receipts', 'Payment Plans', 'My Uploads'];

const clip6  = 'polygon(0 0, calc(100% - 6px) 0, 100% 6px, 100% 100%, 0 100%)';
const clip10 = 'polygon(0 0, calc(100% - 10px) 0, 100% 10px, 100% 100%, 0 100%)';

function DocIcon({ type }: { type: string }) {
  const p = { width: 16, height: 16, viewBox: '0 0 24 24', fill: 'none', stroke: 'currentColor', strokeWidth: 1.8, strokeLinecap: 'round' as const, strokeLinejoin: 'round' as const };
  switch (type) {
    case 'receipt':   return <svg {...p}><polyline points="7 8 3 8 3 21 21 21 21 8 17 8"/><rect x="7" y="2" width="10" height="6" rx="1"/></svg>;
    case 'plan':      return <svg {...p}><rect x="3" y="4" width="18" height="18" rx="2"/><line x1="16" y1="2" x2="16" y2="6"/><line x1="8" y1="2" x2="8" y2="6"/><line x1="3" y1="10" x2="21" y2="10"/></svg>;
    case 'upload':    return <svg {...p}><path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/><polyline points="17 8 12 3 7 8"/><line x1="12" y1="3" x2="12" y2="15"/></svg>;
    case 'mail':      return <svg {...p}><path d="M4 4h16c1.1 0 2 .9 2 2v12c0 1.1-.9 2-2 2H4c-1.1 0-2-.9-2-2V6c0-1.1.9-2 2-2z"/><polyline points="22,6 12,13 2,6"/></svg>;
    case 'pen':       return <svg {...p}><path d="M12 20h9"/><path d="M16.5 3.5a2.121 2.121 0 0 1 3 3L7 19l-4 1 1-4L16.5 3.5z"/></svg>;
    default:          return <svg {...p}><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><polyline points="14 2 14 8 20 8"/></svg>;
  }
}

function fmtDate(s?: string): string {
  if (!s) return '—';
  return new Date(s).toLocaleDateString('en-US', { year: 'numeric', month: 'short', day: 'numeric' });
}

function fmtSize(bytes?: number): string {
  if (!bytes) return '';
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(0)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

export default function DocumentsPage() {
  const [docs, setDocs] = useState<PatientDoc[]>([]);
  const [loading, setLoading] = useState(true);
  const [category, setCategory] = useState('All');
  const [uploading, setUploading] = useState(false);
  const [fetchError, setFetchError] = useState<string | null>(null);

  useEffect(() => {
    getPortalDocuments()
      .then(d => setDocs(Array.isArray(d) ? d : d.items ?? []))
      .catch((err: unknown) => setFetchError(err instanceof Error ? err.message : 'Failed to load documents'))
      .finally(() => setLoading(false));
  }, []);

  const filtered = docs.filter(d => {
    if (category === 'All') return true;
    if (category === 'Statements') return d.data?.type === 'statement';
    if (category === 'Invoices')   return d.data?.type === 'invoice';
    if (category === 'Receipts')   return d.data?.type === 'receipt';
    if (category === 'Payment Plans') return d.data?.type === 'payment_plan';
    if (category === 'My Uploads')  return d.data?.type === 'upload';
    return true;
  });

  const handleUpload = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;
    // Validate file type/size at boundary
    const allowed = ['application/pdf', 'image/jpeg', 'image/png', 'image/webp'];
    if (!allowed.includes(file.type)) {
      alert('Only PDF, JPG, PNG files are accepted.');
      return;
    }
    if (file.size > 10 * 1024 * 1024) {
      alert('File must be under 10 MB.');
      return;
    }
    setUploading(true);
    const form = new FormData();
    form.append('file', file);
    form.append('type', 'upload');
    uploadPortalDocument(form)
      .then(d => setDocs(prev => [d, ...prev]))
      .catch(() => {/* silently ignore in portal, show toast in production */})
      .finally(() => setUploading(false));
    e.target.value = '';
  };

  return (
    <div className="max-w-5xl mx-auto px-4 py-8">
      {/* Header */}
      <div className="flex items-start justify-between mb-8">
        <div>
          <div className="flex items-center gap-3 mb-1">
            <div className="w-[3px] h-6 bg-[#FF4D00] shadow-[0_0_8px_rgba(255,77,0,0.6)]" />
            <h1 className="text-xl font-black tracking-[0.12em] text-white uppercase">Document Center</h1>
          </div>
          <p className="text-sm text-zinc-500 ml-5">All statements, invoices, receipts, and your uploaded documents.</p>
        </div>

        {/* Upload trigger */}
        <label
          className={`flex items-center gap-2 h-9 px-4 cursor-pointer text-[10px] font-bold tracking-widest uppercase transition-colors ${
            uploading
              ? 'bg-zinc-800 text-zinc-500 cursor-not-allowed border border-zinc-700'
              : 'bg-[#FF4D00]/10 border border-[#FF4D00]/30 text-[#FF4D00] hover:bg-[#FF4D00]/20'
          }`}
          style={{ clipPath: clip6 }}
        >
          {uploading ? (
            <div className="w-3 h-3 border-2 border-[#FF4D00] border-t-transparent rounded-full animate-spin" />
          ) : (
            <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/><polyline points="17 8 12 3 7 8"/><line x1="12" y1="3" x2="12" y2="15"/>
            </svg>
          )}
          {uploading ? 'Uploading...' : 'Upload Document'}
          <input type="file" className="hidden" accept=".pdf,.jpg,.jpeg,.png" onChange={handleUpload} disabled={uploading} />
        </label>
      </div>

      {fetchError && (
        <div className="mb-4 px-4 py-3 bg-red-500/8 border border-red-500/20 text-sm text-red-400" style={{ clipPath: clip6 }}>
          Unable to load documents. Please refresh the page or contact billing support.
        </div>
      )}

      {/* Category tabs */}
      <div className="flex items-center gap-2 mb-6 overflow-x-auto pb-2">
        {CATEGORIES.map(cat => (
          <button
            key={cat}
            onClick={() => setCategory(cat)}
            className={`flex-shrink-0 px-3 py-1.5 text-[10px] font-bold tracking-widest uppercase border transition-colors ${
              category === cat
                ? 'bg-[#FF4D00]/10 border-[#FF4D00]/40 text-[#FF4D00]'
                : 'border-zinc-800 text-zinc-500 hover:border-zinc-600 hover:text-zinc-300'
            }`}
            style={{ clipPath: clip6 }}
          >
            {cat}
          </button>
        ))}
      </div>

      {/* Document grid */}
      {loading ? (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {Array.from({ length: 6 }).map((_, i) => (
            <div key={i} className="bg-[#0A0A0B] border border-zinc-900 h-24 animate-pulse" style={{ clipPath: clip10 }} />
          ))}
        </div>
      ) : filtered.length === 0 ? (
        <div className="bg-[#0A0A0B] border border-zinc-800 py-16 text-center" style={{ clipPath: clip10 }}>
          <div className="text-2xl mb-3 opacity-20">📂</div>
          <p className="text-sm text-zinc-500 mb-3">No documents found in this category.</p>
          <label className="inline-block text-[10px] font-bold tracking-widest uppercase text-[#FF4D00] hover:underline cursor-pointer">
            Upload a Document
            <input type="file" className="hidden" accept=".pdf,.jpg,.jpeg,.png" onChange={handleUpload} />
          </label>
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {filtered.map(doc => {
            const fd = doc.data ?? {};
            const typeInfo = DOC_TYPES[fd.type ?? ''] ?? { label: 'Document', icon: 'file-text', color: '#A1A1AA' };
            return (
              <div
                key={doc.id}
                className="bg-[#0A0A0B] border border-zinc-800 p-4 flex items-start gap-4 hover:border-zinc-700 transition-colors group"
                style={{ clipPath: clip10 }}
              >
                {/* Icon */}
                <div
                  className="w-10 h-10 flex-shrink-0 flex items-center justify-center border"
                  style={{ background: typeInfo.color + '15', borderColor: typeInfo.color + '30', color: typeInfo.color, clipPath: clip6 }}
                >
                  <DocIcon type={typeInfo.icon} />
                </div>

                {/* Content */}
                <div className="flex-1 min-w-0">
                  <div className="flex items-start justify-between gap-2">
                    <div className="min-w-0">
                      <div className="text-sm font-semibold text-zinc-200 truncate">{fd.name ?? `${typeInfo.label} ${doc.id.slice(-6).toUpperCase()}`}</div>
                      <div className="text-[10px] text-zinc-600 mt-0.5">
                        {fmtDate(fd.created_at)}
                        {fd.size_bytes ? ` · ${fmtSize(fd.size_bytes)}` : ''}
                      </div>
                    </div>
                    <span
                      className="flex-shrink-0 text-[9px] font-bold tracking-widest uppercase px-2 py-1 border"
                      style={{ background: typeInfo.color + '10', borderColor: typeInfo.color + '25', color: typeInfo.color, clipPath: clip6 }}
                    >
                      {typeInfo.label}
                    </span>
                  </div>
                  {fd.description && (
                    <p className="text-xs text-zinc-500 mt-1.5 line-clamp-1">{fd.description}</p>
                  )}
                </div>

                {/* Download */}
                <a
                  href={fd.file_url ?? '#'}
                  download
                  className="flex-shrink-0 w-8 h-8 flex items-center justify-center border border-zinc-800 text-zinc-600 group-hover:border-zinc-600 group-hover:text-zinc-300 transition-colors"
                  style={{ clipPath: clip6 }}
                  title="Download"
                >
                  <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                    <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/><polyline points="7 10 12 15 17 10"/><line x1="12" y1="15" x2="12" y2="3"/>
                  </svg>
                </a>
              </div>
            );
          })}
        </div>
      )}

      {/* Upload instructions */}
      <div className="mt-8 bg-zinc-900/30 border border-zinc-800 p-4" style={{ clipPath: clip10 }}>
        <div className="text-[10px] font-bold tracking-widest text-zinc-500 uppercase mb-2">Need to upload insurance information?</div>
        <p className="text-xs text-zinc-600 mb-3">
          You can upload insurance cards, EOBs, or supporting documentation here. Your billing team will be notified upon upload.
        </p>
        <label className="inline-flex items-center gap-2 text-[10px] font-bold tracking-widest uppercase text-[#FF4D00] hover:underline cursor-pointer">
          <svg width="11" height="11" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
            <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/><polyline points="17 8 12 3 7 8"/><line x1="12" y1="3" x2="12" y2="15"/>
          </svg>
          Upload Insurance Card / EOB
          <input type="file" className="hidden" accept=".pdf,.jpg,.jpeg,.png" onChange={handleUpload} />
        </label>
      </div>
    </div>
  );
}


