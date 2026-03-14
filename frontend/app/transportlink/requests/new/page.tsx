'use client';

/**
 * TransportLink New Request Wizard
 * 10-step CMS-aware, Wisconsin-first transport intake form.
 * Right-side readiness panel tracks completeness in real time.
 */

import React, { useState, useCallback, useEffect, Suspense } from 'react';
import { useRouter } from 'next/navigation';
import {
  CheckCircle2,
  Circle,
  AlertTriangle,
  ChevronRight,
  ChevronLeft,
  Loader2,
  Shield,
  AlertCircle,
  Info,
  XCircle,
  Clock,
  Truck,
  User,
  MapPin,
  Stethoscope,
  Activity,
  Paperclip,
  PenSquare,
  Eye,
  Send,
} from 'lucide-react';
import { createTransportLinkRequest, submitTransportLinkToCad } from '@/services/api';

// ─────────────────────────────────────────────────────────────
// Types
// ─────────────────────────────────────────────────────────────

type ServiceLevel = 'BLS' | 'ALS' | 'ALS2' | 'CCT' | 'SCT' | '';

type MNStatus =
  | 'MEDICAL_NECESSITY_SUPPORTED'
  | 'MEDICAL_NECESSITY_INSUFFICIENT'
  | 'LIKELY_NOT_MEDICALLY_NECESSARY'
  | 'LEVEL_OF_CARE_NOT_SUPPORTED'
  | 'ABN_REVIEW_REQUIRED'
  | 'HUMAN_REVIEW_REQUIRED'
  | 'WISCONSIN_MEDICAID_SUPPORT_PRESENT'
  | 'WISCONSIN_MEDICAID_SUPPORT_MISSING'
  | '';

interface RequestDraft {
  // Step 1 – Basics
  priority: 'URGENT' | 'SCHEDULED' | '';
  requested_pickup_time: string;
  requestor_name: string;
  requestor_title: string;
  requestor_phone: string;
  facility_department: string;

  // Step 2 – Patient Identity
  patient_first: string;
  patient_last: string;
  patient_dob: string;
  patient_sex: 'M' | 'F' | 'Other' | '';
  mrn: string;
  csn: string;
  encounter_number: string;
  sending_unit: string;
  ordering_provider: string;
  payer: string;
  payer_member_id: string;

  // Step 3 – Origin/Destination
  origin_facility: string;
  origin_address: string;
  origin_unit: string;
  destination_facility: string;
  destination_address: string;
  destination_unit: string;

  // Step 4 – Clinical reason
  chief_complaint: string;
  diagnosis_codes: string;
  clinical_reason: string;
  transport_reason: string;

  // Step 5 – Medical necessity
  mn_reason_cannot_walk: boolean;
  mn_reason_wheelchair_insufficient: boolean;
  mn_reason_supine_required: boolean;
  mn_reason_monitoring: boolean;
  mn_reason_oxygen: boolean;
  mn_reason_infusion: boolean;
  mn_reason_vent: boolean;
  mn_reason_dementia: boolean;
  mn_reason_altered_ms: boolean;
  mn_reason_fall_risk: boolean;
  mn_reason_other: string;
  mn_why_not_wheelchair: string;
  mn_why_not_private_vehicle: string;
  mn_patient_condition_summary: string;

  // Step 6 – Level of care
  requested_service_level: ServiceLevel;
  mn_status: MNStatus;
  mn_explanation: string;
  mn_policy_basis: string;
  mn_human_review_needed: boolean;

  // Step 7 – Documents
  pcs_complete: boolean;
  aob_complete: boolean;
  facesheet_uploaded: boolean;
  physician_order_uploaded: boolean;
  discharge_docs_uploaded: boolean;
  attached_files: string[];

  // Step 8 – Signatures
  requestor_attested: boolean;
  pcs_signed: boolean;
  aob_signed: boolean;
  abn_needed: boolean;
  abn_reviewed: boolean;
  abn_presented: boolean;
  abn_signed: boolean;
  abn_signer_name: string;
  abn_signer_relationship: string;

  // Step 9 – Review (no new fields)
  // Step 10 – Submit (no new fields)
}

const EMPTY_DRAFT: RequestDraft = {
  priority: '',
  requested_pickup_time: '',
  requestor_name: '',
  requestor_title: '',
  requestor_phone: '',
  facility_department: '',
  patient_first: '',
  patient_last: '',
  patient_dob: '',
  patient_sex: '',
  mrn: '',
  csn: '',
  encounter_number: '',
  sending_unit: '',
  ordering_provider: '',
  payer: '',
  payer_member_id: '',
  origin_facility: '',
  origin_address: '',
  origin_unit: '',
  destination_facility: '',
  destination_address: '',
  destination_unit: '',
  chief_complaint: '',
  diagnosis_codes: '',
  clinical_reason: '',
  transport_reason: '',
  mn_reason_cannot_walk: false,
  mn_reason_wheelchair_insufficient: false,
  mn_reason_supine_required: false,
  mn_reason_monitoring: false,
  mn_reason_oxygen: false,
  mn_reason_infusion: false,
  mn_reason_vent: false,
  mn_reason_dementia: false,
  mn_reason_altered_ms: false,
  mn_reason_fall_risk: false,
  mn_reason_other: '',
  mn_why_not_wheelchair: '',
  mn_why_not_private_vehicle: '',
  mn_patient_condition_summary: '',
  requested_service_level: '',
  mn_status: '',
  mn_explanation: '',
  mn_policy_basis: '',
  mn_human_review_needed: false,
  pcs_complete: false,
  aob_complete: false,
  facesheet_uploaded: false,
  physician_order_uploaded: false,
  discharge_docs_uploaded: false,
  attached_files: [],
  requestor_attested: false,
  pcs_signed: false,
  aob_signed: false,
  abn_needed: false,
  abn_reviewed: false,
  abn_presented: false,
  abn_signed: false,
  abn_signer_name: '',
  abn_signer_relationship: '',
};

// ─────────────────────────────────────────────────────────────
// Readiness engine
// ─────────────────────────────────────────────────────────────

interface ReadinessItem {
  label: string;
  complete: boolean;
  warning?: boolean;
}

function computeReadiness(d: RequestDraft): ReadinessItem[] {
  const patientName = !!(d.patient_first && d.patient_last);
  const mnSelected = Object.entries(d).some(
    ([k, v]) => k.startsWith('mn_reason_') && typeof v === 'boolean' && v
  );
  const mnComplete =
    mnSelected &&
    !!d.mn_why_not_private_vehicle &&
    !!d.mn_patient_condition_summary;

  const mnStatusOk = [
    'MEDICAL_NECESSITY_SUPPORTED',
    'WISCONSIN_MEDICAID_SUPPORT_PRESENT',
  ].includes(d.mn_status);

  const abnComplete =
    !d.abn_needed || (d.abn_reviewed && d.abn_presented && d.abn_signed);

  return [
    { label: 'Patient identity', complete: patientName },
    { label: 'MRN', complete: !!d.mrn },
    { label: 'CSN', complete: !!d.csn },
    { label: 'Origin complete', complete: !!(d.origin_facility && d.origin_address) },
    { label: 'Destination complete', complete: !!(d.destination_facility && d.destination_address) },
    { label: 'Clinical reason', complete: !!(d.chief_complaint && d.clinical_reason) },
    { label: 'Medical necessity', complete: mnComplete, warning: !mnStatusOk && mnComplete },
    { label: 'Level of care', complete: !!d.requested_service_level && mnStatusOk, warning: !!d.requested_service_level && !mnStatusOk },
    { label: 'PCS complete', complete: d.pcs_complete },
    { label: 'AOB complete', complete: d.aob_complete },
    { label: 'Facesheet uploaded', complete: d.facesheet_uploaded },
    { label: 'Signatures complete', complete: d.requestor_attested && d.pcs_signed && d.aob_signed },
    { label: 'ABN reviewed if required', complete: abnComplete, warning: d.abn_needed && !abnComplete },
    { label: 'Ready for CAD', complete: false }, // computed below
  ];
}

