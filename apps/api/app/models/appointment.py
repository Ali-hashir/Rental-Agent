"""Appointment model."""
from __future__ import annotations

from datetime import datetime
import enum

from sqlalchemy import DateTime, Enum, ForeignKey, String
from typing import TYPE_CHECKING

from sqlalchemy.orm import Mapped, mapped_column, relationship

if TYPE_CHECKING:
    from .lead import Lead
    from .unit import Unit

from .base import Base


class AppointmentStatus(str, enum.Enum):
    SCHEDULED = "scheduled"
    COMPLETED = "completed"
    CANCELED = "canceled"


class Appointment(Base):
    """Booked viewing appointment."""

    __tablename__ = "appointments"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    lead_id: Mapped[str | None] = mapped_column(ForeignKey("leads.id", ondelete="SET NULL"))
    unit_id: Mapped[str] = mapped_column(ForeignKey("units.id", ondelete="CASCADE"), nullable=False)
    slot_start: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    slot_end: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    status: Mapped[AppointmentStatus] = mapped_column(
        Enum(AppointmentStatus, name="appointment_status"), default=AppointmentStatus.SCHEDULED, nullable=False
    )
    calendar_url: Mapped[str | None] = mapped_column(String)

    lead: Mapped["Lead | None"] = relationship("Lead", back_populates="appointments")
    unit: Mapped["Unit"] = relationship("Unit", back_populates="appointments")
