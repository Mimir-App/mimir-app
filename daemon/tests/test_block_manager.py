"""Tests para BlockManager."""

import pytest
import pytest_asyncio
import asyncio
from datetime import datetime, timezone

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
    """BlockManager con threshold bajo para tests."""
    return BlockManager(db=db, inherit_threshold=5)


@pytest.mark.asyncio
async def test_create_block_on_first_poll(manager, db):
    """Un primer poll crea un bloque nuevo."""
    window = WindowInfo(pid=1234, app_name="code", window_title="main.py - VSCode")
    context = EnrichedContext(cwd="/home/user/project", git_branch="main")

    await manager.process_poll(window, context)

    blocks = await db.get_blocks_by_date(datetime.now(timezone.utc).strftime("%Y-%m-%d"))
    assert len(blocks) == 1
    assert blocks[0]["app_name"] == "code"


@pytest.mark.asyncio
async def test_no_block_on_locked(manager, db):
    """No crea bloque si la sesión está bloqueada."""
    context = EnrichedContext()
    await manager.process_poll(None, context, is_locked=True)

    blocks = await db.get_blocks_by_date(datetime.now(timezone.utc).strftime("%Y-%m-%d"))
    assert len(blocks) == 0


@pytest.mark.asyncio
async def test_inherits_context_within_threshold(manager, db):
    """Polls consecutivos actualizan el mismo bloque."""
    window = WindowInfo(pid=1234, app_name="code", window_title="main.py")
    context = EnrichedContext(cwd="/project", git_branch="feature")

    await manager.process_poll(window, context)
    await manager.process_poll(window, context)

    blocks = await db.get_blocks_by_date(datetime.now(timezone.utc).strftime("%Y-%m-%d"))
    assert len(blocks) == 1


@pytest.mark.asyncio
async def test_handle_lock_closes_block(manager, db):
    """Lock cierra el bloque activo."""
    window = WindowInfo(pid=1234, app_name="code", window_title="main.py")
    context = EnrichedContext()

    await manager.process_poll(window, context)
    await manager.handle_lock()

    assert manager._current_block_id is None
