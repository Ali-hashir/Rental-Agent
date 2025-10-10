"""Deepgram streaming ASR client."""
from __future__ import annotations

import asyncio
import json
from contextlib import asynccontextmanager, suppress
from typing import AsyncIterator, Awaitable, Callable

import websockets
from websockets.client import WebSocketClientProtocol

from ..core.config import settings

AudioChunk = bytes
TranscriptHandler = Callable[[dict], Awaitable[None]]


class DeepgramStream:
    """Handle lifespan of a Deepgram streaming session."""

    def __init__(self, ws: WebSocketClientProtocol, on_transcript: TranscriptHandler | None = None) -> None:
        self._ws = ws
        self._on_transcript = on_transcript
        self._output_task: asyncio.Task[None] | None = None

    async def __aenter__(self) -> "DeepgramStream":
        if self._on_transcript:
            self._output_task = asyncio.create_task(self._receive_loop())
        return self

    async def __aexit__(self, exc_type, exc, tb) -> None:
        if self._output_task:
            self._output_task.cancel()
            with suppress(asyncio.CancelledError):
                await self._output_task
        await self._ws.close()

    async def send_audio(self, chunk: AudioChunk) -> None:
        await self._ws.send(chunk)

    async def flush(self) -> None:
        await self._ws.send(json.dumps({"type": "CloseStream"}))

    async def _receive_loop(self) -> None:
        try:
            async for message in self._ws:
                if isinstance(message, bytes):
                    continue
                payload = json.loads(message)
                if self._on_transcript:
                    await self._on_transcript(payload)
        except asyncio.CancelledError:
            raise
        except Exception:
            # TODO: add structured logging once available.
            pass


@asynccontextmanager
async def connect_stream(
    on_transcript: TranscriptHandler | None = None,
    *,
    model: str = "nova-2",
    language: str = "en",
) -> AsyncIterator[DeepgramStream]:
    """Open a Deepgram live transcription connection."""

    if not settings.deepgram_api_key:
        raise RuntimeError("Deepgram API key missing")

    url = (
        "wss://api.deepgram.com/v1/listen"
        f"?model={model}&language={language}&encoding=linear16&sample_rate=16000"
    )
    headers = {"Authorization": f"Token {settings.deepgram_api_key}"}
    async with websockets.connect(url, extra_headers=headers) as ws:
        stream = DeepgramStream(ws, on_transcript=on_transcript)
        async with stream:
            yield stream
