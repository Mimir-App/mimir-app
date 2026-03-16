"""Tests para el SignalAggregator."""

import pytest
from unittest.mock import AsyncMock, Mock
from datetime import datetime, timezone, timedelta

from mimir_daemon.signal_aggregator import (
    SignalAggregator,
    extract_browser_site,
    compute_context_key,
)


# --- Tests de extraccion de dominio ---

def test_extract_browser_site_chrome_standard():
    assert extract_browser_site("PR #42 — GitHub — Google Chrome", "chrome") == "GitHub"

def test_extract_browser_site_firefox():
    assert extract_browser_site("Inbox - Gmail — Mozilla Firefox", "firefox") == "Gmail"

def test_extract_browser_site_dash_separator():
    assert extract_browser_site("How to fix - Stack Overflow — Google Chrome", "chrome") == "Stack Overflow"

def test_extract_browser_site_no_separator():
    assert extract_browser_site("Stack Overflow", "chrome") == "Stack Overflow"

def test_extract_browser_site_empty():
    assert extract_browser_site("", "chrome") == ""

def test_extract_browser_site_only_browser_name():
    assert extract_browser_site("Google Chrome", "chrome") == ""

def test_extract_browser_site_unknown_browser():
    assert extract_browser_site("Page - Site — Unknown Browser", "unknown") == "Unknown Browser"


# --- Tests de compute_context_key ---

def test_context_key_git_project():
    assert compute_context_key("code", "main.py", "/home/user/project") == "git:/home/user/project"

def test_context_key_browser():
    assert compute_context_key("chrome", "PR — GitHub — Google Chrome", None) == "web:GitHub"

def test_context_key_app():
    assert compute_context_key("slack", "Channel", None) == "app:slack"

def test_context_key_git_overrides_browser():
    """Git project tiene prioridad sobre deteccion de navegador."""
    assert compute_context_key("chrome", "GitHub — Google Chrome", "/project") == "git:/project"

def test_context_key_unknown_app():
    assert compute_context_key(None, None, None) == "app:unknown"


# --- Tests del aggregator ---

@pytest.fixture
def mock_db():
    db = AsyncMock()
    db.create_block = AsyncMock(return_value=1)
    db.update_block = AsyncMock()
    db.link_signal_to_block = AsyncMock()
    db.get_open_blocks = AsyncMock(return_value=[])
    db.get_block_by_id = AsyncMock(return_value=None)
    db.get_signals_by_block = AsyncMock(return_value=[])
    return db


def _signal(id: int, timestamp: str, app: str = "code", context: str = "git:/project", **kw) -> dict:
    """Helper para crear senales de test."""
    return {
        "id": id, "timestamp": timestamp,
        "app_name": app, "window_title": kw.get("title", ""),
        "project_path": kw.get("project", None),
        "git_branch": None, "git_remote": None,
        "context_key": context,
    }


@pytest.mark.asyncio
async def test_first_signal_creates_block(mock_db):
    """La primera senal crea un bloque nuevo."""
    agg = SignalAggregator(db=mock_db)
    await agg.process_signal(_signal(1, "2026-03-16T10:00:00Z"))
    mock_db.create_block.assert_called_once()
    mock_db.link_signal_to_block.assert_called_once_with(1, 1)


@pytest.mark.asyncio
async def test_same_context_extends_block(mock_db):
    """Senales del mismo contexto extienden el bloque actual."""
    agg = SignalAggregator(db=mock_db)
    mock_db.create_block.return_value = 1

    for i in range(3):
        t = datetime(2026, 3, 16, 10, i, 0, tzinfo=timezone.utc).isoformat()
        await agg.process_signal(_signal(i + 1, t))

    assert mock_db.create_block.call_count == 1
    assert mock_db.update_block.call_count == 2
    assert mock_db.link_signal_to_block.call_count == 3


