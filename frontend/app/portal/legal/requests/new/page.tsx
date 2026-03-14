'use client';

import { useMemo, useState } from 'react';
import AccessShell from '@/components/shells/AccessShell';
import { Input, Textarea } from '@/components/ui/Input';
import { StatusChip } from '@/components/ui/StatusChip';
import {
  classifyLegalRequest,
  completeLegalUpload,
  createLegalPaymentCheckout,
  createLegalRequestIntake,
  createLegalUploadPresign,
  type LegalChecklistItem,
  type LegalIntakePayload,
  type LegalIntakeResponse,
  type LegalPricingQuoteResponse,
  previewLegalPricingQuote,
  uploadLegalDocumentToPresignedUrl,
} from '@/services/api';

type RequestTypeOption = 'hipaa_roi' | 'subpoena' | 'court_order';

const REQUEST_TYPE_LABELS: Record<RequestTypeOption, string> = {
  hipaa_roi: 'HIPAA ROI',
  subpoena: 'Subpoena',
  court_order: 'Court Order',
};

const DOCUMENT_KIND_OPTIONS = [
  'authorization',
  'identity_proof',
  'subpoena',
  'court_order',
  'service_proof',
  'jurisdiction_details',
  'other',
];

const REQUESTER_CATEGORY_OPTIONS = [
  'patient',
  'patient_representative',
  'attorney',
  'insurance',
  'government_agency',
  'employer',
  'other_third_party_manual_review',
] as const;

function checklistLabel(item: LegalChecklistItem): string {
  return `${item.label} (${item.code})`;
}

