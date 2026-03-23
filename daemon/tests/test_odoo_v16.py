"""Tests para el cliente Odoo v16 (REST/JSONRPC)."""

import pytest
import httpx
from unittest.mock import AsyncMock, patch, MagicMock

from mimir_daemon.integrations.odoo_v16 import OdooV16Client
from mimir_daemon.integrations.base import TimesheetEntryData

_DUMMY_REQUEST = httpx.Request("POST", "https://odoo16-test.example.com/web/dataset/call_kw")


def _resp(status_code: int = 200, json: dict | None = None) -> httpx.Response:
    """Crea un httpx.Response con request dummy para que raise_for_status funcione."""
    return httpx.Response(status_code, json=json, request=_DUMMY_REQUEST)


@pytest.fixture
def client():
    """Crea un cliente Odoo v16 con credenciales de prueba."""
    return OdooV16Client(
        url="https://odoo16-test.example.com",
        db="testdb",
        token="test-api-key-123",
    )


@pytest.mark.asyncio
async def test_authenticate_rest_api(client):
    """Autenticacion exitosa via REST API."""
    mock_response = httpx.Response(200, json={"uid": 1})
    with patch.object(client._client, "get", return_value=mock_response):
        result = await client.authenticate()
    assert result is True
    assert client._authenticated is True


@pytest.mark.asyncio
async def test_authenticate_jsonrpc_fallback(client):
    """Autenticacion via JSONRPC session si REST falla."""
    rest_resp = httpx.Response(404)
    jsonrpc_resp = httpx.Response(200, json={"result": {"uid": 42}})
    with patch.object(client._client, "get", return_value=rest_resp), \
         patch.object(client._client, "post", return_value=jsonrpc_resp):
        result = await client.authenticate()
    assert result is True


@pytest.mark.asyncio
async def test_authenticate_failure(client):
    """Autenticacion fallida si ambos metodos fallan."""
    rest_resp = httpx.Response(401)
    jsonrpc_resp = httpx.Response(200, json={"result": {}})
    with patch.object(client._client, "get", return_value=rest_resp), \
         patch.object(client._client, "post", return_value=jsonrpc_resp):
        result = await client.authenticate()
    assert result is False


@pytest.mark.asyncio
async def test_authenticate_connection_error(client):
    """Error de conexion devuelve False."""
    with patch.object(client._client, "get", side_effect=httpx.ConnectError("timeout")):
        result = await client.authenticate()
    assert result is False


@pytest.mark.asyncio
async def test_get_projects(client):
    """Obtiene proyectos via JSONRPC."""
    mock_response = _resp(200, json={
        "result": [
            {"id": 1, "name": "Proyecto A"},
            {"id": 2, "name": "Proyecto B"},
        ]
    })
    with patch.object(client._client, "post", return_value=mock_response):
        projects = await client.get_projects()
    assert len(projects) == 2
    assert projects[0] == {"id": 1, "name": "Proyecto A"}


@pytest.mark.asyncio
async def test_get_projects_error(client):
    """Error obteniendo proyectos devuelve lista vacia."""
    with patch.object(client._client, "post", side_effect=Exception("Network error")):
        projects = await client.get_projects()
    assert projects == []


@pytest.mark.asyncio
async def test_get_tasks(client):
    """Obtiene tareas de un proyecto."""
    mock_response = _resp(200, json={
        "result": [
            {"id": 101, "name": "Tarea 1", "project_id": [1, "Proyecto A"], "effective_hours": 4.0},
            {"id": 102, "name": "Tarea 2", "project_id": [1, "Proyecto A"], "effective_hours": 0.0},
        ]
    })
    with patch.object(client._client, "post", return_value=mock_response):
        tasks = await client.get_tasks(1)
    assert len(tasks) == 2
    assert tasks[0] == {"id": 101, "name": "Tarea 1", "project_id": 1, "effective_hours": 4.0}


@pytest.mark.asyncio
async def test_get_tasks_error(client):
    """Error obteniendo tareas devuelve lista vacia."""
    with patch.object(client._client, "post", side_effect=Exception("Timeout")):
        tasks = await client.get_tasks(1)
    assert tasks == []


@pytest.mark.asyncio
async def test_create_entry(client):
    """Crea una entrada de timesheet."""
    mock_response = _resp(200, json={"result": 500})
    entry = TimesheetEntryData(
        date="2026-03-13",
        project_id=1,
        task_id=101,
        description="Desarrollo frontend",
        hours=2.0,
    )
    with patch.object(client._client, "post", return_value=mock_response):
        result = await client.create_entry(entry)
    assert result == 500


@pytest.mark.asyncio
async def test_create_entry_without_task(client):
    """Crea una entrada sin tarea."""
    mock_response = _resp(200, json={"result": 501})
    entry = TimesheetEntryData(
        date="2026-03-13",
        project_id=1,
        task_id=None,
        description="Reunion",
        hours=1.0,
    )
    with patch.object(client._client, "post", return_value=mock_response) as mock_post:
        result = await client.create_entry(entry)
    assert result == 501
    # Verificar que la llamada JSONRPC no incluye task_id
    call_json = mock_post.call_args[1]["json"]
    vals = call_json["params"]["args"][0]
    assert "task_id" not in vals


