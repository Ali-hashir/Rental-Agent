"""Availability repository helpers."""
from __future__ import annotations

from datetime import date

from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession

from ..models.availability import Availability, AvailabilityStatus


async def list_available_windows(
    session: AsyncSession,
    *,
    unit_id: str,
    start_date: date,
    end_date: date,
) -> list[Availability]:
    """Return availability rows for a unit between the provided dates inclusive."""

    stmt = (
        select(Availability)
        .where(
            Availability.unit_id == unit_id,
            Availability.status == AvailabilityStatus.AVAILABLE,
            Availability.date_from >= start_date,
            Availability.date_from <= end_date,
        )
        .order_by(Availability.date_from.asc())
    )
    result = await session.execute(stmt)
    return list(result.scalars().all())


async def get_single_window(session: AsyncSession, *, unit_id: str, day: date) -> Availability | None:
    """Return the availability entry for a specific day if it exists."""

    stmt = select(Availability).where(
        Availability.unit_id == unit_id,
        Availability.date_from == day,
    )
    result = await session.execute(stmt)
    return result.scalar_one_or_none()
