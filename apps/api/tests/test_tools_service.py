"""Service-level tests for agent tool endpoints."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest
from fastapi import HTTPException

from app.models.availability import AvailabilityStatus
from app.models.lead import LeadStage
from app.repositories import appointments as appointments_repo
from app.repositories import availability as availability_repo
from app.repositories import leads as leads_repo
from app.repositories import listings as listings_repo
from app.schemas import tools as schemas
from app.services import tools as tools_service


class DummySession:
    """Minimal session stub supporting async transaction context."""

    def __init__(self) -> None:
        self.added: list[object] = []
        self.begin_called = False

    def add(self, obj: object) -> None:
        self.added.append(obj)

    def begin(self):  # noqa: D401 - mimic SQLAlchemy's async begin
        session = self

        class _Tx:
            async def __aenter__(self_inner):
                session.begin_called = True
                return session

            async def __aexit__(self_inner, exc_type, exc, tb):
                return False

        return _Tx()


class DummyAvailability:
    def __init__(self, *, date_from):
        self.date_from = date_from
        self.status = AvailabilityStatus.AVAILABLE


@pytest.mark.asyncio
async def test_search_listings_encodes_cursor(monkeypatch):
    session = AsyncMock()
    listing_row = listings_repo.ListingRow(
        unit_id="unit-1",
        property_id="prop-1",
        property_name="Tower",
        property_address="123 Main",
        property_city="Metropolis",
        title="Unit",
        rent=150000,
        deposit=300000,
        baths=2,
        beds=2,
        sqft=900,
        furnished=False,
        amenities=["parking"],
        images=[],
        available_from=None,
    )

    monkeypatch.setattr(
        listings_repo,
        "search_units",
        AsyncMock(return_value=([listing_row], (160000, "unit-2"))),
    )

    payload = schemas.SearchListingsRequest(filters=schemas.ListingFilters(location="Metro"), limit=1)

    response = await tools_service.search_listings(payload, session)

    assert response.results[0].unit_id == "unit-1"
    assert response.results[0].property_name == "Tower"
    assert response.results[0].address.endswith("Metropolis")
    assert response.next_cursor is not None
    assert tools_service._decode_cursor(response.next_cursor) == (160000, "unit-2")


@pytest.mark.asyncio
async def test_quote_total_missing_deposit_adds_guard(monkeypatch):
    detail = listings_repo.UnitDetail(
        unit_id="unit-1",
        property_id="prop-1",
        rent=120000,
        deposit=None,
        fees=[{"name": "application", "amount": 2000}],
        utilities_included=["water"],
        notes=None,
        amenities=["gym"],
        images=[],
        available_from=None,
        property_name="",
        property_address="",
        property_city="",
    )
    monkeypatch.setattr(listings_repo, "get_unit_detail", AsyncMock(return_value=detail))

    payload = schemas.QuoteTotalRequest(unit_id="unit-1")
    response = await tools_service.quote_total(payload, AsyncMock())

    assert response.rent == 120000
    assert response.deposit is None
    assert "follow up" in (response.notes or "").lower()
    assert response.fees[0].name == "application"


@pytest.mark.asyncio
async def test_quote_total_not_found(monkeypatch):
    monkeypatch.setattr(listings_repo, "get_unit_detail", AsyncMock(return_value=None))
    payload = schemas.QuoteTotalRequest(unit_id="missing")

    with pytest.raises(HTTPException) as exc:
        await tools_service.quote_total(payload, AsyncMock())

    assert exc.value.status_code == 404


@pytest.mark.asyncio
async def test_list_slots_filters_booked(monkeypatch):
    session = AsyncMock()
    today = datetime.now(timezone.utc).date()
    future_day = today + timedelta(days=2)

    availability = DummyAvailability(date_from=future_day)
    monkeypatch.setattr(
        availability_repo,
        "list_available_windows",
        AsyncMock(return_value=[availability]),
    )

    booked_slot = datetime.combine(future_day, tools_service.DEFAULT_SLOT_TIMES[0], tzinfo=timezone.utc)
    booked = SimpleNamespace(slot_start=booked_slot)
    monkeypatch.setattr(
        appointments_repo,
        "list_booked_slots",
        AsyncMock(return_value=[booked]),
    )

    payload = schemas.ListSlotsRequest(unit_id="unit-1", days_ahead=5)
    response = await tools_service.list_slots(payload, session)

    starts = [slot.start for slot in response.slots]
    assert all(start.date() == future_day for start in starts)
    assert booked_slot not in starts
    assert len(starts) == len(tools_service.DEFAULT_SLOT_TIMES) - 1


@pytest.mark.asyncio
async def test_book_viewing_success(monkeypatch):
    session = DummySession()
    future = datetime.now(timezone.utc) + timedelta(days=1)
    availability = DummyAvailability(date_from=future.date())

    monkeypatch.setattr(
        availability_repo,
        "get_single_window",
        AsyncMock(return_value=availability),
    )
    monkeypatch.setattr(
        appointments_repo,
        "has_conflict",
        AsyncMock(return_value=False),
    )
    monkeypatch.setattr(
        leads_repo,
        "get_or_create_from_contact",
        AsyncMock(return_value=SimpleNamespace(id="lead-1")),
    )
    monkeypatch.setattr(
        appointments_repo,
        "create_appointment",
        AsyncMock(return_value="appt-1"),
    )

    visitor = schemas.VisitorInfo(name="Ada", phone="123", email="ada@example.com")
    payload = schemas.BookViewingRequest(unit_id="unit-1", slot_start=future, visitor=visitor)

    response = await tools_service.book_viewing(payload, session)

    assert response.appointment_id == "appt-1"
    assert availability.status == AvailabilityStatus.ON_HOLD
    assert availability in session.added


@pytest.mark.asyncio
async def test_book_viewing_conflict(monkeypatch):
    session = DummySession()
    future = datetime.now(timezone.utc) + timedelta(days=1)
    availability = DummyAvailability(date_from=future.date())

    monkeypatch.setattr(
        availability_repo,
        "get_single_window",
        AsyncMock(return_value=availability),
    )
    monkeypatch.setattr(
        appointments_repo,
        "has_conflict",
        AsyncMock(return_value=True),
    )

    visitor = schemas.VisitorInfo(name="Ada", phone="123", email="ada@example.com")
    payload = schemas.BookViewingRequest(unit_id="unit-1", slot_start=future, visitor=visitor)

    with pytest.raises(HTTPException) as exc:
        await tools_service.book_viewing(payload, session)

    assert exc.value.status_code == 409


@pytest.mark.asyncio
async def test_send_followup_updates_stage(monkeypatch):
    session = DummySession()
    lead = SimpleNamespace(id="lead-1", stage=LeadStage.NEW)

    monkeypatch.setattr(leads_repo, "get_by_id", AsyncMock(return_value=lead))

    payload = schemas.SendFollowUpRequest(lead_id="lead-1", channel="email")
    response = await tools_service.send_followup(payload, session)

    assert response.status == "queued"
    assert lead.stage == LeadStage.ENGAGED
    assert lead in session.added


@pytest.mark.asyncio
async def test_send_followup_missing_lead(monkeypatch):
    session = DummySession()
    monkeypatch.setattr(leads_repo, "get_by_id", AsyncMock(return_value=None))

    payload = schemas.SendFollowUpRequest(lead_id="missing", channel="sms")
    with pytest.raises(HTTPException) as exc:
        await tools_service.send_followup(payload, session)

    assert exc.value.status_code == 404