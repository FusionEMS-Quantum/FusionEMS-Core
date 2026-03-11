'use client';

import React, { useState, useEffect } from 'react';
import { Lock, FileText, Search, DownloadCloud, Activity, Bookmark } from 'lucide-react';
import { API, aiHeaders } from '@/services/api';
import { QuantumCardSkeleton } from '@/components/ui';

type VaultMode = 
  | 'wisconsin_local_government'
  | 'wisconsin_private_ems'
  | 'wisconsin_medicaid_billing'
  | 'founder_business_document'
  | 'founder_tax_document'
  | 'founder_personal_tax_document';

interface PolicyClass {
  years?: number;
  days?: number;
  description: string;
}

interface VaultPolicy {
  mode: VaultMode;
  classes: Record<string, PolicyClass>;
  updated_at?: string;
  configured_by?: string;
}

const SAVED_VIEWS = [
  "2025 Business Tax Records",
  "Founder Personal Tax Docs",
  "ePCR Records on Legal Hold",
  "Vendor W-9s",
  "Contracts expiring in 90 days",
  "Wisconsin Medicaid-supporting Billing",
  "Founder-private Legal Filings"
];

export default function DocumentVaultPage() {
  const [activeTab, setActiveTab] = useState<'policy' | 'search' | 'packages'>('policy');
  const [policies, setPolicies] = useState<VaultPolicy | null>(null);
  const [loading, setLoading] = useState(true);

  const fetchPolicies = async () => {
    try {
      const res = await API.get('/api/v1/founder/vault/policies', { headers: aiHeaders() });
      setPolicies(res.data);
    } catch (err) {
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchPolicies();
  }, []);

  const formatMode = (mode: string) => {
    return mode.split('_').map((w) => w.charAt(0).toUpperCase() + w.slice(1)).join(' ');
  };

  const navClasses = (tab: string) =>
    `px-4 py-3 text-micro font-label font-bold tracking-wider uppercase transition-colors border-b-2 ${
      activeTab === tab
        ? 'border-[var(--q-orange)] text-[var(--q-orange)]'
        : 'border-transparent text-[var(--color-text-muted)] hover:text-[var(--color-text-primary)] hover:border-[var(--color-border-strong)]'
    }`;

  return (
    <div className="min-h-[calc(100vh-60px)] p-6 bg-[var(--color-bg-base)]">
      <header className="mb-6 border-b border-[var(--color-border-default)] pb-4">
        <div className="flex items-center justify-between">
          <div>
            <div className="flex items-center gap-3">
              <div className="w-1 h-6 chamfer-4 flex-shrink-0 bg-[var(--q-orange)]" />
              <h1 className="text-h2 font-black text-[var(--color-text-primary)] tracking-wider uppercase">
                Executive Document Vault
              </h1>
            </div>
            <p className="text-micro text-[var(--color-text-muted)] mt-2 uppercase tracking-wider ml-4">
              Wisconsin-Oriented Retention, Governance, and Control Center
            </p>
          </div>
          <div className="flex items-center gap-4">
            {policies?.mode && (
              <div className="px-3 py-1 bg-[var(--color-bg-raised)] border border-[var(--color-border-default)] chamfer-4 text-micro font-mono text-[var(--color-text-secondary)]">
                ACTIVE MODE: <span className="text-[var(--q-orange)]">{formatMode(policies.mode)}</span>
              </div>
            )}
          </div>
        </div>

        <nav className="flex items-center gap-2 mt-8">
          <button className={navClasses('policy')} onClick={() => setActiveTab('policy')}>
            <Lock className="w-3.5 h-3.5 inline-block mr-2" />
            Policy Engine
          </button>
          <button className={navClasses('search')} onClick={() => setActiveTab('search')}>
            <Search className="w-3.5 h-3.5 inline-block mr-2" />
            Vault Search
          </button>
          <button className={navClasses('packages')} onClick={() => setActiveTab('packages')}>
            <DownloadCloud className="w-3.5 h-3.5 inline-block mr-2" />
            Handoff Packages
          </button>
        </nav>
      </header>

      {activeTab === 'policy' && (
        <div className="grid grid-cols-12 gap-8">
          <div className="col-span-8 space-y-6">
            <div className="bg-[var(--color-bg-panel)] border border-[var(--color-border-default)] chamfer-12 p-6">
              <div className="flex items-center justify-between mb-6">
                  <h2 className="text-micro font-label font-bold tracking-wider text-[var(--color-text-primary)] uppercase flex items-center gap-2">
                    <Activity className="w-4 h-4 text-[var(--color-status-active)]" />
                    Retention Classes (Wisconsin Default)
                  </h2>
                  <button className="quantum-btn text-micro font-mono text-[var(--q-orange)] border border-[color-mix(in_srgb,var(--q-orange)_30%,transparent)] px-2 py-1 hover:bg-[var(--color-brand-orange-ghost)] transition-colors chamfer-4">EDIT POLICY</button>
              </div>
              
              {loading ? (
                <div className="space-y-3">
                  {Array.from({ length: 4 }).map((_, i) => <QuantumCardSkeleton key={i} />)}
                </div>
              ) : (
                <div className="grid grid-cols-2 gap-4">
                  {policies?.classes && Object.entries(policies.classes).map(([k, v]) => (
                    <div key={k} className="flex flex-col gap-2 p-4 bg-[var(--color-bg-base)] border border-[var(--color-border-subtle)] chamfer-8">
                      <div className="flex items-center justify-between">
                        <span className="text-micro font-mono text-[var(--color-text-secondary)] uppercase">{k.replace('_', ' ')}</span>
                        <span className="text-micro font-bold text-[var(--q-orange)] bg-[var(--color-brand-orange-ghost)] chamfer-4 px-1.5 py-0.5">
                          {v.years ? `${v.years} YEARS` : `${v.days} DAYS`}
                        </span>
                      </div>
                      <div className="text-micro text-[var(--color-text-muted)] leading-tight">{v.description}</div>
                    </div>
                  ))}
                </div>
              )}
            </div>
            
            <div className="bg-[var(--color-bg-panel)] border border-[color-mix(in_srgb,var(--q-orange)_20%,transparent)] chamfer-12 p-6">
                <h2 className="text-micro font-label font-bold tracking-wider uppercase mb-3 text-[var(--q-orange)]">
                    Legal Disclaimer
                </h2>
                <p className="text-micro text-[var(--color-text-muted)] leading-relaxed max-w-4xl">
                    These rules represent an operational assumption for system configuration, not legal advice. The Wisconsin defaults apply common guidelines (e.g., medical records 5–7 years, pediatric exceptions, Medicaid 5 years from payment, etc.) with a margin of operational safety. You must consult your organizational counsel to confirm these retention periods meet your exact regulatory requirements. Any adjustments made here overwrite the platform defaults permanently across the selected Vault domain.
                </p>
            </div>
          </div>

          <div className="col-span-4 space-y-6">
            <div className="bg-[var(--color-bg-panel)] border border-[var(--color-border-default)] chamfer-12 p-6">
              <h2 className="text-micro font-label font-bold tracking-wider text-[var(--color-text-primary)] uppercase mb-5">
                Global Lock States
              </h2>
              <div className="flex flex-wrap gap-2">
                {['active', 'archived', 'legal hold', 'tax hold', 'compliance hold', 'pending disposition', 'destroyed', 'destroy-blocked'].map(state => {
                  const isHold = state.includes('hold');
                  return (
                    <span 
                        key={state} 
                        className={`px-2.5 py-1 text-micro font-mono tracking-wider uppercase border chamfer-4 ${
                          isHold 
                            ? 'border-[color-mix(in_srgb,var(--color-brand-red)_50%,transparent)] text-[var(--color-brand-red)] bg-[var(--color-brand-red-ghost)]' 
                            : 'border-[var(--color-border-default)] text-[var(--color-text-secondary)] bg-[var(--color-bg-raised)]'
                        }`}
                    >
                        {state}
                    </span>
                  );
                })}
              </div>
              <p className="text-micro text-[var(--color-text-muted)] mt-5 leading-relaxed border-t border-[var(--color-border-subtle)] pt-4">
                Records under <strong>legal hold</strong>, <strong>tax hold</strong>, or <strong>compliance hold</strong> cannot be deleted, purged, or overwritten. For final signed ePCR records, you must use append-safe corrections and addenda instead of silent overwrite to meet audit standards.
              </p>
            </div>
          </div>
        </div>
      )}

      {activeTab === 'search' && (
        <div className="grid grid-cols-12 gap-8">
            <div className="col-span-3">
                <div className="bg-[var(--color-bg-panel)] border border-[var(--color-border-default)] chamfer-12 p-4 sticky top-6">
                    <h3 className="text-micro font-mono uppercase text-[var(--color-text-muted)] mb-4 tracking-wider flex items-center gap-2">
                        <Bookmark className="w-3 h-3" />
                        Saved Views
                    </h3>
                    <div className="space-y-1">
                        {SAVED_VIEWS.map((view, i) => (
                            <button key={i} className="block w-full text-left px-3 py-2 text-micro text-[var(--color-text-secondary)] hover:bg-[var(--color-bg-raised)] hover:text-[var(--color-text-primary)] transition-colors truncate chamfer-4">
                                {view}
                            </button>
                        ))}
                    </div>
                </div>
            </div>
            
            <div className="col-span-9 space-y-6">
                <div className="bg-[var(--color-bg-panel)] border border-[var(--color-border-default)] chamfer-12 p-6">
                    <div className="flex gap-4">
                        <input 
                            type="text" 
                            placeholder="Full-text OCR search, metadata filters..."
                            className="flex-1 bg-[var(--color-bg-input)] border border-[var(--color-border-default)] text-[var(--color-text-primary)] text-body px-4 py-2.5 focus:border-[var(--q-orange)] outline-none font-mono placeholder:font-sans chamfer-4"
                        />
                        <button className="quantum-btn-primary text-micro font-label font-bold tracking-wider px-6 py-2.5 uppercase">
                            Refine Search
                        </button>
                    </div>

                    <div className="flex flex-wrap gap-3 mt-4">
                        {['Tax Year', 'Vendor', 'Legal Entity', 'Incident Number', 'Billing Case', 'Patient Record Class', 'Retention Class', 'Hold State', 'Vault'].map((filter) => (
                            <div key={filter} className="text-micro uppercase font-mono px-2 py-1 text-[var(--color-text-muted)] border border-[var(--color-border-default)] chamfer-4 flex items-center gap-2 hover:bg-[var(--color-bg-raised)] cursor-pointer transition-colors">
                                {filter} <span className="text-[var(--color-text-disabled)]">+</span>
                            </div>
                        ))}
                    </div>
                </div>
                
                <div className="text-center py-24 border border-[var(--color-border-subtle)] bg-[var(--color-bg-panel)] chamfer-12 border-dashed">
                    <Search className="w-8 h-8 text-[var(--color-text-disabled)] mx-auto mb-4" />
                    <p className="text-body text-[var(--color-text-muted)]">Enter a query to search the vaulted document repository.</p>
                </div>
            </div>
        </div>
      )}

      {activeTab === 'packages' && (
        <div className="bg-[var(--color-bg-panel)] border border-[var(--color-border-default)] chamfer-12 p-6">
            <div className="flex justify-between items-center mb-6 border-b border-[var(--color-border-subtle)] pb-4">
                <h2 className="text-micro font-label font-bold tracking-wider text-[var(--q-orange)] uppercase pt-1">Export & Handoff</h2>
                <button className="quantum-btn border border-[var(--color-border-strong)] text-[var(--color-text-primary)] font-label font-bold text-micro tracking-wider px-4 py-2 uppercase hover:bg-[var(--color-bg-raised)] transition-colors chamfer-4">
                    Build New Package
                </button>
            </div>
            
            <div className="grid grid-cols-3 gap-6 mb-8">
                {['2026 Business Taxes', 'Audit Evidence Bundle', 'Insurance Renewal Packet'].map((pkg) => (
                    <div key={pkg} className="p-4 border border-[var(--color-border-subtle)] bg-[var(--color-bg-base)] chamfer-8 hover:border-[var(--color-border-strong)] cursor-pointer transition-colors group">
                        <div className="flex items-start justify-between mb-3">
                            <FileText className="w-5 h-5 text-[var(--color-text-disabled)] group-hover:text-[var(--q-orange)] transition-colors" />
                            <span className="text-micro uppercase font-mono text-[var(--color-text-muted)] border border-[var(--color-border-default)] chamfer-4 px-1">ZIP</span>
                        </div>
                        <h4 className="text-micro font-bold text-[var(--color-text-secondary)] mb-1">{pkg}</h4>
                        <p className="text-micro text-[var(--color-text-muted)]">Includes manifest & audit references</p>
                    </div>
                ))}
            </div>

            <div className="text-center py-16 border-t border-[var(--color-border-subtle)]">
                <DownloadCloud className="w-8 h-8 text-[var(--color-text-disabled)] mx-auto mb-4" />
                <p className="text-micro text-[var(--color-text-muted)] max-w-md mx-auto leading-relaxed">
                    Select documents from Vault Search to assemble a new structured ZIP bundle. Handoff packages include a cryptographically signed manifest and complete provenance history for the requested records.
                </p>
            </div>
        </div>
      )}
    </div>
  );
}
