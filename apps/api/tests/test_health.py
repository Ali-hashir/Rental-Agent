import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app


@pytest.mark.asyncio
async def test_health_endpoint() -> None:
    transport = ASGITransport(app=app)

    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        response = await client.get("/api/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


@pytest.mark.asyncio
async def test_robots_and_favicon() -> None:
    transport = ASGITransport(app=app)

    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        robots = await client.get("/robots.txt")
        favicon = await client.get("/favicon.ico")

    assert robots.status_code == 200
    assert "User-agent" in robots.text
    assert favicon.status_code == 200
    assert favicon.headers.get("content-type") == "image/png"
