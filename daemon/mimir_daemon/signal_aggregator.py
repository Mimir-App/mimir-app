"""Agregador de senales a bloques.

Reemplaza al BlockManager. Construye bloques a partir de senales
usando un algoritmo determinista basado en reglas de contexto.
"""

import json
import logging
import re
from collections import Counter
from datetime import datetime, timezone, timedelta

from .db import Database

logger = logging.getLogger(__name__)

DEFAULT_BROWSER_APPS = frozenset({
    "chrome", "chromium", "firefox", "brave", "vivaldi",
    "opera", "microsoft-edge", "zen", "floorp",
})

DEFAULT_TRANSIENT_APPS = frozenset({
    "nautilus", "thunar", "nemo", "pcmanfm", "dolphin",
})

# Nombres visibles de navegadores para strip del titulo
_BROWSER_SUFFIXES = {
    "chrome": "Google Chrome", "chromium": "Chromium",
    "firefox": "Mozilla Firefox", "brave": "Brave",
    "vivaldi": "Vivaldi", "opera": "Opera",
    "microsoft-edge": "Microsoft Edge", "zen": "Zen Browser",
    "floorp": "Floorp",
}

# Separadores comunes en titulos de navegador
_TITLE_SEPARATORS = re.compile(r"\s+[—–\-]\s+")


def extract_browser_site(title: str, app_name: str) -> str:
    """Extrae el nombre del sitio del titulo de un navegador.

    Estrategia:
    1. Eliminar el nombre del navegador del final
    2. Separar por — / – / -
    3. Tomar el ultimo segmento (normalmente el sitio)
    """
    if not title:
        return ""

    # Strip browser name from end
    suffix = _BROWSER_SUFFIXES.get(app_name.lower(), "")
    if suffix and title.endswith(suffix):
        title = title[: -len(suffix)]
        title = re.sub(r"\s*[—–\-]\s*$", "", title).strip()

    if not title:
        return ""

    # Split by separators and take last segment
    parts = _TITLE_SEPARATORS.split(title)
    return parts[-1].strip() if parts else title.strip()


def compute_context_key(
    app_name: str | None,
    window_title: str | None,
    project_path: str | None,
    browser_apps: frozenset[str] = DEFAULT_BROWSER_APPS,
) -> str:
    """Calcula la clave de contexto para una senal."""
    app = (app_name or "").lower()

    if project_path:
        return f"git:{project_path}"

    if app in browser_apps:
        site = extract_browser_site(window_title or "", app)
        if site:
            return f"web:{site}"

    return f"app:{app or 'unknown'}"