function isReadyForCad(items: ReadinessItem[]): boolean {
  return items.slice(0, -1).every((i) => i.complete && !i.warning);
}

// ─────────────────────────────────────────────────────────────
// Step definitions
// ─────────────────────────────────────────────────────────────

const STEPS = [
  { id: 1, label: 'Basics',           icon: Clock },
  { id: 2, label: 'Patient Identity', icon: User },
  { id: 3, label: 'Origin/Dest',      icon: MapPin },
  { id: 4, label: 'Clinical Reason',  icon: Stethoscope },
  { id: 5, label: 'Med Necessity',    icon: Activity },
  { id: 6, label: 'Level of Care',    icon: Truck },
  { id: 7, label: 'Documents',        icon: Paperclip },
  { id: 8, label: 'Signatures',       icon: PenSquare },
  { id: 9, label: 'Review',           icon: Eye },
  { id: 10, label: 'Submit to CAD',   icon: Send },
];

// ─────────────────────────────────────────────────────────────
// Shared input primitives
// ─────────────────────────────────────────────────────────────

const CLIP = { clipPath: 'polygon(0 0, calc(100% - 5px) 0, 100% 5px, 100% 100%, 0 100%)' };
const INPUT = 'w-full h-10 px-3 bg-[var(--color-bg-base)]/[0.04] border border-white/[0.08] focus:border-orange/40 focus:outline-none text-[12px] text-white placeholder:text-[var(--color-text-muted)] transition-colors';
const TEXTAREA = 'w-full px-3 py-2 bg-[var(--color-bg-base)]/[0.04] border border-white/[0.08] focus:border-orange/40 focus:outline-none text-[12px] text-white placeholder:text-[var(--color-text-muted)] transition-colors resize-none';

function FL({ label, req, children }: { label: string; req?: boolean; children: React.ReactNode }) {
  return (
    <div className="space-y-1.5">
      <label className="text-[10px] font-bold uppercase tracking-widest text-[var(--color-text-muted)]">
        {label}{req && <span className="text-red ml-1">*</span>}
      </label>
      {children}
    </div>
  );
}

function CheckRow({
  label,
  value,
  onChange,
  warning,
}: {
  label: string;
  value: boolean;
  onChange: (_v: boolean) => void;
  warning?: string;
}) {
  return (
    <label className="flex items-start gap-2.5 cursor-pointer group">
      <button
        type="button"
        onClick={() => onChange(!value)}
        className={`flex-shrink-0 w-4 h-4 mt-0.5 border ${value ? 'bg-[var(--q-orange)]/20 border-orange' : 'bg-[var(--color-bg-base)]/[0.04] border-white/[0.12]'} transition-colors flex items-center justify-center`}
        style={{ clipPath: 'polygon(0 0, calc(100% - 3px) 0, 100% 3px, 100% 100%, 0 100%)' }}
      >
        {value && <CheckCircle2 className="w-2.5 h-2.5 text-[var(--q-orange)]" />}
      </button>
      <div>
        <span className={`text-[11px] font-medium ${value ? 'text-white' : 'text-[var(--color-text-secondary)]'} group-hover:text-[var(--color-text-primary)] transition-colors`}>
          {label}
        </span>
        {warning && value && (
          <div className="flex items-center gap-1 mt-0.5">
            <AlertTriangle className="w-2.5 h-2.5 text-status-warning flex-shrink-0" />
            <span className="text-[9px] text-status-warning">{warning}</span>
          </div>
        )}
      </div>
    </label>
  );
}

// ─────────────────────────────────────────────────────────────
// MN Status evaluation (client-side rule preview)
// ─────────────────────────────────────────────────────────────

function evaluateMNStatus(d: RequestDraft): { status: MNStatus; explanation: string; policy: string } {
  const hasAnyReason = d.mn_reason_cannot_walk || d.mn_reason_wheelchair_insufficient ||
    d.mn_reason_supine_required || d.mn_reason_monitoring || d.mn_reason_oxygen ||
    d.mn_reason_infusion || d.mn_reason_vent;

  const weakOnly = !hasAnyReason && (d.mn_reason_dementia || d.mn_reason_altered_ms || d.mn_reason_fall_risk);
  const hasWhy = !!d.mn_why_not_private_vehicle && !!d.mn_patient_condition_summary;
  const isMedicare = d.payer?.toLowerCase().includes('medicare');
  const isWiMedicaid = d.payer?.toLowerCase().includes('medicaid') || d.payer?.toLowerCase().includes('forwardhealth');

  if (!hasAnyReason && !weakOnly) {
    return {
      status: '',
      explanation: 'No transport justification has been selected yet.',
      policy: '',
    };
  }

  if (weakOnly) {
    return {
      status: 'LIKELY_NOT_MEDICALLY_NECESSARY',
      explanation: 'Dementia, altered mental status, fall risk, and similar conditions are not stand-alone ambulance medical necessity justifications. The current information does not support ambulance medical necessity. The request requires patient-specific clinical documentation explaining why other transport means are unsafe.',
      policy: 'Medicare Benefit Policy Manual Ch. 10; Wisconsin ForwardHealth non-emergency ambulance criteria',
    };
  }

  if (!hasWhy) {
    return {
      status: 'MEDICAL_NECESSITY_INSUFFICIENT',
      explanation: 'You have selected clinical conditions but have not explained why private vehicle and wheelchair van transport are not appropriate for this patient. Both explanations are required.',
      policy: 'CMS Ambulance Services compliance guidance; Medicare Benefit Policy Manual Ch. 10',
    };
  }

  if (isMedicare && (d.mn_reason_dementia || d.mn_reason_altered_ms) && !hasAnyReason) {
    return {
      status: 'ABN_REVIEW_REQUIRED',
      explanation: 'The selected justifications present noncoverage risk under Original Medicare. ABN review may be required before transport if the service is expected to be denied.',
      policy: 'CMS ABN requirements; Medicare Benefit Policy Manual Ch. 10',
    };
  }

  if (isWiMedicaid) {
    if (d.mn_reason_supine_required || d.mn_reason_monitoring || d.mn_reason_oxygen || d.mn_reason_infusion || d.mn_reason_vent) {
      return {
        status: 'WISCONSIN_MEDICAID_SUPPORT_PRESENT',
        explanation: 'The selected clinical conditions appear to meet Wisconsin ForwardHealth non-emergency ambulance criteria: patient requires BLS/ALS life-support services during transport and/or transport in a supine position.',
        policy: 'Wisconsin ForwardHealth non-emergency ambulance criteria (DHS 107.23)',
      };
    }
    return {
      status: 'WISCONSIN_MEDICAID_SUPPORT_MISSING',
      explanation: 'Wisconsin Medicaid (ForwardHealth) requires that the patient requires BLS or ALS life-support services during transport, supine transport, or has an illness or injury preventing safe transport by other means. The current selection does not clearly meet these criteria.',
      policy: 'Wisconsin ForwardHealth non-emergency ambulance criteria (DHS 107.23)',
    };
  }

  // Default: Medicare / commercial general
  if (hasAnyReason && hasWhy) {
    return {
      status: 'MEDICAL_NECESSITY_SUPPORTED',
      explanation: 'The current documentation supports ambulance medical necessity. The patient cannot be transported safely by other means based on the selected clinical conditions and provided explanations.',
      policy: 'Medicare Benefit Policy Manual Ch. 10; CMS Ambulance Services compliance guidance',
    };
  }

  return {
    status: 'HUMAN_REVIEW_REQUIRED',
    explanation: 'The current information is ambiguous and requires human review before proceeding.',
    policy: '',
  };
}

