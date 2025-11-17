"""Text-to-speech helper supporting Edge TTS and gTTS."""
from __future__ import annotations

import asyncio
import importlib
import logging
from io import BytesIO
from typing import Tuple

_EDGE_TTS_MODULE = importlib.util.find_spec("edge_tts")
edge_tts = importlib.import_module("edge_tts") if _EDGE_TTS_MODULE else None  # type: ignore[assignment]

try:
    _gtts_module = importlib.import_module("gtts")
    gTTS = getattr(_gtts_module, "gTTS")
    _GTTS_IMPORT_ERROR: Exception | None = None
except ModuleNotFoundError as import_error:  # pragma: no cover - handled at runtime
    gTTS = None  # type: ignore[assignment]
    _GTTS_IMPORT_ERROR = import_error

from ..core.config import settings

logger = logging.getLogger(__name__)


async def _edge_tts(phrase: str) -> Tuple[bytes | None, str]:
    if edge_tts is None:  # pragma: no cover - exercised when dependency missing
        raise RuntimeError("edge-tts is not installed.")

    communicator = edge_tts.Communicate(phrase, voice=settings.tts_voice)
    audio_bytes = bytearray()

    async for chunk in communicator.stream():
        if chunk["type"] == "audio":
            audio_bytes.extend(chunk["data"])

    if not audio_bytes:
        logger.warning("Edge TTS returned no audio; falling back to gTTS")
        return None, "audio/mpeg"

    return bytes(audio_bytes), "audio/mpeg"


async def _gtts(phrase: str) -> Tuple[bytes, str]:
    loop = asyncio.get_running_loop()

    def _run_gtts() -> bytes:
        if gTTS is None:  # pragma: no cover - exercised when dependency missing
            raise RuntimeError("gTTS is not installed.") from _GTTS_IMPORT_ERROR
        buffer = BytesIO()
        gTTS(text=phrase, lang="en").write_to_fp(buffer)
        return buffer.getvalue()

    audio = await loop.run_in_executor(None, _run_gtts)
    return audio, "audio/mpeg"


async def synthesize_speech(text: str) -> Tuple[bytes, str]:
    """Return audio bytes (MP3) for the supplied text."""

    phrase = text or "I am here if you need anything."
    provider = settings.tts_provider.strip().lower()

    if provider == "edge":
        try:
            result = await _edge_tts(phrase)
            if result[0] is not None:
                return result
        except Exception as exc:  # noqa: BLE001
            logger.warning("Edge TTS failed (%s); falling back to gTTS", exc)

    # Default to gTTS or fallback from Edge failure.
    return await _gtts(phrase)
