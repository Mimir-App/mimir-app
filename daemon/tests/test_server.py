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
    from mimir_daemon.ai.service import AIService
    config = DaemonConfig(polling_interval=60)
    platform = MockPlatform()
    block_manager = BlockManager(db=db)
    poller = Poller(config=config, db=db, platform=platform, block_manager=block_manager)
    ai_service = AIService(db=db, provider=None)
    return create_app(db=db, poller=poller, registry=registry, ai_service=ai_service)


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
async def test_sync_blocks_update_existing(client, db):
    """POST /blocks/sync actualiza bloques que ya tienen odoo_entry_id."""
    now = datetime.now(timezone.utc).isoformat()
    block_id = await db.create_block(
        start_time=now, end_time=now, duration_minutes=60,
        app_name="code", status="confirmed",
    )
    # Simular que ya fue sincronizado previamente
    await db.update_block(block_id, odoo_project_id=1, odoo_task_id=101,
                          user_description="Desarrollo daemon",
                          odoo_entry_id=999)

    resp = await client.post("/blocks/sync", json={"block_ids": [block_id]})
    assert resp.status_code == 200
    data = resp.json()
    assert data["synced"] == 1

    block = await db.get_block_by_id(block_id)
    assert block["status"] == "synced"
    assert block["odoo_entry_id"] == 999  # Mantiene el remote_id existente


@pytest.mark.asyncio
async def test_confirm_block_already_synced(client, db):
    """POST /blocks/{id}/confirm rechaza bloques ya sincronizados."""
    now = datetime.now(timezone.utc).isoformat()
    block_id = await db.create_block(
        start_time=now, end_time=now, duration_minutes=0,
        app_name="code", status="synced",
    )
    resp = await client.post(f"/blocks/{block_id}/confirm")
    assert resp.status_code == 400


@pytest.mark.asyncio
async def test_update_synced_block_resets_status(client, db):
    """PUT /blocks/{id} marca bloques synced como confirmed para reenvio."""
    now = datetime.now(timezone.utc).isoformat()
    block_id = await db.create_block(
        start_time=now, end_time=now, duration_minutes=30,
        app_name="code", status="synced",
    )
    await db.update_block(block_id, odoo_entry_id=999)

    resp = await client.put(
        f"/blocks/{block_id}",
        json={"user_description": "Actualizado tras sync"},
    )
    assert resp.status_code == 200

    block = await db.get_block_by_id(block_id)
    assert block["status"] == "confirmed"
    assert block["user_description"] == "Actualizado tras sync"


@pytest.mark.asyncio
async def test_retry_sync_success(client, db):
    """POST /blocks/{id}/retry reintenta sync exitosamente."""
    now = datetime.now(timezone.utc).isoformat()
    block_id = await db.create_block(
        start_time=now, end_time=now, duration_minutes=45,
        app_name="code", status="error",
    )
    await db.update_block(block_id, odoo_project_id=1, odoo_task_id=101,
                          user_description="Desarrollo",
                          sync_error="Timeout previo")

    resp = await client.post(f"/blocks/{block_id}/retry")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "synced"

    block = await db.get_block_by_id(block_id)
    assert block["status"] == "synced"
    assert block["sync_error"] is None
    assert block["odoo_entry_id"] is not None


@pytest.mark.asyncio
async def test_retry_sync_not_error_status(client, db):
    """POST /blocks/{id}/retry rechaza bloques que no estan en error."""
    now = datetime.now(timezone.utc).isoformat()
    block_id = await db.create_block(
        start_time=now, end_time=now, duration_minutes=30,
        app_name="code", status="confirmed",
    )
    resp = await client.post(f"/blocks/{block_id}/retry")
    assert resp.status_code == 400


@pytest.mark.asyncio
async def test_retry_sync_no_project(client, db):
    """POST /blocks/{id}/retry falla si no tiene proyecto."""
    now = datetime.now(timezone.utc).isoformat()
    block_id = await db.create_block(
        start_time=now, end_time=now, duration_minutes=30,
        app_name="code", status="error",
    )
    resp = await client.post(f"/blocks/{block_id}/retry")
    assert resp.status_code == 400


@pytest.mark.asyncio
async def test_retry_sync_not_found(client):
    """POST /blocks/{id}/retry devuelve 404 si no existe."""
    resp = await client.post("/blocks/9999/retry")
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_sync_blocks_no_client(db):
    """POST /blocks/sync devuelve 503 sin cliente de timesheet."""
    config = DaemonConfig(polling_interval=60)
    platform = MockPlatform()
    block_manager = BlockManager(db=db)
    poller = Poller(config=config, db=db, platform=platform, block_manager=block_manager)
    app = create_app(db=db, poller=poller, registry=None)

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        resp = await c.post("/blocks/sync", json={"block_ids": [1]})
        assert resp.status_code == 503


@pytest.mark.asyncio
async def test_get_odoo_entries(client):
    """GET /odoo/entries devuelve entradas en el rango."""
    resp = await client.get("/odoo/entries?from=2026-03-01&to=2026-03-31")
    assert resp.status_code == 200
    assert isinstance(resp.json(), list)


