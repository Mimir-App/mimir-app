"""Servidor HTTP local (FastAPI) para comunicacion con la app Tauri."""

import logging
from datetime import datetime, timezone

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from .db import Database
from .integrations.base import TimesheetEntryData
from .integrations.registry import IntegrationRegistry
from .poller import Poller

logger = logging.getLogger(__name__)


def create_app(
    db: Database,
    poller: Poller,
    registry: IntegrationRegistry | None = None,
    version: str = "0.1.0",
) -> FastAPI:
    """Crea la aplicacion FastAPI."""

    app = FastAPI(title="Mimir Daemon", version=version)
    start_time = datetime.now(timezone.utc)
    _registry = registry or IntegrationRegistry()

    # CORS para que Tauri pueda conectarse
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # --- Health & Status ---

    @app.get("/health")
    async def health() -> dict:
        return {"status": "ok", "version": version}

    @app.get("/status")
    async def status() -> dict:
        now = datetime.now(timezone.utc)
        uptime = int((now - start_time).total_seconds())
        blocks_today = await db.count_blocks_today()
        return {
            "running": poller.is_running,
            "mode": "paused" if poller._paused else "active",
            "uptime_seconds": uptime,
            "last_poll": poller.last_poll.isoformat() if poller.last_poll else None,
            "blocks_today": blocks_today,
            "version": version,
        }

    # --- Mode ---

    class ModeRequest(BaseModel):
        mode: str

    @app.post("/mode")
    async def set_mode(req: ModeRequest) -> dict:
        if req.mode == "paused":
            poller.pause()
        elif req.mode in ("active", "silent"):
            poller.resume()
        else:
            raise HTTPException(400, f"Modo no valido: {req.mode}")
        return {"mode": req.mode}

    # --- Blocks ---

    @app.get("/blocks")
    async def get_blocks(date: str = Query(default=None)) -> list[dict]:
        if not date:
            date = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        return await db.get_blocks_by_date(date)

    @app.get("/blocks/summary")
    async def get_blocks_summary(date: str = Query(default=None)) -> dict:
        if not date:
            date = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        return await db.get_blocks_summary(date)

    @app.get("/blocks/{block_id}")
    async def get_block(block_id: int) -> dict:
        block = await db.get_block_by_id(block_id)
        if not block:
            raise HTTPException(404, "Bloque no encontrado")
        return block

    @app.post("/blocks/{block_id}/confirm")
    async def confirm_block(block_id: int) -> dict:
        block = await db.get_block_by_id(block_id)
        if not block:
            raise HTTPException(404, "Bloque no encontrado")
        await db.update_block(block_id, status="confirmed")
        return {"status": "confirmed"}

    class BlockUpdateRequest(BaseModel):
        user_description: str | None = None
        odoo_project_id: int | None = None
        odoo_task_id: int | None = None
        odoo_project_name: str | None = None
        odoo_task_name: str | None = None

    @app.put("/blocks/{block_id}")
    async def update_block(block_id: int, req: BlockUpdateRequest) -> dict:
        block = await db.get_block_by_id(block_id)
        if not block:
            raise HTTPException(404, "Bloque no encontrado")
        updates = {k: v for k, v in req.model_dump().items() if v is not None}
        if updates:
            await db.update_block(block_id, **updates)
        return {"status": "updated"}

    class SyncRequest(BaseModel):
        block_ids: list[int]

    @app.post("/blocks/sync")
    async def sync_blocks(req: SyncRequest) -> dict:
        """Sincroniza bloques confirmados con Odoo."""
        client = _registry.timesheet
        if not client:
            raise HTTPException(503, "No hay cliente de timesheet configurado")

        synced = 0
        errors = []
        for block_id in req.block_ids:
            block = await db.get_block_by_id(block_id)
            if not block:
                errors.append({"block_id": block_id, "error": "No encontrado"})
                continue

            if not block.get("odoo_project_id"):
                errors.append({"block_id": block_id, "error": "Sin proyecto Odoo asignado"})
                await db.update_block(block_id, status="error", sync_error="Sin proyecto Odoo asignado")
                continue

            description = (
                block.get("user_description")
                or block.get("ai_description")
                or f"{block.get('app_name', '')} — {block.get('window_title', '')}"
            )

            entry = TimesheetEntryData(
                date=block["start_time"][:10],
                project_id=block["odoo_project_id"],
                task_id=block.get("odoo_task_id"),
                description=description,
                hours=round(block["duration_minutes"] / 60, 2),
            )

            try:
                remote_id = await client.create_entry(entry)
                await db.update_block(
                    block_id,
                    status="synced",
                    odoo_entry_id=remote_id,
                    sync_error=None,
                )
                synced += 1
                logger.info("Bloque %d sincronizado -> Odoo entry %d", block_id, remote_id)
            except Exception as e:
                error_msg = str(e)
                errors.append({"block_id": block_id, "error": error_msg})
                await db.update_block(block_id, status="error", sync_error=error_msg)
                logger.error("Error sincronizando bloque %d: %s", block_id, error_msg)

        return {"synced": synced, "errors": errors}

    @app.delete("/blocks/{block_id}")
    async def delete_block(block_id: int) -> dict:
        block = await db.get_block_by_id(block_id)
        if not block:
            raise HTTPException(404, "Bloque no encontrado")
        await db.delete_block(block_id)
        return {"status": "deleted"}

    # --- Odoo ---

    @app.get("/odoo/projects")
    async def get_odoo_projects() -> list:
        client = _registry.timesheet
        if not client:
            return []
        return await client.get_projects()

    @app.get("/odoo/tasks/{project_id}")
    async def get_odoo_tasks(project_id: int) -> list:
        client = _registry.timesheet
        if not client:
            return []
        return await client.get_tasks(project_id)

    @app.get("/odoo/entries")
    async def get_odoo_entries(
        date_from: str = Query(alias="from"),
        date_to: str = Query(alias="to"),
    ) -> list:
        client = _registry.timesheet
        if not client:
            return []
        return await client.get_entries(date_from, date_to)

    # --- GitLab (stubs) ---

    @app.get("/gitlab/issues")
    async def get_gitlab_issues() -> list:
        # TODO: implementar con integracion GitLab (Fase 5)
        return []

    @app.get("/gitlab/merge_requests")
    async def get_gitlab_merge_requests() -> list:
        # TODO: implementar con integracion GitLab (Fase 5)
        return []

    return app
