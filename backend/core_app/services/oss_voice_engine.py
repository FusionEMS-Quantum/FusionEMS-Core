from __future__ import annotations

import logging
import os
import subprocess
import uuid
from dataclasses import dataclass
from pathlib import Path

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class VoiceSynthesisConfig:
    primary_engine: str  # xtts | piper
    fallback_engine: str  # piper | xtts
    xtts_model_name: str
    piper_bin_path: str
    piper_model_path: str
    output_dir: str
    base_url: str


def _safe_filename(prefix: str) -> str:
    token = uuid.uuid4().hex[:12]
    return f"{prefix}_{token}.wav"


def _ensure_dir(path: str) -> None:
    Path(path).mkdir(parents=True, exist_ok=True)


def _run(cmd: list[str], stdin: str | None = None) -> None:
    proc = subprocess.run(
        cmd,
        input=stdin.encode("utf-8") if stdin is not None else None,
        capture_output=True,
        check=False,
    )
    if proc.returncode != 0:
        stderr = proc.stderr.decode("utf-8", errors="ignore")[:600]
        raise RuntimeError(f"Command failed ({cmd[0]}): {stderr}")


def _synthesize_with_xtts(text: str, cfg: VoiceSynthesisConfig, out_path: str) -> None:
    # Uses Coqui TTS CLI with XTTS model. Requires package 'TTS'.
    cmd = [
        "tts",
        "--text",
        text,
        "--model_name",
        cfg.xtts_model_name,
        "--out_path",
        out_path,
    ]
    _run(cmd)


def _synthesize_with_piper(text: str, cfg: VoiceSynthesisConfig, out_path: str) -> None:
    cmd = [
        cfg.piper_bin_path,
        "--model",
        cfg.piper_model_path,
        "--output_file",
        out_path,
    ]
    _run(cmd, stdin=text)


def synthesize_to_wav_url(text: str, cfg: VoiceSynthesisConfig, prompt_key: str) -> str:
    if not text.strip():
        raise ValueError("text must not be empty")

    _ensure_dir(cfg.output_dir)
    filename = _safe_filename(prompt_key)
    out_path = os.path.join(cfg.output_dir, filename)

    engines = [cfg.primary_engine.lower(), cfg.fallback_engine.lower()]
    last_err: Exception | None = None

    for engine in engines:
        try:
            if engine == "xtts":
                _synthesize_with_xtts(text, cfg, out_path)
            elif engine == "piper":
                _synthesize_with_piper(text, cfg, out_path)
            else:
                raise RuntimeError(f"Unsupported engine: {engine}")

            base = cfg.base_url.rstrip("/")
            return f"{base}/{filename}"
        except Exception as exc:  # narrow enough for fallback behavior
            last_err = exc
            logger.warning("Voice synthesis via %s failed: %s", engine, exc)

    raise RuntimeError(f"All voice synthesis engines failed: {last_err}")
