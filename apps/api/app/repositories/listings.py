"""Data access helpers for property and unit listings."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from typing import Iterable, Sequence

from sqlalchemy import and_, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from ..models.property import Property
from ..models.unit import Unit


@dataclass(slots=True)
class ListingRow:
    """Flattened listing details used by the service layer."""

    unit_id: str
    property_id: str
    property_name: str
    property_address: str
    property_city: str
    title: str
    rent: int
    deposit: int | None
    baths: int
    beds: int
    sqft: int | None
    furnished: bool
    amenities: list[str]
    images: list[str]
    available_from: date | None


@dataclass(slots=True)
class UnitDetail:
    """Unit detail with property metadata and policy docs."""

    unit_id: str
    property_id: str
    rent: int
    deposit: int | None
    fees: list[dict]
    utilities_included: list[str]
    notes: str | None
    amenities: list[str]
    images: list[str]
    available_from: date | None
    property_name: str
    property_address: str
    property_city: str


async def search_units(
    session: AsyncSession,
    *,
    filters: "ListingFiltersProtocol",
    limit: int,
    cursor_state: tuple[int, str] | None,
) -> tuple[list[ListingRow], tuple[int, str] | None]:
    """Return listings matching the supplied filters.

    The cursor state is an encoded tuple of (rent, unit_id) to enable keyset pagination.
    """

    stmt = select(Unit, Property).join(Property, Unit.property)

    if filters.location:
        location = f"%{filters.location.lower()}%"
        stmt = stmt.where(
            or_(
                func.lower(Property.city).like(location),
                func.lower(Property.address).like(location),
            )
        )

    if filters.rent_min is not None:
        stmt = stmt.where(Unit.rent >= filters.rent_min)
    if filters.rent_max is not None:
        stmt = stmt.where(Unit.rent <= filters.rent_max)
    if filters.beds is not None:
        stmt = stmt.where(Unit.beds >= filters.beds)
    if filters.baths is not None:
        stmt = stmt.where(Unit.baths >= filters.baths)
    if filters.furnished is not None:
        stmt = stmt.where(Unit.furnished.is_(filters.furnished))
    if filters.available_from is not None:
        stmt = stmt.where(
            or_(Unit.available_from == None, Unit.available_from <= filters.available_from)  # noqa: E711
        )
    if filters.amenities:
        stmt = stmt.where(Unit.amenities.contains(filters.amenities))

    if cursor_state:
        cursor_rent, cursor_unit_id = cursor_state
        stmt = stmt.where(
            or_(Unit.rent > cursor_rent, and_(Unit.rent == cursor_rent, Unit.id > cursor_unit_id))
        )

    stmt = stmt.order_by(Unit.rent.asc(), Unit.id.asc()).limit(limit + 1)

    rows: Sequence[tuple[Unit, Property]] = (await session.execute(stmt)).all()

    listing_rows = [
        ListingRow(
            unit_id=unit.id,
            property_id=property.id,
            property_name=property.name,
            property_address=property.address,
            property_city=property.city,
            title=unit.title,
            rent=unit.rent,
            deposit=unit.deposit,
            baths=unit.baths,
            beds=unit.beds,
            sqft=unit.sqft,
            furnished=unit.furnished,
            amenities=list(unit.amenities or []),
            images=list(unit.images or []),
            available_from=unit.available_from,
        )
        for unit, property in rows[:limit]
    ]

    next_cursor: tuple[int, str] | None = None
    if len(rows) > limit:
        next_unit = rows[limit][0]
        next_cursor = (next_unit.rent, next_unit.id)

    return listing_rows, next_cursor


async def get_unit_detail(session: AsyncSession, unit_id: str) -> UnitDetail | None:
    """Fetch a unit with its property metadata and policies."""

    stmt = select(Unit, Property).join(Property, Unit.property).where(Unit.id == unit_id)
    result = await session.execute(stmt)
    row = result.first()
    if row is None:
        return None

    unit, property = row
    policies = property.policies_json or {}
    fees = _normalise_fee_lines(policies.get("fees", []))
    utilities_included = list(policies.get("utilities_included", []))
    notes = policies.get("notes")

    return UnitDetail(
        unit_id=unit.id,
        property_id=property.id,
        rent=unit.rent,
        deposit=unit.deposit,
        fees=fees,
        utilities_included=utilities_included,
        notes=notes,
        amenities=list(unit.amenities or []),
        images=list(unit.images or []),
        available_from=unit.available_from,
        property_name=property.name,
        property_address=property.address,
        property_city=property.city,
    )


def _normalise_fee_lines(raw_fees: Iterable[dict] | None) -> list[dict]:
    """Ensure fee lines conform to name+amount structure."""

    if not raw_fees:
        return []

    normalised: list[dict] = []
    for fee in raw_fees:
        name = str(fee.get("name")) if isinstance(fee, dict) else None
        amount = fee.get("amount") if isinstance(fee, dict) else None
        if not name or not isinstance(amount, (int, float)):
            continue
        normalised.append({"name": name, "amount": int(amount)})
    return normalised


class ListingFiltersProtocol:
    """Protocol-like duck-type to avoid pydantic dependency at repo layer."""

    location: str | None
    rent_min: int | None
    rent_max: int | None
    beds: int | None
    baths: int | None
    furnished: bool | None
    amenities: list[str]
    available_from: date | None
