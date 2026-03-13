"""Unit tests for frontend base URL resolution.

These redirects are used for public onboarding flows (Stripe success/cancel) and must be
stable across environments.
"""

from __future__ import annotations

from core_app.core.config import Settings


def _production_settings(**overrides: object) -> Settings:
    """Construct production Settings for unit tests.

    Production Settings enforce required secret wiring. These tests care about
    `resolved_frontend_base_url()`, so we provide deterministic placeholder
    values for unrelated required fields.
    """

    base: dict[str, object] = dict(
        environment="production",
        auth_mode="cognito",
        session_cookie_secure=True,
        database_url="postgresql://user:pass@localhost:5432/fusionems",
        redis_url="redis://localhost:6379/0",
        jwt_secret_key="prod_ci_jwt_secret_key_1234567890abcdefghijklmnopqrstuvwxyzABCD",
        stripe_secret_key="sk_live_ci_contract_1234567890",
        stripe_webhook_secret="whsec_live_ci_contract_1234567890",
        aws_region="us-east-1",
        system_tenant_id="00000000-0000-0000-0000-000000000001",
        lob_events_queue_url="https://sqs.us-east-1.amazonaws.com/123456789012/lob-events",
        stripe_events_queue_url="https://sqs.us-east-1.amazonaws.com/123456789012/stripe-events",
        neris_pack_import_queue_url="https://sqs.us-east-1.amazonaws.com/123456789012/neris-pack-import",
        neris_pack_compile_queue_url="https://sqs.us-east-1.amazonaws.com/123456789012/neris-pack-compile",
        neris_export_queue_url="https://sqs.us-east-1.amazonaws.com/123456789012/neris-export",
        nemsis_export_queue_url="https://sqs.us-east-1.amazonaws.com/123456789012/nemsis-export",
        statements_table="statements",
        lob_events_table="lob_events",
        stripe_events_table="stripe_events",
        tenants_table="tenants",
        graph_tenant_id="00000000-0000-0000-0000-000000000010",
        graph_client_id="00000000-0000-0000-0000-000000000020",
        graph_client_secret="msgraph_ci_contract_secret_1234567890",
        graph_founder_email="founder@example.com",
        microsoft_redirect_uri="https://api.example.com/api/v1/auth/microsoft/callback",
        microsoft_post_login_url="https://app.example.com/dashboard",
        microsoft_founder_post_login_url="https://app.example.com/dashboard?next=%2Ffounder",
        microsoft_post_logout_url="https://app.example.com/login",
    )
    base.update(overrides)
    return Settings(**base)


class TestResolvedFrontendBaseUrl:
    def test_explicit_frontend_base_url_wins(self) -> None:
        s = _production_settings(
            frontend_base_url="https://app.example.com/",
            microsoft_post_login_url="https://ignored.example.com/dashboard",
        )
        assert s.resolved_frontend_base_url() == "https://app.example.com"

    def test_derived_from_microsoft_post_login_url(self) -> None:
        s = _production_settings(
            frontend_base_url="",
            microsoft_post_login_url="https://console.example.com/dashboard?x=1",
        )
        assert s.resolved_frontend_base_url() == "https://console.example.com"

    def test_development_prefers_localhost_when_default_prod_domain_present(self) -> None:
        # Safety: if the operator didn't configure dev URLs, do not send customers to prod domains.
        s = Settings(
            environment="development",
            frontend_base_url="",
            microsoft_post_login_url="https://app.fusionemsquantum.com/dashboard",
        )
        assert s.resolved_frontend_base_url() == "http://localhost:3000"

    def test_development_prefers_localhost_when_candidate_missing(self) -> None:
        s = Settings(
            environment="development",
            frontend_base_url="",
            microsoft_post_login_url="",
        )
        assert s.resolved_frontend_base_url() == "http://localhost:3000"

    def test_production_falls_back_to_app_domain(self) -> None:
        s = _production_settings(
            frontend_base_url="",
            microsoft_post_login_url="not-a-url",
            debug=False,
        )
        assert s.resolved_frontend_base_url() == "https://app.fusionemsquantum.com"
