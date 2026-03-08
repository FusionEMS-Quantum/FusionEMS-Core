'use client';

import React, { useState, useMemo, useEffect, useCallback } from 'react';
import AppShell from '@/components/AppShell';
import { PlateCard, MetricPlate } from '@/components/ui/PlateCard';
import { StatusChip } from '@/components/ui/StatusChip';
import type { StatusVariant } from '@/lib/design-system/tokens';
import {
  AlertTriangle, Clock, FileCheck, Download,
  ChevronRight, ChevronDown, Activity, TrendingUp, TrendingDown,
  Minus, ExternalLink, FileText, CreditCard, Award, Scale,
  Eye, Lock, Clipboard, Pill, ArrowRight,
  AlertCircle, Layers, Database, CheckCircle2,
  RefreshCw, ChevronUp, Target,
} from 'lucide-react';

const API_BASE = process.env.NEXT_PUBLIC_API_BASE ?? '';

// ═══════════════════════════════════════════════════════════════════════════════
// TYPES
// ═══════════════════════════════════════════════════════════════════════════════

type DomainKey = 'nemsis' | 'hipaa' | 'pcr' | 'billing' | 'accreditation' | 'dea' | 'cms';

type ImpactArea =
  | 'billing' | 'patient-safety' | 'licensing' | 'dea'
  | 'hipaa' | 'audit-risk' | 'nemsis-export' | 'accreditation'
  | 'cms' | 'revenue';

type ActionState =
  | 'no-action' | 'monitor' | 'review-required' | 'blocking'
  | 'escalated' | 'awaiting-evidence' | 'corrective-action';

type TrendDir = 'up' | 'down' | 'stable';
type RiskTier = 'low' | 'medium' | 'high';

interface ComplianceItem {
  id: string;
  name: string;
  description: string;
  status: StatusVariant;
  statusLabel: string;
  lastChecked: string;
  nextDue?: string;
  trend?: TrendDir;
  trendSummary?: string;
  impactAreas: ImpactArea[];
  actionState: ActionState;
  evidenceCount: number;
  owner?: string;
  linkedRecords?: number;
  policyBasis?: string;
}

interface DomainSummary {
  score: number;
  passing: number;
  warning: number;
  critical: number;
  lastReviewed: string;
  trend: TrendDir;
  billingRisk: RiskTier;
  licensureRisk: RiskTier;
  operationalRisk: RiskTier;
  suggestedActions: string[];
}

interface PriorityAlert {
  id: string;
  severity: 'critical' | 'warning';
  domain: DomainKey;
  domainLabel: string;
  title: string;
  reason: string;
  nextAction: string;
}

interface ActionQueueItem {
  id: string;
  title: string;
  owner: string;
  dueDate: string;
  severity: StatusVariant;
  domain: DomainKey;
  domainLabel: string;
  isOverdue: boolean;
  reviewState: 'open' | 'in-progress' | 'pending-review';
}

// ═══════════════════════════════════════════════════════════════════════════════
// DOMAIN CONFIGURATION
// ═══════════════════════════════════════════════════════════════════════════════

interface DomainMeta { label: string; accent: string; icon: React.ElementType }

const DOMAIN_CONFIG: Record<DomainKey, DomainMeta> = {
  nemsis:        { label: 'NEMSIS',             accent: '#22C55E', icon: Database },
  hipaa:         { label: 'HIPAA',              accent: '#38BDF8', icon: Lock },
  pcr:           { label: 'PCR Completion',     accent: '#F59E0B', icon: Clipboard },
  billing:       { label: 'Billing Compliance', accent: '#22d3ee', icon: CreditCard },
  accreditation: { label: 'Accreditation',      accent: '#a855f7', icon: Award },
  dea:           { label: 'DEA',                accent: '#FF2D2D', icon: Pill },
  cms:           { label: 'CMS',                accent: '#FF6A00', icon: Scale },
};

const TABS: DomainKey[] = ['nemsis', 'hipaa', 'pcr', 'billing', 'accreditation', 'dea', 'cms'];

const IMPACT_LABELS: Record<ImpactArea, { label: string; color: string }> = {
  billing:         { label: 'Billing',         color: '#22d3ee' },
  'patient-safety':{ label: 'Patient Safety',  color: '#FF2D2D' },
  licensing:       { label: 'Licensing',        color: '#a855f7' },
  dea:             { label: 'DEA',              color: '#FF2D2D' },
  hipaa:           { label: 'HIPAA',            color: '#38BDF8' },
  'audit-risk':    { label: 'Audit Risk',       color: '#F59E0B' },
  'nemsis-export': { label: 'NEMSIS Export',    color: '#22C55E' },
  accreditation:   { label: 'Accreditation',    color: '#a855f7' },
  cms:             { label: 'CMS',              color: '#FF6A00' },
  revenue:         { label: 'Revenue',          color: '#22d3ee' },
};

const ACTION_STATE_MAP: Record<ActionState, { label: string; status: StatusVariant }> = {
  'no-action':         { label: 'No Action Needed',       status: 'active' },
  'monitor':           { label: 'Monitor',                status: 'info' },
  'review-required':   { label: 'Review Required',        status: 'warning' },
  'blocking':          { label: 'Blocking',               status: 'critical' },
  'escalated':         { label: 'Escalated',              status: 'critical' },
  'awaiting-evidence': { label: 'Awaiting Evidence',      status: 'warning' },
  'corrective-action': { label: 'Corrective Action Open', status: 'override' },
};

// ═══════════════════════════════════════════════════════════════════════════════
// COMPLIANCE DATA — 7 DOMAINS
// ═══════════════════════════════════════════════════════════════════════════════

