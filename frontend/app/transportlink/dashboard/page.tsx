'use client';

import React, { useState, useEffect, useCallback } from 'react';
import Link from 'next/link';
import {
  PlusCircle,
  AlertTriangle,
  Clock,
  Truck,
  FileWarning,
  ChevronRight,
  Shield,
  Activity,
  RefreshCw,
  Zap,
} from 'lucide-react';
import { listTransportLinkRequests, type TransportLinkRequestSummaryApi } from '@/services/api';

type RequestStatus =
  | 'draft'
  | 'submitted'
  | 'awaiting_signatures'
  | 'missing_documentation'
  | 'sent_to_cad'
  | 'scheduled'
  | 'accepted'
  | 'rejected'
  | 'cancelled';

interface TransportSummary {
  id: string;
  data: {
    status: RequestStatus;
    patient_name?: string;
    mrn?: string;
    origin_facility?: string;
    destination_facility?: string;
    service_level?: string;
    medical_necessity_status?: string;
    requested_pickup_time?: string;
    created_at?: string;
    submitted_at?: string;
  };
}

const ALLOWED_REQUEST_STATUSES: readonly RequestStatus[] = [
  'draft',
  'submitted',
  'awaiting_signatures',
  'missing_documentation',
  'sent_to_cad',
  'scheduled',
  'accepted',
  'rejected',
  'cancelled',
] as const;

function normalizeRequestStatus(value: unknown): RequestStatus {
  if (typeof value === 'string' && ALLOWED_REQUEST_STATUSES.includes(value as RequestStatus)) {
    return value as RequestStatus;
  }
  return 'draft';
}

function normalizeTransportSummary(item: TransportLinkRequestSummaryApi): TransportSummary {
  return {
    id: item.id,
    data: {
      ...item.data,
      status: normalizeRequestStatus(item.data?.status),
    },
  };
}

const STATUS_META: Record<
  RequestStatus,
  { label: string; bg: string; text: string; border: string; glow?: string }
> = {
  draft:                 { label: 'DRAFT',              bg: 'bg-[#1A1A1C]',       text: 'text-[var(--color-text-muted)]',           border: 'border-[var(--color-border-default)]' },
  submitted:             { label: 'SUBMITTED',          bg: 'bg-[var(--color-status-info)]/10',     text: 'text-[var(--color-status-info)]',           border: 'border-[var(--color-status-info)]/20' },
  awaiting_signatures:   { label: 'AWAITING SIGS',      bg: 'bg-[var(--q-yellow)]/10',    text: 'text-[var(--q-yellow)]',          border: 'border-amber-500/20' },
  missing_documentation: { label: 'MISSING DOCS',       bg: 'bg-[var(--color-brand-red)]/10',      text: 'text-[var(--color-brand-red)]',            border: 'border-[var(--color-brand-red)]/30', glow: 'shadow-[0_0_15px_rgba(239,68,68,0.15)]' },
  sent_to_cad:           { label: 'SENT TO CAD',        bg: 'bg-[var(--q-orange)]/10',    text: 'text-[var(--q-orange)]',          border: 'border-[var(--q-orange)]/30', glow: 'shadow-[0_0_15px_rgba(255,106,0,0.15)]' },
  scheduled:             { label: 'SCHEDULED',          bg: 'bg-[var(--color-status-active)]/10',  text: 'text-[var(--color-status-active)]',        border: 'border-emerald-500/20' },
  accepted:              { label: 'ACCEPTED',           bg: 'bg-[var(--color-status-active)]/10',  text: 'text-[var(--color-status-active)]',        border: 'border-emerald-500/20' },
  rejected:              { label: 'REJECTED',           bg: 'bg-[var(--color-brand-red)]/10',      text: 'text-[var(--color-brand-red)]',            border: 'border-[var(--color-brand-red)]/30' },
  cancelled:             { label: 'CANCELLED',          bg: 'bg-[#1A1A1C]',       text: 'text-[var(--color-text-muted)]',           border: 'border-[var(--color-border-default)]' },
};