class SignalAggregator:
    """Construye bloques a partir de senales en tiempo real."""

    def __init__(
        self,
        db: Database,
        inactivity_threshold: int = 300,
        browser_apps: set[str] | frozenset[str] | None = None,
        transient_apps: set[str] | frozenset[str] | None = None,
    ) -> None:
        self._db = db
        self._inactivity_threshold = inactivity_threshold
        self._browser_apps = frozenset(browser_apps) if browser_apps else DEFAULT_BROWSER_APPS
        self._transient_apps = frozenset(transient_apps) if transient_apps else DEFAULT_TRANSIENT_APPS
        self._current_block_id: int | None = None
        self._current_context_key: str | None = None
        self._current_start_time: datetime | None = None
        self._last_signal_time: datetime | None = None
        self._window_titles: list[str] = []

    async def recover_open_blocks(self) -> None:
        """Recupera bloques auto abiertos tras un reinicio."""
        open_blocks = await self._db.get_open_blocks()
        if not open_blocks:
            return

        now = datetime.now(timezone.utc)
        for block in open_blocks:
            end_str = block.get("end_time", "")
            try:
                end_time = datetime.fromisoformat(end_str.replace("Z", "+00:00"))
            except (ValueError, AttributeError):
                end_time = now - timedelta(hours=2)

            elapsed = (now - end_time).total_seconds()

            if elapsed < self._inactivity_threshold:
                self._current_block_id = block["id"]
                self._current_context_key = block.get("app_name", "")
                self._last_signal_time = end_time
                try:
                    self._current_start_time = datetime.fromisoformat(
                        block["start_time"].replace("Z", "+00:00")
                    )
                except (ValueError, AttributeError):
                    self._current_start_time = end_time
                # Recuperar titulos de senales asociadas
                signals = await self._db.get_signals_by_block(block["id"])
                self._window_titles = [
                    s["window_title"] for s in signals if s.get("window_title")
                ]
                logger.info("Bloque #%d retomado (elapsed=%.0fs)", block["id"], elapsed)
            else:
                await self._db.update_block(block["id"], status="closed")
                logger.info("Bloque #%d cerrado (stale, elapsed=%.0fs)", block["id"], elapsed)

    async def process_signal(self, signal: dict) -> None:
        """Procesa una senal nueva y actualiza/crea bloques."""
        context_key = signal.get("context_key", "")
        app_name = signal.get("app_name", "")
        timestamp_str = signal.get("timestamp", "")
        signal_id = signal.get("id")

        try:
            signal_time = datetime.fromisoformat(timestamp_str.replace("Z", "+00:00"))
        except (ValueError, AttributeError):
            signal_time = datetime.now(timezone.utc)

        # Apps transitorias heredan contexto del bloque actual
        if app_name and app_name.lower() in self._transient_apps and self._current_block_id:
            context_key = self._current_context_key or context_key

        # Verificar si debemos cerrar el bloque actual
        should_close = False
        if self._current_block_id is not None:
            if context_key != self._current_context_key:
                should_close = True
            elif self._last_signal_time:
                gap = (signal_time - self._last_signal_time).total_seconds()
                if gap > self._inactivity_threshold:
                    should_close = True

        if should_close:
            await self._close_current_block()

        # Crear bloque nuevo si no hay uno activo
        if self._current_block_id is None:
            block_id = await self._db.create_block(
                start_time=timestamp_str,
                end_time=timestamp_str,
                duration_minutes=0.0,
                app_name=app_name or "unknown",
                window_title=signal.get("window_title", ""),
                project_path=signal.get("project_path"),
                git_branch=signal.get("git_branch"),
                git_remote=signal.get("git_remote"),
                status="auto",
            )
            self._current_block_id = block_id
            self._current_context_key = context_key
            self._current_start_time = signal_time
            self._window_titles = []
            logger.info("Nuevo bloque #%d: %s", block_id, context_key)
        else:
            # Actualizar bloque existente
            duration = 0.0
            if self._current_start_time:
                duration = (signal_time - self._current_start_time).total_seconds() / 60
            await self._db.update_block(
                self._current_block_id,
                end_time=timestamp_str,
                duration_minutes=round(duration, 1),
                window_title=signal.get("window_title", ""),
                project_path=signal.get("project_path") or None,
                git_branch=signal.get("git_branch") or None,
                git_remote=signal.get("git_remote") or None,
            )

        # Vincular senal al bloque
        if signal_id and self._current_block_id:
            await self._db.link_signal_to_block(self._current_block_id, signal_id)

        # Acumular titulos
        title = signal.get("window_title", "")
        if title and title not in self._window_titles:
            self._window_titles.append(title)

        self._last_signal_time = signal_time

    async def handle_lock(self) -> None:
        """Cierra el bloque actual al bloquear pantalla."""
        if self._current_block_id:
            await self._close_current_block()
            logger.info("Bloque cerrado por lock")

    async def handle_unlock(self) -> None:
        """Reset tras desbloqueo — la proxima senal abrira bloque nuevo."""
        self._last_signal_time = datetime.now(timezone.utc)

    async def _close_current_block(self) -> None:
        """Cierra el bloque actual."""
        if not self._current_block_id:
            return

        # Generar window_titles_json (top 20 por frecuencia)
        counter = Counter(self._window_titles)
        top_titles = [t for t, _ in counter.most_common(20)]
        titles_json = json.dumps(top_titles, ensure_ascii=False)

        end_time = (
            self._last_signal_time.isoformat()
            if self._last_signal_time
            else datetime.now(timezone.utc).isoformat()
        )

        duration = 0.0
        if self._current_start_time and self._last_signal_time:
            duration = (self._last_signal_time - self._current_start_time).total_seconds() / 60

        await self._db.update_block(
            self._current_block_id,
            status="closed",
            end_time=end_time,
            duration_minutes=round(duration, 1),
            window_titles_json=titles_json,
        )
        logger.info("Bloque #%d cerrado (%.1f min)", self._current_block_id, duration)

        self._current_block_id = None
        self._current_context_key = None
        self._current_start_time = None
        self._window_titles = []
