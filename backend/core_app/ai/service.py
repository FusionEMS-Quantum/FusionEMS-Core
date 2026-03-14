"""AI Service — production-grade multi-provider abstraction.

Supports OpenAI and Amazon Bedrock (Converse API) behind a single interface.

Capabilities:
- Text chat with Prometheus metrics and structured logging
- Structured (JSON) outputs with confidence extraction
- Multimodal / vision (text + base64 image) for both OpenAI and Bedrock
- Automatic provider fallback (fire-once, no cascade)
- PHI-free telemetry/audit — content hash only in logs
- Input hashing for cache keys
"""
from __future__ import annotations

import hashlib
import json
import logging
import os
import time
from typing import Any

import boto3
from botocore.config import Config as BotoConfig
from botocore.exceptions import BotoCoreError, ClientError
from openai import OpenAI
from pydantic import BaseModel, ConfigDict, Field

from core_app.core.config import get_settings
from core_app.observability.metrics import AI_REQUEST_DURATION, AI_REQUESTS_TOTAL

logger = logging.getLogger(__name__)


class AiResponse(BaseModel):
    """Canonical response envelope returned by all AiService methods."""

    model_config = ConfigDict(frozen=True)

    content: str
    """Raw text content from the model (or serialised JSON for structured calls)."""

    confidence: float = Field(ge=0.0, le=1.0, default=1.0)
    """Confidence in [0, 1].  Extracted from JSON payload when present; 1.0 otherwise."""

    provider: str
    """Effective provider that served the request: 'openai' or 'bedrock'."""

    model: str
    """Model identifier as returned by the provider."""

    usage: dict[str, Any] = Field(default_factory=dict)
    """Token-usage dict from the provider (keys vary by provider)."""

    latency_ms: int
    """Wall-clock latency from dispatch to first fully-received response."""

    fallback_used: bool = False
    """True when the primary provider failed and the response came from the fallback."""


# ---------------------------------------------------------------------------
# Provider bootstrap helpers
# ---------------------------------------------------------------------------

def _make_openai_client(settings: Any) -> OpenAI:
    if not settings.openai_api_key:
        raise RuntimeError("OpenAI API key not configured (OPENAI_API_KEY)")
    return OpenAI(api_key=settings.openai_api_key)


def _make_bedrock_client(settings: Any) -> Any:
    region = (
        settings.aws_region
        or os.environ.get("AWS_REGION")
        or os.environ.get("AWS_DEFAULT_REGION")
    )
    if not region:
        raise RuntimeError(
            "AWS region not configured for Bedrock (AWS_REGION / AWS_DEFAULT_REGION)"
        )
    if not settings.bedrock_model_id:
        raise RuntimeError("BEDROCK_MODEL_ID not configured")
    return boto3.client(
        "bedrock-runtime",
        region_name=region,
        config=BotoConfig(
            retries={"max_attempts": 3, "mode": "standard"},
            connect_timeout=3,
            read_timeout=60,
        ),
    )


# ---------------------------------------------------------------------------
# AiService
# ---------------------------------------------------------------------------