const COMPLIANCE_DATA: Record<DomainKey, ComplianceItem[]> = {
  nemsis: [
    { id:'n1', name:'Schema Validation', description:'NEMSIS v3.5.1 XSD schema conformance check against all submitted records', status:'active', statusLabel:'Passing', lastChecked:'2026-03-08 06:00', impactAreas:['nemsis-export','audit-risk'], actionState:'no-action', evidenceCount:12, trend:'stable', trendSummary:'Stable 30d', policyBasis:'NEMSIS v3.5.1 Technical Implementation Guide' },
    { id:'n2', name:'Required Fields', description:'Mandatory NEMSIS data elements present in 100% of active PCRs', status:'active', statusLabel:'Passing', lastChecked:'2026-03-08 06:00', impactAreas:['nemsis-export','billing'], actionState:'no-action', evidenceCount:8, trend:'stable', trendSummary:'Stable' },
    { id:'n3', name:'Demographic Completeness', description:'Patient demographic fields fully populated per state requirement', status:'warning', statusLabel:'94.1% Complete', lastChecked:'2026-03-08 04:30', impactAreas:['nemsis-export','billing','audit-risk'], actionState:'review-required', evidenceCount:5, trend:'up', trendSummary:'+1.2% this week', owner:'QA Team', policyBasis:'State NEMSIS Reporting Requirements' },
    { id:'n4', name:'Timestamp Accuracy', description:'Dispatch, on-scene, and transport times cross-validated against CAD feed', status:'active', statusLabel:'Passing', lastChecked:'2026-03-08 05:45', impactAreas:['nemsis-export','audit-risk'], actionState:'no-action', evidenceCount:6, trend:'stable', trendSummary:'Stable' },
    { id:'n5', name:'Unit Certification', description:'All responding units certified at appropriate ALS/BLS level per call type', status:'active', statusLabel:'Compliant', lastChecked:'2026-03-07 23:00', impactAreas:['licensing','audit-risk'], actionState:'no-action', evidenceCount:4, trend:'stable', trendSummary:'Stable' },
    { id:'n6', name:'Crew Credentials', description:'Active state certifications verified for all personnel on submitted runs', status:'warning', statusLabel:'2 Expiring Soon', lastChecked:'2026-03-08 00:00', nextDue:'2026-03-15', impactAreas:['licensing','patient-safety'], actionState:'review-required', evidenceCount:3, trend:'down', trendSummary:'2 creds expiring', owner:'HR / Credentialing', policyBasis:'State EMS Certification Requirements' },
    { id:'n7', name:'Dispatch Codes', description:'EMD nature codes mapped to valid NEMSIS situation codes in all records', status:'active', statusLabel:'Passing', lastChecked:'2026-03-08 06:00', impactAreas:['nemsis-export'], actionState:'no-action', evidenceCount:7, trend:'stable', trendSummary:'Stable' },
    { id:'n8', name:'Protocol Adherence', description:'Medication and procedure documentation matches active protocol set', status:'active', statusLabel:'Passing', lastChecked:'2026-03-07 22:00', impactAreas:['patient-safety','audit-risk'], actionState:'no-action', evidenceCount:9, trend:'stable', trendSummary:'Stable' },
    { id:'n9', name:'Export Readiness Score', description:'Overall readiness index for state NEMSIS data submission batch', status:'active', statusLabel:'98.2%', lastChecked:'2026-03-08 06:00', impactAreas:['nemsis-export','audit-risk'], actionState:'no-action', evidenceCount:2, trend:'up', trendSummary:'+0.3% this cycle' },
    { id:'n10', name:'Failed Export Count', description:'Records that failed validation during last state submission batch', status:'warning', statusLabel:'3 Records', lastChecked:'2026-03-08 06:00', impactAreas:['nemsis-export','audit-risk'], actionState:'review-required', evidenceCount:3, trend:'down', trendSummary:'+1 since last batch', owner:'Data Quality' },
    { id:'n11', name:'CAD-to-PCR Mismatch', description:'Discrepancies between CAD dispatch record and PCR document times or unit assignment', status:'info', statusLabel:'1 Pending', lastChecked:'2026-03-08 05:00', impactAreas:['nemsis-export','audit-risk'], actionState:'monitor', evidenceCount:1, trend:'stable', trendSummary:'Low volume' },
  ],
  hipaa: [
    { id:'h1', name:'PHI Encryption at Rest', description:'All PHI stored in database encrypted via AES-256; keys managed in AWS KMS', status:'active', statusLabel:'Enforced', lastChecked:'2026-03-08 06:00', impactAreas:['hipaa','audit-risk'], actionState:'no-action', evidenceCount:4, trend:'stable', trendSummary:'Continuously enforced', policyBasis:'HIPAA §164.312(a)(2)(iv)' },
    { id:'h2', name:'PHI Encryption in Transit', description:'TLS 1.3 enforced on all API endpoints and inter-service communication', status:'active', statusLabel:'Enforced', lastChecked:'2026-03-08 06:00', impactAreas:['hipaa','audit-risk'], actionState:'no-action', evidenceCount:3, trend:'stable', trendSummary:'Stable', policyBasis:'HIPAA §164.312(e)(1)' },
    { id:'h3', name:'Access Log Audit', description:'All PHI access events logged to immutable CloudWatch Logs with 7-year retention', status:'active', statusLabel:'Active', lastChecked:'2026-03-08 06:00', impactAreas:['hipaa','audit-risk'], actionState:'no-action', evidenceCount:6, trend:'stable', trendSummary:'Stable' },
    { id:'h4', name:'Minimum Necessary Rule', description:'Role-based access controls limit PHI exposure to job-function scope only', status:'active', statusLabel:'Enforced', lastChecked:'2026-03-08 04:00', impactAreas:['hipaa'], actionState:'no-action', evidenceCount:5, trend:'stable', trendSummary:'Stable', policyBasis:'HIPAA §164.502(b)' },
    { id:'h5', name:'BAA Status', description:'Executed Business Associate Agreements on file for all covered sub-processors', status:'warning', statusLabel:'1 Pending Renewal', lastChecked:'2026-03-07 17:00', nextDue:'2026-03-31', impactAreas:['hipaa','audit-risk'], actionState:'review-required', evidenceCount:2, trend:'down', trendSummary:'Renewal due Mar 31', owner:'Legal' },
    { id:'h6', name:'Breach Notification Procedure', description:'Incident response runbook reviewed and contact list current', status:'active', statusLabel:'Current', lastChecked:'2026-01-15 09:00', impactAreas:['hipaa'], actionState:'no-action', evidenceCount:3, trend:'stable', trendSummary:'Reviewed Jan 15' },
    { id:'h7', name:'Workforce Training', description:'Annual HIPAA training completion rate for all credentialed staff', status:'warning', statusLabel:'87% Complete', lastChecked:'2026-03-07 00:00', nextDue:'2026-03-31', impactAreas:['hipaa','audit-risk'], actionState:'review-required', evidenceCount:4, trend:'up', trendSummary:'+5% this month', owner:'Training Coord', policyBasis:'HIPAA §164.530(b)(1)' },
    { id:'h8', name:'Data Retention', description:'PCR records retained per CMS 7-year rule; automated lifecycle policies active', status:'active', statusLabel:'Compliant', lastChecked:'2026-02-01 00:00', impactAreas:['hipaa','cms','audit-risk'], actionState:'no-action', evidenceCount:2, trend:'stable', trendSummary:'Stable' },
    { id:'h9', name:'Anomalous PHI Access', description:'Flagged access patterns deviating from baseline behavior models', status:'warning', statusLabel:'2 Flagged', lastChecked:'2026-03-08 05:30', impactAreas:['hipaa','audit-risk'], actionState:'review-required', evidenceCount:2, trend:'down', trendSummary:'+2 new flags', owner:'Security' },
    { id:'h10', name:'Inactive User Access', description:'Accounts with no login in 60+ days still retaining PHI access privileges', status:'warning', statusLabel:'4 Accounts', lastChecked:'2026-03-08 00:00', impactAreas:['hipaa'], actionState:'review-required', evidenceCount:0, trend:'stable', trendSummary:'Quarterly review due', owner:'IT Admin' },
    { id:'h11', name:'Privileged Role Audit', description:'Admin and superuser role assignments reviewed against active job functions', status:'active', statusLabel:'Reviewed', lastChecked:'2026-03-01 00:00', impactAreas:['hipaa','audit-risk'], actionState:'no-action', evidenceCount:3, trend:'stable', trendSummary:'Last reviewed Mar 1' },
  ],
  pcr: [
    { id:'p1', name:'Avg Completion Time', description:'Mean time from call close to PCR finalization across all active units', status:'warning', statusLabel:'38 min avg', lastChecked:'2026-03-08 06:00', impactAreas:['billing','audit-risk'], actionState:'monitor', evidenceCount:2, trend:'up', trendSummary:'-4 min this week' },
    { id:'p2', name:'Fields Missing', description:'PCRs with one or more required billing or clinical fields left blank', status:'critical', statusLabel:'14 Records', lastChecked:'2026-03-08 06:00', impactAreas:['billing','nemsis-export','audit-risk'], actionState:'blocking', evidenceCount:14, trend:'down', trendSummary:'+3 since yesterday', owner:'Field Supervisors' },
    { id:'p3', name:'Late Signatures', description:'Crew chief signatures not applied within the required 24-hour window', status:'warning', statusLabel:'6 Pending', lastChecked:'2026-03-08 05:00', impactAreas:['billing','audit-risk'], actionState:'review-required', evidenceCount:6, trend:'stable', trendSummary:'Stable', owner:'Crew Chiefs' },
    { id:'p4', name:'Protocol Deviations', description:'Documented deviations from standing orders requiring medical director review', status:'info', statusLabel:'2 Open', lastChecked:'2026-03-07 20:00', impactAreas:['patient-safety','audit-risk'], actionState:'review-required', evidenceCount:2, trend:'stable', trendSummary:'Low volume', owner:'Medical Director' },
    { id:'p5', name:'Supervisor Reviews', description:'QA supervisor review queue — records flagged for clinical documentation issues', status:'warning', statusLabel:'9 Queued', lastChecked:'2026-03-08 06:00', impactAreas:['audit-risk','billing'], actionState:'review-required', evidenceCount:9, trend:'down', trendSummary:'+2 since yesterday', owner:'QA Supervisors' },
    { id:'p6', name:'Unsigned Charts', description:'PCR charts awaiting any crew member signature before finalization', status:'critical', statusLabel:'8 Charts', lastChecked:'2026-03-08 06:00', impactAreas:['billing','audit-risk','licensing'], actionState:'blocking', evidenceCount:8, trend:'down', trendSummary:'+2 today', owner:'Field Supervisors', policyBasis:'State EMS Documentation Requirements' },
    { id:'p7', name:'Charts Blocking Billing', description:'Incomplete or unfiled charts directly preventing claim submission', status:'critical', statusLabel:'6 Charts', lastChecked:'2026-03-08 06:00', impactAreas:['billing','revenue'], actionState:'blocking', evidenceCount:6, trend:'down', trendSummary:'Revenue impact active', owner:'Billing Team' },
    { id:'p8', name:'Missing Patient Signature', description:'Transport records missing patient or authorized representative signature', status:'warning', statusLabel:'3 Records', lastChecked:'2026-03-08 05:30', impactAreas:['billing','cms'], actionState:'review-required', evidenceCount:3, trend:'stable', trendSummary:'Stable' },
    { id:'p9', name:'QA Return Rate', description:'Percentage of charts returned for correction after initial supervisor review', status:'info', statusLabel:'4.2%', lastChecked:'2026-03-08 06:00', impactAreas:['audit-risk'], actionState:'monitor', evidenceCount:1, trend:'up', trendSummary:'-0.5% this month' },
  ],
  billing: [
    { id:'b1', name:'ABN Compliance', description:'Advance Beneficiary Notice obtained and documented for all non-covered transports', status:'active', statusLabel:'Compliant', lastChecked:'2026-03-08 06:00', impactAreas:['billing','cms','revenue'], actionState:'no-action', evidenceCount:8, trend:'stable', trendSummary:'Stable', policyBasis:'CMS ABN Requirements (CMS-R-131)' },
    { id:'b2', name:'Medical Necessity Docs', description:'Certificate of Medical Necessity on file for all recurring transport authorizations', status:'warning', statusLabel:'3 Missing', lastChecked:'2026-03-08 05:00', nextDue:'2026-03-11', impactAreas:['billing','cms','revenue'], actionState:'review-required', evidenceCount:5, trend:'down', trendSummary:'+1 missing this week', owner:'Billing Team', policyBasis:'CMS CMN/PCS Requirements' },
    { id:'b3', name:'Modifier Accuracy', description:'ALS/BLS level modifiers validated against PCR clinical narrative and crew cert level', status:'active', statusLabel:'99.1% Accurate', lastChecked:'2026-03-08 06:00', impactAreas:['billing','cms','audit-risk'], actionState:'no-action', evidenceCount:6, trend:'stable', trendSummary:'Stable' },
    { id:'b4', name:'Diagnosis Coding', description:'ICD-10 diagnosis codes present and valid on all submitted professional claims', status:'active', statusLabel:'Passing', lastChecked:'2026-03-08 06:00', impactAreas:['billing','audit-risk'], actionState:'no-action', evidenceCount:4, trend:'stable', trendSummary:'Stable' },
    { id:'b5', name:'Prior Auth Rate', description:'Percentage of non-emergency transports with payer prior authorization on file', status:'warning', statusLabel:'91% Coverage', lastChecked:'2026-03-07 22:00', impactAreas:['billing','revenue'], actionState:'review-required', evidenceCount:3, trend:'up', trendSummary:'+2% this month', owner:'Auth Coordinator' },
    { id:'b6', name:'PTAN Active', description:'Medicare Provider Transaction Access Number current and billing privileges active', status:'active', statusLabel:'Active', lastChecked:'2026-02-01 00:00', impactAreas:['billing','cms','licensing'], actionState:'no-action', evidenceCount:2, trend:'stable', trendSummary:'Stable' },
    { id:'b7', name:'Recurring Transport Cert', description:'PCS/CMN certifications for recurring non-emergency transports approaching expiration', status:'warning', statusLabel:'2 Expiring', lastChecked:'2026-03-08 05:00', nextDue:'2026-03-15', impactAreas:['billing','cms','revenue'], actionState:'review-required', evidenceCount:2, trend:'down', trendSummary:'2 due within 7 days', owner:'Billing Team' },
    { id:'b8', name:'Claims at Denial Risk', description:'Submitted claims flagged by pre-adjudication analysis as likely to be denied', status:'critical', statusLabel:'4 Claims', lastChecked:'2026-03-08 06:00', impactAreas:['billing','revenue','cms'], actionState:'blocking', evidenceCount:4, trend:'down', trendSummary:'+2 this week', owner:'Billing Team' },
    { id:'b9', name:'Payer Documentation Gaps', description:'Payer-specific documentation requirements not met on pending claims', status:'warning', statusLabel:'5 Gaps', lastChecked:'2026-03-08 05:30', impactAreas:['billing','revenue'], actionState:'review-required', evidenceCount:5, trend:'stable', trendSummary:'Stable' },
  ],
  accreditation: [
    { id:'a1', name:'CoAEMSP Status', description:'Committee on Accreditation of EMS Professions program accreditation standing', status:'active', statusLabel:'Accredited', lastChecked:'2026-01-01 00:00', impactAreas:['accreditation','licensing'], actionState:'no-action', evidenceCount:3, trend:'stable', trendSummary:'Stable' },
    { id:'a2', name:'CAAS Status', description:'Commission on Accreditation of Ambulance Services certification current', status:'info', statusLabel:'Under Review', lastChecked:'2026-02-14 00:00', impactAreas:['accreditation','audit-risk'], actionState:'awaiting-evidence', evidenceCount:6, trend:'stable', trendSummary:'Review in progress', owner:'Accreditation Coord' },
    { id:'a3', name:'State Licensure', description:'State EMS agency operating license current and all endorsements valid', status:'active', statusLabel:'Current', lastChecked:'2026-02-01 00:00', impactAreas:['licensing','accreditation'], actionState:'no-action', evidenceCount:4, trend:'stable', trendSummary:'Stable' },
    { id:'a4', name:'Equipment Calibration', description:'Cardiac monitors, ventilators, and stretchers on current calibration schedule', status:'warning', statusLabel:'4 Units Due', lastChecked:'2026-03-06 08:00', nextDue:'2026-03-15', impactAreas:['accreditation','patient-safety'], actionState:'review-required', evidenceCount:4, trend:'down', trendSummary:'4 overdue units', owner:'Fleet / Maintenance' },
    { id:'a5', name:'QA Meeting Cadence', description:'Monthly quality assurance committee meetings documented and minutes filed', status:'active', statusLabel:'On Schedule', lastChecked:'2026-03-03 00:00', impactAreas:['accreditation','audit-risk'], actionState:'no-action', evidenceCount:12, trend:'stable', trendSummary:'Stable' },
    { id:'a6', name:'CE Compliance Rate', description:'Continuing education hours on track for all certified personnel this cycle', status:'warning', statusLabel:'83% On Track', lastChecked:'2026-03-08 00:00', impactAreas:['accreditation','licensing'], actionState:'review-required', evidenceCount:5, trend:'up', trendSummary:'+3% this month', owner:'Training Coord' },
    { id:'a7', name:'Evidence Packets Due', description:'Accreditation evidence packets required for upcoming survey or renewal', status:'warning', statusLabel:'2 Packets', lastChecked:'2026-03-08 00:00', nextDue:'2026-03-22', impactAreas:['accreditation','audit-risk'], actionState:'awaiting-evidence', evidenceCount:2, trend:'stable', trendSummary:'Due Mar 22', owner:'Accreditation Coord' },
    { id:'a8', name:'Upcoming Survey Milestones', description:'Scheduled accreditation surveys, site visits, and document submission deadlines', status:'info', statusLabel:'CAAS Apr 15', lastChecked:'2026-03-08 00:00', nextDue:'2026-04-15', impactAreas:['accreditation'], actionState:'monitor', evidenceCount:1, trend:'stable', trendSummary:'On track' },
  ],
  dea: [
    { id:'d1', name:'Narcotics Chain-of-Custody', description:'End-to-end controlled substance custody documentation from receipt to administration or waste', status:'warning', statusLabel:'1 Discrepancy', lastChecked:'2026-03-08 05:30', impactAreas:['dea','patient-safety','licensing'], actionState:'review-required', evidenceCount:4, trend:'down', trendSummary:'1 new discrepancy', owner:'Narcotics Officer', policyBasis:'21 CFR §1304 — DEA Record Keeping' },
    { id:'d2', name:'Controlled Substance Discrepancy', description:'Unreconciled discrepancies in controlled substance inventory counts', status:'critical', statusLabel:'1 Unreconciled', lastChecked:'2026-03-08 06:00', impactAreas:['dea','licensing','audit-risk'], actionState:'blocking', evidenceCount:1, trend:'down', trendSummary:'Requires immediate review', owner:'Narcotics Officer', policyBasis:'21 CFR §1304.21 — Inventory Requirements' },
    { id:'d3', name:'Missing Witness Signatures', description:'Controlled substance waste events lacking required second-party witness signature', status:'warning', statusLabel:'3 Pending', lastChecked:'2026-03-08 05:00', impactAreas:['dea','audit-risk'], actionState:'review-required', evidenceCount:3, trend:'stable', trendSummary:'Stable', owner:'Field Supervisors' },
    { id:'d4', name:'Medication Waste Documentation', description:'Completeness of documentation for all controlled substance waste events', status:'active', statusLabel:'Complete', lastChecked:'2026-03-08 06:00', impactAreas:['dea','audit-risk'], actionState:'no-action', evidenceCount:8, trend:'stable', trendSummary:'Stable' },
    { id:'d5', name:'Lockbox Access Log Review', description:'Secure storage access logs reviewed for anomalous or unauthorized entries', status:'active', statusLabel:'Reviewed', lastChecked:'2026-03-08 04:00', impactAreas:['dea','audit-risk'], actionState:'no-action', evidenceCount:6, trend:'stable', trendSummary:'Stable' },
    { id:'d6', name:'Shift Narcotic Reconciliation', description:'Beginning and end-of-shift narcotic counts reconciled across all active units', status:'active', statusLabel:'Reconciled', lastChecked:'2026-03-08 06:00', impactAreas:['dea'], actionState:'no-action', evidenceCount:12, trend:'stable', trendSummary:'All shifts reconciled' },
    { id:'d7', name:'Overdue Discrepancy Review', description:'Narcotics discrepancies past the 24-hour reconciliation review window', status:'critical', statusLabel:'1 Overdue', lastChecked:'2026-03-08 06:00', impactAreas:['dea','licensing','audit-risk'], actionState:'escalated', evidenceCount:1, trend:'down', trendSummary:'Overdue 36 hours', owner:'Narcotics Officer' },
    { id:'d8', name:'Suspicious Variance Flags', description:'Automated detection of anomalous patterns in controlled substance usage or waste ratios', status:'info', statusLabel:'0 Active', lastChecked:'2026-03-08 06:00', impactAreas:['dea','patient-safety'], actionState:'no-action', evidenceCount:0, trend:'stable', trendSummary:'No anomalies detected' },
  ],
  cms: [
    { id:'c1', name:'ABN Workflow Compliance', description:'Advance Beneficiary Notice procedures followed correctly for all applicable CMS transports', status:'active', statusLabel:'Compliant', lastChecked:'2026-03-08 06:00', impactAreas:['cms','billing','revenue'], actionState:'no-action', evidenceCount:6, trend:'stable', trendSummary:'Stable', policyBasis:'CMS ABN Requirements (CMS-R-131)' },
    { id:'c2', name:'CMN / PCS Completeness', description:'Certificate of Medical Necessity and Physician Certification Statement availability', status:'warning', statusLabel:'3 Missing', lastChecked:'2026-03-08 05:00', nextDue:'2026-03-11', impactAreas:['cms','billing','revenue'], actionState:'review-required', evidenceCount:5, trend:'down', trendSummary:'+1 gap this week', owner:'Billing Team', policyBasis:'CMS CMN/PCS Documentation Standards' },
    { id:'c3', name:'Medical Necessity Readiness', description:'Documentation supports medical necessity for all ambulance transports billed to CMS', status:'active', statusLabel:'Ready', lastChecked:'2026-03-08 06:00', impactAreas:['cms','billing','revenue'], actionState:'no-action', evidenceCount:8, trend:'stable', trendSummary:'Stable' },
    { id:'c4', name:'Prior Authorization Status', description:'Non-emergency repetitive ambulance transports with required prior authorization', status:'warning', statusLabel:'91% Covered', lastChecked:'2026-03-07 22:00', impactAreas:['cms','billing','revenue'], actionState:'review-required', evidenceCount:3, trend:'up', trendSummary:'+2% this month', owner:'Auth Coordinator' },
    { id:'c5', name:'Destination / Origin Validity', description:'Transport origin and destination combinations pass CMS covered-service rules', status:'active', statusLabel:'Passing', lastChecked:'2026-03-08 06:00', impactAreas:['cms','billing'], actionState:'no-action', evidenceCount:4, trend:'stable', trendSummary:'Stable' },
    { id:'c6', name:'Modifier Accuracy', description:'CMS-required modifiers (ALS/BLS/SCT) aligned with clinical documentation', status:'active', statusLabel:'99.1%', lastChecked:'2026-03-08 06:00', impactAreas:['cms','billing','audit-risk'], actionState:'no-action', evidenceCount:5, trend:'stable', trendSummary:'Stable' },
    { id:'c7', name:'Level-of-Care Alignment', description:'Billed level of care matches documented assessment and interventions', status:'active', statusLabel:'Aligned', lastChecked:'2026-03-08 05:30', impactAreas:['cms','billing','audit-risk'], actionState:'no-action', evidenceCount:7, trend:'stable', trendSummary:'Stable' },
    { id:'c8', name:'Billing Doc Mismatch', description:'Claims where billing codes do not align with PCR clinical narrative', status:'warning', statusLabel:'2 Flags', lastChecked:'2026-03-08 06:00', impactAreas:['cms','billing','revenue','audit-risk'], actionState:'review-required', evidenceCount:2, trend:'stable', trendSummary:'Stable', owner:'Billing QA' },
    { id:'c9', name:'Recurrent Transport Docs', description:'Recurring non-emergency transport authorization certifications and supporting documentation', status:'warning', statusLabel:'2 Expiring', lastChecked:'2026-03-08 05:00', nextDue:'2026-03-15', impactAreas:['cms','billing','revenue'], actionState:'review-required', evidenceCount:2, trend:'down', trendSummary:'2 expiring within 7d', owner:'Billing Team' },
    { id:'c10', name:'Denial Risk Indicators', description:'Claims identified by pre-adjudication analysis as high probability of CMS denial', status:'critical', statusLabel:'4 Claims', lastChecked:'2026-03-08 06:00', impactAreas:['cms','billing','revenue'], actionState:'blocking', evidenceCount:4, trend:'down', trendSummary:'+2 this week', owner:'Billing Team' },
  ],
};

