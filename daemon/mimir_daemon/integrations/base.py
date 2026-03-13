"""Interfaz base para clientes de timesheet."""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any


@dataclass
class TimesheetEntryData:
    """Datos de una entrada de timesheet."""

    date: str
    project_id: int
    task_id: int | None
    description: str
    hours: float


class TimesheetClient(ABC):
    """Interfaz abstracta para integración con sistema de timesheets."""

    @abstractmethod
    async def authenticate(self) -> bool:
        """Autentica con el servicio."""
        ...

    @abstractmethod
    async def get_projects(self) -> list[dict[str, Any]]:
        """Obtiene lista de proyectos."""
        ...

    @abstractmethod
    async def get_tasks(self, project_id: int) -> list[dict[str, Any]]:
        """Obtiene tareas de un proyecto."""
        ...

    @abstractmethod
    async def create_entry(self, entry: TimesheetEntryData) -> int:
        """Crea una entrada de timesheet. Retorna ID remoto."""
        ...

    @abstractmethod
    async def update_entry(self, remote_id: int, entry: TimesheetEntryData) -> None:
        """Actualiza una entrada existente."""
        ...

    @abstractmethod
    async def get_entries(
        self, date_from: str, date_to: str, employee_id: int | None = None
    ) -> list[dict[str, Any]]:
        """Obtiene entradas de timesheet en un rango."""
        ...