# --- Config endpoints ---


@pytest.mark.asyncio
async def test_get_config_empty(client):
    """GET /config devuelve config vacia al inicio."""
    resp = await client.get("/config")
    assert resp.status_code == 200
    data = resp.json()
    assert "odoo_configured" in data
    assert "gitlab_configured" in data
    assert data["odoo_configured"] is False


@pytest.mark.asyncio
async def test_put_config(client):
    """PUT /config acepta configuracion y la almacena."""
    resp = await client.put("/config", json={
        "odoo_url": "",
        "odoo_version": "v16",
        "odoo_db": "test",
        "odoo_username": "admin",
        "odoo_token": "",
        "gitlab_url": "https://gitlab.example.com",
        "gitlab_token": "",
    })
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "ok"

    # Verificar que se guardo
    resp2 = await client.get("/config")
    data2 = resp2.json()
    assert data2.get("odoo_db") == "test"
    assert data2["gitlab_configured"] is False  # sin token


@pytest.mark.asyncio
async def test_put_config_no_tokens_in_get(client):
    """GET /config no expone tokens."""
    await client.put("/config", json={
        "odoo_url": "https://odoo.test.com",
        "odoo_version": "v16",
        "odoo_db": "testdb",
        "odoo_username": "user",
        "odoo_token": "secret-token-123",
        "gitlab_url": "https://gitlab.test.com",
        "gitlab_token": "glpat-secret",
    })

    resp = await client.get("/config")
    data = resp.json()
    # Los campos con 'token' no deben estar presentes
    assert "odoo_token" not in data
    assert "gitlab_token" not in data
    # Pero los flags de configuracion si
    assert data["odoo_configured"] is True
    assert data["gitlab_configured"] is True


@pytest.mark.asyncio
async def test_get_integration_status(client):
    """GET /config/integration-status devuelve estado de integraciones."""
    resp = await client.get("/config/integration-status")
    assert resp.status_code == 200
    data = resp.json()
    assert "odoo" in data
    # Con registry mock, odoo esta configurado
    assert data["odoo"]["configured"] is True
    assert data["odoo"]["client_type"] == "MockTimesheetClient"


@pytest.mark.asyncio
async def test_get_integration_status_no_client():
    """GET /config/integration-status sin cliente configurado."""
    db = Database(":memory:")
    await db.connect()
    config = DaemonConfig(polling_interval=60)
    platform = MockPlatform()
    block_manager = BlockManager(db=db)
    poller = Poller(config=config, db=db, platform=platform, block_manager=block_manager)
    # Sin registry -- no hay cliente de timesheet
    app = create_app(db=db, poller=poller, registry=None)

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        resp = await c.get("/config/integration-status")
        assert resp.status_code == 200
        data = resp.json()
        assert data["odoo"]["configured"] is False
        assert data["odoo"]["client_type"] is None

    await db.close()


@pytest.mark.asyncio
async def test_generate_description_endpoint(client, db):
    """POST /blocks/{id}/generate-description genera descripción IA."""
    now = datetime.now(timezone.utc).isoformat()
    block_id = await db.create_block(
        start_time=now, end_time=now, duration_minutes=30,
        app_name="code", window_title="models.py — VS Code",
        project_path="/home/user/project", git_branch="feat/ai",
        status="closed",
    )
    resp = await client.post(f"/blocks/{block_id}/generate-description")
    assert resp.status_code == 200
    data = resp.json()
    assert "description" in data
    assert "confidence" in data

    block = await db.get_block_by_id(block_id)
    assert block["ai_description"] is not None


@pytest.mark.asyncio
async def test_generate_description_block_not_found(client):
    """POST /blocks/{id}/generate-description devuelve 404."""
    resp = await client.post("/blocks/9999/generate-description")
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_put_config_ai_provider(client):
    """PUT /config con ai_provider configura el servicio IA."""
    resp = await client.put("/config", json={
        "odoo_url": "",
        "odoo_version": "v16",
        "odoo_db": "",
        "odoo_username": "",
        "odoo_token": "",
        "gitlab_url": "",
        "gitlab_token": "",
        "ai_provider": "none",
        "ai_api_key": "",
        "ai_user_role": "technical",
        "ai_custom_context": "Desarrollo backend en Python",
    })
    assert resp.status_code == 200


@pytest.mark.asyncio
async def test_config_no_ai_key_exposed(client):
    """GET /config no expone ai_api_key."""
    await client.put("/config", json={
        "odoo_url": "",
        "odoo_version": "v16",
        "odoo_db": "",
        "odoo_username": "",
        "odoo_token": "",
        "gitlab_url": "",
        "gitlab_token": "",
        "ai_provider": "gemini",
        "ai_api_key": "secret-ai-key",
        "ai_user_role": "functional",
        "ai_custom_context": "",
    })
    resp = await client.get("/config")
    data = resp.json()
    assert "ai_api_key" not in data
    assert data.get("ai_provider") == "gemini"
    assert data.get("ai_user_role") == "functional"
    assert data.get("ai_configured") is True
