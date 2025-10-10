"""RTC token issuance and signaling endpoints."""
from __future__ import annotations

from uuid import uuid4

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from ..schemas.rtc import RtcTokenRequest, RtcTokenResponse
from ..services import rtc as rtc_service
from ..services.signaling import SignalingConnection, manager as signaling_manager

router = APIRouter()


@router.post("/token", response_model=RtcTokenResponse)
async def create_rtc_token(payload: RtcTokenRequest) -> RtcTokenResponse:
    """Return a room access token for WebRTC signaling."""

    token = await rtc_service.issue_token(payload.room, payload.user_id)
    return RtcTokenResponse(token=token.token, expires_in=token.expires_in)


@router.websocket("/signaling/{room}")
async def signaling_endpoint(websocket: WebSocket, room: str) -> None:
    """Simple in-memory signaling fanout for SDP and ICE payloads."""

    participant_id = websocket.query_params.get("participant_id") or str(uuid4())
    await websocket.accept()

    connection = SignalingConnection(connection_id=participant_id, send=websocket.send_json)
    existing = await signaling_manager.join(room, connection)

    await websocket.send_json(
        {
            "type": "joined",
            "room": room,
            "participant_id": participant_id,
            "participants": existing,
        }
    )

    if existing:
        await signaling_manager.broadcast(
            room,
            participant_id,
            {"type": "participant_joined", "participant_id": participant_id},
        )

    try:
        while True:
            message = await websocket.receive_json()
            if not isinstance(message, dict):
                continue
            envelope = {
                "type": message.get("type", "signal"),
                "participant_id": participant_id,
                "payload": message.get("payload", message.get("data", message)),
            }
            await signaling_manager.broadcast(room, participant_id, envelope)
    except WebSocketDisconnect:
        pass
    finally:
        await signaling_manager.leave(room, participant_id)
        await signaling_manager.broadcast(
            room,
            participant_id,
            {"type": "participant_left", "participant_id": participant_id},
        )
