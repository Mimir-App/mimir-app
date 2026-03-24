"""Router de mapeos context_key -> proyecto/tarea Odoo."""

import logging

from fastapi import APIRouter, HTTPException, Query, Request

from ..server_models import ContextMappingRequest

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/context-mappings")
async def get_context_mappings(request: Request) -> list[dict]:
    """Obtiene todos los mapeos context_key -> Odoo."""
    db = request.app.state.db
    return await db.get_all_context_mappings()


@router.get("/context-mappings/suggest")
async def suggest_context_mapping(request: Request, context_key: str = Query()) -> dict:
    """Sugiere un mapeo Odoo para un context_key.

    Busca: exacto -> parcial -> historial de bloques.
    Retorna el mapeo con campo 'match' (exact|partial|history) o 404.
    """
    db = request.app.state.db
    suggestion = await db.suggest_mapping(context_key)
    if not suggestion:
        raise HTTPException(404, "Sin sugerencia para este contexto")
    return suggestion


@router.put("/context-mappings")
async def upsert_context_mapping(request: Request, req: ContextMappingRequest) -> dict:
    """Crea o actualiza un mapeo context_key -> Odoo."""
    db = request.app.state.db
    await db.set_context_mapping(
        req.context_key,
        req.odoo_project_id, req.odoo_project_name,
        req.odoo_task_id, req.odoo_task_name,
    )
    return {"status": "saved"}


@router.delete("/context-mappings/{context_key:path}")
async def delete_context_mapping(request: Request, context_key: str) -> dict:
    """Elimina un mapeo context_key -> Odoo."""
    db = request.app.state.db
    await db.delete_context_mapping(context_key)
    return {"status": "deleted"}
