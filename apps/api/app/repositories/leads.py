"""Lead repository helpers."""
from __future__ import annotations

from datetime import datetime
from uuid import uuid4

from sqlalchemy import Select, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from ..models.lead import Lead, LeadStage


async def get_by_id(session: AsyncSession, lead_id: str) -> Lead | None:
    """Return a lead by identifier."""

    stmt: Select[tuple[Lead]] = select(Lead).where(Lead.id == lead_id)
    result = await session.execute(stmt)
    return result.scalar_one_or_none()


async def get_or_create_from_contact(
    session: AsyncSession,
    *,
    name: str,
    phone: str,
    email: str,
) -> Lead:
    """Lookup a lead by contact info or create a new one."""

    contact_filters = []
    if email:
        contact_filters.append(Lead.email == email)
    if phone:
        contact_filters.append(Lead.phone == phone)

    lead: Lead | None = None
    if contact_filters:
        stmt = select(Lead).where(or_(*contact_filters)).order_by(Lead.created_at.asc()).limit(1)
        result = await session.execute(stmt)
        lead = result.scalar_one_or_none()

    if lead:
        updated = False
        if not lead.name and name:
            lead.name = name
            updated = True
        if not lead.email and email:
            lead.email = email
            updated = True
        if not lead.phone and phone:
            lead.phone = phone
            updated = True
        if lead.stage == LeadStage.NEW:
            lead.stage = LeadStage.ENGAGED
            updated = True
        if updated:
            session.add(lead)
        return lead

    lead = Lead(
        id=str(uuid4()),
        name=name or None,
        phone=phone or None,
        email=email or None,
        source="web",
        stage=LeadStage.ENGAGED,
        created_at=datetime.utcnow(),
    )
    session.add(lead)
    await session.flush()
    return lead
