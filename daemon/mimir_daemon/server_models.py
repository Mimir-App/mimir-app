"""Modelos Pydantic y helpers para el servidor HTTP (FastAPI)."""

from datetime import datetime

from pydantic import BaseModel


def calc_duration(start_str: str, end_str: str) -> float:
    """Calcula duracion en minutos entre dos timestamps ISO."""
    try:
        start = datetime.fromisoformat(start_str.replace("Z", "+00:00"))
        end = datetime.fromisoformat(end_str.replace("Z", "+00:00"))
        return round((end - start).total_seconds() / 60, 1)
    except (ValueError, AttributeError):
        return 0.0


class BlockUpdateRequest(BaseModel):
    """Datos editables de un bloque."""

    user_description: str | None = None
    odoo_project_id: int | None = None
    odoo_task_id: int | None = None
    odoo_project_name: str | None = None
    odoo_task_name: str | None = None


class SyncRequest(BaseModel):
    """IDs de bloques a sincronizar con Odoo."""

    block_ids: list[int]


class MergeRequest(BaseModel):
    """IDs de bloques a fusionar."""

    block_ids: list[int]


class ContextMappingRequest(BaseModel):
    """Mapeo context_key -> proyecto/tarea Odoo."""

    context_key: str
    odoo_project_id: int | None = None
    odoo_project_name: str | None = None
    odoo_task_id: int | None = None
    odoo_task_name: str | None = None


class AppConfigRequest(BaseModel):
    """Configuracion de la app recibida desde Tauri."""

    odoo_url: str = ""
    odoo_version: str = "v16"
    odoo_db: str = ""
    odoo_username: str = ""
    odoo_token: str = ""
    gitlab_url: str = ""
    gitlab_token: str = ""
    github_token: str = ""
    ai_provider: str = "none"
    ai_api_key: str = ""
    ai_user_role: str = "technical"
    ai_custom_context: str = ""


class OdooEntryUpdateRequest(BaseModel):
    """Datos editables de una entrada de timesheet en Odoo."""

    project_id: int | None = None
    task_id: int | None = None
    description: str | None = None
    hours: float | None = None
    date: str | None = None


class GeneratedBlock(BaseModel):
    """Bloque generado por el agente Claude Code CLI."""

    start_time: str
    end_time: str
    duration_minutes: float
    type: str = "development"
    description: str = ""
    odoo_project_id: int | None = None
    odoo_project_name: str | None = None
    odoo_task_id: int | None = None
    odoo_task_name: str | None = None
    confidence: float = 0.0
    context_key: str | None = None
    sources: dict | None = None


class GenerateBlocksRequest(BaseModel):
    """Resultado del agente: bloques generados para un día."""

    date: str
    blocks: list[GeneratedBlock]
