"""Stub para Windows — no implementado en MVP."""

from .base import PlatformProvider, WindowInfo, SessionEvent


class WindowsProvider(PlatformProvider):
    """Proveedor de plataforma Windows (no implementado)."""

    async def get_active_window(self) -> WindowInfo | None:
        raise NotImplementedError("Windows no soportado aún")

    async def get_session_events(self) -> list[SessionEvent]:
        raise NotImplementedError("Windows no soportado aún")
