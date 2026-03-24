"""Router de integracion con Odoo (proyectos, tareas, attendance, entries)."""

import logging

from fastapi import APIRouter, HTTPException, Query, Request

from ..integrations.base import TimesheetEntryData
from ..server_models import OdooEntryUpdateRequest

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/odoo/projects")
async def get_odoo_projects(request: Request) -> list:
    """Obtiene proyectos de Odoo. Devuelve lista vacia si no hay cliente."""
    registry = request.app.state.registry
    client = registry.timesheet
    if not client:
        return []
    try:
        return await client.get_projects()
    except Exception as e:
        logger.error("Error obteniendo proyectos de Odoo: %s", e)
        return []


@router.get("/odoo/tasks/{project_id}")
async def get_odoo_tasks(request: Request, project_id: int) -> list:
    """Obtiene tareas de un proyecto en Odoo."""
    registry = request.app.state.registry
    client = registry.timesheet
    if not client:
        return []
    try:
        return await client.get_tasks(project_id)
    except Exception as e:
        logger.error("Error obteniendo tareas de Odoo (proyecto %d): %s", project_id, e)
        return []


@router.get("/odoo/tasks/search")
async def search_odoo_tasks(request: Request, query: str = Query(..., min_length=2), limit: int = Query(default=10)) -> list:
    """Busca tareas en Odoo por nombre. Devuelve id, name, project, effective_hours."""
    registry = request.app.state.registry
    client = registry.timesheet
    if not client:
        return []
    try:
        return await client.search_tasks(query, limit)
    except Exception as e:
        logger.error("Error buscando tareas en Odoo: %s", e)
        return []


@router.get("/odoo/entries")
async def get_odoo_entries(
    request: Request,
    date_from: str = Query(alias="from"),
    date_to: str = Query(alias="to"),
    task_id: int | None = Query(default=None),
) -> list:
    """Obtiene entradas de timesheet de Odoo en un rango."""
    registry = request.app.state.registry
    client = registry.timesheet
    if not client:
        return []
    try:
        entries = await client.get_entries(date_from, date_to)
        if task_id is not None:
            entries = [e for e in entries if e.get("task_id") == task_id]
        return entries
    except Exception as e:
        logger.error("Error obteniendo entradas de Odoo: %s", e)
        return []


@router.get("/odoo/attendance/today")
async def get_today_attendance(request: Request) -> dict:
    """Obtiene el fichaje de hoy."""
    registry = request.app.state.registry
    client = registry.timesheet
    if not client:
        return {"attendance": None}
    try:
        att = await client.get_today_attendance()
        return {"attendance": att}
    except Exception as e:
        logger.error("Error obteniendo attendance: %s", e)
        return {"attendance": None}


@router.post("/odoo/attendance/checkin")
async def attendance_checkin(request: Request) -> dict:
    """Fichar entrada."""
    registry = request.app.state.registry
    client = registry.timesheet
    if not client:
        raise HTTPException(503, "No hay cliente de timesheet configurado")
    try:
        att_id = await client.check_in()
        return {"id": att_id, "status": "checked_in"}
    except Exception as e:
        raise HTTPException(502, f"Error fichando entrada: {e}")


@router.post("/odoo/attendance/{attendance_id}/checkout")
async def attendance_checkout(request: Request, attendance_id: int) -> dict:
    """Fichar salida."""
    registry = request.app.state.registry
    client = registry.timesheet
    if not client:
        raise HTTPException(503, "No hay cliente de timesheet configurado")
    try:
        await client.check_out(attendance_id)
        return {"status": "checked_out"}
    except Exception as e:
        raise HTTPException(502, f"Error fichando salida: {e}")


@router.put("/odoo/entries/{entry_id}")
async def update_odoo_entry(request: Request, entry_id: int, req: OdooEntryUpdateRequest) -> dict:
    """Actualiza una entrada de timesheet en Odoo."""
    registry = request.app.state.registry
    client = registry.timesheet
    if not client:
        raise HTTPException(503, "No hay cliente de timesheet configurado")
    try:
        entry = TimesheetEntryData(
            date=req.date or "",
            project_id=req.project_id or 0,
            task_id=req.task_id,
            description=req.description or "",
            hours=req.hours or 0.0,
        )
        await client.update_entry(entry_id, entry)
        return {"status": "updated", "entry_id": entry_id}
    except Exception as e:
        logger.error("Error actualizando entrada Odoo %d: %s", entry_id, e)
        raise HTTPException(502, f"Error actualizando entrada: {e}")