const MN_STATUS_META: Record<string, { label: string; color: string; border?: string }> = {
  MEDICAL_NECESSITY_SUPPORTED:        { label: 'MN: SUPPORTED',        color: 'text-[var(--color-status-active)]', border: 'border-emerald-500/20 bg-[var(--color-status-active)]/5' },
  MEDICAL_NECESSITY_INSUFFICIENT:     { label: 'MN: INSUFFICIENT',     color: 'text-[var(--q-yellow)]', border: 'border-amber-500/20 bg-[var(--q-yellow)]/5' },
  LIKELY_NOT_MEDICALLY_NECESSARY:     { label: 'MN: ALERT',            color: 'text-[var(--color-brand-red)]', border: 'border-[var(--color-brand-red)]/20 bg-[var(--color-brand-red)]/5' },
  LEVEL_OF_CARE_NOT_SUPPORTED:        { label: 'LOC: NOT SUPPORTED',   color: 'text-[var(--color-brand-red)]', border: 'border-[var(--color-brand-red)]/20 bg-[var(--color-brand-red)]/5' },
  ABN_REVIEW_REQUIRED:                { label: 'ABN: REQUIRED',        color: 'text-[var(--q-yellow)]', border: 'border-amber-500/20 bg-[var(--q-yellow)]/5' },
  HUMAN_REVIEW_REQUIRED:              { label: 'REVIEW: REQUIRED',     color: 'text-[var(--color-status-info)]', border: 'border-[var(--color-status-info)]/20 bg-[var(--color-status-info)]/5' },
  WISCONSIN_MEDICAID_SUPPORT_PRESENT: { label: 'WI-MA: SUPPORTED',     color: 'text-[var(--color-status-active)]', border: 'border-emerald-500/20 bg-[var(--color-status-active)]/5' },
  WISCONSIN_MEDICAID_SUPPORT_MISSING: { label: 'WI-MA: GAP',           color: 'text-[var(--q-yellow)]', border: 'border-amber-500/20 bg-[var(--q-yellow)]/5' },
};

function StatusChip({ status }: { status: RequestStatus }) {
  const m = STATUS_META[status] ?? STATUS_META.draft;
  return (
    <span
      className={`inline-flex items-center px-2 py-0.5 text-[9px] font-bold tracking-[0.15em] border ${m.bg} ${m.text} ${m.border} ${m.glow || ''}`}
      style={{ clipPath: 'polygon(0 0, calc(100% - 4px) 0, 100% 4px, 100% 100%, 0 100%)' }}
    >
      {m.label}
    </span>
  );
}

function MNChip({ mnStatus }: { mnStatus?: string }) {
  if (!mnStatus) return null;
  const m = MN_STATUS_META[mnStatus];
  if (!m) return null;
  return (
    <span className={`inline-flex items-center px-1.5 py-0.5 text-[8px] font-bold tracking-widest border ${m.color} ${m.border || 'border-transparent'}`}>
      {m.label}
    </span>
  );
}

interface StatCardProps {
  label: string;
  value: string | number;
  sub?: string;
  icon: React.ElementType;
  accent?: string;
  bg?: string;
  alert?: boolean;
}

