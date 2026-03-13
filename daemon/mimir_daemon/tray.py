"""Icono de bandeja del sistema con pystray."""

import logging
from concurrent.futures import ThreadPoolExecutor

logger = logging.getLogger(__name__)

_executor = ThreadPoolExecutor(max_workers=1)


class TrayIcon:
    """Icono de bandeja del sistema."""

    def __init__(self, on_mode_change=None, on_quit=None) -> None:
        self._on_mode_change = on_mode_change
        self._on_quit = on_quit
        self._icon = None
        self._mode = "active"

    def start(self) -> None:
        """Arranca el icono de tray en un hilo separado."""
        try:
            import pystray
            from PIL import Image

            # Crear icono simple de 22x22
            image = Image.new("RGB", (22, 22), color=(86, 156, 214))

            def make_menu():
                return pystray.Menu(
                    pystray.MenuItem(
                        "Estado: " + self._mode.capitalize(),
                        None,
                        enabled=False,
                    ),
                    pystray.Menu.SEPARATOR,
                    pystray.MenuItem(
                        "Modo Activo",
                        lambda: self._set_mode("active"),
                    ),
                    pystray.MenuItem(
                        "Silenciar Notificaciones",
                        lambda: self._set_mode("silent"),
                    ),
                    pystray.MenuItem(
                        "Pausar Captura",
                        lambda: self._set_mode("paused"),
                    ),
                    pystray.Menu.SEPARATOR,
                    pystray.MenuItem("Salir", self._quit),
                )

            self._icon = pystray.Icon(
                "mimir",
                image,
                "Mimir",
                menu=make_menu(),
            )

            _executor.submit(self._icon.run)
            logger.info("Tray icon iniciado")

        except Exception as e:
            logger.warning("No se pudo iniciar tray icon: %s", e)

    def _set_mode(self, mode: str) -> None:
        self._mode = mode
        if self._on_mode_change:
            self._on_mode_change(mode)

    def _quit(self) -> None:
        if self._icon:
            self._icon.stop()
        if self._on_quit:
            self._on_quit()

    def stop(self) -> None:
        """Detiene el icono."""
        if self._icon:
            self._icon.stop()
