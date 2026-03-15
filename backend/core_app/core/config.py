import re
import uuid
from functools import lru_cache

from pydantic import AliasChoices, Field, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

_PLACEHOLDER_CONFIG_PATTERN = re.compile(
    r"(?:placeholder(?:_rotate)?_[a-z0-9_]+|replace_with_[a-z0-9_]+|change[-_ ]?me|todo_secret)",
    re.IGNORECASE,
)
_ENTRA_TENANT_DOMAIN_PATTERN = re.compile(
    r"^(?=.{1,255}$)(?:[A-Za-z0-9](?:[A-Za-z0-9-]{0,61}[A-Za-z0-9])?\.)+[A-Za-z]{2,63}$"
)


def is_placeholder_config_value(value: str) -> bool:
    normalized = str(value or "").strip()
    if not normalized:
        return False
    return bool(_PLACEHOLDER_CONFIG_PATTERN.search(normalized))


def is_valid_entra_tenant_identifier(value: str) -> bool:
    normalized = str(value or "").strip()
    if not normalized or is_placeholder_config_value(normalized):
        return False
    try:
        uuid.UUID(normalized)
        return True
    except ValueError:
        return bool(_ENTRA_TENANT_DOMAIN_PATTERN.fullmatch(normalized))


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        env_ignore_empty=True,
        extra="ignore",
    )

    app_name: str = "FusionEMS Core"
    environment: str = Field(default="development")
    debug: bool = Field(default=False)

    @field_validator("debug", mode="before")
    @classmethod
    def _coerce_debug(cls, v: object) -> bool:
        if isinstance(v, str):
            return v.strip().lower() in ("1", "true", "yes")
        return bool(v)

    @field_validator("oss_tts_piper_speaker_id", mode="before")
    @classmethod
    def _coerce_optional_int(cls, v: object) -> object:
        if isinstance(v, str) and not v.strip():
            return None
        return v

    database_url: str = Field(default="")
    api_base_url: str = Field(default="https://api.fusionemsquantum.com")

    frontend_base_url: str = Field(
        default="",
        description=(
            "Optional frontend base URL used for public redirects (Stripe success/cancel, etc.), "
            "e.g. https://app.fusionemsquantum.com. When empty, derived from MICROSOFT_POST_LOGIN_URL."
        ),
    )

    system_tenant_id: str = Field(
        default="",
        description=(
            "Deterministic UUID for system-level events (webhook receipts, etc.) "
            "that have no user tenant. Must be set in all environments."
        ),
    )

    jwt_secret_key: str = Field(default="")
    jwt_algorithm: str = Field(default="HS256")
    jwt_access_token_expire_minutes: int = Field(default=60)

    redis_url: str = Field(default="")
    s3_bucket_docs: str = Field(default="")
    s3_bucket_exports: str = Field(default="")

    # Integrations (injected from Secrets Manager via ECS task definition env vars)
    ai_provider: str = Field(
        default="openai",
        description="AI provider selector: openai|bedrock|disabled",
    )
    openai_api_key: str = Field(default="")
    bedrock_model_id: str = Field(
        default="anthropic.claude-3-7-sonnet-20250219-v1:0",
        description=(
            "AWS Bedrock primary model ID. "
            "Required when AI_PROVIDER=bedrock."
        ),
    )
    bedrock_model_id_fallback: str = Field(
        default="anthropic.claude-3-5-sonnet-20241022-v2:0",
        description=(
            "AWS Bedrock fallback model ID used when the primary model fails or is unavailable."
        ),
    )
    ai_fallback_provider: str = Field(
        default="",
        description=(
            "Secondary AI provider to try if the primary fails: openai|bedrock. "
            "Leave empty to disable fallback. Fallback is fire-once (no cascade)."
        ),
    )
    stripe_secret_key: str = Field(default="")
    stripe_webhook_secret: str = Field(default="")
    telnyx_api_key: str = Field(default="")
    telnyx_from_number: str = Field(default="")
    central_billing_phone_e164: str = Field(
        default="",
        description="Single centralized FusionEMS billing phone number in E.164 format",
    )
    founder_billing_escalation_phone_e164: str = Field(
        default="",
        description="Founder/RCM escalation destination for high-risk billing calls",
    )
    telnyx_central_billing_number_id: str = Field(
        default="",
        description="Telnyx purchased phone number id for the centralized billing line",
    )
    cnam_display_name: str = Field(
        default="FusionEMS Quantum",
        description="CNAM caller ID name shown to patients on outbound billing calls",
    )
    cnam_status: str = Field(
        default="",
        description="CNAM registration status from Telnyx (submitted/active/pending)",
    )
    telnyx_messaging_profile_id: str = Field(default="")
    officeally_sftp_host: str = Field(default="")
    officeally_sftp_port: int = Field(default=22)
    officeally_sftp_username: str = Field(default="")
    officeally_sftp_password: str = Field(default="")
    officeally_sftp_remote_dir: str = Field(default="/")
    lob_api_key: str = Field(default="")
    lob_webhook_secret: str = Field(default="")
    ses_from_email: str = Field(default="noreply@fusionemsquantum.com")

    # Microsoft Graph (application permissions - client credentials flow)
    graph_tenant_id: str = Field(default="", description="Azure AD tenant ID")
    graph_client_id: str = Field(default="", description="Entra app client ID")
    graph_client_secret: str = Field(
        default="", description="Entra app client secret (from Secrets Manager)"
    )
    graph_founder_email: str = Field(
        default="", description="Founder mailbox UPN - used for all Graph calls"
    )

    # Microsoft Entra user login (authorization code flow)
    microsoft_redirect_uri: str = Field(
        default="https://api.fusionemsquantum.com/api/v1/auth/microsoft/callback",
        description="Canonical redirect URI registered in Entra app registration",
    )
    microsoft_post_login_url: str = Field(
        default="https://www.fusionemsquantum.com/dashboard",
        description="Frontend URL to redirect to after successful Microsoft login",
    )
    microsoft_founder_post_login_url: str = Field(
        default="https://www.fusionemsquantum.com/dashboard?next=%2Ffounder",
        description="Frontend URL to redirect founder-intent Microsoft logins after token issuance",
    )
    microsoft_post_logout_url: str = Field(
        default="https://www.fusionemsquantum.com/login",
        description="Frontend URL Entra redirects to after logout (matches manifest logoutUrl)",
    )
    microsoft_founder_required_group_id: str = Field(
        default="",
        description=(
            "Optional Entra group object ID required for founder-intent login. "
            "If set, founder intent requires this group claim in the ID token."
        ),
    )
    microsoft_founder_allowlist_emails: str = Field(
        default="",
        description=(
            "Optional comma-separated founder email allowlist. "
            "Used as a second founder-intent policy control in addition to local role checks."
        ),
    )
    microsoft_oidc_cache_ttl_seconds: int = Field(
        default=3600,
        description="TTL for Entra OIDC discovery/JWKS metadata cache",
    )

    session_cookie_name: str = Field(
        default="fusionems_session",
        description="Primary auth session cookie name used by frontend and backend",
    )
    session_cookie_domain: str = Field(
        default="",
        description=(
            "Optional cookie domain (e.g. .fusionemsquantum.com). "
            "When empty, host-only cookies are used."
        ),
    )
    session_cookie_secure: bool = Field(
        default=False,
        description="Whether auth cookies require HTTPS transport",
    )
    session_cookie_samesite: str = Field(
        default="lax",
        description="Auth cookie SameSite policy: strict|lax|none",
    )
    session_cookie_max_age_seconds: int = Field(
        default=3600,
        description="Auth cookie max age in seconds",
    )

    ses_configuration_set: str = Field(default="")
    aws_region: str = Field(
        default="",
        validation_alias=AliasChoices("AWS_REGION", "AWS_DEFAULT_REGION"),
        description="AWS region (accepts AWS_REGION or AWS_DEFAULT_REGION)",
    )

    # AWS resource identifiers (injected from CFN outputs via ECS task env)
    ecs_cluster_name: str = Field(default="", description="ECS cluster name for CloudWatch metrics")
    ecs_backend_service: str = Field(default="", description="Backend ECS service name")
    rds_instance_id: str = Field(default="", description="RDS DB instance identifier")
    redis_cluster_id: str = Field(default="", description="ElastiCache replication group ID")
    secrets_jwt_arn: str = Field(default="", description="Secrets Manager ARN/name for JWT secret")
    secrets_stripe_arn: str = Field(
        default="", description="Secrets Manager ARN/name for Stripe webhook secret"
    )

    # Telnyx webhook verification + IVR
    telnyx_public_key: str = Field(
        default="", description="Base64-encoded Ed25519 public key from Telnyx portal"
    )
    telnyx_webhook_tolerance_seconds: int = Field(default=300)
    ivr_audio_base_url: str = Field(
        default="", description="S3 or CDN base URL for pre-generated IVR WAV prompts"
    )
    # Open-source-first voice stack (XTTS primary, Piper fallback, faster-whisper STT)
    oss_tts_prompt_dir: str = Field(
        default="/tmp/fusionems_voice_prompts",
        description="Local directory for generated billing prompt WAV files",
    )
    oss_tts_engine_primary: str = Field(default="xtts", description="xtts|piper")
    oss_tts_engine_fallback: str = Field(default="piper", description="piper|xtts")
    oss_tts_xtts_bin: str = Field(default="tts", description="Path to Coqui XTTS CLI binary")
    oss_tts_xtts_model_name: str = Field(
        default="tts_models/multilingual/multi-dataset/xtts_v2",
        description="Coqui XTTS model name",
    )
    oss_tts_xtts_language: str = Field(default="en", description="XTTS synthesis language")
    oss_tts_xtts_speaker_wav: str = Field(
        default="",
        description="Optional path to reference WAV for XTTS voice cloning",
    )
    oss_tts_piper_bin: str = Field(default="piper", description="Path to Piper binary")
    oss_tts_piper_model_path: str = Field(default="", description="Path to Piper model file")
    oss_tts_piper_config_path: str = Field(default="", description="Path to Piper model config")
    oss_tts_piper_speaker_id: int | None = Field(default=None, description="Optional Piper speaker id")

    oss_stt_engine: str = Field(default="faster_whisper", description="STT engine name")
    oss_stt_model_size: str = Field(default="small", description="faster-whisper model size")

    billing_telephony_engine: str = Field(
        default="telnyx",
        description="Primary billing telephony control path: telnyx|asterisk|freeswitch",
    )
    billing_telephony_control_url: str = Field(
        default="",
        description="Optional control-plane URL for Asterisk/FreeSWITCH transfer bridge",
    )
    billing_telephony_control_token: str = Field(
        default="",
        description="Bearer token for telephony control bridge",
    )

    s3_bucket_audio: str = Field(default="")
    fax_classify_queue_url: str = Field(default="")
    fax_outbound_queue_url: str = Field(
        default="",
        description="SQS queue URL for outbound fax send jobs (Lambda worker trigger)",
    )
    telnyx_fax_connection_id: str = Field(
        default="",
        description="Telnyx fax connection_id used for outbound fax sending",
    )

    # Cognito (AWS-native identity)
    auth_mode: str = Field(default="local", description="local|cognito")
    cognito_region: str = Field(default="")
    cognito_user_pool_id: str = Field(default="")
    cognito_app_client_id: str = Field(default="")
    cognito_issuer: str = Field(default="")

    # OPA (optional policy engine)
    opa_url: str = Field(default="", description="OPA HTTP endpoint, e.g. http://opa:8181")
    opa_policy_path: str = Field(default="v1/data/fusionems/allow")

    # ── Founder accounting: open source bank linking ──────────────────────────
    # SimpleFIN (open protocol — primary aggregator, free tier)
    # Setup: user visits https://bridge.simplefin.org, generates a setup token,
    # posts it to /quantum-founder/accounting/bank/simplefin/connect to exchange
    # it for a durable access URL stored here (encrypted at rest in AWS Secrets).
    simplefin_access_url: str = Field(
        default="",
        description=(
            "Durable SimpleFIN access URL obtained after exchanging the one-time "
            "setup token from https://bridge.simplefin.org — 500+ US banks incl. Novo"
        ),
    )

    # American Express Open Banking API (free developer registration required)
    # Register at: https://developer.americanexpress.com
    amex_client_id: str = Field(default="", description="AmEx developer API client ID")
    amex_client_secret: str = Field(default="", description="AmEx developer API client secret")

    # Plaid — optional commercial fallback (free dev tier: 100 items)
    # Only activate if SimpleFIN/OFX does not cover a required institution
    plaid_client_id: str = Field(default="", description="Plaid API client ID")
    plaid_secret: str = Field(default="", description="Plaid API secret")
    plaid_env: str = Field(
        default="sandbox",
        description="Plaid environment: sandbox|development|production",
    )

    # ── Founder accounting: e-file integrations ───────────────────────────────
    # IRS Modernized e-File (MeF) — federal tax electronic filing
    # Registration: https://www.irs.gov/e-file-providers/become-an-authorized-e-file-provider
    irs_mef_api_key: str = Field(
        default="",
        description="IRS MeF EFIN/API credential for electronic filing",
    )
    irs_mef_base_url: str = Field(
        default="https://la.www4.irs.gov/mef/",
        description="IRS MeF submission endpoint (la = live acceptance)",
    )
    irs_efin: str = Field(
        default="",
        description="Electronic Filing Identification Number (EFIN) issued by IRS",
    )

    # Wisconsin Department of Revenue — MyTax Account API
    # Registration: https://www.revenue.wi.gov/Pages/FAQS/ise-prep.aspx
    wi_dor_api_key: str = Field(default="", description="Wisconsin DOR e-file API key")
    wi_dor_base_url: str = Field(
        default="https://tap.revenue.wi.gov/api/",
        description="Wisconsin DOR taxpayer access portal API base URL",
    )

    # SQS queues (Lambda workers)
    lob_events_queue_url: str = Field(default="")
    stripe_events_queue_url: str = Field(default="")
    onboarding_events_queue_url: str = Field(
        default="",
        description="SQS FIFO queue URL for checkout.session.completed → tenant provisioning",
    )
    neris_pack_import_queue_url: str = Field(default="")
    neris_pack_compile_queue_url: str = Field(default="")
    neris_export_queue_url: str = Field(default="")
    nemsis_export_queue_url: str = Field(default="")

    # State API endpoints (NERIS + NEMSIS)
    neris_api_base_url: str = Field(
        default="https://api.neris.usfa.fema.gov/v1",
        description="NERIS state API base URL (testing or production)",
    )
    neris_api_key: str = Field(default="", description="NERIS API key/token")
    nemsis_api_base_url: str = Field(
        default="https://validator.nemsis.org/nemsisWs.asmx",
        description="NEMSIS state submission endpoint",
    )
    nemsis_api_key: str = Field(default="", description="NEMSIS API key")
    nemsis_org_id: str = Field(default="", description="NEMSIS organization ID")

    # DynamoDB tables (Lambda workers) - no default; must be explicitly set per environment
    statements_table: str = Field(default="")
    lob_events_table: str = Field(default="")
    stripe_events_table: str = Field(default="")
    tenants_table: str = Field(default="")

    # GitHub integration (Founder Copilot)
    github_token: str = Field(
        default="", description="GitHub PAT or Actions token for workflow dispatch"
    )
    github_owner: str = Field(default="", description="GitHub org or username")
    github_repo: str = Field(default="FusionEMS-Core", description="GitHub repository name")

    # NEMSIS CTA (Collect & Send) SOAP integration
    nemsis_cta_endpoint: str = Field(
        default="https://cta.nemsis.org:443/ComplianceTestingWs/endpoints/",
        description="NEMSIS TAC CTA SOAP endpoint",
    )
    nemsis_cta_username: str = Field(default="", description="Default NEMSIS CTA SOAP username")
    nemsis_cta_password: str = Field(default="", description="Default NEMSIS CTA SOAP password")
    nemsis_cta_organization: str = Field(
        default="",
        description="Default NEMSIS CTA SOAP organization value",
    )
    nemsis_cta_timeout_seconds: float = Field(
        default=30.0,
        description="HTTP timeout for NEMSIS CTA SOAP requests",
    )
    nemsis_national_endpoint: str = Field(
        default="https://nemsis.org/nemsisWs.wsdl",
        description="NEMSIS national EMS database SOAP endpoint for production submissions",
    )
    nemsis_national_timeout_seconds: float = Field(
        default=60.0,
        description="HTTP timeout for NEMSIS national database SOAP requests",
    )
    nemsis_pm_endpoint: str = Field(
        default="https://perfmeasures.nemsis.org//",
        description="NEMSIS performance measures SOAP endpoint",
    )
    nemsis_local_schematron_dir: str = Field(
        default="",
        description="Optional local directory containing the NEMSIS Schematron development kit",
    )
    nemsis_saxon_jar_path: str = Field(
        default="",
        description="Optional Saxon HE jar path for compiling XSLT2 Schematron rules",
    )

    # Observability
    otel_enabled: bool = Field(default=True)
    otel_service_name: str = Field(default="fusionems-core-backend")
    otel_exporter_otlp_endpoint: str = Field(default="")
    metrics_enabled: bool = Field(default=True)

    def resolved_frontend_base_url(self) -> str:
        """Resolve the public frontend base URL for redirects.

        Priority:
        1) FRONTEND_BASE_URL if explicitly set.
        2) Derive from MICROSOFT_POST_LOGIN_URL (required in staging/prod).
        3) Local dev default when debug is enabled.
        4) Fallback to app.fusionemsquantum.com.
        """

        explicit = str(self.frontend_base_url or "").strip()
        if explicit:
            return explicit.rstrip("/")

        candidate = str(self.microsoft_post_login_url or "").strip()
        if candidate:
            try:
                from urllib.parse import urlsplit

                parsed = urlsplit(candidate)
                if parsed.scheme and parsed.netloc:
                    derived = f"{parsed.scheme}://{parsed.netloc}".rstrip("/")
                    # Local/dev safety: if the operator hasn't configured redirects and
                    # the candidate is the production default, prefer localhost.
                    env = str(self.environment or "").lower()
                    if env not in ("production", "prod", "staging") and parsed.netloc == "app.fusionemsquantum.com":
                        return "http://localhost:3000"
                    return derived
            except Exception:
                # If parsing fails, fall through to safe defaults.
                pass

        env = str(self.environment or "").lower()
        if env not in ("production", "prod", "staging"):
            return "http://localhost:3000"

        if self.debug:
            return "http://localhost:3000"

        return "https://app.fusionemsquantum.com"

    def integration_state_table(self) -> dict[str, dict[str, object]]:
        """Return operator-visible integration state with missing wiring details.

        This table is safe to expose in health/status responses because it only
        reports presence/absence of configuration, never secret values.
        """

        def _entry(*, required: bool, env_names: tuple[str, ...], values: tuple[str, ...]) -> dict[str, object]:
            missing: list[str] = []
            placeholder_fields: list[str] = []
            for env_name, value in zip(env_names, values, strict=False):
                normalized = str(value or "").strip()
                if not normalized:
                    missing.append(env_name)
                    continue
                if is_placeholder_config_value(normalized):
                    placeholder_fields.append(env_name)

            configured = len(missing) == 0 and len(placeholder_fields) == 0
            status = "active"
            if placeholder_fields:
                status = "placeholder_configured"
            elif missing:
                status = "credentials_missing"

            return {
                "required": required,
                "configured": configured,
                "status": status,
                "missing": missing,
                "placeholder_fields": placeholder_fields,
                "ready": configured,
            }

        env = str(self.environment).lower()
        cognito_required = env in ("production", "prod", "staging")

        return {
            "database": _entry(
                required=True,
                env_names=("DATABASE_URL",),
                values=(self.database_url,),
            ),
            "redis": _entry(
                required=True,
                env_names=("REDIS_URL",),
                values=(self.redis_url,),
            ),
            "auth_cognito": _entry(
                required=cognito_required,
                env_names=("AUTH_MODE", "COGNITO_USER_POOL_ID", "COGNITO_CLIENT_ID"),
                values=(
                    "cognito" if str(self.auth_mode).lower() == "cognito" else "",
                    self.cognito_user_pool_id,
                    self.cognito_app_client_id,
                ),
            ),
            "microsoft_graph": _entry(
                required=True,
                env_names=(
                    "GRAPH_TENANT_ID",
                    "GRAPH_CLIENT_ID",
                    "GRAPH_CLIENT_SECRET",
                    "GRAPH_FOUNDER_EMAIL",
                ),
                values=(
                    self.graph_tenant_id,
                    self.graph_client_id,
                    self.graph_client_secret,
                    self.graph_founder_email,
                ),
            ),
            "stripe": _entry(
                required=True,
                env_names=("STRIPE_SECRET_KEY", "STRIPE_WEBHOOK_SECRET"),
                values=(self.stripe_secret_key, self.stripe_webhook_secret),
            ),
            "officeally": _entry(
                required=False,
                env_names=("OFFICEALLY_SFTP_HOST", "OFFICEALLY_SFTP_USERNAME", "OFFICEALLY_SFTP_PASSWORD"),
                values=(
                    self.officeally_sftp_host,
                    self.officeally_sftp_username,
                    self.officeally_sftp_password,
                ),
            ),
            "lob": _entry(
                required=False,
                env_names=("LOB_API_KEY", "LOB_WEBHOOK_SECRET"),
                values=(self.lob_api_key, self.lob_webhook_secret),
            ),
            "telnyx": _entry(
                required=False,
                env_names=(
                    "TELNYX_API_KEY",
                    "TELNYX_FROM_NUMBER",
                    "TELNYX_PUBLIC_KEY",
                    "CENTRAL_BILLING_PHONE_E164",
                ),
                values=(
                    self.telnyx_api_key,
                    self.telnyx_from_number,
                    self.telnyx_public_key,
                    self.central_billing_phone_e164,
                ),
            ),
            "nemsis_submission": _entry(
                required=False,
                env_names=("NEMSIS_API_KEY", "NEMSIS_ORG_ID", "NEMSIS_EXPORT_QUEUE_URL"),
                values=(self.nemsis_api_key, self.nemsis_org_id, self.nemsis_export_queue_url),
            ),
            "neris_submission": _entry(
                required=False,
                env_names=("NERIS_API_KEY", "NERIS_EXPORT_QUEUE_URL"),
                values=(self.neris_api_key, self.neris_export_queue_url),
            ),
        }

    def _is_credential_placeholder(self, value: str) -> bool:
        """Check if a credential value is a placeholder that must never reach production.

        This catches various placeholder patterns used during development that will
        cause authentication failures if deployed to production. This includes secret
        rotation patterns like 'placeholder_rotate_*' which are intermediate values
        during credential rotation that should never be deployed.
        """
        if not value:
            return False
        lower = str(value).lower()
        # Catch explicit placeholders and secret rotation patterns with incomplete values
        patterns = (
            "placeholder",
            "placeholder_rotate",
            "change_me",
            "changeme",
            "your_",
            "your-",
            "replace_with",
            "<your",
            "todo",
            "todo_",
            "xxx",
            "xxxx",
            "insert_",
            "put_your",
            "sample_",
            "test_",
        )
        return any(pattern in lower for pattern in patterns)

    @model_validator(mode="after")
    def _validate_production_secrets(self) -> "Settings":
        env = str(self.environment).lower()
        if env in ("production", "prod", "staging"):
            _REQUIRED: list[tuple[str, str]] = [
                ("database_url", "DATABASE_URL"),
                ("redis_url", "REDIS_URL"),
                ("jwt_secret_key", "JWT_SECRET_KEY"),
                ("stripe_secret_key", "STRIPE_SECRET_KEY"),
                ("stripe_webhook_secret", "STRIPE_WEBHOOK_SECRET"),
                ("aws_region", "AWS_REGION"),
                ("system_tenant_id", "SYSTEM_TENANT_ID"),
                ("lob_events_queue_url", "LOB_EVENTS_QUEUE_URL"),
                ("stripe_events_queue_url", "STRIPE_EVENTS_QUEUE_URL"),
                ("neris_pack_import_queue_url", "NERIS_PACK_IMPORT_QUEUE_URL"),
                ("neris_pack_compile_queue_url", "NERIS_PACK_COMPILE_QUEUE_URL"),
                ("neris_export_queue_url", "NERIS_EXPORT_QUEUE_URL"),
                ("nemsis_export_queue_url", "NEMSIS_EXPORT_QUEUE_URL"),
                ("statements_table", "STATEMENTS_TABLE"),
                ("lob_events_table", "LOB_EVENTS_TABLE"),
                ("stripe_events_table", "STRIPE_EVENTS_TABLE"),
                ("tenants_table", "TENANTS_TABLE"),
                ("graph_tenant_id", "GRAPH_TENANT_ID"),
                ("graph_client_id", "GRAPH_CLIENT_ID"),
                ("graph_client_secret", "GRAPH_CLIENT_SECRET"),
                ("graph_founder_email", "GRAPH_FOUNDER_EMAIL"),
                ("microsoft_redirect_uri", "MICROSOFT_REDIRECT_URI"),
                ("microsoft_post_login_url", "MICROSOFT_POST_LOGIN_URL"),
                (
                    "microsoft_founder_post_login_url",
                    "MICROSOFT_FOUNDER_POST_LOGIN_URL",
                ),
                ("microsoft_post_logout_url", "MICROSOFT_POST_LOGOUT_URL"),
            ]
            missing = [env_name for attr, env_name in _REQUIRED if not getattr(self, attr, "")]
            if missing:
                raise ValueError(
                    f"The following required environment variables are not set "
                    f"for environment '{env}': {', '.join(missing)}. "
                    "All secrets must be injected from AWS Secrets Manager via the ECS task definition."
                )

            # Check for placeholder credentials that would cause authentication failures in production
            # This is critical for Microsoft Graph (which produces AADSTS900023 errors), Stripe, and other integrations
            _CREDENTIAL_FIELDS: list[tuple[str, str]] = [
                ("graph_tenant_id", "GRAPH_TENANT_ID"),
                ("graph_client_id", "GRAPH_CLIENT_ID"),
                ("graph_client_secret", "GRAPH_CLIENT_SECRET"),
                ("stripe_secret_key", "STRIPE_SECRET_KEY"),
                ("stripe_webhook_secret", "STRIPE_WEBHOOK_SECRET"),
                ("jwt_secret_key", "JWT_SECRET_KEY"),
                ("telnyx_api_key", "TELNYX_API_KEY"),
                ("lob_api_key", "LOB_API_KEY"),
            ]
            for attr, env_name in _CREDENTIAL_FIELDS:
                value = getattr(self, attr, "")
                if value and self._is_credential_placeholder(value):
                    raise ValueError(
                        f"SECURITY VIOLATION — {env_name} contains a placeholder/incomplete credential "
                        f"in {env} environment. This will cause authentication failures (e.g., AADSTS900023 from Microsoft). "
                        f"You must update this value in AWS Secrets Manager with the actual credential. "
                        f"Pattern detected: {str(value)[:60]}"
                    )

            if self.jwt_secret_key in ("change-me", "changeme", "secret"):
                raise ValueError(
                    "JWT_SECRET_KEY is set to a known insecure default value. "
                    "Generate a cryptographically random key and inject it from Secrets Manager."
                )
            if not self.session_cookie_secure:
                raise ValueError(
                    "SESSION_COOKIE_SECURE must be true for staging and production environments."
                )
            if str(self.auth_mode).lower() == "local":
                raise ValueError(
                    f"AUTH_MODE is 'local' in environment '{env}'. "
                    "Set AUTH_MODE=fusion_jwt for staging and production deployments."
                )
        return self

    @field_validator("graph_founder_email")
    @classmethod
    def _validate_graph_founder_email(cls, v: str) -> str:
        if v and "@" not in v:
            raise ValueError(f"GRAPH_FOUNDER_EMAIL must be a valid UPN (email address), got: {v!r}")
        return v

    @field_validator("system_tenant_id")
    @classmethod
    def _validate_system_tenant_id(cls, v: str) -> str:
        if not v:
            return v
        import uuid as _uuid

        try:
            _uuid.UUID(v)
        except ValueError as exc:
            raise ValueError(f"SYSTEM_TENANT_ID must be a valid UUID, got: {v!r}") from exc
        return v

    @field_validator("session_cookie_samesite")
    @classmethod
    def _validate_session_cookie_samesite(cls, v: str) -> str:
        normalized = v.strip().lower()
        if normalized not in ("strict", "lax", "none"):
            raise ValueError(
                f"SESSION_COOKIE_SAMESITE must be one of strict|lax|none, got: {v!r}"
            )
        return normalized


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
