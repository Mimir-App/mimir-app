"""Ciclo principal de polling de actividad."""

import asyncio
import logging
from collections import Counter
from datetime import datetime, timezone

from .config import DaemonConfig
from .db import Database
from .platform.base import PlatformProvider
from .context_enricher import enrich_pid, EnrichedContext
from .signal_aggregator import SignalAggregator, compute_context_key

logger = logging.getLogger(__name__)


class Poller:
    """Ciclo asyncio que captura actividad cada N segundos.

    Enfoque híbrido: captura en memoria cada polling_interval (30s)
    y persiste resúmenes en DB cada signal_persist_interval (5 min).
    """

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
        # Buffer híbrido: acumula señales en memoria entre persistencias
        self._signal_buffer: list[dict] = []
        self._last_persist_time: datetime | None = None

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
            "Poller iniciado: intervalo=%ds, inactividad=%ds, persistencia=%ds",
            self._config.polling_interval,
            self._config.inactivity_threshold,
            self._config.signal_persist_interval,
        )

        try:
            while self._running:
                if not self._paused:
                    await self._poll_once()
                await asyncio.sleep(self._config.polling_interval)
        except asyncio.CancelledError:
            logger.info("Poller cancelado")
        finally:
            # Persistir buffer pendiente antes de salir
            if self._signal_buffer:
                await self._persist_summary()
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

            # Acumular señal en buffer (no persistir inmediatamente)
            now = datetime.now(timezone.utc).isoformat()
            self._signal_buffer.append({
                "timestamp": now,
                "app_name": window.app_name,
                "window_title": window.window_title,
                "project_path": context.project_path if context else None,
                "git_branch": context.git_branch if context else None,
                "git_remote": context.git_remote if context else None,
                "ssh_host": context.ssh_host if context else None,
                "pid": window.pid,
                "context_key": context_key,
                "last_commit_message": context.last_commit_message if context else None,
                "idle_ms": sys_ctx.idle_ms,
                "audio_app": sys_ctx.audio_app,
                "is_meeting": 1 if sys_ctx.is_meeting else 0,
                "workspace": sys_ctx.workspace,
                "calendar_event": calendar_event,
                "calendar_attendees": calendar_attendees,
            })

            # Persistir resumen si ha pasado el intervalo
            now_dt = datetime.now(timezone.utc)
            should_persist = (
                self._last_persist_time is None
                or (now_dt - self._last_persist_time).total_seconds()
                >= self._config.signal_persist_interval
            )
            if should_persist and self._signal_buffer:
                await self._persist_summary()
                self._last_persist_time = now_dt

            self._last_poll = now_dt

        except Exception as e:
            logger.error("Error en poll: %s", e, exc_info=True)

    async def _persist_summary(self) -> None:
        """Persiste un resumen de las señales acumuladas en el buffer.

        Agrupa por context_key y guarda una señal resumen por grupo
        con la app predominante, primer timestamp y títulos representativos.
        """
        if not self._signal_buffer:
            return

        # Agrupar por context_key
        groups: dict[str, list[dict]] = {}
        for s in self._signal_buffer:
            key = s.get("context_key", "unknown")
            groups.setdefault(key, []).append(s)

        # Filtrar señales web si browser_history activo (redundantes)
        if self._config.capture_browser_history:
            groups = {k: v for k, v in groups.items() if not k.startswith("web:")}

        persisted = 0
        for ctx_key, signals in groups.items():
            app_counter = Counter(s.get("app_name", "") for s in signals)
            app_name = app_counter.most_common(1)[0][0] if app_counter else ""

            # Títulos únicos (top 5 por frecuencia)
            title_counter = Counter(
                s.get("window_title", "") for s in signals if s.get("window_title")
            )
            top_title = title_counter.most_common(1)[0][0] if title_counter else ""

            first_ts = min(s["timestamp"] for s in signals)
            git_branch = next((s["git_branch"] for s in signals if s.get("git_branch")), None)
            git_remote = next((s["git_remote"] for s in signals if s.get("git_remote")), None)
            project_path = next((s["project_path"] for s in signals if s.get("project_path")), None)
            ssh_host = next((s["ssh_host"] for s in signals if s.get("ssh_host")), None)
            is_meeting = 1 if any(s.get("is_meeting") for s in signals) else 0
            calendar_event = next(
                (s["calendar_event"] for s in signals if s.get("calendar_event")), None
            )
            calendar_attendees = next(
                (s["calendar_attendees"] for s in signals if s.get("calendar_attendees")), None
            )
            min_idle = min(s.get("idle_ms", 0) for s in signals)
            audio_app = next(
                (s["audio_app"] for s in signals if s.get("audio_app")), None
            )

            await self._db.create_signal(
                timestamp=first_ts,
                app_name=app_name,
                window_title=top_title,
                project_path=project_path,
                git_branch=git_branch,
                git_remote=git_remote,
                ssh_host=ssh_host,
                pid=signals[-1].get("pid", 0),
                context_key=ctx_key,
                last_commit_message=next(
                    (s["last_commit_message"] for s in signals if s.get("last_commit_message")),
                    None,
                ),
                idle_ms=min_idle,
                audio_app=audio_app,
                is_meeting=is_meeting,
                workspace=signals[-1].get("workspace"),
                calendar_event=calendar_event,
                calendar_attendees=calendar_attendees,
            )
            persisted += 1

        logger.info(
            "Persistido resumen: %d señales -> %d grupos",
            len(self._signal_buffer), persisted,
        )
        self._signal_buffer.clear()

    def stop(self) -> None:
        """Detiene el poller."""
        self._running = False
