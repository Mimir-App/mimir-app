"""Integración con Odoo v11 via XML-RPC."""

import logging
import xmlrpc.client
from typing import Any

from .base import TimesheetClient, TimesheetEntryData

logger = logging.getLogger(__name__)


class OdooV11Client(TimesheetClient):
    """Cliente Odoo v11 usando XML-RPC con usuario/contraseña."""

    def __init__(self, url: str, db: str, username: str, password: str) -> None:
        self._url = url.rstrip("/")
        self._db = db
        self._username = username
        self._password = password
        self._uid: int | None = None

    async def authenticate(self) -> bool:
        """Autentica via XML-RPC."""
        try:
            common = xmlrpc.client.ServerProxy(f"{self._url}/xmlrpc/2/common")
            self._uid = common.authenticate(self._db, self._username, self._password, {})
            if self._uid:
                logger.info("Autenticado en Odoo v11 como uid=%d", self._uid)
                return True
            logger.error("Autenticación fallida en Odoo v11")
            return False
        except Exception as e:
            logger.error("Error de conexión con Odoo v11: %s", e)
            return False

    def _models(self) -> xmlrpc.client.ServerProxy:
        return xmlrpc.client.ServerProxy(f"{self._url}/xmlrpc/2/object")

    def _execute(self, model: str, method: str, *args: Any) -> Any:
        return self._models().execute_kw(
            self._db, self._uid, self._password, model, method, *args
        )

    async def get_projects(self) -> list[dict[str, Any]]:
        """Obtiene proyectos de Odoo."""
        result = self._execute(
            "project.project", "search_read",
            [[]],
            {"fields": ["id", "name"], "limit": 500},
        )
        return [{"id": r["id"], "name": r["name"]} for r in result]

    async def get_tasks(self, project_id: int) -> list[dict[str, Any]]:
        """Obtiene tareas de un proyecto."""
        result = self._execute(
            "project.task", "search_read",
            [[("project_id", "=", project_id)]],
            {"fields": ["id", "name", "project_id"], "limit": 500},
        )
        return [
            {"id": r["id"], "name": r["name"], "project_id": project_id}
            for r in result
        ]

    async def create_entry(self, entry: TimesheetEntryData) -> int:
        """Crea una línea de timesheet."""
        vals = {
            "date": entry.date,
            "project_id": entry.project_id,
            "name": entry.description,
            "unit_amount": entry.hours,
        }
        if entry.task_id:
            vals["task_id"] = entry.task_id
        result = self._execute("account.analytic.line", "create", [vals])
        logger.info("Entrada creada en Odoo v11: id=%s", result)
        return result

    async def update_entry(self, remote_id: int, entry: TimesheetEntryData) -> None:
        """Actualiza una línea de timesheet."""
        vals = {
            "name": entry.description,
            "unit_amount": entry.hours,
        }
        if entry.task_id:
            vals["task_id"] = entry.task_id
        self._execute("account.analytic.line", "write", [[remote_id], vals])

    async def get_entries(
        self, date_from: str, date_to: str, employee_id: int | None = None
    ) -> list[dict[str, Any]]:
        """Obtiene entradas de timesheet en un rango."""
        domain: list = [
            ("date", ">=", date_from),
            ("date", "<=", date_to),
        ]
        if employee_id:
            domain.append(("employee_id", "=", employee_id))

        result = self._execute(
            "account.analytic.line", "search_read",
            [domain],
            {
                "fields": [
                    "id", "date", "project_id", "task_id", "name",
                    "unit_amount", "employee_id",
                ],
                "limit": 500,
                "order": "date desc",
            },
        )
        return [
            {
                "id": r["id"],
                "date": r["date"],
                "project_id": r["project_id"][0] if r.get("project_id") else 0,
                "project_name": r["project_id"][1] if r.get("project_id") else "",
                "task_id": r["task_id"][0] if r.get("task_id") else None,
                "task_name": r["task_id"][1] if r.get("task_id") else None,
                "description": r.get("name", ""),
                "hours": r.get("unit_amount", 0),
                "employee_id": r["employee_id"][0] if r.get("employee_id") else 0,
            }
            for r in result
        ]