// ─────────────────────────────────────────────────────────────
// Readiness Panel
// ─────────────────────────────────────────────────────────────

function ReadinessPanel({ draft, ready }: { draft: RequestDraft; ready: boolean }) {
  const items = computeReadiness(draft);
  const finalItems = items.map((item, i) =>
    i === items.length - 1 ? { ...item, complete: ready } : item
  );

  return (
    <div
      className="w-60 flex-shrink-0 border border-white/[0.06] bg-[#0D0D0F] overflow-hidden"
      style={{ clipPath: 'polygon(0 0, calc(100% - 10px) 0, 100% 10px, 100% 100%, 0 100%)' }}
    >
      <div className="px-4 py-3 border-b border-white/[0.05] bg-gradient-to-r from-orange/[0.06]">
        <div className="text-[9px] font-black uppercase tracking-[0.25em] text-[var(--q-orange)]">Readiness Check</div>
        <div className="text-[8px] text-[var(--color-text-muted)] mt-0.5">Required for CAD submission</div>
      </div>

      <div className="p-3 space-y-1.5">
        {finalItems.map((item) => (
          <div key={item.label} className="flex items-center gap-2">
            {item.complete && !item.warning ? (
              <CheckCircle2 className="w-3 h-3 text-[var(--color-status-active)] flex-shrink-0" />
            ) : item.warning ? (
              <AlertTriangle className="w-3 h-3 text-status-warning flex-shrink-0" />
            ) : (
              <Circle className="w-3 h-3 text-[var(--color-text-muted)]/30 flex-shrink-0" />
            )}
            <span className={`text-[10px] ${item.complete && !item.warning ? 'text-[var(--color-text-secondary)]' : item.warning ? 'text-status-warning' : 'text-[var(--color-text-muted)]'}`}>
              {item.label}
            </span>
          </div>
        ))}
      </div>

      <div className={`mx-3 mb-3 p-2.5 border text-center ${ready ? 'border-status-active/25 bg-status-active/[0.06]' : 'border-white/[0.06] bg-[var(--color-bg-base)]/[0.02]'}`}
        style={{ clipPath: 'polygon(0 0, calc(100% - 5px) 0, 100% 5px, 100% 100%, 0 100%)' }}>
        <div className={`text-[10px] font-black uppercase tracking-widest ${ready ? 'text-[var(--color-status-active)]' : 'text-[var(--color-text-muted)]'}`}>
          {ready ? '✓ Ready for CAD' : 'Incomplete'}
        </div>
      </div>

      <div className="px-3 pb-3">
        <div className="flex items-start gap-1.5 p-2.5 bg-[var(--q-orange)]/[0.04] border border-orange/10"
          style={{ clipPath: 'polygon(0 0, calc(100% - 4px) 0, 100% 4px, 100% 100%, 0 100%)' }}>
          <Shield className="w-2.5 h-2.5 text-[var(--q-orange)] flex-shrink-0 mt-0.5" />
          <span className="text-[9px] text-[var(--color-text-muted)] leading-relaxed">
            CMS-aware · WI ForwardHealth · ABN logic active
          </span>
        </div>
      </div>
    </div>
  );
}

// ─────────────────────────────────────────────────────────────
// Step Components
// ─────────────────────────────────────────────────────────────

function Step1({ d, set }: { d: RequestDraft; set: (_f: keyof RequestDraft, _v: unknown) => void }) {
  return (
    <div className="space-y-5">
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        <FL label="Priority" req>
          <select value={d.priority} onChange={(e) => set('priority', e.target.value)}
            className={`${INPUT} appearance-none`} style={CLIP}>
            <option value="">Select priority</option>
            <option value="URGENT">Urgent</option>
            <option value="SCHEDULED">Scheduled (Non-Emergency)</option>
          </select>
        </FL>
        <FL label="Requested Pickup Time" req>
          <input type="datetime-local" value={d.requested_pickup_time}
            onChange={(e) => set('requested_pickup_time', e.target.value)}
            className={INPUT} style={CLIP} />
        </FL>
        <FL label="Requestor Name" req>
          <input type="text" value={d.requestor_name} onChange={(e) => set('requestor_name', e.target.value)}
            placeholder="Jane Smith" className={INPUT} style={CLIP} />
        </FL>
        <FL label="Requestor Title / Role">
          <input type="text" value={d.requestor_title} onChange={(e) => set('requestor_title', e.target.value)}
            placeholder="Discharge Planner" className={INPUT} style={CLIP} />
        </FL>
        <FL label="Callback Number">
          <input type="tel" value={d.requestor_phone} onChange={(e) => set('requestor_phone', e.target.value)}
            placeholder="414-555-0100" className={INPUT} style={CLIP} />
        </FL>
        <FL label="Department / Unit">
          <input type="text" value={d.facility_department} onChange={(e) => set('facility_department', e.target.value)}
            placeholder="ED, Case Management, 4 North…" className={INPUT} style={CLIP} />
        </FL>
      </div>
    </div>
  );
}

