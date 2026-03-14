# Separación Capture / Server — Plan de Implementación

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Separar el daemon monolítico en dos procesos: mimir-capture (siempre corriendo, captura actividad, puerto 9476) y mimir-server (lanzado por Tauri, API completa, puerto 9477).

**Architecture:** mimir-capture es un proceso ligero (poller + block_manager + tray + health endpoint mínimo) que escribe en SQLite. mimir-server es el FastAPI completo (bloques CRUD, Odoo, GitLab, IA) que Tauri lanza como child process y mata al cerrar. Ambos comparten la misma SQLite.

**Tech Stack:** Python (FastAPI, uvicorn, asyncio), Rust (Tauri 2, std::process::Command), SQLite compartida.

---

### Task 1: Crear entry point capture.py

**Files:**
- Create: `daemon/mimir_daemon/capture.py`
- Test: `daemon/tests/test_capture.py`

**Step 1: Create capture.py**

Create `daemon/mimir_daemon/capture.py`:

```python
"""Entry point del proceso de captura de actividad.

Proceso ligero que corre siempre como servicio systemd.
Solo captura actividad y escribe bloques en SQLite.
Expone un endpoint HTTP mínimo (/health, /status) en puerto 9476.
"""

import argparse
import asyncio
import logging
import sys

import uvicorn
from fastapi import FastAPI

from .config import DaemonConfig
from .db import Database
from .platform import get_platform_provider
from .block_manager import BlockManager
from .poller import Poller
from .tray import TrayIcon

logger = logging.getLogger("mimir_capture")

VERSION = "0.1.0"
CAPTURE_PORT = 9476


def create_capture_app(poller: Poller, version: str = VERSION) -> FastAPI:
    """Crea la app FastAPI mínima del capture."""
    from datetime import datetime, timezone

    app = FastAPI(title="Mimir Capture", version=version)
    start_time = datetime.now(timezone.utc)

    @app.get("/health")
    async def health() -> dict:
        return {"status": "ok", "service": "capture", "version": version}

    @app.get("/status")
    async def status() -> dict:
        now = datetime.now(timezone.utc)
        uptime = int((now - start_time).total_seconds())
        return {
            "running": poller.is_running,
            "mode": "paused" if poller._paused else "active",
            "uptime_seconds": uptime,
            "last_poll": poller.last_poll.isoformat() if poller.last_poll else None,
            "version": version,
        }

    return app


def parse_args() -> argparse.Namespace:
    """Parsea argumentos de línea de comandos."""
    parser = argparse.ArgumentParser(description="Mimir Capture Daemon")
    parser.add_argument(
        "--port", type=int, default=CAPTURE_PORT,
        help=f"Puerto HTTP (por defecto: {CAPTURE_PORT})",
    )
    return parser.parse_args()


async def run_capture(args: argparse.Namespace) -> None:
    """Arranca el proceso de captura."""
    config = DaemonConfig.load()
    config.save()

    logging.basicConfig(
        level=getattr(logging, config.log_level),
        format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    logger.info("Iniciando Mimir Capture v%s", VERSION)

    db = Database(config.db_path)
    await db.connect()

    platform = get_platform_provider()
    await platform.setup()

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

    app = create_capture_app(poller=poller, version=VERSION)

    tray = TrayIcon(
        on_mode_change=lambda mode: (
            poller.pause() if mode == "paused" else poller.resume()
        ),
        on_quit=lambda: poller.stop(),
    )
    tray.start()

    poller_task = asyncio.create_task(poller.run())

    uvicorn_config = uvicorn.Config(
        app,
        host=config.host,
        port=args.port,
        log_level=config.log_level.lower(),
    )
    server = uvicorn.Server(uvicorn_config)

    logger.info("Capture HTTP en http://%s:%d", config.host, args.port)

    try:
        await server.serve()
    except asyncio.CancelledError:
        pass
    finally:
        poller.stop()
        poller_task.cancel()
        try:
            await poller_task
        except asyncio.CancelledError:
            pass
        tray.stop()
        await platform.teardown()
        await db.close()
        logger.info("Capture detenido")


def main() -> None:
    """Entry point CLI."""
    args = parse_args()
    try:
        asyncio.run(run_capture(args))
    except KeyboardInterrupt:
        logger.info("Capture interrumpido por usuario")
        sys.exit(0)


if __name__ == "__main__":
    main()
```

