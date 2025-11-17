"""Static listing catalog for the demo leasing agent."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import List


@dataclass(slots=True)
class Listing:
    """Rental listing details available to the agent."""

    id: str
    title: str
    area: str
    beds: int
    baths: int
    rent: int
    address: str
    notes: str = ""
    amenities: List[str] = field(default_factory=list)
    viewing_slots: List[str] = field(default_factory=list)


LISTINGS: list[Listing] = [
    Listing(
        id="2br-clifton",
        title="2BR Clifton",
        area="Clifton",
        beds=2,
        baths=2,
        rent=120_000,
        address="Block 5, Clifton, Karachi",
        notes="High-rise apartment with sea view and dedicated parking.",
        amenities=["Sea view", "Parking", "Generator backup"],
        viewing_slots=["Tomorrow 4:00 PM", "Saturday 11:00 AM", "Monday 6:00 PM"],
    ),
    Listing(
        id="1br-gulshan",
        title="1BR Gulshan",
        area="Gulshan",
        beds=1,
        baths=1,
        rent=65_000,
        address="Block 7, Gulshan-e-Iqbal, Karachi",
        notes="Cozy unit near the central park with 24/7 security.",
        amenities=["Near park", "Security", "High-speed internet"],
        viewing_slots=["Today 6:30 PM", "Friday 5:00 PM", "Sunday 2:00 PM"],
    ),
]


AREA_ALIASES: dict[str, str] = {
    "clifton": "Clifton",
    "sea view": "Clifton",
    "gulshan": "Gulshan",
    "gulshan-e-iqbal": "Gulshan",
}