function Step2({ d, set }: { d: RequestDraft; set: (_f: keyof RequestDraft, _v: unknown) => void }) {
  return (
    <div className="space-y-5">
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        <FL label="First Name" req>
          <input type="text" value={d.patient_first} onChange={(e) => set('patient_first', e.target.value)}
            placeholder="John" className={INPUT} style={CLIP} />
        </FL>
        <FL label="Last Name" req>
          <input type="text" value={d.patient_last} onChange={(e) => set('patient_last', e.target.value)}
            placeholder="Smith" className={INPUT} style={CLIP} />
        </FL>
        <FL label="Date of Birth" req>
          <input type="date" value={d.patient_dob} onChange={(e) => set('patient_dob', e.target.value)}
            className={INPUT} style={CLIP} />
        </FL>
        <FL label="Sex">
          <select value={d.patient_sex} onChange={(e) => set('patient_sex', e.target.value)}
            className={`${INPUT} appearance-none`} style={CLIP}>
            <option value="">Select</option>
            <option value="M">Male</option>
            <option value="F">Female</option>
            <option value="Other">Other</option>
          </select>
        </FL>
        <FL label="MRN" req>
          <input type="text" value={d.mrn} onChange={(e) => set('mrn', e.target.value)}
            placeholder="Epic MRN" className={INPUT} style={CLIP} />
        </FL>
        <FL label="CSN / Visit Number" req>
          <input type="text" value={d.csn} onChange={(e) => set('csn', e.target.value)}
            placeholder="Epic CSN" className={INPUT} style={CLIP} />
        </FL>
        <FL label="Encounter Number">
          <input type="text" value={d.encounter_number} onChange={(e) => set('encounter_number', e.target.value)}
            placeholder="If applicable" className={INPUT} style={CLIP} />
        </FL>
        <FL label="Sending Unit / Bed">
          <input type="text" value={d.sending_unit} onChange={(e) => set('sending_unit', e.target.value)}
            placeholder="Room 412B" className={INPUT} style={CLIP} />
        </FL>
        <FL label="Ordering / Attending Provider">
          <input type="text" value={d.ordering_provider} onChange={(e) => set('ordering_provider', e.target.value)}
            placeholder="Dr. Nguyen" className={INPUT} style={CLIP} />
        </FL>
        <FL label="Primary Payer" req>
          <select value={d.payer} onChange={(e) => set('payer', e.target.value)}
            className={`${INPUT} appearance-none`} style={CLIP}>
            <option value="">Select payer</option>
            <option value="Medicare Part B">Medicare Part B (Original)</option>
            <option value="Medicare Advantage">Medicare Advantage</option>
            <option value="Wisconsin Medicaid / ForwardHealth">Wisconsin Medicaid / ForwardHealth</option>
            <option value="Commercial">Commercial / Private Insurance</option>
            <option value="Self-Pay">Self-Pay</option>
            <option value="Other">Other</option>
          </select>
        </FL>
        <FL label="Member ID / Policy Number">
          <input type="text" value={d.payer_member_id} onChange={(e) => set('payer_member_id', e.target.value)}
            placeholder="Insurance member ID" className={INPUT} style={CLIP} />
        </FL>
      </div>
      <div className="p-3 bg-status-info/[0.04] border border-status-info/15"
        style={CLIP}>
        <div className="flex items-start gap-2">
          <Info className="w-3.5 h-3.5 text-status-info flex-shrink-0 mt-0.5" />
          <p className="text-[10px] text-[var(--color-text-secondary)] leading-relaxed">
            MRN and CSN will carry forward to CAD, ePCR, and billing. Ensure these match the patient&apos;s EHR identifiers exactly.
          </p>
        </div>
      </div>
    </div>
  );
}

function Step3({ d, set }: { d: RequestDraft; set: (_f: keyof RequestDraft, _v: unknown) => void }) {
  return (
    <div className="space-y-6">
      <div>
        <div className="flex items-center gap-2 mb-3">
          <div className="w-5 h-5  bg-[var(--q-orange)]/15 border border-orange/25 flex items-center justify-center text-[9px] font-black text-[var(--q-orange)]">O</div>
          <span className="text-[10px] font-black uppercase tracking-widest text-[var(--q-orange)]">Origin</span>
        </div>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <FL label="Origin Facility Name" req>
            <input type="text" value={d.origin_facility} onChange={(e) => set('origin_facility', e.target.value)}
              placeholder="Mercy Medical Center" className={INPUT} style={CLIP} />
          </FL>
          <FL label="Origin Unit / Room">
            <input type="text" value={d.origin_unit} onChange={(e) => set('origin_unit', e.target.value)}
              placeholder="4 North, Room 412" className={INPUT} style={CLIP} />
          </FL>
          <div className="md:col-span-2">
            <FL label="Origin Address" req>
              <input type="text" value={d.origin_address} onChange={(e) => set('origin_address', e.target.value)}
                placeholder="1000 N 92nd St, Milwaukee, WI 53226" className={INPUT} style={CLIP} />
            </FL>
          </div>
        </div>
      </div>

      <div>
        <div className="flex items-center gap-2 mb-3">
          <div className="w-5 h-5  bg-red/15 border border-red/25 flex items-center justify-center text-[9px] font-black text-red">D</div>
          <span className="text-[10px] font-black uppercase tracking-widest text-red">Destination</span>
        </div>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <FL label="Destination Facility / Location" req>
            <input type="text" value={d.destination_facility} onChange={(e) => set('destination_facility', e.target.value)}
              placeholder="Brookfield Rehab Center" className={INPUT} style={CLIP} />
          </FL>
          <FL label="Destination Unit">
            <input type="text" value={d.destination_unit} onChange={(e) => set('destination_unit', e.target.value)}
              placeholder="Admissions, Floor 2" className={INPUT} style={CLIP} />
          </FL>
          <div className="md:col-span-2">
            <FL label="Destination Address" req>
              <input type="text" value={d.destination_address} onChange={(e) => set('destination_address', e.target.value)}
                placeholder="17000 W North Ave, Brookfield, WI 53005" className={INPUT} style={CLIP} />
            </FL>
          </div>
        </div>
      </div>
    </div>
  );
}

function Step4({ d, set }: { d: RequestDraft; set: (_f: keyof RequestDraft, _v: unknown) => void }) {
  return (
    <div className="space-y-4">
      <FL label="Chief Complaint / Primary Diagnosis" req>
        <input type="text" value={d.chief_complaint} onChange={(e) => set('chief_complaint', e.target.value)}
          placeholder="e.g., Hip fracture, post-op day 2, non-ambulatory" className={INPUT} style={CLIP} />
      </FL>
      <FL label="ICD-10 Diagnosis Codes (comma-separated)">
        <input type="text" value={d.diagnosis_codes} onChange={(e) => set('diagnosis_codes', e.target.value)}
          placeholder="S72.001A, Z96.641" className={INPUT} style={CLIP} />
      </FL>
      <FL label="Clinical Narrative for Transport" req>
        <textarea value={d.clinical_reason} onChange={(e) => set('clinical_reason', e.target.value)}
          placeholder="Describe the patient's current clinical condition, why they require ambulance transport, and what makes other transport means unsafe or inappropriate…"
          rows={5} className={TEXTAREA} style={CLIP} />
      </FL>
      <FL label="Transport Reason / Destination Purpose" req>
        <textarea value={d.transport_reason} onChange={(e) => set('transport_reason', e.target.value)}
          placeholder="e.g., Discharge to skilled nursing facility following surgical repair of left hip fracture..."
          rows={3} className={TEXTAREA} style={CLIP} />
      </FL>
      <div className="p-3 bg-status-warning/[0.04] border border-status-warning/15" style={CLIP}>
        <div className="flex items-start gap-2">
          <AlertTriangle className="w-3.5 h-3.5 text-status-warning flex-shrink-0 mt-0.5" />
          <p className="text-[10px] text-[var(--color-text-secondary)] leading-relaxed">
            The clinical narrative must be based on the actual medical record. AI may assist with phrasing, but may not invent diagnoses, mental status findings, mobility limitations, or clinical facts not present in the record.
          </p>
        </div>
      </div>
    </div>
  );
}

