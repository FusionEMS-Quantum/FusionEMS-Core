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
  draft:                 { label: 'DRAFT',              bg: 'bg-[#1A1A1C]',       text: 'text-zinc-500',           border: 'border-zinc-800' },
  submitted:             { label: 'SUBMITTED',          bg: 'bg-blue-500/10',     text: 'text-blue-400',           border: 'border-blue-500/20' },
  awaiting_signatures:   { label: 'AWAITING SIGS',      bg: 'bg-amber-500/10',    text: 'text-amber-500',          border: 'border-amber-500/20' },
  missing_documentation: { label: 'MISSING DOCS',       bg: 'bg-red-500/10',      text: 'text-red-500',            border: 'border-red-500/30', glow: 'shadow-[0_0_15px_rgba(239,68,68,0.15)]' },
  sent_to_cad:           { label: 'SENT TO CAD',        bg: 'bg-[#FF4D00]/10',    text: 'text-[#FF4D00]',          border: 'border-[#FF4D00]/30', glow: 'shadow-[0_0_15px_rgba(255,77,0,0.15)]' },
  scheduled:             { label: 'SCHEDULED',          bg: 'bg-emerald-500/10',  text: 'text-emerald-400',        border: 'border-emerald-500/20' },
  accepted:              { label: 'ACCEPTED',           bg: 'bg-emerald-500/10',  text: 'text-emerald-400',        border: 'border-emerald-500/20' },
  rejected:              { label: 'REJECTED',           bg: 'bg-red-500/10',      text: 'text-red-500',            border: 'border-red-500/30' },
  cancelled:             { label: 'CANCELLED',          bg: 'bg-[#1A1A1C]',       text: 'text-zinc-600',           border: 'border-zinc-800' },
};

