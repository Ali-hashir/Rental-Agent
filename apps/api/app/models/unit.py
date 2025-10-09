"""Unit model."""
from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import Boolean, Date, ForeignKey, Integer, String
from sqlalchemy.dialects.postgresql import ARRAY
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base

if TYPE_CHECKING:
    from .appointment import Appointment
    from .availability import Availability
    from .property import Property


class Unit(Base):
    """Individual rental unit."""

    __tablename__ = "units"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    property_id: Mapped[str] = mapped_column(ForeignKey("properties.id", ondelete="CASCADE"), nullable=False)
    title: Mapped[str] = mapped_column(String, nullable=False)
    beds: Mapped[int] = mapped_column(Integer, nullable=False)
    baths: Mapped[int] = mapped_column(Integer, nullable=False)
    sqft: Mapped[int | None] = mapped_column(Integer)
    rent: Mapped[int] = mapped_column(Integer, nullable=False)
    deposit: Mapped[int | None] = mapped_column(Integer)
    furnished: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    amenities: Mapped[list[str]] = mapped_column(ARRAY(String), default=list, nullable=False)
    available_from: Mapped[Date | None] = mapped_column(Date)
    images: Mapped[list[str]] = mapped_column(ARRAY(String), default=list, nullable=False)

    property: Mapped["Property"] = relationship("Property", back_populates="units")
    appointments: Mapped[list["Appointment"]] = relationship("Appointment", back_populates="unit")
    availability: Mapped[list["Availability"]] = relationship("Availability", back_populates="unit", cascade="all, delete-orphan")
