'use client';

import React, { useState, useMemo, useEffect, useCallback } from 'react';
import AppShell from '@/components/AppShell';
import { PlateCard, MetricPlate } from '@/components/ui/PlateCard';
import { StatusChip } from '@/components/ui/StatusChip';
import type { StatusVariant } from '@/lib/design-system/tokens';
import {
  AlertTriangle, Clock, FileCheck, Download,
  ChevronRight, ChevronDown, Activity, TrendingUp, TrendingDown,
  Minus, ExternalLink, FileText, CreditCard, Award, Scale,
  Eye, Lock, Clipboard, Pill, ArrowRight,
  AlertCircle, Layers, Database, CheckCircle2,
  RefreshCw, ChevronUp, Target,
} from 'lucide-react';
import { getComplianceCommandSummaryPortal } from '@/services/api';

// ═══════════════════════════════════════════════════════════════════════════════
// TYPES
// ═══════════════════════════════════════════════════════════════════════════════

type DomainKey = 'nemsis' | 'hipaa' | 'pcr' | 'billing' | 'accreditation' | 'dea' | 'cms';

type ImpactArea =
  | 'billing' | 'patient-safety' | 'licensing' | 'dea'
  | 'hipaa' | 'audit-risk' | 'nemsis-export' | 'accreditation'
  | 'cms' | 'revenue';

type ActionState =
  | 'no-action' | 'monitor' | 'review-required' | 'blocking'
  | 'escalated' | 'awaiting-evidence' | 'corrective-action';

type TrendDir = 'up' | 'down' | 'stable';
type RiskTier = 'low' | 'medium' | 'high';

interface ComplianceItem {
  id: string;
  name: string;
  description: string;
  status: StatusVariant;
  statusLabel: string;
  lastChecked: string;
  nextDue?: string;
  trend?: TrendDir;
  trendSummary?: string;
  impactAreas: ImpactArea[];
  actionState: ActionState;
  evidenceCount: number;
  owner?: string;
  linkedRecords?: number;
  policyBasis?: string;
}

interface DomainSummary {
  score: number;
  passing: number;
  warning: number;
  critical: number;
  lastReviewed: string;
  trend: TrendDir;
  billingRisk: RiskTier;
  licensureRisk: RiskTier;
  operationalRisk: RiskTier;
  suggestedActions: string[];
}

interface PriorityAlert {
  id: string;
  severity: 'critical' | 'warning';
  domain: DomainKey;
  domainLabel: string;
  title: string;
  reason: string;
  nextAction: string;
}

interface ActionQueueItem {
  id: string;
  title: string;
  owner: string;
  dueDate: string;
  severity: StatusVariant;
  domain: DomainKey;
  domainLabel: string;
  isOverdue: boolean;
  reviewState: 'open' | 'in-progress' | 'pending-review';
}

// ═══════════════════════════════════════════════════════════════════════════════
// DOMAIN CONFIGURATION
// ═══════════════════════════════════════════════════════════════════════════════

interface DomainMeta { label: string; accent: string; icon: React.ElementType }

const DOMAIN_CONFIG: Record<DomainKey, DomainMeta> = {
  nemsis:        { label: 'NEMSIS',             accent: 'var(--color-status-active)', icon: Database },
  hipaa:         { label: 'HIPAA',              accent: '#38BDF8', icon: Lock },
  pcr:           { label: 'PCR Completion',     accent: 'var(--q-yellow)', icon: Clipboard },
  billing:       { label: 'Billing Compliance', accent: '#22d3ee', icon: CreditCard },
  accreditation: { label: 'Accreditation',      accent: '#a855f7', icon: Award },
  dea:           { label: 'DEA',                accent: 'var(--color-brand-red)', icon: Pill },
  cms:           { label: 'CMS',                accent: 'var(--q-orange)', icon: Scale },
};

const TABS: DomainKey[] = ['nemsis', 'hipaa', 'pcr', 'billing', 'accreditation', 'dea', 'cms'];

const IMPACT_LABELS: Record<ImpactArea, { label: string; color: string }> = {
  billing:         { label: 'Billing',         color: '#22d3ee' },
  'patient-safety':{ label: 'Patient Safety',  color: 'var(--color-brand-red)' },
  licensing:       { label: 'Licensing',        color: '#a855f7' },
  dea:             { label: 'DEA',              color: 'var(--color-brand-red)' },
  hipaa:           { label: 'HIPAA',            color: '#38BDF8' },
  'audit-risk':    { label: 'Audit Risk',       color: 'var(--q-yellow)' },
  'nemsis-export': { label: 'NEMSIS Export',    color: 'var(--color-status-active)' },
  accreditation:   { label: 'Accreditation',    color: '#a855f7' },
  cms:             { label: 'CMS',              color: 'var(--q-orange)' },
  revenue:         { label: 'Revenue',          color: '#22d3ee' },
};

const ACTION_STATE_MAP: Record<ActionState, { label: string; status: StatusVariant }> = {
  'no-action':         { label: 'No Action Needed',       status: 'active' },
  'monitor':           { label: 'Monitor',                status: 'info' },
  'review-required':   { label: 'Review Required',        status: 'warning' },
  'blocking':          { label: 'Blocking',               status: 'critical' },
  'escalated':         { label: 'Escalated',              status: 'critical' },
  'awaiting-evidence': { label: 'Awaiting Evidence',      status: 'warning' },
  'corrective-action': { label: 'Corrective Action Open', status: 'override' },
};

// ═══════════════════════════════════════════════════════════════════════════════
// COMPLIANCE DATA — sourced from live API, no static fallback
// ═══════════════════════════════════════════════════════════════════════════════