// ═══════════════════════════════════════════════════════════════════════════════
// DOMAIN SUMMARIES
// ═══════════════════════════════════════════════════════════════════════════════

const DOMAIN_SUMMARIES: Record<DomainKey, DomainSummary> = {
  nemsis: { score:96, passing:9, warning:2, critical:0, lastReviewed:'2026-03-08 06:00', trend:'up', billingRisk:'low', licensureRisk:'low', operationalRisk:'low', suggestedActions:['Review 3 failed export records','Address demographic completeness gap'] },
  hipaa: { score:91, passing:7, warning:4, critical:0, lastReviewed:'2026-03-08 06:00', trend:'up', billingRisk:'low', licensureRisk:'medium', operationalRisk:'low', suggestedActions:['Complete workforce training to 100%','Renew pending BAA','Review anomalous PHI access','Disable inactive user accounts'] },
  pcr: { score:72, passing:2, warning:4, critical:3, lastReviewed:'2026-03-08 06:00', trend:'down', billingRisk:'high', licensureRisk:'medium', operationalRisk:'high', suggestedActions:['Clear 8 unsigned charts immediately','Resolve 6 charts blocking billing','Collect missing patient signatures'] },
  billing: { score:85, passing:5, warning:3, critical:1, lastReviewed:'2026-03-08 06:00', trend:'stable', billingRisk:'high', licensureRisk:'low', operationalRisk:'medium', suggestedActions:['Address 4 claims at denial risk','Obtain 3 missing CMN documents','Renew 2 expiring transport certs'] },
  accreditation: { score:88, passing:4, warning:3, critical:0, lastReviewed:'2026-03-08 00:00', trend:'up', billingRisk:'low', licensureRisk:'medium', operationalRisk:'low', suggestedActions:['Complete equipment calibration backlog','Prepare evidence packets for CAAS review','Push CE completion to 90%+'] },
  dea: { score:78, passing:4, warning:2, critical:2, lastReviewed:'2026-03-08 06:00', trend:'down', billingRisk:'low', licensureRisk:'high', operationalRisk:'high', suggestedActions:['Reconcile unresolved narcotics discrepancy immediately','Clear overdue discrepancy review','Obtain 3 missing witness signatures'] },
  cms: { score:84, passing:6, warning:3, critical:1, lastReviewed:'2026-03-08 06:00', trend:'stable', billingRisk:'high', licensureRisk:'medium', operationalRisk:'medium', suggestedActions:['Address 4 denial-risk claims before submission','Obtain 3 missing CMN/PCS documents','Resolve billing doc mismatches'] },
};

