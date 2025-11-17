"""In-memory conversation session storage for the voice agent."""
from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Dict, Optional

from .agent import SessionState


@dataclass
class _SessionEntry:
    state: SessionState
    last_seen: float


class SessionStore:
    """Very small in-memory session registry with TTL eviction."""

    def __init__(self, ttl_seconds: int = 900) -> None:
        self._ttl = ttl_seconds
        self._sessions: Dict[str, _SessionEntry] = {}

    def get(self, session_id: str) -> Optional[SessionState]:
        self._evict_expired()
        entry = self._sessions.get(session_id)
        if not entry:
            return None
        entry.last_seen = time.time()
        return entry.state

    def save(self, state: SessionState) -> None:
        self._evict_expired()
        self._sessions[state.session_id] = _SessionEntry(state=state, last_seen=time.time())

    def clear(self, session_id: str) -> None:
        self._sessions.pop(session_id, None)

    def _evict_expired(self) -> None:
        now = time.time()
        expired = [key for key, entry in self._sessions.items() if now - entry.last_seen > self._ttl]
        for key in expired:
            self._sessions.pop(key, None)


session_store = SessionStore()