export default function PublicLegalRequestIntakePage() {
  const [form, setForm] = useState<LegalIntakePayload>({
    request_type: 'hipaa_roi',
    requesting_party: '',
    requester_name: '',
    requesting_entity: '',
    requester_category: 'other_third_party_manual_review',
    patient_first_name: '',
    patient_last_name: '',
    patient_dob: '',
    mrn: '',
    csn: '',
    date_range_start: '',
    date_range_end: '',
    request_documents: [],
    requested_page_count: 0,
    jurisdiction_state: 'WI',
    print_mail_requested: false,
    rush_requested: false,
    delivery_preference: 'secure_one_time_link',
    deadline_at: '',
    notes: '',
  });
  const [submitting, setSubmitting] = useState(false);
  const [classifying, setClassifying] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);
  const [intake, setIntake] = useState<LegalIntakeResponse | null>(null);
  const [uploadKind, setUploadKind] = useState('authorization');
  const [uploading, setUploading] = useState(false);
  const [uploadFile, setUploadFile] = useState<File | null>(null);
  const [quote, setQuote] = useState<LegalPricingQuoteResponse | null>(null);
  const [quoteLoading, setQuoteLoading] = useState(false);
  const [checkoutLoading, setCheckoutLoading] = useState(false);

  const submitReady = useMemo(() => {
    return Boolean(form.requesting_party && form.requester_name);
  }, [form.requesting_party, form.requester_name]);

  const handleClassify = async () => {
    setClassifying(true);
    setError(null);
    setNotice(null);
    try {
      const res = await classifyLegalRequest({
        request_type: form.request_type,
        notes: form.notes,
        request_documents: form.request_documents,
        deadline_at: form.deadline_at || undefined,
        date_range_start: form.date_range_start || undefined,
        date_range_end: form.date_range_end || undefined,
      });
      setNotice(
        `Classification: ${res?.triage_summary?.classification || form.request_type} · ` +
        `urgency: ${res?.triage_summary?.urgency_level || 'normal'}`
      );
    } catch {
      setError('Unable to classify request right now. You can still submit intake.');
    } finally {
      setClassifying(false);
    }
  };

  const handleSubmit = async () => {
    if (!submitReady) {
      setError('Requesting party and requester name are required.');
      return;
    }
    setSubmitting(true);
    setError(null);
    setNotice(null);
    try {
      const payload: LegalIntakePayload = {
        ...form,
        request_documents: form.request_documents || [],
        patient_dob: form.patient_dob || undefined,
        date_range_start: form.date_range_start || undefined,
        date_range_end: form.date_range_end || undefined,
        deadline_at: form.deadline_at || undefined,
      };
      const created = await createLegalRequestIntake(payload);
      setIntake(created);
      setQuote(null);
      setNotice(`Intake submitted. Request ID: ${created.request_id}`);
    } catch {
      setError('Failed to submit legal request intake. Check required fields and retry.');
    } finally {
      setSubmitting(false);
    }
  };

  const handleQuote = async () => {
    if (!intake) {
      setError('Submit intake first before calculating pricing.');
      return;
    }
    const intakeToken = intake.intake_token?.trim();
    if (!intakeToken) {
      setError('Intake token missing. Please resubmit the intake request.');
      return;
    }
    setQuoteLoading(true);
    setError(null);
    setNotice(null);
    try {
      const priced = await previewLegalPricingQuote(intake.request_id, {
        intake_token: intakeToken,
        requested_page_count: Number(form.requested_page_count || 0),
        print_mail_requested: Boolean(form.print_mail_requested),
        rush_requested: Boolean(form.rush_requested),
      });
      setQuote(priced);
      setNotice(`Pricing updated. Total due: $${(priced.total_due_cents / 100).toFixed(2)}`);
    } catch {
      setError('Unable to calculate pricing right now. Please retry.');
    } finally {
      setQuoteLoading(false);
    }
  };

  const handleCheckout = async () => {
    if (!intake) {
      setError('Submit intake first before starting checkout.');
      return;
    }
    const intakeToken = intake.intake_token?.trim();
    if (!intakeToken) {
      setError('Intake token missing. Please resubmit the intake request.');
      return;
    }
    setCheckoutLoading(true);
    setError(null);
    setNotice(null);
    try {
      const checkout = await createLegalPaymentCheckout(intake.request_id, {
        intake_token: intakeToken,
      });
      const checkoutUrl = checkout.checkout_url?.trim();
      if (checkoutUrl) {
        let parsedUrl: URL;
        try {
          parsedUrl = new URL(checkoutUrl);
        } catch {
          throw new Error('Checkout returned an invalid URL.');
        }

        if (parsedUrl.protocol !== 'https:' && parsedUrl.protocol !== 'http:') {
          throw new Error('Checkout URL uses an unsupported protocol.');
        }

        window.location.assign(parsedUrl.toString());
        return;
      }
      setNotice('Checkout session created, but no redirect URL was provided.');
    } catch (err: unknown) {
      if (err instanceof Error && err.message) {
        setError(err.message);
      } else {
        setError('Unable to create checkout session. Please confirm quote and try again.');
      }
    } finally {
      setCheckoutLoading(false);
    }
  };

  const handleUpload = async () => {
    if (!intake || !uploadFile) {
      setError('Submit intake first, then choose a document to upload.');
      return;
    }
    const intakeToken = intake.intake_token?.trim();
    if (!intakeToken) {
      setError('Intake token missing. Please resubmit the intake request.');
      return;
    }
    setUploading(true);
    setError(null);
    setNotice(null);
    try {
      const presign = await createLegalUploadPresign(intake.request_id, {
        intake_token: intakeToken,
        document_kind: uploadKind,
        file_name: uploadFile.name,
        content_type: uploadFile.type || 'application/octet-stream',
      });

      if (presign.upload_url) {
        await uploadLegalDocumentToPresignedUrl(presign.upload_url, uploadFile);
      }

      const completed = await completeLegalUpload(intake.request_id, {
        intake_token: intakeToken,
        upload_id: presign.upload_id,
        byte_size: uploadFile.size,
      });

      setIntake((prev) => {
        if (!prev) return prev;
        return {
          ...prev,
          status: completed.status,
          triage_summary: completed.triage_summary,
          missing_items: completed.missing_items,
          required_document_checklist: completed.required_document_checklist,
        };
      });
      setUploadFile(null);
      setNotice('Document uploaded and checklist/triage refreshed.');
    } catch {
      setError('Document upload failed. Verify file and try again.');
    } finally {
      setUploading(false);
    }
  };

  return (
    <AccessShell
      title="Legal Request Intake"
      subtitle="Submit HIPAA ROI, subpoena, or court-order record requests with AI-assisted triage and deterministic document checks."
    >
      <div className="space-y-4">
        {error && <div className="border border-[var(--color-brand-red)]/40 bg-[var(--color-brand-red)]/10 p-3 text-sm text-[var(--color-brand-red)]">{error}</div>}
        {notice && <div className="border border-[var(--color-status-active)]/40 bg-[var(--color-status-active)]/10 p-3 text-sm text-[var(--color-status-active)]">{notice}</div>}

        <div className="grid gap-3 sm:grid-cols-2">
          <div>
            <label className="label-caps">Request Type</label>
            <select
              value={form.request_type}
              onChange={(event) => setForm((prev) => ({ ...prev, request_type: event.target.value as RequestTypeOption }))}
              className="mt-1 w-full border border-border-default bg-[var(--color-bg-base)] px-3 py-2 text-sm text-[var(--color-text-primary)]"
            >
              {Object.entries(REQUEST_TYPE_LABELS).map(([value, label]) => (
                <option key={value} value={value}>{label}</option>
              ))}
            </select>
          </div>
          <Input
            label="Requesting Party"
            value={form.requesting_party}
            onChange={(event) => setForm((prev) => ({ ...prev, requesting_party: event.target.value }))}
            placeholder="law_firm | court | patient | rep"
          />
          <Input
            label="Requester Name"
            value={form.requester_name}
            onChange={(event) => setForm((prev) => ({ ...prev, requester_name: event.target.value }))}
            placeholder="Full legal name"
          />
          <Input
            label="Law Firm / Court / Entity"
            value={form.requesting_entity}
            onChange={(event) => setForm((prev) => ({ ...prev, requesting_entity: event.target.value }))}
            placeholder="Optional"
          />
          <div>
            <label className="label-caps">Requester Category</label>
            <select
              value={form.requester_category}
              onChange={(event) =>
                setForm((prev) => ({
                  ...prev,
                  requester_category: event.target.value as LegalIntakePayload['requester_category'],
                }))
              }
              className="mt-1 w-full border border-border-default bg-[var(--color-bg-base)] px-3 py-2 text-sm text-[var(--color-text-primary)]"
            >
              {REQUESTER_CATEGORY_OPTIONS.map((value) => (
                <option key={value} value={value}>{value}</option>
              ))}
            </select>
          </div>
          <Input
            label="Patient First Name"
            value={form.patient_first_name}
            onChange={(event) => setForm((prev) => ({ ...prev, patient_first_name: event.target.value }))}
          />
          <Input
            label="Patient Last Name"
            value={form.patient_last_name}
            onChange={(event) => setForm((prev) => ({ ...prev, patient_last_name: event.target.value }))}
          />
          <Input
            label="Patient DOB"
            type="date"
            value={form.patient_dob}
            onChange={(event) => setForm((prev) => ({ ...prev, patient_dob: event.target.value }))}
          />
          <Input
            label="MRN"
            value={form.mrn}
            onChange={(event) => setForm((prev) => ({ ...prev, mrn: event.target.value }))}
          />
          <Input
            label="CSN"
            value={form.csn}
            onChange={(event) => setForm((prev) => ({ ...prev, csn: event.target.value }))}
          />
          <Input
            label="Date Range Start"
            type="date"
            value={form.date_range_start}
            onChange={(event) => setForm((prev) => ({ ...prev, date_range_start: event.target.value }))}
          />
          <Input
            label="Date Range End"
            type="date"
            value={form.date_range_end}
            onChange={(event) => setForm((prev) => ({ ...prev, date_range_end: event.target.value }))}
          />
          <Input
            label="Deadline"
            type="datetime-local"
            value={form.deadline_at}
            onChange={(event) => setForm((prev) => ({ ...prev, deadline_at: event.target.value }))}
          />
          <Input
            label="Estimated Page Count"
            type="number"
            value={form.requested_page_count != null ? String(form.requested_page_count) : ''}
            onChange={(event) => setForm((prev) => ({ ...prev, requested_page_count: Number(event.target.value || 0) }))}
          />
          <Input
            label="Jurisdiction State"
            value={form.jurisdiction_state}
            onChange={(event) => setForm((prev) => ({ ...prev, jurisdiction_state: event.target.value.toUpperCase() }))}
            placeholder="WI"
          />
          <div>
            <label className="label-caps">Delivery Preference</label>
            <select
              value={form.delivery_preference}
              onChange={(event) =>
                setForm((prev) => ({
                  ...prev,
                  delivery_preference: event.target.value as 'secure_one_time_link' | 'encrypted_email' | 'manual_pickup',
                }))
              }
              className="mt-1 w-full border border-border-default bg-[var(--color-bg-base)] px-3 py-2 text-sm text-[var(--color-text-primary)]"
            >
              <option value="secure_one_time_link">Secure one-time link</option>
              <option value="encrypted_email">Encrypted email</option>
              <option value="manual_pickup">Manual pickup</option>
            </select>
          </div>
          <label className="mt-6 inline-flex items-center gap-2 text-sm text-[var(--color-text-secondary)]">
            <input
              type="checkbox"
              checked={Boolean(form.print_mail_requested)}
              onChange={(event) => setForm((prev) => ({ ...prev, print_mail_requested: event.target.checked }))}
            />
            Print + mail request
          </label>
          <label className="mt-6 inline-flex items-center gap-2 text-sm text-[var(--color-text-secondary)]">
            <input
              type="checkbox"
              checked={Boolean(form.rush_requested)}
              onChange={(event) => setForm((prev) => ({ ...prev, rush_requested: event.target.checked }))}
            />
            Rush processing requested
          </label>
        </div>

        <Textarea
          label="Notes"
          rows={4}
          value={form.notes}
          onChange={(event) => setForm((prev) => ({ ...prev, notes: event.target.value }))}
          placeholder="Request context, legal basis summary, or supporting details"
        />

        <div className="flex flex-wrap gap-2">
          <button
            type="button"
            onClick={handleClassify}
            disabled={classifying}
            className="quantum-btn"
          >
            {classifying ? 'Classifying…' : 'AI Intake Triage'}
          </button>
          <button
            type="button"
            onClick={handleSubmit}
            disabled={submitting || !submitReady}
            className="quantum-btn-primary disabled:opacity-60"
          >
            {submitting ? 'Submitting…' : 'Submit Request Intake'}
          </button>
        </div>

        {intake && (
          <div className="space-y-3 border border-border-default bg-[var(--color-bg-base)] p-4">
            <div className="flex flex-wrap items-center gap-2">
              <StatusChip status="info">Request {intake.request_id.slice(0, 8)}</StatusChip>
              <StatusChip status={intake.status === 'missing_docs' ? 'warning' : 'active'}>{intake.status}</StatusChip>
              <StatusChip status={intake.triage_summary.deadline_risk === 'high' ? 'critical' : 'neutral'}>
                deadline risk: {intake.triage_summary.deadline_risk}
              </StatusChip>
            </div>

            <div className="flex flex-wrap gap-2">
              <button type="button" onClick={handleQuote} disabled={quoteLoading} className="quantum-btn">
                {quoteLoading ? 'Calculating…' : 'Preview Wisconsin Pricing'}
              </button>
              <button
                type="button"
                onClick={handleCheckout}
                disabled={checkoutLoading || intake.status === 'missing_docs'}
                className="quantum-btn-primary disabled:opacity-60"
              >
                {checkoutLoading ? 'Opening Checkout…' : 'Pay Now'}
              </button>
            </div>

            {quote && (
              <div className="border border-border-subtle bg-[var(--color-bg-base)]/20 p-3 text-sm text-[var(--color-text-primary)]">
                <div className="font-semibold">Fee quote (Wisconsin-first)</div>
                <div>Total due: ${(quote.total_due_cents / 100).toFixed(2)}</div>
                <div>Agency payout: ${(quote.agency_payout_cents / 100).toFixed(2)}</div>
                <div>Platform fee: ${(quote.platform_fee_cents / 100).toFixed(2)}</div>
                <div>Margin status: {quote.margin_status}</div>
                {quote.hold_reasons.length > 0 && (
                  <ul className="mt-2 list-disc pl-5 text-xs text-[var(--q-yellow)]">
                    {quote.hold_reasons.map((reason) => (
                      <li key={reason}>{reason}</li>
                    ))}
                  </ul>
                )}
              </div>
            )}

            <div className="text-sm text-[var(--color-text-secondary)]">
              AI triage: <strong>{intake.triage_summary.classification}</strong> · urgency{' '}
              <strong>{intake.triage_summary.urgency_level}</strong>
            </div>

            <div className="grid gap-2 sm:grid-cols-2">
              <div className="border border-border-subtle bg-[var(--color-bg-base)]/20 p-3">
                <div className="mb-2 text-xs uppercase tracking-widest text-[var(--color-text-muted)]">Required-document checklist</div>
                <div className="space-y-1">
                  {intake.required_document_checklist.map((item) => (
                    <div key={item.code} className="flex items-center justify-between text-sm">
                      <span className="text-[var(--color-text-secondary)]">{checklistLabel(item)}</span>
                      <StatusChip status={item.satisfied ? 'active' : 'warning'} size="sm">
                        {item.satisfied ? 'received' : 'missing'}
                      </StatusChip>
                    </div>
                  ))}
                </div>
              </div>

              <div className="border border-border-subtle bg-[var(--color-bg-base)]/20 p-3">
                <div className="mb-2 text-xs uppercase tracking-widest text-[var(--color-text-muted)]">Missing item cards</div>
                {intake.missing_items.length === 0 ? (
                  <div className="text-sm text-[var(--color-status-active)]">No blocking missing items.</div>
                ) : (
                  <div className="space-y-2">
                    {intake.missing_items.map((item) => (
                      <div key={item.code} className="border border-[var(--color-brand-red)]/30 bg-[var(--color-brand-red)]/10 p-2 text-sm">
                        <div className="font-semibold text-[var(--color-brand-red)]">{item.title}</div>
                        <div className="text-[var(--color-brand-red)]/90">{item.detail}</div>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            </div>

            <div className="grid gap-2 sm:grid-cols-[1fr_1fr_auto]">
              <div>
                <label className="label-caps">Document Kind</label>
                <select
                  value={uploadKind}
                  onChange={(event) => setUploadKind(event.target.value)}
                  className="mt-1 w-full border border-border-default bg-[var(--color-bg-base)] px-3 py-2 text-sm text-[var(--color-text-primary)]"
                >
                  {DOCUMENT_KIND_OPTIONS.map((opt) => (
                    <option key={opt} value={opt}>{opt}</option>
                  ))}
                </select>
              </div>
              <div>
                <label className="label-caps">Upload Request Document</label>
                <input
                  type="file"
                  onChange={(event) => setUploadFile(event.target.files?.[0] || null)}
                  className="mt-1 w-full border border-border-default bg-[var(--color-bg-base)] px-3 py-2 text-sm text-[var(--color-text-primary)]"
                />
              </div>
              <div className="flex items-end">
                <button
                  type="button"
                  disabled={uploading || !uploadFile}
                  onClick={handleUpload}
                  className="quantum-btn-primary disabled:opacity-60"
                >
                  {uploading ? 'Uploading…' : 'Upload'}
                </button>
              </div>
            </div>
          </div>
        )}
      </div>
    </AccessShell>
  );
}
