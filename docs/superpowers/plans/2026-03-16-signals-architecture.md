# Signals Architecture Implementation Plan

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the current block-based capture with a signals architecture: raw signals every 30s, blocks derived in real-time by a deterministic algorithm, AI only on-demand.

**Architecture:** The Poller writes raw signals to a `signals` table. A `SignalAggregator` builds blocks from signals using context-based grouping rules (git project > browser domain > app name). The frontend shows blocks as before, with a new toggle to view raw signals. Split/merge operations let users refine blocks.

**Tech Stack:** Python 3.10+ (asyncio, FastAPI, aiosqlite), Vue 3 + TypeScript, Tauri 2 (Rust)

**Spec:** `docs/superpowers/specs/2026-03-16-signals-architecture-design.md`

---

## File Structure

| Action | File | Purpose |
|--------|------|---------|
| Modify | `daemon/mimir_daemon/db.py` | Add signals table, block_signals table, signal CRUD |
| Create | `daemon/mimir_daemon/signal_aggregator.py` | Deterministic block construction from signals |
| Modify | `daemon/mimir_daemon/poller.py` | Write signals + call aggregator instead of BlockManager |
| Modify | `daemon/mimir_daemon/capture.py` | Use SignalAggregator instead of BlockManager |
| Modify | `daemon/mimir_daemon/server.py` | Add signals endpoints, split/merge |
| Modify | `daemon/mimir_daemon/config.py` | Add inactivity_threshold, browser_apps, transient_apps |
| Create | `daemon/tests/test_signal_aggregator.py` | Tests for aggregation logic |
| Create | `daemon/tests/test_signals_api.py` | Tests for signals/split/merge endpoints |
| Modify | `src/lib/types.ts` | Add Signal interface, update ActivityBlock |
| Modify | `src/lib/api.ts` | Add signals, split, merge API calls |
| Modify | `src/stores/blocks.ts` | Add signals state, split/merge actions |
| Modify | `src/views/ReviewDayView.vue` | Signals toggle, split/merge UI |
| Modify | `src-tauri/src/commands.rs` | Add signals, split, merge Tauri commands |

---

## Chunk 1: Database + SignalAggregator (backend core)

### Task 1: Add signals schema and CRUD to db.py

**Files:**
- Modify: `daemon/mimir_daemon/db.py`

- [ ] **Step 1: Add signals table and block_signals table to SCHEMA**

After the `ai_cache` table creation (around line 61), add:

```python
        CREATE TABLE IF NOT EXISTS signals (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT NOT NULL,
            app_name TEXT,
            window_title TEXT,
            project_path TEXT,
            git_branch TEXT,
            git_remote TEXT,
            ssh_host TEXT,
            pid INTEGER,
            context_key TEXT,
            last_commit_message TEXT,
            created_at TEXT DEFAULT (datetime('now'))
        );
        CREATE INDEX IF NOT EXISTS idx_signals_timestamp ON signals(timestamp);

        CREATE TABLE IF NOT EXISTS block_signals (
            block_id INTEGER NOT NULL REFERENCES blocks(id) ON DELETE CASCADE,
            signal_id INTEGER NOT NULL REFERENCES signals(id),
            PRIMARY KEY (block_id, signal_id)
        );
```

- [ ] **Step 2: Add signal CRUD methods**

After the existing block methods, add:

```python
    async def create_signal(self, **kwargs: object) -> int:
        """Inserta una senal y devuelve su ID."""
        cols = list(kwargs.keys())
        placeholders = ", ".join(["?"] * len(cols))
        col_names = ", ".join(cols)
        values = [kwargs[c] for c in cols]
        async with self.db.execute(
            f"INSERT INTO signals ({col_names}) VALUES ({placeholders})", values
        ) as cursor:
            await self.db.commit()
            return cursor.lastrowid

    async def get_signals_by_date(self, date: str) -> list[dict]:
        """Obtiene senales de un dia."""
        async with self.db.execute(
            "SELECT * FROM signals WHERE date(timestamp) = ? ORDER BY timestamp",
            [date],
        ) as cursor:
            rows = await cursor.fetchall()
            cols = [d[0] for d in cursor.description]
            return [dict(zip(cols, row)) for row in rows]

    async def get_signals_by_block(self, block_id: int) -> list[dict]:
        """Obtiene senales asociadas a un bloque."""
        async with self.db.execute(
            """SELECT s.* FROM signals s
               JOIN block_signals bs ON s.id = bs.signal_id
               WHERE bs.block_id = ?
               ORDER BY s.timestamp""",
            [block_id],
        ) as cursor:
            rows = await cursor.fetchall()
            cols = [d[0] for d in cursor.description]
            return [dict(zip(cols, row)) for row in rows]

    async def link_signal_to_block(self, block_id: int, signal_id: int) -> None:
        """Vincula una senal a un bloque."""
        await self.db.execute(
            "INSERT OR IGNORE INTO block_signals (block_id, signal_id) VALUES (?, ?)",
            [block_id, signal_id],
        )
        await self.db.commit()

    async def cleanup_old_signals(self, months: int = 6) -> int:
        """Elimina senales mas antiguas de N meses."""
        async with self.db.execute(
            "DELETE FROM signals WHERE timestamp < datetime('now', ?)",
            [f"-{months} months"],
        ) as cursor:
            await self.db.commit()
            return cursor.rowcount
```

