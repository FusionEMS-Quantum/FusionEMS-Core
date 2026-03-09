'use client';

import { useEffect, useState } from 'react';
import { motion } from 'framer-motion';
import { Heart, FileText, CreditCard, Bell, ArrowLeft } from 'lucide-react';
import Link from 'next/link';
import {
  getPortalProfile,
  getPortalPaymentPlans,
  getPortalStatements,
  getPortalDocuments,
  requestPortalPaymentPlan,
} from '@/services/api';

interface PatientProfile {
  name?: string;
  date_of_birth?: string;
  member_id?: string;
  email?: string;
}

interface PaymentPlan {
  id: string;
  statement_id: string;
  monthly_amount: number;
  duration_months: number;
  total_amount: number;
  remaining_balance: number;
  status: string;
  next_payment_date?: string;
}

interface Statement {
  id: string;
  statement_number: string;
  patient_account_id: string;
  balance: number;
  amount_due: number;
  due_date: string;
  created_at: string;
}

interface DocRecord {
  id: string;
  name: string;
  type: string;
  uploaded_at: string;
}

export default function PatientCarePlanPage() {
  const [profile, setProfile] = useState<PatientProfile | null>(null);
  const [plans, setPlans] = useState<PaymentPlan[]>([]);
  const [statements, setStatements] = useState<Statement[]>([]);
  const [docs, setDocs] = useState<DocRecord[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [showRequest, setShowRequest] = useState(false);
  const [reqStatementId, setReqStatementId] = useState('');
  const [reqAmount, setReqAmount] = useState('');
  const [reqMonths, setReqMonths] = useState('6');

  useEffect(() => {
    async function loadData() {
      try {
        setLoading(true);
        const results = await Promise.allSettled([
          getPortalProfile(),
          getPortalPaymentPlans(),
          getPortalStatements(),
          getPortalDocuments(),
        ]);
        if (results[0].status === 'fulfilled') {
          const p = results[0].value;
          setProfile(p?.data ?? p);
        }
        if (results[1].status === 'fulfilled') {
          const p = results[1].value;
          setPlans(Array.isArray(p?.data) ? p.data : Array.isArray(p) ? p : []);
        }
        if (results[2].status === 'fulfilled') {
          const s = results[2].value;
          setStatements(Array.isArray(s) ? s : []);
        }
        if (results[3].status === 'fulfilled') {
          const d = results[3].value;
          setDocs(Array.isArray(d?.data) ? d.data : Array.isArray(d) ? d : []);
        }
      } catch (err: unknown) {
        setError(err instanceof Error ? err.message : 'Failed to load care plan data');
      } finally {
        setLoading(false);
      }
    }
    loadData();
  }, []);

  async function handleRequestPlan() {
    if (!reqStatementId || !reqAmount) return;
    try {
      await requestPortalPaymentPlan({
        statement_id: reqStatementId,
        proposed_monthly_amount: parseFloat(reqAmount),
        duration_months: parseInt(reqMonths, 10),
      });
      setShowRequest(false);
      setReqStatementId('');
      setReqAmount('');
      const res = await getPortalPaymentPlans();
      setPlans(Array.isArray(res?.data) ? res.data : Array.isArray(res) ? res : []);
    } catch { /* toast */ }
  }

  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-[60vh]">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-rose-500" />
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

  const activePlans = plans.filter((p) => p.status === 'active');
  const totalOwed = plans.reduce((sum, p) => sum + (p.remaining_balance ?? 0), 0);

  return (
    <div className="p-6 max-w-4xl mx-auto space-y-6">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <Link href="/portal/patient" className="text-gray-400 hover:text-white"><ArrowLeft className="h-5 w-5" /></Link>
          <Heart className="h-6 w-6 text-rose-400" />
          <h1 className="text-2xl font-bold text-white">Care Plan Portal</h1>
        </div>
        <button onClick={() => setShowRequest(!showRequest)} className="px-4 py-2 bg-rose-600 hover:bg-rose-700 rounded-lg text-white text-sm font-medium">
          Request Payment Plan
        </button>
      </div>

      {profile && (
        <div className="bg-gray-800 border border-gray-700 rounded-lg p-4 flex items-center gap-4">
          <div className="w-10 h-10 rounded-full bg-rose-600/30 flex items-center justify-center text-rose-300 font-bold text-lg">{profile.name?.charAt(0) ?? 'P'}</div>
          <div>
            <div className="text-white font-medium">{profile.name ?? 'Patient'}</div>
            <div className="text-xs text-gray-400">DOB: {profile.date_of_birth ?? '—'} · ID: {profile.member_id ?? '—'}</div>
          </div>
        </div>
      )}

      {showRequest && (
        <motion.div initial={{ opacity: 0, y: -10 }} animate={{ opacity: 1, y: 0 }} className="bg-gray-800 border border-gray-700 rounded-lg p-4 space-y-3">
          <h3 className="text-sm font-semibold text-white">Request a Payment Plan</h3>
          <div className="grid grid-cols-3 gap-3">
            <div>
              <label className="block text-xs text-gray-400 mb-1">Statement</label>
              <select value={reqStatementId} onChange={(e) => setReqStatementId(e.target.value)} className="w-full px-3 py-2 bg-gray-900 border border-gray-600 rounded text-white text-sm">
                <option value="">Select...</option>
                {statements.map((s) => <option key={s.id} value={s.id}>{s.statement_number ?? s.id} — ${s.amount_due}</option>)}
              </select>
            </div>
            <div>
              <label className="block text-xs text-gray-400 mb-1">Monthly Amount ($)</label>
              <input value={reqAmount} onChange={(e) => setReqAmount(e.target.value)} type="number" className="w-full px-3 py-2 bg-gray-900 border border-gray-600 rounded text-white text-sm" />
            </div>
            <div>
              <label className="block text-xs text-gray-400 mb-1">Duration (months)</label>
              <input value={reqMonths} onChange={(e) => setReqMonths(e.target.value)} type="number" className="w-full px-3 py-2 bg-gray-900 border border-gray-600 rounded text-white text-sm" />
            </div>
          </div>
          <button onClick={handleRequestPlan} className="px-4 py-2 bg-rose-600 hover:bg-rose-700 rounded text-white text-sm font-medium">Submit Request</button>
        </motion.div>
      )}

      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        {[
          { label: 'Active Plans', value: activePlans.length, icon: CreditCard, color: 'green' },
          { label: 'Total Remaining', value: `$${totalOwed.toLocaleString()}`, icon: FileText, color: 'rose' },
          { label: 'Documents', value: docs.length, icon: Bell, color: 'blue' },
        ].map((kpi) => (
          <motion.div key={kpi.label} initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} className={`bg-gray-800 border border-${kpi.color}-500/30 rounded-lg p-4`}>
            <div className="flex items-center gap-2 text-gray-400 text-xs mb-1"><kpi.icon className="h-4 w-4" />{kpi.label}</div>
            <div className="text-2xl font-bold text-white">{kpi.value}</div>
          </motion.div>
        ))}
      </div>

      <div className="bg-gray-800 border border-gray-700 rounded-lg overflow-hidden">
        <div className="p-4 border-b border-gray-700">
          <h2 className="text-sm font-semibold text-white">Payment Plans</h2>
        </div>
        <table className="w-full text-sm">
          <thead className="bg-gray-900 text-gray-400 text-xs uppercase">
            <tr>
              <th className="px-4 py-3 text-left">Plan ID</th>
              <th className="px-4 py-3 text-left">Monthly</th>
              <th className="px-4 py-3 text-left">Remaining</th>
              <th className="px-4 py-3 text-left">Next Payment</th>
              <th className="px-4 py-3 text-left">Status</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-700">
            {plans.length === 0 ? (
              <tr><td colSpan={5} className="px-4 py-8 text-center text-gray-500">No payment plans found.</td></tr>
            ) : plans.map((p) => (
              <tr key={p.id} className="hover:bg-gray-700/50">
                <td className="px-4 py-3 text-white font-mono text-xs">{p.id}</td>
                <td className="px-4 py-3 text-gray-300">${p.monthly_amount}</td>
                <td className="px-4 py-3 text-gray-300">${p.remaining_balance}</td>
                <td className="px-4 py-3 text-gray-400">{p.next_payment_date ? new Date(p.next_payment_date).toLocaleDateString() : '—'}</td>
                <td className="px-4 py-3">
                  <span className={`px-2 py-0.5 rounded text-xs font-medium ${p.status === 'active' ? 'bg-green-900/50 text-green-300' : 'bg-gray-700 text-gray-300'}`}>{p.status}</span>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {docs.length > 0 && (
        <div className="bg-gray-800 border border-gray-700 rounded-lg overflow-hidden">
          <div className="p-4 border-b border-gray-700">
            <h2 className="text-sm font-semibold text-white">Care Documents</h2>
          </div>
          <div className="divide-y divide-gray-700">
            {docs.map((d) => (
              <div key={d.id} className="px-4 py-3 flex items-center justify-between hover:bg-gray-700/50">
                <div>
                  <div className="text-sm text-white">{d.name}</div>
                  <div className="text-xs text-gray-400">{d.type} · {d.uploaded_at ? new Date(d.uploaded_at).toLocaleDateString() : '—'}</div>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
