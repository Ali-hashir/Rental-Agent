"""Tests for Deepgram streaming client."""
from __future__ import annotations

import asyncio
import json
from types import SimpleNamespace

import pytest

from app.services import deepgram


class DummyWebSocket:
    def __init__(self) -> None:
        self.sent: list[bytes | str] = []
        self.closed = False
        self._messages: asyncio.Queue[str | bytes] = asyncio.Queue()

    async def send(self, data: bytes | str) -> None:
        self.sent.append(data)

    async def close(self) -> None:
        self.closed = True

    def __aiter__(self) -> "DummyWebSocket":
        return self

    async def __anext__(self) -> str | bytes:
        return await self._messages.get()

    async def queue_message(self, payload: dict) -> None:
        await self._messages.put(json.dumps(payload))


class DummyConnect:
    def __init__(self, ws: DummyWebSocket) -> None:
        self.ws = ws

    async def __aenter__(self) -> DummyWebSocket:
        return self.ws

    async def __aexit__(self, exc_type, exc, tb) -> bool:
        return False


@pytest.mark.asyncio
async def test_connect_stream_requires_api_key(monkeypatch):
    monkeypatch.setattr(deepgram.settings, "deepgram_api_key", "")

    with pytest.raises(RuntimeError):
        async with deepgram.connect_stream():  # type: ignore[misc]
            pass


@pytest.mark.asyncio
async def test_connect_stream_sends_audio_and_yields_transcripts(monkeypatch):
    ws = DummyWebSocket()
    monkeypatch.setattr(deepgram, "websockets", SimpleNamespace(connect=lambda *args, **kwargs: DummyConnect(ws)))
    monkeypatch.setattr(deepgram.settings, "deepgram_api_key", "test-key")

    transcripts: list[dict] = []

    async def handle(payload: dict) -> None:
        transcripts.append(payload)

    async with deepgram.connect_stream(on_transcript=handle) as stream:
        await ws.queue_message({"channel": {"alternatives": [{"transcript": "Hello"}]}})
        await stream.send_audio(b"frame")
        await asyncio.sleep(0)  # allow transcript handler to run
        await stream.flush()

    assert b"frame" in [chunk for chunk in ws.sent if isinstance(chunk, bytes)]
    assert any(item.get("channel") for item in transcripts)
    assert ws.closed