**Step 2: Write test**

Create `daemon/tests/test_capture.py`:

```python
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
```

**Step 3: Run tests**

Run: `cd /opt/mimir-app/daemon && .venv/bin/python -m pytest tests/test_capture.py -v`
Expected: ALL PASS

**Step 4: Commit**

```bash
git add daemon/mimir_daemon/capture.py daemon/tests/test_capture.py
git commit -m "feat: create mimir-capture entry point with minimal HTTP"
```

---

### Task 2: Crear entry point api_server.py

**Files:**
- Create: `daemon/mimir_daemon/api_server.py`
- Test: `daemon/tests/test_api_server.py`

**Step 1: Create api_server.py**

Create `daemon/mimir_daemon/api_server.py`:

```python
"""Entry point del servidor API.

Proceso lanzado por la app Tauri cuando se abre.
Provee la API completa: bloques CRUD, Odoo, GitLab, IA, config.
Se cierra cuando la app Tauri se cierra.
"""

import argparse
import asyncio
import logging
import sys

import uvicorn

from .config import DaemonConfig
from .db import Database
from .integrations.registry import IntegrationRegistry
from .sources.registry import SourceRegistry
from .ai.service import AIService
from .server import create_server_app

logger = logging.getLogger("mimir_server")

VERSION = "0.1.0"
SERVER_PORT = 9477


def parse_args() -> argparse.Namespace:
    """Parsea argumentos de línea de comandos."""
    parser = argparse.ArgumentParser(description="Mimir API Server")
    parser.add_argument(
        "--port", type=int, default=SERVER_PORT,
        help=f"Puerto HTTP (por defecto: {SERVER_PORT})",
    )
    parser.add_argument(
        "--mock", action="store_true",
        help="Usar datos mock en lugar de conectar con Odoo/GitLab reales",
    )
    return parser.parse_args()


async def run_server(args: argparse.Namespace) -> None:
    """Arranca el servidor API."""
    config = DaemonConfig.load()

    logging.basicConfig(
        level=getattr(logging, config.log_level),
        format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    logger.info("Iniciando Mimir Server v%s", VERSION)

    db = Database(config.db_path)
    await db.connect()

    registry = IntegrationRegistry()
    if args.mock:
        from .integrations.mock import MockTimesheetClient
        registry.set_timesheet_client(MockTimesheetClient())
        logger.info("Usando cliente mock de timesheet")

    source_registry = SourceRegistry()
    ai_service = AIService(db=db, provider=None)

    app = create_server_app(
        db=db,
        registry=registry,
        ai_service=ai_service,
        source_registry=source_registry,
        version=VERSION,
    )

    uvicorn_config = uvicorn.Config(
        app,
        host=config.host,
        port=args.port,
        log_level=config.log_level.lower(),
    )
    server = uvicorn.Server(uvicorn_config)

    logger.info("Server HTTP en http://%s:%d", config.host, args.port)

    try:
        await server.serve()
    except asyncio.CancelledError:
        pass
    finally:
        await db.close()
        logger.info("Server detenido")


def main() -> None:
    """Entry point CLI."""
    args = parse_args()
    try:
        asyncio.run(run_server(args))
    except KeyboardInterrupt:
        logger.info("Server interrumpido por usuario")
        sys.exit(0)


if __name__ == "__main__":
    main()
```

**Step 2: Refactor server.py — rename create_app to create_server_app, remove Poller dependency**

