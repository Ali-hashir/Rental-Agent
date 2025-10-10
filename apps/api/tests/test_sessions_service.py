"""Tests for session persistence and metrics aggregation."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from types import SimpleNamespace

import pytest
from fastapi import HTTPException

from app.repositories import calls as calls_repo
from app.schemas import sessions as schemas
from app.services import sessions as sessions_service


class DummySession:
    """Minimal session stub supporting async transaction context."""

    def __init__(self) -> None:
        self.added: list[object] = []

    def add(self, obj: object) -> None:
        self.added.append(obj)

    def begin(self):  # noqa: D401 - mimic SQLAlchemy's async begin
        session = self

        class _Tx:
            async def __aenter__(self_inner):
                return session

            async def __aexit__(self_inner, exc_type, exc, tb):
                return False

        return _Tx()


class CallStub(SimpleNamespace):
    def __init__(self, call_id: str) -> None:
        super().__init__(
            id=call_id,
            started_at=None,
            lead_id=None,
            consent_granted_at=None,
            consent_declined_at=None,
            duration_sec=None,
            outcome=None,
            metrics_json={},
            last_event_at=None,
        )


@pytest.mark.asyncio
async def test_start_session_records_consent(monkeypatch):
    session = DummySession()
    call = CallStub("session-1")

    async def ensure_call_stub(*args, **kwargs):
        started_at = kwargs.get("started_at")
        lead_id = kwargs.get("lead_id")
        if call.started_at is None and started_at is not None:
            call.started_at = started_at
        if call.lead_id is None and lead_id is not None:
            call.lead_id = lead_id
        return call

    monkeypatch.setattr(calls_repo, "ensure_call", ensure_call_stub)

    started_at = datetime(2025, 10, 10, 12, 0, tzinfo=timezone.utc)
    payload = schemas.SessionStartRequest(
        session_id="session-1", started_at=started_at, lead_id="lead-123", consent=True
    )

    response = await sessions_service.start_session(payload, session)

    assert response.call_id == "session-1"
    assert response.consent_status is schemas.ConsentStatus.GRANTED
    assert call.consent_granted_at == started_at
    assert call.last_event_at == started_at
    assert call in session.added


@pytest.mark.asyncio
async def test_record_event_updates_metrics_and_duration(monkeypatch):
    session = DummySession()
    call = CallStub("session-2")
    call.started_at = datetime(2025, 10, 10, 12, 0, tzinfo=timezone.utc)

    async def ensure_call_stub(*args, **kwargs):
        started_at = kwargs.get("started_at")
        if call.started_at is None and started_at is not None:
            call.started_at = started_at
        return call

    monkeypatch.setattr(calls_repo, "ensure_call", ensure_call_stub)

    event_ts = call.started_at + timedelta(seconds=5)
    event_payload = schemas.AgentEventRequest(
        session_id="session-2",
        type=schemas.AgentEventType.TTS_STOP,
        ts=event_ts,
        data={"latency_ms": 420},
    )

    await sessions_service.record_event(event_payload, session)

    assert call.metrics_json["tts_stop_count"] == 1
    assert call.metrics_json["barge_in_count"] == 1
    assert call.metrics_json["avg_latency_ms"] == 420
    assert call.last_event_at == event_ts

    end_ts = call.started_at + timedelta(minutes=2)
    end_payload = schemas.AgentEventRequest(
        session_id="session-2",
        type=schemas.AgentEventType.SESSION_ENDED,
        ts=end_ts,
        data={"outcome": "booked"},
    )

    await sessions_service.record_event(end_payload, session)

    assert call.duration_sec == 120
    assert call.outcome == "booked"
    assert call.last_event_at == end_ts


@pytest.mark.asyncio
async def test_record_event_rejects_negative_duration(monkeypatch):
    session = DummySession()
    call = CallStub("session-3")
    call.started_at = datetime(2025, 10, 10, 12, 0, tzinfo=timezone.utc)

    async def ensure_call_stub(*args, **kwargs):
        return call

    monkeypatch.setattr(calls_repo, "ensure_call", ensure_call_stub)

    end_payload = schemas.AgentEventRequest(
        session_id="session-3",
        type=schemas.AgentEventType.SESSION_ENDED,
        ts=call.started_at - timedelta(seconds=1),
    )

    with pytest.raises(HTTPException) as exc:
        await sessions_service.record_event(end_payload, session)

    assert exc.value.status_code == 400