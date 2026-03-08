'use client';

import React, { useState } from 'react';

type StudioTab = 'catalog' | 'pricebooks' | 'estimator';

const TABS: { id: StudioTab; label: string }[] = [
  { id: 'catalog', label: 'Product Catalog' },
  { id: 'pricebooks', label: 'Pricebooks' },
  { id: 'estimator', label: 'Price Estimator' },
];

interface PriceEntry {
  tier: string;
  monthly: number;
  perTransport?: number;
  description: string;
}

const CATALOG: { product: string; key: string; color: string; prices: PriceEntry[] }[] = [
  {
    product: 'Scheduling Only',
    key: 'SCHEDULING_ONLY',
    color: 'var(--color-system-billing)',
    prices: [
      { tier: 'S1 — Starter', monthly: 199, description: 'Up to 10 crew, basic scheduling' },
      { tier: 'S2 — Growth', monthly: 399, description: 'Up to 30 crew, swap/trade/timeoff' },
      { tier: 'S3 — Scale', monthly: 699, description: 'Unlimited crew, AI draft, coverage engine' },
    ],
  },
  {
    product: 'Billing Automation',
    key: 'BILLING_AUTOMATION_BASE',
    color: '#FF4D00',
    prices: [
      { tier: 'B1 — Essentials', monthly: 399, perTransport: 6.00, description: '< 100 transports/mo' },
      { tier: 'B2 — Standard', monthly: 599, perTransport: 5.00, description: '100–300 transports/mo' },
      { tier: 'B3 — Pro', monthly: 999, perTransport: 4.00, description: '300–600 transports/mo' },
      { tier: 'B4 — Enterprise', monthly: 1499, perTransport: 3.25, description: '600+ transports/mo' },
    ],
  },
  {
    product: 'CCT Transport Ops',
    key: 'CCT_TRANSPORT_OPS_ADDON',
    color: 'var(--color-system-compliance)',
    prices: [
      { tier: 'CCT Add-on', monthly: 399, description: 'Critical care transport dispatch + ePCR fields' },
    ],
  },
  {
    product: 'HEMS Module',
    key: 'HEMS_ADDON',
    color: 'var(--q-yellow)',
    prices: [
      { tier: 'HEMS Add-on', monthly: 750, description: 'Helicopter/fixed-wing pilot portal + acceptance checklist + risk audit' },
    ],
  },
  {
    product: 'TRIP Pack (WI)',
    key: 'TRIP_PACK_ADDON',
    color: 'var(--q-green)',
    prices: [
      { tier: 'TRIP Add-on', monthly: 199, description: 'Wisconsin Tax Refund Intercept — government agencies only' },
    ],
  },
];

function StatCard({ label, value, sub }: { label: string; value: string; sub?: string }) {
  return (
    <div className="bg-[#050505] border border-white/[0.07] chamfer-4 px-4 py-3">
      <div className="text-micro uppercase tracking-widest text-zinc-500 mb-1">{label}</div>
      <div className="text-lg font-bold text-zinc-100">{value}</div>
      {sub && <div className="text-micro text-zinc-500 mt-0.5">{sub}</div>}
    </div>
  );
}

