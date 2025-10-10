"""Business logic for agent tool functions."""
from __future__ import annotations

import base64
from datetime import datetime, time, timedelta, timezone

from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from ..models.availability import AvailabilityStatus
from ..models.lead import LeadStage
from ..repositories import appointments as appointments_repo
from ..repositories import availability as availability_repo
from ..repositories import leads as leads_repo
from ..repositories import listings as listings_repo
from ..schemas import tools as schemas

SLOT_DURATION = timedelta(minutes=30)
DEFAULT_SLOT_TIMES: tuple[time, ...] = (
    time(hour=10, minute=0),
    time(hour=12, minute=30),
    time(hour=15, minute=0),
)


async def search_listings(
    payload: schemas.SearchListingsRequest,
    session: AsyncSession,
) -> schemas.SearchListingsResponse:
    """Search listings by filters and support keyset pagination.

    Aligns with FR6/FR5 by grounding values in the database. Cursor encoding follows
    the API contract in section 8 (tokenised state passed between calls).
    """

    cursor_state = _decode_cursor(payload.cursor) if payload.cursor else None

    listing_rows, next_cursor_state = await listings_repo.search_units(
        session,
        filters=payload.filters,
        limit=payload.limit,
        cursor_state=cursor_state,
    )

    results = [
        schemas.ListingCard(
            unit_id=row.unit_id,
            property_id=row.property_id,
            property_name=row.property_name,
            property_city=row.property_city,
            title=row.title,
            rent=row.rent,
            deposit=row.deposit,
            baths=row.baths,
            beds=row.beds,
            sqft=row.sqft,
            furnished=row.furnished,
            amenities=row.amenities,
            address=f"{row.property_address}, {row.property_city}",
            images=row.images,
            available_from=row.available_from,
        )
        for row in listing_rows
    ]

    next_cursor = _encode_cursor(next_cursor_state) if next_cursor_state else None

    return schemas.SearchListingsResponse(results=results, next_cursor=next_cursor)


async def quote_total(
    payload: schemas.QuoteTotalRequest,
    session: AsyncSession,
) -> schemas.QuoteTotalResponse:
    """Return pricing details for a unit, guarding against missing data.

    Implements FR5 acceptance criteria by declining to fabricate values.
    """

    detail = await listings_repo.get_unit_detail(session, payload.unit_id)
    if detail is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Unit not found")

    notes = detail.notes
    if detail.deposit is None:
        notes = notes or "Deposit amount unavailable. I can check with a person and follow up."

    fees = [schemas.FeeLine(name=f["name"], amount=int(f["amount"])) for f in detail.fees]

    return schemas.QuoteTotalResponse(
        rent=detail.rent,
        deposit=detail.deposit,
        fees=fees,
        utilities_included=[str(item) for item in detail.utilities_included],
        notes=notes,
    )


async def list_slots(
    payload: schemas.ListSlotsRequest,
    session: AsyncSession,
) -> schemas.ListSlotsResponse:
    """Return available viewing slots for the requested unit.

    Satisfies FR7 by exposing near-term availability while skipping booked slots.
    """

    now = datetime.now(timezone.utc)
    start_date = now.date()
    end_date = (now + timedelta(days=payload.days_ahead)).date()

    windows = await availability_repo.list_available_windows(
        session, unit_id=payload.unit_id, start_date=start_date, end_date=end_date
    )

    window_start = datetime.combine(start_date, time.min, tzinfo=timezone.utc)
    window_end = datetime.combine(end_date, time.max, tzinfo=timezone.utc)
    booked = await appointments_repo.list_booked_slots(
        session,
        unit_id=payload.unit_id,
        window_start=window_start,
        window_end=window_end,
    )
    booked_starts = {appt.slot_start for appt in booked}

    slots = []
    for availability in windows:
        day = availability.date_from
        for slot_time in DEFAULT_SLOT_TIMES:
            slot_start = datetime.combine(day, slot_time, tzinfo=timezone.utc)
            slot_end = slot_start + SLOT_DURATION
            if slot_start < now:
                continue
            if slot_start in booked_starts:
                continue
            slots.append(schemas.TimeSlot(start=slot_start, end=slot_end))

    return schemas.ListSlotsResponse(slots=sorted(slots, key=lambda item: item.start))


async def book_viewing(
    payload: schemas.BookViewingRequest,
    session: AsyncSession,
) -> schemas.BookViewingResponse:
    """Book a viewing, ensuring the slot is valid and not double booked."""

    slot_start = _ensure_tz(payload.slot_start)
    slot_end = slot_start + SLOT_DURATION
    if slot_start < datetime.now(timezone.utc):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Slot is in the past")

    slot_day = slot_start.date()

    async with session.begin():
        availability = await availability_repo.get_single_window(
            session, unit_id=payload.unit_id, day=slot_day
        )
        if availability is None or availability.status != AvailabilityStatus.AVAILABLE:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Slot no longer available")

        if await appointments_repo.has_conflict(
            session, unit_id=payload.unit_id, slot_start=slot_start, slot_end=slot_end
        ):
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Slot already booked")

        visitor = payload.visitor
        lead = await leads_repo.get_or_create_from_contact(
            session, name=visitor.name, phone=visitor.phone, email=visitor.email
        )

        appointment_id = await appointments_repo.create_appointment(
            session,
            lead_id=lead.id,
            unit_id=payload.unit_id,
            slot_start=slot_start,
            slot_end=slot_end,
        )

        # Mark the availability as on hold to reflect a booked viewing until confirmation.
        availability.status = AvailabilityStatus.ON_HOLD
        session.add(availability)

    return schemas.BookViewingResponse(appointment_id=appointment_id, calendar_event_url=None)


async def send_followup(
    payload: schemas.SendFollowUpRequest,
    session: AsyncSession,
) -> schemas.SendFollowUpResponse:
    """Record that a follow-up was sent to the lead."""

    async with session.begin():
        lead = await leads_repo.get_by_id(session, payload.lead_id)
        if lead is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Lead not found")

        if lead.stage == LeadStage.NEW:
            lead.stage = LeadStage.ENGAGED
            session.add(lead)

    # Real implementation would enqueue email/SMS delivery.
    return schemas.SendFollowUpResponse(status="queued")


def _decode_cursor(cursor: str) -> tuple[int, str]:
    """Decode the base64 cursor token into its tuple form."""

    try:
        decoded = base64.urlsafe_b64decode(cursor.encode("utf-8")).decode("utf-8")
        rent_str, unit_id = decoded.split(":", 1)
        return int(rent_str), unit_id
    except Exception as exc:  # pragma: no cover - defensive guard
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid cursor") from exc


def _encode_cursor(state: tuple[int, str] | None) -> str | None:
    """Encode cursor tuple into a token."""

    if state is None:
        return None
    rent, unit_id = state
    token = f"{rent}:{unit_id}".encode("utf-8")
    return base64.urlsafe_b64encode(token).decode("utf-8")


def _ensure_tz(value: datetime) -> datetime:
    """Ensure the datetime is timezone-aware in UTC."""

    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)