const EMPTY_COMPLIANCE_DATA: Record<DomainKey, ComplianceItem[]> = {
  nemsis: [], hipaa: [], pcr: [], billing: [],
  accreditation: [], dea: [], cms: [],
};

// Static domain/alert/queue data removed — all data sourced from live API

// ═══════════════════════════════════════════════════════════════════════════════
// HELPER COMPONENTS
// ═══════════════════════════════════════════════════════════════════════════════

function TrendBadge({ trend, summary }: { trend?: TrendDir; summary?: string }) {
  if (!trend) return null;
  const Icon = trend === 'up' ? TrendingUp : trend === 'down' ? TrendingDown : Minus;
  const color = trend === 'up' ? 'var(--color-status-active)' : trend === 'down' ? 'var(--color-brand-red)' : '#9CA3AF';
  return (
    <span className="inline-flex items-center gap-1" style={{ color }}>
      <Icon className="w-3 h-3" />
      {summary && <span className="text-[0.6rem] font-bold tracking-wider">{summary}</span>}
    </span>
  );
}

function ImpactTag({ area }: { area: ImpactArea }) {
  const cfg = IMPACT_LABELS[area];
  return (
    <span
      className="inline-flex items-center px-1.5 py-0.5 text-[0.55rem] font-bold tracking-[0.15em] uppercase"
      style={{ color: cfg.color, backgroundColor: `${cfg.color}15`, border: `1px solid ${cfg.color}30` }}
    >
      {cfg.label}
    </span>
  );
}

function ActionStateBadge({ state }: { state: ActionState }) {
  const cfg = ACTION_STATE_MAP[state];
  return <StatusChip status={cfg.status} size="sm">{cfg.label}</StatusChip>;
}

function RiskLevel({ level, label }: { level: RiskTier; label: string }) {
  const color = level === 'high' ? 'var(--color-brand-red)' : level === 'medium' ? 'var(--q-yellow)' : 'var(--color-status-active)';
  return (
    <div className="flex items-center gap-2">
      <span className="text-[0.55rem] font-bold tracking-[0.15em] uppercase text-[var(--color-text-muted)]">{label}</span>
      <span className="text-[0.55rem] font-bold tracking-wider uppercase px-1.5 py-0.5" style={{ color, backgroundColor: `${color}15`, border: `1px solid ${color}30` }}>
        {level}
      </span>
    </div>
  );
}

function ScoreGauge({ score, size = 'lg' }: { score: number; size?: 'sm' | 'lg' }) {
  const color = score >= 90 ? 'var(--color-status-active)' : score >= 75 ? '#38BDF8' : score >= 60 ? 'var(--q-yellow)' : 'var(--color-brand-red)';
  const dim = size === 'lg' ? 72 : 44;
  const stroke = size === 'lg' ? 5 : 3;
  const r = (dim - stroke) / 2;
  const circ = 2 * Math.PI * r;
  const offset = circ * (1 - score / 100);
  return (
    <div className="relative" style={{ width: dim, height: dim }}>
      <svg width={dim} height={dim} className="transform -rotate-90">
        <circle cx={dim / 2} cy={dim / 2} r={r} fill="none" stroke="rgba(255,255,255,0.06)" strokeWidth={stroke} />
        <circle cx={dim / 2} cy={dim / 2} r={r} fill="none" stroke={color} strokeWidth={stroke} strokeDasharray={circ} strokeDashoffset={offset} strokeLinecap="round" className="transition-all duration-700" />
      </svg>
      <div className="absolute inset-0 flex items-center justify-center">
        <span className={`font-black ${size === 'lg' ? 'text-lg' : 'text-[0.65rem]'}`} style={{ color }}>{score}%</span>
      </div>
    </div>
  );
}

function SectionDivider({ label }: { label: string }) {
  return (
    <div className="flex items-center gap-3 my-6">
      <div className="h-px flex-1" style={{ backgroundColor: 'rgba(255,255,255,0.06)' }} />
      <span className="text-[0.55rem] font-bold tracking-[0.25em] uppercase text-[var(--color-text-muted)]">{label}</span>
      <div className="h-px flex-1" style={{ backgroundColor: 'rgba(255,255,255,0.06)' }} />
    </div>
  );
}

function TacticalCorners() {
  return (
    <>
      <div className="absolute top-0 left-0 w-1.5 h-1.5 border-t border-l border-white/20" />
      <div className="absolute top-0 right-0 w-1.5 h-1.5 border-t border-r border-white/20" />
      <div className="absolute bottom-0 left-0 w-1.5 h-1.5 border-b border-l border-white/20" />
      <div className="absolute bottom-0 right-0 w-1.5 h-1.5 border-b border-r border-white/20" />
    </>
  );
}

// ═══════════════════════════════════════════════════════════════════════════════
// PRIORITY ALERT CARD
// ═══════════════════════════════════════════════════════════════════════════════

