import pytest

from app.services import tts


@pytest.mark.asyncio
async def test_synthesize_speech_placeholder_on_failure(monkeypatch) -> None:
    async def _fail_edge(*_args, **_kwargs):
        raise RuntimeError("edge down")

    async def _fail_gtts(*_args, **_kwargs):
        raise RuntimeError("gtts down")

    monkeypatch.setattr(tts, "_edge_tts", _fail_edge)
    monkeypatch.setattr(tts, "_gtts", _fail_gtts)
    monkeypatch.setattr(tts.settings, "tts_provider", "edge", raising=False)

    audio, media_type = await tts.synthesize_speech("hello")

    assert media_type == "audio/wav"
    assert audio.startswith(b"RIFF")
    assert len(audio) > 44  # should contain at least a WAV header plus samples