function CatalogTab() {
  return (
    <div className="space-y-4">
      <div className="grid grid-cols-4 gap-3 mb-6">
        <StatCard label="Active Products" value="8" />
        <StatCard label="Active Prices" value="10" />
        <StatCard label="Active Pricebook" value="v1.0" sub="published" />
        <StatCard label="Stripe Sync" value="Live" sub="SSM-backed" />
      </div>

      {CATALOG.map((product) => (
        <div key={product.key} className="bg-[#050505] border border-white/[0.07] chamfer-4 overflow-hidden">
          <div className="flex items-center justify-between px-4 py-3 border-b border-border-subtle">
            <div className="flex items-center gap-3">
              <span className="w-2 h-2  flex-shrink-0" style={{ backgroundColor: product.color }} />
              <span className="text-sm font-semibold text-zinc-100">{product.product}</span>
              <span className="text-micro text-zinc-500 font-mono">{product.key}</span>
            </div>
            <button className="h-6 px-2.5 bg-[#FF4D00]-ghost border border-brand-orange/[0.2] text-micro font-semibold uppercase tracking-wider text-[#FF4D00] hover:bg-brand-orange/[0.14] transition-colors chamfer-4">
              Edit
            </button>
          </div>
          <div className="divide-y divide-white/[0.04]">
            {product.prices.map((price) => (
              <div key={price.tier} className="flex items-center justify-between px-4 py-3">
                <div>
                  <div className="text-xs font-medium text-zinc-100">{price.tier}</div>
                  <div className="text-body text-zinc-500 mt-0.5">{price.description}</div>
                </div>
                <div className="text-right">
                  <div className="text-sm font-bold" style={{ color: product.color }}>
                    ${price.monthly.toLocaleString()}<span className="text-micro font-normal text-zinc-500">/mo</span>
                  </div>
                  {price.perTransport && (
                    <div className="text-micro text-zinc-500">+ ${price.perTransport.toFixed(2)}/transport</div>
                  )}
                </div>
              </div>
            ))}
          </div>
        </div>
      ))}
    </div>
  );
}

function PricebooksTab() {
  return (
    <div>
      <div className="flex items-center justify-between mb-4">
        <div className="text-xs text-zinc-400">Versioned pricebooks — draft → scheduled → active → archived</div>
        <button className="h-7 px-3 bg-brand-orange/[0.1] border border-brand-orange/[0.25] text-micro font-semibold uppercase tracking-wider text-[#FF4D00] hover:bg-brand-orange/[0.18] transition-colors chamfer-4">
          New Draft
        </button>
      </div>

      <div className="bg-[#050505] border border-white/[0.07] chamfer-4 overflow-hidden">
        <div className="grid grid-cols-6 px-4 py-2 border-b border-border-subtle text-micro uppercase tracking-widest text-zinc-500">
          <span>Version</span><span>Label</span><span>Status</span><span>Effective Date</span><span>Created By</span><span>Actions</span>
        </div>
        <div className="px-4 py-3 grid grid-cols-6 items-center border-b border-border-subtle">
          <span className="text-xs font-mono text-zinc-100">v1.0</span>
          <span className="text-xs text-zinc-100">Initial Catalog</span>
          <span className="inline-flex items-center px-2 py-0.5 text-micro font-semibold uppercase tracking-wider chamfer-4 bg-green-500/[0.12] text-status-active w-fit">Active</span>
          <span className="text-xs text-zinc-400">2026-01-01</span>
          <span className="text-xs text-zinc-400">System</span>
          <div className="flex gap-2">
            <button className="h-6 px-2.5 bg-zinc-950/[0.04] border border-border-DEFAULT text-micro text-zinc-400 hover:text-zinc-100 transition-colors chamfer-4">View</button>
            <button className="h-6 px-2.5 bg-zinc-950/[0.04] border border-border-DEFAULT text-micro text-zinc-400 hover:text-zinc-100 transition-colors chamfer-4">Clone</button>
          </div>
        </div>
        <div className="px-4 py-8 text-center text-xs text-zinc-500">Draft a new pricebook to test pricing changes before activating</div>
      </div>
    </div>
  );
}

