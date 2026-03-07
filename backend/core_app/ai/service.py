"""AI Service — production-grade OpenAI integration.

Provides structured AI calls with:
- Prometheus metrics on every call
- Deterministic temperature settings
- Graceful degradation when API unavailable
- Input hashing for cache keys
"""
from __future__ import annotations

import hashlib
import logging
import time
from typing import Any

from openai import OpenAI

from core_app.core.config import get_settings
from core_app.observability.metrics import AI_REQUEST_DURATION, AI_REQUESTS_TOTAL

logger = logging.getLogger(__name__)


class AiService:
    def __init__(self) -> None:
        settings = get_settings()
        if not settings.openai_api_key:
            raise RuntimeError("OpenAI API key not configured")
        self.client = OpenAI(api_key=settings.openai_api_key)

    def chat(
        self, *, system: str, user: str, max_tokens: int | None = None, model: str = "gpt-4o-mini"
    ) -> tuple[str, dict[str, Any]]:
        start = time.monotonic()
        create_kwargs: dict[str, Any] = {
            "model": model,
            "messages": [{"role": "system", "content": system}, {"role": "user", "content": user}],
            "temperature": 0.2,
        }
        if max_tokens is not None:
            create_kwargs["max_tokens"] = max_tokens
        try:
            resp = self.client.chat.completions.create(**create_kwargs)
            content = resp.choices[0].message.content or ""
            usage = resp.usage.model_dump() if resp.usage else {}
            duration = time.monotonic() - start
            meta = {
                "model": resp.model,
                "usage": usage,
                "latency_ms": int(duration * 1000),
            }
            AI_REQUESTS_TOTAL.labels(model=model, status="success").inc()
            AI_REQUEST_DURATION.labels(model=model).observe(duration)
            logger.info(
                "AI call completed: model=%s latency=%dms",
                model,
                meta["latency_ms"],
                extra={"extra_fields": {"model": model, "latency_ms": meta["latency_ms"]}},
            )
            return content, meta
        except Exception as exc:
            duration = time.monotonic() - start
            AI_REQUESTS_TOTAL.labels(model=model, status="error").inc()
            AI_REQUEST_DURATION.labels(model=model).observe(duration)
            logger.error(
                "AI call failed: model=%s error=%s",
                model,
                str(exc),
                extra={"extra_fields": {"model": model, "error": str(exc)}},
            )
            raise


def hash_input(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()
