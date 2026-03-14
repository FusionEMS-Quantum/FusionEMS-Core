'use client';

import { QuantumCardSkeleton } from '@/components/ui';
import { MetricCard } from '@/components/ui/MetricCard';
import { SeverityBadge } from '@/components/ui/SeverityBadge';
import { useToast } from '@/components/ui/ProductPolish';
import { TabBar, TabPanel } from '@/components/ui/InteractionPatterns';
import { ModuleDashboardShell } from '@/components/shells/PageShells';
import type { SeverityLevel } from '@/lib/design-system/tokens';
import {
  createPortalFleetInspectionTemplate,
  createPortalFleetWorkOrder,
  getPortalFleetReadiness,
  getPortalFleetUnitReadiness,
  listPortalFleetAlerts,
  listPortalFleetInspectionTemplates,
  listPortalFleetWorkOrders,
  resolvePortalFleetAlert,
  updatePortalFleetWorkOrder,
} from '@/services/api';

import { useState, useEffect, useCallback } from 'react';

// ─── Types ────────────────────────────────────────────────────────────────────

type TabId = 'overview' | 'alerts' | 'workorders' | 'inspections';

interface UnitScore {
  unit_id: string;
  readiness_score: number;
  alert_count: number;
  mdt_online: boolean;
  open_maintenance: number;
  [key: string]: unknown;
}

interface FleetReadiness {
  units?: UnitScore[];
  fleet_count?: number;
  avg_readiness?: number;
  units_ready?: number;
  units_limited?: number;
  units_no_go?: number;
  [key: string]: unknown;
}

interface UnitDetail {
  unit_id: string;
  [key: string]: unknown;
}

type AlertSeverity = 'critical' | 'warning' | 'info';

interface FleetAlert {
  alert_id: string;
  severity: AlertSeverity;
  unit_id: string;
  message: string;
  detected_at: string;
  resolved?: boolean;
  [key: string]: unknown;
}

type WOStatus = 'open' | 'in_progress' | 'completed';

interface WorkOrder {
  work_order_id: string;
  unit_id: string;
  title: string;
  description?: string;
  priority: string;
  status: WOStatus;
  due_date?: string;
  [key: string]: unknown;
}

interface InspectionTemplate {
  template_id: string;
  name: string;
  vehicle_type: string;
  frequency: string;
  [key: string]: unknown;
}

// ─── Helpers ──────────────────────────────────────────────────────────────────

function readinessColor(score: number): string {
  if (score >= 80) return 'var(--color-status-active)';
  if (score >= 40) return 'var(--color-status-warning)';
  return 'var(--color-brand-red)';
}

function fmtTs(ts: string): string {
  try { return new Date(ts).toLocaleString(); } catch { return ts; }
}

const ALERT_SEVERITY_MAP: Record<AlertSeverity, SeverityLevel> = {
  critical: 'BLOCKING',
  warning:  'MEDIUM',
  info:     'INFORMATIONAL',
};

const WO_STATUS_STYLE: Record<WOStatus, { color: string; bg: string; label: string }> = {
  open:        { color: 'var(--q-yellow)', bg: 'rgba(255,152,0,0.12)',   label: 'OPEN'        },
  in_progress: { color: 'var(--color-status-info)', bg: 'rgba(66,165,245,0.12)', label: 'IN PROGRESS' },
  completed:   { color: 'var(--q-green)', bg: 'rgba(76,175,80,0.12)',   label: 'COMPLETED'   },
};

function ReadinessBar({ score }: { score: number }) {
  const color = readinessColor(score);
  return (
    <div className="flex items-center gap-2">
      <div className="h-1.5 w-[60px] bg-bg-overlay chamfer-4 overflow-hidden">
        <div
          className="h-full chamfer-4"
          style={{ width: `${Math.min(score, 100)}%`, background: color }}
        />
      </div>
      <span className="text-micro tabular-nums" style={{ color }}>{score}</span>
    </div>
  );
}

// ─── Page ─────────────────────────────────────────────────────────────────────

