"""Tests para el proceso de captura."""

import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport

from mimir_daemon.config import DaemonConfig
from mimir_daemon.db import Database
from mimir_daemon.platform.base import PlatformProvider
from mimir_daemon.block_manager import BlockManager
from mimir_daemon.poller import Poller
from mimir_daemon.capture import create_capture_app


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
def capture_app(db):
    config = DaemonConfig(polling_interval=60)
    platform = MockPlatform()
    block_manager = BlockManager(db=db)
    poller = Poller(config=config, db=db, platform=platform, block_manager=block_manager)
    return create_capture_app(poller=poller)


@pytest_asyncio.fixture
async def client(capture_app):
    transport = ASGITransport(app=capture_app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c


@pytest.mark.asyncio
async def test_capture_health(client):
    resp = await client.get("/health")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "ok"
    assert data["service"] == "capture"


@pytest.mark.asyncio
async def test_capture_status(client):
    resp = await client.get("/status")
    assert resp.status_code == 200
    data = resp.json()
    assert "running" in data
    assert "mode" in data
    assert "uptime_seconds" in data


@pytest.mark.asyncio
async def test_capture_no_other_endpoints(client):
    """Capture no tiene endpoints de bloques ni integraciones."""
    resp = await client.get("/blocks")
    assert resp.status_code in (404, 405)

    resp = await client.get("/odoo/projects")
    assert resp.status_code in (404, 405)
