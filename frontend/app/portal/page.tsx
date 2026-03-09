'use client';

import React, { useEffect, useState } from 'react';
import Link from 'next/link';
import { QuantumEmptyState } from '@/components/ui';
import { QuantumCardSkeleton } from '@/components/ui';
import { ModuleDashboardShell } from '@/components/shells/PageShells';
import { getPortalAgencyMetrics } from '@/services/api';

interface PortalMetadata {
  stat_cards?: Array<{ label: string; value: number | string; href: string }>;
}

export default function PortalDashboardPage() {
  const [data, setData] = useState<PortalMetadata | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const loadMetrics = async () => {
      try {
        const json = await getPortalAgencyMetrics();
        setData((json.portal as PortalMetadata) || { stat_cards: [] });
      } catch (e) {
        console.warn('Failed to fetch agency dashboard', e);
        setData({ stat_cards: [] });
      } finally {
        setLoading(false);
      }
    };

    void loadMetrics();
  }, []);

  return (
    <ModuleDashboardShell
      title="Agency Dashboard"
      subtitle="Live real-time operational data"
    >
      <div className="mb-4 flex flex-wrap gap-2">
        <Link
          href="/portal/dea-cms"
          className="px-3 py-1.5 text-xs font-semibold bg-blue-600 hover:bg-blue-500 text-white transition-colors"
        >
          DEA / CMS Command
        </Link>
        <Link
          href="/portal/cases"
          className="px-3 py-1.5 text-xs font-semibold border border-border-DEFAULT text-zinc-300 hover:bg-zinc-900 transition-colors"
        >
          Open Cases CMS Gate
        </Link>
      </div>

      {loading ? (
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
          <QuantumCardSkeleton />
          <QuantumCardSkeleton />
          <QuantumCardSkeleton />
        </div>
      ) : (!data?.stat_cards || data.stat_cards.length === 0) ? (
        <QuantumEmptyState
          title="No operational data available"
          description="Your agency currently has no active incidents or claims. Data will appear once the API populates metrics."
          icon="activity"
          action={<button onClick={() => window.location.reload()} className="quantum-btn mt-4">Refresh Data</button>}
        />
      ) : (
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
          {data.stat_cards.map((card) => (
            <Link
              key={card.href}
              href={card.href}
              className="group block bg-black border border-[var(--color-border-default)] chamfer-8 p-5 hover:border-brand-orange/35 transition-colors"
            >
              <div className="text-micro uppercase tracking-widest text-zinc-500 mb-3 group-hover:text-brand-orange/70 transition-colors">
                {card.label}
              </div>
              <div className="text-3xl font-bold text-zinc-100">{card.value}</div>
            </Link>
          ))}
        </div>
      )}
    </ModuleDashboardShell>
  );
}