function EstimatorTab() {
  const [plan, setPlan] = useState('SCHEDULING_ONLY');
  const [tier, setTier] = useState('S1');
  const [transports, setTransports] = useState(150);
  const [addons, setAddons] = useState<string[]>([]);

  const toggleAddon = (key: string) => {
    setAddons((prev) => prev.includes(key) ? prev.filter((a) => a !== key) : [...prev, key]);
  };

  const baseMonthly =
    plan === 'SCHEDULING_ONLY'
      ? (tier === 'S1' ? 199 : tier === 'S2' ? 399 : 699)
      : plan === 'BILLING_AUTOMATION_BASE'
      ? (tier === 'B1' ? 399 : tier === 'B2' ? 599 : tier === 'B3' ? 999 : 1499)
      : 0;

  const perTransportRate =
    plan === 'BILLING_AUTOMATION_BASE'
      ? (tier === 'B1' ? 6 : tier === 'B2' ? 5 : tier === 'B3' ? 4 : 3.25)
      : 0;

  const addonPrices: Record<string, number> = { CCT: 399, HEMS: 750, TRIP: 199 };
  const addonLabels: Record<string, string> = { CCT: 'CCT Add-on', HEMS: 'HEMS Add-on', TRIP: 'TRIP Pack' };
  const addonTotal = addons.reduce((sum, a) => sum + (addonPrices[a] ?? 0), 0);
  const total = baseMonthly + perTransportRate * transports + addonTotal;

  return (
    <div className="grid grid-cols-2 gap-6">
      <div className="space-y-4">
        <div className="bg-[#050505] border border-white/[0.07] chamfer-4 p-4">
          <div className="text-micro uppercase tracking-widest text-zinc-500 mb-3">Base Plan</div>
          <div className="flex gap-2 mb-3">
            {['SCHEDULING_ONLY', 'BILLING_AUTOMATION_BASE'].map((p) => (
              <button
                key={p}
                onClick={() => { setPlan(p); setTier(p === 'SCHEDULING_ONLY' ? 'S1' : 'B1'); }}
                className={`flex-1 h-8 text-body font-medium chamfer-4 border transition-colors ${
                  plan === p
                    ? 'bg-brand-orange/[0.15] border-brand-orange/[0.4] text-[#FF4D00]'
                    : 'bg-zinc-950/[0.03] border-border-DEFAULT text-zinc-400 hover:text-zinc-100'
                }`}
              >
                {p === 'SCHEDULING_ONLY' ? 'Scheduling' : 'Billing Auto'}
              </button>
            ))}
          </div>
          <div className="flex gap-2">
            {(plan === 'SCHEDULING_ONLY' ? ['S1', 'S2', 'S3'] : ['B1', 'B2', 'B3', 'B4']).map((t) => (
              <button
                key={t}
                onClick={() => setTier(t)}
                className={`flex-1 h-7 text-body font-mono chamfer-4 border transition-colors ${
                  tier === t
                    ? 'bg-cyan-500/[0.12] border-cyan-500/[0.3] text-system-billing'
                    : 'bg-zinc-950/[0.03] border-border-DEFAULT text-zinc-500 hover:text-zinc-100'
                }`}
              >
                {t}
              </button>
            ))}
          </div>
        </div>

        {plan === 'BILLING_AUTOMATION_BASE' && (
          <div className="bg-[#050505] border border-white/[0.07] chamfer-4 p-4">
            <div className="flex items-center justify-between mb-2">
              <div className="text-micro uppercase tracking-widest text-zinc-500">Monthly Transports</div>
              <span className="text-sm font-bold text-zinc-100">{transports}</span>
            </div>
            <input
              type="range"
              min={10}
              max={1000}
              step={10}
              value={transports}
              onChange={(e) => setTransports(Number(e.target.value))}
              className="w-full accent-[#FF4D00]"
            />
            <div className="flex justify-between text-micro text-zinc-500 mt-1">
              <span>10</span><span>500</span><span>1000</span>
            </div>
          </div>
        )}

        <div className="bg-[#050505] border border-white/[0.07] chamfer-4 p-4">
          <div className="text-micro uppercase tracking-widest text-zinc-500 mb-3">Add-ons</div>
          {[
            { key: 'CCT', label: 'CCT Transport Ops', price: 399 },
            { key: 'HEMS', label: 'HEMS Module', price: 750 },
            { key: 'TRIP', label: 'TRIP Pack (WI Gov)', price: 199 },
          ].map((addon) => (
            <label key={addon.key} className="flex items-center justify-between py-2 border-b border-border-subtle last:border-0 cursor-pointer">
              <div className="flex items-center gap-2">
                <input
                  type="checkbox"
                  checked={addons.includes(addon.key)}
                  onChange={() => toggleAddon(addon.key)}
                  className="accent-[#FF4D00]"
                />
                <span className="text-xs text-zinc-100">{addon.label}</span>
              </div>
              <span className="text-xs text-zinc-400">+${addon.price}/mo</span>
            </label>
          ))}
        </div>
      </div>

      <div className="bg-[#050505] border border-brand-orange/[0.2] chamfer-4 p-5 flex flex-col">
        <div className="text-micro uppercase tracking-widest text-[#FF4D00]-dim mb-4">Monthly Estimate</div>
        <div className="space-y-3 flex-1">
          <div className="flex justify-between text-xs">
            <span className="text-zinc-400">
              Base ({plan === 'SCHEDULING_ONLY' ? `Scheduling ${tier}` : `Billing Auto ${tier}`})
            </span>
            <span className="text-zinc-100 font-medium">${baseMonthly.toLocaleString()}</span>
          </div>
          {perTransportRate > 0 && (
            <div className="flex justify-between text-xs">
              <span className="text-zinc-400">Usage ({transports} × ${perTransportRate.toFixed(2)})</span>
              <span className="text-zinc-100 font-medium">${(perTransportRate * transports).toFixed(2)}</span>
            </div>
          )}
          {addons.map((a) => (
            <div key={a} className="flex justify-between text-xs">
              <span className="text-zinc-400">{addonLabels[a]}</span>
              <span className="text-zinc-100 font-medium">${addonPrices[a].toLocaleString()}</span>
            </div>
          ))}
        </div>
        <div className="border-t border-border-DEFAULT pt-4 mt-4">
          <div className="flex justify-between items-end">
            <span className="text-xs text-zinc-400">Total / month</span>
            <span className="text-2xl font-black text-[#FF4D00]">
              ${total.toLocaleString('en-US', { minimumFractionDigits: 2 })}
            </span>
          </div>
          <div className="text-micro text-zinc-500 mt-1">
            Annual: ${(total * 12).toLocaleString('en-US', { minimumFractionDigits: 2 })}
          </div>
        </div>
      </div>
    </div>
  );
}

