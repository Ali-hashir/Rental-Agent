"""Property model."""
from __future__ import annotations

from sqlalchemy import String
from sqlalchemy.dialects.postgresql import JSONB
from typing import TYPE_CHECKING

from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base

if TYPE_CHECKING:
    from .unit import Unit


class Property(Base):
    """Represents a property containing rental units."""

    __tablename__ = "properties"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    name: Mapped[str] = mapped_column(String, nullable=False)
    address: Mapped[str] = mapped_column(String, nullable=False)
    city: Mapped[str] = mapped_column(String, nullable=False)
    policies_json: Mapped[dict] = mapped_column(JSONB, default=dict, nullable=False)
    units: Mapped[list["Unit"]] = relationship("Unit", back_populates="property")
