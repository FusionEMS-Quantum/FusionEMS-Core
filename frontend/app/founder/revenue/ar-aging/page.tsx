'use client';

import { useEffect, useMemo, useState } from 'react';
import Link from 'next/link';
import { QuantumEmptyState } from '@/components/ui';
import { getBillingARAgingReport, type BillingARAgingApi } from '@/services/api';

type ArBucket = {
  label: string;
  count: number;
  total_cents: number;
};

type ArAgingResponse = BillingARAgingApi & { buckets: ArBucket[] };

export default function ArAgingPage() {
  const [data, setData] = useState<ArAgingResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    getBillingARAgingReport()
      .then((payload: ArAgingResponse) => setData(payload))
      .catch((e: unknown) => {
        setError(e instanceof Error ? e.message : 'Unable to load A/R aging report');
      })
      .finally(() => setLoading(false));
  }, []);

  const totalArDollars = useMemo(() => {
    if (!data) return 0;
    return data.total_ar_cents / 100;
  }, [data]);

  const payerRows = useMemo(() => {
    if (!data?.payer_breakdown) return [];
    return Object.entries(data.payer_breakdown)
      .map(([payer, stats]) => ({
        payer,
        count: stats.count,
        total_cents: stats.total_cents,
        avg_days: stats.avg_days,
      }))
      .sort((a, b) => b.total_cents - a.total_cents)
      .slice(0, 12);
  }, [data]);

  return (
    <div className="p-5 min-h-screen">
      <div className="hud-rail pb-3 mb-6">
        <div className="micro-caps mb-1">Revenue</div>
        <h1 className="text-h2 font-bold text-zinc-100">A/R Aging Report</h1>
        <p className="text-body text-zinc-500 mt-1">Analyze accounts receivable aging buckets with drill-down by payer.</p>
      </div>

      {loading ? (
        <div className="bg-[#0A0A0B] border border-border-DEFAULT chamfer-8 shadow-elevation-1">
          <QuantumEmptyState title="Loading A/R aging..." description="Pulling live billing telemetry from the backend." icon="activity" />
        </div>
      ) : error ? (
        <div className="bg-[#0A0A0B] border border-border-DEFAULT chamfer-8 shadow-elevation-1">
          <QuantumEmptyState title="A/R aging unavailable" description={error} icon="activity" />
        </div>
      ) : !data ? (
        <div className="bg-[#0A0A0B] border border-border-DEFAULT chamfer-8 shadow-elevation-1">
          <QuantumEmptyState title="No A/R data" description="No claims are currently available for aging analysis." icon="activity" />
        </div>
      ) : (
        <div className="space-y-4">
          <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
            {[
              { label: 'Total A/R', value: `$${totalArDollars.toLocaleString()}` },
              { label: 'Open Claims', value: data.total_claims.toLocaleString() },
              { label: 'Avg Days in A/R', value: `${data.avg_days_in_ar}d` },
              { label: 'As Of', value: data.as_of_date },
            ].map((card) => (
              <div key={card.label} className="bg-[#0A0A0B] border border-border-DEFAULT p-4" style={{ clipPath: 'polygon(0 0,calc(100% - 8px) 0,100% 8px,100% 100%,0 100%)' }}>
                <div className="text-micro text-zinc-500 uppercase tracking-widest">{card.label}</div>
                <div className="text-lg font-bold text-zinc-100 mt-1">{card.value}</div>
              </div>
            ))}
          </div>

          <div className="bg-[#0A0A0B] border border-border-DEFAULT p-4" style={{ clipPath: 'polygon(0 0,calc(100% - 10px) 0,100% 10px,100% 100%,0 100%)' }}>
            <div className="text-micro text-zinc-500 uppercase tracking-widest mb-3">A/R Buckets</div>
            <div className="space-y-3">
              {data.buckets.map((bucket) => {
                const pct = data.total_ar_cents > 0 ? (bucket.total_cents / data.total_ar_cents) * 100 : 0;
                return (
                  <div key={bucket.label}>
                    <div className="flex justify-between text-xs mb-1">
                      <span className="text-zinc-400">{bucket.label} days</span>
                      <span className="text-zinc-100 font-semibold">
                        ${(bucket.total_cents / 100).toLocaleString()} · {bucket.count} claims · {pct.toFixed(1)}%
                      </span>
                    </div>
                    <div className="h-2 bg-zinc-950/40 overflow-hidden">
                      <div className="h-full bg-[#FF4D00]" style={{ width: `${pct}%` }} />
                    </div>
                  </div>
                );
              })}
            </div>
          </div>

          <div className="bg-[#0A0A0B] border border-border-DEFAULT p-4 overflow-x-auto" style={{ clipPath: 'polygon(0 0,calc(100% - 10px) 0,100% 10px,100% 100%,0 100%)' }}>
            <div className="text-micro text-zinc-500 uppercase tracking-widest mb-3">Payer Breakdown</div>
            <table className="w-full text-xs min-w-[560px]">
              <thead>
                <tr className="border-b border-white/10">
                  <th className="text-left py-2 text-zinc-500 uppercase tracking-wider">Payer</th>
                  <th className="text-right py-2 text-zinc-500 uppercase tracking-wider">Claims</th>
                  <th className="text-right py-2 text-zinc-500 uppercase tracking-wider">A/R</th>
                  <th className="text-right py-2 text-zinc-500 uppercase tracking-wider">Avg Days</th>
                </tr>
              </thead>
              <tbody>
                {payerRows.map((row) => (
                  <tr key={row.payer} className="border-b border-white/5">
                    <td className="py-2 text-zinc-200">{row.payer}</td>
                    <td className="py-2 text-right text-zinc-400">{row.count.toLocaleString()}</td>
                    <td className="py-2 text-right text-zinc-100 font-semibold">${(row.total_cents / 100).toLocaleString()}</td>
                    <td className="py-2 text-right text-zinc-400">{row.avg_days}d</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      <div className="pt-4">
        <Link
          href="/founder"
          className="inline-flex items-center gap-2 px-4 py-2 text-label font-label uppercase tracking-[var(--tracking-label)] text-[#FF4D00] hover:text-[#FF4D00] transition-colors duration-fast"
        >
          &larr; Back to Command Center
        </Link>
      </div>
    </div>
  );
}