function Step5({ d, set }: { d: RequestDraft; set: (_f: keyof RequestDraft, _v: unknown) => void }) {
  const mnResult = evaluateMNStatus(d);

  const MN_STATUS_STYLES: Record<string, { bg: string; border: string; text: string; icon: React.ElementType }> = {
    MEDICAL_NECESSITY_SUPPORTED:        { bg: 'bg-status-active/[0.05]',  border: 'border-status-active/20',  text: 'text-[var(--color-status-active)]',  icon: CheckCircle2 },
    WISCONSIN_MEDICAID_SUPPORT_PRESENT: { bg: 'bg-status-active/[0.05]',  border: 'border-status-active/20',  text: 'text-[var(--color-status-active)]',  icon: CheckCircle2 },
    MEDICAL_NECESSITY_INSUFFICIENT:     { bg: 'bg-status-warning/[0.05]', border: 'border-status-warning/20', text: 'text-status-warning', icon: AlertTriangle },
    LIKELY_NOT_MEDICALLY_NECESSARY:     { bg: 'bg-red/[0.05]',            border: 'border-red/20',            text: 'text-red',            icon: XCircle },
    LEVEL_OF_CARE_NOT_SUPPORTED:        { bg: 'bg-red/[0.05]',            border: 'border-red/20',            text: 'text-red',            icon: XCircle },
    ABN_REVIEW_REQUIRED:                { bg: 'bg-status-warning/[0.05]', border: 'border-status-warning/20', text: 'text-status-warning', icon: AlertTriangle },
    HUMAN_REVIEW_REQUIRED:              { bg: 'bg-status-info/[0.05]',    border: 'border-status-info/20',    text: 'text-status-info',    icon: Info },
    WISCONSIN_MEDICAID_SUPPORT_MISSING: { bg: 'bg-status-warning/[0.05]', border: 'border-status-warning/20', text: 'text-status-warning', icon: AlertTriangle },
  };

  const style = mnResult.status ? MN_STATUS_STYLES[mnResult.status] : null;
  const MNIcon = style?.icon ?? Info;

  return (
    <div className="space-y-5">
      <div className="p-3 border border-white/[0.06] bg-[var(--color-bg-base)]/[0.02]" style={CLIP}>
        <div className="text-[9px] font-black uppercase tracking-widest text-[var(--color-text-muted)] mb-2">
          Select all applicable transport justifications
        </div>
        <div className="space-y-2">
          <CheckRow label="Patient cannot ambulate safely (unable to walk)" value={d.mn_reason_cannot_walk} onChange={(v) => set('mn_reason_cannot_walk', v)} />
          <CheckRow label="Wheelchair van is not appropriate for this patient" value={d.mn_reason_wheelchair_insufficient} onChange={(v) => set('mn_reason_wheelchair_insufficient', v)} />
          <CheckRow label="Supine transport is required (cannot safely sit upright)" value={d.mn_reason_supine_required} onChange={(v) => set('mn_reason_supine_required', v)} />
          <CheckRow label="Cardiac monitoring required during transport" value={d.mn_reason_monitoring} onChange={(v) => set('mn_reason_monitoring', v)} />
          <CheckRow label="Supplemental oxygen required during transport" value={d.mn_reason_oxygen} onChange={(v) => set('mn_reason_oxygen', v)} />
          <CheckRow label="IV infusion / medication administration required during transport" value={d.mn_reason_infusion} onChange={(v) => set('mn_reason_infusion', v)} />
          <CheckRow label="Ventilator management required during transport" value={d.mn_reason_vent} onChange={(v) => set('mn_reason_vent', v)} />
          <div className="border-t border-white/[0.06] pt-2 mt-1">
            <div className="text-[9px] text-[var(--color-text-muted)] mb-2 uppercase tracking-widest font-bold">
              Behavioral / cognitive factors (not stand-alone justifications)
            </div>
            <CheckRow
              label="Dementia / cognitive impairment"
              value={d.mn_reason_dementia}
              onChange={(v) => set('mn_reason_dementia', v)}
              warning="Dementia alone does not establish ambulance medical necessity. Must be combined with other clinical justifications."
            />
            <CheckRow
              label="Altered mental status"
              value={d.mn_reason_altered_ms}
              onChange={(v) => set('mn_reason_altered_ms', v)}
              warning="Altered mental status alone does not establish ambulance medical necessity."
            />
            <CheckRow
              label="Fall risk"
              value={d.mn_reason_fall_risk}
              onChange={(v) => set('mn_reason_fall_risk', v)}
              warning="Fall risk alone does not establish ambulance medical necessity."
            />
          </div>
        </div>
      </div>

      <FL label="Why can't this patient be transported by private vehicle?" req>
        <textarea value={d.mn_why_not_private_vehicle} onChange={(e) => set('mn_why_not_private_vehicle', e.target.value)}
          placeholder="Specific clinical explanation of why private vehicle or ride service would endanger the patient's health…"
          rows={3} className={TEXTAREA} style={CLIP} />
      </FL>

      <FL label="Why is a wheelchair van not appropriate (if applicable)?">
        <textarea value={d.mn_why_not_wheelchair} onChange={(e) => set('mn_why_not_wheelchair', e.target.value)}
          placeholder="Explain why a wheelchair-accessible van cannot safely accommodate the patient's condition…"
          rows={2} className={TEXTAREA} style={CLIP} />
      </FL>

      <FL label="Patient Condition Summary (for medical necessity)" req>
        <textarea value={d.mn_patient_condition_summary} onChange={(e) => set('mn_patient_condition_summary', e.target.value)}
          placeholder="Brief, fact-based summary of the patient's current clinical condition as it relates to transport necessity…"
          rows={3} className={TEXTAREA} style={CLIP} />
      </FL>

      {/* MN Status indicator */}
      {mnResult.status && style && (
        <div className={`p-3.5 border ${style.bg} ${style.border}`} style={CLIP}>
          <div className={`flex items-center gap-2 mb-1.5 ${style.text}`}>
            <MNIcon className="w-3.5 h-3.5 flex-shrink-0" />
            <span className="text-[10px] font-black uppercase tracking-widest">{mnResult.status.replace(/_/g, ' ')}</span>
          </div>
          <p className="text-[11px] text-[var(--color-text-secondary)] leading-relaxed">{mnResult.explanation}</p>
          {mnResult.policy && (
            <p className="text-[9px] text-[var(--color-text-muted)] mt-1.5 font-medium">Policy basis: {mnResult.policy}</p>
          )}
        </div>
      )}
    </div>
  );
}