const MN_STATUS_META: Record<string, { label: string; color: string; border?: string }> = {
  MEDICAL_NECESSITY_SUPPORTED:        { label: 'MN: SUPPORTED',        color: 'text-emerald-400', border: 'border-emerald-500/20 bg-emerald-500/5' },
  MEDICAL_NECESSITY_INSUFFICIENT:     { label: 'MN: INSUFFICIENT',     color: 'text-amber-500', border: 'border-amber-500/20 bg-amber-500/5' },
  LIKELY_NOT_MEDICALLY_NECESSARY:     { label: 'MN: ALERT',            color: 'text-red-500', border: 'border-red-500/20 bg-red-500/5' },
  LEVEL_OF_CARE_NOT_SUPPORTED:        { label: 'LOC: NOT SUPPORTED',   color: 'text-red-500', border: 'border-red-500/20 bg-red-500/5' },
  ABN_REVIEW_REQUIRED:                { label: 'ABN: REQUIRED',        color: 'text-amber-500', border: 'border-amber-500/20 bg-amber-500/5' },
  HUMAN_REVIEW_REQUIRED:              { label: 'REVIEW: REQUIRED',     color: 'text-blue-400', border: 'border-blue-500/20 bg-blue-500/5' },
  WISCONSIN_MEDICAID_SUPPORT_PRESENT: { label: 'WI-MA: SUPPORTED',     color: 'text-emerald-400', border: 'border-emerald-500/20 bg-emerald-500/5' },
  WISCONSIN_MEDICAID_SUPPORT_MISSING: { label: 'WI-MA: GAP',           color: 'text-amber-500', border: 'border-amber-500/20 bg-amber-500/5' },
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

function StatCard({ label, value, sub, icon: Icon, accent = 'text-[#FF4D00]', alert }: StatCardProps) {
  return (
    <div
      className={`relative min-h-[90px] p-4 flex flex-col justify-between border overflow-hidden group transition-all duration-300
        ${alert ? 'border-red-500/30 bg-red-950/20 shadow-[0_4px_24px_rgba(239,68,68,0.06)]' : 'border-zinc-800/80 bg-[#0A0A0B] hover:border-zinc-700/80'}`}
      style={{ clipPath: 'polygon(0 0, calc(100% - 10px) 0, 100% 10px, 100% 100%, 0 100%)' }}
    >
      <div className="flex items-start justify-between z-10">
        <div>
          <div className={`text-3xl font-black font-mono tracking-tighter leading-none ${accent}`}>{value}</div>
          <div className="text-[10px] font-bold tracking-[0.2em] text-zinc-400 mt-2 uppercase">{label}</div>
          {sub && <div className="text-[9px] text-zinc-600 mt-1 uppercase tracking-wider">{sub}</div>}
        </div>
        <div className={`p-2 bg-black/40 border border-white/5 backdrop-blur-sm`} style={{ clipPath: 'polygon(0 0, calc(100% - 6px) 0, 100% 6px, 100% 100%, 0 100%)' }}>
          <Icon className={`w-4 h-4 ${accent}`} />
        </div>
      </div>
      <div className={`absolute bottom-0 left-0 right-0 h-0.5 ${alert ? 'bg-red-500/30' : 'bg-zinc-800 group-hover:bg-zinc-700'} transition-colors`} />
      {alert && <div className="absolute inset-0 bg-red-500/5 pulse-opacity pointer-events-none" />}
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
      className={`group flex items-center gap-4 px-5 py-4 border-b border-zinc-800/50 bg-[#0A0A0B] hover:bg-[#111113] transition-colors relative`}
    >
      {isActionRequired && (
        <div className="absolute left-0 top-0 bottom-0 w-0.5 bg-red-500/50 group-hover:bg-red-500 transition-colors" />
      )}
      
      <div className="flex-1 min-w-0 grid grid-cols-1 md:grid-cols-12 gap-4">
        <div className="md:col-span-4 flex flex-col justify-center">
          <div className="flex items-center gap-2 mb-1">
            <span className="text-sm font-bold text-zinc-100 uppercase tracking-wide truncate">
              {d.patient_name || 'UNIDENTIFIED PATIENT'}
            </span>
          </div>
          <div className="flex items-center gap-2">
            <StatusChip status={status} />
            {d.mrn && <span className="text-[10px] font-mono text-zinc-500 tracking-wider">MRN: {d.mrn}</span>}
          </div>
        </div>
        
        <div className="md:col-span-5 flex flex-col justify-center">
          <div className="flex items-center gap-2 text-xs font-medium text-zinc-400">
            <span className="truncate">{d.origin_facility || 'ORIGIN PENDING'}</span>
            <ChevronRight className="w-3 h-3 text-zinc-700 mx-1 flex-shrink-0" />
            <span className="truncate">{d.destination_facility || 'DEST PENDING'}</span>
          </div>
          <div className="flex items-center gap-2 mt-1.5">
            {d.medical_necessity_status && <MNChip mnStatus={d.medical_necessity_status} />}
          </div>
        </div>

        <div className="md:col-span-3 flex flex-col justify-center items-end text-right">
          {d.service_level && (
            <span className="text-[11px] font-bold text-[#FF4D00] tracking-widest uppercase bg-[#FF4D00]/10 px-2 py-0.5 border border-[#FF4D00]/20" style={{ clipPath: 'polygon(0 0, calc(100% - 4px) 0, 100% 4px, 100% 100%, 0 100%)' }}>
              {d.service_level}
            </span>
          )}
          {d.requested_pickup_time && (
            <span className="text-[10px] font-mono text-zinc-500 mt-1.5">
              {new Date(d.requested_pickup_time).toLocaleString('en-US', {
                month: 'short', day: '2-digit', hour: '2-digit', minute: '2-digit', hour12: false
              }).toUpperCase()}
            </span>
          )}
        </div>
      </div>
      
      <div className="pl-2">
        <div className="w-8 h-8 flex items-center justify-center bg-zinc-900 border border-zinc-800 group-hover:border-[#FF4D00]/50 group-hover:bg-[#FF4D00]/10 transition-colors" style={{ clipPath: 'polygon(0 0, calc(100% - 6px) 0, 100% 6px, 100% 100%, 0 100%)' }}>
          <ChevronRight className="w-4 h-4 text-zinc-500 group-hover:text-[#FF4D00] transition-colors" />
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
    color: 'text-[#FF4D00]',
    bg: 'bg-[#FF4D00]/10',
    border: 'border-[#FF4D00]/30',
    hover: 'hover:bg-[#FF4D00]/20 hover:border-[#FF4D00]/50',
    glow: 'group-hover:shadow-[0_0_20px_rgba(255,77,0,0.15)]'
  },
  {
    href: '/transportlink/requests?filter=awaiting_signatures',
    label: 'AWAITING SIGS',
    sub: 'RESOLVE PENDING FORMS',
    icon: FileWarning,
    color: 'text-amber-500',
    bg: 'bg-amber-500/10',
    border: 'border-amber-500/30',
    hover: 'hover:bg-amber-500/20 hover:border-amber-500/50',
    glow: 'group-hover:shadow-[0_0_20px_rgba(245,158,11,0.15)]'
  },
  {
    href: '/transportlink/requests?filter=missing_documentation',
    label: 'MISSING DOCS',
    sub: 'ATTENTION REQUIRED',
    icon: AlertTriangle,
    color: 'text-red-500',
    bg: 'bg-red-500/10',
    border: 'border-red-500/30',
    hover: 'hover:bg-red-500/20 hover:border-red-500/50',
    glow: 'group-hover:shadow-[0_0_20px_rgba(239,68,68,0.15)]'
  },
  {
    href: '/transportlink/calendar',
    label: 'TRANSPORT OPS',
    sub: 'SCHEDULE & ALLOCATION',
    icon: Clock,
    color: 'text-zinc-400',
    bg: 'bg-zinc-800/50',
    border: 'border-zinc-700',
    hover: 'hover:bg-zinc-800 hover:border-zinc-500',
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
    <div className="min-h-screen bg-[#050505] text-zinc-200 font-sans p-6">
      <div className="max-w-[1600px] mx-auto space-y-6">
        
        {/* Header - Command Center */}
        <div
          className="relative overflow-hidden border border-zinc-800 bg-[#0A0A0B] p-6 lg:p-8"
          style={{ clipPath: 'polygon(0 0, calc(100% - 20px) 0, 100% 20px, 100% 100%, 20px 100%, 0 calc(100% - 20px))' }}
        >
          <div className="absolute top-0 right-0 w-1/2 h-full bg-gradient-to-l from-[#FF4D00]/5 to-transparent pointer-events-none" />
          <div className="absolute top-0 left-0 w-full h-1 bg-gradient-to-r from-[#FF4D00] via-[#FF4D00]/20 to-transparent" />
          
          <div className="relative flex flex-col md:flex-row items-start md:items-center justify-between gap-6 z-10">
            <div>
              <div className="flex items-center gap-3 mb-2">
                <div className="h-2 w-2  bg-[#FF4D00] animate-pulse" />
                <div className="text-[10px] font-bold tracking-[0.3em] text-[#FF4D00] uppercase">
                  TRANSPORTLINK SYSTEM · TERMINAL ACTIVE
                </div>
              </div>
              <h1 className="text-4xl md:text-5xl font-black text-white tracking-tighter uppercase mb-2">
                OPS COMMAND
              </h1>
              <p className="text-sm font-medium tracking-wide text-zinc-400 max-w-2xl uppercase leading-relaxed">
                CMS-AWARE INTAKE. MEDICAL NECESSITY ENFORCEMENT. CAD LINKAGE.
                CONTINUOUS TRUTH FROM REQUEST TO REVENUE.
              </p>
            </div>
            
            <div className="flex items-center gap-3 shrink-0">
              <button
                onClick={load}
                disabled={loading}
                className="flex items-center justify-center w-12 h-12 border border-zinc-700 bg-zinc-900 text-zinc-400 hover:text-white hover:border-zinc-500 hover:bg-zinc-800 transition-all group"
                style={{ clipPath: 'polygon(0 0, calc(100% - 6px) 0, 100% 6px, 100% 100%, 0 100%)' }}
                title="Refresh State"
              >
                <RefreshCw className={`w-5 h-5 ${loading ? 'animate-spin text-[#FF4D00]' : 'group-hover:rotate-180 transition-transform duration-500'}`} />
              </button>
              
              <Link
                href="/transportlink/requests/new"
                className="flex items-center gap-2 h-12 px-6 bg-[#FF4D00] hover:bg-[#E64500] text-black font-black tracking-widest uppercase transition-colors"
                style={{ clipPath: 'polygon(0 0, calc(100% - 8px) 0, 100% 8px, 100% 100%, 0 100%)' }}
              >
                <Zap className="w-4 h-4" />
                <span>INITIATE</span>
              </Link>
            </div>
          </div>

          {/* Compliance Banner */}
          <div className="relative mt-8 flex flex-col sm:flex-row items-start sm:items-center gap-4 p-3 bg-black border border-zinc-800"
            style={{ clipPath: 'polygon(0 0, calc(100% - 8px) 0, 100% 8px, 100% 100%, 0 100%)' }}>
            <div className="flex items-center gap-3 shrink-0">
              <div className="p-1.5 bg-emerald-500/10 border border-emerald-500/20" style={{ clipPath: 'polygon(0 0, calc(100% - 4px) 0, 100% 4px, 100% 100%, 0 100%)' }}>
                <Shield className="w-4 h-4 text-emerald-400" />
              </div>
              <span className="text-[10px] font-bold tracking-[0.2em] text-zinc-500 uppercase">Compliance</span>
            </div>
            <div className="text-[10px] tracking-wider text-zinc-400 font-medium leading-relaxed uppercase">
              <span className="text-zinc-200">FEDERAL MN</span> <span className="text-zinc-700 mx-1">/</span>
              <span className="text-zinc-200">WI FORWARDHEALTH</span> <span className="text-zinc-700 mx-1">/</span>
              <span className="text-zinc-200">ABN WORKFLOW</span> <span className="text-zinc-700 mx-1">/</span>
              <span className="text-zinc-200">NEMSIS 3.5</span>
            </div>
            <div className="sm:ml-auto text-[10px] font-mono font-medium text-zinc-600 uppercase">
              SYS_SYNC: {lastRefresh.toISOString()}
            </div>
          </div>
        </div>

        {/* Global Stats Grid */}
        <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-3">
          <StatCard label="NETWORK LOAD" value={counts.total} icon={Activity} accent="text-zinc-300" />
          <StatCard label="PENDING DISPATCH" value={counts.sentToCad} sub="AWAITING ALLOCATION" icon={Truck} accent="text-[#FF4D00]" />
          <StatCard label="SCHEDULED" value={counts.scheduled} sub="CONFIRMED RUNS" icon={Clock} accent="text-emerald-400" />
          <StatCard label="REVIEW QUEUE" value={counts.pending} sub="IN PROGRESS" icon={FileWarning} accent="text-amber-500" />
          <StatCard label="MISSING DOCS" value={counts.missing} sub="BLOCKED" icon={AlertTriangle} accent="text-red-500" alert={counts.missing > 0} />
          <StatCard label="MN EXCEPTIONS" value={counts.mnIssues} sub="REQ. OVERRIDE" icon={Shield} accent="text-red-500" alert={counts.mnIssues > 0} />
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-4 gap-6">
          {/* Main Feed */}
          <div className="lg:col-span-3 space-y-4">
            <div className="flex items-center justify-between pb-2 border-b-2 border-zinc-800">
              <h2 className="text-[14px] font-bold tracking-[0.2em] text-white uppercase">Active Transport Log</h2>
              <div className="text-[10px] font-bold tracking-widest text-zinc-500 uppercase flex items-center gap-2">
                <span className="w-2 h-2  bg-emerald-500 inline-block"></span>
                LIVE FEED
              </div>
            </div>

            <div className="bg-[#050505] border border-zinc-900 border-t-0 flex flex-col">
              {loading && recent.length === 0 ? (
                <div className="p-12 text-center text-zinc-500 font-mono text-xs uppercase tracking-widest animate-pulse">
                  ESTABLISHING UPLINK...
                </div>
              ) : loadError ? (
                <div className="p-8 text-center">
                  <div className="mx-auto mb-3 flex h-10 w-10 items-center justify-center rounded-sm border border-red-500/30 bg-red-500/10">
                    <AlertTriangle className="h-4 w-4 text-red-500" />
                  </div>
                  <div className="text-[11px] font-bold uppercase tracking-widest text-red-500">
                    FEED UNAVAILABLE
                  </div>
                  <p className="mx-auto mt-2 max-w-xl text-[10px] tracking-wide text-zinc-400">{loadError}</p>
                </div>
              ) : recent.length === 0 ? (
                <div className="p-12 text-center text-zinc-500 font-mono text-xs uppercase tracking-widest">
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
            <div className="flex items-center justify-between pb-2 border-b-2 border-zinc-800">
              <h2 className="text-[14px] font-bold tracking-[0.2em] text-white uppercase">Protocols</h2>
            </div>
            
            <div className="space-y-3">
              {ACTION_ITEMS.map((item, idx) => (
                <Link
                  key={idx}
                  href={item.href}
                  className={`group block p-4 bg-[#0A0A0B] border transition-all duration-300 ${item.border} ${item.hover} ${item.glow}`}
                  style={{ clipPath: 'polygon(0 0, calc(100% - 10px) 0, 100% 10px, 100% 100%, 0 100%)' }}
                >
                  <div className="flex items-center justify-between mb-3">
                    <div className={`p-2 bg-black border border-white/5 ${item.color}`} style={{ clipPath: 'polygon(0 0, calc(100% - 6px) 0, 100% 6px, 100% 100%, 0 100%)' }}>
                      <item.icon className="w-5 h-5" />
                    </div>
                    <ChevronRight className={`w-4 h-4 ${item.color} opacity-50 group-hover:opacity-100 group-hover:translate-x-1 transition-all`} />
                  </div>
                  <div className={`text-[11px] font-black tracking-widest uppercase mb-1 ${item.color}`}>
                    {item.label}
                  </div>
                  <div className="text-[9px] font-bold tracking-widest text-zinc-500 uppercase">
                    {item.sub}
                  </div>
                </Link>
              ))}
            </div>
            
            {/* System Status Block */}
            <div className="mt-8 p-4 bg-zinc-950 border border-zinc-900" style={{ clipPath: 'polygon(0 0, calc(100% - 10px) 0, 100% 10px, 100% 100%, 0 100%)' }}>
              <div className="text-[9px] font-bold tracking-[0.2em] text-zinc-600 uppercase mb-3 border-b border-zinc-800 pb-2">
                SYSTEM HEALTH
              </div>
              <div className="space-y-2">
                <div className="flex justify-between items-center text-[10px] font-mono uppercase">
                  <span className="text-zinc-400">API UPLINK</span>
                  <span className="text-emerald-500">NOMINAL</span>
                </div>
                <div className="flex justify-between items-center text-[10px] font-mono uppercase">
                  <span className="text-zinc-400">CAD SYNC</span>
                  <span className="text-emerald-500">ACTIVE</span>
                </div>
                <div className="flex justify-between items-center text-[10px] font-mono uppercase">
                  <span className="text-zinc-400">BILLING ENG.</span>
                  <span className="text-emerald-500">READY</span>
                </div>
              </div>
            </div>
            
          </div>
        </div>
      </div>
    </div>
  );
}