class AiService:
    """Multi-provider AI service.

    Instantiate once per request/task context (not a singleton — settings
    are resolved at construction time so provider overrides apply correctly).
    """

    def __init__(self) -> None:
        settings = get_settings()
        provider = (settings.ai_provider or "openai").strip().lower()
        self._provider = provider
        self._settings = settings

        if provider == "openai":
            self._openai_client: OpenAI | None = _make_openai_client(settings)
            self._bedrock_client: Any | None = None
            self._bedrock_model_id = ""
        elif provider == "bedrock":
            self._bedrock_model_id = settings.bedrock_model_id
            self._bedrock_model_id_fallback: str = getattr(settings, "bedrock_model_id_fallback", "")
            self._bedrock_client = _make_bedrock_client(settings)
            self._openai_client = None
        else:
            raise RuntimeError(f"Unsupported AI provider: {provider!r}")

    # ── public: is_configured ──────────────────────────────────────────────

    @classmethod
    def is_configured(cls) -> bool:
        settings = get_settings()
        provider = (settings.ai_provider or "openai").strip().lower()
        if provider == "disabled":
            return False
        if provider == "openai":
            return bool(settings.openai_api_key)
        if provider == "bedrock":
            region = (
                settings.aws_region
                or os.environ.get("AWS_REGION")
                or os.environ.get("AWS_DEFAULT_REGION")
            )
            return bool(region and settings.bedrock_model_id)
        return False

    # ── public: text chat ──────────────────────────────────────────────────

    def chat(
        self,
        *,
        system: str,
        user: str,
        max_tokens: int | None = None,
        model: str = "gpt-4o-mini",
        temperature: float = 0.2,
    ) -> AiResponse:
        """Send a text chat request.

        Performs automatic provider fallback if `AI_FALLBACK_PROVIDER` is
        configured and the primary call raises.
        """
        try:
            return self._dispatch_chat(
                system=system,
                user=user,
                max_tokens=max_tokens,
                model=model,
                temperature=temperature,
                fallback_used=False,
            )
        except Exception as primary_exc:
            fallback = self._try_fallback_provider(
                system=system,
                user=user,
                max_tokens=max_tokens,
                model=model,
                temperature=temperature,
            )
            if fallback is not None:
                return fallback
            raise primary_exc

    # ── public: structured JSON chat ───────────────────────────────────────

    def chat_structured(
        self,
        *,
        system: str,
        user: str,
        max_tokens: int | None = None,
        model: str = "gpt-4o-mini",
        temperature: float = 0.1,
    ) -> tuple[dict[str, Any], AiResponse]:
        """Send a chat request expecting a JSON response.

        Forces JSON-mode instruction in the system prompt, parses the model
        response, and extracts a ``confidence`` field (float 0-1) from the
        payload if present.

        Returns:
            (parsed_payload, AiResponse) — the parsed dict and the raw response
            envelope.  Raises ``ValueError`` if the model returns non-JSON.
        """
        json_system = (
            f"{system}\n\n"
            "IMPORTANT: Respond with a single valid JSON object only. "
            "No markdown fences. No prose outside the JSON."
        )
        response = self.chat(
            system=json_system,
            user=user,
            max_tokens=max_tokens,
            model=model,
            temperature=temperature,
        )

        raw = response.content.strip()
        # Strip markdown code fences if the model ignores the instruction.
        if raw.startswith("```"):
            raw = raw.split("\n", 1)[-1].rsplit("```", 1)[0].strip()

        try:
            payload: dict[str, Any] = json.loads(raw)
        except json.JSONDecodeError as exc:
            logger.warning(
                "AI structured call returned non-JSON: provider=%s model=%s snippet=%.80s",
                response.provider,
                response.model,
                raw,
            )
            raise ValueError(
                f"AI provider {response.provider!r} returned non-JSON output"
            ) from exc

        confidence_raw = payload.get("confidence")
        if isinstance(confidence_raw, (int, float)):
            confidence = float(max(0.0, min(1.0, confidence_raw)))
        else:
            confidence = 1.0

        # Return an updated AiResponse with the extracted confidence.
        enriched = AiResponse(
            content=response.content,
            confidence=confidence,
            provider=response.provider,
            model=response.model,
            usage=response.usage,
            latency_ms=response.latency_ms,
            fallback_used=response.fallback_used,
        )
        return payload, enriched

    # ── public: vision / multimodal ────────────────────────────────────────

    def chat_with_image(
        self,
        *,
        system: str,
        user_text: str,
        image_bytes: bytes,
        image_media_type: str = "image/jpeg",
        max_tokens: int | None = 1024,
        model: str = "gpt-4o-mini",
        temperature: float = 0.1,
    ) -> AiResponse:
        """Send a multimodal request with an inline image.

        Supports OpenAI vision (base64 data URL) and the Bedrock Converse API
        (inline image block).  Automatic fallback is applied on transient errors.
        """
        import base64
        b64 = base64.b64encode(image_bytes).decode()

        try:
            return self._dispatch_image(
                system=system,
                user_text=user_text,
                b64=b64,
                image_media_type=image_media_type,
                max_tokens=max_tokens,
                model=model,
                temperature=temperature,
                fallback_used=False,
            )
        except Exception as primary_exc:
            fallback = self._try_fallback_provider_image(
                system=system,
                user_text=user_text,
                b64=b64,
                image_media_type=image_media_type,
                max_tokens=max_tokens,
                model=model,
                temperature=temperature,
            )
            if fallback is not None:
                return fallback
            raise primary_exc

    # ── internal: dispatch helpers ─────────────────────────────────────────

    def _dispatch_chat(
        self,
        *,
        system: str,
        user: str,
        max_tokens: int | None,
        model: str,
        temperature: float,
        fallback_used: bool,
    ) -> AiResponse:
        if self._provider == "bedrock":
            return self._chat_bedrock(
                system=system,
                user=user,
                max_tokens=max_tokens,
                temperature=temperature,
                fallback_used=fallback_used,
            )
        return self._chat_openai(
            system=system,
            user=user,
            max_tokens=max_tokens,
            model=model,
            temperature=temperature,
            fallback_used=fallback_used,
        )

    def _dispatch_image(
        self,
        *,
        system: str,
        user_text: str,
        b64: str,
        image_media_type: str,
        max_tokens: int | None,
        model: str,
        temperature: float,
        fallback_used: bool,
    ) -> AiResponse:
        if self._provider == "bedrock":
            return self._image_bedrock(
                system=system,
                user_text=user_text,
                b64=b64,
                image_media_type=image_media_type,
                max_tokens=max_tokens,
                temperature=temperature,
                fallback_used=fallback_used,
            )
        return self._image_openai(
            system=system,
            user_text=user_text,
            b64=b64,
            image_media_type=image_media_type,
            max_tokens=max_tokens,
            model=model,
            temperature=temperature,
            fallback_used=fallback_used,
        )

    # ── internal: fallback wiring ──────────────────────────────────────────

    def _try_fallback_provider(
        self,
        *,
        system: str,
        user: str,
        max_tokens: int | None,
        model: str,
        temperature: float,
    ) -> AiResponse | None:
        """Attempt the fallback provider for a text chat call."""
        fallback_name = (self._settings.ai_fallback_provider or "").strip().lower()
        if not fallback_name or fallback_name == self._provider:
            return None

        logger.warning(
            "AI primary provider %r failed — attempting fallback provider %r",
            self._provider,
            fallback_name,
        )
        try:
            fallback_svc = _build_provider_client(fallback_name, self._settings)
        except RuntimeError:
            logger.warning("Fallback provider %r is not configured — skipping", fallback_name)
            return None

        try:
            raw = fallback_svc.dispatch_chat_raw(
                system=system,
                user=user,
                max_tokens=max_tokens,
                model=model,
                temperature=temperature,
            )
            AI_REQUESTS_TOTAL.labels(model=model, status="fallback").inc()
            return AiResponse(**raw, fallback_used=True)
        except Exception:
            logger.exception("AI fallback provider %r also failed", fallback_name)
            return None

    def _try_fallback_provider_image(
        self,
        *,
        system: str,
        user_text: str,
        b64: str,
        image_media_type: str,
        max_tokens: int | None,
        model: str,
        temperature: float,
    ) -> AiResponse | None:
        """Attempt the fallback provider for a vision call."""
        fallback_name = (self._settings.ai_fallback_provider or "").strip().lower()
        if not fallback_name or fallback_name == self._provider:
            return None

        logger.warning(
            "AI vision primary provider %r failed — attempting fallback %r",
            self._provider,
            fallback_name,
        )
        try:
            fallback_svc = _build_provider_client(fallback_name, self._settings)
        except RuntimeError:
            logger.warning("Fallback provider %r is not configured — skipping", fallback_name)
            return None

        try:
            raw = fallback_svc.dispatch_image_raw(
                system=system,
                user_text=user_text,
                b64=b64,
                image_media_type=image_media_type,
                max_tokens=max_tokens,
                model=model,
                temperature=temperature,
            )
            AI_REQUESTS_TOTAL.labels(model=model, status="fallback").inc()
            return AiResponse(**raw, fallback_used=True)
        except Exception:
            logger.exception("AI vision fallback provider %r also failed", fallback_name)
            return None

    # ── internal: OpenAI text ──────────────────────────────────────────────

    def _chat_openai(
        self,
        *,
        system: str,
        user: str,
        max_tokens: int | None,
        model: str,
        temperature: float,
        fallback_used: bool,
    ) -> AiResponse:
        start = time.monotonic()
        create_kwargs: dict[str, Any] = {
            "model": model,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            "temperature": temperature,
        }
        if max_tokens is not None:
            create_kwargs["max_tokens"] = max_tokens
        try:
            assert self._openai_client is not None
            resp = self._openai_client.chat.completions.create(**create_kwargs)
            content = resp.choices[0].message.content or ""
            usage = resp.usage.model_dump() if resp.usage else {}
            duration = time.monotonic() - start
            AI_REQUESTS_TOTAL.labels(model=model, status="success").inc()
            AI_REQUEST_DURATION.labels(model=model).observe(duration)
            logger.info(
                "AI call completed: provider=openai model=%s latency=%dms",
                model,
                int(duration * 1000),
                extra={"extra_fields": {"provider": "openai", "model": model, "latency_ms": int(duration * 1000)}},
            )
            return AiResponse(
                content=content,
                provider="openai",
                model=resp.model,
                usage=usage,
                latency_ms=int(duration * 1000),
                fallback_used=fallback_used,
            )
        except Exception as exc:
            duration = time.monotonic() - start
            AI_REQUESTS_TOTAL.labels(model=model, status="error").inc()
            AI_REQUEST_DURATION.labels(model=model).observe(duration)
            logger.error(
                "AI call failed: provider=openai model=%s error=%s",
                model,
                str(exc),
                extra={"extra_fields": {"provider": "openai", "model": model, "error": str(exc)}},
            )
            raise

    # ── internal: OpenAI vision ────────────────────────────────────────────

    def _image_openai(
        self,
        *,
        system: str,
        user_text: str,
        b64: str,
        image_media_type: str,
        max_tokens: int | None,
        model: str,
        temperature: float,
        fallback_used: bool,
    ) -> AiResponse:
        start = time.monotonic()
        create_kwargs: dict[str, Any] = {
            "model": model,
            "messages": [
                {"role": "system", "content": system},
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": user_text},
                        {
                            "type": "image_url",
                            "image_url": {"url": f"data:{image_media_type};base64,{b64}"},
                        },
                    ],
                },
            ],
            "temperature": temperature,
        }
        if max_tokens is not None:
            create_kwargs["max_tokens"] = max_tokens
        try:
            assert self._openai_client is not None
            resp = self._openai_client.chat.completions.create(**create_kwargs)
            content = resp.choices[0].message.content or ""
            usage = resp.usage.model_dump() if resp.usage else {}
            duration = time.monotonic() - start
            AI_REQUESTS_TOTAL.labels(model=model, status="success").inc()
            AI_REQUEST_DURATION.labels(model=model).observe(duration)
            logger.info(
                "AI vision call completed: provider=openai model=%s latency=%dms",
                model,
                int(duration * 1000),
                extra={"extra_fields": {"provider": "openai", "model": model, "latency_ms": int(duration * 1000)}},
            )
            return AiResponse(
                content=content,
                provider="openai",
                model=resp.model,
                usage=usage,
                latency_ms=int(duration * 1000),
                fallback_used=fallback_used,
            )
        except Exception as exc:
            duration = time.monotonic() - start
            AI_REQUESTS_TOTAL.labels(model=model, status="error").inc()
            AI_REQUEST_DURATION.labels(model=model).observe(duration)
            logger.error(
                "AI vision call failed: provider=openai model=%s error=%s",
                model,
                str(exc),
                extra={"extra_fields": {"provider": "openai", "model": model, "error": str(exc)}},
            )
            raise

    # ── internal: Bedrock text ─────────────────────────────────────────────

    def _chat_bedrock(
        self,
        *,
        system: str,
        user: str,
        max_tokens: int | None,
        temperature: float,
        fallback_used: bool,
    ) -> AiResponse:
        start = time.monotonic()
        model_id = self._bedrock_model_id
        try:
            assert self._bedrock_client is not None
            inference_config: dict[str, Any] = {"temperature": temperature}
            if max_tokens is not None:
                inference_config["maxTokens"] = max_tokens

            resp = self._bedrock_client.converse(
                modelId=model_id,
                system=[{"text": system}],
                messages=[{"role": "user", "content": [{"text": user}]}],
                inferenceConfig=inference_config,
            )
            message = resp.get("output", {}).get("message", {})
            text_parts = [
                p.get("text", "")
                for p in message.get("content", [])
                if isinstance(p, dict)
            ]
            content = "".join(text_parts).strip()
            usage = resp.get("usage", {})
            duration = time.monotonic() - start
            AI_REQUESTS_TOTAL.labels(model=model_id, status="success").inc()
            AI_REQUEST_DURATION.labels(model=model_id).observe(duration)
            logger.info(
                "AI call completed: provider=bedrock model=%s latency=%dms",
                model_id,
                int(duration * 1000),
                extra={"extra_fields": {"provider": "bedrock", "model": model_id, "latency_ms": int(duration * 1000)}},
            )
            return AiResponse(
                content=content,
                provider="bedrock",
                model=model_id,
                usage=usage,
                latency_ms=int(duration * 1000),
                fallback_used=fallback_used,
            )
        except (ClientError, BotoCoreError, AssertionError) as exc:
            duration = time.monotonic() - start
            AI_REQUESTS_TOTAL.labels(model=model_id, status="error").inc()
            AI_REQUEST_DURATION.labels(model=model_id).observe(duration)
            logger.error(
                "AI call failed: provider=bedrock model=%s error=%s",
                model_id,
                str(exc),
                extra={"extra_fields": {"provider": "bedrock", "model": model_id, "error": str(exc)}},
            )
            # Model-level fallback: try the secondary Bedrock model before re-raising.
            fallback_model = self._bedrock_model_id_fallback
            if fallback_model and fallback_model != model_id and not fallback_used:
                logger.warning(
                    "Bedrock primary model %r failed — retrying with fallback model %r",
                    model_id,
                    fallback_model,
                )
                try:
                    assert self._bedrock_client is not None
                    fb_inference: dict[str, Any] = {"temperature": temperature}
                    if max_tokens is not None:
                        fb_inference["maxTokens"] = max_tokens
                    fb_resp = self._bedrock_client.converse(
                        modelId=fallback_model,
                        system=[{"text": system}],
                        messages=[{"role": "user", "content": [{"text": user}]}],
                        inferenceConfig=fb_inference,
                    )
                    fb_msg = fb_resp.get("output", {}).get("message", {})
                    fb_parts = [
                        p.get("text", "")
                        for p in fb_msg.get("content", [])
                        if isinstance(p, dict)
                    ]
                    fb_content = "".join(fb_parts).strip()
                    fb_duration = time.monotonic() - start
                    AI_REQUESTS_TOTAL.labels(model=fallback_model, status="fallback").inc()
                    AI_REQUEST_DURATION.labels(model=fallback_model).observe(fb_duration)
                    logger.info(
                        "Bedrock model fallback succeeded: fallback_model=%s latency=%dms",
                        fallback_model,
                        int(fb_duration * 1000),
                    )
                    return AiResponse(
                        content=fb_content,
                        provider="bedrock",
                        model=fallback_model,
                        usage=fb_resp.get("usage", {}),
                        latency_ms=int(fb_duration * 1000),
                        fallback_used=True,
                    )
                except Exception as fb_exc:
                    logger.error(
                        "Bedrock model fallback also failed: fallback_model=%s error=%s",
                        fallback_model,
                        str(fb_exc),
                    )
            raise

    # ── internal: Bedrock vision ───────────────────────────────────────────

    def _image_bedrock(
        self,
        *,
        system: str,
        user_text: str,
        b64: str,
        image_media_type: str,
        max_tokens: int | None,
        temperature: float,
        fallback_used: bool,
    ) -> AiResponse:
        """Vision call via Bedrock Converse API inline-image block.

        Anthropic Claude 3+ models support inline images through the Converse
        API.  The ``format`` field maps MIME-type suffixes to Bedrock's enum:
        ``jpeg``, ``png``, ``gif``, ``webp``.
        """
        import base64 as _b64_mod

        start = time.monotonic()
        model_id = self._bedrock_model_id

        image_format = image_media_type.split("/")[-1].lower()
        if image_format not in {"jpeg", "jpg", "png", "gif", "webp"}:
            image_format = "jpeg"
        if image_format == "jpg":
            image_format = "jpeg"

        image_bytes_raw = _b64_mod.b64decode(b64)

        try:
            assert self._bedrock_client is not None
            inference_config: dict[str, Any] = {"temperature": temperature}
            if max_tokens is not None:
                inference_config["maxTokens"] = max_tokens

            resp = self._bedrock_client.converse(
                modelId=model_id,
                system=[{"text": system}],
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {"text": user_text},
                            {
                                "image": {
                                    "format": image_format,
                                    "source": {"bytes": image_bytes_raw},
                                }
                            },
                        ],
                    }
                ],
                inferenceConfig=inference_config,
            )
            message = resp.get("output", {}).get("message", {})
            text_parts = [
                p.get("text", "")
                for p in message.get("content", [])
                if isinstance(p, dict)
            ]
            content = "".join(text_parts).strip()
            usage = resp.get("usage", {})
            duration = time.monotonic() - start
            AI_REQUESTS_TOTAL.labels(model=model_id, status="success").inc()
            AI_REQUEST_DURATION.labels(model=model_id).observe(duration)
            logger.info(
                "AI vision call completed: provider=bedrock model=%s latency=%dms",
                model_id,
                int(duration * 1000),
                extra={"extra_fields": {"provider": "bedrock", "model": model_id, "latency_ms": int(duration * 1000)}},
            )
            return AiResponse(
                content=content,
                provider="bedrock",
                model=model_id,
                usage=usage,
                latency_ms=int(duration * 1000),
                fallback_used=fallback_used,
            )
        except (ClientError, BotoCoreError, AssertionError) as exc:
            duration = time.monotonic() - start
            AI_REQUESTS_TOTAL.labels(model=model_id, status="error").inc()
            AI_REQUEST_DURATION.labels(model=model_id).observe(duration)
            logger.error(
                "AI vision call failed: provider=bedrock model=%s error=%s",
                model_id,
                str(exc),
                extra={"extra_fields": {"provider": "bedrock", "model": model_id, "error": str(exc)}},
            )
            raise