export default function FleetPage() {
  const toast = useToast();
  const [activeTab, setActiveTab] = useState<TabId>('overview');

  // ── Overview ──
  const [fleet, setFleet] = useState<FleetReadiness | null>(null);
  const [fleetBusy, setFleetBusy] = useState(false);
  const [selectedUnit, setSelectedUnit] = useState<string | null>(null);
  const [unitDetail, setUnitDetail] = useState<UnitDetail | null>(null);
  const [unitDetailBusy, setUnitDetailBusy] = useState(false);

  // ── Alerts ──
  const [alerts, setAlerts] = useState<FleetAlert[]>([]);
  const [alertsBusy, setAlertsBusy] = useState(false);
  const [resolveNote, setResolveNote] = useState<Record<string, string>>({});
  const [resolvingId, setResolvingId] = useState<string | null>(null);

  // ── Work Orders ──
  const [workOrders, setWorkOrders] = useState<WorkOrder[]>([]);
  const [woBusy, setWoBusy] = useState(false);
  const [woForm, setWoForm] = useState({
    unit_id: '', title: '', description: '', priority: 'routine', due_date: '',
  });
  const [woSubmitBusy, setWoSubmitBusy] = useState(false);

  // ── Inspections ──
  const [templates, setTemplates] = useState<InspectionTemplate[]>([]);
  const [inspBusy, setInspBusy] = useState(false);
  const [inspForm, setInspForm] = useState({
    name: '', vehicle_type: 'ground', frequency: 'daily',
  });
  const [inspSubmitBusy, setInspSubmitBusy] = useState(false);

  // ── Fetchers ──

  const fetchFleet = useCallback(async () => {
    setFleetBusy(true);
    try {
      setFleet(await getPortalFleetReadiness());
    } catch (e: unknown) {
      toast.error(e instanceof Error ? e.message : 'Failed to load fleet readiness');
    } finally {
      setFleetBusy(false);
    }
  }, [toast]);

  const fetchUnitDetail = useCallback(async (unitId: string) => {
    setUnitDetailBusy(true);
    setUnitDetail(null);
    try {
      setUnitDetail(await getPortalFleetUnitReadiness(unitId));
    } catch (e: unknown) {
      toast.error(e instanceof Error ? e.message : 'Failed to load unit detail');
    } finally {
      setUnitDetailBusy(false);
    }
  }, [toast]);

  const fetchAlerts = useCallback(async () => {
    setAlertsBusy(true);
    try {
      setAlerts(await listPortalFleetAlerts(true));
    } catch (e: unknown) {
      toast.error(e instanceof Error ? e.message : 'Failed to load alerts');
    } finally {
      setAlertsBusy(false);
    }
  }, [toast]);

  const fetchWorkOrders = useCallback(async () => {
    setWoBusy(true);
    try {
      setWorkOrders(await listPortalFleetWorkOrders());
    } catch (e: unknown) {
      toast.error(e instanceof Error ? e.message : 'Failed to load work orders');
    } finally {
      setWoBusy(false);
    }
  }, [toast]);

  const fetchTemplates = useCallback(async () => {
    setInspBusy(true);
    try {
      setTemplates(await listPortalFleetInspectionTemplates());
    } catch (e: unknown) {
      toast.error(e instanceof Error ? e.message : 'Failed to load inspection templates');
    } finally {
      setInspBusy(false);
    }
  }, [toast]);

  // Load on mount and on tab switch
  useEffect(() => {
    if (activeTab === 'overview') fetchFleet();
    if (activeTab === 'alerts') fetchAlerts();
    if (activeTab === 'workorders') fetchWorkOrders();
    if (activeTab === 'inspections') fetchTemplates();
  }, [activeTab, fetchFleet, fetchAlerts, fetchWorkOrders, fetchTemplates]);

  // ── Unit click ──
  function handleUnitClick(unitId: string) {
    setSelectedUnit(unitId);
    fetchUnitDetail(unitId);
  }

  // ── Resolve alert ──
  async function resolveAlert(alertId: string) {
    setResolvingId(alertId);
    try {
      await resolvePortalFleetAlert(alertId, { note: resolveNote[alertId] || '' });
      setAlerts((prev) => prev.filter((a) => a.alert_id !== alertId));
      toast.success('Alert resolved');
    } catch (e: unknown) {
      toast.error(e instanceof Error ? e.message : 'Failed to resolve alert');
    } finally {
      setResolvingId(null);
    }
  }

  // ── Create work order ──
  async function createWorkOrder() {
    if (!woForm.unit_id.trim() || !woForm.title.trim()) {
      toast.error('Unit ID and title are required'); return;
    }
    setWoSubmitBusy(true);
    try {
      await createPortalFleetWorkOrder({
        unit_id: woForm.unit_id.trim(),
        title: woForm.title.trim(),
        description: woForm.description || undefined,
        priority: woForm.priority,
        due_date: woForm.due_date || undefined,
      });
      toast.success('Work order created');
      setWoForm({ unit_id: '', title: '', description: '', priority: 'routine', due_date: '' });
      fetchWorkOrders();
    } catch (e: unknown) {
      toast.error(e instanceof Error ? e.message : 'Failed to create work order');
    } finally {
      setWoSubmitBusy(false);
    }
  }

  // ── Update work order status ──
  async function updateWOStatus(woId: string, status: WOStatus) {
    try {
      await updatePortalFleetWorkOrder(woId, { status });
      setWorkOrders((prev) => prev.map((w) => w.work_order_id === woId ? { ...w, status } : w));
      toast.success('Status updated');
    } catch (e: unknown) {
      toast.error(e instanceof Error ? e.message : 'Failed to update status');
    }
  }

  // ── Create inspection template ──
  async function createTemplate() {
    if (!inspForm.name.trim()) { toast.error('Name is required'); return; }
    setInspSubmitBusy(true);
    try {
      await createPortalFleetInspectionTemplate({
        name: inspForm.name.trim(),
        vehicle_type: inspForm.vehicle_type,
        frequency: inspForm.frequency,
      });
      toast.success('Template created');
      setInspForm({ name: '', vehicle_type: 'ground', frequency: 'daily' });
      fetchTemplates();
    } catch (e: unknown) {
      toast.error(e instanceof Error ? e.message : 'Failed to create template');
    } finally {
      setInspSubmitBusy(false);
    }
  }

  const TABS: { id: TabId; label: string }[] = [
    { id: 'overview',     label: 'Fleet Overview' },
    { id: 'alerts',       label: 'Alerts' },
    { id: 'workorders',   label: 'Work Orders' },
    { id: 'inspections',  label: 'Inspections' },
  ];

  const units: UnitScore[] = fleet?.units ?? [];
  const avgReadiness = fleet?.avg_readiness ?? (units.length ? Math.round(units.reduce((s, u) => s + u.readiness_score, 0) / units.length) : 0);

  return (
    <ModuleDashboardShell
      title="Fleet Intelligence"
      subtitle="Unit readiness, alerts, maintenance, and inspections"
      accentColor="var(--q-orange)"
      kpiStrip={fleet ? (
        <>
          <MetricCard label="Fleet Count" value={fleet.fleet_count ?? units.length} domain="fleet" compact />
          <MetricCard label="Avg Readiness" value={avgReadiness} domain="fleet" compact />
          <MetricCard label="Units Ready" value={fleet.units_ready ?? units.filter((u) => u.readiness_score >= 80).length} compact />
          <MetricCard label="Units Limited" value={fleet.units_limited ?? units.filter((u) => u.readiness_score >= 40 && u.readiness_score < 80).length} compact />
          <MetricCard label="Units No-Go" value={fleet.units_no_go ?? units.filter((u) => u.readiness_score < 40).length} compact />
        </>
      ) : undefined}
      toolbar={
        <TabBar
          tabs={TABS.map((t) => ({ id: t.id, label: t.label }))}
          activeTab={activeTab}
          onTabChange={(id) => setActiveTab(id as TabId)}
        />
      }
    >
      {/* ══ FLEET OVERVIEW TAB ══ */}
      <TabPanel tabId="overview" activeTab={activeTab}>
        <div className="space-y-4">
          {fleetBusy && <QuantumCardSkeleton />}

          {fleet && units.length > 0 && (
            <div className="bg-[var(--color-bg-panel)] border border-[var(--color-border-default)] chamfer-8 overflow-hidden">
              <table className="w-full text-body">
                <thead>
                  <tr className="bg-bg-overlay border-b border-[var(--color-border-default)]">
                    {['Unit ID', 'Readiness', 'Alerts', 'MDT', 'Open Maint.'].map((h) => (
                      <th key={h} className="px-3 py-2 text-left font-label text-label uppercase tracking-wider text-[var(--color-text-muted)]">
                        {h}
                      </th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {units.map((u) => (
                    <tr
                      key={u.unit_id}
                      onClick={() => handleUnitClick(u.unit_id)}
                      className="cursor-pointer transition-colors duration-fast border-b border-[var(--color-border-subtle)] hover:bg-bg-overlay"
                      style={{
                        background: selectedUnit === u.unit_id ? 'rgba(255,106,0,0.06)' : undefined,
                      }}
                    >
                      <td className="px-3 py-2 font-semibold text-[var(--q-orange)]">{u.unit_id}</td>
                      <td className="px-3 py-2"><ReadinessBar score={u.readiness_score} /></td>
                      <td className="px-3 py-2 tabular-nums" style={{ color: u.alert_count > 0 ? 'var(--color-brand-red)' : undefined }}>
                        {u.alert_count}
                      </td>
                      <td className="px-3 py-2">
                        <span
                          className="w-2 h-2  inline-block"
                          style={{ background: u.mdt_online ? 'var(--color-status-active)' : 'var(--color-brand-red)' }}
                        />
                      </td>
                      <td className="px-3 py-2 tabular-nums text-[var(--color-text-muted)]">{u.open_maintenance}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}

          {/* Unit detail panel */}
          {selectedUnit && (
            <div className="bg-[var(--color-bg-panel)] border border-orange/20 chamfer-8 p-4">
              <p className="text-label font-label uppercase tracking-wider text-[var(--q-orange)] mb-2">
                Unit Detail — {selectedUnit}
              </p>
              {unitDetailBusy ? (
                <QuantumCardSkeleton />
              ) : unitDetail ? (
                <pre className="text-body whitespace-pre-wrap text-[var(--color-text-muted)] font-mono">
                  {JSON.stringify(unitDetail, null, 2)}
                </pre>
              ) : null}
            </div>
          )}
        </div>
      </TabPanel>

      {/* ══ ALERTS TAB ══ */}
      <TabPanel tabId="alerts" activeTab={activeTab}>
        <div className="space-y-3">
          {alertsBusy && <QuantumCardSkeleton />}
          {!alertsBusy && alerts.length === 0 && (
            <p className="text-body text-text-disabled py-8 text-center">No unresolved alerts.</p>
          )}
          {alerts.map((alert) => (
            <div
              key={alert.alert_id}
              className="bg-[var(--color-bg-panel)] border border-[var(--color-border-default)] chamfer-8 p-3"
            >
              <div className="flex flex-wrap items-center gap-2 mb-1">
                <SeverityBadge severity={ALERT_SEVERITY_MAP[alert.severity]} size="sm" />
                <span className="text-body font-semibold text-[var(--color-text-secondary)]">{alert.unit_id}</span>
                <span className="text-micro ml-auto text-text-disabled">{fmtTs(alert.detected_at)}</span>
              </div>
              <p className="text-body text-[var(--color-text-muted)] mb-2">{alert.message}</p>
              <div className="flex items-center gap-2">
                <input
                  className="flex-1 bg-bg-input border border-[var(--color-border-default)] chamfer-4 px-2 py-1 text-body text-[var(--color-text-primary)] outline-none
                             focus:border-orange transition-colors duration-fast"
                  placeholder="Resolution note (optional)"
                  value={resolveNote[alert.alert_id] || ''}
                  onChange={(e) =>
                    setResolveNote((prev) => ({ ...prev, [alert.alert_id]: e.target.value }))
                  }
                />
                <button
                  onClick={() => resolveAlert(alert.alert_id)}
                  disabled={resolvingId === alert.alert_id}
                  className="px-3 py-1 text-label font-label uppercase tracking-wider chamfer-4
                             bg-[rgba(76,175,80,0.15)] text-[var(--color-status-active)] 
                             border border-[rgba(76,175,80,0.3)]
                             hover:bg-[rgba(76,175,80,0.25)] transition-colors duration-fast
                             disabled:opacity-40"
                  type="button"
                >
                  {resolvingId === alert.alert_id ? 'Resolving...' : 'Resolve'}
                </button>
              </div>
            </div>
          ))}
        </div>
      </TabPanel>

      {/* ══ WORK ORDERS TAB ══ */}
      <TabPanel tabId="workorders" activeTab={activeTab}>
        <div className="space-y-4">
          {/* Create form */}
          <div className="bg-[var(--color-bg-panel)] border border-[var(--color-border-default)] chamfer-8 p-4">
            <p className="text-label font-label uppercase tracking-wider text-[var(--color-text-muted)] mb-3">
              Create Work Order
            </p>
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 mb-3">
              {(
                [
                  { key: 'unit_id',     label: 'Unit ID',     type: 'text' },
                  { key: 'title',       label: 'Title',       type: 'text' },
                  { key: 'description', label: 'Description', type: 'text' },
                  { key: 'due_date',    label: 'Due Date',    type: 'date' },
                ] as { key: keyof typeof woForm; label: string; type: string }[]
              ).map(({ key, label, type }) => (
                <div key={key} className="flex flex-col gap-1">
                  <label className="text-micro font-label uppercase tracking-wider text-[var(--color-text-muted)]">{label}</label>
                  <input
                    type={type}
                    className="bg-bg-input border border-[var(--color-border-default)] chamfer-4 px-2.5 py-1.5 text-body text-[var(--color-text-primary)] outline-none
                               focus:border-orange transition-colors duration-fast"
                    value={woForm[key]}
                    onChange={(e) => setWoForm((p) => ({ ...p, [key]: e.target.value }))}
                  />
                </div>
              ))}
              <div className="flex flex-col gap-1">
                <label className="text-micro font-label uppercase tracking-wider text-[var(--color-text-muted)]">Priority</label>
                <select
                  className="bg-bg-input border border-[var(--color-border-default)] chamfer-4 px-2.5 py-1.5 text-body text-[var(--color-text-primary)] outline-none
                             focus:border-orange transition-colors duration-fast"
                  value={woForm.priority}
                  onChange={(e) => setWoForm((p) => ({ ...p, priority: e.target.value }))}
                >
                  <option value="critical">Critical</option>
                  <option value="urgent">Urgent</option>
                  <option value="routine">Routine</option>
                </select>
              </div>
            </div>
            <button
              onClick={createWorkOrder}
              disabled={woSubmitBusy}
              className="px-4 py-2 text-label font-label uppercase tracking-wider chamfer-4
                         bg-[var(--q-orange)] text-black hover:bg-[#FF6A1A]
                         transition-colors duration-fast disabled:opacity-40"
              type="button"
            >
              {woSubmitBusy ? 'Creating...' : 'Create Work Order'}
            </button>
          </div>

          {/* List */}
          {woBusy && <QuantumCardSkeleton />}
          {workOrders.map((wo) => {
            const s = WO_STATUS_STYLE[wo.status] ?? WO_STATUS_STYLE.open;
            const nextStatuses: WOStatus[] = wo.status === 'open'
              ? ['in_progress', 'completed']
              : wo.status === 'in_progress'
              ? ['completed']
              : [];
            return (
              <div
                key={wo.work_order_id}
                className="bg-[var(--color-bg-panel)] border border-[var(--color-border-default)] chamfer-8 p-3"
              >
                <div className="flex flex-wrap items-center gap-2 mb-1">
                  <span
                    className="px-2 py-0.5 text-micro font-label uppercase tracking-wider chamfer-4 whitespace-nowrap"
                    style={{ color: s.color, background: s.bg, border: `1px solid ${s.color}33` }}
                  >
                    {s.label}
                  </span>
                  <span className="text-body font-semibold text-[var(--color-text-secondary)]">{wo.title}</span>
                  <span className="text-micro text-text-disabled">{wo.unit_id}</span>
                  <span className="text-micro px-1.5 py-0.5 bg-bg-overlay chamfer-4 text-text-disabled ml-auto">
                    {wo.priority}
                  </span>
                </div>
                {wo.description && (
                  <p className="text-body text-[var(--color-text-muted)] mb-2">{wo.description}</p>
                )}
                {nextStatuses.length > 0 && (
                  <div className="flex gap-2">
                    {nextStatuses.map((ns) => {
                      const ns_ = WO_STATUS_STYLE[ns];
                      return (
                        <button
                          key={ns}
                          onClick={() => updateWOStatus(wo.work_order_id, ns)}
                          className="px-2 py-0.5 text-micro font-label uppercase tracking-wider chamfer-4
                                     hover:opacity-80 transition-opacity duration-fast"
                          style={{ color: ns_.color, background: ns_.bg, border: `1px solid ${ns_.color}33` }}
                          type="button"
                        >
                          Mark {ns_.label}
                        </button>
                      );
                    })}
                  </div>
                )}
              </div>
            );
          })}
        </div>
      </TabPanel>

      {/* ══ INSPECTIONS TAB ══ */}
      <TabPanel tabId="inspections" activeTab={activeTab}>
        <div className="space-y-4">
          {/* Create form */}
          <div className="bg-[var(--color-bg-panel)] border border-[var(--color-border-default)] chamfer-8 p-4">
            <p className="text-label font-label uppercase tracking-wider text-[var(--color-text-muted)] mb-3">
              Create Inspection Template
            </p>
            <div className="flex flex-wrap gap-3 mb-3 items-end">
              <div className="flex flex-col gap-1 flex-1 min-w-[140px]">
                <label className="text-micro font-label uppercase tracking-wider text-[var(--color-text-muted)]">Name</label>
                <input
                  className="bg-bg-input border border-[var(--color-border-default)] chamfer-4 px-2.5 py-1.5 text-body text-[var(--color-text-primary)] outline-none
                             focus:border-orange transition-colors duration-fast"
                  value={inspForm.name}
                  onChange={(e) => setInspForm((p) => ({ ...p, name: e.target.value }))}
                />
              </div>
              <div className="flex flex-col gap-1">
                <label className="text-micro font-label uppercase tracking-wider text-[var(--color-text-muted)]">Vehicle Type</label>
                <select
                  className="bg-bg-input border border-[var(--color-border-default)] chamfer-4 px-2.5 py-1.5 text-body text-[var(--color-text-primary)] outline-none
                             focus:border-orange transition-colors duration-fast"
                  value={inspForm.vehicle_type}
                  onChange={(e) => setInspForm((p) => ({ ...p, vehicle_type: e.target.value }))}
                >
                  <option value="ground">Ground</option>
                  <option value="rotor">Rotor</option>
                  <option value="fixed_wing">Fixed Wing</option>
                </select>
              </div>
              <div className="flex flex-col gap-1">
                <label className="text-micro font-label uppercase tracking-wider text-[var(--color-text-muted)]">Frequency</label>
                <select
                  className="bg-bg-input border border-[var(--color-border-default)] chamfer-4 px-2.5 py-1.5 text-body text-[var(--color-text-primary)] outline-none
                             focus:border-orange transition-colors duration-fast"
                  value={inspForm.frequency}
                  onChange={(e) => setInspForm((p) => ({ ...p, frequency: e.target.value }))}
                >
                  <option value="daily">Daily</option>
                  <option value="weekly">Weekly</option>
                  <option value="monthly">Monthly</option>
                </select>
              </div>
              <button
                onClick={createTemplate}
                disabled={inspSubmitBusy}
                className="px-4 py-2 text-label font-label uppercase tracking-wider chamfer-4
                           bg-[var(--q-orange)] text-black hover:bg-[#FF6A1A]
                           transition-colors duration-fast disabled:opacity-40"
                type="button"
              >
                {inspSubmitBusy ? 'Creating...' : 'Create Template'}
              </button>
            </div>
          </div>

          {/* Template list */}
          {inspBusy && <QuantumCardSkeleton />}
          {!inspBusy && templates.length === 0 && (
            <p className="text-body text-text-disabled py-8 text-center">No templates found.</p>
          )}
          {templates.map((t) => (
            <div
              key={t.template_id}
              className="bg-[var(--color-bg-panel)] border border-[var(--color-border-default)] chamfer-8 px-4 py-3 flex flex-wrap items-center gap-3"
            >
              <span className="text-body font-semibold text-[var(--color-text-secondary)]">{t.name}</span>
              <span className="text-micro px-1.5 py-0.5 bg-bg-overlay chamfer-4 text-[var(--color-text-muted)]">
                {t.vehicle_type}
              </span>
              <span className="text-micro px-1.5 py-0.5 bg-[rgba(255,106,0,0.12)] chamfer-4 text-[var(--q-orange)]">
                {t.frequency}
              </span>
              <span className="text-micro ml-auto text-text-disabled">{t.template_id}</span>
            </div>
          ))}
        </div>
      </TabPanel>
    </ModuleDashboardShell>
  );
}
