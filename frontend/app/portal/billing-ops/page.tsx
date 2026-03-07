'use client';

import React, { useState } from 'react';
import { MetricCard } from '@/components/ui/MetricCard';
import { TabBar, TabPanel } from '@/components/ui/InteractionPatterns';
import { ModuleDashboardShell } from '@/components/shells/PageShells';

type TabId = 'statements' | 'payments' | 'disputes' | 'placement' | 'trip_candidates' | 'trip_rejects' | 'trip_postings';

const TABS: { id: TabId; label: string }[] = [
  { id: 'statements', label: 'Statements Due' },
  { id: 'payments', label: 'Payments Posted' },
  { id: 'disputes', label: 'Disputes' },
  { id: 'placement', label: 'Placement Eligible' },
  { id: 'trip_candidates', label: 'TRIP Candidates' },
  { id: 'trip_rejects', label: 'TRIP Rejects' },
  { id: 'trip_postings', label: 'TRIP Postings' },
];

function EmptyState({ label }: { label: string }) {
  return (
    <div className="flex flex-col items-center justify-center py-16 text-center">
      <p className="text-body text-text-disabled">No {label} found</p>
    </div>
  );
}

function ActionBtn({ label, variant = 'default' }: { label: string; variant?: 'default' | 'danger' | 'success' }) {
  const cls =
    variant === 'danger'
      ? 'bg-red-ghost border-red/30 text-red hover:bg-red/20'
      : variant === 'success'
      ? 'bg-[rgba(76,175,80,0.12)] border-[rgba(76,175,80,0.3)] text-[var(--color-status-active)] hover:bg-[rgba(76,175,80,0.2)]'
      : 'bg-orange-ghost border-orange/25 text-orange hover:bg-orange/18';
  return (
    <button className={`h-7 px-3 border text-micro font-label uppercase tracking-wider chamfer-4 transition-colors duration-fast ${cls}`} type="button">
      {label}
    </button>
  );
}

function TableHeader({ columns }: { columns: string[] }) {
  return (
    <div className={`grid px-4 py-2 border-b border-[var(--color-border-subtle)] text-micro font-label uppercase tracking-wider text-text-disabled`}
      style={{ gridTemplateColumns: `repeat(${columns.length}, 1fr)` }}>
      {columns.map((c) => <span key={c}>{c}</span>)}
    </div>
  );
}

function StatementsTab() {
  return (
    <div>
      <div className="grid grid-cols-2 md:grid-cols-4 gap-3 mb-6">
        <MetricCard label="Due Today" value="0" domain="billing" compact />
        <MetricCard label="Overdue" value="0" domain="billing" compact />
        <MetricCard label="Sent This Month" value="0" domain="billing" compact />
        <MetricCard label="Failed Delivery" value="0" domain="billing" compact />
      </div>
      <div className="bg-bg-panel border border-[var(--color-border-default)] chamfer-8 overflow-hidden">
        <TableHeader columns={['Account', 'Patient', 'Balance', 'Day', 'Channel', 'Action']} />
        <EmptyState label="statements due" />
      </div>
    </div>
  );
}

function PaymentsTab() {
  return (
    <div>
      <div className="grid grid-cols-2 md:grid-cols-4 gap-3 mb-6">
        <MetricCard label="Posted Today" value="$0.00" domain="billing" compact />
        <MetricCard label="Pending Review" value="0" domain="billing" compact />
        <MetricCard label="Failed" value="0" domain="billing" compact />
        <MetricCard label="MTD Collected" value="$0.00" domain="billing" compact />
      </div>
      <div className="bg-bg-panel border border-[var(--color-border-default)] chamfer-8 overflow-hidden">
        <TableHeader columns={['Account', 'Amount', 'Source', 'Ref', 'Posted At', 'Status']} />
        <EmptyState label="payments" />
      </div>
    </div>
  );
}

function DisputesTab() {
  return (
    <div>
      <div className="grid grid-cols-2 md:grid-cols-4 gap-3 mb-6">
        <MetricCard label="Open Disputes" value="0" domain="billing" compact />
        <MetricCard label="Resolved This Month" value="0" domain="billing" compact />
        <MetricCard label="Paused Dunning" value="0" domain="billing" compact />
        <MetricCard label="Avg Resolution" value="—" domain="billing" compact />
      </div>
      <div className="bg-bg-panel border border-[var(--color-border-default)] chamfer-8 overflow-hidden">
        <TableHeader columns={['Account', 'Reason', 'Amount', 'Opened', 'Status', 'Action']} />
        <EmptyState label="disputes" />
      </div>
    </div>
  );
}

function PlacementTab() {
  return (
    <div>
      <div className="grid grid-cols-2 md:grid-cols-4 gap-3 mb-6">
        <MetricCard label="Eligible Accounts" value="0" domain="billing" compact />
        <MetricCard label="Total Balance" value="$0.00" domain="billing" compact />
        <MetricCard label="Active Placements" value="0" domain="billing" compact />
        <MetricCard label="Last Export" value="—" domain="billing" compact />
      </div>
      <div className="flex justify-end mb-3">
        <ActionBtn label="Generate Export ZIP" />
      </div>
      <div className="bg-bg-panel border border-[var(--color-border-default)] chamfer-8 overflow-hidden">
        <TableHeader columns={['Account', 'Patient', 'Balance', 'Days Out', 'Vendor', 'Action']} />
        <EmptyState label="placement-eligible accounts" />
      </div>
    </div>
  );
}