function Step6({ d, set }: { d: RequestDraft; set: (_f: keyof RequestDraft, _v: unknown) => void }) {
  const mnResult = evaluateMNStatus(d);

  useEffect(() => {
    if (mnResult.status) {
      set('mn_status', mnResult.status);
      set('mn_explanation', mnResult.explanation);
      set('mn_policy_basis', mnResult.policy);
    }
  }, [mnResult.status, mnResult.explanation, mnResult.policy, set]);

  const levelOk = ['MEDICAL_NECESSITY_SUPPORTED', 'WISCONSIN_MEDICAID_SUPPORT_PRESENT'].includes(d.mn_status);

  const LOC_OPTIONS: { value: ServiceLevel; label: string; desc: string; requires: string }[] = [
    { value: 'BLS', label: 'BLS – Basic Life Support', desc: 'Non-emergency medical monitoring, positioning, basic interventions.', requires: 'Patient cannot be transported by other means; BLS crew competencies sufficient.' },
    { value: 'ALS', label: 'ALS – Advanced Life Support', desc: 'ALS-level monitoring, IV access, ALS interventions en route.', requires: 'Patient requires ALS assessment/intervention; condition warrants ALS provider.' },
    { value: 'ALS2', label: 'ALS2 – Advanced BLS Level 2', desc: 'ALS with 3+ drug administrations or advanced procedure.', requires: 'CMS ALS2 billing criteria must be met.' },
    { value: 'CCT', label: 'CCT – Critical Care Transport', desc: 'Critical care level monitoring and interventions during transport.', requires: 'Patient requires critical care team and equipment.' },
    { value: 'SCT', label: 'SCT – Specialty Care Transport', desc: 'Specialty team (RN, RT, etc.) accompanying for specialized care needs.', requires: 'Requires specialty care provider beyond standard ALS scope.' },
  ];

  return (
    <div className="space-y-5">
      {!levelOk && (
        <div className="p-3 border border-status-warning/25 bg-status-warning/[0.04]" style={CLIP}>
          <div className="flex items-start gap-2">
            <AlertTriangle className="w-3.5 h-3.5 text-status-warning flex-shrink-0 mt-0.5" />
            <div>
              <p className="text-[11px] font-bold text-status-warning">Medical Necessity Not Yet Established</p>
              <p className="text-[10px] text-[var(--color-text-secondary)] mt-0.5 leading-relaxed">
                {d.mn_explanation || 'Complete Step 5 (Medical Necessity) before selecting a level of care. Level of care must be supported by the clinical documentation.'}
              </p>
            </div>
          </div>
        </div>
      )}

      <div className="space-y-2">
        {LOC_OPTIONS.map((opt) => (
          <button
            key={opt.value}
            type="button"
            onClick={() => set('requested_service_level', opt.value)}
            className={`w-full text-left p-3 border transition-colors ${d.requested_service_level === opt.value ? 'border-orange/40 bg-[var(--q-orange)]/[0.06]' : 'border-white/[0.06] bg-[var(--color-bg-base)]/[0.02] hover:border-white/[0.12] hover:bg-[var(--color-bg-base)]/[0.04]'}`}
            style={{ clipPath: 'polygon(0 0, calc(100% - 6px) 0, 100% 6px, 100% 100%, 0 100%)' }}
          >
            <div className="flex items-center justify-between">
              <span className={`text-[11px] font-black ${d.requested_service_level === opt.value ? 'text-[var(--q-orange)]' : 'text-[var(--color-text-primary)]'}`}>{opt.label}</span>
              {d.requested_service_level === opt.value && <CheckCircle2 className="w-3.5 h-3.5 text-[var(--q-orange)]" />}
            </div>
            <p className="text-[10px] text-[var(--color-text-muted)] mt-0.5">{opt.desc}</p>
            <p className="text-[9px] text-[var(--color-text-muted)]/60 mt-0.5 italic">{opt.requires}</p>
          </button>
        ))}
      </div>

      {d.requested_service_level && !levelOk && (
        <div className="p-3 border border-red/25 bg-red/[0.04]" style={CLIP}>
          <div className="flex items-start gap-2">
            <XCircle className="w-3.5 h-3.5 text-red flex-shrink-0 mt-0.5" />
            <p className="text-[11px] text-red leading-relaxed">
              The requested level of care is not supported by the current medical necessity documentation.
              Correct the medical necessity information in Step 5 before final submission.
            </p>
          </div>
        </div>
      )}

      <FL label="Additional Level-of-Care Notes">
        <textarea value={d.mn_reason_other} onChange={(e) => set('mn_reason_other', e.target.value)}
          placeholder="Any additional context supporting the level-of-care selection…"
          rows={2} className={TEXTAREA} style={CLIP} />
      </FL>
    </div>
  );
}

function Step7({ d, set }: { d: RequestDraft; set: (_f: keyof RequestDraft, _v: unknown) => void }) {
  const toggle = (field: keyof RequestDraft) => set(field, !d[field]);

  return (
    <div className="space-y-5">
      <div className="p-3 border border-white/[0.06] bg-[var(--color-bg-base)]/[0.02]" style={CLIP}>
        <div className="text-[9px] font-black uppercase tracking-widest text-[var(--color-text-muted)] mb-3">Document Status</div>
        <div className="space-y-2">
          <CheckRow label="Physician Certification Statement (PCS) obtained" value={d.pcs_complete} onChange={() => toggle('pcs_complete')} />
          <CheckRow label="Authorization of Benefits (AOB) obtained" value={d.aob_complete} onChange={() => toggle('aob_complete')} />
          <CheckRow label="Patient facesheet uploaded" value={d.facesheet_uploaded} onChange={() => toggle('facesheet_uploaded')} />
          <CheckRow label="Physician order / transport order uploaded" value={d.physician_order_uploaded} onChange={() => toggle('physician_order_uploaded')} />
          <CheckRow label="Discharge paperwork uploaded" value={d.discharge_docs_uploaded} onChange={() => toggle('discharge_docs_uploaded')} />
        </div>
      </div>

      {/* Upload area (visual - actual upload uses signed URL flow) */}
      <div className="border-2 border-dashed border-white/[0.1] p-6 text-center" style={CLIP}>
        <div className="flex flex-col items-center gap-2">
          <Paperclip className="w-6 h-6 text-[var(--color-text-muted)]/40" />
          <p className="text-[11px] text-[var(--color-text-muted)]">
            Drag &amp; drop files here, or click to upload
          </p>
          <p className="text-[9px] text-[var(--color-text-muted)]/60">PDF, images, TIFF — max 50 MB per file</p>
          <p className="text-[9px] text-[var(--color-text-muted)]/40 mt-1">
            OCR extraction will be run on uploaded documents to pre-populate request fields.
          </p>
        </div>
      </div>

      <div className="p-3 bg-status-info/[0.04] border border-status-info/15" style={CLIP}>
        <div className="flex items-start gap-2">
          <Info className="w-3.5 h-3.5 text-status-info flex-shrink-0 mt-0.5" />
          <p className="text-[10px] text-[var(--color-text-secondary)] leading-relaxed">
            Uploaded documents will be scanned with OCR. Extracted data will be presented as suggestions — you must review and confirm before it overwrites any field.
            OCR suggestions will not auto-populate silently.
          </p>
        </div>
      </div>
    </div>
  );
}

