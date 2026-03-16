# Wayland Capture Implementation Plan

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make mimir-capture detect the active window on GNOME Wayland via a GNOME Shell extension and D-Bus, while keeping X11 support intact.

**Architecture:** A GNOME Shell extension (`mimir-window-tracker`) registers a D-Bus service exposing `GetActiveWindow()`. The `LinuxProvider` detects X11 vs Wayland via `$XDG_SESSION_TYPE` and uses the appropriate backend. The extension ships inside the `mimir-capture` .deb.

**Tech Stack:** GNOME Shell extension (JavaScript ESM), dbus-next (Python async D-Bus), PyInstaller, dpkg-deb

**Spec:** `docs/superpowers/specs/2026-03-16-wayland-capture-design.md`

---

## File Structure

| Action | File | Purpose |
|--------|------|---------|
| Create | `daemon/mimir_daemon/platform/gnome_extension/metadata.json` | Extension metadata (GNOME 45-46) |
| Create | `daemon/mimir_daemon/platform/gnome_extension/extension.js` | Extension logic: D-Bus service |
| Modify | `daemon/mimir_daemon/platform/linux.py` | Add Wayland backend, detect session type |
| Modify | `daemon/mimir_daemon/capture.py:40-50` | Add backend info to /status |
| Create | `daemon/tests/test_platform_linux.py` | Tests for session detection + Wayland backend |
| Modify | `packaging/mimir-capture/DEBIAN/postinst` | Add extension enable instructions |
| Modify | `packaging/mimir-capture/DEBIAN/prerm` | Add extension disable instructions |

---

## Chunk 1: GNOME Shell Extension + Platform Layer

### Task 1: Create the GNOME Shell extension

**Files:**
- Create: `daemon/mimir_daemon/platform/gnome_extension/metadata.json`
- Create: `daemon/mimir_daemon/platform/gnome_extension/extension.js`

- [ ] **Step 1: Create metadata.json**

```json
{
    "uuid": "mimir-window-tracker@mimir.app",
    "name": "Mimir Window Tracker",
    "description": "Exposes active window info over D-Bus for Mimir capture",
    "shell-version": ["45", "46"],
    "version": 1
}
```

- [ ] **Step 2: Create extension.js**

```javascript
import Gio from 'gi://Gio';

const IFACE_XML = `
<node>
  <interface name="org.mimir.WindowTracker">
    <method name="GetActiveWindow">
      <arg type="u" direction="out" name="pid"/>
      <arg type="s" direction="out" name="wm_class"/>
      <arg type="s" direction="out" name="title"/>
    </method>
  </interface>
</node>`;

export default class MimirWindowTracker {
    enable() {
        this._dbusImpl = Gio.DBusExportedObject.wrapJSObject(IFACE_XML, this);
        this._dbusImpl.export(Gio.DBus.session, '/org/mimir/WindowTracker');
        this._ownerId = Gio.bus_own_name(
            Gio.BusType.SESSION,
            'org.mimir.WindowTracker',
            Gio.BusNameOwnerFlags.NONE,
            null, null, null
        );
    }

    disable() {
        if (this._dbusImpl) {
            this._dbusImpl.unexport();
            this._dbusImpl = null;
        }
        if (this._ownerId) {
            Gio.bus_unown_name(this._ownerId);
            this._ownerId = null;
        }
    }

    GetActiveWindow() {
        const focusWindow = global.display.get_focus_window();
        if (!focusWindow) return [0, '', ''];
        const pid = focusWindow.get_pid() || 0;
        const wmClass = focusWindow.get_wm_class() || '';
        const title = focusWindow.get_title() || '';
        return [pid, wmClass, title];
    }
}
```

- [ ] **Step 3: Commit**

```bash
git add daemon/mimir_daemon/platform/gnome_extension/
git commit -m "feat: add GNOME Shell extension for Wayland window tracking"
```

---

### Task 2: Add Wayland backend to LinuxProvider

**Files:**
- Modify: `daemon/mimir_daemon/platform/linux.py`
- Test: `daemon/tests/test_platform_linux.py`

- [ ] **Step 1: Write tests for session detection**

Create `daemon/tests/test_platform_linux.py`:

```python
"""Tests para el platform layer Linux (X11 + Wayland)."""

import os
import pytest
from unittest.mock import patch, AsyncMock, Mock

from mimir_daemon.platform.linux import LinuxProvider
from mimir_daemon.platform.base import WindowInfo


@pytest.mark.asyncio
async def test_setup_detects_wayland():
    """Detecta Wayland via XDG_SESSION_TYPE."""
    with patch.dict(os.environ, {"XDG_SESSION_TYPE": "wayland"}):
        provider = LinuxProvider()
        provider._connect_wayland_bus = AsyncMock()
        provider._dbus_task = None
        # Mock _listen_dbus para no conectar al bus real
        with patch.object(provider, '_listen_dbus', new_callable=AsyncMock):
            await provider.setup()
        assert provider._use_wayland is True
        provider._connect_wayland_bus.assert_called_once()


@pytest.mark.asyncio
async def test_setup_detects_x11():
    """Detecta X11 via XDG_SESSION_TYPE."""
    with patch.dict(os.environ, {"XDG_SESSION_TYPE": "x11"}):
        provider = LinuxProvider()
        provider._dbus_task = None
        with patch.object(provider, '_listen_dbus', new_callable=AsyncMock):
            await provider.setup()
        assert provider._use_wayland is False


@pytest.mark.asyncio
async def test_setup_missing_session_type_defaults_x11():
    """Sin XDG_SESSION_TYPE usa X11 como fallback."""
    env = {k: v for k, v in os.environ.items() if k != "XDG_SESSION_TYPE"}
    with patch.dict(os.environ, env, clear=True):
        provider = LinuxProvider()
        provider._dbus_task = None
        with patch.object(provider, '_listen_dbus', new_callable=AsyncMock):
            await provider.setup()
        assert provider._use_wayland is False


@pytest.mark.asyncio
async def test_wayland_get_active_window_returns_window_info():
    """Backend Wayland devuelve WindowInfo cuando la extension responde."""
    provider = LinuxProvider()
    provider._use_wayland = True
    provider._wayland_iface = AsyncMock()
    provider._wayland_iface.call_get_active_window = AsyncMock(
        return_value=(1234, "org.gnome.Terminal", "~/projects")
    )
    with patch.object(LinuxProvider, '_get_app_name_sync', return_value="gnome-terminal"):
        result = await provider.get_active_window()

    assert result is not None
    assert result.pid == 1234
    assert result.app_name == "gnome-terminal"
    assert result.window_title == "~/projects"


@pytest.mark.asyncio
async def test_wayland_no_focused_window_returns_none():
    """Backend Wayland devuelve None cuando pid=0."""
    provider = LinuxProvider()
    provider._use_wayland = True
    provider._wayland_iface = AsyncMock()
    provider._wayland_iface.call_get_active_window = AsyncMock(
        return_value=(0, "", "")
    )
    result = await provider.get_active_window()
    assert result is None


@pytest.mark.asyncio
async def test_wayland_extension_not_available():
    """Sin extension devuelve None y no crashea."""
    provider = LinuxProvider()
    provider._use_wayland = True
    provider._wayland_iface = None
    provider._connect_wayland_bus = AsyncMock()  # no conecta (iface sigue None)

    result = await provider.get_active_window()
    assert result is None


@pytest.mark.asyncio
async def test_wayland_connection_lost_resets_iface():
    """Si la conexion D-Bus se pierde, resetea iface para reconectar."""
    provider = LinuxProvider()
    provider._use_wayland = True
    provider._wayland_iface = AsyncMock()
    provider._wayland_iface.call_get_active_window = AsyncMock(
        side_effect=Exception("connection lost")
    )
    provider._wayland_bus = Mock()

    result = await provider.get_active_window()
    assert result is None
    assert provider._wayland_iface is None
    assert provider._wayland_bus is None


@pytest.mark.asyncio
async def test_x11_backend_used_when_not_wayland():
    """En X11, usa el backend xdotool."""
    provider = LinuxProvider()
    provider._use_wayland = False
    provider._get_active_window_x11 = AsyncMock(
        return_value=WindowInfo(pid=1, app_name="code", window_title="test.py")
    )

    result = await provider.get_active_window()
    assert result is not None
    assert result.app_name == "code"
    provider._get_active_window_x11.assert_called_once()
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd daemon && .venv/bin/python -m pytest tests/test_platform_linux.py -v 2>&1`
Expected: FAIL (methods don't exist yet)

- [ ] **Step 3: Implement Wayland backend in linux.py**

Replace the full content of `daemon/mimir_daemon/platform/linux.py`:

```python
"""Proveedor de plataforma Linux."""

import asyncio
import logging
import os
from datetime import datetime, timezone
from pathlib import Path

from .base import PlatformProvider, WindowInfo, SessionEvent

logger = logging.getLogger(__name__)


class LinuxProvider(PlatformProvider):
    """Captura de actividad en Linux (X11 + Wayland)."""

    def __init__(self) -> None:
        self._session_events: list[SessionEvent] = []
        self._dbus_task: asyncio.Task | None = None
        self._use_wayland: bool = False
        self._wayland_bus = None
        self._wayland_iface = None
        self._wayland_warning_shown: bool = False

    @property
    def backend(self) -> str:
        """Devuelve el backend activo: 'wayland' o 'x11'."""
        return "wayland" if self._use_wayland else "x11"

    async def setup(self) -> None:
        """Detecta entorno e inicia listeners D-Bus."""
        session_type = os.environ.get("XDG_SESSION_TYPE", "")
        self._use_wayland = session_type == "wayland"

        if self._use_wayland:
            logger.info("Sesion Wayland detectada, usando backend D-Bus")
            await self._connect_wayland_bus()
        elif session_type:
            logger.info("Sesion %s detectada, usando backend xdotool", session_type)
        else:
            logger.warning("XDG_SESSION_TYPE no definido, usando xdotool como fallback")

        # Listener de lock/unlock (funciona en ambos)
        try:
            self._dbus_task = asyncio.create_task(self._listen_dbus())
            logger.info("Listener D-Bus logind iniciado")
        except Exception as e:
            logger.warning("No se pudo iniciar listener D-Bus: %s", e)

    async def teardown(self) -> None:
        """Cancela listeners y desconecta buses."""
        if self._dbus_task:
            self._dbus_task.cancel()
            try:
                await self._dbus_task
            except asyncio.CancelledError:
                pass
        if self._wayland_bus:
            self._wayland_bus.disconnect()
            self._wayland_bus = None
            self._wayland_iface = None

    async def get_active_window(self) -> WindowInfo | None:
        """Obtiene la ventana activa usando el backend apropiado."""
        if self._use_wayland:
            return await self._get_active_window_wayland()
        return await self._get_active_window_x11()

    # --- Wayland backend ---

    async def _connect_wayland_bus(self) -> None:
        """Establece conexion persistente al D-Bus de la extension."""
        try:
            from dbus_next.aio import MessageBus

            self._wayland_bus = await MessageBus().connect()
            introspection = await self._wayland_bus.introspect(
                "org.mimir.WindowTracker", "/org/mimir/WindowTracker"
            )
            proxy = self._wayland_bus.get_proxy_object(
                "org.mimir.WindowTracker", "/org/mimir/WindowTracker", introspection
            )
            self._wayland_iface = proxy.get_interface("org.mimir.WindowTracker")
            logger.info("Conexion D-Bus con mimir-window-tracker establecida")
        except Exception as e:
            self._wayland_bus = None
            self._wayland_iface = None
            if not self._wayland_warning_shown:
                logger.warning("Extension mimir-window-tracker no disponible: %s", e)
                logger.warning(
                    "Activa la extension: gnome-extensions enable mimir-window-tracker@mimir.app"
                )
                self._wayland_warning_shown = True

    async def _get_active_window_wayland(self) -> WindowInfo | None:
        """Obtiene ventana activa via D-Bus (GNOME Wayland)."""
        if not self._wayland_iface:
            await self._connect_wayland_bus()
            if not self._wayland_iface:
                return None
        try:
            pid, wm_class, title = await self._wayland_iface.call_get_active_window()
            if pid == 0:
                return None
            app_name = self._get_app_name_sync(pid)
            return WindowInfo(pid=pid, app_name=app_name, window_title=title or "")
        except Exception:
            # Conexion perdida — reconectar en el proximo poll
            self._wayland_bus = None
            self._wayland_iface = None
            return None

    # --- X11 backend ---

    async def _get_active_window_x11(self) -> WindowInfo | None:
        """Obtiene la ventana activa usando xdotool."""
        try:
            window_id = await self._run_cmd("xdotool", "getactivewindow")
            if not window_id:
                return None

            window_id = window_id.strip()
            pid_str = await self._run_cmd("xdotool", "getwindowpid", window_id)
            title = await self._run_cmd("xdotool", "getwindowname", window_id)

            if not pid_str:
                return None

            pid = int(pid_str.strip())
            title = (title or "").strip()
            app_name = self._get_app_name_sync(pid)

            return WindowInfo(pid=pid, app_name=app_name, window_title=title)

        except FileNotFoundError:
            logger.warning(
                "xdotool no encontrado. Instalar con: sudo apt install xdotool"
            )
        except Exception as e:
            logger.debug("Error obteniendo ventana activa: %s", e)
        return None

    # --- Utilidades compartidas ---

    async def get_session_events(self) -> list[SessionEvent]:
        """Retorna y limpia eventos de sesion pendientes."""
        events = self._session_events.copy()
        self._session_events.clear()
        return events

    @staticmethod
    async def _run_cmd(*args: str) -> str | None:
        """Ejecuta un comando y devuelve stdout."""
        try:
            proc = await asyncio.create_subprocess_exec(
                *args,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout, _ = await asyncio.wait_for(proc.communicate(), timeout=3)
            if proc.returncode == 0:
                return stdout.decode()
        except asyncio.TimeoutError:
            logger.debug("Timeout ejecutando: %s", " ".join(args))
        except Exception:
            pass
        return None

    @staticmethod
    def _get_app_name_sync(pid: int) -> str:
        """Obtiene el nombre de la aplicacion leyendo /proc directamente."""
        try:
            comm_path = Path(f"/proc/{pid}/comm")
            if comm_path.exists():
                return comm_path.read_text().strip()
        except (PermissionError, OSError):
            pass

        try:
            cmdline_path = Path(f"/proc/{pid}/cmdline")
            if cmdline_path.exists():
                cmdline = cmdline_path.read_bytes().split(b"\x00")
                if cmdline:
                    name = cmdline[0].decode(errors="replace")
                    return Path(name).name
        except (PermissionError, OSError):
            pass

        return "unknown"

    async def _listen_dbus(self) -> None:
        """Escucha eventos de lock/unlock via D-Bus (logind)."""
        try:
            from dbus_next.aio import MessageBus
            from dbus_next import BusType

            bus = await MessageBus(bus_type=BusType.SYSTEM).connect()

            def on_lock_changed(locked: bool) -> None:
                event_type = "lock" if locked else "unlock"
                now = datetime.now(timezone.utc).isoformat()
                self._session_events.append(
                    SessionEvent(event_type=event_type, timestamp=now)
                )
                logger.info("Evento de sesion: %s", event_type)

            introspection = await bus.introspect(
                "org.freedesktop.login1",
                "/org/freedesktop/login1/session/auto",
            )
            obj = bus.get_proxy_object(
                "org.freedesktop.login1",
                "/org/freedesktop/login1/session/auto",
                introspection,
            )
            iface = obj.get_interface("org.freedesktop.DBus.Properties")
            iface.on_properties_changed(
                lambda _iface, changed, _inv: (
                    on_lock_changed(
                        changed.get("LockedHint", {}).get("value", False)
                    )
                    if "LockedHint" in changed
                    else None
                )
            )

            await asyncio.Future()

        except ImportError:
            logger.warning(
                "dbus-next no disponible; eventos lock/unlock deshabilitados"
            )
        except Exception as e:
            logger.warning("Error en listener D-Bus: %s", e)
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd daemon && .venv/bin/python -m pytest tests/test_platform_linux.py -v 2>&1`
Expected: 8 tests PASS

- [ ] **Step 5: Run all daemon tests to check no regressions**

Run: `cd daemon && .venv/bin/python -m pytest tests/ -v 2>&1`
Expected: 110+ tests PASS

- [ ] **Step 6: Commit**

```bash
git add daemon/mimir_daemon/platform/linux.py daemon/tests/test_platform_linux.py
git commit -m "feat: add Wayland backend to LinuxProvider with D-Bus support"
```

---

## Chunk 2: Status endpoint + Packaging

### Task 3: Add backend info to /status endpoint

**Files:**
- Modify: `daemon/mimir_daemon/capture.py:40-50`

- [ ] **Step 1: Update status endpoint**

In `capture.py`, modify `create_capture_app` to accept a `platform` parameter and add `backend` to status:

Change the function signature from:
```python
def create_capture_app(poller: Poller, version: str = VERSION) -> FastAPI:
```
To:
```python
def create_capture_app(poller: Poller, platform: PlatformProvider | None = None, version: str = VERSION) -> FastAPI:
```

Add to the status dict:
```python
"backend": getattr(platform, 'backend', 'unknown') if platform else "unknown",
```

Update the call in `run_capture`:
```python
app = create_capture_app(poller=poller, platform=platform, version=VERSION)
```

Add import at the top:
```python
from .platform.base import PlatformProvider
```

- [ ] **Step 2: Verify capture still starts**

Run: `cd daemon && .venv/bin/python -c "from mimir_daemon.capture import create_capture_app; print('OK')"`
Expected: OK

- [ ] **Step 3: Commit**

```bash
git add daemon/mimir_daemon/capture.py
git commit -m "feat: add backend info to /status endpoint"
```

---

### Task 4: Update packaging for GNOME extension

**Files:**
- Modify: `packaging/mimir-capture/DEBIAN/postinst`
- Modify: `packaging/mimir-capture/DEBIAN/prerm`
- Modify: `scripts/build.sh` (package_deb function)

- [ ] **Step 1: Update postinst**

Replace content of `packaging/mimir-capture/DEBIAN/postinst`:

```bash
#!/bin/bash
if [ "$1" = "configure" ]; then
    echo ""
    echo "=== mimir-capture instalado ==="
    echo "Para activar la captura automatica, ejecuta como tu usuario:"
    echo "  systemctl --user daemon-reload"
    echo "  systemctl --user enable --now mimir-capture"
    echo ""
    echo "Si usas Wayland (GNOME), activa la extension:"
    echo "  gnome-extensions enable mimir-window-tracker@mimir.app"
    echo "  (Requiere cerrar sesion y volver a entrar)"
    echo ""
fi
```

- [ ] **Step 2: Update prerm**

Replace content of `packaging/mimir-capture/DEBIAN/prerm`:

```bash
#!/bin/bash
if [ "$1" = "remove" ]; then
    echo ""
    echo "=== Desinstalando mimir-capture ==="
    echo "Si el servicio esta activo, desactivalo:"
    echo "  systemctl --user disable --now mimir-capture"
    echo ""
    echo "Si activaste la extension de GNOME, desactivala:"
    echo "  gnome-extensions disable mimir-window-tracker@mimir.app"
    echo ""
fi
```

- [ ] **Step 3: Add extension copy to package_deb() in build.sh**

In `scripts/build.sh`, inside the `package_deb()` function, after the line that copies mimir-capture binary (`cp "$DIST_DIR/mimir-capture" "$CAPTURE_PKG/usr/bin/mimir-capture"`), add:

```bash
    # Copiar extension GNOME Shell
    GNOME_EXT_DIR="$CAPTURE_PKG/usr/share/gnome-shell/extensions/mimir-window-tracker@mimir.app"
    mkdir -p "$GNOME_EXT_DIR"
    cp "$PROJECT_DIR/daemon/mimir_daemon/platform/gnome_extension/metadata.json" "$GNOME_EXT_DIR/"
    cp "$PROJECT_DIR/daemon/mimir_daemon/platform/gnome_extension/extension.js" "$GNOME_EXT_DIR/"
    chmod 644 "$GNOME_EXT_DIR/metadata.json" "$GNOME_EXT_DIR/extension.js"
```

- [ ] **Step 4: Verify build script syntax**

Run: `bash -n scripts/build.sh`
Expected: No output (no errors)

- [ ] **Step 5: Commit**

```bash
git add packaging/mimir-capture/DEBIAN/postinst packaging/mimir-capture/DEBIAN/prerm scripts/build.sh
git commit -m "feat: include GNOME Shell extension in mimir-capture .deb"
```

---

## Chunk 3: Manual verification

### Task 5: Test on this machine (Wayland)

- [ ] **Step 1: Install the extension locally**

```bash
mkdir -p ~/.local/share/gnome-shell/extensions/mimir-window-tracker@mimir.app/
cp daemon/mimir_daemon/platform/gnome_extension/metadata.json ~/.local/share/gnome-shell/extensions/mimir-window-tracker@mimir.app/
cp daemon/mimir_daemon/platform/gnome_extension/extension.js ~/.local/share/gnome-shell/extensions/mimir-window-tracker@mimir.app/
gnome-extensions enable mimir-window-tracker@mimir.app
```

Note: requires logout/login for the extension to load.

- [ ] **Step 2: After re-login, verify extension via D-Bus**

```bash
gdbus call --session --dest org.mimir.WindowTracker --object-path /org/mimir/WindowTracker --method org.mimir.WindowTracker.GetActiveWindow
```

Expected: `(uint32 <pid>, '<wm_class>', '<window_title>')`

- [ ] **Step 3: Test the Python backend directly**

```bash
cd daemon && .venv/bin/python -c "
import asyncio
from mimir_daemon.platform.linux import LinuxProvider

async def test():
    p = LinuxProvider()
    await p.setup()
    print('Backend:', p.backend)
    w = await p.get_active_window()
    print('Window:', w)
    await p.teardown()

asyncio.run(test())
"
```

Expected: `Backend: wayland` and `Window: WindowInfo(pid=..., app_name='...', window_title='...')`

- [ ] **Step 4: Run full daemon tests**

Run: `cd daemon && .venv/bin/python -m pytest tests/ -v 2>&1`
Expected: 118+ tests PASS (110 existing + 8 new)

- [ ] **Step 5: Final commit**

```bash
git add -A
git commit -m "feat: Wayland capture support via GNOME Shell extension"
```
