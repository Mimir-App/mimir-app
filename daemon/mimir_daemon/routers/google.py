"""Router de Google Calendar OAuth y eventos."""

import logging

from fastapi import APIRouter, HTTPException, Query, Request

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/google/calendar/auth-url")
async def get_google_auth_url(request: Request) -> dict:
    """Devuelve la URL de autorizacion OAuth2 de Google."""
    calendar_client = request.app.state.calendar_client
    if not calendar_client:
        raise HTTPException(400, "Google Calendar no configurado. Configura client_id y client_secret.")
    url = calendar_client.get_auth_url()
    return {"url": url}


@router.get("/oauth/google/callback")
async def google_oauth_callback(request: Request, code: str = Query(...)) -> dict:
    """Callback OAuth2 — intercambia el codigo por tokens."""
    calendar_client = request.app.state.calendar_client
    if not calendar_client:
        raise HTTPException(400, "Google Calendar no configurado")
    success = await calendar_client.exchange_code(code)
    if not success:
        raise HTTPException(502, "Error al autorizar con Google")
    return {"status": "authorized", "message": "Google Calendar conectado. Puedes cerrar esta ventana."}


@router.get("/google/calendar/status")
async def google_calendar_status(request: Request) -> dict:
    """Estado de la conexion con Google Calendar."""
    calendar_client = request.app.state.calendar_client
    if not calendar_client:
        return {"configured": False, "connected": False}
    return {
        "configured": True,
        "connected": calendar_client.is_configured,
    }


@router.get("/google/calendar/current-event")
async def get_current_event(request: Request) -> dict:
    """Obtiene el evento actual del calendario (si hay uno)."""
    calendar_client = request.app.state.calendar_client
    if not calendar_client or not calendar_client.is_configured:
        return {"event": None}
    event = await calendar_client.get_current_event()
    return {"event": event}


@router.post("/google/calendar/disconnect")
async def disconnect_google_calendar(request: Request) -> dict:
    """Desconecta Google Calendar eliminando tokens."""
    calendar_client = request.app.state.calendar_client
    if calendar_client:
        await calendar_client.disconnect()
    return {"status": "disconnected"}
