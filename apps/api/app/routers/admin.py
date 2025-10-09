"""Admin endpoints for calls, leads, and bookings."""
from __future__ import annotations

from datetime import datetime

from fastapi import APIRouter, Query

from ..schemas import admin as admin_schema

router = APIRouter()


@router.get("/calls", response_model=admin_schema.CallListResponse)
async def list_calls(
    from_: datetime | None = Query(default=None, alias="from"),
    to: datetime | None = None,
    q: str | None = None,
) -> admin_schema.CallListResponse:
    """Return paginated call summaries."""

    # TODO: Query datastore once implemented.
    return admin_schema.CallListResponse(items=[])


@router.get("/calls/{call_id}", response_model=admin_schema.CallDetailResponse)
async def get_call(call_id: str) -> admin_schema.CallDetailResponse:
    """Return call transcript and metrics."""

    # TODO: Load from object storage/transcript store.
    return admin_schema.CallDetailResponse(
        call=admin_schema.CallDetail(
            transcript=[],
            summary="",
            metrics=admin_schema.CallMetrics(avg_latency_ms=0, barge_ins=0)
        )
    )
