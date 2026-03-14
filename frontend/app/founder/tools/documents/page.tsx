'use client';

import { useEffect, useState, useMemo } from 'react';
import Link from 'next/link';
import { ArrowLeft, FileText, RefreshCw, AlertTriangle, Upload, Search, Eye, FolderOpen, File, FileLock, FileCheck } from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';
import { QuantumCardSkeleton } from '@/components/ui';
import { ModuleDashboardShell } from '@/components/shells/PageShells';
import { getDocumentUploadUrl, getDocument, processDocument } from '@/services/api';

interface OrgDocument {
  id: string;
  filename: string;
  content_type: string;
  status: string;
  category?: string;
  created_at?: string;
  uploaded_by?: string;
}

const CATEGORY_ICONS: Record<string, typeof File> = { sop: FileLock, policy: FileCheck };

function StatusChip({ status }: { status: string }) {
  const isActive = status === 'active' || status === 'processed';
  return (
    <span
      className="text-micro font-label uppercase tracking-wider px-2 py-0.5 chamfer-4"
      style={{
        color: isActive ? 'var(--color-status-active)' : 'var(--q-yellow)',
        backgroundColor: isActive ? 'color-mix(in srgb, var(--color-status-active) 12%, transparent)' : 'color-mix(in srgb, var(--q-yellow) 12%, transparent)',
      }}
    >
      {status}
    </span>
  );
}

function CategoryChip({ category }: { category: string }) {
  const colorMap: Record<string, string> = { sop: 'var(--color-system-compliance)', policy: 'var(--color-system-fleet)', general: 'var(--color-text-muted)' };
  const c = colorMap[category] ?? colorMap.general;
  return (
    <span className="text-micro font-label uppercase tracking-wider px-2 py-0.5 chamfer-4" style={{ color: c, backgroundColor: `color-mix(in srgb, ${c} 10%, transparent)` }}>
      {category}
    </span>
  );
}

