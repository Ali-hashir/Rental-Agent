"""RTC token issuance and signaling endpoints."""
from __future__ import annotations

from fastapi import APIRouter, Depends

from ..schemas.rtc import RtcTokenRequest, RtcTokenResponse
from ..services import rtc as rtc_service

router = APIRouter()


@router.post("/token", response_model=RtcTokenResponse)
async def create_rtc_token(payload: RtcTokenRequest) -> RtcTokenResponse:
    """Return a room access token for WebRTC signaling."""

    token = await rtc_service.issue_token(payload.room, payload.user_id)
    return RtcTokenResponse(token=token.token, expires_in=token.expires_in)
