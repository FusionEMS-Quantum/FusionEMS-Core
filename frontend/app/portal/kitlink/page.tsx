"use client";
import { TabBar, TabPanel } from '@/components/ui/InteractionPatterns';
import { ModuleDashboardShell } from '@/components/shells/PageShells';
import { MetricCard } from '@/components/ui/MetricCard';
import { Suspense, useState, useEffect } from "react";
import { useSearchParams } from "next/navigation";

const TABS = ["Dashboard", "Items & Formulary", "Kit Templates", "Unit Layouts", "AR Markers", "Reports"] as const;
type Tab = typeof TABS[number];

const API = "/api/v1/kitlink";

function useApi(path: string, tenantId: string) {
  const [data, setData] = useState<any>(null);
  const [loading, setLoading] = useState(false);
  useEffect(() => {
    if (!tenantId) return;
    setLoading(true);
    fetch(`${API}${path}?tenant_id=${tenantId}`)
      .then((r) => r.json())
      .then(setData)
      .catch((e: unknown) => { console.warn('[kitlink fetch error]', e); })
      .finally(() => setLoading(false));
  }, [path, tenantId]);
  return { data, loading };
}

async function post(path: string, tenantId: string, body: object): Promise<any> {
  try {
    const r = await fetch(`${API}${path}?tenant_id=${tenantId}`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    });
    return r.json();
  } catch (e: unknown) {
    console.warn('[kitlink post error]', e);
    return {};
  }
}

const TAB_ITEMS = TABS.map((t) => ({ id: t, label: t }));

function KitLinkPageInner() {
  const params = useSearchParams();
  const tenantId = params.get("tenant_id") ?? "";
  const [activeTab, setActiveTab] = useState<Tab>("Dashboard");

  return (
    <ModuleDashboardShell
      title="KitLink AR"
      subtitle="Inventory · Narcotics · AR Markers · Compliance"
      accentColor="var(--color-emerald-500, #10b981)"
      headerActions={
        <a
          href={`/portal/kitlink/wizard?tenant_id=${tenantId}`}
          className="px-3 py-1.5 bg-emerald-600 hover:bg-emerald-500 chamfer-4 text-xs font-medium transition-colors"
        >
          1-Day Go-Live Wizard
        </a>
      }
      toolbar={<TabBar tabs={TAB_ITEMS} activeTab={activeTab} onTabChange={(id) => setActiveTab(id as Tab)} />}
    >
      <TabPanel tabId="Dashboard" activeTab={activeTab}><DashboardTab tenantId={tenantId} /></TabPanel>
      <TabPanel tabId="Items & Formulary" activeTab={activeTab}><ItemsTab tenantId={tenantId} /></TabPanel>
      <TabPanel tabId="Kit Templates" activeTab={activeTab}><KitsTab tenantId={tenantId} /></TabPanel>
      <TabPanel tabId="Unit Layouts" activeTab={activeTab}><LayoutsTab tenantId={tenantId} /></TabPanel>
      <TabPanel tabId="AR Markers" activeTab={activeTab}><MarkersTab tenantId={tenantId} /></TabPanel>
      <TabPanel tabId="Reports" activeTab={activeTab}><ReportsTab tenantId={tenantId} /></TabPanel>
    </ModuleDashboardShell>
  );
}