In `daemon/mimir_daemon/server.py`:

a) Remove import of `Poller`
b) Rename `create_app` to `create_server_app`
c) Remove `poller` parameter
d) Remove mode endpoint (that controls the poller) — mode control stays in capture via tray
e) Update status endpoint to not need poller — server has its own uptime

The function signature becomes:

```python
def create_server_app(
    db: Database,
    registry: IntegrationRegistry | None = None,
    ai_service: "AIService | None" = None,
    source_registry: SourceRegistry | None = None,
    version: str = "0.1.0",
) -> FastAPI:
```

Remove the mode endpoint and update the status endpoint:

```python
    @app.get("/status")
    async def status() -> dict:
        now = datetime.now(timezone.utc)
        uptime = int((now - start_time).total_seconds())
        blocks_today = await db.count_blocks_today()
        return {
            "running": True,
            "mode": "active",
            "uptime_seconds": uptime,
            "last_poll": None,
            "blocks_today": blocks_today,
            "version": version,
        }
```

**Step 3: Update test_server.py**

Update imports and fixtures:
- Remove `Poller` from imports and fixture
- Change `create_app` to `create_server_app`
- Remove `MockPlatform` (no longer needed in server tests)
- Remove `test_set_mode` test (mode is now in capture)
- Update `app` fixture to not create poller

**Step 4: Write test for api_server module**

Create `daemon/tests/test_api_server.py`:

```python
"""Tests para el entry point api_server."""

import pytest
from mimir_daemon.api_server import parse_args, SERVER_PORT


def test_parse_args_defaults():
    """parse_args devuelve defaults correctos."""
    # Simular sin argumentos
    import sys
    old_argv = sys.argv
    sys.argv = ["mimir-server"]
    try:
        args = parse_args()
        assert args.port == SERVER_PORT
        assert args.mock is False
    finally:
        sys.argv = old_argv
```

**Step 5: Run all tests**

Run: `cd /opt/mimir-app/daemon && .venv/bin/python -m pytest tests/ -v`
Expected: ALL PASS

**Step 6: Commit**

```bash
git add daemon/mimir_daemon/api_server.py daemon/mimir_daemon/server.py daemon/tests/
git commit -m "feat: create mimir-server entry point, refactor server.py to remove Poller dependency"
```

---

### Task 3: Actualizar __main__.py y PyInstaller specs

**Files:**
- Modify: `daemon/mimir_daemon/__main__.py`
- Modify: `daemon/mimir_daemon/_pyinstaller_entry.py`
- Create: `daemon/mimir_daemon/_pyinstaller_server_entry.py`
- Modify: `daemon/mimir_daemon.spec` (rename to `mimir_capture.spec`)
- Create: `daemon/mimir_server.spec`
- Modify: `daemon/pyproject.toml` (add entry points)

**Step 1: Update __main__.py to launch capture by default**

```python
"""Permite ejecutar con `python -m mimir_daemon`."""

from .capture import main

main()
```

**Step 2: Update _pyinstaller_entry.py for capture**

```python
"""Entry point PyInstaller para mimir-capture."""

from mimir_daemon.capture import main

main()
```

**Step 3: Create _pyinstaller_server_entry.py**

```python
"""Entry point PyInstaller para mimir-server."""

from mimir_daemon.api_server import main

main()
```

**Step 4: Rename mimir_daemon.spec to mimir_capture.spec and update**

Rename the file and change:
- Entry point to `_pyinstaller_entry.py` (already points to capture)
- Output name to `mimir-capture`
- Remove AI/integrations/sources from hiddenimports (not needed in capture)

Keep only these hiddenimports:
```python
    hiddenimports=[
        "uvicorn.logging",
        "uvicorn.loops",
        "uvicorn.loops.auto",
        "uvicorn.protocols",
        "uvicorn.protocols.http",
        "uvicorn.protocols.http.auto",
        "uvicorn.protocols.websockets",
        "uvicorn.protocols.websockets.auto",
        "uvicorn.lifespan",
        "uvicorn.lifespan.on",
        "uvicorn.lifespan.off",
        "mimir_daemon.platform.linux",
        "aiosqlite",
        "pystray",
        "PIL",
        "dbus_next",
    ],
```

