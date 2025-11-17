from unittest.mock import AsyncMock, patch

import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app
from app.services.llm import LLMUnavailableError


@pytest.mark.asyncio
async def test_utterance_happy_path() -> None:
    transport = ASGITransport(app=app)

    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        with (
            patch("app.main.transcribe_audio", AsyncMock(return_value="hello there")),
            patch("app.main.generate_reply", AsyncMock(return_value="Hi! We have a unit ready.")),
            patch("app.main.get_reply_source", return_value="gemini"),
            patch(
                "app.main.synthesize_speech",
                AsyncMock(return_value=(b"fake-bytes", "audio/mpeg")),
            ),
        ):
            response = await client.post(
                "/api/utterance",
                files={"audio": ("audio.wav", b"123", "audio/wav")},
            )

    assert response.status_code == 200
    assert response.headers["X-Transcript"] == "hello there"
    assert response.headers["X-Model-Reply"] == "Hi! We have a unit ready."
    assert response.headers["X-LLM-Source"] == "gemini"
    assert response.headers["X-Agent-Stage"] == "gathering"
    assert "X-Agent-Completed" not in response.headers
    assert "X-Session-Id" in response.headers
    assert response.content == b"fake-bytes"


@pytest.mark.asyncio
async def test_utterance_error_returns_apology_audio() -> None:
    apology_audio = b"sorry"

    transport = ASGITransport(app=app)

    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        with (
            patch("app.main.transcribe_audio", AsyncMock(side_effect=RuntimeError("boom"))),
            patch(
                "app.main.synthesize_speech",
                AsyncMock(return_value=(apology_audio, "audio/mpeg")),
            ) as synth_mock,
        ):
            response = await client.post(
                "/api/utterance",
                files={"audio": ("audio.wav", b"456", "audio/wav")},
            )

    synth_mock.assert_called()
    assert response.status_code == 500
    assert response.headers["X-Error"] == "true"
    assert response.headers["X-Model-Reply"] == "Sorry, I could not process that."
    assert response.headers["X-LLM-Source"] == "error"
    assert response.headers["X-Error-Reason"] == "unknown"
    assert "X-Session-Id" in response.headers
    assert response.content == apology_audio


@pytest.mark.asyncio
async def test_utterance_llm_unavailable_returns_503() -> None:
    apology_audio = b"llm-down"

    transport = ASGITransport(app=app)

    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        with (
            patch("app.main.transcribe_audio", AsyncMock(return_value="hello")),
            patch("app.main.generate_reply", AsyncMock(side_effect=LLMUnavailableError("fail"))),
            patch("app.main.synthesize_speech", AsyncMock(return_value=(apology_audio, "audio/mpeg"))) as synth_mock,
        ):
            response = await client.post(
                "/api/utterance",
                files={"audio": ("audio.wav", b"456", "audio/wav")},
            )

    synth_mock.assert_called()
    assert response.status_code == 503
    assert response.headers["X-Error"] == "true"
    assert response.headers["X-Model-Reply"] == "Our language service is temporarily unavailable. Please try again shortly."
    assert response.headers["X-LLM-Source"] == "unavailable"
    assert response.headers["X-Error-Reason"] == "llm_unavailable"
    assert response.headers["X-Transcript"] == "hello"
    assert "X-Session-Id" in response.headers
    assert response.content == apology_audio
