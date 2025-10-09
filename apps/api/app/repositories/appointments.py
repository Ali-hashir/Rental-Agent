"""Appointment persistence helpers."""
from __future__ import annotations

from datetime import datetime
from uuid import uuid4

from sqlalchemy import Select, and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from ..models.appointment import Appointment, AppointmentStatus


async def has_conflict(
    session: AsyncSession,
    *,
    unit_id: str,
    slot_start: datetime,
    slot_end: datetime,
) -> bool:
    """Return True if there is an overlapping appointment for the unit."""

    stmt: Select[tuple[int]] = select(func.count(Appointment.id)).where(
        Appointment.unit_id == unit_id,
        Appointment.slot_start < slot_end,
        Appointment.slot_end > slot_start,
        Appointment.status != AppointmentStatus.CANCELED,
    )
    count = await session.execute(stmt)
    return count.scalar_one() > 0


async def create_appointment(
    session: AsyncSession,
    *,
    lead_id: str,
    unit_id: str,
    slot_start: datetime,
    slot_end: datetime,
    calendar_url: str | None = None,
) -> str:
    """Persist a new appointment and return its identifier."""

    appointment = Appointment(
        id=str(uuid4()),
        lead_id=lead_id,
        unit_id=unit_id,
        slot_start=slot_start,
        slot_end=slot_end,
        calendar_url=calendar_url,
        status=AppointmentStatus.SCHEDULED,
    )
    session.add(appointment)
    await session.flush()
    return appointment.id


async def list_booked_slots(
    session: AsyncSession,
    *,
    unit_id: str,
    window_start: datetime,
    window_end: datetime,
) -> list[Appointment]:
    """Return booked slots for the unit in the provided window."""

    stmt = (
        select(Appointment)
        .where(
            Appointment.unit_id == unit_id,
            Appointment.slot_start >= window_start,
            Appointment.slot_start < window_end,
            Appointment.status != AppointmentStatus.CANCELED,
        )
        .order_by(Appointment.slot_start.asc())
    )
    result = await session.execute(stmt)
    return list(result.scalars().all())