Name: `"mimir-capture"`

**Step 5: Create mimir_server.spec**

Same structure but:
- Entry point: `_pyinstaller_server_entry.py`
- Name: `"mimir-server"`
- Hiddenimports include everything (integrations, AI, sources, etc.):

```python
    hiddenimports=[
        "uvicorn.logging",
        "uvicorn.loops",
        "uvicorn.loops.auto",
        "uvicorn.protocols",
        "uvicorn.protocols.http",
        "uvicorn.protocols.http.auto",
        "uvicorn.protocols.websockets",
        "uvicorn.protocols.websockets.auto",
        "uvicorn.lifespan",
        "uvicorn.lifespan.on",
        "uvicorn.lifespan.off",
        "mimir_daemon.integrations.odoo_v11",
        "mimir_daemon.integrations.odoo_v16",
        "mimir_daemon.integrations.mock",
        "mimir_daemon.ai.gemini",
        "mimir_daemon.ai.claude_provider",
        "mimir_daemon.ai.openai_provider",
        "mimir_daemon.sources.gitlab",
        "aiosqlite",
        "httpx",
    ],
```

**Step 6: Update pyproject.toml entry points**

```toml
[project.scripts]
mimir-capture = "mimir_daemon.capture:main"
mimir-server = "mimir_daemon.api_server:main"
mimir-daemon = "mimir_daemon.capture:main"
```

**Step 7: Run tests**

Run: `cd /opt/mimir-app/daemon && .venv/bin/python -m pytest tests/ -v`
Expected: ALL PASS

**Step 8: Commit**

```bash
git add daemon/mimir_daemon/ daemon/mimir_capture.spec daemon/mimir_server.spec daemon/pyproject.toml
git rm daemon/mimir_daemon.spec
git commit -m "feat: separate PyInstaller specs for capture and server"
```

---

### Task 4: Tauri lanza mimir-server como child process

**Files:**
- Modify: `src-tauri/src/lib.rs`
- Create: `src-tauri/src/server_process.rs`

**Step 1: Create server_process.rs**

Create `src-tauri/src/server_process.rs`:

```rust
use std::process::{Child, Command};
use std::sync::Mutex;

static SERVER_PROCESS: Mutex<Option<Child>> = Mutex::new(None);

/// Intenta encontrar el binario mimir-server en varias ubicaciones.
fn find_server_binary() -> Option<String> {
    let candidates = [
        // Binario instalado en ~/.local/bin
        format!(
            "{}/.local/bin/mimir-server",
            std::env::var("HOME").unwrap_or_default()
        ),
        // Binario en dist/ (desarrollo)
        "dist/daemon/mimir-server".to_string(),
        // Relativo al ejecutable actual
        {
            let exe = std::env::current_exe().ok()?;
            let dir = exe.parent()?;
            dir.join("mimir-server").to_string_lossy().to_string()
        },
    ];

    for path in &candidates {
        if std::path::Path::new(path).exists() {
            return Some(path.clone());
        }
    }
    None
}

/// Arranca mimir-server como proceso hijo.
pub fn start_server() {
    let mut guard = SERVER_PROCESS.lock().unwrap();
    if guard.is_some() {
        return; // Ya está corriendo
    }

    if let Some(binary) = find_server_binary() {
        match Command::new(&binary).spawn() {
            Ok(child) => {
                log::info!("mimir-server arrancado (pid: {}, binary: {})", child.id(), binary);
                *guard = Some(child);
            }
            Err(e) => {
                log::error!("Error arrancando mimir-server ({}): {}", binary, e);
            }
        }
    } else {
        // Fallback: intentar con python
        match Command::new("python3")
            .args(["-m", "mimir_daemon.api_server"])
            .spawn()
        {
            Ok(child) => {
                log::info!("mimir-server arrancado via python3 (pid: {})", child.id());
                *guard = Some(child);
            }
            Err(e) => {
                log::warn!("No se pudo arrancar mimir-server: {}", e);
            }
        }
    }
}

/// Mata el proceso mimir-server.
pub fn stop_server() {
    let mut guard = SERVER_PROCESS.lock().unwrap();
    if let Some(mut child) = guard.take() {
        log::info!("Deteniendo mimir-server (pid: {})", child.id());
        let _ = child.kill();
        let _ = child.wait();
    }
}
```

