'use client';

import React, { useState } from 'react';
import { MetricCard } from '@/components/ui/MetricCard';
import { TabBar, TabPanel } from '@/components/ui/InteractionPatterns';
import { ModuleDashboardShell } from '@/components/shells/PageShells';

const TABS = [
  { id: 'calendar', label: 'Shift Calendar' },
  { id: 'requests', label: 'Requests' },
  { id: 'coverage', label: 'Coverage' },
  { id: 'ai_drafts', label: 'AI Drafts' },
] as const;

const DAYS = ['Sun', 'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat'];
const HOURS = Array.from({ length: 16 }, (_, i) => `${String(i + 6).padStart(2, '0')}:00`);

type ViewMode = 'day' | 'week' | 'month';

function WeekView({ weekOffset }: { weekOffset: number }) {
  const today = new Date();
  const startOfWeek = new Date(today);
  startOfWeek.setDate(today.getDate() - today.getDay() + weekOffset * 7);

  return (
    <div className="bg-bg-panel border border-[var(--color-border-default)] chamfer-8 overflow-hidden">
      <div className="grid grid-cols-8 border-b border-border-subtle">
        <div className="px-3 py-2 text-micro text-text-muted">Time</div>
        {DAYS.map((day, i) => {
          const d = new Date(startOfWeek);
          d.setDate(startOfWeek.getDate() + i);
          const isToday = d.toDateString() === today.toDateString();
          return (
            <div key={day} className={`px-3 py-2 text-center border-l border-[var(--color-border-default)] ${isToday ? 'bg-brand-orange/5' : ''}`}>
              <div className={`text-micro uppercase tracking-wider ${isToday ? 'text-brand-orange' : 'text-text-muted'}`}>{day}</div>
              <div className={`text-sm font-bold mt-0.5 ${isToday ? 'text-brand-orange' : 'text-text-secondary'}`}>{d.getDate()}</div>
            </div>
          );
        })}
      </div>
      <div className="overflow-y-auto" style={{ maxHeight: 420 }}>
        {HOURS.map((hour) => (
          <div key={hour} className="grid grid-cols-8 border-b border-[var(--color-border-default)] min-h-[40px]">
            <div className="px-3 py-1 text-micro text-text-muted">{hour}</div>
            {DAYS.map((day) => (
              <div
                key={day}
                className="border-l border-[var(--color-border-default)] hover:bg-white/[0.02] transition-colors cursor-pointer"
              />
            ))}
          </div>
        ))}
      </div>
    </div>
  );
}

function CalendarTab() {
  const [view, setView] = useState<ViewMode>('week');
  const [weekOffset, setWeekOffset] = useState(0);

  const today = new Date();
  const startOfWeek = new Date(today);
  startOfWeek.setDate(today.getDate() - today.getDay() + weekOffset * 7);
  const endOfWeek = new Date(startOfWeek);
  endOfWeek.setDate(startOfWeek.getDate() + 6);

  const fmt = (d: Date) => d.toLocaleDateString('en-US', { month: 'short', day: 'numeric' });

  return (
    <div>
      <div className="grid grid-cols-4 gap-3 mb-5">
        <MetricCard label="Shifts This Week" value="0" domain="scheduling" compact />
        <MetricCard label="Crew Scheduled" value="0" domain="scheduling" compact />
        <MetricCard label="Open Slots" value="0" domain="scheduling" compact />
        <MetricCard label="Overtime Risk" value="0" domain="scheduling" compact />
      </div>

      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center gap-2">
          <button
            onClick={() => setWeekOffset((w) => w - 1)}
            className="h-7 w-7 flex items-center justify-center bg-white/[0.04] border border-[var(--color-border-default)] text-text-muted hover:text-text-primary chamfer-4 transition-colors"
          >
            ‹
          </button>
          <span className="text-body font-label text-text-primary min-w-[140px] text-center">
            {fmt(startOfWeek)} — {fmt(endOfWeek)}
          </span>
          <button
            onClick={() => setWeekOffset((w) => w + 1)}
            className="h-7 w-7 flex items-center justify-center bg-white/[0.04] border border-[var(--color-border-default)] text-text-muted hover:text-text-primary chamfer-4 transition-colors"
          >
            ›
          </button>
          <button
            onClick={() => setWeekOffset(0)}
            className="h-7 px-3 bg-white/[0.04] border border-[var(--color-border-default)] text-micro text-text-muted hover:text-text-primary chamfer-4 transition-colors"
          >
            Today
          </button>
        </div>
        <div className="flex items-center gap-2">
          {(['day', 'week', 'month'] as ViewMode[]).map((v) => (
            <button
              key={v}
              onClick={() => setView(v)}
              className={`h-7 px-3 text-micro font-label uppercase tracking-wider chamfer-4 border transition-colors ${
                view === v
                  ? 'bg-brand-orange/15 border-brand-orange/35 text-brand-orange'
                  : 'bg-white/[0.03] border-[var(--color-border-default)] text-text-muted hover:text-text-primary'
              }`}
            >
              {v}
            </button>
          ))}
          <button className="h-7 px-3 bg-brand-orange/10 border border-brand-orange/25 text-micro font-label uppercase tracking-wider text-brand-orange hover:bg-brand-orange/18 transition-colors chamfer-4">
            + Add Shift
          </button>
        </div>
      </div>

      {view === 'week' && <WeekView weekOffset={weekOffset} />}
      {view !== 'week' && (
        <div className="flex items-center justify-center h-64 bg-bg-panel border border-[var(--color-border-default)] chamfer-8 text-body text-text-muted">
          {view.charAt(0).toUpperCase() + view.slice(1)} view
        </div>
      )}
    </div>
  );
}

