"""Integración con Odoo v11 via XML-RPC.

Usa asyncio.to_thread para envolver las llamadas XMLRPC bloqueantes,
manteniendo la interfaz async del TimesheetClient.
"""

import asyncio
import logging
import xmlrpc.client
from typing import Any

from .base import TimesheetClient, TimesheetEntryData

logger = logging.getLogger(__name__)


class OdooV11Client(TimesheetClient):
    """Cliente Odoo v11 usando XML-RPC con usuario/contraseña.

    Las llamadas XMLRPC son síncronas por naturaleza, así que se ejecutan
    en un hilo separado via asyncio.to_thread para no bloquear el event loop.
    """

    def __init__(self, url: str, db: str, username: str, password: str) -> None:
        self._url = url.rstrip("/")
        self._db = db
        self._username = username
        self._password = password
        self._uid: int | None = None

    async def authenticate(self) -> bool:
        """Autentica via XML-RPC en un hilo separado."""
        try:
            self._uid = await asyncio.to_thread(self._authenticate_sync)
            if self._uid:
                logger.info("Autenticado en Odoo v11 como uid=%d", self._uid)
                return True
            logger.error("Autenticación fallida en Odoo v11: uid es None o 0")
            return False
        except Exception as e:
            logger.error("Error de conexión con Odoo v11: %s", e)
            return False

    def _authenticate_sync(self) -> int | None:
        """Autenticación síncrona XMLRPC."""
        common = xmlrpc.client.ServerProxy(f"{self._url}/xmlrpc/2/common")
        return common.authenticate(self._db, self._username, self._password, {})

    def _models(self) -> xmlrpc.client.ServerProxy:
        """Retorna el proxy de modelos XMLRPC."""
        return xmlrpc.client.ServerProxy(f"{self._url}/xmlrpc/2/object")

    def _execute_sync(self, model: str, method: str, *args: Any) -> Any:
        """Ejecuta una llamada XMLRPC síncrona."""
        return self._models().execute_kw(
            self._db, self._uid, self._password, model, method, *args
        )

    async def _execute(self, model: str, method: str, *args: Any) -> Any:
        """Ejecuta una llamada XMLRPC en un hilo separado."""
        return await asyncio.to_thread(self._execute_sync, model, method, *args)

    async def get_projects(self) -> list[dict[str, Any]]:
        """Obtiene proyectos de Odoo accesibles para el usuario."""
        try:
            result = await self._execute(
                "project.project", "search_read",
                [[]],
                {"fields": ["id", "name"], "limit": 500},
            )
            projects = [{"id": r["id"], "name": r["name"]} for r in result]
            logger.info("Odoo v11: %d proyectos obtenidos", len(projects))
            return projects
        except Exception as e:
            logger.error("Error obteniendo proyectos de Odoo v11: %s", e)
            return []

    async def get_tasks(self, project_id: int) -> list[dict[str, Any]]:
        """Obtiene tareas de un proyecto en Odoo."""
        try:
            result = await self._execute(
                "project.task", "search_read",
                [[("project_id", "=", project_id)]],
                {"fields": ["id", "name", "project_id"], "limit": 500},
            )
            tasks = [
                {"id": r["id"], "name": r["name"], "project_id": project_id}
                for r in result
            ]
            logger.info("Odoo v11: %d tareas para proyecto %d", len(tasks), project_id)
            return tasks
        except Exception as e:
            logger.error("Error obteniendo tareas de Odoo v11 (proyecto %d): %s", project_id, e)
            return []

    async def create_entry(self, entry: TimesheetEntryData) -> int:
        """Crea una línea de timesheet en Odoo."""
        vals: dict[str, Any] = {
            "date": entry.date,
            "project_id": entry.project_id,
            "name": entry.description,
            "unit_amount": entry.hours,
        }
        if entry.task_id:
            vals["task_id"] = entry.task_id
        try:
            result = await self._execute("account.analytic.line", "create", [vals])
            logger.info("Entrada creada en Odoo v11: id=%s, proyecto=%d, horas=%.2f",
                        result, entry.project_id, entry.hours)
            return result
        except Exception as e:
            logger.error("Error creando entrada en Odoo v11: %s", e)
            raise

    async def update_entry(self, remote_id: int, entry: TimesheetEntryData) -> None:
        """Actualiza una línea de timesheet existente en Odoo."""
        vals: dict[str, Any] = {
            "name": entry.description,
            "unit_amount": entry.hours,
        }
        if entry.task_id:
            vals["task_id"] = entry.task_id
        try:
            await self._execute("account.analytic.line", "write", [[remote_id], vals])
            logger.info("Entrada actualizada en Odoo v11: id=%d", remote_id)
        except Exception as e:
            logger.error("Error actualizando entrada en Odoo v11 (id=%d): %s", remote_id, e)
            raise

    async def get_entries(
        self, date_from: str, date_to: str, employee_id: int | None = None
    ) -> list[dict[str, Any]]:
        """Obtiene entradas de timesheet en un rango de fechas."""
        domain: list = [
            ("date", ">=", date_from),
            ("date", "<=", date_to),
        ]
        if employee_id:
            domain.append(("employee_id", "=", employee_id))

        try:
            result = await self._execute(
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
            entries = [
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
            logger.info("Odoo v11: %d entradas obtenidas (%s - %s)", len(entries), date_from, date_to)
            return entries
        except Exception as e:
            logger.error("Error obteniendo entradas de Odoo v11: %s", e)
            return []
