"""Call repository helpers for session tracking."""
from __future__ import annotations

from datetime import datetime

from sqlalchemy.ext.asyncio import AsyncSession

from ..models.call import Call


async def get_by_id(session: AsyncSession, call_id: str) -> Call | None:
    """Return a call record by identifier."""

    return await session.get(Call, call_id)


async def ensure_call(
    session: AsyncSession,
    *,
    call_id: str,
    started_at: datetime | None = None,
    lead_id: str | None = None,
) -> Call:
    """Fetch a call or create one if it does not yet exist."""

    call = await session.get(Call, call_id)
    if call is None:
        call = Call(id=call_id)
        if started_at is not None:
            call.started_at = started_at
        if lead_id is not None:
            call.lead_id = lead_id
        session.add(call)
        await session.flush()
        return call

    if started_at is not None and call.started_at is None:
        call.started_at = started_at
    if lead_id is not None and call.lead_id is None:
        call.lead_id = lead_id
    return call