function RequestsTab() {
  const [filter, setFilter] = useState<'all' | 'swap' | 'timeoff' | 'trade'>('all');

  return (
    <div>
      <div className="grid grid-cols-4 gap-3 mb-5">
        <MetricCard label="Pending Requests" value="0" domain="scheduling" compact />
        <MetricCard label="Swap Requests" value="0" domain="scheduling" compact />
        <MetricCard label="Time Off" value="0" domain="scheduling" compact />
        <MetricCard label="Trade Requests" value="0" domain="scheduling" compact />
      </div>

      <div className="flex gap-1 mb-4">
        {(['all', 'swap', 'timeoff', 'trade'] as const).map((f) => (
          <button
            key={f}
            onClick={() => setFilter(f)}
            className={`h-7 px-3 text-micro font-label uppercase tracking-wider chamfer-4 border transition-colors ${
              filter === f
                ? 'bg-brand-orange/15 border-brand-orange/35 text-brand-orange'
                : 'bg-white/[0.03] border-[var(--color-border-default)] text-text-muted hover:text-text-primary'
            }`}
          >
            {f === 'all' ? 'All' : f === 'timeoff' ? 'Time Off' : f.charAt(0).toUpperCase() + f.slice(1)}
          </button>
        ))}
      </div>

      <div className="bg-bg-panel border border-[var(--color-border-default)] chamfer-8 overflow-hidden">
        <div className="grid grid-cols-6 px-4 py-2 border-b border-border-subtle text-micro uppercase tracking-widest text-text-muted">
          <span>Crew Member</span><span>Type</span><span>Date / Shift</span><span>Reason</span><span>Submitted</span><span>Action</span>
        </div>
        <div className="flex flex-col items-center justify-center py-16">
          <div className="text-body text-text-muted">No pending {filter === 'all' ? '' : filter} requests</div>
        </div>
      </div>
    </div>
  );
}

function CoverageTab() {
  return (
    <div>
      <div className="grid grid-cols-4 gap-3 mb-5">
        <MetricCard label="Coverage %" value="—" domain="scheduling" compact />
        <MetricCard label="Uncovered Shifts" value="0" domain="scheduling" compact />
        <MetricCard label="On-Call Available" value="0" domain="scheduling" compact />
        <MetricCard label="Fatigue Flags" value="0" domain="scheduling" compact />
      </div>

      <div className="grid grid-cols-2 gap-4">
        <div className="bg-bg-panel border border-[var(--color-border-default)] chamfer-8 p-4">
          <div className="text-micro uppercase tracking-widest text-text-muted mb-3">Coverage by Day</div>
          <div className="space-y-2">
            {DAYS.map((day) => (
              <div key={day} className="flex items-center gap-3">
                <span className="text-micro text-text-muted w-8">{day}</span>
                <div className="flex-1 h-5 bg-white/[0.04] chamfer-4 overflow-hidden">
                  <div className="h-full bg-green-500/30 chamfer-4" style={{ width: '0%' }} />
                </div>
                <span className="text-micro text-text-muted w-8 text-right">0%</span>
              </div>
            ))}
          </div>
        </div>

        <div className="bg-bg-panel border border-[var(--color-border-default)] chamfer-8 p-4">
          <div className="text-micro uppercase tracking-widest text-text-muted mb-3">Overtime &amp; Fatigue Risk</div>
          <div className="flex flex-col items-center justify-center h-40 text-body text-text-muted">
            No fatigue flags this week
          </div>
        </div>
      </div>
    </div>
  );
}