function StatCard({ label, value, sub, icon: Icon, accent = 'text-[var(--q-orange)]', alert }: StatCardProps) {
  return (
    <div
      className={`relative min-h-[90px] p-4 flex flex-col justify-between border overflow-hidden group transition-all duration-300
        ${alert ? 'border-[var(--color-brand-red)]/30 bg-[var(--color-brand-red)]/20 shadow-[0_4px_24px_rgba(239,68,68,0.06)]' : 'border-[var(--color-border-default)]/80 bg-[var(--color-bg-panel)] hover:border-[var(--color-border-strong)]/80'}`}
      style={{ clipPath: 'polygon(0 0, calc(100% - 10px) 0, 100% 10px, 100% 100%, 0 100%)' }}
    >
      <div className="flex items-start justify-between z-10">
        <div>
          <div className={`text-3xl font-black font-mono tracking-tighter leading-none ${accent}`}>{value}</div>
          <div className="text-[10px] font-bold tracking-[0.2em] text-[var(--color-text-secondary)] mt-2 uppercase">{label}</div>
          {sub && <div className="text-[9px] text-[var(--color-text-muted)] mt-1 uppercase tracking-wider">{sub}</div>}
        </div>
        <div className={`p-2 bg-[var(--color-bg-base)]/40 border border-white/5 backdrop-blur-sm`} style={{ clipPath: 'polygon(0 0, calc(100% - 6px) 0, 100% 6px, 100% 100%, 0 100%)' }}>
          <Icon className={`w-4 h-4 ${accent}`} />
        </div>
      </div>
      <div className={`absolute bottom-0 left-0 right-0 h-0.5 ${alert ? 'bg-[var(--color-brand-red)]/30' : 'bg-[var(--color-bg-raised)] group-hover:bg-[var(--color-bg-overlay)]'} transition-colors`} />
      {alert && <div className="absolute inset-0 bg-[var(--color-brand-red)]/5 pulse-opacity pointer-events-none" />}
    </div>
  );
}

function RequestRow({ req }: { req: TransportSummary }) {
  const d = req.data;
  const status = (d.status as RequestStatus) ?? 'draft';
  const isActionRequired = ['missing_documentation', 'awaiting_signatures'].includes(status);
  
  return (
    <Link
      href={`/transportlink/requests/${req.id}`}
      className={`group flex items-center gap-4 px-5 py-4 border-b border-[var(--color-border-default)]/50 bg-[var(--color-bg-panel)] hover:bg-[#111113] transition-colors relative`}
    >
      {isActionRequired && (
        <div className="absolute left-0 top-0 bottom-0 w-0.5 bg-[var(--color-brand-red)]/50 group-hover:bg-[var(--color-brand-red)] transition-colors" />
      )}
      
      <div className="flex-1 min-w-0 grid grid-cols-1 md:grid-cols-12 gap-4">
        <div className="md:col-span-4 flex flex-col justify-center">
          <div className="flex items-center gap-2 mb-1">
            <span className="text-sm font-bold text-[var(--color-text-primary)] uppercase tracking-wide truncate">
              {d.patient_name || 'UNIDENTIFIED PATIENT'}
            </span>
          </div>
          <div className="flex items-center gap-2">
            <StatusChip status={status} />
            {d.mrn && <span className="text-[10px] font-mono text-[var(--color-text-muted)] tracking-wider">MRN: {d.mrn}</span>}
          </div>
        </div>
        
        <div className="md:col-span-5 flex flex-col justify-center">
          <div className="flex items-center gap-2 text-xs font-medium text-[var(--color-text-secondary)]">
            <span className="truncate">{d.origin_facility || 'ORIGIN PENDING'}</span>
            <ChevronRight className="w-3 h-3 text-[var(--color-text-disabled)] mx-1 flex-shrink-0" />
            <span className="truncate">{d.destination_facility || 'DEST PENDING'}</span>
          </div>
          <div className="flex items-center gap-2 mt-1.5">
            {d.medical_necessity_status && <MNChip mnStatus={d.medical_necessity_status} />}
          </div>
        </div>

        <div className="md:col-span-3 flex flex-col justify-center items-end text-right">
          {d.service_level && (
            <span className="text-[11px] font-bold text-[var(--q-orange)] tracking-widest uppercase bg-[var(--q-orange)]/10 px-2 py-0.5 border border-[var(--q-orange)]/20" style={{ clipPath: 'polygon(0 0, calc(100% - 4px) 0, 100% 4px, 100% 100%, 0 100%)' }}>
              {d.service_level}
            </span>
          )}
          {d.requested_pickup_time && (
            <span className="text-[10px] font-mono text-[var(--color-text-muted)] mt-1.5">
              {new Date(d.requested_pickup_time).toLocaleString('en-US', {
                month: 'short', day: '2-digit', hour: '2-digit', minute: '2-digit', hour12: false
              }).toUpperCase()}
            </span>
          )}
        </div>
      </div>
      
      <div className="pl-2">
        <div className="w-8 h-8 flex items-center justify-center bg-[var(--color-bg-panel)] border border-[var(--color-border-default)] group-hover:border-[var(--q-orange)]/50 group-hover:bg-[var(--q-orange)]/10 transition-colors" style={{ clipPath: 'polygon(0 0, calc(100% - 6px) 0, 100% 6px, 100% 100%, 0 100%)' }}>
          <ChevronRight className="w-4 h-4 text-[var(--color-text-muted)] group-hover:text-[var(--q-orange)] transition-colors" />
        </div>
      </div>
    </Link>
  );
}