- [ ] **Step 3: Run existing tests to verify no regressions**

Run: `cd daemon && .venv/bin/python -m pytest tests/ -v 2>&1 | tail -5`
Expected: 119 passed

- [ ] **Step 4: Commit**

```bash
git add daemon/mimir_daemon/db.py
git commit -m "feat: add signals and block_signals tables with CRUD"
```

---

### Task 2: Create SignalAggregator

**Files:**
- Create: `daemon/mimir_daemon/signal_aggregator.py`
- Create: `daemon/tests/test_signal_aggregator.py`

- [ ] **Step 1: Write tests**

Create `daemon/tests/test_signal_aggregator.py`:

```python
"""Tests para el SignalAggregator."""

import pytest
from unittest.mock import AsyncMock, patch
from datetime import datetime, timezone, timedelta

from mimir_daemon.signal_aggregator import SignalAggregator, extract_browser_site


# --- Tests de extraccion de dominio ---

def test_extract_browser_site_chrome_standard():
    assert extract_browser_site("PR #42 — GitHub — Google Chrome", "chrome") == "GitHub"

def test_extract_browser_site_firefox():
    assert extract_browser_site("Inbox - Gmail — Mozilla Firefox", "firefox") == "Gmail"

def test_extract_browser_site_no_separator():
    assert extract_browser_site("Stack Overflow", "chrome") == "Stack Overflow"

def test_extract_browser_site_empty():
    assert extract_browser_site("", "chrome") == ""

def test_extract_browser_site_mixed_separators():
    assert extract_browser_site("How to fix bug - Stack Overflow — Google Chrome", "chrome") == "Stack Overflow"

def test_extract_browser_site_single_segment_after_strip():
    assert extract_browser_site("Google Chrome", "chrome") == ""


# --- Tests del aggregator ---

@pytest.fixture
def mock_db():
    db = AsyncMock()
    db.create_block = AsyncMock(return_value=1)
    db.update_block = AsyncMock()
    db.link_signal_to_block = AsyncMock()
    db.get_open_blocks = AsyncMock(return_value=[])
    return db


@pytest.mark.asyncio
async def test_first_signal_creates_block(mock_db):
    """La primera senal crea un bloque nuevo."""
    agg = SignalAggregator(db=mock_db)
    signal = {
        "id": 1, "timestamp": "2026-03-16T10:00:00Z",
        "app_name": "code", "window_title": "main.py — project",
        "project_path": "/home/user/project", "context_key": "git:/home/user/project",
        "git_branch": "main", "git_remote": "origin",
    }
    await agg.process_signal(signal)
    mock_db.create_block.assert_called_once()
    mock_db.link_signal_to_block.assert_called_once()


@pytest.mark.asyncio
async def test_same_context_extends_block(mock_db):
    """Senales del mismo contexto extienden el bloque actual."""
    agg = SignalAggregator(db=mock_db)
    mock_db.create_block.return_value = 1

    base = "2026-03-16T10:00:00Z"
    for i in range(3):
        t = datetime(2026, 3, 16, 10, i, 0, tzinfo=timezone.utc).isoformat()
        await agg.process_signal({
            "id": i + 1, "timestamp": t,
            "app_name": "code", "window_title": f"file{i}.py",
            "project_path": "/home/user/project", "context_key": "git:/home/user/project",
        })

    assert mock_db.create_block.call_count == 1
    assert mock_db.update_block.call_count == 2  # 2nd and 3rd signal update
    assert mock_db.link_signal_to_block.call_count == 3


@pytest.mark.asyncio
async def test_context_change_closes_and_creates(mock_db):
    """Cambio de contexto cierra bloque actual y crea nuevo."""
    agg = SignalAggregator(db=mock_db)
    mock_db.create_block.side_effect = [1, 2]

    await agg.process_signal({
        "id": 1, "timestamp": "2026-03-16T10:00:00Z",
        "app_name": "code", "context_key": "git:/project-a",
    })
    await agg.process_signal({
        "id": 2, "timestamp": "2026-03-16T10:00:30Z",
        "app_name": "code", "context_key": "git:/project-b",
    })

    assert mock_db.create_block.call_count == 2
    # First block closed
    mock_db.update_block.assert_any_call(1, status="closed", end_time="2026-03-16T10:00:00Z", duration_minutes=0.0, window_titles_json="[]")


@pytest.mark.asyncio
async def test_inactivity_closes_block(mock_db):
    """Gap mayor al umbral cierra el bloque."""
    agg = SignalAggregator(db=mock_db, inactivity_threshold=300)
    mock_db.create_block.side_effect = [1, 2]

    await agg.process_signal({
        "id": 1, "timestamp": "2026-03-16T10:00:00Z",
        "app_name": "code", "context_key": "git:/project",
    })
    # 10 minutos despues
    await agg.process_signal({
        "id": 2, "timestamp": "2026-03-16T10:10:00Z",
        "app_name": "code", "context_key": "git:/project",
    })

    assert mock_db.create_block.call_count == 2


@pytest.mark.asyncio
async def test_transient_app_inherits_context(mock_db):
    """Apps transitorias heredan el contexto del bloque anterior."""
    agg = SignalAggregator(db=mock_db, transient_apps={"nautilus"})
    mock_db.create_block.return_value = 1

    await agg.process_signal({
        "id": 1, "timestamp": "2026-03-16T10:00:00Z",
        "app_name": "code", "context_key": "git:/project",
    })
    await agg.process_signal({
        "id": 2, "timestamp": "2026-03-16T10:00:30Z",
        "app_name": "nautilus", "context_key": "app:nautilus",
    })

    # Solo 1 bloque — nautilus no genera bloque nuevo
    assert mock_db.create_block.call_count == 1


@pytest.mark.asyncio
async def test_browser_different_domains_split(mock_db):
    """Dominios diferentes en navegador generan bloques separados."""
    agg = SignalAggregator(db=mock_db, browser_apps={"chrome"})
    mock_db.create_block.side_effect = [1, 2]

    await agg.process_signal({
        "id": 1, "timestamp": "2026-03-16T10:00:00Z",
        "app_name": "chrome", "context_key": "web:GitHub",
    })
    await agg.process_signal({
        "id": 2, "timestamp": "2026-03-16T10:00:30Z",
        "app_name": "chrome", "context_key": "web:Gmail",
    })

    assert mock_db.create_block.call_count == 2


@pytest.mark.asyncio
async def test_lock_closes_block(mock_db):
    """handle_lock cierra el bloque actual."""
    agg = SignalAggregator(db=mock_db)
    mock_db.create_block.return_value = 1

    await agg.process_signal({
        "id": 1, "timestamp": "2026-03-16T10:00:00Z",
        "app_name": "code", "context_key": "git:/project",
    })
    await agg.handle_lock()

    assert agg._current_block_id is None
    mock_db.update_block.assert_called()


@pytest.mark.asyncio
async def test_recover_open_blocks(mock_db):
    """Recupera bloque auto reciente al arrancar."""
    mock_db.get_open_blocks.return_value = [{
        "id": 5,
        "start_time": (datetime.now(timezone.utc) - timedelta(minutes=2)).isoformat(),
        "end_time": (datetime.now(timezone.utc) - timedelta(minutes=1)).isoformat(),
        "context_key": "git:/project",
        "app_name": "code",
    }]
    # Need to get signals for this block
    mock_db.get_signals_by_block = AsyncMock(return_value=[
        {"window_title": "file.py"}
    ])

    agg = SignalAggregator(db=mock_db)
    await agg.recover_open_blocks()

    assert agg._current_block_id == 5
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd daemon && .venv/bin/python -m pytest tests/test_signal_aggregator.py -v 2>&1`
Expected: FAIL (module not found)

