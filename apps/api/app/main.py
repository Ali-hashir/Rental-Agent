"""Main FastAPI application entry point.

Targets:
- <600 ms turn latency p95 via lightweight middleware.
- Real-time signaling endpoints to bootstrap browser WebRTC sessions.
"""
from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .core.config import settings
from .routers import admin, rtc, tools

app = FastAPI(title="Rental Agent API", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_allow_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(rtc.router, prefix="/api/rtc", tags=["rtc"])
app.include_router(tools.router, prefix="/api/agent/tool", tags=["tools"])
app.include_router(admin.router, prefix="/api/admin", tags=["admin"])


@app.get("/health", tags=["meta"])
async def health() -> dict[str, str]:
    """Simple liveness probe."""
    return {"status": "ok"}
