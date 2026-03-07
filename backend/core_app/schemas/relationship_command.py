"""Relationship Command Schemas — founder dashboard aggregations."""
from __future__ import annotations

from pydantic import BaseModel


class IdentityConfidenceScore(BaseModel):
    total_patients: int
    verified_count: int
    incomplete_count: int
    duplicate_candidate_count: int
    merge_pending_count: int
    confidence_pct: float


class ResponsiblePartyCompletion(BaseModel):
    total_patients: int
    with_responsible_party: int
    unknown_responsibility: int
    disputed_count: int
    completion_pct: float


class FacilityRelationshipHealth(BaseModel):
    total_facilities: int
    active_count: int
    high_friction_count: int
    review_required_count: int
    inactive_count: int
    health_pct: float


class CommunicationPreferenceCompleteness(BaseModel):
    total_patients: int
    with_preferences: int
    completeness_pct: float


class RelationshipAction(BaseModel):
    priority: int
    category: str
    title: str
    description: str
    severity: str
    action_url: str | None = None


class RelationshipCommandSummary(BaseModel):
    identity_confidence: IdentityConfidenceScore
    responsible_party_completion: ResponsiblePartyCompletion
    facility_health: FacilityRelationshipHealth
    communication_completeness: CommunicationPreferenceCompleteness
    duplicate_review_count: int
    facility_contact_gaps: int
    frequent_utilizer_count: int
    top_actions: list[RelationshipAction]
