"""Tests para BlockManager."""

import asyncio
from datetime import datetime, timezone, timedelta

import pytest
import pytest_asyncio

from mimir_daemon.db import Database
from mimir_daemon.block_manager import BlockManager
from mimir_daemon.platform.base import WindowInfo
from mimir_daemon.context_enricher import EnrichedContext


@pytest_asyncio.fixture
async def db(tmp_path):
    """Base de datos temporal para tests."""
    database = Database(str(tmp_path / "test.db"))
    await database.connect()
    yield database
    await database.close()


@pytest_asyncio.fixture
async def manager(db):
    """BlockManager con threshold bajo para tests (5 segundos)."""
    return BlockManager(db=db, inherit_threshold=5)


# --- Creacion de bloques ---


@pytest.mark.asyncio
async def test_create_block_on_first_poll(manager, db):
    """Un primer poll crea un bloque nuevo."""
    window = WindowInfo(pid=1234, app_name="code", window_title="main.py - VSCode")
    context = EnrichedContext(cwd="/home/user/project", git_branch="main")

    await manager.process_poll(window, context)

    blocks = await db.get_blocks_by_date(
        datetime.now(timezone.utc).strftime("%Y-%m-%d")
    )
    assert len(blocks) == 1
    assert blocks[0]["app_name"] == "code"
    assert blocks[0]["git_branch"] == "main"
    assert blocks[0]["status"] == "auto"


@pytest.mark.asyncio
async def test_no_block_on_locked(manager, db):
    """No crea bloque si la sesion esta bloqueada."""
    context = EnrichedContext()
    await manager.process_poll(None, context, is_locked=True)

    blocks = await db.get_blocks_by_date(
        datetime.now(timezone.utc).strftime("%Y-%m-%d")
    )
    assert len(blocks) == 0


@pytest.mark.asyncio
async def test_no_block_on_no_window(manager, db):
    """No crea bloque si no hay ventana activa."""
    context = EnrichedContext()
    await manager.process_poll(None, context)

    blocks = await db.get_blocks_by_date(
        datetime.now(timezone.utc).strftime("%Y-%m-%d")
    )
    assert len(blocks) == 0


# --- Herencia de contexto ---


@pytest.mark.asyncio
async def test_inherits_context_within_threshold(manager, db):
    """Polls consecutivos actualizan el mismo bloque."""
    window = WindowInfo(pid=1234, app_name="code", window_title="main.py")
    context = EnrichedContext(cwd="/project", git_branch="feature")

    await manager.process_poll(window, context)
    await manager.process_poll(window, context)
    await manager.process_poll(window, context)

    blocks = await db.get_blocks_by_date(
        datetime.now(timezone.utc).strftime("%Y-%m-%d")
    )
    assert len(blocks) == 1


@pytest.mark.asyncio
async def test_updates_duration(manager, db):
    """La duracion se actualiza con cada poll."""
    window = WindowInfo(pid=1234, app_name="code", window_title="main.py")
    context = EnrichedContext()

    await manager.process_poll(window, context)

    # Segundo poll inmediato
    await manager.process_poll(window, context)

    blocks = await db.get_blocks_by_date(
        datetime.now(timezone.utc).strftime("%Y-%m-%d")
    )
    assert len(blocks) == 1
    assert blocks[0]["duration_minutes"] >= 0


# --- Deteccion de cambio de contexto ---


@pytest.mark.asyncio
async def test_new_block_on_app_change(manager, db):
    """Cambio de app crea un bloque nuevo."""
    ctx = EnrichedContext()

    await manager.process_poll(
        WindowInfo(pid=1, app_name="code", window_title="A"), ctx
    )
    await manager.process_poll(
        WindowInfo(pid=2, app_name="firefox", window_title="B"), ctx
    )

    blocks = await db.get_blocks_by_date(
        datetime.now(timezone.utc).strftime("%Y-%m-%d")
    )
    assert len(blocks) == 2
    assert blocks[0]["app_name"] == "code"
    assert blocks[1]["app_name"] == "firefox"


@pytest.mark.asyncio
async def test_new_block_on_project_change(manager, db):
    """Cambio de proyecto crea un bloque nuevo."""
    window = WindowInfo(pid=1, app_name="code", window_title="file.py")

    await manager.process_poll(
        window, EnrichedContext(project_path="/project-a")
    )
    await manager.process_poll(
        window, EnrichedContext(project_path="/project-b")
    )

    blocks = await db.get_blocks_by_date(
        datetime.now(timezone.utc).strftime("%Y-%m-%d")
    )
    assert len(blocks) == 2


# --- Lock / Unlock ---


@pytest.mark.asyncio
async def test_handle_lock_closes_block(manager, db):
    """Lock cierra el bloque activo."""
    window = WindowInfo(pid=1234, app_name="code", window_title="main.py")
    context = EnrichedContext()

    await manager.process_poll(window, context)
    assert manager._current_block_id is not None

    await manager.handle_lock()
    assert manager._current_block_id is None

    # Verificar que el bloque se marco como cerrado
    blocks = await db.get_blocks_by_date(
        datetime.now(timezone.utc).strftime("%Y-%m-%d")
    )
    assert blocks[0]["status"] == "closed"


@pytest.mark.asyncio
async def test_unlock_allows_new_block(manager, db):
    """Unlock permite crear nuevo bloque."""
    window = WindowInfo(pid=1234, app_name="code", window_title="main.py")
    context = EnrichedContext()

    await manager.process_poll(window, context)
    await manager.handle_lock()
    await manager.handle_unlock()
    await manager.process_poll(window, context)

    blocks = await db.get_blocks_by_date(
        datetime.now(timezone.utc).strftime("%Y-%m-%d")
    )
    assert len(blocks) == 2


# --- Recuperacion de bloques ---


@pytest.mark.asyncio
async def test_recover_closes_old_blocks(db):
    """Bloques abiertos viejos se cierran al recuperar."""
    old_time = (
        datetime.now(timezone.utc) - timedelta(hours=2)
    ).isoformat()
    await db.create_block(
        start_time=old_time,
        end_time=old_time,
        duration_minutes=0,
        app_name="code",
        status="auto",
    )

    manager = BlockManager(db=db, inherit_threshold=5)
    await manager.recover_open_blocks()

    assert manager._current_block_id is None
    blocks = await db.get_open_blocks()
    assert len(blocks) == 0


@pytest.mark.asyncio
async def test_recover_continues_recent_block(db):
    """Bloques abiertos recientes se retoman."""
    recent_time = datetime.now(timezone.utc).isoformat()
    block_id = await db.create_block(
        start_time=recent_time,
        end_time=recent_time,
        duration_minutes=0,
        app_name="code",
        status="auto",
    )

    manager = BlockManager(db=db, inherit_threshold=5)
    await manager.recover_open_blocks()

    assert manager._current_block_id == block_id
