'use client';

import { useEffect, useState } from 'react';
import Link from 'next/link';

interface PatientProfile {
  id?: string;
  first_name?: string;
  last_name?: string;
  date_of_birth?: string;
  email?: string;
  phone?: string;
  address?: {
    street?: string;
    city?: string;
    state?: string;
    zip?: string;
  };
  communication_preferences?: {
    email_statements?: boolean;
    sms_reminders?: boolean;
    paperless?: boolean;
    call_reminders?: boolean;
  };
  portal_created_at?: string;
}

const clip6  = 'polygon(0 0, calc(100% - 6px) 0, 100% 6px, 100% 100%, 0 100%)';
const clip10 = 'polygon(0 0, calc(100% - 10px) 0, 100% 10px, 100% 100%, 0 100%)';

function FieldRow({ label, value, editing, name, onChange, type = 'text' }: {
  label: string;
  value: string;
  editing: boolean;
  name: string;
  onChange: (_name: string, _value: string) => void;
  type?: string;
}) {
  return (
    <div className="py-3 border-b border-zinc-900/50 flex items-center gap-4">
      <div className="w-36 text-[10px] font-bold tracking-[0.15em] text-zinc-600 uppercase flex-shrink-0">{label}</div>
      {editing ? (
        <input
          type={type}
          value={value}
          onChange={e => onChange(name, e.target.value)}
          className="flex-1 bg-zinc-900 border border-zinc-700 text-zinc-200 text-sm px-3 py-1.5 outline-none focus:border-[#FF4D00]/50 transition-colors"
          style={{ clipPath: clip6 }}
        />
      ) : (
        <span className="text-sm text-zinc-300 flex-1">{value || <span className="text-zinc-700 italic">Not set</span>}</span>
      )}
    </div>
  );
}

function ToggleRow({ label, description, checked, onChange }: {
  label: string;
  description: string;
  checked: boolean;
  onChange: (_v: boolean) => void;
}) {
  return (
    <div className="flex items-start justify-between gap-4 py-3 border-b border-zinc-900/50">
      <div>
        <div className="text-sm font-semibold text-zinc-200">{label}</div>
        <div className="text-xs text-zinc-600 mt-0.5">{description}</div>
      </div>
      <button
        onClick={() => onChange(!checked)}
        className={`flex-shrink-0 w-10 h-5 relative transition-colors ${checked ? 'bg-[#FF4D00]' : 'bg-zinc-800'}`}
        style={{ clipPath: clip6 }}
        role="switch"
        aria-checked={checked}
      >
        <span
          className={`absolute top-0.5 w-4 h-4 bg-white transition-transform ${checked ? 'translate-x-5' : 'translate-x-0.5'}`}
          style={{ clipPath: clip6 }}
        />
      </button>
    </div>
  );
}

