"""RTC service abstraction.

This module encapsulates token issuance whether we self-host signaling or lean on LiveKit.
Targets: issue tokens under 50 ms server-side."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import timedelta
from secrets import token_urlsafe

from ..core import config


@dataclass(slots=True)
class RtcToken:
    token: str
    expires_in: int


async def issue_token(room: str, user_id: str) -> RtcToken:
    """Produce an RTC access token.

    For the MVP we return a signed placeholder token. Later we will integrate LiveKit or a custom SFU.
    """

    _ = (room, user_id)
    # TODO: integrate with LiveKit via settings.livekit_* when available.
    fake_token = token_urlsafe(32)
    expires = int(timedelta(hours=1).total_seconds())
    return RtcToken(token=fake_token, expires_in=expires)