const ACTION_ITEMS = [
  {
    href: '/transportlink/requests/new',
    label: 'NEW TRANSPORT',
    sub: 'INITIATE INTAKE WORKFLOW',
    icon: PlusCircle,
    color: 'text-[var(--q-orange)]',
    bg: 'bg-[var(--q-orange)]/10',
    border: 'border-[var(--q-orange)]/30',
    hover: 'hover:bg-[var(--q-orange)]/20 hover:border-[var(--q-orange)]/50',
    glow: 'group-hover:shadow-[0_0_20px_rgba(255,106,0,0.15)]'
  },
  {
    href: '/transportlink/requests?filter=awaiting_signatures',
    label: 'AWAITING SIGS',
    sub: 'RESOLVE PENDING FORMS',
    icon: FileWarning,
    color: 'text-[var(--q-yellow)]',
    bg: 'bg-[var(--q-yellow)]/10',
    border: 'border-amber-500/30',
    hover: 'hover:bg-[var(--q-yellow)]/20 hover:border-amber-500/50',
    glow: 'group-hover:shadow-[0_0_20px_rgba(245,158,11,0.15)]'
  },
  {
    href: '/transportlink/requests?filter=missing_documentation',
    label: 'MISSING DOCS',
    sub: 'ATTENTION REQUIRED',
    icon: AlertTriangle,
    color: 'text-[var(--color-brand-red)]',
    bg: 'bg-[var(--color-brand-red)]/10',
    border: 'border-[var(--color-brand-red)]/30',
    hover: 'hover:bg-[var(--color-brand-red)]/20 hover:border-[var(--color-brand-red)]/50',
    glow: 'group-hover:shadow-[0_0_20px_rgba(239,68,68,0.15)]'
  },
  {
    href: '/transportlink/calendar',
    label: 'TRANSPORT OPS',
    sub: 'SCHEDULE & ALLOCATION',
    icon: Clock,
    color: 'text-[var(--color-text-secondary)]',
    bg: 'bg-[var(--color-bg-raised)]/50',
    border: 'border-[var(--color-border-strong)]',
    hover: 'hover:bg-[var(--color-bg-raised)] hover:border-[var(--color-border-strong)]',
    glow: ''
  },
];

