"""Lead model."""
from __future__ import annotations

from datetime import datetime
import enum

from sqlalchemy import DateTime, Enum, String
from typing import TYPE_CHECKING

from sqlalchemy.orm import Mapped, mapped_column, relationship

if TYPE_CHECKING:
    from .appointment import Appointment
    from .call import Call

from .base import Base


class LeadStage(str, enum.Enum):
    NEW = "new"
    ENGAGED = "engaged"
    BOOKED = "booked"
    LOST = "lost"


class Lead(Base):
    """Lead captured from calls."""

    __tablename__ = "leads"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    name: Mapped[str | None] = mapped_column(String)
    phone: Mapped[str | None] = mapped_column(String)
    email: Mapped[str | None] = mapped_column(String)
    source: Mapped[str | None] = mapped_column(String)
    stage: Mapped[LeadStage] = mapped_column(Enum(LeadStage, name="lead_stage"), default=LeadStage.NEW, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow, nullable=False)
    appointments: Mapped[list["Appointment"]] = relationship("Appointment", back_populates="lead")
    calls: Mapped[list["Call"]] = relationship("Call", back_populates="lead")
