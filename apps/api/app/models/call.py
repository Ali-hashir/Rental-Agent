"""Call model."""
from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, ForeignKey, Integer, String
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base

if TYPE_CHECKING:
    from .lead import Lead


class Call(Base):
    """Call record including transcript references."""

    __tablename__ = "calls"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    lead_id: Mapped[str | None] = mapped_column(ForeignKey("leads.id", ondelete="SET NULL"))
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow, nullable=False)
    duration_sec: Mapped[int | None] = mapped_column(Integer)
    outcome: Mapped[str | None] = mapped_column(String)
    transcript_uri: Mapped[str | None] = mapped_column(String)
    metrics_json: Mapped[dict] = mapped_column(JSONB, default=dict, nullable=False)

    lead: Mapped["Lead | None"] = relationship("Lead", back_populates="calls")
