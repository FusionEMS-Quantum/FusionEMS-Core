'use client';

import React, { useState } from 'react';
import { MetricCard } from '@/components/ui/MetricCard';
import { TabBar, TabPanel } from '@/components/ui/InteractionPatterns';
import { ModuleDashboardShell } from '@/components/shells/PageShells';

const TABS = [
  { id: 'overview', label: 'Overview' },
  { id: 'exports', label: 'DOR Exports' },
  { id: 'rejects', label: 'Rejects' },
  { id: 'postings', label: 'Postings' },
] as const;

type TripTab = (typeof TABS)[number]['id'];

function EmptyState({ label }: { label: string }) {
  return (
    <div className="flex flex-col items-center justify-center py-16">
      <div className="text-body text-text-muted">No {label}</div>
    </div>
  );
}

function OverviewTab() {
  return (
    <div className="space-y-6">
      <div className="px-4 py-3 bg-cyan-500/5 border border-cyan-500/20 chamfer-4 flex items-start gap-3">
        <span className="mt-1 w-1.5 h-1.5 rounded-full bg-system-billing flex-shrink-0" />
        <div>
          <div className="text-body font-label text-system-billing mb-0.5">Wisconsin Tax Refund Intercept Program (TRIP)</div>
          <div className="text-body text-text-muted">
            Eligible government agencies may submit qualifying delinquent debts to the Wisconsin DOR for interception of state tax refunds. Minimum debt age: 90 days. Required fields: Debtor name, SSN/DL/FEIN, balance, Agency Debt ID.
          </div>
        </div>
      </div>

      <div className="grid grid-cols-4 gap-3">
        <MetricCard label="Total Enrolled Debts" value="0" domain="billing" compact />
        <MetricCard label="Total Balance" value="$0.00" domain="billing" compact />
        <MetricCard label="Collected via TRIP" value="$0.00" domain="billing" compact />
        <MetricCard label="Open Rejects" value="0" domain="billing" compact />
      </div>

      <div className="grid grid-cols-2 gap-4">
        <div className="bg-bg-panel border border-[var(--color-border-default)] chamfer-8 p-4">
          <div className="text-micro uppercase tracking-widest text-text-muted mb-3">Workflow Steps</div>
          {[
            { step: '1', label: 'Build Candidate Queue', desc: 'Identify debts >= 90 days, not disputed, not previously submitted', color: 'var(--color-system-billing)' },
            { step: '2', label: 'Generate DOR XML Export', desc: 'Produces TRIPSubmission XML per DOR schema v1, zipped for upload', color: 'var(--q-orange)' },
            { step: '3', label: 'Handle Rejects', desc: 'Import DOR reject file, flag accounts, queue fix tasks', color: 'var(--q-yellow)' },
            { step: '4', label: 'Import Posting Notifications', desc: 'Reconcile DOR posting file, auto-post payments to AR ledger', color: 'var(--q-green)' },
          ].map((item) => (
            <div key={item.step} className="flex items-start gap-3 py-3 border-b border-[var(--color-border-default)] last:border-0">
              <div
                className="w-5 h-5 chamfer-4 flex items-center justify-center text-micro font-bold flex-shrink-0"
                style={{ backgroundColor: `${item.color}18`, color: item.color }}
              >
                {item.step}
              </div>
              <div>
                <div className="text-body font-medium text-text-primary mb-0.5">{item.label}</div>
                <div className="text-body text-text-muted">{item.desc}</div>
              </div>
            </div>
          ))}
        </div>

        <div className="bg-bg-panel border border-[var(--color-border-default)] chamfer-8 p-4">
          <div className="text-micro uppercase tracking-widest text-text-muted mb-3">Recent Activity</div>
          <EmptyState label="recent TRIP activity" />
        </div>
      </div>
    </div>
  );
}

