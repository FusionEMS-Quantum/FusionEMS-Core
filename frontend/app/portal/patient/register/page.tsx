'use client';

import { useState } from 'react';
import Link from 'next/link';

interface RegisterForm {
  first_name: string;
  last_name: string;
  date_of_birth: string;
  email: string;
  phone: string;
  statement_id: string;
  zip: string;
  password: string;
  confirm_password: string;
}

const clip6  = 'polygon(0 0, calc(100% - 6px) 0, 100% 6px, 100% 100%, 0 100%)';
const clip10 = 'polygon(0 0, calc(100% - 10px) 0, 100% 10px, 100% 100%, 0 100%)';

export default function RegisterPage() {
  const [form, setForm] = useState<RegisterForm>({
    first_name: '', last_name: '', date_of_birth: '',
    email: '', phone: '', statement_id: '', zip: '',
    password: '', confirm_password: '',
  });
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState('');
  const [success, setSuccess] = useState(false);
  const apiBase = process.env.NEXT_PUBLIC_API_BASE ?? process.env.NEXT_PUBLIC_API_URL ?? '';

  const handleChange = (field: keyof RegisterForm, value: string) => {
    setForm(prev => ({ ...prev, [field]: value }));
    setError('');
  };

  const validate = (): string | null => {
    if (!form.first_name.trim()) return 'First name is required.';
    if (!form.last_name.trim()) return 'Last name is required.';
    if (!form.date_of_birth) return 'Date of birth is required.';
    if (!form.email.trim() || !form.email.includes('@')) return 'Valid email is required.';
    if (!form.zip.trim()) return 'ZIP code is required for verification.';
    if (!form.password || form.password.length < 8) return 'Password must be at least 8 characters.';
    if (form.password !== form.confirm_password) return 'Passwords do not match.';
    return null;
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    const err = validate();
    if (err) { setError(err); return; }
    setSubmitting(true);
    setError('');
    try {
      const r = await fetch(`${apiBase}/api/v1/portal/register`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          first_name: form.first_name.trim(),
          last_name: form.last_name.trim(),
          date_of_birth: form.date_of_birth,
          email: form.email.trim().toLowerCase(),
          phone: form.phone.trim(),
          statement_id: form.statement_id.trim(),
          zip: form.zip.trim(),
          password: form.password,
        }),
      });
      if (!r.ok) {
        const d = await r.json().catch(() => ({}));
        setError((d as { detail?: string }).detail ?? 'Registration failed. Please verify your information.');
        return;
      }
      setSuccess(true);
    } catch {
      setError('Unable to connect. Please try again.');
    } finally {
      setSubmitting(false);
    }
  };

  if (success) {
    return (
      <div className="min-h-screen bg-[#050505] flex items-center justify-center px-4 py-16">
        <div className="max-w-md w-full text-center">
          <div
            className="inline-flex items-center justify-center w-16 h-16 bg-emerald-500/10 border border-emerald-500/20 mb-6 mx-auto"
            style={{ clipPath: clip10 }}
          >
            <svg width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="#10B981" strokeWidth="2.5" strokeLinecap="round">
              <polyline points="20 6 9 17 4 12"/>
            </svg>
          </div>
          <h2 className="text-xl font-black tracking-[0.12em] text-white uppercase mb-3">Registration Complete</h2>
          <p className="text-sm text-zinc-400 mb-2">Your patient billing portal account has been created.</p>
          <p className="text-xs text-zinc-600 mb-8">Check your email for a verification link before logging in.</p>
          <Link
            href="/portal/patient/login"
            className="inline-flex items-center h-10 px-6 bg-[#FF4D00] text-black text-[10px] font-black tracking-widest uppercase hover:bg-[#E64500] transition-colors shadow-[0_0_15px_rgba(255,77,0,0.15)]"
            style={{ clipPath: clip6 }}
          >
            Log In to Portal →
          </Link>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-[#050505] py-12 px-4">
      <div className="max-w-lg mx-auto">
        {/* Header */}
        <div className="text-center mb-10">
          <div className="text-[10px] font-bold tracking-[0.3em] text-zinc-600 uppercase mb-3">Patient Billing Portal</div>
          <h1 className="text-2xl font-black tracking-[0.1em] text-white uppercase mb-3">Create Your Account</h1>
          <p className="text-sm text-zinc-500">
            Already have an account?{' '}
            <Link href="/portal/patient/login" className="text-[#FF4D00] hover:text-[#FF6B35] font-bold transition-colors">
              Log In
            </Link>
          </p>
        </div>

        <div className="bg-[#0A0A0B] border border-zinc-800 p-6" style={{ clipPath: clip10 }}>
          <form onSubmit={e => void handleSubmit(e)} className="space-y-5">
            {/* Identity */}
            <div>
              <div className="text-[10px] font-bold tracking-[0.2em] text-zinc-600 uppercase mb-3">Identity Verification</div>
              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block text-[9px] font-bold tracking-widest text-zinc-600 uppercase mb-1.5">First Name</label>
                  <input
                    type="text"
                    value={form.first_name}
                    onChange={e => handleChange('first_name', e.target.value)}
                    autoComplete="given-name"
                    className="w-full bg-zinc-900 border border-zinc-800 text-zinc-200 text-sm px-3 py-2.5 outline-none focus:border-[#FF4D00]/40 transition-colors"
                    style={{ clipPath: clip6 }}
                    required
                  />
                </div>
                <div>
                  <label className="block text-[9px] font-bold tracking-widest text-zinc-600 uppercase mb-1.5">Last Name</label>
                  <input
                    type="text"
                    value={form.last_name}
                    onChange={e => handleChange('last_name', e.target.value)}
                    autoComplete="family-name"
                    className="w-full bg-zinc-900 border border-zinc-800 text-zinc-200 text-sm px-3 py-2.5 outline-none focus:border-[#FF4D00]/40 transition-colors"
                    style={{ clipPath: clip6 }}
                    required
                  />
                </div>
              </div>
              <div className="mt-3 grid grid-cols-2 gap-3">
                <div>
                  <label className="block text-[9px] font-bold tracking-widest text-zinc-600 uppercase mb-1.5">Date of Birth</label>
                  <input
                    type="date"
                    value={form.date_of_birth}
                    onChange={e => handleChange('date_of_birth', e.target.value)}
                    autoComplete="bday"
                    className="w-full bg-zinc-900 border border-zinc-800 text-zinc-200 text-sm px-3 py-2.5 outline-none focus:border-[#FF4D00]/40 transition-colors"
                    style={{ clipPath: clip6 }}
                    required
                  />
                </div>
                <div>
                  <label className="block text-[9px] font-bold tracking-widest text-zinc-600 uppercase mb-1.5">ZIP Code</label>
                  <input
                    type="text"
                    value={form.zip}
                    onChange={e => handleChange('zip', e.target.value)}
                    autoComplete="postal-code"
                    placeholder="For verification"
                    maxLength={10}
                    className="w-full bg-zinc-900 border border-zinc-800 text-zinc-200 text-sm px-3 py-2.5 outline-none focus:border-[#FF4D00]/40 transition-colors"
                    style={{ clipPath: clip6 }}
                    required
                  />
                </div>
              </div>
            </div>

            {/* Contact */}
            <div>
              <div className="text-[10px] font-bold tracking-[0.2em] text-zinc-600 uppercase mb-3">Contact Information</div>
              <div className="space-y-3">
                <div>
                  <label className="block text-[9px] font-bold tracking-widest text-zinc-600 uppercase mb-1.5">Email Address</label>
                  <input
                    type="email"
                    value={form.email}
                    onChange={e => handleChange('email', e.target.value)}
                    autoComplete="email"
                    className="w-full bg-zinc-900 border border-zinc-800 text-zinc-200 text-sm px-3 py-2.5 outline-none focus:border-[#FF4D00]/40 transition-colors"
                    style={{ clipPath: clip6 }}
                    required
                  />
                </div>
                <div>
                  <label className="block text-[9px] font-bold tracking-widest text-zinc-600 uppercase mb-1.5">Phone (optional)</label>
                  <input
                    type="tel"
                    value={form.phone}
                    onChange={e => handleChange('phone', e.target.value)}
                    autoComplete="tel"
                    placeholder="(555) 000-0000"
                    className="w-full bg-zinc-900 border border-zinc-800 text-zinc-200 text-sm px-3 py-2.5 outline-none focus:border-[#FF4D00]/40 transition-colors"
                    style={{ clipPath: clip6 }}
                  />
                </div>
              </div>
            </div>

            {/* Statement ID (optional for linking) */}
            <div>
              <label className="block text-[9px] font-bold tracking-widest text-zinc-600 uppercase mb-1.5">
                Statement ID <span className="text-zinc-700 normal-case">(optional — links your account)</span>
              </label>
              <input
                type="text"
                value={form.statement_id}
                onChange={e => handleChange('statement_id', e.target.value)}
                placeholder="Found on your billing notice"
                className="w-full bg-zinc-900 border border-zinc-800 text-zinc-200 text-sm px-3 py-2.5 outline-none focus:border-[#FF4D00]/40 transition-colors"
                style={{ clipPath: clip6 }}
              />
            </div>

            {/* Password */}
            <div>
              <div className="text-[10px] font-bold tracking-[0.2em] text-zinc-600 uppercase mb-3">Set Password</div>
              <div className="space-y-3">
                <div>
                  <label className="block text-[9px] font-bold tracking-widest text-zinc-600 uppercase mb-1.5">Password</label>
                  <input
                    type="password"
                    value={form.password}
                    onChange={e => handleChange('password', e.target.value)}
                    autoComplete="new-password"
                    className="w-full bg-zinc-900 border border-zinc-800 text-zinc-200 text-sm px-3 py-2.5 outline-none focus:border-[#FF4D00]/40 transition-colors"
                    style={{ clipPath: clip6 }}
                    required
                    minLength={8}
                  />
                  <div className="text-[9px] text-zinc-700 mt-1">Minimum 8 characters.</div>
                </div>
                <div>
                  <label className="block text-[9px] font-bold tracking-widest text-zinc-600 uppercase mb-1.5">Confirm Password</label>
                  <input
                    type="password"
                    value={form.confirm_password}
                    onChange={e => handleChange('confirm_password', e.target.value)}
                    autoComplete="new-password"
                    className="w-full bg-zinc-900 border border-zinc-800 text-zinc-200 text-sm px-3 py-2.5 outline-none focus:border-[#FF4D00]/40 transition-colors"
                    style={{ clipPath: clip6 }}
                    required
                  />
                </div>
              </div>
            </div>

            {/* Error */}
            {error && (
              <div className="px-4 py-3 bg-red-500/8 border border-red-500/20 text-red-400 text-sm" style={{ clipPath: clip6 }}>
                {error}
              </div>
            )}

            {/* Submit */}
            <button
              type="submit"
              disabled={submitting}
              className="w-full h-11 bg-[#FF4D00] text-black text-[10px] font-black tracking-widest uppercase hover:bg-[#E64500] transition-colors disabled:opacity-50 shadow-[0_0_20px_rgba(255,77,0,0.15)] flex items-center justify-center gap-2"
              style={{ clipPath: clip6 }}
            >
              {submitting && <div className="w-3.5 h-3.5 border-2 border-black border-t-transparent rounded-full animate-spin" />}
              {submitting ? 'Creating Account...' : 'Create Portal Account'}
            </button>

            <p className="text-[9px] text-zinc-700 text-center">
              By creating an account, you agree to our{' '}
              <Link href="/terms" className="text-zinc-600 hover:text-zinc-400 underline">Terms of Service</Link>{' '}
              and{' '}
              <Link href="/privacy" className="text-zinc-600 hover:text-zinc-400 underline">Privacy Policy</Link>.
            </p>
          </form>
        </div>

        {/* Security note */}
        <div className="mt-6 flex items-center justify-center gap-2 text-[9px] text-zinc-700 font-mono">
          <svg width="10" height="10" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
            <rect x="3" y="11" width="18" height="11" rx="2"/><path d="M7 11V7a5 5 0 0 1 10 0v4"/>
          </svg>
          256-BIT ENCRYPTED · HIPAA-CONSCIOUS · YOUR DATA IS PROTECTED
        </div>
      </div>
    </div>
  );
}