- [ ] **Step 3: Create signal_aggregator.py**

Create `daemon/mimir_daemon/signal_aggregator.py`:

```python
"""Agregador de senales a bloques.

Reemplaza al BlockManager. Construye bloques a partir de senales
usando un algoritmo determinista basado en reglas de contexto.
"""

import json
import logging
import re
from collections import Counter
from datetime import datetime, timezone, timedelta

from .db import Database

logger = logging.getLogger(__name__)

DEFAULT_BROWSER_APPS = frozenset({
    "chrome", "chromium", "firefox", "brave", "vivaldi",
    "opera", "microsoft-edge", "zen", "floorp",
})

DEFAULT_TRANSIENT_APPS = frozenset({
    "nautilus", "thunar", "nemo", "pcmanfm", "dolphin",
})

# Separadores comunes en titulos de navegador
_TITLE_SEPARATORS = re.compile(r"\s+[—–\-]\s+")


def extract_browser_site(title: str, app_name: str) -> str:
    """Extrae el nombre del sitio del titulo de un navegador.

    Estrategia:
    1. Eliminar el nombre del navegador del final
    2. Separar por — / – / -
    3. Tomar el ultimo segmento (normalmente el sitio)
    """
    if not title:
        return ""

    # Strip browser name from end
    browser_names = {
        "chrome": "Google Chrome", "chromium": "Chromium",
        "firefox": "Mozilla Firefox", "brave": "Brave",
        "vivaldi": "Vivaldi", "opera": "Opera",
        "microsoft-edge": "Microsoft Edge", "zen": "Zen Browser",
        "floorp": "Floorp",
    }
    suffix = browser_names.get(app_name, "")
    if suffix and title.endswith(suffix):
        title = title[: -len(suffix)]
        # Remove trailing separator
        title = _TITLE_SEPARATORS.sub(lambda m: m.group() if m.end() < len(title) else "", title).rstrip()
        title = re.sub(r"\s*[—–\-]\s*$", "", title).strip()

    if not title:
        return ""

    # Split by separators and take last segment
    parts = _TITLE_SEPARATORS.split(title)
    return parts[-1].strip() if parts else title.strip()


def compute_context_key(
    app_name: str | None,
    window_title: str | None,
    project_path: str | None,
    browser_apps: frozenset[str] = DEFAULT_BROWSER_APPS,
) -> str:
    """Calcula la clave de contexto para una senal."""
    app = (app_name or "").lower()

    if project_path:
        return f"git:{project_path}"

    if app in browser_apps:
        site = extract_browser_site(window_title or "", app)
        if site:
            return f"web:{site}"

    return f"app:{app or 'unknown'}"


class SignalAggregator:
    """Construye bloques a partir de senales en tiempo real."""

    def __init__(
        self,
        db: Database,
        inactivity_threshold: int = 300,
        browser_apps: set[str] | frozenset[str] | None = None,
        transient_apps: set[str] | frozenset[str] | None = None,
    ) -> None:
        self._db = db
        self._inactivity_threshold = inactivity_threshold
        self._browser_apps = frozenset(browser_apps) if browser_apps else DEFAULT_BROWSER_APPS
        self._transient_apps = frozenset(transient_apps) if transient_apps else DEFAULT_TRANSIENT_APPS
        self._current_block_id: int | None = None
        self._current_context_key: str | None = None
        self._last_signal_time: datetime | None = None
        self._window_titles: list[str] = []

    async def recover_open_blocks(self) -> None:
        """Recupera bloques auto abiertos tras un reinicio."""
        open_blocks = await self._db.get_open_blocks()
        if not open_blocks:
            return

        now = datetime.now(timezone.utc)
        for block in open_blocks:
            end_str = block.get("end_time", "")
            try:
                end_time = datetime.fromisoformat(end_str.replace("Z", "+00:00"))
            except (ValueError, AttributeError):
                end_time = now - timedelta(hours=2)

            elapsed = (now - end_time).total_seconds()

            if elapsed < self._inactivity_threshold:
                # Retomar bloque reciente
                self._current_block_id = block["id"]
                self._current_context_key = block.get("context_key") or block.get("app_name")
                self._last_signal_time = end_time
                # Recuperar titulos
                signals = await self._db.get_signals_by_block(block["id"])
                self._window_titles = [
                    s["window_title"] for s in signals if s.get("window_title")
                ]
                logger.info("Bloque #%d retomado (elapsed=%.0fs)", block["id"], elapsed)
            else:
                # Cerrar bloque stale
                await self._db.update_block(block["id"], status="closed")
                logger.info("Bloque #%d cerrado (stale, elapsed=%.0fs)", block["id"], elapsed)

    async def process_signal(self, signal: dict) -> None:
        """Procesa una senal nueva y actualiza/crea bloques."""
        context_key = signal.get("context_key", "")
        app_name = signal.get("app_name", "")
        timestamp_str = signal.get("timestamp", "")
        signal_id = signal.get("id")

        try:
            signal_time = datetime.fromisoformat(timestamp_str.replace("Z", "+00:00"))
        except (ValueError, AttributeError):
            signal_time = datetime.now(timezone.utc)

        # Apps transitorias heredan contexto del bloque actual
        if app_name and app_name.lower() in self._transient_apps and self._current_block_id:
            context_key = self._current_context_key or context_key

        # Verificar si debemos cerrar el bloque actual
        should_close = False
        if self._current_block_id is not None:
            # Cambio de contexto
            if context_key != self._current_context_key:
                should_close = True
            # Inactividad
            elif self._last_signal_time:
                gap = (signal_time - self._last_signal_time).total_seconds()
                if gap > self._inactivity_threshold:
                    should_close = True

        if should_close:
            await self._close_current_block()

        # Crear bloque nuevo si no hay uno activo
        if self._current_block_id is None:
            block_id = await self._db.create_block(
                start_time=timestamp_str,
                end_time=timestamp_str,
                duration_minutes=0.0,
                app_name=app_name or "unknown",
                window_title=signal.get("window_title", ""),
                project_path=signal.get("project_path"),
                git_branch=signal.get("git_branch"),
                git_remote=signal.get("git_remote"),
                status="auto",
            )
            self._current_block_id = block_id
            self._current_context_key = context_key
            self._window_titles = []
            logger.info("Nuevo bloque #%d: %s", block_id, context_key)
        else:
            # Actualizar bloque existente
            duration = (signal_time - self._block_start_time(timestamp_str)).total_seconds() / 60
            await self._db.update_block(
                self._current_block_id,
                end_time=timestamp_str,
                duration_minutes=round(duration, 1),
                window_title=signal.get("window_title", ""),
                project_path=signal.get("project_path") or None,
                git_branch=signal.get("git_branch") or None,
                git_remote=signal.get("git_remote") or None,
            )

        # Vincular senal al bloque
        if signal_id and self._current_block_id:
            await self._db.link_signal_to_block(self._current_block_id, signal_id)

        # Acumular titulos
        title = signal.get("window_title", "")
        if title and title not in self._window_titles:
            self._window_titles.append(title)

        self._last_signal_time = signal_time

    async def handle_lock(self) -> None:
        """Cierra el bloque actual al bloquear pantalla."""
        if self._current_block_id:
            await self._close_current_block()
            logger.info("Bloque cerrado por lock")

    async def handle_unlock(self) -> None:
        """Reset tras desbloqueo — la proxima senal abrira bloque nuevo."""
        self._last_signal_time = datetime.now(timezone.utc)

    async def _close_current_block(self) -> None:
        """Cierra el bloque actual."""
        if not self._current_block_id:
            return

        # Generar window_titles_json (top 20 por frecuencia)
        counter = Counter(self._window_titles)
        top_titles = [t for t, _ in counter.most_common(20)]
        titles_json = json.dumps(top_titles, ensure_ascii=False)

        end_time = self._last_signal_time.isoformat() if self._last_signal_time else datetime.now(timezone.utc).isoformat()
        start_block = await self._db.get_block_by_id(self._current_block_id)
        duration = 0.0
        if start_block:
            try:
                start = datetime.fromisoformat(start_block["start_time"].replace("Z", "+00:00"))
                end = datetime.fromisoformat(end_time.replace("Z", "+00:00")) if isinstance(end_time, str) else self._last_signal_time
                duration = (end - start).total_seconds() / 60
            except (ValueError, AttributeError):
                pass

        await self._db.update_block(
            self._current_block_id,
            status="closed",
            end_time=end_time,
            duration_minutes=round(duration, 1),
            window_titles_json=titles_json,
        )
        logger.info("Bloque #%d cerrado (%.1f min)", self._current_block_id, duration)

        self._current_block_id = None
        self._current_context_key = None
        self._window_titles = []

    def _block_start_time(self, current_timestamp: str) -> datetime:
        """Calcula el inicio del bloque actual (para duracion)."""
        # Simple: usar last_signal_time o current como fallback
        if self._last_signal_time:
            return self._last_signal_time
        try:
            return datetime.fromisoformat(current_timestamp.replace("Z", "+00:00"))
        except (ValueError, AttributeError):
            return datetime.now(timezone.utc)
```

