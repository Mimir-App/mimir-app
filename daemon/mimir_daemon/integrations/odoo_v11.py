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

    def __init__(self, url: str, db: str, username: str, password: str, timezone: str = "Europe/Madrid") -> None:
        self._url = url.rstrip("/")
        self._db = db
        self._username = username
        self._password = password
        self._timezone = timezone
        self._uid: int | None = None
        self._employee_id: int | None = None

    @property
    def employee_id(self) -> int | None:
        """ID del empleado autenticado."""
        return self._employee_id

    async def authenticate(self) -> bool:
        """Autentica via XML-RPC en un hilo separado."""
        try:
            self._uid = await asyncio.to_thread(self._authenticate_sync)
            if self._uid:
                logger.info("Autenticado en Odoo v11 como uid=%d", self._uid)
                await self._fetch_employee_id()
                return True
            logger.error("Autenticación fallida en Odoo v11: uid es None o 0")
            return False
        except Exception as e:
            logger.error("Error de conexión con Odoo v11: %s", e)
            return False

    async def _fetch_employee_id(self) -> None:
        """Obtiene el employee_id del usuario autenticado."""
        try:
            result = await self._execute(
                "hr.employee", "search_read",
                [[("user_id", "=", self._uid)]],
                {"fields": ["id"], "limit": 1},
            )
            if result:
                self._employee_id = result[0]["id"]
                logger.info("Odoo v11: employee_id=%d", self._employee_id)
            else:
                logger.warning("Odoo v11: no se encontró empleado para uid=%d", self._uid)
        except Exception as e:
            logger.warning("Odoo v11: error obteniendo employee_id: %s", e)

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
        """Obtiene tareas abiertas de un proyecto en Odoo (más recientes primero)."""
        try:
            result = await self._execute(
                "project.task", "search_read",
                [[("project_id", "=", project_id), ("stage_id.fold", "=", False)]],
                {"fields": ["id", "name", "project_id", "effective_hours"], "limit": 500, "order": "id desc"},
            )
            tasks = [
                {
                    "id": r["id"], "name": r["name"], "project_id": project_id,
                    "effective_hours": r.get("effective_hours", 0.0),
                }
                for r in result
            ]
            logger.info("Odoo v11: %d tareas para proyecto %d", len(tasks), project_id)
            return tasks
        except Exception as e:
            logger.error("Error obteniendo tareas de Odoo v11 (proyecto %d): %s", project_id, e)
            return []

    async def search_tasks(self, query: str, limit: int = 10) -> list[dict[str, Any]]:
        """Busca tareas por nombre en Odoo v11."""
        try:
            result = await self._execute(
                "project.task", "search_read",
                [[("name", "ilike", query)]],
                {"fields": ["id", "name", "project_id", "effective_hours"], "limit": limit},
            )
            return [
                {
                    "id": r["id"], "name": r["name"],
                    "project_id": r["project_id"][0] if isinstance(r.get("project_id"), list) else r.get("project_id"),
                    "project_name": r["project_id"][1] if isinstance(r.get("project_id"), list) else None,
                    "effective_hours": r.get("effective_hours", 0.0),
                }
                for r in result
            ]
        except Exception as e:
            logger.error("Error buscando tareas en Odoo v11: %s", e)
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
        """Obtiene entradas de timesheet en un rango de fechas.

        Si no se pasa employee_id, usa el del usuario autenticado.
        """
        eid = employee_id or self._employee_id
        domain: list = [
            ("date", ">=", date_from),
            ("date", "<=", date_to),
        ]
        if eid:
            domain.append(("employee_id", "=", eid))

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

    async def check_in(self) -> int:
        """Registra entrada en Odoo."""
        from datetime import datetime, timezone
        vals = {
            "employee_id": self._employee_id,
            "check_in": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S"),
        }
        try:
            result = await self._execute("hr.attendance", "create", [vals])
            logger.info("Attendance check-in creado en Odoo v11: id=%s", result)
            return result
        except Exception as e:
            logger.error("Error creando check-in en Odoo v11: %s", e)
            raise

    async def check_out(self, attendance_id: int) -> None:
        """Registra salida en Odoo."""
        from datetime import datetime, timezone
        vals = {
            "check_out": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S"),
        }
        try:
            await self._execute("hr.attendance", "write", [[attendance_id], vals])
            logger.info("Attendance check-out en Odoo v11: id=%d", attendance_id)
        except Exception as e:
            logger.error("Error en check-out Odoo v11 (id=%d): %s", attendance_id, e)
            raise

    async def get_today_attendance(self) -> dict[str, Any] | None:
        """Obtiene el attendance de hoy del empleado."""
        import zoneinfo
        from datetime import datetime
        user_tz = zoneinfo.ZoneInfo(self._timezone)
        today = datetime.now(user_tz).strftime("%Y-%m-%d")
        domain = [
            ("employee_id", "=", self._employee_id),
            ("check_in", ">=", f"{today} 00:00:00"),
            ("check_in", "<=", f"{today} 23:59:59"),
        ]
        try:
            result = await self._execute(
                "hr.attendance", "search_read",
                [domain],
                {"fields": ["id", "check_in", "check_out", "employee_id"], "limit": 1, "order": "check_in desc"},
            )
            if result:
                r = result[0]
                # Odoo almacena datetimes en UTC sin indicador de zona.
                # Añadimos 'Z' para que el frontend los interprete como UTC.
                ci = r.get("check_in")
                co = r.get("check_out")
                return {
                    "id": r["id"],
                    "check_in": f"{ci}Z" if ci and not ci.endswith("Z") else ci,
                    "check_out": f"{co}Z" if co and not co.endswith("Z") else co,
                    "employee_id": r["employee_id"][0] if isinstance(r.get("employee_id"), (list, tuple)) else r.get("employee_id"),
                }
            return None
        except Exception as e:
            logger.error("Error obteniendo attendance de Odoo v11: %s", e)
            return None
