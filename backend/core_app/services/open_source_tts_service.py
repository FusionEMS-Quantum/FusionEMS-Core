from __future__ import annotations

import hashlib
import logging
import re
import subprocess
from pathlib import Path
from typing import Any

from core_app.core.config import get_settings


class OpenSourceTTSError(RuntimeError):
    """Raised when open-source TTS rendering fails."""


logger = logging.getLogger(__name__)


_PROMPT_KEY_TO_AUDIO_KEY: dict[str, str] = {
    "menu_text": "menu",
    "statement_text": "statement",
    "phone_text": "phone",
    "invalid_text": "invalid",
    "sent_sms_text": "sent_sms",
    "goodbye_text": "goodbye",
    "transfer_text": "transfer",
}

_AUDIO_ID_RE = re.compile(r"^[a-zA-Z0-9_-]+$")


def _prompt_dir() -> Path:
    settings = get_settings()
    configured = (settings.oss_tts_prompt_dir or "").strip()
    directory = Path(configured or "/tmp/fusionems_voice_prompts")  # nosec B108 — configurable via settings.oss_tts_prompt_dir; /tmp fallback is intentional for ephemeral container environments
    directory.mkdir(parents=True, exist_ok=True)
    return directory


def _audio_id(prompt_key: str, text_content: str, engine_fingerprint: str) -> str:
    digest = hashlib.sha256(f"{prompt_key}|{text_content}|{engine_fingerprint}".encode()).hexdigest()
    safe_key = re.sub(r"[^a-zA-Z0-9_-]", "_", prompt_key).lower()
    return f"{safe_key}_{digest[:16]}"


def audio_file_path(audio_id: str) -> Path:
    if not _AUDIO_ID_RE.match(audio_id):
        raise OpenSourceTTSError("invalid audio_id")
    return _prompt_dir() / f"{audio_id}.wav"


def public_audio_url(audio_id: str) -> str:
    settings = get_settings()
    base = str(settings.api_base_url).rstrip("/")
    return f"{base}/api/v1/founder/billing-voice/audio/{audio_id}.wav"


def _run_synthesis_command(cmd: list[str], *, payload: str | None = None) -> None:
    try:
        subprocess.run(
            cmd,
            input=(payload.encode("utf-8") if payload is not None else None),
            capture_output=True,
            check=True,
            timeout=60,
        )
    except subprocess.TimeoutExpired as exc:
        raise OpenSourceTTSError("tts synthesis timed out") from exc
    except subprocess.CalledProcessError as exc:
        stderr = exc.stderr.decode("utf-8", errors="ignore") if exc.stderr else ""
        raise OpenSourceTTSError(f"tts synthesis failed: {stderr[:240]}") from exc
    except OSError as exc:
        raise OpenSourceTTSError(f"tts executable error: {exc}") from exc


def _engine_order(preferred_engine: str | None = None) -> list[str]:
    settings = get_settings()
    order: list[str] = []
    for engine in [
        (preferred_engine or "").strip().lower(),
        str(settings.oss_tts_engine_primary or "xtts").strip().lower(),
        str(settings.oss_tts_engine_fallback or "piper").strip().lower(),
    ]:
        if engine and engine not in order:
            order.append(engine)
    # deterministic final fallback order
    for engine in ("xtts", "piper"):
        if engine not in order:
            order.append(engine)
    return order


def _xtts_fingerprint() -> str:
    settings = get_settings()
    model_name = str(settings.oss_tts_xtts_model_name or "").strip()
    language = str(settings.oss_tts_xtts_language or "en").strip() or "en"
    speaker_wav = str(settings.oss_tts_xtts_speaker_wav or "").strip()
    return f"xtts:{model_name}:{language}:{Path(speaker_wav).name if speaker_wav else 'default'}"


def _piper_fingerprint() -> str:
    settings = get_settings()
    model_path = (settings.oss_tts_piper_model_path or "").strip()
    config_path = (settings.oss_tts_piper_config_path or "").strip()
    speaker_id = settings.oss_tts_piper_speaker_id
    return f"piper:{model_path}:{config_path}:{speaker_id if speaker_id is not None else 'default'}"