function DashboardTab({ tenantId }: { tenantId: string }) {
  const { data: expiringData } = useApi("/reports/expiring?days=30", tenantId);
  const { data: discData } = useApi("/reports/discrepancies", tenantId);
  const { data: parData } = useApi("/reports/par-misses", tenantId);
  const { data: kits } = useApi("/kits", tenantId);

  return (
    <div className="space-y-6">
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <MetricCard label="Kit Templates" value={kits ? String(kits.length) : "—"} compact />
        <MetricCard label="Expiring (30d)" value={String(expiringData?.expiring_count ?? "—")} compact />
        <MetricCard label="Open Discrepancies" value={String(discData?.open_count ?? "—")} compact />
        <MetricCard label="PAR Misses" value={String(parData?.par_miss_count ?? "—")} compact />
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        <div className="chamfer-8 border border-border-subtle bg-bg-panel p-4">
          <h3 className="text-sm font-semibold text-text-primary mb-3">Quick Actions</h3>
          <div className="space-y-2">
            {[
              { label: "Clone Starter Kit", href: "#", action: "kits" },
              { label: "Generate Marker Sheet", href: "#", action: "markers" },
              { label: "Run Expiration Sweep", href: "#", action: "sweep" },
              { label: "Trans 309 Inspection", href: `/portal/kitlink/inspection?tenant_id=${tenantId}`, action: "inspect" },
            ].map((a) => (
              <a
                key={a.label}
                href={a.href !== "#" ? a.href : undefined}
                className="flex items-center justify-between px-3 py-2 chamfer-4 bg-bg-raised hover:bg-bg-overlay text-sm text-text-primary cursor-pointer transition-colors"
              >
                <span>{a.label}</span>
                <span className="text-text-muted">→</span>
              </a>
            ))}
          </div>
        </div>

        <div className="chamfer-8 border border-border-subtle bg-bg-panel p-4">
          <h3 className="text-sm font-semibold text-text-primary mb-3">Open Narcotics Discrepancies</h3>
          {discData?.items?.length ? (
            <div className="space-y-2">
              {discData.items.slice(0, 5).map((item: any) => (
                <div key={item.id} className="flex items-start gap-2 text-xs">
                  <span className="mt-0.5 w-2 h-2 rounded-full bg-red-500 flex-shrink-0" />
                  <div>
                    <p className="text-text-primary">{item.data?.item_name ?? "Unknown item"}</p>
                    <p className="text-text-muted">
                      Expected {item.data?.expected_qty} · Found {item.data?.actual_qty} · Delta {item.data?.delta}
                    </p>
                  </div>
                </div>
              ))}
            </div>
          ) : (
            <p className="text-sm text-text-muted">No open discrepancies</p>
          )}
        </div>
      </div>
    </div>
  );
}

