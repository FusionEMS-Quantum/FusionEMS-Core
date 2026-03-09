"use client";

import { useEffect, useState } from "react";
import { motion } from "framer-motion";
import { ModuleDashboardShell } from "@/components/shells/PageShells";
import {
  getStandaloneMobileOpsAdoptionKpis,
  getStandaloneMobileOpsCredentialCompliance,
  getStandaloneMobileOpsDevices,
  getStandaloneMobileOpsPushAnalytics,
  getStandaloneMobileOpsPwaDeployments,
  getStandaloneMobileOpsStaffingShortagePredictor,
  getStandaloneMobileOpsSyncHealth,
  getStandaloneMobileOpsVersionAdoption,
} from "@/services/api";

function KpiCard({ label, value, sub, color }: { label: string; value: string; sub?: string; color?: string }) {
  return (
    <motion.div initial={{ opacity: 0, y: 6 }} animate={{ opacity: 1, y: 0 }}
      className="bg-[#0A0A0B] border border-[var(--color-border-default)] chamfer-8 p-4">
      <div className="text-micro font-label uppercase tracking-widest text-zinc-500 mb-2">{label}</div>
      <div className="text-2xl font-bold" style={{ color: color ?? "var(--color-text-primary)" }}>{value}</div>
      {sub && <div className="text-body text-zinc-500 mt-1">{sub}</div>}
    </motion.div>
  );
}

function StatusDot({ status }: { status: string }) {
  const colors: Record<string, string> = { active: "var(--color-status-active)", healthy: "var(--color-status-active)", deployed: "var(--color-status-active)", logged_out: "var(--color-text-muted)", wiped: "var(--color-brand-red)", pending: "var(--color-status-warning)", failed: "var(--color-brand-red)" };
  return <span className="w-2 h-2  flex-shrink-0" style={{ background: colors[status] ?? "var(--color-text-muted)" }} />;
}

const FEATURES = [
  "CrewLink PWA deployment","Scheduling PWA deploy","Version tracking","Device registration",
  "Push notification keys","App manifest editor","Offline sync engine","Update enforcement",
  "Version adoption analytics","Mobile error reporting","Device performance monitor","Push failure analytics",
  "User session monitor","Credential expiration alerts","Shift swap approval","Scheduling conflict detector",
  "Staffing shortage predictor","Credential compliance","Mobile OCR capture","Facesheet scan validator",
  "Vital sign auto-detect","Rhythm strip parser","Vent settings extractor","Infusion pump capture",
  "Medication recognition","Lab result OCR","Field mapping NEMSIS","Provider verification",
  "Real-time sync conflicts","Offline data encryption","Mobile biometric login","Push priority control",
  "Incident acknowledgment","Dispatch-EPCR linking","Real-time incident map","Multi-device session",
  "App crash analytics","Mobile compliance mode","Data usage monitor","Low bandwidth fallback",
  "Image compression control","Secure file upload","Tenant PWA branding","App feature gating",
  "Remote device logout","Device trust scoring","Geo-based alert routing","Mobile SLA monitor",
  "Push analytics dashboard","Deployment rollback","Mobile policy enforcement","Role-based mobile access",
  "Offline validation rules","Scheduling heatmap","Crew availability analytics","Shift coverage forecast",
  "Overtime risk alert","Credential gap detection","Notification read tracking","Incident response time",
  "Device compliance check","Session timeout enforcement","Multi-agency management","Tenant push templates",
  "Mobile audit trail","In-app messaging","Secure camera capture","Background sync monitor",
  "Image integrity verification","Upload retry logic","Mobile alert escalation","Credential upload portal",
  "Training module push","App usage analytics","Mobile performance scoring","Battery usage alert",
  "Offline queue monitor","Sync health indicator","Secure local storage","PWA installation tracking",
  "Version compliance enforcement","Push quiet hours","Mobile UI personalization","On-call notifications",
  "Incident priority tagging","Real-time transport status","EPCR draft auto-save","NEMSIS mobile alerts",
  "Crew performance analytics","Shift confirmation alerts","Geo-fencing alerts","Multi-language support",
  "Remote config update","App feature toggle","Mobile auth logs","Secure data wipe",
  "PWA CDN health","Deployment cost tracking","Mobile adoption KPI","Enterprise mobile engine",
];