def _synthesize_with_xtts(*, text_content: str, out_path: Path) -> str:
    settings = get_settings()
    xtts_bin = str(settings.oss_tts_xtts_bin or "tts").strip()
    model_name = str(settings.oss_tts_xtts_model_name or "").strip()
    language = str(settings.oss_tts_xtts_language or "en").strip() or "en"
    speaker_wav = str(settings.oss_tts_xtts_speaker_wav or "").strip()

    if not model_name:
        raise OpenSourceTTSError("OSS_TTS_XTTS_MODEL_NAME not configured")

    cmd: list[str] = [
        xtts_bin,
        "--text",
        text_content,
        "--model_name",
        model_name,
        "--language_idx",
        language,
        "--out_path",
        str(out_path),
    ]
    if speaker_wav:
        cmd.extend(["--speaker_wav", speaker_wav])

    _run_synthesis_command(cmd)
    return f"xtts:{model_name}:{language}:{Path(speaker_wav).name if speaker_wav else 'default'}"


def _synthesize_with_piper(*, text_content: str, out_path: Path) -> str:
    settings = get_settings()
    model_path = (settings.oss_tts_piper_model_path or "").strip()
    if not model_path:
        raise OpenSourceTTSError("OSS_TTS_PIPER_MODEL_PATH not configured")

    piper_bin = (settings.oss_tts_piper_bin or "piper").strip()
    config_path = (settings.oss_tts_piper_config_path or "").strip()
    speaker_id = settings.oss_tts_piper_speaker_id

    cmd: list[str] = [
        piper_bin,
        "--model",
        model_path,
        "--output_file",
        str(out_path),
    ]
    if config_path:
        cmd.extend(["--config", config_path])
    if speaker_id is not None:
        cmd.extend(["--speaker", str(int(speaker_id))])

    _run_synthesis_command(cmd, payload=text_content)
    return f"piper:{model_path}:{config_path}:{speaker_id if speaker_id is not None else 'default'}"


def render_prompt_to_wav(
    *,
    prompt_key: str,
    text_content: str,
    preferred_engine: str | None = None,
) -> str:
    content = (text_content or "").strip()
    if not content:
        raise OpenSourceTTSError("empty text_content")

    last_err: OpenSourceTTSError | None = None
    for engine in _engine_order(preferred_engine):
        try:
            if engine == "xtts":
                fingerprint = _xtts_fingerprint()
                aid = _audio_id(prompt_key, content, fingerprint)
                out_path = audio_file_path(aid)
                if out_path.exists():
                    return aid
                _synthesize_with_xtts(text_content=content, out_path=out_path)
            elif engine == "piper":
                fingerprint = _piper_fingerprint()
                aid = _audio_id(prompt_key, content, fingerprint)
                out_path = audio_file_path(aid)
                if out_path.exists():
                    return aid
                _synthesize_with_piper(text_content=content, out_path=out_path)
            else:
                raise OpenSourceTTSError(f"Unsupported TTS engine '{engine}'")

            if not out_path.exists():
                raise OpenSourceTTSError(f"{engine} completed but output audio file was not created")
            return aid
        except OpenSourceTTSError as exc:
            last_err = exc
            logger.warning("open_source_tts_engine_failed engine=%s prompt_key=%s error=%s", engine, prompt_key, exc)
            continue

    raise OpenSourceTTSError(f"all TTS engines failed for prompt '{prompt_key}': {last_err}")


def render_prompts_to_audio_urls(
    prompts: dict[str, Any],
    *,
    preferred_engine: str | None = None,
) -> dict[str, str]:
    urls: dict[str, str] = {}
    for prompt_key, audio_key in _PROMPT_KEY_TO_AUDIO_KEY.items():
        text_value = str((prompts or {}).get(prompt_key) or "").strip()
        if not text_value:
            continue
        aid = render_prompt_to_wav(
            prompt_key=prompt_key,
            text_content=text_value,
            preferred_engine=preferred_engine,
        )
        urls[audio_key] = public_audio_url(aid)
    return urls
