'use client';

import React, { useState, useCallback } from 'react';
import Link from 'next/link';
import {
  Building2,
  User,
  Phone,
  Mail,
  MapPin,
  Layers,
  CheckCircle2,
  ChevronRight,
  AlertCircle,
  Shield,
  Truck,
  Loader2,
} from 'lucide-react';
import { submitTransportLinkAccessRequest } from '@/services/api';

const EHR_OPTIONS = [
  'Epic',
  'Cerner / Oracle Health',
  'MEDITECH',
  'Allscripts',
  'Athenahealth',
  'eClinicalWorks',
  'Other',
  'Unknown',
];

const USE_CASE_OPTIONS = [
  'Discharge transport scheduling',
  'ED / ED-to-SNF transports',
  'Interfacility transfers',
  'Dialysis transports',
  'Bariatric / specialty transports',
  'Case management coordination',
  'Billing / back-end reconciliation',
  'Other',
];

type FormState = {
  facility_name: string;
  department: string;
  requestor_name: string;
  title: string;
  work_email: string;
  callback_number: string;
  facility_address: string;
  ehr_platform: string;
  expected_volume: string;
  use_case: string;
  notes: string;
};

function Field({
  label,
  required,
  children,
}: {
  label: string;
  required?: boolean;
  children: React.ReactNode;
}) {
  return (
    <div className="space-y-1.5">
      <label className="text-[10px] font-bold uppercase tracking-widest text-[var(--color-text-muted)] flex items-center gap-1">
        {label}
        {required && <span className="text-red text-[9px]">*</span>}
      </label>
      {children}
    </div>
  );
}

const INPUT_CLASS =
  'w-full h-10 px-3 bg-[var(--color-bg-base)]/[0.04] border border-white/[0.08] focus:border-orange/40 focus:outline-none text-[12px] text-white placeholder:text-[var(--color-text-muted)] transition-colors';
const CLIP = { clipPath: 'polygon(0 0, calc(100% - 5px) 0, 100% 5px, 100% 100%, 0 100%)' };