@pytest.mark.asyncio
async def test_create_entry_jsonrpc_error(client):
    """Error JSONRPC al crear entrada lanza excepcion."""
    mock_response = _resp(200, json={
        "error": {"message": "Access Denied", "data": {"message": "No permission"}}
    })
    entry = TimesheetEntryData(
        date="2026-03-13",
        project_id=1,
        task_id=None,
        description="Test",
        hours=1.0,
    )
    with patch.object(client._client, "post", return_value=mock_response):
        with pytest.raises(RuntimeError, match="Access Denied"):
            await client.create_entry(entry)


@pytest.mark.asyncio
async def test_update_entry(client):
    """Actualiza una entrada existente."""
    mock_response = _resp(200, json={"result": True})
    entry = TimesheetEntryData(
        date="2026-03-13",
        project_id=1,
        task_id=101,
        description="Actualizado",
        hours=3.0,
    )
    with patch.object(client._client, "post", return_value=mock_response):
        await client.update_entry(500, entry)


@pytest.mark.asyncio
async def test_update_entry_error(client):
    """Error actualizando lanza excepcion."""
    entry = TimesheetEntryData(
        date="2026-03-13",
        project_id=1,
        task_id=None,
        description="Test",
        hours=1.0,
    )
    with patch.object(client._client, "post", side_effect=httpx.HTTPStatusError(
        "Server Error", request=MagicMock(), response=httpx.Response(500)
    )):
        with pytest.raises(Exception):
            await client.update_entry(500, entry)


@pytest.mark.asyncio
async def test_get_entries(client):
    """Obtiene entradas en un rango."""
    mock_response = _resp(200, json={
        "result": [
            {
                "id": 100,
                "date": "2026-03-13",
                "project_id": [1, "Proyecto A"],
                "task_id": [101, "Tarea 1"],
                "name": "Desarrollo",
                "unit_amount": 2.5,
                "employee_id": [1, "Admin"],
            },
        ]
    })
    with patch.object(client._client, "post", return_value=mock_response):
        entries = await client.get_entries("2026-03-01", "2026-03-31")
    assert len(entries) == 1
    assert entries[0]["project_id"] == 1
    assert entries[0]["project_name"] == "Proyecto A"
    assert entries[0]["task_id"] == 101
    assert entries[0]["hours"] == 2.5


@pytest.mark.asyncio
async def test_get_entries_empty(client):
    """Obtiene lista vacia si no hay entradas."""
    mock_response = _resp(200, json={"result": []})
    with patch.object(client._client, "post", return_value=mock_response):
        entries = await client.get_entries("2026-03-01", "2026-03-31")
    assert entries == []


@pytest.mark.asyncio
async def test_get_entries_error(client):
    """Error obteniendo entradas devuelve lista vacia."""
    with patch.object(client._client, "post", side_effect=Exception("Timeout")):
        entries = await client.get_entries("2026-03-01", "2026-03-31")
    assert entries == []


@pytest.mark.asyncio
async def test_get_entries_null_result(client):
    """Resultado null del JSONRPC devuelve lista vacia."""
    mock_response = _resp(200, json={"result": None})
    with patch.object(client._client, "post", return_value=mock_response):
        entries = await client.get_entries("2026-03-01", "2026-03-31")
    assert entries == []


@pytest.mark.asyncio
async def test_get_today_attendance_uses_timezone(client):
    """get_today_attendance usa la zona horaria configurada."""
    client._employee_id = 1
    mock_response = _resp(200, json={
        "result": [
            {
                "id": 10,
                "check_in": "2026-03-17 07:00:00",
                "check_out": False,
                "employee_id": [1, "Admin"],
            },
        ]
    })
    with patch.object(client._client, "post", return_value=mock_response):
        result = await client.get_today_attendance()
    assert result is not None
    assert result["id"] == 10
    assert result["check_in"].endswith("Z")


@pytest.mark.asyncio
async def test_get_today_attendance_custom_timezone():
    """get_today_attendance respeta timezone personalizada."""
    custom_client = OdooV16Client(
        url="https://odoo16-test.example.com",
        db="testdb",
        token="test-api-key-123",
        timezone="America/New_York",
    )
    custom_client._employee_id = 1
    assert custom_client._timezone == "America/New_York"
    mock_response = _resp(200, json={"result": []})
    with patch.object(custom_client._client, "post", return_value=mock_response):
        result = await custom_client.get_today_attendance()
    assert result is None


@pytest.mark.asyncio
async def test_get_today_attendance_error(client):
    """Error obteniendo attendance devuelve None."""
    client._employee_id = 1
    with patch.object(client._client, "post", side_effect=Exception("Timeout")):
        result = await client.get_today_attendance()
    assert result is None


@pytest.mark.asyncio
async def test_close(client):
    """Cierra el cliente HTTP."""
    with patch.object(client._client, "aclose") as mock_close:
        await client.close()
    mock_close.assert_called_once()
