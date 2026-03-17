"""Proveedor de plataforma Linux."""

import asyncio
import logging
import os
from datetime import datetime, timezone
from pathlib import Path

from .base import PlatformProvider, WindowInfo, SessionEvent, SystemContext

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

        if not self._use_wayland:
            import subprocess
            try:
                result = subprocess.run(
                    ["xdotool", "getactivewindow"],
                    capture_output=True, text=True, timeout=3
                )
                if result.returncode == 0:
                    logger.info("xdotool verificado correctamente (ventana: %s)", result.stdout.strip())
                else:
                    logger.error("xdotool fallo al arrancar: %s", result.stderr.strip())
            except FileNotFoundError:
                logger.error("xdotool no esta instalado. La captura X11 NO funcionara.")
            except Exception as e:
                logger.error("Error verificando xdotool: %s", e)

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
            logger.error(
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

    # --- System context (idle, audio, workspace) ---

    # Apps conocidas de videollamada
    MEETING_APPS = frozenset({
        "zoom", "teams", "slack", "discord", "skype",
        "webex", "google-meet", "jitsi",
    })

    # Patrones en titulos/media que indican reunion
    MEETING_KEYWORDS = frozenset({
        "meet.google.com", "zoom", "teams", "huddle",
        "meeting", "call", "webex", "jitsi",
    })

    async def get_system_context(self) -> SystemContext:
        """Obtiene idle time, audio activo y workspace."""
        idle_ms = await self._get_idle_time()
        audio_app, audio_media, is_meeting = await self._get_audio_info()
        workspace = await self._get_workspace()
        return SystemContext(
            idle_ms=idle_ms,
            audio_app=audio_app,
            audio_media=audio_media,
            is_meeting=is_meeting,
            workspace=workspace,
        )

    async def _get_idle_time(self) -> int:
        """Obtiene milisegundos de inactividad via Mutter IdleMonitor."""
        try:
            output = await self._run_cmd(
                "gdbus", "call", "--session",
                "--dest", "org.gnome.Mutter.IdleMonitor",
                "--object-path", "/org/gnome/Mutter/IdleMonitor/Core",
                "--method", "org.gnome.Mutter.IdleMonitor.GetIdletime",
            )
            if output:
                # Output: "(uint64 1234,)"
                num = output.strip().strip("()").split()[-1].rstrip(",)")
                return int(num)
        except Exception as e:
            logger.debug("Error obteniendo idle time: %s", e)
        return 0

    async def _get_audio_info(self) -> tuple[str | None, str | None, bool]:
        """Detecta streams de audio activos via pactl. Devuelve (app, media, is_meeting)."""
        try:
            output = await self._run_cmd("pactl", "list", "sink-inputs")
            if not output:
                return None, None, False

            app_name = None
            media_name = None
            is_meeting = False

            for line in output.splitlines():
                line = line.strip()
                if line.startswith("application.process.binary"):
                    app_name = line.split("=", 1)[-1].strip().strip('"')
                elif line.startswith("application.name"):
                    val = line.split("=", 1)[-1].strip().strip('"')
                    if not app_name:
                        app_name = val
                elif line.startswith("media.name"):
                    media_name = line.split("=", 1)[-1].strip().strip('"')

            if app_name:
                app_lower = app_name.lower()
                if app_lower in self.MEETING_APPS:
                    is_meeting = True
                elif media_name:
                    media_lower = media_name.lower()
                    if any(kw in media_lower for kw in self.MEETING_KEYWORDS):
                        is_meeting = True
                # Navegador con audio de Meet/Teams
                if app_lower in ("firefox", "chrome", "chromium", "brave") and media_name:
                    media_lower = media_name.lower()
                    if any(kw in media_lower for kw in self.MEETING_KEYWORDS):
                        is_meeting = True

            return app_name, media_name, is_meeting

        except Exception as e:
            logger.debug("Error obteniendo audio info: %s", e)
            return None, None, False

    async def _get_workspace(self) -> str | None:
        """Obtiene el workspace/escritorio virtual activo."""
        try:
            if self._use_wayland:
                # GNOME Wayland: no hay API directa fiable sin extension
                return None
            # X11: wmctrl
            output = await self._run_cmd("wmctrl", "-d")
            if output:
                for line in output.splitlines():
                    if " * " in line:
                        parts = line.split()
                        return parts[0] if parts else None
        except Exception:
            pass
        return None

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
