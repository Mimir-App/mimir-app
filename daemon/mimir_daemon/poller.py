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
        calendar_client: object | None = None,
    ) -> None:
        self._config = config
        self._db = db
        self._platform = platform
        self._aggregator = aggregator
        self._calendar = calendar_client
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
            # Verificar eventos de sesion (solo logging, bloques se generan bajo demanda)
            events = await self._platform.get_session_events()
            for event in events:
                if event.event_type == "lock":
                    logger.debug("Sesion bloqueada")
                elif event.event_type == "unlock":
                    logger.debug("Sesion desbloqueada")

            # Capturar ventana activa
            if not self._config.capture_window:
                self._last_poll = datetime.now(timezone.utc)
                return

            window = await self._platform.get_active_window()
            if not window:
                self._last_poll = datetime.now(timezone.utc)
                return

            # Enriquecer contexto (git, ssh)
            context = None
            if self._config.capture_git or self._config.capture_ssh:
                context = await enrich_pid(window.pid)
                if not self._config.capture_git and context:
                    context.project_path = None
                    context.git_branch = None
                    context.git_remote = None
                    context.last_commit_message = None
                if not self._config.capture_ssh and context:
                    context.ssh_host = None

            # Capturar contexto del sistema (idle, audio)
            from .platform.base import SystemContext
            sys_ctx = SystemContext()
            if self._config.capture_idle or self._config.capture_audio:
                sys_ctx = await self._platform.get_system_context()
                if not self._config.capture_idle:
                    sys_ctx.idle_ms = 0
                if not self._config.capture_audio:
                    sys_ctx.audio_app = None
                    sys_ctx.is_meeting = False

            # Consultar evento del calendario
            calendar_event = None
            calendar_attendees = None
            if self._calendar and hasattr(self._calendar, 'get_current_event'):
                try:
                    event = await self._calendar.get_current_event()
                    if event:
                        calendar_event = event.get("summary")
                        attendees = event.get("attendees", [])
                        calendar_attendees = ", ".join(attendees[:10]) if attendees else None
                        if event.get("is_meeting"):
                            sys_ctx.is_meeting = True
                except Exception as e:
                    logger.debug("Error consultando calendario: %s", e)

            # Calcular context_key
            browser_apps = frozenset(self._config.browser_apps) if self._config.browser_apps else None
            if sys_ctx.is_meeting and calendar_event:
                context_key = f"meeting:{calendar_event}"
            elif sys_ctx.is_meeting:
                context_key = f"meeting:{sys_ctx.audio_app or window.app_name}"
            else:
                context_key = compute_context_key(
                    app_name=window.app_name,
                    window_title=window.window_title,
                    project_path=context.project_path if context else None,
                    browser_apps=browser_apps or compute_context_key.__defaults__[0],
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
                idle_ms=sys_ctx.idle_ms,
                audio_app=sys_ctx.audio_app,
                is_meeting=1 if sys_ctx.is_meeting else 0,
                workspace=sys_ctx.workspace,
                calendar_event=calendar_event,
                calendar_attendees=calendar_attendees,
            )

            # Bloques se generan bajo demanda (no automaticamente)
            # La senal ya fue guardada en SQLite por create_signal()

            self._last_poll = datetime.now(timezone.utc)

        except Exception as e:
            logger.error("Error en poll: %s", e, exc_info=True)

    def stop(self) -> None:
        """Detiene el poller."""
        self._running = False
