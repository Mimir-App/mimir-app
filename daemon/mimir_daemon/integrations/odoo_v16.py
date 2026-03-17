"""Integración con Odoo v16 via REST/JSONRPC.

Usa httpx async para comunicarse con Odoo v16+ mediante JSONRPC.
Soporta autenticación vía API key (Bearer token) o sesión.
"""

import logging
from typing import Any

import httpx

from .base import TimesheetClient, TimesheetEntryData

logger = logging.getLogger(__name__)


class OdooV16Client(TimesheetClient):
    """Cliente Odoo v16 usando JSONRPC con API key o sesión OAuth.

    La autenticación se realiza mediante Bearer token (API key de Odoo)
    o mediante sesión JSONRPC si el endpoint REST no está disponible.
    """

    def __init__(self, url: str, db: str, token: str, timezone: str = "Europe/Madrid") -> None:
        self._url = url.rstrip("/")
        self._db = db
        self._token = token
        self._timezone = timezone
        self._client = httpx.AsyncClient(
            base_url=self._url,
            headers={
                "Authorization": f"Bearer {token}",
                "Content-Type": "application/json",
            },
            timeout=15.0,
        )
        self._session_id: str | None = None
        self._authenticated = False
        self._uid: int | None = None
        self._employee_id: int | None = None

    @property
    def employee_id(self) -> int | None:
        """ID del empleado autenticado."""
        return self._employee_id

    async def authenticate(self) -> bool:
        """Autentica con el servidor Odoo v16.

        Intenta primero con la API REST, luego con JSONRPC session.
        """
        try:
            # Intentar primero REST API (Odoo 16+ con modulo API)
            resp = await self._client.get("/api/v1/auth/check")
            if resp.status_code == 200:
                self._authenticated = True
                logger.info("Autenticado en Odoo v16 via REST API")
                await self._fetch_employee_id()
                return True

            # Fallback: intentar JSONRPC session_info (funciona con API key)
            resp = await self._client.post(
                "/web/session/get_session_info",
                json={"jsonrpc": "2.0", "method": "call", "params": {}},
            )
            data = resp.json()
            uid = data.get("result", {}).get("uid")
            if uid:
                self._authenticated = True
                self._uid = uid
                logger.info("Autenticado en Odoo v16 via session JSONRPC (uid=%d)", uid)
                await self._fetch_employee_id()
                return True

            logger.error("Autenticación fallida en Odoo v16: uid no recibido")
            return False
        except httpx.ConnectError as e:
            logger.error("Error de conexión con Odoo v16 (%s): %s", self._url, e)
            return False
        except Exception as e:
            logger.error("Error inesperado autenticando en Odoo v16: %s", e)
            return False

    async def _fetch_employee_id(self) -> None:
        """Obtiene el employee_id del usuario autenticado."""
        try:
            domain = [("user_id", "=", self._uid)] if self._uid else []
            result = await self._jsonrpc(
                "hr.employee", "search_read",
                [domain, ["id"]],
                {"limit": 1},
            )
            if result:
                self._employee_id = result[0]["id"]
                logger.info("Odoo v16: employee_id=%d", self._employee_id)
            else:
                logger.warning("Odoo v16: no se encontró empleado para uid=%s", self._uid)
        except Exception as e:
            logger.warning("Odoo v16: error obteniendo employee_id: %s", e)

    async def _jsonrpc(self, model: str, method: str, args: list, kwargs: dict | None = None) -> Any:
        """Ejecuta una llamada JSONRPC a Odoo.

        Envía la petición al endpoint /web/dataset/call_kw con el modelo,
        método y argumentos especificados.
        """
        payload = {
            "jsonrpc": "2.0",
            "method": "call",
            "params": {
                "model": model,
                "method": method,
                "args": args,
                "kwargs": kwargs or {},
            },
        }
        resp = await self._client.post("/web/dataset/call_kw", json=payload)
        resp.raise_for_status()
        result = resp.json()
        if "error" in result:
            error_msg = result["error"].get("message", "Error JSONRPC desconocido")
            error_data = result["error"].get("data", {}).get("message", "")
            full_msg = f"{error_msg}: {error_data}" if error_data else error_msg
            raise RuntimeError(full_msg)
        return result.get("result")

    async def get_projects(self) -> list[dict[str, Any]]:
        """Obtiene proyectos accesibles en Odoo v16."""
        try:
            result = await self._jsonrpc(
                "project.project", "search_read",
                [[], ["id", "name"]],
                {"limit": 500},
            )
            projects = [{"id": r["id"], "name": r["name"]} for r in (result or [])]
            logger.info("Odoo v16: %d proyectos obtenidos", len(projects))
            return projects
        except Exception as e:
            logger.error("Error obteniendo proyectos de Odoo v16: %s", e)
            return []

    async def get_tasks(self, project_id: int) -> list[dict[str, Any]]:
        """Obtiene tareas de un proyecto en Odoo v16."""
        try:
            result = await self._jsonrpc(
                "project.task", "search_read",
                [[("project_id", "=", project_id)], ["id", "name", "project_id"]],
                {"limit": 500},
            )
            tasks = [
                {"id": r["id"], "name": r["name"], "project_id": project_id}
                for r in (result or [])
            ]
            logger.info("Odoo v16: %d tareas para proyecto %d", len(tasks), project_id)
            return tasks
        except Exception as e:
            logger.error("Error obteniendo tareas de Odoo v16 (proyecto %d): %s", project_id, e)
            return []

    async def create_entry(self, entry: TimesheetEntryData) -> int:
        """Crea una línea de timesheet en Odoo v16."""
        vals: dict[str, Any] = {
            "date": entry.date,
            "project_id": entry.project_id,
            "name": entry.description,
            "unit_amount": entry.hours,
        }
        if entry.task_id:
            vals["task_id"] = entry.task_id
        try:
            result = await self._jsonrpc(
                "account.analytic.line", "create", [vals]
            )
            logger.info("Entrada creada en Odoo v16: id=%s, proyecto=%d, horas=%.2f",
                        result, entry.project_id, entry.hours)
            return result
        except Exception as e:
            logger.error("Error creando entrada en Odoo v16: %s", e)
            raise

    async def update_entry(self, remote_id: int, entry: TimesheetEntryData) -> None:
        """Actualiza una línea de timesheet existente en Odoo v16."""
        vals: dict[str, Any] = {
            "name": entry.description,
            "unit_amount": entry.hours,
        }
        if entry.task_id:
            vals["task_id"] = entry.task_id
        try:
            await self._jsonrpc(
                "account.analytic.line", "write", [[remote_id], vals]
            )
            logger.info("Entrada actualizada en Odoo v16: id=%d", remote_id)
        except Exception as e:
            logger.error("Error actualizando entrada en Odoo v16 (id=%d): %s", remote_id, e)
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
            result = await self._jsonrpc(
                "account.analytic.line", "search_read",
                [domain, ["id", "date", "project_id", "task_id", "name", "unit_amount", "employee_id"]],
                {"limit": 500, "order": "date desc"},
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
                for r in (result or [])
            ]
            logger.info("Odoo v16: %d entradas obtenidas (%s - %s)", len(entries), date_from, date_to)
            return entries
        except Exception as e:
            logger.error("Error obteniendo entradas de Odoo v16: %s", e)
            return []

    async def check_in(self) -> int:
        """Registra entrada en Odoo."""
        from datetime import datetime, timezone
        vals = {
            "employee_id": self._employee_id,
            "check_in": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S"),
        }
        try:
            result = await self._jsonrpc("hr.attendance", "create", [vals])
            logger.info("Attendance check-in creado en Odoo v16: id=%s", result)
            return result
        except Exception as e:
            logger.error("Error creando check-in en Odoo v16: %s", e)
            raise

    async def check_out(self, attendance_id: int) -> None:
        """Registra salida en Odoo."""
        from datetime import datetime, timezone
        vals = {
            "check_out": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S"),
        }
        try:
            await self._jsonrpc("hr.attendance", "write", [[attendance_id], vals])
            logger.info("Attendance check-out en Odoo v16: id=%d", attendance_id)
        except Exception as e:
            logger.error("Error en check-out Odoo v16 (id=%d): %s", attendance_id, e)
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
            result = await self._jsonrpc(
                "hr.attendance", "search_read",
                [domain, ["id", "check_in", "check_out", "employee_id"]],
                {"limit": 1, "order": "check_in desc"},
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
            logger.error("Error obteniendo attendance de Odoo v16: %s", e)
            return None

    async def close(self) -> None:
        """Cierra el cliente HTTP."""
        await self._client.aclose()
        logger.info("Cliente Odoo v16 cerrado")