- [ ] **Step 4: Run tests**

Run: `cd daemon && .venv/bin/python -m pytest tests/test_signal_aggregator.py -v 2>&1`
Expected: 11 tests PASS (6 extract + 5 aggregator at minimum)

- [ ] **Step 5: Run all tests**

Run: `cd daemon && .venv/bin/python -m pytest tests/ -v 2>&1 | tail -5`
Expected: 130+ tests PASS

- [ ] **Step 6: Commit**

```bash
git add daemon/mimir_daemon/signal_aggregator.py daemon/tests/test_signal_aggregator.py
git commit -m "feat: add SignalAggregator with context-based block grouping"
```

---

## Chunk 2: Wire Poller + Capture to SignalAggregator

### Task 3: Modify Poller to write signals and use SignalAggregator

**Files:**
- Modify: `daemon/mimir_daemon/poller.py`
- Modify: `daemon/mimir_daemon/capture.py`
- Modify: `daemon/mimir_daemon/config.py`

- [ ] **Step 1: Add config fields to DaemonConfig**

In `config.py`, add to the dataclass fields:

```python
    inactivity_threshold: int = 300  # 5 minutes in seconds
    browser_apps: list[str] | None = None
    transient_apps: list[str] | None = None
```

- [ ] **Step 2: Modify Poller to accept SignalAggregator**