**Step 2: Update lib.rs**

```rust
mod clients;
mod commands;
mod models;
mod server_process;

use commands::{auth, config, daemon};

#[cfg_attr(mobile, tauri::mobile_entry_point)]
pub fn run() {
    // Arranca mimir-server al iniciar la app
    server_process::start_server();

    tauri::Builder::default()
        .plugin(tauri_plugin_opener::init())
        .on_window_event(|window, event| {
            if let tauri::WindowEvent::Destroyed = event {
                // Solo cuando se cierra la última ventana
                if window.label() == "main" {
                    server_process::stop_server();
                }
            }
        })
        .invoke_handler(tauri::generate_handler![
            // Daemon proxy
            daemon::get_daemon_status,
            daemon::daemon_health_check,
            daemon::set_daemon_mode,
            daemon::get_blocks,
            daemon::confirm_block,
            daemon::update_block,
            daemon::delete_block,
            daemon::sync_blocks_to_odoo,
            daemon::retry_sync_block,
            daemon::get_odoo_projects,
            daemon::get_odoo_tasks,
            daemon::get_timesheet_entries,
            daemon::get_issues,
            daemon::get_merge_requests,
            daemon::push_config_to_daemon,
            daemon::generate_block_description,
            daemon::get_integration_status,
            // Config
            config::get_config,
            config::save_config,
            // Auth
            auth::store_credential,
            auth::get_credential,
            auth::delete_credential,
        ])
        .run(tauri::generate_context!())
        .expect("error while running tauri application");
}
```

**Step 3: Add log dependency to Cargo.toml**

Add `log = "0.4"` to dependencies in `src-tauri/Cargo.toml`.

**Step 4: Verify Rust compiles**

Run: `cd /opt/mimir-app/src-tauri && cargo check`
Expected: OK

**Step 5: Commit**

```bash
git add src-tauri/src/server_process.rs src-tauri/src/lib.rs src-tauri/Cargo.toml
git commit -m "feat: Tauri launches mimir-server as child process"
```

---

### Task 5: Actualizar DaemonClient para health check dual

**Files:**
- Modify: `src-tauri/src/commands/daemon.rs`
- Modify: `src/stores/daemon.ts`
- Modify: `src/views/DashboardView.vue`

**Step 1: Add capture health check command**

In `src-tauri/src/commands/daemon.rs`, add:

```rust
#[tauri::command]
pub async fn capture_health_check() -> Result<bool, String> {
    let client = DaemonClient::new(9476);
    Ok(client.health_check().await)
}
```

Register in `lib.rs` invoke_handler.

**Step 2: Update daemon store to track both services**

In `src/stores/daemon.ts`, add:

```typescript
const captureConnected = ref(false);

async function captureHealthCheck(): Promise<boolean> {
    try {
        if (await isTauri()) {
            const ok = await tauriInvoke<boolean>('capture_health_check');
            captureConnected.value = ok;
            return ok;
        }
        // Browser fallback
        try {
            const resp = await fetch('http://127.0.0.1:9476/health');
            captureConnected.value = resp.ok;
            return resp.ok;
        } catch {
            captureConnected.value = false;
            return false;
        }
    } catch {
        captureConnected.value = false;
        return false;
    }
}
```

