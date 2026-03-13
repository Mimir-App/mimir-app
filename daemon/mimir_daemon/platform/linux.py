"""Proveedor de plataforma Linux."""

import asyncio
import logging
from datetime import datetime, timezone

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
        except Exception as e:
            logger.warning("No se pudo iniciar listener D-Bus: %s", e)

    async def teardown(self) -> None:
        """Cancela el listener de D-Bus."""
        if self._dbus_task:
            self._dbus_task.cancel()

    async def get_active_window(self) -> WindowInfo | None:
        """Obtiene la ventana activa usando xdotool."""
        try:
            proc = await asyncio.create_subprocess_exec(
                "xdotool", "getactivewindow", "getwindowpid", "getactivewindow", "getwindowname",
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout, _ = await asyncio.wait_for(proc.communicate(), timeout=5)
            lines = stdout.decode().strip().split("\n")
            if len(lines) >= 2:
                pid = int(lines[0])
                title = lines[1] if len(lines) > 1 else ""
                app_name = await self._get_app_name(pid)
                return WindowInfo(pid=pid, app_name=app_name, window_title=title)
        except Exception as e:
            logger.debug("Error obteniendo ventana activa: %s", e)
        return None

    async def get_session_events(self) -> list[SessionEvent]:
        """Retorna y limpia eventos de sesión pendientes."""
        events = self._session_events.copy()
        self._session_events.clear()
        return events

    async def _get_app_name(self, pid: int) -> str:
        """Obtiene el nombre de la aplicación desde /proc."""
        try:
            proc = await asyncio.create_subprocess_exec(
                "cat", f"/proc/{pid}/comm",
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout, _ = await asyncio.wait_for(proc.communicate(), timeout=2)
            return stdout.decode().strip()
        except Exception:
            return "unknown"

    async def _listen_dbus(self) -> None:
        """Escucha eventos de lock/unlock via D-Bus."""
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
                logger.info("Evento de sesión: %s", event_type)

            # Escuchar señal de logind
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
                    on_lock_changed(changed.get("LockedHint", {}).get("value", False))
                    if "LockedHint" in changed
                    else None
                )
            )

            # Mantener el bus activo
            await asyncio.Future()
        except Exception as e:
            logger.warning("Error en listener D-Bus: %s", e)
