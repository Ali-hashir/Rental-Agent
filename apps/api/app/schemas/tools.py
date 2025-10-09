"""Schemas for agent tool interactions."""
from __future__ import annotations

from datetime import date, datetime
from typing import Annotated

from pydantic import BaseModel, Field


class ListingFilters(BaseModel):
    location: str | None = Field(default=None)
    rent_min: int | None = Field(default=None, ge=0)
    rent_max: int | None = Field(default=None, ge=0)
    beds: int | None = Field(default=None, ge=0)
    baths: int | None = Field(default=None, ge=0)
    furnished: bool | None = Field(default=None)
    amenities: list[str] = Field(default_factory=list)
    available_from: date | None = None


class ListingCard(BaseModel):
    unit_id: str
    property_id: str
    title: str
    rent: int
    deposit: int | None = None
    baths: int
    beds: int
    sqft: int | None = None
    furnished: bool = False
    amenities: list[str] = Field(default_factory=list)
    address: str | None = None
    images: list[str] = Field(default_factory=list)
    available_from: date | None = None


class SearchListingsRequest(BaseModel):
    filters: ListingFilters
    limit: int = Field(default=5, ge=1, le=50)
    cursor: str | None = None


class SearchListingsResponse(BaseModel):
    results: list[ListingCard]
    next_cursor: str | None = None


class QuoteTotalRequest(BaseModel):
    unit_id: str
    start_date: date | None = None


class FeeLine(BaseModel):
    name: str
    amount: int


class QuoteTotalResponse(BaseModel):
    rent: int
    deposit: int | None = None
    fees: list[FeeLine] = Field(default_factory=list)
    utilities_included: list[str] = Field(default_factory=list)
    notes: str | None = None


class ListSlotsRequest(BaseModel):
    unit_id: str
    days_ahead: int = Field(default=14, ge=1, le=60)


class TimeSlot(BaseModel):
    start: datetime
    end: datetime


class ListSlotsResponse(BaseModel):
    slots: list[TimeSlot]


class VisitorInfo(BaseModel):
    name: str
    phone: str
    email: str


class BookViewingRequest(BaseModel):
    unit_id: str
    slot_start: datetime
    visitor: VisitorInfo


class BookViewingResponse(BaseModel):
    appointment_id: str
    calendar_event_url: str | None = None


class SendFollowUpRequest(BaseModel):
    lead_id: str
    channel: Annotated[str, Field(pattern="^(sms|email)$")]


class SendFollowUpResponse(BaseModel):
    status: str
