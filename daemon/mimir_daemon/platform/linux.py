"""Proveedor de plataforma Linux."""

import asyncio
import logging
from datetime import datetime, timezone
from pathlib import Path

from .base import PlatformProvider, WindowInfo, SessionEvent

logger = logging.getLogger(__name__)


class LinuxProvider(PlatformProvider):
    """Captura de actividad en Linux usando xdotool y D-Bus."""

    def __init__(self) -> None:
        self._session_events: list[SessionEvent] = []
        self._dbus_task: asyncio.Task | None = None

    async def setup(self) -> None:
        """Inicia listener de D-Bus para lock/unlock."""
        try:
            self._dbus_task = asyncio.create_task(self._listen_dbus())
            logger.info("Listener D-Bus iniciado")
        except Exception as e:
            logger.warning("No se pudo iniciar listener D-Bus: %s", e)

    async def teardown(self) -> None:
        """Cancela el listener de D-Bus."""
        if self._dbus_task:
            self._dbus_task.cancel()
            try:
                await self._dbus_task
            except asyncio.CancelledError:
                pass

    async def get_active_window(self) -> WindowInfo | None:
        """Obtiene la ventana activa usando xdotool."""
        try:
            # Obtener ID de ventana activa
            window_id = await self._run_cmd("xdotool", "getactivewindow")
            if not window_id:
                return None

            window_id = window_id.strip()

            # Obtener PID y titulo en llamadas separadas (mas fiable)
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

        # Fallback: leer cmdline
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

            # Escuchar senal de logind
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

            # Mantener el bus activo
            await asyncio.Future()

        except ImportError:
            logger.warning(
                "dbus-next no disponible; eventos lock/unlock deshabilitados"
            )
        except Exception as e:
            logger.warning("Error en listener D-Bus: %s", e)
