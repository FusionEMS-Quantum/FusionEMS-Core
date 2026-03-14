'use client';

import { useEffect, useState } from 'react';
import Link from 'next/link';
import { ArrowLeft, RefreshCw, AlertTriangle, DollarSign, Package, Tag, Plus, Check, Layers } from 'lucide-react';
import {
  listPricebookEntries,
  createPricebookEntry,
  getPricebookCatalog,
  listPricebooks,
  getActivePricebook,
} from '@/services/api';

interface PricebookEntry {
  id: string;
  code: string;
  description: string;
  unit_price_cents: number;
  category?: string;
  is_active?: boolean;
}

interface Pricebook {
  id: string;
  name: string;
  is_active: boolean;
  entry_count?: number;
  created_at?: string;
}

interface CatalogItem {
  code: string;
  name: string;
  base_price_cents: number;
  category?: string;
}

export default function PricingStudioPage() {
  const [entries, setEntries] = useState<PricebookEntry[]>([]);
  const [pricebooks, setPricebooks] = useState<Pricebook[]>([]);
  const [activePB, setActivePB] = useState<Pricebook | null>(null);
  const [catalog, setCatalog] = useState<CatalogItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [showCreate, setShowCreate] = useState(false);
  const [newEntry, setNewEntry] = useState({ code: '', description: '', unit_price_cents: 0, category: '' });

  const loadData = async () => {
    setLoading(true);
    setError(null);
    try {
      const [entryRes, pbRes, activeRes, catRes] = await Promise.allSettled([
        listPricebookEntries(),
        listPricebooks(),
        getActivePricebook(),
        getPricebookCatalog(),
      ]);
      if (entryRes.status === 'fulfilled') {
        const e = entryRes.value;
        setEntries(Array.isArray(e?.entries) ? e.entries : Array.isArray(e) ? e : []);
      }
      if (pbRes.status === 'fulfilled') {
        const p = pbRes.value;
        setPricebooks(Array.isArray(p?.pricebooks) ? p.pricebooks : Array.isArray(p) ? p : []);
      }
      if (activeRes.status === 'fulfilled') setActivePB(activeRes.value);
      if (catRes.status === 'fulfilled') {
        const c = catRes.value;
        setCatalog(Array.isArray(c?.items) ? c.items : Array.isArray(c) ? c : []);
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load pricing data');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { loadData(); }, []);

  const handleCreate = async () => {
    try {
      await createPricebookEntry(newEntry);
      setShowCreate(false);
      setNewEntry({ code: '', description: '', unit_price_cents: 0, category: '' });
      await loadData();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to create entry');
    }
  };

  const formatCents = (cents: number | undefined) =>
    cents != null ? `$${(cents / 100).toLocaleString('en-US', { minimumFractionDigits: 2 })}` : '$0.00';

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
            <Link href="/founder" className="text-[var(--color-text-secondary)] hover:text-[var(--color-text-primary)] flex items-center gap-1 text-sm mb-2">
              <ArrowLeft className="w-4 h-4" /> Founder OS
            </Link>
            <h1 className="text-3xl font-bold flex items-center gap-3">
              <Tag className="w-8 h-8 text-[var(--color-system-compliance)]" />
              Pricing Studio
            </h1>
            <p className="text-[var(--color-text-secondary)] mt-1">Rate modeling, pricebook management, and subscription configuration</p>
          </div>
          <div className="flex gap-2">
            <button onClick={() => setShowCreate(true)} className="px-4 py-2 bg-violet-600 hover:bg-violet-500 chamfer-8 flex items-center gap-2 text-sm">
              <Plus className="w-4 h-4" /> New Entry
            </button>
            <button onClick={loadData} className="px-4 py-2 bg-[var(--color-bg-raised)] hover:bg-[var(--color-bg-overlay)] chamfer-8 flex items-center gap-2 text-sm">
              <RefreshCw className="w-4 h-4" /> Refresh
            </button>
          </div>
        </div>

        {error && (
          <div className="bg-red-900/30 border border-[var(--color-brand-red)] chamfer-8 p-4 flex items-center gap-3">
            <AlertTriangle className="w-5 h-5 text-[var(--color-brand-red)]" />
            <span className="text-[var(--color-brand-red)]">{error}</span>
          </div>
        )}

        {/* KPIs */}
        <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
          <div className="bg-[var(--color-bg-panel)] border border-[var(--color-border-default)] chamfer-8 p-5">
            <div className="flex items-center gap-2 text-[var(--color-text-secondary)] text-sm mb-1"><Package className="w-4 h-4" /> Pricebooks</div>
            <div className="text-2xl font-bold text-[var(--color-system-compliance)]">{pricebooks.length}</div>
          </div>
          <div className="bg-[var(--color-bg-panel)] border border-[var(--color-border-default)] chamfer-8 p-5">
            <div className="flex items-center gap-2 text-[var(--color-text-secondary)] text-sm mb-1"><Layers className="w-4 h-4" /> Entries</div>
            <div className="text-2xl font-bold text-[var(--color-status-info)]">{entries.length}</div>
          </div>
          <div className="bg-[var(--color-bg-panel)] border border-[var(--color-border-default)] chamfer-8 p-5">
            <div className="flex items-center gap-2 text-[var(--color-text-secondary)] text-sm mb-1"><Check className="w-4 h-4" /> Active Pricebook</div>
            <div className="text-lg font-bold text-[var(--color-status-active)]">{activePB?.name ?? 'None'}</div>
          </div>
          <div className="bg-[var(--color-bg-panel)] border border-[var(--color-border-default)] chamfer-8 p-5">
            <div className="flex items-center gap-2 text-[var(--color-text-secondary)] text-sm mb-1"><DollarSign className="w-4 h-4" /> Catalog Items</div>
            <div className="text-2xl font-bold text-[var(--color-status-info)]">{catalog.length}</div>
          </div>
        </div>

        {/* Create Entry Modal */}
        {showCreate && (
          <div className="bg-[var(--color-bg-panel)] border border-violet-700 chamfer-8 p-6">
            <h3 className="text-lg font-semibold mb-4">Create Pricebook Entry</h3>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <input placeholder="Service code (e.g., A0427)" value={newEntry.code}
                onChange={(e) => setNewEntry({ ...newEntry, code: e.target.value })}
                className="bg-[var(--color-bg-raised)] border border-[var(--color-border-strong)] chamfer-4 px-3 py-2 text-sm text-white" />
              <input placeholder="Description" value={newEntry.description}
                onChange={(e) => setNewEntry({ ...newEntry, description: e.target.value })}
                className="bg-[var(--color-bg-raised)] border border-[var(--color-border-strong)] chamfer-4 px-3 py-2 text-sm text-white" />
              <input placeholder="Unit price (cents)" type="number" value={newEntry.unit_price_cents}
                onChange={(e) => setNewEntry({ ...newEntry, unit_price_cents: parseInt(e.target.value) || 0 })}
                className="bg-[var(--color-bg-raised)] border border-[var(--color-border-strong)] chamfer-4 px-3 py-2 text-sm text-white" />
              <input placeholder="Category" value={newEntry.category}
                onChange={(e) => setNewEntry({ ...newEntry, category: e.target.value })}
                className="bg-[var(--color-bg-raised)] border border-[var(--color-border-strong)] chamfer-4 px-3 py-2 text-sm text-white" />
            </div>
            <div className="mt-4 flex gap-2">
              <button onClick={handleCreate} className="px-4 py-2 bg-violet-600 hover:bg-violet-500 chamfer-4 text-sm">Create</button>
              <button onClick={() => setShowCreate(false)} className="px-4 py-2 bg-[var(--color-bg-overlay)] hover:bg-[var(--color-bg-overlay)] chamfer-4 text-sm">Cancel</button>
            </div>
          </div>
        )}

        {/* Pricebook Entries */}
        <div className="bg-[var(--color-bg-panel)] border border-[var(--color-border-default)] chamfer-8 overflow-hidden">
          <div className="px-6 py-4 border-b border-[var(--color-border-default)]">
            <h2 className="text-lg font-semibold flex items-center gap-2">
              <Tag className="w-5 h-5 text-[var(--color-system-compliance)]" /> Pricebook Entries
            </h2>
          </div>
          {entries.length === 0 ? (
            <div className="p-12 text-center text-[var(--color-text-muted)]">No pricebook entries. Click &quot;New Entry&quot; to add one.</div>
          ) : (
            <table className="w-full text-sm">
              <thead className="bg-[var(--color-bg-raised)]">
                <tr>
                  <th className="text-left px-6 py-3 text-[var(--color-text-secondary)] font-medium">Code</th>
                  <th className="text-left px-6 py-3 text-[var(--color-text-secondary)] font-medium">Description</th>
                  <th className="text-left px-6 py-3 text-[var(--color-text-secondary)] font-medium">Unit Price</th>
                  <th className="text-left px-6 py-3 text-[var(--color-text-secondary)] font-medium">Category</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-800">
                {entries.map((e) => (
                  <tr key={e.id} className="hover:bg-[var(--color-bg-raised)]/30">
                    <td className="px-6 py-3 text-[var(--color-status-info)] font-mono font-medium">{e.code}</td>
                    <td className="px-6 py-3 text-white">{e.description}</td>
                    <td className="px-6 py-3 text-[var(--color-status-active)] font-bold">{formatCents(e.unit_price_cents)}</td>
                    <td className="px-6 py-3 text-[var(--color-text-secondary)]">{e.category ?? '—'}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </div>

        {/* Pricing Catalog */}
        {catalog.length > 0 && (
          <div className="bg-[var(--color-bg-panel)] border border-[var(--color-border-default)] chamfer-8 overflow-hidden">
            <div className="px-6 py-4 border-b border-[var(--color-border-default)]">
              <h2 className="text-lg font-semibold flex items-center gap-2">
                <DollarSign className="w-5 h-5 text-[var(--color-status-info)]" /> Pricing Catalog
              </h2>
            </div>
            <table className="w-full text-sm">
              <thead className="bg-[var(--color-bg-raised)]">
                <tr>
                  <th className="text-left px-6 py-3 text-[var(--color-text-secondary)] font-medium">Code</th>
                  <th className="text-left px-6 py-3 text-[var(--color-text-secondary)] font-medium">Name</th>
                  <th className="text-left px-6 py-3 text-[var(--color-text-secondary)] font-medium">Base Price</th>
                  <th className="text-left px-6 py-3 text-[var(--color-text-secondary)] font-medium">Category</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-800">
                {catalog.map((c) => (
                  <tr key={c.code} className="hover:bg-[var(--color-bg-raised)]/30">
                    <td className="px-6 py-3 text-[var(--color-status-info)] font-mono">{c.code}</td>
                    <td className="px-6 py-3 text-white">{c.name}</td>
                    <td className="px-6 py-3 text-[var(--color-status-active)] font-bold">{formatCents(c.base_price_cents)}</td>
                    <td className="px-6 py-3 text-[var(--color-text-secondary)]">{c.category ?? '—'}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
}
