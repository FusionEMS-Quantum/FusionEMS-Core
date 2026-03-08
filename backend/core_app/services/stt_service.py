from __future__ import annotations

# ruff: noqa: I001

# pylint: disable=import-error

import contextlib
import logging
import os
import tempfile
from dataclasses import dataclass

import requests

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class STTConfig:
    engine: str  # faster_whisper
    model_size: str


def _download_to_temp(url: str) -> str:
    resp = requests.get(url, timeout=30)
    resp.raise_for_status()
    fd, path = tempfile.mkstemp(prefix="voice_stt_", suffix=".wav")
    with os.fdopen(fd, "wb") as f:
        f.write(resp.content)
    return path


def transcribe_audio_url(audio_url: str, cfg: STTConfig) -> str:
    if cfg.engine.lower() != "faster_whisper":
        raise RuntimeError(f"Unsupported STT engine: {cfg.engine}")

    from faster_whisper import WhisperModel

    audio_path = _download_to_temp(audio_url)
    try:
        model = WhisperModel(cfg.model_size)
        segments, _ = model.transcribe(audio_path)
        text = " ".join((s.text or "").strip() for s in segments).strip()
        return text
    finally:
        with contextlib.suppress(Exception):
            os.remove(audio_path)
