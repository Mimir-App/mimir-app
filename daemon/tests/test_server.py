"""Tests para el servidor HTTP del daemon."""

import pytest
import pytest_asyncio
from datetime import datetime, timezone
from httpx import AsyncClient, ASGITransport

from mimir_daemon.db import Database
from mimir_daemon.config import DaemonConfig
from mimir_daemon.platform.base import PlatformProvider, WindowInfo, SessionEvent
from mimir_daemon.block_manager import BlockManager
from mimir_daemon.integrations.registry import IntegrationRegistry
from mimir_daemon.integrations.mock import MockTimesheetClient
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
def registry():
    reg = IntegrationRegistry()
    reg.set_timesheet_client(MockTimesheetClient())
    return reg


@pytest.fixture
def app(db, registry):
    config = DaemonConfig(polling_interval=60)
    platform = MockPlatform()
    block_manager = BlockManager(db=db)
    poller = Poller(config=config, db=db, platform=platform, block_manager=block_manager)
    return create_app(db=db, poller=poller, registry=registry)


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
    assert "version" in data


@pytest.mark.asyncio
async def test_status(client):
    resp = await client.get("/status")
    assert resp.status_code == 200
    data = resp.json()
    assert "running" in data
    assert "version" in data
    assert "blocks_today" in data
    assert "uptime_seconds" in data


@pytest.mark.asyncio
async def test_get_blocks_empty(client):
    resp = await client.get("/blocks?date=2026-01-01")
    assert resp.status_code == 200
    assert resp.json() == []


@pytest.mark.asyncio
async def test_get_blocks_default_today(client, db):
    """GET /blocks sin fecha devuelve bloques de hoy."""
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    now = datetime.now(timezone.utc).isoformat()
    await db.create_block(
        start_time=now, end_time=now, duration_minutes=5,
        app_name="code", status="auto",
    )
    resp = await client.get("/blocks")
    assert resp.status_code == 200
    blocks = resp.json()
    assert len(blocks) == 1
    assert blocks[0]["app_name"] == "code"


@pytest.mark.asyncio
async def test_get_block_by_id(client, db):
    """GET /blocks/{id} devuelve un bloque especifico."""
    now = datetime.now(timezone.utc).isoformat()
    block_id = await db.create_block(
        start_time=now, end_time=now, duration_minutes=0,
        app_name="firefox", status="auto",
    )
    resp = await client.get(f"/blocks/{block_id}")
    assert resp.status_code == 200
    assert resp.json()["app_name"] == "firefox"


@pytest.mark.asyncio
async def test_get_block_not_found(client):
    resp = await client.get("/blocks/9999")
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_blocks_summary(client, db):
    """GET /blocks/summary devuelve estadisticas."""
    now = datetime.now(timezone.utc).isoformat()
    await db.create_block(
        start_time=now, end_time=now, duration_minutes=30,
        app_name="code", status="auto",
    )
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    resp = await client.get(f"/blocks/summary?date={today}")
    assert resp.status_code == 200
    data = resp.json()
    assert data["total_blocks"] == 1
    assert data["total_minutes"] == 30


@pytest.mark.asyncio
async def test_confirm_block(client, db):
    now = datetime.now(timezone.utc).isoformat()
    block_id = await db.create_block(
        start_time=now, end_time=now, duration_minutes=0,
        app_name="code", status="auto",
    )
    resp = await client.post(f"/blocks/{block_id}/confirm")
    assert resp.status_code == 200
    assert resp.json()["status"] == "confirmed"

    block = await db.get_block_by_id(block_id)
    assert block["status"] == "confirmed"


@pytest.mark.asyncio
async def test_update_block(client, db):
    now = datetime.now(timezone.utc).isoformat()
    block_id = await db.create_block(
        start_time=now, end_time=now, duration_minutes=0,
        app_name="code", status="auto",
    )
    resp = await client.put(
        f"/blocks/{block_id}",
        json={"user_description": "Desarrollo feature X"},
    )
    assert resp.status_code == 200

    block = await db.get_block_by_id(block_id)
    assert block["user_description"] == "Desarrollo feature X"


@pytest.mark.asyncio
async def test_delete_block(client, db):
    now = datetime.now(timezone.utc).isoformat()
    block_id = await db.create_block(
        start_time=now, end_time=now, duration_minutes=0,
        app_name="code", status="auto",
    )
    resp = await client.delete(f"/blocks/{block_id}")
    assert resp.status_code == 200

    block = await db.get_block_by_id(block_id)
    assert block is None


@pytest.mark.asyncio
async def test_set_mode(client):
    resp = await client.post("/mode", json={"mode": "paused"})
    assert resp.status_code == 200
    assert resp.json()["mode"] == "paused"

    resp = await client.post("/mode", json={"mode": "active"})
    assert resp.status_code == 200

    resp = await client.post("/mode", json={"mode": "invalid"})
    assert resp.status_code == 400


@pytest.mark.asyncio
async def test_get_odoo_projects(client):
    """GET /odoo/projects devuelve proyectos mock."""
    resp = await client.get("/odoo/projects")
    assert resp.status_code == 200
    projects = resp.json()
    assert len(projects) > 0
    assert "id" in projects[0]
    assert "name" in projects[0]


@pytest.mark.asyncio
async def test_get_odoo_tasks(client):
    """GET /odoo/tasks/{id} devuelve tareas mock."""
    resp = await client.get("/odoo/tasks/1")
    assert resp.status_code == 200
    tasks = resp.json()
    assert len(tasks) > 0
    assert tasks[0]["project_id"] == 1


@pytest.mark.asyncio
async def test_get_odoo_tasks_empty(client):
    """GET /odoo/tasks/{id} devuelve lista vacia si no hay tareas."""
    resp = await client.get("/odoo/tasks/999")
    assert resp.status_code == 200
    assert resp.json() == []


@pytest.mark.asyncio
async def test_sync_blocks_success(client, db):
    """POST /blocks/sync sincroniza bloques con proyecto asignado."""
    now = datetime.now(timezone.utc).isoformat()
    block_id = await db.create_block(
        start_time=now, end_time=now, duration_minutes=60,
        app_name="code", status="confirmed",
    )
    await db.update_block(block_id, odoo_project_id=1, odoo_task_id=101,
                          user_description="Desarrollo daemon")

    resp = await client.post("/blocks/sync", json={"block_ids": [block_id]})
    assert resp.status_code == 200
    data = resp.json()
    assert data["synced"] == 1
    assert len(data["errors"]) == 0

    block = await db.get_block_by_id(block_id)
    assert block["status"] == "synced"
    assert block["odoo_entry_id"] is not None


@pytest.mark.asyncio
async def test_sync_blocks_no_project(client, db):
    """POST /blocks/sync falla si el bloque no tiene proyecto."""
    now = datetime.now(timezone.utc).isoformat()
    block_id = await db.create_block(
        start_time=now, end_time=now, duration_minutes=30,
        app_name="code", status="confirmed",
    )

    resp = await client.post("/blocks/sync", json={"block_ids": [block_id]})
    assert resp.status_code == 200
    data = resp.json()
    assert data["synced"] == 0
    assert len(data["errors"]) == 1

    block = await db.get_block_by_id(block_id)
    assert block["status"] == "error"


@pytest.mark.asyncio
async def test_get_odoo_entries(client):
    """GET /odoo/entries devuelve entradas en el rango."""
    resp = await client.get("/odoo/entries?from=2026-03-01&to=2026-03-31")
    assert resp.status_code == 200
    assert isinstance(resp.json(), list)