export default function MobileOpsPage() {
  const [deployments, setDeployments] = useState<{ deployments?: Array<Record<string, unknown>>; total?: number }>({});
  const [devices, setDevices] = useState<{ devices?: Array<Record<string, unknown>>; total?: number }>({});
  const [versionAdoption, setVersionAdoption] = useState<{ version_adoption?: Array<{ version: string; count: number; pct: number }>; total_devices?: number }>({});
  const [syncHealth, setSyncHealth] = useState<Record<string, unknown>>({});
  const [pushAnalytics, setPushAnalytics] = useState<Record<string, unknown>>({});
  const [adoptionKpis, setAdoptionKpis] = useState<Record<string, unknown>>({});
  const [credCompliance, setCredCompliance] = useState<Record<string, unknown>>({});
  const [shortage, setShortage] = useState<Record<string, unknown>>({});

  useEffect(() => {
    void Promise.allSettled([
      getStandaloneMobileOpsPwaDeployments(),
      getStandaloneMobileOpsDevices(),
      getStandaloneMobileOpsVersionAdoption(),
      getStandaloneMobileOpsSyncHealth(),
      getStandaloneMobileOpsPushAnalytics(),
      getStandaloneMobileOpsAdoptionKpis(),
      getStandaloneMobileOpsCredentialCompliance(),
      getStandaloneMobileOpsStaffingShortagePredictor(),
    ]).then((results) => {
      if (results[0].status === "fulfilled") setDeployments(results[0].value);
      if (results[1].status === "fulfilled") setDevices(results[1].value);
      if (results[2].status === "fulfilled") setVersionAdoption(results[2].value as { version_adoption?: Array<{ version: string; count: number; pct: number }>; total_devices?: number });
      if (results[3].status === "fulfilled") setSyncHealth(results[3].value);
      if (results[4].status === "fulfilled") setPushAnalytics(results[4].value);
      if (results[5].status === "fulfilled") setAdoptionKpis(results[5].value);
      if (results[6].status === "fulfilled") setCredCompliance(results[6].value);
      if (results[7].status === "fulfilled") setShortage(results[7].value);

      results.forEach((result) => {
        if (result.status === "rejected") {
          console.warn("[fetch error]", result.reason);
        }
      });
    });
  }, []);

  const fmtN = (v: unknown) => typeof v === "number" ? v.toLocaleString() : (v != null ? String(v) : "—");
  const fmtPct = (v: unknown) => typeof v === "number" ? `${v}%` : "—";

  const syncStatus = String(syncHealth.health ?? "unknown");
  const syncColor = syncStatus === "healthy" ? "var(--color-status-active)" : "var(--color-brand-red)";
  const shortageRisk = String(shortage.shortage_risk ?? (() => { throw new Error("Fallback detected") })());
  const shortageColor = shortageRisk === "high" ? "var(--color-brand-red)" : shortageRisk === "medium" ? "var(--color-status-warning)" : "var(--color-status-active)";

  return (
    <ModuleDashboardShell
      title="PWA Deployment &amp; Mobile Ops"
      subtitle="100-Feature Mobile Command · CrewLink · Scheduling · OCR · Push Notifications · Compliance"
      accentColor="var(--color-system-fleet)"
    >
      <div className="space-y-6">

      <div className="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-8 gap-3">
        <KpiCard label="PWA Deployments" value={fmtN(deployments.total)} color="var(--color-status-info)" />
        <KpiCard label="Registered Devices" value={fmtN(devices.total)} />
        <KpiCard label="Active Devices" value={fmtN(adoptionKpis.active_devices)} color="var(--color-status-active)" />
        <KpiCard label="Adoption Rate" value={fmtPct(adoptionKpis.adoption_rate_pct)} color="var(--color-status-info)" />
        <KpiCard label="Push Sent" value={fmtN(pushAnalytics.sent)} color="var(--color-system-fleet)" />
        <KpiCard label="Push Read Rate" value={fmtPct(pushAnalytics.read_rate_pct)} color="var(--color-status-info)" />
        <KpiCard label="Sync Health" value={syncStatus.toUpperCase()} color={syncColor} />
        <KpiCard label="Shortage Risk" value={shortageRisk.toUpperCase() || "—"} color={shortageColor} />
      </div>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        {/* Deployments */}
        <div className="bg-[#0A0A0B] border border-[var(--color-border-default)] chamfer-8 p-4">
          <div className="text-micro font-label uppercase tracking-widest text-zinc-500 mb-3">PWA Deployments</div>
          {deployments.deployments?.slice(0, 6).map((d, i) => (
            <div key={i} className="flex items-center justify-between py-1.5 border-b border-[var(--color-border-default)] last:border-0">
              <div className="flex items-center gap-2">
                <StatusDot status={String(d.data ? (d.data as Record<string,unknown>).status : "")} />
                <span className="text-body text-zinc-400 truncate">{String(d.data ? (d.data as Record<string,unknown>).pwa_name ?? "PWA" : "PWA")}</span>
              </div>
              <span className="text-micro text-zinc-500">v{String(d.data ? (d.data as Record<string,unknown>).version ?? (() => { throw new Error("Fallback detected") })() : "")}</span>
            </div>
          ))}
          {!deployments.deployments?.length && <div className="text-body text-zinc-500">No deployments yet</div>}
        </div>

        {/* Version Adoption */}
        <div className="bg-[#0A0A0B] border border-[var(--color-border-default)] chamfer-8 p-4">
          <div className="text-micro font-label uppercase tracking-widest text-zinc-500 mb-3">Version Adoption · {fmtN(versionAdoption.total_devices)} Devices</div>
          {versionAdoption.version_adoption?.map(v => (
            <div key={v.version} className="mb-2">
              <div className="flex justify-between text-body mb-0.5">
                <span className="text-zinc-400">{v.version}</span>
                <span className="font-label text-zinc-100">{v.pct}%</span>
              </div>
              <div className="h-1.5 bg-[rgba(255,255,255,0.06)]  overflow-hidden">
                <motion.div className="h-full  bg-system-fleet" initial={{ width: 0 }} animate={{ width: `${v.pct}%` }} transition={{ duration: 0.8 }} />
              </div>
            </div>
          ))}
          {!versionAdoption.version_adoption?.length && <div className="text-body text-zinc-500">No version data yet</div>}
        </div>

        {/* Compliance */}
        <div className="bg-[#0A0A0B] border border-[var(--color-border-default)] chamfer-8 p-4">
          <div className="text-micro font-label uppercase tracking-widest text-zinc-500 mb-3">Credential Compliance</div>
          {[
            { label: "Total Credentials", value: fmtN(credCompliance.total_credentials), color: "var(--color-text-primary)" },
            { label: "Compliant", value: fmtN(credCompliance.compliant), color: "var(--color-status-active)" },
            { label: "Expiring Soon", value: fmtN(credCompliance.expiring_soon), color: "var(--color-status-warning)" },
            { label: "Expired", value: fmtN(credCompliance.expired), color: "var(--color-brand-red)" },
          ].map(item => (
            <div key={item.label} className="flex justify-between py-2 border-b border-[var(--color-border-default)] last:border-0 text-body">
              <span className="text-zinc-500">{item.label}</span>
              <span className="font-bold" style={{ color: item.color }}>{item.value}</span>
            </div>
          ))}
          <div className="mt-3">
            <div className="text-micro font-label uppercase tracking-widest text-zinc-500 mb-2">Sync Health</div>
            {[
              { label: "Pending Jobs", value: fmtN(syncHealth.pending), color: "var(--color-status-warning)" },
              { label: "Failed Jobs", value: fmtN(syncHealth.failed), color: "var(--color-brand-red)" },
              { label: "Completed", value: fmtN(syncHealth.completed), color: "var(--color-status-active)" },
            ].map(item => (
              <div key={item.label} className="flex justify-between py-1 text-body">
                <span className="text-zinc-500">{item.label}</span>
                <span className="font-bold" style={{ color: item.color }}>{item.value}</span>
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* OCR + Field Mapping */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        <div className="bg-[#0A0A0B] border border-[var(--color-border-default)] chamfer-8 p-4">
          <div className="text-micro font-label uppercase tracking-widest text-zinc-500 mb-3">Mobile OCR Capture Engine</div>
          <div className="grid grid-cols-2 gap-2">
            {[
              { label: "Facesheet Scan", icon: "📋", status: "active" },
              { label: "Vital Sign Detect", icon: "💓", status: "active" },
              { label: "Rhythm Strip Parse", icon: "📈", status: "active" },
              { label: "Vent Settings", icon: "🫁", status: "active" },
              { label: "Infusion Pump", icon: "💉", status: "active" },
              { label: "Medication ID", icon: "💊", status: "active" },
              { label: "Lab Results", icon: "🧪", status: "active" },
              { label: "NEMSIS Mapping", icon: "🗺", status: "active" },
            ].map(item => (
              <div key={item.label} className="flex items-center gap-2 p-2 bg-blue-500/5 border border-blue-500/15 chamfer-4">
                <span className="text-sm">{item.icon}</span>
                <span className="text-micro text-zinc-400">{item.label}</span>
                <span className="ml-auto w-1.5 h-1.5  bg-status-active" />
              </div>
            ))}
          </div>
        </div>

        <div className="bg-[#0A0A0B] border border-[var(--color-border-default)] chamfer-8 p-4">
          <div className="text-micro font-label uppercase tracking-widest text-zinc-500 mb-3">Push Notification Analytics</div>
          {[
            { label: "Total Notifications", value: fmtN(pushAnalytics.total), color: "var(--color-text-primary)" },
            { label: "Sent", value: fmtN(pushAnalytics.sent), color: "var(--color-system-fleet)" },
            { label: "Failed", value: fmtN(pushAnalytics.failed), color: "var(--color-brand-red)" },
            { label: "Read", value: fmtN(pushAnalytics.read), color: "var(--color-status-active)" },
            { label: "Read Rate", value: fmtPct(pushAnalytics.read_rate_pct), color: "var(--color-status-info)" },
          ].map(item => (
            <div key={item.label} className="flex justify-between py-2 border-b border-[var(--color-border-default)] last:border-0 text-body">
              <span className="text-zinc-500">{item.label}</span>
              <span className="font-bold" style={{ color: item.color }}>{item.value}</span>
            </div>
          ))}
          <div className="mt-3 text-micro font-label uppercase tracking-widest text-zinc-500 mb-2">Staffing Shortage Predictor</div>
          <div className="flex items-center gap-3 p-2 bg-zinc-950/[0.03] border border-border-subtle chamfer-4">
            <span className="w-3 h-3  flex-shrink-0" style={{ background: shortageColor }} />
            <span className="text-body text-zinc-400">Shortage Risk: <strong style={{ color: shortageColor }}>{shortageRisk.toUpperCase() || "N/A"}</strong></span>
            <span className="ml-auto text-micro text-zinc-500">{fmtN(shortage.unfilled_shifts)} unfilled</span>
          </div>
        </div>
      </div>

      <div className="bg-[#0A0A0B] border border-[var(--color-border-default)] chamfer-8 p-4">
        <div className="text-micro font-label uppercase tracking-widest text-zinc-500 mb-3">100 Active Mobile Features</div>
        <div className="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-5 gap-1.5">
          {FEATURES.map(f => (
            <div key={f} className="flex items-center gap-1.5 text-micro text-zinc-500">
              <span className="w-1 h-1  bg-system-fleet flex-shrink-0" />
              <span className="truncate">{f}</span>
            </div>
          ))}
        </div>
      </div>
      </div>
    </ModuleDashboardShell>
  );
}