export default function PricingStudioPage() {
  const [activeTab, setActiveTab] = useState<StudioTab>('catalog');

  const content: Record<StudioTab, React.ReactNode> = {
    catalog: <CatalogTab />,
    pricebooks: <PricebooksTab />,
    estimator: <EstimatorTab />,
  };

  return (
    <div className="p-6 max-w-[1300px]">
      <div className="mb-6">
        <div className="text-micro uppercase tracking-widest text-zinc-500 mb-1">Founder OS</div>
        <h1 className="text-xl font-bold text-zinc-100">Pricing Studio</h1>
        <p className="text-xs text-zinc-500 mt-1">Product catalog, versioned pricebooks, price estimator, and Stripe catalog management</p>
      </div>

      <div className="flex gap-0 mb-6 border-b border-border-DEFAULT">
        {TABS.map((tab) => (
          <button
            key={tab.id}
            onClick={() => setActiveTab(tab.id)}
            className={`relative px-4 py-2.5 text-xs font-medium transition-colors ${
              activeTab === tab.id ? 'text-zinc-100' : 'text-zinc-500 hover:text-zinc-100'
            }`}
          >
            {tab.label}
            {activeTab === tab.id && (
              <span className="absolute bottom-0 left-0 right-0 h-[2px] bg-[#FF4D00]" />
            )}
          </button>
        ))}
      </div>

      <div>{content[activeTab]}</div>
    </div>
  );
}
