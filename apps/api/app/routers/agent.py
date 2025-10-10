"""Agent session endpoints for consent tracking and metrics ingestion."""
from __future__ import annotations

from fastapi import APIRouter, Depends, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from ..db.session import get_session
from ..schemas import sessions as schemas
from ..services import sessions as sessions_service

router = APIRouter()


@router.post("/session/start", response_model=schemas.SessionStartResponse)
async def start_session(
    payload: schemas.SessionStartRequest,
    session: AsyncSession = Depends(get_session),
) -> schemas.SessionStartResponse:
    """Register a new agent session and consent decision."""

    return await sessions_service.start_session(payload, session)


@router.post("/events", status_code=status.HTTP_204_NO_CONTENT)
async def ingest_event(
    payload: schemas.AgentEventRequest,
    session: AsyncSession = Depends(get_session),
) -> Response:
    """Capture an agent event for metrics and session tracking."""

    await sessions_service.record_event(payload, session)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
