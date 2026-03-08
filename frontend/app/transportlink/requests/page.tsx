'use client';

import React, { useState, useEffect, useCallback, Suspense } from 'react';
import Link from 'next/link';
import { useSearchParams } from 'next/navigation';
import {
  PlusCircle,
  Search,
  Filter,
  ChevronRight,
  RefreshCw,
  Truck,
  AlertTriangle,
  XCircle,
  Clock,
  CheckCircle2,
  Send,
  Ban,
  FileWarning,
  Activity,
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

interface TransportRequest {
  id: string;
  created_at?: string;
  data: {
    status: RequestStatus;
    priority?: string;
    patient_name?: string;
    patient_first?: string;
    patient_last?: string;
    mrn?: string;
    csn?: string;
    origin_facility?: string;
    destination_facility?: string;
    requested_service_level?: string;
    medical_necessity_status?: string;
    requested_pickup_time?: string;
    requestor_name?: string;
    payer?: string;
    abn_needed?: boolean;
    mn_explanation?: string;
    submitted_at?: string;
  };
}

const STATUS_CONFIG: Record<
  RequestStatus,
  { label: string; bg: string; text: string; border: string; icon: React.ElementType }
> = {
  draft:                 { label: 'Draft',              bg: 'bg-zinc-950/[0.04]',       text: 'text-zinc-500',        border: 'border-white/[0.08]', icon: Clock },
  submitted:             { label: 'Submitted',          bg: 'bg-status-info/10',     text: 'text-status-info',       border: 'border-status-info/20', icon: Send },
  awaiting_signatures:   { label: 'Awaiting Signatures',bg: 'bg-status-warning/10', text: 'text-status-warning',    border: 'border-status-warning/20', icon: FileWarning },
  missing_documentation: { label: 'Missing Docs',       bg: 'bg-red/10',             text: 'text-red',               border: 'border-red/20', icon: AlertTriangle },
  sent_to_cad:           { label: 'Sent to CAD',        bg: 'bg-[#FF4D00]/10',          text: 'text-[#FF4D00]',            border: 'border-orange/25', icon: Activity },
  scheduled:             { label: 'Scheduled',          bg: 'bg-status-active/10',   text: 'text-status-active',     border: 'border-status-active/20', icon: CheckCircle2 },
  accepted:              { label: 'Accepted',           bg: 'bg-status-active/10',   text: 'text-status-active',     border: 'border-status-active/20', icon: CheckCircle2 },
  rejected:              { label: 'Rejected',           bg: 'bg-red/10',             text: 'text-red-300',           border: 'border-red/25', icon: XCircle },
  cancelled:             { label: 'Cancelled',          bg: 'bg-zinc-950/[0.03]',       text: 'text-zinc-500',        border: 'border-white/[0.06]', icon: Ban },
};

const MN_COLORS: Record<string, string> = {
  MEDICAL_NECESSITY_SUPPORTED:        'text-status-active',
  WISCONSIN_MEDICAID_SUPPORT_PRESENT: 'text-status-active',
  MEDICAL_NECESSITY_INSUFFICIENT:     'text-status-warning',
  LIKELY_NOT_MEDICALLY_NECESSARY:     'text-red',
  LEVEL_OF_CARE_NOT_SUPPORTED:        'text-red',
  ABN_REVIEW_REQUIRED:                'text-status-warning',
  HUMAN_REVIEW_REQUIRED:              'text-status-info',
  WISCONSIN_MEDICAID_SUPPORT_MISSING: 'text-status-warning',
};

const FILTER_TABS: { key: string; label: string }[] = [
  { key: 'all', label: 'All' },
  { key: 'draft', label: 'Drafts' },
  { key: 'submitted', label: 'Submitted' },
  { key: 'awaiting_signatures', label: 'Signatures' },
  { key: 'missing_documentation', label: 'Missing Docs' },
  { key: 'sent_to_cad', label: 'Sent to CAD' },
  { key: 'scheduled', label: 'Scheduled' },
  { key: 'accepted', label: 'Accepted' },
  { key: 'rejected', label: 'Rejected' },
  { key: 'cancelled', label: 'Cancelled' },
];

function normalizeRequestStatus(value: unknown): RequestStatus {
  const normalized = typeof value === 'string' ? value : '';
  if (normalized in STATUS_CONFIG) {
    return normalized as RequestStatus;
  }
  return 'draft';
}

function normalizeRequestSummary(item: TransportLinkRequestSummaryApi): TransportRequest {
  const normalizedServiceLevel = item.data.requested_service_level ?? item.data.service_level;
  return {
    id: item.id,
    created_at: item.data.created_at,
    data: {
      status: normalizeRequestStatus(item.data.status),
      priority: item.data.priority,
      patient_name: item.data.patient_name,
      patient_first: item.data.patient_first,
      patient_last: item.data.patient_last,
      mrn: item.data.mrn,
      csn: item.data.csn,
      origin_facility: item.data.origin_facility,
      destination_facility: item.data.destination_facility,
      requested_service_level: normalizedServiceLevel,
      medical_necessity_status: item.data.medical_necessity_status,
      requested_pickup_time: item.data.requested_pickup_time,
      payer: item.data.payer,
      submitted_at: item.data.submitted_at,
    },
  };
}

function StatusBadge({ status }: { status: RequestStatus }) {
  const c = STATUS_CONFIG[status] ?? STATUS_CONFIG.draft;
  const Icon = c.icon;
  return (
    <span
      className={`inline-flex items-center gap-1 px-2 py-0.5 text-[9px] font-bold uppercase tracking-widest border ${c.bg} ${c.text} ${c.border}`}
      style={{ clipPath: 'polygon(0 0, calc(100% - 4px) 0, 100% 4px, 100% 100%, 0 100%)' }}
    >
      <Icon className="w-2.5 h-2.5" />
      {c.label}
    </span>
  );
}

function RequestCard({ req }: { req: TransportRequest }) {
  const d = req.data;
  const status = (d.status as RequestStatus) ?? 'draft';
  const patientName = d.patient_name || `${d.patient_first || ''} ${d.patient_last || ''}`.trim() || 'Unknown Patient';
  const mnColor = d.medical_necessity_status ? MN_COLORS[d.medical_necessity_status] : '';
  const pickupTime = d.requested_pickup_time ? new Date(d.requested_pickup_time) : null;

  return (
    <Link
      href={`/transportlink/requests/${req.id}`}
      className="flex items-start gap-4 px-4 py-4 border-b border-white/[0.04] hover:bg-zinc-950/[0.02] transition-colors group"
    >
      {/* Priority indicator */}
      <div className={`flex-shrink-0 w-1 self-stretch ${d.priority === 'URGENT' ? 'bg-red' : 'bg-zinc-950/[0.08]'}`} />

      <div className="flex-1 min-w-0">
        <div className="flex items-center gap-2 flex-wrap">
          <span className="text-[12px] font-black text-zinc-100">{patientName}</span>
          {d.mrn && <span className="text-[9px] text-zinc-500 font-mono">MRN {d.mrn}</span>}
          {d.csn && <span className="text-[9px] text-zinc-500 font-mono">CSN {d.csn}</span>}
          <StatusBadge status={status} />
          {d.priority === 'URGENT' && (
            <span className="text-[8px] font-black uppercase tracking-widest text-red bg-red/10 border border-red/20 px-1.5 py-0.5"
              style={{ clipPath: 'polygon(0 0, calc(100% - 3px) 0, 100% 3px, 100% 100%, 0 100%)' }}>
              URGENT
            </span>
          )}
        </div>

        <div className="flex items-center gap-2 mt-1 text-[10px] text-zinc-500 flex-wrap">
          <span className="font-medium">{d.origin_facility || '—'}</span>
          <ChevronRight className="w-2.5 h-2.5 text-zinc-500/30 flex-shrink-0" />
          <span className="font-medium">{d.destination_facility || '—'}</span>
          {d.requested_service_level && (
            <span className="text-[#FF4D00] font-bold border border-orange/20 bg-[#FF4D00]/[0.06] px-1.5 py-0.5 text-[9px]"
              style={{ clipPath: 'polygon(0 0, calc(100% - 3px) 0, 100% 3px, 100% 100%, 0 100%)' }}>
              {d.requested_service_level}
            </span>
          )}
          {d.payer && <span className="text-zinc-500/60">{d.payer}</span>}
        </div>

        {d.medical_necessity_status && (
          <div className={`mt-1 text-[9px] font-semibold ${mnColor}`}>
            MN: {d.medical_necessity_status.replace(/_/g, ' ')}
          </div>
        )}

        {d.abn_needed && (
          <div className="mt-1 flex items-center gap-1 text-[9px] font-bold text-status-warning">
            <AlertTriangle className="w-2.5 h-2.5" />
            ABN Required
          </div>
        )}
      </div>

      <div className="flex-shrink-0 text-right">
        {pickupTime && (
          <div className="text-[10px] text-zinc-400 font-medium">
            {pickupTime.toLocaleDateString()}
          </div>
        )}
        {pickupTime && (
          <div className="text-[9px] text-zinc-500">{pickupTime.toLocaleTimeString()}</div>
        )}
        <div className="text-[9px] text-zinc-500 mt-1">{d.requestor_name || ''}</div>
        <ChevronRight className="w-3.5 h-3.5 text-zinc-500 group-hover:text-[#FF4D00] transition-colors mt-2 ml-auto" />
      </div>
    </Link>
  );
}

function RequestsListInner() {
  const searchParams = useSearchParams();
  const filterParam = searchParams.get('filter') ?? 'all';
  const [activeFilter, setActiveFilter] = useState(filterParam);
  const [requests, setRequests] = useState<TransportRequest[]>([]);
  const [loading, setLoading] = useState(true);
  const [loadError, setLoadError] = useState('');
  const [search, setSearch] = useState('');

  const load = useCallback(async () => {
    setLoading(true);
    setLoadError('');
    try {
      const items = await listTransportLinkRequests(200);
      setRequests(items.map((item) => normalizeRequestSummary(item)));
    } catch (err) {
      setLoadError(err instanceof Error ? err.message : 'Unable to load requests right now.');
      setRequests([]);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { load(); }, [load]);
  useEffect(() => { setActiveFilter(filterParam); }, [filterParam]);

  const filtered = requests.filter((req) => {
    const statusMatch = activeFilter === 'all' || req.data.status === activeFilter;
    if (!statusMatch) return false;
    if (!search.trim()) return true;
    const q = search.toLowerCase();
    const d = req.data;
    const name = `${d.patient_name ?? ''} ${d.patient_first ?? ''} ${d.patient_last ?? ''}`.toLowerCase();
    return (
      name.includes(q) ||
      (d.mrn?.toLowerCase() ?? '').includes(q) ||
      (d.csn?.toLowerCase() ?? '').includes(q) ||
      (d.origin_facility?.toLowerCase() ?? '').includes(q) ||
      (d.destination_facility?.toLowerCase() ?? '').includes(q)
    );
  });

  const countByStatus = (s: string) =>
    requests.filter((r) => s === 'all' ? true : r.data.status === s).length;

  return (
    <div className="p-5 max-w-7xl mx-auto">
      {/* Header */}
      <div className="flex items-start justify-between flex-wrap gap-3 mb-5">
        <div>
          <div className="text-[9px] font-bold tracking-[0.3em] text-[#FF4D00] uppercase mb-1">TransportLink · Requests</div>
          <h1 className="text-h1 font-black text-white">All Transport Requests</h1>
        </div>
        <div className="flex items-center gap-2">
          <button
            onClick={load}
            disabled={loading}
            className="flex items-center gap-1.5 h-9 px-3 text-[10px] font-bold uppercase tracking-wider border border-white/[0.08] text-zinc-500 hover:text-zinc-100 transition-colors"
            style={{ clipPath: 'polygon(0 0, calc(100% - 5px) 0, 100% 5px, 100% 100%, 0 100%)' }}
          >
            <RefreshCw className={`w-3 h-3 ${loading ? 'animate-spin' : ''}`} />
            Refresh
          </button>
          <Link
            href="/transportlink/requests/new"
            className="flex items-center gap-1.5 h-9 px-4 text-[10px] font-black uppercase tracking-wider text-white bg-[#FF4D00] hover:bg-[#FF6A1A] transition-colors"
            style={{ clipPath: 'polygon(0 0, calc(100% - 5px) 0, 100% 5px, 100% 100%, 0 100%)' }}
          >
            <PlusCircle className="w-3.5 h-3.5" />
            New Request
          </Link>
        </div>
      </div>

      {/* Search + filter tabs */}
      <div className="flex flex-col gap-3 mb-4">
        <div className="relative">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-3.5 h-3.5 text-zinc-500 pointer-events-none" />
          <input
            type="text"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            placeholder="Search by patient name, MRN, CSN, facility…"
            className="w-full h-10 pl-9 pr-4 bg-zinc-950/[0.04] border border-white/[0.08] focus:border-orange/40 focus:outline-none text-[12px] text-white placeholder:text-zinc-500 transition-colors"
            style={{ clipPath: 'polygon(0 0, calc(100% - 5px) 0, 100% 5px, 100% 100%, 0 100%)' }}
          />
        </div>

        <div className="flex items-center gap-1 overflow-x-auto pb-1">
          <Filter className="w-3 h-3 text-zinc-500 flex-shrink-0 mr-1" />
          {FILTER_TABS.map(({ key, label }) => {
            const count = countByStatus(key);
            const active = activeFilter === key;
            return (
              <button
                key={key}
                type="button"
                onClick={() => setActiveFilter(key)}
                className={`flex items-center gap-1.5 px-3 py-1.5 text-[10px] font-bold uppercase tracking-wider flex-shrink-0 border transition-colors
                  ${active ? 'text-white bg-[#FF4D00]/15 border-orange/30' : 'text-zinc-500 bg-zinc-950/[0.02] border-white/[0.06] hover:text-zinc-100 hover:bg-zinc-950/[0.04]'}`}
                style={{ clipPath: 'polygon(0 0, calc(100% - 4px) 0, 100% 4px, 100% 100%, 0 100%)' }}
              >
                {label}
                {count > 0 && (
                  <span className={`text-[8px] px-1 ${active ? 'bg-[#FF4D00]/30 text-[#FF4D00]' : 'bg-zinc-950/[0.06] text-zinc-500'}`}>
                    {count}
                  </span>
                )}
              </button>
            );
          })}
        </div>
      </div>

      {/* List */}
      <div
        className="border border-white/[0.06] bg-[#0D0D0F] overflow-hidden"
        style={{ clipPath: 'polygon(0 0, calc(100% - 12px) 0, 100% 12px, 100% 100%, 12px 100%, 0 calc(100% - 12px))' }}
      >
        {loadError && (
          <div
            className="mx-4 mt-4 flex items-start gap-2 border border-red/25 bg-red/[0.06] p-3"
            style={{ clipPath: 'polygon(0 0, calc(100% - 4px) 0, 100% 4px, 100% 100%, 0 100%)' }}
          >
            <AlertTriangle className="mt-0.5 h-3.5 w-3.5 flex-shrink-0 text-red" />
            <span className="text-[10px] text-red">{loadError}</span>
          </div>
        )}
        <div className="px-4 py-3 border-b border-white/[0.04] flex items-center justify-between bg-zinc-950/[0.02]">
          <span className="text-[9px] font-black uppercase tracking-widest text-zinc-500">
            {filtered.length} request{filtered.length !== 1 ? 's' : ''}
            {activeFilter !== 'all' && ` · filtered: ${activeFilter.replace(/_/g, ' ')}`}
          </span>
        </div>

        {loading ? (
          <div className="flex items-center justify-center h-48">
            <div className="flex items-center gap-2 text-zinc-500 text-[11px]">
              <RefreshCw className="w-3.5 h-3.5 animate-spin" />
              Loading requests…
            </div>
          </div>
        ) : filtered.length === 0 ? (
          <div className="flex flex-col items-center justify-center h-48 gap-3">
            <Truck className="w-10 h-10 text-zinc-500/20" />
            <p className="text-[11px] text-zinc-500">
              {loadError
                ? 'Requests could not be loaded. Resolve the error and retry.'
                : requests.length === 0
                  ? 'No requests yet.'
                  : 'No requests match the current filter.'}
            </p>
            {requests.length === 0 && !loadError && (
              <Link
                href="/transportlink/requests/new"
                className="flex items-center gap-1.5 h-8 px-4 text-[10px] font-bold uppercase tracking-wider text-white bg-[#FF4D00]/20 border border-orange/30 hover:bg-[#FF4D00]/30 transition-colors"
                style={{ clipPath: 'polygon(0 0, calc(100% - 4px) 0, 100% 4px, 100% 100%, 0 100%)' }}
              >
                <PlusCircle className="w-3 h-3" />
                Create First Request
              </Link>
            )}
          </div>
        ) : (
          <div>
            {filtered.map((req) => (
              <RequestCard key={req.id} req={req} />
            ))}
          </div>
        )}
      </div>
    </div>
  );
}

export default function RequestsListPage() {
  return (
    <Suspense fallback={null}>
      <RequestsListInner />
    </Suspense>
  );
}
