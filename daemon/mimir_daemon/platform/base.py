"""Interfaz base para proveedores de plataforma."""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field


@dataclass
class WindowInfo:
    """Información de la ventana activa."""

    pid: int
    app_name: str
    window_title: str


@dataclass
class SessionEvent:
    """Evento de sesión (lock/unlock)."""

    event_type: str  # "lock" | "unlock"
    timestamp: str


@dataclass
class SystemContext:
    """Contexto adicional del sistema capturado en cada poll."""

    idle_ms: int = 0                       # Milisegundos sin input (teclado/raton)
    audio_app: str | None = None           # App con audio activo (ej: "firefox", "zoom")
    audio_media: str | None = None         # Nombre del media/stream
    is_meeting: bool = False               # Detectado como reunión
    workspace: str | None = None           # Escritorio virtual activo


class PlatformProvider(ABC):
    """Interfaz abstracta para captura de plataforma."""

    @abstractmethod
    async def get_active_window(self) -> WindowInfo | None:
        """Obtiene información de la ventana activa."""
        ...

    @abstractmethod
    async def get_session_events(self) -> list[SessionEvent]:
        """Obtiene eventos de sesión pendientes (lock/unlock)."""
        ...

    async def get_system_context(self) -> SystemContext:
        """Obtiene contexto adicional del sistema (idle, audio, workspace)."""
        return SystemContext()

    async def setup(self) -> None:
        """Inicialización de la plataforma."""

    async def teardown(self) -> None:
        """Limpieza al cerrar."""
