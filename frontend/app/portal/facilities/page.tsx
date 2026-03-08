'use client';

import React, { useCallback, useEffect, useMemo, useState } from 'react';
import { QuantumEmptyState, QuantumTableSkeleton } from '@/components/ui';
import {
  createFacility,
  createFacilityContact,
  createFacilityFriction,
  createFacilityNote,
  createFacilityService,
  createFacilityWarning,
  getRelationshipCommandSummary,
  getRelationshipIssues,
  listFacilities,
  listFacilityContacts,
  listFacilityFriction,
  listFacilityNotes,
  listFacilityServices,
  listFacilityTimeline,
  listFacilityWarnings,
  resolveFacilityFriction,
  resolveFacilityWarning,
  updateFacility,
} from '@/services/api';

interface Facility {
  id: string;
  name: string;
  facility_type: string;
  npi: string | null;
  address_line_1: string | null;
  address_line_2: string | null;
  city: string | null;
  state: string | null;
  zip_code: string | null;
  phone: string | null;
  fax: string | null;
  email: string | null;
  relationship_state: string;
  destination_preference_notes: string | null;
  service_notes: string | null;
  version: number;
}

interface FacilityContact {
  id: string;
  facility_id: string;
  name: string;
  role: string;
  phone: string | null;
  email: string | null;
  preferred_contact_method: string | null;
  notes: string | null;
  is_active: boolean;
  created_at: string;
}

interface FacilityServiceProfile {
  id: string;
  facility_id: string;
  service_line: string;
  accepts_ems_transport: boolean;
  average_turnaround_minutes: number | null;
  capability_notes: string | null;
  is_active: boolean;
  created_at: string;
}

interface FacilityFrictionFlag {
  id: string;
  facility_id: string;
  category: string;
  title: string;
  description: string;
  is_active: boolean;
  resolution_notes: string | null;
  created_at: string;
}

interface FacilityNote {
  id: string;
  facility_id: string;
  note_type: string;
  content: string;
  is_internal: boolean;
  created_at: string;
}

interface FacilityWarning {
  id: string;
  facility_id: string;
  severity: string;
  flag_type: string;
  title: string;
  description: string;
  is_active: boolean;
  resolution_notes: string | null;
  created_at: string;
}

interface TimelineEvent {
  id: string;
  event_type: string;
  title: string;
  description: string;
  source: string;
  created_at: string;
}

interface RelationshipAction {
  priority: number;
  category: string;
  title: string;
  description: string;
  severity: string;
  action_url?: string | null;
}

interface RelationshipSummary {
  facility_health?: {
    total_facilities: number;
    active_count: number;
    high_friction_count: number;
    review_required_count: number;
    inactive_count: number;
    health_pct: number;
  };
  facility_contact_gaps?: number;
  top_actions?: RelationshipAction[];
}

interface RelationshipIssue {
  issue: string;
  severity: string;
  source: string;
  what_is_wrong: string;
  why_it_matters: string;
  what_you_should_do: string;
  relationship_context: string;
  human_review: string;
  confidence: string;
  category?: string | null;
  entity_id?: string | null;
}

type ActiveTab =
  | 'overview'
  | 'services'
  | 'contacts'
  | 'friction'
  | 'warnings'
  | 'timeline'
  | 'notes'
  | 'ai';

type RawData = Record<string, unknown>;

const FACILITY_TYPES = [
  'HOSPITAL',
  'SNF',
  'LTC',
  'REHAB',
  'DIALYSIS',
  'PSYCHIATRIC',
  'URGENT_CARE',
  'PHYSICIANS_OFFICE',
  'HOME_HEALTH',
  'OTHER',
] as const;

const RELATIONSHIP_STATES = [
  'ACTIVE',
  'LIMITED_RELATIONSHIP',
  'HIGH_FRICTION',
  'REVIEW_REQUIRED',
  'INACTIVE',
] as const;

const CONTACT_ROLES = [
  'INTAKE_COORDINATOR',
  'NURSE',
  'SOCIAL_WORKER',
  'CASE_MANAGER',
  'CHARGE_NURSE',
  'ADMINISTRATOR',
  'BILLING_CONTACT',
  'DISPATCH_LIAISON',
  'OTHER',
] as const;

const FRICTION_CATEGORIES = [
  'WAIT_TIMES',
  'COMMUNICATION',
  'DOCUMENTATION',
  'BILLING_DISPUTES',
  'SAFETY_CONCERN',
  'STAFF_CONFLICT',
  'OTHER',
] as const;

const WARNING_SEVERITIES = [
  'BLOCKING',
  'HIGH',
  'MEDIUM',
  'LOW',
  'INFORMATIONAL',
] as const;

function asRecord(value: unknown): RawData {
  if (value && typeof value === 'object') {
    return value as RawData;
  }
  return {};
}

function parseItems<T>(payload: unknown): T[] {
  if (Array.isArray(payload)) {
    return payload as T[];
  }
  const record = asRecord(payload);
  if (Array.isArray(record.items)) {
    return record.items as T[];
  }
  return [];
}

function severityStyle(severity: string): string {
  switch (severity) {
    case 'BLOCKING':
      return 'bg-red-900/40 border-red-500/50 text-red-300';
    case 'HIGH':
      return 'bg-[rgba(255,77,0,0.3)] border-orange-500/40 text-[#FF9A66]';
    case 'MEDIUM':
      return 'bg-yellow-900/30 border-yellow-500/40 text-yellow-300';
    case 'LOW':
      return 'bg-blue-900/30 border-blue-500/40 text-blue-300';
    default:
      return 'bg-zinc-900/50 border-gray-600 text-gray-300';
  }
}

function relationshipStyle(state: string): string {
  switch (state) {
    case 'ACTIVE':
      return 'bg-green-900/20 border-green-500/30 text-green-400';
    case 'LIMITED_RELATIONSHIP':
      return 'bg-yellow-900/20 border-yellow-500/30 text-yellow-400';
    case 'HIGH_FRICTION':
      return 'bg-red-900/20 border-red-500/30 text-red-400';
    case 'REVIEW_REQUIRED':
      return 'bg-[rgba(255,77,0,0.2)] border-orange-500/30 text-[#FF9A66]';
    default:
      return 'bg-zinc-900/50 border-gray-600 text-zinc-500';
  }
}

function median(values: number[]): number | null {
  if (values.length === 0) return null;
  const sorted = [...values].sort((a, b) => a - b);
  const mid = Math.floor(sorted.length / 2);
  return sorted.length % 2 === 0
    ? (sorted[mid - 1] + sorted[mid]) / 2
    : sorted[mid];
}

