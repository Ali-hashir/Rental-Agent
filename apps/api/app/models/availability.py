"""Availability model."""
from __future__ import annotations

from datetime import date
import enum
from typing import TYPE_CHECKING

from sqlalchemy import Date, Enum, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship

if TYPE_CHECKING:
    from .unit import Unit

from .base import Base


class AvailabilityStatus(str, enum.Enum):
    AVAILABLE = "available"
    ON_HOLD = "on_hold"
    RENTED = "rented"


class Availability(Base):
    """Availability for a unit by date."""

    __tablename__ = "availability"

    unit_id: Mapped[str] = mapped_column(ForeignKey("units.id", ondelete="CASCADE"), primary_key=True)
    date_from: Mapped[date] = mapped_column(Date, primary_key=True)
    status: Mapped[AvailabilityStatus] = mapped_column(
        Enum(AvailabilityStatus, name="availability_status"), nullable=False
    )
    unit: Mapped["Unit"] = relationship("Unit", back_populates="availability")
