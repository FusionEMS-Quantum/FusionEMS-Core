"use client";

import { FormEvent, useState } from 'react';
import { useRouter } from 'next/navigation';
import Link from 'next/link';
import AccessShell from '@/components/shells/AccessShell';

export default function AssistedLivingTransportLoginPage() {
  const router = useRouter();
  const [facilityCode, setFacilityCode] = useState('');
  const [staffId, setStaffId] = useState('');
  const [busy, setBusy] = useState(false);

  const onSubmit = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    setBusy(true);
    setTimeout(() => {
      router.push('/portal/cases?facility_type=assisted_living');
    }, 350);
  };

  return (
    <AccessShell
      title="Assisted Living TransportLink Login"
      subtitle="Assisted living and LTC portal login for scheduling and requesting medical transport."
    >
      <form className="space-y-3" onSubmit={onSubmit}>
        <div className="space-y-1">
          <label className="text-label uppercase tracking-[0.12em] text-zinc-500">Facility Code</label>
          <input
            className="w-full bg-bg-input border border-border-default chamfer-8 px-3 py-2 text-body text-zinc-100 outline-none"
            value={facilityCode}
            onChange={(event) => setFacilityCode(event.target.value)}
            required
          />
        </div>

        <div className="space-y-1">
          <label className="text-label uppercase tracking-[0.12em] text-zinc-500">Staff Login ID</label>
          <input
            className="w-full bg-bg-input border border-border-default chamfer-8 px-3 py-2 text-body text-zinc-100 outline-none"
            value={staffId}
            onChange={(event) => setStaffId(event.target.value)}
            required
          />
        </div>

        <div className="flex gap-2 flex-wrap pt-1">
          <button className="quantum-btn-primary" type="submit" disabled={busy}>
            {busy ? 'Entering…' : 'Enter Assisted Living Portal'}
          </button>
          <Link href="/facility-transport-login" className="quantum-btn">Back</Link>
        </div>
      </form>
    </AccessShell>
  );
}