export default function RequestAccessPage() {
  const [form, setForm] = useState<FormState>({
    facility_name: '',
    department: '',
    requestor_name: '',
    title: '',
    work_email: '',
    callback_number: '',
    facility_address: '',
    ehr_platform: '',
    expected_volume: '',
    use_case: '',
    notes: '',
  });
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [submitted, setSubmitted] = useState(false);

  const set = useCallback((field: keyof FormState, value: string) => {
    setForm((f) => ({ ...f, [field]: value }));
  }, []);

  const handleSubmit = useCallback(
    async (e: React.FormEvent) => {
      e.preventDefault();
      if (!form.facility_name.trim()) { setError('Facility name is required.'); return; }
      if (!form.requestor_name.trim()) { setError('Requestor name is required.'); return; }
      if (!form.work_email.trim()) { setError('Work email is required.'); return; }
      setError('');
      setLoading(true);
      try {
        await submitTransportLinkAccessRequest({ ...form });
        setSubmitted(true);
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Network error. Please try again.');
        setLoading(false);
      }
    },
    [form]
  );

  if (submitted) {
    return (
      <div className="min-h-screen bg-[#0A0A0C] flex items-center justify-center px-4">
        <div
          className="w-full max-w-lg border border-status-active/25 bg-status-active/[0.03] p-8 text-center"
          style={{ clipPath: 'polygon(0 0, calc(100% - 14px) 0, 100% 14px, 100% 100%, 14px 100%, 0 calc(100% - 14px))' }}
        >
          <CheckCircle2 className="w-12 h-12 text-[var(--color-status-active)] mx-auto mb-4" />
          <h1 className="text-h2 font-black text-white mb-2">Access Request Received</h1>
          <p className="text-body text-[var(--color-text-muted)] mb-6">
            Your facility access request has been submitted for review. You will receive an email at{' '}
            <strong className="text-white">{form.work_email}</strong> when your request has been reviewed.
            Typical review time is 1–2 business days.
          </p>
          <div className="flex flex-col sm:flex-row gap-3 justify-center">
            <Link
              href="/transportlink/login"
              className="h-10 px-5 text-[11px] font-black uppercase tracking-widest text-white bg-[var(--q-orange)] hover:bg-[#FF6A1A] transition-colors flex items-center justify-center gap-2"
              style={CLIP}
            >
              Back to Login <ChevronRight className="w-3.5 h-3.5" />
            </Link>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-[#0A0A0C] px-4 py-10">
      <div
        className="absolute inset-0 pointer-events-none opacity-[0.02]"
        style={{
          backgroundImage: 'linear-gradient(rgba(255,115,26,0.8) 1px,transparent 1px),linear-gradient(90deg,rgba(255,115,26,0.8) 1px,transparent 1px)',
          backgroundSize: '40px 40px',
        }}
      />

      <div className="relative max-w-2xl mx-auto">
        {/* Header */}
        <div className="flex flex-col items-center mb-8">
          <div
            className="w-12 h-12 flex items-center justify-center mb-3"
            style={{
              background: 'linear-gradient(135deg, #FF4500 0%, #FF7300 60%, #FFB800 100%)',
              clipPath: 'polygon(0 0, calc(100% - 8px) 0, 100% 8px, 100% 100%, 8px 100%, 0 calc(100% - 8px))',
            }}
          >
            <Truck className="w-5 h-5 text-white" strokeWidth={2.5} />
          </div>
          <div className="text-[12px] font-black tracking-[0.22em] text-white uppercase">TransportLink</div>
          <div className="text-[9px] tracking-[0.35em] text-[var(--q-orange)] uppercase font-medium mt-0.5">Facility Access Request</div>
        </div>

        <div
          className="border border-white/[0.07] bg-[#0E0E10] overflow-hidden"
          style={{ clipPath: 'polygon(0 0, calc(100% - 14px) 0, 100% 14px, 100% 100%, 14px 100%, 0 calc(100% - 14px))' }}
        >
          <div className="relative p-6 border-b border-white/[0.05] bg-gradient-to-r from-orange/[0.05]">
            <div className="text-[9px] font-bold tracking-[0.25em] text-[var(--q-orange)] uppercase mb-1">Facility Onboarding</div>
            <h1 className="text-h2 font-black text-white">Request Portal Access</h1>
            <p className="text-[11px] text-[var(--color-text-muted)] mt-1 max-w-lg">
              Complete this form to request access to the TransportLink facility portal.
              Your request will be reviewed and you will be notified once approved.
            </p>
          </div>

          <form onSubmit={handleSubmit} className="p-6 space-y-5">
            {error && (
              <div
                className="flex items-start gap-2 p-3 border border-red/25 bg-red/[0.06]"
                style={CLIP}
              >
                <AlertCircle className="w-3.5 h-3.5 text-red flex-shrink-0 mt-0.5" />
                <span className="text-[11px] text-red">{error}</span>
              </div>
            )}

            {/* Facility Info */}
            <div>
              <div className="flex items-center gap-2 mb-3">
                <Building2 className="w-3.5 h-3.5 text-[var(--q-orange)]" />
                <span className="text-[10px] font-black uppercase tracking-widest text-[var(--q-orange)]">Facility Information</span>
              </div>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <Field label="Facility Name" required>
                  <input type="text" value={form.facility_name} onChange={(e) => set('facility_name', e.target.value)}
                    placeholder="Mercy Medical Center" className={INPUT_CLASS} style={CLIP} />
                </Field>
                <Field label="Department / Unit">
                  <input type="text" value={form.department} onChange={(e) => set('department', e.target.value)}
                    placeholder="Case Management, ED, etc." className={INPUT_CLASS} style={CLIP} />
                </Field>
                <Field label="Facility Address">
                  <div className="relative">
                    <MapPin className="absolute left-2.5 top-1/2 -translate-y-1/2 w-3.5 h-3.5 text-[var(--color-text-muted)] pointer-events-none" />
                    <input type="text" value={form.facility_address} onChange={(e) => set('facility_address', e.target.value)}
                      placeholder="1000 Main St, Milwaukee, WI" className={`${INPUT_CLASS} pl-8`} style={CLIP} />
                  </div>
                </Field>
                <Field label="EHR Platform">
                  <select value={form.ehr_platform} onChange={(e) => set('ehr_platform', e.target.value)}
                    className={`${INPUT_CLASS} appearance-none`} style={CLIP}>
                    <option value="">Select EHR (optional)</option>
                    {EHR_OPTIONS.map((o) => <option key={o} value={o}>{o}</option>)}
                  </select>
                </Field>
              </div>
            </div>

            {/* Requestor Info */}
            <div>
              <div className="flex items-center gap-2 mb-3">
                <User className="w-3.5 h-3.5 text-[var(--q-orange)]" />
                <span className="text-[10px] font-black uppercase tracking-widest text-[var(--q-orange)]">Requestor Information</span>
              </div>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <Field label="Full Name" required>
                  <input type="text" value={form.requestor_name} onChange={(e) => set('requestor_name', e.target.value)}
                    placeholder="Jane Smith" className={INPUT_CLASS} style={CLIP} />
                </Field>
                <Field label="Title / Role">
                  <input type="text" value={form.title} onChange={(e) => set('title', e.target.value)}
                    placeholder="Discharge Planner, Case Manager, etc." className={INPUT_CLASS} style={CLIP} />
                </Field>
                <Field label="Work Email" required>
                  <div className="relative">
                    <Mail className="absolute left-2.5 top-1/2 -translate-y-1/2 w-3.5 h-3.5 text-[var(--color-text-muted)] pointer-events-none" />
                    <input type="email" value={form.work_email} onChange={(e) => set('work_email', e.target.value)}
                      placeholder="jane.smith@facility.org" className={`${INPUT_CLASS} pl-8`} style={CLIP} />
                  </div>
                </Field>
                <Field label="Callback Number">
                  <div className="relative">
                    <Phone className="absolute left-2.5 top-1/2 -translate-y-1/2 w-3.5 h-3.5 text-[var(--color-text-muted)] pointer-events-none" />
                    <input type="tel" value={form.callback_number} onChange={(e) => set('callback_number', e.target.value)}
                      placeholder="414-555-0100" className={`${INPUT_CLASS} pl-8`} style={CLIP} />
                  </div>
                </Field>
              </div>
            </div>

            {/* Use Case */}
            <div>
              <div className="flex items-center gap-2 mb-3">
                <Layers className="w-3.5 h-3.5 text-[var(--q-orange)]" />
                <span className="text-[10px] font-black uppercase tracking-widest text-[var(--q-orange)]">Volume &amp; Use Case</span>
              </div>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <Field label="Expected Monthly Transport Volume">
                  <select value={form.expected_volume} onChange={(e) => set('expected_volume', e.target.value)}
                    className={`${INPUT_CLASS} appearance-none`} style={CLIP}>
                    <option value="">Select range</option>
                    <option value="1-10">1–10 / month</option>
                    <option value="11-50">11–50 / month</option>
                    <option value="51-100">51–100 / month</option>
                    <option value="100+">100+ / month</option>
                  </select>
                </Field>
                <Field label="Primary Use Case">
                  <select value={form.use_case} onChange={(e) => set('use_case', e.target.value)}
                    className={`${INPUT_CLASS} appearance-none`} style={CLIP}>
                    <option value="">Select primary use</option>
                    {USE_CASE_OPTIONS.map((o) => <option key={o} value={o}>{o}</option>)}
                  </select>
                </Field>
              </div>
            </div>

            {/* Notes */}
            <Field label="Additional Notes / Approval Context">
              <textarea value={form.notes} onChange={(e) => set('notes', e.target.value)}
                placeholder="Anything that will help us review your request quickly…"
                rows={3}
                className="w-full px-3 py-2 bg-[var(--color-bg-base)]/[0.04] border border-white/[0.08] focus:border-orange/40 focus:outline-none text-[12px] text-white placeholder:text-[var(--color-text-muted)] transition-colors resize-none"
                style={CLIP}
              />
            </Field>

            {/* Consent notice */}
            <div className="flex items-start gap-2 p-3 bg-[var(--color-bg-base)]/[0.02] border border-white/[0.05]"
              style={CLIP}>
              <Shield className="w-3.5 h-3.5 text-[var(--color-text-muted)] flex-shrink-0 mt-0.5" />
              <p className="text-[10px] text-[var(--color-text-muted)] leading-relaxed">
                Information provided in this form is used solely to evaluate and process your portal access request.
                Approved users will receive role-based access consistent with their stated use case and facility.
              </p>
            </div>

            <div className="flex flex-col sm:flex-row gap-3 pt-2">
              <Link href="/transportlink/login"
                className="h-10 px-5 text-[11px] font-semibold uppercase tracking-wider text-[var(--color-text-muted)] border border-white/[0.08] hover:text-[var(--color-text-primary)] hover:border-white/[0.14] transition-colors flex items-center justify-center"
                style={CLIP}>
                Back to Login
              </Link>
              <button type="submit" disabled={loading}
                className="flex-1 h-10 bg-[var(--q-orange)] hover:bg-[#FF6A1A] disabled:opacity-50 disabled:cursor-not-allowed text-white text-[11px] font-black uppercase tracking-widest transition-colors flex items-center justify-center gap-2"
                style={CLIP}>
                {loading ? (
                  <><Loader2 className="w-3.5 h-3.5 animate-spin" /> Submitting…</>
                ) : (
                  <>Submit Access Request <ChevronRight className="w-3.5 h-3.5" /></>
                )}
              </button>
            </div>
          </form>
        </div>
      </div>
    </div>
  );
}
