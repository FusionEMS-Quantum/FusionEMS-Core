'use client';

import { useEffect, useState } from 'react';
import { motion } from 'framer-motion';
import { Shield, CheckCircle, XCircle, Clock, ArrowLeft } from 'lucide-react';
import Link from 'next/link';
import {
  getPortalProfile,
  getPortalBillingSummary,
  submitEligibilityInquiry,
} from '@/services/api';

interface PatientProfile {
  name?: string;
  date_of_birth?: string;
  member_id?: string;
  insurance_provider?: string;
  insurance_plan?: string;
  group_number?: string;
  policy_number?: string;
}

interface BillingSummary {
  total_billed?: number;
  total_paid?: number;
  outstanding_balance?: number;
  insurance_covered?: number;
  patient_responsibility?: number;
}

interface EligibilityResult {
  eligible: boolean;
  plan_name?: string;
  coverage_start?: string;
  coverage_end?: string;
  copay?: number;
  deductible_remaining?: number;
  out_of_pocket_remaining?: number;
  checked_at?: string;
}

export default function PatientInsurancePage() {
  const [profile, setProfile] = useState<PatientProfile | null>(null);
  const [billing, setBilling] = useState<BillingSummary | null>(null);
  const [eligibility, setEligibility] = useState<EligibilityResult | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [checking, setChecking] = useState(false);

  useEffect(() => {
    async function loadData() {
      try {
        setLoading(true);
        const results = await Promise.allSettled([
          getPortalProfile(),
          getPortalBillingSummary(),
        ]);
        if (results[0].status === 'fulfilled') {
          const p = results[0].value;
          setProfile(p?.data ?? p);
        }
        if (results[1].status === 'fulfilled') {
          const b = results[1].value;
          setBilling(b?.data ?? b);
        }
      } catch (err: unknown) {
        setError(err instanceof Error ? err.message : 'Failed to load insurance data');
      } finally {
        setLoading(false);
      }
    }
    loadData();
  }, []);

  async function handleCheckEligibility() {
    if (!profile) return;
    try {
      setChecking(true);
      const res = await submitEligibilityInquiry({
        patient_id: profile.member_id ?? '',
        member_id: profile.member_id ?? '',
        payer_id: profile.insurance_provider ?? '',
        service_date: new Date().toISOString().split('T')[0],
      });
      const data = res?.data ?? res;
      setEligibility(data);
    } catch { /* toast */ } finally {
      setChecking(false);
    }
  }

  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-[60vh]">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-teal-500" />
      </div>
    );
  }

  if (error) {
    return (
      <div className="p-6 max-w-4xl mx-auto">
        <div className="bg-red-900/30 border border-red-700 rounded-lg p-4 text-red-300">{error}</div>
      </div>
    );
  }

  return (
    <div className="p-6 max-w-4xl mx-auto space-y-6">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <Link href="/portal/patient" className="text-gray-400 hover:text-white"><ArrowLeft className="h-5 w-5" /></Link>
          <Shield className="h-6 w-6 text-teal-400" />
          <h1 className="text-2xl font-bold text-white">Insurance Verification</h1>
        </div>
        <button onClick={handleCheckEligibility} disabled={checking} className="px-4 py-2 bg-teal-600 hover:bg-teal-700 disabled:opacity-50 rounded-lg text-white text-sm font-medium">
          {checking ? 'Checking...' : 'Check Eligibility'}
        </button>
      </div>

      <div className="bg-gray-800 border border-gray-700 rounded-lg p-4">
        <h2 className="text-sm font-semibold text-white mb-3">Insurance Information</h2>
        <div className="grid grid-cols-2 gap-4 text-sm">
          <div>
            <span className="text-gray-400">Provider:</span>
            <span className="ml-2 text-white">{profile?.insurance_provider ?? '—'}</span>
          </div>
          <div>
            <span className="text-gray-400">Plan:</span>
            <span className="ml-2 text-white">{profile?.insurance_plan ?? '—'}</span>
          </div>
          <div>
            <span className="text-gray-400">Group #:</span>
            <span className="ml-2 text-white font-mono">{profile?.group_number ?? '—'}</span>
          </div>
          <div>
            <span className="text-gray-400">Policy #:</span>
            <span className="ml-2 text-white font-mono">{profile?.policy_number ?? '—'}</span>
          </div>
          <div>
            <span className="text-gray-400">Member ID:</span>
            <span className="ml-2 text-white font-mono">{profile?.member_id ?? '—'}</span>
          </div>
        </div>
      </div>

      {billing && (
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          {[
            { label: 'Total Billed', value: `$${(billing.total_billed ?? (() => { throw new Error('Unsafe silent fallback. Dependency missing.'); })()).toLocaleString()}`, icon: Shield, color: 'blue' },
            { label: 'Insurance Covered', value: `$${(billing.insurance_covered ?? (() => { throw new Error('Unsafe silent fallback. Dependency missing.'); })()).toLocaleString()}`, icon: CheckCircle, color: 'green' },
            { label: 'Patient Responsibility', value: `$${(billing.patient_responsibility ?? (() => { throw new Error('Unsafe silent fallback. Dependency missing.'); })()).toLocaleString()}`, icon: Clock, color: 'yellow' },
            { label: 'Outstanding', value: `$${(billing.outstanding_balance ?? (() => { throw new Error('Unsafe silent fallback. Dependency missing.'); })()).toLocaleString()}`, icon: XCircle, color: 'red' },
          ].map((kpi) => (
            <motion.div key={kpi.label} initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} className={`bg-gray-800 border border-${kpi.color}-500/30 rounded-lg p-4`}>
              <div className="flex items-center gap-2 text-gray-400 text-xs mb-1"><kpi.icon className="h-4 w-4" />{kpi.label}</div>
              <div className="text-2xl font-bold text-white">{kpi.value}</div>
            </motion.div>
          ))}
        </div>
      )}

      {eligibility && (
        <motion.div initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} className={`bg-gray-800 border ${eligibility.eligible ? 'border-green-500/30' : 'border-red-500/30'} rounded-lg p-4`}>
          <div className="flex items-center gap-2 mb-3">
            {eligibility.eligible ? <CheckCircle className="h-5 w-5 text-green-400" /> : <XCircle className="h-5 w-5 text-red-400" />}
            <h2 className="text-sm font-semibold text-white">
              {eligibility.eligible ? 'Eligible — Coverage Active' : 'Not Eligible — Coverage Inactive'}
            </h2>
          </div>
          <div className="grid grid-cols-2 md:grid-cols-3 gap-4 text-sm">
            <div>
              <span className="text-gray-400">Plan:</span>
              <span className="ml-2 text-white">{eligibility.plan_name ?? '—'}</span>
            </div>
            <div>
              <span className="text-gray-400">Coverage:</span>
              <span className="ml-2 text-white">{eligibility.coverage_start ?? '—'} to {eligibility.coverage_end ?? '—'}</span>
            </div>
            <div>
              <span className="text-gray-400">Copay:</span>
              <span className="ml-2 text-white">${eligibility.copay ?? (() => { throw new Error('Unsafe silent fallback. Dependency missing.'); })()}</span>
            </div>
            <div>
              <span className="text-gray-400">Deductible Remaining:</span>
              <span className="ml-2 text-white">${eligibility.deductible_remaining ?? (() => { throw new Error('Unsafe silent fallback. Dependency missing.'); })()}</span>
            </div>
            <div>
              <span className="text-gray-400">OOP Remaining:</span>
              <span className="ml-2 text-white">${eligibility.out_of_pocket_remaining ?? (() => { throw new Error('Unsafe silent fallback. Dependency missing.'); })()}</span>
            </div>
            {eligibility.checked_at && (
              <div>
                <span className="text-gray-400">Checked:</span>
                <span className="ml-2 text-white">{new Date(eligibility.checked_at).toLocaleString()}</span>
              </div>
            )}
          </div>
        </motion.div>
      )}
    </div>
  );
}