Replace `daemon/mimir_daemon/poller.py` with:

```python
"""Ciclo principal de polling de actividad."""

import asyncio
import logging
from datetime import datetime, timezone

from .config import DaemonConfig
from .db import Database
from .platform.base import PlatformProvider
from .context_enricher import enrich_pid, EnrichedContext
from .signal_aggregator import SignalAggregator, compute_context_key

logger = logging.getLogger(__name__)


class Poller:
    """Ciclo asyncio que captura actividad cada N segundos."""

    def __init__(
        self,
        config: DaemonConfig,
        db: Database,
        platform: PlatformProvider,
        aggregator: SignalAggregator,
    ) -> None:
        self._config = config
        self._db = db
        self._platform = platform
        self._aggregator = aggregator
        self._running = False
        self._paused = False
        self._last_poll: datetime | None = None

    @property
    def last_poll(self) -> datetime | None:
        return self._last_poll

    @property
    def is_running(self) -> bool:
        return self._running

    def pause(self) -> None:
        """Pausa la captura."""
        self._paused = True
        logger.info("Poller pausado")

    def resume(self) -> None:
        """Reanuda la captura."""
        self._paused = False
        logger.info("Poller reanudado")

    async def run(self) -> None:
        """Bucle principal de polling."""
        self._running = True
        logger.info(
            "Poller iniciado: intervalo=%ds, inactividad=%ds",
            self._config.polling_interval,
            self._config.inactivity_threshold,
        )

        try:
            while self._running:
                if not self._paused:
                    await self._poll_once()
                await asyncio.sleep(self._config.polling_interval)
        except asyncio.CancelledError:
            logger.info("Poller cancelado")
        finally:
            self._running = False

    async def _poll_once(self) -> None:
        """Ejecuta un ciclo de polling."""
        try:
            # Verificar eventos de sesion
            events = await self._platform.get_session_events()
            for event in events:
                if event.event_type == "lock":
                    await self._aggregator.handle_lock()
                elif event.event_type == "unlock":
                    await self._aggregator.handle_unlock()

            # Capturar ventana activa
            window = await self._platform.get_active_window()
            if not window:
                self._last_poll = datetime.now(timezone.utc)
                return

            # Enriquecer contexto
            context = await enrich_pid(window.pid)

            # Calcular context_key
            browser_apps = frozenset(self._config.browser_apps) if self._config.browser_apps else None
            context_key = compute_context_key(
                app_name=window.app_name,
                window_title=window.window_title,
                project_path=context.project_path if context else None,
                browser_apps=browser_apps or frozenset(),
            )

            # Guardar senal
            now = datetime.now(timezone.utc).isoformat()
            signal_id = await self._db.create_signal(
                timestamp=now,
                app_name=window.app_name,
                window_title=window.window_title,
                project_path=context.project_path if context else None,
                git_branch=context.git_branch if context else None,
                git_remote=context.git_remote if context else None,
                ssh_host=context.ssh_host if context else None,
                pid=window.pid,
                context_key=context_key,
                last_commit_message=context.last_commit_message if context else None,
            )

            # Procesar en aggregator
            signal = {
                "id": signal_id,
                "timestamp": now,
                "app_name": window.app_name,
                "window_title": window.window_title,
                "project_path": context.project_path if context else None,
                "git_branch": context.git_branch if context else None,
                "git_remote": context.git_remote if context else None,
                "context_key": context_key,
            }
            await self._aggregator.process_signal(signal)

            self._last_poll = datetime.now(timezone.utc)

        except Exception as e:
            logger.error("Error en poll: %s", e, exc_info=True)

    def stop(self) -> None:
        """Detiene el poller."""
        self._running = False
```