// ═══════════════════════════════════════════════════════════════════════════════
// PRIORITY ALERTS
// ═══════════════════════════════════════════════════════════════════════════════

const PRIORITY_ALERTS: PriorityAlert[] = [
  { id:'pa1', severity:'critical', domain:'dea', domainLabel:'DEA', title:'Unreconciled narcotics discrepancy — 36 hours overdue', reason:'DEA regulation requires reconciliation within 24 hours. Licensing and audit exposure.', nextAction:'Narcotics Officer must reconcile immediately' },
  { id:'pa2', severity:'critical', domain:'pcr', domainLabel:'PCR', title:'8 unsigned charts blocking billing submission', reason:'Revenue delayed on 8 transports. Charts cannot be billed until signed.', nextAction:'Field supervisors must clear signature backlog today' },
  { id:'pa3', severity:'critical', domain:'cms', domainLabel:'CMS', title:'4 claims at high denial risk — documentation mismatch', reason:'Pre-adjudication flags indicate missing medical necessity documentation.', nextAction:'Billing team review and remediate before batch submission' },
  { id:'pa4', severity:'warning', domain:'billing', domainLabel:'Billing', title:'3 missing CMN/PCS on recurring transports', reason:'Recurring transports without current certification will be denied on submission.', nextAction:'Obtain updated certifications from ordering physicians' },
  { id:'pa5', severity:'warning', domain:'hipaa', domainLabel:'HIPAA', title:'Workforce HIPAA training at 87% — below 90% target', reason:'Non-compliance with training requirements creates audit exposure.', nextAction:'Send training reminders to non-compliant staff by Mar 15' },
];

// ═══════════════════════════════════════════════════════════════════════════════
// ACTION QUEUE
// ═══════════════════════════════════════════════════════════════════════════════

const ACTION_QUEUE: ActionQueueItem[] = [
  { id:'aq1', title:'Reconcile narcotics discrepancy — Unit 14', owner:'M. Torres (Narcotics Officer)', dueDate:'2026-03-07', severity:'critical', domain:'dea', domainLabel:'DEA', isOverdue:true, reviewState:'open' },
  { id:'aq2', title:'Complete unsigned PCR charts (8)', owner:'Field Supervisors', dueDate:'2026-03-08', severity:'critical', domain:'pcr', domainLabel:'PCR', isOverdue:false, reviewState:'in-progress' },
  { id:'aq3', title:'Upload CMN documentation — 3 recurring patients', owner:'J. Kim (Billing)', dueDate:'2026-03-11', severity:'warning', domain:'cms', domainLabel:'CMS', isOverdue:false, reviewState:'open' },
  { id:'aq4', title:'Complete HIPAA workforce training push', owner:'L. Chen (Training Coord)', dueDate:'2026-03-15', severity:'warning', domain:'hipaa', domainLabel:'HIPAA', isOverdue:false, reviewState:'in-progress' },
  { id:'aq5', title:'Submit CAAS evidence packets', owner:'R. Patel (Accreditation)', dueDate:'2026-03-22', severity:'info', domain:'accreditation', domainLabel:'Accreditation', isOverdue:false, reviewState:'open' },
  { id:'aq6', title:'Review anomalous PHI access — 2 flags', owner:'K. Wright (Security)', dueDate:'2026-03-10', severity:'warning', domain:'hipaa', domainLabel:'HIPAA', isOverdue:false, reviewState:'open' },
];

// ═══════════════════════════════════════════════════════════════════════════════
// HELPER COMPONENTS
// ═══════════════════════════════════════════════════════════════════════════════