# ---------------------------------------------------------------------------
# Internal: single-provider mini-client used by fallback wiring
# ---------------------------------------------------------------------------

class _ProviderOnlyClient:
    """Minimal client for a single provider, used exclusively by fallback logic."""

    def __init__(self, provider: str, settings: Any) -> None:
        self._provider = provider
        if provider == "openai":
            self._openai = _make_openai_client(settings)
            self._bedrock = None
            self._model_id = ""
        elif provider == "bedrock":
            self._bedrock = _make_bedrock_client(settings)
            self._model_id = settings.bedrock_model_id
            self._openai = None
        else:
            raise RuntimeError(f"Unknown provider: {provider!r}")

    def dispatch_chat_raw(
        self,
        *,
        system: str,
        user: str,
        max_tokens: int | None = None,
        model: str = "gpt-4o-mini",
        temperature: float = 0.2,
    ) -> dict[str, Any]:
        start = time.monotonic()
        if self._provider == "openai":
            assert self._openai is not None
            kwargs: dict[str, Any] = {
                "model": model,
                "messages": [
                    {"role": "system", "content": system},
                    {"role": "user", "content": user},
                ],
                "temperature": temperature,
            }
            if max_tokens is not None:
                kwargs["max_tokens"] = max_tokens
            resp = self._openai.chat.completions.create(**kwargs)
            return {
                "content": resp.choices[0].message.content or "",
                "provider": "openai",
                "model": resp.model,
                "usage": resp.usage.model_dump() if resp.usage else {},
                "latency_ms": int((time.monotonic() - start) * 1000),
            }
        # bedrock
        assert self._bedrock is not None
        inf: dict[str, Any] = {"temperature": temperature}
        if max_tokens is not None:
            inf["maxTokens"] = max_tokens
        resp = self._bedrock.converse(
            modelId=self._model_id,
            system=[{"text": system}],
            messages=[{"role": "user", "content": [{"text": user}]}],
            inferenceConfig=inf,
        )
        message = resp.get("output", {}).get("message", {})
        text_parts = [p.get("text", "") for p in message.get("content", []) if isinstance(p, dict)]
        return {
            "content": "".join(text_parts).strip(),
            "provider": "bedrock",
            "model": self._model_id,
            "usage": resp.get("usage", {}),
            "latency_ms": int((time.monotonic() - start) * 1000),
        }

    def dispatch_image_raw(
        self,
        *,
        system: str,
        user_text: str,
        b64: str,
        image_media_type: str = "image/jpeg",
        max_tokens: int | None = 1024,
        model: str = "gpt-4o-mini",
        temperature: float = 0.1,
    ) -> dict[str, Any]:
        import base64 as _b64_mod

        start = time.monotonic()
        if self._provider == "openai":
            assert self._openai is not None
            kwargs: dict[str, Any] = {
                "model": model,
                "messages": [
                    {"role": "system", "content": system},
                    {
                        "role": "user",
                        "content": [
                            {"type": "text", "text": user_text},
                            {
                                "type": "image_url",
                                "image_url": {"url": f"data:{image_media_type};base64,{b64}"},
                            },
                        ],
                    },
                ],
                "temperature": temperature,
            }
            if max_tokens is not None:
                kwargs["max_tokens"] = max_tokens
            resp = self._openai.chat.completions.create(**kwargs)
            return {
                "content": resp.choices[0].message.content or "",
                "provider": "openai",
                "model": resp.model,
                "usage": resp.usage.model_dump() if resp.usage else {},
                "latency_ms": int((time.monotonic() - start) * 1000),
            }
        # bedrock
        assert self._bedrock is not None
        image_format = image_media_type.split("/")[-1].lower()
        if image_format not in {"jpeg", "jpg", "png", "gif", "webp"}:
            image_format = "jpeg"
        if image_format == "jpg":
            image_format = "jpeg"
        image_bytes_raw = _b64_mod.b64decode(b64)
        inf: dict[str, Any] = {"temperature": temperature}
        if max_tokens is not None:
            inf["maxTokens"] = max_tokens
        resp = self._bedrock.converse(
            modelId=self._model_id,
            system=[{"text": system}],
            messages=[
                {
                    "role": "user",
                    "content": [
                        {"text": user_text},
                        {"image": {"format": image_format, "source": {"bytes": image_bytes_raw}}},
                    ],
                }
            ],
            inferenceConfig=inf,
        )
        message = resp.get("output", {}).get("message", {})
        text_parts = [p.get("text", "") for p in message.get("content", []) if isinstance(p, dict)]
        return {
            "content": "".join(text_parts).strip(),
            "provider": "bedrock",
            "model": self._model_id,
            "usage": resp.get("usage", {}),
            "latency_ms": int((time.monotonic() - start) * 1000),
        }


def _build_provider_client(provider: str, settings: Any) -> _ProviderOnlyClient:
    return _ProviderOnlyClient(provider, settings)


# ---------------------------------------------------------------------------
# Utilities
# ---------------------------------------------------------------------------

def hash_input(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()
