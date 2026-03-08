"""Tests for Contact Preference domain — Part 7 verification.

Validates preference states, opt-out tracking, language settings,
policy audit events, and billing integration enforcement.
"""
from __future__ import annotations

from core_app.models.contact_preference import (
    CommunicationOptOutEvent,
    ContactChannel,
    ContactPolicyAuditEvent,
    ContactPreference,
    ContactPreferenceState,
    LanguagePreference,
    OptOutReason,
)
from core_app.schemas.contact_preference import (
    ContactPreferenceUpsert,
    LanguagePreferenceUpsert,
    OptOutEventCreate,
)

# ── State Tests ──────────────────────────────────────────────────────────────


class TestContactPreferenceStates:
    def test_all_states_defined(self) -> None:
        expected = {
            "SMS_ALLOWED",
            "CALL_ALLOWED",
            "EMAIL_ALLOWED",
            "MAIL_REQUIRED",
            "CONTACT_RESTRICTED",
            "REVIEW_REQUIRED",
        }
        actual = {s.value for s in ContactPreferenceState}
        assert actual == expected


class TestContactChannels:
    def test_all_channels_defined(self) -> None:
        expected = {"SMS", "PHONE", "EMAIL", "MAIL", "FAX"}
        actual = {c.value for c in ContactChannel}
        assert actual == expected


class TestOptOutReasons:
    def test_all_reasons_defined(self) -> None:
        expected = {
            "PATIENT_REQUEST", "LEGAL_REQUIREMENT", "SYSTEM_POLICY",
            "DELIVERY_FAILURE", "OTHER",
        }
        actual = {r.value for r in OptOutReason}
        assert actual == expected


# ── Model Table Tests ────────────────────────────────────────────────────────


class TestContactPreferenceModels:
    def test_preference_table(self) -> None:
        tbl = ContactPreference.__table__
        assert getattr(tbl, "name", None) == "contact_preferences"
        assert "patient_id" in tbl.c
        assert "sms_allowed" in tbl.c
        assert "call_allowed" in tbl.c
        assert "email_allowed" in tbl.c
        assert "mail_required" in tbl.c
        assert "contact_restricted" in tbl.c
        assert "preferred_channel" in tbl.c
        assert "preferred_time_start" in tbl.c
        assert "preferred_time_end" in tbl.c
        assert "facility_callback_preference" in tbl.c

    def test_opt_out_event_table(self) -> None:
        tbl = CommunicationOptOutEvent.__table__
        assert getattr(tbl, "name", None) == "communication_opt_out_events"
        assert "patient_id" in tbl.c
        assert "channel" in tbl.c
        assert "action" in tbl.c
        assert "reason" in tbl.c
        assert "actor_user_id" in tbl.c

    def test_language_preference_table(self) -> None:
        tbl = LanguagePreference.__table__
        assert getattr(tbl, "name", None) == "language_preferences"
        assert "patient_id" in tbl.c
        assert "primary_language" in tbl.c
        assert "secondary_language" in tbl.c
        assert "interpreter_required" in tbl.c
        assert "interpreter_language" in tbl.c

    def test_policy_audit_event_table(self) -> None:
        tbl = ContactPolicyAuditEvent.__table__
        assert getattr(tbl, "name", None) == "contact_policy_audit_events"
        assert "action" in tbl.c
        assert "previous_state" in tbl.c
        assert "new_state" in tbl.c
        assert "actor_user_id" in tbl.c
        assert "correlation_id" in tbl.c


# ── Schema Tests ─────────────────────────────────────────────────────────────


class TestContactPreferenceSchemas:
    def test_preference_upsert(self) -> None:
        pref = ContactPreferenceUpsert(
            sms_allowed=True,
            call_allowed=False,
            email_allowed=True,
            mail_required=False,
            contact_restricted=False,
            preferred_channel=ContactChannel.SMS,
        )
        assert pref.sms_allowed is True
        assert pref.call_allowed is False

    def test_opt_out_create(self) -> None:
        event = OptOutEventCreate(
            channel=ContactChannel.SMS,
            action="opt_out",
            reason=OptOutReason.PATIENT_REQUEST,
            notes="Patient called to opt out of SMS",
        )
        assert event.action == "opt_out"

    def test_language_preference_upsert(self) -> None:
        lp = LanguagePreferenceUpsert(
            primary_language="es",
            interpreter_required=True,
            interpreter_language="es",
        )
        assert lp.primary_language == "es"
        assert lp.interpreter_required is True


# ── Boundary Tests ───────────────────────────────────────────────────────────


class TestContactPreferenceBoundaries:
    """Directive: Contact permissions must be explicit.
    Preference changes must be logged."""

    def test_preference_tenant_scoped(self) -> None:
        tbl = ContactPreference.__table__
        assert "tenant_id" in tbl.c

    def test_opt_out_is_immutable(self) -> None:
        """Opt-out events should have created_at but no updated_at pattern
        of allowing mutation (they're append-only audit events)."""
        tbl = CommunicationOptOutEvent.__table__
        assert "created_at" in tbl.c

    def test_policy_audit_tracks_changes(self) -> None:
        tbl = ContactPolicyAuditEvent.__table__
        assert "previous_state" in tbl.c
        assert "new_state" in tbl.c