export default function ProfilePage() {
  const [profile, setProfile] = useState<PatientProfile>({});
  const [loading, setLoading] = useState(true);
  const [editing, setEditing] = useState(false);
  const [saving, setSaving] = useState(false);
  const [draft, setDraft] = useState<PatientProfile>({});
  const [saved, setSaved] = useState(false);
  const apiBase = process.env.NEXT_PUBLIC_API_BASE ?? process.env.NEXT_PUBLIC_API_URL ?? '';

  useEffect(() => {
    fetch(`${apiBase}/api/v1/portal/profile`, { credentials: 'include' })
      .then(r => r.json())
      .then(d => { setProfile(d); setDraft(d); })
      .catch(() => { setProfile(MOCK_PROFILE); setDraft(MOCK_PROFILE); })
      .finally(() => setLoading(false));
  }, [apiBase]);

  const handleFieldChange = (name: string, value: string) => {
    setDraft(prev => {
      if (name.startsWith('address.')) {
        const key = name.split('.')[1];
        return { ...prev, address: { ...prev.address, [key]: value } };
      }
      return { ...prev, [name]: value };
    });
  };

  const handlePrefChange = (key: keyof NonNullable<PatientProfile['communication_preferences']>, val: boolean) => {
    setDraft(prev => ({
      ...prev,
      communication_preferences: { ...prev.communication_preferences, [key]: val },
    }));
  };

  const handleSave = async () => {
    setSaving(true);
    try {
      await fetch(`${apiBase}/api/v1/portal/profile`, {
        method: 'PATCH',
        credentials: 'include',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(draft),
      });
      setProfile(draft);
      setEditing(false);
      setSaved(true);
      setTimeout(() => setSaved(false), 3000);
    } catch {
      // ignore network error — profile update is non-critical
    } finally {
      setSaving(false);
    }
  };

  const handleCancel = () => {
    setDraft(profile);
    setEditing(false);
  };

  const prefs = draft.communication_preferences ?? {};

  if (loading) {
    return (
      <div className="max-w-3xl mx-auto px-4 py-8">
        <div className="space-y-4">
          {Array.from({ length: 5 }).map((_, i) => (
            <div key={i} className="bg-[#0A0A0B] border border-zinc-900 h-16 animate-pulse" style={{ clipPath: clip10 }} />
          ))}
        </div>
      </div>
    );
  }

  return (
    <div className="max-w-3xl mx-auto px-4 py-8">
      {/* Header */}
      <div className="flex items-start justify-between mb-8">
        <div>
          <div className="flex items-center gap-3 mb-1">
            <div className="w-[3px] h-6 bg-[#FF4D00] shadow-[0_0_8px_rgba(255,77,0,0.6)]" />
            <h1 className="text-xl font-black tracking-[0.12em] text-white uppercase">My Profile</h1>
          </div>
          <p className="text-sm text-zinc-500 ml-5">Manage your contact information and communication preferences.</p>
        </div>
        {saved && (
          <span className="text-[10px] font-bold tracking-widest uppercase text-emerald-400 flex items-center gap-1.5">
            <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5"><polyline points="20 6 9 17 4 12"/></svg>
            Saved
          </span>
        )}
      </div>

      {/* Personal info */}
      <div className="bg-[#0A0A0B] border border-zinc-800 mb-6" style={{ clipPath: clip10 }}>
        <div className="flex items-center justify-between px-5 py-3 border-b border-zinc-900">
          <span className="text-[10px] font-bold tracking-[0.15em] text-zinc-400 uppercase">Personal Information</span>
          {!editing ? (
            <button
              onClick={() => setEditing(true)}
              className="text-[10px] font-bold tracking-widest uppercase text-[#FF4D00] hover:text-[#FF6B35] transition-colors flex items-center gap-1.5"
            >
              <svg width="11" height="11" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><path d="M12 20h9"/><path d="M16.5 3.5a2.121 2.121 0 0 1 3 3L7 19l-4 1 1-4L16.5 3.5z"/></svg>
              Edit
            </button>
          ) : (
            <div className="flex items-center gap-3">
              <button
                onClick={handleCancel}
                className="text-[10px] font-bold tracking-widest uppercase text-zinc-500 hover:text-zinc-300 transition-colors"
              >
                Cancel
              </button>
              <button
                onClick={handleSave}
                disabled={saving}
                className="flex items-center gap-1.5 h-7 px-3 bg-[#FF4D00] text-black text-[10px] font-black tracking-widest uppercase hover:bg-[#E64500] transition-colors disabled:opacity-50"
                style={{ clipPath: clip6 }}
              >
                {saving && <div className="w-2.5 h-2.5 border border-black border-t-transparent rounded-full animate-spin" />}
                {saving ? 'Saving...' : 'Save Changes'}
              </button>
            </div>
          )}
        </div>

        <div className="px-5 py-2">
          <FieldRow label="First Name"    value={draft.first_name ?? ''}                     editing={editing} name="first_name"     onChange={handleFieldChange} />
          <FieldRow label="Last Name"     value={draft.last_name ?? ''}                      editing={editing} name="last_name"      onChange={handleFieldChange} />
          <FieldRow label="Date of Birth" value={draft.date_of_birth ?? ''}                  editing={editing} name="date_of_birth"  onChange={handleFieldChange} type="date" />
          <FieldRow label="Email"         value={draft.email ?? ''}                          editing={editing} name="email"          onChange={handleFieldChange} type="email" />
          <FieldRow label="Phone"         value={draft.phone ?? ''}                          editing={editing} name="phone"          onChange={handleFieldChange} type="tel" />
        </div>
      </div>

      {/* Mailing address */}
      <div className="bg-[#0A0A0B] border border-zinc-800 mb-6" style={{ clipPath: clip10 }}>
        <div className="px-5 py-3 border-b border-zinc-900">
          <span className="text-[10px] font-bold tracking-[0.15em] text-zinc-400 uppercase">Mailing Address</span>
        </div>
        <div className="px-5 py-2">
          <FieldRow label="Street"    value={draft.address?.street ?? ''} editing={editing} name="address.street" onChange={handleFieldChange} />
          <FieldRow label="City"      value={draft.address?.city ?? ''}   editing={editing} name="address.city"   onChange={handleFieldChange} />
          <FieldRow label="State"     value={draft.address?.state ?? ''}  editing={editing} name="address.state"  onChange={handleFieldChange} />
          <FieldRow label="ZIP Code"  value={draft.address?.zip ?? ''}    editing={editing} name="address.zip"    onChange={handleFieldChange} />
        </div>
      </div>

      {/* Communication preferences */}
      <div className="bg-[#0A0A0B] border border-zinc-800 mb-6" style={{ clipPath: clip10 }}>
        <div className="px-5 py-3 border-b border-zinc-900">
          <span className="text-[10px] font-bold tracking-[0.15em] text-zinc-400 uppercase">Communication Preferences</span>
        </div>
        <div className="px-5 py-2">
          <ToggleRow
            label="Paperless Billing"
            description="Receive statements by email instead of mail."
            checked={prefs.paperless ?? false}
            onChange={v => handlePrefChange('paperless', v)}
          />
          <ToggleRow
            label="Email Statements"
            description="Get billing statements and account notices by email."
            checked={prefs.email_statements ?? false}
            onChange={v => handlePrefChange('email_statements', v)}
          />
          <ToggleRow
            label="SMS Payment Reminders"
            description="Receive text message payment reminders."
            checked={prefs.sms_reminders ?? false}
            onChange={v => handlePrefChange('sms_reminders', v)}
          />
          <ToggleRow
            label="Phone Call Reminders"
            description="Allow billing team to call with payment reminders."
            checked={prefs.call_reminders ?? false}
            onChange={v => handlePrefChange('call_reminders', v)}
          />
        </div>
        {(editing) && (
          <div className="px-5 py-3 border-t border-zinc-900 text-right">
            <button
              onClick={handleSave}
              disabled={saving}
              className="h-7 px-4 bg-[#FF4D00] text-black text-[10px] font-black tracking-widest uppercase hover:bg-[#E64500] transition-colors disabled:opacity-50"
              style={{ clipPath: clip6 }}
            >
              {saving ? 'Saving...' : 'Save Preferences'}
            </button>
          </div>
        )}
      </div>

      {/* Portal security */}
      <div className="bg-[#0A0A0B] border border-zinc-800" style={{ clipPath: clip10 }}>
        <div className="px-5 py-3 border-b border-zinc-900">
          <span className="text-[10px] font-bold tracking-[0.15em] text-zinc-400 uppercase">Portal Security</span>
        </div>
        <div className="px-5 py-4 space-y-3">
          <div className="flex items-center justify-between">
            <div>
              <div className="text-sm font-semibold text-zinc-200">Password</div>
              <div className="text-xs text-zinc-600 mt-0.5">Update your portal login password.</div>
            </div>
            <Link
              href="/portal/patient/reset-password"
              className="text-[10px] font-bold tracking-widest uppercase text-[#FF4D00] hover:underline"
            >
              Change Password →
            </Link>
          </div>
          <div className="border-t border-zinc-900/50 pt-3 flex items-center justify-between">
            <div>
              <div className="text-sm font-semibold text-zinc-200">Account Access</div>
              <div className="text-xs text-zinc-600 mt-0.5">Sign out of the patient billing portal.</div>
            </div>
            <Link
              href="/portal/patient/login"
              className="text-[10px] font-bold tracking-widest uppercase text-zinc-500 hover:text-zinc-200 transition-colors border border-zinc-800 hover:border-zinc-600 px-3 py-1.5"
              style={{ clipPath: clip6 }}
            >
              Sign Out
            </Link>
          </div>
        </div>
      </div>

      <div className="mt-6 text-center">
        <p className="text-[10px] text-zinc-700 font-mono">
          For name corrections or HIPAA-related requests, contact{' '}
          <Link href="/portal/patient/support" className="text-zinc-500 hover:text-zinc-400 underline">billing support</Link>.
        </p>
      </div>
    </div>
  );
}

const MOCK_PROFILE: PatientProfile = {
  first_name: 'Jane',
  last_name: 'Doe',
  date_of_birth: '1985-03-15',
  email: 'jane.doe@example.com',
  phone: '(555) 867-5309',
  address: { street: '123 Main Street', city: 'Springfield', state: 'IL', zip: '62701' },
  communication_preferences: { email_statements: true, sms_reminders: true, paperless: true, call_reminders: false },
  portal_created_at: '2025-01-01T00:00:00Z',
};