export default function ToolsDocumentsPage() {
  const [documents, setDocuments] = useState<OrgDocument[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [uploading, setUploading] = useState(false);
  const [searchQuery, setSearchQuery] = useState('');
  const [dragOver, setDragOver] = useState(false);

  const loadDocuments = async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await getDocument('list');
      const docs = Array.isArray((res as { documents?: OrgDocument[] })?.documents) ? (res as { documents?: OrgDocument[] }).documents! : Array.isArray(res) ? (res as OrgDocument[]) : [];
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

  const onDrop = (e: React.DragEvent) => {
    e.preventDefault();
    setDragOver(false);
    const file = e.dataTransfer.files[0];
    if (file) handleUpload(file);
  };

  const filtered = useMemo(
    () => documents.filter(d => d.filename?.toLowerCase().includes(searchQuery.toLowerCase())),
    [documents, searchQuery]
  );

  const sopCount = useMemo(() => documents.filter(d => d.category === 'sop').length, [documents]);
  const policyCount = useMemo(() => documents.filter(d => d.category === 'policy').length, [documents]);

  if (loading) {
    return (
      <div className="flex flex-col gap-4 p-6">
        <QuantumCardSkeleton />
        <div className="grid grid-cols-3 gap-3">{Array.from({ length: 3 }).map((_, i) => <QuantumCardSkeleton key={i} />)}</div>
        <QuantumCardSkeleton />
      </div>
    );
  }

  return (
    <ModuleDashboardShell
      title="Document Manager"
      subtitle="SOP library, policy distribution, and organization-wide document management"
      toolbar={
        <Link href="/founder/tools" className="text-[var(--color-text-muted)] hover:text-[var(--color-text-primary)] flex items-center gap-1 text-micro font-label uppercase tracking-wider transition-colors duration-fast">
          <ArrowLeft className="w-3.5 h-3.5" /> Back to Tools
        </Link>
      }
      headerActions={
        <button onClick={loadDocuments} className="quantum-btn flex items-center gap-2">
          <RefreshCw className="w-3.5 h-3.5" /> Refresh
        </button>
      }
      accentColor="var(--color-system-compliance)"
    >
      <div className="space-y-5 px-1 pb-4">
        {/* Error */}
        <AnimatePresence>
          {error && (
            <motion.div initial={{ opacity: 0, y: -8 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0, y: -8 }}
              className="flex items-center gap-3 p-4 bg-[var(--color-brand-red-ghost)] border border-[var(--color-brand-red)] chamfer-8">
              <AlertTriangle className="w-5 h-5 text-[var(--color-brand-red)] flex-shrink-0" />
              <span className="text-body text-[var(--color-text-primary)]">{error}</span>
            </motion.div>
          )}
        </AnimatePresence>

        {/* Upload + Search */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <label
            onDragOver={(e) => { e.preventDefault(); setDragOver(true); }}
            onDragLeave={() => setDragOver(false)}
            onDrop={onDrop}
            className={`bg-[var(--color-bg-panel)] border border-dashed chamfer-12 p-8 text-center cursor-pointer transition-all duration-fast ${dragOver ? 'border-[var(--q-orange)] bg-[var(--color-brand-orange-ghost)]' : 'border-[var(--color-border-default)] hover:border-[var(--color-border-strong)]'
              }`}
          >
            <Upload className={`w-8 h-8 mx-auto mb-2 transition-colors ${dragOver ? 'text-[var(--q-orange)]' : 'text-[var(--color-text-muted)]'}`} />
            <span className="text-body text-[var(--color-text-muted)] block">
              {uploading ? 'Uploading…' : 'Drop file or click to upload SOP, policy, or document'}
            </span>
            <span className="text-micro text-[var(--color-text-disabled)] mt-2 block">PDF, DOCX, TXT, PNG, JPG</span>
            <input type="file" className="hidden" accept=".pdf,.docx,.doc,.txt,.png,.jpg" disabled={uploading}
              onChange={(e) => { if (e.target.files?.[0]) handleUpload(e.target.files[0]); }} />
          </label>

          <div className="bg-[var(--color-bg-panel)] border border-[var(--color-border-default)] chamfer-12 p-5">
            <div className="flex items-center gap-2 mb-3">
              <Search className="w-4 h-4 text-[var(--color-text-muted)]" />
              <span className="label-caps">Search Documents</span>
            </div>
            <input
              type="text" placeholder="Filter by filename…" value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="w-full bg-[var(--color-bg-input)] border border-[var(--color-border-default)] chamfer-4 px-3 py-2 text-body text-[var(--color-text-primary)] placeholder-[var(--color-text-disabled)] focus:outline-none focus:border-[var(--color-border-focus)] transition-colors"
            />
          </div>
        </div>

        {/* KPI Strip */}
        <div className="grid grid-cols-3 gap-3">
          <div className="bg-[var(--color-bg-panel)] border border-[var(--color-border-default)] chamfer-8 p-4 relative overflow-hidden">
            <div className="absolute top-0 left-0 right-0 h-0.5 bg-[var(--color-status-info)]" />
            <div className="text-micro font-label uppercase tracking-wider text-[var(--color-text-muted)] mb-1">Total Documents</div>
            <div className="text-h2 font-bold text-[var(--color-text-primary)]">{documents.length}</div>
          </div>
          <div className="bg-[var(--color-bg-panel)] border border-[var(--color-border-default)] chamfer-8 p-4 relative overflow-hidden">
            <div className="absolute top-0 left-0 right-0 h-0.5 bg-[var(--color-system-compliance)]" />
            <div className="text-micro font-label uppercase tracking-wider text-[var(--color-text-muted)] mb-1">SOPs</div>
            <div className="text-h2 font-bold text-[var(--color-text-primary)]">{sopCount}</div>
          </div>
          <div className="bg-[var(--color-bg-panel)] border border-[var(--color-border-default)] chamfer-8 p-4 relative overflow-hidden">
            <div className="absolute top-0 left-0 right-0 h-0.5 bg-[var(--color-system-fleet)]" />
            <div className="text-micro font-label uppercase tracking-wider text-[var(--color-text-muted)] mb-1">Policies</div>
            <div className="text-h2 font-bold text-[var(--color-text-primary)]">{policyCount}</div>
          </div>
        </div>

        {/* Document Table */}
        <div className="bg-[var(--color-bg-panel)] border border-[var(--color-border-default)] chamfer-12 overflow-hidden">
          <div className="px-5 py-3 border-b border-[var(--color-border-default)] hud-rail flex items-center gap-2">
            <FileText className="w-4 h-4 text-[var(--color-system-compliance)]" />
            <span className="label-caps">Document Library</span>
            <span className="text-micro text-[var(--color-text-muted)] ml-auto">{filtered.length} document{filtered.length !== 1 ? 's' : ''}</span>
          </div>

          {filtered.length === 0 ? (
            <div className="p-12 text-center">
              <FolderOpen className="w-12 h-12 mx-auto mb-3 text-[var(--color-text-disabled)] opacity-40" />
              <p className="text-body text-[var(--color-text-muted)]">No documents found. Upload your first document.</p>
            </div>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full text-body">
                <thead>
                  <tr className="bg-[var(--color-bg-overlay)]">
                    <th className="text-left px-5 py-2.5 label-caps">Filename</th>
                    <th className="text-left px-5 py-2.5 label-caps">Category</th>
                    <th className="text-left px-5 py-2.5 label-caps">Status</th>
                    <th className="text-left px-5 py-2.5 label-caps">Created</th>
                    <th className="text-left px-5 py-2.5 label-caps">Actions</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-[var(--color-border-subtle)]">
                  {filtered.map((doc, idx) => {
                    const Icon = CATEGORY_ICONS[doc.category ?? ''] ?? File;
                    return (
                      <motion.tr
                        key={doc.id}
                        initial={{ opacity: 0 }} animate={{ opacity: 1 }}
                        transition={{ delay: idx * 0.02 }}
                        className="hover:bg-[var(--color-bg-overlay)] transition-colors duration-fast"
                      >
                        <td className="px-5 py-3 text-[var(--color-text-primary)] font-medium flex items-center gap-2">
                          <Icon className="w-4 h-4 text-[var(--color-text-muted)] flex-shrink-0" />
                          {doc.filename}
                        </td>
                        <td className="px-5 py-3"><CategoryChip category={doc.category ?? 'general'} /></td>
                        <td className="px-5 py-3"><StatusChip status={doc.status} /></td>
                        <td className="px-5 py-3 text-[var(--color-text-muted)]">{doc.created_at ? new Date(doc.created_at).toLocaleDateString() : '—'}</td>
                        <td className="px-5 py-3">
                          <button className="text-[var(--q-orange)] hover:text-[var(--color-brand-orange-bright)] text-micro font-label uppercase tracking-wider flex items-center gap-1 transition-colors">
                            <Eye className="w-3 h-3" /> View
                          </button>
                        </td>
                      </motion.tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          )}
        </div>
      </div>
    </ModuleDashboardShell>
  );
}
