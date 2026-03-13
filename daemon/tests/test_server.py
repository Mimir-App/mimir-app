"""Tests para el servidor HTTP del daemon."""

import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport

from mimir_daemon.db import Database
from mimir_daemon.config import DaemonConfig
from mimir_daemon.platform.base import PlatformProvider, WindowInfo, SessionEvent
from mimir_daemon.block_manager import BlockManager
from mimir_daemon.poller import Poller
from mimir_daemon.server import create_app


class MockPlatform(PlatformProvider):
    async def get_active_window(self):
        return None

    async def get_session_events(self):
        return []


@pytest_asyncio.fixture
async def db(tmp_path):
    database = Database(str(tmp_path / "test.db"))
    await database.connect()
    yield database
    await database.close()


@pytest.fixture
def app(db):
    config = DaemonConfig(polling_interval=60)
    platform = MockPlatform()
    block_manager = BlockManager(db=db)
    poller = Poller(config=config, db=db, platform=platform, block_manager=block_manager)
    return create_app(db=db, poller=poller)


@pytest_asyncio.fixture
async def client(app):
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c


@pytest.mark.asyncio
async def test_health(client):
    resp = await client.get("/health")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "ok"


@pytest.mark.asyncio
async def test_status(client):
    resp = await client.get("/status")
    assert resp.status_code == 200
    data = resp.json()
    assert "running" in data
    assert "version" in data


@pytest.mark.asyncio
async def test_get_blocks_empty(client):
    resp = await client.get("/blocks?date=2026-01-01")
    assert resp.status_code == 200
    assert resp.json() == []


@pytest.mark.asyncio
async def test_set_mode(client):
    resp = await client.post("/mode", json={"mode": "paused"})
    assert resp.status_code == 200
    assert resp.json()["mode"] == "paused"

    resp = await client.post("/mode", json={"mode": "active"})
    assert resp.status_code == 200
