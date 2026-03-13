"""Cliente mock de timesheet para desarrollo sin Odoo."""

import logging
from typing import Any

from .base import TimesheetClient, TimesheetEntryData

logger = logging.getLogger(__name__)

# Datos mock realistas
MOCK_PROJECTS = [
    {"id": 1, "name": "Mimir - Asistente de imputación"},
    {"id": 2, "name": "Portal Cliente FactorLibre"},
    {"id": 3, "name": "ERP Módulo Inventario"},
    {"id": 4, "name": "Migración Odoo v16"},
    {"id": 5, "name": "Infraestructura DevOps"},
    {"id": 6, "name": "Soporte técnico general"},
]

MOCK_TASKS: dict[int, list[dict[str, Any]]] = {
    1: [
        {"id": 101, "name": "Desarrollo daemon", "project_id": 1},
        {"id": 102, "name": "Frontend Tauri/Vue", "project_id": 1},
        {"id": 103, "name": "Integración Odoo", "project_id": 1},
        {"id": 104, "name": "Testing y QA", "project_id": 1},
    ],
    2: [
        {"id": 201, "name": "Diseño UI/UX", "project_id": 2},
        {"id": 202, "name": "Backend API", "project_id": 2},
        {"id": 203, "name": "Despliegue staging", "project_id": 2},
    ],
    3: [
        {"id": 301, "name": "Módulo stock.picking", "project_id": 3},
        {"id": 302, "name": "Reportes inventario", "project_id": 3},
        {"id": 303, "name": "Tests funcionales", "project_id": 3},
    ],
    4: [
        {"id": 401, "name": "Migración datos", "project_id": 4},
        {"id": 402, "name": "Adaptación módulos custom", "project_id": 4},
        {"id": 403, "name": "Validación post-migración", "project_id": 4},
    ],
    5: [
        {"id": 501, "name": "CI/CD pipelines", "project_id": 5},
        {"id": 502, "name": "Monitorización", "project_id": 5},
        {"id": 503, "name": "Mantenimiento servidores", "project_id": 5},
    ],
    6: [
        {"id": 601, "name": "Incidencias clientes", "project_id": 6},
        {"id": 602, "name": "Consultas internas", "project_id": 6},
    ],
}

_next_entry_id = 1000


class MockTimesheetClient(TimesheetClient):
    """Cliente mock para desarrollo sin Odoo real."""

    def __init__(self) -> None:
        self._entries: list[dict[str, Any]] = []
        self._authenticated = False

    async def authenticate(self) -> bool:
        """Siempre autentica correctamente."""
        self._authenticated = True
        logger.info("Mock: autenticado correctamente")
        return True

    async def get_projects(self) -> list[dict[str, Any]]:
        """Devuelve proyectos mock."""
        return MOCK_PROJECTS

    async def get_tasks(self, project_id: int) -> list[dict[str, Any]]:
        """Devuelve tareas mock del proyecto."""
        return MOCK_TASKS.get(project_id, [])

    async def create_entry(self, entry: TimesheetEntryData) -> int:
        """Crea una entrada mock y devuelve su ID."""
        global _next_entry_id
        entry_id = _next_entry_id
        _next_entry_id += 1

        project = next((p for p in MOCK_PROJECTS if p["id"] == entry.project_id), None)
        tasks = MOCK_TASKS.get(entry.project_id, [])
        task = next((t for t in tasks if t["id"] == entry.task_id), None) if entry.task_id else None

        self._entries.append({
            "id": entry_id,
            "date": entry.date,
            "project_id": entry.project_id,
            "project_name": project["name"] if project else "",
            "task_id": entry.task_id,
            "task_name": task["name"] if task else None,
            "description": entry.description,
            "hours": entry.hours,
            "employee_id": 1,
        })
        logger.info("Mock: entrada creada id=%d, proyecto=%s, horas=%.2f",
                     entry_id, project["name"] if project else "?", entry.hours)
        return entry_id

    async def update_entry(self, remote_id: int, entry: TimesheetEntryData) -> None:
        """Actualiza una entrada mock."""
        for e in self._entries:
            if e["id"] == remote_id:
                e["description"] = entry.description
                e["hours"] = entry.hours
                if entry.task_id:
                    e["task_id"] = entry.task_id
                logger.info("Mock: entrada actualizada id=%d", remote_id)
                return

    async def get_entries(
        self, date_from: str, date_to: str, employee_id: int | None = None
    ) -> list[dict[str, Any]]:
        """Devuelve entradas mock en el rango."""
        return [
            e for e in self._entries
            if date_from <= e["date"] <= date_to
        ]