function TrendBadge({ trend, summary }: { trend?: TrendDir; summary?: string }) {
  if (!trend) return null;
  const Icon = trend === 'up' ? TrendingUp : trend === 'down' ? TrendingDown : Minus;
  const color = trend === 'up' ? '#22C55E' : trend === 'down' ? '#FF2D2D' : '#9CA3AF';
  return (
    <span className="inline-flex items-center gap-1" style={{ color }}>
      <Icon className="w-3 h-3" />
      {summary && <span className="text-[0.6rem] font-bold tracking-wider">{summary}</span>}
    </span>
  );
}

function ImpactTag({ area }: { area: ImpactArea }) {
  const cfg = IMPACT_LABELS[area];
  return (
    <span
      className="inline-flex items-center px-1.5 py-0.5 text-[0.55rem] font-bold tracking-[0.15em] uppercase"
      style={{ color: cfg.color, backgroundColor: `${cfg.color}15`, border: `1px solid ${cfg.color}30` }}
    >
      {cfg.label}
    </span>
  );
}

function ActionStateBadge({ state }: { state: ActionState }) {
  const cfg = ACTION_STATE_MAP[state];
  return <StatusChip status={cfg.status} size="sm">{cfg.label}</StatusChip>;
}

function RiskLevel({ level, label }: { level: RiskTier; label: string }) {
  const color = level === 'high' ? '#FF2D2D' : level === 'medium' ? '#F59E0B' : '#22C55E';
  return (
    <div className="flex items-center gap-2">
      <span className="text-[0.55rem] font-bold tracking-[0.15em] uppercase text-zinc-500">{label}</span>
      <span className="text-[0.55rem] font-bold tracking-wider uppercase px-1.5 py-0.5" style={{ color, backgroundColor: `${color}15`, border: `1px solid ${color}30` }}>
        {level}
      </span>
    </div>
  );
}

function ScoreGauge({ score, size = 'lg' }: { score: number; size?: 'sm' | 'lg' }) {
  const color = score >= 90 ? '#22C55E' : score >= 75 ? '#38BDF8' : score >= 60 ? '#F59E0B' : '#FF2D2D';
  const dim = size === 'lg' ? 72 : 44;
  const stroke = size === 'lg' ? 5 : 3;
  const r = (dim - stroke) / 2;
  const circ = 2 * Math.PI * r;
  const offset = circ * (1 - score / 100);
  return (
    <div className="relative" style={{ width: dim, height: dim }}>
      <svg width={dim} height={dim} className="transform -rotate-90">
        <circle cx={dim / 2} cy={dim / 2} r={r} fill="none" stroke="rgba(255,255,255,0.06)" strokeWidth={stroke} />
        <circle cx={dim / 2} cy={dim / 2} r={r} fill="none" stroke={color} strokeWidth={stroke} strokeDasharray={circ} strokeDashoffset={offset} strokeLinecap="round" className="transition-all duration-700" />
      </svg>
      <div className="absolute inset-0 flex items-center justify-center">
        <span className={`font-black ${size === 'lg' ? 'text-lg' : 'text-[0.65rem]'}`} style={{ color }}>{score}%</span>
      </div>
    </div>
  );
}

function SectionDivider({ label }: { label: string }) {
  return (
    <div className="flex items-center gap-3 my-6">
      <div className="h-px flex-1" style={{ backgroundColor: 'rgba(255,255,255,0.06)' }} />
      <span className="text-[0.55rem] font-bold tracking-[0.25em] uppercase text-zinc-500">{label}</span>
      <div className="h-px flex-1" style={{ backgroundColor: 'rgba(255,255,255,0.06)' }} />
    </div>
  );
}

function TacticalCorners() {
  return (
    <>
      <div className="absolute top-0 left-0 w-1.5 h-1.5 border-t border-l border-white/20" />
      <div className="absolute top-0 right-0 w-1.5 h-1.5 border-t border-r border-white/20" />
      <div className="absolute bottom-0 left-0 w-1.5 h-1.5 border-b border-l border-white/20" />
      <div className="absolute bottom-0 right-0 w-1.5 h-1.5 border-b border-r border-white/20" />
    </>
  );
}

// ═══════════════════════════════════════════════════════════════════════════════
// PRIORITY ALERT CARD
// ═══════════════════════════════════════════════════════════════════════════════

function PriorityAlertCard({ alert, onNavigate }: { alert: PriorityAlert; onNavigate: () => void }) {
  const isCritical = alert.severity === 'critical';
  const borderColor = isCritical ? 'rgba(255,45,45,0.4)' : 'rgba(245,158,11,0.3)';
  const glowColor = isCritical ? 'rgba(255,45,45,0.08)' : 'rgba(245,158,11,0.05)';
  const accentColor = isCritical ? '#FF2D2D' : '#F59E0B';
  return (
    <div
      className="relative border p-4 group cursor-pointer hover:border-opacity-70 transition-all"
      style={{ borderColor, backgroundColor: glowColor }}
      onClick={onNavigate}
    >
      <TacticalCorners />
      <div className="flex items-start gap-3 mb-3">
        <div className="mt-0.5">
          {isCritical
            ? <AlertTriangle className="w-4 h-4" style={{ color: accentColor }} />
            : <AlertCircle className="w-4 h-4" style={{ color: accentColor }} />}
        </div>
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 mb-1">
            <StatusChip status={isCritical ? 'critical' : 'warning'} size="sm" pulse={isCritical}>
              {alert.severity.toUpperCase()}
            </StatusChip>
            <span className="text-[0.55rem] font-bold tracking-[0.15em] uppercase" style={{ color: accentColor }}>
              {alert.domainLabel}
            </span>
          </div>
          <p className="text-[0.8rem] font-semibold text-white leading-snug mb-1.5">{alert.title}</p>
          <p className="text-[0.65rem] text-zinc-500 leading-relaxed mb-2">{alert.reason}</p>
        </div>
      </div>
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-1.5">
          <ArrowRight className="w-3 h-3" style={{ color: accentColor }} />
          <span className="text-[0.6rem] font-bold tracking-wider" style={{ color: accentColor }}>{alert.nextAction}</span>
        </div>
        <ChevronRight className="w-3.5 h-3.5 text-zinc-600 group-hover:text-zinc-400 transition-colors" />
      </div>
    </div>
  );
}

// ═══════════════════════════════════════════════════════════════════════════════
// DOMAIN SUMMARY PANEL
// ═══════════════════════════════════════════════════════════════════════════════