function ItemsTab({ tenantId }: { tenantId: string }) {
  const { data: items, loading } = useApi("/items", tenantId);
  const [form, setForm] = useState({ name: "", unit: "each", category: "" });
  const [saving, setSaving] = useState(false);

  async function submit() {
    setSaving(true);
    await post("/items", tenantId, form);
    setSaving(false);
    setForm({ name: "", unit: "each", category: "" });
    window.location.reload();
  }

  return (
    <div className="space-y-6">
      <div className="chamfer-8 border border-border-subtle bg-bg-panel p-4">
        <h3 className="text-sm font-semibold text-text-primary mb-3">Add Inventory Item</h3>
        <div className="grid grid-cols-3 gap-3">
          <input
            className="px-3 py-2 bg-bg-raised border border-border-DEFAULT chamfer-4 text-sm text-text-primary placeholder-gray-500"
            placeholder="Item name"
            value={form.name}
            onChange={(e) => setForm({ ...form, name: e.target.value })}
          />
          <input
            className="px-3 py-2 bg-bg-raised border border-border-DEFAULT chamfer-4 text-sm text-text-primary placeholder-gray-500"
            placeholder="Unit (each, vial, bag)"
            value={form.unit}
            onChange={(e) => setForm({ ...form, unit: e.target.value })}
          />
          <input
            className="px-3 py-2 bg-bg-raised border border-border-DEFAULT chamfer-4 text-sm text-text-primary placeholder-gray-500"
            placeholder="Category"
            value={form.category}
            onChange={(e) => setForm({ ...form, category: e.target.value })}
          />
        </div>
        <button
          onClick={submit}
          disabled={saving || !form.name}
          className="mt-3 px-4 py-2 bg-emerald-600 hover:bg-emerald-500 disabled:opacity-50 chamfer-4 text-sm font-medium transition-colors"
        >
          {saving ? "Saving…" : "Add Item"}
        </button>
      </div>

      <div className="chamfer-8 border border-border-subtle overflow-hidden">
        <table className="w-full text-sm">
          <thead className="bg-bg-raised text-text-muted text-xs">
            <tr>
              <th className="px-4 py-2 text-left">Name</th>
              <th className="px-4 py-2 text-left">Unit</th>
              <th className="px-4 py-2 text-left">Category</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-border-subtle">
            {loading && (
              <tr>
                <td colSpan={3} className="px-4 py-6 text-center text-text-muted">Loading…</td>
              </tr>
            )}
            {items?.map((item: any) => (
              <tr key={item.id} className="hover:bg-bg-raised/50">
                <td className="px-4 py-2 text-text-primary">{item.data?.name}</td>
                <td className="px-4 py-2 text-text-muted">{item.data?.unit}</td>
                <td className="px-4 py-2 text-text-muted">{item.data?.category ?? "—"}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}

function KitsTab({ tenantId }: { tenantId: string }) {
  const { data: kits, loading } = useApi("/kits", tenantId);
  const [cloning, setCloning] = useState<string | null>(null);
  const [cloned, setCloned] = useState<string[]>([]);

  const starters = ["NARC_BOX_V1", "AIRWAY_KIT_V1", "TRAUMA_KIT_V1", "IV_KIT_V1"];

  async function cloneStarter(key: string) {
    setCloning(key);
    await post(`/kits/starter/${key}/clone`, tenantId, {});
    setCloned((p) => [...p, key]);
    setCloning(null);
  }

  return (
    <div className="space-y-6">
      <div className="chamfer-8 border border-border-subtle bg-bg-panel p-4">
        <h3 className="text-sm font-semibold text-text-primary mb-1">Load Starter Templates</h3>
        <p className="text-xs text-text-muted mb-3">Clone a preconfigured kit template into your account.</p>
        <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
          {starters.map((key) => (
            <button
              key={key}
              onClick={() => cloneStarter(key)}
              disabled={!!cloning || cloned.includes(key)}
              className={`px-3 py-2 chamfer-4 text-xs font-medium border transition-colors ${
                cloned.includes(key)
                  ? "border-emerald-700 bg-emerald-900/30 text-emerald-400 cursor-default"
                  : "border-border-DEFAULT bg-bg-raised hover:bg-bg-overlay text-text-primary"
              }`}
            >
              {cloning === key ? "Cloning…" : cloned.includes(key) ? `${key} (loaded)` : key}
            </button>
          ))}
        </div>
      </div>

      <div className="chamfer-8 border border-border-subtle overflow-hidden">
        <table className="w-full text-sm">
          <thead className="bg-bg-raised text-text-muted text-xs">
            <tr>
              <th className="px-4 py-2 text-left">Kit Name</th>
              <th className="px-4 py-2 text-left">Type</th>
              <th className="px-4 py-2 text-left">Requires Seal</th>
              <th className="px-4 py-2 text-left">Source</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-border-subtle">
            {loading && (
              <tr>
                <td colSpan={4} className="px-4 py-6 text-center text-text-muted">Loading…</td>
              </tr>
            )}
            {kits?.map((kit: any) => (
              <tr key={kit.id} className="hover:bg-bg-raised/50">
                <td className="px-4 py-2 text-text-primary">{kit.data?.name}</td>
                <td className="px-4 py-2 text-text-muted">{kit.data?.kit_type}</td>
                <td className="px-4 py-2">
                  <span className={`px-2 py-0.5 chamfer-4 text-xs ${kit.data?.requires_seal ? "bg-amber-900/40 text-amber-400" : "bg-bg-overlay text-text-muted"}`}>
                    {kit.data?.requires_seal ? "Yes" : "No"}
                  </span>
                </td>
                <td className="px-4 py-2 text-text-muted text-xs">{kit.data?.source_key ?? "custom"}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}

function LayoutsTab({ tenantId }: { tenantId: string }) {
  const { data: layouts, loading } = useApi("/layouts", tenantId);
  const [form, setForm] = useState({ unit_id: "", unit_name: "" });
  const [saving, setSaving] = useState(false);
  const [publishing, setPublishing] = useState<string | null>(null);

  async function createLayout() {
    setSaving(true);
    await post("/layouts", tenantId, form);
    setSaving(false);
    setForm({ unit_id: "", unit_name: "" });
    window.location.reload();
  }

  async function publishLayout(id: string) {
    setPublishing(id);
    await post(`/layouts/${id}/publish`, tenantId, {});
    setPublishing(null);
    window.location.reload();
  }

  return (
    <div className="space-y-6">
      <div className="chamfer-8 border border-border-subtle bg-bg-panel p-4">
        <h3 className="text-sm font-semibold text-text-primary mb-3">Create Unit Layout</h3>
        <div className="grid grid-cols-2 gap-3">
          <input
            className="px-3 py-2 bg-bg-raised border border-border-DEFAULT chamfer-4 text-sm text-text-primary placeholder-gray-500"
            placeholder="Unit ID (e.g. M12)"
            value={form.unit_id}
            onChange={(e) => setForm({ ...form, unit_id: e.target.value })}
          />
          <input
            className="px-3 py-2 bg-bg-raised border border-border-DEFAULT chamfer-4 text-sm text-text-primary placeholder-gray-500"
            placeholder="Unit name"
            value={form.unit_name}
            onChange={(e) => setForm({ ...form, unit_name: e.target.value })}
          />
        </div>
        <button
          onClick={createLayout}
          disabled={saving || !form.unit_id}
          className="mt-3 px-4 py-2 bg-emerald-600 hover:bg-emerald-500 disabled:opacity-50 chamfer-4 text-sm font-medium transition-colors"
        >
          {saving ? "Creating…" : "Create Layout"}
        </button>
      </div>

      <div className="chamfer-8 border border-border-subtle overflow-hidden">
        <table className="w-full text-sm">
          <thead className="bg-bg-raised text-text-muted text-xs">
            <tr>
              <th className="px-4 py-2 text-left">Unit</th>
              <th className="px-4 py-2 text-left">Status</th>
              <th className="px-4 py-2 text-left">Actions</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-border-subtle">
            {loading && (
              <tr>
                <td colSpan={3} className="px-4 py-6 text-center text-text-muted">Loading…</td>
              </tr>
            )}
            {layouts?.map((layout: any) => (
              <tr key={layout.id} className="hover:bg-bg-raised/50">
                <td className="px-4 py-2 text-text-primary">{layout.data?.unit_name ?? layout.data?.unit_id}</td>
                <td className="px-4 py-2">
                  <span className={`px-2 py-0.5 chamfer-4 text-xs ${layout.data?.status === "active" ? "bg-emerald-900/40 text-emerald-400" : "bg-bg-overlay text-text-muted"}`}>
                    {layout.data?.status ?? "draft"}
                  </span>
                </td>
                <td className="px-4 py-2">
                  {layout.data?.status !== "active" && (
                    <button
                      onClick={() => publishLayout(layout.id)}
                      disabled={publishing === layout.id}
                      className="px-3 py-1 bg-emerald-700 hover:bg-emerald-600 chamfer-4 text-xs transition-colors"
                    >
                      {publishing === layout.id ? "Publishing…" : "Publish"}
                    </button>
                  )}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}

function MarkersTab({ tenantId }: { tenantId: string }) {
  const [form, setForm] = useState({ entity_type: "kit", entity_id: "", format: "qr" });
  const [generating, setGenerating] = useState(false);
  const [result, setResult] = useState<any>(null);
  const [resolveCode, setResolveCode] = useState("");
  const [resolveResult, setResolveResult] = useState<any>(null);

  async function generateMarker() {
    setGenerating(true);
    const r = await post("/ar/markers/generate", tenantId, form);
    setResult(r);
    setGenerating(false);
  }

  async function resolveMarker() {
    try {
      const r = await fetch(`${API}/ar/resolve/${resolveCode}?tenant_id=${tenantId}`);
      setResolveResult(await r.json());
    } catch (err: unknown) {
      console.warn("[kitlink]", err);
    }
  }

  return (
    <div className="space-y-6">
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        <div className="chamfer-8 border border-border-subtle bg-bg-panel p-4">
          <h3 className="text-sm font-semibold text-text-primary mb-3">AR Marker Builder</h3>
          <div className="space-y-3">
            <select
              className="w-full px-3 py-2 bg-bg-raised border border-border-DEFAULT chamfer-4 text-sm text-text-primary"
              value={form.entity_type}
              onChange={(e) => setForm({ ...form, entity_type: e.target.value })}
            >
              <option value="kit">Kit</option>
              <option value="unit">Unit</option>
              <option value="stock_location">Stock Location</option>
            </select>
            <input
              className="w-full px-3 py-2 bg-bg-raised border border-border-DEFAULT chamfer-4 text-sm text-text-primary placeholder-gray-500"
              placeholder="Entity ID"
              value={form.entity_id}
              onChange={(e) => setForm({ ...form, entity_id: e.target.value })}
            />
            <select
              className="w-full px-3 py-2 bg-bg-raised border border-border-DEFAULT chamfer-4 text-sm text-text-primary"
              value={form.format}
              onChange={(e) => setForm({ ...form, format: e.target.value })}
            >
              <option value="qr">QR Code</option>
              <option value="code128">Code 128</option>
            </select>
            <button
              onClick={generateMarker}
              disabled={generating || !form.entity_id}
              className="w-full px-4 py-2 bg-emerald-600 hover:bg-emerald-500 disabled:opacity-50 chamfer-4 text-sm font-medium transition-colors"
            >
              {generating ? "Generating…" : "Generate Marker"}
            </button>
          </div>
          {result && (
            <div className="mt-3 p-3 bg-bg-raised chamfer-4 text-xs">
              <p className="text-emerald-400 font-mono">{result.marker_code}</p>
              <p className="text-text-muted mt-1">Status: {result.status}</p>
            </div>
          )}
        </div>

        <div className="chamfer-8 border border-border-subtle bg-bg-panel p-4">
          <h3 className="text-sm font-semibold text-text-primary mb-3">Test Marker Resolve</h3>
          <div className="space-y-3">
            <input
              className="w-full px-3 py-2 bg-bg-raised border border-border-DEFAULT chamfer-4 text-sm text-text-primary placeholder-gray-500 font-mono"
              placeholder="KL-XXXXXXXX"
              value={resolveCode}
              onChange={(e) => setResolveCode(e.target.value)}
            />
            <button
              onClick={resolveMarker}
              disabled={!resolveCode}
              className="w-full px-4 py-2 bg-blue-600 hover:bg-blue-500 disabled:opacity-50 chamfer-4 text-sm font-medium transition-colors"
            >
              Resolve
            </button>
          </div>
          {resolveResult && (
            <div className="mt-3 p-3 bg-bg-raised chamfer-4 text-xs space-y-1">
              <p className="text-text-secondary">Entity: <span className="text-blue-400">{resolveResult.entity_type}</span></p>
              <p className="text-text-secondary">Status: <span className="text-emerald-400">{resolveResult.status}</span></p>
              <p className="text-text-secondary">Next steps:</p>
              <ul className="pl-3 space-y-0.5">
                {resolveResult.next_steps?.map((s: string) => (
                  <li key={s} className="text-text-muted">• {s}</li>
                ))}
              </ul>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

function ReportsTab({ tenantId }: { tenantId: string }) {
  const { data: expiring } = useApi("/reports/expiring?days=30", tenantId);
  const { data: disc } = useApi("/reports/discrepancies", tenantId);
  const { data: parMisses } = useApi("/reports/par-misses", tenantId);
  const { data: narcLog } = useApi("/reports/narcotics-log", tenantId);

  return (
    <div className="space-y-6">
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        <ReportPanel
          title="Expiring Items (30d)"
          count={expiring?.expiring_count}
          items={expiring?.items?.slice(0, 8)}
          renderItem={(i: any) => (
            <div className="flex justify-between text-xs">
              <span className="text-text-secondary">{i.data?.item_id ?? "Item"}</span>
              <span className="text-amber-400">{i.data?.expiration_date}</span>
            </div>
          )}
        />
        <ReportPanel
          title="Open Narc Discrepancies"
          count={disc?.open_count}
          items={disc?.items?.slice(0, 8)}
          renderItem={(i: any) => (
            <div className="flex justify-between text-xs">
              <span className="text-text-secondary">{i.data?.item_name}</span>
              <span className="text-red-400">Δ {i.data?.delta}</span>
            </div>
          )}
        />
        <ReportPanel
          title="PAR Misses"
          count={parMisses?.par_miss_count}
          items={parMisses?.items?.slice(0, 8)}
          renderItem={(i: any) => (
            <div className="flex justify-between text-xs">
              <span className="text-text-secondary">{i.data?.item_id ?? "Item"}</span>
              <span className="text-amber-400">{i.data?.current_qty} / {i.data?.par_qty} PAR</span>
            </div>
          )}
        />
        <ReportPanel
          title="Narcotics Log"
          count={(narcLog?.counts?.length ?? 0) + (narcLog?.waste_events?.length ?? 0)}
          items={narcLog?.waste_events?.slice(0, 8)}
          renderItem={(i: any) => (
            <div className="flex justify-between text-xs">
              <span className="text-text-secondary">{i.data?.item_name ?? "Waste event"}</span>
              <span className="text-text-muted">{i.data?.wasted_at?.slice(0, 10)}</span>
            </div>
          )}
        />
      </div>
    </div>
  );
}

function ReportPanel({ title, count, items, renderItem }: { title: string; count: number | undefined; items: any[] | undefined; renderItem: (_i: any) => React.ReactNode }) {
  return (
    <div className="chamfer-8 border border-border-subtle bg-bg-panel p-4">
      <div className="flex items-center justify-between mb-3">
        <h3 className="text-sm font-semibold text-text-primary">{title}</h3>
        {count !== undefined && (
          <span className="px-2 py-0.5 bg-bg-overlay chamfer-4 text-xs text-text-secondary">{count}</span>
        )}
      </div>
      {items?.length ? (
        <div className="space-y-2">{items.map((i, idx) => <div key={idx}>{renderItem(i)}</div>)}</div>
      ) : (
        <p className="text-xs text-text-muted">No data</p>
      )}
    </div>
  );
}

export default function KitLinkPage() {
  return (
    <Suspense fallback={<div className="min-h-screen bg-bg-base flex items-center justify-center text-text-muted">Loading...</div>}>
      <KitLinkPageInner />
    </Suspense>
  );
}
