"""Integración con Odoo v16 via REST/OAuth."""

import logging
from typing import Any

import httpx

from .base import TimesheetClient, TimesheetEntryData

logger = logging.getLogger(__name__)


class OdooV16Client(TimesheetClient):
    """Cliente Odoo v16 usando REST API con OAuth."""

    def __init__(self, url: str, db: str, token: str) -> None:
        self._url = url.rstrip("/")
        self._db = db
        self._client = httpx.AsyncClient(
            base_url=self._url,
            headers={
                "Authorization": f"Bearer {token}",
                "Content-Type": "application/json",
            },
            timeout=15.0,
        )
        self._session_id: str | None = None

    async def authenticate(self) -> bool:
        """Autentica con el servidor Odoo v16."""
        try:
            resp = await self._client.get("/api/v1/auth/check")
            if resp.status_code == 200:
                logger.info("Autenticado en Odoo v16")
                return True
            # Fallback: intentar JSONRPC session
            resp = await self._client.post(
                "/web/session/get_session_info",
                json={"jsonrpc": "2.0", "method": "call", "params": {}},
            )
            data = resp.json()
            if data.get("result", {}).get("uid"):
                logger.info("Autenticado en Odoo v16 via session")
                return True
            logger.error("Autenticación fallida en Odoo v16")
            return False
        except Exception as e:
            logger.error("Error de conexión con Odoo v16: %s", e)
            return False

    async def _jsonrpc(self, model: str, method: str, args: list, kwargs: dict | None = None) -> Any:
        """Ejecuta una llamada JSONRPC a Odoo."""
        resp = await self._client.post(
            "/web/dataset/call_kw",
            json={
                "jsonrpc": "2.0",
                "method": "call",
                "params": {
                    "model": model,
                    "method": method,
                    "args": args,
                    "kwargs": kwargs or {},
                },
            },
        )
        resp.raise_for_status()
        result = resp.json()
        if "error" in result:
            raise Exception(result["error"].get("message", "Error JSONRPC"))
        return result.get("result")

    async def get_projects(self) -> list[dict[str, Any]]:
        result = await self._jsonrpc(
            "project.project", "search_read",
            [[], ["id", "name"]],
            {"limit": 500},
        )
        return [{"id": r["id"], "name": r["name"]} for r in (result or [])]

    async def get_tasks(self, project_id: int) -> list[dict[str, Any]]:
        result = await self._jsonrpc(
            "project.task", "search_read",
            [[("project_id", "=", project_id)], ["id", "name", "project_id"]],
            {"limit": 500},
        )
        return [
            {"id": r["id"], "name": r["name"], "project_id": project_id}
            for r in (result or [])
        ]

    async def create_entry(self, entry: TimesheetEntryData) -> int:
        vals = {
            "date": entry.date,
            "project_id": entry.project_id,
            "name": entry.description,
            "unit_amount": entry.hours,
        }
        if entry.task_id:
            vals["task_id"] = entry.task_id
        result = await self._jsonrpc(
            "account.analytic.line", "create", [vals]
        )
        logger.info("Entrada creada en Odoo v16: id=%s", result)
        return result

    async def update_entry(self, remote_id: int, entry: TimesheetEntryData) -> None:
        vals = {
            "name": entry.description,
            "unit_amount": entry.hours,
        }
        if entry.task_id:
            vals["task_id"] = entry.task_id
        await self._jsonrpc(
            "account.analytic.line", "write", [[remote_id], vals]
        )

    async def get_entries(
        self, date_from: str, date_to: str, employee_id: int | None = None
    ) -> list[dict[str, Any]]:
        domain: list = [
            ("date", ">=", date_from),
            ("date", "<=", date_to),
        ]
        if employee_id:
            domain.append(("employee_id", "=", employee_id))

        result = await self._jsonrpc(
            "account.analytic.line", "search_read",
            [domain, ["id", "date", "project_id", "task_id", "name", "unit_amount", "employee_id"]],
            {"limit": 500, "order": "date desc"},
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
            for r in (result or [])
        ]

    async def close(self) -> None:
        await self._client.aclose()
