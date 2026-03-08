'use client';

import { useEffect, useState } from 'react';
import {
  getFounderPendingFlightMissions,
  getFounderSpecialtyOpsSummary,
} from '@/services/api';

type FounderCommandAction = {
  domain: string;
  severity: string;
  summary: string;
  recommended_action: string;
  entity_id?: string;
};

type SpecialtySummary = {
  preplan_gaps: number;
  active_hazard_flags: number;
  pending_lz_confirmations: number;
  duty_time_warnings: number;
  specialty_missions_blocked: number;
  mission_packet_failures: number;
  top_actions: FounderCommandAction[];
};

type FlightMission = {
  id: string;
  mission_number: string;
  state: string;
  origin: string | null;
  destination: string | null;
  scheduled_departure_at: string | null;
};

function Stat({ label, value }: { label: string; value: number }) {
  return (
    <div className=" border border-white/10 bg-zinc-950/[0.03] p-4">
      <div className="text-xs uppercase tracking-wider text-white/50">{label}</div>
      <div className="mt-2 text-3xl font-black text-white">{value}</div>
    </div>
  );
}

export default function FounderSpecialtyOpsPage() {
  const [summary, setSummary] = useState<SpecialtySummary | null>(null);
  const [missions, setMissions] = useState<FlightMission[]>([]);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const load = async () => {
      try {
        const [summaryRes, missionRes] = await Promise.all([
          getFounderSpecialtyOpsSummary(),
          getFounderPendingFlightMissions(25),
        ]);
        setSummary(summaryRes as SpecialtySummary);
        setMissions(Array.isArray(missionRes) ? (missionRes as FlightMission[]) : []);
      } catch {
        setError('Unable to load specialty operations command data.');
      }
    };
    load();
  }, []);

  return (
    <div className="mx-auto max-w-7xl space-y-6 p-6">
      <div>
        <div className="text-xs uppercase tracking-[0.2em] text-[#FF4D00]-400/80">Founder Command</div>
        <h1 className="text-2xl font-black text-white">Specialty Ops Command Center</h1>
      </div>

      {error && <div className=" border border-red-500/30 bg-red-500/10 p-3 text-sm text-red-300">{error}</div>}

      {!summary ? (
        <div className=" border border-white/10 bg-zinc-950/[0.03] p-4 text-sm text-white/70">Loading specialty operations intelligence…</div>
      ) : (
        <>
          <div className="grid grid-cols-1 gap-3 md:grid-cols-3 lg:grid-cols-6">
            <Stat label="Preplan Gaps" value={summary.preplan_gaps} />
            <Stat label="Active Hazards" value={summary.active_hazard_flags} />
            <Stat label="LZ Pending" value={summary.pending_lz_confirmations} />
            <Stat label="Duty Warnings" value={summary.duty_time_warnings} />
            <Stat label="Missions Blocked" value={summary.specialty_missions_blocked} />
            <Stat label="Packet Failures" value={summary.mission_packet_failures} />
          </div>

          <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
            <div className=" border border-white/10 bg-zinc-950/[0.03] p-4">
              <div className="mb-3 text-xs uppercase tracking-wider text-white/50">Top Actions</div>
              <div className="space-y-2">
                {summary.top_actions.length === 0 && (
                  <div className="text-sm text-white/60">No immediate specialty actions.</div>
                )}
                {summary.top_actions.map((action, idx) => (
                  <div key={`${action.summary}-${idx}`} className=" border border-white/10 bg-black/20 p-3">
                    <div className="text-xs font-bold uppercase tracking-wider text-[#FF4D00]-300">{action.severity}</div>
                    <div className="mt-1 text-sm font-semibold text-white">{action.summary}</div>
                    <div className="mt-1 text-sm text-white/70">{action.recommended_action}</div>
                  </div>
                ))}
              </div>
            </div>

            <div className=" border border-white/10 bg-zinc-950/[0.03] p-4">
              <div className="mb-3 text-xs uppercase tracking-wider text-white/50">Pending Flight Missions</div>
              <div className="space-y-2">
                {missions.length === 0 && <div className="text-sm text-white/60">No pending missions.</div>}
                {missions.map((mission) => (
                  <div key={mission.id} className=" border border-white/10 bg-black/20 p-3">
                    <div className="flex items-center justify-between gap-2">
                      <div className="text-sm font-semibold text-white">{mission.mission_number}</div>
                      <div className="text-xs uppercase tracking-wider text-yellow-300">{mission.state}</div>
                    </div>
                    <div className="mt-1 text-xs text-white/60">
                      {mission.origin || 'Unknown Origin'} → {mission.destination || 'Unknown Destination'}
                    </div>
                  </div>
                ))}
              </div>
            </div>
          </div>
        </>
      )}
    </div>
  );
}
