# Rental Agent API

FastAPI backend delivering real-time tooling, WebRTC signaling, and agent orchestration for the browser-based leasing receptionist.

## Database configuration

The service targets a managed Postgres instance on Neon. Provide the connection string in `.env` at the repository root:

```bash
DATABASE_URL=postgresql://<username>:<password>@<your-neon-host>/<database>?sslmode=require&channel_binding=require
```

During startup the configuration layer automatically upgrades plain `postgresql://` URIs to the async `postgresql+asyncpg://` variant required by SQLAlchemy. This keeps the credentials identical to the Neon connection string you copy from the dashboard.

Once the environment variable is in place, run database migrations or the bootstrap script to create tables before executing the agent tools or tests.