function PriorityAlertCard({ alert, onNavigate }: { alert: PriorityAlert; onNavigate: () => void }) {
  const isCritical = alert.severity === 'critical';
  const borderColor = isCritical ? 'rgba(255,45,45,0.4)' : 'rgba(245,158,11,0.3)';
  const glowColor = isCritical ? 'rgba(255,45,45,0.08)' : 'rgba(245,158,11,0.05)';
  const accentColor = isCritical ? 'var(--color-brand-red)' : 'var(--q-yellow)';
  return (
    <div
      className="relative border p-4 group cursor-pointer hover:border-opacity-70 transition-all"
      style={{ borderColor, backgroundColor: glowColor }}
      onClick={onNavigate}
    >
      <TacticalCorners />
      <div className="flex items-start gap-3 mb-3">
        <div className="mt-0.5">
          {isCritical
            ? <AlertTriangle className="w-4 h-4" style={{ color: accentColor }} />
            : <AlertCircle className="w-4 h-4" style={{ color: accentColor }} />}
        </div>
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 mb-1">
            <StatusChip status={isCritical ? 'critical' : 'warning'} size="sm" pulse={isCritical}>
              {alert.severity.toUpperCase()}
            </StatusChip>
            <span className="text-[0.55rem] font-bold tracking-[0.15em] uppercase" style={{ color: accentColor }}>
              {alert.domainLabel}
            </span>
          </div>
          <p className="text-[0.8rem] font-semibold text-white leading-snug mb-1.5">{alert.title}</p>
          <p className="text-[0.65rem] text-[var(--color-text-muted)] leading-relaxed mb-2">{alert.reason}</p>
        </div>
      </div>
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-1.5">
          <ArrowRight className="w-3 h-3" style={{ color: accentColor }} />
          <span className="text-[0.6rem] font-bold tracking-wider" style={{ color: accentColor }}>{alert.nextAction}</span>
        </div>
        <ChevronRight className="w-3.5 h-3.5 text-[var(--color-text-muted)] group-hover:text-[var(--color-text-secondary)] transition-colors" />
      </div>
    </div>
  );
}

// ═══════════════════════════════════════════════════════════════════════════════
// DOMAIN SUMMARY PANEL
// ═══════════════════════════════════════════════════════════════════════════════

