"""Tests para el cliente Odoo v11 (XMLRPC)."""

import pytest
from unittest.mock import patch, AsyncMock

from mimir_daemon.integrations.odoo_v11 import OdooV11Client
from mimir_daemon.integrations.base import TimesheetEntryData


@pytest.fixture
def client():
    """Crea un cliente Odoo v11 con credenciales de prueba."""
    return OdooV11Client(
        url="https://odoo-test.example.com",
        db="testdb",
        username="admin",
        password="admin-pass",
    )


@pytest.mark.asyncio
async def test_authenticate_success(client):
    """Autenticacion exitosa devuelve True y establece uid."""
    with patch.object(client, "_authenticate_sync", return_value=42):
        result = await client.authenticate()
    assert result is True
    assert client._uid == 42


@pytest.mark.asyncio
async def test_authenticate_failure(client):
    """Autenticacion fallida devuelve False."""
    with patch.object(client, "_authenticate_sync", return_value=None):
        result = await client.authenticate()
    assert result is False
    assert client._uid is None


@pytest.mark.asyncio
async def test_authenticate_connection_error(client):
    """Error de conexion devuelve False sin crash."""
    with patch.object(client, "_authenticate_sync", side_effect=ConnectionError("timeout")):
        result = await client.authenticate()
    assert result is False


@pytest.mark.asyncio
async def test_get_projects(client):
    """Obtiene proyectos correctamente."""
    mock_result = [
        {"id": 1, "name": "Proyecto A"},
        {"id": 2, "name": "Proyecto B"},
    ]
    with patch.object(client, "_execute", new_callable=AsyncMock, return_value=mock_result):
        projects = await client.get_projects()
    assert len(projects) == 2
    assert projects[0] == {"id": 1, "name": "Proyecto A"}
    assert projects[1] == {"id": 2, "name": "Proyecto B"}


@pytest.mark.asyncio
async def test_get_projects_error(client):
    """Error obteniendo proyectos devuelve lista vacia."""
    with patch.object(client, "_execute", new_callable=AsyncMock, side_effect=Exception("XMLRPC error")):
        projects = await client.get_projects()
    assert projects == []


@pytest.mark.asyncio
async def test_get_tasks(client):
    """Obtiene tareas de un proyecto."""
    mock_result = [
        {"id": 101, "name": "Tarea 1", "project_id": [1, "Proyecto A"], "effective_hours": 4.0},
        {"id": 102, "name": "Tarea 2", "project_id": [1, "Proyecto A"], "effective_hours": 0.0},
    ]
    with patch.object(client, "_execute", new_callable=AsyncMock, return_value=mock_result):
        tasks = await client.get_tasks(1)
    assert len(tasks) == 2
    assert tasks[0] == {"id": 101, "name": "Tarea 1", "project_id": 1, "effective_hours": 4.0}


@pytest.mark.asyncio
async def test_get_tasks_error(client):
    """Error obteniendo tareas devuelve lista vacia."""
    with patch.object(client, "_execute", new_callable=AsyncMock, side_effect=Exception("Network error")):
        tasks = await client.get_tasks(1)
    assert tasks == []


@pytest.mark.asyncio
async def test_create_entry(client):
    """Crea una entrada de timesheet."""
    entry = TimesheetEntryData(
        date="2026-03-13",
        project_id=1,
        task_id=101,
        description="Desarrollo daemon",
        hours=2.5,
    )
    with patch.object(client, "_execute", new_callable=AsyncMock, return_value=500):
        result = await client.create_entry(entry)
    assert result == 500


@pytest.mark.asyncio
async def test_create_entry_without_task(client):
    """Crea una entrada sin tarea."""
    entry = TimesheetEntryData(
        date="2026-03-13",
        project_id=1,
        task_id=None,
        description="Reunion",
        hours=1.0,
    )
    mock_exec = AsyncMock(return_value=501)
    with patch.object(client, "_execute", mock_exec):
        result = await client.create_entry(entry)
    assert result == 501
    # Verificar que no se envio task_id en los valores
    call_args = mock_exec.call_args
    vals = call_args[0][2]  # tercer argumento posicional: [vals]
    assert "task_id" not in vals[0]


