"""Session management and metrics aggregation for agent calls."""
from __future__ import annotations

from datetime import datetime, timezone

from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from ..models.call import Call
from ..repositories import calls as calls_repo
from ..schemas import sessions as schemas

METRIC_VAD_START = "vad_start_count"
METRIC_VAD_END = "vad_end_count"
METRIC_TTS_STOP = "tts_stop_count"
METRIC_BARGE_INS = "barge_in_count"
METRIC_LATENCY_SUM = "latency_sum_ms"
METRIC_LATENCY_COUNT = "latency_count"
METRIC_AVG_LATENCY = "avg_latency_ms"


async def start_session(
    payload: schemas.SessionStartRequest,
    session: AsyncSession,
) -> schemas.SessionStartResponse:
    """Create or update a call session with consent tracking."""

    started_at = _ensure_tz(payload.started_at or datetime.now(timezone.utc))

    async with session.begin():
        call = await calls_repo.ensure_call(
            session,
            call_id=payload.session_id,
            started_at=started_at,
            lead_id=payload.lead_id,
        )
        _apply_consent(call, payload.consent, started_at)
        call.last_event_at = started_at
        session.add(call)

    return schemas.SessionStartResponse(
        call_id=payload.session_id,
        consent_status=_map_consent_status(call),
    )


async def record_event(
    payload: schemas.AgentEventRequest,
    session: AsyncSession,
) -> None:
    """Persist an event and update metrics for the associated call."""

    event_ts = _ensure_tz(payload.ts)

    async with session.begin():
        call = await calls_repo.ensure_call(session, call_id=payload.session_id, started_at=event_ts)
        metrics = dict(call.metrics_json or {})

        if payload.type is schemas.AgentEventType.SESSION_ENDED:
            call.duration_sec = _calculate_duration(call, event_ts)
            outcome = payload.data.get("outcome") if payload.data else None
            if outcome:
                call.outcome = outcome
        elif payload.type is schemas.AgentEventType.CONSENT_GRANTED:
            _apply_consent(call, True, event_ts)
        elif payload.type is schemas.AgentEventType.CONSENT_DECLINED:
            _apply_consent(call, False, event_ts)
        elif payload.type is schemas.AgentEventType.VAD_START:
            metrics[METRIC_VAD_START] = metrics.get(METRIC_VAD_START, 0) + 1
        elif payload.type is schemas.AgentEventType.VAD_END:
            metrics[METRIC_VAD_END] = metrics.get(METRIC_VAD_END, 0) + 1
        elif payload.type is schemas.AgentEventType.TTS_STOP:
            metrics[METRIC_TTS_STOP] = metrics.get(METRIC_TTS_STOP, 0) + 1
            metrics[METRIC_BARGE_INS] = metrics.get(METRIC_BARGE_INS, 0) + 1
        elif payload.type is schemas.AgentEventType.SESSION_STARTED:
            # Update started_at if an explicit timestamp is provided.
            call.started_at = event_ts
            call.lead_id = payload.data.get("lead_id") if payload.data else call.lead_id
            consent_value = payload.data.get("consent") if payload.data else None
            if consent_value is not None:
                parsed_consent = _parse_consent(consent_value)
                if parsed_consent is not None:
                    _apply_consent(call, parsed_consent, event_ts)

        latency_ms = None
        if payload.data:
            latency_ms = payload.data.get("latency_ms")
        if latency_ms is not None:
            latency_value = int(latency_ms)
            metrics[METRIC_LATENCY_SUM] = metrics.get(METRIC_LATENCY_SUM, 0) + latency_value
            metrics[METRIC_LATENCY_COUNT] = metrics.get(METRIC_LATENCY_COUNT, 0) + 1
            metrics[METRIC_AVG_LATENCY] = int(
                metrics[METRIC_LATENCY_SUM] / max(1, metrics[METRIC_LATENCY_COUNT])
            )

        call.metrics_json = metrics
        call.last_event_at = event_ts
        session.add(call)


def _ensure_tz(value: datetime) -> datetime:
    """Ensure the provided datetime is timezone-aware in UTC."""

    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def _apply_consent(call: Call, consent: bool | None, ts: datetime) -> None:
    """Update consent timestamps on the call."""

    if consent is True:
        call.consent_granted_at = ts
        call.consent_declined_at = None
    elif consent is False:
        call.consent_declined_at = ts


def _map_consent_status(call: Call) -> schemas.ConsentStatus:
    """Return the consent status for API responses."""

    if call.consent_granted_at:
        return schemas.ConsentStatus.GRANTED
    if call.consent_declined_at:
        return schemas.ConsentStatus.DECLINED
    return schemas.ConsentStatus.UNKNOWN


def _calculate_duration(call: Call, event_ts: datetime) -> int | None:
    """Compute call duration given an end timestamp."""

    if not call.started_at:
        return None
    delta = event_ts - call.started_at
    if delta.total_seconds() < 0:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="End before start")
    return int(delta.total_seconds())


def _parse_consent(value: object) -> bool | None:
    """Parse a consent value that may be provided as bool or string."""

    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        lowered = value.strip().lower()
        if lowered in {"yes", "true", "granted", "accept", "accepted"}:
            return True
        if lowered in {"no", "false", "declined", "reject", "rejected"}:
            return False
    return None