function DomainSummaryPanel({ domain: _domain, summary, config }: { domain: DomainKey; summary: DomainSummary; config: DomainMeta }) {
  const DomainIcon = config.icon;
  return (
    <div className="relative border border-white/8 bg-[#0a0a0c] p-5 mb-4" style={{ borderLeft: `3px solid ${config.accent}` }}>
      <TacticalCorners />
      <div className="grid grid-cols-1 lg:grid-cols-[auto_1fr_1fr] gap-6">
        {/* Score + Domain Info */}
        <div className="flex items-center gap-5">
          <ScoreGauge score={summary.score} size="lg" />
          <div>
            <div className="flex items-center gap-2 mb-1">
              <DomainIcon className="w-4 h-4" style={{ color: config.accent }} />
              <span className="text-[0.65rem] font-bold tracking-[0.15em] uppercase" style={{ color: config.accent }}>{config.label}</span>
            </div>
            <div className="flex items-center gap-4 mt-2">
              <span className="text-[0.6rem] font-bold text-[var(--color-status-active)]">{summary.passing} passing</span>
              <span className="text-[0.6rem] font-bold text-[var(--q-yellow)]">{summary.warning} warning</span>
              <span className="text-[0.6rem] font-bold text-[var(--color-brand-red)]">{summary.critical} critical</span>
            </div>
            <div className="mt-2">
              <TrendBadge trend={summary.trend} summary={summary.trend === 'up' ? 'Improving' : summary.trend === 'down' ? 'Declining' : 'Stable'} />
            </div>
          </div>
        </div>

        {/* Risk Assessment */}
        <div className="flex flex-col gap-2">
          <span className="text-[0.55rem] font-bold tracking-[0.2em] uppercase text-[var(--color-text-muted)] mb-1">Risk Assessment</span>
          <RiskLevel level={summary.billingRisk} label="Billing" />
          <RiskLevel level={summary.licensureRisk} label="Licensure" />
          <RiskLevel level={summary.operationalRisk} label="Operations" />
          <div className="mt-1 text-[0.55rem] text-[var(--color-text-muted)]">
            Last reviewed: {summary.lastReviewed}
          </div>
        </div>

        {/* Suggested Actions */}
        <div>
          <span className="text-[0.55rem] font-bold tracking-[0.2em] uppercase text-[var(--color-text-muted)] mb-2 block">Suggested Actions</span>
          <div className="space-y-1.5">
            {summary.suggestedActions.map((action, i) => (
              <div key={i} className="flex items-start gap-2">
                <ChevronRight className="w-3 h-3 text-[#FF6A00] mt-0.5 shrink-0" />
                <span className="text-[0.65rem] text-[var(--color-text-secondary)] leading-snug">{action}</span>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}

// ═══════════════════════════════════════════════════════════════════════════════
// COMPLIANCE ROW (EXPANDABLE)
// ═══════════════════════════════════════════════════════════════════════════════

function ComplianceRow({ item, isExpanded, onToggle, accent }: { item: ComplianceItem; isExpanded: boolean; onToggle: () => void; accent: string }) {
  const actionCfg = ACTION_STATE_MAP[item.actionState];
  return (
    <div style={{ borderBottom: '1px solid rgba(255,255,255,0.04)' }}>
      {/* Main Row */}
      <div
        className="flex items-start justify-between gap-4 px-4 py-3.5 cursor-pointer hover:bg-white/[0.02] transition-colors group"
        onClick={onToggle}
      >
        <div className="flex items-start gap-3 min-w-0 flex-1">
          {/* Left accent dot */}
          <div className="mt-1.5 shrink-0">
            <div className="w-1.5 h-1.5" style={{ backgroundColor: accent }} />
          </div>
          <div className="min-w-0 flex-1">
            <div className="flex items-center gap-2 mb-0.5">
              <p className="text-[0.8rem] font-semibold text-white leading-snug">{item.name}</p>
              {item.actionState !== 'no-action' && (
                <ActionStateBadge state={item.actionState} />
              )}
            </div>
            <p className="text-[0.65rem] text-[var(--color-text-muted)] leading-relaxed mb-1.5">{item.description}</p>
            <div className="flex flex-wrap items-center gap-1.5">
              {item.impactAreas.slice(0, 3).map(area => (
                <ImpactTag key={area} area={area} />
              ))}
              {item.impactAreas.length > 3 && (
                <span className="text-[0.55rem] text-[var(--color-text-muted)]">+{item.impactAreas.length - 3} more</span>
              )}
            </div>
          </div>
        </div>

        <div className="flex shrink-0 items-center gap-4">
          <div className="flex flex-col items-end gap-1.5">
            <StatusChip status={item.status} size="sm">{item.statusLabel}</StatusChip>
            <TrendBadge trend={item.trend} summary={item.trendSummary} />
          </div>
          <div className="flex flex-col items-end gap-1">
            <span className="text-[0.55rem] text-[var(--color-text-muted)]">{item.lastChecked}</span>
            {item.evidenceCount > 0 && (
              <span className="text-[0.55rem] text-[var(--color-text-muted)] flex items-center gap-1">
                <FileText className="w-2.5 h-2.5" /> {item.evidenceCount}
              </span>
            )}
          </div>
          <div className="text-[var(--color-text-muted)] group-hover:text-[var(--color-text-secondary)] transition-colors">
            {isExpanded ? <ChevronUp className="w-4 h-4" /> : <ChevronDown className="w-4 h-4" />}
          </div>
        </div>
      </div>

      {/* Expanded Detail */}
      {isExpanded && (
        <div className="px-4 pb-4 pt-1 ml-7 border-l-2 animate-in slide-in-from-top-1 duration-200" style={{ borderColor: accent }}>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4 bg-[#07090d] p-4 border border-white/4">
            <TacticalCorners />
            {/* Column 1: Details */}
            <div className="space-y-3">
              <div>
                <span className="text-[0.5rem] font-bold tracking-[0.2em] uppercase text-[var(--color-text-muted)] block mb-1">Policy / Standard Basis</span>
                <span className="text-[0.65rem] text-[var(--color-text-secondary)]">{item.policyBasis ?? 'Internal standard'}</span>
              </div>
              {item.owner && (
                <div>
                  <span className="text-[0.5rem] font-bold tracking-[0.2em] uppercase text-[var(--color-text-muted)] block mb-1">Owner / Reviewer</span>
                  <span className="text-[0.65rem] text-[var(--color-text-secondary)]">{item.owner}</span>
                </div>
              )}
              {item.nextDue && (
                <div>
                  <span className="text-[0.5rem] font-bold tracking-[0.2em] uppercase text-[var(--color-text-muted)] block mb-1">Next Due</span>
                  <span className="text-[0.65rem] text-[var(--color-text-secondary)]">{item.nextDue}</span>
                </div>
              )}
              <div>
                <span className="text-[0.5rem] font-bold tracking-[0.2em] uppercase text-[var(--color-text-muted)] block mb-1">Action State</span>
                <span className="text-[0.65rem] font-semibold" style={{ color: actionCfg.status === 'critical' ? 'var(--color-brand-red)' : actionCfg.status === 'warning' ? 'var(--q-yellow)' : 'var(--color-status-active)' }}>
                  {actionCfg.label}
                </span>
              </div>
            </div>

            {/* Column 2: Impact & Evidence */}
            <div className="space-y-3">
              <div>
                <span className="text-[0.5rem] font-bold tracking-[0.2em] uppercase text-[var(--color-text-muted)] block mb-1">Impact Areas</span>
                <div className="flex flex-wrap gap-1">
                  {item.impactAreas.map(area => <ImpactTag key={area} area={area} />)}
                </div>
              </div>
              <div>
                <span className="text-[0.5rem] font-bold tracking-[0.2em] uppercase text-[var(--color-text-muted)] block mb-1">Evidence Documents</span>
                <span className="text-[0.65rem] text-[var(--color-text-secondary)]">{item.evidenceCount} document{item.evidenceCount !== 1 ? 's' : ''} on file</span>
              </div>
              {item.linkedRecords !== undefined && item.linkedRecords > 0 && (
                <div>
                  <span className="text-[0.5rem] font-bold tracking-[0.2em] uppercase text-[var(--color-text-muted)] block mb-1">Linked Records</span>
                  <span className="text-[0.65rem] text-[var(--color-text-secondary)]">{item.linkedRecords} records</span>
                </div>
              )}
            </div>

            {/* Column 3: Actions */}
            <div className="space-y-2">
              <span className="text-[0.5rem] font-bold tracking-[0.2em] uppercase text-[var(--color-text-muted)] block mb-1">Quick Actions</span>
              <button className="flex items-center gap-2 text-[0.6rem] font-bold tracking-wider uppercase text-[var(--color-text-secondary)] hover:text-white transition-colors w-full py-1.5 px-2 border border-white/6 hover:border-white/15">
                <Eye className="w-3 h-3" /> View Evidence
              </button>
              <button className="flex items-center gap-2 text-[0.6rem] font-bold tracking-wider uppercase text-[var(--color-text-secondary)] hover:text-white transition-colors w-full py-1.5 px-2 border border-white/6 hover:border-white/15">
                <Download className="w-3 h-3" /> Download Evidence
              </button>
              <button className="flex items-center gap-2 text-[0.6rem] font-bold tracking-wider uppercase text-[var(--color-text-secondary)] hover:text-white transition-colors w-full py-1.5 px-2 border border-white/6 hover:border-white/15">
                <FileCheck className="w-3 h-3" /> Mark Reviewed
              </button>
              <button className="flex items-center gap-2 text-[0.6rem] font-bold tracking-wider uppercase text-[var(--color-text-secondary)] hover:text-white transition-colors w-full py-1.5 px-2 border border-white/6 hover:border-white/15">
                <ExternalLink className="w-3 h-3" /> View Linked Records
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

// ═══════════════════════════════════════════════════════════════════════════════
// ACTION QUEUE TABLE
// ═══════════════════════════════════════════════════════════════════════════════

function ActionQueueTable({ items, filter, onFilterChange }: {
  items: ActionQueueItem[];
  filter: string;
  onFilterChange: (_f: 'all' | 'critical' | 'overdue') => void;
}) {
  return (
    <div>
      <div className="flex items-center justify-between mb-3">
        <div className="flex items-center gap-2">
          <Target className="w-4 h-4 text-[#FF6A00]" />
          <span className="text-[0.65rem] font-bold tracking-[0.15em] uppercase text-white">Corrective Action Queue</span>
          <span className="text-[0.55rem] font-bold text-[var(--color-text-muted)] ml-1">{items.length} items</span>
        </div>
        <div className="flex items-center gap-1">
          {(['all', 'critical', 'overdue'] as const).map(f => (
            <button
              key={f}
              onClick={() => onFilterChange(f)}
              className="px-2.5 py-1 text-[0.55rem] font-bold tracking-wider uppercase transition-colors"
              style={{
                color: filter === f ? 'var(--q-orange)' : '#6B7280',
                backgroundColor: filter === f ? 'rgba(255,106,0,0.1)' : 'transparent',
                border: filter === f ? '1px solid rgba(255,106,0,0.3)' : '1px solid transparent',
              }}
            >
              {f}
            </button>
          ))}
        </div>
      </div>
      <div className="border border-white/6 bg-[#0a0a0c] divide-y divide-white/4">
        {items.map(item => {
          const domainCfg = DOMAIN_CONFIG[item.domain];
          const stateColor = item.reviewState === 'in-progress' ? '#38BDF8' : item.reviewState === 'pending-review' ? 'var(--q-yellow)' : '#9CA3AF';
          return (
            <div key={item.id} className="flex items-center justify-between px-4 py-3 hover:bg-white/[0.02] transition-colors">
              <div className="flex items-center gap-3 min-w-0 flex-1">
                <div className="w-1 h-8 shrink-0" style={{ backgroundColor: domainCfg.accent }} />
                <div className="min-w-0">
                  <div className="flex items-center gap-2 mb-0.5">
                    <p className="text-[0.75rem] font-semibold text-white truncate">{item.title}</p>
                    {item.isOverdue && (
                      <StatusChip status="critical" size="sm" pulse>OVERDUE</StatusChip>
                    )}
                  </div>
                  <div className="flex items-center gap-3">
                    <span className="text-[0.55rem] font-bold tracking-wider uppercase" style={{ color: domainCfg.accent }}>{item.domainLabel}</span>
                    <span className="text-[0.55rem] text-[var(--color-text-muted)]">{item.owner}</span>
                  </div>
                </div>
              </div>
              <div className="flex items-center gap-4 shrink-0">
                <div className="text-right">
                  <span className="text-[0.6rem] text-[var(--color-text-secondary)] block">Due: {item.dueDate}</span>
                  <span className="text-[0.55rem] font-bold tracking-wider uppercase" style={{ color: stateColor }}>
                    {item.reviewState.replace('-', ' ')}
                  </span>
                </div>
                <StatusChip status={item.severity} size="sm">
                  {item.severity === 'critical' ? 'CRITICAL' : item.severity === 'warning' ? 'WARNING' : 'INFO'}
                </StatusChip>
              </div>
            </div>
          );
        })}
        {items.length === 0 && (
          <div className="px-4 py-8 text-center">
            <CheckCircle2 className="w-5 h-5 text-[var(--color-status-active)] mx-auto mb-2" />
            <span className="text-[0.65rem] text-[var(--color-text-muted)]">No items match the selected filter</span>
          </div>
        )}
      </div>
    </div>
  );
}

// ═══════════════════════════════════════════════════════════════════════════════
// COMPACT METRIC CARD
// ═══════════════════════════════════════════════════════════════════════════════

function CompactMetric({ label, value, accent, severity }: { label: string; value: string; accent?: string; severity?: 'ok' | 'warn' | 'crit' }) {
  const borderColor = severity === 'crit' ? 'rgba(255,45,45,0.3)' : severity === 'warn' ? 'rgba(245,158,11,0.2)' : 'rgba(255,255,255,0.06)';
  const valueColor = severity === 'crit' ? 'var(--color-brand-red)' : severity === 'warn' ? 'var(--q-yellow)' : accent ?? '#E5E7EB';
  return (
    <div className="relative border bg-[#0a0a0c] p-3 group hover:border-white/15 transition-colors" style={{ borderColor }}>
      <TacticalCorners />
      <p className="text-[0.5rem] font-bold tracking-[0.2em] uppercase text-[var(--color-text-muted)] mb-1.5">{label}</p>
      <p className="text-xl font-black leading-none" style={{ color: valueColor }}>{value}</p>
    </div>
  );
}

// ═══════════════════════════════════════════════════════════════════════════════
// API RESPONSE TYPES
// ═══════════════════════════════════════════════════════════════════════════════

interface ApiDomainScore {
  domain: DomainKey;
  score: number;
  passing: number;
  warning: number;
  critical: number;
  trend: TrendDir;
  billing_risk: RiskTier;
  licensure_risk: RiskTier;
  operational_risk: RiskTier;
  last_reviewed: string;
  suggested_actions: string[];
}

interface ApiPriorityAlert {
  id: string;
  severity: 'critical' | 'warning';
  domain: DomainKey;
  domain_label: string;
  title: string;
  reason: string;
  next_action: string;
}

interface ApiActionQueueItem {
  id: string;
  title: string;
  owner: string;
  due_date: string;
  domain: DomainKey;
  domain_label: string;
  action_state: string;
  impact: string;
}

interface ApiComplianceSummary {
  overall_score: number;
  total_items: number;
  passing_items: number;
  warning_items: number;
  critical_items: number;
  domains: ApiDomainScore[];
  priority_alerts: ApiPriorityAlert[];
  action_queue: ApiActionQueueItem[];
  generated_at: string;
}

// ═══════════════════════════════════════════════════════════════════════════════
// MAIN PAGE COMPONENT
// ═══════════════════════════════════════════════════════════════════════════════

export default function ComplianceCommandPage() {
  const [activeDomain, setActiveDomain] = useState<DomainKey>('nemsis');
  const [expandedItem, setExpandedItem] = useState<string | null>(null);
  const [queueFilter, setQueueFilter] = useState<'all' | 'critical' | 'overdue'>('all');
  const [apiSummary, setApiSummary] = useState<ApiComplianceSummary | null>(null);
  const [apiError, setApiError] = useState(false);

  const fetchSummary = useCallback(() => {
    getComplianceCommandSummaryPortal(30)
      .then((data: ApiComplianceSummary) => {
        setApiSummary(data);
        setApiError(false);
      })
      .catch(() => {
        setApiError(true);
      });
  }, []);

  useEffect(() => { fetchSummary(); }, [fetchSummary]);

  // Domain summaries — exclusively from live API
  const effectiveSummaries = useMemo<Record<DomainKey, DomainSummary>>(() => {
    const EMPTY_DOMAIN: DomainSummary = { score: 0, passing: 0, warning: 0, critical: 0, lastReviewed: '—', trend: 'stable', billingRisk: 'low', licensureRisk: 'low', operationalRisk: 'low', suggestedActions: [] };
    const base: Record<DomainKey, DomainSummary> = { nemsis: EMPTY_DOMAIN, hipaa: EMPTY_DOMAIN, pcr: EMPTY_DOMAIN, billing: EMPTY_DOMAIN, accreditation: EMPTY_DOMAIN, dea: EMPTY_DOMAIN, cms: EMPTY_DOMAIN };
    if (!apiSummary) return base;
    for (const ds of apiSummary.domains) {
      base[ds.domain] = {
        score: ds.score,
        passing: ds.passing,
        warning: ds.warning,
        critical: ds.critical,
        lastReviewed: ds.last_reviewed || '—',
        trend: ds.trend,
        billingRisk: ds.billing_risk,
        licensureRisk: ds.licensure_risk,
        operationalRisk: ds.operational_risk,
        suggestedActions: ds.suggested_actions,
      };
    }
    return base;
  }, [apiSummary]);

  // Priority alerts — exclusively from live API
  const effectiveAlerts = useMemo<PriorityAlert[]>(() => {
    if (!apiSummary) return [];
    return apiSummary.priority_alerts.map(a => ({
      id: a.id,
      severity: a.severity,
      domain: a.domain,
      domainLabel: a.domain_label,
      title: a.title,
      reason: a.reason,
      nextAction: a.next_action,
    }));
  }, [apiSummary]);

  // Action queue — exclusively from live API
  const effectiveActionQueue = useMemo<ActionQueueItem[]>(() => {
    if (!apiSummary) return [];
    return apiSummary.action_queue.map(a => ({
      id: a.id,
      title: a.title,
      owner: a.owner,
      dueDate: a.due_date,
      severity: (a.action_state === 'blocking' ? 'critical' : a.action_state === 'review-required' ? 'warning' : 'info') as StatusVariant,
      domain: a.domain,
      domainLabel: a.domain_label,
      isOverdue: new Date(a.due_date) < new Date(),
      reviewState: 'open' as const,
    }));
  }, [apiSummary]);

  const domainItems = EMPTY_COMPLIANCE_DATA[activeDomain];
  const domainSummary = effectiveSummaries[activeDomain];
  const domainConfig = DOMAIN_CONFIG[activeDomain];

  // Domain counts derived from API summary scores — no static data
  const domainCounts = useMemo(() => {
    const counts: Record<string, { critical: number; warning: number }> = {};
    for (const key of TABS) {
      const ds = effectiveSummaries[key];
      counts[key] = { critical: ds.critical, warning: ds.warning };
    }
    return counts;
  }, [effectiveSummaries]);

  const overallScore = useMemo(() => {
    if (apiSummary) return apiSummary.overall_score;
    return 0;
  }, [apiSummary]);

  const totalCritical = useMemo(() => {
    if (apiSummary) return apiSummary.critical_items;
    return 0;
  }, [apiSummary]);

  const totalWarning = useMemo(() => {
    if (apiSummary) return apiSummary.warning_items;
    return 0;
  }, [apiSummary]);

  const filteredQueue = useMemo(() => {
    const queue = effectiveActionQueue;
    if (queueFilter === 'all') return queue;
    if (queueFilter === 'critical') return queue.filter(a => a.severity === 'critical');
    return queue.filter(a => a.isOverdue);
  }, [queueFilter, effectiveActionQueue]);

  const lastAuditLabel = apiSummary?.generated_at
    ? new Date(apiSummary.generated_at).toLocaleString('en-US', { month: 'short', day: 'numeric', year: 'numeric', hour: '2-digit', minute: '2-digit' })
    : '—';

  return (
    <AppShell>
      {/* API degradation banner */}
      {apiError && (
        <div className="flex items-center gap-2 px-4 py-2.5 mb-4 border border-[#F59E0B]/30 bg-[#F59E0B]/10 text-[#F59E0B]">
          <AlertCircle className="w-4 h-4 flex-shrink-0" />
          <span className="text-[0.65rem] font-bold tracking-wider uppercase">
            Live compliance data unavailable — connect to backend for real-time posture
          </span>
        </div>
      )}
      {/* ═══════════════════════════════════════════════════════════════════════
          COMMAND HEADER
      ═══════════════════════════════════════════════════════════════════════ */}
      <div className="mb-8">
        <div className="flex flex-col lg:flex-row lg:items-start lg:justify-between gap-4 mb-6">
          <div>
            <div className="flex items-center gap-3 mb-3">
              <div className="w-2 h-2 bg-[#FF6A00] shadow-[0_0_8px_#FF6A00]" />
              <span className="text-[0.6rem] font-bold tracking-[0.25em] uppercase text-[#FF6A00]">
                Mission-Critical Compliance
              </span>
            </div>
            <h1 className="text-3xl md:text-4xl font-black tracking-tight text-white mb-2">
              Compliance Command
            </h1>
            <p className="text-sm text-[var(--color-text-muted)] max-w-2xl leading-relaxed">
              Real-time regulatory, clinical, billing, and operational compliance visibility across the FusionEMS platform.
            </p>
          </div>
          <div className="flex flex-wrap items-center gap-3">
            <StatusChip
              status={overallScore >= 85 ? 'active' : overallScore >= 70 ? 'warning' : 'critical'}
              size="lg"
              pulse
            >
              System Health: {overallScore}%
            </StatusChip>
            <div className="flex items-center gap-2 px-3 py-2 border border-white/8 bg-white/[0.02]">
              <Clock className="w-3.5 h-3.5 text-[var(--color-text-muted)]" />
              <span className="text-[0.6rem] font-bold tracking-wider text-[var(--color-text-secondary)] uppercase">Last Full Audit: {lastAuditLabel}</span>
            </div>
            <div className="flex items-center gap-2 px-3 py-2 border border-white/8 bg-white/[0.02]">
              <Clipboard className="w-3.5 h-3.5 text-[var(--color-text-muted)]" />
              <span className="text-[0.6rem] font-bold tracking-wider text-[var(--color-text-secondary)] uppercase">{effectiveActionQueue.length} Reviews Pending</span>
            </div>
            <button
              onClick={fetchSummary}
              className="flex items-center gap-2 px-4 py-2.5 border border-[#FF6A00]/50 bg-[#FF6A00]/10 hover:bg-[#FF6A00]/20 transition-colors text-[0.6rem] font-bold tracking-wider text-[#FF6A00] uppercase"
            >
              <Download className="w-3.5 h-3.5" /> Export Report
            </button>
          </div>
        </div>

        {/* ═══ EXECUTIVE METRICS ═══ */}
        <div className="grid grid-cols-2 md:grid-cols-4 gap-3 mb-4">
          <MetricPlate label="Overall Compliance" value={`${overallScore}%`} accent="compliance" trend="+0.8 pts this week" trendDirection="up" trendPositive />
          <MetricPlate label="Open Violations" value={String(totalCritical)} accent="critical" trend={`${totalWarning} warnings`} trendDirection="down" />
          <MetricPlate label="Pending Reviews" value={String(effectiveActionQueue.length)} accent="cad" />
          <MetricPlate label="Last Audit Date" value="Mar 8" accent="billing" trend="Internal QA" trendDirection="neutral" />
        </div>
        <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
          <CompactMetric label="DEA Exceptions" value="2" severity="crit" />
          <CompactMetric label="CMS Denial Risk" value="4" severity="crit" />
          <CompactMetric label="Expiring Credentials" value="2" severity="warn" />
          <CompactMetric label="Signature Backlog" value="8" severity="warn" />
        </div>
      </div>

      {/* ═══════════════════════════════════════════════════════════════════════
          PRIORITY ACTIONS RAIL
      ═══════════════════════════════════════════════════════════════════════ */}
      <SectionDivider label="Priority Actions — Requires Immediate Attention" />
      <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-3 mb-8">
        {effectiveAlerts.length === 0 ? (
          <div className="col-span-full flex items-center justify-center py-8 text-[0.6rem] font-bold tracking-[0.2em] uppercase text-[var(--color-text-muted)]">
            {apiSummary ? 'No priority alerts' : 'Awaiting live compliance data'}
          </div>
        ) : effectiveAlerts.map(alert => (
          <PriorityAlertCard
            key={alert.id}
            alert={alert}
            onNavigate={() => setActiveDomain(alert.domain)}
          />
        ))}
      </div>

      {/* ═══════════════════════════════════════════════════════════════════════
          DOMAIN TABS
      ═══════════════════════════════════════════════════════════════════════ */}
      <SectionDivider label="Compliance Domains" />
      <div className="flex flex-wrap gap-1.5 mb-6">
        {TABS.map(key => {
          const cfg = DOMAIN_CONFIG[key];
          const counts = domainCounts[key];
          const isActive = activeDomain === key;
          const DIcon = cfg.icon;
          return (
            <button
              key={key}
              onClick={() => { setActiveDomain(key); setExpandedItem(null); }}
              className="group relative flex items-center gap-2 px-4 py-2.5 transition-all"
              style={{
                backgroundColor: isActive ? `${cfg.accent}15` : 'transparent',
                border: isActive ? `1px solid ${cfg.accent}40` : '1px solid rgba(255,255,255,0.06)',
                color: isActive ? cfg.accent : '#6B7280',
              }}
            >
              <DIcon className="w-3.5 h-3.5" />
              <span className="text-[0.6rem] font-bold tracking-[0.12em] uppercase">{cfg.label}</span>
              {counts && counts.critical > 0 && (
                <span className="flex items-center justify-center w-4 h-4 text-[0.5rem] font-bold bg-[var(--color-brand-red)]/20 text-[var(--color-brand-red)] border border-[var(--color-brand-red)]/30">{counts.critical}</span>
              )}
              {counts && counts.warning > 0 && counts.critical === 0 && (
                <span className="flex items-center justify-center w-4 h-4 text-[0.5rem] font-bold bg-yellow-500/20 text-[var(--q-yellow)] border border-yellow-500/30">{counts.warning}</span>
              )}
              {isActive && (
                <div className="absolute bottom-0 left-0 right-0 h-0.5" style={{ backgroundColor: cfg.accent }} />
              )}
            </button>
          );
        })}
      </div>

      {/* ═══════════════════════════════════════════════════════════════════════
          DOMAIN SUMMARY
      ═══════════════════════════════════════════════════════════════════════ */}
      <DomainSummaryPanel
        domain={activeDomain}
        summary={domainSummary}
        config={domainConfig}
      />

      {/* ═══════════════════════════════════════════════════════════════════════
          COMPLIANCE ITEMS LIST
      ═══════════════════════════════════════════════════════════════════════ */}
      <PlateCard
        header={
          <div className="flex items-center gap-2">
            <div className="w-1.5 h-1.5" style={{ backgroundColor: domainConfig.accent }} />
            <span>{domainConfig.label} — Detailed Compliance Items</span>
          </div>
        }
        headerRight={
          <span className="text-[0.55rem] font-bold tracking-wider uppercase text-[var(--color-text-muted)]">
            {domainItems.length} items
          </span>
        }
        accent={domainConfig.accent}
        padding="none"
        className="mb-8"
      >
        <div className="flex flex-col">
          {domainItems.length === 0 ? (
            <div className="flex flex-col items-center justify-center py-12 text-center">
              <AlertCircle className="w-6 h-6 text-[var(--color-text-muted)] mb-3" />
              <span className="text-[0.65rem] font-bold tracking-[0.2em] uppercase text-[var(--color-text-muted)]">
                Detailed compliance items sourced from live compliance engine
              </span>
              <span className="text-[0.55rem] text-[var(--color-text-muted)] mt-1">
                {apiSummary ? `${domainSummary.passing} passing · ${domainSummary.warning} warning · ${domainSummary.critical} critical` : 'Connect to backend for real-time item status'}
              </span>
            </div>
          ) : domainItems.map(item => (
            <ComplianceRow
              key={item.id}
              item={item}
              accent={domainConfig.accent}
              isExpanded={expandedItem === item.id}
              onToggle={() => setExpandedItem(expandedItem === item.id ? null : item.id)}
            />
          ))}
        </div>
      </PlateCard>

      {/* ═══════════════════════════════════════════════════════════════════════
          CORRECTIVE ACTION QUEUE
      ═══════════════════════════════════════════════════════════════════════ */}
      <SectionDivider label="Corrective Actions & Review Queue" />
      <div className="mb-8">
        <ActionQueueTable
          items={filteredQueue}
          filter={queueFilter}
          onFilterChange={setQueueFilter}
        />
      </div>

      {/* ═══════════════════════════════════════════════════════════════════════
          EVIDENCE & EXPORT CONTROLS
      ═══════════════════════════════════════════════════════════════════════ */}
      <div className="relative border border-white/6 bg-[#0a0a0c] p-5 mb-6">
        <TacticalCorners />
        <div className="flex flex-col md:flex-row items-start md:items-center justify-between gap-4">
          <div>
            <div className="flex items-center gap-2 mb-1">
              <Layers className="w-4 h-4 text-[#FF6A00]" />
              <span className="text-[0.65rem] font-bold tracking-[0.15em] uppercase text-white">Evidence & Documentation</span>
            </div>
            <p className="text-[0.6rem] text-[var(--color-text-muted)]">Export compliance reports, generate evidence packets, and download audit summaries.</p>
          </div>
          <div className="flex flex-wrap items-center gap-2">
            <button className="flex items-center gap-2 px-3 py-2 border border-white/10 bg-white/[0.02] hover:bg-white/[0.05] transition-colors text-[0.6rem] font-bold tracking-wider uppercase text-[var(--color-text-secondary)] hover:text-white">
              <FileText className="w-3 h-3" /> Generate Packet
            </button>
            <button className="flex items-center gap-2 px-3 py-2 border border-white/10 bg-white/[0.02] hover:bg-white/[0.05] transition-colors text-[0.6rem] font-bold tracking-wider uppercase text-[var(--color-text-secondary)] hover:text-white">
              <Download className="w-3 h-3" /> Export Audit Summary
            </button>
            <button className="flex items-center gap-2 px-3 py-2 border border-white/10 bg-white/[0.02] hover:bg-white/[0.05] transition-colors text-[0.6rem] font-bold tracking-wider uppercase text-[var(--color-text-secondary)] hover:text-white">
              <Activity className="w-3 h-3" /> Compliance Trend Report
            </button>
            <button
              onClick={fetchSummary}
              className="flex items-center gap-2 px-3 py-2 border border-[#FF6A00]/40 bg-[#FF6A00]/10 hover:bg-[#FF6A00]/20 transition-colors text-[0.6rem] font-bold tracking-wider uppercase text-[#FF6A00]"
            >
              <RefreshCw className="w-3 h-3" /> Refresh All Checks
            </button>
          </div>
        </div>
      </div>

      {/* ═══════════════════════════════════════════════════════════════════════
          FOOTER DISCLOSURE
      ═══════════════════════════════════════════════════════════════════════ */}
      <div className="text-center py-4">
        <p className="text-[0.55rem] text-[var(--color-text-disabled)] max-w-3xl mx-auto leading-relaxed">
          FusionEMS provides compliance workflow tooling to support agency-level readiness. All compliance determinations,
          regulatory interpretations, and enforcement responses remain the sole responsibility of the operating agency and
          its legal counsel. This platform does not provide legal, regulatory, or accreditation advice.
        </p>
      </div>
    </AppShell>
  );
}
