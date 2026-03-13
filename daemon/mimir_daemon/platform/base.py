"""Interfaz base para proveedores de plataforma."""

from abc import ABC, abstractmethod
from dataclasses import dataclass


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

    async def setup(self) -> None:
        """Inicialización de la plataforma."""

    async def teardown(self) -> None:
        """Limpieza al cerrar."""