function Step8({ d, set }: { d: RequestDraft; set: (_f: keyof RequestDraft, _v: unknown) => void }) {
  const toggle = (field: keyof RequestDraft) => set(field, !d[field]);
  const isMedicare = d.payer?.toLowerCase().includes('medicare') && !d.payer?.toLowerCase().includes('advantage');

  return (
    <div className="space-y-5">
      {/* Requestor attestation */}
      <div className="p-4 border border-orange/15 bg-[var(--q-orange)]/[0.03]" style={CLIP}>
        <div className="text-[9px] font-black uppercase tracking-widest text-[var(--q-orange)] mb-3">Requestor Attestation</div>
        <div className="text-[11px] text-[var(--color-text-secondary)] leading-relaxed mb-3">
          By checking below, I attest that:
          <ul className="mt-2 space-y-1 list-disc list-inside text-[10px]">
            <li>The information provided in this request is accurate to the best of my knowledge.</li>
            <li>The clinical information is supported by the available medical record.</li>
            <li>The attached records, if any, correspond to this patient and request.</li>
            <li>I understand that incomplete or unsupported information may delay scheduling, require review, or result in noncoverage or denial.</li>
          </ul>
        </div>
        <CheckRow label="I acknowledge and attest to the above statements" value={d.requestor_attested} onChange={() => toggle('requestor_attested')} />
      </div>

      {/* Form signatures */}
      <div className="p-3 border border-white/[0.06] bg-[var(--color-bg-base)]/[0.02]" style={CLIP}>
        <div className="text-[9px] font-black uppercase tracking-widest text-[var(--color-text-muted)] mb-3">Form Signatures</div>
        <div className="space-y-2">
          <CheckRow label="PCS has been signed by the authorizing provider" value={d.pcs_signed} onChange={() => toggle('pcs_signed')} />
          <CheckRow label="AOB has been signed by the patient or authorized representative" value={d.aob_signed} onChange={() => toggle('aob_signed')} />
        </div>
      </div>

      {/* ABN section — only shown for Original Medicare */}
      {isMedicare && (
        <div className="p-4 border border-status-warning/20 bg-status-warning/[0.03]" style={CLIP}>
          <div className="flex items-center gap-2 mb-3">
            <AlertTriangle className="w-3.5 h-3.5 text-status-warning" />
            <span className="text-[10px] font-black uppercase tracking-widest text-status-warning">ABN Review (Original Medicare)</span>
          </div>
          <p className="text-[10px] text-[var(--color-text-secondary)] leading-relaxed mb-3">
            An Advance Beneficiary Notice of Noncoverage (ABN) must be issued when the service is usually covered by Original Medicare but may be denied in this specific case because medical necessity may not be met.
            The ABN must be reviewed with the beneficiary or representative <strong className="text-white">before</strong> transport, not used as a substitute for missing documentation.
          </p>
          <div className="space-y-2 mb-3">
            <CheckRow label="ABN review is required for this transport" value={d.abn_needed} onChange={() => toggle('abn_needed')} />
          </div>
          {d.abn_needed && (
            <div className="space-y-3 pl-4 border-l border-status-warning/20">
              <CheckRow label="ABN has been reviewed with the beneficiary or representative" value={d.abn_reviewed} onChange={() => toggle('abn_reviewed')} />
              <CheckRow label="ABN has been presented (provided to the beneficiary)" value={d.abn_presented} onChange={() => toggle('abn_presented')} />
              <CheckRow label="ABN has been signed by the beneficiary or authorized representative" value={d.abn_signed} onChange={() => toggle('abn_signed')} />
              {d.abn_signed && (
                <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                  <FL label="Signer Name">
                    <input type="text" value={d.abn_signer_name} onChange={(e) => set('abn_signer_name', e.target.value)}
                      placeholder="Full name of signer" className={INPUT} style={CLIP} />
                  </FL>
                  <FL label="Signer Relationship to Patient">
                    <input type="text" value={d.abn_signer_relationship} onChange={(e) => set('abn_signer_relationship', e.target.value)}
                      placeholder="Self, POA, Legal Guardian, etc." className={INPUT} style={CLIP} />
                  </FL>
                </div>
              )}
            </div>
          )}
        </div>
      )}
    </div>
  );
}

function Step9({ d }: { d: RequestDraft }) {
  const mnResult = evaluateMNStatus(d);
  const readiness = computeReadiness(d);
  const ready = isReadyForCad(readiness);

  const sections = [
    {
      label: 'Request Basics',
      fields: [
        { k: 'Priority', v: d.priority },
        { k: 'Pickup Time', v: d.requested_pickup_time },
        { k: 'Requestor', v: `${d.requestor_name} — ${d.requestor_title}` },
        { k: 'Department', v: d.facility_department },
      ],
    },
    {
      label: 'Patient Identity',
      fields: [
        { k: 'Patient', v: `${d.patient_first} ${d.patient_last}` },
        { k: 'DOB', v: d.patient_dob },
        { k: 'MRN', v: d.mrn },
        { k: 'CSN', v: d.csn },
        { k: 'Payer', v: d.payer },
      ],
    },
    {
      label: 'Transport',
      fields: [
        { k: 'Origin', v: `${d.origin_facility} — ${d.origin_address}` },
        { k: 'Destination', v: `${d.destination_facility} — ${d.destination_address}` },
        { k: 'Level of Care', v: d.requested_service_level },
      ],
    },
    {
      label: 'Medical Necessity',
      fields: [
        { k: 'MN Status', v: d.mn_status?.replace(/_/g, ' ') },
        { k: 'Explanation', v: d.mn_explanation },
        { k: 'Policy Basis', v: d.mn_policy_basis },
      ],
    },
  ];

  return (
    <div className="space-y-4">
      {!ready && (
        <div className="p-3 border border-red/25 bg-red/[0.04]" style={CLIP}>
          <div className="flex items-start gap-2">
            <XCircle className="w-3.5 h-3.5 text-red flex-shrink-0 mt-0.5" />
            <div>
              <p className="text-[11px] font-bold text-red">Request is not ready for CAD submission</p>
              <div className="mt-1.5 space-y-0.5">
                {readiness.filter((r) => !r.complete || r.warning).map((r) => (
                  <div key={r.label} className="flex items-center gap-1.5 text-[10px] text-[var(--color-text-muted)]">
                    {r.warning ? <AlertTriangle className="w-2.5 h-2.5 text-status-warning flex-shrink-0" /> : <Circle className="w-2.5 h-2.5 text-[var(--color-text-muted)]/30 flex-shrink-0" />}
                    {r.label}
                  </div>
                ))}
              </div>
            </div>
          </div>
        </div>
      )}

      {sections.map((sec) => (
        <div key={sec.label} className="border border-white/[0.06] bg-[#0D0D0F]" style={{ clipPath: 'polygon(0 0, calc(100% - 8px) 0, 100% 8px, 100% 100%, 0 100%)' }}>
          <div className="px-4 py-2 border-b border-white/[0.04] bg-[var(--color-bg-base)]/[0.02]">
            <span className="text-[9px] font-black uppercase tracking-widest text-[var(--q-orange)]">{sec.label}</span>
          </div>
          <div className="p-4 space-y-2">
            {sec.fields.map(({ k, v }) => v ? (
              <div key={k} className="flex gap-3">
                <span className="text-[10px] text-[var(--color-text-muted)] w-36 flex-shrink-0">{k}</span>
                <span className="text-[11px] text-[var(--color-text-primary)]">{v}</span>
              </div>
            ) : null)}
          </div>
        </div>
      ))}

      {mnResult.status && (
        <div className={`p-3.5 border ${
          ['MEDICAL_NECESSITY_SUPPORTED', 'WISCONSIN_MEDICAID_SUPPORT_PRESENT'].includes(mnResult.status)
            ? 'border-status-active/20 bg-status-active/[0.04]'
            : 'border-status-warning/20 bg-status-warning/[0.04]'
        }`} style={CLIP}>
          <div className="text-[9px] font-black uppercase tracking-widest text-[var(--color-text-muted)] mb-1">Medical Necessity Engine Assessment</div>
          <p className="text-[11px] text-[var(--color-text-secondary)]">{mnResult.explanation}</p>
        </div>
      )}
    </div>
  );
}

// ─────────────────────────────────────────────────────────────
// Main Wizard
// ─────────────────────────────────────────────────────────────