function ExportsTab() {
  return (
    <div>
      <div className="flex items-center justify-between mb-4">
        <div className="text-body text-text-muted">DOR XML export history</div>
        <div className="flex gap-2">
          <button className="h-7 px-3 bg-brand-orange/10 border border-brand-orange/25 text-micro font-label uppercase tracking-wider text-brand-orange hover:bg-brand-orange/[0.18] transition-colors chamfer-4">
            Build Candidates
          </button>
          <button className="h-7 px-3 bg-cyan-500/10 border border-cyan-500/25 text-micro font-label uppercase tracking-wider text-system-billing hover:bg-cyan-500/[0.18] transition-colors chamfer-4">
            Generate XML Export
          </button>
        </div>
      </div>
      <div className="bg-bg-panel border border-[var(--color-border-default)] chamfer-8 overflow-hidden">
        <div className="grid grid-cols-6 px-4 py-2 border-b border-border-subtle text-micro uppercase tracking-widest text-text-muted">
          <span>Export ID</span><span>Debt Count</span><span>Total Balance</span><span>Generated</span><span>Status</span><span>Download</span>
        </div>
        <EmptyState label="DOR exports" />
      </div>
    </div>
  );
}

function RejectsTab() {
  return (
    <div>
      <div className="flex items-center justify-between mb-4">
        <div className="text-body text-text-muted">Import and review DOR reject files</div>
        <button className="h-7 px-3 bg-amber-500/10 border border-amber-500/25 text-micro font-label uppercase tracking-wider text-status-warning hover:bg-amber-500/[0.18] transition-colors chamfer-4">
          Import Reject File
        </button>
      </div>
      <div className="px-4 py-3 bg-amber-500/5 border border-amber-500/15 chamfer-4 mb-4 text-body text-amber-400/80">
        Rejected debts are automatically flagged and removed from active TRIP status. Review each reject code and correct the underlying data before re-submitting.
      </div>
      <div className="bg-bg-panel border border-[var(--color-border-default)] chamfer-8 overflow-hidden">
        <div className="grid grid-cols-6 px-4 py-2 border-b border-border-subtle text-micro uppercase tracking-widest text-text-muted">
          <span>Account</span><span>Debtor</span><span>Reject Code</span><span>Reason</span><span>Imported</span><span>Action</span>
        </div>
        <EmptyState label="TRIP rejects" />
      </div>
    </div>
  );
}

function PostingsTab() {
  return (
    <div>
      <div className="flex items-center justify-between mb-4">
        <div className="text-body text-text-muted">DOR Posting Notification reconciliation</div>
        <button className="h-7 px-3 bg-green-500/10 border border-green-500/25 text-micro font-label uppercase tracking-wider text-status-active hover:bg-green-500/[0.18] transition-colors chamfer-4">
          Import Posting File
        </button>
      </div>
      <div className="grid grid-cols-4 gap-3 mb-6">
        <MetricCard label="Reconciled" value="0" domain="billing" compact />
        <MetricCard label="Unmatched" value="0" domain="billing" compact />
        <MetricCard label="Total Amount" value="$0.00" domain="billing" compact />
        <MetricCard label="Last Import" value="—" domain="billing" compact />
      </div>
      <div className="bg-bg-panel border border-[var(--color-border-default)] chamfer-8 overflow-hidden">
        <div className="grid grid-cols-6 px-4 py-2 border-b border-border-subtle text-micro uppercase tracking-widest text-text-muted">
          <span>Account</span><span>Amount</span><span>Tax Year</span><span>Agency Debt ID</span><span>Reconciled</span><span>Status</span>
        </div>
        <EmptyState label="TRIP postings" />
      </div>
    </div>
  );
}

const TAB_ITEMS = TABS.map((t) => ({ id: t.id, label: t.label }));

export default function TripDashboardPage() {
  const [activeTab, setActiveTab] = useState<TripTab>('overview');

  return (
    <ModuleDashboardShell
      title="Wisconsin TRIP"
      subtitle="Tax Refund Intercept Program — DOR XML exports, reject handling, and posting reconciliation"
      accentColor="var(--color-system-billing)"
      toolbar={<TabBar tabs={TAB_ITEMS} activeTab={activeTab} onTabChange={(id) => setActiveTab(id as TripTab)} />}
    >
      <TabPanel tabId="overview" activeTab={activeTab}><OverviewTab /></TabPanel>
      <TabPanel tabId="exports" activeTab={activeTab}><ExportsTab /></TabPanel>
      <TabPanel tabId="rejects" activeTab={activeTab}><RejectsTab /></TabPanel>
      <TabPanel tabId="postings" activeTab={activeTab}><PostingsTab /></TabPanel>
    </ModuleDashboardShell>
  );
}