function TripCandidatesTab() {
  return (
    <div>
      <div className="flex items-center gap-3 mb-4 px-4 py-3 bg-[rgba(34,211,238,0.06)] border border-[rgba(34,211,238,0.2)] chamfer-8">
        <span className="w-1.5 h-1.5 rounded-full bg-[var(--color-system-billing)] flex-shrink-0" />
        <span className="text-body text-[rgba(34,211,238,0.9)]">Wisconsin TRIP — available to enrolled government agencies only</span>
      </div>
      <div className="grid grid-cols-2 md:grid-cols-4 gap-3 mb-6">
        <MetricCard label="Eligible Debts" value="0" domain="billing" compact />
        <MetricCard label="Total Balance" value="$0.00" domain="billing" compact />
        <MetricCard label="Last XML Export" value="—" domain="billing" compact />
        <MetricCard label="Accepted by DOR" value="0" domain="billing" compact />
      </div>
      <div className="flex justify-end mb-3">
        <ActionBtn label="Build Candidate Queue" />
      </div>
      <div className="bg-bg-panel border border-[var(--color-border-default)] chamfer-8 overflow-hidden">
        <TableHeader columns={['Account', 'Debtor', 'ID Type', 'Balance', 'Status', 'Action']} />
        <EmptyState label="TRIP candidates" />
      </div>
    </div>
  );
}

function TripRejectsTab() {
  return (
    <div>
      <div className="flex items-center gap-3 mb-4 px-4 py-3 bg-[rgba(245,158,11,0.06)] border border-[rgba(245,158,11,0.2)] chamfer-8">
        <span className="w-1.5 h-1.5 rounded-full bg-[var(--color-status-warning)] flex-shrink-0" />
        <span className="text-body text-[rgba(245,158,11,0.9)]">Rejected debts require correction before re-submission to DOR</span>
      </div>
      <div className="grid grid-cols-2 md:grid-cols-3 gap-3 mb-6">
        <MetricCard label="Open Rejects" value="0" domain="billing" compact />
        <MetricCard label="Fixed This Month" value="0" domain="billing" compact />
        <MetricCard label="Re-submitted" value="0" domain="billing" compact />
      </div>
      <div className="bg-bg-panel border border-[var(--color-border-default)] chamfer-8 overflow-hidden">
        <TableHeader columns={['Account', 'Reject Code', 'Reason', 'Rejected At', 'Action']} />
        <EmptyState label="TRIP rejects" />
      </div>
    </div>
  );
}

function TripPostingsTab() {
  return (
    <div>
      <div className="grid grid-cols-2 md:grid-cols-4 gap-3 mb-6">
        <MetricCard label="Postings Reconciled" value="0" domain="billing" compact />
        <MetricCard label="Unmatched" value="0" domain="billing" compact />
        <MetricCard label="Total Posted" value="$0.00" domain="billing" compact />
        <MetricCard label="Last Import" value="—" domain="billing" compact />
      </div>
      <div className="flex justify-end mb-3">
        <ActionBtn label="Import Posting File" />
      </div>
      <div className="bg-bg-panel border border-[var(--color-border-default)] chamfer-8 overflow-hidden">
        <TableHeader columns={['Account', 'Amount', 'Tax Year', 'Matched', 'Posted At', 'Status']} />
        <EmptyState label="TRIP postings" />
      </div>
    </div>
  );
}

export default function BillingOpsPage() {
  const [activeTab, setActiveTab] = useState<TabId>('statements');

  return (
    <ModuleDashboardShell
      title="Billing Ops Today"
      subtitle="AR queue, dunning schedule, collections placement, and Wisconsin TRIP"
      accentColor="var(--color-system-billing)"
      toolbar={
        <TabBar
          tabs={TABS}
          activeTab={activeTab}
          onTabChange={(id) => setActiveTab(id as TabId)}
          size="sm"
        />
      }
    >
      <TabPanel tabId="statements" activeTab={activeTab}><StatementsTab /></TabPanel>
      <TabPanel tabId="payments" activeTab={activeTab}><PaymentsTab /></TabPanel>
      <TabPanel tabId="disputes" activeTab={activeTab}><DisputesTab /></TabPanel>
      <TabPanel tabId="placement" activeTab={activeTab}><PlacementTab /></TabPanel>
      <TabPanel tabId="trip_candidates" activeTab={activeTab}><TripCandidatesTab /></TabPanel>
      <TabPanel tabId="trip_rejects" activeTab={activeTab}><TripRejectsTab /></TabPanel>
      <TabPanel tabId="trip_postings" activeTab={activeTab}><TripPostingsTab /></TabPanel>
    </ModuleDashboardShell>
  );
}