export default function TransportLinkDashboard() {
  const [recent, setRecent] = useState<TransportSummary[]>([]);
  const [loading, setLoading] = useState(true);
  const [loadError, setLoadError] = useState('');
  const [lastRefresh, setLastRefresh] = useState<Date>(new Date());

  const load = useCallback(async () => {
    setLoading(true);
    setLoadError('');
    try {
      const requests = await listTransportLinkRequests(30);
      setRecent(requests.map(normalizeTransportSummary));
    } catch (err) {
      setLoadError(err instanceof Error ? err.message : 'Unable to load transport dashboard state.');
      setRecent([]);
    } finally {
      setLoading(false);
      setLastRefresh(new Date());
    }
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  const counts = {
    total: recent.length,
    pending: recent.filter((r) => ['submitted', 'awaiting_signatures'].includes(r.data.status)).length,
    missing: recent.filter((r) => r.data.status === 'missing_documentation').length,
    sentToCad: recent.filter((r) => r.data.status === 'sent_to_cad').length,
    scheduled: recent.filter((r) => ['scheduled', 'accepted'].includes(r.data.status)).length,
    mnIssues: recent.filter((r) =>
      ['MEDICAL_NECESSITY_INSUFFICIENT', 'LIKELY_NOT_MEDICALLY_NECESSARY', 'LEVEL_OF_CARE_NOT_SUPPORTED'].includes(
        r.data.medical_necessity_status ?? ''
      )
    ).length,
  };

  return (
    <div className="min-h-screen bg-[var(--color-bg-base)] text-[var(--color-text-primary)] font-sans p-6">
      <div className="max-w-[1600px] mx-auto space-y-6">
        
        {/* Header - Command Center */}
        <div
          className="relative overflow-hidden border border-[var(--color-border-default)] bg-[var(--color-bg-panel)] p-6 lg:p-8"
          style={{ clipPath: 'polygon(0 0, calc(100% - 20px) 0, 100% 20px, 100% 100%, 20px 100%, 0 calc(100% - 20px))' }}
        >
          <div className="absolute top-0 right-0 w-1/2 h-full bg-gradient-to-l from-[var(--q-orange)]/5 to-transparent pointer-events-none" />
          <div className="absolute top-0 left-0 w-full h-1 bg-gradient-to-r from-[var(--q-orange)] via-[var(--q-orange)]/20 to-transparent" />
          
          <div className="relative flex flex-col md:flex-row items-start md:items-center justify-between gap-6 z-10">
            <div>
              <div className="flex items-center gap-3 mb-2">
                <div className="h-2 w-2  bg-[var(--q-orange)] animate-pulse" />
                <div className="text-[10px] font-bold tracking-[0.3em] text-[var(--q-orange)] uppercase">
                  TRANSPORTLINK SYSTEM · TERMINAL ACTIVE
                </div>
              </div>
              <h1 className="text-4xl md:text-5xl font-black text-white tracking-tighter uppercase mb-2">
                OPS COMMAND
              </h1>
              <p className="text-sm font-medium tracking-wide text-[var(--color-text-secondary)] max-w-2xl uppercase leading-relaxed">
                CMS-AWARE INTAKE. MEDICAL NECESSITY ENFORCEMENT. CAD LINKAGE.
                CONTINUOUS TRUTH FROM REQUEST TO REVENUE.
              </p>
            </div>
            
            <div className="flex items-center gap-3 shrink-0">
              <button
                onClick={load}
                disabled={loading}
                className="flex items-center justify-center w-12 h-12 border border-[var(--color-border-strong)] bg-[var(--color-bg-panel)] text-[var(--color-text-secondary)] hover:text-white hover:border-[var(--color-border-strong)] hover:bg-[var(--color-bg-raised)] transition-all group"
                style={{ clipPath: 'polygon(0 0, calc(100% - 6px) 0, 100% 6px, 100% 100%, 0 100%)' }}
                title="Refresh State"
              >
                <RefreshCw className={`w-5 h-5 ${loading ? 'animate-spin text-[var(--q-orange)]' : 'group-hover:rotate-180 transition-transform duration-500'}`} />
              </button>
              
              <Link
                href="/transportlink/requests/new"
                className="flex items-center gap-2 h-12 px-6 bg-[var(--q-orange)] hover:bg-[#E64500] text-black font-black tracking-widest uppercase transition-colors"
                style={{ clipPath: 'polygon(0 0, calc(100% - 8px) 0, 100% 8px, 100% 100%, 0 100%)' }}
              >
                <Zap className="w-4 h-4" />
                <span>INITIATE</span>
              </Link>
            </div>
          </div>

          {/* Compliance Banner */}
          <div className="relative mt-8 flex flex-col sm:flex-row items-start sm:items-center gap-4 p-3 bg-[var(--color-bg-base)] border border-[var(--color-border-default)]"
            style={{ clipPath: 'polygon(0 0, calc(100% - 8px) 0, 100% 8px, 100% 100%, 0 100%)' }}>
            <div className="flex items-center gap-3 shrink-0">
              <div className="p-1.5 bg-[var(--color-status-active)]/10 border border-emerald-500/20" style={{ clipPath: 'polygon(0 0, calc(100% - 4px) 0, 100% 4px, 100% 100%, 0 100%)' }}>
                <Shield className="w-4 h-4 text-[var(--color-status-active)]" />
              </div>
              <span className="text-[10px] font-bold tracking-[0.2em] text-[var(--color-text-muted)] uppercase">Compliance</span>
            </div>
            <div className="text-[10px] tracking-wider text-[var(--color-text-secondary)] font-medium leading-relaxed uppercase">
              <span className="text-[var(--color-text-primary)]">FEDERAL MN</span> <span className="text-[var(--color-text-disabled)] mx-1">/</span>
              <span className="text-[var(--color-text-primary)]">WI FORWARDHEALTH</span> <span className="text-[var(--color-text-disabled)] mx-1">/</span>
              <span className="text-[var(--color-text-primary)]">ABN WORKFLOW</span> <span className="text-[var(--color-text-disabled)] mx-1">/</span>
              <span className="text-[var(--color-text-primary)]">NEMSIS 3.5</span>
            </div>
            <div className="sm:ml-auto text-[10px] font-mono font-medium text-[var(--color-text-muted)] uppercase">
              SYS_SYNC: {lastRefresh.toISOString()}
            </div>
          </div>
        </div>

        {/* Global Stats Grid */}
        <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-3">
          <StatCard label="NETWORK LOAD" value={counts.total} icon={Activity} accent="text-[var(--color-text-secondary)]" />
          <StatCard label="PENDING DISPATCH" value={counts.sentToCad} sub="AWAITING ALLOCATION" icon={Truck} accent="text-[var(--q-orange)]" />
          <StatCard label="SCHEDULED" value={counts.scheduled} sub="CONFIRMED RUNS" icon={Clock} accent="text-[var(--color-status-active)]" />
          <StatCard label="REVIEW QUEUE" value={counts.pending} sub="IN PROGRESS" icon={FileWarning} accent="text-[var(--q-yellow)]" />
          <StatCard label="MISSING DOCS" value={counts.missing} sub="BLOCKED" icon={AlertTriangle} accent="text-[var(--color-brand-red)]" alert={counts.missing > 0} />
          <StatCard label="MN EXCEPTIONS" value={counts.mnIssues} sub="REQ. OVERRIDE" icon={Shield} accent="text-[var(--color-brand-red)]" alert={counts.mnIssues > 0} />
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-4 gap-6">
          {/* Main Feed */}
          <div className="lg:col-span-3 space-y-4">
            <div className="flex items-center justify-between pb-2 border-b-2 border-[var(--color-border-default)]">
              <h2 className="text-[14px] font-bold tracking-[0.2em] text-white uppercase">Active Transport Log</h2>
              <div className="text-[10px] font-bold tracking-widest text-[var(--color-text-muted)] uppercase flex items-center gap-2">
                <span className="w-2 h-2  bg-[var(--color-status-active)] inline-block"></span>
                LIVE FEED
              </div>
            </div>

            <div className="bg-[var(--color-bg-base)] border border-[var(--color-border-subtle)] border-t-0 flex flex-col">
              {loading && recent.length === 0 ? (
                <div className="p-12 text-center text-[var(--color-text-muted)] font-mono text-xs uppercase tracking-widest animate-pulse">
                  ESTABLISHING UPLINK...
                </div>
              ) : loadError ? (
                <div className="p-8 text-center">
                  <div className="mx-auto mb-3 flex h-10 w-10 items-center justify-center rounded-sm border border-[var(--color-brand-red)]/30 bg-[var(--color-brand-red)]/10">
                    <AlertTriangle className="h-4 w-4 text-[var(--color-brand-red)]" />
                  </div>
                  <div className="text-[11px] font-bold uppercase tracking-widest text-[var(--color-brand-red)]">
                    FEED UNAVAILABLE
                  </div>
                  <p className="mx-auto mt-2 max-w-xl text-[10px] tracking-wide text-[var(--color-text-secondary)]">{loadError}</p>
                </div>
              ) : recent.length === 0 ? (
                <div className="p-12 text-center text-[var(--color-text-muted)] font-mono text-xs uppercase tracking-widest">
                  NO ACTIVE TRANSPORTS IN QUEUE
                </div>
              ) : (
                <div className="flex flex-col divide-y divide-zinc-900">
                  {recent.map((req) => (
                    <RequestRow key={req.id} req={req} />
                  ))}
                </div>
              )}
            </div>
          </div>

          {/* Action Protocols */}
          <div className="space-y-4">
            <div className="flex items-center justify-between pb-2 border-b-2 border-[var(--color-border-default)]">
              <h2 className="text-[14px] font-bold tracking-[0.2em] text-white uppercase">Protocols</h2>
            </div>
            
            <div className="space-y-3">
              {ACTION_ITEMS.map((item, idx) => (
                <Link
                  key={idx}
                  href={item.href}
                  className={`group block p-4 bg-[var(--color-bg-panel)] border transition-all duration-300 ${item.border} ${item.hover} ${item.glow}`}
                  style={{ clipPath: 'polygon(0 0, calc(100% - 10px) 0, 100% 10px, 100% 100%, 0 100%)' }}
                >
                  <div className="flex items-center justify-between mb-3">
                    <div className={`p-2 bg-[var(--color-bg-base)] border border-white/5 ${item.color}`} style={{ clipPath: 'polygon(0 0, calc(100% - 6px) 0, 100% 6px, 100% 100%, 0 100%)' }}>
                      <item.icon className="w-5 h-5" />
                    </div>
                    <ChevronRight className={`w-4 h-4 ${item.color} opacity-50 group-hover:opacity-100 group-hover:translate-x-1 transition-all`} />
                  </div>
                  <div className={`text-[11px] font-black tracking-widest uppercase mb-1 ${item.color}`}>
                    {item.label}
                  </div>
                  <div className="text-[9px] font-bold tracking-widest text-[var(--color-text-muted)] uppercase">
                    {item.sub}
                  </div>
                </Link>
              ))}
            </div>
            
            {/* System Status Block */}
            <div className="mt-8 p-4 bg-[var(--color-bg-base)] border border-[var(--color-border-subtle)]" style={{ clipPath: 'polygon(0 0, calc(100% - 10px) 0, 100% 10px, 100% 100%, 0 100%)' }}>
              <div className="text-[9px] font-bold tracking-[0.2em] text-[var(--color-text-muted)] uppercase mb-3 border-b border-[var(--color-border-default)] pb-2">
                SYSTEM HEALTH
              </div>
              <div className="space-y-2">
                <div className="flex justify-between items-center text-[10px] font-mono uppercase">
                  <span className="text-[var(--color-text-secondary)]">API UPLINK</span>
                  <span className="text-[var(--color-status-active)]">NOMINAL</span>
                </div>
                <div className="flex justify-between items-center text-[10px] font-mono uppercase">
                  <span className="text-[var(--color-text-secondary)]">CAD SYNC</span>
                  <span className="text-[var(--color-status-active)]">ACTIVE</span>
                </div>
                <div className="flex justify-between items-center text-[10px] font-mono uppercase">
                  <span className="text-[var(--color-text-secondary)]">BILLING ENG.</span>
                  <span className="text-[var(--color-status-active)]">READY</span>
                </div>
              </div>
            </div>
            
          </div>
        </div>
      </div>
    </div>
  );
}