function DomainSummaryPanel({ domain: _domain, summary, config }: { domain: DomainKey; summary: DomainSummary; config: DomainMeta }) {
  const DomainIcon = config.icon;
  return (
    <div className="relative border border-white/8 bg-[#0a0a0c] p-5 mb-4" style={{ borderLeft: `3px solid ${config.accent}` }}>
      <TacticalCorners />
      <div className="grid grid-cols-1 lg:grid-cols-[auto_1fr_1fr] gap-6">
        {/* Score + Domain Info */}
        <div className="flex items-center gap-5">
          <ScoreGauge score={summary.score} size="lg" />
          <div>
            <div className="flex items-center gap-2 mb-1">
              <DomainIcon className="w-4 h-4" style={{ color: config.accent }} />
              <span className="text-[0.65rem] font-bold tracking-[0.15em] uppercase" style={{ color: config.accent }}>{config.label}</span>
            </div>
            <div className="flex items-center gap-4 mt-2">
              <span className="text-[0.6rem] font-bold text-green-400">{summary.passing} passing</span>
              <span className="text-[0.6rem] font-bold text-yellow-400">{summary.warning} warning</span>
              <span className="text-[0.6rem] font-bold text-red-400">{summary.critical} critical</span>
            </div>
            <div className="mt-2">
              <TrendBadge trend={summary.trend} summary={summary.trend === 'up' ? 'Improving' : summary.trend === 'down' ? 'Declining' : 'Stable'} />
            </div>
          </div>
        </div>

        {/* Risk Assessment */}
        <div className="flex flex-col gap-2">
          <span className="text-[0.55rem] font-bold tracking-[0.2em] uppercase text-zinc-600 mb-1">Risk Assessment</span>
          <RiskLevel level={summary.billingRisk} label="Billing" />
          <RiskLevel level={summary.licensureRisk} label="Licensure" />
          <RiskLevel level={summary.operationalRisk} label="Operations" />
          <div className="mt-1 text-[0.55rem] text-zinc-600">
            Last reviewed: {summary.lastReviewed}
          </div>
        </div>

        {/* Suggested Actions */}
        <div>
          <span className="text-[0.55rem] font-bold tracking-[0.2em] uppercase text-zinc-600 mb-2 block">Suggested Actions</span>
          <div className="space-y-1.5">
            {summary.suggestedActions.map((action, i) => (
              <div key={i} className="flex items-start gap-2">
                <ChevronRight className="w-3 h-3 text-[#FF6A00] mt-0.5 shrink-0" />
                <span className="text-[0.65rem] text-zinc-400 leading-snug">{action}</span>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}

// ═══════════════════════════════════════════════════════════════════════════════
// COMPLIANCE ROW (EXPANDABLE)
// ═══════════════════════════════════════════════════════════════════════════════

function ComplianceRow({ item, isExpanded, onToggle, accent }: { item: ComplianceItem; isExpanded: boolean; onToggle: () => void; accent: string }) {
  const actionCfg = ACTION_STATE_MAP[item.actionState];
  return (
    <div style={{ borderBottom: '1px solid rgba(255,255,255,0.04)' }}>
      {/* Main Row */}
      <div
        className="flex items-start justify-between gap-4 px-4 py-3.5 cursor-pointer hover:bg-white/[0.02] transition-colors group"
        onClick={onToggle}
      >
        <div className="flex items-start gap-3 min-w-0 flex-1">
          {/* Left accent dot */}
          <div className="mt-1.5 shrink-0">
            <div className="w-1.5 h-1.5" style={{ backgroundColor: accent }} />
          </div>
          <div className="min-w-0 flex-1">
            <div className="flex items-center gap-2 mb-0.5">
              <p className="text-[0.8rem] font-semibold text-white leading-snug">{item.name}</p>
              {item.actionState !== 'no-action' && (
                <ActionStateBadge state={item.actionState} />
              )}
            </div>
            <p className="text-[0.65rem] text-zinc-500 leading-relaxed mb-1.5">{item.description}</p>
            <div className="flex flex-wrap items-center gap-1.5">
              {item.impactAreas.slice(0, 3).map(area => (
                <ImpactTag key={area} area={area} />
              ))}
              {item.impactAreas.length > 3 && (
                <span className="text-[0.55rem] text-zinc-600">+{item.impactAreas.length - 3} more</span>
              )}
            </div>
          </div>
        </div>

        <div className="flex shrink-0 items-center gap-4">
          <div className="flex flex-col items-end gap-1.5">
            <StatusChip status={item.status} size="sm">{item.statusLabel}</StatusChip>
            <TrendBadge trend={item.trend} summary={item.trendSummary} />
          </div>
          <div className="flex flex-col items-end gap-1">
            <span className="text-[0.55rem] text-zinc-600">{item.lastChecked}</span>
            {item.evidenceCount > 0 && (
              <span className="text-[0.55rem] text-zinc-600 flex items-center gap-1">
                <FileText className="w-2.5 h-2.5" /> {item.evidenceCount}
              </span>
            )}
          </div>
          <div className="text-zinc-600 group-hover:text-zinc-400 transition-colors">
            {isExpanded ? <ChevronUp className="w-4 h-4" /> : <ChevronDown className="w-4 h-4" />}
          </div>
        </div>
      </div>

      {/* Expanded Detail */}
      {isExpanded && (
        <div className="px-4 pb-4 pt-1 ml-7 border-l-2 animate-in slide-in-from-top-1 duration-200" style={{ borderColor: accent }}>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4 bg-[#07090d] p-4 border border-white/4">
            <TacticalCorners />
            {/* Column 1: Details */}
            <div className="space-y-3">
              <div>
                <span className="text-[0.5rem] font-bold tracking-[0.2em] uppercase text-zinc-600 block mb-1">Policy / Standard Basis</span>
                <span className="text-[0.65rem] text-zinc-400">{item.policyBasis ?? 'Internal standard'}</span>
              </div>
              {item.owner && (
                <div>
                  <span className="text-[0.5rem] font-bold tracking-[0.2em] uppercase text-zinc-600 block mb-1">Owner / Reviewer</span>
                  <span className="text-[0.65rem] text-zinc-400">{item.owner}</span>
                </div>
              )}
              {item.nextDue && (
                <div>
                  <span className="text-[0.5rem] font-bold tracking-[0.2em] uppercase text-zinc-600 block mb-1">Next Due</span>
                  <span className="text-[0.65rem] text-zinc-400">{item.nextDue}</span>
                </div>
              )}
              <div>
                <span className="text-[0.5rem] font-bold tracking-[0.2em] uppercase text-zinc-600 block mb-1">Action State</span>
                <span className="text-[0.65rem] font-semibold" style={{ color: actionCfg.status === 'critical' ? '#FF2D2D' : actionCfg.status === 'warning' ? '#F59E0B' : '#22C55E' }}>
                  {actionCfg.label}
                </span>
              </div>
            </div>

            {/* Column 2: Impact & Evidence */}
            <div className="space-y-3">
              <div>
                <span className="text-[0.5rem] font-bold tracking-[0.2em] uppercase text-zinc-600 block mb-1">Impact Areas</span>
                <div className="flex flex-wrap gap-1">
                  {item.impactAreas.map(area => <ImpactTag key={area} area={area} />)}
                </div>
              </div>
              <div>
                <span className="text-[0.5rem] font-bold tracking-[0.2em] uppercase text-zinc-600 block mb-1">Evidence Documents</span>
                <span className="text-[0.65rem] text-zinc-400">{item.evidenceCount} document{item.evidenceCount !== 1 ? 's' : ''} on file</span>
              </div>
              {item.linkedRecords !== undefined && item.linkedRecords > 0 && (
                <div>
                  <span className="text-[0.5rem] font-bold tracking-[0.2em] uppercase text-zinc-600 block mb-1">Linked Records</span>
                  <span className="text-[0.65rem] text-zinc-400">{item.linkedRecords} records</span>
                </div>
              )}
            </div>

            {/* Column 3: Actions */}
            <div className="space-y-2">
              <span className="text-[0.5rem] font-bold tracking-[0.2em] uppercase text-zinc-600 block mb-1">Quick Actions</span>
              <button className="flex items-center gap-2 text-[0.6rem] font-bold tracking-wider uppercase text-zinc-400 hover:text-white transition-colors w-full py-1.5 px-2 border border-white/6 hover:border-white/15">
                <Eye className="w-3 h-3" /> View Evidence
              </button>
              <button className="flex items-center gap-2 text-[0.6rem] font-bold tracking-wider uppercase text-zinc-400 hover:text-white transition-colors w-full py-1.5 px-2 border border-white/6 hover:border-white/15">
                <Download className="w-3 h-3" /> Download Evidence
              </button>
              <button className="flex items-center gap-2 text-[0.6rem] font-bold tracking-wider uppercase text-zinc-400 hover:text-white transition-colors w-full py-1.5 px-2 border border-white/6 hover:border-white/15">
                <FileCheck className="w-3 h-3" /> Mark Reviewed
              </button>
              <button className="flex items-center gap-2 text-[0.6rem] font-bold tracking-wider uppercase text-zinc-400 hover:text-white transition-colors w-full py-1.5 px-2 border border-white/6 hover:border-white/15">
                <ExternalLink className="w-3 h-3" /> View Linked Records
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

// ═══════════════════════════════════════════════════════════════════════════════
// ACTION QUEUE TABLE
// ═══════════════════════════════════════════════════════════════════════════════

function ActionQueueTable({ items, filter, onFilterChange }: {
  items: ActionQueueItem[];
  filter: string;
  onFilterChange: (_f: 'all' | 'critical' | 'overdue') => void;
}) {
  return (
    <div>
      <div className="flex items-center justify-between mb-3">
        <div className="flex items-center gap-2">
          <Target className="w-4 h-4 text-[#FF6A00]" />
          <span className="text-[0.65rem] font-bold tracking-[0.15em] uppercase text-white">Corrective Action Queue</span>
          <span className="text-[0.55rem] font-bold text-zinc-500 ml-1">{items.length} items</span>
        </div>
        <div className="flex items-center gap-1">
          {(['all', 'critical', 'overdue'] as const).map(f => (
            <button
              key={f}
              onClick={() => onFilterChange(f)}
              className="px-2.5 py-1 text-[0.55rem] font-bold tracking-wider uppercase transition-colors"
              style={{
                color: filter === f ? '#FF6A00' : '#6B7280',
                backgroundColor: filter === f ? 'rgba(255,106,0,0.1)' : 'transparent',
                border: filter === f ? '1px solid rgba(255,106,0,0.3)' : '1px solid transparent',
              }}
            >
              {f}
            </button>
          ))}
        </div>
      </div>
      <div className="border border-white/6 bg-[#0a0a0c] divide-y divide-white/4">
        {items.map(item => {
          const domainCfg = DOMAIN_CONFIG[item.domain];
          const stateColor = item.reviewState === 'in-progress' ? '#38BDF8' : item.reviewState === 'pending-review' ? '#F59E0B' : '#9CA3AF';
          return (
            <div key={item.id} className="flex items-center justify-between px-4 py-3 hover:bg-white/[0.02] transition-colors">
              <div className="flex items-center gap-3 min-w-0 flex-1">
                <div className="w-1 h-8 shrink-0" style={{ backgroundColor: domainCfg.accent }} />
                <div className="min-w-0">
                  <div className="flex items-center gap-2 mb-0.5">
                    <p className="text-[0.75rem] font-semibold text-white truncate">{item.title}</p>
                    {item.isOverdue && (
                      <StatusChip status="critical" size="sm" pulse>OVERDUE</StatusChip>
                    )}
                  </div>
                  <div className="flex items-center gap-3">
                    <span className="text-[0.55rem] font-bold tracking-wider uppercase" style={{ color: domainCfg.accent }}>{item.domainLabel}</span>
                    <span className="text-[0.55rem] text-zinc-500">{item.owner}</span>
                  </div>
                </div>
              </div>
              <div className="flex items-center gap-4 shrink-0">
                <div className="text-right">
                  <span className="text-[0.6rem] text-zinc-400 block">Due: {item.dueDate}</span>
                  <span className="text-[0.55rem] font-bold tracking-wider uppercase" style={{ color: stateColor }}>
                    {item.reviewState.replace('-', ' ')}
                  </span>
                </div>
                <StatusChip status={item.severity} size="sm">
                  {item.severity === 'critical' ? 'CRITICAL' : item.severity === 'warning' ? 'WARNING' : 'INFO'}
                </StatusChip>
              </div>
            </div>
          );
        })}
        {items.length === 0 && (
          <div className="px-4 py-8 text-center">
            <CheckCircle2 className="w-5 h-5 text-green-500 mx-auto mb-2" />
            <span className="text-[0.65rem] text-zinc-500">No items match the selected filter</span>
          </div>
        )}
      </div>
    </div>
  );
}

// ═══════════════════════════════════════════════════════════════════════════════
// COMPACT METRIC CARD
// ═══════════════════════════════════════════════════════════════════════════════

function CompactMetric({ label, value, accent, severity }: { label: string; value: string; accent?: string; severity?: 'ok' | 'warn' | 'crit' }) {
  const borderColor = severity === 'crit' ? 'rgba(255,45,45,0.3)' : severity === 'warn' ? 'rgba(245,158,11,0.2)' : 'rgba(255,255,255,0.06)';
  const valueColor = severity === 'crit' ? '#FF2D2D' : severity === 'warn' ? '#F59E0B' : accent ?? '#E5E7EB';
  return (
    <div className="relative border bg-[#0a0a0c] p-3 group hover:border-white/15 transition-colors" style={{ borderColor }}>
      <TacticalCorners />
      <p className="text-[0.5rem] font-bold tracking-[0.2em] uppercase text-zinc-600 mb-1.5">{label}</p>
      <p className="text-xl font-black leading-none" style={{ color: valueColor }}>{value}</p>
    </div>
  );
}

// ═══════════════════════════════════════════════════════════════════════════════
// API RESPONSE TYPES
// ═══════════════════════════════════════════════════════════════════════════════

interface ApiDomainScore {
  domain: DomainKey;
  score: number;
  passing: number;
  warning: number;
  critical: number;
  trend: TrendDir;
  billing_risk: RiskTier;
  licensure_risk: RiskTier;
  operational_risk: RiskTier;
  last_reviewed: string;
  suggested_actions: string[];
}

interface ApiPriorityAlert {
  id: string;
  severity: 'critical' | 'warning';
  domain: DomainKey;
  domain_label: string;
  title: string;
  reason: string;
  next_action: string;
}

interface ApiActionQueueItem {
  id: string;
  title: string;
  owner: string;
  due_date: string;
  domain: DomainKey;
  domain_label: string;
  action_state: string;
  impact: string;
}

interface ApiComplianceSummary {
  overall_score: number;
  total_items: number;
  passing_items: number;
  warning_items: number;
  critical_items: number;
  domains: ApiDomainScore[];
  priority_alerts: ApiPriorityAlert[];
  action_queue: ApiActionQueueItem[];
  generated_at: string;
}

// ═══════════════════════════════════════════════════════════════════════════════
// MAIN PAGE COMPONENT
// ═══════════════════════════════════════════════════════════════════════════════

export default function ComplianceCommandPage() {
  const [activeDomain, setActiveDomain] = useState<DomainKey>('nemsis');
  const [expandedItem, setExpandedItem] = useState<string | null>(null);
  const [queueFilter, setQueueFilter] = useState<'all' | 'critical' | 'overdue'>('all');
  const [apiSummary, setApiSummary] = useState<ApiComplianceSummary | null>(null);
  const [apiError, setApiError] = useState(false);

  const fetchSummary = useCallback(() => {
    const token = typeof window !== 'undefined' ? localStorage.getItem('token') : null;
    fetch(`${API_BASE}/api/v1/compliance/command/summary?days=30`, {
      headers: {
        ...(token ? { Authorization: `Bearer ${token}` } : {}),
        'Content-Type': 'application/json',
      },
    })
      .then(r => { if (!r.ok) throw new Error(`HTTP ${r.status}`); return r.json(); })
      .then((data: ApiComplianceSummary) => { setApiSummary(data); setApiError(false); })
      .catch(() => { setApiError(true); });
  }, []);

  useEffect(() => { fetchSummary(); }, [fetchSummary]);

  // Merge API domain scores with static summaries — API takes priority when available
  const effectiveSummaries = useMemo<Record<DomainKey, DomainSummary>>(() => {
    if (!apiSummary) return DOMAIN_SUMMARIES;
    const merged = { ...DOMAIN_SUMMARIES };
    for (const ds of apiSummary.domains) {
      merged[ds.domain] = {
        score: ds.score,
        passing: ds.passing,
        warning: ds.warning,
        critical: ds.critical,
        lastReviewed: ds.last_reviewed || DOMAIN_SUMMARIES[ds.domain].lastReviewed,
        trend: ds.trend,
        billingRisk: ds.billing_risk,
        licensureRisk: ds.licensure_risk,
        operationalRisk: ds.operational_risk,
        suggestedActions: ds.suggested_actions.length > 0 ? ds.suggested_actions : DOMAIN_SUMMARIES[ds.domain].suggestedActions,
      };
    }
    return merged;
  }, [apiSummary]);

  // Priority alerts: use API alerts if available, fall back to static
  const effectiveAlerts = useMemo<PriorityAlert[]>(() => {
    if (!apiSummary || apiSummary.priority_alerts.length === 0) return PRIORITY_ALERTS;
    return apiSummary.priority_alerts.map(a => ({
      id: a.id,
      severity: a.severity,
      domain: a.domain,
      domainLabel: a.domain_label,
      title: a.title,
      reason: a.reason,
      nextAction: a.next_action,
    }));
  }, [apiSummary]);

  // Action queue: merge API items with static for richer presentation  
  const effectiveActionQueue = useMemo<ActionQueueItem[]>(() => {
    if (!apiSummary || apiSummary.action_queue.length === 0) return ACTION_QUEUE;
    return apiSummary.action_queue.map(a => ({
      id: a.id,
      title: a.title,
      owner: a.owner,
      dueDate: a.due_date,
      severity: (a.action_state === 'blocking' ? 'critical' : a.action_state === 'review-required' ? 'warning' : 'info') as StatusVariant,
      domain: a.domain,
      domainLabel: a.domain_label,
      isOverdue: new Date(a.due_date) < new Date(),
      reviewState: 'open' as const,
    }));
  }, [apiSummary]);

  const domainItems = COMPLIANCE_DATA[activeDomain];
  const domainSummary = effectiveSummaries[activeDomain];
  const domainConfig = DOMAIN_CONFIG[activeDomain];

  const domainCounts = useMemo(() => {
    const counts: Record<string, { critical: number; warning: number }> = {};
    for (const key of TABS) {
      const items = COMPLIANCE_DATA[key];
      counts[key] = {
        critical: items.filter(i => i.status === 'critical').length,
        warning: items.filter(i => i.status === 'warning').length,
      };
    }
    return counts;
  }, []);

  const overallScore = useMemo(() => {
    if (apiSummary) return apiSummary.overall_score;
    const scores = TABS.map(k => effectiveSummaries[k].score);
    return Math.round(scores.reduce((a, b) => a + b, 0) / scores.length);
  }, [apiSummary, effectiveSummaries]);

  const totalCritical = useMemo(() => {
    if (apiSummary) return apiSummary.critical_items;
    return TABS.reduce((s, k) => s + COMPLIANCE_DATA[k].filter(i => i.status === 'critical').length, 0);
  }, [apiSummary]);

  const totalWarning = useMemo(() => {
    if (apiSummary) return apiSummary.warning_items;
    return TABS.reduce((s, k) => s + COMPLIANCE_DATA[k].filter(i => i.status === 'warning').length, 0);
  }, [apiSummary]);

  const filteredQueue = useMemo(() => {
    const queue = effectiveActionQueue;
    if (queueFilter === 'all') return queue;
    if (queueFilter === 'critical') return queue.filter(a => a.severity === 'critical');
    return queue.filter(a => a.isOverdue);
  }, [queueFilter, effectiveActionQueue]);

  const lastAuditLabel = apiSummary?.generated_at
    ? new Date(apiSummary.generated_at).toLocaleString('en-US', { month: 'short', day: 'numeric', year: 'numeric', hour: '2-digit', minute: '2-digit' })
    : 'Mar 8, 2026 06:00';

  return (
    <AppShell>
      {/* API degradation banner */}
      {apiError && (
        <div className="flex items-center gap-2 px-4 py-2.5 mb-4 border border-[#F59E0B]/30 bg-[#F59E0B]/10 text-[#F59E0B]">
          <AlertCircle className="w-4 h-4 flex-shrink-0" />
          <span className="text-[0.65rem] font-bold tracking-wider uppercase">
            Live compliance data unavailable — showing cached compliance posture
          </span>
        </div>
      )}
      {/* ═══════════════════════════════════════════════════════════════════════
          COMMAND HEADER
      ═══════════════════════════════════════════════════════════════════════ */}
      <div className="mb-8">
        <div className="flex flex-col lg:flex-row lg:items-start lg:justify-between gap-4 mb-6">
          <div>
            <div className="flex items-center gap-3 mb-3">
              <div className="w-2 h-2 bg-[#FF6A00] shadow-[0_0_8px_#FF6A00]" />
              <span className="text-[0.6rem] font-bold tracking-[0.25em] uppercase text-[#FF6A00]">
                Mission-Critical Compliance
              </span>
            </div>
            <h1 className="text-3xl md:text-4xl font-black tracking-tight text-white mb-2">
              Compliance Command
            </h1>
            <p className="text-sm text-zinc-500 max-w-2xl leading-relaxed">
              Real-time regulatory, clinical, billing, and operational compliance visibility across the FusionEMS platform.
            </p>
          </div>
          <div className="flex flex-wrap items-center gap-3">
            <StatusChip
              status={overallScore >= 85 ? 'active' : overallScore >= 70 ? 'warning' : 'critical'}
              size="lg"
              pulse
            >
              System Health: {overallScore}%
            </StatusChip>
            <div className="flex items-center gap-2 px-3 py-2 border border-white/8 bg-white/[0.02]">
              <Clock className="w-3.5 h-3.5 text-zinc-500" />
              <span className="text-[0.6rem] font-bold tracking-wider text-zinc-400 uppercase">Last Full Audit: {lastAuditLabel}</span>
            </div>
            <div className="flex items-center gap-2 px-3 py-2 border border-white/8 bg-white/[0.02]">
              <Clipboard className="w-3.5 h-3.5 text-zinc-500" />
              <span className="text-[0.6rem] font-bold tracking-wider text-zinc-400 uppercase">{effectiveActionQueue.length} Reviews Pending</span>
            </div>
            <button
              onClick={fetchSummary}
              className="flex items-center gap-2 px-4 py-2.5 border border-[#FF6A00]/50 bg-[#FF6A00]/10 hover:bg-[#FF6A00]/20 transition-colors text-[0.6rem] font-bold tracking-wider text-[#FF6A00] uppercase"
            >
              <Download className="w-3.5 h-3.5" /> Export Report
            </button>
          </div>
        </div>

        {/* ═══ EXECUTIVE METRICS ═══ */}
        <div className="grid grid-cols-2 md:grid-cols-4 gap-3 mb-4">
          <MetricPlate label="Overall Compliance" value={`${overallScore}%`} accent="compliance" trend="+0.8 pts this week" trendDirection="up" trendPositive />
          <MetricPlate label="Open Violations" value={String(totalCritical)} accent="critical" trend={`${totalWarning} warnings`} trendDirection="down" />
          <MetricPlate label="Pending Reviews" value={String(effectiveActionQueue.length)} accent="cad" />
          <MetricPlate label="Last Audit Date" value="Mar 8" accent="billing" trend="Internal QA" trendDirection="neutral" />
        </div>
        <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
          <CompactMetric label="DEA Exceptions" value="2" severity="crit" />
          <CompactMetric label="CMS Denial Risk" value="4" severity="crit" />
          <CompactMetric label="Expiring Credentials" value="2" severity="warn" />
          <CompactMetric label="Signature Backlog" value="8" severity="warn" />
        </div>
      </div>

      {/* ═══════════════════════════════════════════════════════════════════════
          PRIORITY ACTIONS RAIL
      ═══════════════════════════════════════════════════════════════════════ */}
      <SectionDivider label="Priority Actions — Requires Immediate Attention" />
      <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-3 mb-8">
        {effectiveAlerts.map(alert => (
          <PriorityAlertCard
            key={alert.id}
            alert={alert}
            onNavigate={() => setActiveDomain(alert.domain)}
          />
        ))}
      </div>

      {/* ═══════════════════════════════════════════════════════════════════════
          DOMAIN TABS
      ═══════════════════════════════════════════════════════════════════════ */}
      <SectionDivider label="Compliance Domains" />
      <div className="flex flex-wrap gap-1.5 mb-6">
        {TABS.map(key => {
          const cfg = DOMAIN_CONFIG[key];
          const counts = domainCounts[key];
          const isActive = activeDomain === key;
          const DIcon = cfg.icon;
          return (
            <button
              key={key}
              onClick={() => { setActiveDomain(key); setExpandedItem(null); }}
              className="group relative flex items-center gap-2 px-4 py-2.5 transition-all"
              style={{
                backgroundColor: isActive ? `${cfg.accent}15` : 'transparent',
                border: isActive ? `1px solid ${cfg.accent}40` : '1px solid rgba(255,255,255,0.06)',
                color: isActive ? cfg.accent : '#6B7280',
              }}
            >
              <DIcon className="w-3.5 h-3.5" />
              <span className="text-[0.6rem] font-bold tracking-[0.12em] uppercase">{cfg.label}</span>
              {counts && counts.critical > 0 && (
                <span className="flex items-center justify-center w-4 h-4 text-[0.5rem] font-bold bg-red-500/20 text-red-400 border border-red-500/30">{counts.critical}</span>
              )}
              {counts && counts.warning > 0 && counts.critical === 0 && (
                <span className="flex items-center justify-center w-4 h-4 text-[0.5rem] font-bold bg-yellow-500/20 text-yellow-400 border border-yellow-500/30">{counts.warning}</span>
              )}
              {isActive && (
                <div className="absolute bottom-0 left-0 right-0 h-0.5" style={{ backgroundColor: cfg.accent }} />
              )}
            </button>
          );
        })}
      </div>

      {/* ═══════════════════════════════════════════════════════════════════════
          DOMAIN SUMMARY
      ═══════════════════════════════════════════════════════════════════════ */}
      <DomainSummaryPanel
        domain={activeDomain}
        summary={domainSummary}
        config={domainConfig}
      />

      {/* ═══════════════════════════════════════════════════════════════════════
          COMPLIANCE ITEMS LIST
      ═══════════════════════════════════════════════════════════════════════ */}
      <PlateCard
        header={
          <div className="flex items-center gap-2">
            <div className="w-1.5 h-1.5" style={{ backgroundColor: domainConfig.accent }} />
            <span>{domainConfig.label} — Detailed Compliance Items</span>
          </div>
        }
        headerRight={
          <span className="text-[0.55rem] font-bold tracking-wider uppercase text-zinc-500">
            {domainItems.length} items
          </span>
        }
        accent={domainConfig.accent}
        padding="none"
        className="mb-8"
      >
        <div className="flex flex-col">
          {domainItems.map(item => (
            <ComplianceRow
              key={item.id}
              item={item}
              accent={domainConfig.accent}
              isExpanded={expandedItem === item.id}
              onToggle={() => setExpandedItem(expandedItem === item.id ? null : item.id)}
            />
          ))}
        </div>
      </PlateCard>

      {/* ═══════════════════════════════════════════════════════════════════════
          CORRECTIVE ACTION QUEUE
      ═══════════════════════════════════════════════════════════════════════ */}
      <SectionDivider label="Corrective Actions & Review Queue" />
      <div className="mb-8">
        <ActionQueueTable
          items={filteredQueue}
          filter={queueFilter}
          onFilterChange={setQueueFilter}
        />
      </div>

      {/* ═══════════════════════════════════════════════════════════════════════
          EVIDENCE & EXPORT CONTROLS
      ═══════════════════════════════════════════════════════════════════════ */}
      <div className="relative border border-white/6 bg-[#0a0a0c] p-5 mb-6">
        <TacticalCorners />
        <div className="flex flex-col md:flex-row items-start md:items-center justify-between gap-4">
          <div>
            <div className="flex items-center gap-2 mb-1">
              <Layers className="w-4 h-4 text-[#FF6A00]" />
              <span className="text-[0.65rem] font-bold tracking-[0.15em] uppercase text-white">Evidence & Documentation</span>
            </div>
            <p className="text-[0.6rem] text-zinc-500">Export compliance reports, generate evidence packets, and download audit summaries.</p>
          </div>
          <div className="flex flex-wrap items-center gap-2">
            <button className="flex items-center gap-2 px-3 py-2 border border-white/10 bg-white/[0.02] hover:bg-white/[0.05] transition-colors text-[0.6rem] font-bold tracking-wider uppercase text-zinc-400 hover:text-white">
              <FileText className="w-3 h-3" /> Generate Packet
            </button>
            <button className="flex items-center gap-2 px-3 py-2 border border-white/10 bg-white/[0.02] hover:bg-white/[0.05] transition-colors text-[0.6rem] font-bold tracking-wider uppercase text-zinc-400 hover:text-white">
              <Download className="w-3 h-3" /> Export Audit Summary
            </button>
            <button className="flex items-center gap-2 px-3 py-2 border border-white/10 bg-white/[0.02] hover:bg-white/[0.05] transition-colors text-[0.6rem] font-bold tracking-wider uppercase text-zinc-400 hover:text-white">
              <Activity className="w-3 h-3" /> Compliance Trend Report
            </button>
            <button
              onClick={fetchSummary}
              className="flex items-center gap-2 px-3 py-2 border border-[#FF6A00]/40 bg-[#FF6A00]/10 hover:bg-[#FF6A00]/20 transition-colors text-[0.6rem] font-bold tracking-wider uppercase text-[#FF6A00]"
            >
              <RefreshCw className="w-3 h-3" /> Refresh All Checks
            </button>
          </div>
        </div>
      </div>

      {/* ═══════════════════════════════════════════════════════════════════════
          FOOTER DISCLOSURE
      ═══════════════════════════════════════════════════════════════════════ */}
      <div className="text-center py-4">
        <p className="text-[0.55rem] text-zinc-700 max-w-3xl mx-auto leading-relaxed">
          FusionEMS provides compliance workflow tooling to support agency-level readiness. All compliance determinations,
          regulatory interpretations, and enforcement responses remain the sole responsibility of the operating agency and
          its legal counsel. This platform does not provide legal, regulatory, or accreditation advice.
        </p>
      </div>
    </AppShell>
  );
}