- [ ] **Step 3: Update capture.py to use SignalAggregator**

In `capture.py`, replace the BlockManager imports and usage:

Change import from:
```python
from .block_manager import BlockManager
```
To:
```python
from .signal_aggregator import SignalAggregator
```

Replace the block_manager creation (around line 83-88):
```python
    block_manager = BlockManager(
        db=db,
        inherit_threshold=config.inherit_threshold,
    )

    await block_manager.recover_open_blocks()

    poller = Poller(
        config=config,
        db=db,
        platform=platform,
        block_manager=block_manager,
    )
```

With:
```python
    aggregator = SignalAggregator(
        db=db,
        inactivity_threshold=config.inactivity_threshold,
        browser_apps=set(config.browser_apps) if config.browser_apps else None,
        transient_apps=set(config.transient_apps) if config.transient_apps else None,
    )

    await aggregator.recover_open_blocks()

    poller = Poller(
        config=config,
        db=db,
        platform=platform,
        aggregator=aggregator,
    )
```

- [ ] **Step 4: Update existing poller tests**

The existing tests in `test_poller.py` mock `block_manager`. Update them to mock `aggregator` instead. Change `block_manager=mock_bm` to `aggregator=mock_agg` in the Poller constructor calls, and update the mock's method names (`process_poll` → `process_signal`, `handle_lock`, `handle_unlock`).

- [ ] **Step 5: Run all tests**

Run: `cd daemon && .venv/bin/python -m pytest tests/ -v 2>&1 | tail -10`
Expected: All tests PASS

- [ ] **Step 6: Commit**

```bash
git add daemon/mimir_daemon/poller.py daemon/mimir_daemon/capture.py daemon/mimir_daemon/config.py daemon/tests/
git commit -m "feat: wire Poller and capture to SignalAggregator"
```

---

## Chunk 3: API Endpoints (signals, split, merge)

### Task 4: Add signals and split/merge endpoints to server.py

**Files:**
- Modify: `daemon/mimir_daemon/server.py`
- Create: `daemon/tests/test_signals_api.py`

- [ ] **Step 1: Add signals GET endpoint**

In `server.py`, after the existing block endpoints, add:

```python
    @app.get("/signals")
    async def get_signals(date: str | None = None, block_id: int | None = None):
        if block_id:
            return await db.get_signals_by_block(block_id)
        if date:
            return await db.get_signals_by_date(date)
        # Default: today
        from datetime import datetime, timezone
        today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        return await db.get_signals_by_date(today)
```

- [ ] **Step 2: Add split endpoint**