export default function FacilitiesPage() {
  const [facilities, setFacilities] = useState<Facility[]>([]);
  const [summary, setSummary] = useState<RelationshipSummary | null>(null);
  const [issues, setIssues] = useState<RelationshipIssue[]>([]);

  const [networkLoading, setNetworkLoading] = useState(true);
  const [networkError, setNetworkError] = useState<string | null>(null);

  const [selectedFacilityId, setSelectedFacilityId] = useState<string | null>(null);
  const [activeTab, setActiveTab] = useState<ActiveTab>('overview');
  const [search, setSearch] = useState('');
  const [stateFilter, setStateFilter] = useState<string>('ALL');

  const [contactsByFacility, setContactsByFacility] = useState<Record<string, FacilityContact[]>>({});
  const [servicesByFacility, setServicesByFacility] = useState<Record<string, FacilityServiceProfile[]>>({});
  const [notesByFacility, setNotesByFacility] = useState<Record<string, FacilityNote[]>>({});
  const [frictionByFacility, setFrictionByFacility] = useState<Record<string, FacilityFrictionFlag[]>>({});
  const [warningsByFacility, setWarningsByFacility] = useState<Record<string, FacilityWarning[]>>({});
  const [timelineByFacility, setTimelineByFacility] = useState<Record<string, TimelineEvent[]>>({});
  const [detailLoadingByFacility, setDetailLoadingByFacility] = useState<Record<string, boolean>>({});

  const [busyAction, setBusyAction] = useState<string | null>(null);
  const [message, setMessage] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  const [newFacility, setNewFacility] = useState({
    name: '',
    facility_type: 'HOSPITAL',
    city: '',
    state: '',
    phone: '',
    npi: '',
    email: '',
  });

  const [contactForm, setContactForm] = useState({
    name: '',
    role: 'INTAKE_COORDINATOR',
    phone: '',
    email: '',
    preferred_contact_method: 'phone',
    notes: '',
  });

  const [serviceForm, setServiceForm] = useState({
    service_line: '',
    accepts_ems_transport: true,
    average_turnaround_minutes: '',
    capability_notes: '',
  });

  const [noteForm, setNoteForm] = useState({
    note_type: 'operational',
    content: '',
    is_internal: true,
  });

  const [frictionForm, setFrictionForm] = useState({
    category: 'WAIT_TIMES',
    title: '',
    description: '',
  });

  const [warningForm, setWarningForm] = useState({
    severity: 'MEDIUM',
    flag_type: 'high_friction',
    title: '',
    description: '',
  });

  const [facilityEdit, setFacilityEdit] = useState<{
    relationship_state: string;
    destination_preference_notes: string;
    service_notes: string;
    version: number;
  } | null>(null);

  const selectedFacility = useMemo(
    () => facilities.find((f) => f.id === selectedFacilityId) || null,
    [facilities, selectedFacilityId],
  );

  const filteredFacilities = useMemo(() => {
    return facilities.filter((facility) => {
      if (stateFilter !== 'ALL' && facility.relationship_state !== stateFilter) {
        return false;
      }
      if (!search) return true;
      const haystack = [
        facility.name,
        facility.facility_type,
        facility.city || '',
        facility.state || '',
        facility.npi || '',
      ].join(' ').toLowerCase();
      return haystack.includes(search.toLowerCase());
    });
  }, [facilities, search, stateFilter]);

  const selectedContacts = selectedFacilityId ? contactsByFacility[selectedFacilityId] || [] : [];
  const selectedServices = selectedFacilityId ? servicesByFacility[selectedFacilityId] || [] : [];
  const selectedNotes = selectedFacilityId ? notesByFacility[selectedFacilityId] || [] : [];
  const selectedFriction = selectedFacilityId ? frictionByFacility[selectedFacilityId] || [] : [];
  const selectedWarnings = selectedFacilityId ? warningsByFacility[selectedFacilityId] || [] : [];
  const selectedTimeline = selectedFacilityId ? timelineByFacility[selectedFacilityId] || [] : [];

  const flattenedServices = useMemo(
    () => Object.values(servicesByFacility).flat(),
    [servicesByFacility],
  );

  const turnaroundValues = useMemo(
    () => flattenedServices
      .map((service) => service.average_turnaround_minutes)
      .filter((minutes): minutes is number => typeof minutes === 'number' && minutes > 0),
    [flattenedServices],
  );

  const medianTurnaround = median(turnaroundValues);
  const apotThresholdBreaches = turnaroundValues.filter((minutes) => minutes > 60).length;
  const acceptanceRate = flattenedServices.length > 0
    ? (flattenedServices.filter((service) => service.accepts_ems_transport).length / flattenedServices.length) * 100
    : 0;

  const facilityIssues = useMemo(() => {
    if (!selectedFacilityId) return [];
    return issues.filter((issue) => {
      const entityMatch = issue.entity_id === selectedFacilityId;
      const categoryMatch = (issue.category || '').toLowerCase().includes('facility');
      return entityMatch || categoryMatch;
    });
  }, [issues, selectedFacilityId]);

  const loadNetwork = useCallback(async () => {
    setNetworkLoading(true);
    setNetworkError(null);
    try {
      const [facilityRes, summaryRes, issuesRes] = await Promise.all([
        listFacilities(),
        getRelationshipCommandSummary().catch(() => null),
        getRelationshipIssues().catch(() => ({ issues: [] })),
      ]);

      const loadedFacilities = parseItems<Facility>(facilityRes)
        .sort((a, b) => a.name.localeCompare(b.name));
      setFacilities(loadedFacilities);
      setSummary(summaryRes ? (asRecord(summaryRes) as RelationshipSummary) : null);

      const issuesRecord = asRecord(issuesRes);
      const loadedIssues = Array.isArray(issuesRecord.issues)
        ? issuesRecord.issues as RelationshipIssue[]
        : [];
      setIssues(loadedIssues);

      setSelectedFacilityId((prev) => {
        if (prev && loadedFacilities.some((facility) => facility.id === prev)) return prev;
        return loadedFacilities[0]?.id || null;
      });

      const servicePairs = await Promise.all(
        loadedFacilities.map(async (facility) => {
          const serviceRes = await listFacilityServices(facility.id).catch(() => ({ items: [] }));
          return [facility.id, parseItems<FacilityServiceProfile>(serviceRes)] as const;
        }),
      );
      setServicesByFacility((prev) => {
        const next = { ...prev };
        for (const [facilityId, services] of servicePairs) {
          next[facilityId] = services;
        }
        return next;
      });
    } catch (_error) {
      setNetworkError('Failed to load facility network command data.');
    } finally {
      setNetworkLoading(false);
    }
  }, []);

  const loadFacilityDetail = useCallback(async (facilityId: string, force = false) => {
    const cached = Boolean(
      contactsByFacility[facilityId]
      && notesByFacility[facilityId]
      && frictionByFacility[facilityId]
      && warningsByFacility[facilityId]
      && timelineByFacility[facilityId]
      && servicesByFacility[facilityId],
    );
    if (cached && !force) return;

    setDetailLoadingByFacility((prev) => ({ ...prev, [facilityId]: true }));
    try {
      const [contactsRes, notesRes, frictionRes, warningsRes, timelineRes, servicesRes] = await Promise.all([
        listFacilityContacts(facilityId),
        listFacilityNotes(facilityId),
        listFacilityFriction(facilityId),
        listFacilityWarnings(facilityId),
        listFacilityTimeline(facilityId),
        listFacilityServices(facilityId),
      ]);

      setContactsByFacility((prev) => ({ ...prev, [facilityId]: parseItems<FacilityContact>(contactsRes) }));
      setNotesByFacility((prev) => ({ ...prev, [facilityId]: parseItems<FacilityNote>(notesRes) }));
      setFrictionByFacility((prev) => ({ ...prev, [facilityId]: parseItems<FacilityFrictionFlag>(frictionRes) }));
      setWarningsByFacility((prev) => ({ ...prev, [facilityId]: parseItems<FacilityWarning>(warningsRes) }));
      setTimelineByFacility((prev) => ({ ...prev, [facilityId]: parseItems<TimelineEvent>(timelineRes) }));
      setServicesByFacility((prev) => ({ ...prev, [facilityId]: parseItems<FacilityServiceProfile>(servicesRes) }));
    } catch (_error) {
      setError('Could not load selected facility details.');
    } finally {
      setDetailLoadingByFacility((prev) => ({ ...prev, [facilityId]: false }));
    }
  }, [
    contactsByFacility,
    frictionByFacility,
    notesByFacility,
    servicesByFacility,
    timelineByFacility,
    warningsByFacility,
  ]);

  useEffect(() => {
    loadNetwork();
  }, [loadNetwork]);

  useEffect(() => {
    if (selectedFacilityId) {
      void loadFacilityDetail(selectedFacilityId);
    }
  }, [selectedFacilityId, loadFacilityDetail]);

  useEffect(() => {
    if (!selectedFacility) {
      setFacilityEdit(null);
      return;
    }
    setFacilityEdit({
      relationship_state: selectedFacility.relationship_state,
      destination_preference_notes: selectedFacility.destination_preference_notes || '',
      service_notes: selectedFacility.service_notes || '',
      version: selectedFacility.version,
    });
  }, [selectedFacility]);

  const clearBanner = useCallback(() => {
    if (message) setMessage(null);
    if (error) setError(null);
  }, [error, message]);

  async function handleCreateFacility() {
    clearBanner();
    if (!newFacility.name.trim()) {
      setError('Facility name is required.');
      return;
    }

    setBusyAction('create-facility');
    try {
      const payload = {
        name: newFacility.name.trim(),
        facility_type: newFacility.facility_type,
        city: newFacility.city || undefined,
        state: newFacility.state || undefined,
        phone: newFacility.phone || undefined,
        npi: newFacility.npi || undefined,
        email: newFacility.email || undefined,
      };
      const created = await createFacility(payload);
      const record = asRecord(created);
      const createdId = typeof record.id === 'string' ? record.id : null;
      await loadNetwork();
      if (createdId) setSelectedFacilityId(createdId);
      setNewFacility({
        name: '',
        facility_type: 'HOSPITAL',
        city: '',
        state: '',
        phone: '',
        npi: '',
        email: '',
      });
      setMessage('Facility created and indexed in command network.');
    } catch (_error) {
      setError('Failed to create facility. Ensure your role has admin/founder permissions.');
    } finally {
      setBusyAction(null);
    }
  }

  async function handleSaveFacilityOverview() {
    clearBanner();
    if (!selectedFacilityId || !selectedFacility || !facilityEdit) return;
    setBusyAction('save-overview');
    try {
      const updated = await updateFacility(selectedFacilityId, {
        name: selectedFacility.name,
        facility_type: selectedFacility.facility_type,
        npi: selectedFacility.npi || undefined,
        address_line_1: selectedFacility.address_line_1 || undefined,
        address_line_2: selectedFacility.address_line_2 || undefined,
        city: selectedFacility.city || undefined,
        state: selectedFacility.state || undefined,
        zip_code: selectedFacility.zip_code || undefined,
        phone: selectedFacility.phone || undefined,
        fax: selectedFacility.fax || undefined,
        email: selectedFacility.email || undefined,
        destination_preference_notes: facilityEdit.destination_preference_notes || undefined,
        service_notes: facilityEdit.service_notes || undefined,
        relationship_state: facilityEdit.relationship_state,
        version: facilityEdit.version,
      });

      const updatedFacility = asRecord(updated) as unknown as Facility;
      setFacilities((prev) => prev.map((facility) => (
        facility.id === selectedFacilityId ? updatedFacility : facility
      )));
      setFacilityEdit((prev) => prev
        ? { ...prev, version: updatedFacility.version }
        : prev);
      setMessage('Facility relationship profile updated.');
    } catch (_error) {
      setError('Failed to update facility profile. Check version freshness and permissions.');
    } finally {
      setBusyAction(null);
    }
  }

  async function handleAddContact() {
    clearBanner();
    if (!selectedFacilityId || !contactForm.name.trim()) {
      setError('Contact name is required.');
      return;
    }
    setBusyAction('add-contact');
    try {
      await createFacilityContact(selectedFacilityId, {
        name: contactForm.name.trim(),
        role: contactForm.role,
        phone: contactForm.phone || undefined,
        email: contactForm.email || undefined,
        preferred_contact_method: contactForm.preferred_contact_method || undefined,
        notes: contactForm.notes || undefined,
      });
      await loadFacilityDetail(selectedFacilityId, true);
      setContactForm({
        name: '',
        role: 'INTAKE_COORDINATOR',
        phone: '',
        email: '',
        preferred_contact_method: 'phone',
        notes: '',
      });
      setMessage('Facility contact added.');
    } catch (_error) {
      setError('Failed to add contact.');
    } finally {
      setBusyAction(null);
    }
  }

  async function handleAddService() {
    clearBanner();
    if (!selectedFacilityId || !serviceForm.service_line.trim()) {
      setError('Service line is required.');
      return;
    }
    setBusyAction('add-service');
    try {
      await createFacilityService(selectedFacilityId, {
        service_line: serviceForm.service_line.trim(),
        accepts_ems_transport: serviceForm.accepts_ems_transport,
        average_turnaround_minutes: serviceForm.average_turnaround_minutes
          ? Number(serviceForm.average_turnaround_minutes)
          : undefined,
        capability_notes: serviceForm.capability_notes || undefined,
      });
      await loadFacilityDetail(selectedFacilityId, true);
      setServiceForm({
        service_line: '',
        accepts_ems_transport: true,
        average_turnaround_minutes: '',
        capability_notes: '',
      });
      setMessage('Service profile added.');
    } catch (_error) {
      setError('Failed to add service profile.');
    } finally {
      setBusyAction(null);
    }
  }

  async function handleAddNote() {
    clearBanner();
    if (!selectedFacilityId || !noteForm.content.trim()) {
      setError('Note content is required.');
      return;
    }
    setBusyAction('add-note');
    try {
      await createFacilityNote(selectedFacilityId, {
        note_type: noteForm.note_type,
        content: noteForm.content.trim(),
        is_internal: noteForm.is_internal,
      });
      await loadFacilityDetail(selectedFacilityId, true);
      setNoteForm({ note_type: 'operational', content: '', is_internal: true });
      setMessage('Relationship note added.');
    } catch (_error) {
      setError('Failed to add relationship note.');
    } finally {
      setBusyAction(null);
    }
  }

  async function handleAddFriction() {
    clearBanner();
    if (!selectedFacilityId || !frictionForm.title.trim() || !frictionForm.description.trim()) {
      setError('Friction title and description are required.');
      return;
    }
    setBusyAction('add-friction');
    try {
      await createFacilityFriction(selectedFacilityId, {
        category: frictionForm.category,
        title: frictionForm.title.trim(),
        description: frictionForm.description.trim(),
      });
      await loadFacilityDetail(selectedFacilityId, true);
      setFrictionForm({ category: 'WAIT_TIMES', title: '', description: '' });
      setMessage('Friction flag raised and logged.');
    } catch (_error) {
      setError('Failed to create friction flag.');
    } finally {
      setBusyAction(null);
    }
  }

  async function handleResolveFriction(flagId: string) {
    clearBanner();
    if (!selectedFacilityId) return;
    const notes = window.prompt('Resolution notes', 'Issue reviewed and resolved via facility command center.');
    if (!notes || !notes.trim()) return;

    setBusyAction(`resolve-friction-${flagId}`);
    try {
      await resolveFacilityFriction(selectedFacilityId, flagId, { resolution_notes: notes.trim() });
      await loadFacilityDetail(selectedFacilityId, true);
      setMessage('Friction flag resolved with audit notes.');
    } catch (_error) {
      setError('Failed to resolve friction flag.');
    } finally {
      setBusyAction(null);
    }
  }

  async function handleAddWarning() {
    clearBanner();
    if (!selectedFacilityId || !warningForm.title.trim() || !warningForm.description.trim()) {
      setError('Warning title and description are required.');
      return;
    }
    setBusyAction('add-warning');
    try {
      await createFacilityWarning(selectedFacilityId, {
        severity: warningForm.severity,
        flag_type: warningForm.flag_type,
        title: warningForm.title.trim(),
        description: warningForm.description.trim(),
      });
      await loadFacilityDetail(selectedFacilityId, true);
      setWarningForm({ severity: 'MEDIUM', flag_type: 'high_friction', title: '', description: '' });
      setMessage('Facility warning flag created.');
    } catch (_error) {
      setError('Failed to create facility warning.');
    } finally {
      setBusyAction(null);
    }
  }

  async function handleResolveWarning(flagId: string) {
    clearBanner();
    if (!selectedFacilityId) return;
    const notes = window.prompt('Resolution notes', 'Warning reviewed and closed.');
    if (!notes || !notes.trim()) return;

    setBusyAction(`resolve-warning-${flagId}`);
    try {
      await resolveFacilityWarning(selectedFacilityId, flagId, { resolution_notes: notes.trim() });
      await loadFacilityDetail(selectedFacilityId, true);
      setMessage('Warning resolved with audit notes.');
    } catch (_error) {
      setError('Failed to resolve warning flag.');
    } finally {
      setBusyAction(null);
    }
  }

  const facilityHealth = summary?.facility_health;
  const topActions = summary?.top_actions || [];

  return (
    <div className="flex flex-col min-h-screen bg-black">
      <div className="border-b border-border-subtle bg-[#0A0A0B]/50 px-5 py-4">
        <div className="flex items-center justify-between">
          <div>
            <div className="text-xs font-black text-zinc-100 uppercase tracking-widest">Facility Command Center</div>
            <div className="text-micro text-zinc-500">
              Receiving network intelligence · APOT-style offload KPIs · friction governance · relationship AI
            </div>
          </div>
          <button
            onClick={() => void loadNetwork()}
            className="quantum-btn-sm"
            disabled={networkLoading}
          >
            {networkLoading ? 'Refreshing…' : '↺ Refresh Network'}
          </button>
        </div>

        <div className="grid grid-cols-4 gap-3 mt-4">
          {[
            {
              label: 'Facilities',
              value: (facilityHealth?.total_facilities ?? facilities.length).toString(),
              color: 'text-zinc-100',
            },
            {
              label: 'Network Health',
              value: facilityHealth?.health_pct != null ? `${Math.round(facilityHealth.health_pct)}%` : '—',
              color: (facilityHealth?.health_pct ?? 0) >= 85 ? 'text-green-400' : 'text-yellow-400',
            },
            {
              label: 'High Friction',
              value: (facilityHealth?.high_friction_count ?? facilities.filter((f) => f.relationship_state === 'HIGH_FRICTION').length).toString(),
              color: 'text-red-400',
            },
            {
              label: 'Review Required',
              value: (facilityHealth?.review_required_count ?? facilities.filter((f) => f.relationship_state === 'REVIEW_REQUIRED').length).toString(),
              color: 'text-[#FF9A66]',
            },
          ].map((metric) => (
            <div key={metric.label} className="bg-[#0A0A0B] border border-border-subtle chamfer-8 px-4 py-3">
              <div className={`text-2xl font-black ${metric.color}`}>{metric.value}</div>
              <div className="text-micro text-zinc-500 mt-0.5">{metric.label}</div>
            </div>
          ))}
        </div>

        <div className="grid grid-cols-4 gap-3 mt-3">
          {[
            {
              label: 'Facility Contact Gaps',
              value: (summary?.facility_contact_gaps ?? 0).toString(),
              color: (summary?.facility_contact_gaps ?? 0) > 0 ? 'text-yellow-400' : 'text-green-400',
            },
            {
              label: 'Median Turnaround',
              value: medianTurnaround != null ? `${Math.round(medianTurnaround)}m` : '—',
              color: medianTurnaround != null && medianTurnaround <= 45 ? 'text-green-400' : 'text-yellow-400',
            },
            {
              label: 'APOT >60m Signals',
              value: apotThresholdBreaches.toString(),
              color: apotThresholdBreaches > 0 ? 'text-red-400' : 'text-green-400',
            },
            {
              label: 'EMS Acceptance Rate',
              value: flattenedServices.length > 0 ? `${Math.round(acceptanceRate)}%` : '—',
              color: acceptanceRate >= 85 ? 'text-green-400' : 'text-yellow-400',
            },
          ].map((metric) => (
            <div key={metric.label} className="bg-[#0A0A0B] border border-border-subtle chamfer-8 px-4 py-3">
              <div className={`text-2xl font-black ${metric.color}`}>{metric.value}</div>
              <div className="text-micro text-zinc-500 mt-0.5">{metric.label}</div>
            </div>
          ))}
        </div>
      </div>

      {(message || error || networkError) && (
        <div className="px-5 pt-4">
          {message && (
            <div className="mb-2 bg-green-900/20 border border-green-500/30 text-green-300 text-sm px-4 py-2 chamfer-8">
              {message}
            </div>
          )}
          {(error || networkError) && (
            <div className="mb-2 bg-red-900/20 border border-red-500/30 text-red-300 text-sm px-4 py-2 chamfer-8">
              {error || networkError}
            </div>
          )}
        </div>
      )}

      <div className="flex-1 p-5 grid grid-cols-12 gap-4">
        <div className="col-span-4 space-y-4">
          <div className="bg-[#0A0A0B] border border-border-subtle chamfer-8 p-4 space-y-3">
            <div className="text-micro uppercase tracking-widest text-zinc-500">Facility Network Directory</div>

            <div className="grid grid-cols-2 gap-2">
              <input
                value={search}
                onChange={(event) => setSearch(event.target.value)}
                className="col-span-2 bg-black border border-border-subtle chamfer-4 px-3 py-2 text-sm text-zinc-100 focus:outline-none focus:border-brand-orange/60"
                placeholder="Search facility, city, type, NPI"
              />
              <select
                value={stateFilter}
                onChange={(event) => setStateFilter(event.target.value)}
                className="col-span-2 bg-black border border-border-subtle chamfer-4 px-3 py-2 text-sm text-zinc-100 focus:outline-none focus:border-brand-orange/60"
              >
                <option value="ALL">All relationship states</option>
                {RELATIONSHIP_STATES.map((state) => (
                  <option key={state} value={state}>{state}</option>
                ))}
              </select>
            </div>

            {networkLoading ? (
              <QuantumTableSkeleton rows={4} />
            ) : filteredFacilities.length === 0 ? (
              <QuantumEmptyState
                title="No facilities match"
                description="Adjust search filters or create a new facility profile."
              />
            ) : (
              <div className="max-h-[420px] overflow-y-auto space-y-2 pr-1">
                {filteredFacilities.map((facility) => {
                  const selected = facility.id === selectedFacilityId;
                  return (
                    <button
                      key={facility.id}
                      type="button"
                      onClick={() => {
                        setSelectedFacilityId(facility.id);
                        setActiveTab('overview');
                        setMessage(null);
                        setError(null);
                      }}
                      className={`w-full text-left border chamfer-8 px-3 py-2 transition-colors ${
                        selected
                          ? 'border-brand-orange/50 bg-brand-orange/10'
                          : 'border-border-subtle bg-black hover:border-brand-orange/30'
                      }`}
                    >
                      <div className="flex items-center justify-between gap-2">
                        <span className="text-sm font-semibold text-zinc-100 truncate">{facility.name}</span>
                        <span className={`text-[10px] font-bold px-2 py-0.5 chamfer-4 border ${relationshipStyle(facility.relationship_state)}`}>
                          {facility.relationship_state}
                        </span>
                      </div>
                      <div className="mt-1 text-micro text-zinc-500 flex items-center gap-2 flex-wrap">
                        <span>{facility.facility_type}</span>
                        {(facility.city || facility.state) && <span>• {facility.city}{facility.city && facility.state ? ', ' : ''}{facility.state}</span>}
                        {facility.phone && <span>• {facility.phone}</span>}
                      </div>
                    </button>
                  );
                })}
              </div>
            )}
          </div>

          <div className="bg-[#0A0A0B] border border-border-subtle chamfer-8 p-4 space-y-3">
            <div className="text-micro uppercase tracking-widest text-zinc-500">Add Facility</div>
            <div className="grid grid-cols-2 gap-2">
              <input
                value={newFacility.name}
                onChange={(event) => setNewFacility((prev) => ({ ...prev, name: event.target.value }))}
                className="col-span-2 bg-black border border-border-subtle chamfer-4 px-3 py-2 text-sm text-zinc-100"
                placeholder="Facility name"
              />
              <select
                value={newFacility.facility_type}
                onChange={(event) => setNewFacility((prev) => ({ ...prev, facility_type: event.target.value }))}
                className="bg-black border border-border-subtle chamfer-4 px-3 py-2 text-sm text-zinc-100"
              >
                {FACILITY_TYPES.map((type) => <option key={type} value={type}>{type}</option>)}
              </select>
              <input
                value={newFacility.state}
                onChange={(event) => setNewFacility((prev) => ({ ...prev, state: event.target.value.toUpperCase() }))}
                className="bg-black border border-border-subtle chamfer-4 px-3 py-2 text-sm text-zinc-100"
                placeholder="State"
                maxLength={2}
              />
              <input
                value={newFacility.city}
                onChange={(event) => setNewFacility((prev) => ({ ...prev, city: event.target.value }))}
                className="bg-black border border-border-subtle chamfer-4 px-3 py-2 text-sm text-zinc-100"
                placeholder="City"
              />
              <input
                value={newFacility.phone}
                onChange={(event) => setNewFacility((prev) => ({ ...prev, phone: event.target.value }))}
                className="bg-black border border-border-subtle chamfer-4 px-3 py-2 text-sm text-zinc-100"
                placeholder="Phone"
              />
              <input
                value={newFacility.npi}
                onChange={(event) => setNewFacility((prev) => ({ ...prev, npi: event.target.value }))}
                className="bg-black border border-border-subtle chamfer-4 px-3 py-2 text-sm text-zinc-100"
                placeholder="NPI"
              />
              <input
                value={newFacility.email}
                onChange={(event) => setNewFacility((prev) => ({ ...prev, email: event.target.value }))}
                className="col-span-2 bg-black border border-border-subtle chamfer-4 px-3 py-2 text-sm text-zinc-100"
                placeholder="Email"
              />
            </div>
            <button
              onClick={() => void handleCreateFacility()}
              disabled={busyAction === 'create-facility'}
              className="quantum-btn-primary w-full disabled:opacity-50"
            >
              {busyAction === 'create-facility' ? 'Creating…' : '+ Create Facility'}
            </button>
          </div>
        </div>

        <div className="col-span-8 space-y-4">
          {!selectedFacility ? (
            <div className="bg-[#0A0A0B] border border-border-subtle chamfer-8">
              <QuantumEmptyState
                title="No facility selected"
                description="Select a facility from the directory to manage contacts, service lines, friction flags, warnings, and relationship intelligence."
              />
            </div>
          ) : (
            <>
              <div className="bg-[#0A0A0B] border border-border-subtle chamfer-8 p-4">
                <div className="flex items-center justify-between gap-3">
                  <div>
                    <div className="text-lg font-bold text-zinc-100">{selectedFacility.name}</div>
                    <div className="text-micro text-zinc-500 mt-1 flex items-center gap-2 flex-wrap">
                      <span>{selectedFacility.facility_type}</span>
                      {(selectedFacility.city || selectedFacility.state) && <span>• {selectedFacility.city}{selectedFacility.city && selectedFacility.state ? ', ' : ''}{selectedFacility.state}</span>}
                      {selectedFacility.phone && <span>• {selectedFacility.phone}</span>}
                      {selectedFacility.npi && <span>• NPI {selectedFacility.npi}</span>}
                    </div>
                  </div>
                  <div className="flex items-center gap-2">
                    <span className={`text-xs font-bold px-2 py-1 chamfer-4 border ${relationshipStyle(selectedFacility.relationship_state)}`}>
                      {selectedFacility.relationship_state}
                    </span>
                    <button
                      onClick={() => selectedFacilityId && void loadFacilityDetail(selectedFacilityId, true)}
                      className="quantum-btn-sm"
                      disabled={Boolean(selectedFacilityId && detailLoadingByFacility[selectedFacilityId])}
                    >
                      {selectedFacilityId && detailLoadingByFacility[selectedFacilityId] ? 'Refreshing…' : 'Refresh'}
                    </button>
                  </div>
                </div>

                <div className="flex items-center gap-1 mt-4 border-b border-border-subtle">
                  {([
                    { id: 'overview', label: 'Overview' },
                    { id: 'services', label: 'Services' },
                    { id: 'contacts', label: 'Contacts' },
                    { id: 'friction', label: 'Friction' },
                    { id: 'warnings', label: 'Warnings' },
                    { id: 'timeline', label: 'Timeline' },
                    { id: 'notes', label: 'Notes' },
                    { id: 'ai', label: `AI Intel (${facilityIssues.length})` },
                  ] as const).map((tab) => (
                    <button
                      key={tab.id}
                      onClick={() => setActiveTab(tab.id)}
                      className={`px-3 py-2 text-micro font-semibold border-b-2 transition-colors ${
                        activeTab === tab.id
                          ? 'border-brand-orange text-brand-orange'
                          : 'border-transparent text-zinc-500 hover:text-zinc-400'
                      }`}
                    >
                      {tab.label}
                    </button>
                  ))}
                </div>
              </div>

              {selectedFacilityId && detailLoadingByFacility[selectedFacilityId] ? (
                <QuantumTableSkeleton rows={6} />
              ) : activeTab === 'overview' ? (
                <div className="grid grid-cols-2 gap-4">
                  <div className="bg-[#0A0A0B] border border-border-subtle chamfer-8 p-4 space-y-3">
                    <div className="text-micro uppercase tracking-widest text-zinc-500">Relationship State</div>
                    <select
                      value={facilityEdit?.relationship_state || selectedFacility.relationship_state}
                      onChange={(event) => setFacilityEdit((prev) => prev ? { ...prev, relationship_state: event.target.value } : prev)}
                      className="w-full bg-black border border-border-subtle chamfer-4 px-3 py-2 text-sm text-zinc-100"
                    >
                      {RELATIONSHIP_STATES.map((state) => <option key={state} value={state}>{state}</option>)}
                    </select>

                    <div className="text-micro uppercase tracking-widest text-zinc-500 pt-2">Destination Preference Notes</div>
                    <textarea
                      value={facilityEdit?.destination_preference_notes || ''}
                      onChange={(event) => setFacilityEdit((prev) => prev ? { ...prev, destination_preference_notes: event.target.value } : prev)}
                      className="w-full h-28 bg-black border border-border-subtle chamfer-4 px-3 py-2 text-sm text-zinc-100"
                      placeholder="Document destination workflow, handoff constraints, and transport preferences."
                    />

                    <div className="text-micro uppercase tracking-widest text-zinc-500 pt-2">Service Notes</div>
                    <textarea
                      value={facilityEdit?.service_notes || ''}
                      onChange={(event) => setFacilityEdit((prev) => prev ? { ...prev, service_notes: event.target.value } : prev)}
                      className="w-full h-24 bg-black border border-border-subtle chamfer-4 px-3 py-2 text-sm text-zinc-100"
                      placeholder="Operational notes impacting acceptance and throughput."
                    />

                    <button
                      onClick={() => void handleSaveFacilityOverview()}
                      disabled={busyAction === 'save-overview'}
                      className="quantum-btn-primary w-full disabled:opacity-50"
                    >
                      {busyAction === 'save-overview' ? 'Saving…' : 'Save Facility Profile'}
                    </button>
                  </div>

                  <div className="bg-[#0A0A0B] border border-border-subtle chamfer-8 p-4">
                    <div className="text-micro uppercase tracking-widest text-zinc-500 mb-3">Operational Snapshot</div>
                    <div className="grid grid-cols-2 gap-3">
                      {[
                        { label: 'Active Friction Flags', value: selectedFriction.filter((flag) => flag.is_active).length, color: 'text-red-400' },
                        { label: 'Active Warnings', value: selectedWarnings.filter((warning) => warning.is_active).length, color: 'text-[#FF9A66]' },
                        { label: 'Service Profiles', value: selectedServices.length, color: 'text-blue-400' },
                        { label: 'Contacts', value: selectedContacts.filter((contact) => contact.is_active).length, color: 'text-green-400' },
                      ].map((item) => (
                        <div key={item.label} className="bg-black border border-border-subtle chamfer-8 px-3 py-3">
                          <div className={`text-2xl font-black ${item.color}`}>{item.value}</div>
                          <div className="text-micro text-zinc-500 mt-0.5">{item.label}</div>
                        </div>
                      ))}
                    </div>
                    <div className="mt-4 text-sm text-zinc-500 leading-relaxed">
                      This facility profile contributes to network APOT and handoff intelligence. Keep relationship status, service lines, and contact routing current to reduce transfer delays.
                    </div>
                  </div>
                </div>
              ) : activeTab === 'services' ? (
                <div className="grid grid-cols-2 gap-4">
                  <div className="bg-[#0A0A0B] border border-border-subtle chamfer-8 p-4">
                    <div className="text-micro uppercase tracking-widest text-zinc-500 mb-3">Service Profiles</div>
                    {selectedServices.length === 0 ? (
                      <QuantumEmptyState title="No service profiles" description="Add ER/ICU/stroke and other destination capabilities for routing intelligence." />
                    ) : (
                      <div className="space-y-2 max-h-[460px] overflow-y-auto pr-1">
                        {selectedServices.map((service) => (
                          <div key={service.id} className="bg-black border border-border-subtle chamfer-8 px-3 py-2">
                            <div className="flex items-center justify-between">
                              <div className="text-sm font-semibold text-zinc-100">{service.service_line}</div>
                              <span className={`text-[10px] font-bold px-2 py-0.5 chamfer-4 border ${
                                service.accepts_ems_transport
                                  ? 'bg-green-900/20 border-green-500/30 text-green-400'
                                  : 'bg-red-900/20 border-red-500/30 text-red-400'
                              }`}>
                                {service.accepts_ems_transport ? 'ACCEPTS EMS' : 'NO EMS ACCEPT'}
                              </span>
                            </div>
                            <div className="text-micro text-zinc-500 mt-1">
                              Avg turnaround: {service.average_turnaround_minutes != null ? `${service.average_turnaround_minutes}m` : 'Not set'}
                            </div>
                            {service.capability_notes && (
                              <div className="text-micro text-zinc-500 mt-1">{service.capability_notes}</div>
                            )}
                          </div>
                        ))}
                      </div>
                    )}
                  </div>
                  <div className="bg-[#0A0A0B] border border-border-subtle chamfer-8 p-4 space-y-3">
                    <div className="text-micro uppercase tracking-widest text-zinc-500">Add Service Profile</div>
                    <input
                      value={serviceForm.service_line}
                      onChange={(event) => setServiceForm((prev) => ({ ...prev, service_line: event.target.value }))}
                      className="w-full bg-black border border-border-subtle chamfer-4 px-3 py-2 text-sm text-zinc-100"
                      placeholder="Service line (e.g., ER, ICU, Stroke Center)"
                    />
                    <input
                      value={serviceForm.average_turnaround_minutes}
                      onChange={(event) => setServiceForm((prev) => ({ ...prev, average_turnaround_minutes: event.target.value }))}
                      className="w-full bg-black border border-border-subtle chamfer-4 px-3 py-2 text-sm text-zinc-100"
                      placeholder="Average turnaround minutes"
                      type="number"
                      min={0}
                    />
                    <textarea
                      value={serviceForm.capability_notes}
                      onChange={(event) => setServiceForm((prev) => ({ ...prev, capability_notes: event.target.value }))}
                      className="w-full h-24 bg-black border border-border-subtle chamfer-4 px-3 py-2 text-sm text-zinc-100"
                      placeholder="Capability and constraints"
                    />
                    <label className="flex items-center gap-2 text-sm text-zinc-400">
                      <input
                        type="checkbox"
                        checked={serviceForm.accepts_ems_transport}
                        onChange={(event) => setServiceForm((prev) => ({ ...prev, accepts_ems_transport: event.target.checked }))}
                        className="accent-brand-orange"
                      />
                      Accepts EMS transport
                    </label>
                    <button
                      onClick={() => void handleAddService()}
                      disabled={busyAction === 'add-service'}
                      className="quantum-btn-primary w-full disabled:opacity-50"
                    >
                      {busyAction === 'add-service' ? 'Adding…' : '+ Add Service'}
                    </button>
                  </div>
                </div>
              ) : activeTab === 'contacts' ? (
                <div className="grid grid-cols-2 gap-4">
                  <div className="bg-[#0A0A0B] border border-border-subtle chamfer-8 p-4">
                    <div className="text-micro uppercase tracking-widest text-zinc-500 mb-3">Facility Contacts</div>
                    {selectedContacts.length === 0 ? (
                      <QuantumEmptyState title="No contacts" description="Add intake, nursing, and escalation contacts for transfer reliability." />
                    ) : (
                      <div className="space-y-2 max-h-[460px] overflow-y-auto pr-1">
                        {selectedContacts.map((contact) => (
                          <div key={contact.id} className="bg-black border border-border-subtle chamfer-8 px-3 py-2">
                            <div className="flex items-center justify-between">
                              <div className="text-sm font-semibold text-zinc-100">{contact.name}</div>
                              <span className="text-[10px] font-bold px-2 py-0.5 chamfer-4 border bg-blue-900/20 border-blue-500/30 text-blue-300">
                                {contact.role}
                              </span>
                            </div>
                            <div className="text-micro text-zinc-500 mt-1">
                              {[contact.phone, contact.email].filter(Boolean).join(' · ') || 'No contact channels'}
                            </div>
                            {contact.notes && <div className="text-micro text-zinc-500 mt-1">{contact.notes}</div>}
                          </div>
                        ))}
                      </div>
                    )}
                  </div>
                  <div className="bg-[#0A0A0B] border border-border-subtle chamfer-8 p-4 space-y-3">
                    <div className="text-micro uppercase tracking-widest text-zinc-500">Add Contact</div>
                    <input
                      value={contactForm.name}
                      onChange={(event) => setContactForm((prev) => ({ ...prev, name: event.target.value }))}
                      className="w-full bg-black border border-border-subtle chamfer-4 px-3 py-2 text-sm text-zinc-100"
                      placeholder="Full name"
                    />
                    <select
                      value={contactForm.role}
                      onChange={(event) => setContactForm((prev) => ({ ...prev, role: event.target.value }))}
                      className="w-full bg-black border border-border-subtle chamfer-4 px-3 py-2 text-sm text-zinc-100"
                    >
                      {CONTACT_ROLES.map((role) => <option key={role} value={role}>{role}</option>)}
                    </select>
                    <input
                      value={contactForm.phone}
                      onChange={(event) => setContactForm((prev) => ({ ...prev, phone: event.target.value }))}
                      className="w-full bg-black border border-border-subtle chamfer-4 px-3 py-2 text-sm text-zinc-100"
                      placeholder="Phone"
                    />
                    <input
                      value={contactForm.email}
                      onChange={(event) => setContactForm((prev) => ({ ...prev, email: event.target.value }))}
                      className="w-full bg-black border border-border-subtle chamfer-4 px-3 py-2 text-sm text-zinc-100"
                      placeholder="Email"
                    />
                    <textarea
                      value={contactForm.notes}
                      onChange={(event) => setContactForm((prev) => ({ ...prev, notes: event.target.value }))}
                      className="w-full h-20 bg-black border border-border-subtle chamfer-4 px-3 py-2 text-sm text-zinc-100"
                      placeholder="Routing notes"
                    />
                    <button
                      onClick={() => void handleAddContact()}
                      disabled={busyAction === 'add-contact'}
                      className="quantum-btn-primary w-full disabled:opacity-50"
                    >
                      {busyAction === 'add-contact' ? 'Adding…' : '+ Add Contact'}
                    </button>
                  </div>
                </div>
              ) : activeTab === 'friction' ? (
                <div className="grid grid-cols-2 gap-4">
                  <div className="bg-[#0A0A0B] border border-border-subtle chamfer-8 p-4">
                    <div className="text-micro uppercase tracking-widest text-zinc-500 mb-3">Friction Board</div>
                    {selectedFriction.length === 0 ? (
                      <QuantumEmptyState title="No friction flags" description="Raise operational friction events (wait times, communication, documentation) for governance and resolution." />
                    ) : (
                      <div className="space-y-2 max-h-[460px] overflow-y-auto pr-1">
                        {selectedFriction.map((flag) => (
                          <div key={flag.id} className="bg-black border border-border-subtle chamfer-8 px-3 py-2">
                            <div className="flex items-center justify-between gap-2">
                              <div className="text-sm font-semibold text-zinc-100">{flag.title}</div>
                              <span className={`text-[10px] font-bold px-2 py-0.5 chamfer-4 border ${
                                flag.is_active
                                  ? 'bg-red-900/20 border-red-500/30 text-red-300'
                                  : 'bg-green-900/20 border-green-500/30 text-green-300'
                              }`}>
                                {flag.is_active ? 'ACTIVE' : 'RESOLVED'}
                              </span>
                            </div>
                            <div className="text-micro text-zinc-500 mt-1">{flag.category} • {new Date(flag.created_at).toLocaleString()}</div>
                            <div className="text-sm text-zinc-400 mt-1">{flag.description}</div>
                            {flag.resolution_notes && (
                              <div className="text-micro text-green-300 mt-1">Resolution: {flag.resolution_notes}</div>
                            )}
                            {flag.is_active && (
                              <button
                                onClick={() => void handleResolveFriction(flag.id)}
                                disabled={busyAction === `resolve-friction-${flag.id}`}
                                className="mt-2 quantum-btn-sm"
                              >
                                {busyAction === `resolve-friction-${flag.id}` ? 'Resolving…' : 'Resolve'}
                              </button>
                            )}
                          </div>
                        ))}
                      </div>
                    )}
                  </div>
                  <div className="bg-[#0A0A0B] border border-border-subtle chamfer-8 p-4 space-y-3">
                    <div className="text-micro uppercase tracking-widest text-zinc-500">Raise Friction Flag</div>
                    <select
                      value={frictionForm.category}
                      onChange={(event) => setFrictionForm((prev) => ({ ...prev, category: event.target.value }))}
                      className="w-full bg-black border border-border-subtle chamfer-4 px-3 py-2 text-sm text-zinc-100"
                    >
                      {FRICTION_CATEGORIES.map((category) => <option key={category} value={category}>{category}</option>)}
                    </select>
                    <input
                      value={frictionForm.title}
                      onChange={(event) => setFrictionForm((prev) => ({ ...prev, title: event.target.value }))}
                      className="w-full bg-black border border-border-subtle chamfer-4 px-3 py-2 text-sm text-zinc-100"
                      placeholder="Short title"
                    />
                    <textarea
                      value={frictionForm.description}
                      onChange={(event) => setFrictionForm((prev) => ({ ...prev, description: event.target.value }))}
                      className="w-full h-28 bg-black border border-border-subtle chamfer-4 px-3 py-2 text-sm text-zinc-100"
                      placeholder="Describe operational impact and required mitigation."
                    />
                    <button
                      onClick={() => void handleAddFriction()}
                      disabled={busyAction === 'add-friction'}
                      className="quantum-btn-primary w-full disabled:opacity-50"
                    >
                      {busyAction === 'add-friction' ? 'Creating…' : '+ Raise Friction Flag'}
                    </button>
                  </div>
                </div>
              ) : activeTab === 'warnings' ? (
                <div className="grid grid-cols-2 gap-4">
                  <div className="bg-[#0A0A0B] border border-border-subtle chamfer-8 p-4">
                    <div className="text-micro uppercase tracking-widest text-zinc-500 mb-3">Warning Flags</div>
                    {selectedWarnings.length === 0 ? (
                      <QuantumEmptyState title="No warning flags" description="Create warning flags for safety and compliance-sensitive facility issues." />
                    ) : (
                      <div className="space-y-2 max-h-[460px] overflow-y-auto pr-1">
                        {selectedWarnings.map((warning) => (
                          <div key={warning.id} className="bg-black border border-border-subtle chamfer-8 px-3 py-2">
                            <div className="flex items-center justify-between">
                              <div className="text-sm font-semibold text-zinc-100">{warning.title}</div>
                              <span className={`text-[10px] font-bold px-2 py-0.5 chamfer-4 border ${severityStyle(warning.severity)}`}>
                                {warning.severity}
                              </span>
                            </div>
                            <div className="text-micro text-zinc-500 mt-1">{warning.flag_type} • {new Date(warning.created_at).toLocaleString()}</div>
                            <div className="text-sm text-zinc-400 mt-1">{warning.description}</div>
                            {warning.resolution_notes && (
                              <div className="text-micro text-green-300 mt-1">Resolution: {warning.resolution_notes}</div>
                            )}
                            {warning.is_active && (
                              <button
                                onClick={() => void handleResolveWarning(warning.id)}
                                disabled={busyAction === `resolve-warning-${warning.id}`}
                                className="mt-2 quantum-btn-sm"
                              >
                                {busyAction === `resolve-warning-${warning.id}` ? 'Resolving…' : 'Resolve'}
                              </button>
                            )}
                          </div>
                        ))}
                      </div>
                    )}
                  </div>
                  <div className="bg-[#0A0A0B] border border-border-subtle chamfer-8 p-4 space-y-3">
                    <div className="text-micro uppercase tracking-widest text-zinc-500">Create Warning</div>
                    <select
                      value={warningForm.severity}
                      onChange={(event) => setWarningForm((prev) => ({ ...prev, severity: event.target.value }))}
                      className="w-full bg-black border border-border-subtle chamfer-4 px-3 py-2 text-sm text-zinc-100"
                    >
                      {WARNING_SEVERITIES.map((severity) => <option key={severity} value={severity}>{severity}</option>)}
                    </select>
                    <input
                      value={warningForm.flag_type}
                      onChange={(event) => setWarningForm((prev) => ({ ...prev, flag_type: event.target.value }))}
                      className="w-full bg-black border border-border-subtle chamfer-4 px-3 py-2 text-sm text-zinc-100"
                      placeholder="Flag type (e.g., safety, communication_gap)"
                    />
                    <input
                      value={warningForm.title}
                      onChange={(event) => setWarningForm((prev) => ({ ...prev, title: event.target.value }))}
                      className="w-full bg-black border border-border-subtle chamfer-4 px-3 py-2 text-sm text-zinc-100"
                      placeholder="Warning title"
                    />
                    <textarea
                      value={warningForm.description}
                      onChange={(event) => setWarningForm((prev) => ({ ...prev, description: event.target.value }))}
                      className="w-full h-28 bg-black border border-border-subtle chamfer-4 px-3 py-2 text-sm text-zinc-100"
                      placeholder="Why this warning matters and how responders should adapt."
                    />
                    <button
                      onClick={() => void handleAddWarning()}
                      disabled={busyAction === 'add-warning'}
                      className="quantum-btn-primary w-full disabled:opacity-50"
                    >
                      {busyAction === 'add-warning' ? 'Creating…' : '+ Create Warning'}
                    </button>
                  </div>
                </div>
              ) : activeTab === 'timeline' ? (
                <div className="bg-[#0A0A0B] border border-border-subtle chamfer-8 p-4">
                  <div className="text-micro uppercase tracking-widest text-zinc-500 mb-3">Relationship Timeline</div>
                  {selectedTimeline.length === 0 ? (
                    <QuantumEmptyState title="No timeline events" description="Timeline events will appear as handoffs, notes, and flags are recorded." />
                  ) : (
                    <div className="space-y-2 max-h-[520px] overflow-y-auto pr-1">
                      {selectedTimeline.map((event) => (
                        <div key={event.id} className="bg-black border border-border-subtle chamfer-8 px-3 py-2">
                          <div className="flex items-center justify-between gap-2">
                            <span className="text-sm font-semibold text-zinc-100">{event.title}</span>
                            <span className="text-[10px] text-zinc-500 font-mono">{new Date(event.created_at).toLocaleString()}</span>
                          </div>
                          <div className="text-micro text-brand-orange mt-0.5">{event.event_type} • {event.source}</div>
                          <div className="text-sm text-zinc-400 mt-1">{event.description}</div>
                        </div>
                      ))}
                    </div>
                  )}
                </div>
              ) : activeTab === 'notes' ? (
                <div className="grid grid-cols-2 gap-4">
                  <div className="bg-[#0A0A0B] border border-border-subtle chamfer-8 p-4">
                    <div className="text-micro uppercase tracking-widest text-zinc-500 mb-3">Relationship Notes</div>
                    {selectedNotes.length === 0 ? (
                      <QuantumEmptyState title="No notes" description="Capture handoff, operational, and billing relationship context." />
                    ) : (
                      <div className="space-y-2 max-h-[460px] overflow-y-auto pr-1">
                        {selectedNotes.map((note) => (
                          <div key={note.id} className="bg-black border border-border-subtle chamfer-8 px-3 py-2">
                            <div className="flex items-center justify-between">
                              <span className="text-xs font-bold text-brand-orange uppercase tracking-widest">{note.note_type}</span>
                              <span className="text-[10px] text-zinc-500 font-mono">{new Date(note.created_at).toLocaleString()}</span>
                            </div>
                            <div className="text-sm text-zinc-400 mt-1 whitespace-pre-wrap">{note.content}</div>
                          </div>
                        ))}
                      </div>
                    )}
                  </div>
                  <div className="bg-[#0A0A0B] border border-border-subtle chamfer-8 p-4 space-y-3">
                    <div className="text-micro uppercase tracking-widest text-zinc-500">Add Note</div>
                    <input
                      value={noteForm.note_type}
                      onChange={(event) => setNoteForm((prev) => ({ ...prev, note_type: event.target.value }))}
                      className="w-full bg-black border border-border-subtle chamfer-4 px-3 py-2 text-sm text-zinc-100"
                      placeholder="Note type (operational, billing, handoff)"
                    />
                    <textarea
                      value={noteForm.content}
                      onChange={(event) => setNoteForm((prev) => ({ ...prev, content: event.target.value }))}
                      className="w-full h-32 bg-black border border-border-subtle chamfer-4 px-3 py-2 text-sm text-zinc-100"
                      placeholder="Capture context, constraints, and follow-up actions."
                    />
                    <label className="flex items-center gap-2 text-sm text-zinc-400">
                      <input
                        type="checkbox"
                        checked={noteForm.is_internal}
                        onChange={(event) => setNoteForm((prev) => ({ ...prev, is_internal: event.target.checked }))}
                        className="accent-brand-orange"
                      />
                      Internal note
                    </label>
                    <button
                      onClick={() => void handleAddNote()}
                      disabled={busyAction === 'add-note'}
                      className="quantum-btn-primary w-full disabled:opacity-50"
                    >
                      {busyAction === 'add-note' ? 'Adding…' : '+ Add Note'}
                    </button>
                  </div>
                </div>
              ) : (
                <div className="grid grid-cols-2 gap-4">
                  <div className="bg-[#0A0A0B] border border-border-subtle chamfer-8 p-4">
                    <div className="text-micro uppercase tracking-widest text-zinc-500 mb-3">AI Relationship Issues</div>
                    {facilityIssues.length === 0 ? (
                      <QuantumEmptyState title="No AI issues for this facility" description="No blocking/high recommendation currently targeted to this facility profile." />
                    ) : (
                      <div className="space-y-2 max-h-[520px] overflow-y-auto pr-1">
                        {facilityIssues.map((issue, index) => (
                          <div key={`${issue.issue}-${index}`} className="bg-black border border-border-subtle chamfer-8 px-3 py-2">
                            <div className="flex items-center justify-between gap-2">
                              <span className="text-sm font-semibold text-zinc-100">{issue.issue}</span>
                              <span className={`text-[10px] font-bold px-2 py-0.5 chamfer-4 border ${severityStyle(issue.severity)}`}>
                                {issue.severity}
                              </span>
                            </div>
                            <div className="text-micro text-zinc-500 mt-1">{issue.source} • confidence: {issue.confidence} • review: {issue.human_review}</div>
                            <div className="text-sm text-red-300 mt-2">{issue.what_is_wrong}</div>
                            <div className="text-sm text-yellow-300 mt-1">{issue.why_it_matters}</div>
                            <div className="text-sm text-green-300 mt-1">{issue.what_you_should_do}</div>
                          </div>
                        ))}
                      </div>
                    )}
                  </div>

                  <div className="bg-[#0A0A0B] border border-border-subtle chamfer-8 p-4">
                    <div className="text-micro uppercase tracking-widest text-zinc-500 mb-3">Command Top Actions</div>
                    {topActions.length === 0 ? (
                      <QuantumEmptyState title="No top actions" description="Relationship command actions will appear when system thresholds are crossed." />
                    ) : (
                      <div className="space-y-2 max-h-[520px] overflow-y-auto pr-1">
                        {topActions.map((action, index) => (
                          <div key={`${action.title}-${index}`} className="bg-black border border-border-subtle chamfer-8 px-3 py-2">
                            <div className="flex items-center justify-between">
                              <div className="text-sm font-semibold text-zinc-100">#{action.priority} {action.title}</div>
                              <span className={`text-[10px] font-bold px-2 py-0.5 chamfer-4 border ${severityStyle(action.severity)}`}>
                                {action.severity}
                              </span>
                            </div>
                            <div className="text-micro text-brand-orange mt-1 uppercase tracking-widest">{action.category}</div>
                            <div className="text-sm text-zinc-400 mt-1">{action.description}</div>
                          </div>
                        ))}
                      </div>
                    )}
                  </div>
                </div>
              )}
            </>
          )}
        </div>
      </div>
    </div>
  );
}