function AiDraftsTab() {
  return (
    <div>
      <div className="flex items-center justify-between mb-4">
        <div>
          <div className="text-body text-text-secondary mb-0.5">AI-generated schedule drafts — review and approve before publishing</div>
          <div className="text-micro text-text-muted">Drafts generated by GPT-4o-mini require human approval. What-if simulation is CPU-only.</div>
        </div>
        <button className="h-7 px-3 bg-brand-orange/10 border border-brand-orange/25 text-micro font-label uppercase tracking-wider text-brand-orange hover:bg-brand-orange/18 transition-colors chamfer-4">
          Generate Draft
        </button>
      </div>

      <div className="grid grid-cols-3 gap-3 mb-5">
        <MetricCard label="Pending Review" value="0" domain="scheduling" compact />
        <MetricCard label="Approved This Week" value="0" domain="scheduling" compact />
        <MetricCard label="AI Draft Accuracy" value="—" domain="scheduling" compact />
      </div>

      <div className="bg-bg-panel border border-[var(--color-border-default)] chamfer-8 overflow-hidden mb-4">
        <div className="grid grid-cols-6 px-4 py-2 border-b border-border-subtle text-micro uppercase tracking-widest text-text-muted">
          <span>Draft ID</span><span>Horizon</span><span>Generated</span><span>Shifts</span><span>Status</span><span>Action</span>
        </div>
        <div className="flex flex-col items-center justify-center py-14">
          <div className="text-body text-text-muted">No AI drafts — generate one to get started</div>
        </div>
      </div>

      <div className="bg-bg-panel border border-[var(--color-border-default)] chamfer-8 p-4">
        <div className="text-micro uppercase tracking-widest text-text-muted mb-2">What-If Simulation</div>
        <div className="text-body text-text-muted mb-3">CPU-only scenario simulation — predict coverage impact before committing changes.</div>
        <div className="grid grid-cols-3 gap-3">
          {[
            { label: 'Remove 1 crew member', desc: 'See coverage drop' },
            { label: 'Add weekend shift', desc: 'See overtime impact' },
            { label: 'Shift start +2h', desc: 'See fatigue change' },
          ].map((scenario) => (
            <button
              key={scenario.label}
              className="text-left px-3 py-2.5 bg-white/[0.03] border border-[var(--color-border-default)] chamfer-4 hover:border-brand-orange/30 transition-colors"
            >
              <div className="text-body font-label text-text-primary mb-0.5">{scenario.label}</div>
              <div className="text-micro text-text-muted">{scenario.desc}</div>
            </button>
          ))}
        </div>
      </div>
    </div>
  );
}

export default function SchedulingPage() {
  const [activeTab, setActiveTab] = useState('calendar');

  return (
    <ModuleDashboardShell
      title="Scheduling"
      subtitle="Shift calendar, swap/trade/time-off requests, coverage monitoring, and AI-assisted drafts"
      accentColor="var(--color-system-scheduling)"
      toolbar={
        <TabBar
          tabs={TABS}
          activeTab={activeTab}
          onTabChange={setActiveTab}
        />
      }
    >
      <TabPanel tabId="calendar" activeTab={activeTab}><CalendarTab /></TabPanel>
      <TabPanel tabId="requests" activeTab={activeTab}><RequestsTab /></TabPanel>
      <TabPanel tabId="coverage" activeTab={activeTab}><CoverageTab /></TabPanel>
      <TabPanel tabId="ai_drafts" activeTab={activeTab}><AiDraftsTab /></TabPanel>
    </ModuleDashboardShell>
  );
}
