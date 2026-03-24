"""Router de notificaciones internas de Mimir."""

import logging

from fastapi import APIRouter, Query, Request

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/notifications")
async def get_notifications(request: Request, unread_only: bool = Query(default=True)) -> list:
    """Obtiene notificaciones."""
    db = request.app.state.db
    try:
        return await db.get_notifications(unread_only=unread_only)
    except Exception as e:
        logger.error("Error obteniendo notificaciones: %s", e)
        return []


@router.get("/notifications/count")
async def get_notification_count(request: Request) -> dict:
    """Obtiene el numero de notificaciones no leidas."""
    db = request.app.state.db
    try:
        count = await db.get_notification_count()
        return {"count": count}
    except Exception as e:
        logger.error("Error obteniendo count de notificaciones: %s", e)
        return {"count": 0}


@router.put("/notifications/{notification_id}/read")
async def mark_notification_read(request: Request, notification_id: int) -> dict:
    """Marca una notificacion como leida."""
    db = request.app.state.db
    await db.mark_notification_read(notification_id)
    return {"status": "read", "id": notification_id}


@router.put("/notifications/read-all")
async def mark_all_notifications_read(request: Request) -> dict:
    """Marca todas las notificaciones como leidas."""
    db = request.app.state.db
    await db.mark_all_notifications_read()
    return {"status": "all_read"}