@pytest.mark.asyncio
async def test_create_entry_error(client):
    """Error creando entrada lanza excepcion."""
    entry = TimesheetEntryData(
        date="2026-03-13",
        project_id=1,
        task_id=None,
        description="Test",
        hours=1.0,
    )
    with patch.object(client, "_execute", new_callable=AsyncMock, side_effect=Exception("Server error")):
        with pytest.raises(Exception, match="Server error"):
            await client.create_entry(entry)


@pytest.mark.asyncio
async def test_update_entry(client):
    """Actualiza una entrada existente."""
    entry = TimesheetEntryData(
        date="2026-03-13",
        project_id=1,
        task_id=101,
        description="Actualizado",
        hours=3.0,
    )
    with patch.object(client, "_execute", new_callable=AsyncMock, return_value=True):
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
    with patch.object(client, "_execute", new_callable=AsyncMock, side_effect=Exception("Write failed")):
        with pytest.raises(Exception, match="Write failed"):
            await client.update_entry(500, entry)


@pytest.mark.asyncio
async def test_get_entries(client):
    """Obtiene entradas en un rango."""
    mock_result = [
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
    with patch.object(client, "_execute", new_callable=AsyncMock, return_value=mock_result):
        entries = await client.get_entries("2026-03-01", "2026-03-31")
    assert len(entries) == 1
    assert entries[0]["project_id"] == 1
    assert entries[0]["project_name"] == "Proyecto A"
    assert entries[0]["task_id"] == 101
    assert entries[0]["hours"] == 2.5


@pytest.mark.asyncio
async def test_get_entries_with_employee_filter(client):
    """Obtiene entradas filtradas por empleado."""
    mock_exec = AsyncMock(return_value=[])
    with patch.object(client, "_execute", mock_exec):
        await client.get_entries("2026-03-01", "2026-03-31", employee_id=42)
    call_args = mock_exec.call_args
    domain = call_args[0][2]  # tercer argumento: [domain]
    assert ("employee_id", "=", 42) in domain[0]


@pytest.mark.asyncio
async def test_get_entries_error(client):
    """Error obteniendo entradas devuelve lista vacia."""
    with patch.object(client, "_execute", new_callable=AsyncMock, side_effect=Exception("Timeout")):
        entries = await client.get_entries("2026-03-01", "2026-03-31")
    assert entries == []


@pytest.mark.asyncio
async def test_get_today_attendance_uses_timezone(client):
    """get_today_attendance usa la zona horaria configurada."""
    client._employee_id = 1
    mock_result = [
        {
            "id": 10,
            "check_in": "2026-03-17 07:00:00",
            "check_out": False,
            "employee_id": [1, "Admin"],
        },
    ]
    with patch.object(client, "_execute", new_callable=AsyncMock, return_value=mock_result):
        result = await client.get_today_attendance()
    assert result is not None
    assert result["id"] == 10
    assert result["check_in"].endswith("Z")


@pytest.mark.asyncio
async def test_get_today_attendance_custom_timezone():
    """get_today_attendance respeta timezone personalizada."""
    custom_client = OdooV11Client(
        url="https://odoo-test.example.com",
        db="testdb",
        username="admin",
        password="admin-pass",
        timezone="America/New_York",
    )
    custom_client._employee_id = 1
    assert custom_client._timezone == "America/New_York"
    with patch.object(custom_client, "_execute", new_callable=AsyncMock, return_value=[]):
        result = await custom_client.get_today_attendance()
    assert result is None


@pytest.mark.asyncio
async def test_get_today_attendance_error(client):
    """Error obteniendo attendance devuelve None."""
    client._employee_id = 1
    with patch.object(client, "_execute", new_callable=AsyncMock, side_effect=Exception("Timeout")):
        result = await client.get_today_attendance()
    assert result is None
