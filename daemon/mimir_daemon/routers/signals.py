"""Router de senales capturadas."""

import logging
from datetime import datetime, timezone

from fastapi import APIRouter, Query, Request

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/signals")
async def get_signals(request: Request, date: str = Query(default=None), block_id: int = Query(default=None)) -> list[dict]:
    """Obtiene senales por fecha o por bloque."""
    db = request.app.state.db
    if block_id:
        return await db.get_signals_by_block(block_id)
    if not date:
        date = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    return await db.get_signals_by_date(date)