function NewRequestWizardInner() {
  const router = useRouter();
  const [step, setStep] = useState(1);
  const [draft, setDraft] = useState<RequestDraft>(EMPTY_DRAFT);
  const [submitting, setSubmitting] = useState(false);
  const [submitError, setSubmitError] = useState('');

  const set = useCallback((field: keyof RequestDraft, value: unknown) => {
    setDraft((d) => ({ ...d, [field]: value }));
  }, []);

  const readiness = computeReadiness(draft);
  const ready = isReadyForCad(readiness);

  const mnResult = evaluateMNStatus(draft);

  // Sync MN evaluation into draft on step 6 visit
  useEffect(() => {
    if (step >= 5 && mnResult.status) {
      setDraft((d) => ({
        ...d,
        mn_status: mnResult.status,
        mn_explanation: mnResult.explanation,
        mn_policy_basis: mnResult.policy,
      }));
    }
  }, [step, mnResult.status, mnResult.explanation, mnResult.policy]);

  const handleSubmit = useCallback(async () => {
    if (!ready) return;
    setSubmitting(true);
    setSubmitError('');
    try {
      // Create draft
      const created = await createTransportLinkRequest({
        ...draft,
        status: 'submitted',
        patient_name: `${draft.patient_first} ${draft.patient_last}`,
      });
      const reqId = created.id || (typeof created.data.id === 'string' ? created.data.id : '');

      if (reqId) {
        // Auto-submit to CAD
        await submitTransportLinkToCad(reqId, 1);
        router.push(`/transportlink/requests/${reqId}`);
      } else {
        router.push('/transportlink/requests');
      }
    } catch (err) {
      setSubmitError(err instanceof Error ? err.message : 'Failed to submit request. Please try again.');
      setSubmitting(false);
    }
  }, [draft, ready, router]);

  const StepComponent = [Step1, Step2, Step3, Step4, Step5, Step6, Step7, Step8, Step9][step - 1];

  return (
    <div className="p-5 max-w-7xl mx-auto">
      {/* Header */}
      <div className="mb-5">
        <div className="text-[9px] font-bold tracking-[0.3em] text-[var(--q-orange)] uppercase mb-1">TransportLink · New Request</div>
        <h1 className="text-h1 font-black text-white">Transport Request Wizard</h1>
        <p className="text-[11px] text-[var(--color-text-muted)] mt-1">CMS-aware · Wisconsin-first · Medical necessity enforced · No incomplete submissions</p>
      </div>

      {/* Step tabs */}
      <div className="flex items-center gap-1 mb-5 overflow-x-auto pb-1">
        {STEPS.map(({ id, label, icon: Icon }) => {
          const past = id < step;
          const active = id === step;
          return (
            <button
              key={id}
              type="button"
              onClick={() => setStep(id)}
              className={`flex items-center gap-1.5 px-3 py-2 text-[10px] font-bold uppercase tracking-wider flex-shrink-0 transition-colors border
                ${active ? 'text-white bg-[var(--q-orange)]/15 border-orange/30' : past ? 'text-[var(--color-status-active)] bg-status-active/[0.06] border-status-active/20 hover:bg-status-active/10' : 'text-[var(--color-text-muted)] bg-[var(--color-bg-base)]/[0.02] border-white/[0.06] hover:text-[var(--color-text-primary)] hover:bg-[var(--color-bg-base)]/[0.04]'}`}
              style={{ clipPath: 'polygon(0 0, calc(100% - 5px) 0, 100% 5px, 100% 100%, 0 100%)' }}
            >
              {past ? <CheckCircle2 className="w-3 h-3" /> : <Icon className="w-3 h-3" />}
              <span className="hidden md:inline">{label}</span>
              <span className="md:hidden">{id}</span>
            </button>
          );
        })}
      </div>

      {/* Main content + side panel */}
      <div className="flex gap-4 items-start">
        <div
          className="flex-1 min-w-0 border border-white/[0.06] bg-[#0D0D0F] overflow-hidden"
          style={{ clipPath: 'polygon(0 0, calc(100% - 12px) 0, 100% 12px, 100% 100%, 12px 100%, 0 calc(100% - 12px))' }}
        >
          {/* Step header */}
          <div className="px-5 py-4 border-b border-white/[0.05] bg-gradient-to-r from-orange/[0.05]">
            <div className="flex items-center gap-2">
              {React.createElement(STEPS[step - 1].icon, { className: 'w-4 h-4 text-[var(--q-orange)]' })}
              <span className="text-[11px] font-black uppercase tracking-wider text-[var(--q-orange)]">
                Step {step} of {STEPS.length} — {STEPS[step - 1].label}
              </span>
            </div>
          </div>

          <div className="p-5">
            {step < 10 && StepComponent && (
              <StepComponent d={draft} set={set} />
            )}

            {step === 10 && (
              <div className="space-y-5">
                <Step9 d={draft} />
                {submitError && (
                  <div className="p-3 border border-red/25 bg-red/[0.05]" style={CLIP}>
                    <div className="flex items-start gap-2">
                      <AlertCircle className="w-3.5 h-3.5 text-red flex-shrink-0 mt-0.5" />
                      <span className="text-[11px] text-red">{submitError}</span>
                    </div>
                  </div>
                )}
                <button
                  type="button"
                  onClick={handleSubmit}
                  disabled={!ready || submitting}
                  className="w-full h-12 text-[11px] font-black uppercase tracking-widest text-white transition-colors flex items-center justify-center gap-2 disabled:opacity-40 disabled:cursor-not-allowed"
                  style={{
                    background: ready ? 'linear-gradient(90deg, #FF4500, #FF7300)' : 'rgba(255,255,255,0.1)',
                    clipPath: 'polygon(0 0, calc(100% - 8px) 0, 100% 8px, 100% 100%, 8px 100%, 0 calc(100% - 8px))',
                  }}
                >
                  {submitting ? (
                    <><Loader2 className="w-4 h-4 animate-spin" /> Submitting to CAD…</>
                  ) : (
                    <><Send className="w-4 h-4" /> Submit to CAD</>
                  )}
                </button>
                {!ready && (
                  <p className="text-[10px] text-red text-center">
                    Complete all required items in the readiness panel before submission.
                  </p>
                )}
              </div>
            )}
          </div>

          {/* Nav buttons */}
          <div className="px-5 py-4 border-t border-white/[0.05] flex items-center justify-between">
            <button
              type="button"
              onClick={() => setStep((s) => Math.max(1, s - 1))}
              disabled={step === 1}
              className="flex items-center gap-1.5 h-9 px-4 text-[10px] font-bold uppercase tracking-wider border border-white/[0.08] text-[var(--color-text-muted)] hover:text-[var(--color-text-primary)] hover:border-white/[0.14] disabled:opacity-30 disabled:cursor-not-allowed transition-colors"
              style={{ clipPath: 'polygon(0 0, calc(100% - 5px) 0, 100% 5px, 100% 100%, 0 100%)' }}
            >
              <ChevronLeft className="w-3.5 h-3.5" />
              Back
            </button>
            {step < STEPS.length && (
              <button
                type="button"
                onClick={() => setStep((s) => Math.min(STEPS.length, s + 1))}
                className="flex items-center gap-1.5 h-9 px-4 text-[10px] font-black uppercase tracking-wider bg-[var(--q-orange)] hover:bg-[#FF6A1A] text-white transition-colors"
                style={{ clipPath: 'polygon(0 0, calc(100% - 5px) 0, 100% 5px, 100% 100%, 0 100%)' }}
              >
                Next
                <ChevronRight className="w-3.5 h-3.5" />
              </button>
            )}
          </div>
        </div>

        {/* Readiness panel */}
        <div className="hidden lg:block sticky top-4">
          <ReadinessPanel draft={draft} ready={ready} />
        </div>
      </div>
    </div>
  );
}

export default function NewRequestPage() {
  return (
    <Suspense fallback={null}>
      <NewRequestWizardInner />
    </Suspense>
  );
}
