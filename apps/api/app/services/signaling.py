"""In-memory WebRTC signaling manager."""
from __future__ import annotations

import asyncio
from dataclasses import dataclass
from typing import Awaitable, Callable, Dict

SendCallable = Callable[[dict], Awaitable[None]]


@dataclass(slots=True)
class SignalingConnection:
    """Connection wrapper for signaling participants."""

    connection_id: str
    send: SendCallable


class SignalingManager:
    """Manage signaling rooms and fan-out messages between participants."""

    def __init__(self) -> None:
        self._rooms: Dict[str, Dict[str, SignalingConnection]] = {}
        self._lock = asyncio.Lock()

    async def join(self, room: str, connection: SignalingConnection) -> list[str]:
        """Register a connection with the room and return existing participant IDs."""

        async with self._lock:
            participants = self._rooms.setdefault(room, {})
            participants[connection.connection_id] = connection
            return [participant_id for participant_id in participants if participant_id != connection.connection_id]

    async def leave(self, room: str, connection_id: str) -> None:
        """Remove a connection from the room, cleaning up empty rooms."""

        async with self._lock:
            participants = self._rooms.get(room)
            if not participants:
                return
            participants.pop(connection_id, None)
            if not participants:
                self._rooms.pop(room, None)

    async def broadcast(self, room: str, sender_id: str, message: dict) -> None:
        """Send a message to all participants in the room except the sender."""

        async with self._lock:
            participants = list(self._rooms.get(room, {}).values())

        if not participants:
            return

        tasks = [connection.send(message) for connection in participants if connection.connection_id != sender_id]
        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)


manager = SignalingManager()
