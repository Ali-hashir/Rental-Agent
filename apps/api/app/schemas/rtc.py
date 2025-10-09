"""Data contracts for RTC endpoints."""
from __future__ import annotations

from pydantic import BaseModel, Field


class RtcTokenRequest(BaseModel):
    room: str = Field(..., description="Room name to join")
    user_id: str = Field(..., description="Opaque user identifier")


class RtcTokenResponse(BaseModel):
    token: str = Field(..., description="JWT token for the RTC backend")
    expires_in: int = Field(..., ge=1, description="Seconds until expiration")
