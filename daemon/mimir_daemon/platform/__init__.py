"""Factory para la plataforma actual."""

import sys

from .base import PlatformProvider


def get_platform_provider() -> PlatformProvider:
    """Retorna el proveedor de plataforma según el SO."""
    if sys.platform == "linux":
        from .linux import LinuxProvider
        return LinuxProvider()
    else:
        raise NotImplementedError(f"Plataforma {sys.platform} no soportada aún")