```python
    @app.post("/blocks/{block_id}/split")
    async def split_block(block_id: int, signal_id: int):
        """Divide un bloque en dos en el punto de una senal."""
        block = await db.get_block_by_id(block_id)
        if not block:
            raise HTTPException(404, "Bloque no encontrado")
        if block["status"] in ("confirmed", "synced"):
            raise HTTPException(400, "No se puede partir un bloque confirmado")

        # Obtener senales del bloque
        signals = await db.get_signals_by_block(block_id)
        if not signals:
            raise HTTPException(400, "Bloque sin senales")

        # Encontrar punto de corte
        before = [s for s in signals if s["id"] < signal_id]
        after = [s for s in signals if s["id"] >= signal_id]
        if not before or not after:
            raise HTTPException(400, "Punto de corte invalido")

        # Actualizar bloque original (primera mitad)
        last_before = before[-1]
        await db.update_block(block_id,
            end_time=last_before["timestamp"],
            duration_minutes=_calc_duration(block["start_time"], last_before["timestamp"]),
            status="closed",
        )

        # Crear segundo bloque
        first_after = after[0]
        last_after = after[-1]
        new_id = await db.create_block(
            start_time=first_after["timestamp"],
            end_time=last_after["timestamp"],
            duration_minutes=_calc_duration(first_after["timestamp"], last_after["timestamp"]),
            app_name=first_after.get("app_name", block["app_name"]),
            window_title=first_after.get("window_title", ""),
            project_path=first_after.get("project_path"),
            git_branch=first_after.get("git_branch"),
            git_remote=first_after.get("git_remote"),
            status="closed",
        )

        # Reasignar senales
        for s in after:
            await db.db.execute(
                "UPDATE block_signals SET block_id = ? WHERE signal_id = ?",
                [new_id, s["id"]],
            )
        await db.db.commit()

        return {"original_block_id": block_id, "new_block_id": new_id}
```

- [ ] **Step 3: Add merge endpoint**

```python
    from pydantic import BaseModel

    class MergeRequest(BaseModel):
        block_ids: list[int]

    @app.post("/blocks/merge")
    async def merge_blocks(req: MergeRequest):
        """Fusiona bloques en uno."""
        if len(req.block_ids) < 2:
            raise HTTPException(400, "Se necesitan al menos 2 bloques")

        blocks = []
        for bid in req.block_ids:
            b = await db.get_block_by_id(bid)
            if not b:
                raise HTTPException(404, f"Bloque {bid} no encontrado")
            if b["status"] in ("confirmed", "synced"):
                raise HTTPException(400, f"Bloque {bid} esta confirmado, no se puede fusionar")
            blocks.append(b)

        # Ordenar por start_time
        blocks.sort(key=lambda b: b["start_time"])
        primary = blocks[0]
        last = blocks[-1]

        # Actualizar bloque primario
        await db.update_block(primary["id"],
            end_time=last["end_time"],
            duration_minutes=_calc_duration(primary["start_time"], last["end_time"]),
            status="closed",
        )

        # Mover senales de los otros bloques al primario
        for b in blocks[1:]:
            await db.db.execute(
                "UPDATE block_signals SET block_id = ? WHERE block_id = ?",
                [primary["id"], b["id"]],
            )
            await db.delete_block(b["id"])
        await db.db.commit()

        return {"merged_block_id": primary["id"]}
```

- [ ] **Step 4: Add helper function**

At module level in server.py:

```python
def _calc_duration(start_str: str, end_str: str) -> float:
    """Calcula duracion en minutos entre dos timestamps ISO."""
    from datetime import datetime
    try:
        start = datetime.fromisoformat(start_str.replace("Z", "+00:00"))
        end = datetime.fromisoformat(end_str.replace("Z", "+00:00"))
        return round((end - start).total_seconds() / 60, 1)
    except (ValueError, AttributeError):
        return 0.0
```

- [ ] **Step 5: Write API tests**

Create `daemon/tests/test_signals_api.py` with basic tests for the new endpoints (GET /signals, POST split, POST merge). Follow the pattern of the existing `test_server.py` using `httpx.AsyncClient` with `ASGITransport`.

- [ ] **Step 6: Run all tests**

Run: `cd daemon && .venv/bin/python -m pytest tests/ -v 2>&1 | tail -10`
Expected: All tests PASS

- [ ] **Step 7: Commit**

```bash
git add daemon/mimir_daemon/server.py daemon/tests/test_signals_api.py
git commit -m "feat: add signals, split, and merge API endpoints"
```

---

## Chunk 4: Frontend (types, API, store, ReviewDayView)

### Task 5: Update TypeScript types and API layer

**Files:**
- Modify: `src/lib/types.ts`
- Modify: `src/lib/api.ts`
- Modify: `src-tauri/src/commands.rs`

- [ ] **Step 1: Add Signal interface to types.ts**

After the `ActivityBlock` interface:

