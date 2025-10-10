"""Schemas for agent session management and event ingestion."""
from __future__ import annotations

from datetime import datetime
import enum
from typing import Any

from pydantic import BaseModel, Field


class ConsentStatus(str, enum.Enum):
    UNKNOWN = "unknown"
    GRANTED = "granted"
    DECLINED = "declined"


class SessionStartRequest(BaseModel):
    session_id: str
    started_at: datetime | None = None
    lead_id: str | None = None
    consent: bool | None = Field(default=None, description="Visitor consent decision")

class SessionStartResponse(BaseModel):
    call_id: str
    consent_status: ConsentStatus


class AgentEventType(str, enum.Enum):
    SESSION_STARTED = "session_started"
    SESSION_ENDED = "session_ended"
    VAD_START = "vad_start"
    VAD_END = "vad_end"
    TTS_STOP = "tts_stop"
    CONSENT_GRANTED = "consent_granted"
    CONSENT_DECLINED = "consent_declined"


class AgentEventRequest(BaseModel):
    session_id: str
    type: AgentEventType
    ts: datetime
    data: dict[str, Any] | None = Field(default=None, description="Optional event payload")
