"""LLM tool endpoints for the agent."""
from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from ..db.session import get_session
from ..schemas import tools as tools_schema
from ..services import tools as tools_service

router = APIRouter()


@router.post("/search_listings", response_model=tools_schema.SearchListingsResponse)
async def search_listings(
    payload: tools_schema.SearchListingsRequest,
    session: AsyncSession = Depends(get_session),
) -> tools_schema.SearchListingsResponse:
    """Return listings matching user filters."""

    results = await tools_service.search_listings(payload, session)
    return results


@router.post("/quote_total", response_model=tools_schema.QuoteTotalResponse)
async def quote_total(
    payload: tools_schema.QuoteTotalRequest,
    session: AsyncSession = Depends(get_session),
) -> tools_schema.QuoteTotalResponse:
    """Return rent totals for the requested unit."""

    return await tools_service.quote_total(payload, session)


@router.post("/list_slots", response_model=tools_schema.ListSlotsResponse)
async def list_slots(
    payload: tools_schema.ListSlotsRequest,
    session: AsyncSession = Depends(get_session),
) -> tools_schema.ListSlotsResponse:
    """Return available appointment slots."""

    return await tools_service.list_slots(payload, session)


@router.post("/book_viewing", response_model=tools_schema.BookViewingResponse)
async def book_viewing(
    payload: tools_schema.BookViewingRequest,
    session: AsyncSession = Depends(get_session),
) -> tools_schema.BookViewingResponse:
    """Book a viewing for the selected unit."""

    return await tools_service.book_viewing(payload, session)


@router.post("/send_followup", response_model=tools_schema.SendFollowUpResponse)
async def send_followup(
    payload: tools_schema.SendFollowUpRequest,
    session: AsyncSession = Depends(get_session),
) -> tools_schema.SendFollowUpResponse:
    """Send a follow-up message."""

    return await tools_service.send_followup(payload, session)
