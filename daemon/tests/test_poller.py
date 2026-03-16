"""Tests end-to-end del poller con plataforma mock."""

import asyncio
from datetime import datetime, timezone

import pytest
import pytest_asyncio

from mimir_daemon.db import Database
from mimir_daemon.config import DaemonConfig
from mimir_daemon.platform.base import PlatformProvider, WindowInfo, SessionEvent
from mimir_daemon.signal_aggregator import SignalAggregator
from mimir_daemon.poller import Poller


class FakePlatform(PlatformProvider):
    """Plataforma fake que simula ventanas activas."""

    def __init__(self) -> None:
        self.windows: list[WindowInfo | None] = []
        self.events: list[SessionEvent] = []
        self._call_count = 0

    async def get_active_window(self) -> WindowInfo | None:
        if self._call_count < len(self.windows):
            w = self.windows[self._call_count]
            self._call_count += 1
            return w
        return self.windows[-1] if self.windows else None

    async def get_session_events(self) -> list[SessionEvent]:
        events = self.events.copy()
        self.events.clear()
        return events


@pytest_asyncio.fixture
async def db(tmp_path):
    database = Database(str(tmp_path / "test.db"))
    await database.connect()
    yield database
    await database.close()


@pytest.mark.asyncio
async def test_poller_creates_blocks(db):
    """El poller crea bloques cuando hay ventana activa."""
    platform = FakePlatform()
    platform.windows = [
        WindowInfo(pid=100, app_name="code", window_title="file.py - VSCode"),
        WindowInfo(pid=100, app_name="code", window_title="file.py - VSCode"),
        WindowInfo(pid=100, app_name="code", window_title="file.py - VSCode"),
    ]

    config = DaemonConfig(polling_interval=0)
    agg = SignalAggregator(db=db, inactivity_threshold=900)
    poller = Poller(config=config, db=db, platform=platform, aggregator=agg)

    for _ in range(3):
        await poller._poll_once()

    blocks = await db.get_blocks_by_date(
        datetime.now(timezone.utc).strftime("%Y-%m-%d")
    )
    assert len(blocks) == 1
    assert blocks[0]["app_name"] == "code"
    assert blocks[0]["duration_minutes"] >= 0


@pytest.mark.asyncio
async def test_poller_no_block_without_window(db):
    """El poller no crea bloques sin ventana activa."""
    platform = FakePlatform()
    platform.windows = [None, None]

    config = DaemonConfig(polling_interval=0)
    agg = SignalAggregator(db=db, inactivity_threshold=900)
    poller = Poller(config=config, db=db, platform=platform, aggregator=agg)

    await poller._poll_once()
    await poller._poll_once()

    blocks = await db.get_blocks_by_date(
        datetime.now(timezone.utc).strftime("%Y-%m-%d")
    )
    assert len(blocks) == 0


@pytest.mark.asyncio
async def test_poller_handles_lock_event(db):
    """El poller cierra bloque al recibir evento lock."""
    platform = FakePlatform()
    platform.windows = [
        WindowInfo(pid=100, app_name="code", window_title="file.py"),
        None,
    ]

    config = DaemonConfig(polling_interval=0)
    agg = SignalAggregator(db=db, inactivity_threshold=900)
    poller = Poller(config=config, db=db, platform=platform, aggregator=agg)

    # Primer poll: crea bloque
    await poller._poll_once()
    assert agg._current_block_id is not None

    # Inyectar evento lock y hacer poll
    platform.events = [
        SessionEvent(
            event_type="lock",
            timestamp=datetime.now(timezone.utc).isoformat(),
        )
    ]
    await poller._poll_once()
    assert agg._current_block_id is None


@pytest.mark.asyncio
async def test_poller_pause_resume(db):
    """El poller no captura mientras esta pausado."""
    platform = FakePlatform()
    platform.windows = [
        WindowInfo(pid=100, app_name="code", window_title="file.py"),
    ]

    config = DaemonConfig(polling_interval=0)
    agg = SignalAggregator(db=db, inactivity_threshold=900)
    poller = Poller(config=config, db=db, platform=platform, aggregator=agg)

    poller.pause()
    assert poller._paused

    poller.resume()
    assert not poller._paused


@pytest.mark.asyncio
async def test_poller_run_loop_stops(db):
    """El poller se detiene correctamente."""
    platform = FakePlatform()
    platform.windows = [None]

    config = DaemonConfig(polling_interval=1)
    agg = SignalAggregator(db=db, inactivity_threshold=900)
    poller = Poller(config=config, db=db, platform=platform, aggregator=agg)

    task = asyncio.create_task(poller.run())
    await asyncio.sleep(0.1)
    poller.stop()
    await asyncio.sleep(0.1)
    task.cancel()
    try:
        await task
    except asyncio.CancelledError:
        pass

    assert not poller.is_running


@pytest.mark.asyncio
async def test_poller_context_change_creates_new_block(db):
    """Cambio de app durante polls consecutivos crea bloque nuevo."""
    platform = FakePlatform()
    platform.windows = [
        WindowInfo(pid=100, app_name="code", window_title="file.py"),
        WindowInfo(pid=200, app_name="slack", window_title="General"),
    ]

    config = DaemonConfig(polling_interval=0)
    agg = SignalAggregator(db=db, inactivity_threshold=900)
    poller = Poller(config=config, db=db, platform=platform, aggregator=agg)

    await poller._poll_once()
    await poller._poll_once()

    blocks = await db.get_blocks_by_date(
        datetime.now(timezone.utc).strftime("%Y-%m-%d")
    )
    assert len(blocks) == 2
    assert blocks[0]["app_name"] == "code"
    assert blocks[1]["app_name"] == "slack"


@pytest.mark.asyncio
async def test_poller_creates_signals(db):
    """El poller guarda senales en la tabla signals."""
    platform = FakePlatform()
    platform.windows = [
        WindowInfo(pid=100, app_name="code", window_title="main.py"),
        WindowInfo(pid=100, app_name="code", window_title="test.py"),
    ]

    config = DaemonConfig(polling_interval=0)
    agg = SignalAggregator(db=db, inactivity_threshold=900)
    poller = Poller(config=config, db=db, platform=platform, aggregator=agg)

    await poller._poll_once()
    await poller._poll_once()

    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    signals = await db.get_signals_by_date(today)
    assert len(signals) == 2
    assert signals[0]["app_name"] == "code"
    assert signals[0]["context_key"] is not None
