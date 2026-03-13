"""Ciclo principal de polling de actividad."""

import asyncio
import logging
from datetime import datetime, timezone

from .config import DaemonConfig
from .db import Database
from .platform.base import PlatformProvider
from .context_enricher import enrich_pid
from .block_manager import BlockManager

logger = logging.getLogger(__name__)


class Poller:
    """Ciclo asyncio que captura actividad cada N segundos."""

    def __init__(
        self,
        config: DaemonConfig,
        db: Database,
        platform: PlatformProvider,
        block_manager: BlockManager,
    ) -> None:
        self._config = config
        self._db = db
        self._platform = platform
        self._block_manager = block_manager
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
        """Pausa la captura (modo no molestar nivel 2)."""
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
            "Poller iniciado: intervalo=%ds, umbral=%ds",
            self._config.polling_interval,
            self._config.inherit_threshold,
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
            # Verificar eventos de sesión
            events = await self._platform.get_session_events()
            is_locked = False
            for event in events:
                if event.event_type == "lock":
                    await self._block_manager.handle_lock()
                    is_locked = True
                elif event.event_type == "unlock":
                    await self._block_manager.handle_unlock()

            # Capturar ventana activa
            window = await self._platform.get_active_window()

            # Enriquecer contexto
            context_data = None
            if window:
                context_data = await enrich_pid(window.pid)

            # Procesar en block manager
            from .context_enricher import EnrichedContext
            await self._block_manager.process_poll(
                window=window,
                context=context_data or EnrichedContext(),
                is_locked=is_locked,
            )

            self._last_poll = datetime.now(timezone.utc)

        except Exception as e:
            logger.error("Error en poll: %s", e, exc_info=True)

    def stop(self) -> None:
        """Detiene el poller."""
        self._running = False
