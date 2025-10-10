"""Tests for signaling manager and websocket endpoint."""
from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.services.signaling import SignalingConnection, SignalingManager


class DummyConnection:
    def __init__(self, connection_id: str) -> None:
        self.connection_id = connection_id
        self.messages: list[dict] = []

    async def send(self, message: dict) -> None:
        self.messages.append(message)


@pytest.mark.asyncio
async def test_signaling_manager_join_broadcast_leave():
    manager = SignalingManager()
    conn_a = DummyConnection("a")
    conn_b = DummyConnection("b")

    existing = await manager.join("room-1", SignalingConnection("a", conn_a.send))
    assert existing == []

    existing = await manager.join("room-1", SignalingConnection("b", conn_b.send))
    assert existing == ["a"]

    await manager.broadcast("room-1", "b", {"type": "offer", "sdp": "foo"})
    assert conn_a.messages == [{"type": "offer", "sdp": "foo"}]

    await manager.leave("room-1", "a")
    await manager.broadcast("room-1", "b", {"type": "candidate"})
    assert conn_a.messages == [{"type": "offer", "sdp": "foo"}]

    await manager.leave("room-1", "b")

    conn_c = DummyConnection("c")
    existing = await manager.join("room-1", SignalingConnection("c", conn_c.send))
    assert existing == []
    await manager.leave("room-1", "c")


def test_signaling_websocket_broadcast():
    client = TestClient(app)

    with client.websocket_connect("/api/rtc/signaling/test-room?participant_id=a") as ws_a:
        joined_a = ws_a.receive_json()
        assert joined_a["participants"] == []

        with client.websocket_connect("/api/rtc/signaling/test-room?participant_id=b") as ws_b:
            joined_b = ws_b.receive_json()
            assert "a" in joined_b["participants"]

            notice = ws_a.receive_json()
            assert notice["type"] == "participant_joined"
            assert notice["participant_id"] == "b"

            ws_b.send_json({"type": "offer", "payload": {"sdp": "hello"}})
            forwarded = ws_a.receive_json()
            assert forwarded["type"] == "offer"
            assert forwarded["participant_id"] == "b"
            assert forwarded["payload"]["sdp"] == "hello"

        left_notice = ws_a.receive_json()
        assert left_notice["type"] == "participant_left"
        assert left_notice["participant_id"] == "b"
