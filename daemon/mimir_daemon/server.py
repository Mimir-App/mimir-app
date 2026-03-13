"""Servidor HTTP local (FastAPI) para comunicación con la app Tauri."""

import logging
from datetime import datetime, timezone

from fastapi import FastAPI, HTTPException, Query
from pydantic import BaseModel

from .db import Database
from .poller import Poller

logger = logging.getLogger(__name__)


def create_app(db: Database, poller: Poller, version: str = "0.1.0") -> FastAPI:
    """Crea la aplicación FastAPI."""

    app = FastAPI(title="Mimir Daemon", version=version)
    start_time = datetime.now(timezone.utc)

    # --- Health & Status ---

    @app.get("/health")
    async def health():
        return {"status": "ok", "version": version}

    @app.get("/status")
    async def status():
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
    async def set_mode(req: ModeRequest):
        if req.mode == "paused":
            poller.pause()
        elif req.mode in ("active", "silent"):
            poller.resume()
        else:
            raise HTTPException(400, f"Modo no válido: {req.mode}")
        return {"mode": req.mode}

    # --- Blocks ---

    @app.get("/blocks")
    async def get_blocks(date: str = Query(default=None)):
        if not date:
            date = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        return await db.get_blocks_by_date(date)

    class ConfirmResponse(BaseModel):
        status: str

    @app.post("/blocks/{block_id}/confirm")
    async def confirm_block(block_id: int):
        await db.update_block(block_id, status="confirmed")
        return {"status": "confirmed"}

    class BlockUpdateRequest(BaseModel):
        user_description: str | None = None
        odoo_project_id: int | None = None
        odoo_task_id: int | None = None
        odoo_project_name: str | None = None
        odoo_task_name: str | None = None

    @app.post("/blocks/{block_id}/update")
    async def update_block(block_id: int, req: BlockUpdateRequest):
        updates = {k: v for k, v in req.model_dump().items() if v is not None}
        if updates:
            await db.update_block(block_id, **updates)
        return {"status": "updated"}

    class SyncRequest(BaseModel):
        block_ids: list[int]

    @app.post("/blocks/sync")
    async def sync_blocks(req: SyncRequest):
        # TODO: integración con Odoo
        for block_id in req.block_ids:
            await db.update_block(block_id, status="synced")
        return {"synced": len(req.block_ids)}

    # --- Odoo (stubs) ---

    @app.get("/odoo/projects")
    async def get_odoo_projects():
        # TODO: implementar con integración Odoo
        return []

    @app.get("/odoo/tasks/{project_id}")
    async def get_odoo_tasks(project_id: int):
        # TODO: implementar con integración Odoo
        return []

    @app.get("/odoo/entries")
    async def get_odoo_entries(
        date_from: str = Query(alias="from"),
        date_to: str = Query(alias="to"),
    ):
        # TODO: implementar con integración Odoo
        return []

    # --- GitLab (stubs) ---

    @app.get("/gitlab/issues")
    async def get_gitlab_issues():
        # TODO: implementar con integración GitLab
        return []

    @app.get("/gitlab/merge_requests")
    async def get_gitlab_merge_requests():
        # TODO: implementar con integración GitLab
        return []

    return app