Add `captureConnected` and `captureHealthCheck` to the return.

**Step 3: Update DashboardView**

Show status of both processes in the daemon card:
- "Capture: Activo/Inactivo"
- "Server: Activo/Inactivo"

**Step 4: Update App.vue health check**

In `App.vue`, check both:

```typescript
const captureOk = await daemonStore.captureHealthCheck();
const ok = await daemonStore.healthCheck();
```

**Step 5: Verify TypeScript**

Run: `cd /opt/mimir-app && npx vue-tsc --noEmit`
Expected: 0 errors

**Step 6: Commit**

```bash
git add src-tauri/src/commands/daemon.rs src-tauri/src/lib.rs src/stores/daemon.ts src/views/DashboardView.vue src/App.vue
git commit -m "feat: dual health check for capture and server processes"
```

---

### Task 6: Actualizar build.sh e install-service.sh

**Files:**
- Modify: `scripts/build.sh`
- Modify: `daemon/install-service.sh`

**Step 1: Update build.sh**

Update the daemon build step to generate TWO binaries:

```bash
build_daemon() {
    echo "--- [daemon] Construyendo capture + server (PyInstaller) ---"
    cd "$DAEMON_DIR"

    if [ ! -d ".venv" ]; then
        python3 -m venv .venv
    fi
    .venv/bin/pip install --quiet --upgrade pip
    .venv/bin/pip install --quiet -e ".[dev]"

    mkdir -p "$DIST_DIR"

    # Build capture
    .venv/bin/pyinstaller mimir_capture.spec \
        --distpath "$DIST_DIR" \
        --workpath /tmp/mimir-build-capture \
        --clean --noconfirm
    echo "Capture binary: $DIST_DIR/mimir-capture"

    # Build server
    .venv/bin/pyinstaller mimir_server.spec \
        --distpath "$DIST_DIR" \
        --workpath /tmp/mimir-build-server \
        --clean --noconfirm
    echo "Server binary: $DIST_DIR/mimir-server"

    cp "$DAEMON_DIR/install-service.sh" "$DIST_DIR/install-daemon.sh"
    chmod +x "$DIST_DIR/install-daemon.sh"
}
```

**Step 2: Update install-service.sh**

Now installs TWO binaries: `mimir-capture` (as systemd service) and `mimir-server` (copied to ~/.local/bin for Tauri to find):

Update the binary detection to look for `mimir-capture` and `mimir-server` separately. The systemd service only runs `mimir-capture`. `mimir-server` is just copied to `~/.local/bin`.

**Step 3: Commit**

```bash
git add scripts/build.sh daemon/install-service.sh
git commit -m "feat: update build and install scripts for capture/server split"
```

---

### Task 7: Limpiar main.py legacy + actualizar PROGRESS.md

**Files:**
- Modify: `daemon/mimir_daemon/main.py` (keep as alias to capture)
- Modify: `PROGRESS.md`

**Step 1: Simplify main.py**

Replace `daemon/mimir_daemon/main.py` with a thin wrapper:

```python
"""Legacy entry point — redirige a capture.

Mantenido para compatibilidad con instalaciones existentes.
"""

from .capture import main

if __name__ == "__main__":
    main()
```

**Step 2: Run full test suite**

Run: `cd /opt/mimir-app/daemon && .venv/bin/python -m pytest tests/ -v`
Expected: ALL PASS

**Step 3: Run TypeScript check**

Run: `cd /opt/mimir-app && npx vue-tsc --noEmit`
Expected: 0 errors

**Step 4: Run Rust check**

Run: `cd /opt/mimir-app/src-tauri && cargo check`
Expected: OK

**Step 5: Update PROGRESS.md**

Add section for the capture/server split refactor.

**Step 6: Commit**

```bash
git add daemon/mimir_daemon/main.py PROGRESS.md
git commit -m "refactor: complete capture/server split"
```
