'use client';

import { Suspense, useCallback, useEffect, useMemo, useState } from 'react';
import { useSearchParams } from 'next/navigation';
import { SettingsShell } from '@/components/shells/PageShells';
import {
  AIExplanationCard,
  QuantumEmptyState,
  QuantumTableSkeleton,
  SimpleModeSummary,
  StatusChip,
} from '@/components/ui';
import {
  getPatientContactPreference,
  getPatientLanguagePreference,
  listOptOutEvents,
} from '@/services/api';

interface ContactPreference {
  id: string;
  patient_id: string;
  sms_allowed: boolean;
  call_allowed: boolean;
  email_allowed: boolean;
  mail_required: boolean;
  contact_restricted: boolean;
  preferred_channel: string | null;
  preferred_time_start: string | null;
  preferred_time_end: string | null;
  facility_callback_preference: string | null;
}

interface LanguagePreference {
  id: string;
  patient_id: string;
  primary_language: string;
  secondary_language: string | null;
  interpreter_required: boolean;
  interpreter_language: string | null;
}

interface OptOutEvent {
  id: string;
  patient_id: string;
  channel: string;
  action: string;
  reason: string;
  notes: string | null;
  created_at: string;
}

function normalizeList<T>(payload: unknown): T[] {
  if (Array.isArray(payload)) return payload as T[];
  if (payload && typeof payload === 'object') {
    const root = payload as { items?: unknown[] };
    if (Array.isArray(root.items)) return root.items as T[];
  }
  return [];
}

function boolChip(label: string, enabled: boolean) {
  return (
    <StatusChip status={enabled ? 'active' : 'critical'} size="sm">
      {label}: {enabled ? 'YES' : 'NO'}
    </StatusChip>
  );
}

