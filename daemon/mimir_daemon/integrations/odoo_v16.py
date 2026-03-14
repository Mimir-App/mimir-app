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

    def __init__(self, url: str, db: str, token: str) -> None:
        self._url = url.rstrip("/")
        self._db = db
        self._token = token
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
                return True

            # Fallback: intentar JSONRPC session_info (funciona con API key)
            resp = await self._client.post(
                "/web/session/get_session_info",
                json={"jsonrpc": "2.0", "method": "call", "params": {}},
            )
            data = resp.json()
            if data.get("result", {}).get("uid"):
                self._authenticated = True
                logger.info("Autenticado en Odoo v16 via session JSONRPC")
                return True

            logger.error("Autenticación fallida en Odoo v16: uid no recibido")
            return False
        except httpx.ConnectError as e:
            logger.error("Error de conexión con Odoo v16 (%s): %s", self._url, e)
            return False
        except Exception as e:
            logger.error("Error inesperado autenticando en Odoo v16: %s", e)
            return False

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
        """Obtiene entradas de timesheet en un rango de fechas."""
        domain: list = [
            ("date", ">=", date_from),
            ("date", "<=", date_to),
        ]
        if employee_id:
            domain.append(("employee_id", "=", employee_id))

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

    async def close(self) -> None:
        """Cierra el cliente HTTP."""
        await self._client.aclose()
        logger.info("Cliente Odoo v16 cerrado")
