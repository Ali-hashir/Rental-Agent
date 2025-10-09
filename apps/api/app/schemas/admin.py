"""Schemas for admin API."""
from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field


class CallSummary(BaseModel):
    call_id: str
    started_at: datetime
    duration_sec: int
    lead_id: str | None = None
    outcome: str | None = Field(default=None)


class CallListResponse(BaseModel):
    items: list[CallSummary]


class TranscriptLine(BaseModel):
    speaker: str
    ts: datetime
    text: str


class CallMetrics(BaseModel):
    avg_latency_ms: int
    barge_ins: int


class CallDetail(BaseModel):
    transcript: list[TranscriptLine]
    summary: str
    metrics: CallMetrics


class CallDetailResponse(BaseModel):
    call: CallDetail