function PatientPreferencesContent() {
  const searchParams = useSearchParams();
  const [activeSection, setActiveSection] = useState('preferences');
  const [preferences, setPreferences] = useState<ContactPreference[]>([]);
  const [languagePreferences, setLanguagePreferences] = useState<LanguagePreference[]>([]);
  const [optOutEvents, setOptOutEvents] = useState<OptOutEvent[]>([]);
  const [loading, setLoading] = useState(true);

  const patientId = useMemo(
    () => searchParams.get('patient_id') || searchParams.get('patientId') || '',
    [searchParams]
  );

  const load = useCallback(async () => {
    if (!patientId) {
      setLoading(false);
      setPreferences([]);
      setLanguagePreferences([]);
      setOptOutEvents([]);
      return;
    }

    setLoading(true);
    try {
      const [prefRes, langRes, optOutRes] = await Promise.all([
        getPatientContactPreference(patientId).catch(() => null),
        getPatientLanguagePreference(patientId).catch(() => null),
        listOptOutEvents(patientId).catch(() => []),
      ]);

      const prefItems = normalizeList<ContactPreference>(prefRes);
      const languageItems = normalizeList<LanguagePreference>(langRes);
      const optItems = normalizeList<OptOutEvent>(optOutRes);

      setPreferences(prefItems.length > 0 ? prefItems : (prefRes ? [prefRes as ContactPreference] : []));
      setLanguagePreferences(languageItems.length > 0 ? languageItems : (langRes ? [langRes as LanguagePreference] : []));
      setOptOutEvents(optItems);
    } finally {
      setLoading(false);
    }
  }, [patientId]);

  useEffect(() => {
    load();
  }, [load]);

  const sections = useMemo(
    () => [
      { id: 'preferences', label: `Contact Preferences (${preferences.length})` },
      { id: 'language', label: `Language (${languagePreferences.length})` },
      { id: 'history', label: `Opt-Out History (${optOutEvents.length})` },
    ],
    [preferences.length, languagePreferences.length, optOutEvents.length]
  );

  const restrictedCount = preferences.filter((p) => p.contact_restricted).length;

  if (loading) {
    return <QuantumTableSkeleton rows={6} />;
  }

  return (
    <SettingsShell
      title="Patient Communication Preferences"
      sections={sections}
      activeSection={activeSection}
      onSectionChange={setActiveSection}
    >
      {!patientId ? (
        <QuantumEmptyState
          title="No patient selected"
          description="Open this page with a patient context (patient_id) to view and manage communication preferences."
          icon="user"
        />
      ) : (
        <div className="space-y-4">
          <SimpleModeSummary
            screenName="Contact Preferences"
            domain="support"
            whatThisDoes="This screen controls allowed communication channels, language requirements, and opt-out history for a patient account."
            whatIsWrong={restrictedCount > 0 ? `${restrictedCount} preference records currently mark contact as restricted.` : undefined}
            whatMatters="Incorrect channel permissions can cause compliance violations, missed outreach, and poor patient experience."
            whatToClickNext={activeSection === 'history' ? 'Review recent opt-out events first, then validate channel settings in Contact Preferences.' : 'Validate channel permissions and language/interpreter settings before outreach.'}
            requiresReview={restrictedCount > 0}
          />

          <AIExplanationCard
            domain="support"
            severity={restrictedCount > 0 ? 'HIGH' : 'INFORMATIONAL'}
            what={restrictedCount > 0
              ? 'One or more records indicate contact restrictions that may block outreach.'
              : 'No elevated contact restrictions detected in loaded preference records.'}
            why="Contact permission and language mismatches create operational friction and legal/compliance risk."
            next={activeSection === 'preferences'
              ? 'Confirm SMS/Call/Email permissions and preferred channel before initiating communications.'
              : activeSection === 'language'
                ? 'Confirm interpreter requirement and language alignment for safe patient communication.'
                : 'Audit opt-out reasons and recency, then reconcile with channel permissions.'}
            requiresReview={restrictedCount > 0}
          />

          {activeSection === 'preferences' && (
            <>
              {preferences.length === 0 ? (
                <QuantumEmptyState
                  title="No contact preferences"
                  description="No contact-preference record found for this patient yet."
                  icon="mail"
                />
              ) : (
                <div className="space-y-3">
                  {preferences.map((pref) => (
                    <div key={pref.id} className="bg-bg-panel border border-border-subtle chamfer-8 p-4 space-y-3">
                      <div className="text-sm font-semibold text-text-primary">Contact Channel Permissions</div>
                      <div className="flex flex-wrap gap-2">
                        {boolChip('SMS', pref.sms_allowed)}
                        {boolChip('CALL', pref.call_allowed)}
                        {boolChip('EMAIL', pref.email_allowed)}
                        {boolChip('MAIL REQUIRED', pref.mail_required)}
                        {boolChip('CONTACT ALLOWED', !pref.contact_restricted)}
                        {pref.preferred_channel && (
                          <StatusChip status="info" size="sm">PREFERRED: {pref.preferred_channel}</StatusChip>
                        )}
                      </div>

                      {(pref.preferred_time_start || pref.preferred_time_end) && (
                        <div className="text-xs text-text-muted">
                          Preferred contact window: {pref.preferred_time_start || '—'} to {pref.preferred_time_end || '—'}
                        </div>
                      )}

                      {pref.facility_callback_preference && (
                        <div className="text-xs text-text-muted">
                          Facility callback preference: {pref.facility_callback_preference}
                        </div>
                      )}
                    </div>
                  ))}
                </div>
              )}
            </>
          )}

          {activeSection === 'language' && (
            <>
              {languagePreferences.length === 0 ? (
                <QuantumEmptyState
                  title="No language preferences"
                  description="No language-preference record found for this patient yet."
                  icon="globe"
                />
              ) : (
                <div className="space-y-3">
                  {languagePreferences.map((lang) => (
                    <div key={lang.id} className="bg-bg-panel border border-border-subtle chamfer-8 p-4 space-y-2">
                      <div className="text-sm font-semibold text-text-primary">Language Configuration</div>
                      <div className="flex flex-wrap gap-2">
                        <StatusChip status="info" size="sm">PRIMARY: {lang.primary_language?.toUpperCase()}</StatusChip>
                        {lang.secondary_language && (
                          <StatusChip status="neutral" size="sm">SECONDARY: {lang.secondary_language.toUpperCase()}</StatusChip>
                        )}
                        <StatusChip status={lang.interpreter_required ? 'review' : 'active'} size="sm">
                          INTERPRETER REQUIRED: {lang.interpreter_required ? 'YES' : 'NO'}
                        </StatusChip>
                        {lang.interpreter_language && (
                          <StatusChip status="warning" size="sm">INTERPRETER: {lang.interpreter_language.toUpperCase()}</StatusChip>
                        )}
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </>
          )}

          {activeSection === 'history' && (
            <>
              {optOutEvents.length === 0 ? (
                <QuantumEmptyState
                  title="No opt-out history"
                  description="No communication opt-out events are recorded for this patient."
                  icon="clock"
                />
              ) : (
                <div className="bg-bg-panel border border-border-subtle chamfer-8 overflow-hidden">
                  <table className="w-full text-left">
                    <thead>
                      <tr className="border-b border-border-subtle">
                        {['Action', 'Channel', 'Reason', 'Timestamp', 'Notes'].map((header) => (
                          <th key={header} className="px-4 py-3 text-micro uppercase tracking-widest text-text-muted">
                            {header}
                          </th>
                        ))}
                      </tr>
                    </thead>
                    <tbody>
                      {optOutEvents.map((event) => (
                        <tr key={event.id} className="border-b border-border-subtle hover:bg-white/[0.02]">
                          <td className="px-4 py-3">
                            <StatusChip status={event.action === 'opt_out' ? 'critical' : 'active'} size="sm">
                              {event.action.replace(/_/g, ' ')}
                            </StatusChip>
                          </td>
                          <td className="px-4 py-3 text-sm text-text-primary font-semibold">{event.channel.toUpperCase()}</td>
                          <td className="px-4 py-3 text-sm text-text-secondary">{event.reason}</td>
                          <td className="px-4 py-3 text-xs text-text-muted font-mono">
                            {new Date(event.created_at).toLocaleString()}
                          </td>
                          <td className="px-4 py-3 text-sm text-text-muted">{event.notes || '—'}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}
            </>
          )}
        </div>
      )}
    </SettingsShell>
  );
}

export default function PatientPreferencesPage() {
  return (
    <Suspense fallback={<QuantumTableSkeleton rows={6} />}>
      <PatientPreferencesContent />
    </Suspense>
  );
}
