"""Servicio de notificaciones que detecta cambios en GitLab."""

import asyncio
import logging

logger = logging.getLogger(__name__)


class NotificationService:
    """Servicio de notificaciones que detecta cambios en GitLab."""

    def __init__(self, db, gitlab_source, interval_minutes: int = 5) -> None:
        self._db = db
        self._gitlab = gitlab_source
        self._interval = interval_minutes * 60
        self._snapshot: dict = {}  # Estado anterior para comparacion

    async def run(self) -> None:
        """Loop principal del servicio."""
        while True:
            try:
                await self._check_for_changes()
                await self._db.cleanup_old_notifications(days=7)
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error("Error en NotificationService: %s", e)
            await asyncio.sleep(self._interval)

    async def _check_for_changes(self) -> None:
        """Comprueba cambios en fuentes externas. TODO: implementar detección real."""
        logger.debug("NotificationService._check_for_changes: stub, pendiente de implementar")
        if not self._gitlab:
            return
        # Check issues comments
        # Check MR comments, pipeline, conflicts
        # Check TODOs
        # Create notifications for changes detected
