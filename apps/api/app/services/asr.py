"""Speech-to-text helper built on faster-whisper."""
from __future__ import annotations

import asyncio
import os
import tempfile
from functools import lru_cache
from typing import Any

try:  # pragma: no cover - import guard for optional dependency
    from faster_whisper import WhisperModel as _WhisperModel
except ImportError as import_error:  # pragma: no cover - handled at runtime
    _WhisperModel = None
    _IMPORT_ERROR = import_error
else:
    _IMPORT_ERROR = None

WhisperModelType = Any

from ..core.config import settings


@lru_cache
def _load_model() -> WhisperModelType:
    """Load the Whisper model once per process."""

    if _WhisperModel is None:  # pragma: no cover - exercised when dependency missing
        raise RuntimeError(
            "faster-whisper is not installed. Install it or set up a different ASR backend."
        ) from _IMPORT_ERROR

    return _WhisperModel(
        settings.whisper_model,
        device=settings.whisper_device,
        compute_type=settings.whisper_compute_type,
    )


async def transcribe_audio(audio_bytes: bytes) -> str:
    """Return the best-effort transcript for the supplied WAV/PCM bytes."""

    loop = asyncio.get_running_loop()

    def _run_transcription() -> str:
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp_file:
            tmp_file.write(audio_bytes)
            tmp_path = tmp_file.name

        try:
            segments, _ = _load_model().transcribe(tmp_path, beam_size=1)
            pieces = [segment.text.strip() for segment in segments if segment.text]
            return " ".join(pieces).strip()
        finally:
            try:
                os.remove(tmp_path)
            except FileNotFoundError:
                pass

    return await loop.run_in_executor(None, _run_transcription)
