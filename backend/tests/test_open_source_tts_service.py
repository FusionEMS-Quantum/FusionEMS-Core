from __future__ import annotations

import subprocess
from pathlib import Path
from types import SimpleNamespace

import pytest

from core_app.services import open_source_tts_service as tts


@pytest.fixture
def tts_settings(tmp_path: Path) -> SimpleNamespace:
    return SimpleNamespace(
        api_base_url="https://api.example.test",
        oss_tts_prompt_dir=str(tmp_path / "prompts"),
        oss_tts_engine_primary="xtts",
        oss_tts_engine_fallback="piper",
        oss_tts_xtts_bin="tts",
        oss_tts_xtts_model_name="tts_models/multilingual/multi-dataset/xtts_v2",
        oss_tts_xtts_language="en",
        oss_tts_xtts_speaker_wav="",
        oss_tts_piper_bin="piper",
        oss_tts_piper_model_path=str(tmp_path / "voice.onnx"),
        oss_tts_piper_config_path="",
        oss_tts_piper_speaker_id=None,
    )


def test_render_prompt_falls_back_to_piper(monkeypatch: pytest.MonkeyPatch, tts_settings: SimpleNamespace):
    monkeypatch.setattr(tts, "get_settings", lambda: tts_settings)

    def fake_run(cmd, input=None, capture_output=True, check=True, timeout=60):
        exe = cmd[0]
        if exe == "tts":
            raise subprocess.CalledProcessError(returncode=1, cmd=cmd, stderr=b"xtts not available")

        output_idx = cmd.index("--output_file") + 1
        out_path = Path(cmd[output_idx])
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_bytes(b"RIFF....WAVE")
        return subprocess.CompletedProcess(cmd, 0, stdout=b"", stderr=b"")

    monkeypatch.setattr(tts.subprocess, "run", fake_run)

    audio_id = tts.render_prompt_to_wav(prompt_key="menu_text", text_content="Welcome caller")

    wav_path = tts.audio_file_path(audio_id)
    assert wav_path.exists()
    assert tts.public_audio_url(audio_id).endswith(f"/api/v1/founder/billing-voice/audio/{audio_id}.wav")


def test_render_prompts_to_audio_urls(monkeypatch: pytest.MonkeyPatch, tts_settings: SimpleNamespace):
    monkeypatch.setattr(tts, "get_settings", lambda: tts_settings)

    def fake_run(cmd, input=None, capture_output=True, check=True, timeout=60):
        output_idx = cmd.index("--output_file") + 1
        out_path = Path(cmd[output_idx])
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_bytes(b"RIFF....WAVE")
        return subprocess.CompletedProcess(cmd, 0, stdout=b"", stderr=b"")

    monkeypatch.setattr(tts.subprocess, "run", fake_run)

    urls = tts.render_prompts_to_audio_urls(
        {
            "menu_text": "Welcome",
            "statement_text": "Enter statement",
        },
        preferred_engine="piper",
    )

    assert "menu" in urls
    assert "statement" in urls
    assert urls["menu"].startswith("https://api.example.test/")
