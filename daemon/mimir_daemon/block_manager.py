"""Gestion de bloques de actividad con herencia de contexto."""

from __future__ import annotations

import json
import logging
from datetime import datetime, timezone, timedelta
from typing import TYPE_CHECKING

from .db import Database
from .platform.base import WindowInfo
from .context_enricher import EnrichedContext

if TYPE_CHECKING:
    from .ai.service import AIService

logger = logging.getLogger(__name__)

# Umbral de similitud: si cambia app O proyecto, se crea bloque nuevo
_CONTEXT_CHANGE_FIELDS = ("app_name", "project_path")


class BlockManager:
    """Gestiona la creacion y mantenimiento de bloques de actividad."""

    def __init__(
        self,
        db: Database,
        inherit_threshold: int = 900,
        ai_service: AIService | None = None,
    ) -> None:
        self._db = db
        self._inherit_threshold = inherit_threshold  # 15 min en segundos
        self._ai_service = ai_service
        self._current_block_id: int | None = None
        self._current_app: str | None = None
        self._current_project: str | None = None
        self._last_activity: datetime | None = None
        self._poll_count: int = 0
        self._checkpoint_interval: int = 5
        self._window_titles: list[str] = []
        self._max_titles: int = 20

    async def recover_open_blocks(self) -> None:
        """Recupera estado tras reinicio del daemon.

        Si hay bloques abiertos (sin cerrar) de las ultimas horas,
        cierra los antiguos y continua el mas reciente si es reciente.
        """
        open_blocks = await self._db.get_open_blocks()
        if not open_blocks:
            logger.info("Sin bloques abiertos previos")
            return

        now = datetime.now(timezone.utc)
        max_age = timedelta(hours=1)

        for block in open_blocks:
            end_time = datetime.fromisoformat(block["end_time"])
            if end_time.tzinfo is None:
                end_time = end_time.replace(tzinfo=timezone.utc)
            age = now - end_time

            if age > max_age:
                # Bloque viejo: cerrarlo
                await self._db.update_block(
                    block["id"],
                    status="closed",
                )
                logger.info(
                    "Bloque #%d cerrado (antiguedad: %s)",
                    block["id"],
                    age,
                )
            else:
                # Bloque reciente: continuar
                self._current_block_id = block["id"]
                self._current_app = block.get("app_name")
                self._current_project = block.get("project_path")
                self._last_activity = end_time
                logger.info(
                    "Retomando bloque #%d (%s - %s)",
                    block["id"],
                    self._current_app,
                    self._current_project,
                )

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
            elif self._is_context_change(window, context):
                await self._close_current_block()
                should_new_block = True

        if should_new_block:
            await self._create_block(window, context, now)
        else:
            await self._update_current_block(window, context, now)

        self._last_activity = now

        # Checkpoint periodico
        if self._poll_count % self._checkpoint_interval == 0:
            await self._checkpoint(now)

    def _is_context_change(
        self, window: WindowInfo, context: EnrichedContext
    ) -> bool:
        """Detecta si hubo un cambio significativo de contexto."""
        # Cambio de aplicacion principal
        if self._current_app and window.app_name != self._current_app:
            # Algunas apps son "transitivas" (file manager, terminal) - no rompen bloque
            transient_apps = {"nautilus", "thunar", "nemo", "xterm", "alacritty"}
            if window.app_name.lower() not in transient_apps:
                return True

        # Cambio de proyecto (si ambos tienen proyecto)
        if (
            self._current_project
            and context.project_path
            and context.project_path != self._current_project
        ):
            return True

        return False

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
        self._current_app = window.app_name
        self._current_project = context.project_path
        self._window_titles = [window.window_title]
        logger.info(
            "Nuevo bloque #%d: %s - %s [%s]",
            self._current_block_id,
            window.app_name,
            window.window_title[:60],
            context.project_path or "sin proyecto",
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

        # Calcular duracion desde el start_time del bloque
        block = await self._db.get_block_by_id(self._current_block_id)
        if not block:
            self._current_block_id = None
            return

        start = datetime.fromisoformat(block["start_time"])
        if start.tzinfo is None:
            start = start.replace(tzinfo=timezone.utc)
        duration = (now - start).total_seconds() / 60

        if window.window_title not in self._window_titles:
            if len(self._window_titles) < self._max_titles:
                self._window_titles.append(window.window_title)

        await self._db.update_block(
            self._current_block_id,
            end_time=now.isoformat(),
            duration_minutes=round(duration, 1),
            window_title=window.window_title,
            project_path=context.project_path or block.get("project_path"),
            git_branch=context.git_branch or block.get("git_branch"),
            git_remote=context.git_remote or block.get("git_remote"),
        )

    async def _close_current_block(self) -> None:
        """Cierra el bloque actual."""
        if self._current_block_id:
            if self._window_titles:
                await self._db.update_block(
                    self._current_block_id,
                    window_titles_json=json.dumps(self._window_titles, ensure_ascii=False),
                )
            await self._db.update_block(
                self._current_block_id, status="closed"
            )
            logger.info(
                "Bloque #%d cerrado", self._current_block_id
            )
            # Generar descripción IA
            if self._ai_service:
                try:
                    block = await self._db.get_block_by_id(self._current_block_id)
                    if block and not block.get("user_description"):
                        from .ai.base import DescriptionRequest
                        request = DescriptionRequest(
                            app_name=block.get("app_name", ""),
                            window_title=block.get("window_title", ""),
                            project_path=block.get("project_path"),
                            git_branch=block.get("git_branch"),
                            git_remote=block.get("git_remote"),
                            duration_minutes=block.get("duration_minutes", 0),
                            window_titles=json.loads(block["window_titles_json"])
                            if block.get("window_titles_json") else None,
                        )
                        result = await self._ai_service.generate(request)
                        await self._db.update_block(
                            self._current_block_id,
                            ai_description=result.description,
                            ai_confidence=result.confidence,
                        )
                        logger.info(
                            "Descripción IA para bloque #%d: %s (%.1f)",
                            self._current_block_id, result.description, result.confidence,
                        )
                except Exception as e:
                    logger.error("Error generando descripción IA: %s", e)
            self._current_block_id = None
            self._current_app = None
            self._current_project = None
            self._window_titles = []

    async def _checkpoint(self, now: datetime) -> None:
        """Checkpoint periodico para persistir estado."""
        if self._current_block_id:
            await self._db.update_block(
                self._current_block_id,
                end_time=now.isoformat(),
            )
            logger.debug(
                "Checkpoint: bloque activo #%d", self._current_block_id
            )

    async def handle_lock(self) -> None:
        """Maneja evento de bloqueo de pantalla."""
        if self._current_block_id:
            await self._close_current_block()
        self._last_activity = None
        logger.info("Sesion bloqueada, bloque cerrado")

    async def handle_unlock(self) -> None:
        """Maneja evento de desbloqueo de pantalla."""
        self._last_activity = datetime.now(timezone.utc)
        logger.info("Sesion desbloqueada")