@pytest.mark.asyncio
async def test_context_change_closes_and_creates(mock_db):
    """Cambio de contexto cierra bloque actual y crea nuevo."""
    agg = SignalAggregator(db=mock_db)
    mock_db.create_block.side_effect = [1, 2]

    await agg.process_signal(_signal(1, "2026-03-16T10:00:00Z", context="git:/project-a"))
    await agg.process_signal(_signal(2, "2026-03-16T10:00:30Z", context="git:/project-b"))

    assert mock_db.create_block.call_count == 2
    # Primer bloque cerrado con status=closed
    close_call = [c for c in mock_db.update_block.call_args_list if "closed" in str(c)]
    assert len(close_call) >= 1


@pytest.mark.asyncio
async def test_inactivity_closes_block(mock_db):
    """Gap mayor al umbral cierra el bloque."""
    agg = SignalAggregator(db=mock_db, inactivity_threshold=300)
    mock_db.create_block.side_effect = [1, 2]

    await agg.process_signal(_signal(1, "2026-03-16T10:00:00Z"))
    await agg.process_signal(_signal(2, "2026-03-16T10:10:00Z"))

    assert mock_db.create_block.call_count == 2


@pytest.mark.asyncio
async def test_no_close_within_threshold(mock_db):
    """Mismo contexto dentro del umbral no cierra."""
    agg = SignalAggregator(db=mock_db, inactivity_threshold=300)
    mock_db.create_block.return_value = 1

    await agg.process_signal(_signal(1, "2026-03-16T10:00:00Z"))
    await agg.process_signal(_signal(2, "2026-03-16T10:04:00Z"))

    assert mock_db.create_block.call_count == 1


@pytest.mark.asyncio
async def test_transient_app_inherits_context(mock_db):
    """Apps transitorias heredan el contexto del bloque anterior."""
    agg = SignalAggregator(db=mock_db, transient_apps={"nautilus"})
    mock_db.create_block.return_value = 1

    await agg.process_signal(_signal(1, "2026-03-16T10:00:00Z"))
    await agg.process_signal(_signal(2, "2026-03-16T10:00:30Z", app="nautilus", context="app:nautilus"))

    assert mock_db.create_block.call_count == 1


@pytest.mark.asyncio
async def test_browser_different_domains_split(mock_db):
    """Dominios diferentes en navegador generan bloques separados."""
    agg = SignalAggregator(db=mock_db, browser_apps={"chrome"})
    mock_db.create_block.side_effect = [1, 2]

    await agg.process_signal(_signal(1, "2026-03-16T10:00:00Z", app="chrome", context="web:GitHub"))
    await agg.process_signal(_signal(2, "2026-03-16T10:00:30Z", app="chrome", context="web:Gmail"))

    assert mock_db.create_block.call_count == 2


@pytest.mark.asyncio
async def test_lock_closes_block(mock_db):
    """handle_lock cierra el bloque actual."""
    agg = SignalAggregator(db=mock_db)
    mock_db.create_block.return_value = 1

    await agg.process_signal(_signal(1, "2026-03-16T10:00:00Z"))
    await agg.handle_lock()

    assert agg._current_block_id is None
    close_call = [c for c in mock_db.update_block.call_args_list if "closed" in str(c)]
    assert len(close_call) >= 1


@pytest.mark.asyncio
async def test_recover_open_blocks_recent(mock_db):
    """Recupera bloque auto reciente al arrancar."""
    recent = (datetime.now(timezone.utc) - timedelta(minutes=2)).isoformat()
    mock_db.get_open_blocks.return_value = [{
        "id": 5,
        "start_time": recent,
        "end_time": recent,
        "app_name": "code",
    }]
    mock_db.get_signals_by_block.return_value = [{"window_title": "file.py"}]

    agg = SignalAggregator(db=mock_db)
    await agg.recover_open_blocks()

    assert agg._current_block_id == 5


@pytest.mark.asyncio
async def test_recover_open_blocks_stale(mock_db):
    """Cierra bloques stale al arrancar."""
    old = (datetime.now(timezone.utc) - timedelta(hours=2)).isoformat()
    mock_db.get_open_blocks.return_value = [{
        "id": 5,
        "start_time": old,
        "end_time": old,
        "app_name": "code",
    }]

    agg = SignalAggregator(db=mock_db)
    await agg.recover_open_blocks()

    assert agg._current_block_id is None
    mock_db.update_block.assert_called_with(5, status="closed")