```typescript
export interface Signal {
  id: number;
  timestamp: string;
  app_name: string | null;
  window_title: string | null;
  project_path: string | null;
  git_branch: string | null;
  git_remote: string | null;
  ssh_host: string | null;
  pid: number | null;
  context_key: string | null;
  last_commit_message: string | null;
  created_at: string;
}
```

- [ ] **Step 2: Add API calls to api.ts**

```typescript
  async getSignals(date?: string, blockId?: number): Promise<Signal[]> {
    const params = new URLSearchParams();
    if (date) params.set('date', date);
    if (blockId) params.set('block_id', String(blockId));
    return this.get(`/signals?${params}`);
  },

  async splitBlock(blockId: number, signalId: number): Promise<{ original_block_id: number; new_block_id: number }> {
    return this.post(`/blocks/${blockId}/split?signal_id=${signalId}`);
  },

  async mergeBlocks(blockIds: number[]): Promise<{ merged_block_id: number }> {
    return this.post('/blocks/merge', { block_ids: blockIds });
  },
```

- [ ] **Step 3: Add Tauri commands**

In `commands.rs`, add proxy commands for the three new endpoints following the existing pattern.

- [ ] **Step 4: Verify TypeScript compiles**

Run: `npx vue-tsc --noEmit 2>&1`
Expected: No errors

- [ ] **Step 5: Commit**

```bash
git add src/lib/types.ts src/lib/api.ts src-tauri/src/commands.rs
git commit -m "feat: add signals types, API calls, and Tauri commands"
```

---

### Task 6: Update blocks store with signals support

**Files:**
- Modify: `src/stores/blocks.ts`

- [ ] **Step 1: Add signals state and actions**

Add to the store:

```typescript
  const signals = ref<Signal[]>([]);
  const signalsLoading = ref(false);

  async function fetchSignals(date?: string, blockId?: number) {
    signalsLoading.value = true;
    try {
      signals.value = await api.getSignals(date || selectedDate.value, blockId) as Signal[];
    } catch { signals.value = []; }
    finally { signalsLoading.value = false; }
  }

  async function splitBlock(blockId: number, signalId: number) {
    await api.splitBlock(blockId, signalId);
    await fetchBlocks();
  }

  async function mergeBlocks(blockIds: number[]) {
    await api.mergeBlocks(blockIds);
    await fetchBlocks();
  }
```

Return the new refs and functions from the store.

- [ ] **Step 2: Verify TypeScript compiles**

Run: `npx vue-tsc --noEmit 2>&1`

- [ ] **Step 3: Commit**

```bash
git add src/stores/blocks.ts
git commit -m "feat: add signals state and split/merge actions to blocks store"
```

---

### Task 7: Add signals toggle to ReviewDayView

**Files:**
- Modify: `src/views/ReviewDayView.vue`

- [ ] **Step 1: Add signals toggle section**

Add a CollapsibleGroup after the blocks table that shows raw signals:

```vue
<CollapsibleGroup title="Senales crudas" :default-open="false">
  <div class="signals-table-wrap">
    <table class="signals-table" v-if="blocksStore.signals.length">
      <thead>
        <tr>
          <th>Hora</th>
          <th>App</th>
          <th>Titulo</th>
          <th>Contexto</th>
          <th>Proyecto</th>
        </tr>
      </thead>
      <tbody>
        <tr v-for="s in blocksStore.signals" :key="s.id">
          <td>{{ formatTime(s.timestamp) }}</td>
          <td>{{ s.app_name }}</td>
          <td class="signal-title">{{ s.window_title }}</td>
          <td><span class="context-badge">{{ s.context_key }}</span></td>
          <td>{{ s.project_path ? s.project_path.split('/').pop() : '' }}</td>
        </tr>
      </tbody>
    </table>
    <EmptyState v-else message="Sin senales para esta fecha" />
  </div>
</CollapsibleGroup>
```

- [ ] **Step 2: Fetch signals when date changes**

In the `watch` or `onMounted` that fetches blocks, also fetch signals:

```typescript
watch(() => blocksStore.selectedDate, () => {
  blocksStore.fetchBlocks();
  blocksStore.fetchSignals();
});
```

- [ ] **Step 3: Add basic styles**

```css
.signals-table { width: 100%; font-size: 12px; border-collapse: collapse; }
.signals-table th { text-align: left; padding: 4px 8px; color: var(--text-secondary); border-bottom: 1px solid var(--border); }
.signals-table td { padding: 4px 8px; border-bottom: 1px solid var(--border); }
.signal-title { max-width: 300px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.context-badge { font-size: 11px; padding: 2px 6px; border-radius: 4px; background: var(--surface-2); }
```

- [ ] **Step 4: Verify TypeScript compiles**

Run: `npx vue-tsc --noEmit 2>&1`

- [ ] **Step 5: Run all daemon tests**

Run: `cd daemon && .venv/bin/python -m pytest tests/ -v 2>&1 | tail -5`

- [ ] **Step 6: Commit**

```bash
git add src/views/ReviewDayView.vue src/stores/blocks.ts
git commit -m "feat: add signals table toggle to ReviewDayView"
```
