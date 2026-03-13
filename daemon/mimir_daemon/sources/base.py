"""Interfaces base para fuentes de datos."""

from abc import ABC, abstractmethod
from typing import Any


class VCSSource(ABC):
    """Fuente de datos de control de versiones."""

    @abstractmethod
    async def get_issues(self) -> list[dict[str, Any]]:
        """Obtiene issues asignadas."""
        ...

    @abstractmethod
    async def get_merge_requests(self) -> list[dict[str, Any]]:
        """Obtiene merge requests asignadas/para revisar."""
        ...


class CalendarSource(ABC):
    """Fuente de datos de calendario."""

    @abstractmethod
    async def get_events(self, date_from: str, date_to: str) -> list[dict[str, Any]]:
        """Obtiene eventos del calendario."""
        ...
