"""Gestión de bloques de actividad con herencia de contexto."""

import logging
from datetime import datetime, timezone, timedelta

from .db import Database
from .platform.base import WindowInfo
from .context_enricher import EnrichedContext

logger = logging.getLogger(__name__)


class BlockManager:
    """Gestiona la creación y mantenimiento de bloques de actividad."""

    def __init__(self, db: Database, inherit_threshold: int = 900) -> None:
        self._db = db
        self._inherit_threshold = inherit_threshold  # 15 min en segundos
        self._current_block_id: int | None = None
        self._last_activity: datetime | None = None
        self._poll_count: int = 0
        self._checkpoint_interval: int = 5

    async def process_poll(
        self,
        window: WindowInfo | None,
        context: EnrichedContext,
        is_locked: bool = False,
    ) -> None:
        """Procesa un poll de actividad."""
        now = datetime.now(timezone.utc)
        self._poll_count += 1

        if is_locked or window is None:
            # Sin actividad: si hay bloque activo, cerrarlo tras umbral
            if self._current_block_id and self._last_activity:
                elapsed = (now - self._last_activity).total_seconds()
                if elapsed > self._inherit_threshold:
                    await self._close_current_block()
            return

        # Determinar si continuar bloque actual o crear uno nuevo
        should_new_block = False

        if self._current_block_id is None:
            should_new_block = True
        elif self._last_activity:
            elapsed = (now - self._last_activity).total_seconds()
            if elapsed > self._inherit_threshold:
                await self._close_current_block()
                should_new_block = True

        if should_new_block:
            await self._create_block(window, context, now)
        else:
            await self._update_current_block(window, context, now)

        self._last_activity = now

        # Checkpoint periódico
        if self._poll_count % self._checkpoint_interval == 0:
            await self._checkpoint()

    async def _create_block(
        self,
        window: WindowInfo,
        context: EnrichedContext,
        now: datetime,
    ) -> None:
        """Crea un nuevo bloque de actividad."""
        now_str = now.isoformat()
        self._current_block_id = await self._db.create_block(
            start_time=now_str,
            end_time=now_str,
            duration_minutes=0,
            app_name=window.app_name,
            window_title=window.window_title,
            project_path=context.project_path,
            git_branch=context.git_branch,
            git_remote=context.git_remote,
            status="auto",
        )
        logger.info(
            "Nuevo bloque #%d: %s - %s",
            self._current_block_id,
            window.app_name,
            window.window_title[:50],
        )

    async def _update_current_block(
        self,
        window: WindowInfo,
        context: EnrichedContext,
        now: datetime,
    ) -> None:
        """Actualiza el bloque actual con nueva actividad."""
        if self._current_block_id is None:
            return

        # Obtener bloque actual para calcular duración
        blocks = await self._db.get_blocks_by_date(now.strftime("%Y-%m-%d"))
        current = next(
            (b for b in blocks if b["id"] == self._current_block_id), None
        )
        if not current:
            return

        start = datetime.fromisoformat(current["start_time"])
        duration = (now - start).total_seconds() / 60

        await self._db.update_block(
            self._current_block_id,
            end_time=now.isoformat(),
            duration_minutes=round(duration, 1),
            app_name=window.app_name,
            window_title=window.window_title,
            project_path=context.project_path or current.get("project_path"),
            git_branch=context.git_branch or current.get("git_branch"),
            git_remote=context.git_remote or current.get("git_remote"),
        )

    async def _close_current_block(self) -> None:
        """Cierra el bloque actual."""
        if self._current_block_id:
            logger.info("Cerrando bloque #%d por inactividad", self._current_block_id)
            self._current_block_id = None

    async def _checkpoint(self) -> None:
        """Checkpoint periódico para persistir estado."""
        if self._current_block_id:
            logger.debug("Checkpoint: bloque activo #%d", self._current_block_id)

    async def handle_lock(self) -> None:
        """Maneja evento de bloqueo de pantalla."""
        await self._close_current_block()
        self._last_activity = None

    async def handle_unlock(self) -> None:
        """Maneja evento de desbloqueo de pantalla."""
        self._last_activity = datetime.now(timezone.utc)
