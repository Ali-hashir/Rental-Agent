# Rental Agent API

FastAPI backend delivering real-time tooling, WebRTC signaling, and agent orchestration for the browser-based leasing receptionist.

## Database configuration

The service targets a managed Postgres instance on Neon. Provide the connection string in `.env` at the repository root:

```bash
DATABASE_URL=postgresql://<username>:<password>@<your-neon-host>/<database>?sslmode=require&channel_binding=require
```

During startup the configuration layer automatically upgrades plain `postgresql://` URIs to the async `postgresql+asyncpg://` variant required by SQLAlchemy. This keeps the credentials identical to the Neon connection string you copy from the dashboard.

Once the environment variable is in place, run database migrations or the bootstrap script to create tables before executing the agent tools or tests.

## Signaling quickstart

Use the new WebSocket endpoint to coordinate SDP/ICE exchange between the browser and the agent runtime:

- URL: `ws://<host>/api/rtc/signaling/{room}?participant_id=<your-id>` (omit the query parameter to let the server assign an ID).
- On connection the server replies with a `{"type": "joined", "participants": [ ... ]}` payload so the caller knows who is already present.
- When a second participant joins, everyone else receives `{"type": "participant_joined", "participant_id": "<id>"}`.
- Send offer/answer/candidate messages as JSON objects containing `type` and `payload` keys. The server relays them to the rest of the room, wrapping them with the sender metadata: `{"type": "offer", "participant_id": "<id>", "payload": {...}}`.
- When a participant disconnects, the remaining peers receive `{"type": "participant_left", ...}` so they can close their peer connections.

This in-memory fan-out is intended for development and single-process deployments. Replace it with a LiveKit or Redis-backed implementation before scaling horizontally.
